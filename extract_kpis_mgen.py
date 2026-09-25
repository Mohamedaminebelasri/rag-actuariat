# -*- coding: utf-8 -*-
"""extract_kpis_mgen.py — Extraction réelle des 22 KPIs MGEN 2025,
insertion dans kpis.db. Document confirmé texte natif (mode="codes_eiopa",
scr_method="formule_standard", document_type="solo", 10 pages QRT
46-55) — même mécanisme que extract_kpis_predica.py (Décision 085) :
classify_pages()+extract_qrt_native() construit un corpus à la volée
(aucun corpus_final.json pré-existant pour MGEN), resoudre_variantes_qrt
le résout.

    python extract_kpis_mgen.py
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "test_markdrop"))

import extract_kpis as ek  # noqa: E402
from ingest import classify_pages, extract_qrt_native, NATIVE_TEXT_THRESHOLD  # noqa: E402
from detecter_templates import detecter_templates  # noqa: E402
from batch_diagnostic import construire_qrt_dict_synthetique  # noqa: E402
import fitz  # noqa: E402

COMPANY_NAME = "MGEN"
YEAR = 2025
PDF_PATH = BASE_DIR / "data" / "MGEN_SFCR_2025.pdf"


def construire_corpus_mgen():
    qrt_dict_synth = construire_qrt_dict_synthetique(ek.KPI_QRT_MAPPING)
    classification = classify_pages(PDF_PATH)
    pages_qrt = [p for p in classification if p["type"] == "qrt"]
    if not pages_qrt:
        raise RuntimeError("0 page QRT détectée par classify_pages() sur MGEN")

    inventaire = detecter_templates(PDF_PATH)
    print(f"[detecter_templates] document_type={inventaire['document_type']!r} "
          f"scr_method={inventaire['scr_method']!r} mode={inventaire['mode']!r} "
          f"({len(pages_qrt)} pages QRT)")

    corpus = []
    pages_ignorees, templates_inconnus = [], []
    doc = fitz.open(str(PDF_PATH))
    for page in pages_qrt:
        template_id = page["template_id"]
        if page["n_caracteres"] <= NATIVE_TEXT_THRESHOLD:
            pages_ignorees.append((template_id, page["page"]))
            continue
        if template_id not in qrt_dict_synth:
            templates_inconnus.append((template_id, page["page"]))
            continue
        sheet_key = next(iter(qrt_dict_synth[template_id]))
        sheet_dict = qrt_dict_synth[template_id][sheet_key]
        pdf_page = doc[page["page"] - 1]
        r = extract_qrt_native(pdf_page, sheet_dict, sheet_key)
        corpus.append({
            "template_id": template_id, "page_source": page["page"],
            "contenu": {"lignes": r["lignes"]},
        })
    doc.close()

    if pages_ignorees:
        print(f"  [pages ignorées, texte insuffisant] {pages_ignorees}")
    if templates_inconnus:
        print(f"  [templates hors dictionnaire connu] {templates_inconnus}")

    return corpus


def _page_source(corpus, template_id):
    return next((e["page_source"] for e in corpus if e["template_id"] == template_id), None)


def extraire_tout_mgen():
    corpus = construire_corpus_mgen()
    templates_presents = {e["template_id"] for e in corpus}
    print(f"[MGEN] templates présents : {sorted(templates_presents)}")

    valeurs = {}

    for kpi_name, diviseur, multiplicateur in [
        ("ratio_scr", 1, 100), ("ratio_mcr", 1, 100),
        ("scr_total", 1000, 1), ("mcr", 1000, 1),
        ("fonds_propres_eligibles", 1000, 1), ("fonds_propres_t1_nr", 1000, 1),
        ("fonds_propres_t1_r", 1000, 1), ("fonds_propres_t2", 1000, 1), ("fonds_propres_t3", 1000, 1),
    ]:
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            print(f"  [NULL] {kpi_name} : aucune variante ne matche")
            valeurs[kpi_name] = (None, None, "aucune variante du mapping ne matche (MGEN)")
            continue
        valeur, template_id, variante = resultats[0]
        valeurs[kpi_name] = (
            valeur * multiplicateur / diviseur, _page_source(corpus, template_id),
            f"{template_id}/{variante['row']}/{variante['col']} ({variante['variante']})",
        )

    for kpi_name, diviseur in [("best_estimate", 1000), ("marge_risque", 1000)]:
        try:
            valeur, template_id, variante = ek.valeur_principale(kpi_name, corpus, templates_presents)
            valeurs[kpi_name] = (valeur / diviseur, _page_source(corpus, template_id), f"{template_id}, somme (mapping)")
        except ek.KpiIntrouvable as e:
            valeurs[kpi_name] = (None, None, str(e))

    if valeurs.get("best_estimate", (None,))[0] is not None and valeurs.get("marge_risque", (None,))[0] is not None:
        valeurs["provisions_techniques"] = (
            valeurs["best_estimate"][0] + valeurs["marge_risque"][0],
            valeurs["best_estimate"][1], "best_estimate + marge_risque",
        )
    else:
        valeurs["provisions_techniques"] = (None, None, "best_estimate ou marge_risque NULL")

    for kpi_name in ("primes_acquises_brutes", "charge_sinistres"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            valeurs[kpi_name] = (None, None, "aucune variante ne matche (MGEN)")
            continue
        total = sum(v for v, _, _ in resultats)
        template_id = resultats[0][1]
        valeurs[kpi_name] = (total / 1000, _page_source(corpus, template_id),
                              f"{template_id}, somme {len(resultats)} variante(s) (mapping)")

    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie", "scr_diversification"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            valeur, template_id, variante = resultats[0]
            valeurs[kpi_name] = (valeur / 1000, _page_source(corpus, template_id),
                                  f"{template_id}/{variante['row']} (mapping, formule standard)")
        else:
            valeurs[kpi_name] = (None, None, "aucune source disponible pour MGEN (pas de picture_75 équivalent)")

    # Corrections manuelles vérifiées — 2 bugs réels trouvés dans
    # extract_qrt_native() sur cette page précise (Décision, cette
    # session), aucun touché dans le code partagé (même discipline que
    # Predica/BPCE IARD) :
    #
    # 1. fonds_propres_eligibles/tiers (S.23.01.01/R0540) : le corpus
    #    donnait "-" (0.0) pour toutes les colonnes alors que le texte
    #    brut page 53 montre clairement R0540 = 3 441 361 / 3 441 361 /
    #    - / - / - (5 colonnes C0010-C0050). Cause probable : plusieurs
    #    tokens numériques proches en y sur cette ligne, mal réassignés
    #    par l'appariement colonne-par-proximité. Vérifié par cohérence
    #    arithmétique : 3 441 361 = R0290 (Total fonds propres de base
    #    après déductions, déjà lu correctement) = R0700 (Excédent
    #    d'actif sur passif, réserve de réconciliation) — 3 sources
    #    indépendantes de la même page concordent exactement. Confirme
    #    aussi ratio_scr : 3 441 361/1 460 979 = 235,55% ≈ 236% publié.
    #
    # 2. scr_diversification (S.25.01.21/R0060) : le corpus donnait
    #    0,16 (probablement une valeur d'une autre ligne mal capturée)
    #    alors que le texte brut page 54 montre "R0060 ... - 452 163"
    #    — signe négatif séparé de la magnitude par une ESPACE FINE
    #    (U+2009, pas une espace normale), que NUMERIC_FRAGMENT_RE ne
    #    reconnaît pas comme un seul token. Vérifié par cohérence
    #    arithmétique EXACTE : R0100 (SCR de base) = somme(R0010..R0070)
    #    = 789578+69440+70433+939219+1267-452163+792 = 1 418 566, qui
    #    correspond EXACTEMENT au R0100 imprimé (1 418 566) — et
    #    R0100+R0130+R0140+R0150 = 1 418 566+99 604+0-57 191=1 460 979 =
    #    scr_total déjà extrait correctement.
    if valeurs.get("fonds_propres_eligibles", (None,))[0] in (0.0, None):
        valeurs["fonds_propres_eligibles"] = (3441.361, 53, "S.23.01.01/R0540/C0010 — corrigé manuellement, vérifié (= R0290 = R0700, 3 sources concordantes exactement)")
        valeurs["fonds_propres_t1_nr"] = (3441.361, 53, "S.23.01.01/R0540/C0020 — corrigé manuellement, même vérification")
        valeurs["fonds_propres_t1_r"] = (0.0, 53, "S.23.01.01/R0540/C0030 (\"-\") — corrigé manuellement")
        valeurs["fonds_propres_t2"] = (0.0, 53, "S.23.01.01/R0540/C0040 (\"-\") — corrigé manuellement")
        valeurs["fonds_propres_t3"] = (0.0, 53, "S.23.01.01/R0540/C0050 (\"-\") — corrigé manuellement")
    if abs(valeurs.get("scr_diversification", (0.0,))[0] or 0.0) < 1.0:
        valeurs["scr_diversification"] = (-452.163, 54, "S.25.01.21/R0060 — signe \"-\" séparé de la magnitude par une espace fine (U+2009), "
                                                          "corrigé manuellement, vérifié par recoupement arithmétique exact (R0100=somme(R0010..R0070)=1 418 566)")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec Groupama/CNP/Predica)")

    return valeurs, corpus, templates_presents


def inserer_en_base_mgen(valeurs):
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
        lignes_resume.append((kpi_name, d["category"], valeur, d["unit"], source_page, note))
    conn.commit()
    conn.close()
    return lignes_resume


def afficher_resume(lignes_resume):
    print("\n" + "=" * 100)
    print("RÉSUMÉ — 22 KPIs MGEN 2025")
    print("=" * 100)
    print(f"  {'kpi_name':28} {'catégorie':14} {'valeur':>14} {'unité':6} {'page':5}  source")
    n_null = 0
    for kpi_name, categorie, valeur, unite, page, note in lignes_resume:
        if valeur is None:
            n_null += 1
            val_str = "NULL"
        else:
            val_str = f"{valeur:,.2f}"
        print(f"  {kpi_name:28} {categorie:14} {val_str:>14} {unite:6} {str(page or '-'):5}  {note}")
    print(f"\n  Total : {len(lignes_resume)} KPIs, {len(lignes_resume) - n_null} valeurs, {n_null} NULL")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    valeurs, corpus, templates_presents = extraire_tout_mgen()
    lignes_resume = inserer_en_base_mgen(valeurs)
    afficher_resume(lignes_resume)
