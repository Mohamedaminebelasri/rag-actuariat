# ARCHITECTURE — RAG Solvabilité II (découpage par article)

Ce document décrit le **nouveau projet planifié**, pas l'ancien (voir archive git).
Le principe directeur : un segment = un article de la directive 2009/138/CE,
jamais un bloc de N caractères arbitraire.

---

## 1. Schéma général

```
════════════════════════════════════════════════════════════════════
PHASE 1 — PRÉPARATION (une seule fois, hors ligne)
════════════════════════════════════════════════════════════════════

  data/solva2.pdf
  (texte officiel, directive 2009/138/CE)
        │
        ▼
  ┌───────────────────────────────────────────┐
  │ src/ingest.py                              │
  │  - PyPDFLoader : lecture page par page     │
  │  - regex "Article \d+" : détection des      │
  │    frontières entre articles               │
  │  - RecursiveCharacterTextSplitter :         │
  │    seulement si un article dépasse la       │
  │    taille max d'un chunk (sous-découpage)   │
  │  - attache à chaque segment :               │
  │      • numéro d'article                     │
  │      • numéro de page                       │
  └───────────────────────────────────────────┘
        │
        ▼
  segments + métadonnées (article, page)
        │
        ▼
  ┌───────────────────────────────────────────┐
  │ src/index.py                               │
  │  - embeddings : multilingual-e5-large (GPU) │
  │  - construction de l'index FAISS            │
  │  - persistance sur disque                   │
  └───────────────────────────────────────────┘
        │
        ▼
  index FAISS + métadonnées (sur disque)

════════════════════════════════════════════════════════════════════
PHASE 2 — QUESTION (à chaque requête utilisateur)
════════════════════════════════════════════════════════════════════

  question utilisateur
        │
        ▼
  ┌───────────────────────────────────────────┐
  │ src/rag.py                                 │
  │  - encodage question (e5-large)             │
  │  - recherche top-k dans l'index FAISS       │
  │  - récupération segments + (article, page)  │
  │  - construction du prompt contraint         │
  │  - appel Groq llama-3.3-70b (température 0) │
  └───────────────────────────────────────────┘
        │
        ▼
  réponse citée [Article X — page Y]
  ou refus explicite si aucun segment pertinent
════════════════════════════════════════════════════════════════════
```

---

## 2. Fichiers planifiés

| Fichier | Rôle (une phrase) | Entrées | Sorties | État |
|---|---|---|---|---|
| `data/solva2.pdf` | Texte source officiel de la directive 2009/138/CE | — | — | **existe** |
| `src/ingest.py` | Découpe le PDF article par article et attache (article, page) à chaque segment | `data/solva2.pdf` | liste de segments + métadonnées | **nouveau — cœur du projet** |
| `src/index.py` | Encode les segments avec e5-large et construit l'index FAISS | segments + métadonnées (sortie d'`ingest.py`) | index FAISS persisté sur disque | **nouveau** |
| `src/rag.py` | Recherche les segments pertinents et génère une réponse citée via Groq | question utilisateur + index FAISS | réponse `[Article X — page Y]` ou refus | **nouveau** |
| `src/golden_set.py` | Jeu de questions/réponses de référence pour l'évaluation | — | golden set (Q/A attendues) | **repris de l'archive** |
| `src/evaluate.py` | Mesure la qualité de la récupération et des réponses sur le golden set | golden set + `rag.py` | rapport de métriques | **nouveau** |
| `DECISIONS.md` | Journal des choix techniques et de leur justification | — | — | **nouveau** |
| `JOURNAL.md` | Journal chronologique de l'avancement du projet | — | — | **nouveau** |

---

## 3. Outils

- **Python 3.11**
- **PyPDFLoader** — lecture du PDF avec conservation du numéro de page
- **regex** (`re`) — détection des frontières `Article \d+`
- **RecursiveCharacterTextSplitter** — filet de sécurité pour les articles trop longs uniquement
- **multilingual-e5-large** (GPU) — modèle d'embeddings
- **FAISS** — index vectoriel
- **Groq `llama-3.3-70b`**, température 0 — génération contrainte, réponses citées

---

## 4. Programme de travail

Chaque étape ci-dessous doit être **documentée dans `DECISIONS.md`** (choix fait et pourquoi)
et **tracée dans `JOURNAL.md`** (ce qui a été fait, quand, résultat).

1. **`ingest.py`** — lire `data/solva2.pdf`, détecter les articles via regex, extraire
   (texte, numéro d'article, numéro de page) pour chaque segment.
2. **Validation manuelle du découpage** — vérifier sur un échantillon que chaque segment
   correspond bien à un article complet, avec le bon numéro et la bonne page.
3. **`index.py`** — encoder les segments validés avec e5-large, construire et persister
   l'index FAISS.
4. **`rag.py`** — implémenter la recherche top-k + le prompt de génération contrainte
   (citation obligatoire ou refus) via Groq.
5. **`golden_set.py`** — reprendre/adapter le golden set de l'archive pour la structure
   par article.
6. **`evaluate.py`** — exécuter le golden set sur `rag.py` et produire un rapport de
   métriques (précision de citation, taux de refus correct, etc.).

---

## 5. Question ouverte

Avant d'écrire `ingest.py` : la forme **"Article N"** est-elle constante dans tout
`solva2.pdf` (même casse, même format, pas de variantes du type "Article premier",
"Art. N", numérotation avec suffixes comme "Article 13 bis", en-têtes/pieds de page
qui répètent le mot "Article", etc.) ? Cette vérification conditionne la fiabilité
de la regex de découpage.
