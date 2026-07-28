---
title: Assistant Solvabilité II
emoji: ⚖️
colorFrom: blue
colorTo: indigo
sdk: gradio
sdk_version: 6.20.0
app_file: app_gradio.py
pinned: false
---

# 🏛️ Assistant Solvabilité II

## Démo en ligne

L'application est déployée et accessible en ligne, gratuitement, à cette adresse : https://huggingface.co/spaces/BELASRI/assistant-solvabilite-ii

Le premier chargement peut prendre entre 30 et 60 secondes. C'est normal : l'application tourne sur un GPU gratuit alloué dynamiquement par Hugging Face (ZeroGPU), qui se met en veille après une période d'inactivité et doit se réveiller au premier message.

## Contexte et objectif

La directive européenne Solvabilité II (2009/138/CE) encadre la solvabilité des compagnies d'assurance. Elle compte 312 articles répartis sur plusieurs centaines de pages. Trouver la bonne référence légale pour répondre à une question précise — par exemple les bornes exactes du minimum de capital requis, ou le niveau de confiance retenu pour le calcul du capital de solvabilité — demande normalement une recherche manuelle longue dans un texte dense et technique.

Utiliser un assistant IA générique pour répondre directement à ce genre de question est risqué. Un grand modèle de langage peut produire une réponse plausible, bien écrite, et complètement fausse sur un point réglementaire précis, sans qu'il soit possible de le détecter sans revérifier soi-même le texte. Dans un contexte réglementaire, ce risque n'est pas acceptable.

L'objectif de ce projet est donc un assistant qui ne répond qu'à partir du texte réel de la directive, qui cite systématiquement l'article sur lequel il s'appuie, et qui refuse de répondre plutôt que d'inventer lorsque l'information n'est pas dans le texte fourni. Le projet a été réalisé dans le cadre d'un stage chez Iconcilio, à destination des équipes qui ont besoin d'un accès rapide et fiable au texte de la directive.

## Architecture générale

Le système fonctionne en deux phases distinctes.

La première phase, l'indexation, ne se fait qu'une seule fois. Le texte officiel de la directive est récupéré depuis EUR-Lex, découpé article par article, puis chaque article est transformé en un vecteur numérique (un « embedding ») qui capture son sens, et l'ensemble de ces vecteurs est stocké dans un index de recherche.

La seconde phase se répète à chaque question posée par l'utilisateur. La question est elle-même transformée en vecteur, comparée à tous les vecteurs de l'index pour retrouver les cinq articles les plus proches en sens, puis ces articles sont transmis à un modèle de langage avec l'instruction stricte de répondre uniquement à partir d'eux et de citer sa source.

```
PHASE 1 — Indexation (une seule fois)
EUR-Lex HTML → découpage par article → BGE-M3 (vecteurs) → index FAISS

PHASE 2 — Question (à chaque fois)
Question → BGE-M3 (vecteur) → FAISS (top 5 articles) → LLM → réponse citée
```

## Chaque outil expliqué en détail

### 1. La source des données — EUR-Lex HTML

Le projet a démarré avec le PDF officiel de la directive, téléchargé depuis EUR-Lex. Après découpage automatique par article, un diagnostic complet a montré que 142 des 312 titres d'articles étaient corrompus : le texte extrait du PDF contenait des espaces insérés au milieu des mots, des numéros de page et des en-têtes du Journal officiel mélangés au corps du texte, et des césures mal recollées. Ce chiffre a été mesuré directement, pas estimé.

La cause est structurelle : un PDF n'a pas de structure sémantique, seulement une disposition visuelle de caractères sur une page. Le projet s'est donc tourné vers la version HTML structurée d'EUR-Lex, qui encode chaque article dans une balise dédiée avec son numéro et son titre clairement identifiés. Après ce changement, les 312 titres extraits sont propres, sans aucune corruption.

