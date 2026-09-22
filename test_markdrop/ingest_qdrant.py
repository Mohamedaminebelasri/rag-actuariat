# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier range réellement tout le contenu préparé (texte, tableaux,
# images, tableaux réglementaires) dans la base de données de recherche,
# prête à être interrogée.
# ------------------------------------------------------------------
"""ingest_qdrant.py — Ingestion RÉELLE des 4 collections Qdrant déjà
créées et vides (texte, tableaux, images, qrt — cf.
create_collection_*.py), à partir des 3 fichiers d'index déjà produits :
- index_texte_bge.json          (190 chunks texte narratif, BGE-M3 1024 dim)
- index_tableaux_texte_bge.json (18 tableaux, représentation texte BGE-M3 1024 dim)
- index_visuels_cohere.json     (36 visuels, représentation image Cohere Embed v4 1536 dim)

LECTURE SEULE sur ces 3 fichiers — aucune modification.

IDs DE POINT QDRANT — VÉRIFIÉ EMPIRIQUEMENT (pas supposé) contre le
serveur local : un ID string arbitraire (ex. "#/tables/5") est REJETÉ en
400 — "valid values are either an unsigned integer or a UUID". Les
identifiants métier lisibles (self_ref, chemin_relatif, position_header/
origine) ne sont pas des UUID — ils sont donc convertis de façon
DÉTERMINISTE via uuid.uuid5(NAMESPACE_PROJET, chaine_identifiante) : la
même chaîne produit toujours le même UUID, donc relancer ce script sur
les mêmes fichiers source réutilise les mêmes IDs de point (upsert, pas
insert — pas de doublon en cas de relance), tout en gardant l'identifiant
métier lisible dans le payload pour la traçabilité.

CAS PARTICULIER "texte" : (position_header, position_origine) n'est PAS
un identifiant unique à lui seul — 5 groupes de 2-3 chunks partagent la
même paire (sous-chunks "paragraphe/type 2" du même parent SECTION_HEADER,
limite déjà documentée dans attach_metadata.py ; vérifié ici : 183 paires
uniques sur 190 entrées). L'index de la liste (0..189, stable tant que
index_texte_bge.json n'est pas régénéré) est donc inclus dans la chaîne
identifiante pour garantir l'unicité.

MÉTADONNÉES MULTI-DOCUMENTS (Phase 2, Décision 046) — chaque point reçoit,
en plus des champs déjà présents ci-dessus, 8 champs constants pour tout le
document (company_name, company_type, source_file) ou dérivés par point
(content_type, page_number, section, chapter_code, chapter) — cf.
enrichir_payload_phase2(). Aucun champ existant n'est renommé ni retiré.

    python ingest_qdrant.py --company "Groupama" --type "mutuelle" --year 2025 --source-file SFCR_2025_Groupe-Groupama.pdf
"""

import argparse
import json
import re
import sys
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qdrant_client import QdrantClient
from qdrant_client.http.models import PointStruct

from parsers import _CODE as _CODE_SECTION

BASE_DIR = Path(__file__).parent
DOSSIER_SOURCE = BASE_DIR / "output_structure_brute"
INDEX_TEXTE_JSON = DOSSIER_SOURCE / "index_texte_bge.json"
INDEX_TABLEAUX_TEXTE_JSON = DOSSIER_SOURCE / "index_tableaux_texte_bge.json"
INDEX_VISUELS_COHERE_JSON = DOSSIER_SOURCE / "index_visuels_cohere.json"

HOTE_QDRANT = "localhost"
PORT_QDRANT = 6333

# Espace de noms fixe pour les UUID déterministes de ce projet — évite
# toute collision avec d'autres données qui utiliseraient le même schéma
# uuid5 sur un serveur Qdrant partagé.
NAMESPACE_PROJET = uuid.uuid5(uuid.NAMESPACE_DNS, "sfcr-groupama-2025.rag-actuariat")

N_TEXTE_ATTENDU = 190
N_TABLEAUX_ATTENDU = 18
N_IMAGES_ATTENDU = 5
N_QRT_ATTENDU = 13


