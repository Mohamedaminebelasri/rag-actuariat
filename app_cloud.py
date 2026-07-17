"""Démo cloud (Streamlit Community Cloud) — corpus publics IFRS 17 / Solvabilité II.

Contrainte RAM (~1 Go sur le cloud) : e5-large (2,24 Go mesurés en local) ne
peut PAS être chargé dans ce process. Les embeddings de la question passent
donc par l'API HuggingFace Inference — aucun modèle local, aucun torch.

mode dense uniquement (pas de BM25/reranker : RAM et simplicité).
"""
import time
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

st.set_page_config(page_title="Assistant réglementaire — IFRS 17 & Solvabilité II", page_icon="📄")

st.markdown(
    """
    <style>
    h1, h2, h3, [data-testid="stMarkdownContainer"] h1 {
        font-family: Georgia, "Times New Roman", serif;
    }
    .bandeau-demo {
        font-size: 0.85rem;
        color: #6B7280;
        border-left: 3px solid #1C3C6E;
        padding: 0.35rem 0.75rem;
        margin: 0.25rem 0 1.25rem 0;
        background: #F4F6F9;
    }
    .pied-reponse {
        font-size: 0.8rem;
        color: #6B7280;
        margin-top: 0.75rem;
        font-style: italic;
    }
    footer[data-testid="stFooter"] { visibility: hidden; }
    .footer-app {
        font-size: 0.75rem;
        color: #9CA3AF;
        margin-top: 3rem;
        border-top: 1px solid #E5E7EB;
        padding-top: 0.75rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


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


def reference_label(norme, page):
    if norme == "Solvabilité II":
        return f"Directive Solvabilité II — page {page}"
    if norme == "IFRS 17":
        return f"Norme IFRS 17 — page {page}"
    return f"{norme} — page {page}"


def poser_question_cloud(question, vs, norme=None, k=5):
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
            return None, None, f"Recherche documentaire indisponible (HTTP {status}) : accès non autorisé."
        body = ""
        try:
            body = e.response.text[:300]
        except Exception:
            pass
        return None, None, f"Recherche documentaire indisponible (HTTP {status}) : {body or 'réponse vide'}"
    except requests.ConnectionError as e:
        return None, None, f"Recherche documentaire indisponible (connexion impossible) : {e}"
    except requests.RequestException as e:
        return None, None, f"Recherche documentaire indisponible (erreur réseau) : {e}"

    # filter accepté nativement par similarity_search_by_vector (vérifié :
    # FAISS.similarity_search_by_vector(embedding, k, filter=None, fetch_k=20, ...))
    filtre = {"norme": norme} if norme else None
    docs = vs.similarity_search_by_vector(query_vec, k=k, filter=filtre, fetch_k=max(20, k * 4))
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

st.title("Assistant réglementaire — IFRS 17 & Solvabilité II")
st.caption("Recherche documentaire avec citation systématique des sources · Démonstration sur corpus publics")
st.markdown(
    '<div class="bandeau-demo">Version de démonstration — ne constitue pas un avis actuariel</div>',
    unsafe_allow_html=True,
)

with st.expander("Protocole de validation", expanded=False):
    st.markdown(
        "Ce système a été évalué sur 25 questions annotées, dont 10 pièges "
        "conçus pour provoquer une invention (concepts inexistants, chiffres "
        "erronés, confusion entre normes).\n\n"
        "Résultat : 100 % des pièges refusés · 0 source inventée (vérification "
        "manuelle sur les PDF) · score global 25/25 en configuration dense.\n\n"
        "Le système répond exclusivement à partir des textes indexés et "
        "signale explicitement toute information absente."
    )

vs = load_index()

if "question" not in st.session_state:
    st.session_state.question = ""

NORMES = {"Les deux normes": None, "IFRS 17": "IFRS 17", "Solvabilité II": "Solvabilité II"}
choix_norme = st.radio("Rechercher dans :", list(NORMES.keys()), horizontal=True)

EXEMPLES = [
    ("Définition de la CSM", "Qu'est-ce que la CSM selon IFRS 17 ?"),
    ("Le SCR relève-t-il d'IFRS 17 ?", "Comment IFRS 17 définit-il le SCR ?"),
    ("Calibrage du SCR à 99,9 % ?", "Pourquoi le SCR est calibré à 99,9 % ?"),
    ("Décomposition des provisions techniques", "Comment se décomposent les provisions techniques sous Solvabilité II ?"),
]

ligne1 = st.columns(2)
ligne2 = st.columns(2)
for col, (label, q) in zip(ligne1 + ligne2, EXEMPLES):
    if col.button(label, use_container_width=True):
        st.session_state.question = q

question = st.text_input("Votre question :", key="question")

if st.button("Rechercher dans les textes", type="primary") and question.strip():
    with st.spinner("Recherche dans les textes réglementaires..."):
        t0 = time.time()
        reponse, docs, erreur = poser_question_cloud(question, vs, norme=NORMES[choix_norme])
        duree = time.time() - t0

    if erreur:
        st.error(erreur)
    else:
        with st.container(border=True):
            st.markdown(reponse)
            st.markdown(
                '<div class="pied-reponse">Réponse générée à partir des seuls extraits cités ci-dessus</div>',
                unsafe_allow_html=True,
            )

        duree_str = f"{duree:.1f}".replace(".", ",")
        st.caption(f"Réponse en {duree_str} s — version de démonstration ; 2 à 3 s en déploiement local.")

        st.markdown("**Références**")
        for i, d in enumerate(docs, 1):
            titre = reference_label(d.metadata.get("norme", "?"), d.metadata.get("page", "?"))
            with st.expander(titre):
                st.caption(d.page_content[:300] + ("…" if len(d.page_content) > 300 else ""))

st.markdown(
    """
    <div class="footer-app">
    Architecture conçue pour exécution locale — cette démonstration utilise des services hébergés, les corpus étant publics.<br>
    Prototype développé pour Iconcilio — Mohamed Amine Belasri · 2026
    </div>
    """,
    unsafe_allow_html=True,
)
