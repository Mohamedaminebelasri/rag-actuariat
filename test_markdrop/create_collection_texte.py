# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier crée, dans la base de données de recherche (Qdrant), un
# espace de rangement vide dédié au texte narratif du rapport. C'est une
# étape de préparation, à faire une seule fois.
# ------------------------------------------------------------------
"""create_collection_texte.py — Crée la collection Qdrant "texte" (la plus
simple des 4 collections prévues : texte, tableaux, images, QRT — un seul
vecteur nommé, pas de double représentation texte+image comme pour les
tableaux). Qdrant tourne en local (localhost:6333, cf. installation
préalable du binaire natif Windows v1.19.1).

Ne crée QUE cette collection — les 3 autres (tableaux, images, QRT) seront
créées séparément, une à la fois. N'insère aucun point : la collection est
créée vide, prête à recevoir les embeddings du texte narratif (BGE-M3,
Décision 004) dans une étape ultérieure.

Dimension du vecteur : 1024 — vérifiée sur la fiche modèle officielle
BAAI/bge-m3 (https://huggingface.co/BAAI/bge-m3, section "Specs" :
"Dimension: 1024"), pas supposée.

Prérequis :
- pip install qdrant-client (déjà fait)
- Qdrant démarré en local sur localhost:6333 (qdrant.exe déjà lancé)

    python create_collection_texte.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

# Adresse du serveur Qdrant local — pas de port gRPC ici, QdrantClient
# utilise le REST (6333) par défaut pour ce type d'appel.
HOTE_QDRANT = "localhost"
PORT_QDRANT = 6333

NOM_COLLECTION = "texte"
NOM_VECTEUR = "dense"  # nom du vecteur nommé — un seul ici, contrairement aux futures collections tableaux/images
DIMENSION_VECTEUR = 1024  # BGE-M3, vérifié sur https://huggingface.co/BAAI/bge-m3 ("Dimension: 1024"), pas deviné
DISTANCE_VECTEUR = Distance.COSINE


def main():
    client = QdrantClient(host=HOTE_QDRANT, port=PORT_QDRANT)

    # Garde-fou : ne pas recréer silencieusement une collection existante
    # (recreate_collection supprimerait des points déjà présents) — ici la
    # collection doit être créée vide, donc on s'arrête si elle existe déjà
    # plutôt que de la remplacer sans le signaler explicitement.
    collections_existantes = [c.name for c in client.get_collections().collections]
    if NOM_COLLECTION in collections_existantes:
        print(f">>> ARRÊT — la collection {NOM_COLLECTION!r} existe déjà sur ce serveur Qdrant. "
              "Rien recréé, pour ne pas risquer d'effacer des points déjà insérés. "
              "Supprime-la explicitement d'abord si une recréation est bien voulue.")
        return

    client.create_collection(
        collection_name=NOM_COLLECTION,
        vectors_config={
            NOM_VECTEUR: VectorParams(size=DIMENSION_VECTEUR, distance=DISTANCE_VECTEUR),
        },
    )

    # Confirmation en RE-INTERROGEANT Qdrant après création — ne pas se
    # fier au seul fait que create_collection() n'a pas levé d'exception.
    info = client.get_collection(NOM_COLLECTION)
    config_vecteurs = info.config.params.vectors

    print(f"Collection {NOM_COLLECTION!r} confirmée présente sur Qdrant (relecture après création) :")
    print(f"  nombre de points : {info.points_count} (attendu : 0, collection vide)")
    print(f"  vecteurs nommés configurés :")
    for nom, params in config_vecteurs.items():
        print(f"    - {nom!r} : taille={params.size}, distance={params.distance}")

    if info.points_count != 0:
        print("  >>> ATTENTION inattendue : la collection contient déjà des points "
              "alors qu'elle vient d'être créée — à vérifier manuellement.")

    if NOM_VECTEUR not in config_vecteurs or config_vecteurs[NOM_VECTEUR].size != DIMENSION_VECTEUR:
        print(f"  >>> ATTENTION — la config relue ne correspond pas à ce qui a été demandé "
              f"({NOM_VECTEUR!r}, taille {DIMENSION_VECTEUR}) — à vérifier avant de continuer.")


if __name__ == "__main__":
    main()
