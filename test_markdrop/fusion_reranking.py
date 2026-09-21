# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier combine les résultats des 4 recherches séparées et les
# classe pour ne garder que le meilleur candidat. C'est le cœur du
# système qui décide quelle réponse est la plus pertinente.
# ------------------------------------------------------------------
"""fusion_reranking.py — Fusion (Reciprocal Rank Fusion) + reranking entre
les 4 collections Qdrant déjà indexées et mesurées séparément (texte,
tableaux, images, qrt).

DÉCISIONS PRISES ICI (documentées aussi dans DECISIONS.md) :

1. **Cohere Rerank est TEXTE UNIQUEMENT** — vérifié dans sa documentation
   officielle (https://docs.cohere.com/docs/rerank-overview : aucune
   mention d'image ; le champ de facturation "images" est toujours à
   None) et recoupé par recherche web (Cohere ne propose pas non plus de
   modèle de chat multimodal dans sa famille Command — "multimodal
   workloads need a different provider"). Ça élimine l'option "un seul
   reranker Cohere pour tout". MÉTHODE RETENUE : un JUGE LLM MULTIMODAL
   (Gemini, déjà utilisé ailleurs dans ce projet — cf. ingest.py,
   CLAUDE.md du projet principal — via l'endpoint OpenAI-compatible,
   MÊME configuration que src/rag.py : base_url
   "https://generativelanguage.googleapis.com/v1beta/openai/",
   GEMINI_API_KEY, modèle "gemini-flash-latest"). Vérifié que cet
   endpoint accepte des images en `image_url` (data URL base64), format
   standard OpenAI vision. UN SEUL appel de jugement par requête, mélangeant
   texte et images — pas deux rerankers séparés (Cohere pour le texte +
   LLM pour le reste), pour rester fidèle à la consigne "capable de
   traiter texte ET image dans le même appel".

2. **Traitement de "tableaux" (2 vecteurs nommés) dans la fusion** :
   compte comme UNE SEULE liste dans la fusion à 4 collections (texte,
   tableaux, images, qrt) — pas deux listes indépendantes
   "tableaux-texte"/"tableaux-image". Raison : la fusion RRF ici combine
   des COLLECTIONS DE CONTENUS DE NATURE DIFFÉRENTE (chunks de texte vs
   tableaux vs images vs pages QRT), pas plusieurs méthodes de recherche
   sur un MÊME corpus (l'usage "classique" de RRF, ex. dense+sparse) —
   donner deux listes à "tableaux" gonflerait artificiellement son poids
   dans la fusion finale par rapport à texte/images/qrt (qui n'ont chacune
   qu'UN signal), ce qui n'est pas justifié par une supériorité réelle du
   contenu tableau, seulement par un détail d'implémentation (2 vecteurs
   au lieu d'1). LA LISTE UNIQUE DE "TABLEAUX" EST ELLE-MÊME CONSTRUITE PAR
   FUSION RRF NATIVE QDRANT (Prefetch + RrfQuery, vérifié empiriquement
   fonctionnel contre le serveur local) des 2 vecteurs "texte"/"image" —
   pas un simple "meilleur des deux rangs" qui perdrait le signal du
   vecteur non retenu : un tableau bien classé sur SES DEUX vecteurs
   remonte légitimement plus haut qu'un tableau bien classé sur un seul.

3. **Constante RRF k=60** — valeur standard de la littérature (papier
   original Cormack, Clarke & Buettcher 2009 ; défaut d'Elasticsearch pour
   son propre RRF), réutilisée à la fois pour la fusion interne de
   "tableaux" (Qdrant natif) et pour la fusion externe entre les 4
   collections (implémentation Python ci-dessous) — même constante partout,
   pas une valeur différente par étage.

Réutilise TELS QUELS les clients/fonctions déjà configurés dans
recherche_collections.py (encoder_bge, encoder_cohere, get_client_qdrant)
— pas recréés différemment.

4. **Filtres disponibles (Décision 047, Phase 2)** — `_construire_filtre`
   (filtre Qdrant natif, avant fusion/reranking) sur "year" (int, Décision
   032) et "company_name" (str, Décision 047), combinables (ET logique) ou
   omis (recherche sur tout le corpus). 4 modes, tous documentés dans
   DECISIONS.md Décision 047 :
   - Mode 1 — global : `fusionner_candidats(question)` (défauts).
   - Mode 2 — filtre entreprise : `fusionner_candidats(question, company_name="Groupama")`.
   - Mode 3 — filtre année : `fusionner_candidats(question, annee=2025)`.
   - Mode 4 — comparatif (2+ entreprises, résultats groupés PAR entreprise,
     jamais fusionnés entre elles) : `fusionner_candidats_comparatif(question, ["Groupama", "X"])`.
   `pipeline_complet*` (avec reranking LLM) accepte les mêmes paramètres
   `annee`/`company_name` que `fusionner_candidats`, transmis tels quels.
   Index de payload Qdrant sur "company_name"/"year" : `creer_index_payload.py`
   (idempotent, vérifié — relançable sans risque après une réindexation).
"""

import base64
import json
import os
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
DOSSIER_SOURCE = BASE_DIR / "output_structure_brute"
CHUNKS_PROPRES_JSON = DOSSIER_SOURCE / "chunks_propres.json"

RRF_K = 60  # cf. point 3 de la documentation ci-dessus — même constante partout

