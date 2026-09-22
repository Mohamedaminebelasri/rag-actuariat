# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier sait lire un type précis de tableau réglementaire (QRT)
# présent dans le rapport, page par page.
# ------------------------------------------------------------------
"""Extracteur QRT spécialisé, TEST limité au template S.23.01.22 (Fonds
propres), sous-feuille .01 uniquement (page 14 = source page 85, la seule
des deux sous-feuilles de ce template à avoir une couche texte native
dans le PDF — voir constat séparé sur la sous-feuille .02).

Approche : lecture du texte brut du PDF (pas du tableau Docling), avec
positions (x, y) de chaque mot, pour associer chaque valeur numérique à
son code de ligne (R00xx, par proximité verticale) et son code de colonne
(C00xx, par proximité horizontale) — pas d'ordre de lecture séquentiel,
positionnel uniquement, comme demandé.
"""

import json
import re
from pathlib import Path

import fitz

BASE_DIR = Path(__file__).parent
INPUT_PDF = BASE_DIR / "input" / "SFCR_2025_Groupe-Groupama_sectionE_QRT.pdf"
DICT_PATH = BASE_DIR / "output_sectionE_QRT" / "qrt_dictionary.json"
OUT_PATH = BASE_DIR / "output_sectionE_QRT" / "extraction_S23_01_22.json"

PAGE_INDEX = 13  # page 14 (0-based) = source page 85 = "S.23.01.22 - 01"
SHEET_KEY = "S.23.01.22.01"

ROW_CODE_RE = re.compile(r"^R\d{4}$")
COL_CODE_RE = re.compile(r"^C\d{4}$")
NUMERIC_FRAGMENT_RE = re.compile(r"^-?\d+([.,]\d+)?$")

MERGE_GAP_PT = 5.0  # écart max entre fragments d'un même nombre (séparateur de milliers)
LINE_TOLERANCE_PT = 1.5  # tolérance verticale pour regrouper mots dupliqués/même ligne


def dedupe_words(words):
    """Le PDF source contient une couche de texte dupliquée quasi à
    l'identique (même texte, position à ±0.3pt, probablement un artefact
    de génération/faux gras). Un simple arrondi de coordonnées échoue par
    effet de bord (deux copies à 0.4 et 0.6 arrondissent différemment) —
    on regroupe donc par clustering de tolérance (1pt) sur les positions
    des occurrences ayant le MÊME texte, plutôt que par arrondi isolé."""
    from collections import defaultdict

    TOL = 1.0
    by_text = defaultdict(list)
    for w in words:
        x0, y0, x1, y1, text = w[0], w[1], w[2], w[3], w[4]
        by_text[text].append((x0, y0, x1, y1))

    out = []
    for text, occurrences in by_text.items():
        occurrences.sort(key=lambda o: (o[1], o[0]))
        used = [False] * len(occurrences)
        for i, (x0, y0, x1, y1) in enumerate(occurrences):
            if used[i]:
                continue
            cluster = [(x0, y0, x1, y1)]
            used[i] = True
            for j in range(i + 1, len(occurrences)):
                if used[j]:
                    continue
                x0j, y0j, x1j, y1j = occurrences[j]
                if abs(x0j - x0) <= TOL and abs(y0j - y0) <= TOL:
                    cluster.append((x0j, y0j, x1j, y1j))
                    used[j] = True
            n = len(cluster)
            out.append((
                sum(c[0] for c in cluster) / n, sum(c[1] for c in cluster) / n,
                sum(c[2] for c in cluster) / n, sum(c[3] for c in cluster) / n,
                text,
            ))
    return out


def merge_numeric_fragments(frags):
    """frags: liste de (x0,x1,text) triée par x0, tous numériques.
    Fusionne les fragments séparés par un petit espace (milliers) en un
    seul nombre ; renvoie liste de (x_centre, valeur_str)."""
    if not frags:
        return []
    frags = sorted(frags, key=lambda f: f[0])
    groups = [[frags[0]]]
    for f in frags[1:]:
        prev = groups[-1][-1]
        if f[0] - prev[1] <= MERGE_GAP_PT:
            groups[-1].append(f)
        else:
            groups.append([f])

    out = []
    for g in groups:
        text = "".join(t for _, _, t in g)
        x_centre = (g[0][0] + g[-1][1]) / 2
        out.append((x_centre, text))
    return out


