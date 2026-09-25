# -*- coding: utf-8 -*-
"""export_kpis_for_frontend.py — Exporte kpis.db vers un JSON statique
consommé par le frontend (frontend/src/data/kpi-sources.json).

Pourquoi un export statique plutôt qu'une connexion live SQLite depuis
Next.js : évite une dépendance native (better-sqlite3) dont la
compilation peut échouer sur cet environnement Windows sans toolchain
de build, pour des données qui ne changent pas à chaque requête. À
re-exécuter après chaque mise à jour de kpis.db (ex. après une
extraction/insertion d'un nouvel assureur) pour garder le frontend à
jour — pas automatique, documenté ici.
"""
import json
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"
OUT_PATH = Path(__file__).parent / "frontend" / "src" / "data" / "kpi-sources.json"


def export_kpis():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    companies = {row["id"]: row["name"] for row in conn.execute("SELECT id, name FROM companies")}

    resultat = {}
    for row in conn.execute(
        """SELECT company_id, year, kpi_name, value, unit, source_page, source_chapter
           FROM kpis WHERE value IS NOT NULL ORDER BY company_id, year DESC"""
    ):
        nom_entreprise = companies.get(row["company_id"])
        if nom_entreprise is None:
            continue
        entreprise = resultat.setdefault(nom_entreprise, {})
        # garde la 1re occurrence par kpi_name = l'année la plus récente
        # (ORDER BY year DESC), n'écrase pas si un doublon d'année existe
        entreprise.setdefault(
            row["kpi_name"],
            {
                "value": row["value"],
                "unit": row["unit"],
                "year": row["year"],
                "source_page": row["source_page"],
                "source_chapter": row["source_chapter"],
            },
        )
    conn.close()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)

    n_entreprises = len(resultat)
    n_kpis = sum(len(v) for v in resultat.values())
    print(f"Exporté {n_kpis} KPIs pour {n_entreprises} entreprises -> {OUT_PATH}")


if __name__ == "__main__":
    export_kpis()
