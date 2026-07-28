import json
import os
import re

# Cache HF explicite, à la racine du projet (portable local/HF Spaces — le
# disque du Space est accessible en écriture par défaut sur le tier gratuit,
# pas besoin de stockage persistant payant pour ça). Ne PAS forcer
# HF_HUB_OFFLINE=1 : ça bloquerait le tout premier déploiement (cache vide,
# mode offline = téléchargement impossible = le Space ne démarre jamais).
os.environ.setdefault("HF_HOME", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".hf_cache"))

import faiss
import numpy as np
import torch
from dotenv import load_dotenv
from openai import APIConnectionError, APITimeoutError, OpenAI
from rank_bm25 import BM25Okapi
from sentence_transformers import SentenceTransformer

load_dotenv()

INDEX_PATH = "faiss_solva2/index.faiss"
MAPPING_PATH = "faiss_solva2/mapping.json"
EMBEDDING_MODEL_NAME = "Shitao/bge-m3"  # miroir safetensors du même modèle que BAAI/bge-m3

# Fournisseurs LLM disponibles, tous compatibles OpenAI SDK (base_url + clé +
# nom de modèle changent, le reste du code est identique). Ne pas supprimer
# une entrée quand on change de défaut : ça permet de rebasculer en une ligne
# (provider="mistral"|"gemini"|...).
PROVIDERS = {
    "gemini": {
        "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
        "api_key_env": "GEMINI_API_KEY",
        "model": "gemini-flash-latest",  # "gemini-2.5-flash" renvoie 404 (fermé aux nouveaux comptes)
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "api_key_env": "MISTRAL_API_KEY",
        "model": "mistral-large-latest",
    },
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_env": "GROQ_API_KEY",
        "model": "llama-3.3-70b-versatile",
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "api_key_env": "CEREBRAS_API_KEY",
        "model": "gpt-oss-120b",  # llama-3.3-70b indisponible sur ce compte (404)
    },
}

# Gemini retenu (Décision 008) : 1500 requêtes/jour, largement suffisant pour
# le pipeline conversationnel (3 appels LLM/question : reformulation +
# clarification + génération) qui saturait le tier gratuit Mistral.
DEFAULT_PROVIDER = "gemini"

# Décision 009 (Gemini->Mistral) puis Décision 012 (ajout de Groq en 3e,
# nouvelle clé validée) : chaîne de fallback automatique. Cerebras disponible
# dans PROVIDERS mais pas dans cette chaîne (pas testé en usage courant, pas
# de raison de l'y ajouter pour l'instant).
FALLBACK_ORDER = ["gemini", "mistral", "groq"]

_llm_clients = {}  # un client OpenAI par provider, créé à la demande


def _get_llm_client(provider):
    if provider not in _llm_clients:
        cfg = PROVIDERS[provider]
        _llm_clients[provider] = OpenAI(
            api_key=os.environ[cfg["api_key_env"]],
            base_url=cfg["base_url"],
            timeout=30,  # évite un blocage indéfini si l'API ne répond pas (défaut SDK ~10 min)
        )
    return _llm_clients[provider]


# Alias de compatibilité (utilisés par app.py et d'anciens scripts) : pointent
# vers le provider par défaut.
LLM_MODEL = PROVIDERS[DEFAULT_PROVIDER]["model"]
_llm_client = _get_llm_client(DEFAULT_PROVIDER)

# Gemini consomme une partie du budget max_tokens en raisonnement interne caché,
# même sur des prompts de classification triviaux (ex. "OUI"/"NON" a consommé
# ~150 tokens de réflexion avant le token de réponse visible). Pas de moyen
# documenté de désactiver ça via l'endpoint compatible OpenAI (reasoning_effort
# et extra_body google.thinking_config testés, tous deux rejetés en 400) — on
# compense en donnant assez de marge. Mistral et Groq n'ont pas ce
# comportement, donc pas besoin d'autant de marge de ce côté.
MAX_TOKENS_COURT = {"gemini": 2000, "mistral": 200, "groq": 200}     # classification (juge OUI/NON, CLAIRE/AMBIGUE)
MAX_TOKENS_LONG = {"gemini": 4096, "mistral": 2048, "groq": 2048}    # réponses substantielles (génération, reformulation)


