# -*- coding: utf-8 -*-
"""extract_kpis.py — Extraction des 22 KPIs Groupama 2025 (Phase 3.3,
Décision 051), à partir des QRT DÉJÀ PARSÉS sur disque
(test_markdrop/output_structure_brute/corpus_final.json) — ne relit JAMAIS
le PDF, sauf 1 appel Gemini Vision sur une image DÉJÀ EXTRAITE
(picture_75.png), jamais une reconversion.

4 sources, par ordre de confiance décroissante (cf. audit exhaustif,
Décision 051) :
1. Lecture directe 1 ligne/N colonnes dans S.23.01.22.01 (texte natif,
   55/55 lignes, méthode d'extraction la plus fiable du corpus).
2. Somme de lignes dans S.02.01.02.01 (union pages 78+79, Gemini VLM,
   74/83 — mais les 10 codes utilisés ici sont TOUS présents, vérifié).
3. Somme lignes×colonnes dans S.05.01.02.01+02 (Gemini VLM, 100% complet
   sur ces 2 sous-feuilles).
4. Gemini Vision sur picture_75.png (organigramme SCR à texte typographié,
   PAS une reconversion PDF — image déjà extraite par extraire_visuels.py).
5. Valeur unique codée en dur (S.25.05.22.02/R0060) — ce tableau n'a
   JAMAIS été extrait par le parser (bug de résolution de sous-feuille,
   documenté mais PAS corrigé ici, cf. Décision 051) ; valeur relevée
   manuellement sur le rendu visuel de la page 87 pendant l'audit,
   confirmée par l'utilisateur.

CHAQUE lecture de cellule VÉRIFIE le libellé officiel attendu avant
d'accepter la valeur (même discipline que final_corrections.py dans
test_markdrop/) — un désaccord de libellé fait échouer proprement
(KpiIntrouvable) plutôt que de lire une cellule décalée en silence.

Toutes les valeurs QRT sont en MILLIERS D'EUROS dans le PDF source
(cf. page 77 : "Les états quantitatifs annexés sont exprimés en milliers
d'euros") — converties en M€ (÷1000) avant insertion, cohérent avec
l'unité déclarée dans kpi_definitions.py.

    python extract_kpis.py
"""

import base64
import json
import os
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
TEST_MARKDROP = BASE_DIR / "test_markdrop"
CORPUS_FINAL = TEST_MARKDROP / "output_structure_brute" / "corpus_final.json"
PICTURE_75 = TEST_MARKDROP / "output_structure_brute" / "visuels" / "2025" / "images" / "picture_75.png"
PDF_SOURCE = BASE_DIR / "data" / "SFCR_2025_Groupe-Groupama.pdf"
PAGE87_RENDER_CACHE = TEST_MARKDROP / "page87_render_cache.png"
DB_PATH = BASE_DIR / "kpis.db"

COMPANY_NAME = "Groupama"
YEAR = 2025

sys.path.insert(0, str(BASE_DIR))
from kpi_definitions import KPI_DEFINITIONS
from paddleocr_reader import lire_image, valeur_a_droite_du_code, valeur_sous_label


class KpiIntrouvable(Exception):
    pass


def _vers_float(brut):
    """valeur_brute est tantôt une str (ex. extraction native S.23.01,
    "2160259" ou "2,74"), tantôt un int/float JSON natif (ex. certaines
    lignes Gemini VLM, S.02.01) — les 2 formats coexistent réellement dans
    corpus_final.json, vérifié en le découvrant ici plutôt que supposé."""
    if isinstance(brut, (int, float)):
        return float(brut)
    return float(str(brut).replace(" ", "").replace(",", "."))


def charger_corpus():
    with open(CORPUS_FINAL, encoding="utf-8") as f:
        return json.load(f)["elements"]


def elements_par_template(corpus, template_id):
    """Tous les éléments QRT d'un template_id donné (plusieurs si le
    template s'étale sur plusieurs pages physiques, ex. S.02.01.02.01 sur
    les pages 78+79 — cf. Décision 022 sur la fusion multi-pages)."""
    return [e for e in corpus if e.get("template_id") == template_id]


