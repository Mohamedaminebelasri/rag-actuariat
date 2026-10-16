# -*- coding: utf-8 -*-
"""validate_kpis.py — Contrôles actuariels sur les KPIs déjà extraits dans
kpis.db (Phase 3.4, Décision 052 ; généralisé à toutes les sociétés,
Décision 090). Écrit chaque résultat dans validation_checks (jamais
silencieux), et met à jour kpis.validated=1 pour les KPIs qui passent au
moins 1 contrôle qui les concerne directement.

CONTRÔLES RETENUS — uniquement des identités/inégalités dont la vérité est
certaine (pas une formule actuarielle incertaine ou approximative), TOUS
génériques (lisent uniquement les KPIs de la société en cours, jamais une
valeur ou un nom d'entreprise codé en dur) sauf mention contraire ci-dessous :
1. provisions_techniques = best_estimate + marge_risque (identité de
   construction, cf. extract_kpis.py — doit TOUJOURS passer, garde-fou de
   non-régression). Skippé si un des 3 KPIs est NULL.
2. fonds_propres_eligibles = somme des 4 tiers (identité de construction).
   Skippé si un des 5 KPIs est NULL.
3. ratio_scr recalculé (fonds_propres_eligibles / scr_total × 100) vs
   ratio_scr publié — tolérance 1% (le ratio publié dans le SFCR n'a que
   2 décimales de précision, cf. "2,74" en source, un recalcul depuis les
   montants complets peut différer légèrement de l'arrondi publié).
4. ratio_mcr recalculé — RESTE SPÉCIFIQUE À GROUPAMA (Décision 090) : le
   numérateur (R0570, fonds propres éligibles pour le MCR — un concept
   DIFFÉRENT de fonds_propres_eligibles/R0540, pas dans les 22 KPIs
   stockés) n'est disponible que via `corpus_final.json`, qui n'existe
   QUE pour Groupama (extraction Docling dédiée) — pour toute autre
   société, aucune source indépendante du numérateur MCR-éligible n'est
   capturée nulle part (ni en base, ni dans un fichier), donc ce contrôle
   ne peut pas être généralisé sans deviner une valeur. Skippé proprement
   (jamais un numérateur approximé) pour toute société sans source
   enregistrée — cf. `SOURCES_MCR_INDEPENDANTES`, registre extensible
   plutôt qu'un `if company_name == "Groupama"` littéral.
5. mcr < scr_total — invariant Solvabilité II de base (le MCR est un
   plancher SOUS le SCR). PAS le corridor réglementaire 25%-45% de
   l'article 129 : ce corridor est défini pour les entités SOLO, pas
   garanti identique pour un MCR consolidé groupe — ne pas l'affirmer
   sans être sûr que la définition s'applique telle quelle au niveau
   groupe (cf. limite déjà documentée dans CLAUDE.md/src/, décisions 014-015
   sur le MCR solo). Skippé si mcr ou scr_total est NULL.
6/7. Croisements SCR — RESTENT SPÉCIFIQUES À GROUPAMA (Décision 090,
   analyse détaillée) : la tentative de généraliser ces 2 contrôles via
   une identité générique "somme des 7 composantes SCR ≈ scr_total"
   (calculable pour toute société depuis kpis.db seul) a été testée
   empiriquement AVANT adoption — REJETÉE après avoir produit des écarts
   énormes et non liés à une erreur d'extraction, y compris sur MACIF SAM
   (22%, pourtant triple-vérifiée, Décision 083), Predica (281%), CNP
   (193%), Aéma Groupe (149%) : le SCR final inclut des ajustements LAC
   DT/LAC TP (capacité d'absorption des pertes par les impôts différés/
   les provisions techniques) qui peuvent être TRÈS matériels et NE SONT
   PAS capturés dans les 22 KPIs stockés — une société parfaitement bien
   extraite peut légitimement avoir un écart de plusieurs dizaines de %
   entre la somme des composantes et le SCR final. Forcer cette identité
   comme contrôle aurait produit une majorité de FAUX échecs plutôt que
   de vrais signaux — contraire à la règle "jamais un signal trompeur".
   Les 2 contrôles restent donc les croisements originaux de Décision 051
   (valeurs codées en dur, vérifiées manuellement pour Groupama
   uniquement), skippés proprement pour toute autre société — cf.
   `CROISEMENTS_GROUPAMA`.
8. Signe de chaque KPI non-NULL conforme à kpi_definitions.py (sign
   "positive"/"negative"/"any") — 1 contrôle par KPI concerné. Décision
   090 : `positive` accepte désormais `>= 0` (pas seulement `> 0`) et
   `negative` accepte `<= 0` — plusieurs sociétés ont légitimement des
   tiers de fonds propres ou des composantes SCR à exactement 0,00
   (ex. fonds_propres_t3/scr_souscription_nonvie pour Predica/MGEN,
   Décision 085/088) ; un vrai 0 n'est ni positif ni négatif au sens
   strict, mais n'est pas non plus un signe erroné.
9. Complétude : exactement N lignes pour (entreprise, année), où N =
   len(KPI_DEFINITIONS), et aucun NULL attendu par défaut (Décision 144 —
   resultat_technique supprimé du référentiel, cf. kpi_definitions.py).
   Contrôle VOLONTAIREMENT NON assoupli (Décision 090) : certaines
   sociétés (ex. SGAM AG2R LA MONDIALE) échoueront légitimement ici —
   c'est un vrai signal de complétude (documenté Décision 087), pas un
   faux positif à cacher.
10. Magnitude (Décision 095) — 1 contrôle par KPI en M€ non-NULL : la
    valeur absolue ne dépasse pas un plafond conservateur selon sa
    catégorie (cf. SEUILS_MAGNITUDE). Objectif : détecter les bugs
    d'ordre de grandeur (unité confondue, double-comptage) qui restaient
    invisibles à TOUS les contrôles ci-dessus — les contrôles 1-4 sont
    des RATIOS entre 2 KPIs de la MÊME société (une erreur qui affecte
    les 2 KPIs dans les mêmes proportions passe inaperçue, cf. Décision
    094 : le bug ×1000 des 7 entités Aéma préservait exactement
    ratio_scr/ratio_mcr recalculés, donc les contrôles 3/4 passaient).
    Seuils choisis avec une marge large (~2-3×) au-dessus du maximum
    RÉEL actuellement observé sur les 28 sociétés (cf. Décision 095 pour
    le détail des maximums mesurés) — pas une limite théorique abstraite
    (le PIB français, ~2 800 Md€, est trop large pour la plupart des
    KPIs : n'aurait pas détecté le bug ×1000 sur scr_total des entités
    Aéma, resté sous ce seuil). PAS un contrôle magique : un facteur ×2
    à ×4 sur un KPI déjà petit (ex. Groupama/MGEN primes_acquises_
    brutes, Décision 093) reste indétectable par un simple plafond —
    limite assumée, documentée, pas cachée.

12. Lignes de primes et de sinistres du S/P non-vie (Décision 159) —
    relues dans le texte de leur page source PDF, cf. `controler_sp_nonvie`.
    N'agit sur aucun des 21 KPIs extraits : sert à la validité des
    composants du KPI calculé sp_nonvie (peupler_kpis_officiels_indicateurs.py).
    Lecture des PDF : PyMuPDF, donc lancer avec le Python du .venv.

    python validate_kpis.py [--company Groupama] [--year 2025]
    python validate_kpis.py --all   # toutes les sociétés de companies
    .venv/Scripts/python.exe -I validate_kpis.py --all   # avec le contrôle 12
"""

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "kpis.db"
CORPUS_FINAL = BASE_DIR / "test_markdrop" / "output_structure_brute" / "corpus_final.json"

