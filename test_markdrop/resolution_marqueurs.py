# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier remplace les renvois internes du texte (par exemple « voir
# tableau X ») par le vrai tableau ou la vraie image correspondante, au
# moment de préparer la réponse.
# ------------------------------------------------------------------
"""resolution_marqueurs.py — Résolution des marqueurs [TABLEAU: self_ref]/
[IMAGE: self_ref] AU MOMENT DE LA GÉNÉRATION (Décision 025, actée mais
jamais implémentée ni testée avant ce module). Ne touche PAS au
retrieval/fusion/reranking (Décision 028) — s'applique UNIQUEMENT après
la sélection du candidat gagnant, pour enrichir le contexte envoyé au
modèle de génération.

FORMAT DES MARQUEURS — vérifié dans chunks_propres.json (pas supposé) :
"[TABLEAU: #/tables/N]", "[IMAGE: #/pictures/N]" — espace après ":",
aucun espace avant "]". "[LEGENDE: #/texts/N]" existe aussi mais référence
une légende texte, pas un visuel — volontairement exclu (hors périmètre
de la Décision 025).

RÉSOLUTION AVANT (texte narratif gagnant -> visuel associé) : les
marqueurs du chunk gagnant sont résolus vers leur fichier réel via le
nommage déterministe déjà en place (chemins_visuels.py — resoudre_chemin_self_ref,
qui gère aussi la déduplication pHash des images).

RÉSOLUTION INVERSE (visuel gagnant -> paragraphe narratif précis) — POINT
TRANCHÉ EXPLICITEMENT (pas deviné) : au lieu de remonter tout
chemin_hierarchique (section entière, potentiellement hors-sujet si la
section est longue), on retrouve le PARAGRAPHE PRÉCIS qui précède le
marqueur. VÉRIFIÉ avant d'écrire ce module : cette information est
INTÉGRALEMENT RECONSTRUCTIBLE depuis les données déjà existantes
(recherche du marqueur littéral dans le texte brut du chunk narratif,
chunks_propres.json/chunks_avec_visuels.json) — AUCUN nouveau champ
stocké nécessaire. Le "paragraphe précédent" = tout le texte entre le
marqueur PRÉCÉDENT du même chunk (ou le début du chunk s'il n'y en a
pas) et le marqueur ciblé — jamais toute la section, jamais le texte qui
suit. Testé sur un cas réel à 2 marqueurs consécutifs sans texte entre
eux (idx 155/chunks_propres.json, #/pictures/58 puis #/pictures/59) :
le 2e donne un paragraphe vide, géré proprement (pas une erreur).

CONTRAINTES (les deux sens) :
- résolution à 1 SEUL niveau, jamais récursive — un marqueur présent DANS
  un élément résolu n'est jamais lui-même suivi.
- déduplication par identifiant AVANT envoi à la génération (self_ref
  canonique pour les visuels, chemin_hierarchique pour le texte).
- plafond de MAX_ELEMENTS_RESOLUS (3) éléments résolus par appel — pas de
  résolution illimitée même si un chunk contient plus de marqueurs.
- cas AMBIGU (visuel référencé dans plusieurs chunks narratifs distincts,
  ex. logo dédupliqué répété) : résolution inverse renvoie None plutôt
  que de choisir arbitrairement un des paragraphes — même principe que
  build_index_visuels.py (chemin_hierarchique=null pour ces cas).
"""

import json
import re
from pathlib import Path

import chemins_visuels as cv

BASE_DIR = Path(__file__).parent
CHUNKS_PROPRES_JSON = BASE_DIR / "output_structure_brute" / "chunks_propres.json"
CHUNKS_AVEC_VISUELS_JSON = BASE_DIR / "output_structure_brute" / "chunks_avec_visuels.json"

# Espace après ":", aucun avant "]" — format vérifié dans chunks_propres.json.
# [LEGENDE: ...] exclu à dessein (référence une légende, pas un visuel).
MOTIF_MARQUEUR = re.compile(r"\[(TABLEAU|IMAGE): (#/(?:tables|pictures)/\d+)\]")

MAX_ELEMENTS_RESOLUS = 3

_chunks_cache = None
_chunks_avec_visuels_cache = None


def _charger_chunks_avec_visuels():
    global _chunks_avec_visuels_cache
    if _chunks_avec_visuels_cache is None:
        with open(CHUNKS_AVEC_VISUELS_JSON, encoding="utf-8") as f:
            _chunks_avec_visuels_cache = json.load(f)
    return _chunks_avec_visuels_cache


