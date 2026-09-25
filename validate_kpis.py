# -*- coding: utf-8 -*-
"""validate_kpis.py — Contrôles actuariels sur les KPIs déjà extraits dans
kpis.db (Phase 3.4, Décision 052). Écrit chaque résultat dans
validation_checks (jamais silencieux), et met à jour kpis.validated=1 pour
les KPIs qui passent au moins 1 contrôle qui les concerne directement.

CONTRÔLES RETENUS — uniquement des identités/inégalités dont la vérité est
certaine (pas une formule actuarielle incertaine ou approximative) :
1. provisions_techniques = best_estimate + marge_risque (identité de
   construction, cf. extract_kpis.py — doit TOUJOURS passer, garde-fou de
   non-régression).
2. fonds_propres_eligibles = somme des 4 tiers (identité de construction).
3. ratio_scr recalculé (fonds_propres_eligibles / scr_total × 100) vs
   ratio_scr publié — tolérance 1% (le ratio publié dans le SFCR n'a que
   2 décimales de précision, cf. "2,74" en source, un recalcul depuis les
   montants complets peut différer légèrement de l'arrondi publié).
4. ratio_mcr recalculé, même principe (numérateur R0570 relu directement
   depuis corpus_final.json — pas stocké comme KPI séparé, cf. Décision 051).
5. mcr < scr_total — invariant Solvabilité II de base (le MCR est un
   plancher SOUS le SCR). PAS le corridor réglementaire 25%-45% de
   l'article 129 : ce corridor est défini pour les entités SOLO, pas
   garanti identique pour un MCR consolidé groupe — ne pas l'affirmer
   sans être sûr que la définition s'applique telle quelle au niveau
   groupe (cf. limite déjà documentée dans CLAUDE.md/src/, décisions 014-015
   sur le MCR solo).
6. scr_total croisé (S.23.01/R0680 vs S.25.05.22.02/R0220 codé en dur) —
   persiste en base le croisement déjà fait à l'extraction.
7. scr_souscription_nonvie croisé (S.25.05.22.01/R0310 vs relecture
   manuelle vérifiée de picture_75.png) — idem.
8. Signe de chaque KPI non-NULL conforme à kpi_definitions.py (sign
   "positive"/"negative"/"any") — 1 contrôle par KPI concerné.
9. Complétude : exactement 22 lignes pour (entreprise, année), exactement
   les NULL attendus (resultat_technique seul pour Groupama 2025).

    python validate_kpis.py [--company Groupama] [--year 2025]
"""

import argparse
import json
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "kpis.db"
CORPUS_FINAL = BASE_DIR / "test_markdrop" / "output_structure_brute" / "corpus_final.json"

sys.path.insert(0, str(BASE_DIR))
from kpi_definitions import KPI_DEFINITIONS

TOLERANCE_PCT_RATIO = 1.0  # % — cf. docstring, contrôles 3/4
TOLERANCE_ABS_IDENTITE = 0.5  # M€ — arrondis flottants, contrôles 1/2


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--company", default="Groupama")
    p.add_argument("--year", type=int, default=2025)
    return p.parse_args()


def charger_kpis(conn, company_id, year):
    lignes = conn.execute(
        "SELECT kpi_name, value, unit FROM kpis WHERE company_id=? AND year=?",
        (company_id, year),
    ).fetchall()
    return {nom: (valeur, unite) for nom, valeur, unite in lignes}


def r0570_eligibles_mcr():
    """Relu directement depuis corpus_final.json — PAS stocké comme KPI
    séparé (les 22 KPIs demandés ne l'incluent pas), nécessaire uniquement
    pour le contrôle 4 (recalcul du ratio_mcr)."""
    with open(CORPUS_FINAL, encoding="utf-8") as f:
        corpus = json.load(f)["elements"]
    for e in corpus:
        if e.get("template_id") == "S.23.01.22.01":
            row = e["contenu"]["lignes"]["R0570"]
            assert "Total eligible own funds to meet the minimum consolidated group SCR" in row["libelle_officiel"]
            return float(row["valeurs"]["C0010"]["valeur_brute"]) / 1000  # M€
    raise RuntimeError("S.23.01.22.01/R0570 introuvable")


