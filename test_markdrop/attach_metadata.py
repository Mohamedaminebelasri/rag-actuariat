# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier attache à chaque morceau de texte les informations qui
# permettront de citer sa source plus tard (numéro de page, titre de la
# section).
# ------------------------------------------------------------------
"""attach_metadata.py — Étape 4 : attache aux 226 chunks de
chunks_finaux.json les métadonnées finales de citation (chemin
hiérarchique complet, pages réellement couvertes, année du document),
avant vectorisation.

Ne recalcule RIEN depuis les items bruts (structure_finale_v4.json,
DoclingDocument) : chunks_finaux.json porte déjà, pour chaque chunk
final, un "chemin_hierarchique" et des "pages" calculés au moment du
découpage (split_and_merge_chunks.py) — directement à partir des items
narratifs réellement inclus dans CE chunk précis, pas du chunk parent
entier. Ce script :
- reprend ces "pages" telles quelles (déjà au bon grain, cf. LIMITE
  CONNUE ci-dessous) ;
- recalcule le "chemin_hierarchique" à partir de celui, déjà validé, du
  chunk PARENT dans sections_directes.json (la référence demandée), en y
  ajoutant un niveau supplémentaire uniquement pour les VRAIS sous-chunks
  bullet-titre (pas pour le sous-chunk "avant le 1er bullet", dont le
  titre est déjà celui du parent).

LIMITE CONNUE (pas corrigée ici, hors périmètre de ce script) : pour les
sous-chunks "paragraphe/type 2" (decouper_paragraphe dans
split_and_merge_chunks.py), la page du SECTION_HEADER parent est
systématiquement ajoutée aux "pages" de CHAQUE sous-chunk issu de ce
parent, même ceux qui ne touchent plus réellement cette page (vérifié sur
le chunk "A.2. Résultats de souscription", position 163 : ses 3
sous-chunks portent tous la page 18, y compris le 3e qui ne contient sans
doute aucun contenu réel page 18). Corriger cela demanderait de rouvrir
les items bruts (hors périmètre des 2 fichiers d'entrée de cette étape,
qui ne recharge QUE chunks_finaux.json et sections_directes.json) — signalé
ici plutôt que corrigé en silence.

Ne modifie ni chunks_finaux.json ni sections_directes.json (lecture seule).

    python attach_metadata.py [chunks_finaux.json] [sections_directes.json] [dossier_sortie] [--annee 2025]
"""

import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

# Isolé et paramétrable en ligne de commande (--annee) : même pipeline
# réutilisé tel quel pour le document 2024 plus tard, sans toucher au
# code, juste à l'argument passé.
ANNEE_DOCUMENT_DEFAUT = 2025

