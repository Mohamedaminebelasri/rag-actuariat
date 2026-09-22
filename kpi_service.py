# -*- coding: utf-8 -*-
"""kpi_service.py — Couche de service au-dessus de kpis.db (Phase 3.5,
Décision 053), pour le futur dashboard comparatif multi-assureurs. AUCUNE
dépendance au RAG/Qdrant — lecture seule sur kpis.db (jamais d'écriture :
extract_kpis.py et validate_kpis.py restent les seuls écrivains).

    from kpi_service import KpiService
    svc = KpiService()
    svc.get_kpi("Groupama", 2025, "ratio_scr")
    svc.get_all_kpis("Groupama", 2025)
    svc.compare(["Groupama", "CNP Assurances"], 2025, "ratio_scr")
    svc.validation_summary("Groupama", 2025)
"""

import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "kpis.db"


class KpiIntrouvable(Exception):
    pass


class KpiService:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path

    def _connexion(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _company_id(self, conn, company_name):
        row = conn.execute("SELECT id FROM companies WHERE name = ?", (company_name,)).fetchone()
        if row is None:
            raise KpiIntrouvable(f"Entreprise {company_name!r} absente de companies")
        return row["id"]

    # -----------------------------------------------------------------
    # Lecture entreprises
    # -----------------------------------------------------------------

    def liste_entreprises(self):
        """Toutes les entreprises connues : [{id, name, type, country}, ...]."""
        with self._connexion() as conn:
            return [dict(r) for r in conn.execute("SELECT * FROM companies ORDER BY name")]

    # -----------------------------------------------------------------
    # Lecture KPIs — 1 entreprise
    # -----------------------------------------------------------------

    def get_kpi(self, company_name, year, kpi_name):
        """1 KPI précis : dict (value, unit, category, source_page,
        source_chapter, validated) ou None si absent — value peut être
        None (KPI présent mais non extractible, ex. resultat_technique)."""
        with self._connexion() as conn:
            company_id = self._company_id(conn, company_name)
            row = conn.execute(
                "SELECT * FROM kpis WHERE company_id=? AND year=? AND kpi_name=?",
                (company_id, year, kpi_name),
            ).fetchone()
            return dict(row) if row else None

    def get_all_kpis(self, company_name, year):
        """Tous les KPIs d'une entreprise/année : liste de dicts, triée
        par catégorie puis kpi_name (ordre stable pour un affichage
        dashboard)."""
        with self._connexion() as conn:
            company_id = self._company_id(conn, company_name)
            rows = conn.execute(
                "SELECT * FROM kpis WHERE company_id=? AND year=? ORDER BY category, kpi_name",
                (company_id, year),
            ).fetchall()
            return [dict(r) for r in rows]

    def get_kpis_by_category(self, company_name, year, category):
        with self._connexion() as conn:
            company_id = self._company_id(conn, company_name)
            rows = conn.execute(
                "SELECT * FROM kpis WHERE company_id=? AND year=? AND category=? ORDER BY kpi_name",
                (company_id, year, category),
            ).fetchall()
            return [dict(r) for r in rows]

    def annees_disponibles(self, company_name):
        with self._connexion() as conn:
            company_id = self._company_id(conn, company_name)
            rows = conn.execute(
                "SELECT DISTINCT year FROM kpis WHERE company_id=? ORDER BY year", (company_id,)
            ).fetchall()
            return [r["year"] for r in rows]

    # -----------------------------------------------------------------
    # Comparaison multi-entreprises
    # -----------------------------------------------------------------

    def compare(self, company_names, year, kpi_name):
        """1 KPI, plusieurs entreprises, même année : {company_name: dict|None}.
        None si l'entreprise n'a pas encore ce KPI en base (jamais une
        erreur qui interrompt la comparaison des autres)."""
        resultat = {}
        for nom in company_names:
            try:
                resultat[nom] = self.get_kpi(nom, year, kpi_name)
            except KpiIntrouvable:
                resultat[nom] = None
        return resultat

    def compare_categorie(self, company_names, year, category):
        """Tous les KPIs d'une catégorie, plusieurs entreprises :
        {kpi_name: {company_name: value_ou_None}} — pratique pour une
        table de dashboard (lignes=KPIs, colonnes=entreprises)."""
        par_entreprise = {}
        for nom in company_names:
            try:
                par_entreprise[nom] = {k["kpi_name"]: k for k in self.get_kpis_by_category(nom, year, category)}
            except KpiIntrouvable:
                par_entreprise[nom] = {}

        tous_kpis = sorted({kn for d in par_entreprise.values() for kn in d})
        return {
            kpi_name: {nom: par_entreprise[nom].get(kpi_name) for nom in company_names}
            for kpi_name in tous_kpis
        }

    # -----------------------------------------------------------------
    # Contrôles de validation
    # -----------------------------------------------------------------

    def get_validation_checks(self, company_name, year):
        with self._connexion() as conn:
            company_id = self._company_id(conn, company_name)
            rows = conn.execute(
                "SELECT * FROM validation_checks WHERE company_id=? AND year=? ORDER BY id",
                (company_id, year),
            ).fetchall()
            return [dict(r) for r in rows]

    def validation_summary(self, company_name, year):
        """Résumé agrégé : {n_checks, n_passed, n_failed, checks_echoues}."""
        checks = self.get_validation_checks(company_name, year)
        echoues = [c["check_name"] for c in checks if not c["passed"]]
        return {
            "n_checks": len(checks),
            "n_passed": len(checks) - len(echoues),
            "n_failed": len(echoues),
            "checks_echoues": echoues,
        }

    def kpis_non_valides(self, company_name, year):
        """KPIs avec validated=0 — utile pour signaler dans un dashboard
        quels chiffres n'ont encore aucun contrôle indépendant les
        couvrant (pas forcément faux, juste pas encore vérifiés)."""
        with self._connexion() as conn:
            company_id = self._company_id(conn, company_name)
            rows = conn.execute(
                "SELECT kpi_name, value, unit FROM kpis WHERE company_id=? AND year=? AND validated=0",
                (company_id, year),
            ).fetchall()
            return [dict(r) for r in rows]


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    svc = KpiService()
    print("Entreprises connues :", [c["name"] for c in svc.liste_entreprises()])

    resume = svc.validation_summary("Groupama", 2025)
    print(f"\nContrôles Groupama 2025 : {resume['n_passed']}/{resume['n_checks']} passés")
    if resume["checks_echoues"]:
        print("  Échoués :", resume["checks_echoues"])

    non_valides = svc.kpis_non_valides("Groupama", 2025)
    print(f"\nKPIs sans contrôle indépendant ({len(non_valides)}) :")
    for k in non_valides:
        val = f"{k['value']:.2f}" if k["value"] is not None else "NULL"
        print(f"  {k['kpi_name']:28} {val:>12} {k['unit']}")

    print("\nExemple compare() sur ratio_scr (Groupama seule, CNP pas encore en base) :")
    print(" ", {k: (v["value"] if v else None) for k, v in svc.compare(["Groupama", "CNP Assurances"], 2025, "ratio_scr").items()})
