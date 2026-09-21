# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier centralise la façon de nommer et de retrouver les fichiers
# d'images (tableaux, images, pages de tableaux réglementaires), pour que
# toutes les autres étapes s'y retrouvent de la même manière.
# ------------------------------------------------------------------
"""chemins_visuels.py — Convention de chemin UNIQUE pour les fichiers
visuels réels (tableaux, images, pages QRT), réutilisée par tous les
scripts de l'étape 3 (extraction, association aux chunks, validation).
Aucune table de correspondance à construire/maintenir pour le cas normal
(chemin dérivé directement et déterministement du self_ref) — SEULE
exception : une poignée d'images quasi-identiques détectées par pHash
(logos répétés), mappées vers un fichier canonique unique via
images_dedup.json (cf. extraire_visuels.py) pour ne pas stocker plusieurs
fois le même visuel.

Racine choisie pour pouvoir migrer vers un stockage objet (S3 ou
équivalent) sans rien changer à la convention : RACINE_VISUELS est le
SEUL point qui changerait (chemin local -> bucket), tout le reste de ce
module ne retourne que des chemins RELATIFS.

    #/tables/16   -> visuels/2025/tables/table_16.png
    #/pictures/75 -> visuels/2025/images/picture_75.png
    page QRT 78   -> visuels/2025/qrt_pages/page_78.png
"""

import json
import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Racine locale actuelle (tâche 1) — le seul élément "backend" de ce
# module. Migrer vers S3 = remplacer RACINE_VISUELS par un préfixe de clé
# de bucket ; chemin_relatif_* ci-dessous ne change pas. Racine PARTAGÉE
# entre années (visuels/2025/... et visuels/2024/... cohabitent sous la
# même RACINE_VISUELS) — c'est la convention voulue, pas un chemin à
# dupliquer par document.
RACINE_VISUELS = BASE_DIR / "output_structure_brute" / "visuels"

# Identique à build_sections.PAGE_MIN_QRT (même limite documentaire, même
# besoin de surcharge par document — cf. son commentaire) : 77 sur
# SFCR_2025_Groupe-Groupama.pdf, 73 sur SFCR_2024_Groupe-Groupama.pdf.
# Surchargeable via PAGE_MIN_QRT_OVERRIDE pour ne pas dupliquer ce module.
PAGE_MIN_QRT = int(os.environ.get("PAGE_MIN_QRT_OVERRIDE", 77))

# self_ref Docling : "#/tables/N" ou "#/pictures/N" — format vérifié sur
# docling_document_complet.json (docling-core 2.16.0).
MOTIF_SELF_REF = re.compile(r"^#/(tables|pictures)/(\d+)$")

# Pluriel (tel qu'il apparaît dans self_ref) -> singulier (préfixe de
# fichier et nom de sous-dossier).
TYPE_VERS_SOUS_DOSSIER = {"tables": "tables", "pictures": "images"}
TYPE_VERS_PREFIXE = {"tables": "table", "pictures": "picture"}


def parser_self_ref(self_ref):
    """Décompose "#/tables/16" -> ("tables", 16). Lève ValueError si le
    format ne correspond pas exactement à ce qui est produit par Docling
    — jamais de tentative de "deviner" un format voisin."""
    m = MOTIF_SELF_REF.match(self_ref)
    if not m:
        raise ValueError(f"self_ref inattendu (format non reconnu) : {self_ref!r}")
    return m.group(1), int(m.group(2))


def chemin_relatif_table_ou_image(self_ref, annee):
    """Chemin relatif (sous RACINE_VISUELS) pour un tableau ou une image
    narrative, dérivé UNIQUEMENT du self_ref et de l'année — déterministe,
    pas de table de correspondance."""
    type_pluriel, indice = parser_self_ref(self_ref)
    sous_dossier = TYPE_VERS_SOUS_DOSSIER[type_pluriel]
    prefixe = TYPE_VERS_PREFIXE[type_pluriel]
    return f"{annee}/{sous_dossier}/{prefixe}_{indice}.png"


def chemin_relatif_page_qrt(page_no, annee):
    """Chemin relatif pour le rendu pleine page d'une annexe QRT — pas de
    self_ref possible ici (ce n'est pas un item Docling, c'est le rendu
    de la page entière), donc nommage par numéro de page."""
    return f"{annee}/qrt_pages/page_{page_no}.png"


def charger_mapping_dedup(annee):
    """Charge, si présent, le mapping self_ref dupliqué -> self_ref
    canonique (cf. extraire_visuels.py) — seule exception au principe
    "aucune table de correspondance", limitée aux images détectées
    quasi-identiques. Retourne {} si le fichier n'existe pas encore."""
    chemin = RACINE_VISUELS / str(annee) / "images_dedup.json"
    if not chemin.exists():
        return {}
    with open(chemin, encoding="utf-8") as f:
        return json.load(f)


def resoudre_chemin_self_ref(self_ref, annee, mapping_dedup=None):
    """Chemin relatif RÉEL pour un self_ref, en tenant compte d'un
    éventuel doublon détecté par pHash (mapping_dedup, cf.
    charger_mapping_dedup) : si ce self_ref a été identifié comme
    quasi-identique à un autre déjà stocké, retourne le chemin du fichier
    CANONIQUE plutôt que son propre chemin self_ref — jamais les deux
    fichiers en parallèle."""
    if mapping_dedup is None:
        mapping_dedup = charger_mapping_dedup(annee)
    self_ref_reel = mapping_dedup.get(self_ref, self_ref)
    return chemin_relatif_table_ou_image(self_ref_reel, annee)


def chemin_absolu(chemin_relatif):
    """Chemin absolu local — seule fonction qui connaît RACINE_VISUELS.
    Migrer vers S3 = ne plus appeler cette fonction, utiliser le chemin
    relatif comme clé d'objet directement."""
    return RACINE_VISUELS / chemin_relatif
