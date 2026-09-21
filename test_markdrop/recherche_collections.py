# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier interroge séparément chacun des 4 espaces de rangement
# (texte, tableaux, images, tableaux réglementaires) pour trouver les
# passages les plus proches de la question posée.
# ------------------------------------------------------------------
"""recherche_collections.py — 4 fonctions de recherche INDÉPENDANTES, une
par collection Qdrant (texte, tableaux, images, qrt) — AUCUNE fusion ni
reranking entre elles à ce stade, comme décidé. Chaque fonction encode la
question avec le même modèle que celui utilisé pour indexer la
collection interrogée (BGE-M3 pour "texte" et le vecteur "texte" de
"tableaux" ; Cohere Embed v4 pour "images", "qrt" et le vecteur "image"
de "tableaux"), puis interroge Qdrant local sur le vecteur nommé
correspondant.

Clients réutilisés tels quels (pas recréés différemment d'un script à
l'autre) :
- Qdrant : QdrantClient(host="localhost", port=6333), même
  host/port que create_collection_*.py et ingest_qdrant.py.
- BGE-M3 : SentenceTransformer("Shitao/bge-m3"), max_seq_length=1024,
  normalize_embeddings=True — mêmes paramètres que build_index_texte_bge.py
  (donc que l'indexation), sans quoi la similarité cosinus n'aurait pas de
  sens (espace vectoriel différent si les paramètres d'encodage diffèrent).
- Cohere Embed v4 : cohere.ClientV2(api_key=os.environ["COHERE_API_KEY"]),
  input_type="search_query" pour une question — VÉRIFIÉ dans
  comparer_cohere.py (déjà utilisé et validé là-bas pour encoder les
  questions du golden set), pas deviné ici. input_type="image" est
  réservé à l'indexation de documents (build_index_visuels.py), jamais à
  une question.

API Qdrant utilisée : client.query_points(collection_name=..., query=vecteur,
using=nom_vecteur, limit=top_k) — vérifié empiriquement contre le serveur
local (qdrant-client 1.19.0 : QdrantClient n'a PAS de méthode .search(),
seulement .query_points()), pas supposé depuis une version antérieure de
la documentation.

Les modèles (BGE-M3) et clients (Cohere, Qdrant) sont chargés une seule
fois en paresseux (singletons module), pas recréés à chaque appel de
fonction — recharger BGE-M3 à chaque question serait inutilement lent.

Prérequis :
- pip install qdrant-client sentence-transformers cohere torch (déjà
  fait, cf. scripts précédents du même venv)
- Qdrant démarré en local sur localhost:6333, les 4 collections déjà
  peuplées (cf. ingest_qdrant.py)
- variable d'environnement COHERE_API_KEY définie

    python recherche_collections.py "Quel est le SCR du Groupe ?"
"""

import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

HOTE_QDRANT = "localhost"
PORT_QDRANT = 6333

MODELE_BGE = "Shitao/bge-m3"  # même miroir safetensors que build_index_texte_bge.py / src/index.py
MODELE_COHERE = "embed-v4.0"  # même modèle que comparer_cohere.py / build_index_visuels.py

# --- Singletons paresseux : chargés une seule fois, réutilisés ensuite ---
_client_qdrant = None
_modele_bge = None
_client_cohere = None
_cache_cohere = {}  # question -> embedding, cf. encoder_cohere ci-dessous


def get_client_qdrant():
    global _client_qdrant
    if _client_qdrant is None:
        from qdrant_client import QdrantClient
        _client_qdrant = QdrantClient(host=HOTE_QDRANT, port=PORT_QDRANT)
    return _client_qdrant


def get_modele_bge():
    global _modele_bge
    if _modele_bge is None:
        import torch
        from sentence_transformers import SentenceTransformer
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[recherche_collections] chargement de {MODELE_BGE} (device: {device})...")
        _modele_bge = SentenceTransformer(MODELE_BGE, device=device)
        _modele_bge.max_seq_length = 1024  # même valeur qu'à l'indexation
    return _modele_bge


def get_client_cohere():
    global _client_cohere
    if _client_cohere is None:
        cle_api = os.environ.get("COHERE_API_KEY")
        if not cle_api:
            raise RuntimeError(
                "Variable d'environnement COHERE_API_KEY absente — nécessaire pour "
                "encoder les questions envoyées aux collections tableaux/images/qrt."
            )
        import cohere
        _client_cohere = cohere.ClientV2(api_key=cle_api)
    return _client_cohere


def encoder_bge(question):
    """Encode une question avec BGE-M3 — mêmes paramètres que
    build_index_texte_bge.py (normalize_embeddings=True), indispensable
    pour que la similarité cosinus soit comparable aux vecteurs indexés."""
    modele = get_modele_bge()
    embedding = modele.encode([question], normalize_embeddings=True, convert_to_numpy=True)[0]
    return embedding.tolist()