def id_deterministe(chaine_identifiante, annee=None):
    """Convertit une chaîne métier (self_ref, chemin_relatif, position...)
    en UUID stable — Qdrant n'accepte que uint/UUID comme ID de point
    (vérifié empiriquement contre le serveur local, pas supposé). Même
    chaîne en entrée => même UUID en sortie, à chaque exécution.

    `annee` optionnel, absent par défaut : préserve EXACTEMENT les IDs
    déjà utilisés pour l'ingestion 2025 existante (aucun appel existant ne
    passe ce paramètre). PROBLÈME RÉEL IDENTIFIÉ avant d'ajouter ce
    paramètre : la numérotation Docling (self_ref, position_header...)
    repart de 0 à chaque conversion indépendante — sans salage par année,
    "#/tables/6" en 2024 produirait le MÊME UUID que "#/tables/6" en 2025,
    et un upsert écraserait silencieusement le point 2025 existant. Passer
    `annee` (ex. 2024) préfixe la chaîne identifiante et garantit un UUID
    disjoint de tout ID déjà utilisé sans ce préfixe."""
    if annee is not None:
        chaine_identifiante = f"{annee}::{chaine_identifiante}"
    return str(uuid.uuid5(NAMESPACE_PROJET, chaine_identifiante))


def charger_json(chemin):
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


# Un segment de chemin_hierarchique porte un code de section SFCR/EIOPA
# reconnu s'il COMMENCE par ce motif ("A.", "A.1.", "A.1.1. Informations...").
# Même motif que parsers._CODE (importé, pas dupliqué) — la détection de
# chapitre réutilise l'heuristique déjà validée sur le sommaire/les titres
# narratifs, appliquée ici à chemin_hierarchique (déjà présent dans les 4
# collections) plutôt qu'à structure_finale_v4.json directement : un seul
# point d'injection pour les 4 collections, pas 4 branchements distincts en
# amont (cf. Décision 046).
_CODE_SECTION_RE = re.compile(rf"^({_CODE_SECTION})\s*")


def extraire_chapitre(chemin_hierarchique):
    """Retourne (section, chapter_code, chapter) à partir du DERNIER segment
    (le plus profond) de chemin_hierarchique qui porte un code de section
    reconnu. (None, None, None) si aucun segment n'en porte — cas réel :
    chunks "SYNTHÈSE" (avant la 1ère section lettrée A-E), et les 4
    collections quand chemin_hierarchique est None (QRT, cf.
    build_index_visuels.py)."""
    if not chemin_hierarchique:
        return None, None, None
    for segment in reversed(chemin_hierarchique.split(" > ")):
        segment = segment.strip()
        m = _CODE_SECTION_RE.match(segment)
        if m:
            code = m.group(1).rstrip(".")
            return code[0], code, segment
    return None, None, None


def enrichir_payload_phase2(payload, pages, chemin_hierarchique, content_type,
                             company_name, company_type, source_file):
    """Ajoute au payload existant (jamais modifié en place — retourne un
    NOUVEAU dict) les 8 champs Phase 2 (Décision 046) : 3 constants pour
    tout le document, 5 dérivés par point. `page_number` = la plus petite
    page de `pages` (liste déjà présente) — un entier unique demandé par la
    spec, "pages" (liste) reste inchangé à côté, jamais retiré. Pour le
    contenu QRT, `chapter` vaut explicitement "Annexes QRT" (structure SFCR
    standard) plutôt que None — QRT n'a jamais de chemin_hierarchique
    (rendu pleine page, pas d'ancrage Docling), mais appartient bien à un
    chapitre nommé, contrairement à "SYNTHÈSE" qui n'en a réellement pas."""
    section, chapter_code, chapter = extraire_chapitre(chemin_hierarchique)
    if content_type == "qrt" and chapter is None:
        chapter = "Annexes QRT"
    return {
        **payload,
        "company_name": company_name,
        "company_type": company_type,
        "source_file": source_file,
        "content_type": content_type,
        "page_number": min(pages) if pages else None,
        "section": section,
        "chapter_code": chapter_code,
        "chapter": chapter,
    }


