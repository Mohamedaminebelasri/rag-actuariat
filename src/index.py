import json
import os
import time

import faiss
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

ARTICLES_PATH = "data/articles.jsonl"
INDEX_DIR = "faiss_solva2"
INDEX_PATH = os.path.join(INDEX_DIR, "index.faiss")
MAPPING_PATH = os.path.join(INDEX_DIR, "mapping.json")

MODEL_NAME = "Shitao/bge-m3"  # miroir safetensors du même modèle que BAAI/bge-m3
BATCH_SIZE = 8


def load_articles():
    articles = []
    with open(ARTICLES_PATH, encoding="utf-8") as f:
        for line in f:
            articles.append(json.loads(line))
    return articles


def build_index():
    articles = load_articles()
    print(f"Articles chargés : {len(articles)} (cible 312)")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Device utilisé : {device}")

    model = SentenceTransformer(MODEL_NAME, device=device)
    model.max_seq_length = 1024

    texts = [f"{a['titre']}\n{a['texte']}" for a in articles]

    t0 = time.perf_counter()
    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        show_progress_bar=False,
        convert_to_numpy=True,
    )
    encode_time = time.perf_counter() - t0

    embeddings = embeddings.astype(np.float32)
    dim = embeddings.shape[1]

    index = faiss.IndexFlatIP(dim)
    index.add(embeddings)

    os.makedirs(INDEX_DIR, exist_ok=True)
    faiss.write_index(index, INDEX_PATH)

    mapping = [
        {"numero_article": a["numero_article"], "titre": a["titre"], "texte": a["texte"]}
        for a in articles
    ]
    with open(MAPPING_PATH, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False)

    index_size = os.path.getsize(INDEX_PATH)
    mapping_size = os.path.getsize(MAPPING_PATH)

    print(f"\nNombre de vecteurs : {index.ntotal}")
    print(f"Dimension : {dim}")
    print(f"Temps d'encodage des {len(articles)} articles : {encode_time:.1f} s")
    print(f"Fichier {INDEX_PATH} : {index_size / 1024:.0f} Ko")
    print(f"Fichier {MAPPING_PATH} : {mapping_size / 1024:.0f} Ko")

    del model
    if device == "cuda":
        torch.cuda.empty_cache()


def verify():
    print("\n--- VÉRIFICATION : rechargement depuis le disque ---")
    index = faiss.read_index(INDEX_PATH)
    with open(MAPPING_PATH, encoding="utf-8") as f:
        mapping = json.load(f)

    print(f"Index rechargé : {index.ntotal} vecteurs, dimension {index.d}")
    print(f"Mapping rechargé : {len(mapping)} entrées")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer(MODEL_NAME, device=device)
    model.max_seq_length = 1024

    question = "Comment calcule-t-on le minimum de capital requis ?"
    q_emb = model.encode([question], normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
    scores, idxs = index.search(q_emb, 5)

    print(f"\nQuestion test : \"{question}\"")
    for rank, (idx, score) in enumerate(zip(idxs[0], scores[0]), start=1):
        entry = mapping[idx]
        print(f"  {rank}. Article {entry['numero_article']} — \"{entry['titre']}\" (score={score:.4f})")

    top1 = mapping[idxs[0][0]]
    if top1["numero_article"] == 129:
        print("\n=> VÉRIFICATION OK : Article 129 en rang 1.")
    else:
        print(f"\n=> VÉRIFICATION ÉCHOUÉE : rang 1 = Article {top1['numero_article']}, pas 129.")


if __name__ == "__main__":
    build_index()
    verify()
