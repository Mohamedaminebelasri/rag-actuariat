# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier lit un autre type de tableau réglementaire (QRT), plus
# complexe, en utilisant un modèle d'intelligence artificielle capable de
# lire des images.
# ------------------------------------------------------------------
"""Test isolé : extraction du tableau QRT S.05.01.02.01 (Primes, sinistres
et dépenses par ligne d'activité — Non-Vie, page source 80) via Gemini.
Le plus large template testé jusqu'ici : 17 colonnes numériques, table
tournée à 90° dans le PDF. Vrai test de la généralisation à un template
non hardcodé auparavant.
"""

import asyncio
import json
import re
from pathlib import Path

from markdrop.parse import AIProcessor, AIProvider, ProcessorConfig
from qrt_checks import detect_column_shifts, print_report

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output_sectionE_QRT"
IMAGE_PATH = OUTPUT_DIR / "page9_S05_rotated.png"
DICT_PATH = OUTPUT_DIR / "qrt_dictionary.json"
OUT_PATH = OUTPUT_DIR / "extraction_S05_01_02_01_gemini.json"

SHEET_KEY = "S.05.01.02.01"

# Valeurs relevées à l'oeil sur l'image rastérisée (pas de vérité terrain
# fournie cette fois — comparaison indépendante construite nous-mêmes,
# sur des cellules réparties sur toute la largeur du tableau : colonne 1,
# colonnes du milieu, et colonne Total tout à droite).
VALEURS_LUES_MANUELLEMENT = {
    "R0110": {"C0010": 3299930, "C0040": 2149974, "C0080": 790603, "C0120": 209621, "C0200": 14235011},
    "R0200": {"C0010": 3882839, "C0060": 38774, "C0110": 339975, "C0160": -222450, "C0200": 14446704},
    "R0400": {"C0010": 2976696, "C0070": 1688216, "C0130": -60, "C0200": 9394390},
    "R1300": {"C0200": 4073372},
}


def build_prompt(colonnes_ordonnees, col_labels):
    lignes_cols = "\n".join(f'- {c} ({col_labels.get(c, c)})' for c in colonnes_ordonnees)
    return (
        "Voici un tableau du template réglementaire EIOPA S.05.01.02.01 "
        "(Primes, sinistres et dépenses par ligne d'activité, non-vie). "
        f"Il a {len(colonnes_ordonnees)} colonnes numériques, dans cet ordre "
        f"de gauche à droite :\n{lignes_cols}\n\n"
        'Chaque ligne a un code officiel (R0110, R0200, etc.) visible dans '
        'la colonne de gauche, sous un intitulé de catégorie en gras '
        '(ex. "Primes émises", "Charge des sinistres"). Extrais chaque '
        'ligne sous forme JSON : [{"code": "R0110", "libelle": "...", '
        + ", ".join(f'"{c}": <valeur ou null>' for c in colonnes_ordonnees)
        + "}, ...]. Si une cellule est vide ou grisée/noircie dans l'image, "
        "mets null — ne devine jamais une valeur absente. Respecte "
        "scrupuleusement l'alignement colonne par colonne : chaque valeur "
        "doit être associée au code de colonne exact sous lequel elle est "
        "imprimée, pas à sa position dans la ligne. Transcris exactement ce "
        "qui est visible, ne calcule rien."
    )


def extraire_json(texte_brut):
    m = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", texte_brut, re.DOTALL)
    candidat = m.group(1) if m else texte_brut.strip()
    return json.loads(candidat)


async def main():
    if not IMAGE_PATH.exists():
        raise FileNotFoundError(f"Image introuvable : {IMAGE_PATH}")

    with open(DICT_PATH, encoding="utf-8") as f:
        qrt_dict = json.load(f)
    sheet_dict = qrt_dict["S.05.01.02"][SHEET_KEY]
    codes_attendus = set(sheet_dict["row_codes"].keys())
    col_labels = sheet_dict["col_codes"]
    colonnes_ordonnees = sorted(col_labels.keys(), key=lambda c: int(re.match(r"C(\d+)", c).group(1)))

    prompt = build_prompt(colonnes_ordonnees, col_labels)
    print(f"Colonnes attendues ({len(colonnes_ordonnees)}) : {colonnes_ordonnees}")
    print(f"Lignes attendues ({len(codes_attendus)}) : {sorted(codes_attendus)}\n")

    config = ProcessorConfig(
        input_path="", output_dir=str(OUTPUT_DIR),
        ai_provider=AIProvider.GEMINI, image_prompt=prompt,
    )
    processor = AIProcessor(config)

    print("Appel Gemini en cours...")
    reponse_brute = await processor.process_image(str(IMAGE_PATH))
    print(f"Réponse reçue ({len(reponse_brute)} caractères)\n")

    try:
        lignes = extraire_json(reponse_brute)
    except (json.JSONDecodeError, AttributeError) as e:
        print(f"[ERREUR] JSON non parsable : {e!r}")
        print(reponse_brute)
        with open(OUT_PATH, "w", encoding="utf-8") as f:
            json.dump({"erreur": str(e), "reponse_brute": reponse_brute}, f, ensure_ascii=False, indent=2)
        return

    lignes_par_code = {l["code"]: l for l in lignes}
    codes_trouves = set(lignes_par_code.keys())
    manquants = sorted(codes_attendus - codes_trouves)
    inattendus = sorted(codes_trouves - codes_attendus)

    print("=== Complétude ===")
    print(f"Codes attendus ({len(codes_attendus)}) : {sorted(codes_attendus)}")
    print(f"Codes trouvés  ({len(codes_trouves)}) : {sorted(codes_trouves)}")
    print(f"Manquants  : {manquants if manquants else 'AUCUN'}")
    print(f"Inattendus : {inattendus if inattendus else 'AUCUN'}")

    print("\n=== Comparaison avec les valeurs relevées manuellement ===")
    n_ok, n_diff = 0, 0
    comparaison = []
    for code, cols in VALEURS_LUES_MANUELLEMENT.items():
        ligne = lignes_par_code.get(code)
        for col, attendu in cols.items():
            trouve = ligne.get(col) if ligne else "(code absent)"
            match = trouve == attendu
            statut = "OK" if match else "ÉCART"
            if match:
                n_ok += 1
            else:
                n_diff += 1
            print(f"{code} {col}: gemini={trouve!r:12} attendu={attendu!r:12} [{statut}]")
            comparaison.append({"code": code, "colonne": col, "gemini": trouve, "attendu": attendu, "statut": statut})
    print(f"\nBilan comparaison : {n_ok} OK, {n_diff} écart(s) sur {n_ok + n_diff} cellules vérifiées.")

    print()
    decalages = detect_column_shifts(lignes, sheet_dict["col_groups"])
    print_report(decalages, len(lignes))

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({
            "reponse_brute": reponse_brute,
            "lignes_gemini": lignes,
            "completude": {"attendus": sorted(codes_attendus), "trouves": sorted(codes_trouves),
                            "manquants": manquants, "inattendus": inattendus},
            "comparaison_manuelle": comparaison,
            "decalages_colonne_suspectes": decalages,
        }, f, ensure_ascii=False, indent=2)
    print(f"\nRésultat écrit dans {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
