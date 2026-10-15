# -*- coding: utf-8 -*-
"""extract_kpis_afi.py — Extraction réelle des 22 KPIs AXA France IARD
(AFI) 2025, insertion dans kpis.db.

Document : annexes QRT seules, 10 pages, texte natif, 9 pages QRT
(classify_pages). Unité confirmée par lecture directe de l'en-tête
("in Thousand EUR" / "In Thousand euros", pages 2/3/8/9) :
DIVISEUR_MONTANT=1000 est un fait vérifié, pas une hypothèse — même
document que AFV mais détection magnitude restée "AMBIGU" à nouveau.

Modèle interne COMPLET : seul S.25.05.21 est présent (aucun S.25.01/
S.25.02) -> scr_method='modele_interne_complet'. Mêmes 4 KPIs
irréductibles qu'AFV (scr_marche+scr_contrepartie fusionnés dans
"Total market & credit risk" R0070/R0080 ; scr_souscription_vie+
scr_souscription_sante fusionnés dans "Total Life & Health
underwriting risk" R0400/R0410) — NULL documentés, jamais devinés.
Recoupement arithmétique exact vérifié sur le texte brut de la page 9 :
R0070(2 803 513,40)+R0190(337 472,64)+R0270(0)+R0310(2 398 727,65)+
R0400(179 315,47)+R0480(620 304,77) = 6 339 333,93 ; + R0060
(diversification, -3 717 871,06) = 2 621 462,87 = scr_total (R0030/
R0040/R0200/R0220, confirmé identique).

S.05.01.02 (primes, sinistres) : lecture MANUELLE de la colonne Total
(Décision 154). L'extraction par position comptait certaines lignes
deux fois (ligne d'activité + Total : R0230 = 977,32 au lieu de 488,66 ;
R0310 = 11 158 949 au lieu de 5 577 862,90) et perdait le signe de R0330
(−12 038,51). Valeurs vérifiées sur rendu image de la page 3 ET par
l'arithmétique du tableau : brut direct + acceptations − part des
réassureurs = net imprimé, à l'euro près (primes 5 626 852,98 ; sinistres
3 526 205,35). La 1re lecture manuelle (9 636 839,19 de primes) était la
bonne, contrairement à ce que ce commentaire affirmait auparavant.

best_estimate inclut une composante "vie" non négligeable (R0670 =
1 263 122,78 K€, ~8% du total) : rentes découlant de sinistres non-vie
classées en provisions "vie" par convention EIOPA (cf. S.02.01.02),
PAS une activité vie commerciale — AFI reste classée type_activite=
'Non-vie' (nom de l'entité, SCR souscription vie non isolable/non
dominant dans le modèle interne).

    python extract_kpis_afi.py
"""
import sqlite3
import sys
from pathlib import Path

# S.05.01.02 p.3, colonne Total (K€), lue sur rendu image (Décision 154).
PRIMES_COMPOSANTS = [
    ("R0210", "Primes acquises brutes — directe (non-vie, Total)", 8_921_270.19),
    ("R0220", "Primes acquises brutes — réassurance proportionnelle acceptée (non-vie, Total)", 715_080.34),
    ("R0230", "Primes acquises brutes — réassurance non proportionnelle acceptée (non-vie, Total)", 488.66),
    ("R1510", "Primes acquises brutes (vie, Total)", 0.0),
]
SINISTRES_COMPOSANTS = [
    ("R0310", "Charge de sinistres — directe (non-vie, Total)", 5_577_862.90),
    ("R0320", "Charge de sinistres — réassurance proportionnelle acceptée (non-vie, Total)", 346_611.98),
    ("R0330", "Charge de sinistres — réassurance non proportionnelle acceptée (non-vie, Total)", -12_038.51),
    ("R1610", "Charge de sinistres (vie, Total)", 0.0),
]

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "test_markdrop"))

import extract_kpis as ek  # noqa: E402
from ingest import classify_pages, extract_qrt_native, NATIVE_TEXT_THRESHOLD  # noqa: E402
from detecter_templates import detecter_templates  # noqa: E402
from batch_diagnostic import construire_qrt_dict_synthetique  # noqa: E402
from kpi_definitions import KPI_DEFINITIONS  # noqa: E402
import fitz  # noqa: E402

COMPANY_NAME = "AXA France IARD"
COMPANY_TYPE = "SA"
YEAR = 2025
PDF_PATH = BASE_DIR / "data" / "Annexe-QRT-Publics-AFI-2025-ok.pdf"
DIVISEUR_MONTANT = 1000  # "in Thousand EUR" confirmé sur chaque page QRT lue


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

    # Décision 154 : lecture manuelle de la colonne Total (C0200 non-vie,
    # C0300 vie) du S.05.01.02 p.3 — l'extraction par position comptait
    # certaines lignes deux fois (colonne de ligne d'activité + Total :
    # R0310 = 11 158 949 au lieu de 5 577 863, R0230 = 977 au lieu de 489)
    # et perdait le signe de R0330.
    for kpi_name, composants in (("primes_acquises_brutes", PRIMES_COMPOSANTS),
                                  ("charge_sinistres", SINISTRES_COMPOSANTS)):
        valeurs[kpi_name] = (sum(v for _, _, v in composants) / DIVISEUR_MONTANT, 3,
                             "S.05.01.02 p.3, colonne Total lue manuellement (R02x0/R03x0 non-vie + R1510/R1610 vie) — Décision 154")
        composants_sommes[kpi_name] = ([{"code": c, "libelle": l, "valeur": v} for c, l, v in composants], 3)

    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie", "scr_diversification"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            valeur, template_id, variante = resultats[0]
            valeurs[kpi_name] = (valeur / DIVISEUR_MONTANT, _page_source(corpus, template_id),
                                  f"{template_id}/{variante['row']} (mapping)")
        else:
            valeurs[kpi_name] = (None, None, "fusionné avec un autre KPI dans le gabarit modèle interne S.25.05.21 (non séparable, jamais deviné)")


    return valeurs, corpus, templates_presents, composants_sommes


def inserer_en_base(valeurs):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """INSERT INTO companies (name, type, country, type_document, scr_method, type_activite, unite_source)
           VALUES (?, ?, 'France', 'solo', 'modele_interne_complet', 'Non-vie', 'K€')
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
