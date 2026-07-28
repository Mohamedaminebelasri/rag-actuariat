# Intégration de la détection d'ambiguïté (Décision 007)

Méthode A (LLM juge) intégrée dans `rag.py` via `clarifier(question)` et le
paramètre `poser_question(..., clarify=True)`. Appelée en premier dans le
pipeline, avant expansion d'acronymes et retrieval.

## Test de confirmation (3 questions)

| Question | Statut | Résultat |
|---|---|---|
| "Comment calcule-t-on le MCR ?" | CLAIRE | Réponse normale, cite [Article 129] |
| "Quel est le minimum ?" | AMBIGUË | Clarification : *"Souhaitez-vous connaître le capital de solvabilité requis (SCR) minimum, le minimum de fonds propres éligibles (MCR), ou un autre seuil spécifique lié à Solvabilité II ?"* |
| "Qu'est-ce que l'ORSA ?" | CLAIRE | Réponse normale, cite [Article 45] |

Comportement conforme à l'attendu : les questions claires passent par le
flux normal (retrieval + génération), la question ambiguë déclenche une
clarification sans aucun retrieval ni génération.

# Interface Streamlit (app.py)

`app.py` créé : interface conversationnelle réutilisant `rag.py`
(`poser_question`, BGE-M3, Mistral, expand acronymes, clarify). Modèle et
index chargés une seule fois via `@st.cache_resource`. Historique en
`st.session_state`, reformulation contextuelle (1 appel Mistral avant chaque
question, sur les 5 derniers échanges max) avant clarify → expand → retrieval
→ génération.

## Test de lancement

`streamlit run app.py --server.headless true` :
- Serveur démarré sans erreur ni traceback.
- `curl http://localhost:8501` → HTTP 200.
- `curl http://localhost:8501/_stcore/health` → `ok`.

L'UI charge correctement. Serveur de test arrêté après vérification.

# Bascule LLM Mistral → Gemini (Décision 008)

**Méthode d'accès retenue : (a) endpoint compatible OpenAI de Gemini**
(`base_url="https://generativelanguage.googleapis.com/v1beta/openai/"`),
SDK OpenAI existant conservé tel quel. Deux ajustements nécessaires :
- `gemini-2.5-flash` renvoie 404 ("no longer available to new users")
  → remplacé par l'alias stable `gemini-flash-latest`.
- Gemini consomme une partie de `max_tokens` en raisonnement interne caché
  (~150 tokens avant "Bonjour" sur un test trivial) → compensé en fixant
  `max_tokens=2000` (classification) et `4096` (réponses substantielles).

Code agnostique via `provider="gemini"|"mistral"|"groq"|"cerebras"`
(dictionnaire `PROVIDERS` dans `rag.py`) ; aucune config existante supprimée.

## Test des 4 questions (provider="gemini")

| Question | Attendu | Résultat | Statut |
|---|---|---|---|
| "Comment calcule-t-on le MCR ?" | cite [Article 129] | Cite [Article 129] (×6) + [Article 166], réponse détaillée et correcte | ✅ PASS |
| "Comment calcule-t-on le SCR inversé ?" | REFUS (concept inventé) | "Je ne trouve pas cette information dans les articles fournis." | ✅ PASS |
| "Pourquoi le SCR est calibré à 99,9% ?" | correction (99,5%) | "Je ne trouve pas cette information dans les articles fournis." | ⚠️ **PAS l'attendu** |
| "C'est qui Donald Trump ?" | REFUS | "Je ne trouve pas cette information dans les articles fournis." | ✅ PASS |

