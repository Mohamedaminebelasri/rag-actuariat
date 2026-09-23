# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier orchestre l'ensemble du traitement d'un PDF, en particulier
# les pages spéciales appelées QRT (des tableaux réglementaires très
# normés) — il s'appuie sur plusieurs petits fichiers spécialisés listés
# dans GUIDE_PROJET.md.
# ------------------------------------------------------------------
"""Orchestrateur unique : PDF SFCR en entrée -> corpus_final.json en sortie.

    python ingest.py <fichier.pdf>

ingest.py NE FAIT AUCUNE EXTRACTION LUI-MÊME. Il :
  1. trie les pages (triage léger, texte seul, avant tout appel Docling/Gemini)
  2. appelle les outils déjà validés sur les groupes de pages correspondants
  3. assemble les résultats en un corpus unique
  4. produit un rapport de diagnostic

CORRECTION IMPORTANTE (découverte en implémentant) : le triage par simple
recherche du code "S.XX.XX.XX" dans le texte brut rate presque toutes les
pages QRT image-only (le code n'apparaît que DANS L'IMAGE, pas dans la
couche texte, sauf sur S.23.01.22.01). Solution : la page "ANNEXES – QRT
PUBLICS" présente dans ce type de document liste "Annexe N -> code EIOPA"
— on construit cet index d'abord, puis toute page "Annexe N (x/y)" est
résolue via cet index. Vérifié sur le document de test : sans cette
correction, seules 2 pages sur 12 pages QRT réelles étaient détectées.
"""

import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

import fitz  # PyMuPDF — bibliothèque "texte léger" déjà utilisée toute
             # cette session ; remplace pdftotext/pdfplumber suggérés par
             # l'utilisateur, même rôle (texte seul, pas de reconstruction
             # de tableau).

from extract_qrt_s23 import dedupe_words, merge_numeric_fragments
from extract_qrt_s05_gemini import extraire_json
from qrt_checks import detect_column_shifts
from parsers import parse_sommaire_lignes, attribuer_section_id

BASE_DIR = Path(__file__).parent

SOMMAIRE_WORD_RE = re.compile(r"\bsommaire\b", re.IGNORECASE)
DOT_LEADER_RE = re.compile(r"\.{4,}\s*\d{1,4}\b")
QRT_CODE_RE = re.compile(r"\bS\.\d{2}\.\d{2}\.\d{2}(?:\.\d{2})?\b")
ANNEXE_INDEX_ENTRY_RE = re.compile(r"Annexe\s+(\d+)\s*\n\s*(S\.\d{2}\.\d{2}\.\d{2})")
ANNEXE_PAGE_RE = re.compile(r"^Annexe\s+(\d+)\b")
NATIVE_TEXT_THRESHOLD = 500  # caractères ; seuil observé (QRT image-only : ~200 ;
                              # QRT texte natif S.23.01.22.01 : 12 664)

ROW_CODE_RE = re.compile(r"^R\d{4}$")
COL_CODE_RE = re.compile(r"^C\d{4}$")
NUMERIC_FRAGMENT_RE = re.compile(r"^-?\d+([.,]\d+)?$")
MERGE_GAP_PT = 5.0
LINE_TOLERANCE_PT = 1.5
RASTER_ZOOM = 4.0
ROTATION_RATIO_THRESHOLD = 1.0  # h/w de l'image intégrée la plus grande


# ============================================================
# ÉTAPE 1 — TRIAGE
# ============================================================

def build_annexe_index(doc):
    """Parse la page 'ANNEXES – QRT PUBLICS' (index Annexe N -> code EIOPA),
    si présente. Nécessaire car les pages QRT image-only n'ont pas le code
    dans leur propre texte."""
    mapping = {}
    for i in range(doc.page_count):
        texte = doc[i].get_text()
        for m in ANNEXE_INDEX_ENTRY_RE.finditer(texte):
            mapping[int(m.group(1))] = m.group(2)
    return mapping


def classify_pages(pdf_path):
    """Retourne une liste de dicts, un par page :
    {"page": int, "type": "sommaire"|"qrt"|"narratif",
     "texte": str, "template_id": str|None, "resolution": str}
    """
    doc = fitz.open(str(pdf_path))
    annexe_index = build_annexe_index(doc)
    classification = []

    for i in range(doc.page_count):
        page_no = i + 1
        texte = doc[i].get_text()

        est_sommaire_a = bool(SOMMAIRE_WORD_RE.search(texte))
        lignes = [l for l in texte.split("\n") if l.strip()]
        n_dot_leader = sum(1 for l in lignes if DOT_LEADER_RE.search(l))
        ratio_dot_leader = (n_dot_leader / len(lignes)) if lignes else 0
        est_sommaire_b = ratio_dot_leader > 0.5

        codes_distincts = set(QRT_CODE_RE.findall(texte))
        est_index_qrt = len(codes_distincts) >= 3

        m_direct = QRT_CODE_RE.search(texte)
        m_annexe = None
        for l in lignes:
            mm = ANNEXE_PAGE_RE.match(l)
            if mm:
                m_annexe = int(mm.group(1))
                break

        resolution = None
        if est_sommaire_a or est_sommaire_b:
            page_type, template_id = "sommaire", None
        elif est_index_qrt:
            page_type, template_id = "sommaire", None
            resolution = f"index QRT détecté ({len(codes_distincts)} codes S.XX.XX.XX distincts) — page exclue, pas un template"
        elif m_direct:
            page_type, template_id = "qrt", m_direct.group(0)[:10]
            resolution = "code trouvé directement dans le texte natif"
        elif m_annexe is not None and m_annexe in annexe_index:
            page_type, template_id = "qrt", annexe_index[m_annexe]
            resolution = f"résolu via index des annexes (Annexe {m_annexe})"
        else:
            page_type, template_id = "narratif", None

        classification.append({
            "page": page_no, "type": page_type, "texte": texte,
            "template_id": template_id, "n_caracteres": len(texte),
            "resolution": resolution,
        })

    doc.close()
    return classification