def encoder_cohere(question):
    """Encode une question avec Cohere Embed v4 — input_type="search_query",
    vérifié dans comparer_cohere.py (déjà utilisé et validé là pour les
    questions du golden set), jamais "image" (réservé aux documents
    indexés, cf. build_index_visuels.py).

    CACHE ajouté (clé COHERE_API_KEY trial, plafond RÉEL rencontré à
    l'usage : 1000 appels/mois, tombé à ~84 restants en cours de session) :
    fusionner_candidats() appelle cette fonction 3 FOIS PAR QUESTION
    (une fois chacune dans rechercher_tableaux_pour_fusion,
    rechercher_images_pour_fusion, rechercher_qrt_pour_fusion) pour
    ENCODER LA MÊME CHAÎNE — gaspillage confirmé, pas supposé, avant ce
    correctif. Résultat identique (déterministe, même question -> même
    vecteur), donc mise en cache pure, aucun changement de comportement/
    résultat, juste 3x moins d'appels API par question fusionnée."""
    if question in _cache_cohere:
        return _cache_cohere[question]
    co = get_client_cohere()
    resp = co.embed(
        model=MODELE_COHERE,
        input_type="search_query",
        embedding_types=["float"],
        texts=[question],
    )
    embedding = resp.embeddings.float[0]
    _cache_cohere[question] = embedding
    return embedding


def formater_resultats(reponse_qdrant):
    """Transforme la réponse Qdrant (QueryResponse.points) en liste de
    dictionnaires simples : score + payload complet aplati — même forme
    pour les 4 collections, quel que soit leur schéma de payload propre."""
    return [
        {"score": point.score, **point.payload}
        for point in reponse_qdrant.points
    ]


def rechercher_texte(question, top_k=5):
    """Interroge la collection "texte" (190 chunks narratifs) sur le
    vecteur nommé "dense" (BGE-M3, 1024 dim). Payload : chemin_hierarchique,
    pages, annee_document, position_header/position_origine."""
    vecteur = encoder_bge(question)
    reponse = get_client_qdrant().query_points(
        collection_name="texte", query=vecteur, using="dense", limit=top_k,
    )
    return formater_resultats(reponse)


def rechercher_tableaux(question, top_k=5, vecteur="image"):
    """Interroge la collection "tableaux" (18 tableaux, double
    représentation). vecteur="image" (défaut) : encode la question avec
    Cohere Embed v4, interroge le vecteur nommé "image" (crop du
    tableau). vecteur="texte" : encode avec BGE-M3, interroge le vecteur
    nommé "texte" (représentation markdown structurée) à la place.
    Payload complet, y compris chemin_relatif (pour l'affichage de
    l'image)."""
    if vecteur not in ("image", "texte"):
        raise ValueError(f"vecteur={vecteur!r} invalide — attendu 'image' ou 'texte'.")

    vecteur_requete = encoder_cohere(question) if vecteur == "image" else encoder_bge(question)
    reponse = get_client_qdrant().query_points(
        collection_name="tableaux", query=vecteur_requete, using=vecteur, limit=top_k,
    )
    return formater_resultats(reponse)


def rechercher_images(question, top_k=5):
    """Interroge la collection "images" (5 images narratives) sur le
    vecteur nommé "image" (Cohere Embed v4, 1536 dim)."""
    vecteur = encoder_cohere(question)
    reponse = get_client_qdrant().query_points(
        collection_name="images", query=vecteur, using="image", limit=top_k,
    )
    return formater_resultats(reponse)


def rechercher_qrt(question, top_k=5):
    """Interroge la collection "qrt" (13 pages QRT pleine page) sur le
    vecteur nommé "image" (Cohere Embed v4, 1536 dim)."""
    vecteur = encoder_cohere(question)
    reponse = get_client_qdrant().query_points(
        collection_name="qrt", query=vecteur, using="image", limit=top_k,
    )
    return formater_resultats(reponse)


def tester_question(question, top_k=5):
    """Test manuel rapide : appelle les 4 fonctions et affiche leurs
    résultats CÔTE À CÔTE — pas de fusion ni de classement combiné, chaque
    collection reste indépendante à ce stade (comme décidé)."""
    print(f"\nQuestion : {question!r}\n")

    for nom_collection, fonction, kwargs in [
        ("texte", rechercher_texte, {}),
        ("tableaux (image)", rechercher_tableaux, {"vecteur": "image"}),
        ("tableaux (texte)", rechercher_tableaux, {"vecteur": "texte"}),
        ("images", rechercher_images, {}),
        ("qrt", rechercher_qrt, {}),
    ]:
        print("=" * 70)
        print(f"{nom_collection.upper()}")
        print("=" * 70)
        try:
            resultats = fonction(question, top_k=top_k, **kwargs)
        except Exception as e:
            print(f"  >>> ÉCHEC : {type(e).__name__}: {e}")
            continue
        if not resultats:
            print("  (aucun résultat)")
        for rang, r in enumerate(resultats, start=1):
            chemin_hier = r.get("chemin_hierarchique")
            self_ref = r.get("self_ref")
            pos = r.get("position_origine") or r.get("position_header")
            identifiant = self_ref if self_ref is not None else f"position={pos}"
            print(f"  {rang}. score={r['score']:.4f}  {identifiant}  "
                  f"pages={r.get('pages')}  chemin_hierarchique={chemin_hier!r}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python recherche_collections.py \"question\"")
        sys.exit(1)
    tester_question(" ".join(sys.argv[1:]))