# Codes déclenchant un fallback : quota/débit (429), facturation (402),
# authentification/clé invalide (401, 403 — et 400 : constaté empiriquement
# que l'endpoint Gemini répond 400 "Please pass a valid API key" pour une clé
# invalide, pas 401 comme la plupart des API OpenAI-compatibles).
CODES_FALLBACK = {400, 401, 402, 403, 429}


def appel_llm(prompt, taille="long", verbose=True, providers=None):
    """Appel LLM unifié avec fallback automatique (Décision 009).

    Essaie les providers de `providers` (par défaut FALLBACK_ORDER) dans
    l'ordre. Bascule sur le suivant en cas d'erreur de quota/débit/
    authentification (CODES_FALLBACK) OU d'erreur de connexion réseau
    (APIConnectionError/APITimeoutError — celles-ci n'ont PAS de status_code
    car l'échec survient avant toute réponse HTTP, donc un simple test sur
    status_code les ratait). Si tous échouent, ou sur toute autre erreur non
    couverte, l'exception remonte telle quelle — pas de 3e fallback, pas de
    boucle. Logs toujours en print(..., flush=True) pour apparaître
    immédiatement dans les logs du Space (pas de bufferisation).
    """
    providers = providers or FALLBACK_ORDER
    max_tokens_par_taille = MAX_TOKENS_COURT if taille == "court" else MAX_TOKENS_LONG

    derniere_erreur = None
    for i, provider in enumerate(providers):
        print(f"[appel_llm] tentative {i + 1}/{len(providers)} : provider={provider}", flush=True)
        try:
            client = _get_llm_client(provider)
            model_name = PROVIDERS[provider]["model"]
            completion = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=max_tokens_par_taille[provider],
            )
            if i > 0:
                print(f"[appel_llm] SUCCÈS après bascule : {providers[i - 1]} -> {provider}", flush=True)
            elif verbose:
                print(f"[appel_llm] SUCCÈS sur {provider} (premier essai)", flush=True)
            return completion.choices[0].message.content
        except Exception as e:
            derniere_erreur = e
            status_code = getattr(e, "status_code", None)
            erreur_connexion = isinstance(e, (APIConnectionError, APITimeoutError))
            declenche_fallback = status_code in CODES_FALLBACK or erreur_connexion

            print(
                f"[appel_llm] ÉCHEC provider={provider} | "
                f"type={type(e).__name__} | status_code={status_code} | "
                f"erreur_connexion={erreur_connexion} | "
                f"message complet={e!r}",
                flush=True,
            )

            if not declenche_fallback:
                print(f"[appel_llm] ARRÊT : erreur non couverte par le fallback, remontée telle quelle", flush=True)
                raise
            if i == len(providers) - 1:
                print(f"[appel_llm] Dernier provider de la chaîne épuisé ({provider})", flush=True)
            else:
                print(f"[appel_llm] Bascule prévue vers : {providers[i + 1]}", flush=True)
            continue

    print(f"[appel_llm] TOUS LES PROVIDERS ONT ÉCHOUÉ : {providers}", flush=True)
    raise RuntimeError(
        f"Tous les fournisseurs LLM ont échoué ({', '.join(providers)}). "
        f"Dernière erreur : {derniere_erreur!r}"
    )


# Dictionnaire fixe (pas de LLM) : sigles courants de Solvabilité II.
# "SCR" apparaît tel quel dans le corpus (38 occurrences, ex. "capital de
# solvabilité requis (SCR)"), mais les autres sigles n'y figurent JAMAIS —
# le texte officiel les épelle toujours en toutes lettres. D'où l'intérêt
# de l'expansion : rapprocher la question posée (en jargon métier) du
# vocabulaire réellement utilisé dans le texte.
ACRONYMES = {
    "SCR": "capital de solvabilité requis",
    "MCR": "minimum de capital requis",
    "ORSA": "évaluation interne des risques et de la solvabilité",
    "BE": "meilleure estimation",
    "PT": "provisions techniques",
    "FP": "fonds propres",
    "VaR": "valeur à risque",
    "SFCR": "rapport sur la solvabilité et la situation financière",
    "EIOPA": "Autorité européenne des assurances et des pensions professionnelles",
    "AEAPP": "Autorité européenne des assurances et des pensions professionnelles",
    "ACPR": "Autorité de contrôle prudentiel et de résolution",
}