TOP_K_PAR_COLLECTION = 10  # nb de candidats remontés par collection AVANT fusion
TOP_K_APRES_FUSION = 8     # nb de candidats envoyés au juge LLM APRÈS fusion RRF
TOP_K_FINAL = 5            # nb de résultats retournés APRÈS reranking

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODELE = "gemini-flash-latest"  # même config que src/rag.py (projet principal)

from qdrant_client.http.models import Filter, FieldCondition, MatchValue

import chemins_visuels as cv
from recherche_collections import get_client_qdrant, encoder_bge, encoder_cohere

_chunks_indexables_cache = None
_client_gemini = None


def get_client_gemini():
    """Client OpenAI SDK pointé sur l'endpoint Gemini — MÊME configuration
    que src/rag.py (projet principal, cf. PROVIDERS["gemini"]), pas une
    config différente inventée ici."""
    global _client_gemini
    if _client_gemini is None:
        cle_api = os.environ.get("GEMINI_API_KEY")
        if not cle_api:
            raise RuntimeError(
                "Variable d'environnement GEMINI_API_KEY absente — nécessaire pour le "
                "reranking (juge LLM multimodal)."
            )
        from openai import OpenAI
        _client_gemini = OpenAI(api_key=cle_api, base_url=GEMINI_BASE_URL, timeout=30)
    return _client_gemini


def _charger_chunks_indexables():
    global _chunks_indexables_cache
    if _chunks_indexables_cache is None:
        with open(CHUNKS_PROPRES_JSON, encoding="utf-8") as f:
            chunks = json.load(f)
        _chunks_indexables_cache = [c for c in chunks if c.get("categorie") == "indexable"]
    return _chunks_indexables_cache


# ---------------------------------------------------------------------
# 1. Recherche par collection — chacune renvoie une liste ordonnée de
#    candidats {id, type, payload, rang} (rang 1-indexé, ordre Qdrant).
# ---------------------------------------------------------------------

def _construire_filtre(annee=None, company_name=None):
    """Filtre Qdrant natif combinant year (Décision 032) et company_name
    (Décision 047), en ET logique quand les deux sont précisés — None si
    aucun des deux ne l'est (comportement inchangé : recherche sur tout le
    corpus, toutes années/entreprises confondues). Filtre NATIF (passé à
    query_points/Prefetch), jamais un post-traitement après coup — la
    limite top_k s'applique alors réellement APRÈS filtrage, pas avant.
    `_filtre_annee` était le nom d'origine (year seul) — généralisé ici
    plutôt que dupliqué à côté, tous les appelants existants continuent de
    fonctionner en ne passant que `annee`."""
    conditions = []
    if annee is not None:
        conditions.append(FieldCondition(key="year", match=MatchValue(value=annee)))
    if company_name is not None:
        conditions.append(FieldCondition(key="company_name", match=MatchValue(value=company_name)))
    if not conditions:
        return None
    return Filter(must=conditions)


def _points_vers_candidats(points, type_collection, prefixe_id):
    candidats = []
    for rang, p in enumerate(points, start=1):
        candidats.append({
            "id": f"{prefixe_id}:{p.id}",
            "type": type_collection,
            "rang": rang,
            "score_brut": p.score,
            "payload": p.payload,
        })
    return candidats


def rechercher_texte_pour_fusion(question, top_k=TOP_K_PAR_COLLECTION, annee=None, company_name=None):
    vecteur = encoder_bge(question)
    reponse = get_client_qdrant().query_points(
        collection_name="texte", query=vecteur, using="dense", limit=top_k,
        query_filter=_construire_filtre(annee, company_name),
    )
    return _points_vers_candidats(reponse.points, "texte", "texte")


def rechercher_tableaux_pour_fusion(question, top_k=TOP_K_PAR_COLLECTION, annee=None, company_name=None):
    """UNE SEULE liste pour "tableaux" (cf. point 2 de la documentation du
    module) — construite par fusion RRF NATIVE Qdrant des 2 vecteurs
    "texte" (BGE-M3) et "image" (Cohere Embed v4), pas un choix arbitraire
    entre les deux. Filtre (annee/company_name) appliqué à CHAQUE Prefetch
    (chacun est une sous-requête vectorielle indépendante) ET au niveau top
    (RRF sur le résultat déjà filtré des 2 sous-requêtes)."""
    from qdrant_client.http.models import Prefetch, RrfQuery, Rrf

    vecteur_texte = encoder_bge(question)
    vecteur_image = encoder_cohere(question)
    filtre = _construire_filtre(annee, company_name)
    reponse = get_client_qdrant().query_points(
        collection_name="tableaux",
        prefetch=[
            Prefetch(query=vecteur_texte, using="texte", limit=top_k, filter=filtre),
            Prefetch(query=vecteur_image, using="image", limit=top_k, filter=filtre),
        ],
        query=RrfQuery(rrf=Rrf(k=RRF_K)),
        query_filter=filtre,
        limit=top_k,
        with_payload=True,
    )
    return _points_vers_candidats(reponse.points, "tableau", "tableaux")


def rechercher_images_pour_fusion(question, top_k=TOP_K_PAR_COLLECTION, annee=None, company_name=None):
    vecteur = encoder_cohere(question)
    reponse = get_client_qdrant().query_points(
        collection_name="images", query=vecteur, using="image", limit=top_k,
        query_filter=_construire_filtre(annee, company_name),
    )
    return _points_vers_candidats(reponse.points, "image", "images")


