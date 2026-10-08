# -*- coding: utf-8 -*-
"""extract_kpis_generali_vie.py — Extraction réelle des 22 KPIs
Generali Vie 2025, insertion dans kpis.db.

Document : Annexe_RSSF_QRT_GVIE_2025.pdf, 11 pages, 100% SCANNÉ (0
texte natif, confirmé en lecture seule la session précédente). Pas de
sous-PDF, pas de décalage de page.

MÊME MÉTHODOLOGIE que Generali IARD (Décision 129, même soir) : lecture
visuelle directe de chaque page PNG (zoom 3x, nette) + recoupement
arithmétique exhaustif contre les totaux déjà imprimés sur le document
lui-même — PP-StructureV3 écarté (Décision 055, plante sur ce poste),
PP-OCRv6 lancé mais non terminé en temps raisonnable (toujours en
cours après 1h+ CPU au moment d'écrire ce script, sortie bufferisée),
Gemini Vision indisponible ce soir (503 puis timeout, pas de clé
Anthropic de secours). Voir Décision 129/130 pour le détail de cet
écart méthodologique assumé.

Unité : "Devise: KEUR - milliers d'Euros" imprimé explicitement sur
chaque page lue (2,3,4,5,8,9,10).

RECOUPEMENTS EFFECTUÉS (page -> chaîne vérifiée) :
- p.2-3 (S.02.01.02, Bilan) : R0600=R0610+R0650 (50 245 917=5 560 837+
  44 685 080 ✓) ; R0610=R0630+R0640 (5 479 680+81 157=5 560 837 ✓) ;
  R0650=R0670+R0680 (44 526 960+158 120=44 685 080 ✓) ; R0690=R0710+
  R0720 (36 296 341+242 509=36 538 850 ✓) ; Total actif(109 268 864)-
  Total passif(103 249 277)=6 019 587=Excédent publié EXACT.
- p.4-5 (S.05.01.02) : section non-vie 100% vide (0 partout, entité
  100% vie, confirmé visuellement) ; colonne "Total" (C0300) de la
  section vie reprise telle qu'imprimée.
- p.8-9 (S.23.01.01, Fonds propres) : R0540(SCR-éligible,6 082 818)=
  T1nr(5 582 818)+T1r(0)+T2(250 000)+T3(250 000) ✓ exact ; ratio_scr
  (198,20%)=6 082 818/3 069 039×100=198,20% EXACT ; ratio_mcr(404,24%)=
  R0550(5 582 818, auxiliaires T2/T3 EXCLUS du MCR)/mcr(1 381 068)×100
  =404,24% EXACT.
- p.10 (S.25.05.21, SCR) : R0200(3 069 039)=R0110(3 806 870)+R0060
  (diversification,-737 831)=3 069 039 EXACT ; R0220(SCR publié)=
  R0200+R0210(0)=3 069 039, identique à R0580 de la page 9 (2 sources
  internes au document, exact).

Modèle interne (S.25.05.21) — même limite que GIARD/AFV/AFI ce soir :
R0070 fusionne marché+contrepartie, R0400 fusionne vie+santé. 4 KPIs
NULL, jamais devinés. scr_souscription_nonvie=R0310=0 (entité 100%
vie, cohérent avec primes/sinistres non-vie également à 0).

    python extract_kpis_generali_vie.py
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from kpi_definitions import KPI_DEFINITIONS  # noqa: E402

COMPANY_NAME = "Generali Vie"
COMPANY_TYPE = "SA"
YEAR = 2025
DB_PATH = BASE_DIR / "kpis.db"
DIVISEUR_MONTANT = 1000  # "Devise: KEUR - milliers d'Euros" confirmé explicitement

BE_COMPOSANTS = [
    ("BE non-vie hors santé (R0540)", 0),
    ("BE santé (similaire non-vie) (R0580)", 0),
    ("BE santé (similaire vie) (R0630)", 5_479_680),
    ("BE vie (hors santé/UC/indexés) (R0670)", 44_526_960),
    ("BE UC et indexés (R0710)", 36_296_341),
]
RM_COMPOSANTS = [
    ("RM non-vie hors santé (R0550)", 0),
    ("RM santé (similaire non-vie) (R0590)", 0),
    ("RM santé (similaire vie) (R0640)", 81_157),
    ("RM vie (hors santé/UC/indexés) (R0680)", 158_120),
    ("RM UC et indexés (R0720)", 242_509),
]
PAGE_BE_RM = 3

PRIMES_COMPOSANTS = [
    ("Primes acquises brutes (non-vie, Total)", 0, 4),
    ("Primes acquises brutes (vie, Total) R1510", 12_839_294, 5),
]
SINISTRES_COMPOSANTS = [
    ("Charge de sinistres (non-vie, Total)", 0, 4),
    ("Charge de sinistres (vie, Total) R1610", 9_426_224, 5),
]

FONDS_PROPRES_ELIGIBLES_KEUR = 6_082_818
FONDS_PROPRES_T1_NR_KEUR = 5_582_818
FONDS_PROPRES_T1_R_KEUR = 0
FONDS_PROPRES_T2_KEUR = 250_000
FONDS_PROPRES_T3_KEUR = 250_000
SCR_TOTAL_KEUR = 3_069_039
MCR_KEUR = 1_381_068
RATIO_SCR_PCT = 198.20
RATIO_MCR_PCT = 404.24
PAGE_FONDS_PROPRES = 9

SCR_SOUSCRIPTION_NONVIE_KEUR = 0
SCR_DIVERSIFICATION_KEUR = -737_831
SCR_OPERATIONNEL_KEUR = 314_864
PAGE_SCR = 10


def construire_valeurs():
    valeurs = {}

    def m(keur):
        return keur / DIVISEUR_MONTANT

    valeurs["ratio_scr"] = (RATIO_SCR_PCT, PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe (scan) — ratio recoupé exact")
    valeurs["ratio_mcr"] = (RATIO_MCR_PCT, PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe — recoupé exact (auxiliaires T2/T3 exclus du MCR)")
    valeurs["scr_total"] = (m(SCR_TOTAL_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe — recoupé exact contre S.25.05.21 p.10 (R0220)")
    valeurs["mcr"] = (m(MCR_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe")
    valeurs["fonds_propres_eligibles"] = (m(FONDS_PROPRES_ELIGIBLES_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe — recoupé exact (somme des tiers)")
    valeurs["fonds_propres_t1_nr"] = (m(FONDS_PROPRES_T1_NR_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe")
    valeurs["fonds_propres_t1_r"] = (m(FONDS_PROPRES_T1_R_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe")
    valeurs["fonds_propres_t2"] = (m(FONDS_PROPRES_T2_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe (fonds propres auxiliaires)")
    valeurs["fonds_propres_t3"] = (m(FONDS_PROPRES_T3_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe (fonds propres auxiliaires)")

    be_total = sum(v for _, v in BE_COMPOSANTS)
    rm_total = sum(v for _, v in RM_COMPOSANTS)
    valeurs["best_estimate"] = (m(be_total), PAGE_BE_RM, "S.02.01.02, lecture visuelle directe (somme 5 lignes, recoupée exacte contre sous-totaux imprimés)")
    valeurs["marge_risque"] = (m(rm_total), PAGE_BE_RM, "S.02.01.02, lecture visuelle directe (somme 5 lignes, recoupée exacte)")
    valeurs["provisions_techniques"] = (m(be_total) + m(rm_total), PAGE_BE_RM, "best_estimate + marge_risque")

    primes_total = sum(v for _, v, _ in PRIMES_COMPOSANTS)
    sinistres_total = sum(v for _, v, _ in SINISTRES_COMPOSANTS)
    valeurs["primes_acquises_brutes"] = (m(primes_total), 5, "S.05.01.02, lecture visuelle directe (section non-vie vide, colonne Total vie p.5)")
    valeurs["charge_sinistres"] = (m(sinistres_total), 5, "S.05.01.02, lecture visuelle directe (section non-vie vide, colonne Total vie p.5)")

    valeurs["scr_operationnel"] = (m(SCR_OPERATIONNEL_KEUR), PAGE_SCR, "S.25.05.21, lecture visuelle directe — chaîne recoupée exacte (R0110+R0060=scr_total)")
    valeurs["scr_marche"] = (None, None, "fusionné avec scr_contrepartie dans le gabarit modèle interne S.25.05.21/R0070 (non séparable, jamais deviné)")
    valeurs["scr_contrepartie"] = (None, None, "fusionné avec scr_marche dans le gabarit modèle interne S.25.05.21/R0070 (non séparable, jamais deviné)")
    valeurs["scr_souscription_vie"] = (None, None, "fusionné avec scr_souscription_sante dans le gabarit modèle interne S.25.05.21/R0400 (non séparable, jamais deviné)")
    valeurs["scr_souscription_sante"] = (None, None, "fusionné avec scr_souscription_vie dans le gabarit modèle interne S.25.05.21/R0400 (non séparable, jamais deviné)")
    valeurs["scr_souscription_nonvie"] = (m(SCR_SOUSCRIPTION_NONVIE_KEUR), PAGE_SCR, "S.25.05.21/R0310, lecture visuelle directe (0, cohérent avec entité 100% vie)")
    valeurs["scr_diversification"] = (m(SCR_DIVERSIFICATION_KEUR), PAGE_SCR, "S.25.05.21/R0060, lecture visuelle directe — chaîne recoupée exacte")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec les autres sociétés)")

    composants_sommes = {
        "best_estimate": [(label, val, PAGE_BE_RM) for label, val in BE_COMPOSANTS],
        "marge_risque": [(label, val, PAGE_BE_RM) for label, val in RM_COMPOSANTS],
        "primes_acquises_brutes": PRIMES_COMPOSANTS,
        "charge_sinistres": SINISTRES_COMPOSANTS,
    }
    return valeurs, composants_sommes


def inserer_en_base(valeurs):
    conn = sqlite3.connect(DB_PATH)
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


def inserer_composants(company_id, composants_sommes):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    for kpi_name, composants in composants_sommes.items():
        conn.execute("DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?",
                     (company_id, YEAR, kpi_name))
        for i, (label, valeur_keur, page) in enumerate(composants, start=1):
            conn.execute(
                """INSERT INTO kpi_composants
                   (company_id, year, kpi_name, composant_index, composant_label,
                    composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
                   VALUES (?, ?, ?, ?, ?, NULL, ?, 'M€', ?, '+')""",
                (company_id, YEAR, kpi_name, i, label, valeur_keur / DIVISEUR_MONTANT, page),
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
    valeurs, composants_sommes = construire_valeurs()
    company_id, lignes_resume = inserer_en_base(valeurs)
    inserer_composants(company_id, composants_sommes)
    afficher_resume(lignes_resume)
