# RAG multinorme — actuariat (Iconcilio)

## Objectif
Assistant qui répond sur IFRS 17 et Solvabilité II en citant
[Norme — page X], et refuse d'inventer plutôt que d'halluciner.

## Stack
- Python 3.11 · venv · Windows · RTX 3050 (4 Go VRAM)
- Embeddings : intfloat/multilingual-e5-large · 1024 dim · cuda · ~2,24 Go VRAM mesurée (torch.cuda.memory_allocated)
- Index : FAISS local · 2 626 chunks (IFRS 17 28% / Solva II 72%)
- LLM : Groq · llama-3.3-70b-versatile · temperature 0

## Fichiers
- src/index.py    → construit faiss_multinorme/
- src/rag.py      → poser_question(q, k=5, norme=None, mode="dense"|"hybrid_rerank")
- src/evaluate.py → golden set + score
- src/golden_set.py → GOLDEN (25 questions, source de vérité)
- src/retrieval.py, retrieval_rrf.py, retrieval_rerank.py, retrieval_rerank_b.py → diagnostics retrieval (0 appel Groq)
- src/evaluate_partial.py → sous-ensemble golden_set (Solva II + comparatives + pièges mauvaise norme), dense vs hybrid_rerank
- src/evaluate_v2.py → golden set complet (25 q.), --mode dense|hybrid_rerank, écriture incrémentale + reprise sur 429 (--resume)
- data/           → ifrs17.pdf (129p) · solva2.pdf (155p)

## État
Baseline dense v2 : 25/25 (rappel 15/15, robustesse 10/10), Q8 = pass avec
réserve documentée — voir eval_dense_2026-07-17.md (source officielle,
re-scoré le 2026-07-17, mode="dense", index post-réindexation \xad)
Retrieval : mode="hybrid_rerank" opérationnel (Ensemble dense 70%/BM25 30%
+ rerank cross-encoder A, top20 → top k), mode="dense" inchangé par défaut
Index réindexé le 2026-07-17 (césures \xad recollées au chunking) — résultats
antérieurs à cette date (resultats.md, resultats_hybrid.md Q1-Q11) générés
sur l'ancien index, Q12 de resultats_hybrid.md généré après réindexation

## Règles non négociables
- Même modèle d'embeddings en indexation ET en requête
- Ne jamais retirer la règle anti-hallucination du prompt
- temperature = 0 toujours
- Hybrid search SANS reranking dégrade → les deux ou aucun
- 4 Go VRAM → Ollama max 3B, pas Mistral 7B
- VRAM libre réelle après e5-large ≈ 1,8 Go (4 Go − 2,24 Go mesurés), pas ~2,8 Go comme l'estimation initiale de 1,2 Go le laissait croire