def lire_cellule(elements, code_ligne, code_colonne, libelle_attendu_sous_chaine):
    """Lit 1 cellule (code_ligne, code_colonne) parmi une liste d'éléments
    (1 ou plusieurs pages du même template). Vérifie que le libellé
    officiel contient `libelle_attendu_sous_chaine` (insensible à la
    casse) avant d'accepter la valeur — lève KpiIntrouvable sinon, ne lit
    JAMAIS une cellule dont le libellé ne correspond pas à ce qui est
    attendu. Retourne la valeur brute en float (milliers d'euros ou
    ratio selon la ligne)."""
    for e in elements:
        lignes = e["contenu"]["lignes"]
        if code_ligne not in lignes:
            continue
        row = lignes[code_ligne]
        libelle = row["libelle_officiel"] or ""
        if libelle_attendu_sous_chaine.lower() not in libelle.lower():
            raise KpiIntrouvable(
                f"{code_ligne} : libellé {libelle!r} ne contient pas {libelle_attendu_sous_chaine!r} — refus de lire"
            )
        if code_colonne not in row["valeurs"]:
            raise KpiIntrouvable(f"{code_ligne}/{code_colonne} absent (page {e['page_source']})")
        brut = row["valeurs"][code_colonne]["valeur_brute"]
        return _vers_float(brut)
    raise KpiIntrouvable(f"{code_ligne} introuvable dans aucun élément fourni")


def sommer_cellules(elements, specs):
    """specs : liste de (code_ligne, libelle_attendu_sous_chaine) — somme
    la colonne C0010 de chaque ligne. Toutes les lignes doivent être
    trouvées et vérifiées (même discipline que lire_cellule) ; une seule
    absente fait échouer toute la somme plutôt que de sommer un
    sous-ensemble silencieusement incomplet."""
    total = 0.0
    for code_ligne, libelle_attendu in specs:
        total += lire_cellule(elements, code_ligne, "C0010", libelle_attendu)
    return total


def sommer_toutes_colonnes(elements, specs):
    """Comme sommer_cellules, mais somme TOUTES les colonnes présentes de
    chaque ligne (pas seulement C0010) — nécessaire pour S.05.01 où les
    lignes de branches (direct/réassurance) sont ventilées sur plusieurs
    colonnes de ligne d'activité, jamais une seule colonne "Total"."""
    total = 0.0
    for code_ligne, libelle_attendu in specs:
        trouve = False
        for e in elements:
            lignes = e["contenu"]["lignes"]
            if code_ligne not in lignes:
                continue
            row = lignes[code_ligne]
            libelle = row["libelle_officiel"] or ""
            if libelle_attendu.lower() not in libelle.lower():
                raise KpiIntrouvable(f"{code_ligne} : libellé {libelle!r} inattendu")
            for cellule in row["valeurs"].values():
                total += _vers_float(cellule["valeur_brute"])
            trouve = True
        if not trouve:
            raise KpiIntrouvable(f"{code_ligne} introuvable dans aucun élément fourni")
    return total


# ---------------------------------------------------------------------
# Règle de concordance 2-sur-3 (Décision 055, Phase 3.7) — AUCUN chiffre
# n'est accepté sur la foi d'un seul outil. Utilisée pour tout KPI dont la
# source primaire est une lecture d'image (pas une cellule QRT native).
# ---------------------------------------------------------------------