sys.path.insert(0, str(BASE_DIR))
import comparabilite
from kpi_definitions import KPI_DEFINITIONS

try:  # contrôle 12 seulement (PyMuPDF n'est installé que dans le .venv)
    import pymupdf as fitz
except ImportError:
    try:
        import fitz
    except ImportError:
        fitz = None

NOMS_KPIS_EXTRAITS = {d["kpi_name"] for d in KPI_DEFINITIONS}
_FILTRE_EXTRAITS = "kpi_name IN ({})".format(",".join(f"'{n}'" for n in sorted(NOMS_KPIS_EXTRAITS)))

TOLERANCE_PCT_RATIO = 1.0  # % — cf. docstring, contrôles 3/4
TOLERANCE_ABS_IDENTITE = 0.5  # M€ — arrondis flottants, contrôles 1/2


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--company", default="Groupama")
    p.add_argument("--year", type=int, default=2025)
    p.add_argument("--all", action="store_true", help="Lance sur toutes les sociétés de companies (ignore --company)")
    return p.parse_args()


def charger_kpis(conn, company_id, year):
    lignes = conn.execute(
        "SELECT kpi_name, value, unit FROM kpis WHERE company_id=? AND year=?",
        (company_id, year),
    ).fetchall()
    # Décision 158 — seulement les 21 KPIs extraits : les KPIs calculés
    # (KPI_INDICATEURS_OFFICIELS) ont leur propre contrôle de recalcul.
    return {nom: (valeur, unite) for nom, valeur, unite in lignes if nom in NOMS_KPIS_EXTRAITS}


def r0570_eligibles_mcr():
    """Relu directement depuis corpus_final.json — PAS stocké comme KPI
    séparé (les 22 KPIs demandés ne l'incluent pas), nécessaire uniquement
    pour le contrôle 4 (recalcul du ratio_mcr). N'existe QUE pour Groupama
    (seule société avec un corpus_final.json Docling dédié) — cf.
    SOURCES_MCR_INDEPENDANTES et le commentaire en tête de fichier."""
    with open(CORPUS_FINAL, encoding="utf-8") as f:
        corpus = json.load(f)["elements"]
    for e in corpus:
        if e.get("template_id") == "S.23.01.22.01":
            row = e["contenu"]["lignes"]["R0570"]
            assert "Total eligible own funds to meet the minimum consolidated group SCR" in row["libelle_officiel"]
            return float(row["valeurs"]["C0010"]["valeur_brute"]) / 1000  # M€
    raise RuntimeError("S.23.01.22.01/R0570 introuvable")


# Décision 090 : registre (pas un `if company_name == "Groupama"` en ligne)
# des sociétés pour lesquelles une source MCR-éligible indépendante du KPI
# stocké est disponible — aujourd'hui, seule Groupama (via
# corpus_final.json). Extensible : ajouter une entrée ici suffit à activer
# le contrôle 4 pour une nouvelle société, SI sa source existe réellement
# (jamais une valeur approximée pour remplir le registre).
SOURCES_MCR_INDEPENDANTES = {
    "Groupama": r0570_eligibles_mcr,
}

# Décision 090 : croisements SCR codés en dur, vérifiés manuellement
# UNIQUEMENT pour Groupama (Décision 051) — voir le commentaire en tête de
# fichier pour l'analyse de pourquoi une généralisation générique (somme
# des composantes SCR) a été testée puis rejetée (faux échecs massifs, pas
# liés à des erreurs d'extraction). Registre extensible de la même façon
# que SOURCES_MCR_INDEPENDANTES.
CROISEMENTS_GROUPAMA = {
    "Groupama": {
        "scr_total": (6_020_977 / 1000, "S.23.01.22.01/R0680 vs S.25.05.22.02/R0220 (codé en dur, cf. Décision 051) — déjà croisés à l'extraction"),
        "scr_souscription_nonvie": (2_474_794 / 1000, "S.25.05.22.01/R0310 vs relecture manuelle vérifiée picture_75.png — déjà croisés à l'extraction"),
    },
}


