"""Comparaison dense vs BM25 sur le docstore FAISS existant. Pas de LLM."""
import io, re, contextlib
from pathlib import Path
from rag import vs
from langchain_community.retrievers import BM25Retriever

QUESTIONS = [
    "À quel niveau de confiance et sur quel horizon temporel le SCR est-il calibré ?",
    "Entre quelles bornes le MCR doit-il se situer par rapport au SCR ?",
    "De quoi se composent les provisions techniques sous Solvabilité II ?",
    "Qu'est-ce que la marge de service contractuelle sous IFRS 17 ?",
]

TARGETS = ["99,5", "25 %", "45 %", "meilleure estimation", "marge de risque"]


def normalize(text):
    # \xa0 = espace insécable, \xad = césure JO ("uti-\xad\nlisée") : cf. CLAUDE.md
    text = text.replace("\xad", "").replace("\xa0", " ")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def contains_targets(text):
    low = normalize(text)
    return [t for t in TARGETS if t.lower() in low]


def show(label, results):
    found = set()
    for i, d in enumerate(results, 1):
        norme = d.metadata.get("norme", "?")
        page = d.metadata.get("page", "?")
        excerpt = d.page_content[:90].replace("\n", " ")
        hits = contains_targets(d.page_content)
        found.update(hits)
        hit_str = f"   <-- CONTIENT: {hits}" if hits else ""
        print(f"  [{label}{i}] {norme:<16} p.{page!s:<5} {excerpt!r}{hit_str}")
    return found


def main():
    docs = list(vs.docstore._dict.values())
    print(f"{len(docs)} chunks chargés depuis le docstore FAISS\n")

    bm25 = BM25Retriever.from_documents(docs)
    bm25.k = 5

    for q in QUESTIONS:
        print("=" * 100)
        print(f"Q: {q}")
        print("=" * 100)

        dense = vs.similarity_search(q, k=5)
        print("\n-- DENSE (e5-large) --")
        found_dense = show("D", dense)

        bm = bm25.invoke(q)
        print("\n-- BM25 --")
        found_bm25 = show("B", bm)

        print(f"\nTermes cibles trouvés — DENSE: {sorted(found_dense) or 'aucun'} | BM25: {sorted(found_bm25) or 'aucun'}")
        print()


if __name__ == "__main__":
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        main()
    out = Path(__file__).parent.parent / "retrieval_comparaison.md"
    out.write_text(buf.getvalue(), encoding="utf-8")
    print("done -> retrieval_comparaison.md")
