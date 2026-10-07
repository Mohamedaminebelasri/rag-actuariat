# -*- coding: utf-8 -*-
"""extract_kpis_afv.py — Extraction réelle des 22 KPIs AXA France Vie
(AFV) 2025, insertion dans kpis.db.

Document : annexes QRT seules (pas de narratif), 11 pages, texte natif,
10 pages QRT (classify_pages). Unité confirmée par lecture directe de
l'en-tête de CHAQUE page QRT ("in thousand EUR" / "in Thousands EUR",
pages 2/5/9/10/11) — pas une détection par magnitude : DIVISEUR_MONTANT=
1000 est un fait vérifié, pas une hypothèse.

Modèle interne COMPLET ("Solvency Capital Requirement - for undertakings
on Full Internal Models", titre exact de S.25.05.21, seul template SCR
présent — aucun S.25.01/S.25.02) : scr_marche/scr_contrepartie ne font
qu'un ("Total market & credit risk", R0070/R0080) et scr_souscription_vie/
scr_souscription_sante ne font qu'un ("Total Life & Health underwriting
risk", R0400/R0410) dans ce gabarit — 4 KPIs laissés NULL, jamais un
chiffre fusionné deviné/réparti arbitrairement entre 2 KPIs. Vérifié par
lecture directe de la page 10 : R0110 (total non diversifié, 13 192 167,79)
= R0070+R0400+R0270(Business risk,=0)+R0480(opérationnel) et
R0220/R0200 (SCR) = R0110+R0060(diversification,-7 722 540,63) =
5 469 627,16 — recoupement arithmétique exact.

BUG PONCTUEL isolé sur primes_acquises_brutes/charge_sinistres : le
tableau S.05.01.02 de ce document a 17 colonnes (non-vie) + 9 colonnes
(vie), largement plus dense que les gabarits habituels — extract_qrt_native()
détecte bien les codes de ligne mais ne positionne AUCUNE valeur
(`valeurs: {}` sur toutes les lignes, vérifié). Plutôt que de modifier
extract_qrt_native() (code partagé, risque de régression sur les 34
sociétés existantes — hors périmètre d'une correction scopée à ce
document), les 2 totaux sont repris directement du texte brut de la
page 4 (même formule que le mapping générique : somme des lignes GROSS
"Premiums earned"/"Claims incurred", non-vie colonne Total C0200
R0210+R0220+R0230, + vie colonne Total C0300 R1510/R1610) :
  primes_acquises_brutes = 4 975 797 + 3 290 341 + 0 (R0230=-) + 12 294 193
                          = 20 560 331 K€
  charge_sinistres        = 3 749 686 + 2 828 066 + 0 (R0330=-) + 14 408 212
                          = 20 985 964 K€
Valeurs lues 2 fois indépendamment sur le texte brut de la page avant
insertion (jamais devinées).

best_estimate/marge_risque viennent de S.02.01.02 (bilan, page 2) —
formule standard R0540+R0580+R0630+R0670+R0710 (BE) /
R0550+R0590+R0640+R0680+R0720 (RM), déjà correcte via le mapping
générique (valeur_principale) : 138 213,354 M€ / 1 429,969 M€, recoupé
manuellement contre le texte brut de la page 2 (somme exacte).

    python extract_kpis_afv.py
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

COMPANY_NAME = "AXA France Vie"
COMPANY_TYPE = "SA"
YEAR = 2025
PDF_PATH = BASE_DIR / "data" / "afv-annexes-2025-etats-quantitatifs.pdf"
DIVISEUR_MONTANT = 1000  # "in thousand EUR" confirmé sur chaque page QRT lue

# Override manuel documenté ci-dessus (page 4, S.05.01.02 — extract_qrt_native
# échoue silencieusement sur ce tableau à 17 colonnes, valeurs toutes vides).
PRIMES_MANUEL_KEUR = 4_975_797 + 3_290_341 + 0 + 12_294_193  # = 20 560 331
SINISTRES_MANUEL_KEUR = 3_749_686 + 2_828_066 + 0 + 14_408_212  # = 20 985 964
PRIMES_COMPOSANTS = [
    ("R0210", "Primes acquises brutes — directe (non-vie, Total)", 4_975_797),
    ("R0220", "Primes acquises brutes — réassurance proportionnelle acceptée (non-vie, Total)", 3_290_341),
    ("R0230", "Primes acquises brutes — réassurance non-proportionnelle acceptée (non-vie, Total)", 0),
    ("R1510", "Primes acquises brutes (vie, Total)", 12_294_193),
]
SINISTRES_COMPOSANTS = [
    ("R0310", "Charge de sinistres — directe (non-vie, Total)", 3_749_686),
    ("R0320", "Charge de sinistres — réassurance proportionnelle acceptée (non-vie, Total)", 2_828_066),
    ("R0330", "Charge de sinistres — réassurance non-proportionnelle acceptée (non-vie, Total)", 0),
    ("R1610", "Charge de sinistres (vie, Total)", 14_408_212),
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
            valeurs[kpi_name] = (valeur / DIVISEUR_MONTANT, _page_source(corpus, template_id), f"{template_id}, somme (mapping)")
            composants_be_rm[kpi_name] = (capturer, _page_source(corpus, template_id))
        except ek.KpiIntrouvable as e:
            valeurs[kpi_name] = (None, None, str(e))

    if valeurs.get("best_estimate", (None,))[0] is not None and valeurs.get("marge_risque", (None,))[0] is not None:
        valeurs["provisions_techniques"] = (
            valeurs["best_estimate"][0] + valeurs["marge_risque"][0],
            valeurs["best_estimate"][1], "best_estimate + marge_risque",
        )
    else:
        valeurs["provisions_techniques"] = (None, None, "best_estimate ou marge_risque NULL")

    # Override manuel documenté en tête de fichier (page 4, tableau dense
    # S.05.01.02 — extract_qrt_native échoue silencieusement sur ce document).
    page_primes = 4
    valeurs["primes_acquises_brutes"] = (
        PRIMES_MANUEL_KEUR / DIVISEUR_MONTANT, page_primes,
        "S.05.01.02, lecture manuelle texte brut (R0210+R0220+R0230+R1510) — extract_qrt_native échoue sur ce tableau 17 colonnes",
    )
    valeurs["charge_sinistres"] = (
        SINISTRES_MANUEL_KEUR / DIVISEUR_MONTANT, page_primes,
        "S.05.01.02, lecture manuelle texte brut (R0310+R0320+R0330+R1610) — extract_qrt_native échoue sur ce tableau 17 colonnes",
    )

    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie", "scr_diversification"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            valeur, template_id, variante = resultats[0]
            valeurs[kpi_name] = (valeur / DIVISEUR_MONTANT, _page_source(corpus, template_id),
                                  f"{template_id}/{variante['row']} (mapping)")
        else:
            # scr_marche/scr_contrepartie et scr_souscription_vie/sante :
            # fusionnés dans ce gabarit modèle interne (S.25.05.21,
            # R0070-R0080 et R0400-R0410) — jamais répartis arbitrairement.
            valeurs[kpi_name] = (None, None, "fusionné avec un autre KPI dans le gabarit modèle interne S.25.05.21 (non séparable, jamais deviné)")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec les autres sociétés)")

    return valeurs, corpus, templates_presents, composants_be_rm


def inserer_en_base(valeurs):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(
        """INSERT INTO companies (name, type, country, type_document, scr_method, type_activite, unite_source)
           VALUES (?, ?, 'France', 'solo', 'modele_interne_complet', 'Vie', 'K€')
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
        for i, (code, label, valeur_keur) in enumerate(composants, start=1):
            conn.execute(
                """INSERT INTO kpi_composants
                   (company_id, year, kpi_name, composant_index, composant_label,
                    composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, 'M€', 4, '+')""",
                (company_id, YEAR, kpi_name, i, label, code, valeur_keur / DIVISEUR_MONTANT),
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
