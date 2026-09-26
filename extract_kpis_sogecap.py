# -*- coding: utf-8 -*-
"""extract_kpis_sogecap.py — Extraction réelle des 22 KPIs Sogécap
(Société Générale Assurances) 2025, insertion dans kpis.db.

Document confirmé texte natif (mode="codes_eiopa", document_type="groupe",
scr_method="formule_standard", 20/20 en diagnostic — cf.
batch_diagnostic_report.json). Même mécanisme que extract_kpis_predica.py/
extract_kpis_creditagricole.py : corpus construit à la volée via
classify_pages()+extract_qrt_native(), résolu via resoudre_variantes_qrt()
— qui inclut désormais le fix Décision 093 (dédoublonnage EN/FR + détection
arithmétique de colonne Total déjà peuplée).

Décision 096 — 3e occurrence du bug d'unité (€ bruts vs K€, cf. Décision
094 sur les 7 entités Aéma) : les annexes QRT de Sogécap sont en EUROS
BRUTS, pas en K€, contrairement à Predica/MGEN/Crédit Agricole Assurances
(vérifié : R0090/S.22.01.21 = "4 259 413 627" et section narrative E.2
p.29 "(En millions d'euros)... Capital de Solvabilité Requis... 4 259
M EUR" — match exact en interprétant le brut comme des € et non des K€ ;
confirmé aussi sur les primes/sinistres, section narrative A p.12
"chiffre d'affaires... 17,5 Md EUR" / "charge de prestations... 11,5 Md
EUR" vs brut QRT 17 594/11 553 M€ calculé en K€, cohérent en €). Diviseur
DIVISEUR_MONTANT = 1_000_000 (pas 1000) appliqué à TOUS les KPIs de
montant ci-dessous — pas seulement primes/sinistres comme pour Crédit
Agricole Assurances (bug différent, distinct de A/B).

    python extract_kpis_sogecap.py
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

COMPANY_NAME = "Sogécap"
COMPANY_TYPE = "groupe"
YEAR = 2025
PDF_PATH = BASE_DIR / "data" / "Rapport_de_solvabilite_2025_Sogécap_01.pdf"
DIVISEUR_MONTANT = 1_000_000  # Décision 096 : € bruts, pas K€ (cf. docstring)


def construire_corpus():
    qrt_dict_synth = construire_qrt_dict_synthetique(ek.KPI_QRT_MAPPING)
    classification = classify_pages(PDF_PATH)
    pages_qrt = [p for p in classification if p["type"] == "qrt"]
    if not pages_qrt:
        raise RuntimeError(f"0 page QRT détectée par classify_pages() sur {COMPANY_NAME}")

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


def extraire_tout():
    corpus = construire_corpus()
    templates_presents = {e["template_id"] for e in corpus}
    print(f"[{COMPANY_NAME}] templates présents : {sorted(templates_presents)}")

    valeurs = {}

    for kpi_name, diviseur, multiplicateur in [
        ("ratio_scr", 1, 100), ("ratio_mcr", 1, 100),
        ("scr_total", DIVISEUR_MONTANT, 1), ("mcr", DIVISEUR_MONTANT, 1),
        ("fonds_propres_eligibles", DIVISEUR_MONTANT, 1), ("fonds_propres_t1_nr", DIVISEUR_MONTANT, 1),
        ("fonds_propres_t1_r", DIVISEUR_MONTANT, 1), ("fonds_propres_t2", DIVISEUR_MONTANT, 1), ("fonds_propres_t3", DIVISEUR_MONTANT, 1),
    ]:
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            print(f"  [NULL] {kpi_name} : aucune variante ne matche")
            valeurs[kpi_name] = (None, None, f"aucune variante du mapping ne matche ({COMPANY_NAME})")
            continue
        valeur, template_id, variante = resultats[0]
        valeurs[kpi_name] = (
            valeur * multiplicateur / diviseur, _page_source(corpus, template_id),
            f"{template_id}/{variante['row']}/{variante['col']} ({variante['variante']})",
        )

    for kpi_name, diviseur in [("best_estimate", DIVISEUR_MONTANT), ("marge_risque", DIVISEUR_MONTANT)]:
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
            valeurs[kpi_name] = (None, None, f"aucune variante ne matche ({COMPANY_NAME})")
            continue
        total = sum(v for v, _, _ in resultats)
        template_id = resultats[0][1]
        valeurs[kpi_name] = (total / DIVISEUR_MONTANT, _page_source(corpus, template_id),
                              f"{template_id}, somme {len(resultats)} variante(s) (mapping, post-fix Décision 093)")

    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie", "scr_diversification"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            valeur, template_id, variante = resultats[0]
            valeurs[kpi_name] = (valeur / DIVISEUR_MONTANT, _page_source(corpus, template_id),
                                  f"{template_id}/{variante['row']} (mapping, formule standard)")
        else:
            valeurs[kpi_name] = (None, None, f"aucune source disponible pour {COMPANY_NAME}")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec les autres sociétés)")

    return valeurs, corpus, templates_presents


def inserer_en_base(valeurs):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT OR IGNORE INTO companies (name, type, country) VALUES (?, ?, 'France')", (COMPANY_NAME, COMPANY_TYPE))
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
    print(f"RÉSUMÉ — 22 KPIs {COMPANY_NAME} 2025")
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
    valeurs, corpus, templates_presents = extraire_tout()
    lignes_resume = inserer_en_base(valeurs)
    afficher_resume(lignes_resume)
