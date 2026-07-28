# DECISIONS.md

## Décision 001 — Stratégie de découpage par article
Date : 2026-07-25

CONTEXTE
Le texte de Solvabilité II contient 1874 occurrences de "Article + numéro",
mais la plupart ne sont PAS le début d'un article : ce sont des références
("article 47, paragraphe 2") ou des tables de correspondance en annexe
("Article 47 Article 158"). Exemple : "Article 47" apparaît 4 fois, dont
une seule est l'article réel (page 34).

DÉCISION
Découper le texte en articles en ne retenant comme début d'article que les
occurrences qui remplissent ces critères :
- "Article" avec A majuscule, suivi d'un numéro
- suivi d'un titre (texte en majuscules, ex. "Audit interne")
- puis d'un début de corps (souvent "1.")
- PAS suivi immédiatement d'un autre "Article" (= table)
- PAS en minuscule "article" (= référence)

ALTERNATIVES ÉCARTÉES
- Découpage à 512 caractères : rejeté, c'est ce qui a fait échouer
  l'ancien projet (l'article 129 se retrouvait au rang 1287).
- Prendre toute occurrence de "Article N" : rejeté, 3 sur 4 sont des
  références ou des tables, pas des articles réels.

COMMENT ON SAURA SI C'ÉTAIT BON
Les articles de Solvabilité II sont numérotés de 1 à ~310 de façon
séquentielle. Le découpage est validé si les articles détectés
forment une suite quasi complète de 1 à ~310, SANS grandes lacunes
(ex. sauter de 45 à 48 = 3 articles perdus) et SANS doublons (un même
numéro détecté deux fois = une référence ou une table prise à tort
pour un article). On imprimera la liste des numéros détectés et on
vérifiera la continuité.

RÉSULTAT (validé) : 312 articles détectés (= le nombre réel), 0
lacune sur 1..312, 0 doublon. Bornes trouvées automatiquement :
sommaire jusqu'à page 17, annexes à partir de page 126. Exemples
vérifiés : Art. 45, 47, 77, 129 corrects.

## Décision 002 — Bornes de page et "Article premier"
CONTEXTE : le texte contient 3 zones — sommaire (pages 0-16),
corps réel (17-125), annexes (126+). Sommaire et annexes contiennent
des "Article N" qui ne sont pas de vrais articles.
DÉCISION : ne retenir que les articles détectés entre la fin du
sommaire (détectée par la première séquence de 5 numéros
consécutifs) et le début des annexes (détecté par "ANNEXE VI" suivi
de "PARTIE" en majuscules). Gérer "Article premier"/"Article 1er"
par un motif dédié pour l'article 1.
RÉSULTAT : 312/312, propre.