## Pièges rencontrés
- La détection de refus par mot-clé produit de faux FAIL
- Le JO européen a deux bugs de texte DISTINCTS, pas un seul :
  1. césure de fin de ligne via soft-hyphen \xad (ex: "uti-lisée" coupé en
     fin de ligne) → corrigé au chunking dans index.py (clean_page), 0 cas
     restant après réindexation du 2026-07-17
  2. espace inséré AU MILIEU d'un mot SANS aucune césure ni \xad, artefact
     de justification du texte PDF (ex: "assuran ce", "n treprise",
     "solvab ilité") → PAS corrigé, 619/2626 chunks encore touchés (mesuré
     après le fix #1). Pas de marqueur pour distinguer cet espace d'un vrai
     espace : nécessiterait un correcteur lexical (dictionnaire FR), pas
     une regex. Donc "d'assuran ce" peut encore apparaître dans les réponses.
- Prompt de rag.py : "[Norme — page X]" comme exemple de citation était
  recopié littéralement par le LLM comme fausse citation → remplacé par un
  exemple concret non-recopiable "[IFRS 17 — page 42]" (visible dans
  resultats.md/resultats_hybrid.md avant correction, ex. R11/R12 anciens)
- Windows + PowerShell : jamais `python -c` avec apostrophes
- Out-File -Encoding utf8 ajoute un BOM → casse dotenv
- e5-large mesuré à 2,24 Go VRAM (fp32), pas 1,2 Go comme estimé au départ
- Le reranking peut DÉGRADER un chunk déjà bien classé : sur la question
  "provisions techniques", le chunk cible (rang 5 après RRF) tombe au rang 18
  avec le reranker A (mmarco-mMiniLMv2-L12) et au rang 13 avec le candidat B
  (bge-reranker-v2-m3, fp16) — testé, pas juste théorique. Le reranking n'est
  donc pas un pur gain : à vérifier par question, pas supposé.
- Un chunk absent du pool retrieval (dense+BM25 top20, ex: MCR "25%/45%" au
  rang réel ~1300/2626) restera absent après reranking : le reranker ne trie
  que ce qui lui est présenté, il ne peut pas rattraper un retrieval manqué
- Expérience confondue du 2026-07-16 — baseline dense (resultats.md) et run
  hybrid (resultats_hybrid.md) utilisaient des formulations différentes ;
  toute comparaison de modes doit utiliser LES MÊMES questions.

## llama3.2:3b — inutilisable comme juge d'évaluation, utilisable pour smoke tests
Testé le 2026-07-17 sur le pipeline réel (même prompt que poser_question,
retrieval dense k=5, extraits identiques à ceux envoyés à Groq), 3 questions,
temperature=0 :

- Q1 "Qu'est-ce que la CSM selon IFRS 17 ?" (23,6s) → cite [IFRS 17 — page 27]
  mais INVENTE l'acronyme : "CSM (Cash Shortfall Measure)" au lieu de
  Contractual Service Margin
- Q2 "Quel est le taux de TVA des croissants ?" (2,5s) → refus correct :
  "Je ne trouve pas cette information dans les documents fournis."
- Q3 "Comment IFRS 17 définit-il le SCR ?" (10,7s) → NE corrige PAS la
  fausse prémisse (règle 3 du prompt), invente une définition et l'attribue
  à "[IFRS 17 — page 89]" alors que le SCR est un concept Solvabilité II

Verdict : 1/3 correct (le refus hors-périmètre). Sur les 2 questions qui
demandaient de la précision factuelle (acronyme exact, correction de norme),
le 3B invente avec la même confiance apparente qu'une réponse correcte —
inutilisable pour juger la qualité du retrieval ou du prompt. Reste utile
pour un smoke test rapide (le pipeline tourne, retourne une réponse dans un
format exploitable) mais pas pour évaluer dense vs hybrid_rerank : `llm="ollama"`
n'est PAS intégré dans rag.py. Comparaison dense vs hybrid actée sur Groq 70B,
étalée sur plusieurs jours de quota (voir src/evaluate_v2.py).

## Axe 3 — traçabilité, validé le 2026-07-17
- Vérification manuelle humaine : 4 annotations sur 4 contrôlées exactes
  dans les PDF (Solva II p.46 Art.77, p.7 recital 62, p.34 Art.45 ; IFRS 17
  physique 37 section 1.5 VFA)
- Découverte : ifrs17.pdf a 12 pages de garde → page imprimée =
  metadata["page"] - 11. solva2.pdf : aucun décalage.
- Correctif à prévoir (phase 5) : afficher page_label au lieu de page dans
  les citations, pour que la vérification humaine tombe juste au premier clic.

## Prochaines étapes
1. ~~Golden set → 25 questions~~ fait (src/golden_set.py)
2. ~~Hybrid BM25 + reranking cross-encoder~~ fait (rag.py mode="hybrid_rerank",
   candidat A conservé — B testé, pas meilleur sur le cas qui compte)
3. MCR "entre quelles bornes" (25%/45%) reste hors de portée : chunk cible
   au rang ~1300/2626, absent de tout pool retrieval testé (dense, BM25,
   RRF). Piste : contextual retrieval (préfixer chaque chunk d'un résumé de
   section généré par LLM avant indexation) ou query expansion — PAS tenté
4. Réévaluer golden_set.py (25 questions) en entier avec evaluate.py une
   fois le quota Groq disponible — jamais fait depuis sa création. Voir
   src/evaluate_v2.py (dense vs hybrid_rerank, étalé sur ~2 jours de quota)
5. ~~Ollama 3B → comparer contre Groq 70B~~ abandonné : le 3B invente sur
   2/3 questions test, inutilisable comme juge (cf. section dédiée ci-dessus)