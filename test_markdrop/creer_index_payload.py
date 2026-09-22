# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier accélère les recherches filtrées par entreprise ou par année
# en créant un index dédié sur ces deux champs, dans les 4 espaces de
# rangement de la base de recherche.
# ------------------------------------------------------------------
"""creer_index_payload.py — Crée les index de payload Qdrant sur
"company_name" et "year", dans les 4 collections (texte, tableaux, images,
qrt) — accélère le filtrage natif déjà utilisé par fusion_reranking.py
(_construire_filtre, Décisions 032, 047). Sans cet index, Qdrant filtre en
scannant le payload de chaque point ; avec, la recherche filtrée passe par
une structure dédiée — la différence ne se voit pas sur les volumes actuels
(quelques centaines de points) mais devient nécessaire à l'échelle visée
(30+ documents SFCR, cf. IDEES_SCALE_UP.md).

IDEMPOTENT — vérifié empiriquement contre le serveur local (pas supposé) :
appeler create_payload_index() une 2e fois sur un champ déjà indexé ne lève
aucune erreur (Qdrant remplace silencieusement l'index existant par un
identique) — sûr à relancer, y compris après une réindexation complète.

Ne crée AUCUNE collection (déjà faites, cf. create_collection_*.py) et ne
touche à aucun point existant — uniquement des métadonnées d'index.

    python creer_index_payload.py
"""

import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qdrant_client import QdrantClient
from qdrant_client.http.models import PayloadSchemaType

HOTE_QDRANT = "localhost"
PORT_QDRANT = 6333

COLLECTIONS = ("texte", "tableaux", "images", "qrt")

# KEYWORD pour company_name (correspondance exacte de chaîne, cf.
# MatchValue dans _construire_filtre) ; INTEGER pour year (comparaisons
# numériques possibles en plus de l'égalité, cohérent avec le type Python
# int déjà utilisé partout pour ce champ, cf. Décision 046).
CHAMPS_INDEXES = {
    "company_name": PayloadSchemaType.KEYWORD,
    "year": PayloadSchemaType.INTEGER,
}


def main():
    client = QdrantClient(host=HOTE_QDRANT, port=PORT_QDRANT)

    collections_existantes = {c.name for c in client.get_collections().collections}
    manquantes = [c for c in COLLECTIONS if c not in collections_existantes]
    if manquantes:
        print(f">>> ARRÊT — collection(s) introuvable(s) sur ce serveur Qdrant : {manquantes}. "
              "Rien créé (cf. create_collection_*.py pour les créer d'abord).")
        return

    print("Création des index de payload...")
    for nom_collection in COLLECTIONS:
        for champ, schema in CHAMPS_INDEXES.items():
            client.create_payload_index(collection_name=nom_collection, field_name=champ, field_schema=schema)
            print(f"  {nom_collection:10} : index créé sur {champ!r} ({schema})")

    # --- Vérification en RE-INTERROGEANT Qdrant (pas se fier au seul fait
    # que create_payload_index() n'a pas levé d'exception). ---
    print("\n" + "=" * 70)
    print("VÉRIFICATION (relecture des collections, après création)")
    print("=" * 70)
    tout_ok = True
    for nom_collection in COLLECTIONS:
        info = client.get_collection(nom_collection)
        indexes = set(info.payload_schema.keys()) if info.payload_schema else set()
        manquants = set(CHAMPS_INDEXES) - indexes
        statut = "OK" if not manquants else "ÉCART"
        if manquants:
            tout_ok = False
        print(f"  {nom_collection:10} : champs indexés = {sorted(indexes)} [{statut}]")

    if tout_ok:
        print("\nLes 4 collections ont bien un index sur company_name et year.")
    else:
        print("\n>>> ATTENTION — au moins une collection n'a pas les index attendus, voir détail ci-dessus.")


if __name__ == "__main__":
    main()
