# -*- coding: utf-8 -*-
"""peupler_composants_provisions.py — Remplit kpi_composants pour
`provisions_techniques`, pour TOUTES les sociétés. Cas particulier : ce
KPI n'est jamais lu sur une cellule QRT, il est TOUJOURS calculé comme
`best_estimate + marge_risque` (kpi_qrt_mapping.py, "calcul interne") —
les composants sont donc simplement les 2 KPIs déjà stockés dans
`kpis`, aucune ré-extraction PDF nécessaire, aucune valeur devinée.

Vérifie que best_estimate + marge_risque == provisions_techniques
(tolérance 0.5 M€, arrondis flottants) avant d'insérer — sinon ignore
la société et le signale, jamais un composant inséré sur une identité
qui ne tient pas.

    python peupler_composants_provisions.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"
TOLERANCE_ABS = 0.5  # M€, mêmes arrondis flottants que validate_kpis.py contrôle 1


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    cur.execute("""
        SELECT c.id, c.name, k_be.year, k_be.value, k_be.source_page, k_be.unit,
               k_mr.value, k_mr.source_page,
               k_pt.value
        FROM companies c
        JOIN kpis k_be ON k_be.company_id = c.id AND k_be.kpi_name = 'best_estimate'
        JOIN kpis k_mr ON k_mr.company_id = c.id AND k_mr.year = k_be.year
                       AND k_mr.kpi_name = 'marge_risque'
        JOIN kpis k_pt ON k_pt.company_id = c.id AND k_pt.year = k_be.year
                       AND k_pt.kpi_name = 'provisions_techniques'
        WHERE k_be.value IS NOT NULL AND k_mr.value IS NOT NULL AND k_pt.value IS NOT NULL
    """)
    lignes = cur.fetchall()

    inseres, ignores = 0, []
    for company_id, name, year, be, be_page, unite, mr, mr_page, pt in lignes:
        somme = be + mr
        if abs(somme - pt) > TOLERANCE_ABS:
            ignores.append((name, somme, pt))
            continue

        cur.execute(
            "DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name='provisions_techniques'",
            (company_id, year),
        )
        composants = [
            (company_id, year, "provisions_techniques", 1, "Meilleure estimation (best_estimate)",
             None, be, unite, be_page, "+"),
            (company_id, year, "provisions_techniques", 2, "Marge de risque (marge_risque)",
             None, mr, unite, mr_page, "+"),
        ]
        cur.executemany(
            """INSERT INTO kpi_composants
               (company_id, year, kpi_name, composant_index, composant_label,
                composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            composants,
        )
        inseres += 1

    conn.commit()
    conn.close()

    print(f"[peupler_composants_provisions] {inseres} sociétés peuplées (provisions_techniques)")
    if ignores:
        print(f"  {len(ignores)} ignorées (somme != valeur stockée, tolérance {TOLERANCE_ABS} M€) :")
        for name, somme, pt in ignores:
            print(f"    {name} : best_estimate+marge_risque={somme} vs provisions_techniques={pt}")


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
