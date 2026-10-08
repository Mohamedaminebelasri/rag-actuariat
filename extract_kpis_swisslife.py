# -*- coding: utf-8 -*-
"""extract_kpis_swisslife.py — Extraction réelle des 22 KPIs SwissLife
Assurance et Patrimoine 2025, insertion dans kpis.db.

Document : rapport narratif complet (109 pages), annexes QRT natives
pages 99-107 (classify_pages : 10 pages QRT, 6 exploitées — S.02.01.02
sur 2 pages, S.05.01.02, S.23.01.01, S.25.01.21 FORMULE STANDARD,
S.28.01.01). Unité confirmée par en-tête explicite ("en milliers
d'euros", pages 99/101/105/106) : DIVISEUR_MONTANT=1000 vérifié, pas
deviné (détection magnitude restée "AMBIGU").

Formule standard (S.25.01.21 présent, pas de S.25.05) : les 22 KPIs
sont TOUS résolubles par le mapping générique, sauf resultat_technique
(jamais disponible pour aucune société, structurel). Entité 100% vie
(S.05.01.02 : uniquement la section "engagements d'assurance vie",
aucune ligne non-vie imprimée sur le document — pas 0, ABSENTE ; une
seule variante matche, confirmé par lecture directe du texte brut).

Recoupements arithmétiques effectués à la main avant insertion
(page 105/106, texte brut) :
- fonds_propres_t1_nr+t1_r+t2+t3 = 2353,042+0+200+150 = 2703,042 =
  fonds_propres_eligibles (exact)
- ratio_mcr=576% recoupé avec le CAP Tier 2 (20% du MCR, règle EIOPA) :
  (2353,042 + min(200, 20%×423,024=84,605)) / 423,024 × 100 = 576,24%
  ≈ 576% publié — confirme que le taux publié applique bien le
  plafond Tier 2, pas une incohérence.
- best_estimate = R0540+R0580+R0630+R0670+R0710 = 0+0+30 923+
  11 783 861+17 614 421 = 29 429 205 K€ (exact, page 99)
- marge_risque = R0550+R0590+R0640+R0680+R0720 = 519 977 K€ (exact)
- scr_total : R0100 (SCR de base, =somme simple des 5 modules +
  diversification + risque incorporel, 3 294 535) + R0130(opérationnel,
  105 322) + R0140(LAC provisions techniques, -1 376 057) + R0150(LAC
  impôts différés, -331 702) = 1 692 097 = scr_total — attention : la
  somme NAÏVE modules+diversification+opérationnel (3 399 857) NE
  matche PAS scr_total à ±2% ici, contrairement à l'heuristique de
  contrôle habituelle ; l'écart vient des 2 ajustements LAC (impact
  massif pour un assureur vie), pas d'une erreur — vérifié ligne par
  ligne sur le texte brut, chaîne complète cohérente.

    python extract_kpis_swisslife.py
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
from kpi_definitions import KPI_DEFINITIONS  # noqa: E402
import fitz  # noqa: E402

COMPANY_NAME = "SwissLife Assurance et Patrimoine"
COMPANY_TYPE = "SA"
YEAR = 2025
PDF_PATH = BASE_DIR / "data" / "SL_AP_Narrative_Report_PdfProof.pdf"
DIVISEUR_MONTANT = 1000  # "en milliers d'euros" confirmé sur chaque page QRT lue


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
    doc = fitz.open(str(PDF_PATH))
    for page in pages_qrt:
        template_id = page["template_id"]
        if page["n_caracteres"] <= NATIVE_TEXT_THRESHOLD:
            continue
        if template_id not in qrt_dict_synth:
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
    return corpus, inventaire


def _page_source(corpus, template_id):
    return next((e["page_source"] for e in corpus if e["template_id"] == template_id), None)


def extraire_tout():
    corpus, inventaire = construire_corpus()
    templates_presents = {e["template_id"] for e in corpus}
    print(f"[{COMPANY_NAME}] templates présents : {sorted(templates_presents)}")

    valeurs = {}

    for kpi_name, diviseur, multiplicateur in [
        ("ratio_scr", 1, 100), ("ratio_mcr", 1, 100),
        ("scr_total", DIVISEUR_MONTANT, 1), ("mcr", DIVISEUR_MONTANT, 1),
        ("fonds_propres_eligibles", DIVISEUR_MONTANT, 1), ("fonds_propres_t1_nr", DIVISEUR_MONTANT, 1),
        ("fonds_propres_t1_r", DIVISEUR_MONTANT, 1), ("fonds_propres_t2", DIVISEUR_MONTANT, 1),
        ("fonds_propres_t3", DIVISEUR_MONTANT, 1),
    ]:
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            valeurs[kpi_name] = (None, None, "aucune variante ne matche")
            continue
        valeur, template_id, variante = resultats[0]
        valeurs[kpi_name] = (
            valeur * multiplicateur / diviseur, _page_source(corpus, template_id),
            f"{template_id}/{variante['row']}/{variante['col']} ({variante['variante']})",
        )

    composants_sommes = {}
    for kpi_name in ("best_estimate", "marge_risque"):
        capturer = []
        try:
            valeur, template_id, variante = ek.valeur_principale(kpi_name, corpus, templates_presents,
                                                                   capturer_composants=capturer)
            valeurs[kpi_name] = (valeur / DIVISEUR_MONTANT, _page_source(corpus, template_id), f"{template_id}, somme (mapping)")
            composants_sommes[kpi_name] = (capturer, _page_source(corpus, template_id))
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
        capturer = []
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents, capturer_composants=capturer)
        if resultats:
            total = sum(v for v, _, _ in resultats)
            template_id = resultats[0][1]
            valeurs[kpi_name] = (total / DIVISEUR_MONTANT, _page_source(corpus, template_id),
                                  f"{template_id}, somme {len(resultats)} variante(s) (mapping — entité 100% vie, section non-vie absente du document)")
            composants_sommes[kpi_name] = (capturer, _page_source(corpus, template_id))
        else:
            valeurs[kpi_name] = (None, None, "aucune variante ne matche")

    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie", "scr_diversification"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            valeur, template_id, variante = resultats[0]
            valeurs[kpi_name] = (valeur / DIVISEUR_MONTANT, _page_source(corpus, template_id),
                                  f"{template_id}/{variante['row']} (mapping, formule standard)")
        else:
            valeurs[kpi_name] = (None, None, "aucune variante ne matche")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec les autres sociétés)")

    return valeurs, corpus, templates_presents, composants_sommes


def inserer_en_base(valeurs):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """INSERT INTO companies (name, type, country, type_document, scr_method, type_activite, unite_source)
           VALUES (?, ?, 'France', 'solo', 'formule_standard', 'Vie', 'K€')
           ON CONFLICT(name) DO UPDATE SET
             type_document=excluded.type_document, scr_method=excluded.scr_method,
             type_activite=excluded.type_activite, unite_source=excluded.unite_source""",
        (COMPANY_NAME, COMPANY_TYPE),
    )
    conn.commit()
    company_id = conn.execute("SELECT id FROM companies WHERE name = ?", (COMPANY_NAME,)).fetchone()[0]

    defs_par_nom = {d["kpi_name"]: d for d in KPI_DEFINITIONS}
    lignes_resume = []
    for kpi_name, (valeur, source_page, note) in valeurs.items():
        d = defs_par_nom[kpi_name]
        raw_value = valeur * DIVISEUR_MONTANT if (valeur is not None and d["unit"] == "M€") else None
        raw_unit = "K€" if raw_value is not None else None
        conn.execute(
            """INSERT INTO kpis (company_id, year, category, kpi_name, value, unit, source_page, source_chapter, validated, raw_value, raw_unit)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
               ON CONFLICT(company_id, year, kpi_name) DO UPDATE SET
                 value=excluded.value, unit=excluded.unit,
                 source_page=excluded.source_page, source_chapter=excluded.source_chapter,
                 raw_value=excluded.raw_value, raw_unit=excluded.raw_unit""",
            (company_id, YEAR, d["category"], kpi_name, valeur, d["unit"], source_page, d["sfcr_chapter"],
             raw_value, raw_unit),
        )
        lignes_resume.append((kpi_name, d["category"], valeur, d["unit"], source_page, note))
    conn.commit()
    conn.close()
    return company_id, lignes_resume


def inserer_composants(company_id, composants_sommes):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    for kpi_name, (capturer, page) in composants_sommes.items():
        conn.execute("DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?",
                     (company_id, YEAR, kpi_name))
        for i, c in enumerate(capturer, start=1):
            conn.execute(
                """INSERT INTO kpi_composants
                   (company_id, year, kpi_name, composant_index, composant_label,
                    composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'M€', ?, '+')""",
                (company_id, YEAR, kpi_name, i, c["libelle"] or c["code"], c["code"],
                 c["valeur"] / DIVISEUR_MONTANT, c.get("page") or page),
            )
    conn.commit()
    conn.close()


def afficher_resume(lignes_resume):
    print("\n" + "=" * 100)
    print(f"RÉSUMÉ — 22 KPIs {COMPANY_NAME} 2025")
    print("=" * 100)
    n_null = 0
    for kpi_name, categorie, valeur, unite, page, note in lignes_resume:
        if valeur is None:
            n_null += 1
            val_str = "NULL"
        else:
            val_str = f"{valeur:,.3f}"
        print(f"  {kpi_name:28} {categorie:14} {val_str:>16} {unite:6} {str(page or '-'):5}  {note}")
    print(f"\n  Total : {len(lignes_resume)} KPIs, {len(lignes_resume) - n_null} valeurs, {n_null} NULL")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    valeurs, corpus, templates_presents, composants_sommes = extraire_tout()
    company_id, lignes_resume = inserer_en_base(valeurs)
    inserer_composants(company_id, composants_sommes)
    afficher_resume(lignes_resume)
