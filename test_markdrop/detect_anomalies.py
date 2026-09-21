# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier relit automatiquement tous les morceaux de texte pour
# repérer les cas suspects, avant qu'une personne ne les vérifie à la
# main.
# ------------------------------------------------------------------
"""detect_anomalies.py — Étape 5 (détection automatique) : repère les cas
suspects dans chunks_avec_metadata.json AVANT la vérification manuelle de
l'étape 6, pour savoir où regarder en priorité plutôt que de tout
re-vérifier à l'aveugle.

Toutes les vérifications portent UNIQUEMENT sur les chunks INDEXABLES
(categorie == "indexable") — les chunks structurels sont hors périmètre de
cette passe (ils n'ont pas vocation à être vectorisés tels quels).

⚠️ VÉRIFIÉ AVANT D'ÉCRIRE CE SCRIPT (pas supposé) : la consigne mentionne
"7 sections de premier niveau connues (SYNTHÈSE, A., B., C., D., E.)" — ça
n'en liste que 6. Inspection directe de chunks_avec_metadata.json : il n'y
a RÉELLEMENT que 6 racines distinctes dans tout le fichier (SYNTHÈSE, A.
ACTIVITÉ ET RÉSULTATS, B. SYSTEME DE GOUVERNANCE, C. PROFIL DE RISQUE, D.
VALORISATION A DES FINS DE SOLVABILITE, E. GESTION DE CAPITAL) — aucune
section F. Le motif de reconnaissance ci-dessous (MOTIF_RACINE_CONNUE)
teste donc une FORME générique ("SYNTHÈSE" ou une lettre majuscule suivie
d'un point), jamais une liste figée de libellés exacts — plus robuste, et
ça évite de coder en dur un chiffre ("7") qui ne correspond pas aux
données réelles.

Script en LECTURE SEULE : ne modifie ni n'exporte aucun fichier de chunks,
uniquement anomalies_detectees.json + affichage console.

    python detect_anomalies.py [chunks_avec_metadata.json] [dossier_sortie]
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

SEUIL_MOTS_COURT = 30     # chunks indexables sous ce seuil : candidats "trop courts"
SEUIL_MOTS_LONG = 700     # chunks indexables au-dessus : auraient dû être découpés à l'étape 3
SEUIL_SAUT_PAGES = 3      # écart entre 2 pages triées consécutives au-delà duquel le saut est jugé anormal
                          # (un saut de 1-2 pages reste "proche" : peut venir d'une page de
                          # tableau/image exclue du texte narratif, donc légitime)
ANNEE_ATTENDUE_DEFAUT = 2025
# Réassigné depuis --annee dans main() avant tout appel aux fonctions
# ci-dessous (qui lisent cette globale au moment de l'appel, pas à la
# définition) — permet de réutiliser ce script tel quel sur un autre
# document (ex. SFCR 2024) sans dupliquer le fichier.
ANNEE_ATTENDUE = ANNEE_ATTENDUE_DEFAUT

PONCTUATION_FINALE_VALIDE = (".", ":", "»")

# Marqueurs de contenu non textuel insérés par build_sections.py
# (TYPES_NON_TEXTUELS) — jamais du texte réel, donc ne doivent pas compter
# quand on juge si LE TEXTE lui-même se termine correctement.
MOTIF_MARQUEUR_NON_TEXTUEL = re.compile(r"^\[(?:TABLEAU|IMAGE|LEGENDE|INDEX): [^\]]*\]\s*$")

# Zone d'usage privé Unicode (Private Use Area) — mêmes bornes que
# filter_fake_headers.py / retype_bullet_headers.py.
PUA_DEBUT, PUA_FIN = 0xE000, 0xF8FF

# Racine connue = "SYNTHÈSE" littéral, OU une lettre majuscule suivie d'un
# point (A., B., C., ... quel que soit le libellé complet qui suit) — cf.
# note ci-dessus sur le chiffre "7" non vérifié.
MOTIF_RACINE_CONNUE = re.compile(r"^[A-Z]\.")


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("chunks_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "chunks_avec_metadata.json"))
    p.add_argument("output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"))
    p.add_argument("--annee", type=int, default=ANNEE_ATTENDUE_DEFAUT,
                   help="Année attendue pour annee_document (défaut 2025)")
    return p.parse_args()


def identifiant(c):
    """Identifiant stable d'un chunk final. position_header + position_origine
    NE SUFFIT PAS : vérifié sur les données réelles, les sous-chunks
    "paragraphe/type2" issus d'un même parent partagent TOUS le même
    position_origine (= position_header du parent, cf.
    decouper_paragraphe dans split_and_merge_chunks.py) — 2 ou 3
    sous-chunks DIFFÉRENTS se retrouveraient sinon avec un id identique.
    L'index de chargement ("_idx", posé une fois dans main()) lève
    l'ambiguïté de façon stable pour la durée d'une exécution."""
    return f"{c['position_header']}_{c.get('position_origine', c['position_header'])}_{c['_idx']}"


def extrait(c, longueur=150):
    texte = c.get("texte") or ""
    return texte[:longueur] + ("…" if len(texte) > longueur else "")


def fiche(c, **extra):
    """Représentation commune d'un chunk dans le rapport d'anomalies —
    mêmes champs de base partout, + des champs spécifiques à la catégorie
    (extra)."""
    base = {
        "id": identifiant(c),
        "titre": c["titre"],
        "chemin_hierarchique": c["chemin_hierarchique"],
        "pages": c.get("pages"),
        "nb_mots": c.get("nb_mots"),
        "extrait_texte": extrait(c),
    }
    base.update(extra)
    return base


def detecter_chemins_anormaux(indexables):
    """Catégorie 1 : chemins dupliqués, racine inconnue/vide, segment
    tronqué (vide entre deux ">", ou ">" en tête/fin).

    "Dupliqué" exclut volontairement les sous-chunks "paragraphe/type2"
    d'un même chunk parent : split_and_merge_chunks.py leur fait
    DÉLIBÉRÉMENT partager le même chemin (et le même titre), faute de
    sous-titre naturel — demandé explicitement à l'étape du découpage, pas
    un bug. Seule une collision entre chunks de PARENTS DIFFÉRENTS
    (position_header distincts) est une vraie anomalie ("ne devrait jamais
    arriver")."""
    par_chemin = defaultdict(list)
    for c in indexables:
        par_chemin[c["chemin_hierarchique"] or ""].append(c)

    duplique, racine_inconnue, segment_tronque = [], [], []

    for chemin, groupe in par_chemin.items():
        position_headers_distincts = {c["position_header"] for c in groupe}
        if len(groupe) > 1 and len(position_headers_distincts) > 1:
            for c in groupe:
                duplique.append(fiche(
                    c, nb_chunks_meme_chemin=len(groupe),
                    position_headers_concernes=sorted(position_headers_distincts),
                ))

    for c in indexables:
        chemin = c["chemin_hierarchique"] or ""

        if not chemin or not (chemin.startswith("SYNTHÈSE") or MOTIF_RACINE_CONNUE.match(chemin)):
            racine_inconnue.append(fiche(c))

        segments = chemin.split(" > ")
        segment_vide = any(seg.strip() == "" for seg in segments)
        bordure_tronquee = bool(chemin) and (chemin.startswith(">") or chemin.endswith(">"))
        if segment_vide or bordure_tronquee:
            segment_tronque.append(fiche(c, segments=segments))

    return duplique, racine_inconnue, segment_tronque


def detecter_longueur_suspecte(indexables):
    """Catégorie 2 : chunks trop courts (< SEUIL_MOTS_COURT) ou trop longs
    (> SEUIL_MOTS_LONG, signe qu'un chunk aurait dû être découpé à
    l'étape 3 mais y a échappé)."""
    trop_court = [fiche(c) for c in indexables if c["nb_mots"] < SEUIL_MOTS_COURT]
    trop_long = [fiche(c) for c in indexables if c["nb_mots"] > SEUIL_MOTS_LONG]
    return trop_court, trop_long


def detecter_metadonnees_incoherentes(indexables):
    """Catégorie 3 : pages absentes/vides, saut de pages anormal, année du
    document différente de celle attendue."""
    pages_absentes, pages_saut_anormal, annee_incoherente = [], [], []

    for c in indexables:
        pages = c.get("pages")
        if not pages:
            pages_absentes.append(fiche(c))
        else:
            pages_triees = sorted(pages)
            sauts = [b - a for a, b in zip(pages_triees, pages_triees[1:])]
            saut_max = max(sauts) if sauts else 0
            if saut_max > SEUIL_SAUT_PAGES:
                pages_saut_anormal.append(fiche(c, saut_max=saut_max))

        if c.get("annee_document") != ANNEE_ATTENDUE:
            annee_incoherente.append(fiche(c, annee_document=c.get("annee_document")))

    return pages_absentes, pages_saut_anormal, annee_incoherente


def verifier_cas_connus(indexables):
    """Catégorie 4 : re-vérifie explicitement, dans le fichier FINAL (pas
    à une étape intermédiaire), 3 cas déjà corrigés lors d'étapes
    antérieures — confirme qu'ils sont bien résolus ici, et pas
    simplement vérifiés ailleurs puis perdus en route. Retourne
    (resultats_par_cas, chunks_en_echec) — le 2e élément reste vide si les
    3 cas passent, et alimente la catégorie "cas_connu_en_echec" sinon."""
    resultats = {}
    en_echec = []

    # Cas 1 : tout chunk descendant de "A.3 Résultats des investissements"
    # doit remonter jusqu'à "A. ACTIVITÉ ET RÉSULTATS".
    descendants_a3 = [c for c in indexables if "A.3 Résultats des investissements" in c["chemin_hierarchique"]]
    echecs_a3 = [c for c in descendants_a3 if not c["chemin_hierarchique"].startswith("A. ACTIVITÉ ET RÉSULTATS")]
    resultats["A.3_vers_A._ACTIVITE_ET_RESULTATS"] = {
        "chunks_concernes": len(descendants_a3), "echecs": len(echecs_a3),
    }
    en_echec.extend(fiche(c, cas="A.3 ne remonte pas à A. ACTIVITÉ ET RÉSULTATS") for c in echecs_a3)

    # Cas 2 : tout chunk descendant de "B.3.2.3" doit remonter jusqu'à
    # "B. SYSTEME DE GOUVERNANCE".
    descendants_b323 = [c for c in indexables if "B.3.2.3" in c["chemin_hierarchique"]]
    echecs_b323 = [c for c in descendants_b323 if not c["chemin_hierarchique"].startswith("B. SYSTEME DE GOUVERNANCE")]
    resultats["B.3.2.3_vers_B._SYSTEME_DE_GOUVERNANCE"] = {
        "chunks_concernes": len(descendants_b323), "echecs": len(echecs_b323),
    }
    en_echec.extend(fiche(c, cas="B.3.2.3 ne remonte pas à B. SYSTEME DE GOUVERNANCE") for c in echecs_b323)

    # Cas 3 : "Epargne retraite" doit être rattaché sous "A.2.1.", jamais racine.
    chunks_epargne = [c for c in indexables if "Epargne retraite" in c["chemin_hierarchique"]]
    echecs_epargne = [c for c in chunks_epargne if "A.2.1" not in c["chemin_hierarchique"]]
    resultats["Epargne_retraite_rattachee_sous_A.2.1"] = {
        "chunks_concernes": len(chunks_epargne), "echecs": len(echecs_epargne),
    }
    en_echec.extend(fiche(c, cas="Epargne retraite pas rattaché sous A.2.1") for c in echecs_epargne)

    return resultats, en_echec


def retirer_marqueurs_finaux(texte):
    """Retire, en repartant de la fin, toutes les lignes qui sont des
    marqueurs de contenu non textuel ([TABLEAU: ...], [IMAGE: ...], etc.)
    — un chunk peut légitimement se terminer par une phrase complète
    SUIVIE d'un tableau/image, ce n'est pas une coupure. Ne touche qu'à la
    fin : un marqueur ailleurs dans le texte (entre 2 paragraphes, légitime)
    reste en place et n'affecte pas ce retrait."""
    lignes = texte.split("\n")
    while lignes and MOTIF_MARQUEUR_NON_TEXTUEL.match(lignes[-1].strip()):
        lignes.pop()
    return "\n".join(lignes).rstrip()


def detecter_texte_suspect(indexables):
    """Catégorie 5 : texte qui semble commencer/finir au milieu d'une
    phrase (hors sous-chunks bullet-titre, où c'est plus normal, et hors
    marqueurs non textuels en fin de texte, cf. retirer_marqueurs_finaux),
    et caractères PUA résiduels (titre ou texte) qui auraient échappé au
    nettoyage de retype_bullet_headers.py / filter_fake_headers.py."""
    coupure_suspecte, pua_residuel = [], []

    for c in indexables:
        texte = (c.get("texte") or "").strip()

        if c.get("origine_decoupage") != "bullet_titre" and texte:
            premier = texte[0]
            debut_suspect = premier.isalpha() and premier.islower()

            # La ponctuation finale se juge sur le texte UTILE (marqueurs
            # non textuels de fin retirés), jamais sur le dernier caractère
            # brut — sinon un "[IMAGE: ...]" final fait à tort passer une
            # phrase complète pour une coupure.
            texte_utile = retirer_marqueurs_finaux(texte)
            dernier = texte_utile[-1] if texte_utile else premier
            fin_suspecte = dernier not in PONCTUATION_FINALE_VALIDE
            if debut_suspect or fin_suspecte:
                coupure_suspecte.append(fiche(
                    c, debut_suspect=debut_suspect, fin_suspecte=fin_suspecte,
                    premier_caractere=premier, dernier_caractere=dernier,
                ))

        # Scanne aussi chemin_hierarchique (pas seulement titre/texte) :
        # attach_metadata.py le construit à partir de "titre", donc un PUA
        # laissé dans l'un peut être laissé dans l'autre par la même
        # régression (cf. fix_chemin_hierarchique.py).
        champs_scannes = ((c.get("titre") or "") + (c.get("texte") or "")
                           + (c.get("chemin_hierarchique") or ""))
        pua_trouves = sorted({car for car in champs_scannes
                               if PUA_DEBUT <= ord(car) <= PUA_FIN})
        if pua_trouves:
            pua_residuel.append(fiche(c, caracteres_pua=[hex(ord(car)) for car in pua_trouves]))

    return coupure_suspecte, pua_residuel


def main():
    global ANNEE_ATTENDUE
    args = parse_cli()
    ANNEE_ATTENDUE = args.annee
    with open(args.chunks_json, encoding="utf-8") as f:
        chunks = json.load(f)

    # Index de chargement, posé une fois ici — seule source fiable
    # d'unicité pour identifiant() (cf. sa docstring). N'est jamais
    # exporté tel quel dans le rapport (fiche() ne reprend que les champs
    # listés explicitement), et ne modifie aucun fichier sur disque.
    for idx, c in enumerate(chunks):
        c["_idx"] = idx

    indexables = [c for c in chunks if c["categorie"] == "indexable"]
    print(f"Chunks chargés : {len(chunks)} | indexables analysés : {len(indexables)} "
          f"| structurels exclus de cette passe : {len(chunks) - len(indexables)}")

    duplique, racine_inconnue, segment_tronque = detecter_chemins_anormaux(indexables)
    trop_court, trop_long = detecter_longueur_suspecte(indexables)
    pages_absentes, pages_saut_anormal, annee_incoherente = detecter_metadonnees_incoherentes(indexables)
    resultats_cas_connus, cas_connu_en_echec = verifier_cas_connus(indexables)
    coupure_suspecte, pua_residuel = detecter_texte_suspect(indexables)

    categories = {
        "chemin_duplique": duplique,
        "chemin_racine_inconnue": racine_inconnue,
        "chemin_segment_tronque": segment_tronque,
        "trop_court": trop_court,
        "trop_long": trop_long,
        "pages_absentes": pages_absentes,
        "pages_saut_anormal": pages_saut_anormal,
        "annee_incoherente": annee_incoherente,
        "cas_connu_en_echec": cas_connu_en_echec,
        "texte_coupure_suspecte": coupure_suspecte,
        "pua_residuel": pua_residuel,
    }

    # --- Affichage, groupé par catégorie, jamais mélangé ---
    LIBELLES = {
        "chemin_duplique": "CHEMINS HIÉRARCHIQUES DUPLIQUÉS",
        "chemin_racine_inconnue": "CHEMIN VIDE OU RACINE DE PREMIER NIVEAU INCONNUE",
        "chemin_segment_tronque": "CHEMIN AVEC SEGMENT TRONQUÉ/VIDE",
        "trop_court": f"CHUNKS TROP COURTS (< {SEUIL_MOTS_COURT} mots)",
        "trop_long": f"CHUNKS TROP LONGS (> {SEUIL_MOTS_LONG} mots)",
        "pages_absentes": "PAGES ABSENTES/VIDES",
        "pages_saut_anormal": f"SAUT DE PAGES ANORMAL (> {SEUIL_SAUT_PAGES})",
        "annee_incoherente": f"ANNEE_DOCUMENT != {ANNEE_ATTENDUE}",
        "cas_connu_en_echec": "CAS CONNUS — ÉCHEC DE RE-VÉRIFICATION",
        "texte_coupure_suspecte": "TEXTE SUSPECT (coupure probable mi-phrase)",
        "pua_residuel": "CARACTÈRES PUA RÉSIDUELS",
    }

    for cle, libelle in LIBELLES.items():
        items = categories[cle]
        print("\n" + "=" * 70)
        print(f"{libelle} — {len(items)} cas")
        print("=" * 70)
        if not items:
            print("  (aucun)")
            continue
        for it in items:
            print(f"\n  id={it['id']}  pages={it['pages']}  nb_mots={it['nb_mots']}")
            print(f"    titre  : {it['titre']!r}")
            print(f"    chemin : {it['chemin_hierarchique']!r}")
            print(f"    extrait: {it['extrait_texte']!r}")
            extras = {k: v for k, v in it.items()
                      if k not in {"id", "titre", "chemin_hierarchique", "pages", "nb_mots", "extrait_texte"}}
            if extras:
                print(f"    détail : {extras}")

    # --- Cas connus : confirmation explicite, même quand ils passent ---
    print("\n" + "=" * 70)
    print("CAS CONNUS — RÉ-VÉRIFICATION DANS LE FICHIER FINAL")
    print("=" * 70)
    for cas, r in resultats_cas_connus.items():
        statut = "OK" if r["echecs"] == 0 else f"ÉCHEC ({r['echecs']})"
        print(f"  {cas} : {r['chunks_concernes']} chunk(s) concerné(s) — {statut}")

    # --- Résumé chiffré + liste priorisée (chunks touchés par >= 2 catégories) ---
    anomalies_par_id = defaultdict(set)
    fiches_par_id = {}
    for cle, items in categories.items():
        for it in items:
            anomalies_par_id[it["id"]].add(cle)
            fiches_par_id[it["id"]] = it

    priorite = sorted(
        (cid for cid, cats in anomalies_par_id.items() if len(cats) >= 2),
        key=lambda cid: -len(anomalies_par_id[cid]),
    )

    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    for cle, libelle in LIBELLES.items():
        print(f"  {libelle:55} : {len(categories[cle])}")
    print(f"\n  Chunks distincts touchés par au moins 1 anomalie : {len(anomalies_par_id)}")
    print(f"  Chunks touchés par 2 catégories ou plus (PRIORITÉ étape 6) : {len(priorite)}")

    if priorite:
        print("\n  LISTE PRIORISÉE (à vérifier en premier) :")
        for cid in priorite:
            it = fiches_par_id[cid]
            cats = sorted(anomalies_par_id[cid])
            print(f"    id={cid}  catégories={cats}")
            print(f"      titre  : {it['titre']!r}")
            print(f"      chemin : {it['chemin_hierarchique']!r}")

    # --- Export du rapport (lecture seule sur les chunks, écrit uniquement le rapport) ---
    rapport = {
        "categories": categories,
        "cas_connus": resultats_cas_connus,
        "priorite_combinee": [
            {"id": cid, "categories": sorted(anomalies_par_id[cid]), **fiches_par_id[cid]}
            for cid in priorite
        ],
    }
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "anomalies_detectees.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)
    print(f"\n[export] rapport écrit dans {out_path}")


if __name__ == "__main__":
    main()
