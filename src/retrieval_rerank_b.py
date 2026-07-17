"""Test du candidat B (BAAI/bge-reranker-v2-m3, fp16) — Q1, Q3, Q4 uniquement.
Même protocole que retrieval_rerank.py (candidat A). Décharge A avant de charger B.
Pas de fallback CPU silencieux : OOM => on arrête et on le dit.
Pas de LLM.
"""
import io, re, gc, contextlib
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
RRF_RANK_AVANT = [2, 5, 1]
RERANK_A_RANK = [1, 18, 1]  # déjà mesuré avec le candidat A

K = 20
MODEL_A = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
MODEL_B = "BAAI/bge-reranker-v2-m3"


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


def vram():
    return torch.cuda.memory_allocated() / 1e6, torch.cuda.memory_reserved() / 1e6


def main():
    a, r = vram()
    print(f"VRAM AVANT tout reranker (e5-large seul) : {a:.1f} Mo alloués / {r:.1f} Mo réservés\n")

    docs = list(vs.docstore._dict.values())
    dense_retriever = vs.as_retriever(search_kwargs={"k": K})
    bm25 = BM25Retriever.from_documents(docs, preprocess_func=bm25_tokenizer)
    bm25.k = K
    ensemble = EnsembleRetriever(retrievers=[dense_retriever, bm25], weights=[0.7, 0.3])

    # --- charge A, mesure, décharge ---
    print(f"Chargement candidat A ({MODEL_A})...")
    reranker_a = CrossEncoder(MODEL_A, device="cuda")
    a, r = vram()
    print(f"VRAM avec A chargé : {a:.1f} Mo alloués / {r:.1f} Mo réservés")

    del reranker_a
    gc.collect()
    torch.cuda.empty_cache()
    a, r = vram()
    print(f"VRAM après déchargement de A (del + empty_cache) : {a:.1f} Mo alloués / {r:.1f} Mo réservés\n")

    # --- charge B en fp16 ---
    print(f"Chargement candidat B ({MODEL_B}, fp16)...")
    try:
        reranker_b = CrossEncoder(MODEL_B, device="cuda", model_kwargs={"torch_dtype": torch.float16})
    except torch.cuda.OutOfMemoryError as e:
        print(f"\n!!! OOM lors du chargement de B en fp16 : {e}")
        print("!!! ARRÊT — pas de fallback CPU silencieux.")
        return
    except RuntimeError as e:
        if "out of memory" in str(e).lower():
            print(f"\n!!! OOM (RuntimeError) lors du chargement de B en fp16 : {e}")
            print("!!! ARRÊT — pas de fallback CPU silencieux.")
            return
        raise

    actual_device = next(reranker_b.model.parameters()).device
    actual_dtype = next(reranker_b.model.parameters()).dtype
    print(f"B chargé sur device={actual_device}, dtype={actual_dtype}")
    if str(actual_device) == "cpu":
        print("!!! ATTENTION : le modèle est sur CPU, pas GPU. Signalé comme demandé, pas de poursuite silencieuse.")
        return

    a, r = vram()
    print(f"VRAM avec B chargé (fp16) : {a:.1f} Mo alloués / {r:.1f} Mo réservés\n")

    rows = []
    for q, anchors, rrf_avant, a_rank in zip(QUESTIONS, ANCHORS, RRF_RANK_AVANT, RERANK_A_RANK):
        print("=" * 100)
        print(f"Q: {q}")
        print(f"Ancre(s) : {anchors}  |  RRF top5 : rang {rrf_avant}  |  rerank A : rang {a_rank}")
        print("=" * 100)

        rrf_docs = ensemble.invoke(q)

        try:
            scores = reranker_b.predict([(q, d.page_content) for d in rrf_docs])
        except torch.cuda.OutOfMemoryError as e:
            print(f"!!! OOM pendant le predict() de B sur cette question : {e}")
            print("!!! ARRÊT.")
            return

        reranked = [d for d, _ in sorted(zip(rrf_docs, scores), key=lambda x: x[1], reverse=True)]

        print("\n-- RERANK-B top5 --")
        print(describe("Y", reranked))

        r_b = rank_of(reranked, anchors)
        print(f"\nRang réel après rerank B (sur pool RRF de {len(rrf_docs)} candidats) : {r_b}")
        print()

        rows.append((q, rrf_avant, a_rank, cell(r_b)))

    print("\n" + "#" * 100)
    print("TABLEAU COMPARATIF A vs B (Q1, Q3, Q4)")
    print("#" * 100)
    print("| Question | RRF top5 | +Rerank A | +Rerank B |")
    print("|---|---|---|---|")
    for q, rrf_avant, a_rank, b_cell in rows:
        print(f"| {q[:50]}... | rang {rrf_avant} | {cell(a_rank)} | {b_cell} |")


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            main()
        except Exception as e:
            print(f"\n!!! EXCEPTION NON GÉRÉE : {type(e).__name__}: {e}")
    out = Path(__file__).parent.parent / "retrieval_rerank_b.md"
    out.write_text(buf.getvalue(), encoding="utf-8")
    print("done -> retrieval_rerank_b.md")