def expand_query(question):
    expanded = question
    for sigle, forme_longue in ACRONYMES.items():
        pattern = re.compile(rf"\b{re.escape(sigle)}\b", re.IGNORECASE)
        if pattern.search(expanded):
            expanded = pattern.sub(f"{sigle} ({forme_longue})", expanded, count=1)
    return expanded


PROMPT_TEMPLATE = """Tu es un assistant spécialisé sur la directive Solvabilité II
(2009/138/CE). Tu réponds UNIQUEMENT à partir des articles fournis
ci-dessous.
RÈGLES ABSOLUES :
1. Réponds uniquement d'après les articles fournis.
2. Cite TOUJOURS l'article source au format [Article N].
3. Si la question contient un chiffre, un pourcentage, un seuil ou une
   borne inexact(e), et que les articles fournis donnent la valeur
   correcte, NE REFUSE PAS : signale explicitement l'écart avec le
   chiffre mentionné dans la question, indique la valeur correcte, et
   cite l'article source. Ceci prime sur la règle 4. Si tu corriges une
   valeur, ne commence JAMAIS ta réponse par la phrase de refus.
   Commence directement par la correction, ex : "Le SCR est calibré à
   99,5 %, et non 99,9 % [Article X]."
4. Si l'information n'est pas dans les articles fournis, réponds
   exactement : "Je ne trouve pas cette information dans les
   articles fournis."
5. N'invente jamais. Ne complète jamais de mémoire.

ARTICLES FOURNIS :
{contexte}

QUESTION : {question}
RÉPONSE :"""

# --- Chargement une fois au chargement du module ---
_index = faiss.read_index(INDEX_PATH)
with open(MAPPING_PATH, encoding="utf-8") as _f:
    _mapping = json.load(_f)

_embedding_model = None  # chargement paresseux


def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device=device)
        _embedding_model.max_seq_length = 1024
    return _embedding_model