def rechercher_qrt_pour_fusion(question, top_k=TOP_K_PAR_COLLECTION, annee=None, company_name=None):
    vecteur = encoder_cohere(question)
    reponse = get_client_qdrant().query_points(
        collection_name="qrt", query=vecteur, using="image", limit=top_k,
        query_filter=_construire_filtre(annee, company_name),
    )
    return _points_vers_candidats(reponse.points, "page_qrt", "qrt")


# ---------------------------------------------------------------------
# 2. Fusion RRF entre les 4 listes (texte, tableaux, images, qrt)
# ---------------------------------------------------------------------

def fusionner_rrf(listes_candidats, k=RRF_K):
    """listes_candidats : liste de listes de candidats (une par
    collection, déjà triées par rang croissant). Combine par RANG (pas
    par score brut — échelles différentes entre BGE-M3 et Cohere, cf.
    consigne). Chaque candidat contribue exactement 1/(k+rang) à son
    propre score RRF — ici chaque candidat n'apparaît que dans UNE seule
    des 4 listes (collections disjointes par nature), donc pas de somme
    sur plusieurs listes comme dans un RRF classique multi-retriever."""
    tous = []
    for liste in listes_candidats:
        for c in liste:
            c = dict(c)
            c["score_rrf"] = 1.0 / (k + c["rang"])
            tous.append(c)
    tous.sort(key=lambda c: c["score_rrf"], reverse=True)
    return tous


def fusionner_candidats(question, top_k_par_collection=TOP_K_PAR_COLLECTION, top_k_apres_fusion=TOP_K_APRES_FUSION,
                         annee=None, company_name=None):
    """Modes 1-3 de la recherche filtrée (Décision 047) :
    - Mode 1 (global) : annee=None, company_name=None (défaut, comportement
      inchangé) — recherche sur tout le corpus, toutes années/entreprises.
    - Mode 2 (filtre entreprise) : company_name="Groupama" par ex.
    - Mode 3 (filtre année) : annee=2025 par ex.
    - Les deux ensemble filtrent sur les deux à la fois (ET logique, cf.
      _construire_filtre).
    Filtre NATIF Qdrant (cf. Décision 032) dans les 4 collections, avant
    même le reranking LLM — jamais un post-filtrage après coup."""
    listes = [
        rechercher_texte_pour_fusion(question, top_k_par_collection, annee=annee, company_name=company_name),
        rechercher_tableaux_pour_fusion(question, top_k_par_collection, annee=annee, company_name=company_name),
        rechercher_images_pour_fusion(question, top_k_par_collection, annee=annee, company_name=company_name),
        rechercher_qrt_pour_fusion(question, top_k_par_collection, annee=annee, company_name=company_name),
    ]
    fusionnes = fusionner_rrf(listes)
    return fusionnes[:top_k_apres_fusion]


def fusionner_candidats_comparatif(question, entreprises, top_k_par_collection=TOP_K_PAR_COLLECTION,
                                    top_k_apres_fusion=TOP_K_APRES_FUSION, annee=None):
    """Mode 4 — recherche comparative (Décision 047) : lance
    fusionner_candidats() EN PARALLÈLE pour CHAQUE entreprise de
    `entreprises` (ThreadPoolExecutor — les appels sont I/O-bound : requêtes
    HTTP Qdrant + encodage), puis regroupe les résultats PAR ENTREPRISE
    plutôt que de les fusionner entre eux : {entreprise: candidats_fusionnes}.
    Une fusion RRF unique entre entreprises mélangerait des résultats
    destinés à être comparés côte à côte, pas classés ensemble — ce n'est
    pas ce que "comparer Groupama et X" demande. `annee` optionnel,
    s'applique à CHAQUE entreprise identiquement (comparaison à année
    égale)."""
    import concurrent.futures

    resultats = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, len(entreprises))) as executor:
        futures = {
            executor.submit(
                fusionner_candidats, question, top_k_par_collection, top_k_apres_fusion,
                annee=annee, company_name=entreprise,
            ): entreprise
            for entreprise in entreprises
        }
        for future in concurrent.futures.as_completed(futures):
            resultats[futures[future]] = future.result()
    # Ordre stable en sortie (celui de `entreprises`), pas l'ordre
    # d'achèvement des threads (non déterministe) — important pour tout
    # affichage/comparaison reproductible côté appelant.
    return {entreprise: resultats[entreprise] for entreprise in entreprises}


# ---------------------------------------------------------------------
# 3. Reranking — juge LLM multimodal (Gemini), UN SEUL appel, texte ET
#    image mélangés (cf. point 1 de la documentation du module).
# ---------------------------------------------------------------------

