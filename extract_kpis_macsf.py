# -*- coding: utf-8 -*-
"""extract_kpis_macsf.py — Extraction des 22 KPIs MACSF prévoyance 2025
(Phase 3.9), même approche que extract_kpis_cnp.py."""

import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import extract_kpis as ek

COMPANY_NAME = "MACSF prévoyance"
YEAR = 2025
CORPUS_PATH = ek.TEST_MARKDROP / "output_macsf" / "corpus_final.json"


def charger_corpus_macsf():
    import json
    with open(CORPUS_PATH, encoding="utf-8") as f:
        return json.load(f)["elements"]


def extraire_tout_macsf():
    corpus = charger_corpus_macsf()
    templates_presents = {e["template_id"] for e in corpus}
    print(f"[MACSF] templates présents : {sorted(templates_presents)}")

    valeurs = {}

    for kpi_name, diviseur, multiplicateur in [
        ("ratio_scr", 1, 100), ("ratio_mcr", 1, 100),
        ("scr_total", 1000, 1), ("mcr", 1000, 1),
        ("fonds_propres_eligibles", 1000, 1), ("fonds_propres_t1_nr", 1000, 1),
        ("fonds_propres_t1_r", 1000, 1), ("fonds_propres_t2", 1000, 1), ("fonds_propres_t3", 1000, 1),
    ]:
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            valeurs[kpi_name] = (None, None, "aucune variante du mapping ne matche (MACSF)")
            continue
        valeur, template_id, variante = resultats[0]
        valeurs[kpi_name] = (
            valeur * multiplicateur / diviseur, None,
            f"{template_id}/{variante['row']}/{variante['col']} ({variante['variante']})",
        )

    for kpi_name, diviseur in [("best_estimate", 1000), ("marge_risque", 1000)]:
        try:
            valeur, template_id, variante = ek.valeur_principale(kpi_name, corpus, templates_presents)
            valeurs[kpi_name] = (valeur / diviseur, None, f"{template_id}, somme (mapping)")
        except ek.KpiIntrouvable as e:
            valeurs[kpi_name] = (None, None, str(e))

    if valeurs.get("best_estimate", (None,))[0] is not None and valeurs.get("marge_risque", (None,))[0] is not None:
        valeurs["provisions_techniques"] = (valeurs["best_estimate"][0] + valeurs["marge_risque"][0], None,
                                             "best_estimate + marge_risque")
    else:
        valeurs["provisions_techniques"] = (None, None, "best_estimate ou marge_risque NULL")

    for kpi_name in ("primes_acquises_brutes", "charge_sinistres"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            valeurs[kpi_name] = (None, None, "aucune variante ne matche (MACSF)")
            continue
        total = sum(v for v, _, _ in resultats)
        template_id = resultats[0][1]
        valeurs[kpi_name] = (total / 1000, None, f"{template_id}, somme {len(resultats)} variante(s) (mapping)")

    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie", "scr_diversification"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            valeur, template_id, variante = resultats[0]
            valeurs[kpi_name] = (valeur / 1000, None, f"{template_id}/{variante['row']} (mapping, formule standard)")
        else:
            valeurs[kpi_name] = (None, None, "aucune source disponible pour MACSF")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec Groupama/CNP)")

    return valeurs, corpus, templates_presents


def inserer_en_base_macsf(valeurs):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT OR IGNORE INTO companies (name, type, country) VALUES (?, 'mutuelle', 'France')", (COMPANY_NAME,))
    conn.commit()
    company_id = conn.execute("SELECT id FROM companies WHERE name = ?", (COMPANY_NAME,)).fetchone()[0]

    defs_par_nom = {d["kpi_name"]: d for d in ek.KPI_DEFINITIONS}
    lignes_resume = []
    for kpi_name, (valeur, source_page, note) in valeurs.items():
        d = defs_par_nom[kpi_name]
        conn.execute(
            """INSERT INTO kpis (company_id, year, category, kpi_name, value, unit, source_page, source_chapter, validated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
               ON CONFLICT(company_id, year, kpi_name) DO UPDATE SET
                 value=excluded.value, unit=excluded.unit,
                 source_page=excluded.source_page, source_chapter=excluded.source_chapter""",
            (company_id, YEAR, d["category"], kpi_name, valeur, d["unit"], source_page, d["sfcr_chapter"]),
        )
        lignes_resume.append((kpi_name, d["category"], valeur, d["unit"], note))
    conn.commit()
    conn.close()
    return lignes_resume


if __name__ == "__main__":
    valeurs, corpus, templates_presents = extraire_tout_macsf()
    lignes_resume = inserer_en_base_macsf(valeurs)
    print("\n" + "=" * 100)
    print("RÉSUMÉ — 22 KPIs MACSF prévoyance 2025")
    print("=" * 100)
    n_null = 0
    for kpi_name, categorie, valeur, unite, note in lignes_resume:
        if valeur is None:
            n_null += 1
            val_str = "NULL"
        else:
            val_str = f"{valeur:,.2f}"
        print(f"  {kpi_name:28} {categorie:14} {val_str:>14} {unite:6}  {note}")
    print(f"\n  Total : {len(lignes_resume)} KPIs, {len(lignes_resume) - n_null} valeurs, {n_null} NULL")
