# -*- coding: utf-8 -*-
"""fix_unnumbered_levels.py — Corrige le niveau du seul section_header sans
numérotation reconnue qui en a réellement besoin ("Epargne retraite",
position 212) : resté au niveau H1 d'origine de Docling faute de
correspondance avec le regex de numérotation de fix_heading_levels.py.

LISTE BLANCHE EXPLICITE, PAS UNE RÈGLE GÉNÉRIQUE. Les 18 section_header
sans numérotation reconnue dans structure_finale_v3.json ont été inspectés
un par un avec l'utilisateur avant d'écrire ce script. Décision : SEUL
"Epargne retraite" (position 212) est corrigé ; les 17 autres sont
volontairement exclus (16 titres d'annexes QRT, page >= 77, hors périmètre
narratif — déjà exclus du pipeline en aval ; "SYNTHÈSE", un vrai titre de
section de premier niveau, simplement sans numérotation lettrée, comme
"A.", "B." mais sans lettre).

Ce script vérifie explicitement, POSITION ET TEXTE, que chaque
section_header non numéroté trouvé appartient soit au cas à corriger, soit
à la liste blanche d'exclusion. Si un cas non couvert apparaît (nouveau
document, nouvelle extraction, décalage de position) — donc si un 19e cas
non numéroté surgissait un jour — ce script S'ARRÊTE et le signale
explicitement, plutôt que d'appliquer une règle générique (ex. "page >= 77
=> exclu", "un seul precedent numérote => +1") qui devinerait comment le
traiter. C'est le comportement voulu, pas un oubli.

    python fix_unnumbered_levels.py [structure_finale_v3.json] [dossier_sortie]
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from fix_heading_levels import MOTIF_NUMEROTATION

BASE_DIR = Path(__file__).parent

# --- Liste blanche, décidée avec l'utilisateur après inspection complète
# des 18 cas (position ET texte attendu, vérifiés avant tout traitement,
# jamais la position seule). ---

POSITION_A_CORRIGER = 212
TEXTE_A_CORRIGER = "Epargne retraite"

POSITIONS_EXCLUES = {
    21: "SYNTHÈSE",  # vrai titre de section de premier niveau, sans numérotation lettrée
    # 16 titres d'annexes QRT (page >= 77), hors périmètre narratif :
    1255: "ANNEXES - QRT PUBLICS",
    1256: "Les états quantitatifs annexés sont exprimés en milliers d'euros.",
    1260: "5020102",
    1265: "Annexe 1 (1/2)",
    1268: "Annexe 1 (2/2)",
    1271: "Annexe 2 (1/2) Primes, sinistres et dépenses par ligne d'activité",
    1276: "Annexe 2 (2/2)",
    1280: "Annexe 3 (1/2)",
    1285: "Annexe 3 (2/2)",
    1290: "Annexe 4",
    1298: "Annexe 5 (1/2)",
    1300: "Annexe 5 (2/2)",
    1301: "523.01.22 02 Fonds propres",
    1305: "Annexe 6",
    1311: "Annexe 7 (1/2)",
    1316: "Annexe 7 (2/2)",
}


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("structure_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "structure_finale_v3.json"))
    p.add_argument("output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"))
    return p.parse_args()


def main():
    args = parse_cli()
    with open(args.structure_json, encoding="utf-8") as f:
        items = json.load(f)

    headers = sorted([it for it in items if it["type"] == "section_header"],
                      key=lambda h: h["position"])

    non_numerotes = [h for h in headers if not MOTIF_NUMEROTATION.match(h["extrait"] or "")]

    print("=" * 70)
    print(f"{len(non_numerotes)} section_header sans numérotation reconnue trouvés "
          f"(sur {len(headers)} au total)")
    print("=" * 70)

    # Vérifie que CHAQUE non-numéroté trouvé est soit le cas à corriger,
    # soit dans la liste blanche d'exclusion (position ET texte) — sinon,
    # arrêt immédiat, aucune correction appliquée, rien exporté.
    inattendus = []
    for h in non_numerotes:
        pos = h["position"]
        texte = (h["extrait"] or "").strip()
        if pos == POSITION_A_CORRIGER:
            if texte != TEXTE_A_CORRIGER:
                inattendus.append((h, f"attendu {TEXTE_A_CORRIGER!r} (cas à corriger), "
                                       f"trouvé {texte!r}"))
        elif pos in POSITIONS_EXCLUES:
            if texte != POSITIONS_EXCLUES[pos]:
                inattendus.append((h, f"attendu {POSITIONS_EXCLUES[pos]!r} (liste blanche "
                                       f"d'exclusion), trouvé {texte!r}"))
        else:
            inattendus.append((h, "position absente de la liste blanche ET du cas à corriger "
                                   "— NON ANTICIPÉ"))

    if inattendus:
        print("\n>>> ARRÊT — cas non couverts par la liste blanche / le cas à corriger :")
        for h, raison in inattendus:
            print(f"  pos {h['position']} p.{h['pages']} niveau=H{h['niveau']} : "
                  f"{h['extrait']!r} — {raison}")
        print("\nAucune correction appliquée, structure_finale_v4.json NON écrit. "
              "Ces cas doivent être validés explicitement avant de continuer.")
        return

    print("\nOK — tous les cas trouvés correspondent soit au cas à corriger, "
          "soit à la liste blanche d'exclusion. Aucune surprise.")
    for h in non_numerotes:
        if h["position"] != POSITION_A_CORRIGER:
            print(f"  [EXCLU, inchangé] pos {h['position']} p.{h['pages']} "
                  f"niveau=H{h['niveau']} : {h['extrait']!r}")

    # Calcule le niveau de référence : niveau du plus proche section_header
    # NUMÉROTÉ (pas juste le précédent, quel qu'il soit) qui précède la
    # position à corriger dans l'ordre de lecture.
    dernier_niveau_numerote = None
    dernier_titre_numerote = None
    header_a_corriger = None
    for h in headers:
        if h["position"] == POSITION_A_CORRIGER:
            header_a_corriger = h
            break
        if MOTIF_NUMEROTATION.match(h["extrait"] or ""):
            dernier_niveau_numerote = h["niveau"]
            dernier_titre_numerote = h["extrait"]

    if header_a_corriger is None or dernier_niveau_numerote is None:
        print(f"\n>>> ARRÊT — impossible de déterminer un section_header numéroté "
              f"précédent pour la position {POSITION_A_CORRIGER}. Aucune correction appliquée.")
        return

    ancien_niveau = header_a_corriger["niveau"]
    nouveau_niveau = dernier_niveau_numerote + 1
    header_a_corriger["niveau"] = nouveau_niveau  # mutation en place, propage à `items`

    print("\n" + "=" * 70)
    print("CORRECTION APPLIQUÉE")
    print("=" * 70)
    print(f"  position {POSITION_A_CORRIGER} p.{header_a_corriger['pages']} : "
          f"{header_a_corriger['extrait']!r}")
    print(f"  niveau H{ancien_niveau} -> H{nouveau_niveau}  "
          f"(= niveau du plus proche section_header NUMÉROTÉ précédent + 1 : "
          f"H{dernier_niveau_numerote} sur {dernier_titre_numerote!r})")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "structure_finale_v4.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"\n[export] {len(items)} items écrits dans {out_path}")


if __name__ == "__main__":
    main()
