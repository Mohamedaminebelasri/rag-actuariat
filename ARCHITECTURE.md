# ARCHITECTURE — RAG Solvabilité II (Iconcilio)

Document régénéré le 2026-07-29 à partir du code réel (`src/*.py`, `app.py`,
`requirements.txt`), pas de l'ancienne version (25/07, projet planifié PDF +
e5-large, jamais celui effectivement construit) ni de suppositions.

---

## 1. Schéma général (pipeline réel)

```
════════════════════════════════════════════════════════════════════
PHASE 1 — PRÉPARATION (une seule fois, hors ligne)
════════════════════════════════════════════════════════════════════

  EUR-Lex HTML (CELEX 32009L0138, FR, requête HTTP directe)
        │
        ▼
  ┌───────────────────────────────────────────┐
  │ src/ingest.py                              │
  │  - requests.get() sur l'URL EUR-Lex         │
  │  - regex sur les <div class="eli-subdivi-   │
  │    sion" id="art_N"> : une frontière = un   │
  │    article                                  │
  │  - nettoyage des balises, détection de mots │
  │    cassés / pieds de page collés            │
  └───────────────────────────────────────────┘
        │
        ▼
  data/articles.jsonl (312 articles : numero_article, titre, texte, source)
        │
        ▼
  ┌───────────────────────────────────────────┐
  │ src/index.py                               │
  │  - embeddings : BGE-M3 (Shitao/bge-m3,      │
  │    miroir safetensors), GPU si dispo        │
  │  - FAISS IndexFlatIP (similarité cosinus,   │
  │    embeddings normalisés)                   │
  └───────────────────────────────────────────┘
        │
        ▼
  faiss_solva2/index.faiss + mapping.json (sur disque)

════════════════════════════════════════════════════════════════════
PHASE 2 — QUESTION (à chaque requête utilisateur, via app.py)
════════════════════════════════════════════════════════════════════

  question utilisateur (chat Streamlit)
        │
        ▼
  reformulation contextuelle (si historique non vide) — appel_llm
        │
        ▼
  clarifier() — juge LLM : CLAIRE ou AMBIGUË
        │                         │
        │ CLAIRE                 └─ AMBIGUË → retourne une question
        ▼                            de clarification, ARRÊT (pas de
  expand_query()                     retrieval, pas de génération)
   résolution d'acronymes (dict
   fixe, 11 sigles : SCR, MCR,
   ORSA, EIOPA...)
        │
        ▼
  _rechercher() — encode la question (BGE-M3), top-k=5 dans FAISS
   (mode="dense" en production ; retrieval_hybride() [BM25+RRF]
   existe dans le code mais rejeté comme défaut — Décisions 010, 015)
        │
        ▼
  poser_question() — construit le prompt contraint (contexte + règles
   de citation/refus/correction) → appel_llm()
        │
        ▼
  appel_llm() — chaîne de fallback Gemini → Mistral → Groq,
   température 0 (Décisions 008, 009, 012)
        │
        ▼
  réponse citée [Article N], correction de fausses prémisses
   numériques (Décision 011), ou refus explicite si hors corpus
        │
        ▼
  app.py affiche la réponse + expander "Articles consultés"
════════════════════════════════════════════════════════════════════
```

---

## 2. Fichiers actifs

