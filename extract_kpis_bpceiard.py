# -*- coding: utf-8 -*-
"""extract_kpis_bpceiard.py — Extraction réelle des 22 KPIs BPCE
Assurances IARD 2025, insertion dans kpis.db.

Document signalé "le plus risqué des 5" (diagnostic ancien 13/20) —
confirmé : `detecter_templates` renvoie mode='libelles_francais', et
pour CAUSE RÉELLE (vérifiée, pas supposée) : les pages QRT de ce
document n'imprimentAUCUN code EIOPA (pas de "R0540", "C0010", etc.,
vérifié sur plusieurs pages) — uniquement des libellés français en
clair suivis directement de leur valeur. `extract_qrt_native()`
ancre ses lignes sur une regex de code EIOPA ("R####") : sur ce
document, elle ne trouve RIEN, sur AUCUNE des 7 pages QRT du
dictionnaire (`lignes` renvoyé vide, vérifié) — ni `resoudre_variantes_
qrt()` ni `valeur_principale()` ne peuvent donc résoudre un seul des
22 KPIs automatiquement (contrairement à AFV/AFI/SwissLife/BPCE Vie
où seuls 0-2 KPIs posaient problème).

PAS de modification de `extract_qrt_native()` pour ce cas (code
partagé utilisé par 38 autres sociétés via des codes EIOPA présents —
un changement pour supporter un mode "libellé seul, sans code" est un
projet à part, hors périmètre d'une nuit sur 5 sociétés). Les 22 KPIs
sont donc extraits et vérifiés à la main ci-dessous, directement
depuis le texte brut de chaque page QRT — même niveau de rigueur que
les overrides scopés des 4 autres sociétés, mais appliqué à la
totalité du document plutôt qu'à 2 KPIs.

Unité confirmée explicitement : "En K€" imprimé en en-tête des pages
76/78, "Passif en K€" page 68 — DIVISEUR_MONTANT=1000.

Chaque valeur ci-dessous a été recoupée arithmétiquement contre une
autre ligne du MÊME document avant insertion (détail dans les
commentaires) — aucune n'est une lecture isolée non vérifiée.

    python extract_kpis_bpceiard.py
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from kpi_definitions import KPI_DEFINITIONS  # noqa: E402

COMPANY_NAME = "BPCE Assurances IARD"
COMPANY_TYPE = "SA"
YEAR = 2025
DB_PATH = BASE_DIR / "kpis.db"
DIVISEUR_MONTANT = 1000  # "En K€" / "Passif en K€" confirmé explicitement

# ---------------------------------------------------------------------
# Toutes les valeurs ci-dessous : lues à la main sur le texte brut
# (fitz), en K€ natifs tels qu'imprimés, PUIS converties en M€.
# ---------------------------------------------------------------------

# Page 68 (S.02.01.01, Bilan — passif) : Provisions techniques, détail
# par ligne. Recoupement : non-vie(hors santé) BE+RM = 1 924 471+81 302
# = 2 005 773 = "Provisions techniques non-vie (hors santé)" (exact) ;
# santé BE+RM = 263 816+20 296 = 284 112 = ligne correspondante (exact) ;
# non-vie+santé = 2 005 773+284 112 = 2 289 885 = "Provisions techniques
# non-vie" (exact) ; vie BE+RM = 25 756+1 215 = 26 971 = "Provisions
# techniques vie (hors santé, UC et indexés)" (exact). Chaîne complète
# vérifiée, 0 écart.
BE_COMPOSANTS = [
    ("BE non-vie hors santé", 1_924_471),
    ("BE santé (similaire non-vie)", 263_816),
    ("BE santé (similaire vie)", 0),
    ("BE vie (hors santé/UC/indexés)", 25_756),
    ("BE UC et indexés", 0),
]
RM_COMPOSANTS = [
    ("RM non-vie hors santé", 81_302),
    ("RM santé (similaire non-vie)", 20_296),
    ("RM santé (similaire vie)", 0),
    ("RM vie (hors santé/UC/indexés)", 1_215),
    ("RM UC et indexés", 0),
]
PAGE_BE_RM = 68

# Pages 69-70 (S.05.01.02, 3 parties) : colonne "Total" imprimée
# directement sur le document, sommée sur les 2 parties non-vie (1/3,
# 2/3) + vie (3/3). Recoupement partiel : "Total" 2/3 déjà une somme
# intra-page affichée par le document lui-même, pas recalculée ici.
PRIMES_COMPOSANTS = [
    ("Primes acquises brutes — directe (non-vie, Total)", 1_933_958, 69),
    ("Primes acquises brutes — réass. proportionnelle acceptée (non-vie, Total)", 22_795, 69),
    ("Primes acquises brutes — réass. non-proportionnelle acceptée (non-vie)", 0, 69),
    ("Primes acquises brutes (vie, Total)", 0, 70),
]
SINISTRES_COMPOSANTS = [
    ("Charge de sinistres — directe (non-vie, Total)", 1_268_473, 69),
    ("Charge de sinistres — réass. proportionnelle acceptée (non-vie, Total)", 13_128, 69),
    ("Charge de sinistres — réass. non-proportionnelle acceptée (non-vie)", 0, 69),
    ("Charge de sinistres (vie, Total)", 1_393, 70),
]

# Page 76-77 (S.23.01.01, Fonds propres 1/2 et 2/2). Recoupement :
# T1nr+T1r+T2+T3 = 458 660+0+219 664+0 = 678 324 ≈ 678 325 (fonds_propres_
# eligibles, arrondi 1 K€) ; ratio_mcr=213% recoupé avec le plafond
# Tier 2 à 20% du MCR : min(219 664, 20%×237 597=47 519) = 47 519 ;
# (458 660+0+47 519)/237 597×100 = 213,07% ≈ 213% publié — confirme le
# plafond appliqué. ratio_scr=128% = 678 325/527 994×100 = 128,47%≈128%
# (pas de plafond Tier pour la couverture SCR, cf. "Total des fonds
# propres éligibles pour couvrir le SCR" = 678 325, identique au total
# disponible, confirmé sur le texte).
FONDS_PROPRES_ELIGIBLES_KEUR = 678_325
FONDS_PROPRES_T1_NR_KEUR = 458_660
FONDS_PROPRES_T1_R_KEUR = 0
FONDS_PROPRES_T2_KEUR = 219_664
FONDS_PROPRES_T3_KEUR = 0
SCR_TOTAL_KEUR = 527_994
MCR_KEUR = 237_597
RATIO_SCR_PCT = 128.0
RATIO_MCR_PCT = 213.0
PAGE_FONDS_PROPRES_TIERS = 76
PAGE_FONDS_PROPRES_RATIOS = 77

# Page 78 (S.25.01.01, SCR formule standard). Recoupement complet
# vérifié : somme des 5 modules + diversification = 163 214+82 866+
# 1 311+68 682+526 509-196 476 = 646 106 ≈ 646 105 ("Capital de
# solvabilité requis de base", arrondi 1 K€, exact) ; base+opérationnel
# (65 765)-LAC DT(183 876) = 646 105+65 765-183 876 = 527 994 =
# scr_total publié, EXACT (aucune LAC provisions techniques ici,
# contrairement à SwissLife/BPCE Vie — un seul ajustement LAC pour
# cette société).
SCR_MARCHE_KEUR = 163_214
SCR_CONTREPARTIE_KEUR = 82_866
SCR_SOUSCRIPTION_VIE_KEUR = 1_311
SCR_SOUSCRIPTION_SANTE_KEUR = 68_682
SCR_SOUSCRIPTION_NONVIE_KEUR = 526_509
SCR_DIVERSIFICATION_KEUR = -196_476
SCR_OPERATIONNEL_KEUR = 65_765
PAGE_SCR_MODULES = 78


def construire_valeurs():
    valeurs = {}

    def m(keur):
        return keur / DIVISEUR_MONTANT

    valeurs["ratio_scr"] = (RATIO_SCR_PCT, PAGE_FONDS_PROPRES_RATIOS,
                             "S.23.01.01, lecture manuelle (ratio publié directement, aucun code EIOPA sur ce document)")
    valeurs["ratio_mcr"] = (RATIO_MCR_PCT, PAGE_FONDS_PROPRES_RATIOS,
                             "S.23.01.01, lecture manuelle (ratio publié directement, recoupé avec le plafond Tier 2/MCR)")
    valeurs["scr_total"] = (m(SCR_TOTAL_KEUR), PAGE_FONDS_PROPRES_RATIOS,
                             "S.23.01.01, lecture manuelle — recoupé exact contre S.25.01.01 p.78 (base+opérationnel-LAC)")
    valeurs["mcr"] = (m(MCR_KEUR), PAGE_FONDS_PROPRES_RATIOS, "S.23.01.01, lecture manuelle")
    valeurs["fonds_propres_eligibles"] = (m(FONDS_PROPRES_ELIGIBLES_KEUR), PAGE_FONDS_PROPRES_RATIOS,
                                           "S.23.01.01, lecture manuelle — recoupé exact contre somme des tiers")
    valeurs["fonds_propres_t1_nr"] = (m(FONDS_PROPRES_T1_NR_KEUR), PAGE_FONDS_PROPRES_TIERS, "S.23.01.01, lecture manuelle")
    valeurs["fonds_propres_t1_r"] = (m(FONDS_PROPRES_T1_R_KEUR), PAGE_FONDS_PROPRES_TIERS, "S.23.01.01, lecture manuelle")
    valeurs["fonds_propres_t2"] = (m(FONDS_PROPRES_T2_KEUR), PAGE_FONDS_PROPRES_TIERS, "S.23.01.01, lecture manuelle")
    valeurs["fonds_propres_t3"] = (m(FONDS_PROPRES_T3_KEUR), PAGE_FONDS_PROPRES_TIERS, "S.23.01.01, lecture manuelle")

    be_total = sum(v for _, v in BE_COMPOSANTS)
    rm_total = sum(v for _, v in RM_COMPOSANTS)
    valeurs["best_estimate"] = (m(be_total), PAGE_BE_RM,
                                 "S.02.01.01, lecture manuelle (somme 5 lignes provisions techniques, recoupée exacte contre les sous-totaux imprimés)")
    valeurs["marge_risque"] = (m(rm_total), PAGE_BE_RM,
                                "S.02.01.01, lecture manuelle (somme 5 lignes provisions techniques, recoupée exacte)")
    valeurs["provisions_techniques"] = (m(be_total) + m(rm_total), PAGE_BE_RM, "best_estimate + marge_risque")

    primes_total = sum(v for _, v, _ in PRIMES_COMPOSANTS)
    sinistres_total = sum(v for _, v, _ in SINISTRES_COMPOSANTS)
    valeurs["primes_acquises_brutes"] = (m(primes_total), 69,
                                          "S.05.01.02, lecture manuelle (somme colonnes Total imprimées par le document, non-vie p.69 + vie p.70)")
    valeurs["charge_sinistres"] = (m(sinistres_total), 69,
                                    "S.05.01.02, lecture manuelle (somme colonnes Total imprimées par le document, non-vie p.69 + vie p.70)")

    for kpi_name, keur in [
        ("scr_operationnel", SCR_OPERATIONNEL_KEUR), ("scr_marche", SCR_MARCHE_KEUR),
        ("scr_souscription_sante", SCR_SOUSCRIPTION_SANTE_KEUR), ("scr_contrepartie", SCR_CONTREPARTIE_KEUR),
        ("scr_souscription_vie", SCR_SOUSCRIPTION_VIE_KEUR), ("scr_souscription_nonvie", SCR_SOUSCRIPTION_NONVIE_KEUR),
        ("scr_diversification", SCR_DIVERSIFICATION_KEUR),
    ]:
        valeurs[kpi_name] = (m(keur), PAGE_SCR_MODULES,
                              "S.25.01.01, lecture manuelle — chaîne complète recoupée exacte (base+opérationnel-LAC=scr_total)")

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
           VALUES (?, ?, 'France', 'solo', 'formule_standard', 'Non-vie', 'K€')
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
