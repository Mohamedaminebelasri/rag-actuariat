# -*- coding: utf-8 -*-
"""peupler_composants_aema_pages.py — Remplit `kpi_composants` pour les
9 entités Aéma dont best_estimate/marge_risque sont une somme de
PLUSIEURS lignes QRT dont le détail n'était PAS déjà noté dans
aema_entites.py (contrairement aux entités mono-ligne, cf.
peupler_composants_aema_connus.py), plus primes_acquises_brutes/
charge_sinistres de MACIF SAM et Aéma Groupe (les 2 seules entités où
ce détail manquait aussi).

Valeurs lues VISUELLEMENT sur le rendu PNG 300 DPI des pages QRT
(S.02.01.02.01 Bilan pour BE/MR, S.05.01.02.01+.02 pour primes/charge)
du PDF combiné "Aéma Groupe RAPPORT UNIQUE..." — chaque valeur vérifiée
par recoupement arithmétique : somme(composants) == valeur déjà
stockée dans `kpis.value` (identique au centime près pour toutes les
11 pages lues, cf. message de commit). Codes R0540/R0580/R0630/R0670/
R0710 (Meilleure estimation) et R0550/R0590/R0640/R0680/R0720 (Marge de
risque) : mêmes 5 segments que kpi_qrt_mapping.py (S.02.01.02) pour
toutes les autres sociétés (non-vie hors santé / santé similaire
non-vie / santé similaire vie / vie hors santé-UC-indexés / UC et
indexés).

    python peupler_composants_aema_pages.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"
YEAR = 2025
TOLERANCE_PCT = 1.0
TOLERANCE_ABS_MIN = 0.5  # M€

ENTITES_UNITE_EUR_BRUT = {
    "Aesio Mutuelle", "MNPAF", "MMJ", "Nuoma",
    "Abeille Vie", "Abeille Epargne Retraite", "Abeille IARD Sante",
}


def diviseur(nom):
    return 1_000_000 if nom in ENTITES_UNITE_EUR_BRUT else 1_000


LABELS_BE = {
    "R0540": "Meilleure estimation — Non-vie (hors santé)",
    "R0580": "Meilleure estimation — Santé (similaire non-vie)",
    "R0630": "Meilleure estimation — Santé (similaire vie)",
    "R0670": "Meilleure estimation — Vie (hors santé, UC/indexés exclus)",
    "R0710": "Meilleure estimation — Vie UC et indexés",
}
LABELS_MR = {
    "R0550": "Marge de risque — Non-vie (hors santé)",
    "R0590": "Marge de risque — Santé (similaire non-vie)",
    "R0640": "Marge de risque — Santé (similaire vie)",
    "R0680": "Marge de risque — Vie (hors santé, UC/indexés exclus)",
    "R0720": "Marge de risque — Vie UC et indexés",
}

# (société, kpi_name, page, {code: valeur_brute})
DONNEES_BE_MR = [
    ("MACIF SAM", "best_estimate", 453, {"R0540": 4561084.0, "R0580": 195303.0, "R0630": 618242.0, "R0670": 595166.0, "R0710": 0.0}),
    ("MACIF SAM", "marge_risque", 453, {"R0550": 252908.0, "R0590": 30669.0, "R0640": 28809.0, "R0680": 28673.0, "R0720": 0.0}),

    ("Aema Groupe", "best_estimate", 440, {"R0540": 6933945.0, "R0580": 965908.0, "R0630": 1041504.0, "R0670": 69434607.0, "R0710": 27489222.0}),
    ("Aema Groupe", "marge_risque", 440, {"R0550": 416581.0, "R0590": 91004.0, "R0640": 69044.0, "R0680": 1025613.0, "R0720": 658473.0}),

    ("Macif Vie", "best_estimate", 469, {"R0540": 0.0, "R0580": 0.0, "R0630": 54352.0, "R0670": 24165943.0, "R0710": 1277676.0}),
    ("Macif Vie", "marge_risque", 469, {"R0550": 0.0, "R0590": 0.0, "R0640": 12580.0, "R0680": 249884.0, "R0720": 11875.0}),

    ("Macif Sante Prevoyance", "best_estimate", 480, {"R0540": 0.0, "R0580": 68670.0, "R0630": 297995.0, "R0670": 226030.0, "R0710": 0.0}),
    ("Macif Sante Prevoyance", "marge_risque", 480, {"R0550": 0.0, "R0590": 13352.0, "R0640": 24065.0, "R0680": 20622.0, "R0720": 0.0}),

    ("Macifilia", "best_estimate", 509, {"R0540": 9735.0, "R0580": 0.0, "R0630": 0.0, "R0670": 1689.0, "R0710": 0.0}),
    ("Macifilia", "marge_risque", 509, {"R0550": 45.0, "R0590": 0.0, "R0640": 0.0, "R0680": 5.0, "R0720": 0.0}),

    ("Aesio Mutuelle", "best_estimate", 524, {"R0540": 0.0, "R0580": 397678555.0, "R0630": 40644763.0, "R0670": 96648591.0, "R0710": 0.0}),
    ("Aesio Mutuelle", "marge_risque", 524, {"R0550": 0.0, "R0590": 43769888.0, "R0640": 3588599.0, "R0680": 18772319.0, "R0720": 0.0}),

    ("Abeille Vie", "best_estimate", 578, {"R0540": 0.0, "R0580": 243905334.0, "R0630": 106994763.0, "R0670": 26384761875.0, "R0710": 19627008033.0}),
    ("Abeille Vie", "marge_risque", 578, {"R0550": 0.0, "R0590": 0.0, "R0640": 0.0, "R0680": 435081532.0, "R0720": 321724693.0}),

    # 100% vie — R0540/R0580/R0630 structurellement non applicables (cellules
    # vides sur la page, pas des 0), seules 2 lignes existent.
    ("Abeille Epargne Retraite", "best_estimate", 594, {"R0670": 17833832925.0, "R0710": 7664362553.0}),
    ("Abeille Epargne Retraite", "marge_risque", 594, {"R0680": 250264544.0, "R0720": 110393565.0}),

    ("Abeille IARD Sante", "best_estimate", 604, {"R0540": 2369530958.0, "R0580": 48757466.0, "R0630": 3470649.0, "R0670": 105488521.0, "R0710": 0.0}),
    ("Abeille IARD Sante", "marge_risque", 604, {"R0550": 161106113.0, "R0590": 547006.0, "R0640": 59670.0, "R0680": 5455812.0, "R0720": 0.0}),
]

# primes_acquises_brutes / charge_sinistres — MACIF SAM et Aéma Groupe
# (seules entités où ce détail n'était pas déjà écrit dans
# aema_entites.py) : page non-vie (S.05.01.02.01) + page vie
# (S.05.01.02.02), colonne Total (C0200/C0300).
DONNEES_PRIMES_CHARGE = [
    ("MACIF SAM", "primes_acquises_brutes", [
        ("R0210", "Primes acquises Brut — Non-vie, assurance directe (Total)", 4410689.0, 455),
        ("R0220", "Primes acquises Brut — Non-vie, réassurance proportionnelle acceptée (Total)", 4.0, 455),
        ("R0230", "Primes acquises Brut — Non-vie, réassurance non proportionnelle acceptée (Total)", 0.0, 455),
        ("R1510", "Primes acquises Brut — Vie (Total)", 35628.0, 456),
    ]),
    ("MACIF SAM", "charge_sinistres", [
        ("R0310", "Charge des sinistres Brut — Non-vie, assurance directe (Total)", 3225436.0, 455),
        ("R0320", "Charge des sinistres Brut — Non-vie, réassurance proportionnelle acceptée (Total)", -1181.0, 455),
        ("R0330", "Charge des sinistres Brut — Non-vie, réassurance non proportionnelle acceptée (Total)", 0.0, 455),
        ("R1610", "Charge des sinistres Brut — Vie (Total)", 38929.0, 456),
    ]),
    ("Aema Groupe", "primes_acquises_brutes", [
        ("R0210", "Primes acquises Brut — Non-vie, assurance directe (Total)", 9493858.0, 442),
        ("R0220", "Primes acquises Brut — Non-vie, réassurance proportionnelle acceptée (Total)", 331094.0, 442),
        ("R0230", "Primes acquises Brut — Non-vie, réassurance non proportionnelle acceptée (Total)", 0.0, 442),
        ("R1510", "Primes acquises Brut — Vie (Total)", 8775062.0, 443),
    ]),
    ("Aema Groupe", "charge_sinistres", [
        ("R0310", "Charge des sinistres Brut — Non-vie, assurance directe (Total)", 6889586.0, 442),
        ("R0320", "Charge des sinistres Brut — Non-vie, réassurance proportionnelle acceptée (Total)", 260074.0, 442),
        ("R0330", "Charge des sinistres Brut — Non-vie, réassurance non proportionnelle acceptée (Total)", 0.0, 442),
        ("R1610", "Charge des sinistres Brut — Vie (Total)", 7885571.0, 443),
    ]),
]


def inserer(cur, company_id, kpi_name, composants, unite, nom):
    div = diviseur(nom)
    stored = cur.execute(
        "SELECT value FROM kpis WHERE company_id=? AND year=? AND kpi_name=? AND value IS NOT NULL",
        (company_id, YEAR, kpi_name),
    ).fetchone()
    if stored is None:
        print(f"  [{nom}/{kpi_name}] pas de valeur stockée — ignoré")
        return
    valeur_stockee = stored[0]
    valeur_recomposee = sum(c[2] for c in composants) / div
    tolerance = max(abs(valeur_stockee) * TOLERANCE_PCT / 100, TOLERANCE_ABS_MIN)
    if abs(valeur_recomposee - valeur_stockee) > tolerance:
        print(f"  [{nom}/{kpi_name}] ÉCART : recomposé={valeur_recomposee:.3f} vs "
              f"stocké={valeur_stockee:.3f} (tolérance {tolerance:.3f}) — IGNORÉ, rien inséré")
        return
    cur.execute("DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?",
                (company_id, YEAR, kpi_name))
    lignes = [
        (company_id, YEAR, kpi_name, i, label, code, valeur_brute / div, unite, page, "+")
        for i, (code, label, valeur_brute, page) in enumerate(composants, start=1)
    ]
    cur.executemany(
        """INSERT INTO kpi_composants
           (company_id, year, kpi_name, composant_index, composant_label,
            composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        lignes,
    )
    print(f"  [{nom}/{kpi_name}] {len(lignes)} composant(s) insérés "
          f"(recomposé={valeur_recomposee:.3f} vs stocké={valeur_stockee:.3f})")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    for nom, kpi_name, page, valeurs_par_code in DONNEES_BE_MR:
        row = cur.execute("SELECT id FROM companies WHERE name=?", (nom,)).fetchone()
        if row is None:
            print(f"  [{nom}] absente de companies — ignorée")
            continue
        company_id = row[0]
        unite_row = cur.execute(
            "SELECT unit FROM kpis WHERE company_id=? AND year=? AND kpi_name=?",
            (company_id, YEAR, kpi_name),
        ).fetchone()
        unite = unite_row[0] if unite_row else "M€"
        labels = LABELS_BE if kpi_name == "best_estimate" else LABELS_MR
        composants = [(code, labels[code], valeur, page) for code, valeur in valeurs_par_code.items()]
        inserer(cur, company_id, kpi_name, composants, unite, nom)

    for nom, kpi_name, composants in DONNEES_PRIMES_CHARGE:
        row = cur.execute("SELECT id FROM companies WHERE name=?", (nom,)).fetchone()
        if row is None:
            print(f"  [{nom}] absente de companies — ignorée")
            continue
        company_id = row[0]
        unite_row = cur.execute(
            "SELECT unit FROM kpis WHERE company_id=? AND year=? AND kpi_name=?",
            (company_id, YEAR, kpi_name),
        ).fetchone()
        unite = unite_row[0] if unite_row else "M€"
        inserer(cur, company_id, kpi_name, composants, unite, nom)

    conn.commit()
    conn.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
