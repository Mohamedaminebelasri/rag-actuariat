# -*- coding: utf-8 -*-
"""validate_kpis.py — Contrôles actuariels sur les KPIs déjà extraits dans
kpis.db (Phase 3.4, Décision 052 ; généralisé à toutes les sociétés,
Décision 090). Écrit chaque résultat dans validation_checks (jamais
silencieux), et met à jour kpis.validated=1 pour les KPIs qui passent au
moins 1 contrôle qui les concerne directement.

CONTRÔLES RETENUS — uniquement des identités/inégalités dont la vérité est
certaine (pas une formule actuarielle incertaine ou approximative), TOUS
génériques (lisent uniquement les KPIs de la société en cours, jamais une
valeur ou un nom d'entreprise codé en dur) sauf mention contraire ci-dessous :
1. provisions_techniques = best_estimate + marge_risque (identité de
   construction, cf. extract_kpis.py — doit TOUJOURS passer, garde-fou de
   non-régression). Skippé si un des 3 KPIs est NULL.
2. fonds_propres_eligibles = somme des 4 tiers (identité de construction).
   Skippé si un des 5 KPIs est NULL.
3. ratio_scr recalculé (fonds_propres_eligibles / scr_total × 100) vs
   ratio_scr publié — tolérance 1% (le ratio publié dans le SFCR n'a que
   2 décimales de précision, cf. "2,74" en source, un recalcul depuis les
   montants complets peut différer légèrement de l'arrondi publié).
4. ratio_mcr recalculé — RESTE SPÉCIFIQUE À GROUPAMA (Décision 090) : le
   numérateur (R0570, fonds propres éligibles pour le MCR — un concept
   DIFFÉRENT de fonds_propres_eligibles/R0540, pas dans les 22 KPIs
   stockés) n'est disponible que via `corpus_final.json`, qui n'existe
   QUE pour Groupama (extraction Docling dédiée) — pour toute autre
   société, aucune source indépendante du numérateur MCR-éligible n'est
   capturée nulle part (ni en base, ni dans un fichier), donc ce contrôle
   ne peut pas être généralisé sans deviner une valeur. Skippé proprement
   (jamais un numérateur approximé) pour toute société sans source
   enregistrée — cf. `SOURCES_MCR_INDEPENDANTES`, registre extensible
   plutôt qu'un `if company_name == "Groupama"` littéral.
5. mcr < scr_total — invariant Solvabilité II de base (le MCR est un
   plancher SOUS le SCR). PAS le corridor réglementaire 25%-45% de
   l'article 129 : ce corridor est défini pour les entités SOLO, pas
   garanti identique pour un MCR consolidé groupe — ne pas l'affirmer
   sans être sûr que la définition s'applique telle quelle au niveau
   groupe (cf. limite déjà documentée dans CLAUDE.md/src/, décisions 014-015
   sur le MCR solo). Skippé si mcr ou scr_total est NULL.
6/7. Croisements SCR — RESTENT SPÉCIFIQUES À GROUPAMA (Décision 090,
   analyse détaillée) : la tentative de généraliser ces 2 contrôles via
   une identité générique "somme des 7 composantes SCR ≈ scr_total"
   (calculable pour toute société depuis kpis.db seul) a été testée
   empiriquement AVANT adoption — REJETÉE après avoir produit des écarts
   énormes et non liés à une erreur d'extraction, y compris sur MACIF SAM
   (22%, pourtant triple-vérifiée, Décision 083), Predica (281%), CNP
   (193%), Aéma Groupe (149%) : le SCR final inclut des ajustements LAC
   DT/LAC TP (capacité d'absorption des pertes par les impôts différés/
   les provisions techniques) qui peuvent être TRÈS matériels et NE SONT
   PAS capturés dans les 22 KPIs stockés — une société parfaitement bien
   extraite peut légitimement avoir un écart de plusieurs dizaines de %
   entre la somme des composantes et le SCR final. Forcer cette identité
   comme contrôle aurait produit une majorité de FAUX échecs plutôt que
   de vrais signaux — contraire à la règle "jamais un signal trompeur".
   Les 2 contrôles restent donc les croisements originaux de Décision 051
   (valeurs codées en dur, vérifiées manuellement pour Groupama
   uniquement), skippés proprement pour toute autre société — cf.
   `CROISEMENTS_GROUPAMA`.
8. Signe de chaque KPI non-NULL conforme à kpi_definitions.py (sign
   "positive"/"negative"/"any") — 1 contrôle par KPI concerné. Décision
   090 : `positive` accepte désormais `>= 0` (pas seulement `> 0`) et
   `negative` accepte `<= 0` — plusieurs sociétés ont légitimement des
   tiers de fonds propres ou des composantes SCR à exactement 0,00
   (ex. fonds_propres_t3/scr_souscription_nonvie pour Predica/MGEN,
   Décision 085/088) ; un vrai 0 n'est ni positif ni négatif au sens
   strict, mais n'est pas non plus un signe erroné.
9. Complétude : exactement 22 lignes pour (entreprise, année), exactement
   les NULL attendus (resultat_technique seul). Contrôle VOLONTAIREMENT
   NON assoupli (Décision 090) : certaines sociétés (ex. SGAM AG2R LA
   MONDIALE, 4 NULL) échoueront légitimement ici — c'est un vrai signal
   de complétude (documenté Décision 087), pas un faux positif à cacher.

    python validate_kpis.py [--company Groupama] [--year 2025]
    python validate_kpis.py --all   # toutes les sociétés de companies
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
    p.add_argument("--all", action="store_true", help="Lance sur toutes les sociétés de companies (ignore --company)")
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
    pour le contrôle 4 (recalcul du ratio_mcr). N'existe QUE pour Groupama
    (seule société avec un corpus_final.json Docling dédié) — cf.
    SOURCES_MCR_INDEPENDANTES et le commentaire en tête de fichier."""
    with open(CORPUS_FINAL, encoding="utf-8") as f:
        corpus = json.load(f)["elements"]
    for e in corpus:
        if e.get("template_id") == "S.23.01.22.01":
            row = e["contenu"]["lignes"]["R0570"]
            assert "Total eligible own funds to meet the minimum consolidated group SCR" in row["libelle_officiel"]
            return float(row["valeurs"]["C0010"]["valeur_brute"]) / 1000  # M€
    raise RuntimeError("S.23.01.22.01/R0570 introuvable")


