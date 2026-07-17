"""Étape 2 : EnsembleRetriever (RRF) 70% dense / 30% BM25, top 20 chacun.
Normalisation \xa0/\xad appliquée AVANT indexation BM25 (pas juste en détection).
Pas de LLM.
"""
import io, re, contextlib
from pathlib import Path
from rag import vs
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever

QUESTIONS = [
    "À quel niveau de confiance et sur quel horizon temporel le SCR est-il calibré ?",
    "Entre quelles bornes le MCR doit-il se situer par rapport au SCR ?",
    "De quoi se composent les provisions techniques sous Solvabilité II ?",
    "Qu'est-ce que la marge de service contractuelle sous IFRS 17 ?",
]

# terme(s)-ancre par question : rang cherché = 1ère position d'un chunk qui
# contient LITTÉRALEMENT (après normalisation) l'un de ces termes
ANCHORS = [
    ["99,5"],
    ["25 %", "45 %"],
    ["meilleure estimation", "marge de risque"],
    ["contractual service margin", "marge pour service contractuel"],
]

K = 20


def normalize(text):
    # \xa0 = espace insécable, \xad = césure JO ("uti-\xad\nlisée") : cf. CLAUDE.md
    text = text.replace("\xad", "").replace("\xa0", " ")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def bm25_tokenizer(text):
    return normalize(text).split()


def rank_of(docs, anchors):
    """1ère position (1-indexée) d'un doc contenant un des termes-ancre, sinon None."""
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
    docs = list(vs.docstore._dict.values())
    print(f"{len(docs)} chunks chargés depuis le docstore FAISS\n")

    dense_retriever = vs.as_retriever(search_kwargs={"k": K})
    bm25 = BM25Retriever.from_documents(docs, preprocess_func=bm25_tokenizer)
    bm25.k = K

    ensemble = EnsembleRetriever(retrievers=[dense_retriever, bm25], weights=[0.7, 0.3])

    rows = []
    for q, anchors in zip(QUESTIONS, ANCHORS):
        print("=" * 100)
        print(f"Q: {q}")
        print(f"Ancre(s) recherchée(s) : {anchors}")
        print("=" * 100)

        dense_docs = vs.similarity_search(q, k=K)
        bm25_docs = bm25.invoke(q)
        rrf_docs = ensemble.invoke(q)

        print("\n-- DENSE top5 (sur top20) --")
        print(describe("D", dense_docs))
        print("\n-- BM25 top5 (sur top20, tokenizer normalisé) --")
        print(describe("B", bm25_docs))
        print("\n-- RRF top5 (fusion 70% dense / 30% BM25) --")
        print(describe("R", rrf_docs))

        r_dense = rank_of(dense_docs, anchors)
        r_bm25 = rank_of(bm25_docs, anchors)
        r_rrf = rank_of(rrf_docs, anchors)

        print(f"\nRang réel (sur top{K}) — DENSE: {r_dense} | BM25: {r_bm25} | RRF: {r_rrf}")
        print()

        rows.append((q, cell(r_dense), cell(r_bm25), cell(r_rrf)))

    print("\n" + "#" * 100)
    print("TABLEAU RÉCAPITULATIF (position dans le top 5 de chaque méthode)")
    print("#" * 100)
    print("| Question | Dense top5 | BM25 top5 | RRF top5 | +Rerank top5 |")
    print("|---|---|---|---|---|")
    for i, (q, d, b, r) in enumerate(rows, 1):
        print(f"| Q{i}: {q[:50]}... | {d} | {b} | {r} | *(en attente — étape 3)* |")


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main()
    out = Path(__file__).parent.parent / "retrieval_rrf.md"
    out.write_text(buf.getvalue(), encoding="utf-8")
    print("done -> retrieval_rrf.md")