def extraire_metadata_couverture(classification):
    """[heuristique, NON vérifiée sur un 2e document] Cherche entité +
    année sur les 3 premières pages. Motif calé sur ce document précis
    ("GROUPE X", "31 DECEMBRE ANNEE")."""
    entite, annee = None, None
    for p in classification[:3]:
        m_annee = re.search(r"31\s+DECEMBRE\s+(\d{4})", p["texte"], re.IGNORECASE)
        if m_annee and annee is None:
            annee = m_annee.group(1)
        m_entite = re.search(r"GROUPE\s+([A-ZÀ-Ü]+)", p["texte"])
        if m_entite and entite is None:
            entite = f"Groupe {m_entite.group(1).title()}"
    return entite, annee


def _sous_pdf(pdf_path, pages, dest_path):
    """Matérialise un sous-PDF contenant uniquement `pages` (liste de
    numéros 1-indexés, pas nécessairement contiguës)."""
    doc = fitz.open(str(pdf_path))
    doc.select([p - 1 for p in pages])
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(dest_path))
    doc.close()


# ============================================================
# ÉTAPE 2a — PAGES NARRATIVES  [réutilise run_test.py, dedup.py,
# build_final.py, verify_final.py tels quels, en sous-processus,
# sur un sous-PDF ne contenant QUE les pages narratives (sommaire
# et QRT déjà exclus PAR LE TRIAGE, avant tout appel Docling)]
# ============================================================

def process_narrative(pdf_path, pages_narratives, work_dir):
    if not pages_narratives:
        return [], {"ecarts_totaux": [], "images_non_logo": []}, 0.0

    t0 = time.time()
    sub_pdf = work_dir / "narratif.pdf"
    narratif_dir = work_dir / "narratif"
    _sous_pdf(pdf_path, pages_narratives, sub_pdf)

    for script in ("run_test.py", "dedup.py", "build_final.py", "verify_final.py"):
        args = [sys.executable, str(BASE_DIR / script)]
        if script in ("run_test.py", "build_final.py"):
            args += [str(sub_pdf), str(narratif_dir)]
        else:
            args += [str(narratif_dir)]
        print(f"[narratif] lancement {script}...")
        subprocess.run(args, cwd=str(BASE_DIR), check=True)

    with open(narratif_dir / "resultat_final.json", encoding="utf-8") as f:
        resultat = json.load(f)
    with open(narratif_dir / "verif_totaux.json", encoding="utf-8") as f:
        verif_totaux = json.load(f)
    dedup_groups_path = narratif_dir / "dedup_groups.json"
    dedup_groups = None
    if dedup_groups_path.exists():
        with open(dedup_groups_path, encoding="utf-8") as f:
            dedup_groups = json.load(f)

    def page_reelle(page_locale):
        """Remappe un numéro de page local au sous-PDF temporaire (1-indexé,
        tel que produit par run_test.py/build_final.py/verify_final.py sur
        `sub_pdf`) vers le numéro de page réel dans le document source.
        `pages_narratives` préserve l'ordre passé à _sous_pdf/doc.select,
        donc page locale i -> pages_narratives[i-1]. Nécessaire dès que les
        pages narratives ne sont pas contiguës (sommaire/QRT intercalés) —
        bug découvert le 2026-08-18 : sans ce remap, page_source pointait
        silencieusement vers le mauvais numéro de page dès la 1ère page
        non contiguë."""
        return pages_narratives[page_locale - 1]

    section_par_page = attribuer_section_id(resultat["pages"])

    elements = []
    for p in resultat["pages"]:
        elements.append({
            "page_source": page_reelle(p["page"]),
            "type": "narratif",
            "section_id": section_par_page.get(p["page"]),
            "contenu": {"texte": p["texte"], "tableaux": p["tableaux"], "images": p["images"]},
        })

    ecarts_totaux = [{**e, "page": page_reelle(e["page"])} for e in verif_totaux["resultats"] if not e["ok"]]
    images_non_logo = []
    if dedup_groups:
        for groupe in dedup_groups["groupes"][1:]:
            for m in groupe:
                images_non_logo.append({"page": page_reelle(m["page"]), "index": m["index"], "fichier": m["filename"]})

    temps = time.time() - t0
    return elements, {"ecarts_totaux": ecarts_totaux, "images_non_logo": images_non_logo}, temps


# ============================================================
# ÉTAPE 2b — PAGES QRT
# ============================================================

def grouper_sous_feuilles_fusionnables(template_dict):
    """Regroupe les sous-feuilles d'un template dont les row_codes sont
    STRICTEMENT IDENTIQUES — signal STRUCTUREL, pas une règle métier
    devinée (ex. pas de mot-clé "vie"/"non-vie" codé en dur). Des
    sous-feuilles à row_codes identiques sont des variantes de colonnes
    d'un même tableau (ex. S.05.02.04 : .01/.02/.03 partagent 18 codes-
    ligne identiques, .04/.05/.06 en partagent 13 identiques — confirmé
    visuellement : chaque groupe correspond à UNE page physique du SFCR
    combinant les 3 sous-feuilles). Retourne une liste de groupes (listes
    triées de sheet_keys), un par ensemble de row_codes partagé par PLUS
    D'UNE sous-feuille. Vérifié : ne s'active QUE pour S.05.02.04 parmi
    les 4 templates multi-sous-feuilles du dictionnaire actuel — S.05.01.02,
    S.23.01.22 et S.25.05.22 n'ont pas cette propriété (row_codes tous
    distincts), donc ce mécanisme ne les affecte jamais."""
    par_signature = defaultdict(list)
    for sheet_key, sheet_dict in template_dict.items():
        signature = frozenset(sheet_dict["row_codes"].keys())
        if not signature:
            continue  # template sans code de ligne (S.32.01.22) : hors scope
        par_signature[signature].append(sheet_key)
    groupes = [sorted(v) for v in par_signature.values() if len(v) > 1]
    groupes.sort(key=lambda g: g[0])
    return groupes


