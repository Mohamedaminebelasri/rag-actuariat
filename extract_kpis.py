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
sys.path.insert(0, str(TEST_MARKDROP))
from kpi_definitions import KPI_DEFINITIONS
from kpi_qrt_mapping import KPI_QRT_MAPPING, variantes_disponibles
import paddleocr_reader
from paddleocr_reader import lire_image, valeur_a_droite_du_code, valeur_sous_label

# Pré-chargement FORCÉ de PaddleOCR ICI, avant l'import de detecter_templates
# (qui importe ingest.py, donc Docling/transformers/torch) — bug d'environnement
# trouvé en réel (Décision 057) : `from paddleocr import PaddleOCR` plante avec
# `ValueError: torch.__spec__ is not set` si Docling importe torch EN PREMIER
# (état partiellement initialisé qui casse la vérification lazy de paddlex/
# modelscope). Contournement : forcer l'import PaddleOCR AVANT tout import
# lié à Docling, pas un correctif de fond (signalé pour investigation future).
paddleocr_reader._get_pipeline()

from detecter_templates import detecter_templates


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


def sommer_cellules_tolerant(elements, specs):
    """Comme sommer_cellules, mais NE FAIT PAS échouer toute la somme si
    une ligne est trouvée avec le bon libellé mais SANS valeur (cellule
    vide dans le PDF source — cas réel : CNP n'a pas de provisions
    "non-vie pure", seulement "santé similaire non-vie"/"vie"/"UC", cf.
    Décision 060) — cette ligne contribue alors 0, comme demandé
    explicitement ("somme uniquement ceux qui ont une valeur"). Un
    DÉSACCORD de libellé (vraie erreur, pas juste une case vide) continue
    en revanche à faire échouer, même discipline que sommer_cellules."""
    total = 0.0
    for code_ligne, libelle_attendu in specs:
        trouve_avec_bon_libelle = False
        for e in elements:
            lignes = e["contenu"].get("lignes", {})
            if code_ligne not in lignes:
                continue
            row = lignes[code_ligne]
            libelle = row["libelle_officiel"] or ""
            if libelle_attendu.lower() not in libelle.lower():
                raise KpiIntrouvable(f"{code_ligne} : libellé {libelle!r} ne contient pas {libelle_attendu!r}")
            trouve_avec_bon_libelle = True
            if "C0010" in row["valeurs"]:
                total += _vers_float(row["valeurs"]["C0010"]["valeur_brute"])
            break
        if not trouve_avec_bon_libelle:
            raise KpiIntrouvable(f"{code_ligne} introuvable (ni avec valeur ni vide) dans aucun élément fourni")
    return total


def sommer_toutes_colonnes(elements, specs, exclure_total=False):
    """Comme sommer_cellules, mais somme TOUTES les colonnes présentes de
    chaque ligne (pas seulement C0010) — nécessaire pour S.05.01 où les
    lignes de branches (direct/réassurance) sont ventilées sur plusieurs
    colonnes de ligne d'activité, jamais une seule colonne "Total".

    Un élément dont le libellé NE correspond PAS est simplement IGNORÉ
    (pas une erreur immédiate) — bug réel trouvé sur CNP (Décision 060) :
    quand une sous-feuille ambiguë est tentée sur PLUSIEURS candidats
    (cf. resoudre_sous_feuille, Décision 055), la même page physique peut
    apparaître comme élément sous 2 clés de template différentes, l'une
    correcte (libellé attendu) et l'autre un doublon mal étiqueté (le
    dictionnaire de l'autre sous-feuille ne connaît pas ce code, donc
    "(code absent du dictionnaire EIOPA)") — la 1re version levait une
    erreur dès la rencontre du doublon, avant même d'atteindre le bon
    élément. La ligne ENTIÈRE échoue seulement si AUCUN élément n'a le
    bon libellé pour ce code."""
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
                continue
            # exclure_total (Décision 060) : certains documents (CNP) ont
            # une colonne "Total" DÉJÀ PEUPLÉE en plus des colonnes par
            # ligne d'activité (vérifié : C0200 = C0010+C0020+C0030
            # exactement sur S.05.01.02.01 de CNP) — sommer "toutes les
            # colonnes" y double-compte. MAIS Groupama (vérifié en
            # régression réelle, pas supposé) a l'inverse : certaines
            # lignes n'ont de valeur QUE dans la colonne "Total" (colonnes
            # par ligne d'activité vides) — l'exclure y donnerait 0,
            # divisant le résultat par 2. Pas de règle universelle
            # observée : contrôlé au cas par cas via le paramètre
            # `exclure_total`, jamais activé par défaut (comportement
            # historique de Groupama préservé).
            for cellule in row["valeurs"].values():
                if exclure_total and (cellule.get("libelle_colonne") or "").strip().lower() == "total":
                    continue
                total += _vers_float(cellule["valeur_brute"])
            trouve = True
        if not trouve:
            raise KpiIntrouvable(f"{code_ligne} introuvable avec le libellé {libelle_attendu!r} dans aucun élément fourni")
    return total


