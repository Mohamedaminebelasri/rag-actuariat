# Rapport de précision — RAG multinorme (IFRS 17 / Solvabilité II)

## 1. Protocole

- **Golden set** : 25 questions (`src/golden_set.py`, source de vérité unique) —
  15 `TROUVE` (5 IFRS 17 + 7 Solvabilité II + 3 comparatives) / 10 `REFUSE`
  (pièges : concept inventé, faux chiffre, mauvaise norme, hors périmètre).
- **Juge** : Groq `llama-3.3-70b-versatile`, `temperature=0`.
- **Index** : FAISS reconstruit le 2026-07-17 (`faiss_multinorme/`), après
  correctif des césures JO (`\xad` recollé au chunking dans `index.py`).
- **Critères de scoring** : match de mots-clés (`c["m"]`) insensible à la
  casse ET aux accents via `_fold()` (NFKD + suppression des diacritiques),
  ajouté dans `evaluate.py` et `evaluate_v2.py` le 2026-07-17. Pour les
  questions `REFUSE`, critère = préfixe exact
  `"je ne trouve pas cette information dans les documents fournis"`.

## 2. Résultats dense — 25/25

Source : `eval_dense_2026-07-17.md` (re-scoré le 2026-07-17 avec les
critères Q1/Q8 corrigés — réponses inchangées, aucun appel LLM pour le
re-scoring).

| Axe | Questions | PASS | FAIL |
|---|---|---|---|
| IFRS 17 | 5 | 5 | 0 |
| Solvabilité II | 7 | 7 | 0 |
| Comparatives | 3 | 3 | 0 |
| Pièges (REFUSE) | 10 | 10 | 0 |
| **Total** | **25** | **25** | **0** |

Rappel (TROUVE) : 15/15 — Robustesse (REFUSE) : 10/10.

**Réserve documentée — Q8** ("Comment calcule-t-on le montant que
l'assureur doit mettre de côté pour couvrir ses engagements futurs envers
les assurés ?") : PASS au sens des mots-clés, mais les 5 sources citées
sont **toutes IFRS 17** — le volet Solvabilité II (provisions techniques,
Art. 77) n'est jamais couvert par la réponse. Marqué en commentaire dans
`golden_set.py` : *"vrai échec partiel — ne couvre jamais le volet
Solvabilité II. Ne pas 'réparer' par les mots-clés."*

## 3. Résultats hybrid_rerank

*[à compléter]*

## 4. Deltas et verdict de mode

*[à compléter]*

## 5. Axe 3 — traçabilité (validé le 2026-07-17)

- **Vérification manuelle humaine** : 4 annotations sur 4 contrôlées exactes
  dans les PDF :
  - Solvabilité II p.46 — Article 77
  - Solvabilité II p.7 — recital 62
  - Solvabilité II p.34 — Article 45
  - IFRS 17 page physique 37 — section 1.5 (VFA)
- **Découverte** : `ifrs17.pdf` a 12 pages de garde → page imprimée =
  `metadata["page"] - 11`. `solva2.pdf` : aucun décalage.
- **Correctif à prévoir (phase 5)** : afficher `page_label` au lieu de
  `page` dans les citations, pour que la vérification humaine tombe juste
  au premier clic.

## 6. Limites connues

- **Q8 (provisions techniques)** : le volet Solvabilité II n'est jamais
  couvert par la réponse (voir section 2) — considéré comme un vrai échec
  partiel malgré le PASS sur mots-clés.
- **"Q2-bornes" (MCR entre 25 % et 45 % du SCR)** : le chunk contenant la
  réponse littérale (Art. 129) est au rang réel ~1300/2626 — hors de
  portée de tout pool de retrieval testé (dense top20, BM25 top20,
  RRF 70/30, avec ou sans reranking). Diagnostiqué comme un problème de
  divergence de vocabulaire, pas un problème de tri. Piste non tentée :
  contextual retrieval ou query expansion.
- **619/2626 chunks** contiennent encore un espace inséré au milieu d'un
  mot (ex. "assuran ce"), sans césure ni marqueur `\xad` — artefact de
  justification du texte PDF, non corrigeable par regex (nécessiterait un
  correcteur lexical). Distinct du bug de césure de fin de ligne, corrigé
  le 2026-07-17.

## 7. Écart juge 3B vs 70B

Testé le 2026-07-17 sur le pipeline réel (même prompt, retrieval dense
k=5), 3 questions, `llama3.2:3b` via Ollama, `temperature=0`.

**Verdict : 1/3 correct.**

- Q1 "Qu'est-ce que la CSM selon IFRS 17 ?" (23,6s) → cite
  [IFRS 17 — page 27] mais **invente l'acronyme** : "CSM (Cash Shortfall
  Measure)" au lieu de Contractual Service Margin.
- Q2 "Quel est le taux de TVA des croissants ?" (2,5s) → refus correct :
  "Je ne trouve pas cette information dans les documents fournis."
- Q3 "Comment IFRS 17 définit-il le SCR ?" (10,7s) → **ne corrige pas** la
  fausse prémisse (règle 3 du prompt), invente une définition et
  l'attribue à "[IFRS 17 — page 89]" alors que le SCR est un concept
  Solvabilité II.

Le 3B invente avec la même confiance apparente qu'une réponse correcte sur
les deux questions qui demandaient de la précision factuelle — jugé
inutilisable comme juge d'évaluation. `llm="ollama"` n'a pas été intégré
dans `rag.py`. Reste utilisable pour un smoke test rapide du pipeline.