**Aucune erreur 429 sur les 4 questions** (temps de réponse 3-20s, contre des
minutes d'attente en backoff avec Mistral).

### Point d'attention — Q3

Le refus sur Q3 n'est **pas un problème de retrieval** : l'Article 101
("Calcul du capital de solvabilité requis", qui contient le vrai taux de
calibration à 99,5 %) était bien remonté en top 5 (vérifié en verbose). Le
prompt actuel n'a que deux comportements possibles — citer, ou refuser avec
la phrase fixe — sans règle pour corriger une prémisse fausse à partir du
contexte récupéré. C'est un défaut de conception du prompt, préexistant et
indépendant de la bascule vers Gemini (le même comportement serait probable
avec Mistral sur le même prompt). Non corrigé ici, hors périmètre de cette
tâche.

# Fallback automatique Gemini → Mistral (Décision 009)

Fonction unifiée `appel_llm(prompt, taille)` dans `rag.py`. Essaie
`FALLBACK_ORDER = ["gemini", "mistral"]` dans l'ordre ; `_juger_retrieval`,
`clarifier` et `poser_question` appellent tous `appel_llm()` sans se soucier
du provider actif. `app.py` mis à jour pour utiliser `appel_llm()` au lieu
d'un appel client direct.

## Test de bascule (panne Gemini simulée)

**Premier essai raté, corrigé** : la détection initiale ne cherchait que les
codes 429/401/402 dans le texte de l'erreur. En simulant une clé Gemini
invalide, l'API a en réalité renvoyé un **400** ("Please pass a valid API
key") — non couvert, donc pas de bascule, crash à la place. Corrigé en
détectant sur `status_code` de l'exception (plus robuste qu'un texte) et en
élargissant l'ensemble à `{400, 401, 402, 403, 429}`.

Après correction :
```
[appel_llm] échec sur gemini (status=400) : Error code: 400 - ... 'Please pass a valid API key' ...
[fallback] gemini indisponible -> bascule sur mistral
RÉPONSE : Le calcul du minimum de capital requis (MCR) est défini à
l'Article 129 de la directive Solvabilité II. ... [Article 129, paragraphe 2] ...
```

**Vérification** : réponse obtenue malgré la panne Gemini = **OUI**, contient
`[Article 129]` = **True**. Aucune exception remontée à l'appelant ; en mode
`verbose=False` (comme utilisé par `app.py`), la bascule serait totalement
invisible côté utilisateur — seule la réponse finale, correcte, apparaît.

# Retrieval hybride dense + BM25 (EN TEST — pas encore validé)

`retrieval_hybride(question, k)` ajouté dans `rag.py` : BM25 (rank_bm25) sur
`titre + corps`, fusion RRF avec le dense (top20 chacun, poids 70% dense /
30% BM25). Paramètre `mode="dense"|"hybrid"` dans `poser_question` (défaut
`"dense"`, comportement actuel inchangé). Retrieval seul testé sur les 18
questions du golden set principal, aucun appel LLM.

## Tableau (rang dense vs hybrid)

| id | question (30c) | attendu | dense | hybrid |
|---|---|---|---|---|
| 1 | Combien de temps les autorités | 58 | 2 | 3 |
| 2 | Que se passe-t-il si le régula | 58 | 2 | 2 |
| 3 | Quels critères examine-t-on po | 59 | 1 | 1 |
| 4 | Comment évalue-t-on le risque | 59 | 1 | 1 |
| 5 | Quelles obligations quand un a | 60 | 1 | 1 |
| 6 | Un assureur doit-il déclarer l | 61 | 1 | 4 |
| 7 | Une autorité peut-elle transme | 70 | 1 | 1 |
| 8 | Quel est le rôle du commissair | 72 | 1 | 1 |
| 9 | Le commissaire aux comptes doi | 72 | absent | 5 |
| 10 | Une compagnie peut-elle faire | 73 | 1 | 2 |
| 11 | Comment séparer la gestion vie | 74 | 1 | 2 |
| 12 | Comment valorise-t-on les acti | 75 | 1 | 1 |
| 13 | Pourquoi une compagnie doit-el | 76 | 2 | 2 |
| 14 | Que représente la valeur des p | 76 | 1 | 1 |
| 15 | Comment calcule-t-on les provi | 77 | 3 | absent |
| 16 | Sur quoi se base le calcul de | 77 | 1 | 1 |
| 17 | Faut-il tenir compte de l'infl | 78 | 1 | 1 |
| 18 | Comment traiter les garanties | 79 | 1 | 1 |

## Métriques (18 questions)