def main():
    with open(DICT_PATH, encoding="utf-8") as f:
        qrt_dict = json.load(f)
    sheet_dict = qrt_dict["S.23.01.22"][SHEET_KEY]
    row_labels = sheet_dict["row_codes"]
    col_labels = sheet_dict["col_codes"]

    doc = fitz.open(str(INPUT_PDF))
    page = doc[PAGE_INDEX]
    words = dedupe_words(page.get_text("words"))

    # --- Colonnes : position x de chaque C00xx dans la zone d'en-tête ---
    header_words = [(x0, y0, x1, y1, t) for (x0, y0, x1, y1, t) in words if COL_CODE_RE.match(t)]
    col_x = {t: (x0 + x1) / 2 for (x0, y0, x1, y1, t) in header_words}
    header_y_max = max((y1 for _, _, _, y1, _ in header_words), default=0)
    print(f"Colonnes détectées : {col_x}")

    # --- Lignes : position y de chaque R00xx sous l'en-tête ---
    row_words = [(x0, y0, x1, y1, t) for (x0, y0, x1, y1, t) in words
                 if ROW_CODE_RE.match(t) and y0 > header_y_max]
    # une ligne peut apparaître avec un y légèrement différent (arrondi) : on garde 1 occurrence par code
    rows_by_code = {}
    for x0, y0, x1, y1, t in row_words:
        if t not in rows_by_code:
            rows_by_code[t] = (x0, y0, x1, y1)

    # --- Pour chaque ligne, récupérer les fragments numériques sur la
    #     même bande y, à droite du code, puis les fusionner et les
    #     assigner à la colonne C00xx la plus proche en x ---
    resultat = {}
    for code, (rx0, ry0, rx1, ry1) in sorted(rows_by_code.items()):
        frags = []
        for x0, y0, x1, y1, t in words:
            if x0 <= rx1:
                continue  # à gauche ou sur le code = libellé, pas une valeur
            if abs(y0 - ry0) > LINE_TOLERANCE_PT:
                continue
            if NUMERIC_FRAGMENT_RE.match(t):
                frags.append((x0, x1, t))

        merged = merge_numeric_fragments(frags)

        valeurs = {}
        for x_centre, text in merged:
            nearest_col = min(col_x, key=lambda c: abs(col_x[c] - x_centre))
            valeurs[nearest_col] = text

        resultat[code] = {
            "libelle_officiel": row_labels.get(code, "(code absent du dictionnaire EIOPA)"),
            "valeurs": {
                c: {"libelle_colonne": col_labels.get(c, c), "valeur_brute": v}
                for c, v in valeurs.items()
            },
        }

    # --- Vérification de complétude : codes attendus (dictionnaire) vs trouvés ---
    codes_attendus = set(row_labels.keys())
    codes_trouves = set(resultat.keys())
    manquants = sorted(codes_attendus - codes_trouves)
    inattendus = sorted(codes_trouves - codes_attendus)

    print(f"\n=== Complétude {SHEET_KEY} ===")
    print(f"Codes attendus (dictionnaire EIOPA) : {len(codes_attendus)}")
    print(f"Codes trouvés dans le PDF           : {len(codes_trouves)}")
    print(f"Codes manquants                      : {manquants if manquants else 'AUCUN'}")
    print(f"Codes trouvés hors dictionnaire       : {inattendus if inattendus else 'AUCUN'}")

    print(f"\n=== Détail complet ({len(resultat)} lignes) ===")
    for code, d in resultat.items():
        vals = ", ".join(f"{c}={v['valeur_brute']}" for c, v in d["valeurs"].items()) or "(aucune valeur)"
        print(f"{code}  {d['libelle_officiel'][:70]:70}  {vals}")

    out = {
        "template": SHEET_KEY,
        "page_pdf": PAGE_INDEX + 1,
        "lignes": resultat,
        "completude": {
            "n_attendus": len(codes_attendus),
            "n_trouves": len(codes_trouves),
            "manquants": manquants,
            "inattendus": inattendus,
        },
    }
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nRésultat écrit dans {OUT_PATH}")


if __name__ == "__main__":
    main()