def ingerer_texte(client, index_texte_json=None, annee=None,
                   company_name=None, company_type=None, source_file=None):
    """Collection "texte" : 1 point par chunk, vecteur nommé "dense"."""
    entrees = charger_json(index_texte_json or INDEX_TEXTE_JSON)
    points = []
    for i, e in enumerate(entrees):
        # (position_header, position_origine) seul n'est PAS unique (cf.
        # docstring du module) — l'index de la liste désambiguïse.
        chaine_id = f"texte:{i:04d}:{e['position_header']}:{e.get('position_origine')}"
        payload = {
            "position_origine": e.get("position_origine"),
            "position_header": e["position_header"],
            "chemin_hierarchique": e["chemin_hierarchique"],
            "pages": e["pages"],
            "year": e["year"],
        }
        payload = enrichir_payload_phase2(
            payload, e["pages"], e["chemin_hierarchique"], "text",
            company_name, company_type, source_file,
        )
        points.append(PointStruct(
            id=id_deterministe(chaine_id, annee=annee),
            vector={"dense": e["embedding"]},
            payload=payload,
        ))
    client.upsert(collection_name="texte", points=points)
    return len(points)


def ingerer_tableaux(client, index_tableaux_texte_json=None, index_visuels_cohere_json=None, annee=None,
                      company_name=None, company_type=None, source_file=None):
    """Collection "tableaux" : 1 point PAR TABLEAU, fusionnant le vecteur
    "texte" (index_tableaux_texte_bge.json) et le vecteur "image"
    (index_visuels_cohere.json, type="tableau") par self_ref. Un self_ref
    présent d'un seul côté est signalé et EXCLU — jamais de point à
    vecteur manquant créé."""
    entrees_texte = {e["self_ref"]: e for e in charger_json(index_tableaux_texte_json or INDEX_TABLEAUX_TEXTE_JSON)}
    entrees_visuels = {
        e["self_ref"]: e for e in charger_json(index_visuels_cohere_json or INDEX_VISUELS_COHERE_JSON)
        if e["type"] == "tableau"
    }

    self_refs_texte = set(entrees_texte)
    self_refs_visuels = set(entrees_visuels)
    manquants_visuel = sorted(self_refs_texte - self_refs_visuels)
    manquants_texte = sorted(self_refs_visuels - self_refs_texte)
    if manquants_visuel:
        print(f"  >>> {len(manquants_visuel)} self_ref présent(s) dans index_tableaux_texte_bge.json "
              f"mais ABSENT(S) de index_visuels_cohere.json (vecteur 'image' manquant, point EXCLU) : "
              f"{manquants_visuel}")
    if manquants_texte:
        print(f"  >>> {len(manquants_texte)} self_ref présent(s) dans index_visuels_cohere.json "
              f"mais ABSENT(S) de index_tableaux_texte_bge.json (vecteur 'texte' manquant, point EXCLU) : "
              f"{manquants_texte}")

    self_refs_communs = sorted(self_refs_texte & self_refs_visuels)
    points = []
    for self_ref in self_refs_communs:
        e_texte = entrees_texte[self_ref]
        e_visuel = entrees_visuels[self_ref]

        # Contrôle de cohérence : les deux scripts amont recalculent
        # chemin_hierarchique via la MÊME logique réutilisée
        # (resoudre_chemin_hierarchique) — un désaccord signalerait une
        # régression entre les deux, pas un simple choix arbitraire à faire.
        if e_texte["chemin_hierarchique"] != e_visuel["chemin_hierarchique"]:
            print(f"  >>> ATTENTION — chemin_hierarchique DIVERGENT pour {self_ref} entre les 2 "
                  f"sources : {e_texte['chemin_hierarchique']!r} vs {e_visuel['chemin_hierarchique']!r} "
                  "— valeur de index_visuels_cohere.json retenue, à investiguer.")

        payload = {
            "self_ref": self_ref,
            "chemin_hierarchique": e_visuel["chemin_hierarchique"],
            # pages : celles de index_tableaux_texte_bge.json (dérivées
            # directement de Docling, TOUJOURS renseignées), pas celles
            # de index_visuels_cohere.json (dérivées du texte narratif,
            # vides pour les 5 tableaux jamais référencés).
            "pages": e_texte["pages"],
            "year": e_texte["year"],
            "chemin_relatif": e_visuel["chemin_relatif"],
        }
        payload = enrichir_payload_phase2(
            payload, e_texte["pages"], e_visuel["chemin_hierarchique"], "table",
            company_name, company_type, source_file,
        )
        points.append(PointStruct(
            id=id_deterministe(self_ref, annee=annee),
            vector={"texte": e_texte["embedding"], "image": e_visuel["embedding"]},
            payload=payload,
        ))
    client.upsert(collection_name="tableaux", points=points)
    return len(points)


