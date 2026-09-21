# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier fait la même chose que le précédent, mais pour l'espace de
# rangement dédié aux tableaux.
# ------------------------------------------------------------------
"""create_collection_tableaux.py — Crée la collection Qdrant "tableaux" :
seule (avec "images") des 4 collections prévues à porter DEUX vecteurs
nommés par point — la double représentation texte + image d'un même
tableau (version markdown/structurée d'un côté, fichier image réel de
l'autre). Qdrant tourne en local (localhost:6333).

Ne crée QUE cette collection — "texte" est déjà créée, "images" et "qrt"
restent à créer séparément. N'insère aucun point : la collection est créée
vide.

Dimensions des 2 vecteurs :
- "texte" : 1024 — BGE-M3 (Décision 004), même dimension que la collection
  "texte" déjà créée (fiche modèle https://huggingface.co/BAAI/bge-m3,
  "Dimension: 1024").
- "image" : 1536 — Cohere Embed v4 (Décision 027), RE-VÉRIFIÉE ici
  directement dans output_structure_brute/index_visuels_cohere.json
  (les 36 entrées réelles, pas seulement rappelée depuis la consigne) :
  une seule dimension distincte trouvée sur les 36 embeddings, 1536.

Prérequis :
- pip install qdrant-client (déjà fait)
- Qdrant démarré en local sur localhost:6333
- output_structure_brute/index_visuels_cohere.json présent (pour la
  vérification de dimension du vecteur "image")

    python create_collection_tableaux.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

BASE_DIR = Path(__file__).parent
INDEX_VISUELS_COHERE_JSON = BASE_DIR / "output_structure_brute" / "index_visuels_cohere.json"

HOTE_QDRANT = "localhost"
PORT_QDRANT = 6333

NOM_COLLECTION = "tableaux"
NOM_VECTEUR_TEXTE = "texte"
DIMENSION_TEXTE = 1024  # BGE-M3, cf. https://huggingface.co/BAAI/bge-m3 ("Dimension: 1024")
NOM_VECTEUR_IMAGE = "image"
DISTANCE_VECTEUR = Distance.COSINE


def verifier_dimension_cohere_reelle():
    """Ne PAS recopier 1536 depuis la consigne sans vérification : relit
    les embeddings RÉELS déjà produits par build_index_visuels.py et
    lève une erreur explicite si plusieurs dimensions distinctes
    apparaissent (signe d'un problème à investiguer, pas à masquer en
    prenant la première valeur trouvée)."""
    if not INDEX_VISUELS_COHERE_JSON.exists():
        raise FileNotFoundError(
            f"{INDEX_VISUELS_COHERE_JSON} introuvable — impossible de vérifier la dimension "
            "réelle des embeddings Cohere avant de créer la collection. Lance "
            "build_index_visuels.py d'abord, ou fournis ce fichier."
        )
    with open(INDEX_VISUELS_COHERE_JSON, encoding="utf-8") as f:
        entrees = json.load(f)

    dimensions_trouvees = {len(e["embedding"]) for e in entrees}
    if len(dimensions_trouvees) != 1:
        raise ValueError(
            f"Dimensions Cohere INCOHÉRENTES trouvées dans {INDEX_VISUELS_COHERE_JSON.name} : "
            f"{dimensions_trouvees} — arrêt plutôt que de deviner laquelle est la bonne."
        )
    return dimensions_trouvees.pop()


def main():
    dimension_image = verifier_dimension_cohere_reelle()
    print(f"Dimension du vecteur 'image' vérifiée dans {INDEX_VISUELS_COHERE_JSON.name} : "
          f"{dimension_image} (36 entrées, une seule dimension distincte trouvée)")

    client = QdrantClient(host=HOTE_QDRANT, port=PORT_QDRANT)

    # Même garde-fou que create_collection_texte.py : ne pas recréer/écraser
    # silencieusement une collection existante.
    collections_existantes = [c.name for c in client.get_collections().collections]
    if NOM_COLLECTION in collections_existantes:
        print(f">>> ARRÊT — la collection {NOM_COLLECTION!r} existe déjà sur ce serveur Qdrant. "
              "Rien recréé, pour ne pas risquer d'effacer des points déjà insérés. "
              "Supprime-la explicitement d'abord si une recréation est bien voulue.")
        return

    client.create_collection(
        collection_name=NOM_COLLECTION,
        vectors_config={
            NOM_VECTEUR_TEXTE: VectorParams(size=DIMENSION_TEXTE, distance=DISTANCE_VECTEUR),
            NOM_VECTEUR_IMAGE: VectorParams(size=dimension_image, distance=DISTANCE_VECTEUR),
        },
    )

    # Confirmation en RE-INTERROGEANT Qdrant après création — ne pas se
    # fier au seul fait que create_collection() n'a pas levé d'exception.
    info = client.get_collection(NOM_COLLECTION)
    config_vecteurs = info.config.params.vectors

    print(f"\nCollection {NOM_COLLECTION!r} confirmée présente sur Qdrant (relecture après création) :")
    print(f"  nombre de points : {info.points_count} (attendu : 0, collection vide)")
    print(f"  vecteurs nommés configurés :")
    for nom, params in config_vecteurs.items():
        print(f"    - {nom!r} : taille={params.size}, distance={params.distance}")

    if info.points_count != 0:
        print("  >>> ATTENTION inattendue : la collection contient déjà des points "
              "alors qu'elle vient d'être créée — à vérifier manuellement.")

    attendu = {NOM_VECTEUR_TEXTE: DIMENSION_TEXTE, NOM_VECTEUR_IMAGE: dimension_image}
    for nom, taille_attendue in attendu.items():
        if nom not in config_vecteurs or config_vecteurs[nom].size != taille_attendue:
            print(f"  >>> ATTENTION — la config relue pour {nom!r} ne correspond pas à ce qui a "
                  f"été demandé (taille attendue {taille_attendue}) — à vérifier avant de continuer.")


if __name__ == "__main__":
    main()