## Décision 003 — Changement de source PDF → HTML EUR-Lex
CONTEXTE : le PDF produisait 142 titres cassés sur 312, des pieds de
page mélangés au corps, et 619 segments avec espaces internes.
DÉCISION : abandonner le PDF, utiliser le HTML structuré officiel
d'EUR-Lex (CELEX 32009L0138, FR). Citation par numéro d'article (la
source HTML n'a pas de pages).
RÉSULTAT : 312 articles, 0 titre cassé, 0 pied de page.
NOTE : version 2009 originale ; à confirmer avec le cabinet s'ils
veulent la version consolidée (Omnibus II 2014).

## Décision 004 — Choix du modèle d'embedding : BGE-M3

CONTEXTE
Comparaison BGE-M3 vs e5-large sur notre golden set
(18 questions validées manuellement sur le texte), retrieval seul,
métriques Recall@5, Recall@1, MRR. Voir data/comparaison_modeles.md.

RÉSULTAT MESURÉ
- Recall@5 : BGE-M3 18/18 (1.000) vs e5 15/18 (0.833)
- Recall@1 : BGE-M3 14/18 (0.778) vs e5 11/18 (0.611)
- MRR : BGE-M3 0.880 vs e5 0.704
BGE-M3 gagne sur les 3 métriques. Mémoire/vitesse quasi identiques
(~2,1 Go VRAM, ~25 s d'encodage des 312 articles sur RTX 3050).

DÉCISION
Adopter BAAI/bge-m3 (mode dense) comme modèle d'embedding, chargé en
safetensors (via miroir Shitao/bge-m3) pour contourner proprement la
restriction CVE-2025-32434 sans toucher à torch/transformers.

ALTERNATIVES ÉCARTÉES (pour l'instant)
- e5-large : bon mais 3 questions ratées complètement (top 5).
- Qwen3-Embedding-8B : meilleur sur MTEB 2026 mais ~5 Go en Q4,
  NE TIENT PAS dans les 4 Go de la RTX 3050. À TESTER PLUS TARD sur
  Kaggle Cloud si BGE-M3 se révèle insuffisant.
- Qwen3-Embedding-0.6B : candidat local non encore testé, à essayer
  si besoin.

COMMENT ON SAURA SI C'ÉTAIT BON
Confirmer sur un golden set plus large (~50 questions). Si BGE-M3
décroche sous 90% de Recall@5 à cette échelle, réévaluer Qwen3.

## Décision 005 — Fournisseur LLM : Mistral

CONTEXTE : Groq (100K tokens/jour, trop petit + clé expirée),
Cerebras (1M/jour mais 402 billing), Gemini (quotas réduits +
training). Besoin d'un fournisseur stable à gros quota pour le
développement.

DÉCISION : Mistral (1 milliard tokens/mois gratuit, entreprise
française — pertinent pour un texte réglementaire français,
compatible OpenAI SDK). Code rendu agnostique du fournisseur
(base_url + model paramétrables) pour rebasculer en une ligne.

NOTE : tier gratuit implique opt-in entraînement des données —
acceptable en développement (corpus public Solvabilité II), à
revoir avant tout usage de documents clients.

## Décision 006 — Résolution d'acronymes (capacité agentique 1)

CONTEXTE : les questions posées avec un sigle seul (SCR, MCR, ORSA,
PT, VaR) échouaient au retrieval car le texte emploie la forme
longue.

DÉCISION : dictionnaire fixe d'acronymes ; expand_query ajoute la
forme longue avant l'encodage BGE-M3.

RÉSULTAT MESURÉ (data/golden_acronymes.jsonl) : Recall@5 0.625 →
1.000, MRR 0.379 → 0.775. 3 questions totalement ratées (ORSA, PT,
VaR) toutes récupérées. Zéro dégradation.

## Décision 007 — Détection d'ambiguïté (capacité agentique 3)

CONTEXTE : deux méthodes comparées pour détecter une question trop
vague avant retrieval — méthode A (1 appel LLM juge CLAIRE/AMBIGUE)
et méthode B (règle sur la dispersion des scores de retrieval,
sans LLM). Sur 10 questions (data/golden_ambiguite.jsonl), les deux
obtiennent 9/10, mais se trompent sur des cas différents.

DÉCISION : retenir la méthode A (LLM juge). Choisie pour sa
robustesse sur des formulations nouvelles : le seuil de la méthode B
(0,075) était calibré sur l'échantillon de test et ne garantit pas
de généraliser, alors que A s'adapte nativement sans recalibration.
Coût accepté : 1 (voire 2, si clarification) appel LLM supplémentaire
par question ambiguë.

INTÉGRATION : fonction clarifier(question) dans rag.py, appelée en
tout premier dans poser_question (avant expansion d'acronymes et
retrieval) si clarify=True. Question AMBIGUË → retourne
{"type": "clarification", "message": ...} sans retrieval ni
génération. clarify=False (défaut) : comportement inchangé.

## Décision 008 — Fournisseur LLM : Gemini 2.5 Flash (à la place de Mistral)

CONTEXTE : le pipeline conversationnel (app.py) fait jusqu'à 3 appels
LLM par question (reformulation contextuelle + clarification +
génération), ce qui saturait rapidement le tier gratuit Mistral
(429 Rate limit fréquents, backoff nécessaire, tests ralentis de
plusieurs minutes).

DÉCISION : basculer sur Gemini, limites bien plus larges (1500
requêtes/jour). Endpoint compatible OpenAI utilisé directement
(base_url="https://generativelanguage.googleapis.com/v1beta/openai/"),
donc le SDK OpenAI existant est conservé tel quel — pas besoin du
SDK natif google-genai. Code rendu agnostique via un paramètre
provider="gemini"|"mistral"|"groq"|"cerebras" (dictionnaire PROVIDERS
dans rag.py) ; aucune config existante supprimée.

NOTE TECHNIQUE : le modèle "gemini-2.5-flash" mentionné initialement
renvoie 404 ("no longer available to new users") ; remplacé par
l'alias stable "gemini-flash-latest". Par ailleurs, Gemini consomme
une partie du budget max_tokens en raisonnement interne caché, même
sur des prompts triviaux (~150 tokens de réflexion avant "Bonjour").
Aucun moyen documenté de désactiver ce comportement via l'endpoint
OpenAI-compatible (reasoning_effort et extra_body google.thinking_config
testés, tous deux rejetés en 400) — compensé en fixant des max_tokens
généreux (2000 pour les appels de classification, 4096 pour les
réponses substantielles).

RÉSULTAT : voir tests dans resultat.md.

## Décision 009 — Fallback automatique Gemini → Mistral

CONTEXTE : même avec les limites larges de Gemini (1500 req/jour),
un 429 (ou une clé invalide 401/402) sur le provider par défaut ne
doit pas bloquer tout le système alors qu'un second fournisseur
fonctionnel (Mistral) est déjà configuré.

DÉCISION : fonction unifiée appel_llm(prompt, taille) dans rag.py.
Essaie FALLBACK_ORDER = ["gemini", "mistral"] dans l'ordre. Sur
429/401/402, bascule automatiquement sur le provider suivant pour
CETTE requête (pas de mémorisation d'un changement permanent). Si
Mistral échoue aussi, erreur claire remontée à l'appelant — pas de
3e fallback (Groq exclu : clé expirée, non retenu), pas de boucle.
_juger_retrieval, clarifier et poser_question appellent tous
appel_llm() sans se soucier du provider actif ; max_tokens résolu en
interne par provider (dict MAX_TOKENS_COURT/MAX_TOKENS_LONG, car
Gemini a besoin de plus de marge que Mistral — voir Décision 008).

COMPORTEMENT : la bascule est silencieuse côté utilisateur final
(app.py appelle avec verbose=False, aucune erreur affichée dans le
chat) ; elle n'est visible que dans les logs quand verbose=True
(ligne "[fallback] gemini indisponible -> bascule sur mistral").

## Décision 010 — Hybrid retrieval : résultat non concluant

Sur golden_set actuel (18 questions) : Recall@5 identique (17/18),
MRR dégradé (0.71 vs 0.82). MAIS l'échantillon est trop petit pour
trancher définitivement (un seul cas — id 9 vs id 15 — inverse le
résultat). DÉCISION : mode="dense" reste le défaut pour l'instant,
le code hybrid est conservé. Ce test sera REFAIT sur un golden set
élargi (~50 questions) avant toute décision finale.

## Décision 011 — Correction des fausses prémisses numériques (Phase 1)

Règle 5 ajoutée au prompt : corriger un chiffre faux avec citation
plutôt que refuser, si le sujet existe dans les articles.

RÉSULTAT : 2/3 cas testés corrigent correctement (99,9%→99,5%,
horizon 5 ans→1 an). 1 échec (MCR bornes 25-45%) dû à un problème
de retrieval (Article 129 absent du top 5 sur cette formulation),
pas à la règle elle-même — le système refuse plutôt que d'inventer,
comportement sûr. Confirme aussi que le fallback Gemini→Mistral
(Décision 009) fonctionne en conditions réelles (429 non simulé).

## Décision 012 — Ajout de Groq en 3e fallback (nouvelle clé)

CONTEXTE : l'ancienne clé Groq était expirée (401), donc exclue de
la chaîne de fallback (Décision 009 : Gemini→Mistral seulement).
Une nouvelle clé GROQ_API_KEY a été fournie.

VÉRIFICATION : nouvelle clé testée isolément (1 appel simple sur
llama-3.3-70b-versatile) avant intégration — fonctionne.

DÉCISION : ajouter Groq comme 3e provider dans FALLBACK_ORDER.
Ordre final : Gemini → Mistral → Groq. Si Gemini ET Mistral échouent
(codes 400/401/402/403/429), appel_llm() essaie Groq avant de
remonter une erreur finale à l'appelant. Aucun changement de
comportement visible pour l'utilisateur — la logique de bascule
(Décision 009) reste identique, seule la liste de providers
s'allonge.

## Décision 013 — Correctif de forme sur la règle de correction (Décision 011)

CONTEXTE : le test du cas 99,9%→99,5% (Décision 011/012) montrait un
contenu correct (bonne valeur, bonnes citations) mais une forme
trompeuse : la réponse démarrait par la phrase de refus exacte avant
de se corriger dans la phrase suivante — un utilisateur lisant juste
la première ligne serait induit en erreur.

DÉCISION : préciser explicitement dans la règle de correction du
prompt : "Si tu corriges une valeur, ne commence JAMAIS ta réponse
par la phrase de refus. Commence directement par la correction, ex :
'Le SCR est calibré à 99,5 %, et non 99,9 % [Article X].'"

RÉSULTAT : voir test dans resultat.md.

## Décision 014 — Golden set final (phase actuelle)

46 questions, 30 articles distincts couverts. Répartition : SCR
(101-127) bien couverte (5 questions sur l'article central 101),
gouvernance/reporting/acquisitions couverts, provisions techniques
couvertes. LIMITE IDENTIFIÉE : MCR (articles 128-131) sous-représenté
(1 seule question sur 129), alors que c'est une zone historiquement
difficile au retrieval (bornes 25-45%).

Selon la littérature (30 questions = seuil minimal, 50 = confiance
directionnelle, 100+ = fiabilité statistique), 46 est suffisant pour
les décisions structurantes déjà prises (choix BGE-M3, rejet hybrid,
choix Gemini) mais insuffisant pour détecter des écarts fins (<5%).

DÉCISION : golden set gelé à 46 pour cette phase. Extension à
prévoir si le projet continue (cible 100 questions).

## Décision 015 — Hybrid retrieval : confirmation finale (rejeté comme défaut)

Testé sur 3 échelles (18, 50 questions) : jamais de gain net.
Sur 50 questions : Recall@5 43→44 (+1), MRR 0.73→0.68 (dégradé).
Corrige 3/4 échecs sur l'article 129 (MCR) mais casse 3 questions qui
réussissaient en dense (id 15, 25, 44) + dégrade le rang de 7 autres.
DÉCISION FINALE : mode="dense" reste le défaut de production.

PISTE FUTURE (non implémentée) : bascule hybrid CIBLÉE par type de
question plutôt que globale — hybrid semble specifiquement efficace
sur les questions portant sur des bornes/seuils/pourcentages (cas
MCR). À explorer : détection automatique de ce type de question
avant de choisir dense ou hybrid.

RÉSULTAT FINAL DU PROJET :
- Recall@5 dense : 43/50 (86%)
- Citation correcte : 43/50 (86%)
- 0 échec de génération pure (100% des articles retrouvés sont bien cités)
- Limite connue et documentée : Article 129 (MCR), 4/7 échecs, formulations
  éloignées du texte source

## Décision 016 — Auto-évaluation du retrieval (self-eval) : rejetée

CONTEXTE : capacité agentique testée en parallèle de l'hybrid retrieval —
avant génération, un appel LLM juge si les articles retrouvés suffisent
pour répondre (_juger_retrieval) ; si non, relance une recherche avec
une requête reformulée par ce même appel. Paramètre self_eval=True/False
dans poser_question.

RÉSULTAT MESURÉ : sur le golden set (18 questions à l'époque du test),
citation correcte identique : 16/18 avec self_eval=False, 16/18 avec
self_eval=True — même échec sur les mêmes 2 questions dans les deux cas.
Coût : ~2x le temps de réponse (1 appel LLM supplémentaire par question,
sans compter la relance éventuelle du retrieval).

DÉCISION : rejetée comme défaut. self_eval=False (comportement simple)
reste le défaut de poser_question. Le code (_juger_retrieval, paramètre
self_eval) est conservé mais non documenté ni testé plus avant faute de
gain mesuré. Cette entrée corrige une lacune : le test avait été exécuté
mais jamais formalisé en décision au moment où il a été fait.