def fusionner_sheet_dicts(groupe, template_dict):
    """Construit un sheet_dict combiné pour un groupe de sous-feuilles à
    row_codes identiques (cf. grouper_sous_feuilles_fusionnables) :
    row_codes pris du 1er membre (identiques par construction dans le
    groupe), col_codes/col_groups = union des colonnes de CHAQUE membre
    (chacun apporte sa ou ses colonnes propres, disjointes)."""
    premier = template_dict[groupe[0]]
    col_codes, col_groups = {}, {}
    titres = []
    for sk in groupe:
        sd = template_dict[sk]
        col_codes.update(sd["col_codes"])
        col_groups.update(sd["col_groups"])
        titres.append(sd.get("titre") or sk)
    return {
        "titre": " + ".join(titres),
        "row_codes": premier["row_codes"],
        "col_codes": col_codes,
        "col_groups": col_groups,
    }


def _cle_composite(template_id, groupe):
    suffixes = "+".join(sk[len(template_id) + 1:] for sk in groupe)
    return f"{template_id}.{suffixes}"


def resoudre_sous_feuille(page, template_id, qrt_dict):
    """Détermine la ou les sous-feuille(s) EIOPA (ex. 'S.23.01.22.01') pour
    une page QRT donnée. Retourne une LISTE de (sheet_key|None, methode,
    sheet_dict_override) — normalement 1 élément ; PLUSIEURS uniquement
    dans le cas "AUCUN indice trouvé" (cf. plus bas) quand le template a
    plusieurs sous-feuilles NON regroupables (row_codes distincts) : on
    tente alors TOUTES les candidates plutôt que de deviner la première
    (bug réel trouvé et corrigé, cf. DECISIONS.md — page 87 du SFCR
    Groupama 2025, S.25.05.22, où le libellé "S.25.05.22.01 -
    S.25.05.22.02" imprimé sur la page N'EST MÊME PAS DU TEXTE EXTRACTIBLE
    — la page entière est une image incrustée, donc AUCUNE regex sur le
    texte de la page ne peut jamais désambiguïser ce cas ; seul un
    changement du comportement par défaut — tenter les deux plutôt qu'une
    seule — peut le corriger, de façon générale, pas seulement pour ce
    document). sheet_dict_override est None dans le cas normal (le
    sheet_dict se trouve alors via qrt_dict[template_id][sheet_key]) —
    non-None quand plusieurs sous-feuilles ont dû être fusionnées (cf.
    grouper_sous_feuilles_fusionnables) OU quand toutes les candidates
    isolées sont tentées (sheet_dict_override reste None dans ce dernier
    cas, chaque sheet_key candidate garde son propre sheet_dict normal)."""
    template_dict = qrt_dict.get(template_id, {})
    sheet_keys = sorted(template_dict.keys())
    if not sheet_keys:
        return [(None, "template absent du dictionnaire", None)]
    if len(sheet_keys) == 1:
        return [(sheet_keys[0], "unique sous-feuille disponible pour ce template", None)]

    groupes = grouper_sous_feuilles_fusionnables(template_dict)

    m = re.search(rf"{re.escape(template_id)}\s*-\s*0?(\d+)", page["texte"])
    if m:
        numero = int(m.group(1))
        # Piège vérifié (S.05.02.04, document 2024, page 79) : le numéro
        # "-NN" imprimé sur la page ne désigne PAS toujours littéralement
        # la sous-feuille dictionnaire .NN — pour un template dont les
        # sous-feuilles se regroupent par row_codes identiques, ce numéro
        # désigne en réalité la Nième PAGE PHYSIQUE du template (donc le
        # Nième GROUPE), exactement comme pour l'heuristique "(x/y)"
        # ci-dessous. Preuve concrète : page 79 porte le libellé
        # "S.05.02.04 - 02" mais son contenu réel est le groupe "vie"
        # (.04/.05/.06) — PAS la sous-feuille .02 seule (qui appartient au
        # groupe .01/.02/.03). Traiter le numéro comme un index de GROUPE
        # (quand des groupes existent) plutôt que comme un suffixe littéral
        # résout ce cas ; sinon, comportement inchangé (lecture directe).
        if groupes and 1 <= numero <= len(groupes):
            groupe = groupes[numero - 1]
            cle = _cle_composite(template_id, groupe)
            return [(cle, (
                f"libellé natif '{template_id} - {m.group(1)}' interprété comme la page physique "
                f"n°{numero} du template (pas comme la sous-feuille .{numero:02d} littérale) — "
                f"{len(groupe)} sous-feuilles à row_codes identiques fusionnées ({', '.join(groupe)}), "
                "signal structurel vérifié"
            ), fusionner_sheet_dicts(groupe, template_dict))]
        candidate = f"{template_id}.{numero:02d}"
        if candidate in template_dict:
            return [(candidate, "code de sous-feuille trouvé dans le texte natif", None)]

    m2 = re.search(r"\((\d+)/(\d+)\)", page["texte"])
    if m2:
        idx = int(m2.group(1)) - 1
        total = int(m2.group(2))
        if groupes and len(groupes) == total and 0 <= idx < len(groupes):
            groupe = groupes[idx]
            cle = _cle_composite(template_id, groupe)
            return [(cle, (
                f"page {m2.group(1)}/{m2.group(2)} — {len(groupe)} sous-feuilles à row_codes "
                f"identiques détectées et fusionnées ({', '.join(groupe)}) — signal structurel "
                "vérifié, pas une supposition de position"
            ), fusionner_sheet_dicts(groupe, template_dict))]
        if 0 <= idx < len(sheet_keys):
            return [(sheet_keys[idx], (f"déduite du suffixe ({m2.group(1)}/{m2.group(2)}) sur la "
                                      f"page — HEURISTIQUE, pas une lecture directe du code"), None)]

    # AUCUN INDICE TEXTUEL — au lieu de deviner sheet_keys[0] (comportement
    # d'origine), tenter TOUTES les sous-feuilles candidates : chaque groupe
    # fusionnable (row_codes identiques, cf. grouper_sous_feuilles_fusionnables)
    # une fois, chaque sous-feuille isolée (row_codes distincts, jamais
    # regroupée) une fois. Bug réel corrigé ici (cf. docstring de la
    # fonction) : sur une page sans AUCUN texte extractible (page entière =
    # image incrustée), aucune regex ne peut jamais distinguer entre
    # plusieurs sous-feuilles non regroupées — deviner la première en
    # ratait systématiquement les autres en silence. La complétude par
    # sous-feuille (déjà calculée en aval, process_qrt) indique ensuite
    # laquelle a réellement des données trouvées.
    sheets_dans_un_groupe = {sk for g in groupes for sk in g}
    candidats_isoles = [sk for sk in sheet_keys if sk not in sheets_dans_un_groupe]
    n_candidats_total = len(candidats_isoles) + len(groupes)

    if n_candidats_total <= 1:
        # Cas normal (pas de multiplicité réelle malgré len(sheet_keys)>1 —
        # ex. tous les sheet_keys appartiennent à un seul et même groupe
        # fusionnable) : comportement inchangé, 1 seule candidate.
        seule = candidats_isoles[0] if candidats_isoles else _cle_composite(template_id, groupes[0])
        override = None if candidats_isoles else fusionner_sheet_dicts(groupes[0], template_dict)
        return [(seule, "AUCUN indice trouvé — 1ère (et seule) sous-feuille prise par défaut — "
                         "À VÉRIFIER MANUELLEMENT", override)]

    raison = (f"AUCUN indice trouvé — {n_candidats_total} sous-feuilles candidates non regroupables, "
              "TOUTES tentées (pas de devinette sur une seule, cf. Décision 055) — "
              "À VÉRIFIER MANUELLEMENT quelles candidates ont réellement des données")
    resultats = [(sk, raison, None) for sk in candidats_isoles]
    for g in groupes:
        resultats.append((_cle_composite(template_id, g), raison, fusionner_sheet_dicts(g, template_dict)))
    return resultats


