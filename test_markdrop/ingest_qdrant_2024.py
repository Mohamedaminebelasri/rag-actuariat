# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier fait la même chose que le précédent, mais pour ajouter le
# rapport de l'année 2024, sans toucher à ce qui est déjà en place pour
# 2025.
# ------------------------------------------------------------------
"""ingest_qdrant_2024.py — Ingère les index 2024 dans les 4 collections
Qdrant EXISTANTES (texte, tableaux, images, qrt — PAS de nouvelle
collection), en réutilisant ingest_qdrant.main()/id_deterministe() TELS
QUELS (annee=2024 salé dans les IDs, cf. leur docstring). Vérifie, par
une VRAIE re-requête Qdrant avant/après (pas juste le compte envoyé) :
1. le delta de points ajoutés correspond à l'attendu 2024 ;
2. un échantillon de points 2025 déjà en place est BYTE-POUR-BYTE
   inchangé après l'ingestion 2024 (même embedding, même payload) —
   preuve directe qu'aucune collision d'ID n'a écrasé de point 2025.
"""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from qdrant_client import QdrantClient
import ingest_qdrant as iq

BASE_DIR = Path(__file__).parent
OUT = BASE_DIR / "output_structure_brute_2024"

N_TEXTE_2024 = 191
N_TABLEAUX_2024 = 18
N_IMAGES_2024 = 3
N_QRT_2024 = 14


def snapshot_echantillon_2025(client, n=3):
    """Retourne un échantillon de points 2025 (id, vector, payload) par
    collection, à re-comparer après l'ingestion 2024 pour prouver
    qu'aucun point 2025 n'a été altéré.

    BUG RÉEL RENCONTRÉ ET CORRIGÉ ICI : un premier essai comparait 2
    scroll() successifs (avant/après ingestion) — scroll() ne garantit PAS
    un ordre stable d'un appel à l'autre une fois la collection modifiée
    (des points insérés entre-temps), donc l'échantillon "après" n'était
    pas les MÊMES points que l'échantillon "avant" : 8 "disparitions"
    signalées à tort, alors qu'un retrieve() direct par ID a confirmé les
    8 points parfaitement intacts (year=2025). Fix : on fige ici
    la LISTE D'IDs via un seul scroll(), puis on relit TOUJOURS ces mêmes
    IDs explicites (retrieve, jamais scroll) pour la comparaison finale."""
    echantillons = {}
    for nom in ("texte", "tableaux", "images", "qrt"):
        points, _ = client.scroll(collection_name=nom, limit=n, with_vectors=True, with_payload=True)
        echantillons[nom] = {p.id: (p.vector, p.payload) for p in points}
    return echantillons


def relire_par_id(client, echantillon):
    """Relit EXACTEMENT les mêmes IDs qu'un échantillon précédent, via
    retrieve() (accès direct par ID, jamais scroll — cf. docstring de
    snapshot_echantillon_2025)."""
    relu = {}
    for nom, points in echantillon.items():
        ids = list(points.keys())
        resultats = client.retrieve(collection_name=nom, ids=ids, with_vectors=True, with_payload=True)
        relu[nom] = {p.id: (p.vector, p.payload) for p in resultats}
    return relu


def comparer_echantillons(avant, apres):
    tout_identique = True
    for nom in avant:
        for id_point, (vec_avant, payload_avant) in avant[nom].items():
            if id_point not in apres[nom]:
                print(f"  >>> ALERTE — point {id_point} de la collection {nom!r} a DISPARU après l'ingestion 2024.")
                tout_identique = False
                continue
            vec_apres, payload_apres = apres[nom][id_point]
            if vec_avant != vec_apres:
                print(f"  >>> ALERTE — vecteur MODIFIÉ pour le point {id_point} ({nom!r}) après l'ingestion 2024.")
                tout_identique = False
            if payload_avant != payload_apres:
                print(f"  >>> ALERTE — payload MODIFIÉ pour le point {id_point} ({nom!r}) après l'ingestion 2024.")
                tout_identique = False
    if tout_identique:
        print(f"  OK — {sum(len(v) for v in avant.values())} point(s) 2025 échantillonné(s) "
              "(vecteurs + payloads) strictement IDENTIQUES avant/après l'ingestion 2024.")
    return tout_identique


def main():
    client = QdrantClient(host=iq.HOTE_QDRANT, port=iq.PORT_QDRANT)

    print("=" * 70)
    print("SNAPSHOT points 2025 AVANT ingestion 2024 (contrôle non-régression)")
    print("=" * 70)
    echantillon_avant = snapshot_echantillon_2025(client)
    for nom, pts in echantillon_avant.items():
        print(f"  {nom:10} : {len(pts)} point(s) échantillonné(s) pour comparaison ultérieure")

    print("\n" + "=" * 70)
    print("INGESTION 2024")
    print("=" * 70)
    iq.main(
        index_texte_json=OUT / "index_texte_bge.json",
        index_tableaux_texte_json=OUT / "index_tableaux_texte_bge.json",
        index_visuels_cohere_json=OUT / "index_visuels_cohere.json",
        annee=2024,
        n_texte_attendu=N_TEXTE_2024,
        n_tableaux_attendu=N_TABLEAUX_2024,
        n_images_attendu=N_IMAGES_2024,
        n_qrt_attendu=N_QRT_2024,
        verifier_delta_uniquement=True,
        company_name="Groupama", company_type="mutuelle",
        source_file="SFCR_2024_Groupe-Groupama.pdf",
    )

    print("\n" + "=" * 70)
    print("VÉRIFICATION NON-RÉGRESSION — re-requête des MÊMES points 2025 par ID exact")
    print("=" * 70)
    echantillon_apres = relire_par_id(client, echantillon_avant)
    comparer_echantillons(echantillon_avant, echantillon_apres)

    print("\n" + "=" * 70)
    print("VÉRIFICATION — les points 2024 sont bien retrouvables par filtre year=2024")
    print("=" * 70)
    from qdrant_client.http.models import Filter, FieldCondition, MatchValue
    filtre_2024 = Filter(must=[FieldCondition(key="year", match=MatchValue(value=2024))])
    for nom in ("texte", "tableaux", "images", "qrt"):
        n = client.count(collection_name=nom, count_filter=filtre_2024).count
        print(f"  {nom:10} : {n} point(s) avec year=2024")


if __name__ == "__main__":
    main()
