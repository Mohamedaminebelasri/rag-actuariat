# -*- coding: utf-8 -*-
"""paddleocr_reader.py — Lecture déterministe (non-LLM) de valeurs numériques
dans une image, via PaddleOCR (PP-OCRv6, texte seul — PAS PP-StructureV3,
cf. Décision 055 : la pipeline structure complète plante sur ce poste avec
oneDNN activé et est de toute façon inutile ici, la structure de la page
étant déjà connue par ailleurs).

`enable_mkldnn=False` est OBLIGATOIRE sur ce poste : avec oneDNN activé
(comportement par défaut), l'inférence lève
`NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support
[pir::ArrayAttribute<pir::DoubleAttribute>]` (bug PaddlePaddle 3.3.1,
backend oneDNN/PIR sur CPU Windows) — vérifié en isolant le paramètre en
cause, pas une supposition.

2 stratégies de association label/code -> valeur, testées et vérifiées
contre les valeurs connues de la page 87 (R0060/R0220/R0470) et de
picture_75.png (les 6 boîtes SCR) :
- `valeur_a_droite_du_code` : tableau QRT, code "R0xxx" à gauche, valeur
  sur la même ligne (tolérance verticale) à sa droite — PAS forcément le
  nombre immédiatement adjacent, le plus proche géométriquement.
- `valeur_sous_label` : diagramme en boîtes (picture_75.png), libellé texte
  au-dessus, valeur au-dessous — le plus proche géométriquement, PAS l'ordre
  de lecture OCR (qui peut désynchroniser labels et valeurs sur des layouts
  complexes).
"""

import re
import unicodedata

_pipeline = None


def _get_pipeline():
    """Instance PaddleOCR partagée (le chargement des modèles prend
    plusieurs secondes) — device CPU explicite (GPU non disponible sur ce
    poste pour paddlepaddle, cf. Décision 055), oneDNN désactivé (cf.
    docstring module)."""
    global _pipeline
    if _pipeline is None:
        from paddleocr import PaddleOCR
        _pipeline = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="cpu",
            enable_mkldnn=False,
        )
    return _pipeline


def lire_image(chemin_image):
    """Retourne une liste de dicts {text, conf, cx, cy} — 1 par bloc de
    texte détecté, cx/cy = centre de la boîte englobante en pixels."""
    pipeline = _get_pipeline()
    resultats = pipeline.predict(str(chemin_image))
    items = []
    for r in resultats:
        for texte, conf, box in zip(r["rec_texts"], r["rec_scores"], r["rec_polys"]):
            xs = [p[0] for p in box]
            ys = [p[1] for p in box]
            items.append({
                "text": texte, "conf": float(conf),
                "cx": sum(xs) / len(xs), "cy": sum(ys) / len(ys),
            })
    return items


def _normaliser(s):
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _parse_nombre(texte):
    """'-4 612 403' / '4612403' / '1271055' -> int, ou None si pas un
    nombre plausible (au moins 3 chiffres, signe optionnel)."""
    t = texte.replace(" ", "").replace(" ", "")
    if not re.fullmatch(r"-?[0-9]{3,}", t):
        return None
    return int(t)


def valeur_a_droite_du_code(items, code_ligne, tolerance_y=15):
    """Cherche `code_ligne` (ex. "R0060") parmi les items OCR (tolère les
    confusions OCR chiffre/lettre O<->0 dans le TEXTE DU CODE uniquement,
    jamais dans la valeur numérique retournée), puis retourne le nombre le
    plus proche géométriquement sur la même ligne (± tolerance_y px) à sa
    droite. Retourne (valeur:int, conf:float) ou (None, None) si le code
    ou une valeur associée est introuvable."""
    code_norm = code_ligne.replace("O", "0")
    candidats_code = [
        it for it in items
        if it["text"].replace(" ", "").replace("O", "0").replace("o", "0") == code_norm
    ]
    if not candidats_code:
        return None, None
    code_item = candidats_code[0]

    nombres = []
    for it in items:
        v = _parse_nombre(it["text"])
        if v is None:
            continue
        if abs(it["cy"] - code_item["cy"]) > tolerance_y:
            continue
        if it["cx"] <= code_item["cx"]:
            continue
        nombres.append((it, v))
    if not nombres:
        return None, None
    nombres.sort(key=lambda t: t[0]["cx"])
    meilleur_item, valeur = nombres[0]
    return valeur, meilleur_item["conf"]


def valeur_sous_label(items, label_norm):
    """Cherche un item dont le texte normalisé == label_norm (ex.
    "scrop"), puis retourne le nombre le plus proche géométriquement
    strictement en dessous. Retourne (valeur:int, conf:float) ou
    (None, None)."""
    candidats_label = [it for it in items if _normaliser(it["text"]) == label_norm]
    if not candidats_label:
        return None, None
    label_item = candidats_label[0]

    nombres = []
    for it in items:
        v = _parse_nombre(it["text"])
        if v is None:
            continue
        if it["cy"] <= label_item["cy"]:
            continue
        d2 = (it["cx"] - label_item["cx"]) ** 2 + (it["cy"] - label_item["cy"]) ** 2
        nombres.append((d2, it, v))
    if not nombres:
        return None, None
    nombres.sort(key=lambda t: t[0])
    _, meilleur_item, valeur = nombres[0]
    return valeur, meilleur_item["conf"]
