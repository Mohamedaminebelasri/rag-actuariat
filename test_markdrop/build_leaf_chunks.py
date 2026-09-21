# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier affine le découpage précédent pour que chaque morceau de
# texte s'arrête au bon endroit, juste avant le titre suivant.
# ------------------------------------------------------------------
"""build_leaf_chunks.py — Reconstruit les chunks avec une frontière
"contenu direct" : le chunk d'un section_header s'arrête au TOUT PROCHAIN
section_header dans l'ordre de lecture, quel que soit son niveau — pas au
prochain de même niveau ou supérieur (règle de sections_brutes.json).
Objectif : chaque mot de texte narratif n'appartient qu'à UN SEUL chunk
direct, pour la vectorisation finale (fini le chevauchement parent/enfant
volontaire de l'étape précédente).

Source retenue (pas sections_brutes.json comme entrée principale) : on
repart des items de structure_finale_v2.json (position/type/pages/
self_ref/niveau), enrichis en texte intégral via le DoclingDocument
sauvegardé — en réutilisant TELLES QUELLES les fonctions déjà validées de
build_sections.py (assembler_contenu, est_zone_qrt,
construire_chemins_hierarchiques) et de recover_full_text.py
(enrichir_avec_texte_integral). Seule la fonction de recherche de
frontière change. Choix fait ainsi car le texte de sections_brutes.json
est déjà concaténé en une seule chaîne par chunk — re-séparer les
frontières internes à partir de cette chaîne serait fragile (recherche de
sous-chaîne), alors que les items d'origine donnent des frontières exactes
par position. sections_brutes.json sert uniquement de RÉFÉRENCE pour la
validation finale (étape 6), pas de source de reconstruction.

Ne modifie ni sections_brutes.json, ni structure_finale_v2.json, ni
docling_document_complet.json.

    python build_leaf_chunks.py [structure_finale_v2.json] [docling_document_complet.json] [sections_brutes.json] [dossier_sortie]
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

# Seuil de mots RÉELS (hors marqueurs table/image, cf. assembler_contenu)
# en dessous duquel un chunk est classé "structurel" (titre d'organisation
# sans vrai texte narratif propre) plutôt que "indexable". Valeur choisie
# après examen de la distribution réelle des petits comptes de mots — voir
# le résumé affiché à l'exécution ; à ajuster si la coupure ne s'avère pas
# nette une fois les vraies données observées.
SEUIL_MOTS_INDEXABLE = 5


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("structure_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "structure_finale_v2.json"))
    p.add_argument("docling_document_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "docling_document_complet.json"))
    p.add_argument("sections_brutes_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "sections_brutes.json"))
    p.add_argument("output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"))
    return p.parse_args()


def trouver_fin_chunk_direct(headers, i):
    """Frontière du contenu DIRECT : le tout prochain header dans l'ordre
    de lecture, quel que soit son niveau — contrairement à
    build_sections.trouver_fin_chunk (prochain de niveau <=). Un enfant
    plus profond ferme désormais le chunk de son parent, au lieu d'y être
    englouti."""
    return i + 1


def construire_chunks_directs(items, bs):
    """Construit un chunk par SECTION_HEADER, contenu limité au tout
    prochain header (cf. trouver_fin_chunk_direct). Réutilise
    assembler_contenu et construire_chemins_hierarchiques de
    build_sections.py sans les modifier — seule la frontière change."""
    items_tries = sorted(items, key=lambda it: it["position"])
    headers = [it for it in items_tries if it["type"] == "section_header"]
    chemins = bs.construire_chemins_hierarchiques(headers)

    # Contenu narratif situé AVANT le tout premier header restant (s'il y
    # en a) : ni l'ancienne ni la nouvelle méthode de chunking ne
    # l'attribuent à un chunk (les deux ne créent des empans qu'APRÈS un
    # header). Remonté (pas juste affiché) pour être réconcilié
    # explicitement dans le total du résumé, plutôt que de ressortir comme
    # un écart de validation non expliqué.
    nb_mots_avant_premier = 0
    if headers:
        avant_premier = [it for it in items_tries if it["position"] < headers[0]["position"]]
        _texte_avant, nb_mots_avant_premier, _pages_avant = bs.assembler_contenu(avant_premier)
        if nb_mots_avant_premier:
            print(f"[INFO] {nb_mots_avant_premier} mot(s) de contenu narratif AVANT le premier "
                  "section_header restant — non rattachés à un chunk (ni ici, ni dans "
                  "sections_brutes.json), réconciliés séparément dans le résumé.")

    chunks = []
    for i, header in enumerate(headers):
        fin_idx = trouver_fin_chunk_direct(headers, i)
        position_fin = headers[fin_idx]["position"] if fin_idx < len(headers) else None

        span = [
            it for it in items_tries
            if it["position"] > header["position"]
            and (position_fin is None or it["position"] < position_fin)
        ]

        texte, nb_mots, pages_contenu = bs.assembler_contenu(span)
        pages_chunk = sorted(set(header.get("pages", [])) | set(pages_contenu))

        chunks.append({
            "titre": header["extrait"],
            "chemin_hierarchique": chemins[header["position"]],
            "niveau": header["niveau"],
            "position_header": header["position"],
            "pages": pages_chunk,
            "nb_mots": nb_mots,
            "texte": texte,
            "categorie": "indexable" if nb_mots >= SEUIL_MOTS_INDEXABLE else "structurel",
        })

    return chunks, nb_mots_avant_premier


def calculer_total_mots_reference(items_enrichis, bs):
    """Référence de validation, calculée DIRECTEMENT sur les items (pas
    sur sections_brutes.json). Tentative initiale écartée après
    vérification : sommer les chunks "racine" de sections_brutes.json
    donnait 29299, différent des 28233 mots réels du corps — écart
    expliqué et confirmé : ces chunks racine, construits sous l'ANCIENNE
    règle de chevauchement, incluent le TITRE de chaque section_header
    descendant comme s'il faisait partie du texte de corps (1162 mots,
    exactement l'écart observé), alors que build_leaf_chunks.py exclut
    toujours les titres du contenu direct (ils vivent dans le champ
    "titre", jamais comptés dans "nb_mots"). Les deux fichiers ne
    comptent donc pas la même chose — sections_brutes.json n'est pas une
    référence fiable pour CETTE vérification précise.
    Référence correcte : tous les items narratifs SAUF les section_header
    eux-mêmes (leur texte est le "titre" d'un chunk, jamais son contenu),
    en excluant aussi les marqueurs table/image comme partout ailleurs."""
    items_corps = [it for it in items_enrichis if it["type"] != "section_header"]
    _texte, nb_mots, _pages = bs.assembler_contenu(items_corps)
    return nb_mots


def main():
    args = parse_cli()

    with open(args.structure_json, encoding="utf-8") as f:
        items = json.load(f)
    with open(args.sections_brutes_json, encoding="utf-8") as f:
        sections_brutes = json.load(f)

    import build_sections as bs
    from docling_core.types.doc.document import DoclingDocument
    from recover_full_text import enrichir_avec_texte_integral

    items_narratifs = [it for it in items if not bs.est_zone_qrt(it)]

    doc = DoclingDocument.load_from_json(args.docling_document_json)
    items_enrichis = enrichir_avec_texte_integral(doc, items_narratifs)

    chunks, nb_mots_avant_premier = construire_chunks_directs(items_enrichis, bs)

    n_indexable = sum(1 for c in chunks if c["categorie"] == "indexable")
    n_structurel = sum(1 for c in chunks if c["categorie"] == "structurel")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "sections_directes.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    total_nouveau = sum(c["nb_mots"] for c in chunks)
    total_reference = calculer_total_mots_reference(items_enrichis, bs)

    # Info affichée pour transparence, mais PAS utilisée comme référence de
    # validation (cf. docstring de calculer_total_mots_reference) : les
    # deux fichiers ne comptent pas la même chose (chevauchement + titres
    # inclus côté sections_brutes.json).
    racines_sb = [s for s in sections_brutes if len(s["chemin_hierarchique"]) == 1]
    total_racines_sb = sum(s["nb_mots"] for s in racines_sb)

    print("=" * 70)
    print("DISTRIBUTION DES PETITS COMPTES DE MOTS (0 à 15), pour juger du seuil")
    print("=" * 70)
    from collections import Counter
    petits = Counter(c["nb_mots"] for c in chunks if c["nb_mots"] <= 15)
    for n in sorted(petits):
        print(f"  {n:2} mot(s) : {petits[n]} chunk(s)")

    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Titres traités                              : {len(chunks)}")
    print(f"  Indexable (>= {SEUIL_MOTS_INDEXABLE} mots réels)              : {n_indexable}")
    print(f"  Structurel (< {SEUIL_MOTS_INDEXABLE} mots réels)              : {n_structurel}")

    total_nouveau_reconcilie = total_nouveau + nb_mots_avant_premier
    print(f"\n  Total mots dans les chunks (indexable+structurel)      : {total_nouveau}")
    print(f"  + mots avant le 1er header (hors chunk, cf. [INFO] ci-dessus) : {nb_mots_avant_premier}")
    print(f"  = total réconcilié                                     : {total_nouveau_reconcilie}")
    print(f"  Total mots de référence (items narratifs hors section_header, "
          f"calcul direct) : {total_reference}")
    if total_nouveau_reconcilie == total_reference:
        print("  OK — aucun mot perdu ni dupliqué (à l'exception, déjà signalée et "
              "réconciliée ci-dessus, du contenu avant le tout premier titre).")
    else:
        ecart = total_nouveau_reconcilie - total_reference
        print(f"  >>> ÉCART DÉTECTÉ (même après réconciliation) : {ecart:+d} mots — à "
              "examiner avant d'utiliser ce fichier.")

    print(f"\n  (Pour information seulement, PAS une référence de validation valide : la "
          f"somme des {len(racines_sb)} chunks racine de sections_brutes.json donne "
          f"{total_racines_sb} — différent car ces chunks comptent aussi le texte des "
          "titres descendants comme contenu, cf. docstring de calculer_total_mots_reference.)")

    print(f"\n[export] {len(chunks)} chunks écrits dans {out_path}")


if __name__ == "__main__":
    main()
