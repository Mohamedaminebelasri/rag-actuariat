"""init_kpi_db.py — Initialise kpis.db (SQLite), base indépendante du RAG/
Qdrant : KPIs actuariels pré-calculés pour le dashboard comparatif
multi-assureurs (Phase 3, Décision 049).

3 tables : companies, kpis, validation_checks. Idempotent (CREATE TABLE IF
NOT EXISTS + INSERT OR IGNORE) — relançable sans casser l'existant.

    python init_kpi_db.py
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "kpis.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    type TEXT NOT NULL,          -- "mutuelle", "SA", "institution de prévoyance"
    country TEXT DEFAULT 'France'
);

CREATE TABLE IF NOT EXISTS kpis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    category TEXT NOT NULL,       -- "solvabilité", "fonds_propres", "scr", "provisions", "mcr"
    kpi_name TEXT NOT NULL,       -- "ratio_scr", "fonds_propres_t1_nr", etc.
    value REAL,                   -- NULL si extraction incertaine, jamais devinée
    unit TEXT NOT NULL,           -- "pct", "M€", "k€"
    source_page INTEGER,
    source_chapter TEXT,          -- "E.1", "D.2", etc.
    validated BOOLEAN DEFAULT 0,
    FOREIGN KEY (company_id) REFERENCES companies(id),
    UNIQUE(company_id, year, kpi_name)
);

CREATE TABLE IF NOT EXISTS validation_checks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    year INTEGER NOT NULL,
    check_name TEXT NOT NULL,
    expected_value REAL,
    computed_value REAL,
    passed BOOLEAN,
    details TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(id)
);

CREATE INDEX IF NOT EXISTS idx_kpis_company_year ON kpis(company_id, year);
CREATE INDEX IF NOT EXISTS idx_kpis_kpi_name ON kpis(kpi_name);
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(SCHEMA)
    conn.execute(
        "INSERT OR IGNORE INTO companies (name, type, country) VALUES (?, ?, ?)",
        ("Groupama", "mutuelle", "France"),
    )
    conn.commit()

    print(f"[init_kpi_db] base initialisée : {DB_PATH}")

    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    print(f"  Tables : {[t[0] for t in tables]}")

    companies = conn.execute("SELECT id, name, type, country FROM companies").fetchall()
    print(f"  companies ({len(companies)}) :")
    for c in companies:
        print(f"    {c}")

    conn.close()


if __name__ == "__main__":
    main()
