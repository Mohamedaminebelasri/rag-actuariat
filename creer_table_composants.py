# -*- coding: utf-8 -*-
"""creer_table_composants.py — Crée la table `kpi_composants` sur kpis.db,
qui stocke la décomposition des KPIs calculés comme somme de sous-lignes
QRT (primes_acquises_brutes, charge_sinistres, best_estimate, marge_risque)
— un composant = une ligne QRT (code R, valeur, page source) qui entre
dans le calcul du KPI final. Permet au frontend d'afficher le détail
d'un KPI composé plutôt qu'un seul chiffre opaque.

    python creer_table_composants.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"

SQL_CREATION = """
CREATE TABLE IF NOT EXISTS kpi_composants (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    kpi_name TEXT NOT NULL,
    composant_index INTEGER NOT NULL,
    composant_label TEXT NOT NULL,
    composant_code_qrt TEXT,
    composant_valeur REAL,
    composant_unite TEXT,
    composant_page INTEGER,
    operation TEXT DEFAULT '+',
    FOREIGN KEY (company_id) REFERENCES companies(id)
)
"""

SQL_INDEX = """
CREATE INDEX IF NOT EXISTS idx_kpi_composants_company_kpi
ON kpi_composants(company_id, year, kpi_name)
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    deja_presente = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='kpi_composants'"
    ).fetchone()[0]
    conn.execute(SQL_CREATION)
    conn.execute(SQL_INDEX)
    conn.commit()
    print("table kpi_composants déjà présente" if deja_presente else "table kpi_composants créée")
    conn.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