# Décision 090 : registre (pas un `if company_name == "Groupama"` en ligne)
# des sociétés pour lesquelles une source MCR-éligible indépendante du KPI
# stocké est disponible — aujourd'hui, seule Groupama (via
# corpus_final.json). Extensible : ajouter une entrée ici suffit à activer
# le contrôle 4 pour une nouvelle société, SI sa source existe réellement
# (jamais une valeur approximée pour remplir le registre).
SOURCES_MCR_INDEPENDANTES = {
    "Groupama": r0570_eligibles_mcr,
}

# Décision 090 : croisements SCR codés en dur, vérifiés manuellement
# UNIQUEMENT pour Groupama (Décision 051) — voir le commentaire en tête de
# fichier pour l'analyse de pourquoi une généralisation générique (somme
# des composantes SCR) a été testée puis rejetée (faux échecs massifs, pas
# liés à des erreurs d'extraction). Registre extensible de la même façon
# que SOURCES_MCR_INDEPENDANTES.
CROISEMENTS_GROUPAMA = {
    "Groupama": {
        "scr_total": (6_020_977 / 1000, "S.23.01.22.01/R0680 vs S.25.05.22.02/R0220 (codé en dur, cf. Décision 051) — déjà croisés à l'extraction"),
        "scr_souscription_nonvie": (2_474_794 / 1000, "S.25.05.22.01/R0310 vs relecture manuelle vérifiée picture_75.png — déjà croisés à l'extraction"),
    },
}


