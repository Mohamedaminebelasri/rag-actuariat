# -*- coding: utf-8 -*-
"""extract_kpis_creditagricole.py — Extraction réelle des 22 KPIs Crédit
Agricole Assurances (groupe combiné) 2025, insertion dans kpis.db.

Document confirmé texte natif (mode="codes_eiopa", document_type="groupe",
scr_method="formule_standard", 20/20 KPIs résolus en diagnostic — cf.
batch_diagnostic_report.json, entrée Groupe-Credit-Agricole-Assurances).
Contrairement à Predica (même groupe, mais document SOLO avec templates
S.23.01.01/S.25.01.21), ce document est un rapport de GROUPE et utilise
les templates .22 (S.23.01.22, S.25.01.22, S.02.01.02 groupe) — déjà
couverts par kpi_qrt_mapping.py (ajoutés pour d'autres groupes : AG2R,
BPCE, Cardif). Même discipline libellé que les autres extract_kpis_*.py :
aucune cellule lue si le libellé officiel ne correspond pas à celui
attendu.

Corpus construit à la volée via classify_pages()+extract_qrt_native() —
même mécanisme que batch_diagnostic.diagnostiquer_pdf() (celui qui a
produit le 20/20 en diagnostic), mais ici les valeurs résolues sont
CAPTURÉES et insérées en base plutôt que seulement comptées.

    python extract_kpis_creditagricole.py
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

COMPANY_NAME = "Crédit Agricole Assurances"
YEAR = 2025
PDF_PATH = BASE_DIR / "data" / "Groupe-Credit-Agricole-Assurances-–-SFCR-2025.pdf"


def construire_corpus_creditagricole():
    qrt_dict_synth = construire_qrt_dict_synthetique(ek.KPI_QRT_MAPPING)
    classification = classify_pages(PDF_PATH)
    pages_qrt = [p for p in classification if p["type"] == "qrt"]
    if not pages_qrt:
        raise RuntimeError("0 page QRT détectée par classify_pages() sur Crédit Agricole Assurances")

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


def extraire_tout_creditagricole():
    corpus = construire_corpus_creditagricole()
    templates_presents = {e["template_id"] for e in corpus}
    print(f"[Crédit Agricole Assurances] templates présents : {sorted(templates_presents)}")

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
            valeurs[kpi_name] = (None, None, "aucune variante du mapping ne matche (Crédit Agricole Assurances)")
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

    # Décision 093 — override manuel vérifié, PAS via resoudre_variantes_qrt :
    # extract_qrt_native() échoue silencieusement sur la ligne R0210/R0220/
    # R0230 de la page 68 (9 colonnes C0010-C0090, "Brut – assurance
    # directe/réassurance proportionnelle/non proportionnelle" — vérifié
    # sur le texte brut : les valeurs sont bien imprimées, ex. R0210 =
    # "1 669 511 / 723 105 / 690 / 623 283 / 1 138 587 / 3 020 / 2 267 322 /
    # 232 240 / 19", mais le corpus ne contient AUCUNE valeur pour cette
    # ligne sur cette page — bug d'appariement position/colonne distinct du
    # double-comptage EN/FR + Total corrigé ci-dessus dans extract_kpis.py,
    # non résolu ici (scope de cette tâche : les 4 nouvelles sociétés, pas
    # une refonte d'extract_qrt_native). Valeurs lues directement sur la
    # colonne Total imprimée (page 69, C0200 pour non-vie ; page 70, C0300
    # pour vie), jamais devinées :
    #   primes non-vie = R0210(7 440 062)+R0220(130 014)+R0230(0) = 7 570 076 K€
    #   primes vie = R1510(41 602 922) K€  ->  total = 49 172 998 K€ = 49 173,00 M€
    #   sinistres non-vie = R0310(5 036 230)+R0320(50 340)+R0330(0) = 5 086 570 K€
    #   sinistres vie = R1610(25 168 806, dont une composante LoB (9 188)
    #     négative déjà intégrée par le document) K€ -> total = 30 255 376 K€
    #     = 30 255,38 M€
    valeurs["primes_acquises_brutes"] = (
        49173.00, 69,
        "S.05.01.02 p.68-70, lecture manuelle colonne Total (C0200 non-vie p.69 + C0300 vie p.70) — "
        "extract_qrt_native() ne capture aucune valeur pour R0210/R0220/R0230 sur la page 68 (bug "
        "d'extraction distinct, non résolu, scope hors Décision 093)",
    )
    valeurs["charge_sinistres"] = (
        30255.38, 69,
        "S.05.01.02 p.68-70, lecture manuelle colonne Total (C0200 non-vie p.69 + C0300 vie p.70, "
        "inclut une composante vie (9 188) K€ négative déjà intégrée par le document) — même limite "
        "d'extraction que primes_acquises_brutes ci-dessus",
    )

    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie", "scr_diversification"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            valeur, template_id, variante = resultats[0]
            valeurs[kpi_name] = (valeur / 1000, _page_source(corpus, template_id),
                                  f"{template_id}/{variante['row']} (mapping, formule standard)")
        else:
            valeurs[kpi_name] = (None, None, "aucune source disponible pour Crédit Agricole Assurances")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec les autres sociétés)")

    return valeurs, corpus, templates_presents


def inserer_en_base_creditagricole(valeurs):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT OR IGNORE INTO companies (name, type, country) VALUES (?, 'groupe', 'France')", (COMPANY_NAME,))
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
    print("RÉSUMÉ — 22 KPIs Crédit Agricole Assurances 2025")
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
    valeurs, corpus, templates_presents = extraire_tout_creditagricole()
    lignes_resume = inserer_en_base_creditagricole(valeurs)
    afficher_resume(lignes_resume)
