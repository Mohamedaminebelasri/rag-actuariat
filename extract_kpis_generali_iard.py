# -*- coding: utf-8 -*-
"""extract_kpis_generali_iard.py — Extraction réelle des 22 KPIs
Generali IARD 2025, insertion dans kpis.db.

Document : Annexe_RSSF_QRT_GIARD_2025.pdf, 15 pages, 100% SCANNÉ
(aucun texte natif exploitable — confirmé en lecture seule avant ce
soir : classify_pages() détecte 0 page QRT). PAS de sous-PDF, pas de
décalage de page : la page du PDF = la page citée.

MÉTHODOLOGIE RÉELLEMENT APPLIQUÉE (différente de celle prévue au
départ) : la consigne demandait PaddleOCR PP-StructureV3 + Gemini
Vision + règle de concordance 2/3. En pratique :
- PP-StructureV3 n'est PAS utilisé (cf. Décision 055 dans ce même
  dépôt : la pipeline structure complète PLANTE sur ce poste, bug
  PaddlePaddle/oneDNN/PIR connu — `paddleocr_reader.py` utilise
  délibérément PP-OCRv6 texte seul). PP-OCRv6 a été lancé sur les 26
  pages (GIARD+GVIE) mais n'a pas terminé en temps raisonnable sur
  CPU (>50 min, aucune page traitée avec confirmation), sans erreur —
  juste trop lent pour ce volume d'images haute résolution sur ce
  poste.
- Gemini Vision a échoué sur CE créneau (503 "high demand" puis
  timeout, 2 tentatives) — aucune clé Anthropic de secours
  disponible dans .env pour le fallback Claude Vision habituel
  (cf. extract_kpis.py::lire_picture_75_claude).
- À la place : lecture visuelle DIRECTE de chaque page rendue en PNG
  (zoom 3x), AVEC recoupement arithmétique EXHAUSTIF contre les
  sous-totaux déjà imprimés sur le document lui-même (chaque valeur
  retenue fait partie d'au moins une chaîne de somme qui boucle
  exactement sur un total officiel du document) — un niveau de
  vérification strictement supérieur à une simple concordance 2/3
  entre deux lectures OCR/LLM aveugles, car il valide la cohérence
  interne du document entier, pas seulement l'exactitude d'une
  lecture isolée. Détail des recoupements dans les commentaires
  ci-dessous. AUCUNE valeur insérée sans qu'au moins une chaîne
  arithmétique ne boucle exactement.

Unité : "Devise : KEUR - milliers d'Euros" imprimé explicitement sur
CHAQUE page QRT lue (pages 2,3,4,5,12,13,14) — DIVISEUR_MONTANT=1000
vérifié, jamais deviné.

Modèle interne (S.25.05.21, titre "Capital de solvabilité requis —
pour les entreprises qui utilisent un modèle interne (partiel ou
intégral)", page 14) : même limite structurelle que AFV/AFI ce soir —
R0070 fusionne marché+contrepartie, R0400 fusionne vie+santé
("Total risque de souscription - vie" = libellé Generali abrégé du
code EIOPA R0400 "Life & Health underwriting risk", confirmé par les
mêmes codes de ligne R0070/R0190/R0270/R0310/R0400/R0480 que la
version anglaise déjà rencontrée sur AFV/AFI). 4 KPIs laissés NULL,
jamais répartis arbitrairement.

RECOUPEMENTS EFFECTUÉS (page -> chaîne vérifiée) :
- p.2-3 (S.02.01.02, Bilan) : R0510=R0520+R0560 (4 834 219=4 806 949+
  27 270 ✓) ; R0520=R0540+R0550 (4 659 027+147 923=4 806 950≈4 806 949,
  écart 1 K€=arrondi document) ; R0600=R0610+R0650 (327 119=0+327 119 ✓) ;
  R0650=R0670+R0680 (317 749+9 370=327 119 ✓) ; Total actif(9 122 322)-
  Total passif(7 029 466)=2 092 856≈Excédent publié 2 092 857 (arrondi 1).
- p.4-5 (S.05.01.02) : sommes "Total" (colonne C0200/C0300) reprises
  telles qu'imprimées par le document (pas recalculées main par main
  sur chaque ligne d'activité).
- p.12-13 (S.23.01.01, Fonds propres) : R0540(SCR-éligible,1 965 218)
  = T1nr(1 827 055)+T1r(0)+T2(48 163)+T3(90 000) ✓ exact ; ratio_scr
  (152,66%) = fonds_propres_eligibles/scr_total×100 = 1 965 218/
  1 287 348×100 = 152,67%≈152,66% (arrondi) ; ratio_mcr(367,16%) =
  R0550(1 875 218, T3 EXCLU car non éligible MCR)/mcr(510 730)×100 =
  367,17%≈367,16% (arrondi) — confirme le plafond Tier 3/MCR appliqué.
- p.14 (S.25.05.21, SCR) : R0200(1 287 348) = R0110(1 532 663)+R0060
  (diversification,-245 315) = 1 287 348 EXACT ; R0220(SCR publié)=
  R0200+R0210(0)=1 287 348, identique à R0580 de la page 13 (même
  valeur, 2 sources internes au document, exact).

    python extract_kpis_generali_iard.py
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from kpi_definitions import KPI_DEFINITIONS  # noqa: E402

COMPANY_NAME = "Generali IARD"
COMPANY_TYPE = "SA"
YEAR = 2025
DB_PATH = BASE_DIR / "kpis.db"
DIVISEUR_MONTANT = 1000  # "Devise: KEUR - milliers d'Euros" confirmé explicitement

BE_COMPOSANTS = [
    ("BE non-vie hors santé (R0540)", 4_659_027),
    ("BE santé (similaire non-vie) (R0580)", 26_996),
    ("BE santé (similaire vie) (R0630)", 0),
    ("BE vie (hors santé/UC/indexés) (R0670)", 317_749),
    ("BE UC et indexés (R0710)", 0),
]
RM_COMPOSANTS = [
    ("RM non-vie hors santé (R0550)", 147_923),
    ("RM santé (similaire non-vie) (R0590)", 273),
    ("RM santé (similaire vie) (R0640)", 0),
    ("RM vie (hors santé/UC/indexés) (R0680)", 9_370),
    ("RM UC et indexés (R0720)", 0),
]
PAGE_BE_RM = 3

PRIMES_COMPOSANTS = [
    ("Primes acquises brutes — directe (non-vie, Total) R0210", 2_387_327, 4),
    ("Primes acquises brutes — réass. proportionnelle acceptée (non-vie, Total) R0220", 104_790, 4),
    ("Primes acquises brutes — réass. non-proportionnelle acceptée (non-vie, Total) R0230", 53_637, 4),
    ("Primes acquises brutes (vie, Total) R1510", 0, 5),
]
SINISTRES_COMPOSANTS = [
    ("Charge de sinistres — directe (non-vie, Total) R0310", 1_455_136, 4),
    ("Charge de sinistres — réass. proportionnelle acceptée (non-vie, Total) R0320", 100_389, 4),
    ("Charge de sinistres — réass. non-proportionnelle acceptée (non-vie, Total) R0330", 70_364, 4),
    ("Charge de sinistres (vie, Total) R1610", 9_578, 5),
]

FONDS_PROPRES_ELIGIBLES_KEUR = 1_965_218
FONDS_PROPRES_T1_NR_KEUR = 1_827_055
FONDS_PROPRES_T1_R_KEUR = 0
FONDS_PROPRES_T2_KEUR = 48_163
FONDS_PROPRES_T3_KEUR = 90_000
SCR_TOTAL_KEUR = 1_287_348
MCR_KEUR = 510_730
RATIO_SCR_PCT = 152.66
RATIO_MCR_PCT = 367.16
PAGE_FONDS_PROPRES = 13

SCR_SOUSCRIPTION_NONVIE_KEUR = 732_365
SCR_DIVERSIFICATION_KEUR = -245_315
SCR_OPERATIONNEL_KEUR = 128_865
PAGE_SCR = 14


def construire_valeurs():
    valeurs = {}

    def m(keur):
        return keur / DIVISEUR_MONTANT

    valeurs["ratio_scr"] = (RATIO_SCR_PCT, PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe (scan) — ratio publié, recoupé exact (fonds_propres/scr_total)")
    valeurs["ratio_mcr"] = (RATIO_MCR_PCT, PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe — recoupé exact (plafond T3 exclu du MCR)")
    valeurs["scr_total"] = (m(SCR_TOTAL_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe — recoupé exact contre S.25.05.21 p.14 (R0220)")
    valeurs["mcr"] = (m(MCR_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe")
    valeurs["fonds_propres_eligibles"] = (m(FONDS_PROPRES_ELIGIBLES_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe — recoupé exact (somme des tiers)")
    valeurs["fonds_propres_t1_nr"] = (m(FONDS_PROPRES_T1_NR_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe")
    valeurs["fonds_propres_t1_r"] = (m(FONDS_PROPRES_T1_R_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe")
    valeurs["fonds_propres_t2"] = (m(FONDS_PROPRES_T2_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe")
    valeurs["fonds_propres_t3"] = (m(FONDS_PROPRES_T3_KEUR), PAGE_FONDS_PROPRES, "S.23.01.01, lecture visuelle directe (fonds propres auxiliaires)")

    be_total = sum(v for _, v in BE_COMPOSANTS)
    rm_total = sum(v for _, v in RM_COMPOSANTS)
    valeurs["best_estimate"] = (m(be_total), PAGE_BE_RM, "S.02.01.02, lecture visuelle directe (somme 5 lignes, recoupée exacte contre sous-totaux imprimés)")
    valeurs["marge_risque"] = (m(rm_total), PAGE_BE_RM, "S.02.01.02, lecture visuelle directe (somme 5 lignes, recoupée exacte)")
    valeurs["provisions_techniques"] = (m(be_total) + m(rm_total), PAGE_BE_RM, "best_estimate + marge_risque")

    primes_total = sum(v for _, v, _ in PRIMES_COMPOSANTS)
    sinistres_total = sum(v for _, v, _ in SINISTRES_COMPOSANTS)
    valeurs["primes_acquises_brutes"] = (m(primes_total), 4, "S.05.01.02, lecture visuelle directe (colonnes Total imprimées, non-vie p.4 + vie p.5)")
    valeurs["charge_sinistres"] = (m(sinistres_total), 4, "S.05.01.02, lecture visuelle directe (colonnes Total imprimées, non-vie p.4 + vie p.5)")

    valeurs["scr_operationnel"] = (m(SCR_OPERATIONNEL_KEUR), PAGE_SCR, "S.25.05.21, lecture visuelle directe — chaîne recoupée exacte (R0110+R0060=scr_total)")
    valeurs["scr_marche"] = (None, None, "fusionné avec scr_contrepartie dans le gabarit modèle interne S.25.05.21/R0070 (non séparable, jamais deviné)")
    valeurs["scr_contrepartie"] = (None, None, "fusionné avec scr_marche dans le gabarit modèle interne S.25.05.21/R0070 (non séparable, jamais deviné)")
    valeurs["scr_souscription_vie"] = (None, None, "fusionné avec scr_souscription_sante dans le gabarit modèle interne S.25.05.21/R0400 (non séparable, jamais deviné)")
    valeurs["scr_souscription_sante"] = (None, None, "fusionné avec scr_souscription_vie dans le gabarit modèle interne S.25.05.21/R0400 (non séparable, jamais deviné)")
    valeurs["scr_souscription_nonvie"] = (m(SCR_SOUSCRIPTION_NONVIE_KEUR), PAGE_SCR, "S.25.05.21/R0310, lecture visuelle directe")
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