def executer_controles(kpis, company_name):
    """Retourne une liste de dicts {check_name, expected_value,
    computed_value, passed, details}. Générique (Décision 090) : chaque
    contrôle qui a besoin d'un KPI absent/NULL pour cette société est
    SKIPPÉ proprement (rien inséré) plutôt que de planter ou de calculer
    sur None — cf. `valeurs()` ci-dessous."""
    controles = []

    def ajouter(nom, attendu, calcule, passe, details):
        controles.append({
            "check_name": nom, "expected_value": attendu, "computed_value": calcule,
            "passed": passe, "details": details,
        })

    def valeurs(*noms):
        """Retourne les valeurs de `noms` si TOUTES sont présentes et
        non-NULL pour cette société, sinon None (signal pour skipper le
        contrôle appelant plutôt que de lever une exception sur un KPI
        absent — cas réel : sociétés Aéma/AG2R avec des NULL au-delà de
        resultat_technique, cf. Décisions 087/089)."""
        sortie = []
        for nom in noms:
            paire = kpis.get(nom)
            if paire is None or paire[0] is None:
                return None
            sortie.append(paire[0])
        return sortie

    # --- 1. provisions_techniques = best_estimate + marge_risque ---
    v = valeurs("best_estimate", "marge_risque", "provisions_techniques")
    if v is not None:
        be, rm, pt = v
        attendu = be + rm
        ecart = abs(attendu - pt)
        ajouter("provisions_techniques_somme", attendu, pt, ecart <= TOLERANCE_ABS_IDENTITE,
                 f"best_estimate({be:.2f}) + marge_risque({rm:.2f}) = {attendu:.2f} vs provisions_techniques={pt:.2f}, écart={ecart:.4f} M€")

    # --- 2. fonds_propres_eligibles = somme des 4 tiers ---
    v = valeurs("fonds_propres_t1_nr", "fonds_propres_t1_r", "fonds_propres_t2", "fonds_propres_t3", "fonds_propres_eligibles")
    fp = None
    if v is not None:
        t1nr, t1r, t2, t3, fp = v
        attendu = t1nr + t1r + t2 + t3
        ecart = abs(attendu - fp)
        ajouter("fonds_propres_eligibles_somme_tiers", attendu, fp, ecart <= TOLERANCE_ABS_IDENTITE,
                 f"T1nr+T1r+T2+T3 = {attendu:.2f} vs fonds_propres_eligibles={fp:.2f}, écart={ecart:.4f} M€")

    # --- 3. ratio_scr recalculé ---
    v = valeurs("scr_total", "ratio_scr")
    if v is not None and fp is not None:
        scr_total, ratio_scr = v
        ratio_recalcule = fp / scr_total * 100
        ecart_pct = abs(ratio_recalcule - ratio_scr) / ratio_scr * 100
        ajouter("ratio_scr_recalcule", ratio_scr, round(ratio_recalcule, 2), ecart_pct <= TOLERANCE_PCT_RATIO,
                 f"fonds_propres_eligibles/scr_total×100 = {ratio_recalcule:.4f}% vs ratio_scr publié={ratio_scr:.2f}%, écart={ecart_pct:.4f}%")

    # --- 4. ratio_mcr recalculé — cf. SOURCES_MCR_INDEPENDANTES en tête de
    # fichier : généralisé sous forme de registre plutôt qu'un nom en dur,
    # mais reste Groupama-only en pratique (seule société avec une source
    # indépendante capturée). Skippé proprement pour toute autre société.
    source_mcr = SOURCES_MCR_INDEPENDANTES.get(company_name)
    v = valeurs("mcr", "ratio_mcr")
    if source_mcr is not None and v is not None:
        mcr, ratio_mcr = v
        fp_mcr = source_mcr()
        ratio_mcr_recalcule = fp_mcr / mcr * 100
        ecart_pct = abs(ratio_mcr_recalcule - ratio_mcr) / ratio_mcr * 100
        ajouter("ratio_mcr_recalcule", ratio_mcr, round(ratio_mcr_recalcule, 2), ecart_pct <= TOLERANCE_PCT_RATIO,
                 f"R0570(eligibles MCR)/mcr×100 = {ratio_mcr_recalcule:.4f}% vs ratio_mcr publié={ratio_mcr:.2f}%, écart={ecart_pct:.4f}%")

    # --- 5. mcr < scr_total (invariant de base, PAS le corridor 25-45% solo) ---
    v = valeurs("mcr", "scr_total")
    if v is not None:
        mcr, scr_total = v
        ajouter("mcr_inferieur_scr_total", None, mcr - scr_total, mcr < scr_total,
                 f"mcr={mcr:.2f} M€ doit être < scr_total={scr_total:.2f} M€ (invariant Solvabilité II de base, "
                 "pas le corridor 25-45% de l'art. 129, défini pour le solo — non affirmé ici pour le groupe)")

    # --- 6/7. Croisements SCR — cf. CROISEMENTS_GROUPAMA en tête de fichier :
    # registre extensible, reste Groupama-only en pratique (généralisation
    # générique testée et rejetée, LAC DT/TP non capturés dans les 22 KPIs
    # — cf. analyse détaillée en tête de fichier).
    for kpi_name, (valeur_attendue, detail) in CROISEMENTS_GROUPAMA.get(company_name, {}).items():
        v = valeurs(kpi_name)
        if v is None:
            continue
        valeur_reelle = v[0]
        check_name = "scr_total_croise_S23_S25" if kpi_name == "scr_total" else "scr_nonvie_croise_QRT_image"
        ajouter(check_name, valeur_attendue, valeur_reelle, abs(valeur_reelle - valeur_attendue) <= TOLERANCE_ABS_IDENTITE, detail)

    # --- 8. Signe de chaque KPI non-NULL — Décision 090 : >=0/<=0 (accepte
    # un vrai zéro, légitime pour plusieurs sociétés, cf. commentaire en
    # tête de fichier) plutôt que >0/<0 strict.
    defs_par_nom = {d["kpi_name"]: d for d in KPI_DEFINITIONS}
    for kpi_name, (valeur, unite) in kpis.items():
        if valeur is None:
            continue
        signe_attendu = defs_par_nom[kpi_name]["sign"]
        if signe_attendu == "positive":
            passe = valeur >= 0
        elif signe_attendu == "negative":
            passe = valeur <= 0
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