def extract_qrt_native(page, sheet_dict, sheet_key):
    """[PROUVÉ] Généralisation directe de extract_qrt_s23.py : mots
    positionnés (x,y), codes R/C associés par proximité, pas d'ordre de
    lecture séquentiel."""
    row_labels = sheet_dict["row_codes"]
    col_labels = sheet_dict["col_codes"]

    words = dedupe_words(page.get_text("words"))

    header_words = [(x0, y0, x1, y1, t) for (x0, y0, x1, y1, t) in words if COL_CODE_RE.match(t)]
    col_x = {t: (x0 + x1) / 2 for (x0, y0, x1, y1, t) in header_words}
    # Bug réel trouvé et corrigé (Décision 059, test CNP) : une feuille à
    # PLUSIEURS sections d'en-tête de colonnes (ex. S.23.01.01.01 — un
    # en-tête 5 colonnes C0010-C0050 en haut, un en-tête C0060 seul plus
    # bas pour la réserve de réconciliation) faisait passer header_y_max
    # au MAX de tous les en-têtes trouvés sur la page, excluant alors
    # TOUTES les lignes situées entre le 1er en-tête et le dernier (ici :
    # R0500-R0640, silencieusement perdues). Le MIN (1er en-tête, celui
    # qui sépare le titre de page du tableau) est le seuil réellement
    # voulu — revérifié fonctionnellement sur CNP ET Groupama (aucune
    # régression, cf. Décision 059) avant d'être adopté.
    header_y_max = min((y1 for _, _, _, y1, _ in header_words), default=0)

    row_words = [(x0, y0, x1, y1, t) for (x0, y0, x1, y1, t) in words
                 if ROW_CODE_RE.match(t) and y0 > header_y_max]
    rows_by_code = {}
    for x0, y0, x1, y1, t in row_words:
        if t not in rows_by_code:
            rows_by_code[t] = (x0, y0, x1, y1)

    resultat = {}
    for code, (rx0, ry0, rx1, ry1) in sorted(rows_by_code.items()):
        frags = []
        for x0, y0, x1, y1, t in words:
            if x0 <= rx1 or abs(y0 - ry0) > LINE_TOLERANCE_PT:
                continue
            if NUMERIC_FRAGMENT_RE.match(t):
                frags.append((x0, x1, t))
        merged = merge_numeric_fragments(frags)
        valeurs = {}
        for x_centre, text in merged:
            if not col_x:
                continue
            nearest_col = min(col_x, key=lambda c: abs(col_x[c] - x_centre))
            valeurs[nearest_col] = text
        resultat[code] = {
            "libelle_officiel": row_labels.get(code, "(code absent du dictionnaire EIOPA)"),
            "valeurs": {c: {"libelle_colonne": col_labels.get(c, c), "valeur_brute": v}
                        for c, v in valeurs.items()},
        }

    codes_attendus = set(row_labels.keys())
    codes_trouves = set(resultat.keys())
    return {
        "sheet_key": sheet_key,
        "lignes": resultat,
        "completude": {
            "n_attendus": len(codes_attendus), "n_trouves": len(codes_trouves),
            "manquants": sorted(codes_attendus - codes_trouves),
            "inattendus": sorted(codes_trouves - codes_attendus),
        },
        "decalages_colonne_suspectes": [],  # non pertinent : texte natif, pas de VLM
    }


def detect_rotation_needed(doc, page_index, threshold=ROTATION_RATIO_THRESHOLD):
    """Le flag natif page.rotation (/Rotate) est à 0 sur tout ce document
    (vérifié) — inutile pour détecter la rotation. En pratique, les
    tableaux QRT larges sont ici intégrés comme une image UNIQUE pré-
    tournée à 90° dans une page portrait (confirmé visuellement sur 4
    pages : le ratio hauteur/largeur de l'image intégrée la plus grande
    dépasse 1.0 quand c'est le cas, contre <1.0 pour les pages déjà bien
    orientées — discriminant validé sur 5 pages, 4 tournées + 1 non)."""
    page = doc[page_index]
    imgs = page.get_images(full=True)
    plus_grande = None
    for im in imgs:
        xref = im[0]
        base = doc.extract_image(xref)
        w, h = base["width"], base["height"]
        if plus_grande is None or w * h > plus_grande[0]:
            plus_grande = (w * h, w, h)
    if plus_grande is None:
        return False
    _, w, h = plus_grande
    return (h / w) > threshold