def ingerer_visuels_simple(client, nom_collection, type_filtre, index_visuels_cohere_json=None, annee=None,
                            company_name=None, company_type=None, source_file=None):
    """Collections "images" et "qrt" : même structure, 1 point par entrée
    de index_visuels_cohere.json filtrée sur type_filtre, vecteur nommé
    "image" uniquement. content_type dérivé de nom_collection ("images" ->
    "image", "qrt" -> "qrt") — les 2 seuls appels existants (cf. main())."""
    content_type = "qrt" if nom_collection == "qrt" else "image"
    entrees = [e for e in charger_json(index_visuels_cohere_json or INDEX_VISUELS_COHERE_JSON) if e["type"] == type_filtre]
    points = []
    for e in entrees:
        # self_ref est None pour les pages QRT (pas d'item Docling, cf.
        # build_index_visuels.py) — chemin_relatif sert alors d'identifiant
        # (toujours présent et unique par fichier physique ; inclut déjà
        # l'année, ex. "2024/qrt_pages/page_74.png" — pas de collision
        # possible même sans le paramètre `annee`, mais on le passe quand
        # même ici par cohérence avec les 3 autres fonctions).
        chaine_id = e["self_ref"] if e["self_ref"] else e["chemin_relatif"]
        payload = {
            "self_ref": e["self_ref"],
            "chemin_hierarchique": e["chemin_hierarchique"],
            "pages": e["pages"],
            "year": e["year"],
            "chemin_relatif": e["chemin_relatif"],
        }
        payload = enrichir_payload_phase2(
            payload, e["pages"], e["chemin_hierarchique"], content_type,
            company_name, company_type, source_file,
        )
        points.append(PointStruct(
            id=id_deterministe(chaine_id, annee=annee),
            vector={"image": e["embedding"]},
            payload=payload,
        ))
    client.upsert(collection_name=nom_collection, points=points)
    return len(points)


