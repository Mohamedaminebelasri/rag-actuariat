# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier transforme chaque morceau de texte en une représentation
# numérique (un « embedding ») qui permet de le retrouver par le sens de
# la question posée, pas seulement par les mots exacts.
# ------------------------------------------------------------------
"""build_index_texte_bge.py — Encode le texte narratif du SFCR 2025 avec
BGE-M3 (dense, 1024 dim — Décision 004), pour :
1. la collection Qdrant "texte" (190 chunks indexables de
   chunks_propres.json) ;
2. le vecteur nommé "texte" de la collection "tableaux" (18 tableaux,
   représentation markdown structurée — distincte du crop image déjà
   encodé par Cohere dans index_visuels_cohere.json, cf.
   create_collection_tableaux.py).

Modèle : chargé via "Shitao/bge-m3" — miroir safetensors du modèle
BAAI/bge-m3, MÊME méthode que src/index.py (Décision 004, contourne la
restriction CVE-2025-32434 sans toucher torch/transformers) :
SentenceTransformer(...), max_seq_length=1024, normalize_embeddings=True.
Dimension 1024 vérifiée sur https://huggingface.co/BAAI/bge-m3
("Dimension: 1024") ET déjà utilisée pour créer les collections Qdrant
"texte"/"tableaux" (create_collection_texte.py / create_collection_tableaux.py).

Texte à encoder — RÈGLE CONFIRMÉE (pas réinventée) :
    texte_a_encoder = " > ".join(chemin_hierarchique.split(" > ")[-2:]) + "\n" + texte
Les 2 DERNIERS segments du chemin hiérarchique (qui se termine déjà par le
titre propre du chunk) + le texte du chunk. Cas rare (chemin_hierarchique
à un seul segment, ex. chunk racine sans parent) : le slicing [-2:] ne
plante jamais sur un index hors bornes, mais le cas est signalé
explicitement plutôt que masqué silencieusement.

Représentation texte des tableaux — VÉRIFIÉ avant d'écrire ce script :
aucun fichier markdown pré-exporté n'existe pour les 18 tableaux
narratifs de CE document (recherché dans output_structure_brute/ — rien
trouvé). Seul un run PARTIEL et sans rapport (build_final.py /
output_sectionE_QRT, sur un sous-PDF différent avec sa propre numérotation
locale incompatible) produit un tel champ "markdown" — pas réutilisable
ici sans risquer un mauvais alignement self_ref. Regénérée à la place
depuis docling_document_complet.json (le DoclingDocument CANONIQUE de ce
document, self_ref-aligné avec table_N.png) via
table.export_to_dataframe().to_markdown() — la MÊME méthode déjà établie
dans ce projet (build_final.py), appliquée à la bonne source, donc pas
une extraction improvisée.

chemin_hierarchique des tableaux : réutilise TELLE QUELLE la logique déjà
écrite et décidée dans build_index_visuels.py
(charger_occurrences_narratives / resoudre_chemin_hierarchique) plutôt
que de la redéfinir — même traitement des tableaux jamais référencés
dans le texte narratif (5 des 18, cf. build_index_visuels.py) : signalé,
pas masqué.

CORRECTION FUSION DÉLÉGUÉS/CAISSES (Décision 021, intégrée le 2026-09-12) :
`correction_fusion_caisses.appliquer_correction` est appelée sur CHAQUE
tableau narratif (pas seulement le tableau Délégués) — ses garde-fous
internes (confirme_type_13_caisses) la rendent silencieuse (retour
inchangé) sur les 17 tableaux qui ne correspondent pas au motif "13
caisses + Total", donc pas besoin de cibler le tableau au préalable. Toute
correction/échec propre est journalisé (log_corrections, affiché dans le
résumé) — jamais silencieux. Ainsi, toute réingestion future via ce
script bénéficie automatiquement de la correction, pas seulement le
tableau Délégués observé jusqu'ici.

Exporte 2 fichiers séparés :
- index_texte_bge.json (190 entrées)
- index_tableaux_texte_bge.json (18 entrées) — À FUSIONNER avec
  index_visuels_cohere.json au moment de l'ingestion réelle dans la
  collection "tableaux" (vecteur nommé "image" déjà présent là-bas,
  vecteur nommé "texte" produit ici).

Prérequis :
- pip install sentence-transformers torch (déjà fait, cf. venv local)
- output_structure_brute/chunks_propres.json et
  output_structure_brute/docling_document_complet.json présents

    python build_index_texte_bge.py
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import pandas as pd
import torch
from docling_core.types.doc.document import DoclingDocument
from sentence_transformers import SentenceTransformer

import chemins_visuels as cv
from build_index_visuels import charger_occurrences_narratives, resoudre_chemin_hierarchique
from correction_fusion_caisses import appliquer_correction

BASE_DIR = Path(__file__).parent
CHUNKS_PROPRES_JSON = BASE_DIR / "output_structure_brute" / "chunks_propres.json"
DOCLING_DOCUMENT_JSON = BASE_DIR / "output_structure_brute" / "docling_document_complet.json"
DOSSIER_SORTIE = BASE_DIR / "output_structure_brute"
INDEX_TEXTE_SORTIE = DOSSIER_SORTIE / "index_texte_bge.json"
INDEX_TABLEAUX_TEXTE_SORTIE = DOSSIER_SORTIE / "index_tableaux_texte_bge.json"

ANNEE_DOCUMENT = 2025  # même convention que build_index_visuels.py
MODELE_BGE = "Shitao/bge-m3"  # miroir safetensors, cf. src/index.py + Décision 004
DIMENSION_ATTENDUE = 1024  # vérifié sur https://huggingface.co/BAAI/bge-m3
TAILLE_LOT = 8  # même valeur que BATCH_SIZE dans src/index.py

N_CHUNKS_ATTENDU = 190
N_TABLEAUX_ATTENDU = 18


def construire_texte_a_encoder(chemin_hierarchique, texte):
    """Règle confirmée par l'utilisateur (pas réinventée) : les 2 derniers
    segments du chemin hiérarchique + le texte du chunk. Retourne
    (texte_a_encoder, segment_unique) — segment_unique=True si
    chemin_hierarchique n'avait qu'un seul segment (cas rare, à signaler
    à l'appelant plutôt qu'à masquer)."""
    segments = chemin_hierarchique.split(" > ")
    segment_unique = len(segments) == 1
    prefixe = " > ".join(segments[-2:])  # [-2:] ne plante jamais, même sur une liste à 1 élément
    return f"{prefixe}\n{texte}", segment_unique


def charger_chunks_indexables():
    with open(CHUNKS_PROPRES_JSON, encoding="utf-8") as f:
        chunks = json.load(f)
    return [c for c in chunks if c.get("categorie") == "indexable"]


def charger_tableaux_markdown():
    """Régénère la représentation markdown des 18 tableaux narratifs
    (page < PAGE_MIN_QRT, même filtre que extraire_visuels.py) depuis le
    DoclingDocument canonique — aucun fichier pré-exporté équivalent pour
    CE document (vérifié avant d'écrire cette fonction).

    Applique aussi correction_fusion_caisses.appliquer_correction (Décision
    021) sur CHAQUE tableau — silencieuse (table inchangée) sur les 17
    tableaux hors périmètre (garde-fou 1a interne), correction ou échec
    propre journalisé sinon. Retourne (entrees, log_corrections)."""
    doc = DoclingDocument.load_from_json(DOCLING_DOCUMENT_JSON)
    tableaux_narratifs = [t for t in doc.tables if t.prov[0].page_no < cv.PAGE_MIN_QRT]
    entrees = []
    log_corrections = []
    for table in tableaux_narratifs:
        df = table.export_to_dataframe()
        table_dict = {
            "index": table.self_ref,
            "page": table.prov[0].page_no,
            "lignes": df.astype(str).values.tolist(),
        }
        table_corrigee, log_entry = appliquer_correction(
            table_dict, table.prov[0].page_no, document="SFCR_2025_Groupe-Groupama",
        )
        if log_entry is not None:
            log_corrections.append(log_entry)

        if log_entry is not None and log_entry["statut"] == "CORRECTION APPLIQUÉE":
            # Reconstruit un DataFrame à partir des lignes CORRIGÉES (mêmes
            # colonnes que l'original) pour régénérer un markdown cohérent —
            # jamais le markdown original réutilisé tel quel dans ce cas.
            df_pour_markdown = pd.DataFrame(table_corrigee["lignes"], columns=df.columns)
        else:
            df_pour_markdown = df

        entrees.append({
            "self_ref": table.self_ref,
            "page": table.prov[0].page_no,  # depuis Docling directement — toujours disponible,
                                             # contrairement à une page dérivée du texte narratif
                                             # (5 des 18 tableaux ne sont référencés dans AUCUN chunk)
            "markdown": df_pour_markdown.to_markdown(index=False),
        })
    return entrees, log_corrections


def verifier_dimension(embeddings, contexte):
    dim = embeddings.shape[1]
    if dim != DIMENSION_ATTENDUE:
        print(f"  >>> ATTENTION — dimension inattendue pour {contexte} : {dim} "
              f"(attendu {DIMENSION_ATTENDUE}) — à vérifier avant toute ingestion Qdrant.")
    else:
        print(f"  Dimension vérifiée pour {contexte} : {dim} (conforme)")
    return dim == DIMENSION_ATTENDUE


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Chargement de {MODELE_BGE} (device: {device})...")
    try:
        model = SentenceTransformer(MODELE_BGE, device=device)
    except Exception as e:
        print(f">>> ARRÊT — échec du chargement du modèle {MODELE_BGE} : {type(e).__name__}: {e}")
        return
    model.max_seq_length = 1024

    # === 1. Texte narratif (190 chunks indexables) ===
    chunks = charger_chunks_indexables()
    print(f"\nChunks indexables chargés : {len(chunks)} (attendu : {N_CHUNKS_ATTENDU})")
    if len(chunks) != N_CHUNKS_ATTENDU:
        print("  >>> ATTENTION : compte différent de l'attendu — vérifie chunks_propres.json "
              "avant de faire confiance au résultat.")

    textes_a_encoder = []
    segments_uniques = []
    for chunk in chunks:
        texte_a_encoder, segment_unique = construire_texte_a_encoder(
            chunk["chemin_hierarchique"], chunk["texte"]
        )
        textes_a_encoder.append(texte_a_encoder)
        if segment_unique:
            segments_uniques.append(chunk["position_header"])

    if segments_uniques:
        print(f"  >>> {len(segments_uniques)} chunk(s) à chemin_hierarchique à UN SEUL segment "
              f"(cas rare, signalé) — position_header : {segments_uniques}")

    print(f"\nEncodage des {len(chunks)} chunks (BGE-M3, batch_size={TAILLE_LOT})...")
    try:
        embeddings = model.encode(
            textes_a_encoder,
            batch_size=TAILLE_LOT,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
    except Exception as e:
        print(f">>> ARRÊT — échec de l'encodage des chunks texte : {type(e).__name__}: {e}")
        return

    dimension_ok_texte = verifier_dimension(embeddings, "index_texte_bge (190 chunks)")

    entrees_texte = [
        {
            # position_origine ABSENT sur 118/190 chunks indexables (chunks de section
            # jamais sous-découpés en bullet/paragraphe, cf. attach_metadata.py) — .get()
            # plutôt qu'un accès direct, qui aurait fait planter le script sur ce cas
            # pourtant majoritaire, pas marginal. position_header, lui, est TOUJOURS présent.
            "position_origine": chunk.get("position_origine"),
            "position_header": chunk["position_header"],
            "chemin_hierarchique": chunk["chemin_hierarchique"],
            "pages": chunk["pages"],
            "year": chunk["year"],
            "embedding": embedding.tolist(),
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    with open(INDEX_TEXTE_SORTIE, "w", encoding="utf-8") as f:
        json.dump(entrees_texte, f, ensure_ascii=False, indent=2)
    print(f"[export] {INDEX_TEXTE_SORTIE}")

    # === 2. Tableaux (18 entrées, représentation markdown) ===
    print(f"\nRégénération de la représentation markdown des tableaux narratifs...")
    tableaux, log_corrections = charger_tableaux_markdown()
    print(f"Tableaux narratifs trouvés : {len(tableaux)} (attendu : {N_TABLEAUX_ATTENDU})")
    for log_entry in log_corrections:
        print(f"  >>> [correction_fusion_caisses] {log_entry['statut']} — "
              f"table_index={log_entry['table_index']}, page={log_entry['page']} : "
              f"{log_entry.get('raison') or log_entry.get('confiance')}")
    if len(tableaux) != N_TABLEAUX_ATTENDU:
        print("  >>> ATTENTION : compte différent de l'attendu — vérifie "
              "docling_document_complet.json avant de faire confiance au résultat.")

    echecs_tableaux = [t["self_ref"] for t in tableaux if not t["markdown"].strip()]
    if echecs_tableaux:
        print(f"  >>> {len(echecs_tableaux)} tableau(x) avec une représentation markdown VIDE "
              f"(échec probable de export_to_dataframe()) : {echecs_tableaux}")

    # chemin_hierarchique : réutilise TELLE QUELLE la logique déjà décidée
    # dans build_index_visuels.py, pas réinventée ici.
    occurrences = charger_occurrences_narratives()

    print(f"\nEncodage des {len(tableaux)} tableaux (BGE-M3, batch_size={TAILLE_LOT})...")
    try:
        embeddings_tableaux = model.encode(
            [t["markdown"] for t in tableaux],
            batch_size=TAILLE_LOT,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=True,
        )
    except Exception as e:
        print(f">>> ARRÊT — échec de l'encodage des tableaux : {type(e).__name__}: {e}")
        return

    dimension_ok_tableaux = verifier_dimension(embeddings_tableaux, "index_tableaux_texte_bge (18 tableaux)")

    absents = []
    entrees_tableaux = []
    for t, embedding in zip(tableaux, embeddings_tableaux):
        chemin_hier, _occ, statut = resoudre_chemin_hierarchique(t["self_ref"], occurrences)
        if statut == "absent":
            absents.append(t["self_ref"])
        entrees_tableaux.append({
            "self_ref": t["self_ref"],
            "chemin_hierarchique": chemin_hier,
            "pages": [t["page"]],
            "year": ANNEE_DOCUMENT,
            "embedding": embedding.tolist(),
        })

    if absents:
        print(f"  >>> {len(absents)} tableau(x) jamais référencé(s) dans le texte narratif "
              f"(chemin_hierarchique=null, même constat que build_index_visuels.py) : {absents}")

    with open(INDEX_TABLEAUX_TEXTE_SORTIE, "w", encoding="utf-8") as f:
        json.dump(entrees_tableaux, f, ensure_ascii=False, indent=2)
    print(f"[export] {INDEX_TABLEAUX_TEXTE_SORTIE}")

    # === Résumé final ===
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Chunks texte encodés    : {len(entrees_texte)}/{N_CHUNKS_ATTENDU} "
          f"(dimension {'OK' if dimension_ok_texte else 'ANORMALE'})")
    print(f"  Tableaux encodés        : {len(entrees_tableaux)}/{N_TABLEAUX_ATTENDU} "
          f"(dimension {'OK' if dimension_ok_tableaux else 'ANORMALE'})")
    print(f"  Chemins à 1 segment     : {len(segments_uniques)}")
    print(f"  Tableaux markdown vide  : {len(echecs_tableaux)}")
    print(f"  Tableaux sans référence narrative : {len(absents)}")
    print(f"  Corrections fusion caisses (Décision 021) : {len(log_corrections)} signalement(s) "
          f"({sum(1 for l in log_corrections if l['statut'] == 'CORRECTION APPLIQUÉE')} appliquée(s))")


if __name__ == "__main__":
    main()