def build_prompt_qrt(sheet_key, colonnes_ordonnees, col_labels, row_labels):
    """Prompt construit dynamiquement à partir du dictionnaire EIOPA pour
    CE sheet_key précis (avant : le nom de template et les exemples de
    codes étaient ceux, codés en dur, de S.05.01.02.01 dans
    extract_qrt_s05_gemini.build_prompt — envoyés tels quels à Gemini
    même pour les autres templates). Deux branches :
    - row_labels non vide : liste EXPLICITEMENT les codes officiels
      attendus (au lieu de "R0110, R0200, etc.") pour empêcher Gemini de
      transcrire un autre schéma de numérotation (bug observé : codes
      Vie/.02 confondus avec Non-Vie/.01).
    - row_labels vide (ex. S.32.01.22, liste d'entités) : prompt sans
      aucune mention de code de ligne, pour empêcher l'invention de
      R00xx qui n'existent pas dans ce template."""
    lignes_cols = "\n".join(f'- {c} ({col_labels.get(c, c)})' for c in colonnes_ordonnees)

    if row_labels:
        codes_attendus = sorted(row_labels.keys())
        lignes_codes = "\n".join(f'- {c} : {row_labels[c]}' for c in codes_attendus)
        return (
            f"Voici un tableau du template réglementaire EIOPA {sheet_key}. "
            f"Il a {len(colonnes_ordonnees)} colonnes numériques, dans cet ordre "
            f"de gauche à droite :\n{lignes_cols}\n\n"
            f"Ce template a EXACTEMENT ces {len(codes_attendus)} codes de ligne "
            "officiels, chacun avec son libellé — n'utilise AUCUN autre code, "
            "n'en invente aucun, ne confonds pas avec la numérotation d'un "
            f"autre sous-modèle de ce même template :\n{lignes_codes}\n\n"
            'Pour chaque code de cette liste visible dans l\'image, donne sa '
            'ligne sous forme JSON : [{"code": "...", "libelle": "...", '
            + ", ".join(f'"{c}": <valeur ou null>' for c in colonnes_ordonnees)
            + "}, ...]. Si un code de la liste n'apparaît pas dans l'image, "
            "omets-le simplement. Si une cellule est vide ou grisée/noircie "
            "dans l'image, mets null — ne devine jamais une valeur absente. "
            "Respecte scrupuleusement l'alignement colonne par colonne : "
            "chaque valeur doit être associée au code de colonne exact sous "
            "lequel elle est imprimée, pas à sa position dans la ligne. "
            "Transcris exactement ce qui est visible, ne calcule rien."
        )

    return (
        f"Voici un tableau du template réglementaire EIOPA {sheet_key}. "
        "CE TABLEAU N'A PAS DE CODE DE LIGNE (pas de R00xx) : chaque ligne "
        "est une entrée distincte (ex. une entité), sans identifiant officiel "
        "de ligne. N'invente AUCUN code de ligne, ne mets jamais de champ "
        f'"code". Il a {len(colonnes_ordonnees)} colonnes, dans cet ordre de '
        f"gauche à droite :\n{lignes_cols}\n\n"
        'Extrais chaque ligne du tableau sous forme JSON : [{'
        + ", ".join(f'"{c}": <valeur ou null>' for c in colonnes_ordonnees)
        + "}, ...], une entrée par ligne du tableau, dans l'ordre où elles "
        "apparaissent. Si une cellule est vide, mets null. Transcris "
        "exactement ce qui est visible, ne calcule rien."
    )


async def extract_qrt_gemini(pdf_path, page_index, sheet_dict, sheet_key, work_dir):
    """[PROUVÉ dans son principe sur 3 templates] Généralisation de
    extract_qrt_s25_gemini.py : prompt Gemini construit dynamiquement
    depuis les colonnes ET les codes du dictionnaire (build_prompt_qrt),
    check de décalage de colonne par groupe EIOPA (qrt_checks corrigé)."""
    from io import BytesIO

    from markdrop.parse import AIProcessor, AIProvider, ProcessorConfig
    from PIL import Image

    row_labels = sheet_dict["row_codes"]
    col_labels = sheet_dict["col_codes"]
    col_groups = sheet_dict["col_groups"]
    colonnes_ordonnees = sorted(col_labels.keys(), key=lambda c: int(re.match(r"C(\d+)", c).group(1)))

    doc = fitz.open(str(pdf_path))
    page = doc[page_index]
    rotation_appliquee = detect_rotation_needed(doc, page_index)
    mat = fitz.Matrix(RASTER_ZOOM, RASTER_ZOOM)
    pix = page.get_pixmap(matrix=mat)
    img_dir = work_dir / "qrt_images"
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"page_{page_index + 1}_{sheet_key}.png"
    if rotation_appliquee:
        im = Image.open(BytesIO(pix.tobytes("png")))
        im.rotate(90, expand=True).save(str(img_path))
    else:
        pix.save(str(img_path))
    doc.close()

    prompt = build_prompt_qrt(sheet_key, colonnes_ordonnees, col_labels, row_labels)
    config = ProcessorConfig(input_path="", output_dir=str(work_dir),
                              ai_provider=AIProvider.GEMINI, image_prompt=prompt)
    processor = AIProcessor(config)
    reponse_brute = await processor.process_image(str(img_path))

    try:
        lignes = extraire_json(reponse_brute)
    except (json.JSONDecodeError, AttributeError) as e:
        return {
            "sheet_key": sheet_key, "lignes": {}, "reponse_brute": reponse_brute,
            "completude": {"erreur": f"JSON non parsable : {e!r}"},
            "decalages_colonne_suspectes": [],
        }

    decalages = detect_column_shifts(lignes, col_groups)

    if not row_labels:
        # Template SANS code-ligne (ex. S.32.01.22, liste d'entités) : pas
        # de clé naturelle pour indexer par "code" comme pour les templates
        # R00xx. Stocké dans "entites" (liste, ordre d'apparition) plutôt
        # que "lignes" (dict par code), qui n'a pas de sens ici.
        entites = [
            {c: {"libelle_colonne": col_labels.get(c, c), "valeur_brute": l.get(c)}
             for c in colonnes_ordonnees if l.get(c) is not None}
            for l in lignes
        ]
        codes_hors_liste = sorted({l["code"] for l in lignes if "code" in l})
        return {
            "sheet_key": sheet_key,
            "entites": entites,
            "completude": {
                "type": "liste_entites_sans_code",
                "n_lignes_trouvees": len(entites),
                "codes_ligne_inattendus": codes_hors_liste,  # devrait rester vide
            },
            "decalages_colonne_suspectes": decalages,
            "image_utilisee": str(img_path),
            "rotation_appliquee": rotation_appliquee,
        }

    lignes_par_code = {l["code"]: l for l in lignes if "code" in l}
    codes_attendus = set(row_labels.keys())
    codes_trouves = set(lignes_par_code.keys())

    resultat = {}
    for code, l in lignes_par_code.items():
        resultat[code] = {
            "libelle_officiel": row_labels.get(code, "(code absent du dictionnaire EIOPA)"),
            "libelle_gemini": l.get("libelle"),
            "valeurs": {c: {"libelle_colonne": col_labels.get(c, c), "valeur_brute": l.get(c)}
                        for c in colonnes_ordonnees if l.get(c) is not None},
        }

    return {
        "sheet_key": sheet_key,
        "lignes": resultat,
        "completude": {
            "n_attendus": len(codes_attendus), "n_trouves": len(codes_trouves),
            "manquants": sorted(codes_attendus - codes_trouves),
            "inattendus": sorted(codes_trouves - codes_attendus),
        },
        "decalages_colonne_suspectes": decalages,
        "image_utilisee": str(img_path),
        "rotation_appliquee": rotation_appliquee,
    }


