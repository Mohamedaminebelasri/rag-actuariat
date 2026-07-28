# RAG Solvabilité II (Iconcilio)

## Objectif
Assistant qui répond sur la directive 2009/138/CE en citant [Article N], et refuse plutôt que d'halluciner.

## Stack
- Python 3.11 · venv · Windows · RTX 3050 (4 Go VRAM)
- Embeddings : BGE-M3 (dense), safetensors via le miroir `Shitao/bge-m3` (contourne CVE-2025-32434)
- Index : FAISS local dans `faiss_solva2/` (index.faiss + mapping.json)
- LLM : Mistral (`api.mistral.ai/v1`), `mistral-large-latest`, température 0

## Fichiers clés
- `src/ingest.py` → HTML EUR-Lex (CELEX 32009L0138, FR) → `data/articles.jsonl`
- `src/index.py` → construit `faiss_solva2/`
- `src/rag.py` → `poser_question(q, k=5, model=..., self_eval=False)` : retrieval + génération + citation
- `src/evaluate.py` → évalue sur `data/golden_set.jsonl`, écrit `data/eval_rag.md`
- `data/articles.jsonl` → 312 articles (numero_article, titre, texte, source)
- `data/golden_set.jsonl` → 18 questions validées manuellement

## État actuel
Retrieval : 18/18 (Recall@5). Génération : 17/18 citations correctes.
Acronymes (SCR, MCR, ORSA...) résolus via `expand_query` (voir Décision 006).

## Règles non négociables
- `temperature=0` toujours
- Citation `[Article N]` obligatoire dans toute réponse
- Si l'info n'est pas dans les articles fournis : refus exact, jamais d'invention

Historique complet des décisions → voir DECISIONS.md.
