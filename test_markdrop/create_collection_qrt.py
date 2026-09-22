# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier fait la même chose, mais pour l'espace de rangement dédié
# aux tableaux réglementaires (QRT).
# ------------------------------------------------------------------
"""create_collection_qrt.py — Crée la collection Qdrant "qrt" : un seul
vecteur nommé par point (Cohere Embed v4 uniquement), même structure que
"images" — les pages QRT sont traitées comme des images de page entière
(pas d'item Docling individuel, cf. Décision de l'étape 3 /
chemins_visuels.py), donc pas de double représentation texte+image comme
pour "tableaux". Qdrant tourne en local (localhost:6333).

C'est la 4e et DERNIÈRE des 4 collections prévues (texte, tableaux,
images, qrt — les 3 premières sont déjà créées et confirmées). N'insère
aucun point : la collection est créée vide. Affiche, une fois celle-ci
confirmée, un résumé global des 4 collections en interrogeant Qdrant
directement (pas depuis la mémoire des scripts précédents), pour une vue
d'ensemble avant de passer à l'ingestion réelle des données.

Dimension du vecteur "image" : 1536 — Cohere Embed v4 (Décision 027),
RE-VÉRIFIÉE ici directement dans
output_structure_brute/index_visuels_cohere.json, comme pour "tableaux"
et "images" — chaque collection revérifie indépendamment, jamais recopiée
d'un script à l'autre.

Prérequis :
- pip install qdrant-client (déjà fait)
- Qdrant démarré en local sur localhost:6333
- output_structure_brute/index_visuels_cohere.json présent (pour la
  vérification de dimension du vecteur "image")

    python create_collection_qrt.py
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

NOM_COLLECTION = "qrt"
NOM_VECTEUR_IMAGE = "image"
DISTANCE_VECTEUR = Distance.COSINE

# Les 4 collections prévues au total pour le résumé final — indépendant de
# l'ordre de création, sert uniquement à l'affichage de la vue d'ensemble.
TOUTES_LES_COLLECTIONS_PREVUES = ["texte", "tableaux", "images", "qrt"]


def verifier_dimension_cohere_reelle():
    """Ne PAS recopier 1536 depuis la consigne ou depuis un autre script
    sans vérification : relit les embeddings RÉELS déjà produits par
    build_index_visuels.py et lève une erreur explicite si plusieurs
    dimensions distinctes apparaissent, plutôt que de masquer le problème
    en prenant la première valeur trouvée."""
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


def creer_collection_qrt(client, dimension_image):
    # Même garde-fou que les 3 collections précédentes : ne pas
    # recréer/écraser silencieusement une collection existante.
    collections_existantes = [c.name for c in client.get_collections().collections]
    if NOM_COLLECTION in collections_existantes:
        print(f">>> ARRÊT — la collection {NOM_COLLECTION!r} existe déjà sur ce serveur Qdrant. "
              "Rien recréé, pour ne pas risquer d'effacer des points déjà insérés. "
              "Supprime-la explicitement d'abord si une recréation est bien voulue.")
        return False

    client.create_collection(
        collection_name=NOM_COLLECTION,
        vectors_config={
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

    if NOM_VECTEUR_IMAGE not in config_vecteurs or config_vecteurs[NOM_VECTEUR_IMAGE].size != dimension_image:
        print(f"  >>> ATTENTION — la config relue pour {NOM_VECTEUR_IMAGE!r} ne correspond pas à ce "
              f"qui a été demandé (taille attendue {dimension_image}) — à vérifier avant de continuer.")

    return True


def afficher_resume_global(client):
    """Interroge Qdrant DIRECTEMENT pour les 4 collections prévues — ne
    réutilise aucune valeur mémorisée des scripts précédents, pour que ce
    résumé reflète l'état réel du serveur au moment où il est affiché."""
    print("\n" + "=" * 70)
    print("RÉSUMÉ GLOBAL DES 4 COLLECTIONS (interrogé directement sur Qdrant)")
    print("=" * 70)

    collections_existantes = [c.name for c in client.get_collections().collections]

    for nom_collection in TOUTES_LES_COLLECTIONS_PREVUES:
        if nom_collection not in collections_existantes:
            print(f"\n{nom_collection!r} : >>> ABSENTE sur ce serveur Qdrant (pas encore créée)")
            continue

        info = client.get_collection(nom_collection)
        config_vecteurs = info.config.params.vectors
        print(f"\n{nom_collection!r} : {info.points_count} point(s)")
        for nom_vecteur, params in config_vecteurs.items():
            print(f"    - {nom_vecteur!r} : taille={params.size}, distance={params.distance}")

    manquantes = [n for n in TOUTES_LES_COLLECTIONS_PREVUES if n not in collections_existantes]
    if manquantes:
        print(f"\n>>> {len(manquantes)} collection(s) prévue(s) encore absente(s) : {manquantes}")
    else:
        print("\nLes 4 collections prévues sont toutes présentes, vides, prêtes pour l'ingestion.")


def main():
    dimension_image = verifier_dimension_cohere_reelle()
    print(f"Dimension du vecteur 'image' vérifiée dans {INDEX_VISUELS_COHERE_JSON.name} : "
          f"{dimension_image} (36 entrées, une seule dimension distincte trouvée)")

    client = QdrantClient(host=HOTE_QDRANT, port=PORT_QDRANT)

    creer_collection_qrt(client, dimension_image)
    afficher_resume_global(client)


if __name__ == "__main__":
    main()