def _contenu_candidat_pour_juge(candidat):
    """Construit le contenu (texte et/ou image) d'UN candidat pour le
    prompt du juge — texte réel pour un chunk narratif (relu depuis
    chunks_propres.json, le payload Qdrant ne stocke pas le texte lui-même),
    image réelle (base64) pour un tableau/image/page QRT."""
    type_ = candidat["type"]
    payload = candidat["payload"]

    if type_ == "texte":
        chunks = _charger_chunks_indexables()
        # Le payload Qdrant de "texte" ne stocke pas index_corpus (cf.
        # ingest_qdrant.py) — on retrouve le chunk par (position_header,
        # position_origine, chemin_hierarchique) combinés, pas par
        # position_header seul (non unique, cf. Décision d'ingestion).
        candidats_possibles = [
            c for c in chunks
            if c["position_header"] == payload["position_header"]
            and c.get("position_origine") == payload.get("position_origine")
            and c["chemin_hierarchique"] == payload["chemin_hierarchique"]
        ]
        if len(candidats_possibles) != 1:
            texte = "(texte introuvable de façon non ambiguë — voir chemin_hierarchique)"
        else:
            texte = candidats_possibles[0]["texte"]
        entete = f"[TEXTE — {payload['chemin_hierarchique']}, pages {payload['pages']}]"
        return {"type": "text", "text": f"{entete}\n{texte[:1500]}"}

    # tableau / image / page_qrt : image réelle
    chemin_absolu = cv.chemin_absolu(payload["chemin_relatif"])
    with open(chemin_absolu, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}


def _juger_avec_client(client, modele, question, candidats):
    """Logique de jugement PARTAGÉE entre Gemini et tout autre fournisseur
    OpenAI-compatible (ex. OpenRouter, cf. juger_candidats_llm_openrouter
    ci-dessous) — même prompt, même format JSON strict, même absence de
    fallback silencieux sur un JSON invalide. Seul le client/modèle passé
    en paramètre change ; NE PAS dupliquer cette logique ailleurs."""
    contenu = [{"type": "text", "text":
        f"Question : {question!r}\n\n"
        f"Voici {len(candidats)} candidats (numérotés 1 à {len(candidats)}), certains sont des extraits "
        "de texte, d'autres des images (tableaux, graphiques, ou pages entières d'annexes réglementaires "
        "QRT). Pour CHAQUE candidat, donne un score de pertinence entier de 0 (aucun rapport) à 10 "
        "(répond directement et précisément à la question). Réponds STRICTEMENT en JSON, une liste "
        "d'objets {\"candidat\": <numéro>, \"score\": <0-10>}, rien d'autre.\n"
    }]
    for i, c in enumerate(candidats, start=1):
        contenu.append({"type": "text", "text": f"\n--- Candidat {i} (type={c['type']}) ---"})
        contenu.append(_contenu_candidat_pour_juge(c))

    completion = client.chat.completions.create(
        model=modele,
        messages=[{"role": "user", "content": contenu}],
        max_tokens=1000,
        temperature=0,
    )
    brut = completion.choices[0].message.content.strip()

    # Le modèle enrobe parfois le JSON de ```json ... ``` malgré la consigne
    # "rien d'autre" — nettoyage minimal avant parsing, pas une tentative
    # de deviner un format différent.
    if brut.startswith("```"):
        brut = brut.strip("`")
        if brut.startswith("json"):
            brut = brut[4:]
        brut = brut.strip()

    try:
        scores = json.loads(brut)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Réponse du juge LLM ({modele}) non parsable en JSON — pas de contournement deviné. "
            f"Réponse brute : {brut[:500]!r}"
        ) from e

    scores_par_indice = {s["candidat"]: s["score"] for s in scores}
    for i, c in enumerate(candidats, start=1):
        if i not in scores_par_indice:
            raise RuntimeError(f"Le juge LLM ({modele}) n'a pas noté le candidat {i} — réponse incomplète : {scores!r}")
        c["score_llm"] = scores_par_indice[i]

    candidats_tries = sorted(candidats, key=lambda c: c["score_llm"], reverse=True)
    return candidats_tries


def juger_candidats_llm(question, candidats):
    """UN SEUL appel Gemini (vision) : la question + tous les candidats
    (texte inline, images en pièces jointes), le juge renvoie un score de
    pertinence 0-10 par candidat (JSON strict). Retourne les candidats
    re-triés par ce score — pas de fallback silencieux si le JSON renvoyé
    est invalide (signalé explicitement, cf. consigne). CHEMIN VALIDÉ (10/10
    sur golden_set_unifie.json, cf. Décision 028) — ne pas modifier ici,
    tout changement de fournisseur passe par une fonction séparée
    (juger_candidats_llm_openrouter)."""
    return _juger_avec_client(get_client_gemini(), GEMINI_MODELE, question, candidats)


# ---------------------------------------------------------------------
# 3bis. Juge de secours OpenRouter — UNIQUEMENT pour les questions du
# golden set unifié que Gemini n'a pas pu traiter (quota gratuit épuisé,
# cf. Décision 028). Ne remplace PAS juger_candidats_llm/pipeline_complet
# (chemin Gemini existant, déjà validé), s'utilise explicitement via
# pipeline_complet_openrouter.
#
# Modèle retenu : nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free —
# choisi après vérification empirique (les 3 modèles initialement
# envisagés — qwen2.5-vl-72b, llama-3.2-11b-vision, mistral-small-3.1-24b,
# tous ":free" — sont TOUS passés payants sur OpenRouter entre-temps ;
# les 2 alternatives Google (gemma-4-31b-it, gemma-4-26b-a4b-it) sont
# disponibles mais rate-limited sur leur pool gratuit partagé au moment du
# test). Testé avec succès sur un vrai visuel du corpus (table_5.png) :
# décrit correctement son contenu.
# ---------------------------------------------------------------------

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
OPENROUTER_MODELE = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"

_client_openrouter = None


