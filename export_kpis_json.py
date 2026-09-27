# -*- coding: utf-8 -*-
"""export_kpis_json.py — Génère kpis_export.json, un export complet de
kpis.db destiné à remplacer les données de démonstration inventées
actuellement utilisées par l'onglet Analyse de l'interface (Décision 105).

AUCUNE écriture sur kpis.db (lecture seule, via kpi_service.KpiService
comme le reste du projet, cf. Décision 053). Ne touche à rien d'autre :
pas de code frontend, pas de RAG.

Contenu du JSON généré :
- generated_at : date/heure de génération (ISO 8601)
- companies : les 34 sociétés + leurs métadonnées (type_document,
  scr_method, type_activite, unite_source, cf. Décision 103) + leurs 22
  KPIs (valeur, unité, validated)
- corpus_stats : moyenne/médiane/min/max par KPI, sur les sociétés qui
  l'ont en base avec une valeur non-NULL (via get_corpus_stats)

    python export_kpis_json.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from kpi_service import KpiService
from kpi_definitions import KPI_DEFINITIONS

BASE_DIR = Path(__file__).parent
OUTPUT_PATH = BASE_DIR / "kpis_export.json"
YEAR = 2025

NOMS_KPIS = [d["kpi_name"] for d in KPI_DEFINITIONS]


def construire_export():
    svc = KpiService()
    entreprises = svc.liste_entreprises()

    companies_out = []
    for c in entreprises:
        kpis_bruts = svc.get_kpis(c["name"], YEAR)
        kpis_out = {}
        for kpi_name in NOMS_KPIS:
            row = kpis_bruts.get(kpi_name)
            if row is None:
                kpis_out[kpi_name] = {"value": None, "unit": None, "validated": False}
            else:
                kpis_out[kpi_name] = {
                    "value": row["value"],
                    "unit": row["unit"],
                    "validated": bool(row["validated"]),
                }
        companies_out.append({
            "name": c["name"],
            "type": c["type"],
            "country": c["country"],
            "type_document": c["type_document"],
            "scr_method": c["scr_method"],
            "type_activite": c["type_activite"],
            "unite_source": c["unite_source"],
            "kpis": kpis_out,
        })

    corpus_stats = {
        kpi_name: svc.get_corpus_stats(kpi_name, YEAR)
        for kpi_name in NOMS_KPIS
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "year": YEAR,
        "n_companies": len(companies_out),
        "companies": companies_out,
        "corpus_stats": corpus_stats,
    }


def main():
    export = construire_export()
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    n_kpis_total = sum(len(c["kpis"]) for c in export["companies"])
    n_valides = sum(
        1 for c in export["companies"] for k in c["kpis"].values() if k["validated"]
    )
    print(f"{OUTPUT_PATH.name} généré : {export['n_companies']} sociétés, "
          f"{n_kpis_total} lignes KPI ({n_valides} validées), "
          f"{len(export['corpus_stats'])} KPIs avec statistiques corpus.")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
