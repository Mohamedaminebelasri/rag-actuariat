# -*- coding: utf-8 -*-
"""peupler_composants_manuels.py — Remplit `kpi_composants` pour les
KPIs sommes dont la résolution est un OVERRIDE MANUEL documenté dans le
script d'extraction lui-même (extract_qrt_native() échoue silencieusement
sur ces pages précises, Décision 093/101) — PAS la résolution générique
`resoudre_variantes_qrt`. Les valeurs ci-dessous sont copiées TELLES
QUELLES des commentaires déjà vérifiés de extract_kpis_allianzvie.py et
extract_kpis_creditagricole.py (lecture manuelle de la colonne Total
imprimée sur le PDF, jamais une valeur devinée ici) — aucune nouvelle
lecture de PDF, aucun nouveau calcul.

    python peupler_composants_manuels.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"
YEAR = 2025
TOLERANCE_PCT = 1.0
TOLERANCE_ABS_MIN = 0.5  # M€

# (société, kpi_name, unité, [(code, libellé, valeur_K€, page)])
# Valeurs sources : commentaires vérifiés dans les scripts cités.
DONNEES = [
    (
        # Bilan p.111 (Passifs, 100% image — texte natif absent, lecture
        # manuelle, Décision 084), 5 segments Meilleure estimation, mêmes
        # codes R0540/R0580/R0630/R0670/R0710 que kpi_qrt_mapping.py
        # (S.02.01.02) pour toutes les autres sociétés — recoupé contre
        # "Excédent d'actif sur passif" = fonds_propres_t1_nr déjà vérifié.
        "MAIF", "best_estimate", "M€",
        [
            ("R0540", "Meilleure estimation — Non-vie (hors santé)", 3_714_290.0, 111),
            ("R0580", "Meilleure estimation — Santé (similaire non-vie)", 146_666.0, 111),
            ("R0630", "Meilleure estimation — Santé (similaire vie)", 70_933.0, 111),
            ("R0670", "Meilleure estimation — Vie (hors santé, UC/indexés exclus)", 475_463.0, 111),
            ("R0710", "Meilleure estimation — Vie UC et indexés", 0.0, 111),
        ],
    ),
    (
        "MAIF", "marge_risque", "M€",
        [
            ("R0550", "Marge de risque — Non-vie (hors santé)", 297_831.0, 111),
            ("R0590", "Marge de risque — Santé (similaire non-vie)", 39_033.0, 111),
            ("R0640", "Marge de risque — Santé (similaire vie)", 1_161.0, 111),
            ("R0680", "Marge de risque — Vie (hors santé, UC/indexés exclus)", 5_227.0, 111),
            ("R0720", "Marge de risque — Vie UC et indexés", 0.0, 111),
        ],
    ),
    (
        "Allianz Vie", "primes_acquises_brutes", "M€",
        [("R1510", "Primes acquises Brut — Vie (Total, non-vie \"Non applicable\" sur ce document)",
          5_979_782.0, 84)],
    ),
    (
        "Allianz Vie", "charge_sinistres", "M€",
        [("R1610", "Charge des sinistres Brut — Vie (Total, non-vie \"Non applicable\" sur ce document)",
          5_619_111.0, 84)],
    ),
    (
        "Crédit Agricole Assurances", "primes_acquises_brutes", "M€",
        [
            ("R0210", "Primes acquises Brut — Non-vie, assurance directe (Total)", 7_440_062.0, 69),
            ("R0220", "Primes acquises Brut — Non-vie, réassurance proportionnelle acceptée (Total)", 130_014.0, 69),
            ("R0230", "Primes acquises Brut — Non-vie, réassurance non proportionnelle acceptée (Total)", 0.0, 69),
            ("R1510", "Primes acquises Brut — Vie (Total)", 41_602_922.0, 70),
        ],
    ),
    (
        "Crédit Agricole Assurances", "charge_sinistres", "M€",
        [
            ("R0310", "Charge des sinistres Brut — Non-vie, assurance directe (Total)", 5_036_230.0, 69),
            ("R0320", "Charge des sinistres Brut — Non-vie, réassurance proportionnelle acceptée (Total)", 50_340.0, 69),
            ("R0330", "Charge des sinistres Brut — Non-vie, réassurance non proportionnelle acceptée (Total)", 0.0, 69),
            ("R1610", "Charge des sinistres Brut — Vie (Total, inclut une composante LoB de -9 188 K€ "
                      "déjà intégrée par le document)", 25_168_806.0, 70),
        ],
    ),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    for nom, kpi_name, unite_attendue, composants in DONNEES:
        row = cur.execute("SELECT id FROM companies WHERE name=?", (nom,)).fetchone()
        if row is None:
            print(f"  [{nom}] absente de companies — ignorée")
            continue
        company_id = row[0]

        stored = cur.execute(
            "SELECT value, unit FROM kpis WHERE company_id=? AND year=? AND kpi_name=? AND value IS NOT NULL",
            (company_id, YEAR, kpi_name),
        ).fetchone()
        if stored is None:
            print(f"  [{nom}/{kpi_name}] pas de valeur stockée — ignoré")
            continue
        valeur_stockee, unite = stored

        valeur_recomposee = sum(c[2] for c in composants) / 1000
        tolerance = max(abs(valeur_stockee) * TOLERANCE_PCT / 100, TOLERANCE_ABS_MIN)
        if abs(valeur_recomposee - valeur_stockee) > tolerance:
            print(f"  [{nom}/{kpi_name}] ÉCART : recomposé={valeur_recomposee:.3f} vs "
                  f"stocké={valeur_stockee:.3f} (tolérance {tolerance:.3f}) — IGNORÉ, rien inséré")
            continue

        cur.execute(
            "DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?",
            (company_id, YEAR, kpi_name),
        )
        lignes = [
            (company_id, YEAR, kpi_name, i, label, code, valeur_k / 1000, unite, page, "+")
            for i, (code, label, valeur_k, page) in enumerate(composants, start=1)
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

    conn.commit()
    conn.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
