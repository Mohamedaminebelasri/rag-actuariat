import re
from pathlib import Path
from collections import Counter
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS

ROOT = Path(__file__).parent.parent
CORPUS = [("ifrs17.pdf", "IFRS 17"), ("solva2.pdf", "Solvabilité II")]


def clean_page(text):
    """Recolle les césures du JO européen (soft-hyphen \xad avant retour à la
    ligne, ex: 'assu\xad\nrance' -> 'assurance') et normalise les espaces
    insécables \xa0. Ne touche pas aux \n/\n\n : le splitter s'appuie dessus."""
    text = re.sub(r"(\w)\xad\s*\n?\s*(\w)", r"\1\2", text)
    text = text.replace("\xad", "")
    text = text.replace("\xa0", " ")
    return text


docs = []
for fichier, norme in CORPUS:
    pages = PyPDFLoader(str(ROOT / "data" / fichier)).load()
    for p in pages:
        p.metadata["norme"] = norme
        p.page_content = clean_page(p.page_content)
    docs.extend(pages)
    print(f"✅ {norme:<16} {len(pages)} pages")

chunks = RecursiveCharacterTextSplitter(
    chunk_size=512, chunk_overlap=150,
    separators=["\n\n", "\n", ".", " "]
).split_documents(docs)

print(f"\n✅ {len(chunks)} chunks")
for n, c in Counter(c.metadata["norme"] for c in chunks).items():
    print(f"   {n:<16} {c}")

print("\n⏳ Chargement e5-large (~15s)...")
emb = HuggingFaceEmbeddings(
    model_name="intfloat/multilingual-e5-large",
    model_kwargs={"device": "cuda"},
    encode_kwargs={"normalize_embeddings": True},
)

print("⏳ Vectorisation...")
vs = FAISS.from_documents(chunks, emb)
vs.save_local(str(ROOT / "faiss_multinorme"))
print(f"✅ Index : {vs.index.ntotal} vecteurs · {vs.index.d} dim")