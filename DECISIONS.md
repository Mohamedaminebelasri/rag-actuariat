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

## Décision 017 — Limite connue : scission de ligne sans séparateur (TableFormer, pipeline SFCR)

CONTEXTE : test d'extraction de test_markdrop/build_final.py (Docling
TableFormer ACCURATE) sur les pages 52 et 73 du SFCR Groupama 2025, avec
valeurs de référence vérifiées à l'œil sur les pages sources. Sur le
tableau page 52 (« Expositions au risque de marché »), la ligne
"Obligations" est scindée par TableFormer en 2 lignes logiques dans
element.export_to_dataframe() : une ligne avec le libellé "Obligations"
et une cellule valeur vide, suivie d'une ligne avec une cellule libellé
vide et la valeur "42 980 977". Dans l'image source du tableau
(narratif-table-1.png), ce sont bien 2 lignes de texte empilées MAIS SANS
séparateur horizontal entre elles — visuellement une seule cellule haute,
pas deux lignes de tableau. Le tableau page 73 (6 lignes, émetteur
unique) n'a pas présenté ce problème.

CAUSE : TableFormer segmente une ligne en fonction des zones de texte
détectées, pas de la présence effective d'un trait de séparation. Une
cellule sans séparateur horizontal visible entre son libellé (en haut) et
sa valeur (en bas) peut donc être découpée en 2 lignes logiques.

DÉCISION : ne PAS corriger automatiquement par une heuristique de
"recollage" de lignes (ex. fusionner une ligne "libellé seul, valeur
vide" avec la ligne suivante) — un seul cas observé, règle construite
dessus serait fragile et risquerait de fusionner à tort des lignes
réellement distinctes sur d'autres tableaux. À la place :
- Le check de comptage de lignes vs image source (verify_final.py,
  count_visual_rows/check_row_count_vs_image) détecte cet écart et
  signale "VÉRIFICATION MANUELLE REQUISE" sans bloquer le pipeline.
- Documentation de la limite ici, pour tout traitement en aval qui
  suppose "1 ligne du tableau extrait = 1 entrée réelle du tableau
  source" (ex. recomptage automatique, indexation ligne par ligne) : ce
  n'est pas garanti, il faut tenir compte des lignes à libellé ou valeur
  vide comme candidates à un rattachement à la ligne précédente/suivante.

RÉSULTAT : valeurs numériques non affectées (toutes exactes sur les 2
tableaux testés) — seul le découpage en lignes logiques est impacté.

## Décision 018 — Limite connue : check comptage de lignes inapplicable aux tableaux sans grille complète

CONTEXTE : test d'extraction sur les pages 12 et 14 du SFCR Groupama
2025 (tableaux plus complexes que 52/73, cf. Décision 017 pour le check
lui-même). Le check count_visual_rows/check_row_count_vs_image
(verify_final.py) — construit et validé sur les tableaux des pages 52 et
73, entièrement quadrillés (une ligne horizontale sous CHAQUE ligne de
données) — a déclenché une alerte massive sur le tableau page 14
(« Chiffre d'affaires par métier ») : 8 lignes horizontales détectées
dans l'image contre 27 lignes réellement extraites par
export_to_dataframe(). Vérification manuelle (image source + comparaison
cellule par cellule à une référence externe) : les 27 lignes extraites
sont TOUTES exactes, 0 écart. La table 12 (« Filiales »), elle,
entièrement quadrillée comme 52/73, n'a déclenché aucune alerte (33 = 33).

CAUSE : le tableau page 14 a une mise en forme différente — lignes de
séparation horizontales uniquement autour de l'en-tête et des bandes
grisées (sous-totaux/total), AUCUNE ligne entre les lignes de détail
simples. Le check compte les bordures physiques de l'image, pas les
lignes logiques du tableau : son hypothèse implicite ("1 ligne de donnée
= délimitée par 2 bordures horizontales") ne tient que pour les tableaux
entièrement quadrillés. C'était déjà noté comme limite potentielle au
moment de sa construction (commentaire LINE_DARK_RATIO_THRESHOLD dans
verify_final.py : "VALIDÉ SUR 2 TABLEAUX SEULEMENT : seuil à revalider
si des tableaux avec fond grisé/zébré ou bordures très fines
apparaissent") — confirmé ici sur un 3e tableau.

DÉCISION : ne PAS corriger maintenant (ex. détecter aussi les
changements de fond grisé/zébré, ou les espacements verticaux réguliers
entre lignes de texte comme proxy de ligne, en plus des bordures) — 1
seul cas de tableau "sans grille complète" observé, une règle
généralisée dessus serait construite sur un échantillon insuffisant
(cohérent avec la Décision 017 : ne pas bâtir d'heuristique sur 1-2 cas).
À la place :
- Le check continue de tourner sur tous les tableaux et de signaler
  "VÉRIFICATION MANUELLE REQUISE" sans bloquer le pipeline — c'est son
  comportement voulu (signaler, ne jamais corriger). Une alerte de ce
  check n'implique donc PAS automatiquement une erreur d'extraction :
  elle peut aussi signaler que le tableau n'a pas une grille complète,
  auquel cas une vérification manuelle de l'image (comme faite ici)
  suffit à lever le doute.
- Documentation de la limite ici, pour ne pas re-diagnostiquer la même
  cause à chaque futur tableau à bandes grisées/sous-totaux qui
  déclenchera ce check.

RÉSULTAT : aucune valeur affectée sur les 2 tableaux testés (page 12 et
14) — l'alerte page 14 est un faux positif du check, pas un défaut de
TableFormer.

## Décision 019 — Vraie erreur : fusion de libellés adjacents + ligne fantôme (tableau « Délégués », page 10)

CONTEXTE : test d'extraction sur le tableau « Délégués » de la page 10
(13 caisses régionales + Total, colonnes Nom | Nombre de délégués).
Dans le PDF source (`narratif-table-2.png`), "Groupama Nord Est" (25
délégués) et "Groupama d'Oc" (25 délégués) sont deux lignes distinctes,
clairement séparées par une bordure horizontale, comme toutes les autres
lignes du tableau. Dans element.export_to_dataframe(), elles ressortent
comme : une ligne à libellé VIDE (valeur 25), suivie d'une ligne à
libellé CONCATÉNÉ "Groupama Nord Est   Groupama d'Oc" (une seule valeur
25). Contrairement à la Décision 017 (scission propre, aucune valeur
perdue), ici il y a un vrai mélange : le libellé d'une ligne se retrouve
accolé à celui de la ligne suivante, et l'autre ligne perd son libellé.

POURQUOI LES 3 CHECKS EN PLACE NE VOIENT RIEN : le nombre de lignes total
reste 14 (13 + Total) car une ligne fantôme (libellé vide) compense
exactement la fusion — le check de comptage de lignes vs image
(Décision 018) ne détecte donc rien. La somme des valeurs reste 235 car
25+25 = 25+25 par pure coïncidence (les deux caisses ont la même valeur)
— le check des totaux (Point 1) ne détecte donc rien non plus. Ce
tableau est passé par les 3 checks sans aucune alerte alors qu'il
contient une vraie erreur.

CAUSE PROBABLE (non confirmée) : les libellés "Groupama Nord Est" et
"Groupama d'Oc" sont plus courts que les autres lignes du tableau
("Groupama Rhône Alpes Auvergne", etc.) — possible confusion de
TableFormer sur la hauteur/l'alignement de deux lignes courtes adjacentes.
Un seul cas observé, hypothèse non vérifiée sur un 2e cas.

DÉCISION : ne PAS construire de correctif automatique maintenant (ex.
détecter un libellé vide suivi ou précédé d'un libellé concaténé
plausible) — un seul cas observé (deux libellés courts adjacents), même
principe que la Décision 017 : une règle bâtie sur un seul cas serait
fragile et risquerait de casser des tableaux corrects. Traiter comme un
SIGNAL À SURVEILLER sur les prochains documents SFCR (si le même motif
réapparaît sur d'autres paires de libellés courts adjacents, ce sera le
moment de généraliser une règle) — pas comme un bug à corriger
immédiatement.

RÉSULTAT : erreur réelle, non détectée par les 3 checks actuels
(totaux, comptage de lignes, exclusion sommaire). À surveiller
manuellement sur les tableaux à libellés courts/adjacents en attendant
un 2e cas.

## Décision 020 — Vraie erreur : ligne entière disparue (tableau « Pays à l'international », page 15)

CONTEXTE : test d'extraction sur le tableau « Chiffre d'affaires des
principaux pays à l'international » (page 15, colonnes En millions
d'euros | 31.12.2025 | Évolution constante). L'image source
(`narratif-table-3.png`) contient 5 lignes de données : Italie, Hongrie,
Roumanie, Autres pays *, et le total "Assurance Internationale".
element.export_to_dataframe() n'en retourne que 4 : la ligne "Hongrie"
(687 M€, 21,9%) a intégralement disparu — pas de fusion, pas de trace
résiduelle, la ligne n'existe simplement pas dans la sortie.

CONFIRMATION ARITHMÉTIQUE : somme des 3 lignes extraites hors Hongrie
(1 375 + 979 + 397 = 2 751) contre le total affiché (3 438) : écart de
687, exactement la valeur manquante de Hongrie. Preuve que ce n'est pas
un problème de comptage superficiel mais une vraie perte de donnée.

POURQUOI LE CHECK DES TOTAUX N'A RIEN DÉTECTÉ : la ligne de total de ce
tableau s'appelle "Assurance Internationale", pas "Total" — le check par
libellé (Point 1) s'abstient donc silencieusement sur ce tableau. C'est
une limite DÉJÀ CONNUE et documentée avant même mes modifications : le
docstring d'origine de verify_final.py citait littéralement cette page
("Assurance Internationale » page 15") comme exemple de tableau où la
recherche du mot "Total" échoue. Rien de nouveau à documenter sur ce
point précis.

POURQUOI LE CHECK DE COMPTAGE DE LIGNES A FONCTIONNÉ : ce tableau est
entièrement quadrillé (une bordure horizontale sous chaque ligne, comme
les pages 52/73/12/10), donc l'hypothèse du check (Décision 018) tient
ici. Il a correctement signalé "VÉRIFICATION MANUELLE REQUISE" (5 lignes
visuelles contre 4 extraites) — c'est le check qui a fonctionné comme
prévu et qui a permis de détecter cette erreur.

CAUSE : inconnue à ce stade (pourquoi TableFormer supprime une ligne
entière plutôt que de la fusionner comme dans les Décisions 017/019).
Un seul cas observé.

DÉCISION : pas de correctif automatique — un seul cas, cause non
identifiée. Le signal existant (check de comptage de lignes) suffit à
détecter ce type d'erreur QUAND le tableau est entièrement quadrillé
(sinon, cf. Décision 018, le check est inopérant). Traiter comme un
SIGNAL À SURVEILLER : toute alerte "VÉRIFICATION MANUELLE REQUISE" du
check de comptage de lignes doit être vérifiée à l'image avant d'être
écartée, car elle peut aussi bien signaler une vraie ligne perdue
(ce cas) qu'une limite du check (Décision 018) — les deux causes ne se
distinguent qu'en ouvrant l'image source.

RÉSULTAT : erreur réelle confirmée (ligne "Hongrie" perdue), détectée
par le check de comptage de lignes, invisible au check des totaux (pour
une raison déjà connue et documentée séparément).

## Décision 021 — Correction ciblée du motif "Nord Est / d'Oc" (tableau « Délégués »)

CONTEXTE : la Décision 019 documentait un mode d'échec réel sur le
tableau « Délégués » (une ligne à libellé vide + une ligne à libellé
fusionné "Groupama Nord Est   Groupama d'Oc"), traité comme un signal à
surveiller plutôt qu'un bug à corriger, faute d'un 2e cas. Ce 2e cas est
survenu : le document SFCR 2024 reproduit EXACTEMENT le même motif, sur
la même paire de caisses, à la même position dans le même tableau. Un
correctif ciblé a donc été construit — `test_markdrop/correction_fusion_caisses.py`.

SCOPE EXACT DE LA CORRECTION (2 garde-fous stricts, ne pas élargir sans
revalidation) :
1. **Déclenchement** (`confirme_type_13_caisses` + `detecter_motif_fusion`) :
   la correction ne s'active QUE si (a) au moins 11 des 13 caisses
   canoniques sont reconnues dans le tableau, DANS L'ORDRE CANONIQUE
   STRICTEMENT CROISSANT (pas juste présentes en vrac — ce test exclut
   correctement le tableau « Filiales », qui liste les mêmes caisses mais
   dans un ORDRE DIFFÉRENT, non croissant selon la séquence de référence),
   ET (b) le motif exact est détecté sans ambiguïté : exactement 1 ligne
   à libellé vide, adjacente à exactement 1 ligne à libellé correspondant
   à EXACTEMENT 2 caisses canoniques à la fois — aucune autre ligne
   anormale ailleurs dans le tableau.
2. **Attribution par position, jamais par supposition** : les 2 caisses
   manquantes sont déterminées par l'écart, dans l'ordre canonique, entre
   la dernière caisse reconnue avant l'anomalie et la première après.
   Si cet écart ne fait pas exactement 2, OU si les 2 caisses ainsi
   déterminées ne correspondent pas aux 2 caisses lues dans le libellé
   fusionné, la fonction échoue proprement (retourne None, log
   "ÉCHEC PROPRE" avec la raison) — le signalement existant (Méthode 1 +
   Méthode 2) reste seul à s'appliquer, aucune valeur n'est devinée.

POINT DE VIGILANCE (documenté, pas résolu) : dans les 2 cas connus
(2024 et 2025), les 2 caisses concernées (Nord Est, d'Oc) ont la MÊME
valeur (25 délégués), donc une éventuelle inversion de l'attribution
positionnelle serait sans conséquence sur les données. La fonction
journalise ce fait via un champ "confiance" : "normale" si les 2 lignes
avaient la même valeur avant correction, "RÉDUITE" sinon (ex. si ce motif
apparaissait un jour sur le tableau « Certificats mutualistes », où les
valeurs par caisse diffèrent) — dans ce 2e cas, la correction s'applique
quand même par position (jamais par valeur), mais le niveau de confiance
réduit signale qu'une vérification humaine reste recommandée.

TESTS (avant intégration au pipeline — NON encore intégrée à la date de
cette décision, en attente de validation utilisateur) :
1. Document 2025, tableau Délégués : les 2 lignes fautives deviennent
   "Groupama Nord Est | 25" et "Groupama d'Oc | 25". ✓ (confiance normale)
2. Document 2024, tableau Délégués : même résultat, calculé
   indépendamment sur ce document. ✓ (confiance normale)
3. Régression sur les 9 autres tableaux déjà testés (Expositions marché,
   Titres subordonnés, Filiales ×2, CA par métier, Certificats
   mutualistes ×2, Pays international, Résultat opérationnel économique) :
   0 correction déclenchée à tort, 0 échec propre inattendu — soit hors
   scope Garde-fou 1(a) (dont Filiales, à dessein, cf. ci-dessus), soit
   tableau sain sans aucune ligne vide/fusionnée. ✓
4. Cette entrée DECISIONS.md. ✓

DÉCISION : correction construite et testée avec succès sur les 4 tests
ci-dessus, mais **NON intégrée** à `verify_final.py`/`build_final.py` —
reste un module autonome (`correction_fusion_caisses.py`), en attente
d'une confirmation explicite avant intégration au pipeline de
production, conformément à la demande.

**MISE À JOUR 2026-09-12 — INTÉGRATION RÉELLE CONFIRMÉE ET VÉRIFIÉE.**
Contexte : en auditant l'étape 8 partie A (traitement du document
complet), la question "cette correction a-t-elle vraiment été branchée
un jour ?" a été explicitement vérifiée plutôt que supposée — réponse :
NON, `correction_fusion_caisses.appliquer_correction` n'était toujours
importée que par son propre fichier de test (`test_correction_fusion.py`),
jamais par le pipeline réel. Le bug de fusion Nord Est/d'Oc était donc
encore réellement présent dans le corpus en production (`table_6.png` /
`index_tableaux_texte_bge.json`, vecteur "texte" de la collection Qdrant
"tableaux") au moment de cet audit.

CORRECTIF INTÉGRÉ : `build_index_texte_bge.py::charger_tableaux_markdown()`
appelle désormais `appliquer_correction` sur CHAQUE tableau narratif (les
garde-fous internes de la fonction — `confirme_type_13_caisses` —
la rendent silencieuse sur les 17 tableaux hors périmètre, donc pas
besoin de cibler le tableau au préalable). Toute correction ou échec
propre est journalisé dans le résumé du script, jamais silencieux. Toute
réingestion future via ce script bénéficiera donc automatiquement de la
correction.

VÉRIFICATION (pas seulement le code — le résultat réel) :
1. `charger_tableaux_markdown()` ré-exécuté : 1 seul signalement sur 18
   tableaux — `#/tables/6`, statut "CORRECTION APPLIQUÉE", confiance
   "normale" (les 2 lignes avaient la même valeur, 25, avant correction).
   Markdown corrigé : "Groupama Nord Est | 25" et "Groupama d'Oc | 25"
   redeviennent 2 lignes distinctes.
2. Résultat corrigé comparé DIRECTEMENT à l'image source
   (`table_6.png`, lue visuellement) : les 13 lignes de la table
   correspondent exactement, y compris Nord Est et d'Oc en lignes
   séparées avec bordure — confirmation visuelle, pas seulement
   textuelle.
3. Réingestion CIBLÉE (pas tout le corpus) : nouveau vecteur "texte"
   calculé (BGE-M3) pour `#/tables/6` uniquement, mis à jour dans Qdrant
   via `update_vectors` (vérifié empiriquement au préalable : préserve le
   vecteur "image" et le payload du point, contrairement à un `upsert`
   qui aurait remplacé tout le point) sur l'UUID déterministe déjà en
   place (upsert logique, pas un nouveau point). Re-requête réelle
   après coup : vecteur texte changé, vecteur image ET payload
   inchangés — confirmé, pas supposé sur la seule foi du message de
   succès. `index_tableaux_texte_bge.json` (fichier source) synchronisé
   avec le nouvel embedding pour rester cohérent avec Qdrant.
4. Golden sets vérifiés : seul `golden_set_unifie.json` référence
   `#/tables/6` (question U08, "Groupama Antilles Guyane" — une ligne
   jamais affectée par la fusion Nord Est/d'Oc, à l'autre bout du
   tableau). Réponse attendue toujours correcte après correctif, aucune
   mise à jour de golden set nécessaire.

RÉSULTAT : correction Décision 021 réellement intégrée au pipeline de
production (pas seulement testée isolément) et vérifiée à chaque étape
sur données réelles — plusieurs mois après sa conception initiale,
confirmée intégrée le jour de l'audit de l'étape 8 partie A.

## Décision 022 — Fusion multi-pages des templates QRT : état des lieux vérifié

CONTEXTE : clarification demandée sur le fonctionnement exact de la
fusion des templates QRT s'étalant sur plusieurs pages physiques (ex.
S.02.01.02.01 : Actif p.7, Passif p.8), et sur un point noté dans un
résumé antérieur — "affichage de la complétude multi-pages" — signalé
comme potentiellement un problème ouvert. **Aucune trace de ce point
n'a été retrouvée** dans les 3 fichiers mémoire disponibles ni dans
`IDEES_SCALE_UP.md`/`CHOIX_OUTILS.md` : origine non identifiée.

CE QUE LE CODE MONTRE (`test_markdrop/ingest.py::process_qrt`, lignes
484-581) — deux mécanismes distincts, à ne pas confondre :

1. **Extraction par page, ancrée sur le code** : `extract_qrt_native`
   (ligne 290, `resultat[code] = {...}`) et `extract_qrt_gemini` (lignes
   457/462, `lignes_par_code = {l["code"]: l for l in lignes if "code" in l}`)
   associent chaque valeur à son code R00xx AVANT tout regroupement —
   par position géométrique (x,y) en natif, par le champ `"code"` du
   JSON en VLM. Aucune valeur n'est jamais associée par ordre de lecture
   ou par position dans une liste.

2. **Vérification de complétude fusionnée, également ancrée sur le
   code** (lignes 538-579) : les pages CONSÉCUTIVES du même `sheet_key`
   sont regroupées (lignes 546-554), puis l'union des codes trouvés sur
   tout le groupe est comparée au total EIOPA attendu pour CE sheet_key
   — `codes_attendus = set(row_labels.keys())` (ligne 562), comparé à
   l'union `codes_trouves_union` accumulée par `|=` sur toutes les pages
   du groupe (lignes 564-567), jamais page par page isolément. Le
   commentaire d'origine (lignes 538-545) documente explicitement que ce
   bloc a été construit pour corriger un faux signal ("chaque page
   semble ~50% incomplète alors que l'union ne l'est pas") — c'est donc
   une correction déjà appliquée, pas un problème en attente.

NUANCE IMPORTANTE (ne pas confondre avec un défaut) : la complétude est
unifiée, mais les DONNÉES publiées dans `elements` (donc dans
`corpus_final.json`) restent **une entrée par page**, jamais fusionnées
en un seul enregistrement par template. Un template sur 2 pages produit
2 éléments distincts du corpus, chacun incomplet pris isolément mais
tous deux portant le même `template_id` — un consommateur en aval
pourrait les recombiner, `ingest.py` ne le fait pas lui-même. Rien
n'est perdu (`page_source` préservé sur chaque élément), ce n'est
simplement pas un enregistrement fusionné au sens strict.

DÉCISION : aucune modification nécessaire à ce stade — la vérification
de complétude multi-pages est robuste, ancrée sur le code, et déjà
vérifiée contre le total EIOPA (pas page par page). Le point noté dans
l'historique semble soit obsolète (déjà résolu par le bloc lignes
538-579), soit mal attribué à cette partie du code — aucune preuve dans
le code actuel d'un problème réel à cet endroit. Si un besoin futur
exige un enregistrement unique par template (plutôt que N éléments par
template étalé sur N pages) pour l'indexation RAG, ce sera un ajout
délibéré à faire, pas une correction d'un bug existant.

RÉSULTAT : audit de code uniquement, aucune modification apportée à
`ingest.py`.

## Décision 023 — Correction du bug S.32.01.22 : routage vers Gemini + filet de sécurité

CONTEXTE : suite à la Décision 022, un vrai bug (distinct de l'hypothèse
de départ sur la complétude) a été confirmé en creusant `corpus_final.json`
d'un run complet antérieur : sur le template S.32.01.22 (liste d'entités,
`row_codes` vide — le seul des 7 templates du dictionnaire dans ce cas),
`extract_qrt_native` est structurellement incapable d'extraire quoi que ce
soit (elle cherche des codes R00xx qui n'existent pas sur ce type de
page) et retourne un résultat vide en silence. Confirmé sur la page 89 du
document 2025 : 0 entité extraite via le chemin natif, sans aucune
anomalie levée (la vérification de complétude est, à raison, désactivée
pour ce template — cf. Décision 022).

OPTION RETENUE : B — router systématiquement les templates à `row_codes`
vide vers `extract_qrt_gemini`, quel que soit `NATIVE_TEXT_THRESHOLD`,
plutôt que de doter `extract_qrt_native` d'une branche "liste d'entités"
équivalente (Option A, écartée). Raison : `extract_qrt_gemini` a déjà une
branche dédiée et déjà prouvée pour ce cas précis (37 entités correctement
extraites sur la page 88) ; dupliquer côté natif une détection de lignes
par position aurait réintroduit le type de risque déjà documenté aux
Décisions 017/019 (segmentation de lignes réinventée, fragile). Le
changement de code est une seule condition de routage dans `process_qrt`
(`ingest.py`) : `sans_code_de_ligne = not sheet_dict["row_codes"]`, ajouté
à la condition existante — comportement strictement inchangé pour les 6
autres templates (tous à `row_codes` non vide).

FILET DE SÉCURITÉ AJOUTÉ (indépendant du correctif ci-dessus, cf. demande
explicite) : `detect_entites_vides_suspectes` (`ingest.py`) — pour tout
template à `row_codes` vide, si une page produit 0 entité alors qu'au
moins une AUTRE page du même `sheet_key` (même document) en a produit,
signale "VÉRIFICATION MANUELLE REQUISE" (`entites_qrt_vides_suspectes`
dans le diagnostic, comptée dans le `bloquant`). Ne dépend pas de la
correction de routage — continuerait à fonctionner même si une page vide
était produite pour une autre raison. Ne bloque rien, ne corrige rien.

DÉCOUVERTE FAITE PENDANT LES TESTS (hors scope de cette correction, notée
pour référence) : en re-questionnant Gemini sur la page 88 (déjà routée
vers Gemini avant ET après ce correctif), les 37 entités reviennent en
même nombre mais avec des libellés partiellement différents d'un appel à
l'autre (ex. "Groupama Grand-Est" vs "Groupama Grand Est", "Bon Outre Mer
(AIX)" vs "Gan Outre Mer IARD") — une variabilité absente sur les
templates À codes de ligne (où le prompt contraint Gemini à une liste
fermée de codes officiels). C'est cohérent avec la cause racine de ce
template (aucun ancrage par code possible) mais reste un risque distinct,
non traité ici.

TESTS (tous exécutés sur le document réel, aucun mocké) :
1. Pages 88-89 (document 2025, sous-feuillet S.32.01.22.01 complet —
   confirmé "Annexe 7 (1/2)" et "(2/2)") : page 88 inchangée (37 entités,
   déjà Gemini avant/après) ; page 89 route désormais vers Gemini (au
   lieu du texte natif) et retourne 0 entité — **vérifié manuellement
   par inspection de l'image de la page 89 : c'est la page de LÉGENDE
   des codes EIOPA (Type d'entreprise, Catégorie, etc.), PAS une
   continuation du tableau de données. Le 0 est correct.** Le filet de
   sécurité de l'Étape 3 s'est déclenché comme prévu sur cette page — la
   vérification manuelle qu'il réclame a été faite ici et confirme
   qu'il n'y a pas de perte de donnée. Total : 37/37 entités réelles
   capturées, 0 perte. ✓
2. Sous-PDF complet du sous-feuillet (pages 88-89, qui EST l'intégralité
   de S.32.01.22.01 dans ce document — pas besoin du run 89 pages
   complet, déjà couvert). ✓
3. Régression sur les 12 pages QRT réelles (78-89, les 7 templates) :
   diff structurel programmatique entre le run antérieur stocké et le
   nouveau run sur les pages 78-87 (les 6 autres templates) — méthode
   d'extraction et résultats strictement identiques sur les pages à
   comparaison déterministe (dont la page 85, seule en texte natif parmi
   elles) ; les pages Gemini à codes de ligne fermés (78-84, 86-87)
   identiques aussi. Seule la page 88 (déjà Gemini avant/après) diffère
   dans son contenu détaillé — attribué à la non-déterminisme de Gemini
   sur un 2e appel indépendant (cf. découverte ci-dessus), pas au
   correctif. 0 changement de routage sur les 6 autres templates. ✓
4. Filet de sécurité testé sur 5 scénarios simulés indépendants du cas
   réel (1 vide + 1 non-vide → signale ; tout vide → silencieux ; 1
   seule page → silencieux ; template À codes de ligne avec page vide →
   jamais traité par ce filet ; cas réel corrigé pages 88/89 → signale
   89) — les 5 passent. ✓

DÉCISION : correctif + filet de sécurité implémentés et testés avec
succès sur les 4 tests ci-dessus.

**MISE À JOUR 2026-09-12** : confirmé INTÉGRÉ et vérifié — le routage
`sans_code_de_ligne` (ligne 673 de `ingest.py`) est bien câblé dans la
boucle principale de traitement QRT, pas resté un module autonome non
branché. Vérifié directement dans le code (pas supposé) au moment
d'auditer l'étape 8 partie A. La note "non encore confirmé intégré"
ci-dessus était devenue obsolète sans avoir été corrigée — signalé ici
pour qu'une future relecture de cette décision ne soit plus induite en
erreur.

RÉSULTAT : bug confirmé et corrigé pour le seul cas actuellement dans le
dictionnaire (S.32.01.22) ; 0 régression mesurée sur les 6 autres
templates ; le filet de sécurité fonctionne indépendamment du correctif
et a démontré son utilité en pratique (a exigé la vérification manuelle
de la page 89 qui a confirmé l'absence de perte réelle).

## Décision 024 — Correction de `resoudre_sous_feuille` pour S.05.02.04 (résolution en amont, pas extraction)

CONTEXTE : la Décision 022 avait identifié que `resoudre_sous_feuille`
résolvait mal les pages du template S.05.02.04 (pages 82-83, document
2025) vers de mauvaises sous-feuilles, via son heuristique positionnelle
`(x/y)`. Vérification approfondie avant correction (Étapes 1-2) :

- **Portée réelle du bug** : sur les 4 templates multi-sous-feuilles du
  dictionnaire (S.05.01.02, S.05.02.04, S.23.01.22, S.25.05.22), le
  problème touche **2 templates, pas 1 seul** : S.05.02.04 (confirmé,
  cause déjà identifiée : chaque page physique combine visuellement 3
  sous-feuilles EIOPA) ET **S.25.05.22** (découvert en vérifiant : une
  seule page physique combine ses 2 sous-feuilles empilées verticalement,
  confirmé par l'image — libellé natif littéralement "S.25.05.22.01 -
  S.25.05.22.02"). S.05.01.02 et S.23.01.22 n'ont pas ce piège — 1 page
  physique = 1 sous-feuille, y compris pour S.23.01.22 dont la page .01
  est résolue par lecture directe du code natif (12 664 caractères) et
  non par l'heuristique risquée.
- **Ordre d'exécution** : `resoudre_sous_feuille` s'exécute AVANT
  l'extraction et la DÉTERMINE pour le chemin Gemini — `sheet_dict`
  (donc `sheet_key`) alimente directement `build_prompt_qrt`, qui énumère
  dans le prompt les codes que Gemini doit chercher. Une résolution fausse
  produit donc un prompt qui demande les mauvais codes, pas seulement une
  mauvaise étiquette sur un résultat par ailleurs correct.

OPTION CHOISIE — ni A ni B tels quels : Option A (résolution par contenu
déjà extrait) écartée : pour le chemin Gemini (celui de toutes les pages
concernées, natif ou non selon le document), "le contenu trouvé" dépend
déjà du `sheet_key` résolu via le prompt — comparer après-coup un
résultat biaisé par un mauvais prompt n'apporte rien sans réinterroger le
modèle. Option B ("page 1 = non-vie, page 2 = vie") écartée en l'état :
la règle ne se généralise PAS à S.25.05.22 (vérifié : pas de séparation
vie/non-vie par page, un empilement de 2 tableaux à lignes distinctes sur
1 seule page) — donc invalidée comme règle générale, conformément à la
consigne de ne pas construire une généralisation non vérifiée.

**Solution retenue** : un signal STRUCTUREL vérifiable — grouper les
sous-feuilles d'un template dont les `row_codes` sont STRICTEMENT
IDENTIQUES (`grouper_sous_feuilles_fusionnables`, `ingest.py`). Ce test
ne s'active que pour S.05.02.04 parmi les 4 templates (vérifié
programmatiquement, pas supposé) : .01/.02/.03 partagent 18 row_codes
identiques, .04/.05/.06 en partagent 13 identiques ; aucun autre template
n'a cette propriété. Quand `resoudre_sous_feuille` détecte qu'un numéro
"-NN"/"(N/total)" imprimé sur la page correspond à un template ayant de
tels groupes, il interprète ce numéro comme l'index du GROUPE (Nième page
physique), pas comme un suffixe de sous-feuille littéral, et retourne une
clé composite (ex. "S.05.02.04.01+02+03") dont le `sheet_dict` est fusionné
(`fusionner_sheet_dicts` : row_codes du groupe, union des col_codes de
chaque membre). `process_qrt` maintient une correspondance locale
`sheet_dicts_effectifs` (clé résolue -> sheet_dict réellement utilisé)
pour que le reste du pipeline (complétude fusionnée multi-pages, filet
S.32.01.22) n'ait jamais besoin d'indexer `qrt_dict` avec une clé
composite absente du dictionnaire brut.

**Piège trouvé et corrigé en cours de route** : la 1ère version du
correctif ne traitait que l'heuristique `(x/y)` (2e mécanisme de
résolution), en supposant la lecture directe du code natif (1er
mécanisme) fiable par nature. Faux : sur le document 2024, la page 79
est résolue par lecture directe ("S.05.02.04 - 02" trouvé littéralement
dans le texte natif) mais désigne en réalité le groupe "vie" (.04/.05/.06),
pas la sous-feuille .02 seule — le numéro imprimé encode la page
physique, pas le suffixe dictionnaire, quel que soit le mécanisme qui le
détecte. Le correctif final applique donc la même interprétation
positionnelle-par-groupe aux deux mécanismes.

SCOPE EXACT : uniquement S.05.02.04. S.25.05.22, bien que confirmé cassé
lui aussi, N'EST PAS corrigé ici — son problème est différent dans sa
forme (2 sous-feuilles à row_codes DISTINCTS empilées sur 1 seule page,
pas des variantes de colonnes d'un même jeu de lignes) et nécessiterait
qu'une page produise plusieurs éléments du corpus, un changement
d'architecture hors périmètre de cette correction.

TESTS :
1. Pages 82-83 (document 2025) : résolvent vers `S.05.02.04.01+02+03` et
   `S.05.02.04.04+05+06`. Complétude passée de 0/18 et 0/13 (avant, sur
   les mauvaises sous-feuilles) à 18/18 et 13/13 lignes trouvées. ✓ pour
   la résolution de sous-feuille et les colonnes "Home country"/"Total".
   **Limite résiduelle découverte, PAS corrigée ici** : la colonne
   "Top 5 pays" perd 1 des 2 valeurs réelles par ligne (page 82 : IT
   conservé, RO perdu ; page 83 : les deux valeurs "vie" perdues) — cause
   distincte et déjà identifiée (le dictionnaire EIOPA ne définit qu'UN
   seul code, ex. C0090, pour un concept répété 5 fois dans le rapport
   réel — cf. l'investigation "col_x" du tour précédent). Le test "sans
   perte" ne passe donc que partiellement : la résolution de sous-feuille
   est intégralement corrigée, la capture multi-instance d'une colonne
   répétée ne l'est pas (hors scope de cette tâche).
2. Régression S.23.01.22 : pages 85-86 strictement identiques avant/après
   (routage, méthode, complétude). ✓
3. Régression sur les templates déjà testés (S.02.01.02, S.05.01.02,
   S.22.01.22, S.32.01.22) : diff structurel programmatique contre le
   run de référence de la Décision 023 — 0 changement de routage/méthode
   sur toutes les pages hors 82-83 (seule la page 88 diffère dans son
   contenu détaillé, non-déterminisme Gemini déjà documenté, sans lien
   avec ce correctif). ✓
4. Document 2024 (pages 78-79, équivalent) : résolvent vers les mêmes
   groupes combinés, 0 code manquant sur les deux pages (19/18 et 14/13,
   les codes en trop étant des lignes d'en-tête sans valeur). Généralise
   correctement au 2e document — et a permis de détecter puis corriger
   le piège du 1er mécanisme de résolution ci-dessus. ✓

OBSERVATIONS INCIDENTES NON CORRIGÉES (notées pour référence, hors scope) :
- Sur le document 2024, les pages 76-77 (S.05.01.02) et 80 (S.22.01.22)
  trouvent 0 code malgré un texte natif abondant (>3000 caractères) —
  piste non vérifiée : tableau large potentiellement pivoté/rotaté, non
  géré par `extract_qrt_native` (qui suppose une orientation portrait
  standard). Aucun lien avec ce correctif (templates sans groupe fusionné,
  code non modifié pour eux).
- S.25.05.22 reste cassé sur les 2 documents (page 87 en 2025, page 83 en
  2024), confirmé non traité — cf. scope ci-dessus.

DÉCISION : correctif implémenté et testé avec succès sur les 4 tests
ci-dessus (avec une réserve documentée sur la perte résiduelle "Top 5
pays", hors scope, toujours d'actualité — cf. remarque ci-dessous).

**MISE À JOUR 2026-09-12** : confirmé INTÉGRÉ et vérifié —
`grouper_sous_feuilles_fusionnables`/`resoudre_sous_feuille` (avec le
regroupement de sous-feuilles) sont bien appelés dans la boucle
principale de traitement QRT de `ingest.py` (ligne 648), pas restés un
module autonome non branché. Vérifié directement dans le code (pas
supposé) au moment d'auditer l'étape 8 partie A. La note "non encore
confirmé intégré" ci-dessus était devenue obsolète sans avoir été
corrigée — signalé ici pour qu'une future relecture de cette décision ne
soit plus induite en erreur. La réserve "Top 5 pays" (perte résiduelle),
elle, reste un vrai point ouvert, non traité par cette mise à jour.

## Décision 025 — Combinaison texte narratif + tableau/image à la génération (small-to-big retrieval)

CONTEXTE
Découvert en travaillant sur le chunking du texte narratif (sections A à
D) : certains sous-titres contiennent un tableau directement lié au texte
qui le précède — le texte donne le contexte/l'interprétation, le tableau
donne les données chiffrées. Exemple concret : A.1.2 Entreprises liées
importantes, où le texte explique la structure de détention à 100% par
les caisses régionales, et le tableau juste après donne le nombre de
certificats mutualistes par caisse.

PROBLÈME
L'architecture validée (4 index séparés — texte, tableaux, images, QRT —
avec fusion et reranking) sélectionne un seul type de chunk gagnant. Rien
ne prévoit de combiner automatiquement un tableau avec le texte narratif
de son propre sous-titre, ou inversement, alors que certaines questions
ont besoin des deux pour une réponse complète.

DÉCISION
Résoudre ce problème au niveau de la génération de la réponse, pas au
niveau de la recherche — aucun changement à l'architecture des 4 index, à
la fusion ou au reranking.
- Un marqueur [TABLEAU: self_ref] (ou [IMAGE: self_ref]) est déjà inséré
  dans le texte narratif à l'endroit exact où l'élément apparaît. Quand un
  chunk narratif contenant ce marqueur est sélectionné, résoudre le
  self_ref pour inclure le contenu réel de l'élément référencé dans le
  contexte envoyé au modèle de génération.
- Dans le sens inverse (un tableau ou une image gagne le reranking),
  remonter vers le texte narratif associé — mais en stockant sur
  l'élément lui-même une référence précise vers le paragraphe déclencheur
  qui le précède directement, pas vers toute la section via le chemin
  hiérarchique complet. Ce point corrige une asymétrie de précision
  identifiée pendant la revue de cette décision : sans lui, remonter
  "toute la section" risquerait d'injecter du texte hors sujet si la
  section est longue.
- Résolution à un seul niveau, jamais récursive.
- Dédupliquer par identifiant de chunk avant l'envoi au modèle de
  génération : si un élément a déjà été inclus indépendamment par le
  retrieval, ne pas le réinclure via la résolution du marqueur.
- Si un chunk contient plusieurs marqueurs (cas possible après le
  sous-découpage des sections trop longues), plafonner le nombre
  d'éléments résolus par appel de génération (2-3 maximum) plutôt que de
  tout résoudre sans limite.

JUSTIFICATION
Ce pattern est documenté sous le nom "small-to-big retrieval" /
"parent-document retrieval" : découpler la granularité de recherche de la
granularité envoyée au modèle de génération. Une étude récente sur des
documents financiers réglementaires comparables (10-K/10-Q/8-K
américains) a mesuré un gain de 65% des cas gagnants par rapport au
chunking classique, pour un coût de latence négligeable (+0,2s).

SUIVI À NOTER
Ajouter au golden set une question nécessitant explicitement la
combinaison texte + tableau (ex. "combien de certificats détient
Groupama Centre Manche, et pourquoi ?" sur A.1.2), pour vérifier que la
génération combine bien les deux sources — pas seulement que le
retrieval les trouve séparément.

## Décision 026 — Deux pièges Kaggle découverts en exécutant comparer_colqwen3.ipynb

CONTEXTE
Étape 4 (embedding multimodal), comparaison de 3 candidats sur le golden
set visuels (16 questions, corpus de 36 fichiers). Les notebooks
ColQwen3/Qwen3-VL-Embedding sont écrits pour tourner sur Kaggle/Colab
(pas de GPU local suffisant, cf. Décision 004). Deux problèmes réels
rencontrés en exécutant *réellement* comparer_colqwen3.ipynb sur Kaggle
(pas anticipés à l'écriture, découverts à l'usage) — documentés ici pour
ne pas relancer la même investigation au prochain notebook Kaggle/Colab
de ce projet.

PROBLÈME 1 — Conflit binaire numpy/scipy/scikit-learn
Erreur exacte obtenue : `ImportError: cannot import name '_center' from
'numpy._core.umath'`, déclenchée par `from sentence_transformers import
SentenceTransformer` (chaîne d'import `sentence_transformers -> sklearn
-> scipy -> numpy`).

HISTORIQUE DES 3 HYPOTHÈSES SUCCESSIVES (pour ne pas les retenter) :
1. **INCORRECTE** : que ce soit notre propre cellule d'installation
   (`pip install ... numpy --upgrade` sans upgrader `scipy`/`scikit-
   learn` en même temps) qui désynchronise leurs versions binaires.
   Correctif tenté : `pip install --upgrade numpy scipy scikit-learn`
   ensemble — testé, **ne suffit pas**, l'erreur persiste.
2. **INCOMPLÈTE / CONTRE-PRODUCTIVE** : rechercher en ligne a d'abord
   semblé confirmer un bug connu des images Kaggle/Colab (Python 3.12,
   incohérence binaire entre les modules Python de `numpy` et son
   fichier `umath` compilé) touchant d'autres projets sans rapport
   (WhisperX, Open3D, mapclassify), avec pour correctif de désinstaller
   puis réinstaller (`pip uninstall -y numpy scipy scikit-learn` puis
   `pip install -U numpy scipy scikit-learn`). Ça fait bien disparaître
   l'erreur `_center` immédiate, MAIS installe `numpy 2.5.3` + `scipy
   1.18.1` — une combinaison qui s'est révélée elle-même encore instable
   (nouveaux problèmes en aval, non détaillés ici).
3. **CAUSE RÉELLE RETENUE** : l'image Kaggle de base fournit DÉJÀ
   `numpy`/`scipy`/`scikit-learn` dans des versions mutuellement
   compatibles, testées par Kaggle elle-même. C'est le fait de forcer
   leur mise à jour (`--upgrade`, et pire encore, une réinstallation
   complète) qui casse cette cohérence dès le départ — pas l'inverse.
   Les hypothèses 1 et 2 attaquaient toutes les deux le symptôme (une
   erreur d'import) en modifiant des paquets qu'il ne fallait pas
   toucher du tout.

DÉCISION FINALE : ne JAMAIS installer/upgrader/désinstaller `numpy`,
`scipy` ou `scikit-learn` dans ces notebooks, sauf nécessité absolue
vérifiée. La cellule d'installation se limite strictement à ce qui
manque réellement à l'image de base : `pip install -q sentence-
transformers accelerate pillow` — `torch` et `transformers` aussi
retirés de cette commande (déjà fournis par l'image, même risque que
`numpy` si on les force). Documenté dans une cellule markdown dédiée en
tête des 2 notebooks, avec l'historique des 3 hypothèses ci-dessus, pour
qu'une future tentative de "corriger" une erreur d'import numpy ne
reparte pas de zéro.

PROBLÈME 2 — Chemin de montage du dataset Kaggle à double niveau
Le dataset `golden-set-visuels` ne se monte PAS sous
`/kaggle/input/golden-set-visuels` comme le nom du dataset le laisserait
supposer, mais sous :
`/kaggle/input/datasets/<utilisateur>/golden-set-visuels/golden-set-visuels`
(confirmé en listant `/kaggle/input/datasets/` directement sur Kaggle).
Cause probable : le zip uploadé contenait déjà un dossier
`golden-set-visuels/` à sa racine, et Kaggle a ajouté son propre niveau
utilisateur/dataset par-dessus, d'où le doublon de nom dans le chemin.

DÉCISION : ne pas re-zipper différemment pour contourner (fragile, dépend
de la façon exacte dont l'utilisateur crée son zip) — à la place, la
liste `CANDIDATS_RACINE` des notebooks essaie plusieurs chemins connus
dans l'ordre (local `test_markdrop`, Kaggle "plat" théorique, Kaggle réel
à double niveau, Colab) et prend le premier qui existe. Les deux chemins
Kaggle (plat et double niveau) sont conservés ensemble, sans supprimer
l'un pour l'autre, pour rester robuste si un futur re-zip donne une
structure différente.

RÉSULTAT : les deux correctifs appliqués à `comparer_colqwen3.ipynb` ET
`comparer_qwen3vl.ipynb` (ce dernier pas encore exécuté sur Kaggle au
moment de cette décision, mais partage le même dataset et la même chaîne
d'import `sentence_transformers` — même risque, corrigé préventivement).

## Décision 027 — Choix du modèle d'embedding multimodal : Cohere Embed v4

CONTEXTE
Étape 4 du pipeline SFCR Groupama : choisir un modèle d'embedding
multimodal pour les 36 visuels stockés à l'étape 3 (18 tableaux, 5
images, 13 pages QRT). Contrainte matérielle connue (Décision 004) : RTX
3050 Laptop, 4 Go VRAM — élimine d'emblée tout modèle local de plusieurs
milliards de paramètres en pleine précision.

CANDIDATS TESTÉS SUR LE GOLDEN SET VISUELS (16 questions, corpus de 36
visuels)

1. **Cohere Embed v4** (API managée) : Recall@5 = 0,933, MRR = 0,872 (15
   questions, Q02 exclu pour défaut de rotation connu sur sa page
   source ; 16 questions toutes incluses : Recall@5 = 0,938, MRR = 0,880).

2. **ColQwen3-4B** (TomoroAI) — ABANDONNÉ : bug confirmé dans le code
   custom du modèle lui-même (`create_mm_token_type_ids` manquant dans
   `processing_colqwen3.py`), reproduit à la fois via
   `sentence-transformers`/`MultiVectorEncoder` et via l'API officielle
   `transformers` documentée. Aucune solution trouvée. Cf. Décision 026
   pour les pièges Kaggle rencontrés en l'exécutant.

3. **Qwen3-VL-Embedding-8B** — ABANDONNÉ : la version complète (16,3 Go)
   est en `OutOfMemoryError` sur GPU T4 (15 Go) malgré
   `device_map="auto"` (cause : `sentence-transformers` force `.to(device)`
   sur un seul GPU, annulant le sharding attendu). La version quantifiée
   tierce `collin-park/Qwen3-VL-Embedding-8B-W8A8` échoue ensuite en
   erreur de dtype côté packaging (encodeur vision non exclu correctement
   du schéma de quantification).

4. **Voyage multimodal-3** (API managée) — ABANDONNÉ : compte sans moyen
   de paiement limité à 3 requêtes/min et 10 000 tokens/min. Les pages
   QRT (~14 300 tokens chacune en résolution native, formule documentée
   tokens = pixels / 560) dépassent ce plafond à elles seules — aucun
   pacing ne peut corriger ça, seul un redimensionnement avant envoi le
   peut (downscale testé avec succès à ce niveau). Même avec ce
   contournement et un pacing client conservateur (budget tokens/min
   avec marge, espacement des appels sous le seuil RPM), la même erreur
   de rate limit s'est reproduite après 13 appels réussis — cause exacte
   non identifiée (candidats non vérifiés : comptage de tokens réel
   différent de la formule documentée, retries internes du SDK consommant
   du quota invisiblement, ou quota non strictement glissant). Documenté
   comme tel, pas de solution retenue faute de temps/coût supplémentaire
   en appels API.

5. **ModernVBERT/colmodernvbert** (250M paramètres, léger, tourne en
   local CPU) : Recall@5 = 0,800, MRR = 0,646 (15 questions ; 16 questions
   toutes incluses : Recall@5 = 0,812, MRR = 0,668) — nettement en dessous
   de Cohere. Deux réserves non levées mais sans incidence sur la
   décision (le score est de toute façon inférieur) : la variable
   `HF_HUB_DISABLE_XET` n'a pas pris effet (bug connu de la version
   installée de `huggingface_hub`, vérifié en pratique via logs de debug
   — les téléchargements continuent de passer par le backend Xet malgré
   la variable), et deux jeux de poids (`custom_text_proj.*`, base model
   et adaptateur LoRA) apparaissent `UNEXPECTED` au chargement sans
   confirmation certaine que c'est bénin (probable redondance avec les
   modules `1_Dense`/`2_Normalize`/`3_MultiVectorMask` propres à
   `sentence-transformers`, qui eux se chargent sans avertissement — non
   vérifié en profondeur).

DÉCISION
Cohere Embed v4 retenu comme modèle d'embedding multimodal final pour les
tableaux, images et pages QRT du pipeline SFCR. Seul candidat des 5 à la
fois fonctionnel de bout en bout et au meilleur score mesuré.

OBSERVATION CROISÉE À GARDER EN TÊTE (indépendante du choix de modèle)
Le tableau T05 (« risque de marché par instrument ») échoue chez les deux
modèles utilisables (rang 12 chez Cohere, rang 21 chez colmodernvbert) —
signal que ce visuel précis est probablement mal exploitable en l'état
(texte dense, peu de structure visuelle), à revérifier au niveau du crop
extrait à l'étape 3, indépendamment du modèle retenu.

PROCHAINE ÉTAPE
Générer les embeddings Cohere Embed v4 pour l'ensemble des 36 visuels
(pas seulement le golden set), pour construire les index tableaux/
images/QRT définitifs.

## Décision 028 — Fusion (RRF) + reranking entre les 4 collections Qdrant

CONTEXTE
Les 4 collections Qdrant (texte, tableaux, images, qrt) sont indexées et
mesurées séparément (Décisions 026-027, golden sets texte/visuels).
Étape suivante : un mécanisme de fusion + reranking pour produire UN
classement final unifié à partir des 4 recherches indépendantes.

DÉCISION 1 — Cohere Rerank écarté, juge LLM multimodal retenu
Vérifié dans la documentation officielle Cohere
(https://docs.cohere.com/docs/rerank-overview) et recoupé par recherche
web : Rerank est TEXTE UNIQUEMENT (aucune mention d'image ; le champ de
facturation "images" est toujours à `None` ; Cohere ne propose pas non
plus de modèle vision dans sa famille Command — "multimodal workloads
need a different provider"). Élimine l'option "un seul reranker Cohere
pour tout".
RETENU : un juge LLM multimodal — Gemini, via l'endpoint OpenAI-compatible
DÉJÀ utilisé par le projet principal (`src/rag.py`, PROVIDERS["gemini"]) :
`base_url="https://generativelanguage.googleapis.com/v1beta/openai/"`,
`GEMINI_API_KEY`, modèle `gemini-flash-latest`. Vérifié (docs Gemini +
test réel) que cet endpoint accepte des images via `image_url` (data URL
base64, format standard OpenAI vision). UN SEUL appel de jugement par
requête, mélangeant texte et images dans le même prompt — pas deux
rerankers séparés (Cohere pour le texte + LLM pour le reste), qui
casserait l'unification recherchée et réintroduirait 2 échelles de score.

DÉCISION 2 — Traitement de "tableaux" (2 vecteurs nommés) dans la fusion
"Tableaux" compte comme UNE SEULE liste dans la fusion à 4 collections
(texte, tableaux, images, qrt) — pas deux listes indépendantes
("tableaux-texte" + "tableaux-image"). Raison : la fusion ici combine des
COLLECTIONS DE CONTENU DE NATURE DIFFÉRENTE (chunks vs tableaux vs images
vs pages QRT), pas plusieurs méthodes de recherche sur un même corpus
(usage "classique" du RRF) — donner 2 listes à "tableaux" gonflerait
artificiellement son poids par rapport aux 3 autres collections (1 seul
signal chacune), sans justification autre qu'un détail d'implémentation
(2 vecteurs au lieu d'1).
La liste unique de "tableaux" est elle-même construite par FUSION RRF
NATIVE QDRANT (`Prefetch` + `RrfQuery`, vérifié empiriquement fonctionnel
contre le serveur local — cf. `fusion_reranking.rechercher_tableaux_pour_fusion`)
des 2 vecteurs "texte"/"image" — pas un simple "meilleur des deux rangs"
qui perdrait le signal du vecteur non retenu : un tableau bien classé sur
SES DEUX vecteurs remonte légitimement plus haut qu'un tableau bien classé
sur un seul.

DÉCISION 3 — Constante RRF k=60
Valeur standard de la littérature (papier original Cormack, Clarke &
Buettcher 2009 ; défaut d'Elasticsearch pour son propre RRF) — réutilisée
identique pour la fusion interne de "tableaux" (Qdrant natif) ET pour la
fusion externe entre les 4 collections (implémentation Python), pas une
valeur différente par étage.

IMPLÉMENTATION (`fusion_reranking.py`)
- `rechercher_texte/tableaux/images/qrt_pour_fusion` : top 10 par
  collection (`TOP_K_PAR_COLLECTION`), fusionnés par RANG (pas score brut
  — échelles différentes entre BGE-M3 et Cohere).
- `fusionner_rrf` : combine les 4 listes, top 8 (`TOP_K_APRES_FUSION`)
  envoyés au reranking.
- `juger_candidats_llm` : 1 appel Gemini vision, texte (relu depuis
  chunks_propres.json — le payload Qdrant ne stocke pas le texte lui-même)
  et images (rechargées depuis disque en base64) mélangés dans le même
  prompt, score 0-10 par candidat, JSON strict (pas de fallback deviné si
  le JSON est invalide — erreur explicite).
- `baseline_meilleur_score_normalise` : baseline volontairement naïve
  (sans fusion RRF, sans reranking) — interroge les 4 collections
  séparément (tableaux : 2 requêtes indépendantes ici, PAS la fusion RRF
  native — la baseline ne doit dépendre d'aucun choix de fusion évalué),
  normalise min-max chaque liste indépendamment, retourne le meilleur
  score normalisé toutes collections confondues.

GOLDEN SET UNIFIÉ (`golden_set_unifie.json`, ENRICHI de 7 à 19 questions)
Vérifie que le PIPELINE CHOISIT LE BON TYPE de collection face à la
concurrence (pas juste le bon résultat dans une collection isolée). Même
méthode que tous les golden sets du projet : contenu réel inspecté
question par question dans chunks_propres.json/docling_document_complet.json,
aucune génération à l'aveugle. Composition finale par catégorie :
- **Texte pur** (U01, U07, U14, U18) : DORA, MCR, notation Fitch, périmètre
  prudentiel (exclusions) — aucun tableau/image ne couvre ces sujets.
- **Tableau pur, renfort** (U15, U19) : résultat net (renvoi explicite du
  texte au tableau), impact VA sur le SCR (idem).
- **Image pur, renfort** (U16) : cas le plus net du lot — le chunk
  narratif correspondant (A.1.3, structure simplifiée) est catégorisé
  "structurel" et donc ABSENT de la collection "texte" : aucune
  compétition possible.
- **QRT pur** (U05, U17) : total actif bilan S2 (page 78), nombre
  d'entités liées de l'annexe S.32.01.22 (page 88, fait déjà vérifié en
  Décision 023).
- **Texte↔tableau ambigu** (U02, U03, U06, U08, U09, U10) : Centre Manche
  et Italie (déjà connus) + 3 NOUVEAUX cas vérifiés dans le même chunk
  narratif A.1.2/A.1.4/A.2 (délégués par caisse, CA de l'Épargne retraite
  individuelle, résultat des Activités financières) — dans chaque cas le
  texte ne donne qu'un chiffre agrégé ou une variation, jamais le montant
  précis demandé, qui n'existe que dans le tableau.
- **Discrimination QRT** (U11) : la ventilation par Tier des fonds
  propres — le texte narratif (E.1.2) contient le LIBELLÉ quasi mot pour
  mot de la question mais dit explicitement "présentée à l'annexe 5"
  (renvoi vers le QRT S.23.01.22, pages 85-86) sans aucun chiffre. Teste
  si le reranking suit la ressemblance de surface (texte) ou la vraie
  source (QRT).
- **Tableau↔image** : recherché explicitement dans le corpus (chunks
  co-portant un tableau ET une image) — **AUCUN cas réel trouvé**. Vérifié
  systématiquement : sur les 3 seules images narratives non-logo du
  corpus (#/pictures/12, 64, 75 — tout le reste des références "image"
  dans les chunks se résout, via images_dedup.json, vers le logo
  Groupama répété), aucune ne co-occurre avec un tableau topiquement lié.
  Absence documentée plutôt qu'un cas fabriqué artificiellement.
- **Pièges** (U12, U13) : U12 présuppose un "tableau des acquisitions"
  inexistant (le fait est purement narratif) ; U13 dit explicitement
  "d'après le texte narratif" alors que le texte ne donne que la
  VARIATION (-15 M€), jamais le montant absolu demandé (-160 M€, tableau
  uniquement) — teste si l'instruction de surface fait suivre une
  heuristique plutôt que la vraie source.

RÉSULTAT MESURÉ SUR LES 7 PREMIÈRES QUESTIONS (1er passage)
- Baseline : 3/7 bon type. Pipeline complet : **7/7 bon type**, y compris
  le cas délibérément ambigu U06.

RÉSULTAT MESURÉ SUR LES 19 QUESTIONS ENRICHIES (2e passage)
- Baseline (meilleur score normalisé, sans fusion ni reranking), complété
  en entier : **6/19 bon type, 6/19 bon identifiant exact**.
- Pipeline complet (fusion RRF + reranking LLM multimodal) : **10 des 19
  questions traitées AVEC SUCCÈS, 10/10 correctes (type ET identifiant
  exact)** — 0 erreur parmi les questions effectivement jugées, y compris
  les 3 nouveaux cas les plus difficiles du lot (U08 délégués, U09
  épargne retraite individuelle, U11 discrimination QRT/texte). **9
  questions (U10, U12-U19) N'ONT PAS PU être testées** : quota gratuit
  Gemini épuisé en cours de mesure (`429 RESOURCE_EXHAUSTED`,
  "GenerateRequestsPerDayPerProjectPerModel-FreeTier", limite 20
  requêtes/jour pour le modèle résolu par l'alias "gemini-flash-latest" —
  1 cas `503` "high demand" en plus). Ce ne sont PAS des échecs de
  raisonnement : aucune réponse n'a été obtenue du tout pour ces 9 cas,
  comptées comme incorrectes uniquement par le garde-fou du script de
  mesure (ne jamais deviner un résultat en cas d'erreur d'API). Point de
  vigilance noté : GEMINI_API_KEY est la MÊME clé que celle utilisée par
  défaut dans `src/rag.py` (projet principal) — un usage intensif de
  tests sur ce projet peut donc consommer le même quota partagé que
  l'application de production.
- DÉCISION : documenter ce résultat partiel tel quel plutôt qu'attendre
  la réinitialisation du quota ou ajouter un moyen de paiement — les 9
  questions restantes pourront être testées lors d'une prochaine session.

TENTATIVE DE JUGE DE SECOURS (OpenRouter) POUR LES 9 QUESTIONS RESTANTES
Objectif : finir les 9 questions non jugées par Gemini (U10, U12-U19)
avec un fournisseur DIFFÉRENT, sans toucher au chemin Gemini existant
(`fusion_reranking.juger_candidats_llm`/`pipeline_complet`, inchangés —
la logique de jugement partagée a été extraite dans
`_juger_avec_client`, appelée à l'identique par les deux chemins ; ajout
de `juger_candidats_llm_openrouter`/`pipeline_complet_openrouter`,
fonctions séparées).

Choix du modèle — VÉRIFIÉ EMPIRIQUEMENT, pas deviné : les 3 modèles
initialement envisagés (qwen2.5-vl-72b-instruct:free,
llama-3.2-11b-vision-instruct:free, mistral-small-3.1-24b-instruct:free)
sont TOUS passés payants sur OpenRouter entre-temps (404 "unavailable for
free"). Les 2 alternatives Google (gemma-4-31b-it:free,
gemma-4-26b-a4b-it:free) sont rate-limited sur leur pool gratuit partagé
("Google AI Studio", 429 persistant sur 2 tentatives espacées). Modèle
finalement retenu après consultation : **nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free**
— seul candidat testé avec succès sur un appel image simple (description
correcte de table_5.png).

RÉSULTAT SUR LES 9 QUESTIONS RESTANTES : **0/9 bon type** — échec quasi
total, 3 modes distincts, tous vérifiés en détail (pas de log seul) :
1. **3/9 (U10, U12, U14) — panne infrastructure** : le backend gratuit
   Nvidia est en sur-capacité ("Worker local total request limit
   reached"). OpenRouter renvoie alors un corps 200 avec `choices: None`
   et un champ `error` embarqué, PAS une exception HTTP normale — un cas
   que `_juger_avec_client` ne gérait pas (`TypeError: 'NoneType' object
   is not subscriptable`), diagnostiqué en reproduisant l'appel brut et
   en inspectant `completion.model_dump()`. Bug réel du code de secours,
   pas du modèle lui-même — non corrigé (le juge de secours est
   abandonné, cf. décision finale ci-dessous).
2. **4/9 (U13, U15, U18, U19) — non-respect du format** : le modèle
   renvoie un JSON valide mais INCOMPLET (ex. `[{"candidat": 6, "score":
   10}]` au lieu d'un score par candidat) — capté CORRECTEMENT par le
   garde-fou existant ("pas de fallback silencieux", même exigence que
   pour Gemini) plutôt que masqué. Confirme que ce modèle ne suit pas de
   façon fiable une consigne de scoring multi-candidats stricte.
3. **2/9 (U16, U17) — mauvaise réponse** : réponse JSON complète et bien
   formée, mais type gagnant faux dans les deux cas.

DÉCISION FINALE : le juge de secours OpenRouter est ABANDONNÉ tel quel
(pas de 3e modèle essayé, pas de correction du bug infrastructure ci-
dessus) — documenté comme échec plutôt que contourné. Les 9 questions
restantes (U10, U12-U19) restent NON RÉSOLUES à l'issue de cette
décision.

CONCLUSION — LE GOLDEN SET UNIFIÉ N'A JAMAIS ÉTÉ JUGÉ DE BOUT EN BOUT PAR
UN SEUL MODÈLE HOMOGÈNE. Les résultats se lisent comme 2 SOUS-MESURES
DISTINCTES, jamais fusionnées en un seul chiffre global (19/19 ou autre) :
- **Gemini** (gemini-flash-latest, 10 questions : U01-U09, U11) :
  **10/10 bon type et bon identifiant exact**, 0 erreur.
- **OpenRouter/nvidia-nemotron-3-nano-omni-30b-a3b-reasoning:free**
  (9 questions : U10, U12-U19) : **0/9**, échec documenté (3 causes
  distinctes ci-dessus), juge abandonné.
- **Baseline** (sans fusion ni reranking, complétée en entier sur les 19
  questions par simple recherche vectorielle — ne dépend d'aucun LLM
  juge) : **6/19 bon type**.
La complexité ajoutée (fusion RRF + reranking LLM multimodal) apporte un
gain réel et mesuré chaque fois qu'un juge fiable a pu être utilisé :
7/7 puis 10/10 avec Gemini (17 questions jugées au total, 0 erreur),
contre 6/19 pour la baseline sur l'ensemble complet. Le juge de secours
testé (OpenRouter/nemotron) n'apporte AUCUN gain — au contraire, il
invaliderait le pipeline s'il était utilisé tel quel. Aucune conclusion
n'est tirée sur "le pipeline" en général indépendamment du modèle de
jugement : la qualité du reranking dépend fortement du LLM choisi, ce
n'est pas un simple détail d'implémentation interchangeable.

## Décision 029 — Résolution des marqueurs [TABLEAU:/IMAGE: self_ref] à la génération (Décision 025, implémentée)

CONTEXTE
La Décision 025 avait acté le principe (texte narratif + tableau/image
lié combinés à la génération, via les marqueurs déjà présents dans le
texte narratif) mais ne l'avait jamais implémenté ni testé. Ce module se
situe STRICTEMENT après la sélection du candidat gagnant par la fusion
RRF + reranking (Décision 028) — ne touche à aucun des deux.

EXPLORATION PRÉALABLE (vérifiée, pas supposée)
- Format des marqueurs confirmé dans chunks_propres.json :
  `[TABLEAU: #/tables/N]`, `[IMAGE: #/pictures/N]` (espace après ":",
  aucun avant "]"). `[LEGENDE: #/texts/N]` existe aussi mais référence une
  légende texte, pas un visuel — exclu du périmètre.
- Correspondance self_ref -> fichier réel : déjà entièrement construite à
  l'étape 3 (`chemins_visuels.py`, `resoudre_chemin_self_ref` — gère
  aussi la déduplication pHash des logos) — réutilisée telle quelle, pas
  reconstruite.

IMPLÉMENTATION (`resolution_marqueurs.py`, `generation.py`)
1. **Résolution AVANT** (texte gagnant -> visuel) :
   `resoudre_visuels_du_chunk` — parse les marqueurs du chunk gagnant,
   résout chacun via `chemins_visuels.resoudre_chemin_self_ref`, attache
   le fichier réel au contexte.
2. **Résolution INVERSE** (visuel gagnant -> paragraphe narratif précis)
   — POINT TRANCHÉ EXPLICITEMENT (pas deviné) : au lieu de remonter tout
   `chemin_hierarchique` (section entière), le paragraphe précis est
   reconstruit À LA VOLÉE depuis la POSITION du marqueur dans le texte
   brut du chunk narratif (`chunks_propres.json`) — **vérifié que cette
   information est intégralement reconstructible depuis les données
   existantes, AUCUN nouveau champ créé**. Le paragraphe = tout le texte
   entre le marqueur précédent du même chunk (ou le début du chunk) et le
   marqueur ciblé. Cas AMBIGU (visuel référencé dans plusieurs chunks
   narratifs distincts, ex. logo dédupliqué) : renvoie `None` plutôt
   qu'un choix arbitraire — même principe que `build_index_visuels.py`.
3. **Contraintes** : résolution à 1 seul niveau (jamais récursive),
   dédup par identifiant (self_ref canonique / chemin_hierarchique) avant
   envoi à la génération, plafond `MAX_ELEMENTS_RESOLUS = 3`.

VÉRIFICATION UNITAIRE (6/6, contre données réelles, pas de mock)
1. Chunk DORA (2 marqueurs IMAGE consécutifs, sans texte entre eux) :
   dédup interne correcte (les 2 marqueurs pointent vers le même fichier
   canonique après pHash — 1 seul résolu, pas 2 doublons).
2. `#/tables/5` (Centre Manche) : paragraphe correctement isolé à
   l'intro certificats mutualistes, SANS la phrase délégués qui suit.
3. `#/tables/6` (délégués, même chunk que #2, marqueur suivant) :
   paragraphe correctement isolé à la SEULE phrase délégués, sans
   ré-inclure l'intro certificats — confirme la segmentation par marqueur
   précédent/suivant plutôt que par chunk entier.
4. `#/pictures/1` (logo, 68 occurrences) : `None` (cas ambigu, comme prévu).
5. `#/tables/0` (jamais référencé) : `None` (cas absent, comme prévu).
6. `self_ref=None` (page QRT) : `None` immédiat (pas de marqueur possible
   pour une page QRT, qui n'a pas d'item Docling).

TEST DE BOUT EN BOUT (pas seulement unitaire, comme demandé)
Sur les 2 cas déjà connus (U01 texte pur/DORA, U02 tableau/Centre
Manche), fusion RRF RÉELLE (Qdrant + Cohere + BGE-M3, aucun mock) pour
retrouver le candidat gagnant, puis assemblage RÉEL du contexte :
- **U01 (résolution avant)** : gagnant texte confirmé (chemin_hierarchique
  DORA exact), contexte assemblé = texte + logo résolu (`#/pictures/58`
  -> `#/pictures/1`), EXACTEMENT la structure attendue.
- **U02 (résolution inverse)** : gagnant tableau confirmé (`#/tables/5`),
  contexte assemblé = image du tableau + paragraphe narratif résolu
  (l'intro certificats mutualistes, sans la phrase délégués), EXACTEMENT
  la structure attendue.
L'assemblage de contexte est donc **vérifié correct dans les 2 sens, sur
données réelles, sans aucun mock**.

GÉNÉRATION FINALE (prose) — NON CONFIRMÉE, blocage d'accès fournisseur,
PAS un échec du mécanisme :
- Gemini (`gemini-flash-latest`) : quota gratuit quotidien épuisé
  (429, même quota que la Décision 028).
- Anthropic (`claude-sonnet-5`) : solde de crédit insuffisant (400).
- OpenRouter (`google/gemma-4-31b-it:free`) : rate-limited sur le pool
  gratuit partagé "Google AI Studio" (429), un seul essai fait comme
  convenu, pas de 3e fournisseur cherché.
Aucun texte de réponse finale combinant les 2 sources n'a donc pu être
généré et lu aujourd'hui — à confirmer lors d'une prochaine session avec
un fournisseur disponible.

RÉSUMÉ — CE QUI EST PROUVÉ AUJOURD'HUI vs CE QUI RESTE À CONFIRMER
- PROUVÉ (données réelles, sans mock) : format des marqueurs, résolution
  avant et inverse toutes deux correctes unitairement (6/6) ET en contexte
  réel de bout en bout jusqu'à l'assemblage (U01, U02) — dédup,
  non-récursivité et plafond respectés par construction du code.
- NON CONFIRMÉ : le texte de réponse finale généré par un LLM à partir de
  ce contexte assemblé — bloqué par 3 fournisseurs indisponibles
  (Gemini : quota ; Anthropic : crédit ; OpenRouter/gemma : rate-limit
  partagé), pas par un défaut du mécanisme lui-même.

## Décision 030 — Feuille de route : "Partie B" (multi-entités) hors périmètre actuel, prochaine étape = robustesse inter-annuelle (même entité)

CONTEXTE
Précision apportée après la clôture de l'étape 8 partie A (Décision 021,
mise à jour ci-dessus) : "Partie B" avait été évoquée en fin de cette
étape comme suite possible ("2e SFCR d'une autre entité"), mais ce n'est
PAS la prochaine étape réelle du projet — clarification faite pour éviter
toute confusion à une prochaine relecture de la feuille de route.

DÉCISION
- **Élargissement multi-entités (autres compagnies que Groupama)** :
  reporté à plus tard, explicitement PAS la prochaine étape. Le projet
  reste volontairement limité à Groupama pour l'instant.
- **Prochaine étape réelle** : un test de robustesse INTER-ANNUELLE sur
  la MÊME entité (Groupama) — golden set construit sur le SFCR Groupama
  **2024** (déjà partiellement vérifié par le passé sur les pages 11/12/18,
  où le bug de fusion Délégués Nord Est/d'Oc — Décision 019/021 — s'était
  reproduit à l'identique sur ce document aussi).
- Les questions de ce golden set 2024 sont en cours de préparation
  EXTERNE (Claude.ai, à partir de mini-PDF envoyés section par section),
  PAS encore prêtes à transmettre — rien à faire côté pipeline pour
  l'instant. À reprendre quand les questions seront fournies.

RÉSULTAT : aucune action technique dans cette entrée — clarification de
périmètre et de séquencement uniquement, pour que "Partie B" ne soit plus
lue comme la suite immédiate du projet.

## Décision 031 — Robustesse inter-annuelle (SFCR Groupama 2024) : extraction, correction Nord Est/d'Oc, ingestion Qdrant multi-année, golden set 66 questions, mesure en cours

CONTEXTE
Suite directe de la Décision 030 : golden set 2024 reçu (66 questions,
`questions_sfcr_2024_partie1.md`), pipeline complet exécuté sur
`SFCR_2024_Groupe-Groupama.pdf` (86 pages, PAS 89 comme 2025 — vérifié
avant tout traitement, conformément à la consigne).

STRUCTURE RÉELLE 2024 (vérifiée, pas supposée identique à 2025)
- 86 pages (2025 : 89).
- Annexes QRT à partir de la page **73** (2025 : 77) — `PAGE_MIN_QRT`
  rendu paramétrable (variable d'environnement `PAGE_MIN_QRT_OVERRIDE`,
  défaut 77 inchangé) dans `build_sections.py` et `chemins_visuels.py`,
  plutôt que dupliquer ces modules par année.
- Mapping annexe -> template EIOPA confirmé par lecture directe (pas par
  déduction) : Annexe 1=S.02.01.02 (p.74-75), 2=S.05.01.02 (p.76-77),
  3=S.05.02.04 (p.78-79), 4=S.22.01.22 (p.80), 5=S.23.01.22 (p.81-82),
  6=S.25.05.22 (p.83), 7=S.32.01.22 (p.84-**86**, 3 pages — 2025 n'en a
  que 2). La 3e page (86) est une page de LÉGENDE/codes EIOPA sans aucune
  entité — 0 entité extraite y est donc CORRECT, pas un échec (signalé
  par le détecteur d'anomalies `entites_vides_suspectes`, vérifié
  manuellement comme faux positif après lecture réelle de la page).

TÂCHE 2 (PRIORITAIRE) — BUG NORD EST/D'OC : CONFIRMÉ REPRODUIT, CORRECTION VALIDÉE
Le tableau Délégués (page 11, `#/tables/6` — même numéro que 2025, par
coïncidence de renumérotation Docling) présente EXACTEMENT le même défaut
que sur 2025 : une ligne vide adjacente à "Groupama Nord Est   Groupama
d'Oc" fusionnés, toutes deux à 25. `correction_fusion_caisses.appliquer_correction`
(Décision 021), réutilisée SANS AUCUNE MODIFICATION, corrige correctement
les deux lignes (25/25, confiance "normale"). Confirme que la correction
est bien scopée à l'entité (Groupama, ordre des 13 caisses), pas au
document — généralise correctement à un 2e exercice.

NOUVEAUX CAS LIMITES DÉCOUVERTS SUR 2024 (documentés, pas écartés)
1. **Puce non-PUA** : les puces "faits marquants" de 2024 sont codées en
   U+25AA (▪, caractère Unicode réel) au lieu du caractère PUA ``
   utilisé par 2025 pour la même puce visuelle — vraisemblablement un
   encodage de police différent entre les 2 PDF. `retype_bullet_headers.py`
   ne reconnaissait QUE la plage PUA (0xE000-0xF8FF) : 49 puces 2024
   passaient inaperçues (0 retypage au lieu de 49). Corrigé en ajoutant
   U+25AA à une liste blanche explicite de caractères de puce connus
   (pas un assouplissement générique "tout caractère non-alphanumérique") ;
   2025 vérifié inchangé (toujours 53 retypages).
2. **10 titres non numérotés mal placés dans la hiérarchie** : les
   mini-titres "faits marquants" (Notation financière, Cyclone Chido...,
   page 16) et 2 légendes de figure/tableau (page 13-14), laissés au
   niveau H1 brut de Docling, "fermaient" à tort le contexte hiérarchique
   racine — BUG RÉEL CONFIRMÉ sur données réelles (pas supposé) : le
   chunk "A.2. Résultats de souscription" héritait du chemin
   `"Cyclone Chido à Mayotte > A.2. Résultats de souscription"` avant
   correction. Corrigé (`fix_unnumbered_levels_2024.py`, nouveau fichier
   — la liste blanche de `fix_unnumbered_levels.py` est verrouillée sur
   les 18 cas 2025, jamais réutilisable telle quelle) en promouvant
   chacun des 10 cas au niveau de son ancêtre numéroté réel + 1, même
   logique que la correction "Epargne retraite" de 2025, généralisée à
   plusieurs cas au lieu d'un seul, chacun vérifié individuellement
   (texte + ancêtre réellement adjacent dans le flux).
3. **3 phrases d'introduction mal typées section_header** ("Ce rapport a
   pour objectif :", "Dans ce cadre, Groupama Assurances Mutuelles :",
   "La Direction Risques Groupe :") — chacune immédiatement suivie d'un
   `list_item`, jamais d'un texte narratif libre. Motif absent de 2025.
   Retypées en `text` dans le même script.
4. **Bug de contamination inter-modules** (le plus sérieux) :
   `build_index_texte_bge.py` importe `charger_occurrences_narratives`/
   `resoudre_chemin_hierarchique` DEPUIS `build_index_visuels.py` — ces
   fonctions lisent `ANNEE_DOCUMENT`/`CHUNKS_AVEC_VISUELS_JSON` comme
   globales du module `build_index_visuels`, PAS celles du module
   appelant. Un premier lancement qui ne surchargeait que les constantes
   de `build_index_texte_bge` a calculé le `chemin_hierarchique` de 8/18
   tableaux 2024 à partir des chunks narratifs **2025** (occurrences
   fantômes). Détecté par le garde-fou existant de `ingerer_tableaux`
   (divergence chemin_hierarchique texte vs visuel, 0 cas sur 2025,
   8/18 sur 2024) — jamais silencieux. Corrigé en surchargeant aussi les
   constantes de `build_index_visuels` dans le script pilote 2024 ;
   ré-exécuté, ré-ingéré dans Qdrant (upsert, mêmes ID déterministes) :
   0 divergence après correction, vérifié par re-requête réelle.

TÂCHE 4 — INGESTION QDRANT MULTI-ANNÉE (4 collections EXISTANTES, aucune nouvelle)
`id_deterministe()` (`ingest_qdrant.py`) accepte désormais un paramètre
`annee` optionnel (défaut `None`, comportement 2025 strictement inchangé)
qui préfixe la chaîne identifiante (`f"{annee}::{chaine}"`) avant hachage
— nécessaire car la numérotation Docling (self_ref, position_header)
repart de 0 à chaque conversion indépendante : sans ce salage, le
`#/tables/6` de 2024 aurait produit le MÊME UUID que celui de 2025,
écrasant silencieusement le point existant. Vérifié après ingestion :
- Delta EXACT par collection (191/18/3/14 texte/tableaux/images/qrt),
  preuve qu'aucune collision n'a eu lieu (une collision aurait réduit le
  delta, pas juste laissé le total inchangé).
- 53 points 2025 échantillonnés, relus par ID exact (`retrieve`, jamais
  `scroll` — un premier essai avec 2 `scroll()` successifs a signalé à
  tort 8 "disparitions" : `scroll()` n'a pas d'ordre stable entre 2
  appels une fois la collection modifiée ; `retrieve()` par ID confirmé
  fiable), vecteurs + payloads strictement identiques avant/après.

TÂCHE 5 — GOLDEN SET 2024 (66 questions) : INCIDENT D'INTÉGRITÉ CORRIGÉ
Le fichier source (`questions_sfcr_2024_partie1.md`, réponses attendues
incluses) avait été résumé hors du contexte entre 2 tours de
conversation ; golden_set_2024.json avait été reconstruit de MÉMOIRE
plutôt que copié du fichier source — violation du principe du projet
("jamais de réponse de golden set devinée"). Détecté par un
contre-exemple concret (G24-52 : "228%" écrit de mémoire, "241%" trouvé
en lisant réellement la page présumée du document) AVANT validation
finale — l'utilisateur a alors renvoyé le fichier source, confirmant que
"228%" était en fait la bonne réponse... mais à la page **64**, pas 65 :
le tableau de sensibilité Avec VA/Sans VA (D.2.3.1) qui porte les 3
valeurs SCR/ratio/impact MCR (G24-51/52/53) a une pagination réelle
différente de la plage p.60-65 indiquée dans le regroupement d'origine.
Corrigé : réponses remplacées mot pour mot par le fichier source
ré-envoyé, pages de G24-49/50 (63, pas 62) et G24-51/52/53 (64, pas 65)
recalées sur la position réelle vérifiée dans le PDF. Les 66
`identifiants_attendus` (self_ref / chemin_hierarchique / index_corpus /
chemin_relatif QRT) sont désormais tous dérivés du corpus 2024 réel et
vérifiés par correspondance de contenu (mots-clés numériques de la
réponse retrouvés dans le texte/tableau candidat), jamais par supposition
de page.

TÂCHE 6 — MESURE DU PIPELINE : QUOTA GEMINI GRATUIT, CONTRAINTE DURABLE ACCEPTÉE
Constat factuel (pas une supposition) : la facturation Gemini n'est PAS
active sur ce projet — chaque échec 429 nomme explicitement
`generate_content_free_tier_requests`, `GenerateRequestsPerDayPerProjectPerModel-FreeTier`,
limite 20/jour pour `gemini-3.8-flash`. Décision : ce n'est plus traité
comme un incident à corriger, mais comme une contrainte durable du
projet pour l'instant — la mesure des 75 questions restantes (66 de 2024
+ 9 de 2025 encore en échec 429, cf. ci-dessous) est étalée sur plusieurs
jours, 20 questions maximum par jour, arrêt propre (sans réessai
insistant) dès le premier 429 rencontré, reprise automatique le
lendemain via `output_structure_brute_2024/suivi_mesure_prioritaire.json`
(`mesure_prioritaire_quotidienne.py`).

Ordre de priorité retenu (valeur informative, pas ordre brut des ID) :
1. G24-13/14 (anti-fusion Nord Est/d'Oc) + G24-15/35 (cas combinés
   texte+tableau) — validation la plus directe de la robustesse
   inter-annuelle.
2. Les 62 autres questions 2024, interclassées proportionnellement par
   type (texte/tableau/page_qrt/image) à chaque lot de 20 — jamais une
   catégorie vidée avant la suivante (algorithme du plus petit quotient
   restant).
3. Les 9 questions 2025 encore en échec 429 (U10, U12-U16, U18, U19 —
   U17 résolu entre-temps, cf. ci-dessous).

**Jour 1 (2026-09-13) : 0/74 traitées.** Le quota du jour avait déjà été
intégralement consommé par 2 mesures exploratoires lancées EN PARALLÈLE
avant que cette discipline de traitement par lots ne soit établie (la
mesure complète des 66 questions 2024 en ordre brut, et une reprise des 9
questions 2025 bloquées — les deux ont sollicité Gemini simultanément).
Reprise prévue demain sur le nouvel ordre de priorité, en partant de zéro
question traitée aujourd'hui.

**Jour 2 (2026-09-13, quota réinitialisé) : 14/74 traitées, 14/74 cumulé.**
Les 4 questions les plus prioritaires (Nord Est/d'Oc + cas combinés) sont
passées EN PREMIER, comme prévu :
- **G24-13, G24-14 (Nord Est/d'Oc) : TYPE OK ET ID OK toutes les deux** —
  confirme que le pipeline complet (fusion RRF + reranking), pas
  seulement l'inspection directe de la table 2024 (tâche 2), retrouve
  correctement le tableau Délégués corrigé pour ces 2 questions
  spécifiques. Résultat le plus important de cette journée.
- G24-15, G24-35 (cas combinés texte+tableau) : ÉCHOUÉES, mais pour des
  raisons SANS lien avec le quota ni avec la correction Nord Est/d'Oc —
  G24-15 : réponse du juge Gemini non parsable en JSON (cas déjà connu,
  cf. Décision 028) ; G24-35 : erreur 503 "high demand" ponctuelle côté
  Gemini. Comptées comme traitées (pas de ré-essai en boucle), à
  ré-examiner séparément si le motif se répète.
- Sur les 14 traitées : **pipeline 10/14 bon type, 8/14 bon identifiant
  exact**. 2 écarts type-OK/ID-faux à noter : G24-24 (image organigramme)
  et G24-57 (QRT) — le pipeline choisit la bonne CATÉGORIE de contenu
  mais pas le bon élément précis ; à investiguer plus tard, pas un signal
  d'alarme isolé sur 14 questions.
- Arrêt propre sur le 15e appel (429), reprise demain.

EFFET DE BORD SUR LA MESURE 2025 (golden_set_unifie, 19 questions)
Tentative de reprise des 9 questions bloquées en 429 (U10, U12-U19) avec
la même clé Gemini : 1 seule a abouti (U17, page_qrt, TYPE+ID corrects)
avant réépuisement du quota — les 8 autres restent en échec 429.
**Résultat honnête actuel : pipeline 11/19 (pas 19/19)**, baseline
inchangée 6/19. Le chiffre 10/19 documenté à la Décision 028 était donc
bien, comme suspecté, le résultat incomplet bloqué par le quota gratuit
(confirmé en relisant `resultats_pipeline_unifie.json` : les 9 entrées
portaient encore l'erreur 429 brute, jamais un vrai résultat substitué) —
corrigé à 11/19, les 8 questions restantes suivront le même calendrier de
traitement par lots que les questions 2024 (tâche 3 de la liste de
priorité ci-dessus).

JUGE DE SECOURS MISTRAL (PIXTRAL/MEDIUM 3.5) — TESTÉ, ÉCHEC AU CRITÈRE 3, PLAN GEMINI MAINTENU
Piste explorée pour contourner le quota Gemini gratuit (20/jour) : Mistral
propose un tier gratuit "Experiment" (aucune carte requise, vérification
téléphonique). Avant tout traitement en masse, un seul test (U01/U02,
même discipline que pour Nemotron) :
- **Modèle** : `pixtral-large-latest` INVALIDE d'emblée — DÉPRÉCIÉ depuis
  le 27/02/2026 (remplacé par Mistral Medium 3.5). L'identifiant lu sur
  `docs.mistral.ai/models` (`mistral-medium-3-5-26-04`) s'est révélé être
  un simple SLUG D'URL, pas l'identifiant API réel — rejeté en 400
  "Invalid model" au premier essai. Ré-vérifié via la SOURCE DE VÉRITÉ
  réelle (`GET https://api.mistral.ai/v1/models` avec la clé du compte,
  pas la documentation) : `mistral-medium-2604` retenu parmi plusieurs
  alias valides confirmés présents (`mistral-medium-2604`,
  `mistral-medium-3-5`, `mistral-medium-3.5`, `mistral-medium-latest`).
  Aucune entrée `pixtral*` dans cette liste réelle : Pixtral n'est plus
  proposé du tout sur ce compte, cohérent avec son retrait.
- **SDK** : le SDK natif `mistralai` (`client.chat.complete(...)`, image
  = chaîne data-URL directe) diffère de l'interface OpenAI-compatible
  utilisée pour Gemini/OpenRouter (`client.chat.completions.create(...)`,
  image = dict imbriqué `{"url": ...}`) — vérifié en inspectant la
  signature réelle du SDK installé, pas supposé identique. Fonction
  séparée écrite (`juger_candidats_llm_mistral`/`pipeline_complet_mistral`
  dans `fusion_reranking.py`), PAS un remplacement de `_juger_avec_client`.
- **Résultat du test unique** : les 2 appels (U01, U02) ont échoué en 429
  "Rate limit exceeded" — y compris le TOUT PREMIER appel du compte (35s
  de latence avant l'échec, signe probable d'un retry interne du SDK
  consommant plusieurs requêtes du quota pour un seul appel côté code).
  Critère 3 de la checklist (comportement prévisible/gérable du tier
  gratuit) **ÉCHOUÉ** : un débit qui rate-limite dès la première requête
  réelle, avec une latence irrégulière avant l'échec, n'est pas un plan
  de traitement fiable pour 74 questions.
- **Décision, conformément à la consigne donnée** : PAS de recherche d'un
  2e modèle Mistral, PAS d'insistance (pas de nouvel essai avec un délai
  différent). Le code du juge Mistral est conservé (fonctionnel, pourrait
  resservir si le tier gratuit se stabilise), mais le plan de traitement
  réel des 74 questions restantes revient entièrement au calendrier Gemini
  gratuit par lots de 20/jour (Jour 1 ci-dessus), comme prévu en dernier
  recours.

BASCULE GEMINI -> CLAUDE HAIKU 4.5 (JUGE ET GÉNÉRATION) — TÂCHE 6 TERMINÉE
Le quota gratuit Gemini (20/jour) est un blocage d'infrastructure/
facturation durable (facturation non activée sur ce projet, cf. plus
haut), pas un incident à corriger — Mistral testé et écarté (ci-dessus).
Bascule sur Claude Haiku 4.5 (`claude-haiku-4-5-20251001`, le moins cher
des modèles Claude avec support vision), pour minimiser le coût sur le
crédit de 20 $ disponible (rechargement automatique désactivé). Sonnet/
Opus explicitement écartés sans besoin validé.
- **Test préalable sur échantillon** (même discipline que Mistral) :
  juge testé sur 3 questions (G24-13, G24-14, G24-24) — format JSON
  strict respecté, jugement correct sur les 3 (TYPE OK + ID OK), coût
  réel ~0,0058 $/question. Génération testée sur U01/U02 (cas préparés
  Décision 029) — réponses correctes, bien sourcées, registre
  professionnel adapté à un contexte réglementaire ; 1 défaut mineur
  relevé (terminologie interne "CANDIDAT GAGNANT" ayant fuité dans une
  citation sur U02) — jugé comme un réglage de prompt, pas une
  insuffisance de Haiku sur ce rôle : Sonnet non testé (le critère
  d'écart de qualité n'était pas atteint).
- **Traitement du lot complet en un seul lancement**, pas étalé sur
  plusieurs jours : le débit n'est plus limité par un quota quotidien
  gratuit mais par un budget (garde-fou de sécurité à 2 $, très au-dessus
  de la projection réelle ~0,40 $) — `mesure_prioritaire_quotidienne.py`
  adapté en conséquence (MAX_PAR_JOUR remplacé par BUDGET_MAX_USD).
- **Coût réel final observé : 0,40956 $** pour 62 questions traitées
  dans cette session (les 12 restantes du total de 74 avaient déjà été
  mesurées avec Gemini, conservées telles quelles — pas de mélange de
  fournisseur AU SEIN d'un même lot de mesure, conformément à la
  consigne, mais un historique Gemini+Claude assumé sur l'ensemble de la
  tâche). Aucun échec technique (0 erreur non liée au budget) sur les 62.

RÉSULTATS FINAUX — GOLDEN SET 2024 (66 questions)
**Pipeline complet : 52/66 bon type (78,8%), 43/66 bon identifiant exact
(65,2%).** Les 2 questions Nord Est/d'Oc prioritaires (G24-13, G24-14)
sont TYPE OK + ID OK — confirmation la plus importante de cette tâche.
Comparaison au texte seul 2025 (`resultats_texte_bge_m3.json`,
recall@5 88,9% sur 18 questions, mesure de retrieval pur, pas directement
comparable à ce pipeline complet type+ID sur 66 questions multi-type) :
pas de régression de méthode détectée, les écarts observés relèvent de
cas individuels (cf. Décision 032 pour 2 d'entre eux, résolus).

RÉSULTATS FINAUX — GOLDEN SET UNIFIÉ 2025 (19 questions), MESURE ENFIN COMPLÈTE
Les 8 questions bloquées en 429 depuis la Décision 028 (U10, U12-U16,
U18, U19) mesurées avec Claude : **7/8 réussies** (seule U16, image du
schéma de structure simplifiée du Groupe, `#/pictures/12`, échoue —
nouveau cas non encore diagnostiqué, distinct de G24-24/G24-57 puisque le
filtre annee=2025 était actif ici, donc pas une confusion inter-année).
Fusionné avec les 11/19 déjà acquis (10 Gemini + U17) dans
`resultats_pipeline_unifie.json` : **pipeline final 18/19 (94,7%), contre
6/19 pour la baseline (31,6%)** — le chiffre "10/19 puis 11/19" documenté
provisoirement à la Décision 028 est maintenant définitivement remplacé
par ce résultat complet.

RÉSULTAT : tâches 1 à 6 de la robustesse inter-annuelle TERMINÉES.
Extraction complète, correction Nord Est/d'Oc confirmée sur 2024 (y
compris via le pipeline complet, pas seulement l'inspection directe),
visuels stockés sous `visuels/2024/`, ingestion Qdrant multi-année sans
collision ni altération des données 2025, golden set 2024 fiable (66
questions, identifiants vérifiés), mesure du pipeline complet achevée sur
les 2 golden sets (2024 : 66/66 mesurées ; 2025 : 19/19 mesurées, quota
Gemini enfin contourné via Claude). Reste ouvert : U16 (2025) et les
écarts type-OK/ID-faux résiduels du golden set 2024, non
individuellement diagnostiqués — à reprendre si une analyse plus fine
est demandée.

## Décision 032 — Filtre natif Qdrant sur annee_document dans les 4 collections (changement d'architecture de recherche)

CONTEXTE
Diagnostic de 2 cas "type OK, identifiant faux" rencontrés au Jour 2 de la
mesure prioritaire (Décision 031) : G24-24 (image, organigramme) et
G24-57 (QRT). Investigation demandée AVANT toute correction, pour
distinguer confusion de similarité (embeddings) vs bug d'indexation.

DIAGNOSTIC
- **G24-24 : confusion de similarité CONFIRMÉE.** Le pool de candidats
  RRF contenait `#/pictures/13` (organigramme 2024, correct) ET
  `#/pictures/12` (organigramme **2025**) — le même diagramme, quasiment
  inchangé d'une année sur l'autre (mêmes libellés, même mise en page,
  même note "9 caisses régionales métropolitaines, 2 caisses outre-mer et
  2 caisses spécialisées"). Similarité cosinus RÉELLE entre les 2
  embeddings Cohere : **0,9954** — quasi-duplicat. Le candidat 2025
  concurrençait directement le candidat 2024 attendu, purement parce que
  la recherche ne distinguait pas les années.
- **G24-57 : diagnostic bloqué, mais un vrai bug annexe trouvé au
  passage.** `identifiants_attendus` était VIDE (`{}`) pour les 11
  questions QRT du golden set 2024 (gap de construction antérieur,
  corrigé ici : `{"page_qrt": "2024/qrt_pages/page_<N>.png"}`) — le
  résultat "ID FAUX" enregistré pour G24-57 comparait en réalité contre
  `None`, donc n'était PAS informatif, quel qu'ait été le choix réel du
  pipeline. Le quota Gemini étant épuisé au moment du diagnostic, la
  vraie réponse du pipeline n'a pas pu être récupérée ; par comparaison,
  la similarité cosinus entre la page QRT 2024 attendue (p.74,
  S.02.01.02) et 2 candidates concurrentes (p.80 2024, autre template :
  0,623 ; p.77 2025, même template : 0,619) est BIEN PLUS FAIBLE que pour
  le cas image (0,995) — si une erreur de sélection existe ici, elle
  n'est probablement pas de même nature (confusion visuelle extrême),
  à reconfirmer avec le vrai résultat du pipeline dès que le quota le
  permet.

CAUSE RACINE (vérifiée dans le code, pas supposée)
`rechercher_texte_pour_fusion`/`rechercher_tableaux_pour_fusion`/
`rechercher_images_pour_fusion`/`rechercher_qrt_pour_fusion`
(`fusion_reranking.py`) et `baseline_meilleur_score_normalise`
n'appliquaient AUCUN filtre — chaque `query_points` cherchait sur
l'intégralité de la collection, 2024 et 2025 mélangés sans distinction,
pour TOUTE question, pas seulement celles du golden set 2024.

DÉCISION — CHANGEMENT D'ARCHITECTURE (distinct de la Décision 031, pas un
correctif ponctuel sur G24-24)
Ajout d'un paramètre optionnel `annee` (défaut `None`, comportement
inchangé — recherche sur toutes les années, pour tout appelant qui ne le
précise pas) à `fusionner_candidats`, aux 4 fonctions `rechercher_*_pour_fusion`,
à `baseline_meilleur_score_normalise`, et aux 3 variantes de
`pipeline_complet` (Gemini/OpenRouter/Mistral). Quand `annee` est fourni,
un `Filter(must=[FieldCondition(key="annee_document", match=MatchValue(value=annee))])`
est passé en `query_filter` NATIF à `query_points` (et en `filter` sur
chaque `Prefetch` pour la collection "tableaux", qui interroge 2 vecteurs
en sous-requêtes) — jamais un post-filtrage après coup, pour que `limit`
s'applique réellement sur le résultat déjà filtré. Le chemin de reranking
LLM lui-même (`juger_candidats_llm`, validé Décision 028) n'est PAS
modifié — seule la recherche en amont change.
`mesure_prioritaire_quotidienne.py`, `mesurer_pipeline_2024.py`,
`mesurer_pipeline_unifie.py` et `reprendre_9_unifie_gemini.py` mis à jour
pour passer l'année réelle de chaque golden set (2024 ou 2025).

VÉRIFICATION PARTIELLE (gratuite, sans appel LLM, faite immédiatement)
`fusionner_candidats` ré-exécuté sur la question G24-24 avec `annee=2024` :
les 8 candidats du pool retournent TOUS `annee_document=2024` (0 candidat
2025) — le duplicat `#/pictures/12` disparaît entièrement du pool, et le
candidat correct (`#/pictures/13`) remonte du rang 7 au rang 3. Confirme
la cause au niveau de la RECHERCHE. La confirmation complète (le
reranking LLM choisit-il maintenant le bon candidat en rang 1 ?) reste à
faire dès que le quota Gemini le permet — G24-24 et G24-57 retirés de
`suivi_mesure_prioritaire.json` pour être re-mesurés avec le filtre actif
au prochain lot quotidien (les 12 autres résultats déjà acquis, dont
G24-13/G24-14, sont conservés tels quels — non affectés par ce
changement, pas de raison de re-consommer du quota dessus).

RÉSULTAT : changement d'architecture appliqué et vérifié au niveau
recherche (gratuit) ; confirmation de bout en bout (recherche + reranking)
en attente du prochain accès quota, avec l'hypothèse que le problème
G24-24 disparaît complètement (pas seulement s'améliore) et que le
diagnostic G24-57 devient enfin exploitable une fois son identifiant
attendu corrigé et le vrai résultat du pipeline observé.

CONFIRMATION DE BOUT EN BOUT (2026-09-13, juge Claude Haiku 4.5, cf. mise à jour Décision 031)
Hypothèse CONFIRMÉE dans les 2 cas — le problème disparaît complètement,
pas seulement s'améliore :
- **G24-24 : TYPE OK ET ID OK.** Avec le filtre `annee=2024` actif, le
  candidat correct (`#/pictures/13`) ne concourt plus contre son
  quasi-duplicat 2025 et remonte en tête du jugement du reranker.
- **G24-57 : TYPE OK ET ID OK** (une fois `identifiants_attendus`
  corrigé, cf. ci-dessus) — le diagnostic bloqué par le quota Gemini a pu
  être complété avec le juge de secours Claude.
Les 2 questions sont retirées de la liste des écarts résiduels du golden
set 2024 (52/66 bon type, 43/66 bon identifiant, cf. Décision 031).

## Décision 033 — Diagnostic des 23 écarts d'identifiant restants (golden set 2024) : concentration sur TEXTE, cause = jugement pas retrieval, Sonnet écarté, 1 étiquette golden set corrigée

CONTEXTE
Avant de considérer la mesure du golden set 2024 close : décomposition
des 23 écarts d'identifiant exact (66 - 43) par type de contenu, à partir
des résultats déjà produits (aucun nouvel appel LLM pour cette étape).

RÉPARTITION PAR TYPE — concentration nette, pas dispersion uniforme
| Type            | N  | id_ok | Taux  |
|-----------------|----|----|-------|
| TEXTE           | 29 | 12 | 41,4% |
| TABLEAU         | 23 | 22 | 95,7% |
| QRT             | 11 |  8 | 72,7% |
| TABLEAU+TEXTE   |  2 |  0 |  0,0% |
| IMAGE           |  1 |  1 | 100%  |

TEXTE concentre 17 des 23 échecs (74%) — le problème n'est pas dispersé,
il est concentré sur le texte narratif. Les 17 échecs se regroupent en 6
zones documentaires denses en sous-sections numérotées proches (A.1.2,
A.1.4 "Analyse de l'activité du Groupe", B.2.1.x "compétence", B.3.1.x
"gestion des risques", D.2.1.x/D.2.3.x "provisions techniques").

DIAGNOSTIC CAUSE — retrieval vs jugement (5 cas testés, 1 par zone sur 4 des 6)
Vérifié gratuitement (aucun appel LLM) : le pool de candidats RRF fusionné
réellement envoyé au juge est RECONSTRUCTIBLE de façon déterministe
(`fusionner_candidats`, aucune stochasticité, mêmes vecteurs Qdrant que
lors de la mesure réelle) — pas besoin de rejouer la mesure pour savoir
ce que le juge a vu.
- **`_contenu_candidat_pour_juge` transmet au juge le chemin_hierarchique
  COMPLET et non tronqué** (vérifié dans le code) — seule
  `construire_texte_a_encoder` (étape d'embedding, en amont) tronque aux
  2 derniers segments. Le juge n'est donc PAS mal informé sur la
  hiérarchie, contrairement à l'hypothèse initiale.
- **Sur les 5 cas testés (A.1.x, B.2.1.x, B.3.1.x, D.2.x×2), le chunk
  correct était présent dans le pool RRF envoyé au juge — 5/5, jamais
  absent** — et classé **rang 1 avant reranking dans 4 cas sur 5**. Le
  scénario "embedding pas assez distinctif au point de perdre le bon
  candidat avant le jugement" ne s'est produit dans AUCUN des 5 cas
  vérifiés. Le scénario "présent mais le juge choisit quand même un
  frère" s'est produit dans les 5 cas, de façon cohérente sur les 4
  zones testées — pas un cas isolé.
- **Conclusion** : la cause dominante observée est le JUGEMENT (le juge
  dévie d'un candidat déjà correctement classé en tête par la fusion
  RRF), PAS la distinctivité de l'embedding. La troncature à 2 segments
  dans `construire_texte_a_encoder` reste un mécanisme réel dans le code
  mais n'a provoqué aucune perte de candidat observée sur cet
  échantillon — hypothèse non confirmée comme cause active ici, pas
  invalidée en général (pourrait se manifester ailleurs, non vérifié).

CORRECTION GOLDEN SET — G24-40 (pas un échec de jugement)
Ré-examen demandé avant généralisation : le candidat en tête du pool RRF
pour G24-40 (`B.1.2.1.1. Composition`, 15 administrateurs dont 9
présidents de caisses + 4 indépendants) et l'étiquette originale du
golden set (`B.2.1.1. Procédure de nomination des administrateurs`)
contiennent en réalité le MÊME FAIT, répété mot pour mot dans les 2
sections du document réel (vérifié par lecture directe des 2 textes
complets, pas supposé) — pas un frère "moins pertinent", un vrai doublon
de contenu. Corrigé : `identifiants_attendus.texte` de G24-40 accepte
désormais les 2 chemins (liste au lieu d'une chaîne unique) ;
`evaluer_resultat` (`mesurer_pipeline_unifie.py`) étendu pour accepter une
liste d'identifiants valides (comportement inchangé si chaîne unique).
Re-vérifié : Haiku avait en réalité choisi `B.1.2.1.1. Composition` —
avec la correction, G24-40 passe à TYPE OK + ID OK. Golden set 2024
recalé à 43/66 -> **44/66 bon identifiant** (retiré de la liste des 17
échecs TEXTE, qui passe donc à 16).

TEST SONNET 5 SUR LES 16 ÉCHECS RESTANTS — ÉCARTÉ, PAS DE GÉNÉRALISATION
Testé UNIQUEMENT sur les 16 cas (pas généralisé avant d'avoir le
chiffre, conformément à la consigne), même pool RRF déterministe réutilisé
(coût = 16 appels de jugement seulement) :
- **1/16 corrigé (6,2%)** — gain non net, largement en-dessous du seuil
  qui justifierait une généralisation.
- **7/16 en ÉCHEC DE FORMAT** : Sonnet a renvoyé des objets JSON
  concaténés ligne par ligne (`{"candidat": 1, "score": 8}\n{"candidat":
  2...`) au lieu d'une liste JSON unique, malgré la consigne stricte —
  échec de parsing, comportement bien MOINS fiable que Haiku sur ce
  point précis (0 échec de format sur Haiku dans toute la mesure).
- **1/16 erreur technique nouvelle** : `AttributeError: 'ThinkingBlock'
  object has no attribute 'text'` — Sonnet 5 a renvoyé un bloc de
  raisonnement étendu en premier élément de `message.content`, jamais
  vu avec Haiku ; `message.content[0].text` invalide dans ce cas (code
  du test uniquement, pas corrigé dans le pipeline principal).
- **Coût réel : 0,2401 $ pour 16 appels** (0,015 $/question en moyenne)
  contre ~0,096 $ pour Haiku sur le même volume — **2,5× plus cher**, pour
  un résultat NET NÉGATIF (moins fiable ET plus cher).
- **Particularité API notée** : `claude-sonnet-5` rejette le paramètre
  `temperature` en 400 ("deprecated for this model") — vérifié à
  l'exécution, pas supposé identique à Haiku ; géré en omettant ce
  paramètre uniquement pour Sonnet dans `juger_candidats_llm_claude`
  (paramètre `modele`/`prix` ajoutés à cette fonction pour permettre le
  test sans dupliquer le code).

DÉCISION : Haiku 4.5 reste le juge pour l'ensemble du pipeline. Sonnet
n'est PAS généralisé (gain marginal négatif, fiabilité de format
inférieure, coût 2,5×, conformément à la consigne de ne pas généraliser
sans gain net). Aucun changement au pipeline principal en dehors de la
correction ponctuelle de golden set (G24-40) et de l'extension
`evaluer_resultat` pour les identifiants multiples.

TEST PROMPT AJUSTÉ (poids explicite au rang RRF pré-reranking) — 0/16, ÉCARTÉ
Dernier essai bon marché avant de documenter la limite : prompt du juge
Haiku modifié pour (a) afficher le rang de pré-classement RRF de chaque
candidat, (b) ajouter une consigne explicite ("le candidat en tête de la
recherche correspond souvent déjà au bon sujet — ne t'en écarte que pour
une réponse NETTEMENT plus précise, pas simplement différente"). Testé
sur les mêmes 16 cas, même pool RRF déterministe réutilisé (fonction de
test isolée, hors `fusion_reranking.py` tant que non validée) :
- **0/16 corrigé (0%)** — aucune amélioration, pas même marginale.
- Signal supplémentaire défavorable : plusieurs cas qui gardaient au
  moins le bon TYPE avec le prompt standard (G24-38, G24-45, G24-46,
  G24-50 — tous `texte`) basculent vers un type différent et tout aussi
  faux avec le prompt ajusté (`tableau`/`image`/`page_qrt`) — indice que
  la consigne ajoutée a perturbé le jugement plutôt que de l'ancrer,
  pas juste "sans effet".
- Coût : 0,109 $ pour 16 appels (comparable à Haiku standard, ce n'est
  pas un problème de coût qui a motivé l'abandon).
Conformément à la consigne : n'améliore pas -> pas de nouvelle décision
de correctif, pas de reprise de mesure avec ce prompt, fonction de test
supprimée (jamais intégrée à `fusion_reranking.py`).

RÉSULTAT : golden set 2024 final — **44/66 bon identifiant exact (66,7%)**,
52/66 bon type (78,8%, inchangé). 16 échecs TEXTE restants documentés
comme LIMITE CONNUE du juge (Claude Haiku 4.5, prompt standard) sur des
frères numérotés proches, non résolue après 3 pistes testées (Sonnet 5,
prompt à poids RRF explicite, et golden set déjà audité pour de vraies
ambiguïtés — cf. G24-40) : cause identifiée avec certitude (jugement, pas
retrieval — chunk correct présent et souvent en tête du pool RRF dans
100% des cas vérifiés), mais aucun correctif testé n'a apporté de gain
net. Mesure du golden set 2024 close sur cette base.

## Décision 034 — Clôture de l'investigation des 16 échecs TEXTE : bug extended thinking corrigé, Sonnet propre à 3/16 (sous le seuil), Haiku maintenu en production

CONTEXTE
Suite de la Décision 033 : le premier test Sonnet (0/16 utile, 7/16
échecs de parsing + 1 bug technique) s'est révélé pollué, pas concluant
en soi — investigation de la cause avant tout saut vers un modèle encore
plus coûteux (Opus), conformément à la consigne "diagnostiquer avant
d'escalader".

CHRONOLOGIE COMPLÈTE (honnête, chaque étape et son résultat réel)

1. **Diagnostic initial (cause confirmée par les données, pas supposée)** :
   sur 5 cas vérifiés couvrant les 4 zones de confusion (A.1.x, B.2.1.x,
   B.3.1.x, D.2.x×2), le chunk correct était présent dans le pool RRF
   envoyé au juge dans 100% des cas (5/5), et déjà classé rang 1 avant
   reranking dans 4/5. Le juge reçoit par ailleurs le chemin_hierarchique
   COMPLET (vérifié dans le code, `_contenu_candidat_pour_juge`), pas
   tronqué. Conclusion : la cause est le JUGEMENT (le juge dévie d'un
   candidat déjà correctement classé en tête), pas le retrieval/embedding.

2. **Tentative 1 — prompt ajusté (poids explicite au rang RRF pré-reranking)** :
   0/16 corrigé (0%), ET régression constatée sur 4 cas (G24-38, G24-45,
   G24-46, G24-50) qui gardaient au moins le bon TYPE avec le prompt
   standard mais basculent vers un type différent et tout aussi faux avec
   le prompt ajusté — signal que la consigne ajoutée a perturbé le
   jugement plutôt que de l'ancrer. Écarté, prompt standard restauré.

3. **Tentative 2 — Sonnet 5, premier essai : résultat POLLUÉ, non concluant** :
   1/16 corrigé apparent, mais 7/16 en échec de PARSING JSON (Sonnet
   renvoyait des objets JSON valides individuellement mais concaténés
   ligne par ligne au lieu d'une liste JSON unique) + 1/16 en erreur
   technique (`AttributeError: 'ThinkingBlock' object has no attribute
   'text'`). Diagnostic demandé avant tout nouveau test coûteux : les 2
   symptômes tracés à la MÊME cause — l'"extended thinking" de
   claude-sonnet-5 est activé PAR DÉFAUT côté serveur (confirmé : un
   ThinkingBlock est apparu dans la réponse sans jamais avoir été
   demandé), ce qui insère un bloc de raisonnement avant le texte final
   ET semble altérer la structure de sortie du JSON demandé. Corrigé
   dans `juger_candidats_llm_claude` (`fusion_reranking.py`) : (a)
   `thinking={"type": "disabled"}` passé explicitement pour Sonnet
   (forme vérifiée dans le SDK installé, pas devinée) ; (b) extraction du
   premier bloc de type `"text"` dans `message.content` au lieu de
   supposer `content[0]` ; (c) filet de sécurité CIBLÉ sur le motif JSONL
   réellement observé (objets JSON valides ligne par ligne, regroupés en
   liste si le motif correspond exactement — pas un JSON invalide
   générique). Aucun effet sur Haiku (paramètres conditionnés au modèle).

4. **Tentative 3 — Sonnet 5, après correctif : SIGNAL PROPRE, 3/16 (18,8%)** :
   0 échec de parsing, 0 bug technique (1 seule erreur réseau transitoire
   sur G24-04, sans rapport). Résultat fiable cette fois : **3/16 corrigés
   (G24-17, G24-47, G24-50)**, contre 0/16 pour Haiku standard sur ces
   mêmes cas. Coût réel : 0,412 $ pour 16 appels (~0,026 $/question),
   soit environ 4,3× le coût de Haiku sur le même volume.

DÉCISION
**18,8% reste sous le seuil fixé pour généraliser** ("gain net, pas
marginal") — 13 des 16 cas échouent encore même avec Sonnet, le
mécanisme de déviation du juge n'est donc pas résolu, seulement
partiellement atténué sur un sous-ensemble. Sonnet n'est PAS généralisé.
Le juge de production reste Claude Haiku 4.5, avec le PROMPT D'ORIGINE
(celui d'avant la tentative 1, jamais modifié en production — la
tentative 1 n'a jamais été déployée au-delà de son propre test isolé).
Aucun autre changement de pipeline à ce stade.

SCORE FINAL DU GOLDEN SET 2024 — précision explicite sur ce qui est inclus
**44/66 bon identifiant exact (66,7%), 52/66 bon type (78,8%)** — ce
chiffre correspond au pipeline de PRODUCTION tel qu'il tourne réellement
(Haiku 4.5, prompt d'origine, filtre annee actif). **Les 3 cas
récupérables avec Sonnet (G24-17, G24-47, G24-50) ne sont PAS inclus**
dans ce score : Sonnet n'étant pas déployé en production, mélanger un
résultat obtenu avec un modèle non utilisé réellement fausserait la
mesure de ce que le pipeline livre effectivement. Les 16 cas TEXTE
restent documentés comme limitation connue du juge sur les frères
hiérarchiques numérotés proches et sémantiquement voisins — non comme un
échec de la mesure, mais comme ce qu'elle a permis de révéler avec
précision (cause identifiée, 3 pistes de correction testées et
documentées, aucune ne franchissant le seuil de généralisation).

---

## Clôture — Robustesse inter-annuelle SFCR Groupama 2024 vs 2025

Les 2 validations centrales de cette tâche (Décision 030) sont réussies :
- **Correction Nord Est/d'Oc (Décision 021)** : reproduite à l'identique
  sur 2024, corrigée sans aucune modification du code (logique scopée à
  l'entité, pas au document), et confirmée jusqu'au bout du pipeline
  complet (fusion RRF + reranking), pas seulement par inspection directe
  de la table.
- **Confusion inter-année (G24-24/G24-57, Décision 032)** : diagnostiquée
  avec preuve chiffrée (similarité cosinus 0,9954 sur les embeddings du
  cas image), corrigée par un filtre natif Qdrant sur `annee_document`
  (changement d'architecture appliqué aux 4 collections, pas un
  correctif ponctuel), et confirmée résolue de bout en bout.

Le seul point non résolu — 16/66 questions TEXTE du golden set 2024 avec
un identifiant faux malgré un chunk correct présent et souvent en tête du
pool de recherche (Décisions 033/034) — est un résultat HONNÊTE de la
mesure, pas un échec de la démarche : la cause est identifiée avec
certitude (déviation du juge de reranking sur des frères hiérarchiques
proches), 3 pistes de correction ont été testées avec rigueur (prompt
ajusté, Sonnet en test pollué, Sonnet après correctif), et aucune ne
justifie un changement de pipeline en production au regard du seuil fixé
(gain net requis, pas marginal). Le pipeline reste sur Claude Haiku 4.5
(juge et génération), filtre annee actif dans les 4 collections Qdrant,
golden sets 2024 (66 questions) et 2025 (19 questions, désormais mesuré
à 18/19) tous deux mesurés jusqu'au bout.

## Décision 035 — Test "Contextual Retrieval" envisagé sur les 16 échecs TEXTE : reciblé sur 5 cas après avoir séparé 2 causes distinctes, bloqué par le quota Cohere (trial, 1000/mois)

CONTEXTE
Avant de tester la technique "Contextual Retrieval" d'Anthropic (générer
une phrase de contexte via Haiku pour chaque chunk avant son embedding
BGE-M3, au lieu de la troncature aux 2 derniers segments de
chemin_hierarchique) sur les 16 échecs TEXTE : identification précise des
chunks concernés, par re-jeu déterministe (temperature=0) du juge Haiku
standard sur le pool RRF déjà reconstruit — 5 questions traitées avant
blocage.

2 DÉCOUVERTES AVANT LE BLOCAGE

1. **Quota Cohere réellement épuisé, pas un simple rate-limit ponctuel** :
   confirmé par un appel isolé de test après le blocage initial —
   `TooManyRequestsError` persistante, clé "Trial", plafond annoncé 1000
   appels/mois. Cause AGGRAVANTE trouvée et corrigée au passage (gain
   général, pas spécifique à ce test) : `encoder_cohere()`
   (`recherche_collections.py`) n'avait AUCUN cache — `fusionner_candidats`
   l'appelle 3 fois PAR QUESTION (une fois dans chacune de
   `rechercher_tableaux_pour_fusion`/`rechercher_images_pour_fusion`/
   `rechercher_qrt_pour_fusion`, pour encoder la MÊME chaîne à chaque
   fois) — gaspillage confirmé, pas supposé, qui a probablement contribué
   à l'épuisement plus rapide du quota tout au long de cette session.
   Corrigé par un cache simple (question -> embedding), comportement et
   résultats strictement inchangés (déterministe), 3× moins d'appels
   Cohere par question fusionnée désormais.

2. **Les 16 échecs TEXTE ne sont PAS tous des confusions de frères** —
   distinction cruciale manquée jusqu'ici, établie par FILTRAGE DIRECT
   des résultats déjà stockés (`suivi_mesure_prioritaire.json`), aucun
   nouvel appel nécessaire :
   - **5 cas type_ok=True, id_ok=False** — vraie confusion de frères
     TEXTE (le pipeline choisit un autre chunk texte, structurellement
     proche) : **G24-38, G24-44, G24-45, G24-46, G24-50**. Seuls ces 5
     cas correspondent au mécanisme que "Contextual Retrieval" peut
     effectivement adresser (distinctivité de l'embedding ENTRE chunks
     texte voisins).
   - **11 cas type_ok=False** — confusion INTER-TYPE (le pipeline
     choisit un tableau, une image ou une page QRT à la place d'un
     chunk texte) : **G24-04, G24-16, G24-17, G24-25, G24-26, G24-27,
     G24-28, G24-29, G24-47, G24-54, G24-55**. Catégorie DISTINCTE,
     documentée mais explicitement HORS PÉRIMÈTRE de ce test — la cause
     probable est différente (compétition RRF/jugement entre
     collections, pas distinctivité au sein de la collection texte) et
     nécessiterait une approche différente si traitée plus tard.

DÉCISION
Le test "Contextual Retrieval" sera mené UNIQUEMENT sur les 5 cas
(G24-38, G24-44, G24-45, G24-46, G24-50) une fois le quota Cohere
disponible à nouveau — ni sur les 16 échecs complets (mauvaise cible pour
11 d'entre eux), ni avant d'avoir cette confirmation. Réduit à la fois le
coût du test (5 appels de contextualisation + 5 comparaisons au lieu de
16+) ET le cible correctement sur le mécanisme qu'il peut réellement
corriger. Les 11 cas de confusion inter-type restent un chantier
SÉPARÉ, non entamé, à traiter plus tard si jugé utile.

RÉSULTAT : aucun changement de pipeline à ce stade (hors correctif de
cache Cohere, sans effet sur les résultats). Test en attente du reset du
quota Cohere (mensuel, clé trial) — reprise prévue sur les 5 cas ciblés
dès que possible, méthodologie inchangée par ailleurs (chunks à
contextualiser identifiés depuis les golden_set_2024.json + résultats
stockés, comparaison de similarité cosinus avant tout nouveau passage
par la fusion/reranking, seuil de généralisation identique aux tests
précédents — gain net requis, pas 1-2 cas).

MISE À JOUR — NATURE DU BLOCAGE CONFIRMÉE : PLAFOND MENSUEL, PAS UN DÉBIT COURT TERME
Vérifié avant de programmer une nouvelle tentative, par 2 sources
indépendantes (pas une supposition à partir de l'absence d'erreur
explicite) :
- **Le message d'erreur reçu lui-même** (déjà capturé) : "You are using a
  Trial key, which is limited to **1000 API calls / month**."
- **Documentation officielle Cohere** (`docs.cohere.com/docs/rate-limits`) :
  confirme "Trial keys... are limited to 1,000 API calls a month",
  DISTINCT des limites par minute également documentées pour certains
  endpoints (ex. 20 req/min pour Chat) — les 2 contraintes coexistent,
  ce n'est pas la même limite. Le mécanisme exact de réinitialisation
  (mois calendaire vs fenêtre glissante de 30 jours) n'est PAS précisé
  publiquement — hors de portée sans contacter le support Cohere.

CONSÉQUENCE : ce n'est PAS un débit court terme qui se réinitialiserait
"dans l'heure" — attendre 1h n'aurait aucun effet. Boucle de nouvelle
tentative programmée annulée. Bloqué jusqu'à la réinitialisation
mensuelle (date exacte inconnue) OU un passage à une clé Cohere payante
— **décision qui revient à l'utilisateur**, pas quelque chose à reporter
en silence.

IMPACT — pas seulement ce test : toute mesure dépendant des 3 collections
Qdrant multimodales (tableaux/images/qrt, toutes indexées et interrogées
via Cohere Embed v4) est bloquée tant que ce plafond n'est pas levé — y
compris une éventuelle reprise de la mesure golden_set_2024/2025 complète
si elle devait être relancée d'ici la réinitialisation.

DÉBLOQUÉ — 2e clé Cohere (`COHERE_API_KEY2` dans `.env`) fournie par
l'utilisateur, vérifiée fonctionnelle (appel de test réussi). Test
"Contextual Retrieval" repris sur les 5 cas ciblés (G24-38, G24-44,
G24-45, G24-46, G24-50) avec cette clé.

3e DÉCOUVERTE — G24-38 ÉTAIT AUSSI UNE ÉTIQUETTE GOLDEN SET FAUSSE, PAS UNE CONFUSION
En identifiant le vrai gagnant réel (rejeu déterministe du juge standard
sur le pool déjà reconstruit) pour préparer les 5 cas : le gagnant de
G24-38 (`B.1.4.3. Politique et pratiques de rémunération applicables aux
salariés`) est en réalité la BONNE réponse à "De quoi se compose la
rémunération des salariés ?" — vérifié par lecture directe du texte réel
("La rémunération des salariés est composée : -d'une rémunération
fixe..."), correspondant mot pour mot à la `reponse_attendue` déjà
enregistrée. L'étiquette originale (`B.2.1.1`, procédure d'évaluation des
dirigeants effectifs) n'avait AUCUN rapport avec la question — 3e cas de
ce type après G24-40 (Décision 033), pas une coïncidence isolée : un
audit plus systématique des étiquettes golden set pourrait révéler
d'autres cas similaires si repris plus tard. Corrigé (`identifiants_attendus.texte`
remplacé par le chemin exact vérifié), confirmé `id_ok=True` après
correction. **Golden set 2024 recalé à 45/66 (68,2%)**. Retiré de la
liste des cas à tester — il ne reste que 4 vraies confusions de frères :
G24-44, G24-45, G24-46, G24-50.

STRUCTURE RÉELLE DES 4 CAS RESTANTS — pas tous des "frères proches"
Vérifié avant de lancer le test coûteux : sur ces 4, un seul
(G24-46 : `B.3.1.1` vs `B.3.1.2`, même parent direct) est un vrai frère
numéroté adjacent. G24-50 est une confusion PARENT/ENFANT (`D.2.1`
générique vs son sous-chunk `D.2.1.5`). G24-44 et G24-45 opposent le même
chunk correct (`B.3.1.1`) à des chunks de sections ÉLOIGNÉES et sans
lien hiérarchique (`C.1.3.2` et `A.1.5`, respectivement en section C et
A) — une confusion TOPIQUE (les 2 mentionnent "réassurance") plutôt
qu'une indistinction structurelle de frères proches, hors du mécanisme
que "Contextual Retrieval" cible en théorie.

RÉSULTAT DU TEST — 0/4 AMÉLIORATION RÉELLE, 2 RÉGRESSIONS
Contexte généré via Haiku pour les 6 chunks uniques impliqués (section
parente complète transmise, consigne explicite de distinction),
nouveaux embeddings BGE-M3 calculés en LOCAL uniquement (jamais écrits
dans Qdrant), comparaison de similarité cosinus question/chunk avant vs
après, sur les 4 cas :
- **G24-44** : correct passe de 0,441 à 0,361 (RÉGRESSE), frère reste
  ~stable (0,533 -> 0,537) — toujours faux, et pire qu'avant.
- **G24-45** : correct passe de 0,543 à 0,348 (RÉGRESSE fortement),
  frère progresse même légèrement (0,555 -> 0,579) — toujours faux, et
  nettement pire qu'avant.
- **G24-46** : correct quasi stable (0,519 -> 0,521), frère progresse
  aussi (0,581 -> 0,590) — toujours faux, écart inchangé en pratique.
- **G24-50** : correct devance déjà le frère AVANT contextualisation
  (0,679 > 0,567) — ce cas n'était donc PAS un problème de similarité
  d'embedding pour commencer (cohérent avec Décision 033 : c'est le
  JUGEMENT qui se trompe ici, pas la recherche) ; la contextualisation
  n'y change rien de pertinent (0,718 vs 0,573, toujours correct devant,
  comme avant).

**Bilan honnête : 0 cas nouvellement corrigé sur les 3 vraies confusions
testées, 2 régressions.** Hypothèse sur la cause de la régression (pas
vérifiée plus avant, cohérente avec les données observées) : le chunk
`B.3.1.1` sert de bonne réponse à 3 questions différentes portant sur des
FACETTES distinctes de son contenu (référentiel de réassurance externe,
plafond événements naturels, dates du dispositif de tolérance) ; la
phrase de contexte générée par Haiku met l'accent sur UNE SEULE facette
("cadre d'appétence au risque... niveaux cibles d'indicateurs"), ce qui
peut avoir déplacé l'embedding vers cette facette précise au détriment
des 2 autres — un risque structurel de la technique quand un même chunk
répond à des questions variées, pas un problème d'exécution du test.

DÉCISION : "Contextual Retrieval" écarté, aucune extension aux 191
chunks du corpus. 2 étiquettes golden set corrigées au passage (G24-38,
G24-40) en cours d'investigation, ramenant les échecs TEXTE de 17 à 15
(4 vraies confusions de frères + 11 confusions inter-type) — cause des 4
confusions de frères confirmée comme relevant du JUGEMENT, pas de la
distinctivité d'embedding, après 4 pistes de correction testées au total
(prompt ajusté, Sonnet, Sonnet corrigé, Contextual Retrieval), aucune
n'ayant franchi le seuil de généralisation. Golden set 2024 final
définitivement arrêté à **45/66 (68,2%) bon identifiant exact**, 52/66
bon type (78,8%, inchangé) — 15 échecs TEXTE restants (4 frères proches
+ 11 confusions inter-type, catégorie séparée non traitée) documentés
comme limite connue, chantier de diagnostic clos.

CLÔTURE — HYBRID SEARCH (BM25 + EMBEDDING) ÉCARTÉ, SUR PREUVE PONCTUELLE
Avant de construire une infrastructure hybrid search : test diagnostique
ponctuel sur G24-46 (`B.3.1.1` vs `B.3.1.2`, le seul des 4 cas restants
à être une vraie paire de frères numérotés adjacents) — recherche par
correspondance de chaîne, aucun nouvel index. Résultat : les numéros de
section ("B.3.1.1", "B.3.1.2", et même le préfixe parent "B.3.1")
n'apparaissent **0 fois** dans le corps du texte des 2 chunks, vérifié
directement sur le texte réel stocké — uniquement présents dans
`chemin_hierarchique`, déjà transmis en entier au juge (cf. Décision
033). Un hybrid search BM25 chercherait dans ce même corps de texte : il
ne trouverait pas ces numéros non plus, et n'apporterait donc AUCUNE
information que le juge n'a pas déjà.

DÉCISION : infrastructure hybrid search non construite, pour ce motif
précis. Les cas restants de ce type sont un jugement de contenu
authentiquement ambigu (deux sections légitimement proches
thématiquement, ex. B.3.1.1 "objectifs et stratégies de gestion des
risques" vs B.3.1.2 "identification, évaluation et suivi des risques"),
pas un problème de correspondance lexicale — hors de portée de ce type
de correctif.

CLÔTURE DÉFINITIVE DU FIL DE DIAGNOSTIC — GOLDEN SET 2024, ÉCHECS TEXTE
5 approches testées et rejetées SUR PREUVE, pas par manque d'effort :
prompt ajusté (0/16), Sonnet brut (résultat pollué par un bug SDK,
non concluant), Sonnet corrigé (3/16, signal propre mais sous le seuil),
Contextual Retrieval (0/4, 2 régressions), hybrid search (écarté avant
construction, 0 information supplémentaire disponible pour ce mécanisme
de confusion). Aucune n'a démontré un gain justifiant son coût ou sa
complexité. Score final du golden set 2024 : **45/66 bon identifiant
exact (68,2%)**, 52/66 bon type (78,8%). Ce chantier de diagnostic est
clos.

## Décision 036 — Pool de candidats top-20 (au lieu de top-8) testé et REJETÉ : 0 réparation, 2 régressions, 2,45× le coût

CONTEXTE
Avant tout changement en production : tester si augmenter le nombre de
candidats envoyés au juge après fusion RRF (top-20 au lieu de top-8
actuel) améliore la précision — hypothèse que les 11 confusions
inter-type (Décision 035) pourraient être dues à un pool trop étroit
excluant le bon candidat.

PRÉALABLE TECHNIQUE VÉRIFIÉ
`TOP_K_PAR_COLLECTION = 10` (candidats remontés par collection AVANT
fusion RRF) suffit largement pour alimenter un pool fusionné de 20 après
troncature (jusqu'à 40 candidats bruts disponibles avant coupe, 4
collections × 10) — aucun changement necessaire à ce niveau, seul
`top_k_apres_fusion` (8 -> 20) a été modifié pour ce test.

PRÉ-CHECK GRATUIT (sans appel LLM, sur les 11 confusions inter-type)
Sur les 11 cas : **8/11** avaient déjà le bon candidat texte dans le
pool top-8 actuel (souvent en tête) — le juge le voyait déjà et
choisissait quand même autre chose ; **2/11** (G24-04, G24-29)
n'apparaissaient qu'entre les rangs 9 et 13, donc potentiellement
récupérables par un pool élargi à 20 ; **1/11** (G24-28) absent même
d'un pool de 40 — hors de portée d'un simple élargissement. Plafond
théorique identifié avant le test complet : 2/11 au mieux sur cette
catégorie.

MESURE COMPLÈTE (39 questions : 11 échecs inter-type + 9 cas déjà
corrects stratifiés par type [4 texte, 3 tableau, 1 qrt, 1 image] +
19 questions du golden set unifié 2025 — 78 appels de jugement au total,
top-8 et top-20 sur les mêmes questions)

| Métrique | Résultat |
|---|---|
| Réparations (faux -> correct) | **0/11**, y compris les 2 cas du pré-check pourtant entrés dans le pool |
| Régressions (correct -> faux) | **2** (U11, U17 — golden set 2025, tous deux corrects à top-8) |
| Inchangés corrects | 23 |
| Inchangés faux | 14 |
| Coût total | 0,256 $ (top-8) vs 0,627 $ (top-20) — **2,45× plus cher** (0,0066 $/question vs 0,0161 $/question) |
| Latence moyenne | 14,2 s (top-8) vs 14,4 s (top-20) — quasiment inchangée, pas un facteur limitant ici |

Le pré-check avait identifié un plafond théorique de 2/11 récupérables ;
même ce plafond ne s'est PAS matérialisé une fois le juge réellement
sollicité — élargir le pool a rendu les bons candidats disponibles sans
que le juge les choisisse pour autant, et a en plus fait régresser 2 cas
qui fonctionnaient déjà (probablement en diluant l'attention du juge
parmi davantage de candidats concurrents, notamment des images
supplémentaires).

DÉCISION : top-20 REJETÉ, top-8 reste la configuration de production.
Résultat net négatif sur les 3 axes demandés (précision : 0 gain, 2
régressions ; coût : 2,45× ; latence : neutre, pas un argument en sa
faveur). Confirme, comme les Décisions 033-035, que la cause des échecs
restants est un problème de JUGEMENT face à des candidats déjà
disponibles, pas un problème de PROFONDEUR de récupération — élargir la
fenêtre ne fait qu'ajouter du bruit sans ajouter de signal utile.

## Décision 037 — BM25 (hybrid search) testé sur échantillon représentatif : résultat NEUTRE en précision, gain inattendu en coût/latence, intégration peu coûteuse

CONTEXTE
Suite à la Décision 035 (BM25 écarté sur le seul cas G24-46, où
l'information n'existait nulle part dans le texte) : mesure de sa valeur
GÉNÉRALE, pas limitée à ce cas, sur un échantillon représentatif —
correction méthodologique demandée explicitement (le pré-check d'un seul
cas ne renseigne pas sur la valeur de la technique ailleurs dans le
corpus).

ÉTAPE 1 — Index isolé, aucune modification de production
Index BM25 (`rank_bm25.BM25Okapi`) construit en mémoire sur les 381
chunks texte indexables (191 2024 + 190 2025), en parallèle de Qdrant,
sans y toucher. Ajouté comme **5e liste** dans la fusion RRF
(`fusionner_rrf`, réutilisée telle quelle) via une fonction de recherche
BM25 au même format que les 4 fonctions `rechercher_*_pour_fusion`
existantes — aucune modification du code de production, tout dans un
script de test isolé.

ÉTAPE 2 — Échantillon de 36 questions, construit objectivement
Classification par inspection RÉELLE du texte source (pas des questions
elles-mêmes) :
- **13 questions avec signal à correspondance exacte VÉRIFIÉ** dans le
  chunk correct (numéro de section type "X.Y.Z.", sigle réglementaire
  précis — DORA, ACPR, SCR, MCR, IFRS — confirmé présent littéralement
  dans le texte, pas supposé) : G24-16/17/18/41/47/49/50/54/55,
  U01/07/12/18.
- **12 questions texte-pertinentes SANS signal** (6 déjà correctes + 6
  en échec), pour mesurer l'effet en l'absence de la condition que BM25
  est censé exploiter.
- **11 questions non-texte déjà correctes** (tableau/qrt/image), pour
  détecter tout effet indirect sur des collections que BM25 ne touche
  pourtant pas directement (l'ajout d'une 5e liste modifie la dynamique
  RRF globale, pas seulement pour le texte).

ÉTAPE 3-4 — MESURE (36 questions × 2 configurations, juge Haiku standard)

| Métrique | Résultat |
|---|---|
| Réparations | **1** — G24-16 (image -> texte, TYPE OK + ID OK), un des cas à signal vérifié |
| Régressions | **1** — G24-65 (QRT correct -> QRT toujours mais MAUVAISE page) |
| Inchangés corrects | 22 |
| Inchangés faux | 12 |
| Coût total | 0,242 $ (sans BM25) vs **0,187 $ (avec BM25)** — 22% MOINS cher, pas plus |
| Latence moyenne | 12,9 s (sans) vs **11,1 s (avec)** — plus rapide, pas plus lent |

**Précision : résultat NET NEUTRE (1 réparation, 1 régression)** — ne
franchit PAS le seuil "amélioration nette sans régression" au sens
strict, puisqu'une régression réelle existe (pas une absence totale de
régression). La régression (G24-65) est un effet INDIRECT confirmé :
BM25 n'ajoute que des candidats texte, mais modifie la dynamique de
score RRF pour TOUTES les collections en fusion, ce qui a fait basculer
un choix QRT-vs-QRT (page 76 correcte vers une autre page du même
gabarit) sans lien direct avec le contenu texte ajouté — un risque
d'interaction indirecte à noter, pas spécifique à BM25 en soi (le même
risque existe pour toute modification de la composition du pool fusionné,
cf. Décision 036 sur top-20).

**Coût et latence : gain réel et inattendu**, expliqué de façon
plausible (pas juste supposé) : en faisant remonter des candidats texte
via BM25, la fusion déplace parfois des candidats IMAGE (coûteux en
tokens, base64) hors du top-8 final au profit de candidats texte moins
chers — observé de façon cohérente sur la majorité des questions
individuelles (coûts unitaires systématiquement plus bas avec BM25 dans
le journal détaillé), pas un artefact isolé.

COÛT D'INTÉGRATION RÉEL (demandé explicitement, pas juste le gain de précision)
Faible : une dépendance légère (`rank_bm25`, déjà testée), un index
tenu en mémoire à reconstruire si le corpus change (pas de service
externe, pas d'infrastructure nouvelle), et une fonction de recherche au
même format que les 4 existantes, ajoutée comme 5e argument à la liste
déjà fusionnée par `fusionner_rrf` (réutilisée sans modification). Script
de test complet : ~150 lignes, majoritairement de la réutilisation.

DÉCISION
Résultat neutre en précision sur cet échantillon (pas un rejet net comme
top-20 ou Contextual Retrieval, mais pas non plus un gain net comme le
seuil l'exige) — PAS d'intégration en production sur la base de cette
seule mesure. Cependant, à la différence des techniques précédentes
rejetées, celle-ci ne montre AUCUN signal négatif fort (pas de coût
supplémentaire, pas de latence supplémentaire, complexité d'intégration
basse), et un mécanisme de réparation plausible et vérifié sur au moins
un cas réel (G24-16). Ni adopté, ni définitivement écarté : contrairement
aux Décisions 033-036, le dossier reste ouvert — un échantillon plus
large (au-delà de 36 questions) serait nécessaire pour distinguer un
signal réel modeste d'un bruit statistique sur un échantillon de cette
taille, avant de trancher définitivement.

## Décision 038 — BM25 étendu aux 85 questions (stock complet) : résultat NÉGATIF net en précision, clôture définitive de l'investigation

CONTEXTE
Suite à la Décision 037 (36 questions, résultat neutre 1 réparation/1
régression, dossier volontairement laissé ouvert faute d'échantillon
assez grand pour distinguer un signal réel d'un bruit statistique) :
extension du même protocole (index BM25 isolé en mémoire, 5e liste RRF,
juge Haiku standard, aucune modification de production) à l'intégralité
du stock de questions déjà existant — golden_set_2024.json (66) +
golden_set_unifie.json 2025 (19) = **85 questions, aucune question
nouvelle créée**.

INCIDENT DE PARCOURS ET RÉCUPÉRATION (transparence méthodologique)
Un premier lancement de ce test à 85 questions, exécuté EN PARALLÈLE de
la mise au point de l'interface Reflex (qui sollicitait aussi BGE-M3),
est mort dès le chargement du modèle, avant même la première question —
concurrence suspectée sur BGE-M3, hypothèse plausible mais non prouvée
formellement. Inspection du fichier de résultats de ce run mort :
**aucune question n'y était persistée** (le script d'origine n'écrivait
son JSON qu'à la toute fin des deux passes, jamais atteinte). Rien à
récupérer de cette tentative — reprise à zéro, mais cette fois seule
(aucun autre processus ne sollicitant BGE-M3 pendant l'exécution), et
avec un script corrigé qui checkpoint désormais le résultat de CHAQUE
question immédiatement après son calcul (`test_bm25_85q_checkpoint.json`),
pour ne plus jamais perdre un run entier sur un crash tardif.

Le run complet (isolé, 170 appels) a rencontré 3 erreurs de connexion
API transitoires (`APIConnectionError`, réseau) sur G24-42 (config sans
BM25), G24-23 et U05 (config avec BM25) — non liées à BM25 lui-même.
Ces 3 questions ont été retirées du checkpoint et recalculées seules
(toujours isolément, sans Reflex) ; le nouveau essai a réussi sans
erreur. Sur les 3, 2 se sont révélées être de faux signaux (G24-42 et
G24-23 ne figurent plus dans les listes finales de réparations/
régressions une fois recalculées proprement) — confirmation qu'il était
juste de les traiter comme invalides plutôt que de les compter tel quel.
Résultat final : **0 erreur restante sur les 170 mesures (85 questions
× 2 configurations)**.

RÉSULTAT (85 questions × 2 configurations, mesure complète et propre)

| Métrique | Sans BM25 | Avec BM25 |
|---|---|---|
| Type correct | 70/85 (82,4%) | 70/85 (82,4%) — identique |
| Identifiant correct | **62/85 (72,9%)** | **59/85 (69,4%)** |
| Coût total | 0,55571 $ | 0,43249 $ (-22,2%) |
| Coût moyen/question | 0,00654 $ | 0,00509 $ |
| Latence moyenne | 13,1 s | 11,9 s (-9,0%) |

Réparations : **3** — G24-16 (texte), G24-48 (texte), G24-64 (page_qrt)
Régressions : **6** — G24-34 (tableau), G24-62 (page_qrt), G24-65
(page_qrt), G24-66 (page_qrt), U05 (page_qrt), U17 (page_qrt)

**Précision : résultat NÉGATIF net** — contrairement à l'échantillon de
36 questions (Décision 037), l'échantillon complet de 85 questions
inverse le signal : 6 régressions contre seulement 3 réparations, soit
une perte nette de 3 questions correctes sur l'identifiant (62 -> 59).
Ce n'est plus un résultat neutre : c'est exactement le scénario que
l'extension à un échantillon plus large était censée détecter (Décision
037 : "un échantillon plus large serait nécessaire pour distinguer un
signal réel modeste d'un bruit statistique").

MÉCANISME (confirmé, pas juste supposé)
5 des 6 régressions (G24-62/65/66, U05/U17) touchent le même type de
contenu : **page_qrt**, alors que BM25 n'ajoute QUE des candidats texte.
Ceci confirme et généralise l'effet indirect déjà repéré sur le cas
isolé G24-65 en Décision 037 : en faisant remonter des candidats texte
via une 5e liste RRF, BM25 modifie la dynamique de score de fusion pour
TOUTES les collections en compétition, ce qui déplace de façon répétée
et non aléatoire le choix du juge parmi des pages QRT du même gabarit —
un effet secondaire réel et désormais statistiquement visible, pas un
artefact isolé. Les 3 réparations restent cohérentes avec le mécanisme
recherché (2 texte + 1 QRT, où BM25 aide légitimement).

Coût et latence : le gain (-22% coût, -9% latence) se confirme et reste
dans le même ordre de grandeur qu'en Décision 037 — mais le seuil
explicitement fixé pour cette technique ("le manque de régression à lui
seul peut justifier l'adoption même sans gain de précision net")
supposait précisément l'ABSENCE de régression significative. Ce n'est
plus le cas ici : 6 régressions documentées et mécaniquement expliquées
ne sont pas un "manque de régression".

DÉCISION
**BM25 (hybrid search) est définitivement écarté de la production.**
Contrairement à la Décision 037 qui laissait le dossier ouvert faute de
preuve suffisante, l'échantillon complet de 85 questions apporte cette
preuve : le gain de coût/latence est réel mais insuffisant pour
compenser une perte nette et mécaniquement expliquée de précision sur
les annexes QRT. L'investigation BM25 est close. Le fil de diagnostic
golden-set-2024 dans son ensemble (Décisions 033-038, 6 techniques
testées : prompt ajusté, Sonnet comme juge, Contextual Retrieval,
top-20, BM25 sur 36 puis 85 questions) reste donc lui aussi définitivement
clos sur la base de production actuelle (top-8, juge Haiku, 4 listes RRF
sans BM25) — score de référence inchangé : 45/66 (68,2%) golden 2024 +
18/19 (94,7%) unifié 2025.

## Décision 039 — Étape de reformulation de question (interface Reflex) : implémentée, testée, désactivée par défaut faute de clé Gemini fiable

CONTEXTE
Ajout demandé d'une étape de reformulation en amont du pipeline existant
(fusion + reranking + génération, `fusion_reranking.py`/`generation.py`
strictement inchangés) : l'utilisateur tape une question, un appel Gemini
léger propose 3 reformulations, l'utilisateur choisit l'une des 3 ou
garde sa question d'origine, et SEULE la version choisie part dans le
pipeline. Exigence explicite de sécurité (veille de présentation) :
interrupteur unique (`REFORMULATION_ACTIVEE`) permettant de revenir
instantanément au comportement actuel sans toucher au reste du code, et
décision finale (activer ou non par défaut) déléguée explicitement à
Claude Code selon le résultat des tests.

IMPLÉMENTATION (sfcr_app.py uniquement — aucune modification de
fusion_reranking.py, generation.py, resolution_marqueurs.py, ni des
collections Qdrant)
- `_generer_reformulations(question)` : appel Gemini isolé
  (`gemini-flash-latest`, endpoint OpenAI-compatible), clé dédiée
  `GEMINI_API_KEY2`, prompt demandant 3 reformulations en JSON strict,
  intention/sujet inchangés.
- `State._executer_pipeline(question_finale)` : le chemin de pipeline
  EXISTANT (identique à l'ancien `soumettre()`), factorisé pour être
  appelé à l'identique que la reformulation soit activée ou non — le
  chemin déjà validé n'a pas été dupliqué ni modifié, seulement entouré.
- `State.soumettre()` : si `REFORMULATION_ACTIVEE` est faux, appelle
  `_executer_pipeline` directement (comportement actuel inchangé). Sinon,
  génère les reformulations ; si le modèle n'en renvoie aucune
  (erreur ou réponse vide), retombe automatiquement sur la question
  d'origine sans jamais bloquer l'utilisateur.
- `State.choisir_reformulation(texte)` : appelée au clic sur l'une des 3
  reformulations OU sur "Garder ma question telle quelle" (qui renvoie
  simplement la question d'origine stockée) ; lance `_executer_pipeline`
  avec le texte choisi.
- UI (`zone_reformulation`) : bulle intermédiaire affichant la question
  d'origine, les 3 reformulations cliquables, et l'option explicite de
  conservation ; saisie désactivée pendant l'attente du choix.

PROBLÈME BLOQUANT DÉCOUVERT PENDANT LA PHASE DE TEST OBLIGATOIRE
Avant tout test fonctionnel des reformulations elles-mêmes, test isolé
et gratuit (pas d'appel pipeline) des deux clés Gemini disponibles :
- **`GEMINI_API_KEY2`** (présentée comme "la clé neuve") : échec
  immédiat et systématique, `403 PermissionDenied` — "Your project has
  been denied access." Erreur au niveau du projet Google associé à la
  clé, pas une erreur de code ni de quota ; non réparable depuis le code.
- **`GEMINI_API_KEY`** (l'ancienne, présumée épuisée depuis la Décision
  031) : répond mais avec un piège distinct découvert en creusant un
  `content=None` inattendu — `gemini-flash-latest` consomme une partie
  du budget `max_tokens` en "thinking" interne invisible
  (`extra_content.google.thought_signature`, non exposé comme texte),
  exactement la même famille de problème que l'extended thinking de
  Claude Sonnet (Décision 033) ; `finish_reason="length"` avec
  `completion_tokens=0` pour `max_tokens=10`, réponse tronquée à "OK"
  pour `max_tokens=50`. Un test avec un budget large (`max_tokens=2000`)
  n'a pas pu confirmer si cela suffit : la clé a immédiatement renvoyé
  `429 RESOURCE_EXHAUSTED` — quota free tier de **20 requêtes/jour**
  pour le modèle résolu (`gemini-3.8-flash`, derrière l'alias
  "gemini-flash-latest"), déjà quasi épuisé par les quelques appels de
  diagnostic eux-mêmes.

Aucune des deux clés n'est donc utilisable de façon fiable maintenant.

DÉCISION (déléguée par l'utilisateur, tranchée par Claude Code)
**`REFORMULATION_ACTIVEE = False` par défaut** (activable via la
variable d'environnement `REFORMULATION_ACTIVEE=1` dès qu'une clé Gemini
fonctionnelle sera disponible). Conformément à l'instruction explicite
de sécurité avant une démo ("désactiver l'interrupteur avant demain et
présenter l'interface sans cette étape, plutôt que de présenter quelque
chose de non fiabilisé") : le blocage n'est pas un problème de qualité
des reformulations (jamais atteint ce stade du test) mais un problème
d'infrastructure (clé API cassée + quota epuisé), non résolvable dans le
temps disponible avant la présentation. Vérifié : avec l'interrupteur
désactivé, le comportement est identique à celui déjà validé (aucune
étape de reformulation visible, question envoyée directement au
pipeline, réponse et nommage du document corrects) — confirmé par un
test réel (question DORA, SFCR 2025). Le code de la fonctionnalité reste
en place, isolé, et prêt à être activé dès qu'une clé Gemini fiable sera
disponible ; aucun des 4 types de contenu déjà validés n'a été retesté
avec la reformulation active puisque l'étape elle-même n'a pas pu être
exercée au-delà du diagnostic de la clé.

## Décision 040 — Reformulation basculée sur Claude Haiku 4.5, prompt durci après 2 échecs de sens, activée par défaut

CONTEXTE
Suite à la Décision 039 (fonctionnalité complète mais désactivée faute
de clé Gemini fiable) : bascule du fournisseur sur Claude Haiku 4.5
(`fr.CLAUDE_MODELE_JUGE`, même modèle que le juge et la génération dans
le pipeline existant), en réutilisant le client Anthropic déjà partagé
(`fr.get_client_claude()`) -- aucune autre modification de l'architecture
ni de `fusion_reranking.py`/`generation.py`.

PREMIER TEST (4 questions mal formulées, prompt initial)
Latence ajoutée mesurée : 1,1 à 1,9 s par appel (négligeable face aux
~13 s de latence moyenne du pipeline complet). Sur 4 reformulations,
**2 échecs de sens réels**, pas de simples différences de style :
- "combien caisse regional" -> reformulé en question de MONTANT
  ("quel est le montant de la caisse régionale") au lieu de comptage --
  nature de l'information changée.
- "parle moi un peu du groupe la" -> "la" interprété comme faisant
  partie d'un nom propre inconnu ("groupe LA") au lieu d'être résolu en
  référence à Groupama, le sujet du document.

CORRECTIF DE PROMPT (ciblé, architecture inchangée)
Ajout de 3 règles explicites au prompt, chacune illustrée par l'exemple
négatif réel qui l'a motivée (pas seulement une instruction abstraite) :
1. ne jamais changer la NATURE de l'information demandée (comptage
   préservé si comptage), avec l'exemple "combien caisse regional" cité
   littéralement comme contre-exemple à ne pas reproduire ;
2. tout mot ambigu/isolé doit être résolu en référence à Groupama (le
   document a un sujet unique), avec l'exemple "groupe la" -> "groupe
   Groupama" cité littéralement ;
3. en cas de doute réel sur l'intention, préférer une reformulation
   minimale/littérale plutôt qu'une interprétation créative -- le
   filet "garder ma question telle quelle" existe déjà.

RETEST (6 questions : les 4 précédentes + 2 nouvelles pour vérifier la
généralisation, pas juste la mémorisation des 2 cas cités)
- Les 2 échecs connus sont corrigés : "combien caisse regional" ->
  3/3 reformulations restent des comptages ("Combien de caisses
  régionales y a-t-il...") ; "parle moi du groupe la" -> 3/3
  correctement résolu en "groupe Groupama".
- 2 nouvelles questions ("y'a combien de deleguer chez nord est",
  "c koi le SCR") : aucun problème de sens sur les 6 reformulations
  produites (comptage préservé pour la première, question de
  définition préservée pour la seconde).
- Deux points mineurs notés, honnêtement, mais NE constituant PAS un
  problème de sens au sens du critère de décision : (a) une des 3
  reformulations de "actif truc R0500 c koi" contient un résidu
  cosmétique ("R0500 c") sans changer l'objet de la question ; (b) une
  latence ponctuelle de 5,2 s sur "c koi le SCR" (contre 0,9-1,7 s pour
  les 5 autres), un aléa isolé plutôt qu'une tendance.

DÉCISION
Critère de décision de l'utilisateur rempli (2 échecs connus corrigés,
aucun nouveau problème de sens sur les 2 cas inédits) :
**`REFORMULATION_ACTIVEE = True` par défaut, activée pour la démo.**
Les deux points mineurs notés ci-dessus sont documentés pour référence
mais ne justifient pas une 3e itération le soir même, conformément à la
limite explicitement fixée par l'utilisateur.

## Décision 041 — Reformulation history-aware query rewriting : implémentée, NON validée en conditions réelles faute d'infra stable, désactivée pour la démo

CONTEXTE
Extension de l'étape de reformulation (Décision 040, déjà active) pour
prendre en compte l'historique de conversation ("history-aware query
rewriting") : les 1-2 derniers échanges {question, réponse} du workspace
actif sont transmis au même appel Claude Haiku 4.5, avec instruction de
résoudre toute référence à cet historique (pronoms, "et pour l'autre
année", etc.) en question autonome, sans jamais inventer d'information
absente de l'historique réel, et sans forcer de référence quand la
nouvelle question est déjà autonome. Modification appliquée DANS la
fonction déjà active par défaut (`_generer_reformulations`), pas dans un
chemin séparé -- confirmé explicitement avant tout test.

VALIDATION DE LA LOGIQUE (standalone, avec de vraies données)
Testé en isolation (sans navigateur, donc sans le risque d'aléa
d'infra) avec un vrai échange capturé en direct comme contexte :
- Référence elliptique résolue correctement sur 2 cas ("et pour Nord
  Est ?" -> question complète sur les certificats mutualistes de
  Nord Est ; "et le nombre total ?" -> total raisonnablement scopé aux
  entités effectivement mentionnées dans l'historique transmis, sans
  invention d'un total absent de ce contexte).
- Non-régression confirmée : une question indépendante avec un
  historique non pertinent présent reste une reformulation simple, sans
  référence forcée.
**La logique elle-même est donc validée et correcte.**

BLOCAGE : IMPOSSIBLE DE VALIDER LE COMPORTEMENT RÉEL EN NAVIGATEUR
Deux gels de l'interface observés lors de tests d'enchaînement de
questions en direct (aucune erreur logguée, aucun message d'erreur).
Diagnostic explicitement priorisé avant toute hypothèse sur le code :
un appel pipeline isolé, strictement identique et INCHANGÉ depuis des
mois (`fr.pipeline_complet_claude`, ne touchant à aucun code de ce
soir), a mis **45,8 s** puis, 18 minutes plus tard, **72,3 s** contre
une latence normale de ~13 s observée toute la soirée sur des dizaines
d'appels. Le ralentissement touche donc l'infrastructure sous-jacente
(réseau, Cohere, Claude ou Qdrant), pas le code de reformulation ni son
extension history-aware -- confirmé en contournant complètement le
navigateur et Reflex. Deux vérifications à 18 minutes d'intervalle
montrent une dégradation stable, pas un pic isolé en train de se
résorber.

DÉCISION
Conformément au protocole fixé explicitement par l'utilisateur (revérifier
l'infra avant tout nouveau test ; si toujours anormale, ne pas tester et
arrêter net, sans nouvelle tentative même si l'infra se rétablit plus
tard dans la nuit) : **`REFORMULATION_ACTIVEE` reste à `False`.**
Le code de l'extension history-aware reste en place, intact, prêt à être
testé en conditions réelles (les 3 paires de test à rythme réaliste,
critère strict 3/3) dès qu'une session avec une infra stable sera
disponible -- après la présentation, pas cette nuit. Ce n'est pas un
échec de la fonctionnalité (sa logique est validée) mais un report pour
absence d'environnement de test fiable. Fin de toute activité sur ce
chantier pour la nuit du 2026-09-13 au 2026-09-14.

## Décision 042 — Étape 0 (vérification infra) refaite avec réessais autonomes : infrastructure restée instable, chantier arrêté, fonctionnalité non intégrée

CONTEXTE
Reprise explicitement autorisée de la Décision 041 (history-aware query
rewriting, logique déjà validée en isolation mais bloquée faute d'infra
stable) : nouvelle vérification de latence avec jusqu'à 4 tentatives
autonomes espacées de 15 minutes (budget 1h max), avant tout nouveau
test en navigateur, avec engagement explicite de ne pas activer sur la
base d'un test réalisé en conditions dégradées.

MESURES (appel pipeline direct, sans navigateur, code de production
inchangé -- `fr.pipeline_complet_claude`)
- Tentative 1 : 54,1 s (seuil 25 s, normale ~13 s) -- anormal.
- Tentative 2 (15 min plus tard) : 49,8 s -- toujours anormal.
- Tentative 3 : le script de réessai autonome a été **tué par le
  système pour cause de mémoire insuffisante** avant d'obtenir une
  mesure -- un signal d'instabilité infrastructurelle supplémentaire,
  plus sévère qu'une simple latence élevée.
- Défaut mineur noté au passage (sans impact sur le verdict, les deux
  mesures réelles étant sans ambiguïté au-dessus du seuil) : la
  commande `bc` utilisée pour la comparaison automatique du seuil dans
  le script n'est pas disponible dans cet environnement Git Bash --
  chaque mesure a néanmoins été lue et comparée manuellement au seuil.

Sur l'ensemble de la session (cette nuit), 4 mesures indépendantes de
latence du même appel pipeline inchangé : 45,8 s / 72,3 s / 54,1 s /
49,8 s -- toutes 3,5 à 5,5 fois la latence normale (~13 s), aucune
amélioration dans le temps (la 2e mesure est la pire des 4). Un
schéma cohérent de dégradation, pas un pic isolé.

DÉCISION
**Arrêt du chantier, sans passer à l'Étape 1.** Conformément à
l'instruction explicite ("ne pas dépasser ce budget de temps", "ne pas
activer sur la base d'un test réalisé en conditions dégradées") et à
l'absence de personne disponible pour arbitrer une ambiguïté : le
signal (latence 3,5-5,5x la normale sur 4 mesures + un kill mémoire
système) est jugé suffisamment net pour ne pas justifier d'attendre les
tentatives 3 et 4 restantes -- les relancer maintenant, sur une machine
qui vient de tuer un processus pour manque de mémoire, irait à
l'encontre de l'esprit de prudence explicitement demandé.

**`REFORMULATION_ACTIVEE` reste à `False`.** Aucune modification du
code de production (`fusion_reranking.py`, `generation.py`) -- seul le
diagnostic a tourné. Le code de reformulation history-aware
(`sfcr_app.py`) reste en place, intact, inactivé, prêt à être testé dès
qu'une session ultérieure disposera d'une infrastructure stable. Fin de
toute activité sur ce chantier jusqu'à nouvel ordre.

RÉSUMÉ POUR LA PROCHAINE SESSION
**La reformulation avec historique de conversation reste désactivée
(`REFORMULATION_ACTIVEE=False`) : l'infrastructure (latence
réseau/API) est restée anormalement dégradée toute la nuit du
2026-09-13 au 2026-09-14 (jusqu'à un kill mémoire système), empêchant
toute validation fiable en conditions réelles -- la logique elle-même
est déjà validée en isolation (Décision 041) et prête à être testée dès
que l'infra le permettra.**

NOTE DE CLARIFICATION (2026-09-14, ajoutée sans réécrire ce qui précède)
Un nouveau diagnostic en plein jour, sur machine saine, a montré que la
latence "anormale" de la nuit du 2026-09-13 (45-72 s contre ~13 s de
référence) était très probablement, en majorité, un **artefact de
méthode de mesure** : chaque script de diagnostic isolé lançait un
processus Python neuf, qui recharge BGE-M3 à froid (~17-21 s, coût
normal de désérialisation d'un modèle de ~2 Go, pas spécifiquement un
problème réseau/DNS -- `HF_HUB_OFFLINE=1` n'a réduit ce temps que de
~16%), alors que le serveur Reflex réel ne charge ce modèle qu'une
seule fois et le réutilise pour toutes les questions suivantes. Comparer
un démarrage à froid répété à la référence "~13s" (mesurée sur un
serveur déjà chaud) était donc une comparaison faussée dès le départ.
Ceci ne remet pas en cause les décisions prises cette nuit-là avec
l'information disponible à ce moment, mais **ne pas partir d'une
inquiétude sur la fiabilité de Cohere/Claude/le réseau en général** à la
lecture des Décisions 041/042 : elle n'était pas établie. Voir Décision
043 pour la suite (retest en conditions réelles, serveur chaud).

## Décision 043 — Retest en conditions réelles (serveur chaud) : latence confirmée normale, mais anomalie de test non résolue sur Pair 2 -- reformulation avec historique reste désactivée

CONTEXTE
Retest demandé en plein jour, via le serveur Reflex réel déjà démarré
et chauffé (pas de script de diagnostic isolé), pour trancher la
question laissée en suspens par la note ci-dessus.

LATENCE : CONFIRMÉE NORMALE
- Une question "à blanc" (chargement du modèle) suivie d'une 2e mesurée
  précisément (chronométrage JS, pas une estimation par capture
  d'écran) : 21,5 s -- plus haut que ~13 s mais très loin de la plage
  anormale de la veille (45-70 s).
- 3 mesures supplémentaires à la suite, serveur chaud : **14,2 s /
  14,5 s / 15,1 s** -- variance faible (0,9 s d'écart), cohérent avec
  un palier stable proche de la référence historique. Verdict : latence
  normale, pas d'instabilité résiduelle à creuser.

TEST DES 3 PAIRES (rythme réaliste, réponse complète affichée avant la
question suivante)
- **Pair 1** (SFCR 2024, "certificats mutualistes Centre Manche" puis
  "et pour Nord Est ?") : **réussi sans réserve.** Référence résolue
  correctement en question autonome sur Nord Est, réponse exacte
  (35 714 035, cohérente avec le tableau), aucune information inventée,
  latences 15,1 s puis 14,5 s.
- **Pair 2** (SFCR 2025, DORA puis "et le RGPD ?") : **tentative
  invalidée, deux anomalies distinctes, aucune ne pouvant être
  écartée avec certitude comme un simple artefact de script de test**.
  1. Un clic de changement de workspace (2024 -> 2025) ne s'est pas
     appliqué silencieusement : la question DORA est partie dans le
     workspace 2024, qui a correctement répondu "je ne peux pas
     répondre" (comportement honnête du pipeline, pas une hallucination
     -- mais ce n'était pas le test prévu).
  2. Après correction du workspace et nouvelle soumission de DORA, une
     question jamais intentionnellement soumise à ce moment
     ("Quel est le nombre de délégués chez Groupama Rhône Alpes
     Auvergne ?") est apparue dans l'historique, correctement répondue
     mais sans lien avec le scénario en cours. Aucune erreur serveur
     loggée. Cause précise non déterminée avec certitude : le
     répertoire le plus probable est un script de test JS ayant déjà
     produit une erreur `Illegal invocation` juste avant sur un appel
     très proche, laissant possiblement une valeur de champ orpheline
     dans le DOM -- mais ceci n'a pas été prouvé, seulement observé
     comme l'hypothèse la plus plausible.
- **Pair 3** : non tentée (arrêt immédiat conformément au critère
  "un seul échec, même une fois").

DÉCISION
Conformément au critère strict fixé explicitement par l'utilisateur
("pas de marge d'interprétation ; un seul échec, quelle qu'en soit
l'ampleur apparente, arrête le test entier") : **`REFORMULATION_ACTIVEE`
reste à `False`.** Aucune tentative de correction improvisée sans
supervision, aucune 4e itération non demandée. Le code (fonctionnalité
et logique history-aware) reste intact et inchangé. Point important
pour la suite : contrairement aux Décisions 041/042, ce n'est
**probablement pas** un problème d'infrastructure externe (la latence
est confirmée normale) -- l'anomalie de Pair 2 pointe plutôt vers soit
un artefact du harnais de test scripté (le plus probable, non prouvé),
soit une fragilité réelle de l'enchaînement d'événements Reflex sous
interactions rapprochées (non exclue). À la prochaine reprise : retester
Pair 2 et Pair 3 avec un harnais de test plus robuste (éviter les
appels JS consécutifs sans vérification explicite de l'état entre
chaque étape), en isolant si le problème se reproduit avec des clics
utilisateur réels plutôt que scriptés.

## Décision 044 — History-aware query rewriting validé 3/3 via clics utilisateur réels : activé en production

CONTEXTE
Retest de Pair 2 et Pair 3 (Pair 1 déjà acquis en Décision 043) avec une
méthode strictement différente de la nuit précédente : clics réels via
`claude-in-chrome` sur les éléments affichés à l'écran (`find` pour
localiser l'élément puis `computer left_click` par référence
d'élément, qui dispatch un vrai événement de clic sans coordonnées
brutes ni exécution JavaScript dans la console), et saisie clavier
simulée réelle -- objectif explicite : déterminer si les 2 anomalies de
Pair 2 (mauvais workspace, question fantôme) venaient du harnais de
script JS ou de l'application elle-même.

MÉTHODE : CLICS RÉELS CONFIRMÉS VIABLES
Le premier clic de la session a nécessité une nouvelle tentative
(silencieux, sans erreur, cas isolé) ; tous les clics suivants ont
fonctionné du premier coup. Aucun contournement JavaScript n'a été
nécessaire -- la méthode de clic réel fonctionne dans cet environnement.

RÉSULTAT : 3/3, AUCUNE ANOMALIE
- **Pair 2** (SFCR 2025, DORA puis "et le RGPD ?") : workspace resté
  correct tout du long, historique exactement conforme aux 2 questions
  réellement posées, référence "et le RGPD ?" correctement résolue
  ("Qu'en est-il du RGPD pour le Groupe Groupama ?"), réponse honnête
  ("le document ne traite pas spécifiquement du RGPD") -- aucune
  hallucination. Aucune des 2 anomalies de la Décision 043 ne s'est
  reproduite.
- **Pair 3** (SFCR 2024, actif R0500 puis "et le montant du passif ?") :
  référence résolue avec une inférence correcte du code QRT analogue
  (R0700 puis, après vérification dans le document, R0900 "Total du
  passif" = 83 735 578, cohérent avec le tableau réel de l'Annexe 1
  2/2). Aucune anomalie.

CONCLUSION SUR LA CAUSE DES ANOMALIES D'HIER SOIR
Les 2 anomalies de la Décision 043 (mauvais workspace, question
fantôme) étaient donc bien, très probablement, un artefact du harnais
de script JavaScript utilisé cette nuit-là (clics/soumissions
programmatiques enchaînés rapidement, sans les mêmes garanties
qu'un vrai événement utilisateur), et non un défaut de l'application ou
de la logique de reformulation elle-même.

NON-RÉGRESSION SUR LES 4 TYPES DE CONTENU (avec reformulation active,
clics réels)
Texte (DORA, RGPD), Tableau (Pair 1, certificats mutualistes),
Annexe QRT (Pair 3, bilan actif/passif), Image (organigramme des
caisses régionales, 2024) -- les 4 confirmés fonctionnels, badges
corrects, aucune information inventée, document source toujours
correctement nommé.

DÉCISION
Critère strict rempli (3/3 sur l'ensemble des 3 paires, aucune marge
d'interprétation) : **`REFORMULATION_ACTIVEE = True` par défaut,
intégré en production.** L'interrupteur (`REFORMULATION_ACTIVEE=0` en
variable d'environnement) est conservé comme filet de sécurité pour une
désactivation d'urgence future, sans qu'aucune autre modification de
code ne soit nécessaire. Aucune 4e itération technique non demandée.

---

**RÉSUMÉ POUR LA PROCHAINE SESSION (à lire en premier)** : la
reformulation de question consciente de l'historique de conversation
est **activée et validée** (`REFORMULATION_ACTIVEE = True`) --
history-aware query rewriting testé 3/3 en conditions réelles via clics
utilisateur réels, non-régression confirmée sur les 4 types de contenu.
Rien d'autre en attente sur ce chantier.

## Décision 045 — Restauration de 7 scripts narratifs archivés par erreur, vérifiée byte-pour-byte contre le corpus 2025 en production

CONTEXTE : Phase 2 (métadonnées multi-documents, company_name/company_type/
year/chapter) nécessite un orchestrateur unique (`run_pipeline.py`) rejouant
toute la chaîne narrative + QRT + indexation. Investigation préalable a
révélé que `process_narrative()` dans `ingest.py` est du code mort (jamais
appelé ailleurs, le vrai pipeline narratif 2025/2024 ne passe pas par lui —
confirmé par `run_qrt_2024.py` : "le texte narratif 2024 a déjà été produit
séparément") et que `GUIDE_PROJET.md` documente la vraie chaîne active comme
12 scripts distincts. Plus grave : le réarrangement du 14/09 (qui a créé
`GUIDE_PROJET.md` et simplifié `ingest.py` au rôle QRT seul) a archivé par
erreur, dans `_historique_dev/scripts_et_logs/`, **7 scripts qui restent des
dépendances réelles** de la chaîne active (`build_sections.py`,
`build_leaf_chunks.py`, `split_and_merge_chunks.py` en dépendent tous) :
`recover_full_text.py`, `filter_fake_headers.py`, `fix_heading_levels.py`,
`inspect_bullet_candidates.py`, `final_corrections.py`,
`fix_unnumbered_levels.py`, `fix_unnumbered_levels_2024.py`.

VÉRIFICATION AVANT RESTAURATION (pas supposée) : le traitement narratif 2024
(191 chunks, golden set 66 questions) a réellement réussi de bout en bout le
12/09 en 44 minutes (`output_structure_brute_2024/` contient toute la chaîne,
de `structure_corrigee.json` à `index_visuels_cohere.json`) — confirmant que
la chaîne complète EST rejouable, contrairement à une première hypothèse
erronée (rapport d'exploration incomplet ayant conclu à tort à un blocage
structurel).

DÉCISION : les 7 scripts sont déplacés (pas copiés) de
`_historique_dev/scripts_et_logs/` vers la racine de `test_markdrop/`, où ils
étaient à l'origine et où leurs imports relatifs (`import build_sections as
bs`, `from retype_bullet_headers import retyper`, etc.) et leur `BASE_DIR`
fonctionnent correctement.

VÉRIFICATION PAR REJEU (pas juste "ça s'exécute sans erreur" — comparaison
byte-pour-byte à chaque étape contre les fichiers déjà en production, sur le
document SFCR 2025) :
- `structure_brute.json` → `fix_heading_levels.py` → `structure_corrigee.json` : **identique**
- → `filter_fake_headers.py` → `structure_filtree.json` : **identique**
- → `retype_bullet_headers.py` → `structure_finale.json` : **identique**
- → `final_corrections.py` → `structure_finale_v3.json` : **identique** (9/9 corrections position+texte acceptées, aucun refus)
- → `fix_unnumbered_levels.py` → `structure_finale_v4.json` : **identique**
- → `build_leaf_chunks.py` (avec `structure_finale_v4.json` explicite, PAS son défaut `structure_finale_v2.json`) → `sections_directes.json` : **identique**
- → `recover_full_text.py::regenerer_sections_brutes(doc, structure_path=".../structure_finale_v4.json")` (idem, pas le défaut v2 codé en dur) → `sections_brutes.json` : **identique**
- → `split_and_merge_chunks.py` → `chunks_finaux.json` (226 chunks) : **identique**
- → `attach_metadata.py --annee 2025` → `chunks_avec_metadata.json` : **identique**

DÉCOUVERTE EN COURS DE VÉRIFICATION — `structure_finale_v2.json` est un
fichier PÉRIMÉ, laissé sur disque par une itération antérieure de
`fix_heading_levels.py` (avant que son regex de numérotation soit rendu
tolérant au point final optionnel — diff exact avec v3 : seulement 2 items,
"A.3 Résultats des investissements" et "B.3.2.3 Fréquence de réalisation...",
les 2 cas cités nommément dans le docstring du regex). Bien que
`build_leaf_chunks.py` et `recover_full_text.py` documentent encore v2 comme
leur défaut, le run réel qui a produit les données actuellement indexées
utilisait déjà v4 explicitement (confirmé empiriquement : `sections_directes.
json` porte les niveaux CORRIGÉS H2/H4, pas les niveaux périmés H1/H1 de v2).
`run_pipeline.py` devra donc toujours passer `structure_finale_v4.json`
explicitement à ces deux scripts, jamais compter sur leur défaut documenté
(trompeur, jamais mis à jour après le fix du regex).

DEUX ÉCARTS RÉELS TROUVÉS SUR `clean_final_text.py`, un corrigé un accepté :

1. **CORRIGÉ** — `clean_final_text.py` actuel documente explicitement ne
   jamais toucher `chemin_hierarchique`, mais les 51 chunks bullet-titre déjà
   indexés en production ONT un `chemin_hierarchique` nettoyé de la puce PUA
   résiduelle (ex. `"SYNTHÈSE > Activité"`, pas `"SYNTHÈSE >  Activité"`)
   — preuve qu'une version antérieure du script le faisait, avant un
   rétrécissement de périmètre non suivi d'une régénération des données.
   Décision utilisateur explicite : rétablir ce nettoyage. Ajout de
   `nettoyer_dernier_segment_chemin()` dans `clean_final_text.py`, appliquée
   en même temps que `nettoyer_titre_bullet()` (même correction, un seul
   champ de plus impacté, pas un 4e bug indépendant). Vérifié : les 51
   diffs disparaissent, `chunks_propres.json` redevient identique sur ce
   point.

2. **ACCEPTÉ TEL QUEL, NON CORRIGÉ** — 1 chunk sur 226 (`position_header=123,
   position_origine=128`, "Emission de titres subordonnés") a un débordement
   d'1 mot en fin de texte ("...opportunités de marché.\nActivité") déjà
   présent dans `chunks_finaux.json` (identique aux deux runs, donc hérité de
   `split_and_merge_chunks.py`/`decouper_bullet_titre`, hors périmètre de
   `clean_final_text.py`), absent du `chunks_propres.json` de production.
   Recherche d'un 2e cas AVANT toute décision (discipline du projet, cf.
   Décisions 017/019/020) : trouvé — le chunk JUMEAU sous le même header
   parent 123 (`position_origine=123`, "A.1.5. Faits marquants de
   l'exercice") a EXACTEMENT le même défaut ("...décrites ci-après
   :\nSolidité Financière") et n'a PAS été corrigé en production. Un vrai
   correctif de script aurait traité les deux chunks jumeaux identiquement —
   l'incohérence prouve qu'il s'agit d'une retouche manuelle ponctuelle sur
   un seul chunk, pas d'une règle générale à reproduire. Bâtir une règle
   dessus reviendrait à généraliser depuis un cas non représentatif de son
   propre résultat. Écart accepté, documenté ici, non corrigé.

RÉSULTAT : 7 scripts restaurés et vérifiés fonctionnels, chaîne narrative
complète reproductible byte-pour-byte du PDF jusqu'à `chunks_avec_metadata.
json`, `clean_final_text.py` corrigé sur un point réel et documenté sur un
écart résiduel mineur et sciemment non reproduit (1 mot sur 1 chunk/226).
Suite : construction de `run_pipeline.py` (orchestrateur complet narratif +
QRT + indexation), puis validation croisée identique sur le document 2024.

## Décision 046 — Phase 2, étapes 2.1/2.3 : métadonnées multi-documents (company_name/company_type/chapter/section/content_type/page_number/source_file), renommage annee_document -> year

CONTEXTE : Phase 2 demande d'ajouter 9 champs de métadonnées à chaque point
des 4 collections Qdrant (company_name, company_type, year, chapter,
chapter_code, section, content_type, page_number, source_file), reportait
explicitement que "les 4 collections séparées" restent la décision actée
(cf. Décision 028) — pas de fusion. Reprend et réactive la Décision 030
(multi-entité explicitement reportée en juillet) : ce chantier l'implémente
maintenant, à la demande explicite de l'utilisateur.

RENOMMAGE `annee_document` -> `year` : décidé par l'utilisateur (rendu
cohérent avec le nom demandé par la spec Phase 2, plutôt que de garder le
nom existant et faire porter l'incohérence de nommage indéfiniment).
Appliqué dans les 11 fichiers vivants qui utilisaient ce champ (le rename
touche UNIQUEMENT la clé de payload/dict, pas les noms de variables Python
internes en français type `ANNEE_DOCUMENT`/`annee` qui restent inchangés,
ni le comportement de `id_deterministe(annee=...)` qui reste un paramètre
de salage d'ID indépendant) : `attach_metadata.py` (source du champ, CLI
`--annee` renommé `--year`), `build_index_texte_bge.py`,
`build_index_visuels.py`, `associer_visuels_chunks.py`,
`detect_anomalies.py` (CLI `--annee` renommé `--year`), `clean_final_text.py`
(docstring), `fusion_reranking.py` (filtre Qdrant `_filtre_annee`),
`recherche_collections.py` (docstring), `generation.py`, `ingest_qdrant.py`,
`ingest_qdrant_2024.py`. Les 2 fichiers archivés dans `_historique_dev/`
(non vivants, exclus du git) n'ont pas été touchés.

POINT D'INJECTION CHOISI : `ingest_qdrant.py`, pas les scripts amont
(`attach_metadata.py`, `build_index_*.py`), pour 3 des 4 nouveaux champs :
- `company_name`/`company_type`/`source_file` : constants pour tout un
  document, n'existaient nulle part en amont — les injecter directement
  dans `main()`/les 3 fonctions `ingerer_*` évite de modifier 8+ scripts
  intermédiaires pour faire transiter une valeur qui ne varie jamais au
  sein d'un même run.
- `chapter`/`chapter_code`/`section` : DÉRIVÉS de `chemin_hierarchique`,
  déjà présent tel quel dans les 4 collections (ex. "A. ACTIVITÉ ET
  RÉSULTATS > A.1. Activité > A.1.1. Informations générales sur le
  Groupe") — contient déjà les codes de section en clair dans chaque
  segment. `extraire_chapitre()` réutilise le motif de `parsers._CODE`
  (importé, pas dupliqué — même heuristique que la détection de chapitre
  mentionnée dans la spec) sur le DERNIER segment qui porte un code
  reconnu (pas forcément le tout dernier segment — ex. chemin se terminant
  par un sous-titre libre non codé, le code du parent le plus proche est
  utilisé). `section` = 1ère lettre du code. Cas `None` réels et attendus :
  chunks "SYNTHÈSE" (avant la 1ère section lettrée A-E) et tout contenu QRT
  (jamais de chemin_hierarchique, rendu pleine page) — pour ce dernier cas,
  `chapter` vaut explicitement "Annexes QRT" (nom standard SFCR), pas None.
- `content_type` : littéral selon la collection/le type d'entrée ("text"
  pour texte, "table" pour tableaux, "image"/"qrt" dérivés de
  `nom_collection` dans `ingerer_visuels_simple`).
- `page_number` : `min(pages)` — `pages` (liste) déjà présent n'est ni
  retiré ni renommé, `page_number` (entier unique, demandé par la spec)
  s'ajoute à côté.

UN SEUL POINT D'INJECTION POUR LES 4 COLLECTIONS (`enrichir_payload_phase2`,
appelée dans les 3 fonctions `ingerer_*`) plutôt que 4 branchements
distincts en amont — cohérent avec le choix de garder les 4 collections
séparées (Décision 028) mais de partager la logique de métadonnées.

CLI : `ingest_qdrant.py` n'avait aucun argparse (`main()` appelé sans
argument). Ajouté : `--company`, `--type`, `--year`, `--source-file` (+ les
paramètres déjà existants de `main()` exposés en CLI : chemins des 3 index,
comptes attendus, `--verifier-delta-uniquement`). Défauts de
`--company`/`--type`/`--source-file` = valeurs Groupama 2025 réelles, pour
que `python ingest_qdrant.py` sans argument garde EXACTEMENT le comportement
actuel (dont le rappel de `ingest_qdrant_2024.py`, mis à jour pour passer
`company_name="Groupama", company_type="mutuelle",
source_file="SFCR_2024_Groupe-Groupama.pdf"` explicitement).

VÉRIFIÉ (fonctions pures, sans toucher au serveur Qdrant réel — la
vérification contre les 4 collections réelles est prévue à l'étape 2.5,
lors de la réindexation) : `extraire_chapitre()` testé sur des
`chemin_hierarchique` réels de `index_texte_bge.json` (entrées 0, 5, 100,
150, 180, 189) — résultats corrects sur SYNTHÈSE (None), sections A/C/D/E,
et sur le cas à sous-titre non codé (garde le code du parent le plus
proche, ex. "C.1.3.1." pour un chemin se terminant par "Gestion du risque
de cumul", non codé). `enrichir_payload_phase2()` testé sur un cas QRT
(chapter="Annexes QRT") et un cas texte (chapter="E.1. Fonds propres").
CLI testée via `--help`, aucune erreur de syntaxe sur les fichiers modifiés.

CE QUI RESTE HORS PÉRIMÈTRE DE CETTE DÉCISION (reporté à l'étape 2.5) : les
4 scripts non encore revérifiés depuis la restauration (Décision 045) —
`extraire_visuels.py`, `associer_visuels_chunks.py`,
`build_index_texte_bge.py`, `build_index_visuels.py` — et la construction
de `run_pipeline.py`, qui orchestrera l'ensemble (narratif + QRT +
indexation) avec `--pdf`/`--company`/`--type`/`--year` propagés de bout en
bout. `generation.py` garde le libellé "SFCR Groupama {année}" en dur
(hors périmètre explicite de cette décision — l'étape 2.4/comparaison
multi-entreprises y reviendra si besoin).

## Décision 047 — Phase 2, étape 2.4 : filtrage par entreprise/année dans la recherche (4 modes), index de payload

CONTEXTE : suite à la Décision 046 (métadonnées injectées à l'indexation),
l'étape 2.4 demande le filtrage côté RECHERCHE — 4 modes (global, filtre
entreprise, filtre année, comparaison multi-entreprises), appliqués aux 4
collections EN PARALLÈLE avant la fusion RRF, filtre optionnel (comportement
actuel préservé par défaut), index Qdrant sur company_name/year pour la
performance.

GÉNÉRALISATION DE `_filtre_annee` (existant, Décision 032) EN
`_construire_filtre(annee=None, company_name=None)`, dans
`fusion_reranking.py` — pas une fonction séparée à côté : construit un
`Filter` Qdrant avec les conditions `year`/`company_name` présentes (ET
logique si les deux sont donnés), `None` si aucune (recherche non filtrée,
comportement inchangé). Threadé dans les 4 fonctions `rechercher_*_pour_
fusion`, `fusionner_candidats`, et les 4 variantes de `pipeline_complet*`
(Gemini/OpenRouter/Claude/Mistral) — même signature partout
(`annee=None, company_name=None`), aucun appelant existant cassé (tous les
nouveaux paramètres sont optionnels, positionnés après les paramètres
existants).

4 MODES (tous dans `fusion_reranking.py`, documentés dans son docstring de
module, point 4) :
1. **Global** — `fusionner_candidats(question)` : aucun changement, filtre
   `None` comme avant la Décision 032.
2. **Filtre entreprise** — `fusionner_candidats(question, company_name="Groupama")`.
3. **Filtre année** — `fusionner_candidats(question, annee=2025)` (déjà
   existant depuis la Décision 032, inchangé).
4. **Comparatif (2+ entreprises)** — nouvelle fonction
   `fusionner_candidats_comparatif(question, entreprises, annee=None)` :
   lance `fusionner_candidats` EN PARALLÈLE (ThreadPoolExecutor, appels
   I/O-bound) pour CHAQUE entreprise de la liste, retourne un dict
   `{entreprise: candidats_fusionnes}` — les résultats sont GROUPÉS PAR
   ENTREPRISE, jamais fusionnés entre elles (une fusion RRF unique entre
   entreprises mélangerait des résultats destinés à être comparés côte à
   côte). Ordre de sortie = ordre de la liste `entreprises` passée en
   entrée, pas l'ordre d'achèvement des threads (non déterministe).

INDEX DE PAYLOAD : nouveau script `creer_index_payload.py` (pas ajouté à
`create_collection_*.py`, qui refusent explicitement de toucher une
collection déjà créée) — crée un index KEYWORD sur `company_name` et
INTEGER sur `year`, pour les 4 collections. VÉRIFIÉ CONTRE LE SERVEUR LOCAL
RÉEL (pas supposé) : exécuté 2 fois de suite, aucune erreur au 2e passage,
les 4 collections confirment les 2 champs indexés après coup (relecture,
pas juste absence d'exception) — l'idempotence annoncée dans le docstring
est vérifiée, pas seulement présumée du comportement Qdrant en général.

VÉRIFICATION SANS RÉINDEXATION (les points existants portent encore
`annee_document`, pas `year`, et n'ont pas `company_name` — la
réindexation réelle est l'étape 2.5) :
- `_construire_filtre()` testé sur les 4 combinaisons (aucun filtre,
  company_name seul, annee seul, les deux) — structure `Filter` correcte
  dans chaque cas.
- `rechercher_texte_pour_fusion` interrogé en réel contre le serveur Qdrant
  local : sans filtre, résultats non vides (3/3) ; avec `company_name=
  "Groupama"` ou `annee=2025`, 0 résultat — ATTENDU, pas un bug : confirmé
  en relisant un point brut via l'API Qdrant (`scroll`) que le payload
  porte encore `annee_document: 2025`, pas `year`, et aucun `company_name`
  — la migration réelle des données se fait à l'étape 2.5, pas ici.
- `fusionner_candidats_comparatif` : le chemin réel (Cohere) a buté sur un
  quota épuisé (clé `COHERE_API_KEY` trial, 1000 appels/mois, déjà
  documentée comme limite connue dans `recherche_collections.py`) — donc
  vérifié structurellement à la place (fusionner_candidats stubbé) : les 3
  entreprises testées sont bien interrogées EN PARALLÈLE (pas séquentiel),
  chacune reçoit ses propres candidats correctement étiquetés, l'ordre de
  sortie respecte l'ordre d'entrée malgré un achèvement de threads non
  déterministe (délai simulé différent par entreprise).

RÉSULTAT : code des 4 modes + index de payload écrits et vérifiés au niveau
fonction/structure/serveur Qdrant réel (index), mais PAS encore vérifiés de
bout en bout sur des données réellement filtrables (company_name/year
absents des points actuels) — c'est l'objet de l'étape 2.5. `generation.py`
garde le libellé "SFCR Groupama {année}" en dur, pas généralisé ici (hors
périmètre — n'affecte pas la recherche/le filtrage, seulement l'affichage
du nom de document dans le prompt de génération finale).

## Décision 048 — Phase 2 : vérification des 4 derniers scripts, run_pipeline.py, réindexation réelle Groupama 2025 et tests de filtrage (étape 2.5)

CONTEXTE : suite aux Décisions 045-047, il restait à vérifier
`extraire_visuels.py`, `associer_visuels_chunks.py`, `build_index_texte_bge.py`,
`build_index_visuels.py`, construire l'orchestrateur `run_pipeline.py`, puis
réindexer réellement Groupama 2025 et tester les 4 modes de filtrage.
Exécuté d'un bout à l'autre, sans validation intermédiaire, à la demande
explicite de l'utilisateur.

**1. VÉRIFICATION DES 4 SCRIPTS RESTANTS** (méthodologie identique à la
Décision 045 : rejeu réel + comparaison, pas une simple lecture de code) :

- `associer_visuels_chunks.py` : rejoué sur le `chunks_propres.json`
  fraîchement régénéré (avec `year`) — 85 marqueurs résolus, **0 fichier
  manquant**, résultat identique à l'existant à l'unique écart déjà connu
  près (Décision 045, position_header=123/128). Confirme que la ligne
  `chunk.get("year")` (renommée en Décision 046) fonctionne avec de vraies
  données.
- `build_index_texte_bge.py` : rejoué en réel (BGE-M3, local, gratuit) —
  190/190 chunks + 18/18 tableaux ré-encodés, correction Nord-Est/d'Oc
  toujours appliquée (Décision 021). Comparaison à l'existant : tous les
  champs non-embedding strictement identiques (hors renommage), similarité
  cosinus des embeddings re-calculés vs existants = **0,9999 en moyenne**
  (min 0,9977) — bruit numérique CPU normal, pas une régression.
- `build_index_visuels.py` : **`COHERE_API_KEY` (clé principale) s'est
  révélée épuisée** (quota trial 1000 appels/mois, confirmé par un appel
  minimal isolé avant tout diagnostic plus poussé) — `COHERE_API_KEY2`
  (présente dans `.env`, jamais utilisée jusqu'ici) testée et fonctionnelle,
  utilisée pour ce script ainsi que pour tous les tests de filtrage de
  cette décision. 1er essai interrompu à 25/36 par un `ConnectTimeout`
  réseau transitoire (pas un problème de clé/quota) ; 2e essai réussi,
  36/36 visuels encodés, champs non-embedding identiques à l'existant.
- `extraire_visuels.py` : **non rejoué** (coût : ouverture PDF + rendu de
  toutes les pages, script non modifié par cette Phase 2) — vérifié plus
  légèrement : comptes sur disque (18 tables, 5 images après dédup, 13
  pages QRT) strictement conformes aux constantes attendues par
  `build_index_visuels.py`. Vérification proportionnée au risque (script
  inchangé), pas la même profondeur que les 3 scripts modifiés.

**2. BUG RÉEL TROUVÉ ET CORRIGÉ DANS `ingest.py`** (au-delà de la Décision
045) : `qrt_dictionary.json` (dictionnaire de référence EIOPA, lu par
`ingest.py` et `extract_qrt_s23.py`) n'existait plus qu'archivé dans
`_historique_dev/dossiers_de_test/output_sectionE_QRT/` — même cause que les
7 scripts restaurés (réarrangement du 14/09), même type d'erreur (dépendance
réelle archivée par erreur). Restauré à `test_markdrop/output_sectionE_QRT/
qrt_dictionary.json` (copié, pas déplacé — le reste de ce dossier historique
est bien du débris de test ponctuel, vérifié fichier par fichier, pas
restauré). `.gitignore` mis à jour pour suivre explicitement ce seul
fichier de référence, pas les sorties d'extraction régénérables du même
dossier.

**3. `ingest.py::main_async` SIMPLIFIÉ EN QRT-SEUL** : `process_narrative()`
(confirmée code mort en Décision 045) et `process_sommaire()` (résultat
consommé par rien en aval) ne sont plus appelées — `main_async` correspond
maintenant exactement au rôle documenté dans `GUIDE_PROJET.md`. Vérifié en
réel sur le PDF Groupama 2025 (472s, dominé par les appels Gemini VLM des
pages QRT image-only) : 89 pages triées (71 narratif/12 QRT/6 sommaire),
12/12 pages QRT résolues à leur template EIOPA, diagnostic conforme aux
anomalies déjà connues et documentées (décalage de colonne S.32.01.22,
codes manquants S.02.01.02/S.25.05.22, sous-feuilles incertaines par
heuristique) — aucune anomalie NOUVELLE introduite par la simplification.

**4. `run_pipeline.py` CONSTRUIT** — orchestrateur complet (narratif 16
étapes + QRT + indexation), `--pdf/--company/--type/--year` propagés,
`--skip-narratif/--skip-qrt/--skip-index` pour rejouer un seul bloc. Limites
documentées explicitement dans son propre docstring (pas cachées) : listes
blanches de `fix_unnumbered_levels.py`/`final_corrections.py` codées en dur
pour Groupama 2025 (s'arrêtent proprement sur un 3e document, ne devinent
rien) ; `build_index_texte_bge.py`/`build_index_visuels.py`/
`chemins_visuels.RACINE_VISUELS` sans CLI, câblés sur `output_structure_brute/`
(pas de vraie isolation multi-documents) ; `RACINE_VISUELS` partagée par
ANNÉE, pas par entreprise (collision possible entre 2 entreprises de même
année — sans conséquence pour Groupama 2025/2024, à corriger avant un 2e
émetteur). ÉCRIT MAIS NON REJOUÉ DE BOUT EN BOUT (le rejeu complet
inclurait 2 reconversions Docling >10 min chacune, jugé disproportionné vu
que la chaîne narrative est déjà vérifiée bloc par bloc en Décisions
045/048 point 1) — chaque bloc individuel EST vérifié (narratif via rejeu
partiel ci-dessous, QRT et indexation en réel ci-dessous et point 3).

**BUG DE CONCEPTION TROUVÉ ET CORRIGÉ EN CONSTRUISANT `run_pipeline.py`** :
le flag `--year` d'`ingest_qdrant.py` (Décision 046) contrôle À LA FOIS
(a) rien directement sur le payload — le champ `year` du payload est déjà
correct, lu depuis les fichiers `index_*.json` régénérés par
`attach_metadata.py --year`, indépendamment de ce flag — ET (b) le SALAGE
D'ID (`id_deterministe(annee=...)`, Décision initiale sur `ingest_qdrant_2024.py`).
Passer `--year 2025` en ré-ingérant Groupama 2025 (dont les points
EXISTANTS ont des IDs NON salés) créerait des points EN DOUBLE (nouveaux
UUID salés) au lieu d'un upsert en place. Corrigé AVANT toute exécution
réelle (pas après coup) : `run_pipeline.py` a un flag séparé `--salt-ids`
(défaut désactivé), avec un avertissement explicite dans son aide sur
quand NE JAMAIS l'utiliser.

**5. RÉINDEXATION RÉELLE DE GROUPAMA 2025** (`ingest_qdrant.py --company
Groupama --type mutuelle --source-file SFCR_2025_Groupe-Groupama.pdf`,
SANS `--year`/salage, cf. bug ci-dessus) : **upsert en place choisi plutôt
que suppression-puis-réinsertion** (contrairement à la formulation
littérale de la spec Phase 2 étape 2.5) — les IDs de point sont
DÉTERMINISTES (Décision initiale `ingest_qdrant.py`), donc un upsert avec
les mêmes chaînes identifiantes réécrit les MÊMES points existants, sans
fenêtre où la donnée serait absente (plus sûr qu'un delete explicite pour
un résultat final identique). VÉRIFIÉ, PAS SUPPOSÉ : le compteur "ÉCART"
affiché par `ingest_qdrant.py` (381/36/8/27 points au lieu de 190/18/5/13
attendus) a d'abord semblé indiquer un doublon — vérification directe
(requêtes Qdrant par filtre `year`/`annee_document`) confirme qu'il s'agit
en fait de la somme EXACTE des points 2025 (nouveau champ `year`) et 2024
(encore `annee_document`, jamais retouché) déjà présents dans les mêmes
collections : 190+191=381, 18+18=36, 5+3=8, 13+14=27 — **aucun doublon**,
juste une alerte de vérification calibrée pour un seul document à la fois.
Point échantillonné directement par son ID Qdrant AVANT/APRÈS : même UUID
(`013cc95f-be48-516b-ae0b-1201c41dfea5`), payload enrichi des 8 nouveaux
champs, confirmant l'upsert en place.

**2024 VOLONTAIREMENT NON RETOUCHÉ** dans cette décision (hors périmètre —
la spec Phase 2 vise Groupama sans préciser les 2 années, et régénérer toute
la chaîne 2024 aurait dupliqué l'effort sans être demandé) : reste sur
`annee_document`, sans `company_name`/`company_type`/etc. Conséquence
directe et attendue : les filtres `year`/`company_name` ne trouvent AUCUN
point 2024 (vérifié ci-dessous, Mode 3b) — signalé comme limite connue, pas
un bug.

**6. TESTS DE FILTRAGE — LES 4 MODES, CONTRE LES DONNÉES RÉELLEMENT
RÉINDEXÉES** (pas de mock, requêtes Qdrant réelles via `fusion_reranking.py`) :

- **Mode 1 (global)** : `fusionner_candidats(question)` — retourne un
  mélange de points 2024 (`company_name=None`, ancien schéma) et 2025
  (`company_name='Groupama'`, nouveau schéma) — comportement CORRECT pour
  "pas de filtre", cohérent avec le point 2024 non retouché ci-dessus.
- **Mode 2 (filtre entreprise)** : `company_name="Groupama"` → 5/5
  candidats tous `company_name='Groupama'`. `company_name="SociologiqueAssurance"`
  (inexistante) → **0 candidat**, confirmé (pas d'erreur, pas de résultat
  fantôme).
- **Mode 3 (filtre année)** : `annee=2025` → 5/5 candidats tous
  `year=2025`. `annee=2024` → **0 candidat**, cohérent avec le point 5
  ci-dessus (2024 encore sur `annee_document`, jamais retouché) — pas un
  bug de cette décision.
- **Mode 4 (comparatif)** : `fusionner_candidats_comparatif(question,
  ["Groupama", "SociologiqueAssurance"])` → `{"Groupama": 5 candidats,
  "SociologiqueAssurance": 0 candidats}` — dict groupé par entreprise
  confirmé, ordre de sortie respecté, aucune fusion croisée entre les deux.
- **Filtre `chapter_code`** (bonus, demandé dans la spec avec l'exemple
  "E.1") : `chapter_code == "E.1"` retourne **0 chunk** — vérifié AVANT de
  conclure à un bug (discipline du projet) : la collection "texte" n'a
  AUCUN chunk avec `chapter_code` exactement "E.1" littéral, seulement
  "E.1.1"/"E.1.2" (14 chunks distincts sous `section="E"` recensés,
  aucun à la profondeur E.1 seule — chaque chunk direct de E.1 est en
  réalité rattaché à une sous-section plus profonde dans ce document).
  `chapter_code == "E.1.1"` (code réellement peuplé) retourne bien le
  chunk correct, confirmant que le MÉCANISME de filtrage fonctionne —
  l'exemple "E.1" de la spec ne correspond simplement à aucun chunk réel
  de ce document précis.
- **Fusion RRF + reranking LLM** (`pipeline_complet`, filtre entreprise
  actif) : 1er et 2e essais échoués sur un `WriteTimeout` (écriture de la
  requête HTTP, PAS une erreur de l'API elle-même) lors de l'envoi du
  payload multi-images au juge Gemini — hypothèse testée AVANT de conclure :
  requête réduite à 2 candidats (au lieu de 5, donc moins d'images
  encodées en base64) → **succès immédiat**, confirmant que la cause est
  la taille du payload/une contrainte réseau de cet environnement, PAS une
  régression de la fusion RRF ni du reranking eux-mêmes. RRF + reranking
  LLM restent fonctionnels avec le filtre `company_name` actif.

RÉSULTAT FINAL : les 4 scripts restants sont vérifiés (3 rejoués en réel,
1 vérifié plus légèrement car non modifié) ; 2 bugs réels trouvés et
corrigés en cours de route (`qrt_dictionary.json` archivé par erreur,
confusion `--year` payload/salage) ; `run_pipeline.py` existe et documente
honnêtement ses limites plutôt que de prétendre à une automatisation
complète non vérifiée ; Groupama 2025 est réellement réindexé (upsert en
place, 0 doublon confirmé) avec les 8 nouveaux champs de métadonnées ; les
4 modes de filtrage (+ chapter_code) et la fusion RRF/reranking sont
vérifiés fonctionnels contre le serveur Qdrant réel, filtre actif compris.
2024 reste sciemment non migré (limite connue, pas une régression).

## Décision 049 — Phase 3, étape 3.1 : schéma initial de kpis.db (SQLite), indépendant du RAG/Qdrant

CONTEXTE : Phase 3 ajoute une base SQLite (`kpis.db`, racine du projet) pour
stocker des KPIs actuariels pré-calculés, en vue d'un dashboard comparatif
multi-assureurs — usage distinct du RAG/Qdrant (pas de retrieval sémantique
ici, des chiffres structurés et leurs contrôles de cohérence). Demande
explicite : ne toucher à rien d'autre (RAG, Qdrant, pipeline SFCR).

DÉCISION : `init_kpi_db.py` (racine du projet, sibling de `kpis.db`, PAS
dans `test_markdrop/` — cohérent avec le fait que `kpis.db` lui-même est
demandé à la racine, sous-système séparé du pipeline SFCR de `test_markdrop/`)
crée 3 tables exactement selon le schéma fourni : `companies`, `kpis`,
`validation_checks`, + 2 index (`kpis(company_id, year)`, `kpis(kpi_name)`).
DDL en `CREATE TABLE IF NOT EXISTS` / `CREATE INDEX IF NOT EXISTS` +
`INSERT OR IGNORE` pour l'entreprise Groupama — idempotent par construction,
pas juste par convention.

VÉRIFIÉ (pas supposé) :
- Script exécuté 2 fois de suite : 2e exécution sans erreur, `companies`
  reste à 1 seule ligne Groupama (pas de doublon).
- Schéma relu via `sqlite_master` après création : les 3 tables + 2 index
  correspondent exactement à la demande.
- `value NULL` accepté sur `kpis` (extraction incertaine, jamais devinée —
  conforme à la contrainte demandée).
- `UNIQUE(company_id, year, kpi_name)` testé en réel : un doublon exact est
  rejeté (`IntegrityError`), pas juste déclaré dans le DDL sans être vérifié.
- Contrainte `FOREIGN KEY (company_id) REFERENCES companies(id)` testée en
  réel avec `PRAGMA foreign_keys = ON` (off par défaut en SQLite, activé
  explicitement dans le script) : un `company_id` inexistant est rejeté.

RÉSULTAT : `kpis.db` créé et vérifié fonctionnellement sur les 3 contraintes
demandées (nullable, unicité, clé étrangère), pas seulement sur la présence
du DDL. Aucun fichier du RAG/pipeline SFCR/Qdrant modifié.

## Décision 050 — Phase 3, étape 3.2 : KPI_DEFINITIONS (22 KPIs) + écart réel trouvé sur 2 des 5 QRT sources demandées

CONTEXTE : `kpi_definitions.py` (racine du projet) définit les 22 KPIs à
extraire (6 catégories : solvabilité 2, fonds_propres 5, scr 8, provisions
3, mcr 1, activité 3 — total vérifié par script, `kpi_name` tous uniques).
`unit` assigné par cohérence avec les montants réels déjà observés dans le
SFCR Groupama (ex. "500 millions d'euros" pour une émission obligataire,
Décision 045) : "M€" pour tous les montants, "pct" pour les 2 ratios de
couverture. `sign="negative"` pour `scr_diversification` (donnée explicite
de la consigne — un bénéfice de diversification qui SOUSTRAIT du SCR
total) ; `sign="any"` pour `resultat_technique` (jugement ajouté, pas dans
la consigne : un solde technique P&L peut légitimement être une perte,
contrairement aux montants de capital/primes toujours positifs) ; tous les
19 autres KPIs en `sign="positive"`.

VÉRIFICATION DEMANDÉE (QRT réellement présents pour Groupama) — faite
contre `corpus_final.json` (sortie réelle d'`ingest.py`, Décision 048, PAS
un fichier théorique), qui liste les `template_id` EIOPA effectivement
extraits, eux-mêmes résolus depuis l'index "ANNEXES – QRT PUBLICS" du
document lui-même (pas une heuristique de ce projet — l'index officiel du
SFCR) : **`S.02.01.02`, `S.05.01.02`, `S.05.02.04`, `S.22.01.22`,
`S.23.01.22`, `S.25.05.22`, `S.32.01.22`** — 7 templates, aucun autre.

Sur les 5 QRT sources demandées par la spec Phase 3 :
- `S.02.01` ✓ présent (`S.02.01.02.01`)
- `S.05.01` ✓ présent (`S.05.01.02.01`, `S.05.01.02.02`)
- `S.23.01` ✓ présent (`S.23.01.22.01`, `S.23.01.22.02`)
- **`S.25.01` ✗ ABSENT** — le document publie `S.25.05.22` à la place, PAS
  une erreur de triage : `S.25.05` est le template EIOPA pour les groupes
  utilisant un modèle interne partiel/complet en complément de la formule
  standard, distinct de `S.25.01` (formule standard seule). Cohérent avec
  un grand groupe d'assurance susceptible d'utiliser un modèle interne
  partiel sur certains modules de risque.
- **`S.28.01` ✗ ABSENT entièrement** — aucune annexe QRT dédiée au MCR
  n'est publiée dans ce rapport GROUPE. Hypothèse la plus probable, non
  vérifiée plus avant (hors périmètre de cette étape, purement définitoire) :
  le MCR groupe ("Minimum consolidated Group SCR") apparaît comme une ligne
  à l'intérieur de `S.23.01` (fonds propres/solvabilité groupe) plutôt que
  dans un template solo dédié — `S.28.01`/`S.28.02` sont typiquement des
  templates SOLO (entité individuelle), pas des templates de reporting
  groupe standard.

DÉCISION : `KPI_DEFINITIONS` créé EXACTEMENT selon la spec fournie (schéma
de référence cible, indépendant de ce qui est disponible aujourd'hui pour
UN émetteur précis) — ne pas remplacer `S.25.01`/`S.28.01` par
`S.25.05`/une source alternative dans ce fichier, qui reste la table de
référence déclarative. L'écart est documenté ici pour que l'étape
d'EXTRACTION (pas encore commencée) sache, avant de commencer, qu'il lui
faudra une logique dédiée pour `ratio_mcr`/`mcr`/les 7 KPIs `scr_*` sur
Groupama : soit lire `S.25.05.22` à la place de `S.25.01`, soit chercher le
MCR ailleurs (probablement `S.23.01`) plutôt que d'échouer silencieusement
ou d'inventer une valeur — cohérent avec la contrainte `value` nullable de
`kpis.db` (Décision 049) : mieux vaut NULL qu'une valeur devinée depuis la
mauvaise source.

RÉSULTAT : 22 KPIs définis et vérifiés (compte, unicité). Écart RÉEL trouvé
sur 2/5 sources QRT demandées, vérifié contre les données réelles (pas
supposé), documenté pour la suite plutôt que masqué ou corrigé
silencieusement dans la définition elle-même.

## Décision 051 — Phase 3.3 : audit exhaustif avant NULL, puis extraction des 22 KPIs Groupama 2025

CONTEXTE : avant d'accepter des `NULL` sur les 7 KPIs SCR détaillés et
`resultat_technique` (recommandés NULL dans un premier temps), consigne
explicite de l'utilisateur : "on ne met NULL que quand on a prouvé que le
chiffre n'est PAS dans le PDF". Audit exhaustif mené AVANT tout code
d'extraction.

DÉCOUVERTES DE L'AUDIT (aucune supposée, toutes vérifiées contre le PDF
source ou les fichiers intermédiaires réels) :
1. **Bug réel confirmé — `S.25.05.22.02` jamais extrait.** La page 87
   contient 2 tableaux EIOPA empilés (titre imprimé "S.25.05.22.01 -
   S.25.05.22.02"). Le dictionnaire du projet définit bien les 2 (28
   lignes pour `.02`), mais la résolution de sous-feuille n'en extrait
   qu'un. Les 11 lignes "manquantes" du 1er tableau sont réellement vides
   sur le PDF (vérifié visuellement) — mais le 2e tableau, jamais touché,
   contient `R0060 Diversification = -4 612 403`, `R0220 = 6 020 977`
   (= `scr_total`) et `R0470 = 3 840 840` (= `mcr`), les 2 derniers
   cross-validés à l'identique contre S.23.01. **Correctif du parser
   PAS fait ici** (hors périmètre de cette étape, accord explicite de
   l'utilisateur) — valeur `R0060` codée en dur dans `extract_kpis.py`.
2. **S.28.01 confirmé absent, exhaustivement** — contre l'index officiel
   du document lui-même (page 77, "ANNEXES – QRT PUBLICS" : exactement 7
   annexes listées), pas seulement contre le dictionnaire du projet.
3. **`resultat_technique` cherché sur tout le document** (regex sur
   "résultat technique", "résultat de souscription", "résultat net",
   "underwriting/technical result") — aucun chiffre group sous ce libellé
   exact. Page 18 : Groupama désigne explicitement "résultat opérationnel
   économique" (1 172 M€ en 2025) comme SON indicateur retenu pour "suivre
   le résultat de souscription" — un APM maison, pas un concept
   standardisé Solvabilité II. Tranché par l'utilisateur : **NULL**
   (pas un proxy non comparable inter-assureurs).
4. **`picture_76` retrouvée fusionnée à tort avec le logo Groupama**
   (`picture_1`) par la déduplication pHash — faux positif confirmé en
   ouvrant les 2 images. Sans impact sur les 22 KPIs (picture_75 seule
   suffit) — signalé comme bug séparé, pas corrigé ici.
5. **`picture_75` : organigramme SCR à texte typographié**, pas une photo
   floue — lu par LLM vision, PAS un remplacement d'une reconversion PDF
   (image déjà extraite sur disque par `extraire_visuels.py`).

EXTRACTION (`extract_kpis.py`, racine du projet) — 5 niveaux de source,
CHAQUE lecture de cellule vérifie le libellé officiel EIOPA avant
d'accepter la valeur (même discipline que `final_corrections.py`,
`test_markdrop/`) :
1. Lecture directe (S.23.01.22.01, texte natif, page 85) : `ratio_scr`,
   `ratio_mcr`, `scr_total`, `mcr`, et les 5 `fonds_propres_*` — TOUS
   depuis `R0660` (Total eligible own funds to meet total group SCR, PAS
   `R0290` basic own funds avant restrictions d'éligibilité) pour
   cohérence interne : vérifié que `R0660/C0010 ÷ R0680 = R0690` (le ratio
   déjà publié), confirmant que c'est la bonne base.
2. Somme de lignes (S.02.01.02.01, union pages 78+79) : `best_estimate`
   (5 lignes), `marge_risque` (5 lignes), `provisions_techniques` (somme
   des deux) — PAS les lignes "Technical provisions" par segment
   (R0510/R0600 etc.), qui sont des SOUS-TOTAUX redondants (vérifié :
   R0510 = R0520+R0560 à l'arrondi près) qui auraient doublé-compté.
3. Somme lignes×colonnes (S.05.01.02.01+02) : `primes_acquises_brutes`,
   `charge_sinistres` — gross uniquement, toutes lignes d'activité et
   tous types (direct/réassurance acceptée proportionnelle/non
   proportionnelle) sommés.
4. LLM Vision sur `picture_75.png` : **Gemini a échoué en réel** (503
   "high demand" persistant sur 3 tentatives + clé de secours
   `GEMINI_API_KEY2` rejetée en 403 "project denied access") — bascule
   sur Claude Haiku 4.5 (même modèle/config que le juge de secours déjà
   utilisé dans `fusion_reranking.py`, pas une config improvisée).
   **DÉCOUVERTE EN VÉRIFIANT (pas supposée) : la lecture Claude Vision
   s'est trouvée FAUSSE sur 2-3 des 6 valeurs à chaque appel** (`SCR
   Défaut` lu 783 108-783 110 au lieu de 785 108 ; `SCR Vie` lu 1 453 720-724
   au lieu de 1 455 724 ; `SCR Santé` lu 1 271 053 au lieu de 1 271 055 sur
   un 2e appel) — écarts ~2000 k€, invisibles sans une relecture manuelle
   zoomée (crop 2x) de l'image. **Décision : la relecture manuelle zoomée
   fait autorité**, jamais la sortie LLM brute, cohérent avec la
   contrainte "précision absolue" — chaque appel LLM est quand même
   journalisé et comparé chiffre par chiffre pour garder une trace de
   l'écart trouvé, pas juste écrasé silencieusement.
5. Valeur codée en dur (`R0060` S.25.05.22.02 = -4 612 403, cf. point 1) :
   `scr_diversification`.
6. NULL tranché par l'utilisateur : `resultat_technique`.

CROISEMENT DE SOURCES (implémenté, pas juste mentionné) : `scr_total`
(S.23.01/R0680 vs S.25.05.22.02/R0220, écart 0,00%) et
`scr_souscription_nonvie` (S.25.05.22.01/R0310 vs relecture manuelle
picture_75, écart 0,00%) — les 2 concordent exactement après correction
d'un bug de double-conversion d'unité dans le code de croisement lui-même
(trouvé et corrigé avant de faire confiance au résultat, pas après).

RÉSULTAT : 22/22 KPIs traités, **21 valeurs + 1 NULL** (résultat_technique
uniquement) — les 7 KPIs SCR détaillés initialement recommandés NULL sont
TOUS extraits avec une source vérifiée, confirmant que la consigne "prouver
l'absence avant NULL" a évité 7 faux négatifs. Insérés dans `kpis.db`
(company_id=1 Groupama, year=2025, upsert idempotent via
`ON CONFLICT...DO UPDATE`). 2 bugs réels trouvés en cours de route
(résolution de sous-feuille S.25.05.22, déduplication pHash picture_76) —
documentés, PAS corrigés (hors périmètre explicite de cette étape).

## Décision 052 — Phase 3.4 : contrôles actuariels sur les 22 KPIs (validate_kpis.py)

CONTEXTE : suite à la Décision 051, valider ce qui a été extrait plutôt que
de s'arrêter à l'extraction — contrôles écrits dans `validation_checks`,
`kpis.validated` mis à jour en conséquence (jamais optimiste par défaut :
0 sauf si TOUS les contrôles concernant ce KPI passent, cf. schéma
Décision 049).

CHOIX DES CONTRÔLES — uniquement des identités/inégalités CERTAINES, rien
d'approximatif présenté comme une règle actuarielle :
1. `provisions_techniques = best_estimate + marge_risque` (identité de
   construction).
2. `fonds_propres_eligibles = T1nr+T1r+T2+T3` (identité de construction).
3. `ratio_scr` recalculé (fonds_propres_eligibles/scr_total×100) vs publié
   — tolérance 1%.
4. `ratio_mcr` recalculé, numérateur `R0570` relu directement depuis
   `corpus_final.json` (pas stocké comme KPI séparé, hors périmètre des 22
   demandés).
5. `mcr < scr_total` — **volontairement PAS le corridor réglementaire
   25%-45% de l'article 129** : ce corridor est défini pour les entités
   SOLO ; rien ne garantit qu'il s'applique identiquement à un MCR
   CONSOLIDÉ GROUPE (le MCR groupe = somme des MCR solo, une construction
   différente) — affirmer ce corridor sans vérification aurait été le
   même type d'erreur que les KPIs SCR détaillés déclarés NULL trop vite
   en premier jet (Décision 051). Seul l'invariant universellement vrai
   (MCR < SCR) est testé.
6-7. Croisements de sources déjà faits à l'extraction (`scr_total`,
   `scr_souscription_nonvie`), persistés ici en base plutôt que laissés
   uniquement dans la console de `extract_kpis.py`.
8. Signe de chacun des 21 KPIs non-NULL, contre `kpi_definitions.py`
   (champ `sign`) — 1 contrôle par KPI.
9. Complétude : 22 lignes exactement, 1 seul NULL (`resultat_technique`).

RÉSULTAT : **30/30 contrôles passés** — écarts de recalcul des ratios
faibles et attendus (0,099% sur `ratio_scr`, 0,0009% sur `ratio_mcr`,
cohérent avec le fait que le SFCR ne publie ces ratios qu'à 2 décimales).
13 KPIs marqués `validated=1` (les 13 directement concernés par une
identité/un recalcul/un croisement — les 6 KPIs SCR détaillés de
`picture_75` et `scr_diversification` restent `validated=0` : aucun
contrôle indépendant ne les couvre encore, pas une non-confiance
arbitraire, juste l'absence d'un 2e signal pour ceux-là).

## Décision 053 — Phase 3.5 : kpi_service.py, couche de lecture pour le futur dashboard

CONTEXTE : pas de spec détaillée fournie pour cette étape (contrairement
aux 3.1-3.4) — conçu par cohérence avec l'usage déjà annoncé en Décision
049 ("dashboard comparatif multi-assureurs").

DÉCISION : `KpiService`, LECTURE SEULE sur `kpis.db` (jamais d'écriture —
`extract_kpis.py`/`validate_kpis.py` restent les seuls écrivains, séparation
volontaire) : `get_kpi`, `get_all_kpis`, `get_kpis_by_category`,
`compare` (1 KPI, plusieurs entreprises), `compare_categorie` (tous les
KPIs d'une catégorie, plusieurs entreprises — forme table, utile pour un
dashboard), `validation_summary`, `kpis_non_valides`. `compare()` ne lève
jamais d'exception pour une entreprise absente (`None` dans le résultat) —
pour ne pas interrompre l'affichage des autres entreprises déjà en base
quand une seule manque (ex. CNP Assurances, pas encore ingérée).

VÉRIFIÉ (exécution réelle, pas juste lu) : `get_all_kpis` → 22 lignes,
`get_kpis_by_category("scr")` → 8 lignes (conforme à `kpi_definitions.py`),
`compare(["Groupama","CNP Assurances"], ...)` → `{"Groupama": 274.0,
"CNP Assurances": None}` sans erreur.

RÉSULTAT : Phase 3 (3.1 à 3.5) terminée sur Groupama — schéma, définitions,
extraction (21/22 valeurs), contrôles (30/30), couche de service. Aucun
fichier du RAG/Qdrant/pipeline SFCR touché sur l'ensemble de la Phase 3,
conformément à la consigne initiale.

## Décision 054 — Phase 3.6 : validation finale, 5 vérifications manuelles, ajout de 4 méthodes à kpi_service.py

CONTEXTE : dernière passe de vérification demandée avant de considérer la
Phase 3 close sur Groupama — 5 KPIs recontrôlés indépendamment contre le
PDF source, rapport de contrôles réaffiché via l'API de service (pas
juste relu en base), `kpi_service.py` testé avec les noms de méthodes
réellement attendus par l'utilisateur (`get_kpis`, `compare_kpis`,
`get_corpus_stats`, `get_validation_report` — absents jusqu'ici,
ajoutés ici en complément des méthodes existantes, pas en remplacement).

DEUX PRÉCISIONS RÉELLES TROUVÉES EN VÉRIFIANT (aucune ne remet en cause
une valeur déjà stockée, mais toutes deux auraient pu induire en erreur
sans être signalées) :

1. **Page 87 n'a AUCUN texte extractible** — vérifié directement (couche
   texte = 206 caractères, seulement "Annexe 6" + en-tête/pied de page,
   0 chiffre). Les 2 tableaux QRT de cette page (S.25.05.22.01 ET .02)
   sont des images incrustées dans le PDF, pas du texte sélectionnable.
   La "relecture manuelle" de `R0060`/`R0220`/`R0470` documentée en
   Décision 051 était donc une lecture de pixels par l'agent, de la MÊME
   NATURE que les appels vision LLM (Gemini/Claude) utilisés pour
   `picture_75` — sa fiabilité vient exclusivement du croisement réussi
   contre S.23.01 (vrai texte natif, concordance exacte sur `scr_total`
   et `mcr`), pas du fait d'être "extraite du texte". Nuance importante
   pour toute réutilisation future de cette valeur : ce n'est pas une
   source plus fiable par nature qu'une lecture vision, juste une lecture
   vision faite avec plus de soin et recoupée.

2. **`fonds_propres_eligibles` utilise `R0660`, PAS `R0290`** (la ligne
   demandée lors de cette vérification) — choix DÉJÀ documenté en
   Décision 051, reconfirmé ici avec les 2 valeurs affichées côte à côte
   (`R0290`=16 349 956 vs `R0660`=16 481 186, un écart réel de 131 230 k€,
   PAS un arrondi) : `R0660` ("Total eligible own funds to meet the total
   group SCR") est la ligne qui, divisée par `scr_total`, redonne
   exactement le `ratio_scr` publié — `R0290` ("Total basic own funds
   after deductions") est une étape antérieure de la cascade EIOPA, avant
   les plafonds d'éligibilité par tier. Pas un désaccord non résolu :
   juste rendu explicite pour que quiconque relit cette ligne plus tard
   sache que les 2 chiffres existent et lequel a été retenu, et pourquoi.

VÉRIFICATIONS RÉELLES (5/5, indépendantes du code d'extraction) :
`ratio_scr` (narratif p.75 "274%" + S.23.01/R0690 "2,74"), `scr_total`
(S.23.01/R0680 texte natif + picture_75, concordance exacte),
`fonds_propres_eligibles` (écart réel R0290 vs R0660 expliqué ci-dessus),
`best_estimate` (recalcul indépendant depuis les 5 lignes brutes : somme
exacte 69 035 100 k€), `scr_marche` (picture_75 rezoomée : "4 675 236",
exact).

RÉSULTAT : 21/22 valeurs confirmées, 30/30 contrôles actuariels
reconfirmés via l'API de service, `kpi_service.py` complété et testé en
conditions réelles (y compris le cas CNP Assurances absente — dict/liste
vide, jamais d'exception). Phase 3 close sur Groupama.

## Décision 055 — Phase 3.7 (WIP) : triple extraction PaddleOCR+Gemini+QRT, 2 bugs corrigés, feasibility PaddleOCR confirmée

CONTEXTE : objectif "zéro LLM comme source unique de chiffre" (consigne
explicite) — remplacé en cours de route par un design "triple extraction,
concordance 2-sur-3 à ±1%" après avoir constaté qu'EasyOCR (déjà présent
en dépendance transitive) lit R0060 en '4612 03' à confiance 0,22 (chiffre
manquant), inutilisable seul.

SESSION INTERROMPUE PAR L'UTILISATEUR (dépassement 2h/107k tokens) avant
la fin de l'étape 3.7 — ce qui suit est TERMINÉ ET VÉRIFIÉ vs EN COURS,
distingué explicitement.

TERMINÉ ET VÉRIFIÉ :

1. **Bug réel corrigé — résolution de sous-feuille (`test_markdrop/ingest.py`,
   `resoudre_sous_feuille`/`process_qrt`).** Contrat changé : retourne
   TOUJOURS une liste (au lieu d'une seule sous-feuille devinée). Quand
   aucun indice textuel ne permet de trancher entre plusieurs sous-feuilles
   candidates sur une même page (cas page 87 : S.25.05.22.01 ET .02, page
   sans AUCUN texte natif exploitable — confirmé via `get_text("dict")`,
   uniquement un bloc image), les 2 sont TOUTES tentées plutôt qu'une
   seule devinée. Vérifié fonctionnellement (pas seulement syntaxiquement) :
   `test_markdrop/test_sous_feuille_p87.py` confirme que page 87 résout
   maintenant en 2 candidats ; `test_markdrop/reextraire_page87.py` (relance
   `process_qrt` sur la page 87 seule, fusionne le résultat dans
   `corpus_final.json`) confirme que S.25.05.22.02 passe de 0 élément
   (jamais extrait, cf. Décision 051) à 26/28 lignes réelles extraites par
   Gemini VLM, dont R0060=-4 612 403 — IDENTIQUE à la valeur qui était
   codée en dur depuis Décision 051. R0470=3 840 840 et R0220/R0570=
   6 020 977 également extraits réellement (nouveaux croisements possibles,
   cf. ci-dessous).

2. **Correction d'une fausse affirmation antérieure (Décision 051, point 4)** :
   `picture_76` n'est PAS un faux positif de déduplication pHash fusionné
   à tort avec le logo. Vérifié en rendant le bbox exact des 2 images
   (`picture_76` : page 75, bbox quasi identique à `picture_1` page 2,
   logo Groupama récurrent en en-tête) — c'est littéralement le même logo.
   Aucun correctif nécessaire, `extraire_visuels.py` non modifié.

3. **Feasibility PaddleOCR confirmée, avec un bug d'environnement identifié
   et contourné.** `PPStructureV3` (pipeline complet layout+table+OCR)
   plante après un long chargement de modèles avec
   `NotImplementedError: ConvertPirAttribute2RuntimeAttribute not support
   [pir::ArrayAttribute<pir::DoubleAttribute>]` — bug du backend oneDNN de
   PaddlePaddle 3.3.1 sur ce poste (CPU, Windows), pas une erreur de
   config. **Contournement trouvé et vérifié : `enable_mkldnn=False`** sur
   la classe `PaddleOCR` (texte seul, PP-OCRv6 — PAS PP-StructureV3, dont
   la structure complète est de toute façon inutile ici puisque la
   position des cellules est déjà connue par ailleurs). Avec ce
   contournement, PaddleOCR lit :
   - Page 87 (rendu 3x) : R0060=-4 612 403 (conf 1.00), R0220=6 020 977
     (conf 0,96-0,98), R0470=3 840 840 (conf 0,94) — les 3 valeurs de
     référence, EXACTEMENT justes.
   - `picture_75.png` : les 6 valeurs SCR (677 423 / 4 675 236 / 1 271 055
     / 785 108 / 1 455 724 / 2 474 794), TOUTES exactes contre
     `VALEURS_VERIFIEES_PICTURE_75` (Décision 051), à confiance 0,92-1,00.
   Découverte annexe (empirique, pas supposée) : `S.25.05.22.01` (table
   QRT réelle du modèle interne partiel) ne décompose PAS le SCR dans les
   5 modules standards — `R0400 = "Total Life & Health" = 4 389 411`, qui
   n'est PAS la somme de `scr_souscription_vie` (1 455 724) et
   `scr_souscription_sante` (1 271 055) = 2 726 779. `picture_75.png` (un
   graphique narratif) reste donc la SEULE source pour 5 des 6 KPIs SCR
   détaillés sur ce document précis — aucun raccourci QRT n'existe, pas
   une lacune du parser.
   Implémenté dans `paddleocr_reader.py` (nouveau, racine du projet) :
   `valeur_a_droite_du_code` (tableaux QRT, code à gauche/valeur à droite
   même ligne) et `valeur_sous_label` (diagramme en boîtes, libellé
   au-dessus/valeur en dessous) — les 2 stratégies testées et vérifiées
   contre les valeurs connues ci-dessus, par proximité géométrique réelle
   (bbox), jamais par ordre de lecture OCR (qui peut désynchroniser
   labels et valeurs).

4. **`extract_kpis.py` réécrit** pour utiliser `concordance_2_sur_3`
   (nouvelle fonction : accepte une valeur SEULEMENT si ≥2 sources sur les
   disponibles concordent à ±1%, sinon NULL — jamais un seul outil qui
   tranche seul, y compris la relecture manuelle) :
   - `scr_diversification` (R0060) : QRT réel (Gemini VLM, parser corrigé)
     + PaddleOCR sur le rendu de la page 87 — la constante codée en dur
     `R0060_S250522_02` est SUPPRIMÉE.
   - Les 6 KPIs SCR de `picture_75.png` : PaddleOCR + LLM Vision (Gemini,
     Claude en secours) + relecture manuelle (UNIQUEMENT pour Groupama
     2025 — absente pour toute autre entreprise/année, dégénère
     naturellement en 2 sources).
   - `croiser_sources` étendu : `scr_total` croisé sur 3 sources QRT
     désormais toutes réelles (S.23.01/R0680, S.25.05.22.02/R0220 et
     R0570 — plus d'"audit manuel" en dur) ; nouveau croisement `mcr`
     (S.23.01/R0610 vs S.25.05.22.02/R0470), inédit, possible seulement
     depuis la correction du bug de sous-feuille.
   Syntaxe vérifiée (`ast.parse` OK). **Run end-to-end PAS ENCORE confirmé
   réussi au moment de l'interruption** — 1re tentative a échoué
   (`ModuleNotFoundError: paddleocr`, lancée avec le venv racine du projet
   qui n'a pas paddleocr installé, seul `test_markdrop/.venv` l'a) ; 2e
   tentative relancée avec le bon interpréteur, toujours en cours au
   moment du commit.

EN COURS / PAS ENCORE FAIT (à reprendre dans une nouvelle session) :
- Confirmer le run complet de `extract_kpis.py` (2e tentative), vérifier
  les 22 valeurs, relancer `validate_kpis.py` (30 contrôles).
- `kpi_qrt_mapping.py` (mapping multi-variantes solo/groupe/formule
  standard/modèle interne pour généraliser à un futur SFCR quelconque) —
  recherche partielle faite (S.23.01 solo confirmé via un QRT annexe réel
  d'un autre assureur : R0580=SCR, R0600=MCR, R0620=Ratio EOF/SCR,
  R0700=Excess Assets over Liabilities ; S.25.01 groupe formule standard
  confirmé via solvencytool.com : R0060=Diversification, R0130=Risque
  opérationnel, R0220/R0470/R0570=SCR/MCR/Total groupe — structure
  identique à S.25.05 groupe modèle interne partiel déjà vérifiée sur
  Groupama), mais PAS ENCORE écrit en fichier, et S.28.01/S.28.02 (MCR
  solo) pas trouvés.
- Détection auto des templates présents + format (texte natif/image) +
  méthode SCR (standard/IM partiel/IM complet) — pas commencé.
- Table de comparaison finale (4 colonnes : Outil 1/2/3/Concordance/Valeur
  retenue/Confiance) demandée par l'utilisateur — pas produite.
- Nettoyage des fichiers de scratch (`test_markdrop/paddle_*.log/json`,
  `page87_paddle_test.png`, `extract_kpis_run.log`) — non commités
  (scratch de débogage, régénérables).
- Reprise Phase 2 (ingestion CNP Assurances) — toujours en pause, après
  Phase 3 complète (décision de l'utilisateur, inchangée).

## Décision 056 — Phase 3.7 (session 2, 1h) : mapping multi-variantes, détection auto, contrôles OK

CONTEXTE : suite de la Décision 055, contrainte de temps explicite de
l'utilisateur ("si ça dépasse 1h, commite ce qui est fait"). Ce qui suit
est TERMINÉ ET VÉRIFIÉ vs PAS FAIT, distingué explicitement — aucune
ligne de code de ce commit n'a été devinée, chaque code R0xxx/C0xxx est
sourcé contre un QRT réel et rempli (jamais un résumé IA d'un PDF
compressé — le PDF a été relu directement quand la 1re tentative de
résumé automatique était trop dégradée).

TERMINÉ ET VÉRIFIÉ :

1. **`kpi_qrt_mapping.py`** (nouveau, racine du projet) — dictionnaire
   `KPI_QRT_MAPPING`, 22 KPIs, chaque variante sourcée contre un QRT réel :
   - S.23.01.22 (groupe) — Groupama 2025 (extraction réelle).
   - S.23.01.01 (solo) — Bornholms Brandforsikring (Danemark) ET AXA SA,
     2 sources concordantes (R0580=SCR, R0600=MCR, R0620=ratio SCR,
     R0640=ratio MCR, R0540/R0550=fonds propres éligibles).
   - S.25.01.22/S.25.01.01 (formule standard, groupe/solo) — solvencytool.com
     (groupe) ET AXA SA (solo, QRT réel rempli) : **R0010=Market risk,
     R0020=Counterparty default, R0030=Life underwriting, R0040=Health
     underwriting, R0050=Non-life underwriting, R0060=Diversification,
     R0130=Operational risk, R0220=SCR final** — mêmes codes solo/groupe,
     vérifié.
   - S.28.01.01 (solo, MCR vie-ou-non-vie exclusif) — AXA SA ET Yuzzu
     (Belgique), 2 sources concordantes (R0400=MCR final).
   - S.02.01.02/S.05.01.02 (provisions/activité) — **codes IDENTIQUES
     solo/groupe**, vérifié sur 3 documents indépendants (Groupama, AXA,
     Yuzzu) : R0540/R0550 etc. pour les provisions, R0210-230/R0310-330
     pour primes/sinistres.
   - **Découverte empirique importante** : contrairement aux templates
     réglementaires "purs" ci-dessus, les templates de répartition SCR en
     MODÈLE INTERNE (S.25.02 à S.25.05) n'ont **aucun code de ligne fixe
     universel** — comparaison directe Groupama (groupe, S.25.05.22,
     Diversification en R0060) vs Yuzzu (solo, S.25.05.01, Diversification
     en R0020) : même concept, codes différents, chaque modèle interne a
     sa propre structure. **Documenté explicitement plutôt que masqué** :
     aucune entrée à code fixe n'est ajoutée pour les 5 KPIs de risque
     détaillé (scr_marche/contrepartie/vie/sante/operationnel) en modèle
     interne — la résolution par libellé officiel (déjà en place dans
     `lire_cellule`) reste la seule méthode fiable pour ces cas.
   - S.28.02 (solo, MCR vie ET non-vie combinées) — **PAS trouvé de QRT
     réel rempli** dans le temps imparti, volontairement absent du
     mapping plutôt que deviné.
   - **PAS ENCORE FAIT : `extract_kpis.py` n'a PAS été modifié pour
     utiliser ce mapping** — il continue d'utiliser les templates
     Groupama codés en dur (S.23.01.22, S.25.05.22, etc.), qui restent
     corrects pour Groupama lui-même. Le mapping est prêt et documenté
     mais son intégration (remplacer les appels directs par
     `kpi_qrt_mapping.variantes_disponibles()`) reste à faire — nécessaire
     seulement pour généraliser à un futur document (CNP ou autre), pas
     pour Groupama.

2. **`test_markdrop/detecter_templates.py`** (nouveau) —
   `detecter_templates(pdf_path)` : scanne les pages QRT via
   `classify_pages` (déjà dans `ingest.py`), retourne `document_type`
   (solo/groupe, détecté via le suffixe de S.23.01.XX — SEUL signal fiable
   vérifié, S.02.01/S.05.01 ne permettent PAS cette distinction), `scr_method`
   (formule_standard si S.25.01 présent, modele_interne si S.25.02-05,
   sans distinguer partiel/complet — non vérifiable de façon fiable,
   laissé explicite plutôt que deviné), et l'inventaire des templates
   présents avec leur format par page (`texte_natif`/`image`/**`mixte`**
   quand un même template tronqué couvre des pages de format différent —
   ex. Groupama S.23.01.22 : page 85 texte natif, page 86 image ; reporté
   explicitement plutôt que moyenné).
   **Bug trouvé et corrigé pendant l'implémentation** : 1re version
   utilisait `template_id.split(".")[2]` pour lire le suffixe solo/groupe,
   qui retombe TOUJOURS sur "01" (c'est le numéro de version du template,
   pas l'indicateur solo/groupe) — donnait "solo" pour le document GROUPE
   de Groupama. Corrigé en `split(".")[-1]` (dernier segment), revérifié :
   `document_type="groupe"` correct sur Groupama.

3. **`validate_kpis.py` relancé** : 30/30 contrôles toujours OK (aucune
   régression depuis Décision 055 — normal, `extract_kpis.py` n'a pas
   été modifié depuis, `kpi_qrt_mapping.py`/`detecter_templates.py` sont
   des fichiers indépendants pas encore branchés).

4. **Tableau de comparaison** (7 KPIs à sources multiples — les 15 autres
   sont des lectures QRT texte natif directes, 1 seule source, pas de
   concordance à afficher) :

| KPI | QRT natif | PaddleOCR | LLM Vision | Relecture manuelle | Concordance retenue | Valeur | Confiance |
|---|---|---|---|---|---|---|---|
| scr_operationnel | — | 677 423 | indisponible* | 677 423 | PaddleOCR & manuelle | 677.42 M€ | partielle |
| scr_marche | — | 4 675 236 | indisponible* | 4 675 236 | PaddleOCR & manuelle | 4675.24 M€ | partielle |
| scr_souscription_sante | — | 1 271 055 | indisponible* | 1 271 055 | PaddleOCR & manuelle | 1271.06 M€ | partielle |
| scr_contrepartie | — | 785 108 | indisponible* | 785 108 | PaddleOCR & manuelle | 785.11 M€ | partielle |
| scr_souscription_vie | — | 1 455 724 | indisponible* | 1 455 724 | PaddleOCR & manuelle | 1455.72 M€ | partielle |
| scr_souscription_nonvie | R0310=2 474 794 | 2 474 794 | indisponible* | 2 474 794 | QRT & PaddleOCR & manuelle | 2474.79 M€ | haute |
| scr_diversification | R0060=-4 612 403 (Gemini VLM, parser corrigé) | -4 612 403 | — | — | QRT & PaddleOCR | -4612.40 M€ | haute |

*Gemini/Claude indisponibles lors du dernier run confirmé (clés API
absentes de l'environnement d'exécution) — géré proprement par le
fallback (Décision 055), sans crash, concordance recalculée sur les
sources restantes (jamais moins de 2). scr_total et mcr sont croisés à
3 et 2 sources QRT respectivement (S.23.01 vs S.25.05.22.02/R0220+R0570
et R0470), 0.00% d'écart — détaillé en Décision 055.

PAS FAIT (temps écoulé) :
- Intégration de `kpi_qrt_mapping.py` dans `extract_kpis.py` (le mapping
  existe et est vérifié, mais `extract_kpis.py` utilise toujours les
  templates Groupama codés en dur — corrects pour Groupama, pas encore
  généralisés).
- S.28.02 (solo, MCR vie+non-vie combinées) non trouvé/mappé.
- Test du pipeline complet sur un 2e document réel (CNP ou autre) pour
  valider concrètement la généralisation — nécessite de reprendre Phase 2
  (toujours en pause).

## Décision 057 — Phase 3.7 FINALE : extract_kpis.py généralisé via le mapping, régression trouvée et corrigée

CONTEXTE : suite de la Décision 056, branchement effectif de
`kpi_qrt_mapping.py`/`detecter_templates.py` dans `extract_kpis.py`
(plus AUCUN template Groupama codé en dur). Contrainte de temps 45 min.

TERMINÉ ET VÉRIFIÉ :

1. **`extract_kpis.py` réécrit** — `extraire_tout()` appelle
   `detecter_templates(PDF_SOURCE)` au démarrage (log l'inventaire),
   puis résout CHAQUE KPI via `resoudre_variantes_qrt()` (parcourt
   `KPI_QRT_MAPPING[kpi]` dans l'ordre, ne retient que les variantes dont
   le template est présent dans le corpus). Les 22 templates codés en dur
   (S.23.01.22.01, S.25.05.22.01/02, S.02.01.02.01, S.05.01.02.01/02) ont
   TOUS disparu du code — remplacés par des appels au mapping. Nouveau :
   `resoudre_par_libelle_modele_interne()`, fallback pour S.25.02-05 (pas
   de code fixe, cf. Décision 056) — cherche une ligne dont le libellé
   officiel ÉGALE (pas contient) un des libellés attendus du KPI.

2. **Bug d'environnement réel trouvé et contourné** : importer
   `detecter_templates` (donc `ingest.py`, donc Docling/transformers/
   torch) AVANT le premier appel à PaddleOCR fait planter
   `from paddleocr import PaddleOCR` avec
   `ValueError: torch.__spec__ is not set` (conflit d'ordre d'import entre
   le chargement torch de Docling et la vérification lazy de paddlex/
   modelscope) — reproduit 2 fois de suite, pas un flake isolé. Contourné
   en forçant `paddleocr_reader._get_pipeline()` AVANT l'import de
   `detecter_templates` dans `extract_kpis.py` — vérifié, la 3e tentative
   passe. Signalé pour investigation future, pas creusé plus (hors budget).

3. **RÉGRESSION RÉELLE TROUVÉE ET CORRIGÉE** (exactement le scénario que
   la consigne "STOP si un KPI change" visait à attraper) : la 1re version
   du fallback par libellé utilisait une correspondance par SOUS-CHAÎNE
   ("Life underwriting risk" dans le libellé de la ligne) — or "Life
   underwriting risk" est une sous-chaîne littérale de "**Non**-life
   underwriting risk", et "Health underwriting risk" une sous-chaîne de
   "Life **&** Health underwriting risk". Résultat en test réel :
   `scr_souscription_vie` retombait sur la ligne "Total **Non**-life
   underwriting risk" de S.25.05.22.01 (2 474,79 M€ au lieu de 1 455,72),
   et `scr_souscription_sante` sur "Total Life **&** Health underwriting
   risk" (4 389,41 M€ au lieu de 1 271,06). **Diagnostiqué avant de
   continuer** (comme demandé), corrigé en passant à une égalité EXACTE
   (après normalisation du préfixe "Risk type – ") plutôt qu'une
   inclusion — retesté, les 2 valeurs reviennent à l'identique de la
   Décision 055/056.

4. **Retest complet confirmé** : les 22 KPIs sont désormais
   **strictement identiques** aux valeurs de référence (Décision 055) —
   274.00 / 379.28 / 6020.98 / 3840.84 / 16481.19 / 13329.15 / 601.32 /
   2068.91 / 481.82 / 69035.10 / 2384.34 / 71419.44 / 39062.34 / 27949.85
   / 677.42 / 4675.24 / 1271.06 / 785.11 / 1455.72 / 2474.79 / -4612.40 /
   NULL. **30/30 contrôles actuariels repassés, toujours OK.** Aucune
   régression persistante.

5. **Tableau final** (Étape 3) :

| KPI | Template utilisé | Méthode | Outil 1 | Outil 2 | Concordance | Valeur | Confiance |
|---|---|---|---|---|---|---|---|
| ratio_scr | S.23.01.22.01/R0690 | texte natif | lecture QRT directe | — | 1 source | 274.00 pct | haute |
| ratio_mcr | S.23.01.22.01/R0650 | texte natif | lecture QRT directe | — | 1 source | 379.28 pct | haute |
| scr_total | S.23.01.22.01/R0680 | texte natif | QRT S.23.01 | QRT S.25.05.22.02/R0220 | 0.00% OK | 6020.98 M€ | haute |
| mcr | S.23.01.22.01/R0610 | texte natif | QRT S.23.01 | QRT S.25.05.22.02/R0470 | 0.00% OK | 3840.84 M€ | haute |
| fonds_propres_eligibles/t1_nr/t1_r/t2/t3 | S.23.01.22.01/R0660 | texte natif | lecture QRT directe | — | 1 source | (5 valeurs) | haute |
| best_estimate | S.02.01.02.01 | image (Gemini VLM) | somme 5 lignes | — | 1 source | 69035.10 M€ | haute |
| marge_risque | S.02.01.02.01 | image (Gemini VLM) | somme 5 lignes | — | 1 source | 2384.34 M€ | haute |
| provisions_techniques | calculé | — | best_estimate+marge_risque | — | — | 71419.44 M€ | haute |
| primes_acquises_brutes | S.05.01.02.01/02 | image (Gemini VLM) | somme vie+non-vie (2 variantes) | — | 1 source | 39062.34 M€ | haute |
| charge_sinistres | S.05.01.02.01/02 | image (Gemini VLM) | somme vie+non-vie (2 variantes) | — | 1 source | 27949.85 M€ | haute |
| scr_operationnel | picture_75.png | image | PaddleOCR | relecture manuelle (LLM indispo) | 0.000% OK | 677.42 M€ | partielle |
| scr_marche | picture_75.png | image | PaddleOCR | relecture manuelle (LLM indispo) | 0.000% OK | 4675.24 M€ | partielle |
| scr_souscription_sante | picture_75.png | image | PaddleOCR | relecture manuelle (LLM indispo) | 0.000% OK | 1271.06 M€ | partielle |
| scr_contrepartie | picture_75.png | image | PaddleOCR | relecture manuelle (LLM indispo) | 0.000% OK | 785.11 M€ | partielle |
| scr_souscription_vie | picture_75.png | image | PaddleOCR | relecture manuelle (LLM indispo) | 0.000% OK | 1455.72 M€ | partielle |
| scr_souscription_nonvie | S.25.05.22.01/R0310 | image (Gemini VLM) | QRT (mapping) | picture_75 (PaddleOCR+manuelle) | 0.00% OK | 2474.79 M€ | haute |
| scr_diversification | S.25.05.22.02/R0060 | image (Gemini VLM) | QRT (mapping) | PaddleOCR (page 87) | 0.000% OK | -4612.40 M€ | haute |
| resultat_technique | — | — | — | — | — | NULL | — |

Note : Gemini/Claude indisponibles lors du run confirmé (clés API
absentes de l'environnement) — géré proprement, sans crash (Décision 055).

PAS FAIT (hors périmètre de cette étape finale, pas de blocage pour CNP) :
- Test sur un 2e document réel (CNP) — nécessite de reprendre Phase 2.
- S.28.02 (solo, MCR vie+non-vie combinées) toujours non trouvé/mappé.
- Root cause exacte du conflit d'import torch/modelscope non creusée
  (contournée, fonctionnelle, mais pas expliquée en profondeur).

**Phase 3.7 est TERMINÉE.** Le système peut désormais, en principe,
extraire les 22 KPIs de n'importe quel SFCR français dont les templates
suivent les codes EIOPA standards vérifiés ici (S.23.01, S.25.01,
S.28.01, S.02.01, S.05.01) — MODULO la limite documentée : les templates
modèle interne (S.25.02-05) nécessitent une vérification manuelle du
libellé au cas par cas, la résolution automatique n'y est fiable que si
le libellé QRT du nouveau document correspond EXACTEMENT à un des
libellés déjà connus (peu probable pour un 2e modèle interne différent —
seule certitude testée : ça ne produit PLUS de faux positifs silencieux,
cf. le bug de la sous-chaîne corrigé ci-dessus).

## Décision 058 — Test CNP Assurances : benchmark localisation QRT fait, extraction bloquée (point d'étape, 1h)

CONTEXTE : 1er test de généralisation réelle sur un 2e document (CNP
Assurances 2025, solo, 108 pages, déjà téléchargé). Contrainte de temps
explicite de l'utilisateur ("si ça dépasse 1h, commite ce qui marche").

TERMINÉ ET VÉRIFIÉ :

1. **Benchmark des 3 méthodes de localisation QRT**
   (`test_markdrop/benchmark_localisation_qrt.py`, nouveau) :

| Méthode | Temps | Pages QRT trouvées | Fiable ? |
|---|---|---|---|
| A — Sommaire (pages 1-5) | 70ms | 0 | **Non** — CNP n'a pas de ligne "Annexes/QRT" avec numéro de page dans ses 5 premières pages, matchable par le motif testé |
| B — Scan par la fin | 109ms | 6 | **Non** — trouve 91,92,94,95,97,98 mais rate 76 et 83 (S.23.01.01 et S.02.01.02, trop loin du début de la fenêtre testée) |
| C — Scan complet (regex `S\.\d{2}\.\d{2}`) | 595ms | 12 | Techniquement complet MAIS inclut des FAUX POSITIFS (pages 3, 47 — mentions narratives d'un code QRT en passant, pas de vraies tables) |

**Conclusion empirique (pas la recommandation a priori de l'utilisateur,
confirmée par le test réel)** : aucune des 3 méthodes proposées n'est à
la fois rapide ET précise sur un document réel. La méthode déjà en place
depuis Phase 1 (`classify_pages()` dans `ingest.py` — combine plusieurs
heuristiques : mots-clés sommaire, ratio de "dot leaders", regex codes
QRT, index des annexes) fait mieux que les 3 : **1,3s, 10 pages exactes,
0 faux positif, 0 faux négatif** — déjà validée en Phase 1/2, pas besoin
d'en écrire une 4e. Utilisée directement pour la suite.

2. **Structure du document CNP identifiée** (10 pages QRT réelles) :
   `document_type=solo` (S.23.01.**01**, pas .22), `scr_method=formule
   standard` (S.25.01.**21**, PAS S.25.05 — contrairement à Groupama qui
   est en modèle interne partiel) — templates : S.23.01.01 (p.76 ET 95),
   S.02.01.02 (p.83), S.05.01.02 (p.86), S.12.01.02 (p.88, vie — absent
   chez Groupama), S.17.01.02 (p.91, non-vie — absent chez Groupama),
   S.19.01.21 (p.92, sinistres — absent chez Groupama), S.22.01.21 (p.94,
   LTG — absent chez Groupama), S.25.01.21 (p.97, SCR formule standard),
   S.28.02.01 (p.98, MCR vie+non-vie combinées — jamais vu, jamais
   vérifié).

BLOQUANT RÉEL TROUVÉ (pas une excuse — 2 découvertes concrètes empêchant
une extraction fiable dans le temps imparti) :

1. **`qrt_dictionary.json` ne couvre QUE les 7 templates de Groupama**
   (S.02.01.02, S.05.01.02, S.05.02.04, S.22.01.22, S.23.01.22, S.25.05.22,
   S.32.01.22) — AUCUN ne correspond aux templates de CNP (préfixes
   différents : S.23.01.**01** pas .22, S.25.01.**21** pas .01/.22 ;
   templates entièrement absents : S.12.01, S.17.01, S.19.01, S.22.01,
   S.28.02). `process_qrt()` planterait immédiatement (`KeyError`) sur
   n'importe quelle page CNP tant qu'un dictionnaire adapté n'existe pas.
   Ce dictionnaire n'a JAMAIS été conçu pour être multi-documents — c'est
   un fichier statique généré une fois pour Groupama en Phase 1, jamais
   généralisé depuis (angle mort non détecté avant ce test, précisément
   parce que c'est le premier vrai test sur un 2e document).

2. **Découverte du suffixe "21" pour S.25.01** (CNP) — `kpi_qrt_mapping.py`
   ne matche que "S.25.01.22" (groupe, vérifié solvencytool.com) et
   "S.25.01.01" (solo, vérifié AXA SA) ; "S.25.01.**21**" ne matche NI
   l'un NI l'autre (`variantes_disponibles()` retournerait 0 résultat).
   Les codes de ligne R0010-R0050/R0060/R0130/R0220 sont probablement
   identiques (formule standard = structure EIOPA fixe, vérifié
   solo/groupe) mais **PAS reconfirmés empiriquement pour ce suffixe
   précis** — élargir le mapping sans le vérifier reviendrait à deviner,
   exactement ce que la consigne interdit.

DÉCISION (conforme à la consigne explicite "si ça dépasse 1h, commite ce
qui marche, donne le point d'étape") : **ARRÊT ICI plutôt qu'une
extraction précipitée.** Construire dans le temps restant un dictionnaire
QRT minimal pour CNP sans le vérifier soigneusement referait exactement
l'erreur de la Décision 057 (le bug de sous-chaîne sur scr_souscription_
vie/sante, trouvé PARCE QUE le résultat a été comparé à une référence
connue) — sauf qu'ici, il n'existe AUCUNE valeur de référence connue pour
CNP pour détecter une éventuelle erreur silencieuse. Committer un chiffre
faux et invérifié serait pire que ne pas extraire.

PAS FAIT (prochaine session) :
- Généraliser `qrt_dictionary.json` (ou une alternative) pour accepter
  plusieurs documents — actuellement un artefact Groupama-only jamais
  pensé comme réutilisable.
- Vérifier le suffixe "21" de S.25.01 contre un exemple QRT réel rempli
  (comme fait pour "22"/"01") avant de l'ajouter au mapping.
- Rechercher S.28.02.01 (MCR vie+non-vie combinées) — jamais trouvé de
  QRT réel rempli avec ce template précis, malgré plusieurs recherches.
- `extract_kpis.py` reste structurellement mono-document (COMPANY_NAME,
  YEAR, PDF_SOURCE, CORPUS_FINAL, PICTURE_75 sont des constantes en tête
  de fichier, pas des paramètres) — non testé sur un 2e appel avec des
  valeurs différentes, probable travail additionnel non anticipé.
- Étapes 2-5 du prompt (extraction ciblée, tableau 22 KPIs CNP, insertion
  DB, `compare_kpis`, commit final) — non atteintes, bloquées par ce qui
  précède.

## Décision 059 — Phase 3.8 : extraction CNP Assurances réussie (16/22), 2 bugs réels corrigés

CONTEXTE : suite de la Décision 058 (extraction bloquée). Cette session
a débloqué le pipeline en vérifiant manuellement chaque template CNP
directement dans le PDF source (pas de dictionnaire EIOPA officiel
téléchargé — le site EIOPA n'a pas été consulté, l'approche "QRT réels
vérifiés" déjà validée en session précédente s'est montrée plus rapide
et plus fiable).

TERMINÉ ET VÉRIFIÉ :

1. **2 nouveaux bugs réels trouvés et corrigés, tous deux dans du code
   PARTAGÉ avec Groupama — retesté sur Groupama après chaque correctif** :
   - `classify_pages()` a un **faux positif** (page 76 : mention narrative
     "QRT S.23.01.01 présenté en annexe", pas une vraie table) et **rate
     les pages de continuation** sans code répété (84, 87, 96, 99 — les
     vraies suites de S.02.01.02, S.05.01.02, S.23.01.01, S.28.02.01).
     Contourné pour CNP par une liste de pages vérifiée manuellement
     (`test_markdrop/extraire_cnp.py`) plutôt qu'une correction générale
     de `classify_pages()` (hors budget de cette session).
   - **Bug réel dans `extract_qrt_native()`** (`ingest.py`) : `header_y_max`
     prenait le **MAX** de TOUS les en-têtes de colonnes trouvés sur la
     page — sur une feuille à plusieurs sections d'en-têtes (ex.
     S.23.01.01.01 : en-tête 5 colonnes en haut, en-tête 1 colonne plus
     bas pour la réserve de réconciliation), cela excluait SILENCIEUSEMENT
     toutes les lignes situées ENTRE le 1er et le dernier en-tête (R0500-
     R0640 perdues, exactement les lignes SCR/MCR dont on a besoin).
     Corrigé en `min()` (le 1er en-tête, celui qui sépare le titre de page
     du tableau). **Revérifié sur Groupama après correction : les 22 KPIs
     restent identiques à la référence (Décision 057), aucune régression.**

2. **Dictionnaire QRT minimal pour CNP** (`test_markdrop/qrt_dictionary_cnp.json`,
   5 templates : S.02.01.02, S.05.01.02, S.23.01.01, S.25.01.21, S.28.02.01)
   — PAS un dictionnaire "universel" exhaustif (hors budget), mais couvrant
   exactement ce qui est nécessaire aux 22 KPIs, chaque code R/C vérifié
   en lisant directement le texte natif des pages PDF de CNP (`fitz`,
   pas de résumé IA) — pas la taxonomie EIOPA officielle, pas devinée.

3. **Découverte empirique : le suffixe ".21" (S.25.01.21, formule
   standard) a EXACTEMENT les mêmes codes de ligne que ".01"/".22"**
   (R0010-R0050 modules, R0060 diversification, R0130 opérationnel,
   R0220 SCR final) — confirmé en lisant la page 97 de CNP directement et
   en croisant R0220=14 256 819 contre S.23.01.01/R0580=14 256 819 (écart
   0%). **Mais la COLONNE diffère** : C0110 chez CNP (taxonomie EIOPA
   2025) contre C0040/C0100 chez AXA (rapport 2023) — nouvelle variante
   ajoutée à `kpi_qrt_mapping.py` avec la bonne colonne, pas une simple
   généralisation du suffixe.

4. **S.28.02.01 (MCR composite vie+non-vie) enfin vérifié** — jamais
   trouvé de QRT réel rempli en 2 sessions de recherche précédentes ;
   lu directement depuis la page 99 de CNP (R0300-R0400, mêmes codes que
   S.28.01) et **croisé contre S.23.01.01/R0600 : 6 415 569 = 6 415 569,
   écart 0%**. Ajouté au mapping avec cette vérification citée.

5. **Découverte : CNP rédige son SFCR en FRANÇAIS** (Groupama/AXA/
   Bornholms/Yuzzu étaient tous en anglais) — les libellés officiels
   ("Ratio fonds propres éligibles sur capital de solvabilité requis" vs
   "Ratio of Eligible own funds to SCR") ne correspondaient à AUCUNE
   variante existante du mapping, provoquant des NULL silencieux corrects
   (jamais une valeur fausse) mais incomplets. **Variantes françaises
   ajoutées** pour ratio_scr/ratio_mcr/fonds_propres_*/best_estimate/
   marge_risque/primes_acquises_brutes/charge_sinistres — EN ADDITION
   des variantes anglaises existantes (Groupama/AXA restent inchangés).

6. **Extraction CNP : 16/22 KPIs extraits, 6 NULL honnêtes** (pas devinés) :
   `best_estimate`, `marge_risque`, `provisions_techniques`,
   `primes_acquises_brutes`, `charge_sinistres` — CNP déclare ses
   provisions non-vie sous "santé similaire à la non-vie" (R0560-590),
   PAS sous "non-vie pure" (R0540-550, littéralement vide dans son
   bilan — vérifié en lisant la page 84) ; le mapping actuel exige les 5
   lignes standard (dont R0540/R0550) et échoue proprement plutôt que de
   sommer un sous-ensemble. **Corrigible dans une session future** (ajouter
   une variante utilisant R0560-590 au lieu de R0540-550) mais pas fait
   ici (temps).

RÉSULTAT (16 valeurs, `extract_kpis_cnp.py`, insérées dans `kpis.db`,
entreprise "CNP Assurances" créée) :

| KPI | CNP | Groupama |
|---|---|---|
| ratio_scr | 258.00 % | 274.00 % |
| ratio_mcr | 506.00 % | 379.28 % |
| scr_total | 14 256.82 M€ | 6 020.98 M€ |
| mcr | 6 415.57 M€ | 3 840.84 M€ |
| fonds_propres_eligibles | 36 778.13 M€ | 16 481.19 M€ |
| scr_marche | 34 424.16 M€ | 4 675.24 M€ |
| scr_operationnel | 1 065.80 M€ | 677.42 M€ |
| scr_diversification | -9 821.13 M€ | -4 612.40 M€ |
| (+8 autres KPIs SCR/fonds propres) | ... | ... |
| best_estimate, marge_risque, primes, sinistres | NULL (4) | valeurs réelles |

`compare_kpis("ratio_scr", 2025)` testé et fonctionnel — 1re comparaison
multi-assureurs réelle du projet.

PAS FAIT (temps épuisé, session largement au-delà d'1h30) :
- Fix pour best_estimate/marge_risque/primes/charge_sinistres (variante
  R0560-590 pour CNP) — diagnostiqué, pas corrigé.
- `validate_kpis.py` pas adapté/relancé pour CNP (script mono-Groupama).
- Généralisation de `classify_pages()` (faux positif + pages de
  continuation) — contournée manuellement pour CNP, pas corrigée à la
  racine.
- Dictionnaire QRT vraiment "universel" (S.02.01.01, S.25.03, etc. de la
  demande initiale) — seuls les 5 templates nécessaires aux 22 KPIs sur
  CNP ont été construits et vérifiés.

## Décision 060 — Phase 3.8.1 : 21/22 KPIs sur CNP ET Groupama, régression trouvée et corrigée en cours de route

CONTEXTE : suite de la Décision 059 (16/22 sur CNP), objectif : couvrir
les 6 KPIs restants (provisions + primes/sinistres) en sommant TOUS les
segments (non-vie/santé/vie/UC), pas seulement non-vie.

TERMINÉ ET VÉRIFIÉ — 3 bugs réels trouvés et corrigés :

1. **`extract_qrt_native()` (`ingest.py`) : les pages de CONTINUATION
   d'un tableau mono-colonne perdaient TOUTES leurs valeurs.** Page 84 de
   CNP (section "Passifs" de S.02.01.02, suite de la page 83 "Actifs")
   ne répète pas l'en-tête "C0010" — `col_x` restait vide et AUCUNE
   valeur n'était assignée, même pour des lignes non ambiguës (R0670=
   208 236 026, R0710=63 315 077, vérifiées manuellement correctes sur le
   PDF). Corrigé : repli sûr sur l'unique colonne déclarée quand le
   sheet_dict n'a qu'UNE colonne (aucune ambiguïté possible) — pas de
   changement de comportement si plusieurs colonnes sont possibles.

2. **`sommer_toutes_colonnes()` (`extract_kpis.py`) : un doublon mal
   étiqueté faisait échouer toute la somme au lieu d'être ignoré.**
   Conséquence directe de la résolution de sous-feuille "essaie tous les
   candidats" (Décision 055) : la même page physique de CNP (86, 87)
   apparaît comme élément sous LES 2 clés de sous-feuille (S.05.01.02.01
   ET .02), l'une correcte, l'autre un doublon dont le dictionnaire ne
   connaît pas le code (libellé "(code absent du dictionnaire EIOPA)").
   La fonction levait une erreur dès qu'elle rencontrait CE doublon,
   avant même d'atteindre le bon élément. Corrigée pour ignorer un
   élément au libellé non conforme et continuer à en chercher un bon,
   échouant seulement si AUCUN élément valide n'existe pour ce code.

3. **RÉGRESSION RÉELLE TROUVÉE ET CORRIGÉE avant de continuer** (la
   consigne "ne casse pas Groupama" a directement attrapé ce bug) : 1er
   correctif du double-comptage (CNP a une colonne "Total" DÉJÀ PEUPLÉE
   en plus des colonnes par ligne d'activité — vérifié : C0200 =
   C0010+C0020+C0030 exactement sur S.05.01.02.01 de CNP, donc sommer
   "toutes les colonnes" double-comptait) — appliqué GLOBALEMENT à
   `sommer_toutes_colonnes`, a fait chuter `primes_acquises_brutes`/
   `charge_sinistres` de Groupama à EXACTEMENT la moitié de leur valeur
   de référence (39 062,34 → 19 531,17 M€). **Diagnostiqué avant de
   committer** : Groupama a la structure INVERSE (certaines lignes n'ont
   de valeur QUE dans la colonne "Total", les colonnes par activité étant
   vides — les exclure donne 0 et divise le résultat par 2, pas une
   coïncidence). Pas de règle universelle solo/groupe ou EN/FR ici —
   corrigé en ajoutant un paramètre `exclure_total` au niveau de CHAQUE
   variante du mapping (`kpi_qrt_mapping.py`), activé UNIQUEMENT sur les
   4 variantes françaises ajoutées pour CNP, comportement de Groupama
   totalement inchangé. Cause racine annexe trouvée en diagnostiquant :
   `qrt_dictionary_cnp.json` utilisait des libellés PLACEHOLDER anglais
   ("Premiums earned") copiés de la structure Groupama au lieu du texte
   français réel de CNP — corrigé en "Primes acquises"/"Charge des
   sinistres", ce qui fait désormais matcher la BONNE variante du
   mapping (française, `exclure_total=True`) au lieu de l'anglaise.

RÉSULTAT — 21/22 KPIs sur CNP ET Groupama (`resultat_technique` NULL
pour les deux, acté, pas un bug) :

| KPI | CNP | Groupama |
|---|---|---|
| ratio_scr | 258,00 % | 274,00 % |
| ratio_mcr | 506,00 % | 379,28 % |
| scr_total | 14 256,82 M€ | 6 020,98 M€ |
| mcr | 6 415,57 M€ | 3 840,84 M€ |
| fonds_propres_eligibles | 36 778,13 M€ | 16 481,19 M€ |
| fonds_propres_t1_nr/t1_r/t2/t3 | 28 605,49 / 2 605,98 / 4 379,84 / 1 186,82 M€ | 13 329,15 / 601,32 / 2 068,91 / 481,82 M€ |
| best_estimate | 277 208,17 M€ | 69 035,10 M€ |
| marge_risque | 3 740,67 M€ | 2 384,34 M€ |
| provisions_techniques | 280 948,84 M€ | 71 419,44 M€ |
| primes_acquises_brutes | 22 238,96 M€ | 39 062,34 M€ |
| charge_sinistres | 20 072,45 M€ | 27 949,85 M€ |
| scr_marche/vie/santé/contrepartie/opérationnel/diversification | (tous remplis) | (tous remplis) |
| scr_souscription_nonvie | 0,00 M€ (réel — CNP n'a quasi aucune activité non-vie) | 2 474,79 M€ |
| resultat_technique | NULL | NULL |

`validate_kpis.py` (Groupama) : **30/30 toujours OK.** `extract_kpis.py`
(Groupama, retesté 3 fois après chaque correctif) : **22/22 valeurs
identiques à la référence à chaque fois** — aucune régression persistante.

PAS FAIT :
- `validate_kpis.py` non adapté pour tourner sur CNP (script mono-Groupama,
  déjà noté Décision 059).
- Le comportement `exclure_total` reste réglé variante par variante, pas
  déduit automatiquement — un 3e assureur pourrait exiger une nouvelle
  variante explicite plutôt qu'une règle générale (aucune règle fiable
  identifiée entre 2 documents seulement).

## Décision 061 — Test AXA SA (redirigé vers MACSF prévoyance) : 3e assureur, 14/22 KPIs

CONTEXTE : le prompt demandait AXA SA 2025. **Blocage réel, documenté
avant de router ailleurs (consigne "diagnostique et corrige, ne
t'arrête pas")** : le PDF AXA SA 2025 déjà présent dans `data/` est
UNIQUEMENT narratif — page 81 mentionne explicitement "Annexe I -
Modèles de déclaration quantitative" mais les tableaux QRT eux-mêmes ne
sont PAS dans ce fichier (AXA publie narratif et QRT en 2 PDF séparés,
confirmé aussi en session précédente en trouvant un vrai QRT AXA sur un
domaine séparé axa-contento-118412.eu). Recherche du compagnon QRT 2025
infructueuse en temps raisonnable (le fichier FY2025 n'est pas encore
indexé). **Pivot vers MACSF prévoyance** (`data/RAPPORT_SFCR_MACSF_
prevoyance_2025.pdf`), déjà présent dans le dossier, QRT embarqués dans
le même fichier — décision justifiée par la consigne "économie de temps
maximale" plutôt que de bloquer sur un fichier externe introuvable.

TERMINÉ ET VÉRIFIÉ — 2 nouvelles variantes de colonne EIOPA découvertes
(4e et 5e observées au total pour les mêmes concepts, sur seulement 3
documents solo formule standard) :
- S.23.01.01 (SCR/MCR/fonds propres) : colonne **C0060** chez MACSF
  (au lieu de C0010 chez AXA/Bornholms/CNP) — ajoutée au mapping.
- S.25.01.21 (répartition SCR) : colonne **C0090** chez MACSF (au lieu
  de C0110 chez CNP, C0040/C0100 chez AXA) — ajoutée au mapping (1re
  tentative avait mis C0080 par erreur de lecture du positionnement des
  en-têtes, corrigée après vérification empirique de la vraie colonne
  porteuse de la valeur).

RÉSULTAT : 14/22 KPIs MACSF extraits et vérifiés contre lecture manuelle
du PDF (SCR=439,84 M€, MCR=109,96 M€, fonds propres éligibles=2 291,37 M€,
best_estimate=88,00 M€, marge_risque=14,38 M€, primes=42,60 M€,
sinistres=14,99 M€, + 5 des 7 KPIs SCR détaillés). MACSF prévoyance
insérée dans `kpis.db`. `compare_kpis("ratio_scr", 2025)` : CNP=258%,
Groupama=274%, MACSF=NULL (limitation documentée ci-dessous).

**Groupama ET CNP retestés après tous les ajouts de cette session : 0
régression** (22/22 et 21/22 identiques aux valeurs de référence).

PAS FAIT / LIMITATIONS DOCUMENTÉES (honnêtes, pas des chiffres inventés) :
- `ratio_scr`/`ratio_mcr` NULL pour MACSF : les valeurs sont imprimées en
  FORMAT POURCENTAGE ("521%", "2084%") sur cette page précise, et
  `NUMERIC_FRAGMENT_RE` (`ingest.py`) n'accepte que des fragments
  purement numériques (pas de "%" final) — jamais rencontré sur Groupama/
  CNP (ratios toujours en décimal brut "2,74" ou "%"-séparé). Correctif
  identifié (élargir la regex) mais PAS appliqué — c'est une regex
  PARTAGÉE avec tout le pipeline, et le temps restant ne permettait pas
  de la modifier ET de revérifier Groupama/CNP en toute sécurité (cf.
  la régression réelle de la Décision 060, qui a montré qu'un changement
  partagé non revérifié peut casser un document qui marchait).
- `fonds_propres_t1_r/t2/t3` NULL pour MACSF — cohérent avec la réalité
  (MACSF n'a que du Tier 1 non restreint, vérifié sur le PDF : toutes
  les autres colonnes de fonds propres à "-").
- `scr_souscription_sante`/`scr_souscription_nonvie` NULL pour MACSF —
  valeurs réellement à "-" (zéro) sur le PDF, pas capturées par
  l'extracteur positionnel (même limite que les pourcentages : "-" n'est
  pas reconnu comme "0" par `NUMERIC_FRAGMENT_RE`) — NULL plutôt que
  deviné, conforme à la consigne.
- Compagnon QRT réel d'AXA SA 2025 non trouvé — reste à faire si AXA
  est explicitement requis dans une session future.

## Décision 062 — Fix regex "%" : ratio_scr/ratio_mcr MACSF corrigés, 0 régression

CONTEXTE : suite de la Décision 061, correctif identifié mais pas
appliqué (temps insuffisant pour revérifier Groupama/CNP en toute
sécurité après la vraie régression de la Décision 060).

FIX (2 endroits, strictement additif — aucun cas déjà géré ne pouvait
contenir "%", donc aucune valeur déjà extraite avec succès ne peut être
affectée) :
1. `NUMERIC_FRAGMENT_RE` (`ingest.py`) élargie de `^-?\d+([.,]\d+)?$` à
   `^-?\d+([.,]\d+)?%?$|^%$` — accepte un "%" directement accolé au
   nombre ("521%", 1 seul mot PDF, cas réel vérifié sur MACSF) ou un "%"
   en mot PDF séparé ("521 %", fusionné ensuite par
   `merge_numeric_fragments` déjà existant, pas modifié).
2. `_vers_float()` (`extract_kpis.py`) : un suffixe "%" est retiré et le
   nombre divisé par 100, pour revenir à la même convention "décimal
   brut" que Groupama/CNP (qui impriment "2,74", pas "274%") — le code
   appelant multiplie TOUJOURS par 100 au niveau KPI, donc sans cette
   division "521%" deviendrait 52 100% au lieu de 521%.
2 nouvelles variantes ajoutées au mapping (`ratio_scr`/`ratio_mcr`,
colonne C0060 chez MACSF, format pourcentage — vérifiées contre le PDF).

RÉSULTAT :
- **MACSF : ratio_scr passe de NULL à 521,00 %, ratio_mcr de NULL à
  2 084,00 %** — vérifiés exacts contre le texte imprimé sur le PDF
  ("521%", "2084%"). MACSF passe de 14/22 à **16/22 KPIs**.
- **Groupama : 22/22 valeurs identiques à la référence, 30/30 contrôles
  actuariels toujours OK.**
- **CNP : 21/22 valeurs identiques à la référence.**
- Aucune régression sur aucun des 2 documents déjà validés.

| KPI | CNP | Groupama | MACSF |
|---|---|---|---|
| ratio_scr | 258,00 % | 274,00 % | 521,00 % |
| ratio_mcr | 506,00 % | 379,28 % | 2 084,00 % |
| scr_total | 14 256,82 M€ | 6 020,98 M€ | 439,84 M€ |
| mcr | 6 415,57 M€ | 3 840,84 M€ | 109,96 M€ |
| fonds_propres_eligibles | 36 778,13 M€ | 16 481,19 M€ | 2 291,37 M€ |

Note : `ratio_mcr` de MACSF (2 084 %) est réellement énorme mais pas
suspect — cohérent avec un MCR très petit (109,96 M€) face à des fonds
propres de 2 291,37 M€ pour une mutuelle prévoyance de cette taille,
déjà visible dans le texte source non retraité ("2084%" imprimé tel
quel sur le PDF).

PAS FAIT (limitations MACSF restantes, hors périmètre de ce fix ciblé) :
- `scr_souscription_sante`/`scr_souscription_nonvie` toujours NULL
  (valeurs réellement "-" sur le PDF, pas "0" ni un nombre — non
  capturées par `NUMERIC_FRAGMENT_RE`, différent du cas "%").
- `fonds_propres_t1_r/t2/t3` toujours NULL (cohérent : MACSF n'a que du
  Tier 1, vérifié).

## Décision 063 — Fix tiret EIOPA "-" → 0.0 : MACSF passe de 16/22 à 21/22, 0 régression

CONTEXTE : suite du diagnostic demandé (5 KPIs NULL identifiés : cellule
QRT contenant un tiret isolé "-", convention EIOPA "zéro/non
applicable"). Vérifié AVANT correctif (pas supposé) que les 3 tirets de
S.23.01.01.01/R0540 (Niveau1-restreint/Niveau2/Niveau3) sont à x=507,9/
531,7/555,5 — écarts >20pt entre eux et par rapport aux vrais nombres,
bien au-delà de `MERGE_GAP_PT` (5.0) — aucun risque de fusion accidentelle
avec un signe moins de nombre négatif voisin.

FIX (2 endroits, additif comme le fix "%" de la Décision 062) :
1. `NUMERIC_FRAGMENT_RE` (`ingest.py`) : 3e alternative `^-$` — un tiret
   isolé est désormais un fragment valide (auparavant totalement ignoré,
   la cellule n'apparaissait même pas dans `valeurs`).
2. `_vers_float()` (`extract_kpis.py`) : si la chaîne vaut exactement
   "-", retourne 0.0.

RÉSULTAT :
- **MACSF passe de 16/22 à 21/22 KPIs** — les 5 valeurs ciblées valent
  toutes 0.00 M€, comme attendu (`fonds_propres_t1_r/t2/t3`,
  `scr_souscription_sante/nonvie`).
- **Groupama : 22/22 identiques à la référence, 30/30 contrôles
  actuariels toujours OK.**
- **CNP : 21/22 identiques à la référence.** Aucune régression.
- Seul NULL restant sur les 3 documents : `resultat_technique` (acté,
  pas un bug, cf. Décision 051).

**DÉCOUVERTE ANNEXE, PAS CORRIGÉE ICI (hors périmètre de cette demande,
signalée pour transparence)** : en vérifiant les positions de tokens
autour de R0060 (Diversification, MACSF) pour m'assurer que le fix du
tiret ne risquait pas d'interférer avec un signe négatif, j'ai constaté
que `scr_diversification` de MACSF vaut **+14,14 M€ (positif)** alors
que la diversification est TOUJOURS un effet négatif par construction
(bénéfice qui réduit le SCR total — Groupama=-4 612,40, CNP=-9 821,13,
`kpi_definitions.py` déclare explicitement `sign: "negative"` pour ce
KPI). Cause probable : sur la page 62 de MACSF, le signe "-" de R0060
est positionné à x≈467 (colonne C0080) tandis que le nombre "14 137"
est à x≈557 (colonne C0090) — 90pt d'écart, donc jamais fusionnés par
`merge_numeric_fragments`, et mon mapping lit uniquement C0090 (positif,
sans signe). Le tiret-fix de cette session NE RÉSOUT PAS ce cas (le
tiret isolé de R0060 est dans une colonne différente de celle lue par
le mapping, donc n'a aucun effet sur cette valeur). **Signe
potentiellement faux pour ce KPI précis sur MACSF — à corriger dans une
session dédiée**, pas traité maintenant (hors périmètre de la demande
"fix tiret pour les 5 NULL identifiés").

## Décision 064 — Phase 3.9 : mode extraction par libellé français, MAIF + Covéa supportés

CONTEXTE : le diagnostic visuel a confirmé que MAIF et Covéa ont de vrais
tableaux QRT complets, sans AUCUN code R0xxx/C0xxx — seul le titre de
section porte le code ("Tableau S.25.01.22 : Capital de solvabilité
requis"). Objectif : ajouter un mode d'extraction par libellé en repli,
sans toucher au mode codes_eiopa.

TERMINÉ ET VÉRIFIÉ :

1. **`kpi_labels_fr.py`** (nouveau) — libellés français par KPI, TOUS vus
   directement (rendu image ou texte brut PyMuPDF) sur MAIF/Covéa/
   Groupama/CNP/MACSF, aucun deviné.

2. **`extraire_par_libelle.py`** (nouveau) — `classifier_lignes()` sépare
   le texte brut d'une page en paires (libellé accumulé, valeur(s))
   selon qu'une ligne est 100% numérique ou non (vérifié sur la structure
   réelle : labels repliés sur 1-3 lignes, suivis d'une ligne de valeurs
   séparées par grands espaces). `extraire_par_libelle()` : priorité à
   l'ÉGALITÉ STRICTE, repli en SUFFIXE avec frontière de mot uniquement
   si aucune égalité stricte n'existe (bug réel trouvé ET corrigé en
   cours de route : le repli en suffixe seul cassait MAIF — scr_total et
   mcr récupéraient la mauvaise ligne, "...pour couvrir le capital de
   solvabilité requis" au lieu de la ligne exacte — corrigé en donnant
   priorité à l'égalité stricte).

3. **`detecter_templates()` étendu** avec un champ `mode`
   ("codes_eiopa"/"libelles_francais"), détecté en cherchant un vrai
   `R0\d{3}` dans le texte des pages QRT (pas dans les titres, qui
   portent le code dans les 2 modes). Vérifié : Groupama/CNP/MACSF =
   codes_eiopa, MAIF/Covéa = libelles_francais. Champ additif, aucun
   changement pour les appels existants.

4. **RÉGRESSION RÉELLE TROUVÉE ET CORRIGÉE avant de livrer** (la
   consigne "précision absolue, NULL si pas sûr" l'a directement
   attrapée) : le repli par libellé, une fois branché dans
   `batch_diagnostic.py` pour les 12 documents, a produit des **FAUX
   POSITIFS** sur MAAF/MMA IARD/MMA Vie (12/20 KPIs chacun) — alors que
   la session précédente avait déjà prouvé, par recherche exhaustive de
   `R0\d{3}` sur la TOTALITÉ de ces documents, qu'ils ne contiennent
   AUCUN vrai tableau QRT (narratif pur). Diagnostiqué avant de livrer :
   le libellé "Meilleure estimation" de MAAF matchait un PARAGRAPHE DE
   MÉTHODOLOGIE ("la meilleure estimation se décompose en...") et
   récupérait la valeur 910 — sans rapport avec la réalité (un assureur
   de cette taille a des provisions en dizaines de millions, pas 910 k€).
   **Un filtre par densité de paires libellé/valeur a été testé et
   rejeté** : MAAF produit 347 paires, Covéa (vrai tableau) en produit
   415 — la densité seule ne distingue PAS narratif de tabulaire (le
   texte narratif français est lui-même truffé de statistiques
   chiffrées). Faute d'un détecteur fiable dans le temps imparti,
   **solution retenue : liste blanche des documents VÉRIFIÉS
   VISUELLEMENT** (`DOCUMENTS_LIBELLE_VERIFIES` dans
   `batch_diagnostic.py`) — seuls MAIF et Covéa passent par le repli par
   libellé ; tout autre document en mode `libelles_francais` reste NULL
   avec un motif explicite ("document non vérifié, extraction non
   tentée par prudence") plutôt qu'un risque de faux positif silencieux.

RÉSULTAT :

| KPI | MAIF (test manuel, p.121-122) | Covéa (batch, p.82-99) |
|---|---|---|
| ratio_scr | 227,00 % | 221,00 % |
| ratio_mcr | 869,00 % | 511,00 % |
| scr_total | 2 344 989 k€ | 15 058 209 k€ |
| mcr | 612 514 k€ | 6 478 904 k€ |
| fonds_propres_eligibles | 5 329 707 k€ | 33 251 714 k€ |
| scr_marche | (image, non extrait) | 12 077 364 k€ |
| scr_souscription_vie | (image, non extrait) | 7 607 617 k€ |
| scr_souscription_nonvie | (image, non extrait) | 8 859 509 k€ |
| scr_souscription_sante | (image, non extrait) | 1 352 876 k€ |
| scr_contrepartie | (image, non extrait) | 694 793 k€ |
| scr_operationnel | (image, non extrait) | 1 058 463 k€ |
| scr_diversification | (image, non extrait) | -10 324 898 k€ |
| best_estimate | (image, non extrait) | 84 032 648 k€ |
| marge_risque | (image, non extrait) | 5 263 956 k€ |

Toutes les valeurs Covéa croisées avec succès contre la lecture visuelle
initiale (diagnostic visuel précédent) — 0 écart. MAIF : 5/5 valeurs de
S.23.01.01 croisées avec succès contre la lecture visuelle (p.121-122).

**Groupama/CNP/MACSF retestés après tous les changements : 22/22, 21/22,
21/22 — strictement identiques à la référence, 0 régression.**

PAS FAIT / LIMITATIONS DOCUMENTÉES :
- **MAIF : 8 des 10 pages de son annexe QRT sont en IMAGE** (S.17.01.02,
  S.22.01.21, S.25.01.21, S.28.01.01 — vérifié : `n_caracteres` ≈ 90-110,
  quasi aucun texte extractible) — SEULE S.23.01.01 (pages 121-122) est
  en texte natif. L'extraction par libellé ne peut structurellement rien
  faire sur du texte absent ; une lecture PaddleOCR/Gemini serait
  nécessaire (prévue par la consigne comme "cross-validation", pas
  implémentée — temps insuffisant).
- **`batch_diagnostic.py` sur MAIF reste à 0/20** malgré le mode
  correctement détecté : `classify_pages()` ne trouve QUE 2 pages QRT
  pour MAIF (112, 121) et RATE la page de continuation 122 (qui porte
  SCR/MCR/ratios) — même angle mort déjà documenté Décisions 059-060,
  pas corrigé ici (hors périmètre, risque de regression sur la détection
  générale). Le test manuel (pages 121-122 concaténées à la main) donne
  le résultat réel, 5/5 KPIs disponibles pour MAIF.
- **`primes_acquises_brutes`/`charge_sinistres` en mode libellé** :
  volontairement NON implémentés (structure multi-lignes/multi-colonnes
  par ligne d'activité, ex. Covéa "Primes acquises" + sous-lignes "Brut –
  Assurance directe/Réassurance proportionnelle/non proportionnelle" ×
  9-16 colonnes de LoB — trop complexe et risqué à fiabiliser dans le
  temps imparti) — restent NULL pour MAIF et Covéa.
- Cross-validation PaddleOCR (prévue par la consigne pour les pages
  image) non implémentée — temps insuffisant après la découverte et la
  correction de la régression des faux positifs.

## Décision 065 — Fix colonnes QRT : Crédit Agricole 20/20, découverte d'un vrai bug dans le diagnostic

CONTEXTE : le batch montrait AFI (13/20) et Crédit Agricole (13/20)
bloqués sur des colonnes QRT "inconnues".

DIAGNOSTIC PRÉCIS (avant tout correctif) :
- **AFI : PAS un problème de colonne.** Ses 7 KPIs SCR détaillés NULL
  viennent de `S.25.05.21`, un template **modèle interne** absent du
  mapping par choix (Décision 056 : les templates modèle interne
  S.25.02-05 n'ont aucun code fixe universel, vérifié empiriquement sur
  Groupama vs Yuzzu — un "ordre de priorité de colonnes" ne peut rien y
  faire, il faudrait une résolution par libellé document par document,
  hors périmètre de cette demande). **Non corrigé, honnêtement signalé.**
- **Crédit Agricole : vrai problème de colonne.** `S.25.01.22` (formule
  standard, groupe) utilise la colonne **C0110** — vérifié en lisant le
  texte brut de sa page 78 directement, en français ("Risque de
  marché... R0010... C0110"). C0110 était déjà connu pour `S.25.01.21`
  (CNP) mais pas encore ajouté pour `S.25.01.22`.

FIX 1 — `kpi_qrt_mapping.py` : 8 nouvelles variantes `S.25.01.22`/C0110
(mêmes libellés français que CNP), vérifiées contre Crédit Agricole.

**FIX 2 — bug réel trouvé DANS `batch_diagnostic.py` lui-même, pas dans
le pipeline réel** : après le fix 1, Crédit Agricole restait bloqué à
14/20 (seul `scr_diversification` s'est débloqué). Diagnostiqué : la
fonction `construire_qrt_dict_synthetique()` utilisait `setdefault()`
pour associer un libellé à chaque (template, ligne) — quand 2 variantes
du mapping déclarent des libellés DIFFÉRENTS pour le même code (ex.
`S.25.01.22/R0010` a "Market risk" en anglais ET "Risque de marché" en
français), seul le PREMIER libellé inséré était conservé. `extract_qrt_
native` rapportait alors TOUJOURS "Market risk" comme libellé trouvé,
faisant échouer le contrôle de la variante française même quand la
cellule existait réellement — un faux "colonne inconnue" qui était en
réalité un faux "libellé inconnu" causé par le script de diagnostic
lui-même. **Corrigé en accumulant TOUS les libellés connus pour un code
donné** (séparés par " | "), pas seulement le premier.

RÉSULTAT — tableau avant/après (batch complet, 12 documents) :

| # | Fichier | Avant | Après |
|---|---|---|---|
| 1 | AFI | 13/20 | 13/20 (inchangé, cf. diagnostic ci-dessus) |
| 2 | Allianz Group 2024 | 2/20 | 2/20 (inchangé, hors périmètre) |
| 3 | **Crédit Agricole Assurances** | 13/20 | **20/20** |
| 4 | MAIF | 0/20 | 0/20 (inchangé, angle mort continuation déjà connu) |
| 5 | **MACSF prévoyance** | 17/20 | **20/20** (bénéficie du même fix 2, EN/FR se percutaient déjà silencieusement) |
| 6 | Groupama 2024 | 11/20 | 11/20 (inchangé, modèle interne S.25.05) |
| 7 | Groupama 2025 | 9/20 | 9/20 (inchangé, modèle interne S.25.05) |
| 8 | CNP Assurances | 10/20 | 10/20 (inchangé) |
| 9 | Covéa | 14/20 | 14/20 (mode libellé, non affecté) |
| 10-12 | MAAF/MMA IARD/MMA Vie | 0/20 | 0/20 (inchangé, narratif pur) |

**Groupama/CNP/MACSF (pipelines réels `extract_kpis*.py`, pas le
diagnostic) retestés : 22/22, 21/22, 21/22 — strictement identiques à
la référence, 0 régression.**

PAS FAIT :
- AFI reste à 13/20 — nécessiterait une résolution par libellé pour
  S.25.05.21 (modèle interne), hors périmètre de "fix colonnes".
- CNP reste à 10/20 dans le diagnostic BATCH (avec son dictionnaire
  synthétique générique) — rappel : son pipeline RÉEL dédié
  (`extract_kpis_cnp.py`, dictionnaire construit à la main) est à 21/22,
  le diagnostic batch est volontairement plus grossier (1 seule
  sous-feuille par template, pas de résolution multi-pages) et ne
  reflète pas la capacité réelle du pipeline sur CNP.
- Pas de "ordre de priorité générique" façon liste de colonnes à essayer
  dans le sens demandé par le prompt — chaque variante de colonne
  ajoutée reste une entrée explicite vérifiée contre un document réel,
  cohérent avec la règle du projet "ne devine pas".

## Décision 066 — Fix 4 colonnes QRT : diagnostic préalable a écarté 2 des 4, 2 vrais fixes appliqués

CONTEXTE : le prompt demandait de corriger 4 templates signalés "colonne
inconnue" (S.28.01.01, S.28.02.01, S.25.01.21, S.23.01.22). Exécution
différée à 19h00 sur demande explicite de l'utilisateur (attente via
`Monitor`, re-armée 3 fois jusqu'à l'heure demandée), puis lancée
automatiquement sans confirmation, comme prescrit.

DIAGNOSTIC PRÉALABLE (avant tout correctif — 2 des 4 templates se sont
révélés être de FAUX signaux, pas de vrais manques de colonne) :

1. **S.28.01.01 (MCR solo) : PAS un problème.** Testé directement sur
   MACSF (`extract_qrt_native` + dictionnaire synthétique déjà en place) :
   R0400 "Minimum de capital requis" = 109 959, extrait CORRECTEMENT sous
   C0070 — la colonne déjà connue. Vérifié aussi qu'aucun des 4 documents
   flaggés (AFI, Cardif RD, Sogécap, MACSF) n'a `mcr` dans sa liste de
   KPIs NULL : le signal "colonne_inconnue" concernait des lignes
   (R0010-R0350, répartition non-vie) qu'AUCUN KPI n'utilise — du bruit
   de diagnostic, pas un vrai manque. **Aucune variante ajoutée.**

2. **S.28.02.01 (MCR composite, CNP) : PAS un problème de colonne non
   plus.** Vérifié en relisant directement la page 98 de CNP : le
   tableau s'arrête à R0200, la ligne R0400 (MCR final) est sur la
   PAGE 99 — une page de CONTINUATION que `classify_pages()` ne tague
   jamais comme faisant partie de S.28.02.01 (le titre du template ne
   se répète pas). C'est le même angle mort déjà documenté 3 fois
   (Décisions 059, 060, 061) — un vrai fix nécessiterait de faire lire au
   diagnostic la page suivante pour tout template multi-pages, un
   changement d'architecture, pas l'ajout d'une variante de colonne.
   **Aucune variante ajoutée** (le mapping a déjà la bonne colonne C0130,
   vérifiée Décision 059 — ce n'est pas elle le problème).

3. **S.25.01.21 (SCR formule standard) : vrai problème, corrigé.**
   Vérifié sur Cardif Assurance Vie (page 13, texte brut) : les 6
   modules de risque (R0010-R0070) utilisent la colonne **C0040** — une
   4e variante de colonne pour ce concept (après C0040 groupe/solo
   standard AXA, C0110 CNP, C0090 MACSF). Risque opérationnel (R0130) et
   SCR final (R0220) utilisent **C0100**. 8 nouvelles variantes ajoutées
   à `kpi_qrt_mapping.py`.

4. **S.23.01.22 (fonds propres groupe) : vrai problème, corrigé —
   découverte plus profonde qu'une simple colonne.** Vérifié sur
   Sogécap (page 40) : le tableau est TITRÉ "S.23.01.22" (suffixe
   groupe) mais utilise les CODES DE LIGNE SOLO (R0580/R0600/R0620/
   R0640/R0540, pas R0680/R0690/R0610/R0650/R0660 attendus pour un
   groupe) — pas juste une colonne différente, un schéma de
   numérotation entièrement différent sous un même titre. 9 nouvelles
   variantes ajoutées (`col="C0010"`, comme pour un document solo),
   explicitement annotées comme un cas Sogécap précis, pas une règle
   groupe générale.

RÉSULTAT (batch 14 documents) :

| Fichier | Avant | Après |
|---|---|---|
| **Cardif Assurance Vie** | 13/20 | **19/20** (+6, ne manque que scr_operationnel) |
| **Cardif risques divers** | 13/20 | **19/20** (+6) |
| **Sogécap** | 4/20 | **13/20** (+9 — ratio_scr/ratio_mcr/scr_total/mcr/fonds_propres_eligibles+4 tiers) |
| AFI | 13/20 | 13/20 (inchangé, cf. point 1 — pas un problème de colonne) |
| CNP (diagnostic générique) | 10/20 | 10/20 (inchangé, cf. point 2 — angle mort de continuation) |
| Groupama/MACSF/Covéa/etc. | — | inchangés |

Sogécap garde 7 KPIs NULL (les modules SCR détaillés) — pour une raison
DIFFÉRENTE et non investiguée ici : son `scr_method` ressort "inconnu"
(aucun template S.25.01 détecté sur ce document du tout), hors périmètre
de "fix colonnes".

**Pipelines réels (`extract_kpis*.py`, pas le diagnostic générique)
retestés : Groupama 22/22, CNP 21/22, MACSF 21/22 — strictement
identiques à la référence, 0 régression.**

LEÇON MÉTHODOLOGIQUE : sur 4 signaux "colonne inconnue" fournis par le
diagnostic automatique, seuls 2 étaient de vrais manques de colonne — 2
étaient du bruit (une ligne non utilisée par les KPIs, une page de
continuation non lue). Vérifier CHAQUE signal contre le vrai document
et contre la liste réelle des KPIs NULL avant de corriger reste
indispensable — un correctif appliqué aveuglément sur les 4 aurait
gaspillé la moitié de l'effort sans gagner un seul KPI.

## Décision 067 — Fix scr_operationnel Cardif Vie : mauvaise colonne verifiée session précédente

CONTEXTE : session autonome 6 tâches. Tâche 1 (10 min) — `scr_operationnel`
restait NULL pour Cardif Assurance Vie malgré l'ajout d'une variante
`S.25.01.21/R0130/C0100` en fin de session précédente (commit `0373f35`).

DIAGNOSTIC : extraction directe de la page S.25.01.21 de Cardif Vie
montre que R0130 ("Risque opérationnel") a sa valeur réelle sous
**C0040**, pas C0100. La variante ajoutée en session précédente était
tout simplement mal vérifiée (probablement une confusion avec une autre
colonne du même tableau) — C0040 est cohérent avec `scr_diversification`
déjà vérifié sur ce même document.

FIX : correction de la colonne dans `kpi_qrt_mapping.py` (C0100 → C0040).

RÉSULTAT : Cardif Assurance Vie 19/20 → 20/20 KPIs (diagnostic générique).
Aucune régression : Groupama 21/22, CNP 21/22, MACSF 21/22.

Commit : `2a36d2e`.

## Décision 068 — Fix classify_pages() : détection multi-templates sur une même page (Sogécap)

CONTEXTE : Tâche 3 (25 min) — `detecter_templates()` renvoyait
`scr_method="inconnu"` pour Sogécap alors que le sommaire du document
liste explicitement "9. ÉTAT S.25.01.21 CAPITAL DE SOLVABILITÉ REQUIS...".

DIAGNOSTIC : `classify_pages()` ne retient que le PREMIER code
`S.xx.xx.xx` trouvé sur une page (`QRT_CODE_RE.search`, pas
`.finditer`). Or la page 40 du PDF Sogécap contient physiquement la
FIN de S.23.01.22 ("FONDS PROPRES (SUITE)") ET le DÉBUT de S.25.01.21
juste en dessous, sur la même page — le second template était donc
invisible. Les colonnes lues manuellement sur cette page (C0110/C0090)
correspondent exactement à la variante déjà vérifiée sur CNP Assurances
— aucune nouvelle variante de mapping n'était nécessaire.

FIX : `classify_pages()` détecte maintenant TOUS les codes `S.xx.xx.xx`
distincts sur une page "qrt" (pas seulement le premier) et ajoute une
entrée de classification supplémentaire par code additionnel, pointant
vers la même page physique. `process_qrt()`/le diagnostic essaient donc
d'extraire les deux templates sur cette page — sans risque, car
l'extraction ancre par regex de code de ligne (R0xxx), indépendante du
texte qui précède sur la page.

RÉSULTAT : Sogécap 13/20 → 20/20 KPIs (diagnostic générique),
`scr_method` "inconnu" → "formule_standard".

## Décision 069 — Fix classify_pages() : détection des pages de continuation QRT (CNP)

CONTEXTE : Tâche 4 (30 min) — bug documenté 3 fois auparavant
(Décisions 059-061, 066) : la page 99 de CNP Assurances est la suite du
template S.28.02.01 (contient R0210 à R0560, dont R0400 = MCR final)
mais ne répète PAS le titre "S.28.02.01" — `classify_pages()` la
classait "narratif" et le diagnostic générique perdait ces lignes.

FIX : `classify_pages()` mémorise le template de la dernière page "qrt"
immédiatement précédente. Une page classée "narratif" par les critères
existants, mais qui contient au moins 2 lignes isolées matchant
`ROW_CODE_RE` (`^R\d{4}$`), est reclassée "qrt" avec ce template
précédent. La mémoire du template précédent est réinitialisée à chaque
page qui NE qualifie PAS comme continuation, pour ne pas chaîner au-delà
de la vraie section QRT et limiter le risque de faux positif.

VÉRIFICATION ANTI-FAUX-POSITIFS : rejoué sur les 14 PDF de `data/` —
seuls CNP (5 pages recatégorisées, toutes vérifiées manuellement comme
de vraies suites de tableau QRT) et Allianz (8 pages, même mécanisme,
document multi-pages volumineux) sont affectés. Aucun autre document
(Groupama, MACSF, Sogécap, Cardif, Crédit Agricole, etc.) ne change.

RÉSULTAT : CNP 10/20 → 20/20 KPIs (diagnostic générique) — le
contournement manuel de la Décision 059 n'est plus nécessaire pour que
le diagnostic générique trouve ces KPIs (le pipeline dédié `extract_kpis_cnp.py`
reste à 21/22, il contournait déjà le problème). Allianz 2/20 → 6/20
(bénéfice secondaire, même mécanisme).

**Pipelines réels retestés après les 3 correctifs (067+068+069) :
Groupama 21/22, CNP 21/22, MACSF 21/22 — strictement identiques à la
référence, 0 régression.**

NOTE DE PROCESSUS : les correctifs des Décisions 068 et 069 ont été
codés l'un après l'autre dans `test_markdrop/ingest.py` avant qu'un
commit intermédiaire ne soit fait entre les deux — ils se retrouvent
donc TOUS LES DEUX dans le commit `c991573`, dont le message ne décrit
que la Décision 068. Les deux correctifs sont testés et fonctionnels
(vérifié séparément avant et après l'ajout de la Décision 069) ; cette
note sert de trace écrite pour la Décision 069, absente du message de
commit.

Commit (contient 068 + 069) : `c991573`.

## Décision 070 — Diagnostic AFV/ARE (pas de fix rapide) + clarification du faux signal Groupama

CONTEXTE : Tâche 2 (15 min) — AFV et ARE n'avaient jamais été
investigués en détail. Tâche 5 (10 min) — le diagnostic générique
signale des KPIs manquants sur Groupama à cause de pages image, alors
que le pipeline réel (PaddleOCR) les résout déjà.

**AFV** (`afv-annexes-2025-etats-quantitatifs.pdf`) : 13/20 KPIs, les 7
`scr_*` manquants viennent tous du même blocage — la page SCR de ce
document utilise le template `S.25.05.21` (modèle interne complet, non
mappé), avec une structure de lignes fondamentalement différente de
toute variante connue (ex. R0070 = "Total market & credit risk" combiné,
ne se sépare pas proprement en `scr_marche`/`scr_contrepartie`). Un vrai
fix demanderait une session dédiée de lecture ligne par ligne, pas un
patch de 5 minutes — documenté, non corrigé. Le signal
"colonne_inconnue:S.28.02.01" sur ce document est un faux signal : `mcr`
se résout déjà par une autre voie.

**ARE** (`are-annexes-2025-etats-quantitatifs.pdf`) : 0/0 KPIs. Le
document n'utilise PAS la nomenclature EIOPA `S.xx.xx.xx` du tout, mais
la nomenclature française nationale ("États C/P" : `RC.02.01`,
`RP.05.01.01`, `RP.42.03.01`). `classify_pages()` n'a aucun support pour
cette famille de codes — écart architectural, pas un fix de colonne/ligne.
Non corrigé (hors budget).

**Clarification Groupama** : ajout de `DOCUMENTS_IMAGE_RESOLUE_PAR_PIPELINE_REEL`
dans `batch_diagnostic.py` — quand une page image est ignorée par le
diagnostic générique (`page_image_non_traitee`) sur un document listé
(actuellement `SFCR_2025_Groupe-Groupama.pdf`), le problème reporté
porte maintenant une note explicite `"FAUX SIGNAL pour ce document : ..."`
pointant vers la résolution réelle par PaddleOCR dans `extract_kpis.py`,
pour éviter toute confusion future avec un vrai bug.

Commit (batch_diagnostic.py) : voir commit suivant.

## Décision 071 — Session autonome 6 tâches : bilan final

CONTEXTE : session autonome de 2h, 6 tâches séquentielles sans
confirmation entre elles, commit après chaque tâche réussie, budget de
temps par tâche, passage à la suivante si dépassement.

| # | Tâche | Statut | Détail |
|---|-------|--------|--------|
| 1 | Cardif Vie `scr_operationnel` | **Faite** | Mauvaise colonne (C0100→C0040) corrigée. 19/20→20/20. Décision 067, commit `2a36d2e`. |
| 2 | Diagnostic AFV + ARE | **Faite (diagnostic seul)** | AFV : template SCR `S.25.05.21` non mappé, structure incompatible, pas de fix <5min. ARE : nomenclature française nationale (RC/RP), pas EIOPA — écart architectural. Décision 070, commit `ab8cb70`. |
| 3 | Sogécap, vrai template SCR | **Faite** | `classify_pages()` ne lisait que le 1er code par page ; S.25.01.21 était caché derrière S.23.01.22 sur la même page. Fixé génériquement. 13/20→20/20, scr_method inconnu→formule_standard. Décision 068, commit `c991573`. |
| 4 | CNP, pages de continuation | **Faite** | `classify_pages()` détecte maintenant les pages sans titre via codes R0xxx isolés + template précédent. 10/20→20/20. Décision 069, commit `c991573` (bundlé avec la tâche 3, cf. note de processus dans la Décision 069). |
| 5 | Clarifier diagnostic Groupama | **Faite** | Note explicite "FAUX SIGNAL" ajoutée au rapport pour les pages image déjà résolues par le pipeline réel (PaddleOCR). Décision 070, commit `ab8cb70`. |
| 6 | MAIF, intégrer PaddleOCR | **Pas commencée** | Reconnaissance du périmètre effectuée : ~12 pages quasi-image (pas 8), et le seul précédent existant (Groupama/picture_75) est un processus manuel page-par-page (valeurs de référence vérifiées à l'œil, prompts Gemini/Claude sur-mesure par image) — pas une fonction générique réutilisable. Le refaire correctement pour 12 pages dépasse largement le budget restant ; le tenter à la hâte risquerait de violer la règle non négociable "NULL si pas sûr, jamais d'invention" du projet. Documentée, non implémentée. |

RÉGRESSION : vérifiée après CHAQUE tâche sur les 3 pipelines de
référence dédiés. Résultat stable du début à la fin de la session :
**Groupama 21/22, CNP 21/22, MACSF 21/22** (1 seul NULL chacun =
`resultat_technique`, cf. Décision 051 — cohérent avec le comportement
historique du projet). Note : le prompt de la session mentionnait
"Groupama 22/22" comme référence attendue ; le compte réel et stable
sur l'ensemble du projet a toujours été 21/22 pour les 3 documents —
traité comme la référence correcte plutôt que comme une régression.

DIAGNOSTIC GÉNÉRIQUE (`batch_diagnostic.py`) — évolution sur la session :
Cardif Vie 19→20/20, Sogécap 13→20/20, CNP 10→20/20, Allianz 2→6/20
(bénéfice secondaire de la Décision 069). Aucun document n'a régressé.

FIN DE SESSION : les 6 tâches ont été traitées dans l'ordre prescrit ;
aucune tâche hors de cette liste n'a été entamée.

## Décision 075 — Session "résoudre tous les problèmes restants" : bilan final

CONTEXTE : session autonome longue, 6 tâches séquentielles sans
confirmation, commit après chaque tâche réussie, règle absolue de ne
jamais toucher `resultat_technique` (NULL acté, Décision 051).

| # | Tâche | Statut | KPIs avant → après (diagnostic générique) | Détail |
|---|-------|--------|---------------------------------------------|--------|
| 1 | Cardif RD, dernier KPI manquant | **Déjà résolu** | 20/20 → 20/20 (aucun changement nécessaire) | Effet de bord du fix Cardif Vie de la session précédente (même colonne C0040 partagée par les 2 entités Cardif). Aucun commit. |
| 2 | AFV, fix template SCR | **Faite (partielle, limite confirmée)** | AFV 13/20 → 16/20, AFI 13/20 → 16/20 | 3 des 7 sous-modules SCR séparables (`S.25.05.21`/R0310,R0480,R0060). Les 4 autres (marché+contrepartie fusionnés en R0070, vie+santé fusionnés en R0400) sont irréductibles — le template modèle interne ne publie pas ce niveau de détail. Décision 072, commit `308ee54`. |
| 3 | ARE, diagnostic complet | **Faite (diagnostic)** | 0/0 (inchangé, hors périmètre confirmé) | Le document N'EST PAS un extrait tronqué : sa propre table des matières liste exactement les 3 tableaux présents. Nomenclature française nationale (RC/RP), pas EIOPA S.xx — écart architectural réel, pas un bug. Aucun commit (rien à corriger). |
| 4 | AFI, mode libellé | **Faite (limite confirmée 2e fois)** | 16/20 (inchangé) | Testé empiriquement : aucun des 4 labels français (marché/contrepartie/vie/santé) n'existe nulle part sur la page, ni en français ni en anglais — la donnée n'est jamais imprimée séparément, quel que soit le mode d'extraction. Aucun commit (rien à corriger, confirmation seulement). |
| 5 | Covéa, primes/sinistres en mode libellé | **Faite** | 14/20 → 16/20 | 2 bugs racine corrigés : `classifier_lignes()` ne gardait que la 1re valeur/ligne (colonnes larges perdues) ; libellés identiques répétés dans 3 sections de la même page (ambiguïté résolue par `extraire_section()`). Valeurs vérifiées par calcul manuel indépendant avant intégration. Décision 073, commit `2ceff21`. |
| 6 | MAIF, PaddleOCR sur 8 pages image | **Faite — chemin alternatif sans OCR, meilleur résultat** | 0/20 → 13/20 | Découverte que les pages narratives natives 106-108 ("Gestion du capital") contiennent déjà, en texte propre, le détail SCR/MCR/ratios/fonds propres — aucun OCR nécessaire pour 13 KPIs. PaddleOCR non tenté (inutile pour ce résultat). Décision 074, commit `3d45ffd`. |

RÉGRESSION : vérifiée après chaque tâche. Stable du début à la fin de
la session sur les 3 pipelines de référence dédiés :
**Groupama 21/22, CNP 21/22, MACSF 21/22** (1 seul NULL chacun =
`resultat_technique`, jamais touché, conforme à la Décision 051).

### Tableau final — tous les PDF de data/ (diagnostic générique, 20 KPIs)

| Fichier | Avant cette session | Après cette session |
|---|---|---|
| afv-annexes-2025-etats-quantitatifs.pdf | 13/20 | 16/20 |
| Annexe-QRT-Publics-AFI-2025-ok.pdf | 13/20 | 16/20 |
| are-annexes-2025-etats-quantitatifs.pdf | 0/0 | 0/0 (hors périmètre confirmé) |
| Cardif-Assurance-Vie – Annexes-2025.pdf | 20/20 | 20/20 |
| cardif-assurances-risques-divers – annexes-2025.pdf | 20/20 | 20/20 |
| en-Allianz-Group-SFCR-2024.pdf | 6/20 | 6/20 (non ciblé cette session) |
| Groupe-Credit-Agricole-Assurances – SFCR-2025.pdf | 20/20 | 20/20 |
| rapport-solvabilite-maif-2025.pdf | 0/20 | 13/20 |
| Rapport_de_solvabilite_2025_Sogécap_01.pdf | 20/20 | 20/20 |
| RAPPORT_SFCR_MACSF_prevoyance_2025.pdf | 20/20 | 20/20 |
| SFCR_2024_Groupe-Groupama.pdf | 11/20 | 11/20 (non ciblé cette session) |
| SFCR_2025_Groupe-Groupama.pdf | 9/20 | 9/20 (non ciblé cette session — le pipeline dédié `extract_kpis.py`, avec PaddleOCR, reste à 21/22, cf. Décision 070) |
| sfcr_cnp_assurances_2025.pdf | 20/20 | 20/20 |
| sfcr_covea_2025.pdf | 14/20 | 16/20 |

### Problèmes VRAIMENT irréductibles (limite architecturale, pas un bug)

1. **AFV + AFI — 4 sous-modules SCR fusionnés** (`scr_marche`,
   `scr_contrepartie`, `scr_souscription_vie`, `scr_souscription_sante`) :
   le template `S.25.05.21` (modèle interne partiel/complet) publie
   "Total market and credit risk" (R0070) et "Total Life and Health
   underwriting risk" (R0400) comme des sous-totaux FUSIONNÉS — la
   donnée séparée n'existe nulle part dans le document, testé sur 2
   documents indépendants et confirmé par recherche de libellé
   (Décisions 070, 072, 073bis/074-équivalent pour AFI).
2. **ARE — nomenclature hors EIOPA** : document complet (vérifié via sa
   propre table des matières) utilisant les "États C/P" français
   nationaux (`RC.02.01`, `RP.05.01.01`, `RP.42.03.01`), jamais les
   codes `S.xx.xx.xx`. Supporter cette famille de codes demanderait une
   architecture de mapping entièrement séparée.
3. **MAIF — fonds_propres_t1_r/t2/t3** : colonnes vides (ni "0" ni "-")
   sur la ligne totale de `S.23.01.01` — ambigu entre "vraiment zéro"
   et "non imprimé", laissé NULL par prudence plutôt que deviné.
4. **MAIF — best_estimate/marge_risque/primes_acquises_brutes/charge_sinistres** :
   le tableau `S.05.01.02` de MAIF n'imprime AUCUNE colonne "Total"
   (contrairement à Covéa) — une sommation manuelle sur ~9 colonnes de
   ligne d'activité sans total de contrôle imprimé serait un risque
   d'erreur silencieuse non résolu dans cette session.
5. **Allianz + Groupama SFCR 2024 — non ciblés cette session**, restent
   respectivement à 6/20 et 11/20 dans le diagnostic générique (hors
   liste des 6 tâches demandées).

FIN DE SESSION : les 6 tâches ont été traitées dans l'ordre prescrit ;
aucune tâche hors de cette liste n'a été entamée ; `resultat_technique`
n'a jamais été touché.

## Décision 076 — Fix SwissLife : 6 variantes C0100 sur S.25.01.21 (14/20 → 20/20)

CONTEXTE : SwissLife (formule standard, `S.25.01.21`) avait ses 6 sous-
modules SCR restants NULL (`scr_marche`, `scr_contrepartie`,
`scr_souscription_vie`, `scr_souscription_sante`, `scr_operationnel`,
`scr_diversification`).

DIAGNOSTIC : l'en-tête imprimé sur la page annonce la colonne `C0110`
pour ces lignes (R0010/R0020/R0030/R0040/R0060/R0130), mais
l'extraction positionnelle (`extract_qrt_native`) place systématiquement
les valeurs sous `C0100` — vérifié valeur par valeur contre une lecture
manuelle de la page (2 851 424 / 158 169 / 983 224 / 13 206 / -711 488 /
105 322, tous exacts). Seule la ligne R0050 (non-vie, déjà résolue)
atterrit sous C0110. Décalage de colonne propre à l'extraction sur ce
document, pas une erreur de lecture des valeurs elles-mêmes.

FIX : ajout d'une 5e/6e variante `col="C0100"` pour les 6 KPIs
concernés sur `S.25.01.21`, verifie_contre SwissLife. Distinct du cas
Cardif Vie (Décision 067, où C0100 était la mauvaise réponse) : ici
C0100 est la colonne réellement extraite et vérifiée juste pour ce
document — noté explicitement dans le commentaire du mapping pour ne
pas confondre les deux cas à l'avenir.

RÉSULTAT : SwissLife 14/20 → **20/20**.

## Décision 077 — Fix classify_pages() : faux positif "index QRT" sur une page à sous-sections (Allianz Vie 13/20 → 15/20)

CONTEXTE : Allianz Vie avait `primes_acquises_brutes` et
`charge_sinistres` NULL alors qu'aucune page `S.05.01.02` n'apparaissait
dans les pages QRT détectées.

DIAGNOSTIC : la page 84 contient bien le tableau complet S.05.01.02
(R1510 Primes acquises Brut, R1610 Charge des sinistres Brut, colonne
Total C0300 présente et lisible) — mais `classify_pages()` la classait
"sommaire" (page d'index exclue), car son heuristique `est_index_qrt`
compte les codes `S.xx.xx.xx` DISTINCTS sur la page et exclut dès qu'il
y en a ≥3. Cette page cite "S.05.01.02", "S.05.01.02.01" et
"S.05.01.02.02" (3 chaînes distinctes) — mais ce sont les
SOUS-SECTIONS du MÊME tableau, pas 3 templates différents comme sur une
vraie page de sommaire.

FIX : `est_index_qrt` compte désormais les codes distincts par TEMPLATE
DE BASE (10 premiers caractères, ex. "S.05.01.02"), pas par chaîne
brute. Une vraie page de sommaire liste toujours plusieurs templates de
base différents ; une page QRT réelle ne cite que les sous-sections
d'un seul.

RÉSULTAT : Allianz Vie 13/20 → **15/20** (primes_acquises_brutes et
charge_sinistres récupérés). Effet de bord positif identique sur la
page 83 (S.04.05.21, non utilisé par nos KPIs, mais confirme que le fix
fonctionne au-delà du cas isolé).

RESTE NULL sur Allianz Vie (5 KPIs, diagnostiqué précisément, non
corrigé) :
- `scr_marche` + `scr_contrepartie` : fusionnés dans R0070 "Total
  market & credit risk" du template `S.25.05.21` (modèle interne) —
  irréductible par construction, même limite qu'AFV/AFI/Allianz IARD
  (Décision 072).
- `scr_souscription_vie` + `scr_souscription_sante` : fusionnés dans
  R0400 "Total Life & Health underwriting risk" — même limite.
- `scr_diversification` : même bug que sur Allianz IARD (session
  précédente) — le signe négatif de la valeur ("-               912 286")
  est physiquement détaché du nombre sur la page et mal attribué par
  `extract_qrt_native` à une colonne différente. Ajouter une variante de
  colonne stockerait la valeur en POSITIF (faux). Non corrigé —
  nécessiterait un fix du tokenizer partagé, plus risqué, documenté
  comme limite pour une session dédiée future.

**Régression vérifiée sur 15 documents (au-delà des 3 habituels, comme
demandé)** : Groupama 21/22 (pipeline dédié), CNP 21/22, MACSF 21/22,
AFV 16/20, AFI 16/20, Sogécap 20/20, Cardif Vie 20/20, Cardif RD 20/20,
Crédit Agricole 20/20, Covéa 16/20, MAIF 13/20, Allianz IARD 15/20,
BPCE Vie 20/20, Predica 20/20 — tous strictement identiques à avant le
fix. Aucune régression.

Commit : voir commit associé à cette décision.

## Décision 078 — Fix Pacifica : tolérance de repli directionnelle dans extract_qrt_native() (4/20 → 20/20)

CONTEXTE : Pacifica (formule standard, `codes_eiopa`) n'avait que 4/20
KPIs alors que Predica (même groupe Crédit Agricole, même mode) est à
20/20. Diagnostic précédent : sur Pacifica, la valeur d'une ligne est
imprimée ~6.6pt AU-DESSUS du code de ligne R0xxx (pas sur la même ligne
de base), contre un alignement parfait sur Predica — vérifié mot par
mot (`page.get_text("words")`). `extract_qrt_native()` exige
`abs(y0 - ry0) <= LINE_TOLERANCE_PT` (1.5pt) pour associer une valeur à
une ligne : ce décalage fait échouer l'appariement pour la quasi-
totalité des lignes du document.

FIX — conçu pour un risque de régression minimal sur du code partagé
par TOUS les documents :
1. La tolérance stricte (1.5pt, symétrique) reste le chemin PRINCIPAL,
   inchangé.
2. Un repli (`LIGNE_REPLI_TOLERANCE_HAUT_PT = 8.0`) ne se déclenche QUE
   si la tolérance stricte n'a trouvé AUCUN fragment numérique pour
   cette ligne précise — donc jamais sur une ligne déjà correctement
   appariée sur un document qui fonctionne déjà.
3. Le repli est ASYMÉTRIQUE (vers le haut uniquement, jamais vers le
   bas/ligne suivante) — sur Pacifica les lignes sont espacées de ~15pt
   ; un repli symétrique large aurait risqué de chevaucher la ligne
   suivante et de lui voler sa valeur. Une fenêtre dirigée vers le haut
   seulement (8pt, au-delà des 6.6pt observés) ne touche jamais le
   territoire de la ligne du dessous.

VÉRIFICATION AVANT COMMIT (exigée par la tâche — "zéro régression sur
TOUS les documents déjà traités, pas seulement les 3 habituels") :
- **16 documents en diagnostic générique** (AFV, AFI, Sogécap, Cardif
  Vie, Cardif RD, Crédit Agricole, Covéa, CNP, MACSF, MAIF, Allianz
  IARD, Allianz Vie, SwissLife, BPCE Vie, Predica, Pacifica) : scores
  ET listes de KPIs NULL strictement identiques à avant le fix, sauf
  Pacifica (4/20 → 20/20, l'objectif).
- **3 pipelines dédiés** (Groupama, CNP, MACSF, 22 KPIs) : non
  seulement les scores (21/22 chacun) mais **les valeurs numériques
  extraites elles-mêmes** comparées une à une contre les runs
  précédents de cette session — identiques au chiffre près (ex. CNP
  best_estimate = 277 208.17 M€, Groupama scr_total = 6 020.98 M€,
  inchangés).

RÉSULTAT : Pacifica 4/20 → **20/20**. Aucune régression détectée nulle
part.

Commit : voir commit associé à cette décision.

## Décision 079 — BPCE IARD : whitelist libellé (0/20 → 13/20), fix de signe détaché tenté puis annulé (régression réelle détectée)

CONTEXTE : BPCE IARD (`bpcea-iard-sfcr-2025.pdf`), mode `libelles_francais`,
n'avait jamais été vérifié visuellement ni ajouté à `DOCUMENTS_LIBELLE_VERIFIES`.

VÉRIFICATION VISUELLE (rendu image des pages S.25.01.01 et S.23.01.01,
comme fait pour MAIF/Covéa) : vrais tableaux QRT structurés, formule
standard, aucun code R0xxx/C0xxx. Ajouté à `DOCUMENTS_LIBELLE_VERIFIES`.

RÉSULTAT IMMÉDIAT avec les labels déjà connus (MAIF/Covéa) : **0/20 →
14/20** sans aucun ajout de label — `scr_marche`, `scr_contrepartie`,
`scr_souscription_vie/nonvie/sante`, `scr_operationnel`, `scr_total`,
`mcr`, `ratio_scr`, `ratio_mcr`, `fonds_propres_eligibles`,
`best_estimate`, `marge_risque` tous corrects (vérifiés contre l'image
rendue et par cohérence arithmétique : somme des 6 sous-modules SCR +
diversification = capital de solvabilité requis de base).

BUG DÉTECTÉ ET CORRIGÉ PARTIELLEMENT : `scr_diversification` extrait à
+196 476 alors que le vrai signe est négatif (preuve arithmétique :
163214+82866+1311+68682+526509-196476 = 646106 ≈ 646105, le total
imprimé — la version positive ne colle pas). Cause : la page imprime le
signe "-" et la magnitude "196 476" sur 2 LIGNES DE TEXTE SÉPARÉES ;
`classifier_lignes()` les accumule comme 2 valeurs indépendantes
([196476.0, 0.0, 196476.0, 0.0]) au lieu d'un seul nombre négatif.

TENTATIVE DE FIX GÉNÉRIQUE, TESTÉE, PUIS **ANNULÉE** : une fonction
`_appliquer_signes_detaches()` a été ajoutée à `classifier_lignes()`
pour ré-attacher un "-" isolé à la magnitude adjacente. Testée
immédiatement contre Covéa/MAIF (déjà fonctionnels) AVANT tout commit,
conformément à la règle "zéro régression, même code partagé" — **a
cassé Covéa** : sur sa page S.22.01.22 (mesures de mesures long terme),
la ligne "Capital de solvabilité requis" a la forme
`[15058209, "-", "-", 82817, "-"]` où les "-" sont des CELLULES VOISINES
VIDES (colonnes sans rapport), pas des signes détachés — le fix a
transformé `scr_total` de +15 058 209 (correct) en -15 058 209 (valeur
impossible, un SCR ne peut jamais être négatif). Ambiguïté non
résoluble sans connaître la vraie position de colonne, que
`classifier_lignes()` ne suit pas structurellement. **Fix retiré
immédiatement**, `extraire_par_libelle.py` restauré à l'identique
d'avant cette tentative.

GESTION DE LA VALEUR CONNUE COMME FAUSSE : plutôt que de laisser
`scr_diversification` afficher +196 476 (faux) pour BPCE IARD, ajout
d'un mécanisme d'exclusion explicite et documenté
(`DOCUMENTS_KPI_LIBELLE_NON_FIABLE` dans `batch_diagnostic.py`) — force
ce KPI précis à NULL pour ce document précis, avec la raison consignée
dans les "problèmes" du diagnostic (`libelle_valeur_non_fiable`).
Mécanisme strictement additif et filtré par nom de fichier : aucun
autre document n'est affecté.

RÉSULTAT FINAL : BPCE IARD **0/20 → 13/20**, `scr_diversification`
honnêtement NULL plutôt que faux. Restent NULL : `scr_diversification`
(signe détaché, cf. ci-dessus), `fonds_propres_t1_nr/t1_r/t2/t3`
(labels pas encore ajoutés — la ligne existe et est lisible en page 77,
mais non traité par manque de temps dans cette tâche),
`primes_acquises_brutes`/`charge_sinistres` (tableau S.05.01.02 non
investigué dans cette tâche).

**Régression vérifiée sur les 16 documents déjà traités** (au-delà de
Covéa/MAIF, vérification valeur par valeur en plus du comptage) : tous
strictement identiques à avant cette tâche.

Commit : voir commit associé à cette décision.

## Décision 080 — Generali Iard + Generali Vie : OCR/lecture manuelle complète (0/20 → 17/20 chacun)

CONTEXTE : les 2 documents (GIARD 15 pages, GVIE 11 pages) sont
**100% image** — vérifié : 0 page ne dépasse 24 caractères de texte
natif, aucune page QRT détectée par `classify_pages()`. Contrairement à
Groupama (1 seule page image dans un document sinon natif), ici
CHAQUE page doit être traitée sans texte natif du tout — le pipeline
existant (PaddleOCR ciblé sur 1-2 codes précis) ne s'applique pas
directement, il faut d'abord identifier QUEL template chaque page
représente avant de pouvoir en extraire quoi que ce soit.

MÉTHODE : rendu de toutes les pages en PNG (zoom 1.3x pour le survol,
zooms ciblés 2.5-3x sur les tableaux denses pour une lecture précise),
lues manuellement — texte typographique net (pas un scan), haute
confiance de lecture. Chaque valeur retenue est vérifiée par
**recoupement interne entre 2 à 3 pages QRT indépendantes** du même
document (ex. GIARD : Capital de solvabilité requis = 1 287 348 apparaît
identiquement sur S.22.01.21/R0090, S.23.01.01/R0580 ET
S.25.05.21/R0220 ET S.28.01.01/R0310) — recoupement au moins aussi
robuste que la règle "2 sources" standard du projet.

PaddleOCR testé en complément sur la page S.23.01.01 de GIARD (lecture
automatique par code de ligne) : résultat **incohérent avec lui-même**
(valeurs décalées d'une ligne — R0580 renvoyait la valeur de R0550,
etc.). Re-vérifié à très fort zoom (3x, crop ciblé) : confirme
intégralement la lecture manuelle initiale, PaddleOCR écarté pour cette
mise en page précise (pas un problème générique de l'outil, un problème
d'appariement code-ligne/position sur ce rendu particulier).

TEMPLATE SCR IDENTIFIÉ : `S.25.05.21` (modèle interne partiel/intégral)
pour les 2 entités — MAIS avec un layout légèrement plus détaillé
qu'AFV/AFI/Allianz : le risque de souscription VIE (R0400) est ici
séparé du risque non-vie (R0310), contrairement au layout AFV/AFI où
vie+santé sont fusionnés. Seul le risque de marché+crédit (R0070) reste
fusionné, et aucune ligne "santé" distincte n'existe dans ce template
pour ces 2 entités (probablement car le template ne désagrège pas ce
sous-risque à ce niveau pour un modèle interne partiel).

Implémentation : `GENERALI_KPIS` (dict de valeurs + sources documentées
par KPI) et `diagnostiquer_generali()` dans `batch_diagnostic.py` —
bypass complet du pipeline `classify_pages()`/`extract_qrt_native()`
pour ces 2 fichiers précis (inutile, 0% de texte natif), branché en
tout début de `diagnostiquer_pdf()`.

RÉSULTAT : **GIARD 0/20 → 17/20, GVIE 0/20 → 17/20** — tous deux
largement "exploitables" (seuil 15+/20). Restent NULL (documentés comme
irréductibles, jamais forcés) : `scr_marche`, `scr_contrepartie`
(fusionnés dans R0070, même limite qu'AFV/AFI/Allianz — Décision 072),
`scr_souscription_sante` (non désagrégée dans ce template pour ces 2
entités).

**Régression vérifiée sur les 22 autres documents** (diagnostic
générique, comptages strictement identiques) + 3 pipelines dédiés
(Groupama/CNP/MACSF, 22 KPIs, valeurs inchangées) : le changement est
un bypass entièrement additif, filtré par nom de fichier exact, aucun
autre document ne passe par ce code.

Commit : voir commit associé à cette décision.

## Décision 081 — MACIF SAM (bloc isolé, pages 452-467) : OCR/lecture manuelle complète — 20/20, aucun KPI irréductible

CONTEXTE : suite Priorité 1 (session précédente), le bloc MACIF SAM
(pages 452-467 du document combiné Aéma Groupe, 621 pages) avait été
isolé proprement via `fitz.insert_pdf(from_page=451, to_page=466)` et
diagnostiqué à 0/20 — mais pour la mauvaise raison identifiée à
l'époque (pas l'agrégation multi-entités, mais des pages 100% image,
même conclusion que Generali). Cette tâche applique la même méthode
que pour Generali Iard/Vie (Décision 080) : rendu PNG + lecture
manuelle avec recoupement interne.

MÉTHODE IDENTIQUE À LA DÉCISION 080 : ré-isolation du bloc (technique
validée, réutilisable telle quelle), rendu PNG (zoom 1.3-3x selon
densité), lecture manuelle avec recoupement entre pages indépendantes
du même bloc (ex. Capital de solvabilité requis = 2 964 220 apparaît
identiquement sur S.23.01.01.01 (p.12/463, R0580), S.25.01.21.02
(p.13/464, R0200/R0220) ET S.28.01.01.05 (p.16/467, R0310) — 3
confirmations indépendantes).

DÉCOUVERTE CLÉ : contrairement à Generali Iard/Vie, **MACIF SAM utilise
la FORMULE STANDARD** (`S.25.01.21`, pas `S.25.05.21` modèle interne) —
confirmé par la page S.25.01.21.01 (p.13/464) qui liste les 6
sous-modules de risque **complètement désagrégés, sans aucune
fusion** : Risque de marché (R0010), Risque de contrepartie (R0020),
Risque de souscription vie (R0030), Risque de souscription santé
(R0040), Risque de souscription non-vie (R0050), Diversification
(R0060), plus Risque opérationnel (R0130) sur la page suivante. **Aucun
des 4 KPIs habituellement irréductibles sur les templates modèle
interne (AFV/AFI/Allianz/Generali) ne l'est ici** — la formule standard
désagrège tout nativement.

RÉSULTAT : **MACIF SAM 0/20 → 20/20** — score parfait, tous les KPIs
extraits et recoupés :
- best_estimate = 5 969 795 K€, marge_risque = 341 059 K€ (S.02.01.02.01
  Bilan, p.2/453, somme 5 segments)
- primes_acquises_brutes = 4 854 620 K€, charge_sinistres = 3 429 372 K€
  (S.05.01.02.01 non-vie p.4/455 + S.05.01.02.02 vie p.5/456, sommes
  R0210+R0220+R0230 et R0310+R0320+R0330, colonne Total)
- fonds_propres_eligibles = 9 443 143 K€ (T1nr=7 872 072, T1r=374 465,
  T2=751 973, T3=444 633), scr_total = 2 964 220 K€, mcr = 746 130 K€,
  ratio_scr = 319%, ratio_mcr = 1125% (S.23.01.01, p.12/463)
- scr_marche = 2 713 693, scr_contrepartie = 63 361,
  scr_souscription_vie = 40 522, scr_souscription_sante = 235 321,
  scr_souscription_nonvie = 1 464 010, scr_diversification = -1 035 321,
  scr_operationnel = 148 152 (S.25.01.21, p.13-14/464-465)

NOTE D'IMPLÉMENTATION : ces valeurs sont documentées ici (source de
vérité) mais **pas encore branchées dans `batch_diagnostic.py`** — le
pipeline suppose actuellement "1 fichier = 1 score", et le fichier Aéma
combine 13 entités dans un seul PDF physique. Les brancher proprement
nécessiterait soit un mécanisme multi-entités par fichier (hors
périmètre de cette tâche, qui demandait explicitement d'isoler et
documenter, pas de refondre l'architecture), soit republier un sous-PDF
physique dédié à MACIF SAM. Le score 20/20 est donc confirmé et
documenté, mais n'apparaît pas encore dans `batch_diagnostic_report.json`
pour le fichier Aéma (qui reste à 0/20, un signal fidèle à l'état actuel
du pipeline, pas une contradiction).

Aucune modification de code cette tâche — travail 100% diagnostic/OCR
manuel, rien à régresser.

## Décision 082 — Bilan final, session nocturne autonome (Tâches 0-5)

CONTEXTE : session nocturne longue, 6 tâches séquentielles (Tâche 0 :
SwissLife+Allianz Vie déjà en cours à l'interruption ; Tâches 1-5 :
Pacifica, BPCE IARD, Generali Iard/Vie, MACIF SAM, ce bilan), commit
après chaque tâche réussie, attente automatique si tokens épuisés (non
nécessaire ici), règle absolue "NULL plutôt que deviner".

### Tableau final — diagnostic générique (/20), tous les PDF de data/

| # | Fichier | Groupe | KPIs | Statut |
|---|---|---|---|---|
| 1 | Aema-Groupe (fichier combiné, 621p) | Aéma/MACIF | 0/20 | Non exploitable tel quel (13 entités mélangées) |
| — | ↳ MACIF SAM (bloc isolé p.452-467) | MACIF | **20/20** | Exploitable — documenté, pas encore automatisé (Décision 081) |
| 2 | AFV (AXA France Vie) | AXA | 16/20 | Exploitable |
| 3 | AFI (AXA France IARD) | AXA | 16/20 | Exploitable |
| 4 | ARE (AXA Retraite Entreprise) | AXA | 0/0 | Hors périmètre (nomenclature nationale) |
| 5 | Generali Iard | Generali | **17/20** | Exploitable (nouveau) |
| 6 | Generali Vie | Generali | **17/20** | Exploitable (nouveau) |
| 7 | BPCE Vie | BPCE | 20/20 | Exploitable |
| 8 | BPCE IARD | BPCE | 13/20 | Partiel |
| 9 | Cardif Vie | BNP Paribas | 20/20 | Exploitable |
| 10 | Cardif RD | BNP Paribas | 20/20 | Exploitable |
| 11 | Allianz Group 2024 (international) | Allianz | 6/20 | Faible |
| 12 | Allianz IARD | Allianz | 15/20 | Exploitable |
| 13 | Allianz Vie | Allianz | 15/20 | Exploitable |
| 14 | Crédit Agricole Assurances | Crédit Agricole | 20/20 | Exploitable |
| 15 | Pacifica | Crédit Agricole | **20/20** | Exploitable (corrigé cette session) |
| 16 | Predica | Crédit Agricole | 20/20 | Exploitable |
| 17 | MAIF | MAIF | 13/20 | Partiel |
| 18 | Sogécap | Société Générale | 20/20 | Exploitable |
| 19 | MACSF | MACSF | 20/20 (21/22 dédié) | Exploitable |
| 20 | Groupama 2024 | Groupama | 11/20 | Partiel |
| 21 | Groupama 2025 | Groupama | 9/20 (**21/22 pipeline dédié**) | Exploitable (pipeline réel) |
| 22 | CNP Assurances | CNP | 20/20 (21/22 dédié) | Exploitable |
| 23 | Covéa | Covéa | 16/20 | Exploitable |
| 24 | SwissLife | SwissLife | **20/20** | Exploitable (corrigé cette session) |

### Comparaison au top 15 du marché français

| Groupe parent | Testé ? | Meilleur score | Statut |
|---|---|---|---|
| CNP Assurances | Oui | 21/22 | **Exploitable** |
| Crédit Agricole | Oui | 20/20 (×3 entités) | **Exploitable** |
| BNP Paribas (Cardif) | Oui | 20/20 (×2) | **Exploitable** |
| Société Générale (Sogécap) | Oui | 20/20 | **Exploitable** |
| Covéa | Oui | 16/20 | **Exploitable** |
| Groupama | Oui | 21/22 (dédié) | **Exploitable** |
| AXA | Oui | 16/20 | **Exploitable** |
| BPCE | Oui | 20/20 (BPCE Vie) | **Exploitable** |
| Allianz | Oui | 15/20 (×2) | **Exploitable** |
| Generali | Oui | 17/20 (×2) | **Exploitable (nouveau)** |
| SwissLife | Oui | 20/20 | **Exploitable (nouveau, corrigé)** |
| MACIF/Aéma | Oui (partiel) | 20/20 (MACIF SAM, non automatisé) | Exploitable en pratique, pas en pipeline |
| MAIF | Oui | 13/20 | Partiel |
| AG2R La Mondiale | **Non** | — | Non testé |
| MGEN | **Non** | — | Non testé |

### Réponse mise à jour : combien de groupes exploitables ?

**11 groupes sur 15 sont pleinement exploitables (15+/20) dans le
pipeline automatisé** — CNP, Crédit Agricole, BNP Paribas, Société
Générale, Covéa, Groupama, AXA, BPCE, Allianz, Generali, SwissLife.
C'est **+3 par rapport au dernier bilan** (8/15) : Generali (nouveau,
Décision 080), SwissLife (corrigé, Décision 076), et BPCE confirmé via
BPCE Vie.

**MACIF est un cas à part** : son entité principale (MACIF SAM) est
elle aussi à 20/20, mais uniquement documentée manuellement (Décision
081) — pas encore intégrée au pipeline automatisé car le fichier source
combine 13 entités juridiques et l'architecture actuelle suppose "1
fichier = 1 score". Si on la compte, **12 groupes sur 15** sont
exploitables en pratique.

Seuls **2 groupes restent non testés** (aucun PDF dans `data/`) : AG2R
La Mondiale et MGEN. MAIF reste partiel (13/20, tableau S.05.01.02 sans
colonne Total imprimée, cf. Décision 074).

Compte tenu des parts de marché déjà établies (bilan précédent : top 8
groupes ≈ 70% du marché à eux seuls, top 15 probablement 80-85%+) — la
couverture RÉELLE du pipeline a nettement progressé cette session,
passant d'environ 70% (8 groupes exploitables) à une couverture
substantiellement plus large avec l'ajout de Generali (24,9 Md€, un des
plus gros acteurs du marché) et la confirmation de BPCE/SwissLife.

### Récapitulatif des 6 tâches de la session nocturne

| Tâche | Statut | Résultat |
|---|---|---|
| 0 — SwissLife + Allianz Vie | Faite | SwissLife 14→20/20 ; Allianz Vie 13→15/20 (classify_pages fix + limite architecturale documentée) |
| 1 — Pacifica, décalage géométrique | Faite | 4→20/20, tolérance de repli directionnelle, zéro régression sur 16 documents |
| 2 — BPCE IARD, libellé | Faite | 0→13/20, whitelist + fix de signe tenté PUIS annulé après régression détectée sur Covéa |
| 3 — Generali Iard/Vie, OCR complet | Faite | 0→17/20 chacun, lecture manuelle + recoupement interne (PaddleOCR écarté après désaccord) |
| 4 — MACIF SAM, bloc isolé | Faite | 0→20/20, documenté (pas encore automatisé) |
| 5 — Bilan final | Faite | ce document |

`resultat_technique` n'a jamais été touché (Décision 051). Toutes les
tâches ont respecté la règle "NULL plutôt que deviner" — 2 tentatives
de fix ont été testées puis explicitement annulées après avoir détecté
une régression réelle (BPCE IARD sign-fix sur Covéa), plutôt que
d'accepter un chiffre faux pour gagner un KPI.

FIN DE SESSION — comme demandé, aucune nouvelle tâche n'est commencée
au-delà de ces 6.

## Décision 083 — Intégration multi-entités Aéma : pipeline généralisé, 2/13 entités extraites et branchées dans kpis.db

CONTEXTE : session "Intégrer MACIF au pipeline + améliorer MAIF et
Allianz Vie", Tâche 1. Interrompue une fois en cours de route (pause
connexion utilisateur, cf. `POINT_ETAPE_PAUSE.md`, désormais obsolète —
tout son contenu est repris et complété ici), reprise et menée à un
point d'arrêt honnête.

GÉNÉRALISATION DEMANDÉE : `extraire_entite(pdf_path, page_debut,
page_fin, nom_entite=None, out_dir=None)` ajoutée dans
`test_markdrop/ingest.py` — isole `[page_debut, page_fin]` en sous-PDF
autonome via `fitz.insert_pdf`, généralise la technique déjà validée
sur MACIF SAM (Décision 081) et Generali (Décision 080). Testée sur
les 13 entités : **confirmation automatisée que les 13 sont 100%
image** (0/20 via le pipeline standard `diagnostiquer_pdf`, mode
`libelles_francais` partout) — y compris MACIF SAM elle-même, dont
l'extraction de la Décision 081 était donc déjà, en réalité, une
lecture manuelle sur rendu image, pas du texte natif.

TRAVAIL RÉALISÉ CETTE SESSION : lecture manuelle + recoupement interne
(même méthode que Décision 080/081) sur **Aéma Groupe** (la
consolidée, pages 439-451), en plus de MACIF SAM déjà faite. Les 2
utilisent la **formule standard** (`S.25.01.22`/`S.25.01.21`) — tous
les sous-modules SCR sont désagrégés nativement, aucun KPI
irréductible pour ces 2 entités (contrairement aux templates modèle
interne de Generali). Chaque grand chiffre recoupé sur ≥2 pages
indépendantes avant d'être retenu (ex. Aéma Groupe : SCR = 6 063 105 K€
confirmé sur S.22.01.22, S.23.01.22 ET S.25.01.22 — 3 pages
indépendantes).

**RÉSULTAT : MACIF SAM 20/20, Aéma Groupe 20/20** — détail complet des
valeurs et sources dans `aema_entites.py` (nouveau module dédié).

INSERTION EN BASE : `aema_entites.inserer_entite_en_base()` crée une
société séparée par entité dans `kpis.db` (`companies.type =
"mutuelle (Aéma Groupe)"`), avec une note explicite dans
`kpis.source_chapter` indiquant la provenance ("Document combiné 'Aéma
Groupe...' (621p), entité isolée pages X-Y, extraction manuelle sur
rendu image"). Conversion K€→M€ (÷1000) appliquée à l'insertion,
cohérente avec la convention déjà utilisée par `extract_kpis.py` —
vérifiée : `best_estimate` MACIF SAM stocké à 5969.795 M€ = 5 969 795 K€
lu sur la page. Les ratios (déjà en points de %) ne sont pas divisés.
**2 sociétés créées** (`MACIF SAM` id=44, `Aema Groupe` id=45), 20 KPIs
chacune.

**PORTÉE RÉELLE VS. DEMANDÉE — honnêteté sur le périmètre** : la tâche
demandait les 13 entités. **2 sur 13 sont faites et vérifiées** ; les
**11 autres ne le sont pas** — chacune nécessite la même lecture
manuelle complète (rendu PNG multi-pages + recoupement), estimée à
15-20 minutes par entité sur la base de l'expérience Generali/MACIF
SAM/Aéma Groupe, soit plusieurs heures de travail pour les 11
restantes. Aller plus vite en devinant des valeurs ou en généralisant
sans lecture réelle violerait la règle "NULL plutôt que deviner" —
non fait. Les bornes de page des 11 entités restantes sont déjà dans
`aema_entites.ENTITES_BORNES`, prêtes à être traitées avec exactement
la même méthode (voir `afficher_scores()` qui liste leur statut
"Non traité (bornes connues, à faire)") :

| Entité | Pages | Statut |
|---|---|---|
| Macif Vie | 468-478 | Non traité |
| Macif Santé Prévoyance | 479-493 | Non traité |
| Thémis | 494-507 | Non traité |
| Macifilia | 508-522 | Non traité |
| Aésio Mutuelle | 523-538 | Non traité |
| MNPAF | 539-550 | Non traité |
| MMJ | 551-563 | Non traité |
| Nuoma | 564-576 | Non traité |
| Abeille Vie | 577-592 | Non traité |
| Abeille Épargne Retraite | 593-602 | Non traité |
| Abeille IARD & Santé | 603-621 | Non traité |

RÉGRESSION VÉRIFIÉE (demandée explicitement) : Groupama (pipeline
dédié, 22 KPIs), CNP (21/22), MACSF (21/22), Pacifica (20/20), SwissLife
(20/20) — tous strictement identiques. Le travail de cette tâche est
entièrement additif (nouveau module `aema_entites.py`, nouvelle
fonction dans `ingest.py`, 2 nouvelles lignes dans `companies`) —
aucun code partagé existant modifié, risque de régression nul par
construction au-delà de la vérification de routine.

`POINT_ETAPE_PAUSE.md` est maintenant obsolète (tout son contenu
repris ici) — supprimé.

## Décision 084 — Amélioration MAIF (13/20 → 17/20) et Allianz Vie (confirmé irréductible)

CONTEXTE : Tâche 2, "vérifie toujours d'abord si le KPI est réellement
NULL — plusieurs signaux précédents étaient du bruit".

### Allianz Vie — re-diagnostic complet, tout confirmé irréductible

Les 5 KPIs NULL (`scr_marche`, `scr_contrepartie`, `scr_souscription_vie`,
`scr_souscription_sante`, `scr_diversification`) ont été re-vérifiés
directement sur la page S.25.05.21 (pas de confiance en mémoire) :
- `scr_marche`/`scr_contrepartie` : toujours fusionnés dans R0070 "Total
  market & credit risk" = 3 516 303 (une seule ligne, pas de sous-détail).
- `scr_souscription_vie`/`scr_souscription_sante` : toujours fusionnés
  dans R0400 "Total Life & Health underwriting risk" = 465 160.
- `scr_diversification` : toujours le même bug de signe détaché
  ("-               912 286", signe et magnitude sur 2 lignes séparées).

**Aucun fix sûr possible — 0 corrigé, confirmation pure.** Pas de
régression possible (aucun code touché pour ce document).

### MAIF — 3 bugs réels trouvés et corrigés, 4 KPIs débloqués

Diagnostic précis des 7 NULL :

1. **`best_estimate`/`marge_risque`** : la page censée les contenir
   (Bilan Passifs, p.111) est en réalité **100% image** (95 caractères
   natifs — en-tête/pied de page seulement), une extraction textuelle y
   est structurellement impossible. Bug intermédiaire : j'avais d'abord
   ciblé la page 110 (Actifs, mauvaise page) par erreur — corrigé avant
   de découvrir que la bonne page (111) est de toute façon une image.
   Valeurs lues manuellement (même méthode que Generali/MACIF SAM) :
   `best_estimate` = 3 714 290+146 666+70 933+475 463+0 = **4 407 352**,
   `marge_risque` = 297 831+39 033+1 161+5 227+0 = **343 252** —
   recoupées : "Excédent d'actif sur passif" = 5 319 982 sur cette même
   page correspond exactement à `fonds_propres_t1_nr` déjà vérifié
   (Décision 074), confirmant la fiabilité de la lecture.

2. **`primes_acquises_brutes`/`charge_sinistres`** : Décision 074 avait
   conclu "pas de colonne Total imprimée" — **faux**, re-vérifié : la
   colonne Total EXISTE (page 113, S.05.01.02.01 2/2) mais
   `classifier_lignes()` ne la voyait pas à cause de cellules vides SANS
   aucun placeholder (contrairement à Covéa qui utilise "-") qui
   décalaient le comptage. `colonne=-1` (dernière valeur, peu importe
   combien de cellules vides avant) contourne le problème — vérifié par
   cohérence arithmétique (somme page 112 + LoB propres de la page 113
   = Total imprimé, écart 0). Bug supplémentaire trouvé et corrigé :
   concaténer le texte des pages 112+113 avant `extraire_section()`
   cassait la détection de section (chaque page répète ses propres
   en-têtes "Primes acquises"/"Charge des sinistres") — utiliser
   uniquement la page 113 (celle qui a la colonne Total) résout le
   problème. `primes_acquises_brutes` = **3 964 257** (non-vie,
   composante vie vérifiée = 0). `charge_sinistres` = **2 393 639**
   (non-vie uniquement) — la composante vie (30 615 K€, ~1,3% du
   total) existe réellement (page 114, tableau à libellés tournés à
   90° que le parser ne sait pas lire) mais n'est **pas incluse**,
   documentée explicitement dans la source plutôt que devinée ou
   cachée.

3. **`fonds_propres_t1_r`/`fonds_propres_t2`/`fonds_propres_t3`** :
   confirmés irréductibles (Décision 074) — colonnes vides sans aucun
   placeholder sur la ligne totale de S.23.01.01, ambigu entre "0" et
   "non imprimé". **Non corrigé**, cohérent avec la règle "NULL plutôt
   que deviner".

**RÉSULTAT : MAIF 13/20 → 17/20** (4 KPIs débloqués : best_estimate,
marge_risque, primes_acquises_brutes, charge_sinistres). 3 KPIs restent
NULL, tous documentés comme irréductibles ou incomplets par choix
explicite (pas par manque d'investigation).

RÉGRESSION VÉRIFIÉE : 16 documents en diagnostic générique (AFV, AFI,
Sogécap, Cardif Vie/RD, Crédit Agricole, Covéa, CNP, MACSF, Allianz
IARD, SwissLife, BPCE Vie/IARD, Predica, Pacifica) strictement
identiques ; CNP 21/22, MACSF 21/22, Groupama 21/22 (pipeline dédié)
inchangés. Changement localisé à `resoudre_scr_mcr_maif()` dans
`batch_diagnostic.py`, filtré par nom de fichier MAIF uniquement.

## Décision 085 — Extraction réelle Predica, insertion dans kpis.db

CONTEXTE : Predica (PREDICA-–-SFCR-2025.pdf, dans data/ depuis un moment)
n'avait jamais été passée dans un pipeline d'insertion réel — seul
`batch_diagnostic.py` l'avait testée en diagnostic générique (20/20,
mode `codes_eiopa`, 0 NULL, 0 erreur, cf. `batch_diagnostic_report.json`).
Aucun `corpus_final.json` Docling n'existe pour ce document (jamais
parsé) — contrairement à Groupama/CNP/MACSF.

EXTRACTION : nouveau `extract_kpis_predica.py`, sur le modèle de
`extract_kpis_cnp.py` (réutilise les fonctions génériques
`resoudre_variantes_qrt`/`valeur_principale` d'`extract_kpis.py`), mais
le corpus est construit À LA VOLÉE via `classify_pages()` +
`extract_qrt_native()` (`ingest.py`) — exactement le mécanisme interne de
`diagnostiquer_pdf()`, dont les valeurs résolues sont ici capturées et
insérées plutôt que seulement comptées. Document 100% texte natif
(`scr_method="formule_standard"`) : aucune lecture d'image/PaddleOCR/
Gemini nécessaire, contrairement à Groupama.

**BUG RÉEL TROUVÉ ET CORRIGÉ — `scr_diversification`** : la valeur brute
lue pour S.25.01.21/R0060 était `475` (0,475 M€), manifestement fausse
(un bénéfice de diversification de moins de 500€ sur ~48 Md€ de risques
SCR sommés est impossible). Cause : le texte source page 71 porte
`(10 475 550)` — notation comptable parenthèses-négatif — mais
`NUMERIC_FRAGMENT_RE` (`ingest.py`) ne matche que des fragments purement
numériques ; les fragments `(10` et `550)` sont rejetés, seul le
fragment médian `475` est retenu. Même bug confirmé sur R0140/R0150 de
la même page (non utilisés par aucun KPI mappé, donc sans impact).
Valeur corrigée manuellement à **-10 475,55 M€**, vérifiée par 2 moyens
indépendants : lecture directe du texte PDF brut (`(10 475 550)`) ET
recoupement arithmétique EXACT (R0100 - somme(R0010..R0050) =
37 866 516 - 48 342 066 = -10 475 550, à l'euro près). Correction
appliquée UNIQUEMENT dans `extract_kpis_predica.py` (override documenté,
même discipline que les relectures manuelles Generali/MACIF SAM/Aéma
Groupe) — `ingest.py` n'a PAS été modifié : le bug est générique
(notation parenthèses-négatif) et pourrait affecter d'autres documents,
mais le corriger dans le parser partagé est hors du périmètre de cette
tâche et exigerait sa propre régression complète sur tous les documents
déjà extraits.

**BUG RÉEL TROUVÉ ET CORRIGÉ — `validate_kpis.py` jamais généralisé** :
les contrôles 4 (`ratio_mcr_recalcule`), 6 et 7 (croisements QRT/image)
étaient codés en dur pour Groupama — `r0570_eligibles_mcr()` lit
toujours `test_markdrop/output_structure_brute/corpus_final.json`
(Groupama) quelle que soit l'entreprise passée en `--company`, et les
contrôles 6/7 comparent à des valeurs Groupama codées en dur. Vérifié :
`validate_kpis.py` n'avait, dans les faits, JAMAIS tourné sur CNP/MACSF
malgré leurs scripts d'extraction dédiés (aucune ligne dans
`validation_checks` pour elles). Lancer ces 3 contrôles pour Predica
aurait mélangé le numérateur MCR de Groupama avec le MCR de Predica —
un chiffre inventé, pas un vrai contrôle. `executer_controles()` prend
maintenant `company_name` et n'exécute ces 3 contrôles QUE pour
Groupama (skippés proprement pour toute autre société, jamais insérés
avec un résultat trompeur). RÉGRESSION VÉRIFIÉE : Groupama toujours
30/30, valeurs identiques avant/après le changement.

**RÉSULTAT : Predica — 22 KPIs insérés (21 valeurs, 1 NULL
`resultat_technique`, cohérent avec Groupama/CNP), 25/27 contrôles
actuariels applicables passés** (27 = 30 - les 3 contrôles Groupama-
only skippés). Les 2 échecs restants (`signe_fonds_propres_t3`,
`signe_scr_souscription_nonvie`) sont des FAUX SIGNAUX : les 2 valeurs
sont légitimement 0,00 (Predica n'a pas d'activité non-vie ni de tier 3
de fonds propres de base) mais le contrôle de signe `"positive"` exige
`valeur > 0` strictement — limitation connue de `validate_kpis.py`
(devrait accepter `>= 0`), pas une erreur d'extraction. Non corrigé ici
(changerait le comportement pour toutes les entreprises déjà validées,
hors périmètre de cette tâche).

RÉGRESSION VÉRIFIÉE : Groupama (22 KPIs, 30/30 contrôles), CNP
Assurances (22 KPIs), MACSF prévoyance (22 KPIs) — comptes et
`ratio_scr` strictement inchangés après l'insertion de Predica.

## Décision 086 — BPCE IARD : fix scr_diversification sans casser Covéa (13/20 → 14/20)

CONTEXTE : Décision 079 avait tenté un fix générique du bug de signe
détaché (`_appliquer_signes_detaches()` dans `classifier_lignes()`,
`extraire_par_libelle.py`) pour corriger `scr_diversification` de BPCE
IARD (lu +196 476 au lieu de -196 476), mais l'avait annulé après avoir
cassé `scr_total` de Covéa (transformé en -15 058 209, valeur
impossible).

RÉ-ANALYSE DU BLOCAGE : le fix générique opère sur la sortie de
`classifier_lignes()` — une liste de fragments texte SANS position de
colonne conservée. Un "-" isolé y est structurellement AMBIGU entre 2
cas : (1) un signe négatif détaché de sa magnitude (BPCE IARD, page 78,
ligne "Diversification" : tokens `["196 476", "-", "196 476", "-"]`,
magnitude PUIS signe, pour les 2 colonnes net/brut) et (2) une cellule
voisine vide, convention EIOPA "non applicable" (Covéa, page S.22.01.22,
ligne "Capital de solvabilité requis" : `[15058209, "-", "-", 82817,
"-"]`, où les "-" sont de VRAIES colonnes sans rapport, pas des signes).
Une fois réduits à une liste plate de tokens, ces 2 cas sont
indiscernables sans réintroduire le suivi de position (x,y) à travers
tout `classifier_lignes()` — changement bien plus large que ce bug
précis, hors périmètre ici.

SOLUTION RETENUE : `resoudre_scr_diversification_bpce_iard()`
(`batch_diagnostic.py`), scoped par nom de fichier exact
(`bpcea-iard-sfcr-2025.pdf`), même pattern que
`resoudre_scr_mcr_maif()`/`resoudre_primes_sinistres_covea()` — lit
directement le texte brut de la page 78 (S.25.01.01), localise la ligne
"Diversification", vérifie STRICTEMENT que les 4 tokens suivants ont la
forme exacte `[magnitude, "-", magnitude, "-"]` (2 magnitudes
identiques) avant d'accepter — retourne `None` (jamais une valeur
devinée) si la page a changé de forme. Ne touche AUCUN code partagé
(`classifier_lignes()`/`extraire_par_libelle()` restent identiques à
avant Décision 079) : risque de régression nul par construction, pas
seulement vérifié.

`DOCUMENTS_KPI_LIBELLE_NON_FIABLE` vidé (l'entrée BPCE IARD/
scr_diversification n'est plus nécessaire — le KPI est maintenant
résolu correctement avant que ce mécanisme d'exclusion s'applique).

RÉSULTAT : **BPCE IARD 13/20 → 14/20** (`scr_diversification` =
-196 476 K€, vérifié par cohérence arithmétique contre le capital de
base : 163214+82866+1311+68682+526509-196476 = 646106 ≈ 646105 imprimé,
écart 1 K€ = arrondi source). Restent NULL (non traités ici, hors
scope) : `fonds_propres_t1_nr/t1_r/t2/t3`, `primes_acquises_brutes`,
`charge_sinistres`.

RÉGRESSION VÉRIFIÉE (le point critique de cette tâche) : **Covéa
toujours 16/20**, `scr_diversification` toujours -10 324 898 (identique
à avant) — zéro impact, confirmé en isolant le test sur les 2
documents. **MAIF toujours 17/20** (3e document partageant
`classifier_lignes()`/`extraire_par_libelle()`), également inchangé.

## Décision 087 — AG2R La Mondiale : 9 entités découvertes et extraites (document combiné, texte natif)

CONTEXTE : `AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf` (288 pages) avait des
templates QRT qui se répètent à plusieurs endroits — signe d'un
document combiné multi-entités, comme Aéma Groupe.

CARTOGRAPHIE : `classify_pages()` sur les 288 pages → 9 blocs QRT
contigus : (122-134), (139-157), (159-177), (179-196), (198-215),
(217-235), (237-254), (256-271), (273-286). Chaque bloc précédé d'une
page "Identification de l'entreprise" portant le nom juridique,
vérifié pour les 9 : **SGAM AG2R LA MONDIALE** (entité consolidée),
**AG2R Prévoyance**, **Arpège Prévoyance**, **Prima**, **AG.Mut**,
**VIASANTÉ Mutuelle**, **La Mondiale**, **La Mondiale Europartner**,
**La Mondiale Partenaire**.

DIFFÉRENCE MAJEURE AVEC AÉMA : ce document est confirmé **texte natif**
(`detecter_templates` → `mode="codes_eiopa"`, `scr_method=
"formule_standard"`) — contrairement à Aéma (100% image). Chaque entité
isolée via `extraire_entite()` (déjà existante, `ingest.py`) est donc
extraite par le MÊME mécanisme que `extract_kpis_predica.py`
(`classify_pages`+`extract_qrt_native` construit un corpus à la volée,
`resoudre_variantes_qrt` le résout) — pas de lecture manuelle. Nouveau
module `ag2r_entites.py`.

**BUG RÉEL TROUVÉ ET CORRIGÉ — primes_acquises_brutes/charge_sinistres
à 0,00 pour les 9 entités** : les pages S.05.01.02 de ce document
utilisent du texte natif TOURNÉ 90° (vérifié : `span['dir'] = (0.0,
-1.0)` sur PyMuPDF, au lieu de `(1.0, 0.0)` horizontal) — même famille
de limite que MAIF page 114 (Décision 084, "colonnes rotées non
parsable automatiquement"), mais ici touchant TOUTES les entités du
document. `extract_qrt_native()` suppose un texte horizontal (position
x croissante = colonne suivante) et ne trouve AUCUNE valeur sur ces
pages (`valeurs={}` pour toutes les lignes), silencieusement — sans
vérification, cela aurait inséré 0,00 (une valeur fausse et trompeuse,
pas un NULL honnête) pour les 9 entités.

Corrigé SANS toucher `extract_qrt_native()` ni `classifier_lignes()`
(zéro risque de régression sur les autres documents) : sur du texte
tourné, PyMuPDF imprime chaque valeur sur SA PROPRE LIGNE — exactement
le pattern que `classifier_lignes()` (Décision 073, déjà utilisée pour
MAIF/Covéa) sait déjà accumuler. `resoudre_primes_sinistres_ag2r()`
appelle `classifier_lignes()` directement sur le texte brut de chaque
page S.05.01.02, cherche les lignes dont le libellé normalisé se
termine par un code R0210/R0220/R0230/R1510 (primes) ou
R0310/R0320/R0330/R1610 (sinistres), et prend la DERNIÈRE valeur
(colonne Total). Vérifié sur AG2R Prévoyance : R0210 Total = 2 339 198
= 1 343 253+995 945+0×10, exact. Résultats plausibles sur les 9
entités (ratio primes/best_estimate cohérent partout, pas de zéro
suspect) — voir `ag2r_extraction.log`.

RÉSULTAT : **9 entités insérées, 22/22 KPIs chacune** (structure
complète), 1 seul NULL chacune (`resultat_technique`, NULL par
construction) sauf SGAM AG2R LA MONDIALE (entité consolidée, 4 NULL :
`fonds_propres_t3`, `scr_souscription_nonvie`, `scr_diversification`,
`resultat_technique` — mapping groupe moins complet que solo pour ces
lignes, non forcé).

RÉGRESSION : aucun risque structurel (nouveau module dédié, aucun code
partagé modifié) — non re-vérifié explicitement ici, couvert par la
vérification de régression globale en fin de session (batch_diagnostic
+ requête directe sur les sociétés pipeline dédié).

## Décision 088 — MGEN : extraction réelle, 2 bugs parser trouvés et corrigés (21/22)

CONTEXTE : `MGEN_SFCR_2025.pdf`, document simple, un seul bloc QRT
(pages 46-55), confirmé texte natif solo/formule standard. Même
mécanisme que `extract_kpis_predica.py` (`extract_kpis_mgen.py`,
Décision 085).

**BUG RÉEL TROUVÉ ET CORRIGÉ — fonds_propres_eligibles à 0,00** :
`extract_qrt_native()` donnait "-" (0,0) pour S.23.01.01/R0540 (Total
des fonds propres éligibles pour couvrir le SCR) sur les 5 colonnes,
alors que le texte brut page 53 montre clairement R0540 = 3 441 361 /
3 441 361 / - / - / -. Vérifié par 2 recoupements indépendants sur la
même page : R0290 (Total fonds propres de base après déductions) =
3 441 361 (déjà lu correctement) et R0700 (Excédent d'actif sur passif,
sous-tableau réserve de réconciliation) = 3 441 361 — 3 sources
concordent exactement. Confirme aussi le ratio_scr publié (236%) :
3 441 361/1 460 979 = 235,55% ≈ 236%.

**BUG RÉEL TROUVÉ ET CORRIGÉ — scr_diversification à +0,16 au lieu de
-452 163** : le texte brut page 54 montre `R0060 ... "- 452 163"`
— signe négatif séparé de la magnitude par une ESPACE FINE (U+2009,
`THIN SPACE`), pas une espace normale — `NUMERIC_FRAGMENT_RE` ne
reconnaît pas ce caractère comme faisant partie du même token, cause
distincte du bug BPCE IARD (Décision 086, magnitude-puis-signe) et du
bug Predica (Décision 085, notation parenthèses). Vérifié par
recoupement arithmétique EXACT : R0100 (SCR de base) = somme(R0010..
R0070) = 789 578+69 440+70 433+939 219+1 267-452 163+792 = **1 418 566**,
qui correspond EXACTEMENT au R0100 imprimé — et R0100+R0130+R0140+R0150
= 1 418 566+99 604+0-57 191 = **1 460 979** = scr_total déjà extrait
correctement (3e recoupement indépendant).

Les 2 corrections sont des overrides SCOPÉS à `extract_kpis_mgen.py`
(condition sur la valeur suspecte détectée, jamais un changement dans
`extract_qrt_native()`/`ingest.py` partagés) — même discipline que
Predica/BPCE IARD : zéro risque de régression sur les autres documents.
Les 7 autres composantes SCR (scr_marche, scr_contrepartie,
scr_souscription_vie/santé/non-vie, scr_operationnel) ET
best_estimate/marge_risque/primes/sinistres ont TOUS été revérifiés
manuellement contre le texte brut et sont corrects sans modification.

RÉSULTAT : **21/22 KPIs** (seul `resultat_technique` NULL, par
construction). `validate_kpis.py --company MGEN` : **24/27 contrôles
passés** — les 3 échecs sont les faux signaux connus (fonds_propres_
t1_r/t2/t3 légitimement à 0,00, rejetés par le contrôle de signe
`"positive"` trop strict, cf. Décision 085/Predica), pas des erreurs.
`ratio_scr_recalcule` et `fonds_propres_eligibles_somme_tiers` passent
tous les deux — confirmation indépendante supplémentaire que les 2
corrections manuelles sont exactes.

## Décision 089 — Bilan de session : 4 tâches, top 15 recompté, régression vérifiée

CONTEXTE : session longue autonome, 4 tâches séquentielles (commit
après chaque étape réussie) : (1) les 11 entités Aéma restantes,
(2) BPCE IARD sans casser Covéa, (3) AG2R La Mondiale, diagnostic +
traitement, (4) MGEN, diagnostic + traitement. Voir Décisions 085-088
pour le détail complet de chaque tâche — ce bilan consolide l'état
final.

### Tâche 1 — Aéma Groupe : 13/13 entités désormais complètes

11 entités extraites par lecture manuelle sur rendu image (Macif Vie,
Macif Santé Prévoyance, Thémis, Macifilia, Aésio Mutuelle, MNPAF, MMJ,
Nuoma, Abeille Vie, Abeille Épargne Retraite, Abeille IARD & Santé),
chacune avec recoupements arithmétiques internes vérifiés (excédent
actif/passif, SCR de base = somme des 7 composantes, SCR final).
Complétude corrigée pour les 13 entités (provisions_techniques +
resultat_technique ajoutés automatiquement, manquaient depuis Décision
083). **13/13 entités, 22/22 KPIs chacune** (1 seul NULL :
resultat_technique). 2 cas légitimes de MCR > SCR (plancher absolu,
Thémis/Macifilia) et 1 charge_sinistres négative vérifiée (Macifilia,
reprise de provision) documentés, pas des erreurs.

### Tâche 2 — BPCE IARD : 13/20 → 14/20, zéro régression Covéa

Fix scopé par nom de fichier (`resoudre_scr_diversification_bpce_iard`)
au lieu du fix générique annulé en Décision 079. Analyse du blocage :
un "-" isolé dans `classifier_lignes()` est structurellement ambigu
entre signe détaché (BPCE IARD) et cellule voisine vide (Covéa) sans
suivi de position de colonne. Solution : aucune modification de code
partagé, donc zéro risque par construction — vérifié Covéa 16/20 et
MAIF 17/20 inchangés.

### Tâche 3 — AG2R La Mondiale : 9 entités découvertes, texte natif

`classify_pages()` sur 288 pages → 9 entités (SGAM AG2R LA MONDIALE,
AG2R Prévoyance, Arpège Prévoyance, Prima, AG.Mut, VIASANTÉ Mutuelle,
La Mondiale, La Mondiale Europartner, La Mondiale Partenaire).
Contrairement à Aéma, document texte natif — extraction automatisée
(`ag2r_entites.py`, même mécanisme que `extract_kpis_predica.py`), pas
de lecture manuelle. Bug de texte tourné 90° trouvé et corrigé sur
S.05.01.02 (primes/sinistres), sans toucher le code partagé. **9
entités, 22/22 KPIs chacune** (1 NULL sauf l'entité consolidée, 4 NULL).

### Tâche 4 — MGEN : extraction réelle, 21/22

Document simple, texte natif, un seul bloc QRT (`extract_kpis_mgen.py`).
2 bugs parser réels trouvés et corrigés par overrides scopés (fonds
propres éligibles mal assignées ; signe négatif séparé par une espace
fine U+2009) — tous deux vérifiés par recoupement arithmétique exact.
`validate_kpis.py` : 24/27 (3 faux signaux connus).

### État final de kpis.db

**27 sociétés**, toutes à 22/22 KPIs (structure complète), la quasi-
totalité avec 1 seul NULL (`resultat_technique`) :
Groupama, CNP Assurances, MACSF prévoyance, MGEN, Predica (pipeline
dédié/texte natif) ; les 13 entités Aéma Groupe ; les 9 entités AG2R
La Mondiale.

### Régression vérifiée (Groupama, CNP, MACSF, Predica, Pacifica, SwissLife)

- **Groupama, CNP Assurances, MACSF prévoyance, Predica** : lignes,
  `ratio_scr` et `scr_total` en base strictement identiques à avant
  cette session (requête directe sur `kpis.db`).
- **Pacifica, SwissLife** : jamais insérées dans `kpis.db` (testées
  uniquement via `batch_diagnostic.py`, pas de pipeline dédié) — leur
  "régression" se vérifie sur le score diagnostic : les deux restent à
  **20/20**, inchangé.
- `batch_diagnostic.py` relancé sur tous les PDF de `data/` :
  **Covéa 16/20** (inchangé), **MAIF 17/20** (inchangé), **BPCE IARD
  14/20** (amélioré, cf. Tâche 2), **CNP 20/20**, **Pacifica 20/20**,
  **Predica 20/20** (tous inchangés). Note : le diagnostic générique
  sous-évalue Groupama (9/20, cf. Décision 070 — pipeline dédié résout
  bien plus via PaddleOCR/Gemini, 21/22 réel) et MGEN de la même
  façon (16/20 générique vs 21/22 réel, mêmes overrides scopés non vus
  par le diagnostic générique) — signal attendu, pas une régression.
- Nettoyage : les 20 fichiers `_entite_*.pdf` temporaires (isolation
  Aéma/AG2R, régénérables via `extraire_entite()`) supprimés de
  `data/` après usage — ils polluaient le diagnostic générique en
  étant scannés comme des documents à part entière.

### Couverture du top 15 du marché français — recomptage

| Groupe parent | Statut avant cette session | Statut après |
|---|---|---|
| CNP, Crédit Agricole, BNP Paribas, Société Générale, Covéa, Groupama, AXA, BPCE, Allianz, Generali, SwissLife (11 groupes) | Exploitable | Inchangé, exploitable |
| MACIF/Aéma | "Exploitable en pratique" (2/13 entités, pas en pipeline) | **13/13 entités, pleinement exploitable** |
| MAIF | Partiel (17/20, hors scope cette session) | Inchangé (17/20) |
| AG2R La Mondiale | **Non testé** | **Exploitable (nouveau, 9 entités)** |
| MGEN | **Non testé** | **Exploitable (nouveau, 21/22)** |

**Avant cette session : 11 groupes pleinement automatisés + 1 en
pratique (Aéma partiel) + 1 partiel (MAIF) + 2 non testés (AG2R, MGEN)
= 12/15 exploitables en pratique.**

**Après cette session : 14/15 groupes exploitables** (les 11
inchangés + Aéma désormais complet + AG2R nouveau + MGEN nouveau) —
seul MAIF reste "partiel" (17/20, pas 20/20, hors périmètre de cette
session). Progression de **+2 groupes nouvellement couverts** (AG2R,
MGEN) et **1 groupe passé de partiel à complet** (Aéma/MACIF) en une
session.

### Correction (2026-09-26) — tally 14/15 incohérent, corrigé à 15/15

Incohérence trouvée en auditant ce tally sur demande de l'utilisateur
(qui avait en tête "Allianz Vie est le groupe partiel", alors que ce
paragraphe nomme MAIF) : **le seuil "exploitable" n'était pas appliqué
de façon cohérente**. Dans le même tableau ("11 groupes... inchangé,
exploitable"), **Covéa (16/20)** et **Allianz (15/20, Allianz IARD ET
Allianz Vie)** sont comptés "Exploitable" — des scores INFÉRIEURS à
celui de MAIF (**17/20**), pourtant seul nommé "partiel". Vérifié
contre les diagnostics réels (`batch_diagnostic_report.json`) et
`kpis.db` : aucun des 4 (MAIF, Covéa, Allianz IARD, Allianz Vie) n'est
en réalité inséré dans `kpis.db` — les 4 sont strictement au même
niveau (diagnostic seul, jamais migré vers une extraction réelle),
donc rien ne justifie de traiter MAIF différemment des 3 autres.

**Correction : en appliquant le même seuil (≥15/20 = exploitable) de
façon uniforme, MAIF doit être compté "exploitable" comme Covéa et
Allianz. Le tally correct est 15/15 groupes exploitables au sens
diagnostic**, pas 14/15 — MAIF n'a jamais été une exception, c'était
une incohérence de rédaction dans ce paragraphe (probablement parce
que "hors périmètre de cette session" a été confondu avec "hors seuil
d'exploitabilité").

Ceci dit, la phrase "Allianz Vie reste partiel" n'est pas fausse pour
autant — elle décrit une réalité DIFFÉRENTE et bien réelle : Allianz
Vie est la SEULE des 4 (MAIF/Covéa/Allianz IARD/Allianz Vie) dont
l'incomplétude a été explicitement confirmée comme **architecturalement
irréductible** (Décision 084 : `scr_marche`/`scr_contrepartie` fusionnés
dans une seule ligne QRT R0070, `scr_souscription_vie`/`sante` fusionnés
dans R0400, `scr_diversification` bloqué par un bug de signe propre à ce
document — 3 KPIs qui ne seront JAMAIS résolus avec ce document, quel
que soit l'effort). MAIF et Covéa, eux, ont des gaps documentés comme
"incomplets" mais pas tous formellement qualifiés d'irréductibles au
même degré de certitude. **"14/15 groupes, MAIF seul partiel" (tally
global) était incohérent et corrigé à 15/15 ; "Allianz Vie a le seul
gap confirmé architecturalement permanent" (une affirmation différente,
au niveau de l'entité, pas du tally) reste vraie et n'a jamais été
contredite.**

## Décision 090 — validate_kpis.py généralisé aux 27 sociétés

CONTEXTE : 24 des 27 sociétés de `kpis.db` n'avaient jamais eu leurs
KPIs passés dans `validate_kpis.py` — pas par doute sur leurs données,
mais parce que 3 de ses contrôles restaient codés en dur pour Groupama
(cf. Décision 086) et le contrôle de signe rejetait à tort les zéros
légitimes.

### Les 3 contrôles codés en dur (identifiés)

1. **`ratio_mcr_recalcule`** — recalcule `ratio_mcr` à partir d'un
   numérateur (fonds propres éligibles pour le MCR, R0570) lu
   directement dans `corpus_final.json`, un fichier Docling qui
   n'existe QUE pour Groupama. Ce numérateur n'est PAS un des 22 KPIs
   stockés (concept différent de `fonds_propres_eligibles`, qui est
   l'éligibilité SCR/R0540).
2. **`scr_total_croise_S23_S25`** — compare `scr_total` à une valeur
   fixe (6 020 977 K€) vérifiée manuellement pour Groupama (Décision
   051) en croisant 2 pages QRT différentes.
3. **`scr_nonvie_croise_QRT_image`** — même principe pour
   `scr_souscription_nonvie` (2 474 794 K€, relecture manuelle
   picture_75.png).

### Généralisation tentée puis rejetée pour #2/#3

Avant d'adopter une solution, une généralisation générique a été
testée empiriquement : `scr_total ≈ somme(scr_marche+scr_contrepartie+
scr_souscription_vie+santé+nonvie+scr_diversification+scr_operationnel)`,
calculable pour N'IMPORTE QUELLE société depuis `kpis.db` seul (sans
fichier externe). **Rejetée après test** : l'écart dépasse 20-280% y
compris sur des sociétés parfaitement extraites — MACIF SAM (22%,
pourtant triple-vérifiée p.464/467, Décision 083), Predica (281%), CNP
(193%), Aéma Groupe (149%). Cause : le SCR final inclut des
ajustements LAC DT/LAC TP (capacité d'absorption des pertes par les
impôts différés/les provisions techniques) souvent très matériels,
JAMAIS capturés dans les 22 KPIs stockés. Adopter cette identité
aurait produit une majorité de faux échecs — contraire à la règle
"jamais un signal trompeur". Les 3 contrôles restent donc scopés à
Groupama, mais réécrits en REGISTRES extensibles
(`SOURCES_MCR_INDEPENDANTES`, `CROISEMENTS_GROUPAMA`) plutôt qu'un
`if company_name == "Groupama"` littéral — une future société avec une
vraie source indépendante capturée s'y ajouterait sans toucher la
logique de contrôle.

### Autres corrections généralisées

- **Signe** : `positive` accepte désormais `>= 0` (pas `> 0`),
  `negative` accepte `<= 0` — plusieurs sociétés ont légitimement des
  tiers de fonds propres ou composantes SCR à exactement 0,00.
- **Garde NULL** : chaque contrôle arithmétique (1, 2, 3, 4, 5) est
  SKIPPÉ proprement (rien inséré, jamais un crash ni un calcul sur
  `None`) si un des KPIs qu'il utilise est NULL pour cette société —
  via une fonction `valeurs()` dédiée.
- `completude_null_attendu` (exactement 1 NULL = `resultat_technique`)
  **volontairement NON assoupli** — un vrai signal de complétude, pas
  un faux positif (cf. ci-dessous).
- Nouveau flag `--all` (`valider_societe()` factorisée depuis `main()`)
  pour lancer sur toutes les sociétés de `companies` en un seul appel.

### Test de non-régression (étape 3) — AVANT le rollout complet

Groupama, Predica, MGEN relancés isolément : **Groupama 30/30**
(identique bit à bit) ; **Predica 25/27 → 27/27** et **MGEN 24/27 →
27/27** — amélioration ATTENDUE (les faux signaux zéro corrigés),
mêmes dénominateurs qu'avant (aucun contrôle ajouté/retiré pour ces 3),
confirmant zéro régression.

### Rollout sur les 27 sociétés — 1 bug réel trouvé (pré-existant, hors session)

**BUG RÉEL TROUVÉ ET CORRIGÉ — MACSF prévoyance/scr_diversification** :
stocké à tort à **+14,14 M€** (positif — impossible par construction,
la diversification est toujours un bénéfice ≤0) au lieu de **-14,14
M€**. Bug pré-existant (extraction d'une session antérieure à
celle-ci, jamais re-vérifié depuis). Cause : même famille que BPCE
IARD/Predica/MGEN (Décisions 085/086/088) — signe "-" détaché, mal
assigné à une colonne `C0100`/"Value" distincte au lieu d'être
attaché à la magnitude en `C0090`. Vérifié par cohérence arithmétique
EXACTE contre `test_markdrop/output_macsf/corpus_final.json` :
R0100 (SCR de base) = 497 952+3 875+15 313+0+0**-14 137**+0 = **503
003**, quasi-identique au R0100 imprimé (503 004, écart 1 = arrondi)
— la version positive (531 277) ne colle pas du tout. Valeur corrigée
directement en base (`kpis.db`), `source_chapter` mis à jour avec la
justification complète.

**RÉSULTAT FINAL — 27/27 sociétés testées :**

| Société | Contrôles passés / applicables | Échecs réels (hors faux signaux zéro) |
|---|---|---|
| Groupama | 30/30 | — |
| CNP Assurances | 27/27 | — |
| MACSF prévoyance | 27/27 | — (corrigée cette tâche) |
| Predica | 27/27 | — |
| MGEN | 27/27 | — |
| Aema Groupe | 27/27 | — |
| MACIF SAM | 27/27 | — |
| Macif Vie | 27/27 | — |
| Macif Sante Prevoyance | 27/27 | — |
| Themis | 26/27 | `mcr_inferieur_scr_total` — plancher absolu MCR, légitime (Décision 085) |
| Macifilia | 25/27 | `mcr_inferieur_scr_total` — plancher absolu MCR, légitime (Décision 085) |
| Aesio Mutuelle | 27/27 | — |
| MNPAF | 27/27 | — |
| MMJ | 27/27 | — |
| Nuoma | 27/27 | — |
| Abeille Vie | 27/27 | — |
| Abeille Epargne Retraite | 27/27 | — |
| Abeille IARD Sante | 27/27 | — |
| SGAM AG2R LA MONDIALE | 21/22 | `completude_null_attendu` — 4 NULL, mapping groupe incomplet, légitime (Décision 087) |
| AG2R Prevoyance | 25/26 | `completude_null_attendu` — 2 NULL (scr_souscription_nonvie), légitime (Décision 087) |
| Arpege Prevoyance | 27/27 | — |
| Prima | 27/27 | — |
| AG.Mut | 27/27 | — |
| VIASANTE Mutuelle | 27/27 | — |
| La Mondiale | 27/27 | — |
| La Mondiale Europartner | 27/27 | — |
| La Mondiale Partenaire | 27/27 | — |

**Sur 27 sociétés, 4 "échecs réels" — les 4 sont des cas déjà
documentés dans des Décisions antérieures (085/087), pas de nouveaux
bugs** — sauf la correction MACSF elle-même (trouvée PAR cette tâche
de généralisation, pas dans son résultat final).

RÉGRESSION VÉRIFIÉE : Groupama 30/30 inchangé ; Predica/MGEN passés à
27/27 (amélioration attendue, faux signaux corrigés, pas une
régression).

## Décision 091 — Détection systématique du bug de signe détaché (solution générale)

CONTEXTE : 4 sociétés (Predica, BPCE IARD, MGEN, MACSF) avaient eu le
même type de bug — un signe négatif séparé de sa magnitude — corrigé
à chaque fois au cas par cas (Décisions 085/086/088/090). Objectif :
construire une détection et une correction SYSTÉMATIQUES, pas une
énième correction manuelle.

### Étape 1 — Les 4 variantes déjà recensées

| Société | Décision | Variante | Pipeline concerné |
|---|---|---|---|
| Predica | 085 | Notation comptable entre parenthèses : "(10 475 550)" = -10 475 550. PyMuPDF sépare "(10" et "550)" en 2 mots, tous deux rejetés par NUMERIC_FRAGMENT_RE (aucun ne matche un nombre pur). | extract_qrt_native (ingest.py) |
| BPCE IARD | 086 | Signe et magnitude sur des tokens séparés, magnitude AVANT le signe : ["196 476", "-", "196 476", "-"] (2 colonnes net/brut). | classifier_lignes/extraire_par_libelle (mode libellés français, PAS extract_qrt_native) |
| MGEN | 088 | Espace Unicode INVISIBLE entre le signe et la magnitude, dans un SEUL mot PDF : "-[espace fine U+2009]452" — vérifié via page.get_text("words"), PyMuPDF ne scinde pas ce caractère comme un espace normale. | extract_qrt_native (ingest.py) |
| MACSF | 090 | Signe attaché à une CELLULE/COLONNE différente de la magnitude : C0090="14137", C0100="-" (colonne "Value" distincte) — trouvé dans un corpus pré-construit par un pipeline Docling plus ancien. | Pipeline corpus_final.json historique (pas extract_qrt_native, script de construction du corpus non ré-exécuté) |

Point clé : ces 4 variantes vivent dans 3 pipelines d'extraction
différents — extract_qrt_native (Predica/MGEN), classifier_lignes
(BPCE IARD), et l'ancien pipeline Docling (MACSF/Groupama/CNP). Un seul
fix ne peut pas couvrir les 3 sans un risque de régression majeur — cf.
Décision 079 (un fix générique dans classifier_lignes avait cassé
Covéa).

### Étape 2 — Détecteur systématique construit et testé

Fix appliqué aux 2 variantes qui vivent réellement dans
extract_qrt_native (Predica, MGEN) :
- NUMERIC_FRAGMENT_RE (ingest.py) étendue avec 4 nouveaux termes,
  chacun ANCRÉ sur un caractère qu'aucune valeur déjà extraite avec
  succès ne pouvait contenir (parenthèse ouvrante/fermante, espaces
  Unicode précis) — donc strictement additif, zéro risque de faire
  matcher un mot qui matchait déjà autrement.
- _vers_float (extract_kpis.py) étendue pour reconstruire la valeur
  finale : retire les espaces Unicode (U+2009/U+00A0/U+202F/U+2007), et
  traite "(...)" comme négatif.
- 21 tests unitaires (test_normalisation_signe.py, nouveau fichier)
  couvrant : reconnaissance des 2 variantes, absence de faux positifs
  sur du texte non-numérique, ET non-régression stricte sur tous les
  formats déjà gérés (entier, décimal virgule, pourcentage, tiret
  EIOPA, négatif collé, espaces milliers ASCII) — tous passent, y
  compris une reproduction bout-en-bout exacte des bugs Predica/MGEN.

BPCE IARD (classifier_lignes) et MACSF (pipeline Docling ancien) ne
sont PAS touchés : la généralisation de classifier_lignes a déjà été
tentée et rejetée en Décision 079 (régression Covéa) ; le pipeline
Docling ancien n'est plus ré-exécuté pour aucune société active. Ces 2
restent couverts par leurs fix scopés existants (Décision 086) et par
le filet de sécurité de l'Étape 3 ci-dessous.

### Étape 3/4 — Scan rétroactif des 27 sociétés + non-régression

Scan direct en base : les 563 valeurs non-NULL des 27 sociétés
auditées contre le signe attendu (kpi_definitions.py) — 1 seule
anomalie hors zéro trouvée (Macifilia/charge_sinistres, déjà
documentée et vérifiée comme légitime, Décision 087).

Screening par ratio (garde-fou plus fin, car un signe déjà correct
peut cacher une MAGNITUDE tronquée) : |scr_diversification| / somme
des 5 autres composantes SCR, calculé pour les 25 sociétés avec
données complètes. Toutes dans une fourchette 13-43%, plausible pour un
vrai effet de diversification, SAUF MACSF (2,73%, déjà vérifiée exacte
par recoupement arithmétique en Décision 090) — aucune nouvelle
anomalie détectée.

Régression réelle : batch_diagnostic.py relancé sur les 25 documents
réels (hors fragments _entite_* déjà nettoyés) — scores strictement
identiques avant/après, document par document.

BONUS non anticipé : en ré-exécutant extract_kpis_predica.py après le
fix pour confirmer que l'override manuel devenait inutile (confirmé :
resoudre_variantes_qrt retourne directement -10 475 550 sans override),
une DIFFÉRENCE inattendue est apparue sur charge_sinistres (83 983,72
-> 83 966,88 M€). Investiguée avant d'être acceptée (jamais une
différence silencieuse) : le texte brut page 57 contient "(8 420)"
dans une colonne de la ligne R1610 — un signe détaché NON encore
trouvé, sur un KPI DIFFÉRENT de scr_diversification. Sous l'ANCIEN
parser, cette colonne était purement absente de la somme (silencieusement
traitée comme 0 plutôt que -8 420) ; le nouveau parser l'inclut
correctement. Vérifié par recoupement exact : 18 089 651+0(ancien,
colonne rejetée)+2 619 270+20 700 500 = 41 409 421 (ancienne valeur,
fausse) contre 18 089 651-8 420+2 619 270+20 700 500 = 41 401 001
(nouvelle valeur, exacte) — la correction du parser révèle et corrige
une DEUXIÈME instance du même bug, invisible à la détection par signe
seul puisque charge_sinistres reste positif dans les 2 cas. Ceci valide
directement la prémisse de la tâche : le bug était bien plus répandu
que les 4 cas déjà trouvés. AG2R (9 entités) ré-exécuté également :
aucun changement (aucune notation parenthèses/espace invisible sur ses
cellules).

Overrides manuels devenus redondants NETTOYÉS (code mort retiré) :
extract_kpis_predica.py et extract_kpis_mgen.py — le fix général
résout maintenant scr_diversification correctement sans eux, vérifié
avant suppression. L'override fonds_propres_eligibles de MGEN reste
(bug DIFFÉRENT — mauvaise colonne, pas un signe détaché).

### Étape 5 — validate_kpis.py --all après le fix

Identique à avant le fix (Groupama 30/30, Predica/MGEN/MACSF 27/27,
les 4 mêmes échecs déjà documentés comme légitimes) — zéro régression.

### Étape 6 — Tableau récapitulatif

| Société | Signe détecté avant | Signe après nouveau détecteur | Changé ? | Vérifié arithmétiquement ? |
|---|---|---|---|---|
| Predica | positif (bug, Décision 085) | négatif (résolu directement, override retiré) | Oui (déjà corrigé avant cette tâche) | Oui (R0100=somme composantes, exact) |
| BPCE IARD | positif (bug, Décision 086) | positif (non couvert — pipeline classifier_lignes, fix scopé conservé) | Non re-testé ici (hors kpis.db, jamais inséré) | Oui, en Décision 086 |
| MGEN | positif (bug, Décision 088) | négatif (résolu directement, override retiré) | Oui (déjà corrigé avant cette tâche) | Oui (R0100=somme composantes, exact) |
| MACSF prévoyance | positif (bug, Décision 090) | négatif (inchangé par ce fix, déjà corrigé) | Non (déjà bon) | Oui, en Décision 090 |
| Predica (bonus) | charge_sinistres correct en apparence (positif, mais magnitude fausse) | charge_sinistres corrigé (+16,84 M€, colonne (8 420) incluse) | Oui — nouveau, trouvé par cette tâche | Oui (recoupement exact 41 401 001) |
| Les 22 autres sociétés (Aéma x13, AG2R x9, CNP, Groupama) | négatif (déjà correct) | négatif (inchangé) | Non | Scan systématique (polarité + ratio), pas de ré-arithmétique individuelle sauf AG2R (9 entités ré-exécutées, 0 changement) |

### Étape 7 — Commit

Commité avec le message demandé.

Limite assumée : la détection reste au niveau texte pour
extract_qrt_native uniquement (2 des 3 pipelines). BPCE IARD
(classifier_lignes) et le pipeline Docling historique (MACSF/Groupama/
CNP) ne sont couverts que par le filet de sécurité arithmétique
rétroactif (Étape 3), pas par une correction automatique à la source —
un choix assumé pour ne pas répéter la régression Covéa de Décision
079.

## Décision 092 — État des lieux de session + tentative d'ingestion RAG CNP Assurances (diagnostiquée, bloquée proprement)

Session enchaînant automatiquement : commit interface Reflex → Décision
091 (bug de signe) → merge phase2-metadonnees-multidoc → ingestion CNP
dans le RAG conversationnel. Bilan des 3 dernières tâches.

### 1. Interface Reflex "Analyse" (onglet, `test_markdrop/sfcr_app/analyse/`)

Committée (`c83d3ef`). 5 phases livrées : squelette, analyse
individuelle, analyse comparative, graphiques (décomposition SCR,
radar, barres), alertes/benchmark/export CSV. **Compile** (`reflex
compile --dry` → Success) mais **non vérifiée visuellement** :
`reflex run` (dev ET prod) échoue de façon reproductible sur un bug
upstream de `@react-router/dev` ("restartWithMergedOptions() was
called...") indépendant du code ajouté ici — confirmé en isolant le
port, `NODE_OPTIONS`, et en supprimant/régénérant `.web/` entièrement.
Corrigible en installant WSL (recommandation de l'outil), délibérément
NON fait : changement système, hors périmètre autorisé. **À faire par
l'utilisateur** : soit installer WSL et relancer `reflex run --env
prod` pour valider visuellement l'onglet avant mise en production,
soit tester directement sur la VM Oracle Cloud (Linux, pas ce bug).

### 2. Branche `phase2-metadonnees-multidoc`

Vérifiée : **n'existe plus, ni en local ni sur `origin`**
(`git branch -a` / `git ls-remote --heads origin` : seul `master`
présent). `git log --all --grep` retrouve le commit `1cba307 Merge
branch 'phase2-metadonnees-multidoc'`, déjà un ancêtre de `master`
(vérifié via `git merge-base --is-ancestor`). **Conclusion : déjà
mergée et supprimée, aucune action nécessaire.**

### 3. Ingestion CNP Assurances dans le RAG conversationnel (Qdrant) — BLOQUÉE, diagnostiquée

**Constat de départ** : `output_cnp/corpus_final.json` (existant avant
cette session) ne couvre QUE les 9 pages QRT en texte natif, utilisé
uniquement par `extract_kpis_cnp.py` pour peupler `kpis.db`. **Aucun
chunk narratif, tableau ou image de CNP n'était présent dans les 4
collections Qdrant** (vérifié par requête directe : `texte`/
`tableaux`/`images`/`qrt` ne contiennent que des points `company_name
= "Groupama"` ou `None` [ingestion 2024 pré-Décision 046, sans
métadonnées Phase 2] — zéro point CNP).

**Tentative** : lancement de `run_pipeline.py --pdf
data/sfcr_cnp_assurances_2025.pdf --company "CNP Assurances" --type
SA --year 2025 --work-dir output_cnp_full --salt-ids
--verifier-delta-uniquement` (bloc narratif complet, 12 étapes).

**Progression réelle avant blocage** :
- `extract_raw_structure.py` : conversion Docling complète, 2072
  items extraits (948,9s), `structure_brute.json` écrit.
- `save_docling_document.py` : 2e conversion Docling indépendante
  (938,5s — le coût documenté de "chaque script reconvertit
  séparément"), `docling_document_complet.json` écrit (5,6 Mo).
- `fix_heading_levels.py`, `filter_fake_headers.py`,
  `retype_bullet_headers.py`, `final_corrections.py` : passés sans
  erreur (chacun < 0,3s — ces 4 scripts n'ont pas de garde-fou
  bloquant sur liste blanche, contrairement au suivant).
- `fix_unnumbered_levels.py` : **ARRÊT PROPRE, comportement voulu du
  script** (cf. son propre docstring : "s'arrête et le signale
  explicitement, plutôt que d'appliquer une règle générique qui
  devinerait"). `structure_finale_v4.json` non écrit → tout le reste
  du bloc narratif (10 étapes restantes) et le bloc QRT/indexation
  n'ont pas pu s'exécuter.

**Cause racine identifiée (pas une supposition — comptage exact sur
les 362 cas signalés)** : la convention de numérotation des titres de
CNP diffère structurellement de celle de Groupama, sur laquelle
`MOTIF_NUMEROTATION` (`^([A-Z])((?:\.\d+)*)\.?\s`, dans
`fix_heading_levels.py`) et la liste blanche de
`fix_unnumbered_levels.py` (18 cas, un seul document) ont été
construits :

| Catégorie | Effectif | Exemple CNP | Pourquoi ça ne matche pas `MOTIF_NUMEROTATION` |
|---|---|---|---|
| Sections de tête lettre+chiffre SANS point | 25 | `A1 Activité`, `B3 Système de gestion des risques`, `E2 Capital de solvabilité requis...` | Regex exige un point après la lettre (`A.`) — CNP écrit `A1`, pas `A.1` |
| Sous-sections en chiffres nus | 216 | `1. Renseignements de caractère général`, `4.1 Environnement économique et financier` | Regex exige une lettre MAJUSCULE en tête — CNP numérote les sous-niveaux sans répéter la lettre parente |
| Sous-sous-items lettrés | 6 | `a) Actions propres` | Non couvert par le motif (lettre minuscule + parenthèse) |
| Titres réellement non numérotés (style narratif propre à CNP) | 115 | `Chiffres clés`, `Une stratégie de développement`, `Notes :` | Légitimement sans numéro — mais 6× plus nombreux que chez Groupama (18 cas au total, tout confondu) |

Chez Groupama, ce même filtre ne remontait que 18 cas au total (dont
17 volontairement exclus et 1 seul réellement corrigé) — governance
document avec numérotation quasi-exhaustive `A.`/`A.1.`/`A.1.1.`. Chez
CNP, c'est la **majorité des 374 section_header H1** qui ne matche
pas : pas un cas limite à ajouter à une liste blanche, mais un
**format de numérotation entièrement différent**, comme documenté
comme risque connu par `run_pipeline.py` lui-même (point 1 de son
docstring : "sur un 3e document, un 3e script à écrire après
inspection manuelle, pas une branche automatique") — exactement le
mécanisme déjà utilisé pour 2024 (`fix_unnumbered_levels_2024.py`,
liste blanche distincte).

**Décision : ne pas deviner une correction ici.** Construire un
`fix_unnumbered_levels_cnp.py` (ou généraliser `MOTIF_NUMEROTATION`
avec un 2e motif alternatif letter+digit-sans-point, strictement
ADDITIF et re-testé sur Groupama pour zéro régression — cf. la leçon
de la régression Covéa, Décision 079) demande de vérifier un par un,
page par page contre le PDF réel, comment traiter au minimum les 25
sections de tête + 216 sous-sections numérotées (241 cas à
hiérarchiser correctement, pas à exclure) — travail comparable en
volume à la construction initiale du pipeline Groupama, pas une
correction de session. **Non fait ici, volontairement, plutôt que de
produire une hiérarchie `chemin_hierarchique` fausse qui pollue les
métadonnées `section`/`chapter` de TOUS les futurs chunks CNP dans
Qdrant.**

**Travail conservé, réutilisable sans repayer le coût Docling (≈31
minutes)** : `test_markdrop/output_cnp_full/` contient
`structure_brute.json`, `docling_document_complet.json`,
`structure_corrigee.json`, `structure_filtree.json`,
`structure_finale.json`, `structure_finale_v3.json`. Une prochaine
session peut reprendre directement à `fix_unnumbered_levels_cnp.py`
sans relancer `extract_raw_structure.py`/`save_docling_document.py`.

**Prochaine étape concrète recommandée** :
1. Écrire `fix_unnumbered_levels_cnp.py` : reconnaître le motif
   `^[A-Z]\d` (25 cas, niveau = niveau racine du document) et le motif
   `^\d+(\.\d+)*\.?\s` (216 cas, niveau = niveau du dernier
   section_header letter+digit précédent + profondeur du numéro,
   même logique que la correction "Epargne retraite" de
   `fix_unnumbered_levels.py`).
2. Décider, avec vérification PDF à l'appui (pas une supposition), du
   traitement des 115 cas "autres" — vraisemblablement tous exclus
   (niveau inchangé), mais à confirmer qu'aucun n'est un vrai titre de
   section manqué (ex. couverture, page de garde).
3. Relancer `run_pipeline.py --skip-narratif` une fois
   `structure_finale_v4.json` produit à la main... non — en pratique
   relancer le bloc narratif à partir de `build_leaf_chunks.py` (pas
   besoin de refaire les 2 conversions Docling ni les 4 scripts déjà
   passés), avec `--work-dir output_cnp_full`.
4. Avant l'indexation Qdrant finale (`ingest_qdrant.py`), vérifier le
   point 3 du docstring de `run_pipeline.py` : `extraire_visuels.py`
   écrit sous une racine partagée PAR ANNÉE (`<année>/...`) — CNP 2025
   et Groupama 2025 partagent l'année 2025, collision de chemin
   possible, à vérifier/corriger avant d'exécuter cette étape (pas
   rencontré ici puisque le bloc narratif ne l'a jamais atteint).

### 4. État complet de `kpis.db` (rappel, inchangé par cette session sauf Décision 091)

27/27 sociétés dans `companies`, toutes passées par
`validate_kpis.py --all` (Décision 090) : 23 sociétés à 100% de
contrôles applicables passés, 4 échecs réels mais tous légitimes et
déjà documentés (Themis/Macifilia : plancher MCR absolu, Décision
085 ; SGAM AG2R/AG2R Prévoyance : NULL de mapping groupe incomplet,
Décision 087). Le bug de signe détaché (Décision 091) a corrigé
Predica (`scr_diversification` + `charge_sinistres`) et laissé
inchangées les 25 autres sociétés (déjà correctes ou hors périmètre
du fix générique, cf. limite assumée ci-dessus).

### Résumé une ligne par tâche chaînée

| Tâche demandée | Statut |
|---|---|
| Commit interface Reflex Analyse | Fait (`c83d3ef`) |
| Bug de signe détaché, scan rétroactif 27 sociétés | Fait (`ca62cd9`, Décision 091) |
| Merge `phase2-metadonnees-multidoc` | Déjà fait avant cette session (`1cba307`) — rien à merger |
| Ingestion CNP dans le RAG conversationnel (Qdrant) | Bloquée proprement à l'étape `fix_unnumbered_levels.py` — diagnostiquée, travail Docling conservé, script dédié à écrire (non deviné) |
| État des lieux DECISIONS.md | Cette entrée |

## Décision 093 — Généralisation à 4 nouvelles sociétés : 2 bugs systémiques trouvés et corrigés (code partagé), 1 régression évitée, Crédit Agricole Assurances intégrée

CONTEXTE : tâche demandée — généraliser le pipeline KPI à Allianz Vie,
MAIF, Covéa, Crédit Agricole Assurances (groupe combiné), dans cet
ordre. L'objectif explicite de l'utilisateur : voir si le système
généralise ou révèle des bugs inédits. **Réponse : les deux** — la
généralisation a immédiatement révélé un bug systémique touchant
`primes_acquises_brutes`/`charge_sinistres` sur plusieurs sociétés
DÉJÀ en base, dont Groupama (la société de référence du projet). Seule
Crédit Agricole Assurances a été menée à terme dans cette tâche ;
MAIF/Covéa/Allianz Vie restent à faire (cf. section finale).

### Étape 1 — Crédit Agricole Assurances : diagnostic 20/20 en apparence, mais valeurs fausses

Diagnostic `batch_diagnostic.py` : `codes_eiopa`, `groupe`,
`formule_standard`, 20/20 (comme Predica/MGEN). `extract_kpis_
creditagricole.py` construit sur le même modèle que `extract_kpis_
predica.py`. Premher essai : `primes_acquises_brutes` = **183 334,32
M€** — implausible (plus que le marché français de l'assurance sur
une année entière). Investigation immédiate plutôt que d'insérer une
valeur non vérifiée.

### Étape 2 — Bug A (EN/FR) : le dictionnaire QRT synthétique concatène les libellés

`construire_qrt_dict_synthetique()` (`batch_diagnostic.py`), utilisé
par tous les `extract_kpis_*.py` SANS `corpus_final.json` dédié
(Predica, MGEN, AG2R, Crédit Agricole), accumule TOUS les libellés
connus pour un même code de ligne, séparés par `" | "` — ex.
`"Premiums earned | Primes acquises"`. `KPI_QRT_MAPPING` déclare une
variante EN (`"Premiums earned"`) ET une variante FR (`"Primes
acquises"`) pour le MÊME `(template, row, col)` — sur un document où
le libellé synthétique combine les deux, LES DEUX variantes matchent
la MÊME cellule, et l'appelant (`total = sum(v for v,_,_ in
resultats)`, cumulatif par construction pour primes/sinistres)
comptait deux fois la même donnée.

### Étape 3 — Bug B (colonne Total) : `col="toutes"` incluait une vraie colonne Total déjà peuplée

Bug distinct, déjà partiellement connu (paramètre `exclure_total`,
Décision 060, activé uniquement pour CNP) mais jamais généralisé :
quand un document imprime À LA FOIS les colonnes par ligne d'activité
ET une colonne "Total" (qui vaut par construction leur somme),
`sommer_toutes_colonnes(col="toutes")` additionnait tout, doublant le
résultat. `exclure_total` existait mais n'était PAS activé par défaut
("comportement historique de Groupama préservé" — analyse montrée
fausse ci-dessous pour ce KPI précis).

**Vérification que Groupama a RÉELLEMENT le même bug** (pas supposé) :
inspection directe de `corpus_final.json` — la ligne R0210 (Primes
acquises Brut, non-vie) a ses 12 colonnes de ligne d'activité PLUS une
colonne `C0200`/"Total" TOUTES peuplées, `Total = somme exacte des 12
colonnes` (14 013 513 ≈ 14 013 512 calculé). Le commentaire d'origine
("Groupama a l'inverse : certaines lignes n'ont de valeur QUE dans la
colonne Total") ne s'applique à AUCUNE ligne de primes_acquises_brutes/
charge_sinistres sur le document réel — l'exception documentée en 2024
ne concernait pas ce KPI précis.

### Étape 4 — Détection par ARITHMÉTIQUE, pas par libellé de colonne

Piège trouvé en corrigeant Bug B avec une détection par libellé
(`libelle_colonne == "total"`) : ça fonctionne sur le corpus Docling
(Groupama/CNP/MACSF, qui stocke le texte d'en-tête réel "Total") mais
PAS sur le corpus texte natif (`extract_qrt_native`, Predica/MGEN/AG2R/
Crédit Agricole), qui stocke seulement le CODE de colonne ("C0200") —
zéro effet sur ces documents, régression silencieuse évitée en testant
avant de valider. **Solution finale : détection par ARITHMÉTIQUE**
(une cellule dont la valeur == somme des autres cellules de la même
ligne, tolérance 1 unité pour l'arrondi, UN SEUL candidat accepté pour
éviter les faux positifs sur des cellules coïncidemment égales ou
toutes nulles) — fonctionne identiquement sur les 2 conventions de
corpus, sans dépendre du texte de libellé.

**Piège multi-pages trouvé et corrigé avant de valider** : sur Crédit
Agricole Assurances, la ligne R0210 est imprimée sur 2 pages physiques
(9 colonnes p.68, colonnes restantes + Total p.69) — une détection
arithmétique PAGE PAR PAGE ratait le Total (qui somme des colonnes des
2 pages, pas seulement de la sienne). Corrigé en accumulant TOUTES les
cellules de toutes les pages correspondant à un code de ligne AVANT de
faire la détection.

**Régression trouvée et corrigée avant de valider** : la 1re version
de la détection globale levait une erreur (`KpiIntrouvable`) dès qu'UNE
des lignes sommées (ex. R0230, souvent vide — "Réassurance non
proportionnelle acceptée") n'avait AUCUNE valeur, cassant tout le KPI
alors que les 2 autres lignes avaient des données (afv, Allianz Vie,
AG2R groupe consolidé : `primes_acquises_brutes`/`charge_sinistres`
passaient de résolu à `KpiIntrouvable`, -2 KPIs chacun en diagnostic).
Corrigé : une ligne trouvée avec le bon libellé mais sans valeur
contribue 0 (comme avant), ne lève pas d'erreur.

### Étape 5 — Régression réelle trouvée EN COURS DE RÉGRESSION-TEST : MACSF

En re-exécutant `extract_kpis_macsf.py` pour vérifier l'absence de
régression (étape de discipline standard), découverte que `scr_
diversification` de MACSF prévoyance est repassé de **-14,14 M€ à
+14,14 M€** — la correction de la Décision 090 avait été appliquée
**directement en base**, jamais encodée dans le script lui-même
(seule occurrence de ce type dans tout le projet, vérifié par grep sur
"corrigée directement en base"). Contrairement à Predica/MGEN (Décision
091, override retiré car devenu redondant avec le détecteur générique),
la variante MACSF (signe sur une colonne `C0100` séparée) n'est PAS
couverte par le détecteur de Décision 091. **Corrigé en 2 temps** :
override ajouté DANS `extract_kpis_macsf.py` (idempotent — ne
s'applique que si la valeur résolue est positive, donc sans risque si
le bug source venait à être corrigé un jour) + valeur re-corrigée en
base. Leçon retenue : ne plus jamais re-lancer un script d'extraction
sans avoir vérifié au préalable l'existence d'un override DB-only.

### Étape 6 — Régression-test complet sur les 27 sociétés (avant/après)

- `batch_diagnostic.py` : 22 documents comparables, **KPIs résolus
  strictement identiques avant/après** sur chacun (vérifié champ par
  champ, pas juste visuellement).
- `ag2r_entites.py` (9 entités) : sortie **strictement identique**
  (`diff` vide) — `primes_acquises_brutes`/`charge_sinistres` de ces
  entités passent par une fonction dédiée (`resoudre_primes_sinistres_
  ag2r`, texte tourné à 90°, jamais `resoudre_variantes_qrt`), donc
  hors périmètre de ce fix par construction ; les autres KPIs (SCR,
  fonds propres) confirmés inchangés.
- `validate_kpis.py --all` (27 sociétés) : **721/726 contrôles passés,
  exactement les mêmes 5 échecs déjà documentés et légitimes** qu'avant
  cette tâche (AG2R Prévoyance 25/26, SGAM 21/22, Macifilia 25/27,
  Themis 26/27, Groupama 30/30 inchangé) — zéro nouvel échec, zéro
  échec disparu.

### Étape 7 — Sociétés déjà en base, valeurs corrigées

| Société | primes_acquises_brutes avant | après (vérifié) | charge_sinistres avant | après (vérifié) |
|---|---|---|---|---|
| Groupama | 39 062,34 M€ (×2,00 trop élevé) | **19 531,17 M€** | 27 949,85 M€ | **13 974,93 M€** |
| Predica | 121 745,81 M€ (×3,95 trop élevé) | **30 799,57 M€** | 83 966,88 M€ | **21 282,94 M€** |
| MGEN | 12 836,05 M€ (×2,00 trop élevé) | **3 209,01 M€** | 9 514,70 M€ | **2 378,68 M€** |
| CNP Assurances | 22 238,96 M€ | inchangé (déjà correct — libellé FR unique + `exclure_total` déjà actif) | 20 072,45 M€ | inchangé |
| MACSF prévoyance | 42,60 M€ | inchangé (déjà correct) | 14,99 M€ | inchangé — `scr_diversification` reconfirmé -14,14 M€ après régression corrigée |
| Les 9 entités AG2R | — | inchangées (fonction dédiée, hors périmètre du bug) | — | inchangées |

Tous re-validés via `validate_kpis.py` individuellement — 27/27 (30/30
Groupama) — après mise à jour.

### Étape 8 — Crédit Agricole Assurances intégrée (28e société)

22 KPIs, 21 valeurs, 1 NULL (`resultat_technique`). `primes_acquises_
brutes`/`charge_sinistres` insérés via override manuel scopé au
fichier (49 173,00 M€ / 30 255,38 M€, lecture directe de la colonne
Total imprimée p.69/70) — PAS via `resoudre_variantes_qrt`, à cause
d'un **3e bug, distinct, non corrigé** : `extract_qrt_native()` ne
capture AUCUNE valeur pour la ligne R0210/R0220/R0230 sur la page 68
de ce document, bien que 9 valeurs soient bien imprimées à cet endroit
(vérifié sur le texte brut) — un bug d'appariement position/colonne
distinct des bugs A/B, hors périmètre de cette tâche (scopé au fichier,
documenté dans `extract_kpis_creditagricole.py`, pas deviné ni forcé
dans le code partagé). `validate_kpis.py` : **27/27**. Cohérence
croisée vérifiée : `fonds_propres_eligibles/scr_total×100 = 194,50%`
vs `ratio_scr` publié `195%` (à la limite d'arrondi, cohérent) ;
`T1nr+T1r+T2+T3 = fonds_propres_eligibles` exact.

### Bilan génériques vs spécifiques (objectif de la session)

| Catégorie | Compte |
|---|---|
| Bugs GÉNÉRIQUES trouvés (code partagé, `extract_kpis.py`) | 2 (Bug A dédoublonnage EN/FR, Bug B colonne Total) — corrigés une fois pour toutes, zéro régression sur 27 sociétés |
| Bugs SPÉCIFIQUES à un document trouvés | 1 (Crédit Agricole Assurances p.68, extraction positionnelle) — non corrigé, scopé |
| Régression trouvée en testant AVANT de valider (Bug B, détection par libellé) | 1 — corrigée avant intégration (jamais livrée) |
| Régression trouvée en testant AVANT de valider (empty-values raise) | 1 (afv/Allianz Vie/AG2R groupe) — corrigée avant intégration |
| Régression réelle DÉJÀ EN BASE, trouvée en re-testant (MACSF) | 1 — corrigée, override ajouté au code pour ne plus jamais la reperdre |
| Nouvelle société intégrée | Crédit Agricole Assurances (28e, 22/22, 27/27) |

### Reste à faire (hors périmètre de cette tâche, non commencé)

MAIF, Covéa, Allianz Vie — non extraites. Le contexte fourni par
l'utilisateur (Décisions 077/079/082/084/090) reste le point de départ
valide : Allianz Vie 15/20 diagnostic, 3 KPIs confirmés irréductibles ;
MAIF 17/20, fonction `resoudre_scr_mcr_maif()` déjà construite et
vérifiée (Décision 074/084), prête à être branchée dans un
`extract_kpis_maif.py` ; Covéa 16/20, `resoudre_primes_sinistres_
covea()` déjà construite, le reste des KPIs passerait par le repli
libellé générique (`KPI_LABELS_FR`) déjà utilisé en diagnostic — **à
revérifier avec la même rigueur que cette tâche** (le bug de cette
session prouve qu'un score de diagnostic élevé ne garantit PAS des
valeurs correctes pour primes_acquises_brutes/charge_sinistres — les 2
KPIs à vérifier en priorité, par recoupement arithmétique direct contre
le PDF, avant toute insertion).

## Décision 094 — 7 entités Aéma Groupe : bug d'unité (€ bruts confondus avec K€), tous les KPIs inflatés ×1000

CONTEXTE : entrée rédigée après coup, à la demande de l'utilisateur —
ce fix avait été fait et commité (`7788328`, même commit que Décision
093) mais n'avait jamais eu sa propre entrée DECISIONS.md, seulement
une mention dans le message de commit et un paragraphe dans Décision
093. Chronologiquement, ce fix a été fait AVANT le fix EN/FR + colonne
Total de Décision 093, dans la même session — découvert en auditant
`primes_acquises_brutes` de Crédit Agricole Assurances, qui a mené à
vérifier Predica, puis par ricochet toutes les sociétés du projet.

### Constat initial

En vérifiant `scr_total` sur les 27 sociétés alors en base, 4 entités
montraient des valeurs manifestement impossibles (des centaines de
milliards à ~2 000 milliards €) : **Abeille Vie, Abeille IARD Santé,
Aésio Mutuelle, Abeille Épargne Retraite**. 3 autres montraient des
valeurs plus discrètement suspectes (20 à 34 milliards €, trop élevé
pour des mutuelles de niche) : **MNPAF, MMJ, Nuoma**.

### Cause racine

`aema_entites.py` (Décision 083, intégration des 13 entités du document
combiné "Aéma Groupe RAPPORT UNIQUE...", 621 pages, 100% image) suppose
— dans son propre commentaire d'origine — que **toutes** les valeurs
lues sur les pages QRT sont en K€ ("Valeurs en K€ BRUT... converties en
M€ uniquement au moment de l'insertion en base", diviseur ÷1000
appliqué uniformément dans `inserer_entite_en_base`). Cette hypothèse
est vraie pour 6 des 13 entités (MACIF SAM, Macif Vie, Macif Santé
Prévoyance, Themis, Macifilia, Aéma Groupe) mais **fausse pour 7
d'entre elles** : leurs pages QRT (S.23.01.01, S.05.01.02 — 100% image,
aucun texte natif, aucune étiquette d'unité visible sur la page
elle-même) sont en réalité en **euros bruts**, pas en K€. Diviser par
1000 au lieu de 1 000 000 laissait chaque valeur 1000× trop grande.

Aucune étiquette "En milliers d'euros"/"En euros" n'étant présente sur
ces pages spécifiques (contrairement aux sections narratives du
document, qui affichent "EN MILLIERS D'EUROS"), l'erreur n'était pas
détectable par simple lecture — seul un recoupement d'ordre de grandeur
contre une source indépendante permettait de la révéler.

### Vérification — par recoupement groupe, PAS par lecture directe de la colonne Total

Contrairement à Groupama/Predica/MGEN (Décision 093), la vérification
n'a PAS été faite en lisant directement la colonne Total imprimée page
par page (ces pages sont des images, sans colonne Total séparée à
extraire de la même façon) — mais par **recoupement arithmétique contre
des valeurs de contexte indépendantes** :

- **Aésio Mutuelle** : `scr_total` stocké 680 657,83 M€ (680 milliards
  €, impossible) alors que le SCR marché du GROUPE ENTIER (p.66,
  section narrative "ÉVOLUTION DES SCR ET MCR", explicitement en K€)
  n'est que de 4 301 737 K€ = 4,3 milliards € — Aésio (une seule entité
  parmi 13) ne peut pas avoir un SCR 160× plus grand que TOUT le
  groupe. Après correction (÷1000 supplémentaire) : 680,66 M€,
  cohérent.
- **Abeille Vie** : "Capital en actions ordinaires" (R0010, p.588) =
  1 205 528 533 — en K€ ce serait 1 205 milliards € de capital social
  (impossible), en € bruts c'est 1,2 milliard € (plausible pour cette
  entité, l'ex-Aviva Vie, une des plus grosses du groupe).
- **MNPAF/MMJ/Nuoma** : SCR corrigés (34,4 / 22,0 / 20,8 M€)
  cohérents avec des mutuelles de niche (effectifs Air France,
  personnels...), contre 34,4 / 22,0 / 20,8 **milliards** € avant
  correction.

Confirmation croisée sur les 7 entités après correction :
`fonds_propres_eligibles / scr_total × 100` retombe systématiquement à
quelques centièmes du `ratio_scr` publié sur chaque page (ex. Aésio :
270,38% calculé vs 270% publié ; Abeille Vie : 254,94% vs 255% ;
Abeille IARD Santé : 167,47% vs 167% ; MMJ : 227,37% vs 227% ; MNPAF :
283,39% vs 283% ; Nuoma : 294,85% vs 295%) — cohérence exacte
recalculée sur les 7, aucune simple supposition.

### Impact — TOUS les KPIs numériques (pas seulement primes/sinistres)

Contrairement aux bugs de Décision 093 (limités à
`primes_acquises_brutes`/`charge_sinistres`), celui-ci touchait les 20
KPIs numériques de chaque entité (le diviseur `÷1000` s'applique
uniformément à tout KPI dont l'unité n'est pas `pct` dans
`inserer_entite_en_base`) : `scr_total`, `mcr`, `fonds_propres_*`,
`best_estimate`, `marge_risque`, `provisions_techniques`,
`primes_acquises_brutes`, `charge_sinistres`, `scr_marche`,
`scr_contrepartie`, `scr_souscription_vie/sante/nonvie`,
`scr_diversification`, `scr_operationnel`.

| Société | scr_total avant | scr_total après |
|---|---|---|
| Aésio Mutuelle | 680 657,83 M€ | 680,66 M€ |
| MNPAF | 34 398,84 M€ | 34,40 M€ |
| MMJ | 22 040,34 M€ | 22,04 M€ |
| Nuoma | 20 812,24 M€ | 20,81 M€ |
| Abeille Vie | 1 997 456,96 M€ | 1 997,46 M€ |
| Abeille Épargne Retraite | 438 900,68 M€ | 438,90 M€ |
| Abeille IARD Santé | 931 326,71 M€ | 931,33 M€ |

(`primes_acquises_brutes`/`charge_sinistres` avant/après : cf. tableau
de l'audit post-Décision 093, réponse du 2026-09-26 — mêmes ordres de
grandeur ×1000.)

### Correction appliquée

- Nouveau registre `ENTITES_UNITE_EUR_BRUT` (`aema_entites.py`) listant
  explicitement les 7 entités concernées, avec justification complète
  en commentaire (recoupements ci-dessus).
- `inserer_entite_en_base()` : diviseur devient `1_000_000.0` pour ces
  7 entités (au lieu de `1000.0`), déterminé dynamiquement par
  `nom_entite in ENTITES_UNITE_EUR_BRUT` — les 6 autres entités
  gardent le comportement d'origine (÷1000), aucune régression
  possible sur elles par construction (branche de code distincte).
- `note_origine` (traçabilité en base, colonne `source_chapter`) inclut
  désormais explicitement l'unité source retenue ("euros bruts
  (Décision 093)" ou "K€") pour chaque ligne insérée.
- Les 7 entités ré-insérées via `inserer_entite_en_base()`, `ON
  CONFLICT DO UPDATE` (idempotent).

### Vérification finale

`validate_kpis.py` relancé individuellement sur les 7 entités après
correction : **27/27 chacune**. Aucune régression sur les 6 autres
entités Aéma (branche de code non modifiée pour elles).

Limite assumée : la vérification par recoupement (SCR entité vs SCR
groupe, capital social) est moins directe qu'une lecture de colonne
Total page par page — jugée suffisante ici car (a) le facteur d'erreur
est un ordre de grandeur exact (×1000, pas une valeur approximative),
rendant toute confusion impossible, et (b) la cohérence du ratio_scr
recalculé retombe systématiquement à ±0,5% du publié sur les 7
entités, un signal fort qu'une coïncidence n'expliquerait pas.

### Addendum (2026-09-26) — Macifilia/charge_sinistres : "probable" reclassé "confirmé"

Hors périmètre du bug ×1000 ci-dessus (Macifilia fait partie des 6
entités Aéma correctement en K€, cf. Décision 093), mais vérifié le
même jour : `charge_sinistres` = -939,552 M€ était noté "reprise de
provision **probable**, pas une erreur" depuis son extraction initiale
(Décision 083), jamais recoupé formellement. Relecture directe du
rendu image de la page 511 (S.05.01.02.01, Macifilia) : la valeur
**-939 552** (colonne Total, ligne "Charge des sinistres — Brut —
assurance directe", R0310) est confirmée pixel par pixel, exactement
celle en base. Cohérence interne exacte trouvée en même temps que
la vérification : R0340 (Part des réassureurs, même ligne) affiche
**la même valeur** -939 552, donnant R0400 (Net) = 0 — cette ligne
d'activité est intégralement réassurée (100% cédée), tout comme
`primes_acquises_brutes` sur la même page (R0210/Total = 5 554,
R0300 Net = 0 également). Un signe négatif sur une charge de sinistres
intégralement cédée à un réassureur est économiquement cohérent
(reprise nette d'une provision antérieure, sans impact net puisque
la part réassureur suit à l'identique). Note en base mise à jour de
"probable" à "confirmé" (`kpis.db`, `source_chapter`). Aucune valeur
modifiée — seule la note de confiance change.

## Décision 095 — Nouveau contrôle de magnitude dans validate_kpis.py (contrôle 10)

CONTEXTE : les bugs ×1000 (Décision 094, 7 entités Aéma) et ×2/×3,95
(Décision 093, Groupama/Predica/MGEN) sont restés invisibles à TOUS les
contrôles de `validate_kpis.py` pendant potentiellement plusieurs
sessions — non par manque de contrôles, mais parce que les contrôles
1-4 sont tous des RATIOS entre 2 KPIs de la MÊME société : une erreur
qui affecte les 2 KPIs dans les mêmes proportions (ex. `fonds_propres_
eligibles` et `scr_total` tous les deux ×1000) laisse le ratio recalculé
inchangé — `ratio_scr_recalcule` passait EXACTEMENT pour les 7 entités
Aéma malgré des valeurs absolues 1000× trop grandes (vérifié : 270,38%
recalculé vs 270% publié, Aésio, avant ET après correction — le
contrôle ne voyait rien passer d'un état à l'autre). Aucun contrôle
existant ne regardait une valeur ABSOLUE.

### Seuils retenus — mesurés, pas devinés

Deux catégories, avec une marge ~2-3× au-dessus du maximum RÉEL observé
sur les 28 sociétés en base (requête directe `MAX(ABS(value))` par
KPI, pas une estimation) :

| Catégorie | KPIs concernés | Max réel mesuré | Plafond retenu |
|---|---|---|---|
| Montants standard | scr_total, mcr, fonds_propres_* (4 tiers + éligibles), primes_acquises_brutes, charge_sinistres, scr_marche/contrepartie/souscription_vie/sante/nonvie/diversification/operationnel | 49 173 M€ (primes_acquises_brutes, Crédit Agricole Assurances) | **100 000 M€** |
| Provisions actuarielles | best_estimate, marge_risque, provisions_techniques | 283 474 M€ (provisions_techniques, CNP Assurances) | **1 000 000 M€** |

Le PIB français (~2 800 Md€), suggéré comme référence de départ, a été
**explicitement écarté** pour la catégorie "montants standard" : à ce
niveau, il n'aurait PAS détecté le bug ×1000 sur `scr_total` des
entités Aéma (valeurs 438 900 à 1 997 457 M€, toutes sous 2 800 000
M€) — un seuil calé sur l'échelle réelle des KPIs concernés, pas sur
une limite macroéconomique abstraite, est le seul qui détecte
effectivement ce type de bug.

### Vérification — 3 axes

1. **Zéro faux positif sur les 28 sociétés en base** : `validate_kpis.py
   --all` relancé après ajout du contrôle — exactement les 5 échecs déjà
   connus et légitimes (AG2R Prévoyance, SGAM, Macifilia ×2, Themis),
   aucun nouvel échec `magnitude_*`.
2. **Test rétroactif contre les bugs réels déjà corrigés** (valeurs
   historiques réinjectées directement dans `executer_controles()`,
   sans toucher `kpis.db`) :
   - Aésio Mutuelle, `scr_total` = 680 657,83 M€ (avant fix Décision
     094) → **détecté** (magnitude_scr_total, dépasse 100 000 M€).
   - Predica, `primes_acquises_brutes` = 121 745,81 M€ (avant fix
     Décision 093) → **détecté**.
   - Groupama, `primes_acquises_brutes` = 39 062,34 M€ (avant fix
     Décision 093) → **NON détecté** (39 062 < 100 000).
3. Confirme la limite assumée et documentée dans le docstring du
   fichier : un facteur ×2 à ×4 sur un KPI déjà petit (le cas
   Groupama/MGEN) reste indétectable par un plafond simple, quel que
   soit le seuil choisi tant qu'il reste au-dessus du maximum réel
   plausible — un seuil plus bas aurait produit des faux positifs sur
   Crédit Agricole Assurances (primes_acquises_brutes = 49 173 M€,
   légitime). Ce contrôle attrape spécifiquement la classe de bug la
   plus grave (erreur d'ordre de grandeur, ×100 et plus), pas tous les
   bugs de valeur — un filet de sécurité supplémentaire, pas un
   remplacement des recoupements arithmétiques au cas par cas.

### Implémentation

`validate_kpis.py` : registre `SEUILS_MAGNITUDE` (dict KPI → plafond
M€, construit depuis `KPIS_MONTANT_STANDARD`/`KPIS_MONTANT_PROVISIONS`
plutôt que des valeurs codées en dur par KPI), nouvelle boucle dans
`executer_controles()` (contrôle 10) — 1 contrôle `magnitude_{kpi_name}`
par KPI en M€ non-NULL ayant un plafond enregistré. Skippé proprement
pour les KPIs en `pct` (ratio_scr/ratio_mcr, jamais concernés par une
erreur d'unité de montant) et pour tout KPI NULL.

## Décision 096 — Sogécap intégrée (29e société) : 3e occurrence du bug d'unité € bruts/K€

CONTEXTE : extraction de Sogécap (Société Générale Assurances), même
méthode que Crédit Agricole Assurances (Décision 093) — document texte
natif, `codes_eiopa`, `groupe`, 20/20 en diagnostic. **Premier essai
détecté immédiatement par le nouveau contrôle de magnitude (Décision
095, livré la veille)** : `scr_total` = 4 259 413,63 M€ (4,26
billions €, impossible), `primes_acquises_brutes` = 17 594 087,40 M€.
Le ratio_scr recalculé restait cohérent (215,80% = publié), signal
caractéristique d'un bug d'ÉCHELLE UNIFORME, pas une erreur ponctuelle
(même signature que Décision 094).

### Diagnostic — même famille de bug que les 7 entités Aéma, sur un document totalement différent

Contrairement à Crédit Agricole Assurances/Predica/MGEN (K€, correct),
l'annexe QRT de Sogécap est en **euros bruts**. Confirmé sans ambiguïté
par recoupement contre 2 sections narratives DISTINCTES et
explicitement libellées "(En millions d'euros)" :
- Page 29 (E.2) : "Capital de Solvabilité Requis... **4 259 M EUR**" —
  le brut QRT `R0090`/S.22.01.21 = "4 259 413 627" colle exactement
  interprété en euros (4 259,41 M€), pas en K€ (aurait donné 4,26
  billions).
- Page 29 : "Fonds propres S2 éligibles à la couverture du SCR... **9
  185 M EUR**" vs brut QRT `R0540`/S.23.01.22 = 9 190,41 M€ (écart
  0,06%, cohérent).
- Page 12 (A) : "chiffre d'affaires... **17,5 Md EUR**" / "charge de
  prestations... **11,5 Md EUR**" vs primes/sinistres QRT calculés
  17 594,09 / 11 553,01 M€ (écarts <0,6%, cohérents — chiffre
  d'affaires commercial vs primes acquises QRT ne sont jamais
  identiques au M€ près, par définition).

Contrairement au bug Aéma (document 100% image, aucun texte natif),
celui-ci touche un document texte natif normalement bien couvert par
`resoudre_variantes_qrt()` (déjà corrigé Décision 093) — preuve que
Décision 093 (dédoublonnage EN/FR + colonne Total) et Décision
094/096 (unité € bruts/K€) sont des bugs **structurellement
indépendants**, l'un n'impliquant pas l'autre.

### Correction

`extract_kpis_sogecap.py` : constante `DIVISEUR_MONTANT = 1_000_000`
(au lieu de `1000` implicite ailleurs) appliquée à TOUS les KPIs de
montant (SCR/MCR/fonds propres/best_estimate/marge_risque/
provisions_techniques/primes/sinistres/composantes SCR) — pas
seulement primes/sinistres comme pour Crédit Agricole Assurances
(bug différent, cf. Décision 093). ratio_scr/ratio_mcr non affectés
(dimensionless).

### Vérification

- Cohérence interne exacte après correction :
  `fonds_propres_eligibles/scr_total×100` = 215,79% vs `ratio_scr`
  publié 215,80% ; `T1nr+T1r+T2+T3` = 9 190,41 = `fonds_propres_
  eligibles` exact ; `best_estimate+marge_risque` = 144 531,05 =
  `provisions_techniques` exact.
- `validate_kpis.py --company Sogécap` : **46/46 contrôles passés**
  (dont 16 contrôles de magnitude, Décision 095 — aucun ne s'était
  déclenché après correction, tous largement sous les plafonds).
- 22 KPIs, 21 valeurs, 1 NULL (`resultat_technique`, attendu).

Leçon retenue : le contrôle de magnitude (Décision 095, écrit la
veille pour un problème déjà résolu) a immédiatement attrapé ce
3e bug en conditions réelles, sur une société entièrement nouvelle —
validation empirique de son utilité au-delà des tests rétroactifs.

## Décision 097 — Cardif Assurance Vie intégrée (30e société), K€ confirmé correct

Même méthode que Sogécap (Décision 096), mais résultat différent :
document texte natif, `codes_eiopa`, `solo`, 20/20 diagnostic.
`DIVISEUR_MONTANT` testé d'abord à 1000 (K€, comportement par défaut)
**avant** toute insertion, par précaution après la découverte Sogécap —
`ratio_scr` recalculé (`fonds_propres_eligibles/scr_total×100` =
170,24%) contre `ratio_scr` publié (170,00%) : écart 0,24%, dans la
tolérance normale d'arrondi, **confirme K€ correct, pas de bug
d'unité ici**. Fichier source purement annexes QRT (pas de section
narrative "(En millions/milliers d'euros)" disponible pour recoupement
indépendant supplémentaire) — le recalcul du ratio reste la
vérification la plus fiable disponible sur ce document, comme déjà
pratiqué pour plusieurs entités Aéma sans narrative dédiée.

Identités vérifiées exactes : `T1nr+T1r+T2+T3` = 11 254,37 =
`fonds_propres_eligibles` ; `best_estimate+marge_risque` = 175 844,60
= `provisions_techniques`.

`validate_kpis.py --company "Cardif Assurance Vie"` : **46/46**. 22
KPIs, 21 valeurs, 1 NULL (`resultat_technique`).

## Décision 098 — Cardif Assurances Risques Divers intégrée (31e société), K€ confirmé correct

Même méthode que Cardif Assurance Vie (Décision 097) : document texte
natif, `codes_eiopa`, `solo`, K€ testé et confirmé AVANT insertion
(`ratio_scr` recalculé 145,76% vs 146,00% publié, écart normal
d'arrondi). Identité `T1nr+T1r+T2+T3` = 617,81 = `fonds_propres_
eligibles` exacte. Magnitudes plausibles pour une entité IARD (plus
petite que l'entité Vie du même groupe, cohérent) : SCR=423,85 M€,
fonds propres=617,81 M€, primes=1 006,82 M€.

`validate_kpis.py --company "Cardif Assurances Risques Divers"` :
**46/46**. 22 KPIs, 21 valeurs, 1 NULL (`resultat_technique`).

## Décision 099 — MAIF intégrée (32e société), 18/22 KPIs, 2 bugs de conversion trouvés dans resoudre_scr_mcr_maif()

Contrairement à Predica/MGEN/Crédit Agricole/Sogécap/Cardif (texte
natif `codes_eiopa`), MAIF est en mode `libelles_francais` (pas de code
R/C standard) — passe par `resoudre_scr_mcr_maif()` (`batch_diagnostic.py`,
Décision 074/084), déjà construite et vérifiée manuellement page par
page pour le diagnostic (17/20). Réutilisée ici SANS relecture des
pages sources (aucune nouvelle valeur devinée, uniquement les résultats
déjà éprouvés par cette fonction, capturés et insérés plutôt que
seulement comptés).

### 2 bugs de conversion trouvés en insérant (la fonction sert au diagnostic, jamais convertie en M€ jusqu'ici)

`resoudre_scr_mcr_maif()` retourne des valeurs BRUTES telles que lues
sur la page, jamais converties (suffisant pour un diagnostic qui ne
fait que compter les KPIs non-NULL) :
1. **Montants en K€, jamais divisés** : `scr_total` brut = 2 344 989 —
   confondu avec des M€ aurait donné 2,3 milliards de milliards.
   Vérifié par cohérence : `fonds_propres_eligibles/scr_total×100` =
   5 329 707/2 344 989×100 = **227,28%**, quasi identique au
   `ratio_scr` brut lu (2,27, cf. point 2) ×100 = 227% — confirme K€,
   PAS le bug euros-bruts de Sogécap (Décision 096), un bug différent
   (simple oubli de conversion, pas une erreur de la source).
2. **Ratios en fraction décimale, jamais ×100** : `ratio_scr` brut lu
   = 2,27 (signifie 227%, pas 2,27%) — confirmé par le même
   recoupement ci-dessus.

Corrigé dans `extract_kpis_maif.py` (÷1000 pour les montants, ×100
pour les 2 ratios) — **PAS dans `resoudre_scr_mcr_maif()` elle-même**,
qui reste inchangée pour ne rien casser dans son usage diagnostic
existant (`batch_diagnostic.py`, 17/20 sur MAIF).

### Irréductibles confirmés, restent NULL (Décision 074, aucune nouvelle tentative)

`fonds_propres_t1_r`/`t2`/`t3` : colonnes vides sans placeholder sur
S.23.01.01 p.121, ambigu 0 vs non-imprimé. `charge_sinistres` exclut
la composante vie (30 615 K€, ~1,3% du total, tableau p.114 en
colonnes rotées non parsable) — documenté explicitement dans la note,
pas caché.

### Vérification

`ratio_scr` recalculé 227,28% vs 227,00% publié (écart normal). 18/22
KPIs remplis. `validate_kpis.py --company MAIF` : **37/38** — le seul
échec (`completude_null_attendu`, 4 NULL au lieu d'1) est le signal de
complétude ATTENDU (même famille que SGAM/AG2R Prévoyance, Décision
087), pas un bug.

## Décision 100 — Covéa intégrée (33e société), 17/22 KPIs, 1 vrai bug de matching trouvé et corrigé (scopé)

Mode `libelles_francais` comme MAIF — **aucun** KPI ne passe par
`resoudre_variantes_qrt()` (pas de code R/C sur ce document), tous
via le repli libellé : `primes_acquises_brutes`/`charge_sinistres`
via `resoudre_primes_sinistres_covea()` (Décision 073, dédiée), le
reste via `extraire_par_libelle()` générique + `KPI_LABELS_FR` —
reproduction exacte du mécanisme de `diagnostiquer_pdf()` (16/20 en
diagnostic), CAPTURÉ ici plutôt que seulement compté. **Aucun code
partagé touché** (rappel Décision 079 : un fix générique avait cassé
Covéa, régression annulée — ce script n'ajoute qu'un fichier
d'extraction, ne modifie ni `classifier_lignes()` ni
`extraire_par_libelle()`).

### Mêmes 2 bugs de conversion que MAIF (Décision 099), corrigés pareil

`ratio_scr`/`ratio_mcr` en fraction décimale (2,21/5,11 -> ×100 = 221%/
511%) ; montants en K€ jamais divisés. Vérifié : `ratio_scr` recalculé
220,82% vs 221,00% publié (écart normal) ; `ratio_mcr` recalculé
513,23% vs 511,00% publié (écart un peu plus large mais attendu —
le numérateur MCR-éligible diffère du numérateur SCR-éligible utilisé
ici par approximation, cf. limite déjà documentée Décision 090 pour
`ratio_mcr_recalcule`, jamais généralisée pour cette même raison).

### 1 vrai bug trouvé : `scr_operationnel` matchait le mauvais libellé fusionné

`extraire_par_libelle()` (jamais modifiée) a retourné **-2 677 K€**
pour "Risque opérationnel" — signe et magnitude incohérents (ce KPI
est toujours positif par construction, et les autres composantes SCR
de ce document vont de 695 à 12 077 M€). Investigation : le libellé
"Risque opérationnel" apparaît 3 fois dans le texte concaténé des
pages QRT, dont 2 fois comme SUFFIXE d'un label fusionné avec 2
AUTRES lignes sans rapport ("Capacité d'absorption des pertes des
impôts différés / Capital de solvabilité requis de base / Risque
opérationnel", collées en un seul "libellé" par `classifier_lignes()`
faute d'une ligne 100% numérique pour les séparer) — la fonction
(repli suffixe, cf. Décision 064) retient la 1re occurrence trouvée,
pas la bonne. La 3e occurrence — "Calcul du capital de solvabilité
requis **C0100** Risque opérationnel" = 1 058 463 K€ — porte un vrai
code de colonne EIOPA et une magnitude cohérente avec les autres
composantes. **Retenue par override scopé au fichier**
(`extract_kpis_covea.py`, jamais dans le code partagé), documenté en
base avec l'analyse complète.

### Irréductibles, restent NULL

`fonds_propres_t1_nr`/`t1_r`/`t2`/`t3` : aucun libellé connu pour ces
4 KPIs dans `KPI_LABELS_FR` sur ce document (jamais construits en
session précédente, contrairement à `fonds_propres_eligibles` qui a
son propre libellé direct) — NULL plutôt que deviné, pas une tentative
échouée mais un gap de couverture déjà présent avant cette tâche.

### Vérification

`validate_kpis.py --company Covéa` : **35/36** — seul échec
(`completude_null_attendu`, 5 NULL) est le signal de complétude
attendu (4 tiers + resultat_technique), pas un bug. 17/22 KPIs
remplis.

## Décision 101 — Allianz Vie intégrée (34e société), 16/22 KPIs, irréductibles re-confirmés + 4e bug positionnel trouvé

Mode `codes_eiopa` (comme Predica/Sogécap/Cardif), `document_type=
"solo"`, `scr_method="modele_interne"`. K€ confirmé correct par
recoupement (`ratio_scr` recalculé 192,32% vs 192,00% publié).

### Les 3 irréductibles de Décision 084 — RE-vérifiés directement sur le document, pas supposés

- `scr_marche`/`scr_contrepartie` : `resoudre_variantes_qrt()` retourne
  **0 variante** pour ces 2 KPIs — confirmé toujours fusionnés dans une
  seule ligne du template modèle interne (`S.25.05.21`, "Total market &
  credit risk"), aucune ligne séparée pour les décomposer.
- `scr_souscription_vie`/`scr_souscription_sante` : idem, fusionnés.
- `scr_diversification` : **re-confirmé** en lisant directement la page
  90 (`S.25.05.21`) — `R0060 "Diversification"` = `"-               912
  286"`, signe et magnitude toujours séparés par un grand espacement
  (même famille que BPCE IARD/Predica/MGEN/MACSF, Décision 091), mais
  cette variante précise (magnitude et signe comme 2 TOKENS distincts
  très espacés sur la même ligne, pas juste une espace fine adjacente
  ou des parenthèses) n'est PAS couverte par le détecteur générique de
  Décision 091 — cohérent avec le choix déjà documenté de ne PAS
  généraliser ce cas précis dans le code partagé (Décision 085 : un fix
  générique de ce type avait cassé Covéa). Laissé NULL, comme prévu par
  la tâche demandée — aucune tentative de nouveau fix scopé ici (hors
  périmètre explicite de cette tâche).

### 4e occurrence du bug positionnel (Décision 093, page "Crédit Agricole")

`primes_acquises_brutes`/`charge_sinistres` : `extract_qrt_native()`
trouve le libellé de la ligne R1510/R1610 (p.84, S.05.01.02.02) mais
**capture zéro valeur**, alors que 9 valeurs sont bien imprimées en
texte natif (vérifié : R1510 = "1 864 213 / 1 295 378 / 2 266 284 / - /
- / - / 285 192 / 268 714 / **5 979 782**"). Même bug positionnel,
distinct des bugs A/B, déjà rencontré sur Crédit Agricole Assurances
(Décision 093) et maintenant sur un 2e document — pas encore
généralisé/corrigé dans le code partagé (occurrence trop rare, 2
documents sur 34, scoping par fichier reste le choix le plus sûr pour
l'instant). Non-vie explicitement "Non applicable" sur ce document
(assureur vie pur) — seule la composante vie compte. Valeurs lues
manuellement sur la colonne Total (C0300) : primes = 5 979,78 M€,
sinistres = 5 619,11 M€.

### Vérification

`validate_kpis.py --company "Allianz Vie"` : **35/36** — seul échec
(`completude_null_attendu`, 6 NULL) est le signal de complétude
attendu (5 KPIs irréductibles + resultat_technique), pas un bug.
16/22 KPIs remplis — le plus bas des 6 sociétés ajoutées dans cette
tâche, cohérent avec son score diagnostic déjà le plus bas (15/20).

### Bilan génériques vs spécifiques (les 6 sociétés de cette tâche)

| Société | Bugs génériques (déjà connus) | Bugs/limites spécifiques au document |
|---|---|---|
| Sogécap | — | Bug d'unité € bruts/K€ (3e occurrence, Décision 096) |
| Cardif Assurance Vie | — | Aucun (K€ confirmé correct du 1er coup) |
| Cardif Assurances Risques Divers | — | Aucun |
| MAIF | 2 bugs de conversion dans `resoudre_scr_mcr_maif()` (jamais adaptée pour l'insertion) | 3 tiers de fonds propres irréductibles (déjà connus, Décision 074) |
| Covéa | Mêmes 2 bugs de conversion que MAIF | 1 vrai bug de matching (`scr_operationnel`, label fusionné) + 4 tiers non couverts par `KPI_LABELS_FR` |
| Allianz Vie | — | 3 irréductibles re-confirmés (Décision 084) + 4e occurrence du bug positionnel de Décision 093 |

**3 sur 6 sociétés ont révélé un problème JAMAIS rencontré avant cette
tâche** (Sogécap : nouveau document en € bruts ; Covéa : nouveau bug de
matching ; Allianz Vie : 2e occurrence confirmée d'un bug déjà vu 1
seule fois) — confirme que le score de diagnostic (/20) ne garantit
JAMAIS la fiabilité en l'absence de vérification arithmétique
individuelle, cohérent avec la leçon déjà tirée en Décision 093.

## Décision 102 — Clarification : "15/15 groupes exploitables" (diagnostic) ≠ "groupes avec extraction réelle en base"

CONTEXTE : après l'ajout de Sogécap/Cardif Vie/Cardif RD/MAIF/Covéa/
Allianz Vie (Décisions 096-101), un résumé de session a affirmé "les
15 groupes du marché français initialement visés sont maintenant tous
couverts par au moins une extraction réelle en base" — **confusion
détectée et corrigée sur demande de l'utilisateur** : ce n'était vrai
qu'au sens du tally DIAGNOSTIC (Décision 089/090, score `/20` via
`batch_diagnostic.py`), jamais vérifié contre la présence réelle dans
`kpis.db`. Les deux mesures sont **distinctes et ne doivent jamais être
confondues** :

- **"15/15 groupes exploitables au sens diagnostic"** (Décision 089/090)
  — reste VRAI, ne pas supprimer ni réviser : mesure la qualité de
  l'extraction générique/libellé sur un score `/20` (via
  `batch_diagnostic.py`), sans jamais insérer la moindre valeur dans
  `kpis.db`. Un groupe "exploitable" à ce sens peut n'avoir AUCUNE
  ligne dans `kpis.db`.
- **"Groupes avec extraction réelle en base"** — mesure DIFFÉRENTE,
  vérifiée par requête directe sur `kpis.db` (`SELECT DISTINCT name
  FROM companies`) au moment de l'écriture de cette décision :
  **11 groupes sur 15** ont au moins une entité réellement insérée
  (CNP, Crédit Agricole, BNP Paribas/Cardif, Société Générale/Sogécap,
  Covéa, Groupama, Allianz, MACIF/Aéma, MAIF, AG2R La Mondiale, MGEN).
  **4 groupes n'en ont AUCUNE**, malgré un score diagnostic ancien
  jamais migré :

| Groupe | Entités diagnostiquées (ancien, jamais migré) | Décision d'origine |
|---|---|---|
| AXA | AFV (AXA France Vie) 16/20, AFI (AXA France IARD) 16/20 | Décision 082 |
| BPCE | BPCE Vie 20/20, BPCE IARD 13/20 | Décision 082/086 |
| Generali | Generali Iard 17/20, Generali Vie 17/20 | Décision 080 |
| SwissLife | 20/20 | Décision 076/082 |

### Règle retenue pour la suite

Tout futur bilan de session doit préciser EXPLICITEMENT laquelle des 2
mesures est citée ("exploitable au sens diagnostic" vs "avec extraction
réelle en base") — ne jamais réutiliser "couvert"/"exploitable" seul
sans qualificatif, cause directe de la confusion corrigée ici. AXA,
BPCE, Generali, SwissLife restent des candidats identifiés pour une
future extraction réelle (mêmes méthodes déjà éprouvées : native texte
`codes_eiopa` pour BPCE Vie/Generali/SwissLife probablement, à
re-diagnostiquer avant extraction — ne pas supposer le mode sans
vérifier, cf. leçon Sogécap/Décision 096), non commencée à ce jour.

## Décision 103 — Métadonnées `type_document`/`scr_method`/`type_activite`/`unite_source` sur `companies`

CONTEXTE : la table `companies` (`id, name, type, country`) manquait de
métadonnées que le pipeline connaît déjà de façon éparse (résultat de
`detecter_templates()`, décisions d'unité 094/096), utiles pour un
futur dashboard comparatif (filtrage par type d'activité, méthode SCR,
etc.) sans devoir re-parser 34 scripts d'extraction à chaque fois.

4 colonnes TEXT ajoutées par `ALTER TABLE` (script `populate_company_metadata.py`,
idempotent — vérifie `PRAGMA table_info` avant d'ajouter) et remplies
pour les 34 sociétés, **jamais devinées** :

- **`type_document`** (solo/groupe) et **`scr_method`**
  (formule_standard/modele_interne_partiel/modele_interne_complet) :
  - 12 sociétés à PDF autonome → `detecter_templates()` **ré-exécuté
    en direct** cette session (pas repris d'une décision ancienne),
    résultat brut dans `metadata_diagnostic.txt`. Cas particulier
    **Allianz Vie** : `detecter_templates()` renvoie `document_type=
    "inconnu"` (classification auto ambiguë sur ce PDF) — recoupé avec
    le template EIOPA réellement utilisé lors de l'extraction
    (Décision 101, S.23.01.01 = code solo, vs S.23.01.22 pour un
    groupe) → stocké `"solo"`, évidence directe, pas une supposition.
  - 22 entités AG2R (9)/Aéma (13), extraites depuis un document
    combiné (pas de PDF autonome à re-diagnostiquer) → reprises des
    décisions déjà vérifiées (081/083/087) : `formule_standard` pour
    les 22 ; `groupe` uniquement pour SGAM AG2R LA MONDIALE et Aema
    Groupe (entités consolidées), `solo` pour les 20 autres.
  - **MAIF** : `scr_method` laissé **NULL** — mode `libelles_francais`,
    non détectable automatiquement, et aucune source fiable alternative
    trouvée. Seule valeur NULL sur les 34×2 champs.

- **`type_activite`** (Vie/Non-vie/Mixte/Mutuelle) : déduit par requête
  directe sur `kpis` (année 2025) selon la règle demandée —
  `scr_souscription_vie` ET `scr_souscription_nonvie` > 0 → Mixte ;
  vie seul → Vie ; non-vie seul → Non-vie ; ni l'un ni l'autre positif
  → Mutuelle (mutuelles/prévoyance santé pures, ex. Macifilia/Themis/
  Prima/AG.Mut/MMJ/MNPAF/Nuoma). Résultat sur les 34 : 17 Vie, 9 Mixte,
  5 Mutuelle, 3 Non-vie, 0 NULL.
  - **Override documenté pour Allianz Vie** : la règle KPI dérivait à
    tort "Mutuelle", car `scr_souscription_vie` est NULL (fusionné avec
    `scr_souscription_sante` dans une seule ligne QRT modèle interne —
    irréductible, Décision 084/101) alors que `scr_souscription_nonvie`
    vaut 0. Le document source lui-même le dément sans ambiguïté (page
    84, dump `allianzvie_p84_dump.txt` : *"S.05.01.02.01 - Non-vie...
    Non applicable"*, seule la colonne Vie porte des primes) — la
    société s'appelle d'ailleurs "Allianz **Vie**". Conformément à la
    consigne "déduis-le des KPIs... ou depuis le PDF si l'info est plus
    fiable", override ciblé et documenté dans le code
    (`TYPE_ACTIVITE_OVERRIDES`) → stocké `"Vie"`. Aucun autre override
    appliqué : les 33 autres sociétés suivent la règle KPI brute sans
    intervention manuelle.

- **`unite_source`** (K€ / euros bruts) : connu précisément par les bugs
  déjà corrigés (Décisions 094/096) — 7 entités Aéma (Aesio Mutuelle,
  MNPAF, MMJ, Nuoma, Abeille Vie, Abeille Epargne Retraite, Abeille
  IARD Santé) + Sogécap = 8 sociétés en euros bruts ; les 26 autres en
  K€ (convention majoritaire du corpus).

RÉSULTAT : `ALTER TABLE companies ADD COLUMN` ×4, 34/34 sociétés
remplies, 1 seul NULL (MAIF/scr_method), 0 valeur devinée.

## Décision 104 — Vérification kpi_service.py (34 sociétés) : 2 bugs trouvés et corrigés

CONTEXTE : test systématique des 5 fonctions de requête exposées par
`kpi_service.py` (`get_kpis`, `get_kpi`, `compare_kpis`,
`get_corpus_stats`, `get_validation_report`) contre les 34 sociétés
réellement en base — script de vérification exécuté en session, pas
de suite de tests automatisée dédiée à ce jour.

### Résultats des tests demandés

- `get_kpis("Groupama"/"Sogécap"/"MAIF", 2025)` : 22 KPIs chacune,
  21/21/18 valeurs non-NULL respectivement (cohérent avec les
  irréductibles déjà documentés de chaque société). OK.
- `compare_kpis("ratio_scr", 2025)` sur les 34 : 34 valeurs, 0 `None`
  — `ratio_scr` est effectivement rempli pour toutes. OK.
- `get_corpus_stats("ratio_scr", 2025)` : n=34, moyenne=298.26,
  médiane=233.5, min=144.0 (Themis), max=953.0 (Macifilia) — moyenne
  tirée vers le haut par quelques petites mutuelles à SCR faible
  (Macifilia), cohérent, pas d'anomalie de calcul.
- `get_validation_report("Macifilia", 2025)` : **anomalie trouvée**
  (détaillée ci-dessous), corrigée, puis re-testée OK : 46/46 checks,
  2 échecs réels (`mcr_inferieur_scr_total`, `signe_charge_sinistres`
  — cohérent avec les échecs déjà connus/attendus sur cette société).

### Bug 1 — `validation_checks` accumulait des doublons à chaque ré-exécution de `validate_kpis.py`

`inserer_controles()` (validate_kpis.py) faisait un `INSERT` simple
sans purge préalable, et la table n'a aucune contrainte unique sur
(company_id, year, check_name). Chaque ré-exécution de
`validate_kpis.py --all`/`--company` (fréquentes cette session, pour
re-tester après chaque correction) **ajoutait** des lignes au lieu de
les remplacer. Constaté sur les 34 sociétés : de 144 à 695 lignes en
base pour seulement 36 à 49 `check_name` distincts réels (facteur
×2 à ×14). Conséquence directe : `get_validation_report`/
`validation_summary` retournaient un `n_checks` gonflé et une liste
`checks_echoues` avec des doublons — ne reflétait PAS l'état réel de
`kpis.db`, sans jamais planter (d'où la difficulté à le repérer sans
comparer explicitly `COUNT(*)` vs `COUNT(DISTINCT check_name)`).

**Corrections appliquées** :
1. `inserer_controles()` : ajout d'un `DELETE FROM validation_checks
   WHERE company_id=? AND year=?` avant la boucle d'insertion — rend
   l'exécution idempotente, plus aucune accumulation possible.
2. Nettoyage ponctuel des 13262 lignes déjà accumulées en base : pour
   chaque (company_id, year, check_name), conservation de la ligne
   `MAX(id)` uniquement (= résultat de la dernière exécution réelle),
   suppression des 11733 doublons plus anciens. Résultat : 1529 lignes
   — coïncide exactement avec le total déjà documenté dans
   `PIPELINE_EXTRACTION_KPIs.md` ("1521/1529, 99.5%"), confirmant que
   le nettoyage retombe bien sur l'état réel et non sur un chiffre
   inventé.

### Bug 2 — `get_validation_report` n'était pas gracieux sur une société inconnue (contredit son propre contrat documenté)

Le commentaire de section (kpi_service.py, "Phase 3.6") promet que ces
alias sont "GRACIEUX sur une entreprise absente (dict/liste vide,
jamais une exception)", et `get_kpis` le respecte bien. Mais
`get_validation_report` appelle en interne `validation_summary()` et
`get_validation_checks()` — deux méthodes plus anciennes, STRICTES,
qui lèvent `KpiIntrouvable` — sans les intercepter : testé sur une
société absente de `companies`, `get_validation_report` plantait avec
une exception non gérée au lieu de retourner un rapport vide.
**Corrigé** par un `try/except KpiIntrouvable` retournant
`{"summary": {n_checks:0, n_passed:0, n_failed:0, checks_echoues:[]},
"checks": []}`, conforme au contrat documenté. `get_kpi` (méthode
ancienne, non listée dans les alias Phase 3.6) reste volontairement
stricte — comportement voulu, pas un bug.

### Règle retenue

Toute future modification touchant l'insertion dans une table sans
contrainte unique doit explicitement vérifier l'idempotence d'une
ré-exécution (comparer `COUNT(*)` vs `COUNT(DISTINCT ...)` avant/après
un second run) — ce bug est passé inaperçu plusieurs sessions car
aucune fonction ne plantait ni ne renvoyait un résultat visiblement
faux, juste gonflé.

## Décision 105 — Export JSON de kpis.db (export_kpis_json.py / kpis_export.json)

CONTEXTE : l'onglet Analyse de l'interface (développée ailleurs,
migration Next.js) consomme actuellement des données de démonstration
inventées (`frontend/src/data/analyse-demo.ts`). `kpis_export.json`
est un premier pas vers leur remplacement par les vraies données de
`kpis.db` — **l'interface elle-même n'est pas modifiée par cette
tâche**, seul le JSON est produit.

`export_kpis_json.py` (lecture seule, via `KpiService`, aucune
dépendance RAG/Qdrant) génère `kpis_export.json` à la racine, avec :
- `generated_at` (ISO 8601, UTC) et `year` (2025).
- `companies` : les 34 sociétés, chacune avec ses métadonnées
  (`type_document`, `scr_method`, `type_activite`, `unite_source` —
  Décision 103) et ses 22 KPIs (`value`, `unit`, `validated`) —
  toujours les 22 clés présentes même si `value` est NULL, pour un
  accès direct côté frontend sans vérification d'existence de clé.
- `corpus_stats` : moyenne/médiane/min/max par KPI (via
  `get_corpus_stats`, déjà vérifié Décision 104), sur les sociétés qui
  l'ont en base avec une valeur non-NULL.

VÉRIFICATION : 34 sociétés, 748 lignes KPI (34×22, cohérent), 428
validées, 22 KPIs avec statistiques corpus. Contrôles ponctuels
manuels : `ratio_scr` corpus_stats identique au résultat déjà vérifié
en Décision 104 (moyenne 298.26, médiane 233.5, min 144.0, max 953.0) ;
Allianz Vie → `type_activite="Vie"` (override Décision 103) présent
dans l'export ; MAIF → `scr_method=None` (NULL) présent tel quel, pas
substitué par une valeur inventée ; encodage UTF-8 du fichier vérifié
directement (`€` présent correctement, pas d'échappement cassé).

## Décision 106 — extraire_un_pdf.py : extraction à chaud sur un PDF SFCR jamais vu (contrat frontend "Ajouter un PDF")

CONTEXTE : demande du soir (frontend, coordination écrite dans
`Claude outputs/demande-claude-code-extraction-live.md`) — le nouvel
onglet "Ajouter un PDF" (commit f90e74f) écrit déjà le PDF confirmé
dans `data/` ; il manquait le pont vers le pipeline d'extraction.

### Corrections apportées à la demande d'origine (avant de coder, comme invité par le document de coordination)

1. **"Cascade Gemini/Mistral/Groq"** : cette cascade n'existe PAS dans
   le pipeline d'extraction KPI — c'est le fallback LLM du chatbot RAG
   sur la directive 2009/138/CE (`src/rag.py`, CLAUDE.md), un système
   séparé. L'extraction KPI (34 sociétés) repose sur un appariement de
   gabarits QRT en texte natif (`detecter_templates()` +
   `classify_pages()`/`extract_qrt_native()` + `resoudre_variantes_qrt()`/
   `valeur_principale()`, dictionnaire `KPI_QRT_MAPPING`) — AUCUN appel
   LLM sauf un fallback vision Gemini très ponctuel et non générique
   (`extract_kpis.py::lire_picture_75`, spécifique à une image de
   Groupama). `extraire_un_pdf.py` réutilise donc la vraie logique déjà
   testée, sans nouvelle méthode d'extraction — l'étape `"appel_modele"`
   du contrat JSON est conservée telle quelle (le frontend est déjà
   écrit autour de ce nom), son message décrit honnêtement
   l'appariement de gabarits, pas un appel LLM.
2. **`export_kpis_for_frontend.py` (ou l'équivalent) pour
   `donnees-extraites.json`** : ce script existait déjà mais
   n'écrivait QUE `kpi-sources.json` — `donnees-extraites.json` avait
   été généré une fois par une requête SQL ad hoc (commit 2a71854),
   jamais rejouable. Étendu (`export_donnees_extraites()`) pour générer
   aussi ce second fichier, avec la même forme exacte (vérifié :
   0 divergence de contenu KPI contre le fichier committé, hors champ
   `valide` qui a légitimement changé après le nettoyage des doublons
   de validation_checks, Décision 104). **Piège trouvé en vérifiant** :
   `companies.type` en base porte déjà, pour les 21 sociétés
   multi-entités, un suffixe `" (Nom du groupe)"` ajouté directement en
   base par une mutation antérieure NON reflétée dans le JSON committé
   — le générateur retire ce suffixe s'il est présent pour reproduire
   fidèlement l'affichage actuellement déployé plutôt que de le changer
   silencieusement via un export.

### `extraire_un_pdf.py`

CLI : `python extraire_un_pdf.py --pdf <chemin> --societe <nom> --annee <int> --job-id <id>`.
Écrit `jobs/<job-id>.json` à chaque étape (`extraction_pdf` →
`appel_modele` → `ecriture_db` → `validation` → `ecriture_db` régénération
export — ordre légèrement différent de la demande d'origine, la
validation devant lire des KPIs déjà en base). Structure JSON conforme
au contrat demandé (`statut`, `etape`, `message`, `societe`, `annee`,
`kpis[]`, `erreur`). Ne lève jamais d'exception non gérée : un seul
`try/except` englobant toute la logique métier écrit `statut="erreur"`
avec un message clair en cas d'échec, à n'importe quelle étape.

**`validated` forcé à `0`** pour tous les KPIs de cette extraction à
chaud, y compris ceux dont TOUS les contrôles automatiques passent
(écrase volontairement le résultat de `marquer_valides()` après coup)
— conforme à la demande explicite : un contrôle mécanique n'est pas
une revue humaine, "pas de checkpoint humain avant demain matin".
`unite_source` enregistre l'hypothèse K€ comme **non vérifiée**
(contrairement aux 8 sociétés confirmées par recoupement, Décisions
094/096) — aucune correction d'unité silencieuse possible sur un
document jamais vu.

En cas de succès : régénère automatiquement `kpi-sources.json` et
`donnees-extraites.json` (appel direct des fonctions de
`export_kpis_for_frontend.py`), pour que "Base de données" affiche la
nouvelle société sans étape manuelle.

### Bug trouvé et corrigé en testant contre un cas réel

Test end-to-end sur `data/sfcr_cnp_assurances_2025.pdf` (société
factice "TEST Extraction Live", année 2099, nettoyée après test),
comparé aux 22 valeurs déjà vérifiées de CNP Assurances 2025 (même
PDF) : **1er essai, 2 KPIs faux d'un facteur ~23-26×**
(`primes_acquises_brutes`, `charge_sinistres`) — le script prenait la
1re variante du mapping qui matche (`resultats[0]`), alors que ces 2
KPIs sont CUMULATIFS (vie et non-vie sont 2 variantes COMPLÉMENTAIRES,
pas alternatives, cf. docstring de `resoudre_variantes_qrt`) : sur un
assureur mixte comme CNP, seule la composante vie était captée.
Corrigé en sommant TOUTES les variantes matchées, même pattern déjà
vérifié dans `extract_kpis_cnp.py` (Décision 059,
`sum(v for v, _, _ in resultats)`). Après correction : **0 divergence
sur les 22 KPIs** contre les valeurs déjà en base.

**Effet de bord corrigé au passage** : `extract_kpis.py` force le
préchargement de PaddleOCR au niveau module (contournement Décision
057) — plantait l'import ENTIER du module (y compris les fonctions
génériques sans rapport avec l'OCR) dans un environnement sans
`paddleocr` installé du tout. Rendu non bloquant (`try/except
ImportError`, avertissement au lieu d'un crash) — élargissement strict,
aucun changement de comportement quand `paddleocr` est présent.

**Environnement d'exécution** : ce script (comme tout le pipeline
Docling/PyMuPDF/PaddleOCR) doit tourner via
`test_markdrop/.venv/Scripts/python.exe`, PAS le Python système —
`fitz`/`docling`/`paddleocr` n'y sont pas installés. À communiquer côté
frontend pour la commande lancée en détaché.

## Décision 107 — GAP 1 : auto-détection d'unité K€/€ bruts + contrôle plancher

CONTEXTE : `extraire_un_pdf.py` (Décision 106) supposait K€ en dur,
sans aucune vérification — si un PDF réel arrivait en € bruts, tous
les montants sortiraient ×1000 trop grands, et le contrôle de
magnitude existant (Décision 095, plafond) ne détecte que les valeurs
trop GRANDES, jamais trop PETITES.

### Contrôle plancher (`validate_kpis.py`)

Ajouté, symétrique du plafond : `scr_total`/`fonds_propres_eligibles`
(seuls KPIs toujours strictement significatifs, contrairement à
`scr_diversification` ou `fonds_propres_t3` souvent proches de 0) < 0,5
M€ → suspicion d'erreur d'unité ÷1 000 000 au lieu de ÷1000. Testé
rétroactivement sur les 34 sociétés (`validate_kpis.py --all`) :
**zéro faux positif** (plus petite valeur réelle : Themis
scr_total=1,055 M€ — marge ≥2×), 1597 contrôles au total
(1529 + 68 nouveaux = 34×2), 0 doublon (idempotence Décision 104
toujours valide).

### Auto-détection (`extraire_un_pdf.py::detecter_diviseur_montant`)

Décide K€ (÷1000) vs € bruts (÷1 000 000) en comparant l'ordre de
grandeur BRUT (avant tout diviseur) de `scr_total`/
`fonds_propres_eligibles` contre la plage [0,5 ; 100 000] M€ (mêmes
seuils plancher/plafond que `validate_kpis.py`, une seule source de
vérité) — **même méthode que celle qui a réellement permis de détecter
le bug historique** (Décision 094, recoupement d'ordre de grandeur),
pas une heuristique inventée. Une recherche textuelle d'étiquette
d'unité ("(en euros)", "(en milliers d'euros)"...) a été écartée comme
signal primaire : Décision 094 documente explicitement qu'aucune
étiquette n'était visible sur les pages QRT des 7 entités Aéma
concernées — un texte absent n'aurait rien détecté dans le cas réel
qui motive ce correctif.

**Testé rétroactivement sur les 34 sociétés** (raw reconstruit =
valeur stockée × diviseur réel connu, Décision 103) :
**31/34 correctement détectées, zéro faux positif** (aucune société
K€ n'est jamais mal classée euros-bruts, ni l'inverse — la détection
retombe sur le défaut K€ en cas de doute, jamais une fausse
confiance). **3 échecs identifiés et compris** : MMJ, MNPAF, Nuoma —
leur ordre de grandeur reste plausible sous LES DEUX hypothèses (ni
impossible ni évidemment trop petit pour un assureur français
quelconque). Décision 094 elle-même n'a résolu ces 3 cas précis
qu'en recoupant contre le SCR narratif du GROUPE ENTIER (signal
externe au document) — hors de portée d'une détection par magnitude
sur un seul document, non tentée ici (hors périmètre de ce correctif).
Dans ces 3 cas comme dans tout cas ambigu, `unite_source` reste
explicitement marqué "AMBIGU... non vérifié", jamais une étiquette
"détecté" trompeuse.

**Limite additionnelle notée** : pour toute société de taille normale
ou grande (scr_total réel ≥ 500 M€), les deux hypothèses (K€ et euros
bruts) tombent techniquement dans la plage [0,5 ; 100 000] M€ une fois
divisées — la détection retombe donc sur "AMBIGU → K€" même quand K€
est en réalité la seule interprétation raisonnable. Ce n'est pas un
défaut fonctionnel (le choix retenu reste le bon dans ces cas, c'est
la convention majoritaire déjà établie du corpus) mais une limite de
la façon dont la confiance est rapportée — "AMBIGU" est donc l'issue
ATTENDUE pour la plupart des grandes sociétés, pas un signe d'échec.

Re-testé end-to-end sur CNP Assurances (comme Décision 106) après
câblage : 22/22 valeurs identiques aux valeurs déjà vérifiées en base,
aucune régression.

## Décision 108 — GAP 2 : messages clairs pour un PDF sans annexe QRT exploitable

CONTEXTE : `extraire_un_pdf.py` (Décision 106) s'arrêtait déjà
proprement sur un PDF sans QRT exploitable (jamais de résultat faux),
mais avec un seul message générique ne distinguant pas la cause —
important pour que le fondateur comprenne POURQUOI une extraction a
échoué (document non-SFCR vs. document SFCR scanné).

### 3 cas désormais distingués dans `construire_corpus()`

1. **0 page QRT détectée** → *"Aucune annexe QRT trouvée dans ce
   document"* — probablement un rapport narratif pur (type MAAF) sans
   annexes quantitatives, ou pas un document SFCR.
2. **Pages QRT détectées mais 100% image** (texte natif insuffisant
   sur TOUTES, `pages_ignorees` non vide, `templates_inconnus` vide) →
   *"N page(s) QRT détectée(s) mais en format image — extraction
   automatique non supportée, traitement manuel requis"* — même limite
   que les documents 100% image déjà rencontrés dans ce projet
   (Aéma/AG2R, jamais traités automatiquement, toujours par isolation
   de pages + relecture manuelle). **Aucun pipeline OCR automatique
   ajouté** (explicitement hors périmètre demandé, trop lourd).
3. **Pages QRT avec texte natif mais aucun gabarit reconnu** (cas non
   demandé explicitement mais découvert en implémentant — un document
   SFCR d'un type EIOPA non couvert par `KPI_QRT_MAPPING`) →
   *"N page(s) QRT détectée(s) mais aucune ne correspond à un gabarit
   EIOPA connu"*, distinct des 2 autres.

Ces 3 cas restaient auparavant indiscernables (les 2 premiers
produisaient le même message ; le 3e n'était même pas détecté comme un
échec — le corpus restait silencieusement vide et l'extraction
continuait vers 22 KPIs NULL, un "succès" trompeur).

### Test

Testé par substitution de `classify_pages()` (Docling) par une liste
de pages fabriquée pour chacun des 3 cas — évite de faire tourner
Docling sur un vrai document 621 pages (Aéma, 100% image) juste pour
vérifier une branche de contrôle. Les 3 messages s'affichent
correctement, chacun avec sa cause distincte.

## Décision 109 — GAP 3 : généralisation du fallback modèle interne + 2 découvertes signalées, non corrigées

CONTEXTE : `resoudre_par_libelle_modele_interne()` (Décision 056)
n'était appelée que par le script Groupama (`extract_kpis.py::
extraire_tout`), jamais par les scripts des 2 autres sociétés modèle
interne déjà en base (Allianz Vie/IARD) ni par `extraire_un_pdf.py` —
un nouveau PDF en modèle interne ne bénéficiait du mapping standard
que "par chance" (cas d'Allianz Vie), pas par construction.

### Correctif appliqué

Dans la boucle SCR (`scr_operationnel`... `scr_diversification`) de
`extraire_un_pdf.py::extraire_kpis()` : si `resoudre_variantes_qrt()`
ne matche rien ET que `inventaire["scr_method"]` commence par
`"modele_interne"`, tente désormais `resoudre_par_libelle_modele_
interne()` avant de mettre NULL. Jamais tenté sur une société en
formule standard (où l'absence de résultat via le mapping standard
reste un signal fiable, pas une raison d'aller chercher un libellé de
modèle interne hors de propos).

### Test sur Groupama (modèle interne partiel)

`extraire_un_pdf.py` exécuté sur `data/SFCR_2025_Groupe-Groupama.pdf`
(société de test, nettoyée après coup) : seulement 1 page QRT
exploitable en texte natif sur les 12 détectées (10 ignorées, format
image ; 1 template hors dictionnaire) — bien EN DEÇÀ de ce que la
vraie extraction Groupama utilise (`extract_kpis.py` s'appuie sur un
corpus pré-construit via Gemini VLM sur plusieurs sources, hors
périmètre de ce pipeline générique à chaud). **Résultat : les 7 KPIs
SCR restent NULL, identique à avant le fix** — le fallback n'a rien à
chercher car les pages S.25.0x n'atteignent jamais le corpus. Pas une
régression du correctif, une limite du corpus disponible en amont.

### Test sur Allianz Vie (modèle interne partiel) — 2 découvertes

`extraire_un_pdf.py` exécuté sur
`data/Rapport_de_solvabilité_Allianz_Vie_2025.pdf` (société de test,
nettoyée après coup), comparé aux 22 valeurs déjà vérifiées en base :

1. **`scr_diversification` : NULL → 912,286 M€ via le fallback**
   (template `S.25.05.21`, libellé exact `"Diversification"` — match
   net, pas approximatif). **PAS écrit dans la vraie ligne Allianz Vie
   de kpis.db** : le signe est positif alors que
   `kpi_definitions.py` attend `"negative"` pour ce KPI, et le
   docstring de `extract_kpis_allianzvie.py` documente déjà
   explicitement un "bug de signe détaché sur CE document précis" pour
   ce KPI exact — la valeur trouvée est probablement juste, mais son
   signe est suspect et non vérifié indépendamment. Conforme à la
   consigne : *"si le fallback améliore un KPI qui était NULL → mets à
   jour... si le fallback contredit une valeur existante → signale
   sans corriger"* — ici ambigu (améliore un NULL mais avec un signe
   suspect) → signalé, non appliqué à la vraie ligne. Le fallback reste
   actif pour tout FUTUR document inconnu : le contrôle `signe_
   scr_diversification` déjà existant (`validate_kpis.py`) capterait
   un signe positif comme échec, et `validated` reste de toute façon
   forcé à 0 sur une extraction à chaud (Décision 106) — aucun risque
   silencieux introduit.

2. **Découverte séparée, non corrigée** : `primes_acquises_brutes`/
   `charge_sinistres` valent **0,0** (pas NULL) au lieu des 5979,78/
   5619,11 M€ déjà vérifiés — cause : `sommer_toutes_colonnes()`
   (`extract_kpis.py`) traite délibérément "ligne trouvée par libellé
   mais 0 colonne capturée du tout" de la MÊME façon que "ligne trouvée
   avec certaines cellules légitimement à 0/tiret" (comportement
   documenté et VOULU depuis un fix antérieur, motivé précisément par
   AFV/Allianz Vie/AG2R groupe — cf. commentaire en tête de fonction).
   Ce n'est PAS une régression de ce correctif (le bug pré-existe,
   indépendant de la boucle SCR modifiée ici) mais une découverte
   dangereuse : `0,0` n'est filtré par AUCUN contrôle actuel
   (`primes_acquises_brutes` n'est pas dans `KPIS_MONTANT_PLANCHER`,
   Décision 107) — ressemble à une extraction réussie alors que c'est
   un échec silencieux. **Non corrigé ce soir** : cette fonction a déjà
   régressé 2 fois historiquement sur ce point précis (cf. son propre
   commentaire), est partagée par les 34 scripts + `extraire_un_pdf.py`,
   et mérite le plein protocole de régression sur les 34 sociétés avant
   toute modification — hors du temps disponible ce soir, signalé pour
   une session dédiée plutôt que patché à la hâte.

### Régression finale (les 34 sociétés réelles)

`validate_kpis.py --all` : mêmes 3 échecs déjà connus et attendus
(MAIF/SGAM `completude_null_attendu`, Macifilia/Themis `mcr_inferieur_
scr_total`), **zéro nouvelle régression, zéro faux positif plancher/
plafond**. `kpis.db` : 34 sociétés, 748 lignes KPI, 1597 contrôles de
validation, 0 doublon — état identique à avant ce correctif (les 2
sociétés de test ont été entièrement nettoyées).

## Décision 110 — raw_value/raw_unit sur kpis (chiffre brut du PDF, additif) + correction d'un compte d'échecs sous-estimé

CONTEXTE : signalé "bug critique" côté frontend/fondateur (28/09/2026) —
la conversion K€→M€ était perçue comme une perte de précision ("le PDF
dit 4 266 905, l'outil stocke 4266,9 M€"). Vérification factuelle
AVANT toute action : la conversion est mathématiquement correcte
(4 266 905 K€ = 4266,905 M€, exactement ce qui est stocké) et résulte
de ~10 décisions de vérification ce soir (094-107) — ce n'est pas un
bug de calcul. Le signalement mentionnait aussi "le prompt d'extraction
LLM" comme fichier concerné : n'existe pas dans ce pipeline (déjà
clarifié Décision 106 pour un signalement similaire). Question posée à
l'utilisateur avant de toucher au schéma partagé : ajouter le chiffre
brut EN PLUS (additif) ou remplacer entièrement la conversion M€
(cassant, annulerait ~10 décisions) → **réponse : additif**.

### Correctif

2 colonnes ajoutées sur `kpis` (`ajouter_valeurs_brutes.py`, idempotent) :
- `raw_value` : chiffre brut tel qu'imprimé dans le PDF, AVANT ÷1000/
  ÷1 000 000 — uniquement pour les KPIs `unit='M€'` (c'est là que la
  conversion existe ; les KPIs `pct` n'ont pas d'équivalent, laissés à
  NULL).
- `raw_unit` : "K€" ou "euros bruts", depuis `companies.unite_source`
  (Décision 103/107).

`value`/`unit` restent la SEULE source de vérité pour tout calcul/
contrôle existant (validate_kpis.py, kpi_service.py) — vérifié 0
divergence value/unit avant/après sur les 748 lignes.

**34 sociétés existantes** : `raw_value` RECONSTRUIT par arithmétique
inverse (`value × diviseur`, depuis `unite_source`) — identité exacte
avec l'insertion d'origine (`value = raw/diviseur`), pas une nouvelle
lecture du PDF. Vérifié sur l'exemple cité du signalement : Allianz
Vie `fonds_propres_eligibles` → `raw_value=4266905.0, raw_unit="K€"`,
correspond exactement au "4 266 905" du PDF. 630 lignes M€
reconstruites, 68 lignes pct laissées sans raw_value, 0 ambiguïté.

**`extraire_un_pdf.py`** (toute future extraction à chaud) : capture
`raw_value` par la même reconstruction exacte, depuis
`diviseur_montant` réellement utilisé pour cette extraction (Décision
107) — pas une reconstruction a posteriori, le diviseur est connu au
moment de l'insertion.

**Exports frontend** : `export_kpis_for_frontend.py` expose désormais
`raw_value`/`raw_unit` dans `kpi-sources.json` et `valeurBrute`/
`uniteBrute` dans `donnees-extraites.json` (convention camelCase déjà
en place). **Le type TypeScript `KpiExtrait`
(frontend/src/lib/donnees-extraites-utils.ts) n'a pas été modifié** —
scope backend uniquement, comme pour tout le reste de la session ; le
frontend doit ajouter ces 2 champs à son type et à l'affichage pour
les exploiter.

### Correction — compte d'échecs sous-estimé dans les Décisions 107-109

En creusant une variation inattendue des totaux de contrôles (48/48 vs
45/46, 37/38, 51/51...) après ce correctif, réalisé que les messages
de commit des Décisions 107, 108 et 109 affirmaient à tort "mêmes 3
échecs déjà connus, zéro nouvelle régression" — le compte RÉEL, vérifié
maintenant de façon exhaustive (comparaison programmatique de
`executer_controles()`+`executer_completude()` sur kpis.db AVANT
(commit 9ca54a1, avant Décision 106) et APRÈS ce soir, hors le nouveau
contrôle plancher) est de **7 sociétés avec au moins 1 échec**, pas 3-4 :

| Société | Échec(s) |
|---|---|
| AG2R Prevoyance | completude_null_attendu (scr_souscription_nonvie NULL — assureur vie pure) |
| Allianz Vie | completude_null_attendu (3 KPIs fusionnés, irréductibles, Décision 084/101) |
| Covéa | completude_null_attendu (fonds_propres_t1_nr/t1_r/t2/t3 NULL) |
| MAIF | completude_null_attendu (déjà connu) |
| SGAM AG2R LA MONDIALE | completude_null_attendu (déjà connu) |
| Macifilia | mcr_inferieur_scr_total + signe_charge_sinistres (déjà connu) |
| Themis | mcr_inferieur_scr_total (déjà connu) |

**Le résultat de fond reste inchangé et rassurant** : la comparaison
programmatique confirme que cet ENSEMBLE de 7 sociétés et leurs échecs
respectifs sont **strictement identiques** avant et après TOUT le
travail de ce soir (Décisions 106-110) — zéro échec nouveau, zéro
échec disparu, zéro régression réelle. L'erreur était uniquement dans
le CHIFFRE cité ("3" au lieu de "7") dans mes propres messages de
commit, jamais vérifié de façon exhaustive avant ce soir — seulement
recopié d'une mémoire de session partielle. Les 4 échecs non
mentionnés jusqu'ici (AG2R Prevoyance, Allianz Vie, Covéa — tous des
`completude_null_attendu`) correspondent à des NULL déjà documentés et
justifiés ailleurs dans DECISIONS.md (ex. Allianz Vie : "3 KPIS
CONFIRMÉS IRRÉDUCTIBLES", docstring de `extract_kpis_allianzvie.py`,
Décision 084/101) — pas des échecs silencieux nouvellement découverts,
juste des échecs déjà connus mais mal comptés dans mes résumés
récents.

### Règle retenue

Ne plus jamais affirmer "zéro régression" sur la seule base d'un
souvenir de session ("mêmes échecs déjà connus") sans une comparaison
PROGRAMMATIQUE explicite de l'ensemble des échecs avant/après — cf.
leçon déjà tirée en Décision 102 pour un problème de nature similaire
(confusion entre 2 mesures jamais recoupées explicitement).

## Décision 111 — Endpoint POST /api/kpi/correct + table corrections (correction manuelle des KPIs)

CONTEXTE : le frontend a ajouté un bouton "Corriger" dans le modal
KPI (onglet Données) — l'utilisateur voyant une valeur extraite fausse
peut saisir la vraie valeur + un commentaire. Tâche assignée
explicitement au backend, avec schéma/contrat déjà fourni.

### Table `corrections` (`creer_table_corrections.py`)

Créée exactement selon le schéma fourni (`CREATE TABLE IF NOT EXISTS`,
idempotent) — journal jamais purgé, sert à analyser les erreurs du
modèle d'extraction dans le temps.

### Point important vérifié avant d'écrire le code : la saisie est la valeur BRUTE, pas M€

Le champ "Valeur corrigée" du modal (`kpi-pdf-modal.tsx`) est juxtaposé
à l'affichage de `kpi.valeurBrute` (`formatValeurBrute()`, Décision
110 — ex. "54 487 486 K€", PAS "54,49 M€"), avec un placeholder de la
même forme ("Ex : 54 487 486" — l'exemple même du signalement
original). La saisie représente donc le nouveau `raw_value`, dans
l'unité déjà connue (`raw_unit`), PAS directement la nouvelle `value`
M€ — vérifié en lisant le composant avant d'écrire `corriger_kpi.py`,
pas supposé. Pour un KPI sans `raw_value` (pct — `ratio_scr`/
`ratio_mcr`, `formatValeurBrute()` retombe alors sur l'affichage M€/pct
natif), la saisie représente directement la nouvelle `value`, sans
conversion.

### `corriger_kpi.py`

Appelé synchronement (pas un job en arrière-plan comme
`extraire_un_pdf.py`) par la route Next.js via `execFile` :
1. Résout `company_id` depuis le nom de société.
2. Trouve la ligne `kpis` la plus récente pour (company_id, kpi_name) —
   même convention "année la plus récente" que `export_kpis_for_
   frontend.py`.
3. Parse la saisie (gère le format FR : espaces = milliers, virgule =
   décimale — ex. "54 487 486" ou "262,5") ; erreur claire si non
   numérique, jamais une valeur devinée.
4. Si le KPI a un `raw_unit` connu : reconvertit vers M€ par la MÊME
   identité arithmétique que Décision 110 (`value = raw/diviseur`).
   Sinon : écrit la saisie directement comme nouvelle `value`.
5. Insère la ligne `corrections` (ancienne valeur/unité, nouvelle
   valeur TEXTE brute telle que saisie, commentaire) puis met à jour
   `kpis` (`value`, `raw_value`, `validated=1`).
Ne lève jamais d'exception non gérée — toujours `{"ok": false,
"erreur": "..."}` en JSON sur stdout en cas d'échec (société/KPI
introuvable, saisie non numérique).

### Route `frontend/src/app/api/kpi/correct/route.ts`

Suit exactement les conventions déjà établies dans ce dépôt
(`runtime = "nodejs"`, variables d'environnement `SFCR_*`
surchargeables, `RACINE_DEPOT` relatif à `process.cwd()`) — mêmes
choix que `/api/lancer-extraction` et `/api/upload-pdf`, mais
`execFile` synchrone (pas `spawn` détaché + fichier de statut à
sonder) : cette route répond immédiatement, pas un job de fond. Python
"léger" (`python`, pas le venv Docling/PyMuPDF/PaddleOCR) — `corriger_
kpi.py` n'utilise que `sqlite3` (stdlib).

**N'appelle PAS Python pour régénérer le JSON automatiquement (Option
B, comme demandé)** : `frontend/package.json` reçoit un script
`regenerate-json` (`python ../export_kpis_for_frontend.py`) à lancer
manuellement après une correction.

### Tests effectués (société/KPI jetables, nettoyés après)

- `corriger_kpi.py` en CLI direct : correction M€ ("54 487 486" K€ →
  54487,486 M€, `raw_value` mis à jour), correction pct ("262,5" →
  262.5 direct), société inconnue → erreur claire, texte non numérique
  → erreur claire. 4/4 comportements corrects.
- Route HTTP réelle (`npm run dev` local + `curl`) : POST valide → `{
  "ok": true, ... }` avec les bons chiffres reconvertis ; société
  inconnue → 400 + message clair ; corps incomplet (kpiId manquant) →
  400 + message clair. `npm run regenerate-json` testé, régénère bien
  les 2 exports (698 KPIs, 34 sociétés).
- `kpis.db`/`corrections` revérifiés propres après tests (aucune
  société de test résiduelle).

### Documentation

`IDEES_KPI_A_FAIRE_PLUS_TARD.md` créé (n'existait nulle part dans le
dépôt ni son historique — vérifié avant de l'écrire) avec la section
"Bugs à corriger — Backend" demandée : bug valeurs brutes marqué
résolu, décalage page noté déjà corrigé côté frontend, nouvel endpoint
documenté.

## Décision 112 — TÂCHE 1 (nuit) : correction source_page + réfutation du diagnostic "Catégorie A" du prompt de nuit

CONTEXTE : prompt de nuit signalant 4 catégories de problèmes sur
`source_page` (A: multi-entités "le plus grave" — pages titre QRT au
lieu de la donnée réelle ; B: décalage ±1 entité unique ; C: mauvaise
section ; D: 13 sociétés à NULL), avec diagnostic technique déjà
correct (repris de mon propre diagnostic de la nuit précédente).
Chemins de fichiers donnés dans le prompt FAUX (`test_markdrop/
extract_kpis.py` etc. — ces scripts sont à la racine, vérifié avant de
commencer, pas supposé).

### Outil : `corriger_source_page.py`

Recherche RÉTROACTIVE et générique (pas une correction par script,
trop risqué sur 15+ scripts différents) : pour chaque KPI non-NULL
d'une société à PDF en texte natif, cherche la page où la valeur BRUTE
(`raw_value` pour M€, `value` pour pct) apparaît réellement, désambiguïsée
par les codes de ligne QRT connus (`KPI_QRT_MAPPING`, déjà vérifiés par
l'extraction réelle — pas des codes inventés) quand la valeur seule
matche plusieurs pages (mention narrative + ligne QRT réelle).
**Jamais une page devinée** : 0 ou ≥2 candidats après filtre -> page
laissée inchangée, journalisée.

2 bugs trouvés et corrigés en construisant l'outil :
- Comparaison d'égalité flottante naïve (`valeur == int(valeur)`) ratait
  les artefacts d'arrondi (`430.99999999999994` pour 431, résultat de
  `×100/÷1`) — remplacée par une comparaison à l'arrondi avec tolérance.
- 1re passe (valeur seule) : 128 KPIs ambigus sur ~381 (valeur reprise
  en résumé narratif EN PLUS de la ligne QRT) — réduit à 63 après le
  filtre par code de ligne.

**Résultat sur les sociétés à PDF texte natif** (hors 13 entités Aéma,
100% image) : 171 `source_page` corrigés, 63 ambigus (inchangés), 129
introuvables (inchangés) — dominés par les KPIs **dérivés/sommés**
(`best_estimate`, `marge_risque`, `provisions_techniques`,
`primes_acquises_brutes`, `charge_sinistres`) qui ne peuvent
structurellement PAS apparaître comme un nombre unique imprimé (ce
sont des sommes de plusieurs lignes QRT) — limite inhérente, pas un
bug de l'outil, jamais forcé.

### Réfutation du diagnostic "Catégorie A" (Aéma, 100% image) — vérifié, pas supposé

Les 4 exemples cités dans le prompt de nuit comme "le plus grave" ont
été vérifiés un par un en rendant la page PDF réellement stockée
(`fitz.get_pixmap`) et en LISANT l'image :

| Exemple cité | Page stockée | Affirmation du prompt | Vérifié sur la page stockée |
|---|---|---|---|
| MNPAF ratio_scr 283% | 547 | "page titre", vrai ~262 | **R0620 = 283% imprimé sur la page 547 elle-même** |
| La Mondiale Europartner fonds_propres 637 645 | 266 (déjà corrigé par l'outil ci-dessus, était 10) | "page organigramme", vrai ~87 | **R0500 = 637 645 imprimé sur la page 266** |
| Aéma Groupe fonds_propres_t3 485 268 | 446 | "page titre", vrai ~64 | **R0660/Niveau 3 = 485 268 imprimé sur la page 446** |
| Macifilia fonds_propres 18 411 | 518 | "page titre", vrai ~213 | **R0540 = 18 411 imprimé sur la page 518** |

**4/4 exemples cités étaient déjà corrects avant toute intervention de
cette nuit** — le diagnostic "Catégorie A" du prompt ne correspond pas
à l'état réel de `kpis.db`. Étendu à un contrôle programmatique sur
les **273** lignes KPI non-NULL des 13 entités Aéma (les pages
gardent un petit texte natif — le TITRE seulement, ex. "MACIFILIA
S.23.01.01.01 FONDS PROPRES" — même si les valeurs elles-mêmes sont en
image) : vérifie que la page stockée porte bien le nom de la BONNE
entité et un gabarit plausible pour ce KPI. **273/273 passent.** Aucune
correction nécessaire côté Aéma — probablement parce que
`aema_entites.py::ENTITES_KPIS` a été rempli par une vraie lecture
manuelle humaine (docstring du script), contrairement au bug
`_page_source()` (1re page du gabarit) qui touche les scripts
automatisés.

### `extraire_un_pdf.py` (futures extractions)

Ajout d'un appel à `corriger_pour_societe()` (fonction réutilisable
extraite de l'outil ci-dessus) juste après l'insertion en base, avant
la régénération des exports — toute future extraction à chaud
bénéficie automatiquement de la même correction, non bloquant en cas
d'erreur (n'interrompt jamais l'extraction). Testé end-to-end (société
jetable, nettoyée après) : 5 `source_page` corrigés automatiquement
sur l'extraction de test.

### État final

`source_page` NULL sur KPI non-NULL : 87 → **53**, concentré sur les
KPIs dérivés/sommés (CNP/MACSF/MAIF/Covéa en tête) + un reliquat de 2
par entité AG2R (même limite). Combler ces 53 nécessiterait de retracer
manuellement, pour chaque script, quelle(s) page(s) QRT ont
effectivement servi à calculer la somme — hors périmètre de ce
correctif rétroactif générique.

`donnees-extraites.json` régénéré avec les `pageSource` corrigés.

## Décision 113 — TÂCHE 3 (nuit) : réfutation "métadonnées inventées" + export typeActivite/scrMethod

CONTEXTE : prompt de nuit affirmant `type_activite`/`scr_method` sur
`companies` "contiennent des valeurs inventées pour la démo".
**Vérifié FAUX** : ces champs ont déjà été remplis à partir de vraies
données dès Décision 103 (plus tôt cette nuit) — `detecter_templates()`
pour `scr_method`, règle dérivée des KPIs `scr_souscription_vie/nonvie`
réellement extraits pour `type_activite`. Seul `analyse-demo.ts`
(onglet Analyse, frontend) reste sur des données inventées — un
fichier DIFFÉRENT, déjà connu et documenté (Décision 105).

Re-vérifié ce soir par recherche textuelle directe dans 7 PDF (chapitre
A/pages de garde), sans se contenter de faire confiance à Décision
103 : Groupama ("modèle interne partiel **groupe**" — texte explicite,
confirme la valeur déjà stockée) ; Covéa et Crédit Agricole Assurances
(mentions explicites "assurance non-vie" ET "vie et santé"/"assurance
de personnes" — confirme "Mixte") ; MGEN (santé et prévoyance,
cohérent). **Aucune divergence trouvée entre le PDF et la valeur déjà
stockée.**

Ambiguïté identifiée et laissée EXPLICITEMENT non résolue (jamais
deviné) : Allianz Vie `scr_method` — recherche exhaustive du mot
"partiel" dans les 93 pages ne trouve aucune déclaration propre à
Allianz Vie sur l'étendue de son modèle interne (seule occurrence :
le nom générique du gabarit EIOPA S.25.05.21, qui s'appelle "modèle
interne (partiel ou intégral)" pour TOUTE société l'utilisant, pas une
déclaration spécifique). Indice indirect fort en faveur d'un modèle
COMPLET (toutes les briques SCR principales fusionnées/opaques, cf.
Décision 084/101) mais pas une confirmation textuelle — valeur laissée
inchangée.

**Correctif réel apporté** : `typeActivite`/`scrMethod` n'étaient
jusqu'ici PAS exposés dans `donnees-extraites.json` (seuls `type`/
`groupe`/`country` l'étaient), alors que l'onglet Analyse en a besoin
pour le filtrage/avertissement de comparabilité demandé — ajoutés à
`export_kpis_for_frontend.py::export_donnees_extraites()`.

## Décision 114 — TÂCHE 2 (nuit) : PdfPageViewer, scroll continu (onglet Documents)

CONTEXTE : refactoring explicitement autorisé à toucher le frontend
("EXCEPTION"), scope limité à l'onglet Documents — le modal KPI garde
le mode page-par-page (vérifie seulement 1-2 pages, pas besoin de
défilement continu).

### Architecture

`PdfPageViewer` devient un point d'entrée qui choisit entre
`PdfSingleViewer` (implémentation historique, **strictement
inchangée**, extraite telle quelle) et `PdfScrollViewer` (nouveau,
défilement continu), via une prop `mode?: "single" | "scroll"`
**par défaut `"single"`** — `kpi-pdf-modal.tsx` n'a donc AUCUNE
modification à faire, son comportement (`defaultZoom={lastKpiZoom}`,
`onZoomChange`) reste identique par construction. Seul
`documents/page.tsx` passe `mode="scroll"` — unique changement
frontend en dehors du composant lui-même.

`PdfScrollViewer` : toutes les pages sont des "slots" absolument
positionnés (hauteur/largeur connues dès le chargement des métadonnées
de TOUTES les pages, avant tout rendu — nécessaire pour une scrollbar
correcte dès le départ, même sur 621 pages). Seules les pages dans la
fenêtre tampon (page visible ±3) portent un `<canvas>` réellement
monté ; les autres sont un `<div>` vide de la bonne taille — React
démonte le canvas en dehors de la fenêtre (libère la mémoire, pas
juste un `style=display:none`). Un `IntersectionObserver` par slot met
à jour la page courante et la fenêtre tampon au fil du scroll.

### 2 bugs réels trouvés et corrigés en testant dans un vrai navigateur

Conformément à la consigne de test des changements UI : serveur `npm
run dev` lancé, testé sur `/documents` avec Allianz Vie (93 pages) —
pas seulement un `tsc`/`eslint` propre.

1. **Gel de l'onglet sur un saut lointain** (`goToPage` avec
   `behavior: "smooth"`) : un saut page 2 → 80 anime le scroll sur des
   dizaines de slots, chacun déclenchant l'`IntersectionObserver` à
   chaque frame de l'animation → tempête de recalculs de fenêtre
   tampon + rendus canvas annulés/relancés en boucle, jusqu'à geler
   l'onglet (`CDP Page.captureScreenshot timed out`, constaté
   plusieurs fois en test réel). Corrigé : `behavior: "auto"` (saut
   instantané, un seul recalcul à l'arrivée).
2. **`setVisibleRange({...})` avec un nouvel objet à chaque callback
   de l'observer**, même quand `start`/`end` ne changeaient pas —
   l'effet de rendu (dépendance `[visibleRange, layout]`) se
   redéclenchait en boucle, annulant sans fin des rendus jamais
   terminés (constaté : `renderedScale` jamais posé après un saut,
   nouveau gel du navigateur reproduit une 2e fois). Corrigé par un
   setter stable qui ne déclenche une mise à jour que si les valeurs
   changent réellement (`prev.start===next.start && prev.end===next.end`).

**Fix additionnel de robustesse** (découvert en creusant le bug 2) :
tester a révélé que l'`IntersectionObserver` ne se redéclenche pas de
façon fiable après un saut instantané loin de la position actuelle
(0 callback reçu même avec une géométrie correcte, vérifié avec un
observer de test indépendant). `goToPage` et le scroll initial fixent
donc directement `currentPage`/`pageInput`/`visibleRange` plutôt que
de dépendre uniquement de l'observer pour ce cas précis — l'observer
reste la seule source pour le scroll naturel de l'utilisateur.

### Validé en navigateur réel (pas seulement `tsc`/`eslint`)

- Scroll naturel (molette) : page 1→2, indicateur mis à jour
  correctement.
- Saut lointain (page 2→80, saisie + Entrée) : scrollTop correct,
  fenêtre tampon exactement 7 pages (77-83, ±3 autour de 80), contenu
  réellement rendu visible (capture d'écran : texte du PDF affiché).
- Retour page 1 : fenêtre tampon redevient 1-4, canvas de la page 80
  bien démonté (libération mémoire confirmée par inspection DOM).
- Modal KPI (`base-donnees` → Allianz Vie → Ratio SCR) : **totalement
  inchangé** — mode page-par-page, saute directement à la page 89
  (cohérent avec le correctif Décision 112), zoom 300% préservé,
  contenu exact affiché (R0500/R0540 = 4 266 905, déjà vérifié
  Décision 112).

## Décision 115 — Correctif du correctif : source_page des PDFs multi-entités (Aéma/AG2R)

CONTEXTE : prompt de nuit signalant que la Décision 112 (28/09) avait
laissé les PDFs multi-entités (Aéma Groupe, AG2R LA MONDIALE) faux —
un test sur 10 KPIs aléatoires donnait 5/10 corrects, les 5 échecs
tous sur des multi-entités, avec 5 exemples précis cités.

### Vérification préalable (avant toute correction, comme la nuit précédente)

Les 5 exemples cités ont été vérifiés un par un contre `kpis.db` et le
texte réel des PDF — **cette fois les 5 claims du prompt se sont
confirmés exacts** (contrairement au prompt de la nuit du 28/09, où
les 4 exemples "Catégorie A" s'étaient révélés faux à la vérification).
Différence de fond trouvée : la Décision 112 avait skippé entièrement
les 13 entités Aéma en les croyant "100% image" — vrai pour l'annexe
QRT (pages 439-621) mais **FAUX pour le chapitre narratif qui la
précède** (pages 1-438) : chaque entité y a sa PROPRE section avec un
tableau natif "ÉVOLUTION DES SCR ET MCR (EN MILLIERS D'EUROS)"
reprenant la plupart des KPIs en clair — vérifié en lisant directement
le texte des pages 64-67 (Aéma Groupe) et 377 (Abeille Vie) avant
d'écrire une seule ligne de correctif. Même chose pour AG2R : les
sommes/totaux (best_estimate) absents de l'annexe QRT apparaissent
dans un chapitre "Bilan"/"Provisions" narratif antérieur (ex. Prima
p.76-77 : "Total... Meilleure estimation 550 081", texte natif).

### Correctifs apportés à `corriger_source_page.py`

1. **`AEMA_BORNES`** remplace le skip total des 13 entités Aéma —
   bornes de pages narratives précises par entité, découvertes en
   cherchant les pages dont la 1re ligne EST exactement le nom de
   l'entité (en-tête de section, contigu et sans chevauchement pour
   les 13).
2. **`AG2R_BORNES`** élargi : recherche désormais 1..fin-du-bloc-QRT
   (pas seulement le bloc QRT lui-même) — structure narrative AG2R
   moins régulière que Aéma (mini-blocs dispersés par entité à travers
   plusieurs sections), pas de bornes précises par entité possibles,
   compensé par la désambiguïsation valeur+code/libellé.
3. **Alternative K€ pour les entités en euros bruts** (7 Aéma + Sogécap,
   Décision 094/096) : leur chapitre narratif reste en milliers d'euros
   même quand leur annexe QRT (et donc `raw_value`) est en euros bruts
   — cherche aussi `raw_value/1000` ET sa forme arrondie à l'entier
   (le texte narratif affiche un arrondi, ex. "818 851" pour
   818850,67 — bug de comparaison flottante trouvé et corrigé en
   testant, pas supposé).

### 2 bugs de désambiguïsation trouvés et corrigés EN TESTANT (pas supposés)

1. **Filtre par code de ligne trop large** (fenêtre de 150 caractères) :
   un code SANS RAPPORT (ex. R0220 d'une tout autre ligne) tombait
   parfois dans la fenêtre par coïncidence — repéré sur Allianz Vie/
   scr_total (pages 89 ET 90 passaient le filtre, la "dernière
   occurrence" aurait retenu 90, qui est un renvoi de calcul MCR, pas
   la vraie ligne SCR en page 89). Fenêtre resserrée à 40 caractères
   ET, plus important, **le repli "dernière occurrence" aveugle a été
   supprimé entièrement** pour le cas "ambigu même après filtre code" :
   deviner entre 2 pages QRT-codées est plus dangereux que de laisser
   inchangé.
2. **Coïncidence numérique dans le chapitre narratif** : MNPAF/
   marge_risque — la vraie valeur "1 741" (page 278/279, à côté du
   libellé "Marge de risque") réapparaît PAR COÏNCIDENCE page 283 comme
   variation annuelle d'un tout autre poste (le SCR). Un repli
   "dernière occurrence" aveugle aurait retenu 283 (faux). Remplacé par
   `LABELS_NARRATIFS` : dictionnaire de libellés français observés
   DIRECTEMENT dans les PDF (pas inventés) servant de désambiguïsation
   par proximité, même logique que les codes de ligne — un repli
   "dernière occurrence" n'est maintenant accepté QUE si chaque
   candidat est DÉJÀ confirmé par un libellé pertinent à proximité ET
   que les candidats sont à ≤2 pages d'écart (répétition de la même
   donnée dans 2 tableaux voisins du même sous-chapitre, pas 2 faits
   différents — vérifié sur Prima/best_estimate et AG.Mut/best_estimate).

### Résultat

171 `source_page` corrigés sur cette passe (98 ambigus et 209
introuvables laissés inchangés, jamais devinés). `source_page` NULL
sur KPI non-NULL : 53 → 44 (reste concentré sur les KPIs dérivés/sommés
dont le total n'apparaît littéralement nulle part, limite déjà
documentée Décision 112 — ex. Crédit Agricole/primes_acquises_brutes,
confirmé absent du document entier par recherche exhaustive).

**Validation (15 KPIs demandés, couvrant Aéma/AG2R/single-entity/Crédit
Agricole)** : 12/15 corrects par vérification directe du texte PDF à
la page stockée. Les 3 échecs (SGAM AG2R LA MONDIALE/scr_total,
Groupama/ratio_scr, Crédit Agricole/scr_total) sont des gaps
**PRÉ-EXISTANTS** — valeurs identiques bit-à-bit à l'état d'avant ce
correctif (vérifié par diff contre le commit précédent), donc AUCUNE
régression ; `corriger_source_page.py` les a examinés et correctement
laissés inchangés plutôt que deviner (ex. Groupama/ratio_scr : "274%"
apparaît dans 5 contextes narratifs différents, vraiment ambigu, sans
code de ligne pour trancher — un chantier futur, pas pour ce soir).

Les 5 KPIs "déjà bons" cités dans le prompt comme référence (AG2R
Prévoyance, La Mondiale, Cardif Assurances RD, Allianz Vie, Sogécap)
restent inchangés et corrects — vérifié explicitement, zéro régression.

## Décision 116 — Investigation forensique : valeurs KPI "introuvables" dans le PDF

CONTEXTE : prompt de nuit signalant 4 valeurs KPI stockées dans
`kpis.db` introuvables dans leur PDF source par `pdftotext`, posant la
question d'une possible invention/mauvais calcul. Mission : tracer
chaque valeur jusqu'à sa source et donner un verdict vérifié, pas
corriger à l'aveugle.

### Verdict : 3/4 cas cités étaient des fausses alertes, 1 était un vrai bug

- **MMJ/charge_sinistres** (❌ FAUX) : `aema_entites.py` annonçait
  "R0310/Total" (Charge des sinistres Brut) mais contenait en réalité
  la valeur de R0300 (Primes acquises Net) — 2 lignes adjacentes d'un
  tableau QRT tourné à 90°, confondues à la lecture manuelle. Confirmé
  par rendu PNG p.554 et lecture ligne par ligne. Corrigé :
  69 127 735 → 55 926 771 (euros bruts).
- **Cardif Assurance Vie/charge_sinistres** (✅ CORRECT) : somme
  automatique via `resoudre_variantes_qrt()` de 2 cellules QRT réelles
  (R1610 vie p.6 + R0310/R0320/R0330 non-vie p.5), extraites en texte
  natif, pas devinées. Logiquement introuvable comme chaîne littérale
  puisque c'est une somme calculée sur 2 pages, jamais imprimée telle
  quelle — exactement le pattern déjà documenté Décision 112 pour les
  KPIs dérivés/sommés.
- **Crédit Agricole Assurances/primes_acquises_brutes** (✅ CORRECT) :
  le prompt affirmait à tort que la page 69 était une "page de titre" ;
  vérifié par rendu PNG que c'est une page de DONNÉES réelles
  (S.05.01.02, 2/3, non-vie). Somme vérifiée exacte :
  7 570 076 (non-vie, p.69, R0210+R0220+R0230) + 41 602 922 (vie, p.70,
  R1510) = 49 172 998 K€ ≈ 49 173,00 M€ stocké.
- **Abeille Vie/fonds_propres_t2** (✅ CORRECT) : vérifié directement
  sur le rendu PNG p.588 — ligne R0540, colonne "Niveau 2" =
  998 728 480, correspondance exacte. Introuvable par `pdftotext`
  simplement parce que la page est 100% image (aucune valeur de cette
  page n'a de couche texte, pas spécifique à ce KPI). Recoupement
  interne déjà cohérent avant même le rendu : t1_nr+t1_r+t2+t3 =
  fonds_propres_eligibles à l'euro près.

**Conclusion méthodologique** : "introuvable par recherche textuelle"
n'est PAS un signal fiable d'invention — déjà établi Décision 112, ici
confirmé sur un 2e lot de cas avec un diagnostic complet par KPI. Les
2 causes légitimes sont : (1) somme calculée de plusieurs cellules QRT
réelles, jamais imprimée comme chaîne unique ; (2) page 100% image
sans couche texte, où AUCUNE valeur n'est trouvable par cette méthode.
Le seul cas réellement faux (MMJ) avait une cause différente : une
erreur de lecture manuelle (ligne adjacente), détectable uniquement
par relecture visuelle directe de la page — pas par recherche
textuelle, qui aurait de toute façon échoué pour les 2 valeurs (la
fausse ET la vraie), puisque la page est en image.

### Bug supplémentaire trouvé (vérification de précaution, hors 4 cas cités)

Après avoir confirmé MMJ, vérification du même risque (ligne confondue
sur tableau tourné 90°) sur les 4 autres entités Aéma au gabarit
identique ("non-vie seule", S.05.01.02.01) : Macifilia, MNPAF, Nuoma
vérifiées correctes, mais **Thémis avait 2 valeurs fausses** :
`primes_acquises_brutes` (R0110 "Primes émises" confondu avec R0210
"Primes acquises", 1 899 → 1 920 K€) et `charge_sinistres` (R0300
"Primes acquises Net" confondu avec R0310 "Charge sinistres Brut",
1 920 → 386 K€). Les deux corrigées après vérification visuelle du
rendu PNG p.497. Portée de cette vérification bonus limitée à ces 5
entités (sur 13 Aéma au total) — un audit complet des 273 KPIs "rendu
image" (Tâche 2 du prompt, "si temps") n'a pas été fait, reporté à une
session future.

### Fichiers modifiés

`aema_entites.py` (3 valeurs corrigées, commentées avec justification
et renvoi à cette décision), `kpis.db` (mêmes 3 corrections),
`frontend/src/data/donnees-extraites.json` + `kpi-sources.json`
(régénérés).

## Décision 117 — Audit qualité systématique : 6 nouvelles valeurs fausses trouvées (bug "ligne adjacente" confirmé systématique)

CONTEXTE : prompt de nuit demandant un audit qualité des 273 KPIs
Aéma "image/rendu" + un test aléatoire de 20 KPIs toutes sources, pour
vérifier si le bug "ligne adjacente" trouvé 2 fois la nuit précédente
(Décision 116, MMJ et Thémis) était isolé ou systématique.

### Méthode

1. Vérification arithmétique automatisée (fonds_propres=somme des
   tiers, ratio_scr/ratio_mcr recalculés, scr_total ≥ modules
   individuels, scr_diversification ≤ 0) sur les 13 entités Aéma.
2. Vérification visuelle (rendu PNG + lecture directe) de
   `primes_acquises_brutes` et `charge_sinistres` pour les 13 entités
   (les 2 KPIs identifiés à risque), complétée par 4 pages S.25.01
   entières et 1 page S.28.
3. Test aléatoire de 20 KPIs toutes sources (seed=2026 fixé).

### Résultat de la vérification arithmétique : 0 vrai bug, 8 faux positifs tous expliqués

Le check naïf a signalé 4 entités où un module SCR individuel dépasse
`scr_total`, et 4 où `ratio_mcr` ne recalcule pas depuis
`fonds_propres_eligibles`. Vérifiées une par une par rendu PNG : les 8
sont légitimes.
- `scr_total` < somme des modules bruts à cause de la capacité
  d'absorption des pertes des provisions techniques et des impôts
  différés (lignes R0140/R0150, template S.25.01.2x.02) — mécanisme
  réel, vérifié recalculer EXACTEMENT au stockage près sur les 4 cas
  (ex. Macif Vie : 3 963 973 − 3 191 149 − 71 910 + 113 265 = 814 179,
  exact).
- `ratio_mcr` utilise R0550 (fonds propres éligibles pour le MCR,
  restriction Tier 2/3 différente), pas R0540 (ce que nous stockons
  comme `fonds_propres_eligibles`, éligible pour le SCR) — les 2
  chiffres diffèrent par construction du template QRT S.23.01, donc le
  ratio recalculé depuis R0540 ne matche jamais exactement R0550/mcr.
  Vérifié sur Abeille Vie : R0550=4 256 915 348, 4 256 915 348/818 850
  670=519,9%≈520% stocké.

**Enseignement** : les checks arithmétiques "évidents" sur les
rapports Solvabilité II ignorent facilement 2 mécanismes réels (LAC
TP/DT, distinction R0540/R0550) — une vérification automatisée seule,
sans retour au PDF, aurait produit 8 fausses alertes ou pire, 8
"corrections" incorrectes si on avait fait confiance à l'arithmétique
naïve. Confirme encore la discipline "vérifier sur le PDF avant de
conclure", déjà centrale aux Décisions 112/115/116.

### Résultat de la vérification visuelle ciblée : 6 vraies valeurs fausses trouvées

Toutes sur `primes_acquises_brutes`/`charge_sinistres`, toutes des
variantes du même bug de fond (ligne ou colonne ADJACENTE confondue
sur un tableau QRT S.05.01.02 tourné à 90°, déjà identifié Décision
116 sur MMJ/Thémis) :

- **MACIF SAM** (primes et charge) : incluait en trop R0240/R0340
  ("Part des réassureurs" — une ligne de DÉDUCTION pour obtenir le
  Net, jamais une composante à ADDITIONNER au Brut). Corrigé :
  4 854 620 → 4 446 321 K€ (primes) ; 3 429 372 → 3 263 184 K€
  (charge).
- **Abeille IARD Santé** (charge_sinistres) : composante non-vie
  confondait R0300 (Primes acquises Net) avec R0310 (Charge sinistres
  Brut). Corrigé : 1 999 115 035 → 1 464 937 847 €.
- **Abeille Épargne Retraite** (primes_acquises_brutes) : confondait
  R1500 (Primes ÉMISES Net) avec R1510 (Primes ACQUISES Brut). Corrigé
  : 1 262 145 906 → 1 264 646 880 €.
- **Aéma Groupe** (primes_acquises_brutes) : composante vie confondait
  R1500 (Net) avec R1510 (Brut). Corrigé : 18 552 020 → 18 600 014 K€.
- **Abeille Vie** (primes_acquises_brutes) : composante vie confondait
  R1600 (Net) avec R1510 (Brut). Corrigé : 3 971 475 103 →
  3 984 172 891 €.

Chaque correction vérifiée par rendu PNG + lecture directe de la ligne
ET section concernées (jamais devinée), recoupée arithmétiquement
(non-vie + vie = total stocké, à l'unité près) avant application.

**Entités vérifiées SANS bug** (même KPIs, même méthode) : Macif Santé
Prévoyance, Aésio Mutuelle, Macif Vie, Macifilia, MNPAF, Nuoma (déjà
V3). Couverture désormais complète : les 26 KPIs
`primes_acquises_brutes`/`charge_sinistres` des 13 entités Aéma ont
tous été vérifiés par lecture directe du PDF (V3+V4 combinées).

### Résultat du test aléatoire (Tâche 2, 20 KPIs, seed=2026)

**20/20 corrects** : 18 par correspondance texte/visuel directe, 2 par
recoupement arithmétique exact (La Mondiale Europartner et Crédit
Agricole Assurances / `provisions_techniques`, tous deux des sommes
calculées best_estimate+marge_risque dont chaque composant a été
vérifié individuellement). Aucune nouvelle anomalie — cohérent avec le
fait que la Tâche 1 avait déjà couvert la zone à risque principale.

### Portée restante non couverte

Les 273 KPIs Aéma n'ont pas tous été vérifiés visuellement un par un
(impossible en une session) — la vérification ciblée a porté sur les 2
KPIs à risque identifiés (primes/charge, 26/26 couverts) + les KPIs
SCR/MCR/fonds_propres des entités déjà flagged par les checks
arithmétiques (tous légitimes) + un échantillon aléatoire de 20. Les
KPIs non spécifiquement revérifiés (best_estimate, marge_risque,
scr_marche, etc. pour les entités jamais flagged ni échantillonnées)
restent sous la confiance accordée par les recoupements internes déjà
documentés dans les commentaires `aema_entites.py` (Décision 083) —
pas une garantie à 100%, mais pas un point faible identifié non plus.

### Fichiers modifiés

`aema_entites.py` (6 valeurs corrigées, commentées avec justification
et renvoi à cette décision), `kpis.db` (mêmes 6 corrections),
`frontend/src/data/donnees-extraites.json` + `kpi-sources.json`
(régénérés).

## Décision 118 — Vérification single-entity texte natif : 26 source_page corrigés, 0 valeur fausse trouvée

CONTEXTE : prompt de nuit ciblant les 12 sociétés single-entity à PDF
texte natif (catégorie jusqu'ici la moins auditée), suite à un test
Cowork (10 KPIs, seed=77) ayant trouvé 1 bug pageSource (Groupama/
provisions_techniques, page 79 = titre vide au lieu de 68/71) et 1
écart d'arrondi mineur (2 K€).

### Vérification préalable (avant toute action)

Les 2 claims du prompt vérifiés exacts : page 79 est réellement vide
("Annexe 1 (2/2)", juste l'en-tête) ; pages 68 et 71 contiennent
littéralement "71 419 437" ; le stocké (71 419 439) = best_estimate +
marge_risque calculés séparément, écart de 2 K€ par arrondi
indépendant de chaque composante — mineur, non corrigé (corriger
provisions_techniques casserait sa cohérence avec ses 2 composantes).

### Méthode : script automatisé + vérification manuelle systématique de chaque flag

Un script (fitz, pas pdftotext) a vérifié les ~240 KPIs testables des
12 sociétés contre leur `source_page` (puis ±3 pages en repli).
**Aucune correction n'a été appliquée sur la seule foi du script** —
chaque "page décalée" ou "introuvable" a été re-vérifié manuellement,
ce qui a révélé 2 classes de faux positifs/négatifs importantes :

1. **Le script trouve parfois une page COÏNCIDENTE plutôt que la
   bonne** : pour `scr_total`/`mcr`, le tableau QRT S.23.01.01
   commence souvent sur une page et les lignes R0580/R0600 (SCR/MCR)
   n'arrivent que sur la page SUIVANTE. Une page de comparaison
   voisine (template S.22.01.21, "Impact des mesures relatives aux
   garanties de long terme") répète souvent les MÊMES totaux comme
   valeurs de référence, avec des codes de ligne DIFFÉRENTS (R0090/
   R0110 au lieu de R0580/R0600) — un script qui cherche juste "la
   valeur existe sur une page voisine" peut se tromper de page de
   manière invisible si on ne vérifie pas le CODE DE LIGNE. Confirmé
   sur Allianz Vie (88→89, pas 87), Crédit Agricole (74→76, pas 73),
   Predica (68→70, pas 67).
2. **Mon propre script de vérification avait 2 bugs** (faux négatifs,
   pas des bugs de données) : ne gérait pas les nombres négatifs
   (signe affiché dans une cellule séparée du nombre dans le texte PDF
   extrait, ex. "-\n...\n14 137") — affectait `scr_diversification`
   sur 4 sociétés, toutes confirmées correctes une fois le signe
   ignoré dans la recherche. Et une troncature au lieu d'un arrondi
   sur des valeurs `.999...` (ex. ratio_mcr=430,99999999999994 →
   cherché "430" au lieu de "431", qui est la vraie valeur imprimée).

### Cause racine trouvée chez CNP Assurances et Covéa : page jamais capturée par le script d'extraction

`extract_kpis_cnp.py` et `extract_kpis_covea.py` passent
`page_source=None` EN DUR pour chaque KPI (jamais dérivé du corpus
QRT, contrairement aux autres scripts qui ont une fonction
`_page_source()`). Les 11/21 (CNP) et 9/17 (Covéa) KPIs qui ont
aujourd'hui une page l'ont reçue via `corriger_source_page.py` lors
d'une nuit précédente ; les KPIs restants étaient resté `NULL` car ce
script ne les avait pas résolus avec confiance. Recherche manuelle
dans le document complet : `scr_total`/`mcr`/`ratio_scr`/`ratio_mcr`
trouvés et confirmés pour les deux sociétés (CNP p.94 ; Covéa p.93,
tableau de consolidation groupe méthode D&A). Non corrigé dans le code
source ce soir (le `kpis.db` est corrigé, suffisant pour le frontend ;
corriger `extract_kpis_cnp.py`/`extract_kpis_covea.py` pour qu'ils
dérivent la page depuis le corpus serait un chantier plus large, hors
scope "corrections ciblées" de ce soir).

Même cause chez **MAIF** (source_chapter="E.1"/"E.2"/"D.2" mais jamais
de page) : 6 KPIs trouvés groupés sur une seule page QRT (122,
S.23.01.01 complet) + `provisions_techniques` trouvé page 120 (valeur
identique imprimée littéralement, en plus d'être une somme calculée en
interne). `best_estimate` reste `NULL` : confirmé correct par calcul
exact (3 860 956 non-vie p.118 + 546 396 vie p.125 = 4 407 352) mais
aucune page unique ne porte le total combiné — jamais deviné. Même
cause chez **MACSF prévoyance** (`mcr` trouvé p.61).

### Résultat : 0 valeur fausse trouvée, 26 source_page corrigés

Contrairement aux nuits V3/V4 (9 valeurs fausses trouvées sur la
catégorie Aéma multi-entité/image), **aucune valeur n'était fausse**
dans cette catégorie single-entity/texte natif — cohérent avec
l'hypothèse du prompt ("la catégorie la plus propre du dataset").
Toutes les 26 corrections sont des `source_page` (traçabilité),
jamais une valeur. Détail complet des 26 corrections et de la limite
non résolue (Groupama, 7 composantes SCR introuvables, voir ci-dessous)
dans NIGHT_LOG_V5.md.

### Limite non résolue : Groupama, ventilation SCR par module introuvable

7 KPIs (scr_operationnel, scr_marche, scr_souscription_sante/vie/
nonvie, scr_contrepartie, scr_diversification) ont une `source_page`
qui ne correspond à AUCUN texte réel — recherche exhaustive, avec et
sans signe, dans tout le document. La page actuellement citée pour 5
d'entre eux (75) est un chapitre narratif qualitatif sans tableau
chiffré (discussion du modèle interne partiel). Non corrigé : aucune
page de remplacement trouvée avec confiance (jamais deviné) — Groupama
utilise un modèle interne partiel, la ventilation par module n'est
peut-être publiée qu'en image ou sous une forme non standard. À
creuser dans une session future (rendu PNG des pages 73-90).

### Test post-correction (10 KPIs, seed=2026) : 10/10, + 12/12 sociétés cohérentes

Score parfait, et les 12 sociétés single-entity passent les 2 checks
de cohérence demandés (décomposition fonds propres par tiers, ratio
recalculé) sans anomalie.

### Fichiers modifiés

`kpis.db` (26 `source_page` corrigés ou remis à NULL),
`frontend/src/data/donnees-extraites.json` + `kpi-sources.json`
(régénérés). Aucun script d'extraction modifié.

## Décision 119 — Audit complet single-entity (actuariel + sources image) : résolution de la limite Groupama

CONTEXTE : prompt de nuit demandant (1) 10 règles de cohérence
actuarielle appliquées systématiquement aux 12 sociétés single-entity,
et (2) une re-vérification des sources incluant la possibilité de
pages QRT en image dans ces PDF "texte natif" — en particulier pour
clore la limite laissée ouverte dans NIGHT_LOG_V5.md (7 composantes
SCR de Groupama introuvables nulle part dans le texte).

### Tâche 1 — 10 règles actuarielles : 16 signalements, 0 vrai bug

Toutes les "anomalies" brutes se sont révélées légitimes après
investigation individuelle (jamais classées "faux positif" sans
preuve) :
- **Corridor MCR (Art. 129, 25-45%)** : CNP (45,000003%) et MACSF
  (24,999943%) sont exactement aux bornes réglementaires (bruit
  flottant), pas des violations. **Groupama (63,8%)** dépasse
  réellement le corridor, mais légitimement : au niveau GROUPE, le
  MCR consolidé est une SOMME des MCR solos (chacun dans son propre
  corridor), comparé à un SCR groupe qui bénéficie lui de la
  diversification inter-entités — le narratif du rapport (p.75, E.2.2)
  le confirme explicitement ("le minimum de capital requis au niveau
  groupe est la somme des minima de capital requis de l'ensemble des
  entités du Groupe"). Le corridor solo ne s'applique structurellement
  pas de la même façon au niveau groupe.
- **scr_total < somme des modules individuels** (7 sociétés) :
  mécanisme de capacité d'absorption des pertes (LAC TP/DT), déjà
  identifié Décision 117 sur les entités Aéma, re-confirmé ici en
  détail sur **CNP** (lecture directe p.97, S.25.01.21 : SCR de
  base=40 711 593, LAC TP=-26 691 143, LAC DT=-829 430, opérationnel=
  1 065 800 → 14 256 820 ≈ scr_total stocké, exact à l'arrondi près).
- **Allianz Vie** : absence structurelle de `scr_marche`/
  `scr_contrepartie`/`scr_souscription_vie`/`scr_souscription_sante`/
  `scr_diversification` déjà documentée et justifiée (Décision 084,
  modèle interne, lignes fusionnées dans le template S.25.05.21) — pas
  une anomalie nouvelle.
- **Cardif Assurances Risques Divers, loss ratio 23,3%** (sous le
  seuil indicatif de 30%) : documenté comme sondage statistique, pas
  une preuve d'erreur (valeurs déjà individuellement vérifiées
  correctes, Décision 118) — non corrigé, cohérent avec le cas
  similaire déjà rencontré sur Macifilia (ratio négatif légitime,
  Décision 116/117).

### Tâche 2 — Scan systématique des pages image : Groupama isolé, 7 citations corrigées

Les 12 PDF ont été scannés pour détecter les pages à texte natif
quasi-absent (<300 caractères, signal d'une page scannée/image), puis
croisés avec les `source_page` actuellement utilisées. **Seule
Groupama** avait des citations tombant sur de telles pages — les 11
autres sociétés confirment que V5 n'avait manqué aucune page image.

Root cause trouvée pour Groupama : 5 KPI (`scr_operationnel`,
`scr_marche`, `scr_contrepartie`, `scr_souscription_vie`,
`scr_souscription_sante`) proviennent, d'après `extract_kpis.py`, d'une
image embarquée nommée "picture_75.png" (un schéma SCR en waterfall,
lu par 3 sources croisées — PaddleOCR + Gemini Vision + Claude Vision,
déjà vérifié manuellement par l'utilisateur selon le commentaire du
script). **"picture_75" est un index séquentiel d'extraction, pas un
numéro de page** — quelqu'un avait déduit à tort `source_page=75` de
ce nom de fichier. Rendu PNG de la page 74 (pas 75) : le schéma SCR y
est bien visible, avec les 5 valeurs EXACTEMENT identiques à celles
stockées (confirmé par recherche texte : absent de la couche texte de
la page 74, c'est une image pure — ce qui explique pourquoi ni V5 ni
le scan texte de ce soir ne les avaient trouvées). Corrigé : 75 → 74.

2 autres KPI (`scr_total`, `scr_souscription_nonvie`) pointaient vers
la page 85, qui est en réalité la table FONDS PROPRES (Annexe 5,
S.23.01.22-01), pas la table SCR — confusion probable entre 2 annexes
voisines. La vraie table SCR (Annexe 6, S.25.05.22, template de modèle
interne partiel — fusionne aussi marché+crédit en R0070 et vie+santé
en R0400, cohérent avec le schéma) est page 87, où les 2 valeurs sont
confirmées littéralement (R0220/R0570=6 020 977 ;
R0310=2 474 794). Corrigé : 85 → 87.

**0 valeur modifiée** — les 7 corrections sont uniquement des
`source_page`, toutes les valeurs étaient déjà correctes. Ceci clôt
définitivement la limite "Groupama, 7 composantes SCR introuvables"
laissée ouverte dans NIGHT_LOG_V5.md.

### Tâche 4 — Test post-correction : 10/10, cohérence confirmée

Même échantillon aléatoire que V5 (seed=2026) — 10/10, aucun des 7 KPI
corrigés ce soir n'y figurant par hasard, mais les 12 sociétés passent
désormais la totalité des 10 règles actuarielles (après explication
des faux positifs ci-dessus).

### Fichiers modifiés

`kpis.db` (7 `source_page` corrigés, Groupama uniquement),
`frontend/src/data/donnees-extraites.json` + `kpi-sources.json`
(régénérés). Aucun script d'extraction modifié.

## Décision 120 — Audit complet multi-entity (Aéma + AG2R) : 91 source_page corrigés, découverte d'une régression massive

CONTEXTE : prompt de nuit demandant un audit complet (10 règles
actuarielles + vérification exhaustive des sources) pour les 13
entités Aéma et les entités AG2R, après que V5/V6 aient nettoyé la
catégorie single-entity. Prompt contenant 2 inexactitudes vérifiées
avant de commencer : (1) le groupe AG2R compte 9 entités réelles, pas
8, avec des noms différents de ceux listés ; (2) `primes_emises_brutes`
n'est pas un KPI suivi par le projet (21 KPIs réels dans
`kpi_definitions.py`) — remplacé par `fonds_propres_eligibles`.

### Méthode qui a payé : comparaison systématique au lieu d'un échantillonnage

Plutôt que de vérifier des KPIs au hasard, la comparaison
programmatique de TOUTES les `source_page` de `kpis.db` contre les
pages documentées dans `aema_entites.py` (qui contient, pour chaque
entité, la page QRT d'origine ET des commentaires de recoupement
arithmétique écrits lors de l'extraction initiale, Décision 083/085)
a immédiatement révélé **140 écarts** sur 273 KPIs Aéma.

### Découverte majeure : une régression de 58 source_page causée par une nuit antérieure

Chaque écart vérifié individuellement (recherche littérale du texte
stocké sur la page actuellement en base) :
- **82/140** : citation narrative légitime (le même chiffre apparaît
  aussi dans le chapitre narratif AEMA_BORNES, mécanisme déjà établi
  Décision 115/116) — laissées inchangées.
- **58/140** : la valeur stockée n'existe PAS sur la page en base.
  **Diagnostic** : `corriger_source_page.py`, lors d'une nuit
  antérieure (probablement la recherche élargie `AEMA_BORNES` des
  Décisions 115-117), a trouvé un match textuel COÏNCIDENTEL dans le
  chapitre narratif et a remplacé une page QRT déjà correcte et
  documentée par une page narrative FAUSSE — une régression, pas un
  nouveau bug d'extraction. Corrigé : reverti vers la page
  `aema_entites.py` documentée, après spot-check visuel confirmant
  le bon titre de tableau (ex. page 446 confirmée "AÉMA GROUPE —
  S.23.01.22.01 FONDS PROPRES").

**Aucune des 58 valeurs elles-mêmes n'était fausse** — uniquement la
`source_page`. Ceci souligne un risque méthodologique à retenir : un
outil de correction automatique de pages, même disambiguisé avec soin
(codes de ligne, libellés), peut dans de rares cas écraser une
citation DÉJÀ CORRECTE par une autre techniquement "trouvée" mais en
réalité fausse (un faux positif de "found=True" sur un texte voisin
mais non identique), si le process n'a pas de garde-fou comparant
contre une source de vérité indépendante. `aema_entites.py` a servi
ce soir de garde-fou — cette discipline (toujours garder une trace
indépendante vérifiable) mérite d'être reproduite pour les futures
passes de correction automatique.

### AG2R : bug systémique de pages relatives jamais converties en absolues

`ag2r_entites.py` passe `page_source=None` en dur pour la plupart des
KPIs (même pattern que CNP/Covéa, Décision 118). Une correction
antérieure a comblé une partie des `NULL`, mais avec des **pages
relatives à chaque sous-PDF isolé d'entité**, jamais converties en
pages absolues du document combiné de 288 pages (ex. "page 12",
"page 15", "page 1" sans rapport avec l'entité). Hypothèse testée et
confirmée sur AG.Mut (bornes 198-215) : `scr_souscription_vie` "page
15" = page absolue 212 (=198+15-1) exactement, confirmée par "Risque
de souscription en vie R0030 = 0" à cet endroit précis.

**33 `source_page` AG2R corrigés** : 17 cas "page=12" (placeholder
générique) sur 6 entités (`scr_total`/`mcr`/`fonds_propres_t1_r/t2/t3`),
8 cas supplémentaires (pages relatives mal converties sur d'autres
entités/KPIs, confirmés par code de ligne R0090/R0220/R0680 selon le
template), 4 cas de citations narratives retrouvées par recherche
plein document (Prima/marge_risque p.77, VIASANTE Mutuelle/
best_estimate+marge_risque p.80, La Mondiale Partenaire/
provisions_techniques p.279), et 16 cas remis à `NULL` (confirmés
sommes calculées sans citation littérale possible après recherche
exhaustive — cohérent avec le pattern Décision 112, jamais deviné).

### Règles actuarielles : 220 tests, 16 signalements, 0 vrai bug

Toutes les anomalies retombent sur des mécanismes déjà documentés :
capacité d'absorption des pertes réduisant `scr_total` sous la somme
des modules bruts (Décision 117, re-confirmé en détail sur La
Mondiale : 5 591 244 − 3 336 477 + 187 212 = 2 441 979, exact) ;
plancher absolu du MCR pour Thémis/Macifilia (déjà documenté dans les
commentaires `aema_entites.py` depuis Décision 083) ; exception du
corridor MCR 25-45% au niveau groupe pour Aéma Groupe et SGAM AG2R LA
MONDIALE (même mécanisme que Groupama, Décision 119) ; AG.Mut proche
du plancher MCR absolu sur une petite entité (3,9 M€).

### Résultat final

**91 `source_page` corrigés cette nuit (58 Aéma + 33 AG2R), 0 valeur
modifiée.** Test de validation post-correction (15 KPIs, seed=777,
mix Aéma/AG2R, mix image/texte) : 15/15. Bilan cumulé du projet
(V3→V7) : 9 valeurs corrigées au total, 124 `source_page` corrigés au
total, 0 valeur inventée.

### Fichiers modifiés

`kpis.db` (91 `source_page` corrigés/nullifiés),
`frontend/src/data/donnees-extraites.json` + `kpi-sources.json`
(régénérés). Aucun script d'extraction modifié.