def concordance_2_sur_3(kpi_name, valeurs_sources, tolerance_pct=1.0):
    """valeurs_sources : liste de (nom_source, valeur|None). Accepte une
    valeur SEULEMENT si au moins 2 sources indépendantes concordent à
    ±tolerance_pct% — sinon NULL. Ne fait jamais confiance à une source
    unique, quelle qu'elle soit (y compris une relecture manuelle) :
    2 sources en désaccord = NULL, jamais un arbitrage silencieux.
    Retourne (valeur_retenue, confiance, détail_texte)."""
    dispo = [(n, v) for n, v in valeurs_sources if v is not None]
    print(f"    {kpi_name}: " + ", ".join(f"{n}={v}" for n, v in valeurs_sources))

    if len(dispo) < 2:
        print(f"      -> NULL ({len(dispo)}/{len(valeurs_sources)} source(s) disponible(s), minimum 2 requis)")
        return None, "NULL", f"{len(dispo)}/{len(valeurs_sources)} source(s) disponible(s), minimum 2 requis"

    meilleure_paire = None
    for i in range(len(dispo)):
        for j in range(i + 1, len(dispo)):
            n1, v1 = dispo[i]
            n2, v2 = dispo[j]
            base = max(abs(v1), abs(v2), 1)
            ecart_pct = abs(v1 - v2) / base * 100
            if ecart_pct <= tolerance_pct and (meilleure_paire is None or ecart_pct < meilleure_paire[2]):
                meilleure_paire = (n1, n2, ecart_pct, v1)

    if meilleure_paire is None:
        print(f"      -> NULL (aucune paire ne concorde a {tolerance_pct}% pres)")
        return None, "NULL", "aucune paire de sources concordantes"

    n1, n2, ecart_pct, valeur = meilleure_paire
    confiance = "haute" if len(dispo) == len(valeurs_sources) else "partielle"
    print(f"      -> {valeur} (concordance {n1} & {n2}, ecart {ecart_pct:.3f}%, confiance {confiance})")
    return valeur, confiance, f"{n1} & {n2} concordent (ecart {ecart_pct:.3f}%), confiance {confiance}"


# ---------------------------------------------------------------------
# PaddleOCR (PP-OCRv6, texte seul) — lecture déterministe non-LLM,
# tool 1/3 pour toute page/image sans texte natif exploitable (Décision
# 055). Voir paddleocr_reader.py pour le détail de l'implémentation et
# le bug oneDNN contourné (enable_mkldnn=False obligatoire sur ce poste).
# ---------------------------------------------------------------------

def rendre_page87(zoom=3.0):
    """Rend la page 87 du PDF source (Annexe 6, S.25.05.22) en PNG haute
    résolution pour lecture PaddleOCR — mis en cache sur disque (le rendu
    ne change jamais pour un PDF donné)."""
    if PAGE87_RENDER_CACHE.exists():
        return PAGE87_RENDER_CACHE
    import fitz
    doc = fitz.open(str(PDF_SOURCE))
    page = doc[86]  # page 87, index 0
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
    pix.save(str(PAGE87_RENDER_CACHE))
    doc.close()
    return PAGE87_RENDER_CACHE


def lire_r0060_paddleocr():
    """Lecture PaddleOCR de R0060 (Diversification, S.25.05.22.02) sur le
    rendu de la page 87 — code ancré à gauche, valeur la plus proche à
    droite sur la même ligne (cf. paddleocr_reader.valeur_a_droite_du_code,
    vérifié -4 612 403 à confiance 1.00 contre la valeur QRT réelle)."""
    items = lire_image(rendre_page87())
    valeur, conf = valeur_a_droite_du_code(items, "R0060")
    return valeur


LABELS_PICTURE_75_PADDLEOCR = {
    "scr_operationnel": "scrop",
    "scr_marche": "scrmarche",
    "scr_souscription_sante": "scrsante",
    "scr_contrepartie": "scrdefaut",
    "scr_souscription_vie": "scrvie",
    "scr_souscription_nonvie": "scrnonvie",
}


def lire_picture_75_paddleocr():
    """Lecture PaddleOCR des 6 valeurs SCR de picture_75.png — libellé
    normalisé (accents/espaces retirés) ancré au-dessus, valeur la plus
    proche géométriquement au-dessous (cf.
    paddleocr_reader.valeur_sous_label, vérifié : les 6 valeurs concordent
    EXACTEMENT avec VALEURS_VERIFIEES_PICTURE_75, ci-dessous)."""
    items = lire_image(PICTURE_75)
    resultat = {}
    for kpi_name, label_norm in LABELS_PICTURE_75_PADDLEOCR.items():
        valeur, conf = valeur_sous_label(items, label_norm)
        resultat[kpi_name] = valeur
    return resultat


# ---------------------------------------------------------------------
# Gemini Vision — picture_75.png (organigramme SCR, PAS une reconversion
# PDF : image déjà extraite sur disque par extraire_visuels.py)
# ---------------------------------------------------------------------

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODELE = "gemini-flash-latest"  # même config que test_markdrop/fusion_reranking.py