# Décision 095 — plafonds de magnitude, en M€, par catégorie de KPI.
# Choisis avec une marge ~2-3× au-dessus du maximum RÉEL mesuré sur les 28
# sociétés en base au moment de l'écriture de ce contrôle (vérifié par
# requête directe sur kpis.db, pas deviné) :
#   - SCR/MCR/fonds propres/primes/sinistres/composantes SCR : max réel
#     49 173 M€ (primes_acquises_brutes, Crédit Agricole Assurances,
#     groupe) -> plafond 100 000 M€.
#   - best_estimate/marge_risque/provisions_techniques : structurellement
#     bien plus grands (provisions actuarielles vie, pas des flux annuels)
#     — max réel 283 474 M€ (provisions_techniques, CNP Assurances) ->
#     plafond 1 000 000 M€ (1 000 Md€), un ordre de grandeur au-dessus,
#     encore loin sous le PIB français (~2 800 Md€) pour ne jamais
#     confondre un vrai grand assureur avec un bug d'unité.
PLAFOND_MONTANT_STANDARD = 100_000.0  # M€
PLAFOND_MONTANT_PROVISIONS = 1_000_000.0  # M€

KPIS_MONTANT_STANDARD = {
    "scr_total", "mcr", "fonds_propres_eligibles", "fonds_propres_t1_nr",
    "fonds_propres_t1_r", "fonds_propres_t2", "fonds_propres_t3",
    "primes_acquises_brutes", "charge_sinistres",
    "scr_marche", "scr_contrepartie", "scr_souscription_vie",
    "scr_souscription_sante", "scr_souscription_nonvie",
    "scr_diversification", "scr_operationnel",
}
KPIS_MONTANT_PROVISIONS = {"best_estimate", "marge_risque", "provisions_techniques"}

SEUILS_MAGNITUDE = {
    **{k: PLAFOND_MONTANT_STANDARD for k in KPIS_MONTANT_STANDARD},
    **{k: PLAFOND_MONTANT_PROVISIONS for k in KPIS_MONTANT_PROVISIONS},
}

# Décision 107 — plancher, symétrique du plafond ci-dessus : le plafond
# détecte une erreur d'unité ÷1000 au lieu de ÷1 000 000 (valeur ×1000
# trop GRANDE, cas réel Décision 094) mais est aveugle à l'erreur inverse
# (÷1 000 000 au lieu de ÷1000, valeur ×1000 trop PETITE) — un risque
# nouveau depuis l'auto-détection d'unité à 2 sens d'extraire_un_pdf.py
# (une détection qui se trompe dans CE sens produirait un scr_total/
# fonds_propres_eligibles anormalement bas, jamais vu jusqu'ici car le
# diviseur était jusqu'alors toujours fixé en dur par société après
# vérification manuelle). Scopé à seulement 2 KPIs (scr_total,
# fonds_propres_eligibles) — les 2 seuls TOUJOURS strictement positifs et
# significatifs pour un assureur réel, contrairement à scr_diversification
# (peut être proche de 0) ou fonds_propres_t3 (souvent 0 ou absent) qui
# généreraient de faux positifs. Seuil 0,5 M€ vérifié sans aucun faux
# positif sur les 34 sociétés actuelles (plus petite valeur réelle :
# Themis scr_total=1,055 M€, fonds_propres_eligibles=9,428 M€ — marge
# ≥2× sur le KPI le plus bas, largement plus sur l'autre).
PLANCHER_MONTANT = 0.5  # M€
KPIS_MONTANT_PLANCHER = {"scr_total", "fonds_propres_eligibles"}

# Diagnostic 12/10/2026, Problèmes 2-4 — registre extensible (même esprit que
# CROISEMENTS_GROUPAMA) des échecs déjà vérifiés manuellement et jugés
# légitimes : ils continuent d'échouer "techniquement" (passed=0, c'est la
# réalité du calcul) mais ne doivent plus être confondus avec un vrai bug non
# investigué dans le résumé --all. Clé (company_name, check_name).
ECHECS_LEGITIMES_CONNUS = {
    ("Macifilia", "signe_charge_sinistres"): (
        "Reprise de provision vérifiée pixel par pixel (Décision 094, "
        "addendum 2026-09-26) : page 511, R0310=-939 552 confirmé exact, "
        "R0340 (part réassureur) identique -> R0400 (Net)=0, ligne "
        "intégralement réassurée. Signe négatif économiquement cohérent, "
        "pas une erreur d'extraction."
    ),
    ("Macifilia", "mcr_inferieur_scr_total"): (
        "Plancher MCR absolu sur petite structure, déjà documenté "
        "(Décision 085)."
    ),
    ("Themis", "mcr_inferieur_scr_total"): (
        "Plancher MCR absolu sur petite structure, déjà documenté "
        "(Décision 085)."
    ),
    # Décision 150 — modèles internes complets : le risque de souscription
    # santé n'existe pas comme catégorie séparée, il est inclus dans
    # scr_souscription_vie (vie ET santé) ; scr_souscription_sante reste
    # NULL par construction, jamais deviné.
    **{(societe, "completude_aucun_null"): (
        "Seul NULL : scr_souscription_sante, inclus dans scr_souscription_vie "
        "(modèle interne complet sans catégorie santé séparée, Décision 150)."
    ) for societe in ("AXA France Vie", "AXA France IARD", "Generali Vie", "Generali IARD", "Allianz Vie")},
}


