# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier corrige un petit défaut où certaines puces de liste avaient
# été confondues avec des titres de section.
# ------------------------------------------------------------------
"""retype_bullet_headers.py — Re-type en LIST_ITEM les SECTION_HEADER dont
le texte commence par une puce de la zone d'usage privé Unicode (PUA,
U+E000-U+F8FF — ex. \\uf0a7, \\uf0b7, glyphes de police symbole/Wingdings
non mappés par Docling).

Distinct de filter_fake_headers.py : ce n'est PAS un texte illisible (il
a déjà été vérifié lisible et exploitable une fois la puce retirée — 0
suppression au tour précédent), c'est un MAUVAIS TYPE assigné par
Docling — une puce de liste classée SECTION_HEADER au lieu de LIST_ITEM.
Ce script corrige le type et nettoie le texte, ne supprime rien.

Ne touche à AUCUN autre SECTION_HEADER que ceux commençant par une puce
PUA (après un éventuel espace de début) — tous les autres items,
quel que soit leur type, passent inchangés.

    python retype_bullet_headers.py [structure_filtree.json] [dossier_sortie]
"""

import argparse
import json
import sys
from pathlib import Path

# Console robuste aux caractères PUA (même précaution que dans
# fix_heading_levels.py / filter_fake_headers.py) — n'affecte que
# l'affichage, pas le JSON exporté.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

# Zone d'usage privé Unicode (Private Use Area) — U+E000 à U+F8FF.
PUA_DEBUT, PUA_FIN = 0xE000, 0xF8FF

# Caractères de puce connus, hors PUA : U+25AA (▪ BLACK SMALL SQUARE).
# Vérifié sur SFCR_2024_Groupe-Groupama.pdf (structure_filtree.json, 49
# SECTION_HEADER) : même symbole visuel que la puce PUA  utilisée
# sur le document 2025 (même rôle, même position dans le texte), mais
# décodé par Docling avec un point de code différent — vraisemblablement
# un encodage de police différent entre les 2 PDF. Ajouté ici plutôt
# qu'en assouplissant est_pua() à "tout caractère non alphanumérique",
# pour ne reconnaître QUE ce caractère précis, vérifié, et pas n'importe
# quelle puce ou symbole qui apparaîtrait un jour dans un autre document.
CARACTERES_PUCE_CONNUS_HORS_PUA = {0x25AA}

# Type cible du re-typage. "list_item" est la valeur réelle du label
# Docling DocItemLabel.LIST_ITEM (vérifiée dans structure_brute.json /
# structure_filtree.json) — c'est le type le plus proche disponible dans
# le schéma pour une puce de liste.
TYPE_CIBLE = "list_item"


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "structure_json", nargs="?",
        default=str(BASE_DIR / "output_structure_brute" / "structure_filtree.json"),
        help="structure_filtree.json déjà produit par filter_fake_headers.py",
    )
    p.add_argument(
        "output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"),
        help="Dossier de sortie (reçoit structure_finale.json)",
    )
    return p.parse_args()


def est_pua(caractere):
    return PUA_DEBUT <= ord(caractere) <= PUA_FIN


def est_puce_connue(caractere):
    """PUA, ou l'un des caractères de puce hors-PUA vérifiés (cf.
    CARACTERES_PUCE_CONNUS_HORS_PUA)."""
    return est_pua(caractere) or ord(caractere) in CARACTERES_PUCE_CONNUS_HORS_PUA


def commence_par_puce_pua(texte):
    """Vrai si, après un éventuel espace de début, le premier caractère
    du texte est une puce connue (PUA ou équivalent vérifié)."""
    texte_sans_espace_initial = (texte or "").lstrip()
    return bool(texte_sans_espace_initial) and est_puce_connue(texte_sans_espace_initial[0])


def retirer_puce(texte):
    """Retire les espaces de tête, PUIS le caractère de puce PUA initial,
    PUIS les espaces qui suivent la puce. Ne touche à rien d'autre dans
    le texte (pas de nettoyage supplémentaire, pas de reformulation)."""
    sans_espace = texte.lstrip()
    sans_puce = sans_espace[1:]  # retire uniquement le 1er caractère (la puce)
    return sans_puce.lstrip()


def retyper(items):
    """Retourne (items_corriges, journal_retypages). Ne modifie et
    n'évalue QUE les SECTION_HEADER commençant par une puce PUA — tout le
    reste (autres SECTION_HEADER inclus) passe inchangé."""
    corriges = []
    journal = []

    for item in items:
        if item["type"] != "section_header" or not commence_par_puce_pua(item["extrait"]):
            corriges.append(item)
            continue

        texte_avant = item["extrait"]
        texte_apres = retirer_puce(texte_avant)

        nouvel_item = dict(item)
        nouvel_item["type"] = TYPE_CIBLE
        nouvel_item["extrait"] = texte_apres
        nouvel_item["niveau"] = None  # les LIST_ITEM n'ont pas de niveau hiérarchique
        # position, pages, self_ref : inchangés (copiés tels quels via dict(item))

        corriges.append(nouvel_item)
        journal.append({
            "position": item["position"],
            "pages": item["pages"],
            "texte_avant": texte_avant,
            "texte_apres": texte_apres,
        })

    return corriges, journal


def main():
    args = parse_cli()
    with open(args.structure_json, encoding="utf-8") as f:
        items = json.load(f)

    n_section_header_avant = sum(1 for it in items if it["type"] == "section_header")

    corriges, journal = retyper(items)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "structure_finale.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(corriges, f, ensure_ascii=False, indent=2)

    print("=" * 70)
    print("JOURNAL DES RE-TYPAGES (SECTION_HEADER -> LIST_ITEM)")
    print("=" * 70)
    if not journal:
        print("\nAucun item re-typé — aucun SECTION_HEADER ne commence par une puce PUA.")
    else:
        for entree in journal:
            print(f"\n  position {entree['position']} — page(s) {entree['pages']}")
            print(f"    avant : {entree['texte_avant']!r}")
            print(f"    après : {entree['texte_apres']!r}")

    n_section_header_apres = sum(1 for it in corriges if it["type"] == "section_header")

    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Items re-typés               : {len(journal)}")
    print(f"  SECTION_HEADER avant re-typage : {n_section_header_avant}")
    print(f"  SECTION_HEADER après re-typage : {n_section_header_apres}")
    print(f"\n[export] {len(corriges)} items écrits dans {out_path}")


if __name__ == "__main__":
    main()
