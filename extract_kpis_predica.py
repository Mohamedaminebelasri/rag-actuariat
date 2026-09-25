# -*- coding: utf-8 -*-
"""extract_kpis_predica.py — Extraction réelle des 22 KPIs Predica 2025,
insertion dans kpis.db.

Document confirmé texte natif (mode="codes_eiopa", scr_method=
"formule_standard", 20/20 KPIs résolus, 0 NULL, 0 erreur — cf.
batch_diagnostic_report.json, entrée PREDICA-–-SFCR-2025.pdf). Contrairement
à Groupama (Décision 051), AUCUNE lecture d'image/Vision (PaddleOCR/Gemini)
n'est nécessaire ici : les 20 KPIs viennent tous de cellules QRT en texte
natif, lues et vérifiées via kpi_qrt_mapping.py — même discipline libellé
que extract_kpis.py/extract_kpis_cnp.py (aucune cellule lue si le libellé
officiel ne correspond pas à celui attendu).

Contrairement à Groupama/CNP/MACSF, aucun corpus_final.json pré-construit
par Docling n'existe pour Predica (jamais parsé). Le corpus est donc
construit ICI, à la volée, via classify_pages()+extract_qrt_native()
(test_markdrop/ingest.py) — exactement le même mécanisme que
batch_diagnostic.diagnostiquer_pdf() (celui qui a produit le 20/20), mais
ici les valeurs résolues sont CAPTURÉES et insérées en base plutôt que
seulement comptées.

    python extract_kpis_predica.py
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "test_markdrop"))

import extract_kpis as ek  # noqa: E402 (précharge PaddleOCR avant Docling, cf. extract_kpis.py)
from ingest import classify_pages, extract_qrt_native, NATIVE_TEXT_THRESHOLD  # noqa: E402
from detecter_templates import detecter_templates  # noqa: E402
from batch_diagnostic import construire_qrt_dict_synthetique  # noqa: E402
import fitz  # noqa: E402

COMPANY_NAME = "Predica"
YEAR = 2025
PDF_PATH = BASE_DIR / "data" / "PREDICA-–-SFCR-2025.pdf"


def construire_corpus_predica():
    """Construit le corpus QRT de Predica à la volée — même mécanisme que
    diagnostiquer_pdf() dans batch_diagnostic.py (classify_pages +
    detecter_templates + extract_qrt_native sur chaque page QRT), mais on
    garde ici le corpus complet (au format template_id/page_source/contenu,
    identique à corpus_final.json) plutôt que de seulement compter les
    KPIs résolus."""
    qrt_dict_synth = construire_qrt_dict_synthetique(ek.KPI_QRT_MAPPING)
    classification = classify_pages(PDF_PATH)
    pages_qrt = [p for p in classification if p["type"] == "qrt"]
    if not pages_qrt:
        raise RuntimeError("0 page QRT détectée par classify_pages() sur Predica")

    inventaire = detecter_templates(PDF_PATH)
    print(f"[detecter_templates] document_type={inventaire['document_type']!r} "
          f"scr_method={inventaire['scr_method']!r} mode={inventaire['mode']!r} "
          f"({len(pages_qrt)} pages QRT)")

    corpus = []
    pages_ignorees = []
    templates_inconnus = []
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


def extraire_tout_predica():
    corpus = construire_corpus_predica()
    templates_presents = {e["template_id"] for e in corpus}
    print(f"[Predica] templates présents : {sorted(templates_presents)}")

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
            valeurs[kpi_name] = (None, None, "aucune variante du mapping ne matche (Predica)")
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
            valeurs["best_estimate"][1],
            "best_estimate + marge_risque",
        )
    else:
        valeurs["provisions_techniques"] = (None, None, "best_estimate ou marge_risque NULL")

    for kpi_name in ("primes_acquises_brutes", "charge_sinistres"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            valeurs[kpi_name] = (None, None, "aucune variante ne matche (Predica)")
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
            valeurs[kpi_name] = (None, None, "aucune source disponible pour Predica (pas de picture_75 équivalent)")

    # Correction manuelle vérifiée — scr_diversification (Décision, cette
    # session) : extract_qrt_native() (ingest.py) ne reconnaît pas la
    # notation comptable "(N N N)" (parenthèses = négatif) — NUMERIC_FRAGMENT_RE
    # ne matche que des fragments purement numériques, donc "(10" et "550)"
    # sont rejetés et seul le fragment médian "475" est retenu, lu à tort
    # comme 475 K€ au lieu de -10 475 550 K€. Confirmé par lecture directe du
    # texte brut page 71 ("R0060 ... (10 475 550)") ET par recoupement
    # arithmétique EXACT : R0100 (SCR de base, lu correctement = 37 866 516)
    # - somme(R0010..R0050 = 25 138 474+319 385+22 372 731+511 476+0 =
    # 48 342 066) = -10 475 550, à l'euro près. Un même bug affecte R0140/
    # R0150 sur la même page (non utilisés par aucun KPI mappé, donc sans
    # impact ici) — bug générique du parser natif, PAS corrigé dans
    # ingest.py (hors scope de cette tâche, affecterait potentiellement
    # d'autres documents, nécessiterait sa propre régression complète) ;
    # uniquement cette valeur, pour ce document, corrigée manuellement ici,
    # avec la même discipline "jamais deviner, toujours recoupé" que les
    # extractions manuelles Generali/MACIF SAM/Aéma Groupe.
    if valeurs["scr_diversification"][0] == 475 / 1000:
        valeurs["scr_diversification"] = (
            -10_475_550 / 1000, valeurs["scr_diversification"][1],
            "S.25.01.21/R0060 — valeur brute lue par erreur \"475\" (parser ne gère pas la notation "
            "parenthèses-négatif \"(10 475 550)\") ; corrigée manuellement, vérifiée par lecture directe "
            "du texte PDF ET recoupement arithmétique exact R0100 - somme(R0010..R0050) = -10 475 550",
        )

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec Groupama/CNP)")

    return valeurs, corpus, templates_presents


def inserer_en_base_predica(valeurs):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT OR IGNORE INTO companies (name, type, country) VALUES (?, 'SA', 'France')", (COMPANY_NAME,))
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
    print("RÉSUMÉ — 22 KPIs Predica 2025")
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
    valeurs, corpus, templates_presents = extraire_tout_predica()
    lignes_resume = inserer_en_base_predica(valeurs)
    afficher_resume(lignes_resume)
