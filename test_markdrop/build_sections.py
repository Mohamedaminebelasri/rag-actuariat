# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier regroupe le texte brut extrait du PDF en sections cohérentes,
# une par titre du document. C'est ce qui permet ensuite de retrouver un
# passage précis plutôt que tout le rapport d'un coup.
# ------------------------------------------------------------------
"""build_sections.py — Regroupe le contenu narratif (hors annexes QRT) de
structure_finale_v2.json en chunks hiérarchiques, un par SECTION_HEADER.

⚠️ LIMITE CRITIQUE VÉRIFIÉE AVANT D'ÉCRIRE CE SCRIPT (pas découverte après
coup) : extract_raw_structure.py ne conserve que les 100 premiers
caractères de chaque item texte ("extrait"). Vérifié sur les données
réelles : 638 items texte sur 906 (70%) sont tronqués exactement à 100
caractères — leur contenu réel est plus long mais n'a JAMAIS été
sauvegardé nulle part (ni le DoclingDocument complet, ni un texte
intégral). Conséquence directe : le "nombre de mots" calculé ici ne
reflète PAS la vraie longueur du contenu narratif, seulement le nombre
d'items × ~100 caractères plafonnés. Ce script reste utile pour valider
la LOGIQUE DE REGROUPEMENT HIÉRARCHIQUE (laquelle section contient quoi),
mais la distribution de mots et le classement "plus longs/plus courts"
demandés à l'étape 7 doivent être interprétés avec cette réserve — ils ne
serviront à un vrai re-découpage (étape 3) qu'une fois le texte intégral
récupéré (reconversion avec sauvegarde complète du DoclingDocument).

Règle de regroupement (donnée par l'utilisateur) : un chunk = tout le
contenu qui suit un SECTION_HEADER, jusqu'au PROCHAIN section_header de
même niveau ou de niveau numériquement inférieur ou égal (plus haut dans
la hiérarchie). Un header plus profond (enfant) NE FERME PAS le chunk du
parent — son contenu continue d'alimenter le chunk du parent EN PLUS de
générer son propre chunk, plus étroit. Les chunks se chevauchent donc
volontairement (rollup parent + chunk enfant plus granulaire) : le
re-découpage à l'étape 3 décidera quoi garder.

Ne modifie jamais structure_finale_v2.json (lecture seule).

    python build_sections.py [structure_finale_v2.json] [dossier_sortie]
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

import os

# Seuil confirmé par comparison_sommaire.json sur SFCR_2025_Groupe-Groupama.pdf :
# au-delà, annexes QRT. Ce seuil dépend du document (pagination différente
# d'une année sur l'autre — vérifié : 73 pour SFCR_2024_Groupe-Groupama.pdf,
# pas 77) : surchargeable via la variable d'environnement PAGE_MIN_QRT_OVERRIDE
# pour les scripts qui réutilisent bs.PAGE_MIN_QRT/bs.est_zone_qrt en sous-processus
# sur un autre document, sans dupliquer ce module ni changer le défaut 2025.
PAGE_MIN_QRT = int(os.environ.get("PAGE_MIN_QRT_OVERRIDE", 77))

# Types de contenu NON textuel : leur contenu n'est jamais inclus tel quel
# dans le texte du chunk (ils sont traités par les index séparés
# table/image du pipeline global) — seule une référence inline est
# insérée, à leur emplacement exact dans le flux de lecture.
# "document_index" ajouté à cette liste après vérification : son "extrait"
# est TOUJOURS None dans structure_finale.json (Docling le représente sans
# attribut .text, comme les tableaux) — impossible de le traiter comme du
# texte de toute façon, ce n'est pas un choix arbitraire de ce script.
TYPES_NON_TEXTUELS = {
    "table": "TABLEAU",
    "picture": "IMAGE",
    "caption": "LEGENDE",
    "document_index": "INDEX",
}


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("structure_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "structure_finale_v2.json"))
    p.add_argument("output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"))
    return p.parse_args()


def est_zone_qrt(item):
    """Vrai si l'item touche une page >= PAGE_MIN_QRT (zone annexes)."""
    return any(p >= PAGE_MIN_QRT for p in item.get("pages", []))


def trouver_fin_chunk(headers, i):
    """Pour le header headers[i], retourne l'index (dans `headers`) du
    PROCHAIN header de niveau <= headers[i]['niveau'], ou len(headers) s'il
    n'y en a pas. O(n) par header, O(n²) au total — largement suffisant
    pour ~190 headers, privilégié ici pour sa lisibilité."""
    niveau_ref = headers[i]["niveau"]
    for j in range(i + 1, len(headers)):
        if headers[j]["niveau"] <= niveau_ref:
            return j
    return len(headers)


