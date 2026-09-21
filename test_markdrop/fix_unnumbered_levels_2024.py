# -*- coding: utf-8 -*-
"""fix_unnumbered_levels_2024.py — Équivalent, pour SFCR_2024, de
fix_unnumbered_levels.py (verrouillé sur les 18 cas 2025 inspectés avec
l'utilisateur, cf. son propre docstring — non réutilisable tel quel pour
un autre document). Même philosophie : chaque section_header sans
numérotation reconnue est inspecté INDIVIDUELLEMENT (texte + contexte
immédiat, position ET texte suivant) avant toute décision — jamais une
règle générique ("page >= X => exclu") appliquée à l'aveugle.

31 cas trouvés dans structure_finale_v3.json (2024), classés en 4
catégories après inspection réelle (voir DECISIONS.md, Décision 031) :

CATÉGORIE A — titres de premier niveau réels, jamais numérotés dans ce
document, SANS AUCUN header numéroté avant eux dans le flux (RAPPORT...,
SOMMAIRE, SYNTHÈSE) : INCHANGÉS, même traitement que "SYNTHÈSE" sur 2025.

CATÉGORIE B — phrase d'introduction à une énumération, mal typée
section_header par Docling au lieu de "text" (vérifié : chacune est
IMMÉDIATEMENT suivie d'un list_item, jamais d'un texte narratif libre) :
RETYPÉE en "text". Motif NOUVEAU, absent du document 2025 (probablement
lié à la même différence de police/mise en page que le motif de puce
▪ vs PUA détecté dans retype_bullet_headers.py).

CATÉGORIE C — légendes de figure/tableau ou mini-titres de "faits
marquants", sans puce ni numérotation, mais avec un header numéroté RÉEL
juste avant eux dans le flux (A.1.2/A.1.4/A.1.5) : PROMUS au niveau de ce
header + 1 — MÊME LOGIQUE que la correction "Epargne retraite" de 2025
(fix_unnumbered_levels.py : nouveau_niveau = dernier_niveau_numerote + 1),
généralisée ici à 10 cas au lieu d'1 seul, chacun vérifié individuellement
(texte + header numéroté précédent réellement adjacent dans le contenu,
pas juste par position). BUG RÉEL CONFIRMÉ avant correction, pas une
supposition : laissés inchangés (niveau Docling H1), ces 10 titres
"ferment" à tort le contexte hiérarchique H1 ouvert par le vrai "A."
racine — vérifié sur chunks_avec_metadata.json : sans cette correction,
le chunk "A.2. Résultats de souscription" (contenu réel, sans lien avec
un fait marquant) héritait du chemin_hierarchique "Cyclone Chido à
Mayotte > A.2. Résultats de souscription", jusqu'au prochain header de
niveau <= 1 rencontré dans le flux.

CATÉGORIE D — titres d'annexes QRT (page >= 73 = PAGE_MIN_QRT pour ce
document) : INCHANGÉS, hors périmètre du pipeline narratif de toute
façon (même traitement que 2025, page >= 77 sur ce document-là).

    python fix_unnumbered_levels_2024.py [structure_finale_v3.json] [dossier_sortie]
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fix_heading_levels import MOTIF_NUMEROTATION

BASE_DIR = Path(__file__).parent
PAGE_MIN_QRT_2024 = 73

# Catégorie B — vérifiée un par un : texte exact ET position ET item
# suivant (list_item) inspectés avant d'écrire cette liste.
POSITIONS_A_RETYPER_TEXTE = {
    8: "Ce rapport a pour objectif :",
    519: "Dans ce cadre, Groupama Assurances Mutuelles :",
    527: "La Direction Risques Groupe :",
}

# Catégorie C — vérifiée un par un : texte exact ET header numéroté
# parent réellement adjacent dans le flux (vu par inspection directe de
# structure_finale_v4.json), pas seulement la position.
POSITIONS_A_PROMOUVOIR = {
    111: "ORGANIGRAMME JURIDIQUE SIMPLIFIE",
    119: "Chiffre d'affaires des principaux métiers au 31 décembre 2024",
    130: "Chiffre d'affaires des principaux pays à l'international au 31 décembre 2024",
    142: "Notation financière",
    144: "Couverture de réassurance climatique",
    146: "Remboursement de dette Tier 1",
    148: "Emission de titres subordonnés",
    151: "PREFON",
    153: "Evénements en Nouvelle-Calédonie",
    155: "Cyclone Chido à Mayotte",
}


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("structure_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute_2024" / "structure_finale_v3.json"))
    p.add_argument("output_dir", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute_2024"))
    return p.parse_args()


def main():
    args = parse_cli()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    with open(args.structure_json, encoding="utf-8") as f:
        items = json.load(f)

    sans_numerotation = [
        it for it in items
        if it["type"] == "section_header" and not MOTIF_NUMEROTATION.match(it["extrait"] or "")
    ]
    print(f"{len(sans_numerotation)} section_header sans numérotation reconnue trouvés")

    n_retypes = 0
    n_qrt = 0
    n_racines = 0
    n_promus = 0
    cas_non_anticipes = []

    # Dernier niveau numéroté rencontré en parcourant le flux dans l'ordre
    # (nécessaire pour catégorie C : +1 par rapport à ce niveau, calculé,
    # jamais codé en dur position par position).
    dernier_niveau_numerote = None

    for it in items:
        est_header = it["type"] == "section_header"
        numerote = est_header and MOTIF_NUMEROTATION.match(it["extrait"] or "")
        if numerote:
            dernier_niveau_numerote = it["niveau"]
            continue
        if not est_header:
            continue
        # ici : section_header SANS numérotation reconnue

        pos = it["position"]
        page = min(it["pages"]) if it["pages"] else None
        if pos in POSITIONS_A_RETYPER_TEXTE:
            if (it["extrait"] or "").strip() != POSITIONS_A_RETYPER_TEXTE[pos]:
                cas_non_anticipes.append((it, "texte attendu ne correspond plus (catégorie B)"))
                continue
            it["type"] = "text"
            it["niveau"] = None
            n_retypes += 1
        elif pos in POSITIONS_A_PROMOUVOIR:
            if (it["extrait"] or "").strip() != POSITIONS_A_PROMOUVOIR[pos]:
                cas_non_anticipes.append((it, "texte attendu ne correspond plus (catégorie C)"))
                continue
            if dernier_niveau_numerote is None:
                cas_non_anticipes.append((it, "aucun header numéroté précédent trouvé (catégorie C)"))
                continue
            it["niveau"] = dernier_niveau_numerote + 1
            n_promus += 1
        elif page is not None and page >= PAGE_MIN_QRT_2024:
            n_qrt += 1  # catégorie D, inchangé
        else:
            n_racines += 1  # catégorie A, inchangé (aucun ancêtre numéroté)

    print(f"  catégorie B (retypés en 'text')            : {n_retypes}")
    print(f"  catégorie C (promus niveau+1 sous leur ancêtre) : {n_promus}")
    print(f"  catégorie D (annexes QRT, inchangés)       : {n_qrt}")
    print(f"  catégorie A (titres racine, inchangés)     : {n_racines}")

    if cas_non_anticipes:
        print("\n>>> ARRÊT — cas de la catégorie B dont le texte a changé depuis l'inspection :")
        for it, raison in cas_non_anticipes:
            print(f"  pos {it['position']} p.{it['pages']} : {raison} — {it['extrait']!r}")
        print("\nAucune correction appliquée, structure_finale_v4.json NON écrit.")
        return

    out_path = output_dir / "structure_finale_v4.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"\n[export] {len(items)} items écrits dans {out_path}")


if __name__ == "__main__":
    main()
