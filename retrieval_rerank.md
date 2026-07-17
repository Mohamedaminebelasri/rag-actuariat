VRAM allouée AVANT chargement du reranker (e5-large seul déjà chargé) : 2239.6 Mo

VRAM allouée APRÈS chargement du reranker (e5-large + cross-encoder) : 2710.1 Mo
VRAM réservée par torch (e5-large + cross-encoder) : 2736.8 Mo
Delta reranker seul : 470.6 Mo

====================================================================================================
Q: À quel niveau de confiance et sur quel horizon temporel le SCR est-il calibré ?
Ancre(s) : ['99,5']  |  rang RRF top5 mesuré à l'étape 2 : 2
====================================================================================================

-- RRF top5 (avant rerank, rappel) --
  [R1] Solvabilité II   p.124   '— SCR taux d’in térêt,  qui représente  le sous-module «risque de taux d’in té rêt»;  — SC'
  [R2] Solvabilité II   p.51    'aboutissent  à un  capital de solvabilité  requis glo bal satisfaisant  aux  principes  én'
  [R3] Solvabilité II   p.57    'd’assuran ce  et de réassuran ce  tien nent   compte, dans  leur modèle interne,  de tous '
  [R4] IFRS 17          p.19    'jacents au contrat selon la possibilité que la garantie promise ne soit signiﬁcativement s'
  [R5] Solvabilité II   p.57    'à des portefeuilles de référen ce  pertinents,  en  utilisant  des  hypothèses fon dées  s'

-- RERANK top5 (cross-encoder appliqué au pool RRF) --
  [X1] Solvabilité II   p.51    'aboutissent  à un  capital de solvabilité  requis glo bal satisfaisant  aux  principes  én'
  [X2] Solvabilité II   p.2     'le secteur de l’assuran ce,  est le «capital de solvab ilité  requis» (SCR). I l  conviend'
  [X3] Solvabilité II   p.113   'Journal officiel de l’Union européenne 17.12.2009   confiance  assuran t  aux pren eurs  e'
  [X4] Solvabilité II   p.50    'avec un  niveau  de confiance  de 99,5\xa0% à  l’horizon  d’un  an.  4. Le  capital de solvab'
  [X5] Solvabilité II   p.124   'couvrir toutes les comb inaisons  possibles  de i et j. Dan s  le calcul, SCR i et SCRj so'

Rang réel après rerank (sur pool RRF de 37 candidats) : 1

====================================================================================================
Q: De quoi se composent les provisions techniques sous Solvabilité II ?
Ancre(s) : ['meilleure estimation', 'marge de risque']  |  rang RRF top5 mesuré à l'étape 2 : 5
====================================================================================================

-- RRF top5 (avant rerank, rappel) --
  [R1] Solvabilité II   p.44    'et  les données  généralement  disponibles  sur les risques de souscrip\xad tion  (cohérence '
  [R2] Solvabilité II   p.44    'veillen t  à ce que les en treprises  d’assu\xad rance  et de réassurance  établissent  des p'
  [R3] Solvabilité II   p.45    'durée de ceux-ci.  Article\xa0 78 Autres  éléments à prendre en considération dans le calcu l'
  [R4] Solvabilité II   p.44    'actuel  que les en treprises  d’assurance  et de réassuran ce  devraient  payer  si elles '
  [R5] Solvabilité II   p.44    'cul des provisions  techniques  est effectué conformément  aux arti\xad cles\xa077\xa0à\xa082 et\xa086. A'

-- RERANK top5 (cross-encoder appliqué au pool RRF) --
  [X1] Solvabilité II   p.60    'liées  à la valeur de parts d’un OPCVM au sen s  de la directive  85/611/CEE  ou à la vale'
  [X2] Solvabilité II   p.60    'de  l’ensemble  du portefeuille. En  outre, la localisation  de ces actifs  est telle qu’e'
  [X3] Solvabilité II   p.5     'droits et obligations  contractuels  à une  autre entreprise.  En  conséquence,  la valeur'
  [X4] Solvabilité II   p.44    'veillen t  à ce que les en treprises  d’assu\xad rance  et de réassurance  établissent  des p'
  [X5] Solvabilité II   p.111   'l’article\xa02, paragraphe\xa0 3, points\xa0 b)\xa0 iii), iv) et\xa0v), de ladite direc\xad tive, l’exig enc'

Rang réel après rerank (sur pool RRF de 34 candidats) : 18

====================================================================================================
Q: Qu'est-ce que la marge de service contractuelle sous IFRS 17 ?
Ancre(s) : ['contractual service margin', 'marge pour service contractuel']  |  rang RRF top5 mesuré à l'étape 2 : 1
====================================================================================================

-- RRF top5 (avant rerank, rappel) --
  [R1] IFRS 17          p.23    '12 Chapitre 1. IFRS 17 rerie ajustés pour risques. Ils doivent être explicites, non biaisé'
  [R2] IFRS 17          p.27    'plus tôt dans la période aﬁn de pouvoir mesurer les éléments du passif selon IFRS 17, et p'
  [R3] IFRS 17          p.12    'IFRS 17 sont nombreux et leurs interprétations ne sont pas encore ﬁxées à l’heure actuelle'
  [R4] IFRS 17          p.13    'tique l’approche. Ensuite, et par de-là les contraintes techniques que la norme impose, no'
  [R5] IFRS 17          p.120   '3.5. Limites de l’étude & Ouvertures 109 de la norme chez les assureurs. Il est par ailleu'

-- RERANK top5 (cross-encoder appliqué au pool RRF) --
  [X1] IFRS 17          p.27    'plus tôt dans la période aﬁn de pouvoir mesurer les éléments du passif selon IFRS 17, et p'
  [X2] IFRS 17          p.23    '12 Chapitre 1. IFRS 17 rerie ajustés pour risques. Ils doivent être explicites, non biaisé'
  [X3] IFRS 17          p.12    'IFRS 17 sont nombreux et leurs interprétations ne sont pas encore ﬁxées à l’heure actuelle'
  [X4] IFRS 17          p.120   '3.5. Limites de l’étude & Ouvertures 109 de la norme chez les assureurs. Il est par ailleu'
  [X5] IFRS 17          p.122   'à reconsidérer la conception de leurs outils et de leurs modèles, aﬁn de prendre en compte'

Rang réel après rerank (sur pool RRF de 32 candidats) : 1


####################################################################################################
TABLEAU — colonne +Rerank complétée (Q1, Q3, Q4 uniquement — Q2 non tenté)
####################################################################################################
| Question | RRF top5 (rappel) | +Rerank top5 |
|---|---|---|
| À quel niveau de confiance et sur quel horizon temporel... | rang 2 | rang 1 |
| De quoi se composent les provisions techniques sous Sol... | rang 5 | absent (top5) — rang réel 18 |
| Qu'est-ce que la marge de service contractuelle sous IF... | rang 1 | rang 1 |
