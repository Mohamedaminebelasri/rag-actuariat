# -*- coding: utf-8 -*-
"""peupler_composants_aema_connus.py — Remplit `kpi_composants` pour les
KPIs sommes des entités Aéma dont le détail ligne par ligne est DÉJÀ
documenté, textuellement, dans les commentaires vérifiés de
`aema_entites.py` (Décisions 085/116/117) — soit parce qu'un seul code
QRT contribue (entité mono-activité), soit parce que le détail
non-vie/vie a déjà été noté avec sa page lors de l'audit V3-V8. AUCUNE
nouvelle lecture de PDF ici — valeurs copiées telles quelles des
commentaires de aema_entites.py.

Les entités dont best_estimate/marge_risque/primes/charge_sinistres
sont une somme de PLUSIEURS lignes dont les valeurs individuelles ne
sont PAS déjà écrites dans les commentaires (ex. "somme 5 segments",
sans détail) restent hors de ce script — cf.
peupler_composants_aema_pages.py (lecture visuelle des pages
restantes).

Unités : ENTITES_UNITE_EUR_BRUT (aema_entites.py) liste les entités en
euros bruts (÷1 000 000 pour M€) ; les autres sont en K€ (÷1 000) —
même règle que `inserer_entite_en_base`.

    python peupler_composants_aema_connus.py
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


# (société, kpi_name, [(code, libellé, valeur_brute, page)])
# valeur_brute : même unité source que la société (K€ ou € bruts, cf.
# ENTITES_UNITE_EUR_BRUT) — divisée par `diviseur(nom)` à l'insertion.
DONNEES = [
    # --- Macif Vie (K€) : primes/charge = vie seule (R1510/R1610 seul) ---
    ("Macif Vie", "primes_acquises_brutes", [("R1510", "Primes acquises Brut — Vie (seule activité)", 2278966.0, 471)]),
    ("Macif Vie", "charge_sinistres", [("R1610", "Charge des sinistres Brut — Vie (seule activité)", 1844429.0, 471)]),

    # --- Macif Santé Prévoyance (K€) : détail déjà noté ---
    ("Macif Sante Prevoyance", "primes_acquises_brutes", [
        ("R0210", "Primes acquises Brut — Non-vie (Total)", 896062.0, 482),
        ("R1510", "Primes acquises Brut — Vie (Total)", 285524.0, 483),
    ]),
    ("Macif Sante Prevoyance", "charge_sinistres", [
        ("R0310", "Charge des sinistres Brut — Non-vie (Total)", 656058.0, 482),
        ("R1610", "Charge des sinistres Brut — Vie (Total)", 121470.0, 483),
    ]),

    # --- Themis (K€) : 100% non-vie, tout en 1 ligne ---
    ("Themis", "best_estimate", [("R0540", "Meilleure estimation — Non-vie (hors santé, seule activité)", 1218.0, 495)]),
    ("Themis", "marge_risque", [("R0550", "Marge de risque — Non-vie (hors santé, seule activité)", 78.0, 495)]),
    ("Themis", "primes_acquises_brutes", [("R0210", "Primes acquises Brut — Non-vie (seule activité)", 1920.0, 497)]),
    ("Themis", "charge_sinistres", [("R0310", "Charge des sinistres Brut — Non-vie (seule activité)", 386.0, 497)]),

    # --- Macifilia (K€) : non-vie seule pour primes/charge (vie en run-off, pas de primes) ---
    ("Macifilia", "primes_acquises_brutes", [("R0210", "Primes acquises Brut — Non-vie (seule activité avec primes)", 5554.0, 511)]),
    ("Macifilia", "charge_sinistres", [("R0310", "Charge des sinistres Brut — Non-vie (négatif, reprise de provision)", -939552.0, 511)]),

    # --- Aésio Mutuelle (€ bruts) : détail déjà noté ---
    ("Aesio Mutuelle", "primes_acquises_brutes", [
        ("R0210", "Primes acquises Brut — Non-vie (Total)", 1707564110.0, 526),
        ("R1510", "Primes acquises Brut — Vie (Total)", 65838911.0, 527),
    ]),
    ("Aesio Mutuelle", "charge_sinistres", [
        ("R0310", "Charge des sinistres Brut — Non-vie (Total)", 1289307027.0, 526),
        ("R1610", "Charge des sinistres Brut — Vie (Total)", 36622017.0, 527),
    ]),

    # --- MNPAF (€ bruts) : 100% non-vie/santé, tout en 1 ligne ---
    ("MNPAF", "best_estimate", [("R0580", "Meilleure estimation — Santé similaire non-vie (seule activité)", 4848587.0, 540)]),
    ("MNPAF", "marge_risque", [("R0590", "Marge de risque — Santé similaire non-vie (seule activité)", 1740626.0, 540)]),
    ("MNPAF", "primes_acquises_brutes", [("R0210", "Primes acquises Brut — Non-vie (seule activité)", 124606250.0, 542)]),
    ("MNPAF", "charge_sinistres", [("R0310", "Charge des sinistres Brut — Non-vie (seule activité)", 110861791.0, 542)]),

    # --- MMJ (€ bruts) : 100% non-vie/santé, tout en 1 ligne ---
    ("MMJ", "best_estimate", [("R0580", "Meilleure estimation — Santé similaire non-vie (seule activité)", 3277082.0, 552)]),
    ("MMJ", "marge_risque", [("R0590", "Marge de risque — Santé similaire non-vie (seule activité)", 921004.0, 552)]),
    ("MMJ", "primes_acquises_brutes", [("R0210", "Primes acquises Brut — Non-vie (seule activité)", 70690019.0, 554)]),
    ("MMJ", "charge_sinistres", [("R0310", "Charge des sinistres Brut — Non-vie (seule activité)", 55926771.0, 554)]),

    # --- Nuoma (€ bruts) : 100% non-vie/santé, tout en 1 ligne ---
    ("Nuoma", "best_estimate", [("R0580", "Meilleure estimation — Santé similaire non-vie (seule activité)", 5730487.0, 565)]),
    ("Nuoma", "marge_risque", [("R0590", "Marge de risque — Santé similaire non-vie (seule activité)", 961250.0, 565)]),
    ("Nuoma", "primes_acquises_brutes", [("R0210", "Primes acquises Brut — Non-vie (seule activité)", 57945849.0, 567)]),
    ("Nuoma", "charge_sinistres", [("R0310", "Charge des sinistres Brut — Non-vie (seule activité)", 50072108.0, 567)]),

    # --- Abeille Vie (€ bruts) : détail déjà noté ---
    ("Abeille Vie", "primes_acquises_brutes", [
        ("R0210", "Primes acquises Brut — Non-vie (Total)", 85683521.0, 580),
        ("R1510", "Primes acquises Brut — Vie (Total)", 3898489370.0, 581),
    ]),
    ("Abeille Vie", "charge_sinistres", [
        ("R0310", "Charge des sinistres Brut — Non-vie (Total)", 95067347.0, 580),
        ("R1610", "Charge des sinistres Brut — Vie (Total)", 3639847251.0, 581),
    ]),

    # --- Abeille Épargne Retraite (€ bruts) : 100% vie, tout en 1 ligne ---
    ("Abeille Epargne Retraite", "primes_acquises_brutes", [
        ("R1510", "Primes acquises Brut — Vie (seule activité)", 1264646880.0, 595)]),
    ("Abeille Epargne Retraite", "charge_sinistres", [
        ("R1610", "Charge des sinistres Brut — Vie (seule activité)", 1769662909.0, 595)]),

    # --- Abeille IARD Santé (€ bruts) : détail déjà noté ---
    ("Abeille IARD Sante", "primes_acquises_brutes", [
        ("R0210", "Primes acquises Brut — Non-vie (Total)", 2140998437.0, 606),
        ("R1510", "Primes acquises Brut — Vie (Total, rentes issues de sinistres non-vie convertis)", 0.0, 607),
    ]),
    ("Abeille IARD Sante", "charge_sinistres", [
        ("R0310", "Charge des sinistres Brut — Non-vie (Total)", 1491017726.0, 606),
        ("R1610", "Charge des sinistres Brut — Vie (négatif, rentes issues de sinistres non-vie convertis)", -26079879.0, 607),
    ]),
]


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    for nom, kpi_name, composants in DONNEES:
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

        div = diviseur(nom)
        valeur_recomposee = sum(c[2] for c in composants) / div
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

    conn.commit()
    conn.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
