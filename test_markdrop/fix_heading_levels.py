# -*- coding: utf-8 -*-
"""fix_heading_levels.py — Correction des niveaux de titres (SECTION_HEADER)
à partir de structure_brute.json.

CE N'EST PAS HeadingHierarchyModel. Vérifié avant d'écrire ce script :
HeadingHierarchyOptions/HeadingHierarchyModel (assign_heading_levels(),
signaux numérotation + style + signets PDF, le premier disponible
l'emportant) existent bien dans Docling, mais pas dans la version
installée sur ce projet (docling 2.17.0 / docling-core 2.16.0) — la
fonctionnalité n'apparaît dans docling qu'à partir de la v2.106.0
(inférence des niveaux depuis le PDF), soit ~90 versions mineures plus
loin. Jugé trop risqué à absorber sans test isolé sur ce pipeline déjà
validé (TableFormer, build_final.py, run_test.py...) — décision prise
avec l'utilisateur : réimplémenter ICI, en heuristique maison, UN SEUL
des 3 signaux que HeadingHierarchyModel utiliserait : la numérotation
("A.", "A.1.", "A.1.2.3."), déjà visible dans le texte extrait. Pas de
signal style, pas de signets PDF — si besoin un jour, ce sera un autre
module, pas improvisé ici en silence.

Ne reconvertit RIEN : ce signal ne regarde que le texte des titres déjà
présent dans structure_brute.json (produit par extract_raw_structure.py)
— aucun besoin du DoclingDocument complet pour cette approche précise,
donc aucune reconversion PDF (>10 min) n'est nécessaire ici.

    python fix_heading_levels.py [structure_brute.json] [dossier_sortie]
"""

import argparse
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

# Certains titres mal classés par Docling contiennent des puces de police
# symbole (ex. , zone d'usage privé Unicode) que la console Windows
# (cp1252) ne sait pas afficher — remplace plutôt que de planter en plein
# comparatif. N'affecte que l'affichage : le JSON exporté reste en UTF-8
# complet, sans perte.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

# Motif de numérotation observé sur le SFCR (vérifié sur le run réel 89
# pages) : une lettre majuscule, suivie de 0 ou plusieurs groupes ".N",
# suivie D'UN POINT FINAL OPTIONNEL puis d'un espace — "A." (profondeur
# 1), "A.1." (2), "A.1.2." (3), "D.1.6.1." (4), "B.3.2.1.2.1." (6, cas
# réel le plus profond observé). Point final rendu optionnel (\.?, pas
# \.) après découverte de 2 titres réels sans point avant l'espace
# ("A.3 Résultats des investissements", "B.3.2.3 Fréquence de
# réalisation...") — le regex strict les faisait échouer silencieusement,
# les laissant au niveau H1 d'origine de Docling au lieu de leur
# profondeur réelle. Vérifié avant ce changement (pas supposé) : sur les
# 253 SECTION_HEADER bruts, SEULS ces 2 titres matchent en plus avec le
# point optionnel — aucun faux positif introduit (pas de lettre isolée
# suivie d'un espace sans numérotation dans ce document). La logique de
# calcul de profondeur (nombre de groupes ".N" capturés) est INCHANGÉE.
# Conçu spécifiquement pour CE schéma de numérotation (lettre.chiffres)
# — pas de support pour un schéma romain ou
# alphabétique minuscule, ce document n'en a pas montré besoin.
MOTIF_NUMEROTATION = re.compile(r"^([A-Z])((?:\.\d+)*)\.?\s")

# Même borne que max_level par défaut de HeadingHierarchyOptions (pour
# référence, pas parce qu'on réimplémente cette option).
NIVEAU_MAX = 6

TAILLE_ECHANTILLON = 15


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "structure_json", nargs="?",
        default=str(BASE_DIR / "output_structure_brute" / "structure_brute.json"),
        help="structure_brute.json déjà produit par extract_raw_structure.py",
    )
    p.add_argument(
        "output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"),
        help="Dossier de sortie (reçoit structure_corrigee.json)",
    )
    return p.parse_args()