def _rechercher(question, k):
    model = _get_embedding_model()
    q_emb = model.encode([question], normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
    _, idxs = _index.search(q_emb, k)
    return [_mapping[i] for i in idxs[0]]


def _rechercher_dense_idx(question, k):
    model = _get_embedding_model()
    q_emb = model.encode([question], normalize_embeddings=True, convert_to_numpy=True).astype(np.float32)
    _, idxs = _index.search(q_emb, k)
    return list(idxs[0])


# --- Retrieval hybride EN TEST (mode="hybrid" dans poser_question) : BM25 en
# complément du dense BGE-M3, ne remplace pas le retrieval actuel tant que non
# validé sur le golden set. ---
def _tokeniser_bm25(texte):
    return re.findall(r"\w+", texte.lower())


_bm25_corpus_tokens = [_tokeniser_bm25(f"{a['titre']} {a['texte']}") for a in _mapping]
_bm25 = BM25Okapi(_bm25_corpus_tokens)


def _rechercher_bm25_idx(question, k):
    scores = _bm25.get_scores(_tokeniser_bm25(question))
    return list(np.argsort(scores)[::-1][:k])


def retrieval_hybride(question, k=5, k_fusion=20, poids_dense=0.7, poids_bm25=0.3, rrf_k=60):
    """Fusion par Reciprocal Rank Fusion (RRF) du dense (BGE-M3/FAISS) et de
    BM25, pondérée 70% dense / 30% BM25 par défaut."""
    dense_idx = _rechercher_dense_idx(question, k_fusion)
    bm25_idx = _rechercher_bm25_idx(question, k_fusion)

    scores_fusion = {}
    for rang, idx in enumerate(dense_idx, start=1):
        idx = int(idx)
        scores_fusion[idx] = scores_fusion.get(idx, 0.0) + poids_dense * (1 / (rrf_k + rang))
    for rang, idx in enumerate(bm25_idx, start=1):
        idx = int(idx)
        scores_fusion[idx] = scores_fusion.get(idx, 0.0) + poids_bm25 * (1 / (rrf_k + rang))

    tries = sorted(scores_fusion.items(), key=lambda x: x[1], reverse=True)[:k]
    return [_mapping[idx] for idx, _ in tries]


def _construire_contexte(articles):
    blocs = []
    for a in articles:
        blocs.append(f"[Article {a['numero_article']} — {a['titre']}]\n{a['texte']}\n")
    return "\n".join(blocs)


def _est_un_refus(reponse):
    return reponse.strip().startswith("Je ne trouve pas") and "[Article" not in reponse


JUGE_PROMPT_TEMPLATE = """Voici une question et des articles de loi récupérés pour y répondre.

QUESTION : {question}

ARTICLES RÉCUPÉRÉS :
{contexte}

Ces articles contiennent-ils de quoi répondre à la question ?
Réponds STRICTEMENT sous l'une de ces deux formes, rien d'autre :
OUI
NON : <reformulation courte de la requête de recherche>"""


def _juger_retrieval(question, articles, verbose=True):
    contexte = _construire_contexte(articles)
    prompt = JUGE_PROMPT_TEMPLATE.format(question=question, contexte=contexte)

    reponse = appel_llm(prompt, taille="court", verbose=verbose).strip()

    if reponse.upper().startswith("OUI"):
        return True, None
    if reponse.upper().startswith("NON"):
        partie = reponse.split(":", 1)
        reformulation = partie[1].strip() if len(partie) > 1 else None
        return False, reformulation
    # réponse hors format attendu : par prudence, on considère le retrieval suffisant
    # (évite de déclencher une reformulation sur une base non fiable)
    return True, None


CLARIFICATION_JUGE_PROMPT = """Cette question sur Solvabilité II est-elle assez précise pour y répondre, ou trop vague/ambiguë ?
Réponds uniquement par un seul mot : CLAIRE ou AMBIGUE.

QUESTION : {question}"""

CLARIFICATION_REFORMULATION_PROMPT = """Cette question sur Solvabilité II est trop vague ou ambiguë pour y répondre directement :

QUESTION : {question}

Propose UNE seule question de clarification précise, en français, pour aider
l'utilisateur à préciser sa demande. Réponds uniquement avec cette question
de clarification, rien d'autre."""


def clarifier(question, verbose=True):
    decision = appel_llm(
        CLARIFICATION_JUGE_PROMPT.format(question=question), taille="court", verbose=verbose
    ).strip().upper()

    if "AMBIG" not in decision:
        return {"ambigue": False, "message": None}

    message = appel_llm(
        CLARIFICATION_REFORMULATION_PROMPT.format(question=question), taille="long", verbose=verbose
    ).strip()
    return {"ambigue": True, "message": message}


def poser_question(question, k=5, verbose=True, self_eval=False, clarify=False, mode="dense"):
    if clarify:
        resultat_clarif = clarifier(question, verbose=verbose)
        if resultat_clarif["ambigue"]:
            if verbose:
                print(f"QUESTION : {question}")
                print(f"[clarification] question jugée AMBIGUË — pas de retrieval, pas de génération")
                print(f"CLARIFICATION DEMANDÉE : {resultat_clarif['message']}")
                print()
            return {"type": "clarification", "message": resultat_clarif["message"]}

    requete_recherche = expand_query(question)
    articles = retrieval_hybride(requete_recherche, k) if mode == "hybrid" else _rechercher(requete_recherche, k)

    if self_eval:
        suffisant, reformulation = _juger_retrieval(question, articles, verbose=verbose)
        if not suffisant and reformulation:
            if verbose:
                print(f"[self-eval] retrieval jugé insuffisant, reformulation : \"{reformulation}\"")
            reformulation_expandue = expand_query(reformulation)
            articles = (
                retrieval_hybride(reformulation_expandue, k)
                if mode == "hybrid"
                else _rechercher(reformulation_expandue, k)
            )
        elif not suffisant and verbose:
            print("[self-eval] retrieval jugé insuffisant, mais pas de reformulation exploitable — on garde le résultat initial")

    contexte = _construire_contexte(articles)
    prompt = PROMPT_TEMPLATE.format(contexte=contexte, question=question)

    reponse = appel_llm(prompt, taille="long", verbose=verbose)

    if verbose:
        print(f"QUESTION : {question}")
        print(f"RÉPONSE  : {reponse}")
        refus = _est_un_refus(reponse)
        print(f"REFUS DÉTECTÉ : {refus}")
        print("SOURCES CONSULTÉES :")
        for a in articles:
            print(f"  - Article {a['numero_article']} — {a['titre']}")
        print()

    return reponse


if __name__ == "__main__":
    questions_test = [
        "Comment calcule-t-on le minimum de capital requis ?",
        "Comment sont calculées les provisions techniques ?",
        "Quel est le taux de TVA sur les croissants ?",
    ]

    for q in questions_test:
        poser_question(q)
        print("-" * 70)