def _n_elements(resultat):
    """Nombre d'entrées produites par une extraction QRT, quel que soit le
    schéma (liste "entites" pour les templates sans code de ligne, dict
    "lignes" par code R00xx sinon)."""
    if "entites" in resultat:
        return len(resultat["entites"])
    return len(resultat.get("lignes", {}))


def detect_entites_vides_suspectes(resultats, sheet_dicts_effectifs):
    """Filet de sécurité INDÉPENDANT du choix d'extraction (natif vs
    Gemini) : sur un template SANS code de ligne (row_codes vide, ex.
    S.32.01.22 — liste d'entités), la vérification de complétude standard
    est désactivée à raison (rien à comparer à un ensemble de codes
    attendus vide) — mais ça la rend aveugle à une page qui produit 0
    résultat par erreur, puisque 0 attendu / 0 trouvé passe pour
    "complet". Si une page d'un tel template ne produit AUCUNE entité
    alors qu'au moins une AUTRE page du même sheet_key (même document) en
    a produit, c'est suspect : on le signale, sans bloquer et sans
    dépendre du correctif de routage ci-dessus — ce filet doit continuer
    à fonctionner même si un autre bug produit une page vide autrement.

    sheet_dicts_effectifs (pas qrt_dict directement) : les sheet_key
    peuvent être des clés composites issues d'une fusion de sous-feuilles
    (cf. resoudre_sous_feuille), absentes de qrt_dict — sheet_dicts_effectifs
    contient le sheet_dict réellement utilisé pour CHAQUE sheet_key résolu
    pendant cette exécution, composite ou non."""
    par_sheet_key = defaultdict(list)
    for r in resultats:
        row_labels = sheet_dicts_effectifs.get(r["sheet_key"], {}).get("row_codes", {})
        if row_labels:
            continue  # ce filet ne concerne que les templates SANS code de ligne
        par_sheet_key[r["sheet_key"]].append(r)

    signalements = []
    for sheet_key, groupe in par_sheet_key.items():
        comptages = [(r["page"], _n_elements(r["resultat"])) for r in groupe]
        if len(comptages) < 2:
            continue  # une seule page pour ce sheet_key : rien à comparer
        pages_vides = [p for p, n in comptages if n == 0]
        pages_non_vides = [p for p, n in comptages if n > 0]
        if pages_vides and pages_non_vides:
            for p in pages_vides:
                signalements.append({
                    "page": p, "sheet_key": sheet_key,
                    "flag": "VÉRIFICATION MANUELLE REQUISE",
                    "detail": (f"page {p} (template {sheet_key}, sans code de ligne) : 0 entité "
                               f"extraite, alors que d'autres pages du même template en ont trouvé "
                               f"({pages_non_vides}) — la complétude standard ne peut pas détecter "
                               "ce cas (0 attendu/0 trouvé accepté par construction pour ce type de "
                               "template), vérification manuelle requise."),
                })
    return signalements