def parser_marqueurs(texte):
    """Marqueurs [TABLEAU:/IMAGE: self_ref] trouvés dans `texte`, dans
    l'ordre d'apparition, avec position de DÉBUT et de FIN (caractères)."""
    return [
        {"type": m.group(1), "self_ref": m.group(2), "debut": m.start(), "fin": m.end()}
        for m in MOTIF_MARQUEUR.finditer(texte)
    ]


# --- 1. Résolution AVANT (texte narratif gagnant -> visuel associé) ---

def resoudre_visuels_du_chunk(texte_chunk, annee=2025, deja_inclus=None, max_elements=MAX_ELEMENTS_RESOLUS):
    """Résout les marqueurs TABLEAU/IMAGE d'un chunk narratif gagnant
    vers leur fichier réel (nommage déterministe, chemins_visuels.py) —
    1 seul niveau (le contenu résolu n'est jamais re-parsé pour d'autres
    marqueurs), dédup contre deja_inclus, plafonné à max_elements."""
    if deja_inclus is None:
        deja_inclus = set()
    mapping_dedup = cv.charger_mapping_dedup(annee)

    resolus = []
    for m in parser_marqueurs(texte_chunk):
        if len(resolus) >= max_elements:
            break
        self_ref = m["self_ref"]
        self_ref_canonique = mapping_dedup.get(self_ref, self_ref)
        if self_ref_canonique in deja_inclus:
            continue  # déjà présent dans le contexte — dédup, pas de doublon
        try:
            chemin_relatif = cv.resoudre_chemin_self_ref(self_ref, annee, mapping_dedup)
        except ValueError:
            continue  # self_ref hors format attendu — signalé en pratique via logs applicatifs, pas deviné
        resolus.append({
            "self_ref": self_ref,
            "self_ref_canonique": self_ref_canonique,
            "type": m["type"].lower(),
            "chemin_relatif": chemin_relatif,
            "chemin_absolu": str(cv.chemin_absolu(chemin_relatif)),
        })
        deja_inclus.add(self_ref_canonique)
    return resolus


# --- 2. Résolution INVERSE (visuel gagnant -> paragraphe narratif précis) ---

def _trouver_occurrences_narratives(self_ref, annee=2025):
    """Chunks narratifs référençant CE self_ref (après dédup) — 0, 1, ou
    plusieurs (cas ambigu, cf. docstring du module)."""
    mapping_dedup = cv.charger_mapping_dedup(annee)
    self_ref_canonique = mapping_dedup.get(self_ref, self_ref)

    occurrences = []
    for chunk in _charger_chunks_avec_visuels():
        for v in chunk.get("visuels", []):
            sr_original = v["self_ref"]
            if mapping_dedup.get(sr_original, sr_original) == self_ref_canonique:
                occurrences.append({"chunk": chunk, "self_ref_original": sr_original})
    return occurrences


def resoudre_paragraphe_associe(self_ref, annee=2025):
    """Paragraphe narratif PRÉCIS associé à ce visuel, ou None si le
    visuel n'est référencé nulle part (statut "absent") ou dans PLUSIEURS
    chunks narratifs distincts (statut "ambigu", ex. logo répété — pas de
    choix arbitraire). self_ref=None (cas des pages QRT, qui n'ont pas
    d'item Docling) renvoie None immédiatement."""
    if self_ref is None:
        return None  # pages QRT : pas de marqueur possible, cf. chemins_visuels.py

    occurrences = _trouver_occurrences_narratives(self_ref, annee)
    chemins_distincts = {o["chunk"]["chemin_hierarchique"] for o in occurrences}
    if len(chemins_distincts) != 1:
        return None  # absent (0) ou ambigu (>1) — jamais de choix arbitraire

    occurrence = occurrences[0]
    chunk = occurrence["chunk"]
    self_ref_original = occurrence["self_ref_original"]
    texte = chunk["texte"]

    marqueurs = parser_marqueurs(texte)
    indice_cible = next((i for i, m in enumerate(marqueurs) if m["self_ref"] == self_ref_original), None)
    if indice_cible is None:
        raise RuntimeError(
            f"self_ref {self_ref_original!r} référencé dans chunks_avec_visuels.json mais aucun "
            f"marqueur correspondant trouvé dans le texte brut du chunk "
            f"{chunk['chemin_hierarchique']!r} — incohérence à investiguer, pas masquée."
        )

    debut = marqueurs[indice_cible - 1]["fin"] if indice_cible > 0 else 0
    fin = marqueurs[indice_cible]["debut"]
    paragraphe = texte[debut:fin].strip()

    return {
        "chemin_hierarchique": chunk["chemin_hierarchique"],
        "pages": chunk["pages"],
        "paragraphe": paragraphe,
    }