# ---------------------------------------------------------------------
# Résolution générique via kpi_qrt_mapping.py (Décision 056/057, Phase
# 3.7 étape finale) — remplace les templates Groupama codés en dur.
# ---------------------------------------------------------------------

def resoudre_variantes_qrt(kpi_name, corpus, templates_presents):
    """Essaie CHAQUE variante de KPI_QRT_MAPPING[kpi_name] dont le
    template est présent (variantes_disponibles), dans l'ordre déclaré.
    Retourne la liste de TOUTES celles qui aboutissent (pas seulement la
    1re) — l'appelant décide : 1re = valeur principale, suivantes =
    croisement, ou somme de toutes si le KPI est cumulatif (primes,
    sinistres — vie + non-vie sont 2 variantes complémentaires, pas des
    alternatives). Chaque élément : (valeur, template_id_complet, variante_dict)."""
    resultats = []
    for v in variantes_disponibles(kpi_name, templates_presents):
        template_prefix = v["template"]
        elements = [e for e in corpus if e["template_id"].startswith(template_prefix)]
        if not elements:
            continue
        row, col, libelle = v["row"], v["col"], v["libelle_attendu"]
        try:
            if isinstance(row, list):
                if col == "toutes":
                    valeur = sommer_toutes_colonnes(elements, [(r, libelle) for r in row],
                                                     exclure_total=v.get("exclure_total", False))
                else:
                    valeur = sommer_cellules_tolerant(elements, [(r, libelle) for r in row])
            else:
                valeur = lire_cellule(elements, row, col, libelle)
            template_id_complet = next(e["template_id"] for e in elements if row in e["contenu"].get("lignes", {})) \
                if not isinstance(row, list) else elements[0]["template_id"]
            resultats.append((valeur, template_id_complet, v))
        except KpiIntrouvable:
            continue
    return resultats


def resoudre_par_libelle_modele_interne(kpi_name, corpus, templates_presents):
    """Fallback modèle interne (Décision 056) : les templates S.25.02 à
    S.25.05 n'ont PAS de code R/C universel (vérifié : Groupama R0060 vs
    Yuzzu R0020 pour "Diversification", même concept). Cherche une ligne
    dont le libellé officiel ÉGALE (pas "contient" — cf. Décision 057, bug
    réel trouvé : "Life underwriting risk" est une SOUS-CHAÎNE de "Non-life
    underwriting risk", et "Health underwriting risk" une sous-chaîne de
    "Life & Health underwriting risk" ; la correspondance par sous-chaîne a
    donc mappé scr_souscription_vie/sante sur les mauvaises lignes en test
    réel — cette exactitude stricte a été ajoutée EN RÉACTION à cette
    découverte, pas par précaution théorique) un des libellés attendus
    déclarés pour ce KPI (toutes variantes du mapping confondues), après
    normalisation du préfixe "Risk type – "/"Risk type - " et des espaces.
    UNIQUEMENT parmi les templates modèle interne présents. Retourne
    (valeur, template_id, libelle_trouve) ou None — jamais un code deviné,
    et maintenant jamais un concept voisin pris par erreur."""
    libelles_connus = {
        v["libelle_attendu"].strip().lower() for v in KPI_QRT_MAPPING.get(kpi_name, [])
        if v.get("libelle_attendu")
    }
    if not libelles_connus:
        return None

    def normaliser(libelle):
        l = libelle.strip().lower()
        for prefixe in ("risk type – ", "risk type - ", "risk type — "):
            if l.startswith(prefixe):
                l = l[len(prefixe):]
        return l.strip()

    for e in corpus:
        if not e["template_id"].startswith(("S.25.02", "S.25.03", "S.25.04", "S.25.05")):
            continue
        for row in e["contenu"].get("lignes", {}).values():
            libelle = normaliser(row.get("libelle_officiel") or "")
            if libelle not in libelles_connus:
                continue
            valeurs_cols = row.get("valeurs", {})
            for col_pref in ("C0100", "C0010"):
                if col_pref in valeurs_cols:
                    return _vers_float(valeurs_cols[col_pref]["valeur_brute"]), e["template_id"], row["libelle_officiel"]
            if len(valeurs_cols) == 1:
                seule = next(iter(valeurs_cols.values()))
                return _vers_float(seule["valeur_brute"]), e["template_id"], row["libelle_officiel"]
    return None


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
# Extraction — entièrement pilotée par kpi_qrt_mapping.py +
# detecter_templates.py (Décision 057, Phase 3.7 finale) : AUCUN
# template Groupama codé en dur. Le mapping est parcouru dans l'ordre de
# priorité déclaré ; la 1re variante dont le template est présent ET dont
# la cellule se lit avec succès (libellé vérifié) devient la valeur
# retenue, les suivantes servent de croisement.
# ---------------------------------------------------------------------