async def process_qrt(pdf_path, pages_qrt, qrt_dict, work_dir):
    t0 = time.time()
    elements = []
    anomalies = {"sous_feuilles_incertaines": [], "codes_manquants": [], "decalages_colonne": [],
                 "entites_vides_suspectes": []}
    resultats = []  # trace ordonnée pour la fusion de complétude multi-pages, ci-dessous
    # sheet_key -> sheet_dict effectivement utilisé pour cette page (celui de
    # qrt_dict normalement, ou un sheet_dict FUSIONNÉ pour les clés composites
    # issues de resoudre_sous_feuille, ex. "S.05.02.04.01+02+03" — absent de
    # qrt_dict par construction). Sert de référence unique pour tout code qui
    # a besoin de retrouver le sheet_dict d'un sheet_key déjà résolu, plutôt
    # que d'indexer qrt_dict directement (ce qui échouerait sur une clé
    # composite).
    sheet_dicts_effectifs = {}

    doc = fitz.open(str(pdf_path))
    for page in pages_qrt:
        template_id = page["template_id"]
        # resoudre_sous_feuille retourne une LISTE — normalement 1 élément,
        # plusieurs UNIQUEMENT dans le cas "aucun indice, plusieurs
        # sous-feuilles non regroupables" (cf. son docstring, Décision 055) :
        # boucle interne pour traiter chaque candidate comme un élément QRT
        # séparé, produit sur la MÊME page physique.
        candidats = resoudre_sous_feuille(page, template_id, qrt_dict)
        for sheet_key, methode, sheet_dict_override in candidats:
            if sheet_key is None:
                anomalies["sous_feuilles_incertaines"].append({
                    "page": page["page"], "template_id": template_id, "raison": methode,
                })
                continue
            if "À VÉRIFIER" in methode or "HEURISTIQUE" in methode:
                anomalies["sous_feuilles_incertaines"].append({
                    "page": page["page"], "sheet_key": sheet_key, "raison": methode,
                })

            sheet_dict = sheet_dict_override if sheet_dict_override is not None else qrt_dict[template_id][sheet_key]
            sheet_dicts_effectifs[sheet_key] = sheet_dict

            # BUG CONFIRMÉ (cf. DECISIONS.md) : extract_qrt_native est bâti autour
            # de l'ancrage par code R00xx (ROW_CODE_RE) — sur un template SANS
            # code de ligne (row_codes vide, ex. S.32.01.22, liste d'entités), il
            # ne peut structurellement rien trouver et retourne {} en silence,
            # sans qu'aucune anomalie ne soit levée (la complétude est vide des
            # deux côtés). extract_qrt_gemini a déjà une branche dédiée et
            # validée pour ce cas (cf. plus bas, "if not row_labels"). Plutôt que
            # de dupliquer cette logique côté texte natif, on route
            # systématiquement ces templates vers Gemini, quel que soit
            # NATIVE_TEXT_THRESHOLD — scopé aux seuls templates row_codes vide,
            # aucun changement pour les 6 autres.
            sans_code_de_ligne = not sheet_dict["row_codes"]
            if page["n_caracteres"] > NATIVE_TEXT_THRESHOLD and not sans_code_de_ligne:
                pdf_page = doc[page["page"] - 1]
                resultat = extract_qrt_native(pdf_page, sheet_dict, sheet_key)
                resultat["methode_extraction"] = "texte natif (positionnel)"
            else:
                resultat = await extract_qrt_gemini(pdf_path, page["page"] - 1, sheet_dict, sheet_key, work_dir)
                resultat["methode_extraction"] = "Gemini VLM"

            resultat["page_source"] = page["page"]
            resultat["methode_resolution_sous_feuille"] = methode

            contenu = {"completude": resultat["completude"], "methode_extraction": resultat["methode_extraction"]}
            if "entites" in resultat:
                contenu["entites"] = resultat["entites"]
            else:
                contenu["lignes"] = resultat["lignes"]
            elements.append({
                "page_source": page["page"], "type": "qrt", "template_id": sheet_key,
                "contenu": contenu,
            })

            if resultat.get("decalages_colonne_suspectes"):
                anomalies["decalages_colonne"].append({
                    "page": page["page"], "sheet_key": sheet_key,
                    "signalements": resultat["decalages_colonne_suspectes"],
                })

            resultats.append({"page": page["page"], "template_id": template_id,
                           "sheet_key": sheet_key, "resultat": resultat})

    doc.close()

    # Complétude fusionnée : plusieurs pages CONSÉCUTIVES résolues vers le
    # même sheet_key = un même sous-feuillet étalé sur plusieurs pages
    # physiques (ex. S.02.01.02.01 : Actif p.7, Passif p.8). Comparer
    # chaque page séparément aux codes attendus du sheet_key ENTIER est
    # trompeur (chaque page semble ~50% incomplète alors que l'union des
    # deux ne l'est pas). Ne s'applique qu'aux sheet_key à codes-ligne
    # (row_codes non vide) — les listes d'entités (S.32.01.22) n'ont pas
    # cette notion de complétude comparable au dictionnaire.
    i = 0
    while i < len(resultats):
        j = i + 1
        while (j < len(resultats)
               and resultats[j]["sheet_key"] == resultats[i]["sheet_key"]
               and resultats[j]["page"] == resultats[j - 1]["page"] + 1):
            j += 1
        groupe = resultats[i:j]
        i = j

        sheet_key = groupe[0]["sheet_key"]
        row_labels = sheet_dicts_effectifs[sheet_key]["row_codes"]
        if not row_labels:
            continue

        codes_attendus = set(row_labels.keys())
        codes_trouves_union, codes_inattendus_union = set(), set()
        for g in groupe:
            c = g["resultat"]["completude"]
            codes_trouves_union |= (codes_attendus - set(c["manquants"]))
            codes_inattendus_union |= set(c["inattendus"])

        manquants_final = sorted(codes_attendus - codes_trouves_union)
        if manquants_final or codes_inattendus_union:
            anomalies["codes_manquants"].append({
                "pages": [g["page"] for g in groupe],
                "sheet_key": sheet_key,
                "n_attendus": len(codes_attendus),
                "n_trouves_union": len(codes_trouves_union),
                "codes_manquants": manquants_final,
                "codes_inattendus": sorted(codes_inattendus_union),
            })

    anomalies["entites_vides_suspectes"] = detect_entites_vides_suspectes(resultats, sheet_dicts_effectifs)

    temps = time.time() - t0
    return elements, anomalies, temps


# ============================================================
# ÉTAPE 2c — PAGES SOMMAIRE
# ============================================================

def process_sommaire(pages_sommaire):
    t0 = time.time()
    elements = []
    for page in pages_sommaire:
        entries, residu = parse_sommaire_lignes(page["texte"])
        for e in entries:
            elements.append({
                "page_source": page["page"], "type": "sommaire",
                "contenu": {"section_id": e["section_id"], "titre": e["titre"], "page_cible": e["page"]},
            })
    temps = time.time() - t0
    return elements, temps


# ============================================================
# ÉTAPE 3 — ASSEMBLAGE
# ============================================================