def get_client_openrouter():
    global _client_openrouter
    if _client_openrouter is None:
        cle_api = os.environ.get("OPENROUTER_API_KEY")
        if not cle_api:
            raise RuntimeError("Variable d'environnement OPENROUTER_API_KEY absente.")
        from openai import OpenAI
        _client_openrouter = OpenAI(api_key=cle_api, base_url=OPENROUTER_BASE_URL, timeout=30)
    return _client_openrouter


def juger_candidats_llm_openrouter(question, candidats):
    """MÊME logique de jugement que juger_candidats_llm (cf.
    _juger_avec_client) — seul le fournisseur/modèle change (OpenRouter /
    nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free au lieu de Gemini)."""
    return _juger_avec_client(get_client_openrouter(), OPENROUTER_MODELE, question, candidats)


def pipeline_complet(question, top_k_par_collection=TOP_K_PAR_COLLECTION,
                      top_k_apres_fusion=TOP_K_APRES_FUSION, top_k_final=TOP_K_FINAL, annee=None, company_name=None):
    """Fusion RRF (4 collections) puis reranking LLM multimodal (Gemini)
    sur le top des candidats fusionnés — pipeline complet de bout en
    bout. Reranking LLM CHEMIN VALIDÉ, non modifié (cf. Décision 028) ;
    `annee`/`company_name` (défaut None, comportement inchangé) ajoutent
    UNIQUEMENT un filtre natif Qdrant en amont, au niveau de la recherche
    (cf. Décisions 032, 047) — ne touche pas juger_candidats_llm."""
    fusionnes = fusionner_candidats(question, top_k_par_collection, top_k_apres_fusion, annee=annee, company_name=company_name)
    reclasses = juger_candidats_llm(question, fusionnes)
    return reclasses[:top_k_final]


def pipeline_complet_openrouter(question, top_k_par_collection=TOP_K_PAR_COLLECTION,
                                 top_k_apres_fusion=TOP_K_APRES_FUSION, top_k_final=TOP_K_FINAL,
                                 annee=None, company_name=None):
    """MÊME pipeline que pipeline_complet (fusion RRF identique, même
    fonction fusionner_candidats), mais reranking via le juge de secours
    OpenRouter au lieu de Gemini — utilisé uniquement pour les questions
    du golden set unifié que Gemini n'a pas pu traiter."""
    fusionnes = fusionner_candidats(question, top_k_par_collection, top_k_apres_fusion, annee=annee, company_name=company_name)
    reclasses = juger_candidats_llm_openrouter(question, fusionnes)
    return reclasses[:top_k_final]


# ---------------------------------------------------------------------
# 3ter. Juge de secours Mistral (Mistral Medium 3.5) — quota Gemini
# gratuit épuisé de façon durable (facturation Google non activée sur ce
# projet, cf. Décision 031), pas un incident ponctuel. Modèle choisi
# après vérification DIRECTE (pas deviné) : pixtral-large-latest est
# DÉPRÉCIÉ depuis le 27/02/2026, remplacé par Mistral Medium 3.5.
# L'identifiant lu sur docs.mistral.ai/models ("mistral-medium-3-5-26-04")
# s'est révélé être un SLUG D'URL, pas l'identifiant API réel — rejeté en
# 400 "Invalid model" au premier essai. Ré-vérifié via l'endpoint réel
# GET https://api.mistral.ai/v1/models (source de vérité, pas la doc) :
# "mistral-medium-2604" retenu parmi les alias valides confirmés présents
# dans la liste réelle du compte (mistral-medium-2604, mistral-medium-3-5,
# mistral-medium-3.5, mistral-medium-latest). Aucune entrée "pixtral*"
# dans cette liste : Pixtral n'est plus proposé du tout sur ce compte.
#
# NE RÉUTILISE PAS _juger_avec_client : le SDK natif mistralai diffère de
# l'interface OpenAI-compatible sur 2 points vérifiés (pas supposés) —
# (1) méthode client.chat.complete(...), pas client.chat.completions.create(...) ;
# (2) contenu image = {"type": "image_url", "image_url": "data:...;base64,..."}
# (chaîne texte directe), pas {"image_url": {"url": "..."}} (dict imbriqué
# à la OpenAI). Réutilise EN REVANCHE _contenu_candidat_pour_juge pour le
# texte (identique), avec un remontage du bloc image en local ici.
#
# Tier gratuit "Experiment" : limite de débit non publiée officiellement
# (vérifiée non trouvable dans la doc, confirmée par l'utilisateur à 2
# requêtes/minute) — appelant responsable d'espacer les appels, cette
# fonction ne fait qu'UN seul appel par question, pas de boucle interne.
# ---------------------------------------------------------------------

MISTRAL_MODELE = "mistral-medium-2604"

_client_mistral = None


def get_client_mistral():
    global _client_mistral
    if _client_mistral is None:
        cle_api = os.environ.get("MISTRAL_API_KEY")
        if not cle_api:
            raise RuntimeError("Variable d'environnement MISTRAL_API_KEY absente.")
        from mistralai.client import Mistral
        _client_mistral = Mistral(api_key=cle_api)
    return _client_mistral