def executer_controles(kpis, company_name):
    """Retourne une liste de dicts {check_name, expected_value,
    computed_value, passed, details}. Générique (Décision 090) : chaque
    contrôle qui a besoin d'un KPI absent/NULL pour cette société est
    SKIPPÉ proprement (rien inséré) plutôt que de planter ou de calculer
    sur None — cf. `valeurs()` ci-dessous."""
    controles = []

    def ajouter(nom, attendu, calcule, passe, details):
        controles.append({
            "check_name": nom, "expected_value": attendu, "computed_value": calcule,
            "passed": passe, "details": details,
        })

    def valeurs(*noms):
        """Retourne les valeurs de `noms` si TOUTES sont présentes et
        non-NULL pour cette société, sinon None (signal pour skipper le
        contrôle appelant plutôt que de lever une exception sur un KPI
        absent — cas réel : sociétés Aéma/AG2R avec des NULL au-delà de
        resultat_technique, cf. Décisions 087/089)."""
        sortie = []
        for nom in noms:
            paire = kpis.get(nom)
            if paire is None or paire[0] is None:
                return None
            sortie.append(paire[0])
        return sortie

    # --- 1. provisions_techniques = best_estimate + marge_risque ---
    v = valeurs("best_estimate", "marge_risque", "provisions_techniques")
    if v is not None:
        be, rm, pt = v
        attendu = be + rm
        ecart = abs(attendu - pt)
        ajouter("provisions_techniques_somme", attendu, pt, ecart <= TOLERANCE_ABS_IDENTITE,
                 f"best_estimate({be:.2f}) + marge_risque({rm:.2f}) = {attendu:.2f} vs provisions_techniques={pt:.2f}, écart={ecart:.4f} M€")

    # --- 2. fonds_propres_eligibles = somme des 4 tiers ---
    v = valeurs("fonds_propres_t1_nr", "fonds_propres_t1_r", "fonds_propres_t2", "fonds_propres_t3", "fonds_propres_eligibles")
    fp = None
    if v is not None:
        t1nr, t1r, t2, t3, fp = v
        attendu = t1nr + t1r + t2 + t3
        ecart = abs(attendu - fp)
        ajouter("fonds_propres_eligibles_somme_tiers", attendu, fp, ecart <= TOLERANCE_ABS_IDENTITE,
                 f"T1nr+T1r+T2+T3 = {attendu:.2f} vs fonds_propres_eligibles={fp:.2f}, écart={ecart:.4f} M€")

    # --- 3. ratio_scr recalculé ---
    v = valeurs("scr_total", "ratio_scr")
    if v is not None and fp is not None:
        scr_total, ratio_scr = v
        ratio_recalcule = fp / scr_total * 100
        ecart_pct = abs(ratio_recalcule - ratio_scr) / ratio_scr * 100
        ajouter("ratio_scr_recalcule", ratio_scr, round(ratio_recalcule, 2), ecart_pct <= TOLERANCE_PCT_RATIO,
                 f"fonds_propres_eligibles/scr_total×100 = {ratio_recalcule:.4f}% vs ratio_scr publié={ratio_scr:.2f}%, écart={ecart_pct:.4f}%")

    # --- 4. ratio_mcr recalculé — cf. SOURCES_MCR_INDEPENDANTES en tête de
    # fichier : généralisé sous forme de registre plutôt qu'un nom en dur,
    # mais reste Groupama-only en pratique (seule société avec une source
    # indépendante capturée). Skippé proprement pour toute autre société.
    source_mcr = SOURCES_MCR_INDEPENDANTES.get(company_name)
    v = valeurs("mcr", "ratio_mcr")
    if source_mcr is not None and v is not None:
        mcr, ratio_mcr = v
        fp_mcr = source_mcr()
        ratio_mcr_recalcule = fp_mcr / mcr * 100
        ecart_pct = abs(ratio_mcr_recalcule - ratio_mcr) / ratio_mcr * 100
        ajouter("ratio_mcr_recalcule", ratio_mcr, round(ratio_mcr_recalcule, 2), ecart_pct <= TOLERANCE_PCT_RATIO,
                 f"R0570(eligibles MCR)/mcr×100 = {ratio_mcr_recalcule:.4f}% vs ratio_mcr publié={ratio_mcr:.2f}%, écart={ecart_pct:.4f}%")

    # --- 5. mcr < scr_total (invariant de base, PAS le corridor 25-45% solo) ---
    v = valeurs("mcr", "scr_total")
    if v is not None:
        mcr, scr_total = v
        ajouter("mcr_inferieur_scr_total", None, mcr - scr_total, mcr < scr_total,
                 f"mcr={mcr:.2f} M€ doit être < scr_total={scr_total:.2f} M€ (invariant Solvabilité II de base, "
                 "pas le corridor 25-45% de l'art. 129, défini pour le solo — non affirmé ici pour le groupe)")

    # --- 6/7. Croisements SCR — cf. CROISEMENTS_GROUPAMA en tête de fichier :
    # registre extensible, reste Groupama-only en pratique (généralisation
    # générique testée et rejetée, LAC DT/TP non capturés dans les 22 KPIs
    # — cf. analyse détaillée en tête de fichier).
    for kpi_name, (valeur_attendue, detail) in CROISEMENTS_GROUPAMA.get(company_name, {}).items():
        v = valeurs(kpi_name)
        if v is None:
            continue
        valeur_reelle = v[0]
        check_name = "scr_total_croise_S23_S25" if kpi_name == "scr_total" else "scr_nonvie_croise_QRT_image"
        ajouter(check_name, valeur_attendue, valeur_reelle, abs(valeur_reelle - valeur_attendue) <= TOLERANCE_ABS_IDENTITE, detail)

    # --- 8. Signe de chaque KPI non-NULL — Décision 090 : >=0/<=0 (accepte
    # un vrai zéro, légitime pour plusieurs sociétés, cf. commentaire en
    # tête de fichier) plutôt que >0/<0 strict.
    defs_par_nom = {d["kpi_name"]: d for d in KPI_DEFINITIONS}
    for kpi_name, (valeur, unite) in kpis.items():
        if valeur is None:
            continue
        signe_attendu = defs_par_nom[kpi_name]["sign"]
        if signe_attendu == "positive":
            passe = valeur >= 0
        elif signe_attendu == "negative":
            passe = valeur <= 0
        else:  # "any"
            passe = True
        ajouter(f"signe_{kpi_name}", signe_attendu, valeur, passe,
                f"valeur={valeur:.2f} {unite}, signe attendu={signe_attendu!r}")

    # --- 10. Magnitude (Décision 095) — cf. commentaire en tête de fichier
    # pour la justification des seuils et la limite assumée (ne détecte
    # pas un facteur ×2-4 sur un KPI déjà petit).
    for kpi_name, (valeur, unite) in kpis.items():
        if valeur is None or unite != "M€":
            continue
        plafond = SEUILS_MAGNITUDE.get(kpi_name)
        if plafond is None:
            continue
        passe = abs(valeur) <= plafond
        ajouter(f"magnitude_{kpi_name}", plafond, valeur, passe,
                f"|{valeur:,.2f}| M€ doit être ≤ {plafond:,.0f} M€ (plafond {'provisions' if kpi_name in KPIS_MONTANT_PROVISIONS else 'standard'}, Décision 095)")

    # --- 11. Magnitude plancher (Décision 107) — symétrique du contrôle
    # 10 ci-dessus, cf. commentaire en tête de fichier (SEUILS_MAGNITUDE
    # détecte ÷1000 au lieu de ÷1M ; ce contrôle détecte l'erreur inverse).
    for kpi_name in KPIS_MONTANT_PLANCHER:
        paire = kpis.get(kpi_name)
        if paire is None or paire[0] is None:
            continue
        valeur, unite = paire
        if unite != "M€":
            continue
        passe = abs(valeur) >= PLANCHER_MONTANT
        ajouter(f"plancher_{kpi_name}", PLANCHER_MONTANT, valeur, passe,
                f"|{valeur:,.4f}| M€ doit être ≥ {PLANCHER_MONTANT} M€ (plancher, suspicion d'erreur "
                f"d'unité ÷1 000 000 au lieu de ÷1000 sinon, Décision 107)")

    return controles


