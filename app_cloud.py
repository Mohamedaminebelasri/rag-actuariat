"""Démo cloud (Streamlit Community Cloud) — corpus publics IFRS 17 / Solvabilité II.

Contrainte RAM (~1 Go sur le cloud) : e5-large (2,24 Go mesurés en local) ne
peut PAS être chargé dans ce process. Les embeddings de la question passent
donc par l'API HuggingFace Inference — aucun modèle local, aucun torch.

mode dense uniquement (pas de BM25/reranker : RAM et simplicité).
"""
import numpy as np
import requests
import streamlit as st
from pathlib import Path
from langchain_core.embeddings import Embeddings
from langchain_community.vectorstores import FAISS
from openai import OpenAI, RateLimitError

ROOT = Path(__file__).parent
FAISS_DIR = ROOT / "faiss_multinorme"

HF_MODEL = "intfloat/multilingual-e5-large"
# ATTENTION : l'ancien endpoint "api-inference.huggingface.co/models/..."
# ne résout plus en DNS (0 enregistrement, vérifié le 2026-07-17) — HF a migré
# vers le "router". Ne pas revenir à l'ancienne URL sans revérifier en DNS.
HF_API_URL = f"https://router.huggingface.co/hf-inference/models/{HF_MODEL}"
GROQ_MODEL = "llama-3.3-70b-versatile"

st.set_page_config(page_title="Démo en ligne — corpus publics uniquement", page_icon="📄")


class HFInferenceEmbeddings(Embeddings):
    """Embeddings de la question via l'API HuggingFace Inference (pas de
    modèle local).

    PAS de préfixe "query: " — vérifié le 2026-07-17 : l'index local
    (faiss_multinorme/) a été construit avec langchain_huggingface.
    HuggingFaceEmbeddings, qui n'ajoute AUCUN préfixe e5 automatiquement
    (source : embed_documents/embed_query appellent SentenceTransformer.encode()
    tel quel, sans prompt_name). intfloat/multilingual-e5-large n'a par
    ailleurs pas de config_sentence_transformers.json définissant un
    default_prompt_name — confirmé absent du repo HF (cache local :
    .no_exist/.../config_sentence_transformers.json). Donc les chunks de
    l'index ont été embeddés SANS "passage: ", et poser_question() interroge
    SANS "query: ". Ajouter un préfixe ici casserait cette cohérence et
    dégraderait le retrieval en silence — exactement le risque signalé.
    Si l'index est un jour reconstruit avec préfixes, ce commentaire (et ce
    client) devront changer en même temps.
    """

    def __init__(self, token):
        self.token = token

    def _call_api(self, inputs):
        resp = requests.post(
            HF_API_URL,
            headers={"Authorization": f"Bearer {self.token}"},
            json={"inputs": inputs, "options": {"wait_for_model": True}},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    def embed_query(self, text):
        data = self._call_api(text)
        vec = np.array(data, dtype="float32").reshape(-1)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_documents(self, texts):
        raise NotImplementedError(
            "app_cloud.py ne réindexe jamais - lecture seule de faiss_multinorme/ "
            "(construit en local par src/index.py)."
        )


@st.cache_resource(show_spinner="Chargement de l'index...")
def load_index():
    # embeddings factice pour satisfaire la signature de FAISS.load_local ;
    # jamais utilisé pour indexer ici (lecture seule), l'embedding réel de la
    # question passe par HFInferenceEmbeddings.embed_query() appelé explicitement.
    dummy = HFInferenceEmbeddings(token="")
    return FAISS.load_local(str(FAISS_DIR), dummy, allow_dangerous_deserialization=True)


def get_secret(key):
    try:
        return st.secrets[key]
    except (KeyError, FileNotFoundError):
        return None


def poser_question_cloud(question, vs, k=5):
    hf_token = get_secret("HF_TOKEN")
    groq_key = get_secret("GROQ_API_KEY")
    if not hf_token or not groq_key:
        return None, None, "Secrets manquants (HF_TOKEN / GROQ_API_KEY) — configuration incomplète."

    embedder = HFInferenceEmbeddings(token=hf_token)
    try:
        query_vec = embedder.embed_query(question)
    except requests.HTTPError as e:
        status = e.response.status_code if e.response is not None else None
        if status == 429:
            return None, None, "Quota du prototype épuisé — réessayez dans quelques heures."
        if status in (401, 403):
            return None, None, f"Embeddings HF — HTTP {status} : token HF invalide ou sans les droits requis."
        body = ""
        try:
            body = e.response.text[:300]
        except Exception:
            pass
        return None, None, f"Erreur d'embedding (HTTP {status}) : {body or 'réponse vide'}"
    except requests.ConnectionError as e:
        return None, None, f"Embeddings HF — connexion impossible ({e.__class__.__name__}) : {e}"
    except requests.RequestException as e:
        return None, None, f"Embeddings HF — erreur réseau ({e.__class__.__name__}) : {e}"

    docs = vs.similarity_search_by_vector(query_vec, k=k)
    ctx = "".join(
        f"\n[{d.metadata['norme']} — page {d.metadata.get('page', '?')}]\n{d.page_content}\n"
        for d in docs
    )

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

    client = OpenAI(api_key=groq_key, base_url="https://api.groq.com/openai/v1")
    try:
        r = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        ).choices[0].message.content
    except RateLimitError:
        return None, None, "Quota du prototype épuisé — réessayez dans quelques heures."

    return r, docs, None


# ─────────────────────────── UI ───────────────────────────

st.title("Démo en ligne — corpus publics uniquement")
st.caption("IFRS 17 & Solvabilité II · retrieval dense · réponses citées, refus si absent des documents")

vs = load_index()

if "question" not in st.session_state:
    st.session_state.question = ""

EXEMPLES = [
    ("CSM", "Qu'est-ce que la CSM selon IFRS 17 ?"),
    ("Comment IFRS 17 définit-il le SCR ?", "Comment IFRS 17 définit-il le SCR ?"),
    ("Pourquoi le SCR est calibré à 99,9 % ?", "Pourquoi le SCR est calibré à 99,9 % ?"),
]

cols = st.columns(len(EXEMPLES))
for col, (label, q) in zip(cols, EXEMPLES):
    if col.button(label, use_container_width=True):
        st.session_state.question = q

question = st.text_input("Votre question :", key="question")

if st.button("Interroger", type="primary") and question.strip():
    with st.spinner("Recherche puis génération..."):
        reponse, docs, erreur = poser_question_cloud(question, vs)

    if erreur:
        st.error(erreur)
    else:
        st.markdown(reponse)
        with st.expander("Sources"):
            for i, d in enumerate(docs, 1):
                st.markdown(f"**[{i}]** {d.metadata.get('norme', '?')} — page {d.metadata.get('page', '?')}")
                st.caption(d.page_content[:300] + ("…" if len(d.page_content) > 300 else ""))
