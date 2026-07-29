# RAG Solvabilité II (Iconcilio)

## Objectif
Assistant qui répond sur la directive 2009/138/CE en citant [Article N], et refuse plutôt que d'halluciner.

## Stack réelle
- Python 3.11 (dev) / 3.10 (VM prod, Oracle Cloud) · BGE-M3 dense, safetensors via `Shitao/bge-m3`
- Index : FAISS `IndexFlatIP` dans `faiss_solva2/` (index.faiss + mapping.json)
- LLM : fallback automatique **Gemini (`gemini-flash-latest`) → Mistral (`mistral-large-latest`) → Groq (`llama-3.3-70b-versatile`)**, température 0

## Fichiers clés
- `src/ingest.py` → HTML EUR-Lex (CELEX 32009L0138, FR) → `data/articles.jsonl` (312 articles)
- `src/index.py` → construit `faiss_solva2/`
- `src/rag.py` → retrieval + acronymes + clarification d'ambiguïté + génération citée
- `src/evaluate.py` → évalue sur `data/golden_set.jsonl` (**50 questions**), écrit `data/eval_final_50.md`
- `app.py` → interface Streamlit, **seule interface active** (déployée sur VM Oracle Cloud)
- `app_gradio.py` → **abandonné** (ex-Hugging Face Spaces/ZeroGPU), non couvert par requirements.txt

## État actuel (data/eval_final_50.md)
Recall@5 : 43/50 (0.860). Citation correcte : 43/50 (0.860). MRR : 0.7307.
Acronymes (SCR, MCR, ORSA...) résolus via `expand_query` (Décision 006).

## Règles non négociables
- `temperature=0` toujours
- Citation `[Article N]` obligatoire dans toute réponse
- Si l'info n'est pas dans les articles fournis : refus exact, jamais d'invention

Historique complet des décisions → voir DECISIONS.md. Architecture détaillée → voir ARCHITECTURE.md.