# Décision 159 — contrôle 12 : lignes de primes acquises et de charge des
# sinistres non-vie utilisées par le KPI calculé sp_nonvie, relues dans le
# texte de leur page source (tableau S.05.01). Pour chaque groupe (primes,
# sinistres) :
#   a) chaque montant non nul est imprimé dans la bonne section de la page
#      (« Primes acquises » ou « Charge des sinistres »), en milliers d'euros
#      ou en euros, au signe près ;
#   b) identité du tableau : Σ lignes brutes − part des réassureurs = net,
#      avec deux montants imprimés dans la même section. C'est elle qui
#      vérifie les signes (en format comptable, un tiret de signe ne se
#      distingue pas d'une case vide dans le texte) et qu'aucune ligne ne
#      manque, montants nuls compris.
# Une ligne n'est vérifiée que si a) et b) passent. Page image sans texte,
# PDF introuvable ou PyMuPDF absent : contrôle impossible (« non
# contrôlable »), ligne non vérifiée, raison écrite — jamais une
# vérification forcée.
PDF_PAR_SOCIETE_TS = BASE_DIR / "frontend" / "src" / "lib" / "pdf-par-societe.ts"
DATA_DIR = BASE_DIR / "data"
TOLERANCE_SP = 0.05  # points de %, comme les autres KPIs officiels (Décision 158)
GROUPES_SP = {"primes_acquises_brutes": "primes", "charge_sinistres": "sinistres"}
ECHELLES_SP = ((1e3, "milliers d'euros"), (1e6, "euros"))
# En-têtes de section du S.05.01 (français ou anglais) ; None = section
# sans intérêt ici (primes émises, dépenses, autres provisions).
SECTIONS_S0501 = (
    (("primes acquises", "premiums earned"), "primes"),
    (("charge des sinistres", "claims incurred"), "sinistres"),
    (("primes émises", "premiums written", "dépenses engagées", "expenses incurred",
      "variation des autres provisions", "changes in other technical provisions"), None),
)
_MONTANT = re.compile(r"\d{1,3}(?:[   .]\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?")
_PDFS_OUVERTS = {}


def pdf_par_societe():
    """PDF par défaut de chaque société, lu (sans le modifier) dans le
    mapping du front-end (même source que le lien « voir le PDF »)."""
    return dict(re.findall(r'"([^"]+)":\s*"([^"]+\.pdf)"', PDF_PAR_SOCIETE_TS.read_text(encoding="utf-8")))


def lire_montant(case):
    """(valeur absolue, nombre de décimales) d'une case de tableau, ou None.
    Le signe est ignoré (cf. identité b ci-dessus)."""
    s = case.strip().strip("()").replace("−", "-").lstrip("-").strip()
    if not _MONTANT.fullmatch(s):
        return None
    s = re.sub(r"[   ]", "", s)
    if "," in s:  # virgule décimale, points éventuels = milliers
        entier, decimales = s.replace(".", "").split(",")
    elif re.fullmatch(r"\d{1,3}(?:\.\d{3})+", s):  # points des milliers
        entier, decimales = s.replace(".", ""), ""
    else:  # point décimal éventuel
        entier, _, decimales = s.partition(".")
    return float(f"{entier}.{decimales or 0}"), len(decimales)


def montants_par_section(texte):
    """{"primes": [...], "sinistres": [...]} : montants imprimés dans les
    sections « Primes acquises » et « Charge des sinistres » de la page. Une
    ligne de texte est coupée en cases aux suites d'au moins 2 espaces (un
    espace seul sépare les milliers)."""
    sections = {"primes": [], "sinistres": []}
    courante = None
    for ligne in texte.splitlines():
        bas = ligne.lower()
        for motifs, section in SECTIONS_S0501:
            if any(m in bas for m in motifs):
                courante = section
                break
        if courante is None:
            continue
        for case in re.split(r"\s{2,}|\|", ligne):
            m = lire_montant(case)
            if m is not None:
                sections[courante].append(m)
    return sections


