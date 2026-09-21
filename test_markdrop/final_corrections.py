# -*- coding: utf-8 -*-
"""final_corrections.py — Applique les 9 corrections manuelles décidées sur
les SECTION_HEADER "en trop" (suppression / retypage caption / retypage
list_item / aucun changement), PAR POSITION EXACTE — jamais par texte, pour
éviter toute ambiguïté — plus la correction de "B.2.1. Compétence"
(position 392), sous-catégorisé "text" par Docling au lieu de
"section_header".

Vérification faite avant d'écrire ce script (pas supposée) : la position
392 existe DÉJÀ dans structure_finale.json, toujours typée "text" — elle
n'a jamais été perdue par le pipeline (aucun script précédent ne touche
aux items non-section_header). Ce script la MUTE EN PLACE ; il ne la
réinsère pas depuis structure_brute.json, ce qui créerait un doublon.
structure_brute.json ne sert ici qu'à vérifier, par sécurité, que le texte
d'origine à cette position correspond bien à ce qui a été décidé.

Chaque correction est vérifiée AVANT application : le texte actuellement
présent à la position indiquée doit correspondre exactement à ce qui a
été inspecté manuellement. En cas d'écart, la correction est REFUSÉE et
signalée dans le log — jamais appliquée à l'aveugle sur un simple numéro
de position qui aurait pu se décaler entre deux runs.

Ne touche à AUCUNE autre position que celles listées ci-dessous — en
particulier, ne touche PAS aux 13 titres d'annexes QRT (page > 76,
identifiés par compare_to_sommaire.py) : hors scope de cette passe.

    python final_corrections.py [structure_finale.json] [structure_brute.json] [dossier_sortie]
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

# Même motif de numérotation que fix_heading_levels.py, réappliqué UNIQUEMENT
# pour calculer le niveau de "B.2.1. Compétence" de la même façon que tous
# les autres titres du document — pas un nombre choisi à la main.
MOTIF_NUMEROTATION = re.compile(r"^([A-Z])((?:\.\d+)*)\.\s")


def deduire_niveau(extrait):
    m = MOTIF_NUMEROTATION.match(extrait or "")
    if not m:
        return None
    return 1 + m.group(2).count(".")


# --- Les 9 décisions, par position EXACTE, avec le texte attendu pour
# vérification défensive (protège contre un décalage de position). ---
SUPPRESSIONS = {
    1: "RAPPORT SUR LA SOLVABILITE ET LA SITUATION FINANCIERE AU 31 DECEMBRE 2025",
    2: "GROUPE GROUPAMA",
    6: "SOMMAIRE",
}
RETYPAGES_CAPTION = {
    98: "ORGANIGRAMME JURIDIQUE SIMPLIFIE",
    107: "Chiffre d'affaires des principaux métiers au 31 décembre 2025",
}
RETYPAGES_LIST_ITEM = {
    125: "Solidité Financière",
    130: "Activité",
    506: "La Direction Risques Groupe :",
}
POSITION_INCHANGEE = {212: "Epargne retraite"}

POSITION_B21 = 392
TEXTE_B21_ATTENDU = "B.2.1. Compétence"
TYPE_ACTUEL_B21_ATTENDU = "text"  # tel que sous-catégorisé par Docling

PAGE_MAX_QRT = 76  # rappel de scope : rien au-delà n'est touché ici (vérifié, pas juste évité)


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("structure_finale", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "structure_finale.json"))
    p.add_argument("structure_brute", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "structure_brute.json"))
    p.add_argument("output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"))
    return p.parse_args()


def texte_correspond(item, texte_attendu):
    return (item.get("extrait") or "").strip() == texte_attendu.strip()


def main():
    args = parse_cli()
    with open(args.structure_finale, encoding="utf-8") as f:
        items = json.load(f)
    with open(args.structure_brute, encoding="utf-8") as f:
        items_brute = json.load(f)

    par_position = {it["position"]: it for it in items}
    par_position_brute = {it["position"]: it for it in items_brute}

    n_section_header_avant = sum(1 for it in items if it["type"] == "section_header")

    journal = []
    positions_a_supprimer = set()

    # --- Garde-fou de scope : aucune des 9 positions ni B.2.1 ne doit être
    # une annexe QRT (page > 76) — vérifié, pas supposé, avant d'agir. ---
    toutes_positions_decision = (set(SUPPRESSIONS) | set(RETYPAGES_CAPTION)
                                  | set(RETYPAGES_LIST_ITEM) | set(POSITION_INCHANGEE))
    for pos in toutes_positions_decision:
        it = par_position.get(pos)
        if it and any(p > PAGE_MAX_QRT for p in it.get("pages", [])):
            journal.append(f"[ALERTE SCOPE] position {pos} est sur une page > {PAGE_MAX_QRT} "
                            "(zone annexes QRT) — vérifier manuellement, cette passe ne devrait "
                            "pas y toucher.")

    # --- 1. Suppressions (positions 1, 2, 6) ---
    for pos, texte_attendu in SUPPRESSIONS.items():
        item = par_position.get(pos)
        if item is None or item["type"] != "section_header" or not texte_correspond(item, texte_attendu):
            trouve = None if item is None else f"{item['type']!r} {item.get('extrait')!r}"
            journal.append(f"[REFUSÉ] suppression position {pos} : attendu section_header "
                            f"{texte_attendu!r}, trouvé {trouve} — aucune suppression appliquée.")
            continue
        positions_a_supprimer.add(pos)
        journal.append(f"[SUPPRIMÉ] position {pos} p.{item['pages']} : {item['extrait']!r} "
                        "(section_header -> supprimé)")

    # --- 2. Retypages en caption (positions 98, 107) ---
    for pos, texte_attendu in RETYPAGES_CAPTION.items():
        item = par_position.get(pos)
        if item is None or item["type"] != "section_header" or not texte_correspond(item, texte_attendu):
            trouve = None if item is None else f"{item['type']!r} {item.get('extrait')!r}"
            journal.append(f"[REFUSÉ] retypage caption position {pos} : attendu section_header "
                            f"{texte_attendu!r}, trouvé {trouve} — aucun retypage appliqué.")
            continue
        ancien_type = item["type"]
        item["type"] = "caption"
        item["niveau"] = None
        journal.append(f"[RETYPÉ] position {pos} p.{item['pages']} : {ancien_type} -> caption "
                        f"— {item['extrait']!r}")

    # --- 3. Retypages en list_item (positions 125, 130, 506) ---
    for pos, texte_attendu in RETYPAGES_LIST_ITEM.items():
        item = par_position.get(pos)
        if item is None or item["type"] != "section_header" or not texte_correspond(item, texte_attendu):
            trouve = None if item is None else f"{item['type']!r} {item.get('extrait')!r}"
            journal.append(f"[REFUSÉ] retypage list_item position {pos} : attendu section_header "
                            f"{texte_attendu!r}, trouvé {trouve} — aucun retypage appliqué.")
            continue
        ancien_type = item["type"]
        item["type"] = "list_item"
        item["niveau"] = None
        journal.append(f"[RETYPÉ] position {pos} p.{item['pages']} : {ancien_type} -> list_item "
                        f"— {item['extrait']!r}")

    # --- 4. Position laissée intacte (212) : log seulement ---
    for pos, texte_attendu in POSITION_INCHANGEE.items():
        item = par_position.get(pos)
        if item is None or not texte_correspond(item, texte_attendu):
            trouve = None if item is None else item.get("extrait")
            journal.append(f"[ATTENTION] position {pos} : texte inattendu pour un item à laisser "
                            f"inchangé (attendu {texte_attendu!r}, trouvé {trouve!r})")
        else:
            journal.append(f"[INCHANGÉ] position {pos} p.{item['pages']} : {item['extrait']!r} "
                            "(décision : vrai titre narratif, conservé tel quel)")

    # --- 5. Correction de B.2.1. Compétence : mutation EN PLACE de l'item
    #     déjà présent dans structure_finale.json (jamais réinséré depuis
    #     structure_brute.json — il n'a jamais été perdu). structure_brute
    #     ne sert que de vérification croisée indépendante. ---
    item_b21 = par_position.get(POSITION_B21)
    item_b21_brut = par_position_brute.get(POSITION_B21)

    verif_brute_ok = item_b21_brut is not None and texte_correspond(item_b21_brut, TEXTE_B21_ATTENDU)
    verif_finale_ok = (item_b21 is not None and item_b21["type"] == TYPE_ACTUEL_B21_ATTENDU
                        and texte_correspond(item_b21, TEXTE_B21_ATTENDU))

    if not verif_brute_ok:
        trouve = None if item_b21_brut is None else item_b21_brut.get("extrait")
        journal.append(f"[REFUSÉ] réintégration B.2.1 : structure_brute.json position "
                        f"{POSITION_B21} ne correspond pas à l'attendu ({TEXTE_B21_ATTENDU!r}), "
                        f"trouvé {trouve!r}.")
    if not verif_finale_ok:
        trouve = None if item_b21 is None else f"{item_b21['type']!r} {item_b21.get('extrait')!r}"
        journal.append(f"[REFUSÉ] correction B.2.1 : structure_finale.json position "
                        f"{POSITION_B21} ne correspond pas à l'attendu (text {TEXTE_B21_ATTENDU!r}), "
                        f"trouvé {trouve} — aucune correction appliquée.")

    b21_corrige = verif_brute_ok and verif_finale_ok
    if b21_corrige:
        niveau_b1 = deduire_niveau("B.1. Informations générales sur le système de gouvernance")
        niveau_b3 = deduire_niveau("B.3. Système de gestion des risques")
        niveau_b21 = deduire_niveau(TEXTE_B21_ATTENDU)
        journal.append(f"[INFO] niveau calculé avec la même formule que fix_heading_levels.py : "
                        f"B.1.=H{niveau_b1}, B.3.=H{niveau_b3}, B.2.1.=H{niveau_b21} — un cran plus "
                        "profond que B.1./B.3., cohérent avec le fait que B.2.1. est un enfant de "
                        "B.2. (lui-même à H2), pas un frère direct de B.1./B.3.")
        ancien_type = item_b21["type"]
        item_b21["type"] = "section_header"
        item_b21["niveau"] = niveau_b21
        journal.append(f"[CORRIGÉ] position {POSITION_B21} p.{item_b21['pages']} : "
                        f"{ancien_type} -> section_header (H{niveau_b21}) — {TEXTE_B21_ATTENDU!r}")

    # --- Assemblage final : suppressions appliquées, le reste (retypages
    #     et correction B.2.1) a déjà été muté en place dans `items`. ---
    resultat = [it for it in items if it["position"] not in positions_a_supprimer]

    n_section_header_apres = sum(1 for it in resultat if it["type"] == "section_header")

    print("=" * 70)
    print("JOURNAL DES CORRECTIONS")
    print("=" * 70)
    for ligne in journal:
        print(" ", ligne)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "structure_finale_v3.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)

    n_attendu = (n_section_header_avant - len(SUPPRESSIONS) - len(RETYPAGES_CAPTION)
                 - len(RETYPAGES_LIST_ITEM) + (1 if b21_corrige else 0))

    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  SECTION_HEADER avant cette passe : {n_section_header_avant}")
    print(f"  SECTION_HEADER après cette passe  : {n_section_header_apres}")
    print(f"  Attendu (200 - 3 - 2 - 3 + 1)      : {n_attendu}")
    if n_section_header_apres != n_attendu:
        ecart = n_section_header_apres - n_attendu
        print(f"  >>> ÉCART DÉTECTÉ : {ecart:+d} par rapport à l'attendu — "
              "voir le journal ci-dessus pour les corrections REFUSÉES.")
    else:
        print("  Conforme au calcul attendu.")

    print(f"\n[export] {len(resultat)} items écrits dans {out_path}")


if __name__ == "__main__":
    main()