def lire_picture_75_gemini():
    """Un seul appel Gemini Vision sur picture_75.png, prompt strict JSON,
    température 0 — même discipline que fusion_reranking._juger_avec_client
    (pas de fallback silencieux sur une réponse non parsable)."""
    from openai import OpenAI

    cle_api = os.environ.get("GEMINI_API_KEY")
    if not cle_api:
        raise RuntimeError("GEMINI_API_KEY absente — nécessaire pour lire picture_75.png")
    client = OpenAI(api_key=cle_api, base_url=GEMINI_BASE_URL, timeout=60)

    with open(PICTURE_75, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    prompt = (
        "Cette image est un organigramme de ventilation du SCR (Capital de Solvabilité Requis) "
        "d'un groupe d'assurance, en milliers d'euros (k€). Lis EXACTEMENT les 6 valeurs numériques "
        "suivantes, telles qu'affichées dans les boîtes bleues et la boîte \"SCR op\" (ne calcule rien, "
        "ne devine rien — si une boîte n'est pas lisible, mets null) :\n"
        "- \"SCR op\" (SCR opérationnel)\n"
        "- \"SCR Marché\"\n"
        "- \"SCR Santé\"\n"
        "- \"SCR Défaut\"\n"
        "- \"SCR Vie\"\n"
        "- \"SCR Non vie\"\n"
        "Réponds STRICTEMENT en JSON : "
        '{"scr_operationnel": <nombre ou null>, "scr_marche": <nombre ou null>, '
        '"scr_souscription_sante": <nombre ou null>, "scr_contrepartie": <nombre ou null>, '
        '"scr_souscription_vie": <nombre ou null>, "scr_souscription_nonvie": <nombre ou null>}. '
        "Rien d'autre."
    )
    completion = client.chat.completions.create(
        model=GEMINI_MODELE,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
        max_tokens=500,
        temperature=0,
    )
    brut = completion.choices[0].message.content.strip()
    if brut.startswith("```"):
        brut = brut.strip("`")
        if brut.startswith("json"):
            brut = brut[4:]
    return json.loads(brut)


CLAUDE_MODELE_VISION = "claude-haiku-4-5-20251001"  # même modèle/config que test_markdrop/fusion_reranking.py

PROMPT_PICTURE_75 = (
    "Cette image est un organigramme de ventilation du SCR (Capital de Solvabilité Requis) "
    "d'un groupe d'assurance, en milliers d'euros (k€). Lis EXACTEMENT les 6 valeurs numériques "
    "suivantes, telles qu'affichées dans les boîtes bleues et la boîte \"SCR op\" (ne calcule rien, "
    "ne devine rien — si une boîte n'est pas lisible, mets null) :\n"
    "- \"SCR op\" (SCR opérationnel)\n"
    "- \"SCR Marché\"\n"
    "- \"SCR Santé\"\n"
    "- \"SCR Défaut\"\n"
    "- \"SCR Vie\"\n"
    "- \"SCR Non vie\"\n"
    "Réponds STRICTEMENT en JSON : "
    '{"scr_operationnel": <nombre ou null>, "scr_marche": <nombre ou null>, '
    '"scr_souscription_sante": <nombre ou null>, "scr_contrepartie": <nombre ou null>, '
    '"scr_souscription_vie": <nombre ou null>, "scr_souscription_nonvie": <nombre ou null>}. '
    "Rien d'autre."
)


def lire_picture_75_claude():
    """Secours si Gemini est indisponible (503 "high demand" rencontré en
    réel pendant cette extraction, pas hypothétique) — même modèle/SDK que
    le juge de secours déjà utilisé dans fusion_reranking.py
    (claude-haiku-4-5-20251001), même prompt strict JSON que la voie
    Gemini, pas une logique différente."""
    cle_api = os.environ.get("ANTHROPIC_API_KEY")
    if not cle_api:
        raise RuntimeError("ANTHROPIC_API_KEY absente — nécessaire pour le secours Claude Vision")
    from anthropic import Anthropic
    client = Anthropic(api_key=cle_api)

    with open(PICTURE_75, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")

    completion = client.messages.create(
        model=CLAUDE_MODELE_VISION,
        max_tokens=500,
        messages=[{"role": "user", "content": [
            {"type": "text", "text": PROMPT_PICTURE_75},
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
        ]}],
    )
    brut = completion.content[0].text.strip()
    if brut.startswith("```"):
        brut = brut.strip("`")
        if brut.startswith("json"):
            brut = brut[4:]
    return json.loads(brut)



# Valeurs VÉRIFIÉES MANUELLEMENT en zoomant picture_75.png (crop 2x sur
# chaque ligne de boîtes, cf. Décision 051) — retenues comme source
# d'AUTORITÉ plutôt que la lecture Claude Vision brute : l'appel Claude
# Vision (secours après échec Gemini, cf. ci-dessous) a été comparé
# CHIFFRE PAR CHIFFRE à cette relecture zoomée, et s'est trouvé FAUX sur
# 2 des 6 valeurs (SCR Défaut lu 783 110 par Claude, 785 108 en réalité ;
# SCR Vie lu 1 453 720 par Claude, 1 455 724 en réalité — écarts d'environ
# 2000 k€, invisibles sans cette re-vérification). Contrainte "précision
# absolue" : la relecture manuelle zoomée l'emporte sur la lecture LLM,
# jamais l'inverse. SCR op et SCR Non vie CONCORDAIENT déjà entre Claude
# et la relecture manuelle (ce dernier aussi cross-validé contre le QRT
# S.25.05.22.01/R0310 = 2 474 794, exact).
VALEURS_VERIFIEES_PICTURE_75 = {
    "scr_operationnel": 677_423,
    "scr_marche": 4_675_236,
    "scr_souscription_sante": 1_271_055,
    "scr_contrepartie": 785_108,
    "scr_souscription_vie": 1_455_724,
    "scr_souscription_nonvie": 2_474_794,
}


def lire_picture_75():
    """3 sources indépendantes par KPI (Décision 055, Phase 3.7) :
    1. PaddleOCR (déterministe, non-LLM, primaire) — lit picture_75.png
       directement.
    2. LLM Vision (Gemini par défaut, Claude en secours si Gemini échoue —
       503 "high demand" réellement rencontré en Phase 3.3, GEMINI_API_KEY2
       aussi rejetée en 403 — jamais un fallback silencieux, l'échec est
       affiché).
    3. Relecture manuelle zoomée (VALEURS_VERIFIEES_PICTURE_75) — UNIQUEMENT
       pour Groupama 2025, ce document précis (Décision 051) ; absente pour
       toute autre entreprise/année, le système retombe alors sur
       PaddleOCR + LLM Vision seuls (2 sources).
    Règle 2-sur-3 (concordance_2_sur_3) : aucun outil ne décide seul — 2
    sources doivent concorder à ±1%, sinon NULL."""
    print("\n  --- Lecture picture_75.png : jusqu'à 3 sources indépendantes ---")
    paddle_valeurs = lire_picture_75_paddleocr()

    try:
        llm_valeurs, source_llm = lire_picture_75_gemini(), "Gemini"
    except Exception as e:
        print(f"  [secours] Gemini a échoué ({type(e).__name__}: {str(e)[:150]}) — bascule sur Claude Vision")
        try:
            llm_valeurs, source_llm = lire_picture_75_claude(), "Claude"
        except Exception as e2:
            print(f"  [secours] Claude a aussi échoué ({type(e2).__name__}: {str(e2)[:150]}) — LLM Vision indisponible")
            llm_valeurs, source_llm = {}, None

    est_document_de_reference = (COMPANY_NAME, YEAR) == ("Groupama", 2025)

    resultat, details = {}, {}
    for kpi_name in LABELS_PICTURE_75_PADDLEOCR:
        sources = [
            ("PaddleOCR", paddle_valeurs.get(kpi_name)),
            (source_llm or "LLM(indisponible)", llm_valeurs.get(kpi_name) if llm_valeurs else None),
        ]
        if est_document_de_reference:
            sources.append(("relecture manuelle", VALEURS_VERIFIEES_PICTURE_75.get(kpi_name)))
        valeur, confiance, detail = concordance_2_sur_3(kpi_name, sources)
        resultat[kpi_name] = valeur
        details[kpi_name] = f"picture_75.png — {detail} [confiance {confiance}]"

    return resultat, details


# ---------------------------------------------------------------------
# Extraction
# ---------------------------------------------------------------------

def extraire_tout():
    corpus = charger_corpus()
    s2301_01 = elements_par_template(corpus, "S.23.01.22.01")
    s0201 = elements_par_template(corpus, "S.02.01.02.01")
    s0501_01 = elements_par_template(corpus, "S.05.01.02.01")
    s0501_02 = elements_par_template(corpus, "S.05.01.02.02")

    if not s2301_01:
        raise KpiIntrouvable("S.23.01.22.01 absent de corpus_final.json")
    if not s0201:
        raise KpiIntrouvable("S.02.01.02.01 absent de corpus_final.json")
    if not s0501_01 or not s0501_02:
        raise KpiIntrouvable("S.05.01.02.01/02 absent de corpus_final.json")

    valeurs = {}  # kpi_name -> (valeur_M€_ou_pct, source_page, note)

    # --- Niveau 1 : lecture directe, S.23.01.22.01 (page 85) ---
    ratio_scr = lire_cellule(s2301_01, "R0690", "C0010", "Ratio of Total Eligible own funds to Total group SCR")
    ratio_mcr = lire_cellule(s2301_01, "R0650", "C0010", "Ratio of Eligible own funds to Minimum Consolidated Group SCR")
    scr_total = lire_cellule(s2301_01, "R0680", "C0010", "Total Group SCR")
    mcr = lire_cellule(s2301_01, "R0610", "C0010", "Minimum consolidated Group SCR")
    fp_eligibles = lire_cellule(s2301_01, "R0660", "C0010", "Total eligible own funds to meet the total group SCR")
    fp_t1_nr = lire_cellule(s2301_01, "R0660", "C0020", "Total eligible own funds to meet the total group SCR")
    fp_t1_r = lire_cellule(s2301_01, "R0660", "C0030", "Total eligible own funds to meet the total group SCR")
    fp_t2 = lire_cellule(s2301_01, "R0660", "C0040", "Total eligible own funds to meet the total group SCR")
    fp_t3 = lire_cellule(s2301_01, "R0660", "C0050", "Total eligible own funds to meet the total group SCR")

    valeurs["ratio_scr"] = (ratio_scr * 100, 85, "S.23.01.22.01/R0690/C0010, ratio brut x100")
    valeurs["ratio_mcr"] = (ratio_mcr * 100, 85, "S.23.01.22.01/R0650/C0010, ratio brut x100")
    valeurs["scr_total"] = (scr_total / 1000, 85, "S.23.01.22.01/R0680/C0010")
    valeurs["mcr"] = (mcr / 1000, 85, "S.23.01.22.01/R0610/C0010")
    valeurs["fonds_propres_eligibles"] = (fp_eligibles / 1000, 85, "S.23.01.22.01/R0660/C0010")
    valeurs["fonds_propres_t1_nr"] = (fp_t1_nr / 1000, 85, "S.23.01.22.01/R0660/C0020")
    valeurs["fonds_propres_t1_r"] = (fp_t1_r / 1000, 85, "S.23.01.22.01/R0660/C0030")
    valeurs["fonds_propres_t2"] = (fp_t2 / 1000, 85, "S.23.01.22.01/R0660/C0040")
    valeurs["fonds_propres_t3"] = (fp_t3 / 1000, 85, "S.23.01.22.01/R0660/C0050")

    # --- Niveau 2 : somme de lignes, S.02.01.02.01 (pages 78-79) ---
    best_estimate = sommer_cellules(s0201, [
        ("R0540", "Best Estimate"), ("R0580", "Best Estimate"),
        ("R0630", "Best Estimate"), ("R0670", "Best Estimate"), ("R0710", "Best Estimate"),
    ])
    marge_risque = sommer_cellules(s0201, [
        ("R0550", "Risk margin"), ("R0590", "Risk margin"),
        ("R0640", "Risk margin"), ("R0680", "Risk margin"), ("R0720", "Risk margin"),
    ])
    valeurs["best_estimate"] = (best_estimate / 1000, 79, "S.02.01.02.01, somme 5 lignes Best Estimate")
    valeurs["marge_risque"] = (marge_risque / 1000, 79, "S.02.01.02.01, somme 5 lignes Risk margin")
    valeurs["provisions_techniques"] = ((best_estimate + marge_risque) / 1000, 79, "best_estimate + marge_risque")

    # --- Niveau 3 : somme lignes x colonnes, S.05.01 (pages 80-81) ---
    primes_brutes = sommer_toutes_colonnes(s0501_01, [
        ("R0210", "Premiums earned"), ("R0220", "Premiums earned"), ("R0230", "Premiums earned"),
    ]) + sommer_toutes_colonnes(s0501_02, [("R1510", "Premiums earned")])
    charge_sinistres = sommer_toutes_colonnes(s0501_01, [
        ("R0310", "Claims incurred"), ("R0320", "Claims incurred"), ("R0330", "Claims incurred"),
    ]) + sommer_toutes_colonnes(s0501_02, [("R1610", "Claims incurred")])
    valeurs["primes_acquises_brutes"] = (primes_brutes / 1000, 80, "S.05.01.02.01+02, somme gross toutes colonnes")
    valeurs["charge_sinistres"] = (charge_sinistres / 1000, 80, "S.05.01.02.01+02, somme gross toutes colonnes")

    # --- Niveau 4 : picture_75.png — 3 sources indépendantes, concordance 2-sur-3 ---
    vision, details_vision = lire_picture_75()
    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie"):
        v = vision.get(kpi_name)
        valeurs[kpi_name] = (v / 1000 if v is not None else None, 75, details_vision[kpi_name])

    # --- Niveau 5 : S.25.05.22.02/R0060 (page 87, image-only) — 2 sources
    # indépendantes désormais que le bug de résolution de sous-feuille est
    # corrigé (Décision 055) : lecture QRT réelle (Gemini VLM, via le
    # parser corrigé) + lecture PaddleOCR déterministe directe sur le
    # rendu de la page. Concordance 2-sur-3 comme pour picture_75 (avec
    # seulement 2 sources dispo ici : les 2 doivent s'accorder). ---
    s250501 = elements_par_template(corpus, "S.25.05.22.01")
    s250502 = elements_par_template(corpus, "S.25.05.22.02")
    if not s250501 or not s250502:
        raise KpiIntrouvable("S.25.05.22.01/02 absent de corpus_final.json — relancer reextraire_page87.py")

    r0060_qrt = lire_cellule(s250502, "R0060", "C0100", "Diversification")
    r0060_paddle = lire_r0060_paddleocr()
    print("\n  --- Lecture S.25.05.22.02/R0060 (page 87) : 2 sources indépendantes ---")
    r0060_valeur, r0060_confiance, r0060_detail = concordance_2_sur_3(
        "scr_diversification", [("QRT (Gemini VLM, parser corrigé)", r0060_qrt), ("PaddleOCR", r0060_paddle)]
    )
    valeurs["scr_diversification"] = (
        r0060_valeur / 1000 if r0060_valeur is not None else None, 87,
        f"S.25.05.22.02/R0060 — {r0060_detail} [confiance {r0060_confiance}]",
    )

    # --- NULL tranché (Décision 051) ---
    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé trouvé (Décision 051)")

    scr_nonvie_qrt = lire_cellule(s250501, "R0310", "C0010", "Total Net Non-life underwriting risk")
    mcr_qrt_s25 = lire_cellule(s250502, "R0470", "C0100", "Minimum consolidated group solvency capital requirement")
    scr_total_qrt_s25 = lire_cellule(s250502, "R0220", "C0100", "Consolidated Group SCR")
    scr_total_qrt_s25_bis = lire_cellule(s250502, "R0570", "C0100", "Total group solvency capital requirement")

    return valeurs, {
        "scr_total_qrt": scr_total, "mcr_qrt": mcr,
        "scr_total_qrt_s25_R0220": scr_total_qrt_s25, "scr_total_qrt_s25_R0570": scr_total_qrt_s25_bis,
        "mcr_qrt_s25_R0470": mcr_qrt_s25,
        "scr_nonvie_qrt": scr_nonvie_qrt, "vision": vision,
    }


# ---------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------

def croiser_sources(valeurs, extras):
    """Compare, quand 2+ sources existent pour le même concept, qu'elles
    concordent (tolérance 2%, cf. imprécision attendue d'une lecture
    vision vs une cellule QRT exacte). N'échoue jamais le script — journal
    imprimé, jugement laissé à l'étape 3.4 (contrôles actuariels)."""
    rapport = []

    # scr_total : 3 sources QRT indépendantes, désormais TOUTES réelles
    # (le bug de résolution de sous-feuille corrigé, Décision 055, donne
    # accès à S.25.05.22.02 — plus d'"audit manuel" en dur ici).
    scr_total_qrt = extras["scr_total_qrt"]
    rapport.append(("scr_total", "S.23.01/R0680", scr_total_qrt,
                     "S.25.05.22.02/R0220", extras["scr_total_qrt_s25_R0220"]))
    rapport.append(("scr_total (bis)", "S.23.01/R0680", scr_total_qrt,
                     "S.25.05.22.02/R0570", extras["scr_total_qrt_s25_R0570"]))

    # mcr : S.23.01/R0610 vs S.25.05.22.02/R0470 — nouveau croisement,
    # possible seulement depuis la correction du bug de sous-feuille.
    rapport.append(("mcr", "S.23.01/R0610", extras["mcr_qrt"],
                     "S.25.05.22.02/R0470", extras["mcr_qrt_s25_R0470"]))

    # scr_souscription_nonvie : S.25.05.22.01/R0310 (donnée réelle du
    # corpus désormais) vs picture_75 (concordance 2-sur-3 déjà appliquée
    # en amont dans lire_picture_75 — ici on revérifie juste l'accord avec
    # le QRT, pour la traçabilité du rapport).
    scr_nonvie_qrt = extras["scr_nonvie_qrt"]
    scr_nonvie_vision = extras["vision"].get("scr_souscription_nonvie")
    rapport.append(("scr_souscription_nonvie", "S.25.05.22.01/R0310", scr_nonvie_qrt,
                     "picture_75.png (valeur retenue par concordance 2-sur-3)", scr_nonvie_vision))

    print("\n" + "=" * 70)
    print("CROISEMENT DES SOURCES (concordance attendue, tolérance 2%)")
    print("=" * 70)
    tout_ok = True
    for kpi, src_a, val_a, src_b, val_b in rapport:
        if val_b is None:
            print(f"  {kpi:28} : {src_b} non disponible — pas de croisement possible")
            continue
        ecart_pct = abs(val_a - val_b) / val_a * 100 if val_a else float("inf")
        statut = "OK" if ecart_pct <= 2.0 else "ÉCART"
        if statut != "OK":
            tout_ok = False
        print(f"  {kpi:28} : {src_a}={val_a:,.0f}  vs  {src_b}={val_b:,.0f}  (écart {ecart_pct:.2f}%) [{statut}]")
    return tout_ok


# ---------------------------------------------------------------------
# Insertion en base
# ---------------------------------------------------------------------

def inserer_en_base(valeurs):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    company_id = conn.execute("SELECT id FROM companies WHERE name = ?", (COMPANY_NAME,)).fetchone()
    if company_id is None:
        raise RuntimeError(f"Entreprise {COMPANY_NAME!r} absente de companies — lance init_kpi_db.py d'abord")
    company_id = company_id[0]

    defs_par_nom = {d["kpi_name"]: d for d in KPI_DEFINITIONS}

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
    print("RÉSUMÉ — 22 KPIs Groupama 2025")
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
    valeurs, extras = extraire_tout()
    tout_ok = croiser_sources(valeurs, extras)
    lignes_resume = inserer_en_base(valeurs)
    afficher_resume(lignes_resume)
    if not tout_ok:
        print("\n>>> ATTENTION — au moins un croisement de sources a un écart > 2%, voir détail ci-dessus.")