def texte_page(nom_pdf, page):
    if nom_pdf not in _PDFS_OUVERTS:
        chemin = DATA_DIR / nom_pdf
        _PDFS_OUVERTS[nom_pdf] = fitz.open(chemin) if chemin.exists() else None
    doc = _PDFS_OUVERTS[nom_pdf]
    if doc is None or not 1 <= page <= doc.page_count:
        return None
    return doc[page - 1].get_text()


def imprime(montants, cible):
    """Montant imprimé égal à `cible` (même unité), à l'arrondi d'affichage près."""
    return next((x for x, d in montants if abs(x - cible) <= 0.5 * 10 ** -d + 1e-6 * max(cible, 1)), None)


def identite_s0501(montants, bruts):
    """Identité b) : (part, net, signe) imprimés dans la section tels que
    Σ bruts − part = signe × net, ou None. `bruts` : lignes brutes signées,
    dans l'unité de la page. Part et net : montants non nuls, autres que les
    lignes brutes elles-mêmes (sinon « brut − brut = 0 » passerait toujours)."""
    total = sum(bruts)
    candidats = [(x, d) for x, d in montants if x > 0 and imprime([(abs(b), d) for b in bruts], x) is None]
    tol = 0.5 * (len(bruts) + 2)  # arrondi d'affichage de chaque montant
    return next(((p, n, signe) for p, dp in candidats for n, dn in candidats for signe in (1, -1)
                 if abs(total - p - signe * n) <= tol * 10 ** -min(dp, dn)), None)


def controler_sp_nonvie(conn, company_id, company_name, year):
    """Contrôle 12 (Décision 159) — cf. commentaire ci-dessus. Seulement pour
    les sociétés où sp_nonvie existe (mêmes règles que comparabilite.py)."""
    kpis = {r[0]: (r[1], r[2]) for r in conn.execute(
        "SELECT kpi_name, value, source_pdf FROM kpis WHERE company_id=? AND year=? AND value IS NOT NULL",
        (company_id, year))}
    lignes = {}
    for kpi, index, code, label, valeur, page in conn.execute(
            """SELECT kpi_name, composant_index, composant_code_qrt, composant_label, composant_valeur, composant_page
               FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name IN ('primes_acquises_brutes',
               'charge_sinistres') ORDER BY kpi_name, composant_index""", (company_id, year)):
        lignes.setdefault(kpi, []).append((index, code, label, valeur, page))
    perimetre, scr_method = conn.execute("SELECT type_document, scr_method FROM companies WHERE id=?",
                                         (company_id,)).fetchone()
    ind = comparabilite.indicateurs({k: v for k, (v, _) in kpis.items()},
                                    {k: [(c, l, v) for _, c, l, v, _ in ls] for k, ls in lignes.items()},
                                    perimetre, scr_method)
    if ind.get("sp_nonvie_pct") is None:
        return []

    controles = []
    pdf_defaut = pdf_par_societe().get(company_name)
    total = {}
    for kpi, groupe in GROUPES_SP.items():
        retenues = [l for l in lignes[kpi] if comparabilite._classe_composant(l[1], l[2]) == "non-vie"]
        total[groupe] = sum(l[3] for l in retenues)
        nom_pdf = kpis[kpi][1] or pdf_defaut

        def ajouter(nom, attendu, calcule, passe, details, non_controlable=False):
            controles.append({"check_name": nom, "expected_value": attendu, "computed_value": calcule,
                              "passed": passe, "details": details, "non_controlable": non_controlable})

        raison = None
        montants = []
        if fitz is None:
            raison = "PyMuPDF absent : relancer avec .venv/Scripts/python.exe -I validate_kpis.py"
        elif not nom_pdf:
            raison = "aucun PDF source connu pour la société"
        else:
            for page in sorted({l[4] for l in retenues if l[4] is not None}):
                texte = texte_page(nom_pdf, page)
                if texte is None:
                    raison = f"page {page} introuvable dans {nom_pdf}"
                    break
                montants += montants_par_section(texte)[groupe]
            if raison is None and not montants:
                raison = (f"aucune section « {'Primes acquises' if groupe == 'primes' else 'Charge des sinistres'} » "
                          f"lisible p.{', '.join(str(p) for p in sorted({l[4] for l in retenues}))} de {nom_pdf} "
                          "(page image, sans texte)")
        if raison:
            for index, code, label, valeur, page in retenues:
                ajouter(f"sp_nonvie_ligne_{kpi}_{index}", valeur, None, False,
                        f"NON CONTRÔLABLE — {label} : {raison}", non_controlable=True)
            continue

        # a) présence de chaque montant non nul, à l'échelle la plus fréquente.
        echelle, unite = max(ECHELLES_SP, key=lambda e: sum(
            imprime(montants, abs(l[3]) * e[0]) is not None for l in retenues if l[3]))
        trouve = {l[0]: imprime(montants, abs(l[3]) * echelle) if l[3] else 0.0 for l in retenues}
        # b) identité Brut − part des réassureurs = net.
        brut = total[groupe] * echelle
        couple = identite_s0501(montants, [l[3] * echelle for l in retenues])
        if couple:
            p, n, signe = couple
            detail_id = (f"brut {brut:,.0f} − part des réassureurs {p:,.0f} = net {signe * n:,.0f} "
                         f"({unite}, p.{retenues[0][4]})")
        else:
            detail_id = (f"aucun couple (part des réassureurs, net) imprimé ne vérifie brut {brut:,.0f} − part = net "
                         f"({unite}, p.{retenues[0][4]}) : signe ou ligne à revoir")
        ajouter(f"sp_nonvie_identite_{groupe}", brut / echelle, (brut - p) / echelle if couple else None,
                couple is not None, f"Identité S.05.01 {groupe} : {detail_id}")
        for index, code, label, valeur, page in retenues:
            present = trouve[index] is not None
            passe = present and couple is not None
            if not valeur:
                quoi = "montant nul : vérifié par l'identité du tableau"
            elif present:
                quoi = f"{abs(valeur) * echelle:,.0f} imprimé p.{page} ({unite})"
            else:
                quoi = f"{abs(valeur) * echelle:,.0f} ({unite}) introuvable dans la section p.{page}"
            ajouter(f"sp_nonvie_ligne_{kpi}_{index}", valeur, valeur if passe else None, passe,
                    f"{label} = {valeur:,.3f} M€ — {quoi}" + ("" if couple else " ; identité du tableau non vérifiée"))

    recalcul = total["sinistres"] / total["primes"] * 100
    controles.append({
        "check_name": "sp_nonvie_recalcul", "expected_value": ind["sp_nonvie_pct"], "computed_value": round(recalcul, 4),
        "passed": abs(recalcul - ind["sp_nonvie_pct"]) <= TOLERANCE_SP + 1e-9, "non_controlable": False,
        "details": f"sinistres non-vie {total['sinistres']:,.3f} ÷ primes non-vie {total['primes']:,.3f} × 100 = "
                   f"{recalcul:.4f} vs sp_nonvie={ind['sp_nonvie_pct']} (tolérance {TOLERANCE_SP})"})
    return controles