def construire_chemins_hierarchiques(headers):
    """Calcule, pour CHAQUE header, son chemin hiérarchique complet
    (liste de titres, du plus haut niveau jusqu'à lui-même), via une pile
    parcourue dans l'ordre de lecture réel (le champ position, déjà
    trié). Gère nativement les niveaux manqués : si un H4 apparaît sans
    H3 juste avant dans le flux, la pile ne contient alors que les
    niveaux réellement rencontrés (ex. H2), et le chemin remonte
    directement à ce niveau-là sans supposer un H3 fantôme."""
    chemins = {}
    pile = []  # liste de (niveau, titre), du plus haut (racine) au plus profond
    for h in headers:
        niveau = h["niveau"]
        # Retire de la pile tout ancêtre de niveau >= au niveau courant :
        # un header de niveau N ferme tous les niveaux N et plus profonds.
        while pile and pile[-1][0] >= niveau:
            pile.pop()
        chemin = [titre for _, titre in pile] + [h["extrait"]]
        chemins[h["position"]] = chemin
        pile.append((niveau, h["extrait"]))
    return chemins


def assembler_contenu(items_span):
    """Assemble le texte d'un chunk à partir des items compris dans son
    empan (hors le header de tête lui-même, déjà exclu par l'appelant).
    Retourne (texte_assemble, nb_mots, pages_couvertes). Les items non
    textuels (TYPES_NON_TEXTUELS) deviennent un marqueur inline à leur
    position exacte, sans contribuer au texte ni au compte de mots."""
    lignes = []
    nb_mots = 0
    pages = set()

    for item in items_span:
        pages.update(item.get("pages", []))
        if item["type"] in TYPES_NON_TEXTUELS:
            etiquette = TYPES_NON_TEXTUELS[item["type"]]
            lignes.append(f"[{etiquette}: {item['self_ref']}]")
        else:
            texte = item.get("extrait") or ""
            if texte:
                lignes.append(texte)
                nb_mots += len(texte.split())

    return "\n".join(lignes), nb_mots, sorted(pages)


def construire_sections(items):
    """Construit un chunk par SECTION_HEADER (chevauchement volontaire
    parent/enfant, cf. docstring du module)."""
    items_tries = sorted(items, key=lambda it: it["position"])
    headers = [it for it in items_tries if it["type"] == "section_header"]
    chemins = construire_chemins_hierarchiques(headers)

    # index -> liste des items (tous types) strictement après ce header et
    # avant le prochain header de niveau <=, pour construction rapide des
    # empans sans re-scanner toute la liste à chaque header.
    positions = [it["position"] for it in items_tries]

    sections = []
    for i, header in enumerate(headers):
        fin_idx = trouver_fin_chunk(headers, i)
        position_fin = headers[fin_idx]["position"] if fin_idx < len(headers) else None

        span = [
            it for it in items_tries
            if it["position"] > header["position"]
            and (position_fin is None or it["position"] < position_fin)
        ]

        texte, nb_mots, pages_contenu = assembler_contenu(span)
        pages_chunk = sorted(set(header.get("pages", [])) | set(pages_contenu))

        sections.append({
            "titre": header["extrait"],
            "chemin_hierarchique": chemins[header["position"]],
            "niveau": header["niveau"],
            "position_header": header["position"],
            "pages": pages_chunk,
            "nb_mots": nb_mots,
            "texte": texte,
        })

    return sections


def main():
    args = parse_cli()
    with open(args.structure_json, encoding="utf-8") as f:
        items = json.load(f)

    items_narratifs = [it for it in items if not est_zone_qrt(it)]
    n_exclus = len(items) - len(items_narratifs)
    print(f"Items chargés : {len(items)} | exclus (page >= {PAGE_MIN_QRT}, annexes QRT) : "
          f"{n_exclus} | restants pour cette passe : {len(items_narratifs)}")

    sections = construire_sections(items_narratifs)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "sections_brutes.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)

    # --- Résumé ---
    nb_mots_liste = [s["nb_mots"] for s in sections]
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Chunks produits : {len(sections)}")
    if nb_mots_liste:
        print(f"  Nombre de mots  : min={min(nb_mots_liste)}  "
              f"max={max(nb_mots_liste)}  médiane={statistics.median(nb_mots_liste):.0f}")

    print("\n  ⚠️  Rappel : ces comptes de mots sont plafonnés par la troncature à 100 "
          "caractères des items texte (cf. docstring) — 70% des items texte réels sont "
          "concernés. Ne pas encore s'en servir pour décider des seuils de re-découpage "
          "(étape 3) sans avoir récupéré le texte intégral.")

    sections_triees = sorted(sections, key=lambda s: s["nb_mots"])
    print(f"\n  10 chunks les PLUS COURTS (mots) :")
    for s in sections_triees[:10]:
        print(f"    {s['nb_mots']:4} mots | p.{s['pages']} | {s['titre']}")

    print(f"\n  10 chunks les PLUS LONGS (mots) :")
    for s in sections_triees[-10:][::-1]:
        print(f"    {s['nb_mots']:4} mots | p.{s['pages']} | {s['titre']}")

    print(f"\n[export] {len(sections)} chunks écrits dans {out_path}")


if __name__ == "__main__":
    main()
