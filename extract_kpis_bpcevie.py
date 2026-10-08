# -*- coding: utf-8 -*-
"""extract_kpis_bpcevie.py — Extraction réelle des 22 KPIs BPCE Vie
2025, insertion dans kpis.db.

Document : rapport narratif complet (88 pages), annexes QRT natives
pages 75-87 (classify_pages : 16 pages QRT). Unité confirmée par le
texte lui-même : "Devise d'affichage : k EUR" imprimé en pied de
page 78/79 — DIVISEUR_MONTANT=1000 vérifié, pas deviné.

PIÈGE 1 — `_page_source()` naïf donne la MAUVAISE page pour best_estimate/
marge_risque/provisions_techniques. S.02.01.02 (bilan) apparaît 3 FOIS
dans le corpus : page 51 (chapitre narratif D.1, classify_pages la
classe "qrt" par erreur — 0 ligne avec valeur dedans, vérifié, donc
inoffensif pour le calcul) PUIS pages 75 (actifs) et 76 (passifs,
où sont RÉELLEMENT best_estimate/marge_risque). Le mapping générique
calcule la bonne VALEUR (vérifiée exacte sur le texte brut page 76 :
R0540+R0580+R0630+R0670+R0710 = 113 837 694 — exact), mais
`_page_source()` renvoie la 1re page du corpus pour ce template_id
(51, narrative, FAUSSE) au lieu de 76 (réelle). Page forcée
manuellement à 76 ci-dessous, documenté plutôt que corrigé dans
`extraire_un_pdf.py` partagé (33 autres sociétés en dépendent, risque
de régression hors périmètre d'un fix scopé à ce document).

PIÈGE 2 (RÉEL, celui explicitement signalé dans la consigne de ce
soir) — DOUBLE-COMPTAGE sur primes_acquises_brutes/charge_sinistres,
section non-vie (page 78, template "S.05.01.02 - 01"). Une seule
ligne d'activité non-vie a une valeur non nulle ("Assurance de
protection du revenu") ; comme Total=seule-LoB (aucune autre LoB ne
contribue), `resoudre_variantes_qrt()` renvoie R0210=R0220=100 308
alors que le texte brut montre R0210(Premiums earned, gross direct)=
50 154 UNE SEULE FOIS (répété 2× dans le flux de texte car LoB=Total,
cf. même pattern que AFV/AFI) et R0220(réassurance proportionnelle
acceptée)=VIDE/0 — confirmé en relisant la page : "Brutes – Réassurance
proportionnelle acceptée / R0220 / Brutes – Réassurance non
proportionnelle acceptée" sans AUCUN nombre entre les 2 libellés.
100 308 = 2×50 154 : le code additionne par erreur le token LoB et le
token Total au lieu d'isoler seulement la colonne Total sur cette
table clairsemée (1 seule colonne active + Total). Même mécanisme
pour R0310/R0320 (charge_sinistres, 13 972 dupliqué en 27 944).
La partie VIE (page 79, R1510/R1610) est lue correctement (vérifiée
exacte contre le texte brut : R1510=17 175 273, R1610=7 630 287).
Override manuel ci-dessous (page 78 pour R0210/R0310, page 79 pour
R1510/R1610), PAS de modification de `resoudre_variantes_qrt()`
(code partagé, risque de régression — hors périmètre).

    python extract_kpis_bpcevie.py
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

COMPANY_NAME = "BPCE Vie"
COMPANY_TYPE = "SA"
YEAR = 2025
PDF_PATH = BASE_DIR / "data" / "bpce-vie-rapport-sfcr-2025.pdf"
DIVISEUR_MONTANT = 1000  # "Devise d'affichage : k EUR" confirmé en pied de page

# Override manuel documenté ci-dessus (page 78 : non-vie, page 79 : vie).
PRIMES_MANUEL_KEUR = 50_154 + 0 + 0 + 17_175_273  # = 17 225 427
SINISTRES_MANUEL_KEUR = 13_972 + 0 + 0 + 7_630_287  # = 7 644 259
PRIMES_COMPOSANTS = [
    ("R0210", "Primes acquises brutes — directe (non-vie, Total, 1 LoB active)", 50_154, 78),
    ("R0220", "Primes acquises brutes — réassurance proportionnelle acceptée (non-vie)", 0, 78),
    ("R0230", "Primes acquises brutes — réassurance non-proportionnelle acceptée (non-vie)", 0, 78),
    ("R1510", "Primes acquises brutes (vie, Total)", 17_175_273, 79),
]
SINISTRES_COMPOSANTS = [
    ("R0310", "Charge de sinistres — directe (non-vie, Total, 1 LoB active)", 13_972, 78),
    ("R0320", "Charge de sinistres — réassurance proportionnelle acceptée (non-vie)", 0, 78),
    ("R0330", "Charge de sinistres — réassurance non-proportionnelle acceptée (non-vie)", 0, 78),
    ("R1610", "Charge de sinistres (vie, Total)", 7_630_287, 79),
]


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

    composants_be_rm = {}
    for kpi_name in ("best_estimate", "marge_risque"):
        capturer = []
        try:
            valeur, template_id, variante = ek.valeur_principale(kpi_name, corpus, templates_presents,
                                                                   capturer_composants=capturer)
            # PIÈGE 1 (cf. docstring) : page forcée à 76 (réelle), pas celle
            # renvoyée par _page_source() (51, narrative, 0 ligne de valeur).
            valeurs[kpi_name] = (valeur / DIVISEUR_MONTANT, 76, f"{template_id}, somme (mapping) — page forcée (cf. PIÈGE 1 docstring)")
            composants_be_rm[kpi_name] = (capturer, 76)
        except ek.KpiIntrouvable as e:
            valeurs[kpi_name] = (None, None, str(e))

    if valeurs.get("best_estimate", (None,))[0] is not None and valeurs.get("marge_risque", (None,))[0] is not None:
        valeurs["provisions_techniques"] = (
            valeurs["best_estimate"][0] + valeurs["marge_risque"][0],
            76, "best_estimate + marge_risque",
        )
    else:
        valeurs["provisions_techniques"] = (None, None, "best_estimate ou marge_risque NULL")

    # Override manuel documenté en tête de fichier (PIÈGE 2 — double
    # comptage R0210/R0220 et R0310/R0320 sur la section non-vie, page 78).
    valeurs["primes_acquises_brutes"] = (
        PRIMES_MANUEL_KEUR / DIVISEUR_MONTANT, 79,
        "S.05.01.02, lecture manuelle texte brut (R0210+R0220+R0230 p.78 + R1510 p.79) — resoudre_variantes_qrt double-compte R0210/R0220 sur ce document (cf. PIÈGE 2 docstring)",
    )
    valeurs["charge_sinistres"] = (
        SINISTRES_MANUEL_KEUR / DIVISEUR_MONTANT, 79,
        "S.05.01.02, lecture manuelle texte brut (R0310+R0320+R0330 p.78 + R1610 p.79) — resoudre_variantes_qrt double-compte R0310/R0320 sur ce document (cf. PIÈGE 2 docstring)",
    )

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

    return valeurs, corpus, templates_presents, composants_be_rm


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


def inserer_composants(company_id, composants_be_rm):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    for kpi_name, (capturer, page) in composants_be_rm.items():
        conn.execute("DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?",
                     (company_id, YEAR, kpi_name))
        for i, c in enumerate(capturer, start=1):
            conn.execute(
                """INSERT INTO kpi_composants
                   (company_id, year, kpi_name, composant_index, composant_label,
                    composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'M€', ?, '+')""",
                (company_id, YEAR, kpi_name, i, c["libelle"] or c["code"], c["code"],
                 c["valeur"] / DIVISEUR_MONTANT, page),
            )

    for kpi_name, composants in (("primes_acquises_brutes", PRIMES_COMPOSANTS), ("charge_sinistres", SINISTRES_COMPOSANTS)):
        conn.execute("DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?",
                     (company_id, YEAR, kpi_name))
        for i, (code, label, valeur_keur, page) in enumerate(composants, start=1):
            conn.execute(
                """INSERT INTO kpi_composants
                   (company_id, year, kpi_name, composant_index, composant_label,
                    composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'M€', ?, '+')""",
                (company_id, YEAR, kpi_name, i, label, code, valeur_keur / DIVISEUR_MONTANT, page),
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
    valeurs, corpus, templates_presents, composants_be_rm = extraire_tout()
    company_id, lignes_resume = inserer_en_base(valeurs)
    inserer_composants(company_id, composants_be_rm)
    afficher_resume(lignes_resume)
