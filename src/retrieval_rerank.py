"""Étape 3 : rerank du top20 RRF avec cross-encoder/mmarco-mMiniLMv2-L12-H384-v1.
Q2 volontairement exclu (hors de portée du reranking : chunk cible au rang ~1287,
problème de vocabulaire, pas de tri — cf. discussion précédente).
Pas de LLM.
"""
import io, re, contextlib
from pathlib import Path
import torch
from rag import vs
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from sentence_transformers import CrossEncoder

QUESTIONS = [
    "À quel niveau de confiance et sur quel horizon temporel le SCR est-il calibré ?",
    "De quoi se composent les provisions techniques sous Solvabilité II ?",
    "Qu'est-ce que la marge de service contractuelle sous IFRS 17 ?",
]
ANCHORS = [
    ["99,5"],
    ["meilleure estimation", "marge de risque"],
    ["contractual service margin", "marge pour service contractuel"],
]
RRF_RANK_AVANT = [2, 5, 1]  # rangs déjà mesurés à l'étape 2 (RRF top5), pour rappel

K = 20
RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


def normalize(text):
    text = text.replace("\xad\n", "").replace("\xad", "")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def bm25_tokenizer(text):
    return normalize(text).split()


def rank_of(docs, anchors):
    for i, d in enumerate(docs, 1):
        low = normalize(d.page_content)
        if any(a.lower() in low for a in anchors):
            return i
    return None


def cell(rank):
    if rank is None:
        return "absent"
    return f"rang {rank}" if rank <= 5 else f"absent (top5) — rang réel {rank}"


def describe(label, docs, n=5):
    lines = []
    for i, d in enumerate(docs[:n], 1):
        norme = d.metadata.get("norme", "?")
        page = d.metadata.get("page", "?")
        excerpt = d.page_content[:90].replace("\n", " ")
        lines.append(f"  [{label}{i}] {norme:<16} p.{page!s:<5} {excerpt!r}")
    return "\n".join(lines)


def main():
    vram_before_ce = torch.cuda.memory_allocated()
    print(f"VRAM allouée AVANT chargement du reranker (e5-large seul déjà chargé) : {vram_before_ce/1e6:.1f} Mo\n")

    docs = list(vs.docstore._dict.values())
    dense_retriever = vs.as_retriever(search_kwargs={"k": K})
    bm25 = BM25Retriever.from_documents(docs, preprocess_func=bm25_tokenizer)
    bm25.k = K
    ensemble = EnsembleRetriever(retrievers=[dense_retriever, bm25], weights=[0.7, 0.3])

    reranker = CrossEncoder(RERANK_MODEL, device="cuda")

    vram_after_ce = torch.cuda.memory_allocated()
    vram_reserved = torch.cuda.memory_reserved()
    print(f"VRAM allouée APRÈS chargement du reranker (e5-large + cross-encoder) : {vram_after_ce/1e6:.1f} Mo")
    print(f"VRAM réservée par torch (e5-large + cross-encoder) : {vram_reserved/1e6:.1f} Mo")
    print(f"Delta reranker seul : {(vram_after_ce - vram_before_ce)/1e6:.1f} Mo\n")

    rows = []
    for q, anchors, rrf_rank_avant in zip(QUESTIONS, ANCHORS, RRF_RANK_AVANT):
        print("=" * 100)
        print(f"Q: {q}")
        print(f"Ancre(s) : {anchors}  |  rang RRF top5 mesuré à l'étape 2 : {rrf_rank_avant}")
        print("=" * 100)

        rrf_docs = ensemble.invoke(q)  # top ~20-40 fusionné (candidats pour le rerank)

        pairs = [(q, d.page_content) for d in rrf_docs]
        scores = reranker.predict(pairs)
        reranked = [d for d, _ in sorted(zip(rrf_docs, scores), key=lambda x: x[1], reverse=True)]

        print("\n-- RRF top5 (avant rerank, rappel) --")
        print(describe("R", rrf_docs))
        print("\n-- RERANK top5 (cross-encoder appliqué au pool RRF) --")
        print(describe("X", reranked))

        r_rerank = rank_of(reranked, anchors)
        print(f"\nRang réel après rerank (sur pool RRF de {len(rrf_docs)} candidats) : {r_rerank}")
        print()

        rows.append((q, rrf_rank_avant, cell(r_rerank)))

    print("\n" + "#" * 100)
    print("TABLEAU — colonne +Rerank complétée (Q1, Q3, Q4 uniquement — Q2 non tenté)")
    print("#" * 100)
    print("| Question | RRF top5 (rappel) | +Rerank top5 |")
    print("|---|---|---|")
    for i, (q, before, after) in enumerate(rows, 1):
        print(f"| {q[:55]}... | rang {before} | {after} |")


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main()
    out = Path(__file__).parent.parent / "retrieval_rerank.md"
    out.write_text(buf.getvalue(), encoding="utf-8")
    print("done -> retrieval_rerank.md")