| Fichier | Rôle (une phrase) | Entrées | Sorties | Statut |
|---|---|---|---|---|
| `src/ingest.py` | Télécharge le HTML EUR-Lex de la directive et en extrait les articles structurés par regex | URL EUR-Lex (CELEX 32009L0138, FR) | `data/articles.jsonl` (312 articles) | **Actif** |
| `src/index.py` | Encode les articles avec BGE-M3 et construit l'index vectoriel FAISS | `data/articles.jsonl` | `faiss_solva2/index.faiss` + `faiss_solva2/mapping.json` | **Actif** |
| `src/rag.py` | Cœur du pipeline : retrieval dense, expansion d'acronymes, clarification d'ambiguïté, appel LLM multi-fournisseur avec fallback, prompt de génération citée | question utilisateur + `faiss_solva2/` + `.env` (clés API) | chaîne de réponse citée `[Article N]`, refus explicite, ou `{"type": "clarification", "message": ...}` | **Actif** |
| `src/evaluate.py` | Exécute le golden set sur `rag.py` et mesure Recall@5, taux de citation correcte, MRR | `data/golden_set.jsonl` (50 questions) + `src/rag.py` | `data/eval_final_50.md` | **Actif** |
| `app.py` | Interface web Streamlit (chat) — seule interface effectivement déployée (VM Oracle Cloud, service systemd `solvabilite2`) | question utilisateur (navigateur) | réponse affichée + sources dans un expander | **Actif** |
| `requirements.txt` | Dépendances de production : `streamlit`, `torch`, `sentence-transformers`, `faiss-cpu`, `rank-bm25`, `openai` (SDK générique multi-fournisseur), `python-dotenv`, `requests`, `numpy` | — | — | **Actif** |

**Fichier abandonné mais toujours présent :**

| Fichier | Rôle d'origine | Statut |
|---|---|---|
| `app_gradio.py` | Interface Gradio pour déploiement Hugging Face Spaces (ZeroGPU) | **Abandonné** — annoté en tête de fichier, non couvert par `requirements.txt` (plus de `gradio`/`spaces`), migration VM Oracle Cloud retenue à la place |

**Contenu de `archive/` (déplacé lors de l'audit du 28/07, historique git préservé) :**

| Fichier | Contenu | Raison de l'archivage |
|---|---|---|
| `archive/DIAGNOSTIC.md` | Audit ponctuel de la qualité de `data/articles.jsonl` | Analyse one-shot, non maintenue |
| `archive/resultat.md` | Notes de dev sur l'intégration de la détection d'ambiguïté | Contenu repris dans `DECISIONS.md` (Décision 007) |
| `archive/comparaison_modeles.md` | Comparaison e5-large vs BGE-M3 (retrieval seul) | Analyse ayant motivé la Décision 004, décision déjà actée |
| `archive/eval_rag.md` | Ancien résultat d'évaluation (18 questions, sans fallback) | Remplacé par `data/eval_final_50.md` (50 questions) |

**Fichiers `data/` présents mais non consommés par le pipeline actif :**

`data/solva2.pdf` et `data/ifrs17.pdf` ne sont référencés par aucun script actuel — reliquats de l'ancien pipeline PDF (Décision 003, remplacé par l'ingestion HTML EUR-Lex). `data/golden_acronymes.jsonl` (8 questions) et `data/golden_ambiguite.jsonl` (10 questions) ne sont pas lus par `src/evaluate.py` (qui n'utilise que `data/golden_set.jsonl`, 50 questions) — probablement des jeux de test manuels ponctuels.

---

## 3. Outils réels

- **Python 3.11.9** en local (dev) · **Python 3.10.12** sur la VM de production (Oracle Cloud, Ubuntu 22.04 ARM)
- **BGE-M3** (`Shitao/bge-m3`, miroir safetensors — contourne CVE-2025-32434) — embeddings dense, `max_seq_length=1024`
- **FAISS** `IndexFlatIP` — recherche par similarité cosinus (embeddings normalisés)
- **rank-bm25** — présent, utilisé par `retrieval_hybride()` (RRF dense+BM25) mais **non actif par défaut** (Décisions 010, 015)
- **OpenAI SDK** en client générique — compatible avec 4 fournisseurs déclarés (`gemini`, `mistral`, `groq`, `cerebras`), 3 dans la chaîne de fallback réelle (`gemini → mistral → groq`)
- **Streamlit** — interface web, seule interface déployée
- **systemd** (`solvabilite2.service`) — supervision du process en production, `Restart=always`

---

## 4. Ordre d'exécution pour repartir de zéro

```bash
# 1. Cloner et installer
git clone https://github.com/Mohamedaminebelasri/rag-actuariat.git
cd rag-actuariat
python -m venv .venv
source .venv/bin/activate          # ou .venv\Scripts\activate sous Windows
pip install -r requirements.txt

# 2. Configurer les clés (jamais commitées, .env dans .gitignore)
cat > .env << 'EOF'
GEMINI_API_KEY=...
MISTRAL_API_KEY=...
GROQ_API_KEY=...
EOF

# 3. Ingestion — télécharge et parse la directive depuis EUR-Lex
python src/ingest.py
# -> génère data/articles.jsonl (312 articles attendus)

# 4. Indexation — encode avec BGE-M3, construit l'index FAISS
python src/index.py
# -> génère faiss_solva2/index.faiss + faiss_solva2/mapping.json
# -> vérifie automatiquement que l'Article 129 sort en rang 1 sur une
#    question test (garde-fou intégré à verify())

# 5. (optionnel mais recommandé) Valider le pipeline complet
python src/evaluate.py
# -> génère data/eval_final_50.md (Recall@5, citation correcte, MRR)

# 6. Lancer l'interface
streamlit run app.py
# -> http://localhost:8501
```

Aucune étape ne dépend d'un GPU : `torch` bascule sur CPU automatiquement
(`device = "cuda" if torch.cuda.is_available() else "cpu"`), plus lent mais
fonctionnel — c'est le mode réel de la VM de production (1 vCPU ARM, pas
de GPU).