| Métrique | dense | hybrid |
|---|---|---|
| Recall@5 | 17/18 (0.944) | 17/18 (0.944) |
| MRR | 0.8241 | 0.7102 |

**Constat** : Recall@5 identique, mais MRR nettement moins bon en hybrid
(0.710 vs 0.824). L'hybride corrige un échec (id 9, absent → rang 5) mais en
casse un autre (id 15, rang 3 → absent) et dégrade le rang de plusieurs
questions déjà bien classées en dense (id 1, 6, 10, 11). **Pas de gain net
sur ce golden set** — le dense reste meilleur en l'état. `mode="dense"` reste
le défaut, comme prévu ; l'hybride n'est pas validé pour remplacer quoi que
ce soit.

**Décision 010** : résultat non concluant, échantillon trop petit pour
trancher (un seul cas inverse le résultat). `mode="dense"` reste le défaut,
le code hybrid est conservé, à refaire sur un golden set élargi (~50
questions) avant décision finale.

# Phase 1 — Correction de prémisse numérique fausse (règle 5 du prompt)

Règle 5 ajoutée à `PROMPT_TEMPLATE` dans `rag.py` : si la question contient
un chiffre/pourcentage/seuil inexact et que les articles fournis donnent la
valeur correcte, corriger explicitement (au lieu de refuser), avec citation.
Prime sur la règle de refus (info absente).

## Test sur les 3 cas connus

| Cas | Attendu | Résultat | Statut |
|---|---|---|---|
| SCR calibré à 99,9 % (réel : 99,5 %) | Correction citée | "Le pourcentage de 99,9 % mentionné... est inexact. Le SCR est en réalité calibré... 99,5 %... [Article 101]" + [Article 104] | ✅ PASS |
| MCR plafonné à 60 % du SCR (réel : 25-45 %) | Correction citée | Refus — "Je ne trouve pas cette information..." | ⚠️ ÉCHEC |
| SCR calibré sur 5 ans (réel : 1 an) | Correction citée | "Le SCR n'est pas calibré sur un horizon de 5 ans, mais sur un horizon d'un an. [Article 101(3)]" + citation directe du texte | ✅ PASS |

**2/3 réussissent.** Diagnostic de l'échec (vérifié en verbose) : **ce n'est
pas un problème de règle 5, mais de retrieval** — l'Article 129 (qui contient
les vraies bornes 25 %-45 %) n'était pas dans le top 5 pour cette formulation
précise ("Le MCR est-il plafonné à 60 % du SCR ?"). Le modèle a reçu les
Articles 166, 98, 101, 131, 303, aucun ne donnant la borne explicite — il a
donc correctement refusé plutôt que d'inventer une correction sans preuve
dans son contexte. La règle 5 fonctionne bien quand le bon article est
présent (cas 1 et 3) ; le cas 2 est une limite de retrieval, pas de prompt.

Bonus constaté en cours de route : ce diagnostic a déclenché un vrai 429
Gemini (pas simulé) — le fallback automatique vers Mistral (Décision 009) a
fonctionné en conditions réelles, sans intervention.

# Ajout de Groq en 3e fallback (Décision 012)

Nouvelle clé `GROQ_API_KEY` testée isolément (1 appel simple) avant
intégration — fonctionne. `FALLBACK_ORDER = ["gemini", "mistral", "groq"]`
dans `rag.py`, `model="llama-3.3-70b-versatile"`. Aucun changement de
comportement visible : même logique de bascule (Décision 009), une entrée
de plus dans la liste.

## Test des 3 questions habituelles

| Question | Attendu | Résultat | Statut |
|---|---|---|---|
| "Comment calcule-t-on le minimum de capital requis ?" | cite [Article 129] | Cite [Article 129] à répétition, réponse complète et correcte | ✅ PASS |
| "Quel est le taux de TVA sur les croissants ?" | REFUS | "Je ne trouve pas cette information dans les articles fournis." | ✅ PASS |
| "Pourquoi le SCR est calibré à 99,9% ?" | correction citée (99,5%) | Corrige bien en 99,5% avec [Article 101, paragraphe 3] + [Article 104, paragraphe 4]… **mais la réponse commence quand même par la phrase de refus exacte** avant de se corriger elle-même dans la phrase suivante | ⚠️ PASS avec réserve |

