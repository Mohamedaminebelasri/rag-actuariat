# IDEES_SCALE_UP.md

Idées capturées pendant la phase de test (`test_markdrop/`), volontairement
**non implémentées** — à réexaminer au moment de concevoir le passage à
l'échelle sur les 30 fichiers SFCR Groupama. Contrairement à DECISIONS.md,
rien ici n'est validé ni tranché.

## Idée 001 — Sommaire comme couche de routage hiérarchique

**Statut : NON implémenté — idée capturée pour la phase de scale-up (30 fichiers)**
**Date : 2026-07-29**

### Contexte

Le Sommaire (table des matières) de chaque SFCR a été exclu du corpus RAG
final (voir la détection automatique pages 2-6 sur le document test) car
il duplique les titres de section sans contenu réel — le garder dans
l'index vectoriel risquait de polluer les résultats de recherche.

Mais un Sommaire structuré (titre de section + numéro + page) reste utile
ailleurs : comme **carte de navigation**, pas comme contenu à chercher.

### L'idée

Au lieu de jeter le Sommaire, le transformer en table de correspondance :

```
{ "section_id": "B.3.2", "titre": "Évaluation interne des risques...", "page": 37 }
```

Puis, à chaque question posée par un utilisateur, faire deux choses :
1. **Routage** (rapide, peu coûteux) : comparer la question aux titres du
   Sommaire (recherche par mots-clés, ou un appel LLM qui regarde le
   Sommaire et identifie la/les section(s) probablement concernées).
2. **Récupération fine** : lancer la recherche vectorielle (embeddings)
   déjà construite, mais en la restreignant/priorisant aux sections
   identifiées à l'étape 1.

### Pourquoi ce n'est pas juste une intuition — appui académique trouvé (juillet 2026)

- **HiKEY** (2026) formule explicitement le principe : les humains
  parcourent d'abord la table des matières pour réduire le champ de
  recherche (routage), puis lisent en détail la section pertinente
  (récupération fine). C'est exactement le même mécanisme.
- **HiREC** (Choe, Kim, Jung 2025) applique une récupération hiérarchique
  document → passage sur des **SEC filings** (rapports financiers
  réglementaires américains) — cas d'usage très proche du nôtre (SFCR).
- Papier dédié : *"Zero-Shot Document Understanding using Pseudo Table of
  Contents-Guided RAG"* (DocsRay) — utilise directement une ToC (réelle ou
  générée) comme guide de récupération.
- **Hierarchical Node-Based Reasoning** (VectifyAI) : représente un
  document comme un arbre de sections avec plages de pages ; le LLM
  traverse l'arbre pour choisir les nœuds pertinents avant de récupérer
  le texte — élimine même le besoin d'embeddings pour le routage.

### Pourquoi ce n'est PAS prioritaire maintenant (15 pages, 1 document)

Le gain de cette approche est faible sur un seul document de test. Il
devient significatif au passage à l'échelle des 30 fichiers Groupama
(plusieurs années × plusieurs entités : Groupe, Assurances Mutuelles,
Gan Vie). Exemple concret : une question comme *"Quel est le SCR de
Groupama Gan Vie en 2024 ?"* a d'abord besoin d'un routage au niveau
**document** (bon fichier = bonne entité + bonne année) avant même de
chercher dans le contenu — c'est exactement ce que la métadonnée
hiérarchique (dérivée du Sommaire de chaque fichier) permettrait de faire
efficacement.

### Prochaine étape (quand on y arrivera)

À reprendre au moment de concevoir le schéma d'indexation pour les 30
fichiers — après avoir validé l'extraction sur la partie financière
difficile (section E / annexe QRT) du document test actuel.

## Idée 002 — Résolution de sous-feuillet QRT non fiable pour les templates à variantes structurellement identiques

**Statut : bug identifié, NON corrigé — pas bloquant sur le document de test actuel**
**Date : 2026-08-18**

### Contexte

`resoudre_sous_feuille()` (`test_markdrop/ingest.py`) déduit le
sous-feuillet EIOPA exact (ex. `S.05.02.04.02`) d'une page QRT
image-only à partir du numéro local imprimé dans le document, format
`"S.05.02.04 - 02"`, en supposant que ce numéro correspond directement
au suffixe `.02` du sous-feuillet EIOPA.

Cette hypothèse casse pour les templates ayant **3 sous-feuillets ou
plus structurellement identiques** (mêmes codes-ligne, seul un axe
annexe — ex. le pays — change). `S.05.02.04` en est l'exemple concret :
vérifié contre le DPM officiel EIOPA (`EIOPA_Solvency_II_DPM_Annotated_
Templates_2.8.2.xlsx`), ce template a **6** sous-feuillets légitimement
identiques deux à deux par groupe de 3 :
- `.01`/`.02`/`.03` — Non-Vie (Home Country / Top 5 pays / Total), 18
  codes-ligne identiques
- `.04`/`.05`/`.06` — Vie, mêmes 3 variantes, 13 codes-ligne identiques

Rien ne garantit que l'ordre d'impression du document (le "01/02" local)
suive l'ordre officiel `.01→.06`. Sur le document de test, la page
imprimée "02" contenait en réalité les codes Vie (`.04`/`.05`/`.06`),
pas Non-Vie (`.02`) — la résolution locale s'est donc trompée de groupe
entier, pas seulement de variante au sein du bon groupe.

**Important : `qrt_dictionary.json` lui-même est correct** — vérifié
exhaustivement contre le DPM officiel pour tous les templates
multi-sous-feuillets (`S.05.01.02`, `S.05.02.04`, `S.23.01.22`,
`S.25.05.22`) : 0 écart. Le bug est uniquement dans la logique de
résolution du bon sous-feuillet à partir du numéro local, pas dans les
données de référence.

### L'idée (à corriger, pas encore fait)

Ne pas se fier au seul numéro local "01/02" quand un template a 3+
variantes identiques. Vérifier le **contenu réel** de la page pour
choisir la bonne sous-feuille — par exemple :
- lire le nom de pays affiché dans les colonnes (`IT`, `RO`... vu sur
  les pages testées) pour distinguer Home Country / Top 5 / Total,
- ou détecter la plage de codes-ligne réellement présents dans l'image
  (R01xx-R13xx = Non-Vie, R14xx-R27xx = Vie) avant même de tenter le
  matching complet, pour au moins choisir le bon groupe de 3.

### Pourquoi ce n'est pas prioritaire maintenant

Un seul document de test, un seul cas observé. À corriger si ce cas se
répète sur d'autres documents lors du passage à l'échelle (30 fichiers)
— pas bloquant pour avancer maintenant.
