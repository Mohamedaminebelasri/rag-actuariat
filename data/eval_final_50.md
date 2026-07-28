# Évaluation finale du système RAG complet (50 questions)

Golden set : `data/golden_set.jsonl` (50 questions). Retrieval BGE-M3 mode="dense", k=5. Génération avec fallback Gemini -> Mistral -> Groq (Décision 012).

## Résultats question par question

| id | question (30c) | attendu | rang retrieval | cité ? |
|---|---|---|---|---|
| 1 | Combien de temps les autorités | 58 | 2 | Oui |
| 2 | Que se passe-t-il si le régula | 58 | 2 | Oui |
| 3 | Quels critères examine-t-on po | 59 | 1 | Oui |
| 4 | Comment évalue-t-on le risque  | 59 | 1 | Oui |
| 5 | Quelles obligations quand un a | 60 | 1 | Oui |
| 6 | Un assureur doit-il déclarer l | 61 | 1 | Oui |
| 7 | Une autorité peut-elle transme | 70 | 1 | Oui |
| 8 | Quel est le rôle du commissair | 72 | 1 | Oui |
| 9 | Le commissaire aux comptes doi | 72 | absent | Non |
| 10 | Une compagnie peut-elle faire  | 73 | 1 | Oui |
| 11 | Comment séparer la gestion vie | 74 | 1 | Oui |
| 12 | Comment valorise-t-on les acti | 75 | 1 | Oui |
| 13 | Pourquoi une compagnie doit-el | 76 | 2 | Oui |
| 14 | Que représente la valeur des p | 76 | 1 | Oui |
| 15 | Comment calcule-t-on les provi | 77 | 3 | Oui |
| 16 | Sur quoi se base le calcul de  | 77 | 1 | Oui |
| 17 | Faut-il tenir compte de l'infl | 78 | 1 | Oui |
| 18 | Comment traiter les garanties  | 79 | 1 | Oui |
| 19 | Pourquoi le SCR est-il calibré | 101 | 1 | Oui |
| 20 | Le MCR est-il plafonné à 60% d | 129 | absent | Non |
| 21 | Le SCR est-il calibré sur un h | 101 | 1 | Oui |
| 22 | Quelles informations sur le ca | 51 | 1 | Oui |
| 23 | Une compagnie peut-elle refuse | 53 | 1 | Oui |
| 24 | Combien de temps une compagnie | 54 | 1 | Oui |
| 25 | Qui doit approuver le rapport  | 55 | 1 | Oui |
| 26 | Le rapport de solvabilité doit | 51 | 1 | Oui |
| 27 | Que fait une autorité de contr | 52 | 1 | Oui |
| 28 | À partir de quel seuil de part | 57 | 1 | Oui |
| 29 | L'article sur les acquisitions | 57 | absent | Non |
| 30 | Quelles exigences pèsent sur u | 53 | 2 | Oui |
| 31 | Une compagnie peut-elle publie | 54 | 3 | Oui |
| 32 | Avec quelle probabilité une co | 101 | 1 | Oui |
| 33 | Le SCR de base couvre-t-il aus | 101 | 2 | Oui |
| 34 | Quels sont les 6 risques minim | 101 | 1 | Oui |
| 35 | À quelle fréquence une compagn | 102 | 1 | Oui |
| 36 | Une compagnie peut-elle change | 102 | 1 | Oui |
| 37 | De quels 3 éléments la formule | 103 | 1 | Oui |
| 38 | Le risque de crédit fait-il pa | 104 | 1 | Oui |
| 39 | Sur quelle mesure statistique  | 104 | 1 | Oui |
| 40 | Le module marché du SCR prend- | 105 | 2 | Oui |
| 41 | Qu'est-ce qui limite l'ajustem | 106 | 1 | Oui |
| 42 | L'exigence de capital pour ris | 107 | 1 | Oui |
| 43 | Combien de temps les autorités | 112 | 3 | Oui |
| 44 | Une compagnie qui a un modèle  | 117 | 3 | Oui |
| 45 | Que se passe-t-il si une compa | 118 | 1 | Oui |
| 46 | À quelle fréquence les données | 121 | absent | Non |
| 47 | Entre quelles bornes le minimu | 129 | absent | Non |
| 48 | Le MCR peut-il descendre en de | 129 | absent | Non |
| 49 | Selon quelle fréquence une com | 129 | 5 | Oui |
| 50 | Le MCR est-il calculé selon la | 129 | absent | Non |

## Métriques finales (50/50 questions traitées)

| Métrique | Valeur |
|---|---|
| Recall@5 (retrieval) | 43/50 (0.860) |
| Citation correcte (génération) | 43/50 (0.860) |
| MRR (retrieval) | 0.7307 |

## Échecs — article attendu non cité (7)

- id 9 : "Le commissaire aux comptes doit-il signaler une violation du SCR au régulateur ?" (attendu Art. 72, rang retrieval : absent, articles cités dans la réponse : [])
- id 20 : "Le MCR est-il plafonné à 60% du SCR ?" (attendu Art. 129, rang retrieval : absent, articles cités dans la réponse : [])
- id 29 : "L'article sur les acquisitions qualifiées traite-t-il du calcul du capital de solvabilité requis ?" (attendu Art. 57, rang retrieval : absent, articles cités dans la réponse : [])
- id 46 : "À quelle fréquence les données du modèle interne doivent-elles être mises à jour ?" (attendu Art. 121, rang retrieval : absent, articles cités dans la réponse : [])
- id 47 : "Entre quelles bornes le minimum de capital requis doit-il se situer par rapport au SCR ?" (attendu Art. 129, rang retrieval : absent, articles cités dans la réponse : [101, 166])
- id 48 : "Le MCR peut-il descendre en dessous d'un montant absolu minimum, même si 25% du SCR est plus bas ?" (attendu Art. 129, rang retrieval : absent, articles cités dans la réponse : [])
- id 50 : "Le MCR est-il calculé selon la même formule standard complexe que le SCR ?" (attendu Art. 129, rang retrieval : absent, articles cités dans la réponse : [103, 166, 166])