def deduire_niveau(extrait):
    """Déduit la profondeur hiérarchique à partir du préfixe numéroté du
    titre ("A." -> 1, "A.1." -> 2, "D.1.6.1." -> 4...). Retourne None si
    aucun préfixe numéroté n'est reconnu — dans ce cas le niveau Docling
    d'origine est conservé tel quel ailleurs dans ce script : on ne
    devine jamais un niveau au hasard, on signale l'absence de signal."""
    if not extrait:
        return None
    m = MOTIF_NUMEROTATION.match(extrait)
    if not m:
        return None
    groupes_intermediaires = m.group(2)  # ex. ".3.2.1.2.1"
    profondeur = 1 + groupes_intermediaires.count(".")
    return min(profondeur, NIVEAU_MAX)


def corriger_niveaux(items):
    """Retourne une NOUVELLE liste, même schéma que structure_brute.json
    (position, type, niveau, pages, extrait, self_ref) — seul le champ
    "niveau" change, et uniquement pour les section_header dont la
    numérotation est reconnue. Ne regroupe rien, ne touche à aucun autre
    champ ni aucun autre type d'item."""
    corriges = []
    for it in items:
        nouvel_item = dict(it)
        if it["type"] == "section_header":
            niveau_detecte = deduire_niveau(it["extrait"])
            if niveau_detecte is not None:
                nouvel_item["niveau"] = niveau_detecte
            # sinon : niveau Docling d'origine conservé tel quel (pas deviné)
        corriges.append(nouvel_item)
    return corriges


def comparatif(avant, apres):
    """Affiche la distribution des niveaux avant/après (SECTION_HEADER
    uniquement) et un échantillon de 15 titres pris au hasard, niveau
    avant -> après côte à côte, pour vérification visuelle."""
    print("=" * 70)
    print("COMPARATIF AVANT / APRÈS")
    print("=" * 70)

    niveaux_avant = Counter(it["niveau"] for it in avant if it["type"] == "section_header")
    niveaux_apres = Counter(it["niveau"] for it in apres if it["type"] == "section_header")

    print("\nDistribution des niveaux (SECTION_HEADER uniquement) :")
    print(f"  {'Niveau':10} {'Avant':>8} {'Après':>8}")
    tous_niveaux = sorted(set(niveaux_avant) | set(niveaux_apres), key=lambda x: (x is None, x))
    for n in tous_niveaux:
        etiquette = f"H{n}" if n is not None else "(aucun)"
        print(f"  {etiquette:10} {niveaux_avant.get(n, 0):>8} {niveaux_apres.get(n, 0):>8}")

    par_position_avant = {it["position"]: it for it in avant}
    par_position_apres = {it["position"]: it for it in apres}
    titres_positions = [it["position"] for it in apres if it["type"] == "section_header"]

    n_sans = sum(
        1 for p in titres_positions
        if deduire_niveau(par_position_avant[p]["extrait"]) is None
    )
    print(f"\n{n_sans}/{len(titres_positions)} titres SANS numérotation reconnue "
          "(niveau Docling d'origine conservé tel quel, pas deviné).")

    print(f"\nÉchantillon de {min(TAILLE_ECHANTILLON, len(titres_positions))} titres "
          "(positions aléatoires), niveau avant -> après :")
    echantillon = sorted(random.sample(titres_positions, min(TAILLE_ECHANTILLON, len(titres_positions))))
    for p in echantillon:
        a, b = par_position_avant[p], par_position_apres[p]
        detecte = deduire_niveau(a["extrait"]) is not None
        marque = "" if detecte else "  (numérotation non détectée)"
        print(f"  pos {p:5} p.{a['pages']} H{a['niveau']} -> H{b['niveau']}{marque}"
              f"  « {a['extrait']} »")


def main():
    args = parse_cli()
    with open(args.structure_json, encoding="utf-8") as f:
        avant = json.load(f)

    apres = corriger_niveaux(avant)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "structure_corrigee.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(apres, f, ensure_ascii=False, indent=2)
    print(f"[export] {len(apres)} items écrits dans {out_path}")

    comparatif(avant, apres)


if __name__ == "__main__":
    main()