Le découpage par article reste néanmoins un exercice délicat même sur du HTML propre, car le mot « article » apparaît des centaines de fois dans le texte sans être à chaque fois le début d'un vrai article : parfois c'est une référence croisée (« conformément à l'article 47, paragraphe 2 »), parfois une entrée de sommaire, parfois une ligne de table de correspondance en annexe. Le système repère automatiquement où se termine le sommaire et où commencent les annexes, pour ne retenir que les vrais débuts d'article entre les deux.

### 2. Le modèle d'embeddings — BGE-M3

Un modèle d'embeddings est un modèle qui transforme un texte en une liste de nombres, de telle sorte que deux textes proches en sens obtiennent des listes de nombres proches entre elles, même s'ils n'utilisent pas les mêmes mots. C'est ce qui permet de retrouver un article pertinent même quand la question posée ne reprend pas le vocabulaire exact du texte de loi.

Deux modèles ont été comparés directement sur le golden set du projet : BGE-M3 et e5-large, deux modèles multilingues de taille comparable. Sur les mêmes questions, BGE-M3 retrouve l'article attendu dans le top 5 des résultats 18 fois sur 18, contre 15 fois sur 18 pour e5-large. Sur la position exacte du bon résultat (le MRR), BGE-M3 obtient 0,88 contre 0,70 pour e5-large. Le choix n'a donc pas été fait sur réputation ou intuition, mais sur une mesure comparative directe, dans les conditions réelles du projet.

### 3. L'index vectoriel — FAISS

Une fois les 312 articles transformés en vecteurs, il faut un moyen de retrouver rapidement, parmi ces 312 vecteurs, les plus proches du vecteur de la question posée. C'est le rôle de FAISS, une bibliothèque de recherche par similarité développée par Meta. Elle est utilisée ici en local, gratuitement, sans dépendre d'un service tiers payant — un choix naturel vu la taille modeste du corpus, puisque 312 articles tiennent largement en mémoire et se recherchent en quelques millisecondes.

### 4. La génération — trois fournisseurs LLM en cascade

Trouver les bons articles ne suffit pas : il faut ensuite un modèle de langage capable de rédiger une réponse à partir de ces articles, en citant sa source. Le projet a d'abord utilisé un seul fournisseur, puis a dû changer à plusieurs reprises pour des raisons très concrètes rencontrées en cours de route : une clé Groq expirée, un compte Cerebras bloqué par une erreur de facturation, un quota Mistral trop vite atteint dès que le pipeline conversationnel a commencé à faire plusieurs appels par question, puis un quota Gemini réel qui s'est révélé beaucoup plus bas qu'annoncé, et enfin une erreur de connexion réseau récurrente vers Gemini une fois l'application déployée sur Hugging Face.

Plutôt que de dépendre d'un seul fournisseur et de subir chacune de ces pannes, le système essaie désormais Gemini en premier, puis bascule automatiquement sur Mistral si Gemini échoue, puis sur Groq si Mistral échoue aussi. La bascule est invisible pour l'utilisateur, qui reçoit une réponse normale, mais elle reste visible dans les journaux techniques du système. Ce mécanisme a été testé aussi bien en conditions simulées qu'en conditions réelles, où il a effectivement sauvé plusieurs réponses qui auraient sinon échoué.

### 5. Résolution d'acronymes

Les utilisateurs posent naturellement leurs questions avec des sigles du métier : SCR, MCR, ORSA. Le texte officiel de la directive, lui, n'utilise presque jamais ces sigles — il écrit « capital de solvabilité requis » ou « minimum de capital requis » en toutes lettres. Un moteur de recherche sémantique cherchant « MCR » a donc du mal à retrouver un texte qui ne contient jamais ce mot.

La solution retenue est volontairement simple : un dictionnaire fixe qui reconnaît les sigles courants et ajoute leur forme longue entre parenthèses avant la recherche, sans faire appel à un modèle de langage pour cette étape. Sur un jeu de huit questions construites autour de ces sigles, le taux de succès dans le top 5 passe de 62,5 % à 100 % avec cette expansion, sans aucune dégradation sur les questions qui fonctionnaient déjà.

### 6. Clarification des questions ambiguës

Une question comme « quel est le minimum ? » est ambiguë : elle peut viser le minimum de capital requis, un seuil de participation, ou autre chose. Deux méthodes ont été comparées pour détecter ce genre de question avant de lancer une recherche inutile : demander à un modèle de langage de juger si la question est claire ou ambiguë, ou bien observer si les résultats de la recherche sémantique sont dispersés ou concentrés, une question ambiguë tendant à donner des résultats plus dispersés.

Sur dix questions de test, les deux méthodes obtiennent exactement le même score, neuf sur dix, mais elles ne se trompent pas sur les mêmes cas. La méthode fondée sur un modèle de langage a été retenue malgré son coût plus élevé, un appel supplémentaire à chaque question, parce que son seuil de décision n'a pas besoin d'être recalibré pour chaque nouvelle façon de poser une question, contrairement à la méthode fondée sur la dispersion des résultats, dont le seuil avait été ajusté spécifiquement sur l'échantillon de test.

### 7. Correction des fausses prémisses

Un assistant IA classique, confronté à une question du type « pourquoi le capital de solvabilité requis est-il calibré à 99,9 % ? », a tendance soit à confirmer ce chiffre par politesse, soit à refuser de répondre puisque « 99,9 % » n'apparaît nulle part dans le texte. Aucun des deux comportements n'est satisfaisant : le vrai chiffre, 99,5 %, est disponible dans l'article 101, et un bon assistant devrait le signaler.

Une règle a donc été ajoutée explicitement au système : si la question contient un chiffre inexact et que le texte fourni donne la valeur correcte, l'assistant doit corriger explicitement, citer sa source, et surtout ne jamais commencer sa réponse par la phrase de refus avant de se corriger — un premier test a montré que cette formulation en deux temps pouvait induire en erreur un lecteur pressé qui ne lirait que la première ligne.

### 8. Mémoire conversationnelle

Dans une conversation, une question de suivi comme « et comment on le calcule ? » n'a de sens qu'avec le contexte de la question précédente. Avant chaque nouvelle recherche, le système reformule donc la question posée en tenant compte des derniers échanges de la conversation, pour obtenir une question autonome.

Par exemple, si l'utilisateur demande d'abord « Qu'est-ce que le MCR ? » puis ensuite « comment on le calcule ? », le système reformule cette seconde question en « Comment calcule-t-on le MCR ? » avant de lancer la recherche — la question posée telle quelle à l'index de recherche n'aurait presque aucune chance de retrouver le bon article.

### 9. L'interface — Gradio et ZeroGPU

L'interface a d'abord été construite avec Streamlit. Au moment du déploiement sur Hugging Face Spaces, le sélecteur de SDK proposé pour créer un nouvel espace ne présentait plus que trois options : Gradio, Docker, et une page statique — Streamlit n'y figurait plus. L'interface a donc été migrée vers Gradio, en conservant strictement le même moteur de recherche et de génération : seule la couche d'affichage a changé.

Cette migration a eu un bénéfice inattendu : Gradio est le seul SDK compatible avec ZeroGPU, un mécanisme Hugging Face qui alloue dynamiquement un vrai GPU gratuit le temps du calcul, puis le libère. L'application bénéficie ainsi d'une accélération matérielle gratuite pour l'étape de recherche sémantique, ce qui n'aurait pas été possible avec l'interface précédente.

## La discipline de mesure — le golden set

Aucune des décisions présentées plus haut n'a été prise à l'intuition. Chacune s'appuie sur un jeu de questions de test, appelé golden set, dont la réponse attendue — l'article exact qui doit être cité — a été vérifiée manuellement en relisant le texte réel de la directive avant de valider chaque question. Cette vérification a d'ailleurs permis de repérer et corriger une erreur : quatre questions initialement attribuées à l'article 130 pointaient en réalité vers l'article 129, l'article 130 ne contenant qu'une clause de renvoi technique sans substance.

Le golden set final compte 50 questions couvrant 31 articles distincts de la directive. Onze de ces questions sont volontairement construites comme des pièges, répartis en cinq familles : des questions contenant un chiffre faux que le système doit corriger, des questions contenant une affirmation factuellement fausse, une question nécessitant de combiner deux articles différents pour obtenir la bonne réponse, une question qui cite le bon numéro d'article mais dans un mauvais contexte thématique, et une question utilisant un terme technique proche mais différent du terme réellement employé dans le texte.

C'est ce golden set, plus que n'importe quelle ligne de code, qui constitue la partie la plus précieuse du projet : sans lui, chaque choix technique — le modèle d'embeddings, le fournisseur de génération, la stratégie de recherche — n'aurait été qu'une opinion.

## Résultats finaux mesurés

| Métrique | Valeur | Ce que ça mesure |
|---|---|---|
| Recall@5 | 43/50 (86 %) | l'article attendu figure-t-il parmi les 5 résultats retournés par la recherche ? |
| MRR | 0,73 | à quel rang moyen, pondéré, l'article attendu apparaît-il quand il est trouvé ? |
| Citation correcte | 43/50 (86 %) | la réponse finale, générée par le modèle de langage, cite-t-elle bien l'article attendu ? |
| Échecs de génération pure | 0 | combien de fois l'article était disponible dans le contexte mais n'a pas été cité ? |

Le dernier chiffre est le plus important à comprendre : dans les sept cas où le système se trompe, ce n'est jamais parce que le modèle de langage a mal utilisé un bon contexte — c'est toujours parce que la recherche sémantique n'a pas retrouvé le bon article en premier lieu. Quatre de ces sept échecs concernent l'article 129, qui définit le minimum de capital requis : c'est une limite connue et documentée du système, pas une surprise.

## Ce qui a été testé et rejeté

Un projet qui ne documente que ses succès donne une fausse impression de facilité. Deux pistes sérieuses ont été testées puis écartées, et les deux méritent d'être présentées ici avec les mêmes chiffres que les choix retenus.

La première piste est un retrieval hybride, combinant la recherche sémantique BGE-M3 avec une recherche par mots-clés classique (BM25), fusionnées par un algorithme de pondération des rangs. Cette approche a été testée à deux reprises, à des échelles croissantes du golden set. Sur 50 questions, elle corrige bien trois des quatre échecs connus sur l'article 129, mais elle casse en retour trois questions qui réussissaient parfaitement en recherche purement sémantique, et dégrade le classement de sept autres. Le score global de rappel progresse d'une seule unité, tandis que la qualité moyenne du classement recule nettement. Le verdict final est que cette approche n'apporte pas de gain net et n'est pas retenue par défaut, même si le code reste disponible pour une utilisation ciblée future sur les questions portant spécifiquement sur des seuils numériques.

Une seconde piste testée est l'auto-évaluation du retrieval avant génération (le système juge lui-même si les articles trouvés suffisent, et relance une recherche reformulée sinon). Sur le golden set, cette méthode obtient exactement le même taux de citation correcte que le mode simple, tout en doublant approximativement le temps de réponse à cause de l'appel supplémentaire. Elle n'a pas non plus corrigé le cas spécifique qu'elle visait à résoudre. Le mode simple reste donc le défaut.

Documenter un rejet a la même valeur qu'un choix retenu : ça évite de retester la même idée six mois plus tard en pensant qu'elle n'a jamais été essayée, et ça montre que chaque décision du projet peut être remise en cause par une mesure contraire, pas seulement défendue par une intuition.

## Limites connues et honnêtes

Le texte utilisé est la version originale de la directive publiée en 2009, pas sa version consolidée intégrant les amendements ultérieurs, notamment Omnibus II de 2014. L'article 129, qui définit le minimum de capital requis, reste la zone la plus fragile du système au niveau de la recherche, avec quatre échecs sur sept documentés sur des formulations qui s'éloignent du vocabulaire exact du texte. Enfin, les questions de suivi très courtes dans une conversation sont parfois mal reformulées faute de contexte suffisant.

## Stack technique complète

- **Python 3.10** — version imposée par l'environnement d'exécution Hugging Face Spaces ZeroGPU.
- **Gradio** — framework d'interface web utilisé pour l'application.
- **BGE-M3 (safetensors)** — modèle d'embeddings multilingue, chargé au format safetensors pour éviter une restriction de sécurité récente sur les anciens formats de sauvegarde PyTorch.
- **sentence-transformers** — bibliothèque utilisée pour charger et exécuter BGE-M3.
- **FAISS** — bibliothèque de recherche vectorielle par similarité, utilisée en local.
- **Hugging Face Spaces ZeroGPU** — hébergement avec allocation dynamique et gratuite d'un GPU.
- **Gemini, Mistral, Groq** — les trois fournisseurs de génération, tous appelés via le SDK standard OpenAI grâce à leurs points d'accès compatibles.

## Installation locale

```bash
python -m venv .venv
source .venv/Scripts/activate  # ou .venv/bin/activate sous Linux/Mac
pip install -r requirements.txt
python app_gradio.py
```

## Auteur

Mohamed Amine Belasri — stage Iconcilio 2026

---

Projet propriétaire — réalisé dans le cadre d'un stage chez Iconcilio, 2026. Tous droits réservés.