def executer_controles(kpis, company_name):
    """Retourne une liste de dicts {check_name, expected_value,
    computed_value, passed, details}."""
    controles = []

    def ajouter(nom, attendu, calcule, passe, details):
        controles.append({
            "check_name": nom, "expected_value": attendu, "computed_value": calcule,
            "passed": passe, "details": details,
        })

    # --- 1. provisions_techniques = best_estimate + marge_risque ---
    be, _ = kpis["best_estimate"]
    rm, _ = kpis["marge_risque"]
    pt, _ = kpis["provisions_techniques"]
    attendu = be + rm
    ecart = abs(attendu - pt)
    ajouter("provisions_techniques_somme", attendu, pt, ecart <= TOLERANCE_ABS_IDENTITE,
             f"best_estimate({be:.2f}) + marge_risque({rm:.2f}) = {attendu:.2f} vs provisions_techniques={pt:.2f}, écart={ecart:.4f} M€")

    # --- 2. fonds_propres_eligibles = somme des 4 tiers ---
    t1nr, _ = kpis["fonds_propres_t1_nr"]
    t1r, _ = kpis["fonds_propres_t1_r"]
    t2, _ = kpis["fonds_propres_t2"]
    t3, _ = kpis["fonds_propres_t3"]
    fp, _ = kpis["fonds_propres_eligibles"]
    attendu = t1nr + t1r + t2 + t3
    ecart = abs(attendu - fp)
    ajouter("fonds_propres_eligibles_somme_tiers", attendu, fp, ecart <= TOLERANCE_ABS_IDENTITE,
             f"T1nr+T1r+T2+T3 = {attendu:.2f} vs fonds_propres_eligibles={fp:.2f}, écart={ecart:.4f} M€")

    # --- 3. ratio_scr recalculé ---
    scr_total, _ = kpis["scr_total"]
    ratio_scr, _ = kpis["ratio_scr"]
    ratio_recalcule = fp / scr_total * 100
    ecart_pct = abs(ratio_recalcule - ratio_scr) / ratio_scr * 100
    ajouter("ratio_scr_recalcule", ratio_scr, round(ratio_recalcule, 2), ecart_pct <= TOLERANCE_PCT_RATIO,
             f"fonds_propres_eligibles/scr_total×100 = {ratio_recalcule:.4f}% vs ratio_scr publié={ratio_scr:.2f}%, écart={ecart_pct:.4f}%")

    # --- 4. ratio_mcr recalculé — UNIQUEMENT Groupama : r0570_eligibles_mcr()
    # lit un chemin corpus_final.json codé en dur (Groupama), donc appliquer
    # ce contrôle à une autre entreprise mélangerait le numérateur de
    # Groupama avec le mcr d'une autre société — un nombre inventé, pas un
    # vrai contrôle. Skippé proprement (pas inséré) pour toute autre société,
    # plutôt que de produire un résultat trompeur.
    mcr, _ = kpis["mcr"]
    if company_name == "Groupama":
        ratio_mcr, _ = kpis["ratio_mcr"]
        fp_mcr = r0570_eligibles_mcr()
        ratio_mcr_recalcule = fp_mcr / mcr * 100
        ecart_pct = abs(ratio_mcr_recalcule - ratio_mcr) / ratio_mcr * 100
        ajouter("ratio_mcr_recalcule", ratio_mcr, round(ratio_mcr_recalcule, 2), ecart_pct <= TOLERANCE_PCT_RATIO,
                 f"R0570(eligibles MCR)/mcr×100 = {ratio_mcr_recalcule:.4f}% vs ratio_mcr publié={ratio_mcr:.2f}%, écart={ecart_pct:.4f}%")

    # --- 5. mcr < scr_total (invariant de base, PAS le corridor 25-45% solo) ---
    ajouter("mcr_inferieur_scr_total", None, mcr - scr_total, mcr < scr_total,
             f"mcr={mcr:.2f} M€ doit être < scr_total={scr_total:.2f} M€ (invariant Solvabilité II de base, "
             "pas le corridor 25-45% de l'art. 129, défini pour le solo — non affirmé ici pour le groupe)")

    # --- 6/7. Croisements déjà faits à l'extraction, persistés ici — valeurs
    # de référence codées en dur pour Groupama (cf. Décision 051), non
    # applicables ailleurs : skippés proprement pour toute autre société.
    if company_name == "Groupama":
        ajouter("scr_total_croise_S23_S25", 6_020_977 / 1000, scr_total, abs(scr_total - 6_020_977 / 1000) <= TOLERANCE_ABS_IDENTITE,
                 "S.23.01.22.01/R0680 vs S.25.05.22.02/R0220 (codé en dur, cf. Décision 051) — déjà croisés à l'extraction")
        scr_nonvie, _ = kpis["scr_souscription_nonvie"]
        ajouter("scr_nonvie_croise_QRT_image", 2_474_794 / 1000, scr_nonvie, abs(scr_nonvie - 2_474_794 / 1000) <= TOLERANCE_ABS_IDENTITE,
                 "S.25.05.22.01/R0310 vs relecture manuelle vérifiée picture_75.png — déjà croisés à l'extraction")

    # --- 8. Signe de chaque KPI non-NULL ---
    defs_par_nom = {d["kpi_name"]: d for d in KPI_DEFINITIONS}
    for kpi_name, (valeur, unite) in kpis.items():
        if valeur is None:
            continue
        signe_attendu = defs_par_nom[kpi_name]["sign"]
        if signe_attendu == "positive":
            passe = valeur > 0
        elif signe_attendu == "negative":
            passe = valeur < 0
        else:  # "any"
            passe = True
        ajouter(f"signe_{kpi_name}", signe_attendu, valeur, passe,
                f"valeur={valeur:.2f} {unite}, signe attendu={signe_attendu!r}")

    return controles


