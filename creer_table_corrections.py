# -*- coding: utf-8 -*-
"""creer_table_corrections.py — Crée la table `corrections` sur kpis.db
(Décision 111), journal des corrections manuelles saisies via le bouton
"Corriger" du modal KPI (frontend, onglet Données). Sert à garder
l'historique de chaque correction pour analyser les erreurs du modèle
d'extraction — jamais écrasé, jamais purgé.

    python creer_table_corrections.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"

SQL_CREATION = """
CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    company_id INTEGER NOT NULL,
    kpi_name TEXT NOT NULL,
    year INTEGER NOT NULL,
    ancienne_valeur REAL,
    ancienne_unite TEXT,
    nouvelle_valeur TEXT NOT NULL,
    commentaire TEXT,
    date_correction TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (company_id) REFERENCES companies(id)
)
"""


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    deja_presente = conn.execute(
        "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='corrections'"
    ).fetchone()[0]
    conn.execute(SQL_CREATION)
    conn.commit()
    print("table corrections déjà présente" if deja_presente else "table corrections créée")
    conn.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