def executer_completude(conn, company_id, year):
    # Décision 158 — complétude des 21 KPIs extraits seulement (hors KPIs calculés).
    n = conn.execute(f"SELECT COUNT(*) FROM kpis WHERE company_id=? AND year=? AND {_FILTRE_EXTRAITS}",
                     (company_id, year)).fetchone()[0]
    n_null = conn.execute(f"SELECT COUNT(*) FROM kpis WHERE company_id=? AND year=? AND value IS NULL AND {_FILTRE_EXTRAITS}",
                           (company_id, year)).fetchone()[0]
    noms_null = [r[0] for r in conn.execute(
        f"SELECT kpi_name FROM kpis WHERE company_id=? AND year=? AND value IS NULL AND {_FILTRE_EXTRAITS}", (company_id, year)
    ).fetchall()]
    n_total = len(KPI_DEFINITIONS)
    return [
        {"check_name": "completude_kpis", "expected_value": n_total, "computed_value": n, "passed": n == n_total,
         "details": f"{n} lignes trouvées pour (company_id={company_id}, year={year})"},
        {"check_name": "completude_aucun_null", "expected_value": 0, "computed_value": n_null,
         "passed": n_null == 0,
         "details": f"{n_null} NULL trouvé(s) : {noms_null} (attendu : aucun, Décision 144)"},
    ]


# Décision 151 — fourchettes plausibles de best_estimate / scr_total par
# activité (companies.type_activite, Décision 149). Observé sur les 41
# sociétés 2025 : vie 0,2-65, non-vie 0,8-7, santé 0,1-8, mixte 6-18.
# Bornes larges : le but est d'attraper une erreur d'unité ×1000 (Crédit
# Agricole Assurances : 0,024, Décision 148), pas de juger un profil.
FOURCHETTE_BE_SUR_SCR = {
    "Vie": (0.1, 150), "Non-vie": (0.1, 30), "Santé/prévoyance": (0.02, 30), "Mixte": (0.5, 80),
}


def executer_plausibilite(conn, company_id, kpis):
    row = conn.execute("SELECT type_activite FROM companies WHERE id=?", (company_id,)).fetchone()
    activite = row[0] if row else None
    be, scr = kpis.get("best_estimate", (None,))[0], kpis.get("scr_total", (None,))[0]
    if activite not in FOURCHETTE_BE_SUR_SCR or not be or not scr:
        return []
    bas, haut = FOURCHETTE_BE_SUR_SCR[activite]
    ratio = be / scr
    return [{
        "check_name": "plausibilite_best_estimate_scr_total", "expected_value": None, "computed_value": ratio,
        "passed": bas <= ratio <= haut,
        "details": f"best_estimate / scr_total = {ratio:.3f}, attendu entre {bas} et {haut} pour l'activité "
                   f"{activite} (sinon suspicion d'erreur d'unité, Décision 151)",
    }]


