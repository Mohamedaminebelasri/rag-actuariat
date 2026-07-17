import re, os
from pathlib import Path
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from openai import OpenAI

ROOT = Path(__file__).parent.parent
load_dotenv(ROOT / ".env")

emb = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-large",
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True},
)
vs = FAISS.load_local(str(ROOT / "faiss_multinorme"), emb,
                      allow_dangerous_deserialization=True)
client = OpenAI(api_key=os.getenv("GROQ_API_KEY"),
                base_url="https://api.groq.com/openai/v1")

RERANK_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
_hybrid = {}  # ensemble retriever + reranker, construits paresseusement (mode="dense" ne les charge jamais)


def _normalize(text):
    # \xa0 = espace insécable, \xad = césure JO ("uti-\xad\nlisée") : cf. CLAUDE.md
    text = text.replace("\xad\n", "").replace("\xad", "")
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.lower()


def _get_ensemble():
    if "ensemble" not in _hybrid:
        from langchain_community.retrievers import BM25Retriever
        from langchain_classic.retrievers import EnsembleRetriever
        docs = list(vs.docstore._dict.values())
        bm25 = BM25Retriever.from_documents(docs, preprocess_func=lambda t: _normalize(t).split())
        bm25.k = 20
        dense_retriever = vs.as_retriever(search_kwargs={"k": 20})
        _hybrid["ensemble"] = EnsembleRetriever(retrievers=[dense_retriever, bm25], weights=[0.7, 0.3])
    return _hybrid["ensemble"]


def _get_reranker():
    if "reranker" not in _hybrid:
        from sentence_transformers import CrossEncoder
        _hybrid["reranker"] = CrossEncoder(RERANK_MODEL, device="cuda")
    return _hybrid["reranker"]


def _retrieve_hybrid_rerank(question, k, norme=None):
    candidates = _get_ensemble().invoke(question)
    if norme:
        candidates = [d for d in candidates if d.metadata.get("norme") == norme]
    reranker = _get_reranker()
    scores = reranker.predict([(question, d.page_content) for d in candidates])
    ranked = [d for d, _ in sorted(zip(candidates, scores), key=lambda x: x[1], reverse=True)]
    return ranked[:k]


def poser_question(question, k=5, norme=None, mode="dense", verbose=True):
    if mode == "dense":
        f = {"norme": norme} if norme else None
        docs = vs.similarity_search(question, k=k, filter=f)
    elif mode == "hybrid_rerank":
        docs = _retrieve_hybrid_rerank(question, k=k, norme=norme)
    else:
        raise ValueError(f"mode inconnu: {mode!r} (attendu 'dense' ou 'hybrid_rerank')")

    ctx = "".join(f"\n[{d.metadata['norme']} — page {d.metadata.get('page','?')}]\n{d.page_content}\n" for d in docs)

    prompt = f"""Tu es un expert en réglementation actuarielle (IFRS 17 et Solvabilité II).

RÈGLES :
1. Réponds UNIQUEMENT depuis les extraits.
2. Cite TOUJOURS la norme et la page exactes de l'extrait utilisé, au format [IFRS 17 — page 42] (ceci est un exemple de FORMAT, pas une page à recopier).
3. Si la question attribue un concept à la mauvaise norme, corrige-le.
4. Si absent : "Je ne trouve pas cette information dans les documents fournis."
5. N'invente jamais.

EXTRAITS :{ctx}

QUESTION : {question}
RÉPONSE :"""

    r = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role":"user","content":prompt}],
        temperature=0).choices[0].message.content

    if verbose:
        cite = bool(re.search(r'\[[^\]]+—\s*page\s*\d+\]', r))
        print("═"*60); print(f"❓ {question}"); print("═"*60)
        print(f"\n💬 {r}\n")
        if cite or not r.strip().lower().startswith("je ne trouve pas"):
            for i,d in enumerate(docs,1):
                print(f"   [{i}] {d.metadata['norme']:<16} p.{d.metadata.get('page','?')}")
    return r

if __name__ == "__main__":
    poser_question("Comment IFRS 17 définit-il le SCR ?")