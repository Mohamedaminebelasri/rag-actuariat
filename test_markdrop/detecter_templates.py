# -*- coding: utf-8 -*-
"""detecter_templates.py — Détection automatique de l'inventaire QRT d'un
SFCR (Phase 3.7, Décision 056) : quels templates sont présents, sous
quel format (texte natif vs image), et quelle variante solo/groupe et
formule standard/modèle interne — pour piloter kpi_qrt_mapping.py sur un
document jamais vu.

MÉTHODE (pas de supposition non vérifiable) :
- document_type : le suffixe de S.23.01.XX (Own Funds — présent dans
  quasi tout SFCR) est le signal le plus fiable, vérifié empiriquement
  (Groupama/S.23.01.22 = groupe ; Bornholms/AXA/Yuzzu/S.23.01.01 = solo)
  — S.02.01/S.05.01 NE PERMETTENT PAS cette distinction (suffixe .02
  pour solo ET groupe, vérifié sur les 3 mêmes documents).
- scr_method : S.25.01 présent = formule standard (vérifié : mêmes codes
  de ligne chez Groupama... non, Groupama n'a PAS S.25.01, il a S.25.05 —
  vérifié directement). S.25.02/03/04/05 = modèle interne (partiel ou
  complet) — la distinction partiel/complet n'est PAS déterminable de
  façon fiable depuis le seul numéro de template (non vérifié, donc
  laissé "inconnu" plutôt que deviné).
- format : texte_natif si n_caracteres > NATIVE_TEXT_THRESHOLD (même
  seuil que process_qrt dans ingest.py), image sinon.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingest import classify_pages, NATIVE_TEXT_THRESHOLD


def detecter_templates(pdf_path):
    classification = classify_pages(pdf_path)
    pages_qrt = [p for p in classification if p["type"] == "qrt"]

    # NOTE (limite connue) : classify_pages() ne connaît que le template
    # TRONQUÉ (ex. "S.23.01.22", pas ".01"/".02" — la sous-feuille n'est
    # résolue que plus tard par resoudre_sous_feuille). Un même template
    # tronqué peut donc couvrir 2 pages de format DIFFÉRENT si ses
    # sous-feuilles ne sont pas homogènes (ex. Groupama page 85 = texte
    # natif, page 86 = image, toutes 2 sous "S.23.01.22") — reporté
    # explicitement en "mixte" avec le détail par page, JAMAIS moyenné ou
    # tranché silencieusement vers l'un des deux.
    templates = {}
    for p in pages_qrt:
        tid = p["template_id"]
        fmt = "texte_natif" if p["n_caracteres"] > NATIVE_TEXT_THRESHOLD else "image"
        if tid not in templates:
            templates[tid] = {"pages": [], "formats_par_page": {}}
        templates[tid]["pages"].append(p["page"])
        templates[tid]["formats_par_page"][p["page"]] = fmt

    for tid, info in templates.items():
        formats = set(info["formats_par_page"].values())
        info["format"] = formats.pop() if len(formats) == 1 else "mixte"

    prefixes = set(templates.keys())

    document_type = "inconnu"
    s2301 = next((t for t in prefixes if t.startswith("S.23.01")), None)
    if s2301:
        suffixe = s2301.split(".")[-1]  # dernier segment = indicateur solo(01)/groupe(22)
        if suffixe == "22":
            document_type = "groupe"
        elif suffixe == "01":
            document_type = "solo"

    scr_method = "inconnu"
    if any(t.startswith("S.25.01") for t in prefixes):
        scr_method = "formule_standard"
    elif any(t.startswith(("S.25.02", "S.25.03", "S.25.04", "S.25.05")) for t in prefixes):
        scr_method = "modele_interne (partiel ou complet — non distinguable automatiquement)"

    return {
        "document_type": document_type,
        "scr_method": scr_method,
        "templates": templates,
    }


if __name__ == "__main__":
    import json
    pdf = Path(r"C:\Users\PC\Documents\rag-actuariat\data\SFCR_2025_Groupe-Groupama.pdf")
    resultat = detecter_templates(pdf)
    print(json.dumps(resultat, ensure_ascii=False, indent=2))