def assemble_corpus(pdf_path, entite, annee, elements_narratifs, elements_qrt, elements_sommaire):
    corpus = []
    for e in elements_narratifs + elements_qrt + elements_sommaire:
        corpus.append({
            "source_fichier": Path(pdf_path).name,
            "entite": entite, "annee": annee,
            "page_source": e["page_source"],
            "type": e["type"],
            "section_id": e.get("section_id"),
            "template_id": e.get("template_id"),
            "contenu": e["contenu"],
        })
    metadata = {
        "entite_annee_non_verifiee": True,
        "raison": "Heuristique testée sur un seul document/émetteur (Groupama) — "
                  "pas encore validée sur un 2e document, cf. point 6 en attente.",
    }
    return corpus, metadata


# ============================================================
# ÉTAPE 4 — DIAGNOSTIC
# ============================================================

def build_diagnostic(classification, temps, anomalies_narratif, anomalies_qrt):
    n_narratif = sum(1 for p in classification if p["type"] == "narratif")
    n_qrt = sum(1 for p in classification if p["type"] == "qrt")
    n_sommaire = sum(1 for p in classification if p["type"] == "sommaire")

    anomalies = {
        "ecarts_totaux": anomalies_narratif.get("ecarts_totaux", []),
        "images_non_logo": anomalies_narratif.get("images_non_logo", []),
        "codes_qrt_manquants": anomalies_qrt.get("codes_manquants", []),
        "decalages_colonne_qrt": anomalies_qrt.get("decalages_colonne", []),
        "sous_feuilles_qrt_incertaines": anomalies_qrt.get("sous_feuilles_incertaines", []),
        "entites_qrt_vides_suspectes": anomalies_qrt.get("entites_vides_suspectes", []),
    }

    bloquant = bool(
        anomalies["codes_qrt_manquants"] or anomalies["decalages_colonne_qrt"]
        or anomalies["sous_feuilles_qrt_incertaines"] or anomalies["entites_qrt_vides_suspectes"]
        or any(not e.get("ok", True) for e in anomalies["ecarts_totaux"])
    )
    conclusion = "VÉRIFICATION MANUELLE REQUISE" if bloquant else "PRÊT POUR INDEXATION"

    return {
        "n_pages_total": len(classification),
        "repartition": {"narratif": n_narratif, "qrt": n_qrt, "sommaire": n_sommaire},
        "temps_s": temps,
        "anomalies": anomalies,
        "conclusion": conclusion,
    }


# ============================================================
# ORCHESTRATION
# ============================================================

async def main_async(pdf_path_str, work_dir_str=None):
    pdf_path = Path(pdf_path_str)
    work_dir = Path(work_dir_str) if work_dir_str else BASE_DIR / "ingest_output" / pdf_path.stem
    work_dir.mkdir(parents=True, exist_ok=True)
    t_start = time.time()

    t0 = time.time()
    classification = classify_pages(pdf_path)
    entite, annee = extraire_metadata_couverture(classification)
    t_triage = time.time() - t0

    pages_narratives = [p for p in classification if p["type"] == "narratif"]
    pages_qrt = [p for p in classification if p["type"] == "qrt"]
    pages_sommaire = [p for p in classification if p["type"] == "sommaire"]

    print(f"[triage] {len(classification)} pages classées en {t_triage:.1f}s "
          f"({len(pages_narratives)} narratives, {len(pages_qrt)} QRT, "
          f"{len(pages_sommaire)} sommaire) — entité={entite!r} année={annee!r}")
    for p in pages_qrt:
        print(f"    page {p['page']} -> {p['template_id']} ({p['resolution']})")

    with open(BASE_DIR / "output_sectionE_QRT" / "qrt_dictionary.json", encoding="utf-8") as f:
        qrt_dict = json.load(f)

    # process_narrative()/process_sommaire() NE SONT PLUS APPELÉES ICI —
    # rôle réel confirmé d'ingest.py : QRT uniquement (cf. GUIDE_PROJET.md,
    # Décision 045). process_narrative() est du code mort (son unique
    # appelant était ce bloc ; le vrai pipeline narratif est la chaîne
    # extract_raw_structure.py -> ... -> correction_fusion_caisses.py,
    # jamais celle-ci) — l'appeler plantait (run_test.py/dedup.py/
    # build_final.py/verify_final.py n'existent plus à la racine).
    # process_sommaire() ne plante pas mais son résultat n'est consommé
    # par rien en aval (corpus_final.json n'est lu par aucun script
    # d'indexation réel) — retirée par cohérence, pas par nécessité.
    anomalies_narratif = {"ecarts_totaux": [], "images_non_logo": []}
    t_narratif = 0.0

    elements_qrt, anomalies_qrt, t_qrt = await process_qrt(pdf_path, pages_qrt, qrt_dict, work_dir)
    print(f"[qrt] {len(elements_qrt)} éléments en {t_qrt:.1f}s")

    t0 = time.time()
    corpus, metadata = assemble_corpus(pdf_path, entite, annee, [], elements_qrt, [])
    t_assemblage = time.time() - t0

    temps = {"triage_s": round(t_triage, 1), "narratif_s": round(t_narratif, 1),
             "qrt_s": round(t_qrt, 1), "sommaire_s": 0.0,
             "assemblage_s": round(t_assemblage, 1), "total_s": round(time.time() - t_start, 1)}

    diagnostic = build_diagnostic(classification, temps, anomalies_narratif, anomalies_qrt)

    with open(work_dir / "corpus_final.json", "w", encoding="utf-8") as f:
        json.dump({"metadata": metadata, "elements": corpus}, f, ensure_ascii=False, indent=2)
    with open(work_dir / "diagnostic.json", "w", encoding="utf-8") as f:
        json.dump(diagnostic, f, ensure_ascii=False, indent=2)

    print(f"\n=== DIAGNOSTIC ===")
    print(json.dumps(diagnostic, ensure_ascii=False, indent=2))
    print(f"\ncorpus_final.json : {len(corpus)} éléments écrits dans {work_dir / 'corpus_final.json'}")

    return corpus, diagnostic


def main(pdf_path_str, work_dir_str=None):
    return asyncio.run(main_async(pdf_path_str, work_dir_str))


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("pdf")
    p.add_argument("work_dir", nargs="?", default=None)
    args = p.parse_args()
    main(args.pdf, args.work_dir)