def valeur_principale(kpi_name, corpus, templates_presents):
    """1re variante qui aboutit — lève KpiIntrouvable si aucune ne
    marche (comportement identique à lire_cellule direct, juste indirect
    via le mapping)."""
    resultats = resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
    if not resultats:
        raise KpiIntrouvable(f"{kpi_name} : aucune variante du mapping ne matche un template présent")
    valeur, template_id, variante = resultats[0]
    return valeur, template_id, variante


def extraire_tout():
    corpus = charger_corpus()
    templates_presents = {e["template_id"] for e in corpus}

    inventaire = detecter_templates(PDF_SOURCE)
    print(f"[detecter_templates] document_type={inventaire['document_type']!r} "
          f"scr_method={inventaire['scr_method']!r} "
          f"({len(inventaire['templates'])} templates détectés)")

    valeurs = {}       # kpi_name -> (valeur_M€_ou_pct, source_page, note)
    templates_utilises_par_kpi = {}  # kpi_name -> (template_id, méthode) pour le tableau final

    # --- Fonds propres + ratios + SCR/MCR "haut niveau" : S.23.01 (toutes variantes) ---
    for kpi_name, diviseur, multiplicateur in [
        ("ratio_scr", 1, 100), ("ratio_mcr", 1, 100),
        ("scr_total", 1000, 1), ("mcr", 1000, 1),
        ("fonds_propres_eligibles", 1000, 1), ("fonds_propres_t1_nr", 1000, 1),
        ("fonds_propres_t1_r", 1000, 1), ("fonds_propres_t2", 1000, 1), ("fonds_propres_t3", 1000, 1),
    ]:
        resultats = resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            raise KpiIntrouvable(f"{kpi_name} : aucune variante du mapping ne matche un template présent")
        valeur, template_id, variante = resultats[0]
        valeurs[kpi_name] = (
            valeur * multiplicateur / diviseur, 85,
            f"{template_id}/{variante['row']}/{variante['col']} ({variante['variante']})",
        )
        templates_utilises_par_kpi[kpi_name] = (template_id, "texte_natif")
        # Croisement : variantes suivantes qui matchent aussi (ex. Groupama :
        # S.23.01.22 ET S.25.05.22 tous 2 présents pour scr_total/mcr).
        if len(resultats) > 1:
            valeurs[f"__croisement_{kpi_name}"] = resultats[1]

    # --- Provisions : S.02.01, codes identiques solo/groupe (mapping) ---
    best_estimate, be_template, _ = valeur_principale("best_estimate", corpus, templates_presents)
    marge_risque, mr_template, _ = valeur_principale("marge_risque", corpus, templates_presents)
    valeurs["best_estimate"] = (best_estimate / 1000, 79, f"{be_template}, somme 5 lignes Best Estimate (mapping)")
    valeurs["marge_risque"] = (marge_risque / 1000, 79, f"{mr_template}, somme 5 lignes Risk margin (mapping)")
    valeurs["provisions_techniques"] = ((best_estimate + marge_risque) / 1000, 79, "best_estimate + marge_risque")
    templates_utilises_par_kpi["best_estimate"] = (be_template, "texte_natif")
    templates_utilises_par_kpi["marge_risque"] = (mr_template, "texte_natif")
    templates_utilises_par_kpi["provisions_techniques"] = ("calculé", "-")

    # --- Activité : S.05.01, variantes vie + non-vie CUMULATIVES (pas des
    # alternatives — sommées toutes ensemble quand présentes) ---
    for kpi_name in ("primes_acquises_brutes", "charge_sinistres"):
        resultats = resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            raise KpiIntrouvable(f"{kpi_name} : aucune variante du mapping ne matche un template présent")
        total = sum(v for v, _, _ in resultats)
        template_id = resultats[0][1]
        valeurs[kpi_name] = (total / 1000, 80, f"{template_id}, somme {len(resultats)} variante(s) (mapping)")
        templates_utilises_par_kpi[kpi_name] = (template_id, "image")

    # --- Niveau 4 : picture_75.png — 3 sources indépendantes, concordance 2-sur-3.
    # Sert de fallback pour les 6 KPIs SCR détaillés : d'abord tenté via le
    # mapping (formule standard S.25.01, ou libellé en modèle interne) ;
    # sur Groupama (modèle interne, aucun libellé standard trouvé, cf.
    # Décision 056), les 2 tentatives échouent proprement et on retombe
    # ici — comportement inchangé depuis Décision 055 pour ce document.
    vision, details_vision = lire_picture_75()
    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie"):
        qrt_direct = resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        libelle_fallback = None if qrt_direct else resoudre_par_libelle_modele_interne(kpi_name, corpus, templates_presents)
        if qrt_direct:
            valeur, template_id, variante = qrt_direct[0]
            valeurs[kpi_name] = (valeur / 1000, 85, f"{template_id}/{variante['row']} (mapping, code R/C)")
            templates_utilises_par_kpi[kpi_name] = (template_id, "texte_natif/image")
        elif libelle_fallback:
            valeur, template_id, libelle = libelle_fallback
            valeurs[kpi_name] = (valeur / 1000, 87, f"{template_id}, libellé {libelle!r} (fallback modèle interne)")
            templates_utilises_par_kpi[kpi_name] = (template_id, "image, résolu par libellé")
        else:
            v = vision.get(kpi_name)
            valeurs[kpi_name] = (v / 1000 if v is not None else None, 75, details_vision[kpi_name])
            templates_utilises_par_kpi[kpi_name] = ("picture_75.png", "image (hors QRT)")

    # --- scr_diversification : QRT (via mapping, code Groupama-spécifique
    # S.25.05.22/R0060 déjà déclaré) + PaddleOCR, concordance 2-sur-3 ---
    div_qrt_resultats = resoudre_variantes_qrt("scr_diversification", corpus, templates_presents)
    if not div_qrt_resultats:
        raise KpiIntrouvable("scr_diversification : aucune variante du mapping ne matche (S.25.05.22 attendu)")
    r0060_qrt, div_template_id, div_variante = div_qrt_resultats[0]
    r0060_paddle = lire_r0060_paddleocr()
    print(f"\n  --- Lecture {div_template_id}/{div_variante['row']} (page 87) : 2 sources indépendantes ---")
    r0060_valeur, r0060_confiance, r0060_detail = concordance_2_sur_3(
        "scr_diversification", [("QRT (Gemini VLM, parser corrigé, via mapping)", r0060_qrt), ("PaddleOCR", r0060_paddle)]
    )
    valeurs["scr_diversification"] = (
        r0060_valeur / 1000 if r0060_valeur is not None else None, 87,
        f"{div_template_id}/{div_variante['row']} — {r0060_detail} [confiance {r0060_confiance}]",
    )
    templates_utilises_par_kpi["scr_diversification"] = (div_template_id, "image")

    # --- NULL tranché (Décision 051) ---
    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé trouvé (Décision 051)")
    templates_utilises_par_kpi["resultat_technique"] = ("-", "-")

    extras = {
        "scr_total_qrt": valeurs["scr_total"][0] * 1000,
        "mcr_qrt": valeurs["mcr"][0] * 1000,
        "vision": vision,
        "templates_utilises_par_kpi": templates_utilises_par_kpi,
    }
    if "__croisement_scr_total" in valeurs:
        extras["scr_total_qrt_s25_R0220"] = valeurs.pop("__croisement_scr_total")[0]
    if "__croisement_mcr" in valeurs:
        extras["mcr_qrt_s25_R0470"] = valeurs.pop("__croisement_mcr")[0]
    nonvie_resultats = resoudre_variantes_qrt("scr_souscription_nonvie", corpus, templates_presents)
    extras["scr_nonvie_qrt"] = nonvie_resultats[0][0] if nonvie_resultats else None

    return valeurs, extras