def _contenu_candidat_pour_juge_mistral(candidat):
    """Identique à _contenu_candidat_pour_juge pour le texte (même
    fonction réutilisée) ; pour l'image, format Mistral natif vérifié
    (image_url = chaîne data-URL directe, pas de dict imbriqué)."""
    type_ = candidat["type"]
    if type_ == "texte":
        return _contenu_candidat_pour_juge(candidat)

    payload = candidat["payload"]
    chemin_absolu = cv.chemin_absolu(payload["chemin_relatif"])
    with open(chemin_absolu, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return {"type": "image_url", "image_url": f"data:image/png;base64,{b64}"}


def juger_candidats_llm_mistral(question, candidats):
    """Même logique de jugement que _juger_avec_client (même prompt, même
    format JSON strict imposé, même absence de fallback silencieux sur un
    JSON invalide) mais via le SDK natif mistralai (cf. note ci-dessus
    sur les 2 différences d'interface avec les clients OpenAI-compatibles)."""
    client = get_client_mistral()
    contenu = [{"type": "text", "text":
        f"Question : {question!r}\n\n"
        f"Voici {len(candidats)} candidats (numérotés 1 à {len(candidats)}), certains sont des extraits "
        "de texte, d'autres des images (tableaux, graphiques, ou pages entières d'annexes réglementaires "
        "QRT). Pour CHAQUE candidat, donne un score de pertinence entier de 0 (aucun rapport) à 10 "
        "(répond directement et précisément à la question). Réponds STRICTEMENT en JSON, une liste "
        "d'objets {\"candidat\": <numéro>, \"score\": <0-10>}, rien d'autre.\n"
    }]
    for i, c in enumerate(candidats, start=1):
        contenu.append({"type": "text", "text": f"\n--- Candidat {i} (type={c['type']}) ---"})
        contenu.append(_contenu_candidat_pour_juge_mistral(c))

    reponse = client.chat.complete(
        model=MISTRAL_MODELE,
        messages=[{"role": "user", "content": contenu}],
        max_tokens=1000,
        temperature=0,
    )
    brut = reponse.choices[0].message.content.strip()

    if brut.startswith("```"):
        brut = brut.strip("`")
        if brut.startswith("json"):
            brut = brut[4:]
        brut = brut.strip()

    try:
        scores = json.loads(brut)
    except json.JSONDecodeError as e:
        raise RuntimeError(
            f"Réponse du juge LLM ({MISTRAL_MODELE}) non parsable en JSON — pas de contournement deviné. "
            f"Réponse brute : {brut[:500]!r}"
        ) from e

    scores_par_indice = {s["candidat"]: s["score"] for s in scores}
    for i, c in enumerate(candidats, start=1):
        if i not in scores_par_indice:
            raise RuntimeError(f"Le juge LLM ({MISTRAL_MODELE}) n'a pas noté le candidat {i} — réponse incomplète : {scores!r}")
        c["score_llm"] = scores_par_indice[i]

    return sorted(candidats, key=lambda c: c["score_llm"], reverse=True)


# ---------------------------------------------------------------------
# 3quater. Juge (et génération, cf. generation.py) de secours Claude
# (claude-haiku-4-5) — bascule suite à l'épuisement du quota gratuit
# Gemini (blocage d'infrastructure/facturation, pas un défaut de code,
# cf. Décision 031). Haiku 4.5 retenu explicitement : moins cher des
# modèles Claude avec support vision (1 $/5 $ par million de tokens
# entrée/sortie, vérifié via recherche externe au moment de l'écriture —
# à re-vérifier si le prix change), gamme comparable à Gemini Flash qui a
# déjà validé 10/10 sur ce rôle (Décision 028). Sonnet/Opus explicitement
# écartés sans validation explicite d'un besoin (consigne).
#
# Format API Anthropic vérifié DIFFÉRENT de l'API OpenAI-compatible :
# client.messages.create(...) (pas chat.completions.create), et un bloc
# image = {"type": "image", "source": {"type": "base64", "media_type":
# ..., "data": ...}} (pas {"image_url": {"url": "data:...;base64,..."}})
# — _convertir_blocs_pour_claude ci-dessous convertit à partir du format
# OpenAI déjà produit par _contenu_candidat_pour_juge, réutilisé tel quel.
# ---------------------------------------------------------------------

CLAUDE_MODELE_JUGE = "claude-haiku-4-5-20251001"
PRIX_CLAUDE_HAIKU_45 = {"entree_par_million": 1.0, "sortie_par_million": 5.0}  # USD, vérifié externe

# Sonnet 5 — testé UNIQUEMENT sur échantillon (17 échecs identifiant TEXTE,
# cf. Décision 031/033), jamais généralisé sans un gain net mesuré (consigne).
CLAUDE_MODELE_SONNET = "claude-sonnet-5"
PRIX_CLAUDE_SONNET_5 = {"entree_par_million": 2.0, "sortie_par_million": 10.0}  # USD, vérifié externe

_client_claude = None


def get_client_claude():
    global _client_claude
    if _client_claude is None:
        cle_api = os.environ.get("ANTHROPIC_API_KEY")
        if not cle_api:
            raise RuntimeError("Variable d'environnement ANTHROPIC_API_KEY absente.")
        from anthropic import Anthropic
        _client_claude = Anthropic(api_key=cle_api)
    return _client_claude


def _convertir_blocs_pour_claude(blocs):
    """Convertit une liste de blocs de contenu au format OpenAI-compatible
    (texte inchangé, image = {"image_url": {"url": "data:...;base64,..."}})
    vers le format natif Anthropic (image = {"type": "image", "source":
    {"type": "base64", "media_type": ..., "data": ...}}) — les 2 API
    diffèrent réellement sur ce point, vérifié avant d'écrire cette
    fonction, pas supposé identique."""
    convertis = []
    for bloc in blocs:
        if bloc["type"] == "text":
            convertis.append(bloc)
        elif bloc["type"] == "image_url":
            url = bloc["image_url"]["url"]
            entete, b64 = url.split(",", 1)
            media_type = entete.split(";")[0].removeprefix("data:")
            convertis.append({"type": "image", "source": {"type": "base64", "media_type": media_type, "data": b64}})
        else:
            raise ValueError(f"Type de bloc non géré pour Claude : {bloc['type']!r}")
    return convertis


def cout_usd_claude(usage, prix=PRIX_CLAUDE_HAIKU_45):
    """Coût réel en USD d'un appel, à partir de l'objet usage retourné par
    l'API Anthropic (input_tokens/output_tokens) — jamais une estimation
    a priori, toujours le nombre de tokens réellement facturés."""
    return (usage.input_tokens * prix["entree_par_million"] / 1_000_000
            + usage.output_tokens * prix["sortie_par_million"] / 1_000_000)


def juger_candidats_llm_claude(question, candidats, modele=CLAUDE_MODELE_JUGE, prix=PRIX_CLAUDE_HAIKU_45):
    """Même logique de jugement que _juger_avec_client (même prompt, même
    format JSON strict imposé, même absence de fallback silencieux sur un
    JSON invalide) mais via le SDK natif Anthropic. Retourne (candidats
    triés, cout_usd) — le coût est renvoyé explicitement pour permettre le
    suivi réel demandé (pas une estimation), contrairement aux autres
    juges de secours qui ne le trackent pas encore. `modele`/`prix`
    paramétrables (défaut Haiku, comportement inchangé) pour permettre un
    test comparatif Sonnet SANS dupliquer cette fonction (cf. Décision 033)."""
    client = get_client_claude()
    contenu = [{"type": "text", "text":
        f"Question : {question!r}\n\n"
        f"Voici {len(candidats)} candidats (numérotés 1 à {len(candidats)}), certains sont des extraits "
        "de texte, d'autres des images (tableaux, graphiques, ou pages entières d'annexes réglementaires "
        "QRT). Pour CHAQUE candidat, donne un score de pertinence entier de 0 (aucun rapport) à 10 "
        "(répond directement et précisément à la question). Réponds STRICTEMENT en JSON, une liste "
        "d'objets {\"candidat\": <numéro>, \"score\": <0-10>}, rien d'autre.\n"
    }]
    for i, c in enumerate(candidats, start=1):
        contenu.append({"type": "text", "text": f"\n--- Candidat {i} (type={c['type']}) ---"})
        contenu.append(_contenu_candidat_pour_juge(c))
    contenu_claude = _convertir_blocs_pour_claude(contenu)

    # `temperature` REJETÉ en 400 ("deprecated for this model") par
    # claude-sonnet-5 — vérifié à l'exécution, pas supposé identique à
    # Haiku. Paramètre omis uniquement pour ce modèle précis.
    kwargs_temperature = {} if modele == CLAUDE_MODELE_SONNET else {"temperature": 0}
    # "extended thinking" CONFIRMÉ actif par défaut côté serveur sur
    # claude-sonnet-5 (un ThinkingBlock est apparu en tête de
    # message.content sans jamais avoir été demandé, cf. Décision 033) —
    # désactivé explicitement pour ce modèle (forme exacte vérifiée dans
    # le SDK installé : {"type": "disabled"}, pas devinée). Sans effet sur
    # Haiku (paramètre omis, comportement inchangé).
    kwargs_thinking = {"thinking": {"type": "disabled"}} if modele == CLAUDE_MODELE_SONNET else {}
    message = client.messages.create(
        model=modele,
        max_tokens=1000,
        messages=[{"role": "user", "content": contenu_claude}],
        **kwargs_temperature,
        **kwargs_thinking,
    )
    # Cherche le premier bloc TEXTE, plutôt que de supposer content[0] —
    # un ThinkingBlock (ou un futur type de bloc) peut précéder le texte,
    # vérifié nécessaire sur Sonnet avant "thinking": "disabled".
    blocs_texte = [b for b in message.content if b.type == "text"]
    if not blocs_texte:
        raise RuntimeError(f"Réponse du juge LLM ({modele}) sans bloc texte — blocs reçus : "
                            f"{[b.type for b in message.content]!r}")
    brut = blocs_texte[0].text.strip()
    cout = cout_usd_claude(message.usage, prix=prix)

    if brut.startswith("```"):
        brut = brut.strip("`")
        if brut.startswith("json"):
            brut = brut[4:]
        brut = brut.strip()

    try:
        scores = json.loads(brut)
    except json.JSONDecodeError:
        # Motif RÉELLEMENT observé sur claude-sonnet-5 (Décision 033,
        # test du 2026-09-13) : des objets JSON valides individuellement,
        # concaténés ligne par ligne au lieu d'une liste JSON unique
        # ({"candidat": 1, "score": 8}\n{"candidat": 2, "score": ...).
        # Filet de sécurité CIBLÉ sur ce motif précis (pas un JSON invalide
        # générique) : si CHAQUE ligne non vide est un objet JSON valide,
        # on les regroupe en liste — sinon on lève l'erreur d'origine,
        # aucun autre contournement deviné.
        try:
            scores = [json.loads(ligne) for ligne in brut.splitlines() if ligne.strip()]
            if not all(isinstance(s, dict) and "candidat" in s and "score" in s for s in scores):
                raise ValueError
        except (json.JSONDecodeError, ValueError):
            scores = None
    if scores is None:
        raise RuntimeError(
            f"Réponse du juge LLM ({modele}) non parsable en JSON — pas de contournement deviné. "
            f"Réponse brute : {brut[:500]!r}"
        )

    scores_par_indice = {s["candidat"]: s["score"] for s in scores}
    for i, c in enumerate(candidats, start=1):
        if i not in scores_par_indice:
            raise RuntimeError(f"Le juge LLM ({modele}) n'a pas noté le candidat {i} — réponse incomplète : {scores!r}")
        c["score_llm"] = scores_par_indice[i]

    return sorted(candidats, key=lambda c: c["score_llm"], reverse=True), cout


def pipeline_complet_claude(question, top_k_par_collection=TOP_K_PAR_COLLECTION,
                             top_k_apres_fusion=TOP_K_APRES_FUSION, top_k_final=TOP_K_FINAL,
                             annee=None, company_name=None):
    """MÊME pipeline que pipeline_complet (fusion RRF identique), mais
    reranking via Claude Haiku 4.5. Retourne (candidats[:top_k_final], cout_usd)."""
    fusionnes = fusionner_candidats(question, top_k_par_collection, top_k_apres_fusion, annee=annee, company_name=company_name)
    reclasses, cout = juger_candidats_llm_claude(question, fusionnes)
    return reclasses[:top_k_final], cout


def pipeline_complet_mistral(question, top_k_par_collection=TOP_K_PAR_COLLECTION,
                              top_k_apres_fusion=TOP_K_APRES_FUSION, top_k_final=TOP_K_FINAL,
                              annee=None, company_name=None):
    """MÊME pipeline que pipeline_complet (fusion RRF identique), mais
    reranking via le juge de secours Mistral au lieu de Gemini."""
    fusionnes = fusionner_candidats(question, top_k_par_collection, top_k_apres_fusion, annee=annee, company_name=company_name)
    reclasses = juger_candidats_llm_mistral(question, fusionnes)
    return reclasses[:top_k_final]


# ---------------------------------------------------------------------
# 4. Baseline simple (sans fusion RRF, sans reranking) — pour mesurer si
#    la complexité ajoutée apporte un vrai gain.
# ---------------------------------------------------------------------

def baseline_meilleur_score_normalise(question, top_k_par_collection=TOP_K_PAR_COLLECTION, top_k_final=TOP_K_FINAL, annee=None):
    """Baseline volontairement naïve : interroge les 4 collections
    séparément (tableaux : vecteur "image" ET vecteur "texte" comme 2
    requêtes indépendantes ici, PAS la fusion RRF native utilisée par le
    pipeline complet — la baseline ne doit dépendre d'aucun des choix de
    fusion évalués), normalise min-max les scores de CHAQUE liste
    indépendamment (les échelles brutes ne sont pas comparables entre
    BGE-M3 et Cohere), puis retourne simplement les candidats avec le
    meilleur score normalisé, toutes collections confondues — sans RRF,
    sans reranking LLM. `annee` (défaut None) : même filtre natif que
    fusionner_candidats (cf. Décision 032), pour une comparaison
    baseline/pipeline honnête sur le même périmètre de recherche."""
    vecteur_bge = encoder_bge(question)
    vecteur_cohere = encoder_cohere(question)
    client = get_client_qdrant()
    filtre = _construire_filtre(annee)

    reponse_texte = client.query_points(collection_name="texte", query=vecteur_bge, using="dense", limit=top_k_par_collection, query_filter=filtre)
    reponse_tableaux_image = client.query_points(collection_name="tableaux", query=vecteur_cohere, using="image", limit=top_k_par_collection, query_filter=filtre)
    reponse_tableaux_texte = client.query_points(collection_name="tableaux", query=vecteur_bge, using="texte", limit=top_k_par_collection, query_filter=filtre)
    reponse_images = client.query_points(collection_name="images", query=vecteur_cohere, using="image", limit=top_k_par_collection, query_filter=filtre)
    reponse_qrt = client.query_points(collection_name="qrt", query=vecteur_cohere, using="image", limit=top_k_par_collection, query_filter=filtre)

    groupes = [
        ("texte", reponse_texte.points),
        ("tableau", reponse_tableaux_image.points),
        ("tableau", reponse_tableaux_texte.points),
        ("image", reponse_images.points),
        ("page_qrt", reponse_qrt.points),
    ]

    tous = []
    for type_, points in groupes:
        if not points:
            continue
        scores = [p.score for p in points]
        mini, maxi = min(scores), max(scores)
        etendue = (maxi - mini) or 1.0  # évite une division par zéro si tous les scores sont égaux
        for p in points:
            score_norm = (p.score - mini) / etendue
            tous.append({
                "id": f"{type_}:{p.id}", "type": type_, "score_norm": score_norm,
                "score_brut": p.score, "payload": p.payload,
            })

    tous.sort(key=lambda c: c["score_norm"], reverse=True)
    return tous[:top_k_final]