**2/3 propres, 1/3 correct sur le fond mais maladroit dans la forme** : la
réponse au cas 99,9% contient la bonne correction et les bonnes citations,
mais démarre par "Je ne trouve pas cette information dans les articles
fournis." avant de se contredire immédiatement en donnant la vraie valeur.
Un utilisateur qui ne lit que la première phrase serait induit en erreur.
Le contenu factuel est correct (donc pas un échec de la règle 5 en soi),
mais la formulation mériterait d'être resserrée — à surveiller, pas corrigé
dans le cadre de cette tâche.

# Correctif de forme (Décision 013)

Règle de correction du prompt précisée : "Si tu corriges une valeur, ne
commence JAMAIS ta réponse par la phrase de refus. Commence directement par
la correction, ex : 'Le SCR est calibré à 99,5 %, et non 99,9 % [Article X].'"

## Re-test du cas 99,9% sur les 3 providers (appels individuels forcés)

| Provider | Réponse | Commence par refus ? | Statut |
|---|---|---|---|
| Gemini | ERREUR — 429 quota épuisé (`generativelanguage.googleapis.com`, limite **20 requêtes/jour** pour `gemini-3.6-flash`, l'alias réel derrière `gemini-flash-latest`) | N/A, pas de réponse obtenue | ⚠️ Non testable directement |
| Mistral | "Le SCR est calibré à **99,5 %**, et non 99,9 % [Article 101, paragraphe 3]." + citation directe du texte | **Non** | ✅ PASS |
| Groq | "Le SCR est calibré à 99,5 %, et non 99,9 % [Article 101]." | **Non** | ✅ PASS |

**Correctif validé sur Mistral et Groq** — les deux commencent directement
par la correction, plus de phrase de refus en tête. Gemini n'a pas pu être
testé isolément (quota journalier réellement épuisé, pas simulé) ; en usage
normal (`poser_question`, sans forcer un provider unique), ce même 429
aurait déclenché la bascule automatique vers Mistral (Décision 009), qui est
confirmé fonctionnel avec le correctif.

**Point notable hors périmètre** : la limite Gemini observée ici (20
requêtes/jour sur `gemini-3.6-flash`) est très inférieure aux 1500/jour
supposés en Décision 008. À vérifier si c'est spécifique à ce modèle précis
ou au compte — pourrait remettre en question la pertinence de Gemini comme
provider par défaut si confirmé à cette échelle.

# Évaluation finale — golden set complet (50 questions)

`src/evaluate.py` corrigé (utilisait encore `poser_question(..., model=...)`,
paramètre supprimé lors du refactor Décision 009 — remplacé par le fallback
interne `appel_llm`). Exécuté sur les 50 questions, retrieval BGE-M3
`mode="dense"`, fallback Gemini→Mistral→Groq actif. Écriture incrémentale
dans `data/eval_final_50.md`.

## Métriques finales (50/50 traitées)

| Métrique | Valeur |
|---|---|
| Recall@5 (retrieval) | 43/50 (0.860) |
| Citation correcte (génération) | 43/50 (0.860) |
| MRR (retrieval) | 0.7307 |

## Échecs (7) — article attendu non cité

- id 9 : "Le commissaire aux comptes doit-il signaler une violation du SCR au régulateur ?" (Art. 72, retrieval absent)
- id 20 : "Le MCR est-il plafonné à 60% du SCR ?" (Art. 129, retrieval absent)
- id 29 : "L'article sur les acquisitions qualifiées traite-t-il du calcul du capital de solvabilité requis ?" (Art. 57, retrieval absent)
- id 46 : "À quelle fréquence les données du modèle interne doivent-elles être mises à jour ?" (Art. 121, retrieval absent)
- id 47 : "Entre quelles bornes le minimum de capital requis doit-il se situer par rapport au SCR ?" (Art. 129, retrieval absent — cité [101, 166] à la place)
- id 48 : "Le MCR peut-il descendre en dessous d'un montant absolu minimum, même si 25% du SCR est plus bas ?" (Art. 129, retrieval absent)
- id 50 : "Le MCR est-il calculé selon la même formule standard complexe que le SCR ?" (Art. 129, retrieval absent — cité [103, 166] à la place)

**Constat notable** : les 7 échecs sont TOUS des échecs de retrieval (0
échec de génération pure — quand l'article est retrouvé, il est cité).
**4 des 7 échecs (20, 47, 48, 50) portent sur l'Article 129 (MCR)** — malgré
l'ajout ciblé de 5 questions dessus en Décision 014 pour corriger ce point
faible identifié, 4 sur 5 échouent encore au retrieval. Confirme que c'est
une vraie limite de retrieval sur cet article, pas un artefact du golden set
précédent.

# Hybrid vs dense sur les 50 questions (retrieval seul)

## Tableau global

| Métrique | dense | hybrid |
|---|---|---|
| Recall@5 | 43/50 (0.860) | **44/50 (0.880)** |
| MRR | **0.7307** | 0.6773 |

Hybrid gagne +1 en Recall@5, mais perd sur MRR (0.68 vs 0.73) — même profil
que sur le golden set à 18 questions : hybrid récupère des échecs complets
mais dégrade le rang de questions qui marchaient déjà bien.

## Focus — 7 échecs connus du dense

| id | question | attendu | dense | hybrid |
|---|---|---|---|---|
| 9 | Commissaire aux comptes / SCR | 72 | absent | **5** ✅ corrigé |
| 20 | MCR plafonné à 60% du SCR | 129 | absent | absent ❌ toujours en échec |
| 29 | Acquisitions qualifiées vs calcul SCR | 57 | absent | absent ❌ toujours en échec |
| 46 | Fréquence mise à jour modèle interne | 121 | absent | **4** ✅ corrigé |
| 47 | Bornes MCR/SCR | 129 | absent | **3** ✅ corrigé |
| 48 | Plancher absolu MCR | 129 | absent | **2** ✅ corrigé |
| 50 | MCR formule linéaire vs SCR | 129 | absent | absent ❌ toujours en échec |

**4/7 corrigés par hybrid, dont 3 des 4 échecs sur l'Article 129 (MCR)** —
c'est un gain réel et ciblé sur le point faible identifié en Décision 014.
3 échecs persistent (20, 29, 50), dont un 4e cas MCR (id 50).

## Dégradations — hybrid fait moins bien que dense (10 questions)

| id | question | dense → hybrid |
|---|---|---|
| 1 | Délai d'évaluation d'une acquisition | 2 → 3 |
| 6 | Déclaration changement actionnariat | 1 → 4 |
| 10 | Vie et non-vie simultanément | 1 → 2 |
| 11 | Séparer gestion vie/non-vie | 1 → 2 |
| 15 | Calcul des provisions techniques | 3 → **absent** |
| 25 | Approbation du rapport de solvabilité | 1 → **absent** |
| 26 | Rapport de solvabilité semestriel | 1 → 2 |
| 34 | 6 risques minimums du SCR | 1 → 2 |
| 44 | Modèle interne, retour formule standard | 3 → **absent** |
| 45 | Non-conformité modèle interne | 1 → 2 |

**3 nouvelles pertes totales** (15, 25, 44 : succès en dense → absent en
hybrid) compensent presque les 4 gains — d'où le +1 net en Recall@5 seulement
(4 gagnés − 3 perdus = +1). Les 7 autres dégradations restent dans le top 5
mais avec un rang moins bon.

## Verdict

**Toujours pas de gain net clair.** Hybrid corrige bien 3 des 4 cas MCR
identifiés comme faibles, mais dégrade 10 questions au total (dont 3 échecs
complets nouveaux) et fait baisser le MRR global. Sur 50 questions, le signal
est plus net qu'à 18 (Décision 010) mais reste mitigé : gain ciblé sur MCR,
coût diffus ailleurs. `mode="dense"` reste le défaut ; à envisager
uniquement une bascule ciblée par sujet (ex. hybrid seulement pour les
questions contenant "MCR") plutôt qu'un remplacement global.