def inserer_controles(conn, company_id, year, controles, company_name=None):
    # Décision 104 — sans ce DELETE, chaque ré-exécution de validate_kpis.py
    # (--all ou --company) ACCUMULE indéfiniment des lignes en doublon dans
    # validation_checks (aucune contrainte unique en base) : constaté sur
    # les 34 sociétés, de 144 à 695 lignes pour 36-49 check_name distincts
    # réels — n_checks devenait un artefact du nombre de ré-exécutions, pas
    # un état réel. Purge (company_id, year) avant d'insérer les contrôles
    # frais de cette exécution, la rendant idempotente.
    conn.execute("DELETE FROM validation_checks WHERE company_id=? AND year=?", (company_id, year))
    for c in controles:
        note = ECHECS_LEGITIMES_CONNUS.get((company_name, c["check_name"]))
        conn.execute(
            """INSERT INTO validation_checks (company_id, year, check_name, expected_value, computed_value, passed, details, legitime, note_legitimite)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (company_id, year, c["check_name"], c["expected_value"], c["computed_value"], int(c["passed"]), c["details"],
             int(note is not None), note),
        )
    conn.commit()


def marquer_valides(conn, company_id, year, controles):
    """kpis.validated=1 pour tout KPI directement concerné par au moins 1
    contrôle, et dont TOUS les contrôles qui le concernent passent — 0
    sinon (jamais validé par défaut/optimisme, cf. schéma Décision 049)."""
    kpi_concerne = {}
    for c in controles:
        nom = c["check_name"]
        for kpi_name in ("best_estimate", "marge_risque", "provisions_techniques",
                          "fonds_propres_t1_nr", "fonds_propres_t1_r", "fonds_propres_t2",
                          "fonds_propres_t3", "fonds_propres_eligibles", "ratio_scr", "ratio_mcr",
                          "mcr", "scr_total", "scr_souscription_nonvie"):
            if kpi_name in nom or nom == f"signe_{kpi_name}":
                kpi_concerne.setdefault(kpi_name, []).append(c["passed"])
    for kpi_name, resultats in kpi_concerne.items():
        valide = all(resultats)
        conn.execute(
            "UPDATE kpis SET validated=? WHERE company_id=? AND year=? AND kpi_name=?",
            (int(valide), company_id, year, kpi_name),
        )
    conn.commit()


def valider_societe(conn, company_name, year, afficher_detail=True):
    """Exécute tous les contrôles pour 1 société, persiste, retourne
    (n_passed, controles) — utilisé par --company ET --all."""
    row = conn.execute("SELECT id FROM companies WHERE name=?", (company_name,)).fetchone()
    if row is None:
        print(f">>> ARRÊT — entreprise {company_name!r} absente de companies.")
        return None, None
    company_id = row[0]

    kpis = charger_kpis(conn, company_id, year)
    if not kpis:
        print(f">>> ARRÊT — aucun KPI trouvé pour ({company_name}, {year}). Lance extract_kpis.py d'abord.")
        return None, None

    controles = (executer_controles(kpis, company_name) + executer_completude(conn, company_id, year)
                 + executer_plausibilite(conn, company_id, kpis)
                 + controler_sp_nonvie(conn, company_id, company_name, year))
    for c in controles:
        c["note_legitimite"] = ECHECS_LEGITIMES_CONNUS.get((company_name, c["check_name"]))
    inserer_controles(conn, company_id, year, controles, company_name=company_name)
    marquer_valides(conn, company_id, year, controles)

    n_passed = sum(1 for c in controles if c["passed"])
    if afficher_detail:
        print("=" * 100)
        print(f"CONTRÔLES ACTUARIELS — {company_name} {year}")
        print("=" * 100)
        for c in controles:
            if c["passed"]:
                statut = "OK"
            elif c.get("non_controlable"):
                statut = "N/C"
            elif c.get("note_legitimite"):
                statut = "LÉGIT"
            else:
                statut = "ÉCHEC"
            print(f"  [{statut:5}] {c['check_name']:32} {c['details']}")
            if not c["passed"] and c.get("note_legitimite"):
                print(f"           -> {c['note_legitimite']}")
        print(f"\n  Total : {n_passed}/{len(controles)} contrôles passés\n")
    return n_passed, controles


def main():
    args = parse_cli()
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    if args.all:
        noms = [r[0] for r in conn.execute("SELECT name FROM companies ORDER BY name")]
        recap = []
        for nom in noms:
            n_passed, controles = valider_societe(conn, nom, args.year)
            if controles is None:
                continue
            # Diagnostic 12/10/2026, Problème 2 — l'ancien filtre excluait
            # TOUS les checks "signe_*" des "échecs réels", pas seulement les
            # faux signaux à 0 : un vrai échec de signe (valeur non-nulle,
            # non vérifiée) disparaissait silencieusement du résumé. Ici,
            # seuls 2 cas sortent des "échecs réels" : (1) le faux signal à 0
            # (signe "positive" qui échoue uniquement parce que la valeur
            # vaut exactement 0, cas sans portée actuarielle) et (2) un échec
            # déjà vérifié et classé légitime (ECHECS_LEGITIMES_CONNUS,
            # Problèmes 3-4) — les deux restent visibles dans le résumé,
            # jamais juste supprimés.
            # Décision 159 : (3) contrôle impossible (page image, PyMuPDF
            # absent) — compté à part, ce n'est pas une erreur de donnée.
            echecs_signe_zero, echecs_legitimes, echecs_reels, non_controlables = [], [], [], []
            for c in controles:
                if c["passed"]:
                    continue
                if c["check_name"].startswith("signe_") and abs(c["computed_value"]) < 1e-9:
                    echecs_signe_zero.append(c)
                elif c.get("non_controlable"):
                    non_controlables.append(c)
                elif c.get("note_legitimite"):
                    echecs_legitimes.append(c)
                else:
                    echecs_reels.append(c)
            recap.append((nom, n_passed, len(controles), echecs_reels, echecs_legitimes, echecs_signe_zero,
                          non_controlables))
        conn.close()

        print("\n" + "=" * 100)
        print("RÉCAPITULATIF — validate_kpis.py --all")
        print("=" * 100)
        if fitz is None:
            print("  ATTENTION : PyMuPDF absent, contrôle 12 (S/P non-vie) non contrôlable partout — relancer avec "
                  ".venv/Scripts/python.exe -I validate_kpis.py --all")
        print(f"  {'Société':30} {'Contrôles':12} {'Échecs réels':14} {'Connus/légitimes':18} {'Faux signaux (0,00)':21}"
              f" {'Non contrôlables'}")
        for nom, n_passed, n_total, echecs_reels, echecs_legitimes, echecs_zero, non_ctrl in recap:
            print(f"  {nom:30} {n_passed}/{n_total:<9} {len(echecs_reels):<14} {len(echecs_legitimes):<18} "
                  f"{len(echecs_zero):<21} {len(non_ctrl)}")
            for e in echecs_reels:
                print(f"      >>> ÉCHEC RÉEL [{e['check_name']}] {e['details']}")
            for e in echecs_legitimes:
                print(f"      --- connu/légitime [{e['check_name']}] {e['note_legitimite']}")
            if non_ctrl:
                print(f"      ... non contrôlable [{non_ctrl[0]['check_name']} +{len(non_ctrl) - 1}] "
                      f"{non_ctrl[0]['details']}")
        return

    n_passed, controles = valider_societe(conn, args.company, args.year)
    conn.close()


if __name__ == "__main__":
    main()
