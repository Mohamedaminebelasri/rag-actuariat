# Évaluation du système RAG complet (retrieval BGE-M3 + génération Mistral)

Golden set : `data/golden_set.jsonl` (18 questions). Modèle : `mistral-large-latest`, k=5.

## Résultats question par question

| id | question (30c) | attendu | rang retrieval | cité ? |
|---|---|---|---|---|
| 1 | Combien de temps les autorités | 58 | 2 | Oui |
| 2 | Que se passe-t-il si le régula | 58 | 2 | Non |
| 3 | Quels critères examine-t-on po | 59 | 1 | Oui |
| 4 | Comment évalue-t-on le risque  | 59 | 1 | Oui |
| 5 | Quelles obligations quand un a | 60 | 1 | Oui |
| 6 | Un assureur doit-il déclarer l | 61 | 1 | Oui |
| 7 | Une autorité peut-elle transme | 70 | 1 | Oui |
| 8 | Quel est le rôle du commissair | 72 | 1 | Oui |
| 9 | Le commissaire aux comptes doi | 72 | 1 | Oui |
| 10 | Une compagnie peut-elle faire  | 73 | 1 | Oui |
| 11 | Comment séparer la gestion vie | 74 | 1 | Oui |
| 12 | Comment valorise-t-on les acti | 75 | 1 | Oui |
| 13 | Pourquoi une compagnie doit-el | 76 | 2 | Oui |
| 14 | Que représente la valeur des p | 76 | 1 | Oui |
| 15 | Comment calcule-t-on les provi | 77 | 3 | Oui |
| 16 | Sur quoi se base le calcul de  | 77 | 1 | Oui |
| 17 | Faut-il tenir compte de l'infl | 78 | 1 | Oui |
| 18 | Comment traiter les garanties  | 79 | 1 | Oui |

## Métriques finales (18/18 questions traitées)

| Métrique | Valeur |
|---|---|
| Recall@5 (retrieval) | 18/18 (1.000) |
| Citation correcte (génération) | 17/18 (0.944) |
| MRR (retrieval) | 0.8796 |

## Échecs — article attendu non cité (1)

- id 2 : "Que se passe-t-il si le régulateur ne s'oppose pas à une acquisition dans les délais ?" (attendu Art. 58, rang retrieval : 2, articles cités dans la réponse : [])