def executer_completude(conn, company_id, year):
    n = conn.execute("SELECT COUNT(*) FROM kpis WHERE company_id=? AND year=?", (company_id, year)).fetchone()[0]
    n_null = conn.execute("SELECT COUNT(*) FROM kpis WHERE company_id=? AND year=? AND value IS NULL",
                           (company_id, year)).fetchone()[0]
    noms_null = [r[0] for r in conn.execute(
        "SELECT kpi_name FROM kpis WHERE company_id=? AND year=? AND value IS NULL", (company_id, year)
    ).fetchall()]
    return [
        {"check_name": "completude_22_kpis", "expected_value": 22, "computed_value": n, "passed": n == 22,
         "details": f"{n} lignes trouvées pour (company_id={company_id}, year={year})"},
        {"check_name": "completude_null_attendu", "expected_value": 1, "computed_value": n_null,
         "passed": n_null == 1 and noms_null == ["resultat_technique"],
         "details": f"{n_null} NULL trouvé(s) : {noms_null} (attendu : uniquement resultat_technique)"},
    ]


def inserer_controles(conn, company_id, year, controles):
    for c in controles:
        conn.execute(
            """INSERT INTO validation_checks (company_id, year, check_name, expected_value, computed_value, passed, details)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (company_id, year, c["check_name"], c["expected_value"], c["computed_value"], int(c["passed"]), c["details"]),
        )
    conn.commit()


def marquer_valides(conn, company_id, year, controles):
    """kpis.validated=1 pour tout KPI directement concerné par au moins 1
    contrôle, et dont TOUS les contrôles qui le concernent passent — 0
    sinon (jamais validé par défaut/optimisme, cf. schéma Décision 049)."""
    kpi_concerne = {}
    for c in controles:
        nom = c["check_name"]
        for kpi_name in ("best_estimate", "marge_risque", "provisions_techniques",
                          "fonds_propres_t1_nr", "fonds_propres_t1_r", "fonds_propres_t2",
                          "fonds_propres_t3", "fonds_propres_eligibles", "ratio_scr", "ratio_mcr",
                          "mcr", "scr_total", "scr_souscription_nonvie"):
            if kpi_name in nom or nom == f"signe_{kpi_name}":
                kpi_concerne.setdefault(kpi_name, []).append(c["passed"])
    for kpi_name, resultats in kpi_concerne.items():
        valide = all(resultats)
        conn.execute(
            "UPDATE kpis SET validated=? WHERE company_id=? AND year=? AND kpi_name=?",
            (int(valide), company_id, year, kpi_name),
        )
    conn.commit()


def main():
    args = parse_cli()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    company_id = conn.execute("SELECT id FROM companies WHERE name=?", (args.company,)).fetchone()
    if company_id is None:
        print(f">>> ARRÊT — entreprise {args.company!r} absente de companies.")
        return
    company_id = company_id[0]

    kpis = charger_kpis(conn, company_id, args.year)
    if not kpis:
        print(f">>> ARRÊT — aucun KPI trouvé pour ({args.company}, {args.year}). Lance extract_kpis.py d'abord.")
        return

    controles = executer_controles(kpis, args.company) + executer_completude(conn, company_id, args.year)
    inserer_controles(conn, company_id, args.year, controles)
    marquer_valides(conn, company_id, args.year, controles)
    conn.close()

    print("=" * 100)
    print(f"CONTRÔLES ACTUARIELS — {args.company} {args.year}")
    print("=" * 100)
    n_passed = sum(1 for c in controles if c["passed"])
    for c in controles:
        statut = "OK" if c["passed"] else "ÉCHEC"
        print(f"  [{statut:5}] {c['check_name']:32} {c['details']}")
    print(f"\n  Total : {n_passed}/{len(controles)} contrôles passés")


if __name__ == "__main__":
    main()