# ---------------------------------------------------------------------
# Cross-validation
# ---------------------------------------------------------------------

def croiser_sources(valeurs, extras):
    """Compare, quand 2+ sources existent pour le même concept, qu'elles
    concordent (tolérance 2%, cf. imprécision attendue d'une lecture
    vision vs une cellule QRT exacte). N'échoue jamais le script — journal
    imprimé, jugement laissé à l'étape 3.4 (contrôles actuariels)."""
    rapport = []

    # scr_total / mcr : croisement entre les 2 premières variantes du
    # mapping dont le template est présent (pour Groupama : S.23.01.22 vs
    # S.25.05.22) — plus aucun template codé en dur ici (Décision 057).
    scr_total_qrt = extras["scr_total_qrt"]
    if "scr_total_qrt_s25_R0220" in extras:
        rapport.append(("scr_total", "1re variante mapping", scr_total_qrt,
                         "2e variante mapping (croisement)", extras["scr_total_qrt_s25_R0220"]))

    if "mcr_qrt_s25_R0470" in extras:
        rapport.append(("mcr", "1re variante mapping", extras["mcr_qrt"],
                         "2e variante mapping (croisement)", extras["mcr_qrt_s25_R0470"]))

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
        if val_a is None or val_b is None:
            print(f"  {kpi:28} : une des 2 sources indisponible — pas de croisement possible")
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