---

## 5. Écarts entre CLAUDE.md et le code réel

| Point | CLAUDE.md dit | Le code fait réellement |
|---|---|---|
| Fournisseur LLM | "Mistral (`api.mistral.ai/v1`), `mistral-large-latest`" comme seul fournisseur | `DEFAULT_PROVIDER = "gemini"` (`gemini-flash-latest`), avec fallback automatique **Gemini → Mistral → Groq** (Décisions 008, 009, 012). Mistral n'est utilisé qu'en secours. `température=0` reste vrai sur les 3. |
| Sortie de `src/evaluate.py` | "écrit `data/eval_rag.md`" | Écrit `data/eval_final_50.md` (`OUTPUT_PATH` dans le code). `eval_rag.md` est l'**ancien** output (18 questions, sans fallback), maintenant dans `archive/`. |
| Taille du golden set | "18 questions validées manuellement" | `data/golden_set.jsonl` contient **50 questions** (Décision 014, golden set étendu). Les jeux de 18 questions (`golden_acronymes.jsonl` 8 + `golden_ambiguite.jsonl` 10) existent séparément mais ne sont pas utilisés par `evaluate.py`. |
| État actuel (métriques) | "Retrieval : 18/18 (Recall@5). Génération : 17/18 citations correctes." | Chiffres périmés (ancien golden set 18 questions). Dernière mesure réelle (50 questions, `data/eval_final_50.md`) : **Recall@5 = 43/50 (0.860)**, **citation correcte = 43/50 (0.860)**, **MRR = 0.7307**. |
| Fichiers clés | Ne mentionne ni `app.py` ni le déploiement | `app.py` (Streamlit) est la seule interface active, déployée en production sur une VM Oracle Cloud via systemd. `app_gradio.py` est un fichier abandonné, non listé nulle part dans `CLAUDE.md`. |
| Capacités du pipeline | Ne mentionne que la résolution d'acronymes (Décision 006) | Le pipeline inclut aussi la **détection d'ambiguïté** (Décision 007, `clarifier()`) et la **correction de fausses prémisses numériques** (Décision 011), toutes deux actives dans `app.py` (`clarify=True`). |
| Retrieval hybride | Non mentionné | `rank-bm25` est dans les dépendances et `retrieval_hybride()` existe dans `rag.py`, mais **explicitement rejeté comme défaut** après deux évaluations (Décisions 010, 015) — mode `"dense"` partout en production. |

`CLAUDE.md` n'a pas été modifié dans le cadre de cette régénération —
seuls les écarts sont documentés ci-dessus, à corriger séparément si besoin.