LONGUEUR_APERCU_TEXTE = 160  # uniquement pour l'affichage console de l'échantillon, jamais pour l'export


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("chunks_finaux_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "chunks_finaux.json"))
    p.add_argument("sections_directes_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "sections_directes.json"))
    p.add_argument("output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"))
    p.add_argument("--annee", type=int, default=ANNEE_DOCUMENT_DEFAUT,
                    help="Année du document SFCR (défaut : %(default)s)")
    return p.parse_args()


def est_vrai_sous_chunk_bullet(chunk):
    """Distingue, parmi les chunks "origine_decoupage" == "bullet_titre",
    le VRAI sous-chunk bullet (titre = texte d'un bullet-titre, position_
    origine = position du bullet) du sous-chunk "avant le 1er bullet"
    (titre = celui du parent, position_origine = position_header du
    parent lui-même, cf. decouper_bullet_titre dans
    split_and_merge_chunks.py). Seul le premier cas ajoute un niveau au
    chemin hiérarchique — le second est déjà couvert par le chemin du
    parent tel quel, puisque son titre EST celui du parent."""
    return (chunk.get("origine_decoupage") == "bullet_titre"
            and chunk["position_origine"] != chunk["position_header"])


def construire_chemin_final(chunk, chemin_parent):
    """Chemin hiérarchique complet, sous forme de chaîne lisible pour
    citation ("A > B > C"), à partir du chemin déjà calculé du chunk
    PARENT (sections_directes.json) — inchangé pour tout sauf un VRAI
    sous-chunk bullet-titre, auquel cas son propre titre (le texte du
    bullet) est ajouté en dernier niveau."""
    chemin_liste = list(chemin_parent)
    if est_vrai_sous_chunk_bullet(chunk):
        chemin_liste = chemin_liste + [chunk["titre"]]
    return " > ".join(chemin_liste)


def main():
    args = parse_cli()

    with open(args.chunks_finaux_json, encoding="utf-8") as f:
        chunks = json.load(f)
    with open(args.sections_directes_json, encoding="utf-8") as f:
        sections_directes = json.load(f)

    chemins_parents = {s["position_header"]: s["chemin_hierarchique"] for s in sections_directes}

    # --- Vérification de correspondance AVANT tout calcul : chaque chunk
    # final doit retrouver son chunk parent d'origine dans
    # sections_directes.json via position_header. Ne devrait jamais
    # échouer (position_header copié tel quel depuis le parent à l'étape
    # précédente) — signalé et arrêté explicitement si ça arrive, plutôt
    # que de deviner un chemin par défaut. ---
    sans_correspondance = [c for c in chunks if c["position_header"] not in chemins_parents]
    if sans_correspondance:
        print(">>> ARRÊT — chunk(s) sans correspondance claire vers un chunk parent de "
              "sections_directes.json (position_header introuvable) :")
        for c in sans_correspondance:
            print(f"    position_header={c['position_header']}  titre={c['titre']!r}")
        print("\nAucune valeur par défaut devinée. Rien exporté.")
        return

    # --- Attache des métadonnées : conserve tous les champs existants,
    # met à jour "chemin_hierarchique" (étendu pour les vrais sous-chunks
    # bullet-titre) et "pages" (déjà calculées au bon grain par chunk,
    # cf. LIMITE CONNUE en tête de module), ajoute "annee_document". ---
    chunks_avec_metadata = []
    for chunk in chunks:
        chemin_parent = chemins_parents[chunk["position_header"]]
        nouveau_chunk = dict(chunk)  # copie — ne modifie pas l'entrée d'origine
        nouveau_chunk["chemin_hierarchique"] = construire_chemin_final(chunk, chemin_parent)
        nouveau_chunk["pages"] = chunk["pages"]  # déjà au grain du chunk précis (cf. LIMITE CONNUE)
        nouveau_chunk["annee_document"] = args.annee
        chunks_avec_metadata.append(nouveau_chunk)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "chunks_avec_metadata.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks_avec_metadata, f, ensure_ascii=False, indent=2)

    # --- Échantillon de 5 chunks, mélange des 3 origines, pour
    # vérification visuelle rapide du format (texte tronqué À L'AFFICHAGE
    # SEULEMENT — le fichier exporté garde le texte intégral). ---
    par_origine = {"bullet_titre": [], "paragraphe_type2": [], None: []}
    for c in chunks_avec_metadata:
        par_origine[c.get("origine_decoupage")].append(c)

    echantillon = (par_origine["bullet_titre"][:2]
                   + par_origine["paragraphe_type2"][:2]
                   + par_origine[None][:1])

    print("=" * 70)
    print(f"ÉCHANTILLON DE {len(echantillon)} CHUNKS (bullet-titre / paragraphe-type2 / inchangé)")
    print("=" * 70)
    for c in echantillon:
        apercu = (c["texte"][:LONGUEUR_APERCU_TEXTE] + "…") if len(c["texte"]) > LONGUEUR_APERCU_TEXTE else c["texte"]
        print(f"\n  origine_decoupage : {c.get('origine_decoupage')}")
        print(f"  titre             : {c['titre']!r}")
        print(f"  chemin_hierarchique : {c['chemin_hierarchique']!r}")
        print(f"  pages             : {c['pages']}")
        print(f"  annee_document    : {c['annee_document']}")
        print(f"  nb_mots           : {c['nb_mots']}")
        print(f"  categorie         : {c['categorie']}")
        print(f"  texte (aperçu)    : {apercu!r}")

    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Chunks chargés               : {len(chunks)}")
    print(f"  Chunks avec métadonnées attachées : {len(chunks_avec_metadata)}")
    n_chemin_etendu = sum(1 for c in chunks if est_vrai_sous_chunk_bullet(c))
    print(f"  dont chemin_hierarchique étendu (vrai bullet-titre) : {n_chemin_etendu}")
    print(f"  Année du document (--annee)  : {args.annee}")
    print(f"\n[export] {len(chunks_avec_metadata)} chunks écrits dans {out_path}")


if __name__ == "__main__":
    main()
