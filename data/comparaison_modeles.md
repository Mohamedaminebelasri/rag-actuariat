# Comparaison e5-large vs BGE-M3 sur le golden set du projet

Protocole : retrieval seul (aucun LLM), 312 articles, 18 questions du golden set (`data/golden_set.jsonl`).

e5-large utilise les préfixes `passage: ` / `query: ` ; BGE-M3 sans préfixe.


## Tableau comparatif

| id | question (30 car) | attendu | rang e5 | rang BGE-M3 |
|---|---|---|---|---|
| 1 | Combien de temps les autorités | 58 | absent | 2 |
| 2 | Que se passe-t-il si le régula | 58 | absent | 2 |
| 3 | Quels critères examine-t-on po | 59 | 1 | 1 |
| 4 | Comment évalue-t-on le risque  | 59 | 1 | 1 |
| 5 | Quelles obligations quand un a | 60 | 1 | 1 |
| 6 | Un assureur doit-il déclarer l | 61 | 1 | 1 |
| 7 | Une autorité peut-elle transme | 70 | 1 | 1 |
| 8 | Quel est le rôle du commissair | 72 | 3 | 1 |
| 9 | Le commissaire aux comptes doi | 72 | 1 | 1 |
| 10 | Une compagnie peut-elle faire  | 73 | 3 | 1 |
| 11 | Comment séparer la gestion vie | 74 | 2 | 1 |
| 12 | Comment valorise-t-on les acti | 75 | 1 | 1 |
| 13 | Pourquoi une compagnie doit-el | 76 | 2 | 2 |
| 14 | Que représente la valeur des p | 76 | 1 | 1 |
| 15 | Comment calcule-t-on les provi | 77 | absent | 3 |
| 16 | Sur quoi se base le calcul de  | 77 | 1 | 1 |
| 17 | Faut-il tenir compte de l'infl | 78 | 1 | 1 |
| 18 | Comment traiter les garanties  | 79 | 1 | 1 |

## Métriques

| Métrique | e5-large | BGE-M3 |
|---|---|---|
| Recall@5 | 15/18 (0.833) | 18/18 (1.000) |
| Recall@1 | 11/18 (0.611) | 14/18 (0.778) |
| MRR | 0.7037 | 0.8796 |

## Questions où les deux modèles échouent (0)

Aucune — au moins un des deux modèles trouve l'article attendu dans le top 5 pour chaque question.

## Constat factuel

- Meilleur MRR : BGE-M3 (0.7037 vs 0.8796)
- Meilleur Recall@5 : BGE-M3 (0.833 vs 1.000)
- Décision de modèle final non tranchée ici — voir chiffres ci-dessus.