def valider_societe(conn, company_name, year, afficher_detail=True):
    """Exécute tous les contrôles pour 1 société, persiste, retourne
    (n_passed, controles) — utilisé par --company ET --all."""
    row = conn.execute("SELECT id FROM companies WHERE name=?", (company_name,)).fetchone()
    if row is None:
        print(f">>> ARRÊT — entreprise {company_name!r} absente de companies.")
        return None, None
    company_id = row[0]

    kpis = charger_kpis(conn, company_id, year)
    if not kpis:
        print(f">>> ARRÊT — aucun KPI trouvé pour ({company_name}, {year}). Lance extract_kpis.py d'abord.")
        return None, None

    controles = executer_controles(kpis, company_name) + executer_completude(conn, company_id, year)
    inserer_controles(conn, company_id, year, controles)
    marquer_valides(conn, company_id, year, controles)

    n_passed = sum(1 for c in controles if c["passed"])
    if afficher_detail:
        print("=" * 100)
        print(f"CONTRÔLES ACTUARIELS — {company_name} {year}")
        print("=" * 100)
        for c in controles:
            statut = "OK" if c["passed"] else "ÉCHEC"
            print(f"  [{statut:5}] {c['check_name']:32} {c['details']}")
        print(f"\n  Total : {n_passed}/{len(controles)} contrôles passés\n")
    return n_passed, controles


def main():
    args = parse_cli()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    if args.all:
        noms = [r[0] for r in conn.execute("SELECT name FROM companies ORDER BY name")]
        recap = []
        for nom in noms:
            n_passed, controles = valider_societe(conn, nom, args.year)
            if controles is None:
                continue
            echecs_reels = [c for c in controles if not c["passed"] and not c["check_name"].startswith("signe_")]
            echecs_signe_zero = [c for c in controles if not c["passed"] and c["check_name"].startswith("signe_")
                                  and abs(c["computed_value"]) < 1e-9]
            recap.append((nom, n_passed, len(controles), echecs_reels, echecs_signe_zero))
        conn.close()

        print("\n" + "=" * 100)
        print("RÉCAPITULATIF — validate_kpis.py --all")
        print("=" * 100)
        print(f"  {'Société':30} {'Contrôles':12} {'Échecs réels':14} {'Faux signaux (0,00)'}")
        for nom, n_passed, n_total, echecs_reels, echecs_zero in recap:
            print(f"  {nom:30} {n_passed}/{n_total:<9} {len(echecs_reels):<14} {len(echecs_zero)}")
            for e in echecs_reels:
                print(f"      >>> ÉCHEC RÉEL [{e['check_name']}] {e['details']}")
        return

    n_passed, controles = valider_societe(conn, args.company, args.year)
    conn.close()


if __name__ == "__main__":
    main()