def main(index_texte_json=None, index_tableaux_texte_json=None, index_visuels_cohere_json=None,
         annee=None, n_texte_attendu=None, n_tableaux_attendu=None, n_images_attendu=None,
         n_qrt_attendu=None, verifier_delta_uniquement=False,
         company_name="Groupama", company_type="mutuelle", source_file="SFCR_2025_Groupe-Groupama.pdf"):
    """Paramètres optionnels (défaut = None) : préservent EXACTEMENT le
    comportement 2025 existant (fichiers/constantes du module, aucun
    salage d'ID) quand appelés sans argument. Passés explicitement (cf.
    ingest_qdrant_2024.py), ils permettent de réutiliser cette même
    fonction pour ingérer un autre document dans les 4 collections
    EXISTANTES, avec des IDs garantis non-collisionnants (cf.
    id_deterministe) — jamais de nouvelle collection créée ici.

    `verifier_delta_uniquement` : si True, la vérification finale compare
    le nombre de points APRÈS à AVANT plus n_attendu (delta), plutôt qu'un
    total absolu — nécessaire quand la collection contient déjà des
    points d'une autre année.

    `company_name`/`company_type`/`source_file` (Décision 046) : défaut
    "Groupama"/"mutuelle" pour préserver le comportement des appels
    existants (main() sans argument, ingest_qdrant_2024.py) sans qu'ils
    aient besoin d'être modifiés pour continuer à fonctionner — seul
    `source_file` n'a pas de défaut générique sensé (dépend du document),
    passé explicitement par l'appelant (cf. parse_cli())."""
    client = QdrantClient(host=HOTE_QDRANT, port=PORT_QDRANT)

    comptes_avant = {}
    if verifier_delta_uniquement:
        for nom in ("texte", "tableaux", "images", "qrt"):
            comptes_avant[nom] = client.get_collection(nom).points_count

    kwargs_phase2 = dict(company_name=company_name, company_type=company_type, source_file=source_file)

    print("Ingestion 'texte'...")
    n_texte = ingerer_texte(client, index_texte_json=index_texte_json, annee=annee, **kwargs_phase2)
    print(f"  {n_texte} point(s) envoyé(s)")

    print("\nIngestion 'tableaux'...")
    n_tableaux = ingerer_tableaux(
        client, index_tableaux_texte_json=index_tableaux_texte_json,
        index_visuels_cohere_json=index_visuels_cohere_json, annee=annee, **kwargs_phase2,
    )
    print(f"  {n_tableaux} point(s) envoyé(s)")

    print("\nIngestion 'images'...")
    n_images = ingerer_visuels_simple(client, "images", "image",
                                       index_visuels_cohere_json=index_visuels_cohere_json, annee=annee,
                                       **kwargs_phase2)
    print(f"  {n_images} point(s) envoyé(s)")

    print("\nIngestion 'qrt'...")
    n_qrt = ingerer_visuels_simple(client, "qrt", "page_qrt",
                                    index_visuels_cohere_json=index_visuels_cohere_json, annee=annee,
                                    **kwargs_phase2)
    print(f"  {n_qrt} point(s) envoyé(s)")

    # --- Vérification finale : RE-INTERROGER Qdrant, pas se fier au
    # nombre de points "envoyés" (qui pourrait différer d'un comptage réel
    # en cas d'échec partiel silencieux d'un upsert). ---
    print("\n" + "=" * 70)
    print("VÉRIFICATION (comptage réel sur Qdrant, après ingestion)")
    print("=" * 70)
    attendu = {
        "texte": n_texte_attendu if n_texte_attendu is not None else N_TEXTE_ATTENDU,
        "tableaux": n_tableaux_attendu if n_tableaux_attendu is not None else N_TABLEAUX_ATTENDU,
        "images": n_images_attendu if n_images_attendu is not None else N_IMAGES_ATTENDU,
        "qrt": n_qrt_attendu if n_qrt_attendu is not None else N_QRT_ATTENDU,
    }
    tout_ok = True
    for nom_collection, n_attendu in attendu.items():
        info = client.get_collection(nom_collection)
        if verifier_delta_uniquement:
            valeur_comparee = info.points_count - comptes_avant[nom_collection]
        else:
            valeur_comparee = info.points_count
        statut = "OK" if valeur_comparee == n_attendu else "ÉCART"
        if statut != "OK":
            tout_ok = False
        libelle = "delta" if verifier_delta_uniquement else "total"
        print(f"  {nom_collection:10} : {info.points_count} point(s) au total, "
              f"{libelle}={valeur_comparee} (attendu {n_attendu}) [{statut}]")

    if tout_ok:
        print("\nLes 4 collections contiennent exactement le nombre de points attendu.")
    else:
        print("\n>>> ATTENTION — au moins une collection a un nombre de points différent de "
              "l'attendu (cf. détail ci-dessus, self_ref manquants notamment).")


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--company", dest="company_name", default="Groupama",
                    help="Nom de l'entreprise (défaut : %(default)s, pour préserver l'appel sans argument)")
    p.add_argument("--type", dest="company_type", default="mutuelle",
                    help="Type d'entreprise, ex. mutuelle/SA/institution de prévoyance (défaut : %(default)s)")
    p.add_argument("--year", dest="annee", type=int, default=None,
                    help="Année du document — salage d'ID (cf. id_deterministe) ; None = comportement 2025 inchangé")
    p.add_argument("--source-file", dest="source_file", default="SFCR_2025_Groupe-Groupama.pdf",
                    help="Nom du fichier PDF source (défaut : %(default)s)")
    p.add_argument("--index-texte", dest="index_texte_json", default=None)
    p.add_argument("--index-tableaux-texte", dest="index_tableaux_texte_json", default=None)
    p.add_argument("--index-visuels", dest="index_visuels_cohere_json", default=None)
    p.add_argument("--n-texte-attendu", type=int, default=None)
    p.add_argument("--n-tableaux-attendu", type=int, default=None)
    p.add_argument("--n-images-attendu", type=int, default=None)
    p.add_argument("--n-qrt-attendu", type=int, default=None)
    p.add_argument("--verifier-delta-uniquement", action="store_true",
                    help="Comparer le nombre de points ajoutés (delta) plutôt qu'un total absolu — "
                         "à utiliser quand les collections contiennent déjà d'autres documents")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_cli()
    main(
        index_texte_json=args.index_texte_json,
        index_tableaux_texte_json=args.index_tableaux_texte_json,
        index_visuels_cohere_json=args.index_visuels_cohere_json,
        annee=args.annee,
        n_texte_attendu=args.n_texte_attendu,
        n_tableaux_attendu=args.n_tableaux_attendu,
        n_images_attendu=args.n_images_attendu,
        n_qrt_attendu=args.n_qrt_attendu,
        verifier_delta_uniquement=args.verifier_delta_uniquement,
        company_name=args.company_name,
        company_type=args.company_type,
        source_file=args.source_file,
    )
