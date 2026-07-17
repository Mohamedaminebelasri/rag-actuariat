VRAM AVANT tout reranker (e5-large seul) : 2239.6 Mo alloués / 2252.3 Mo réservés

Chargement candidat A (cross-encoder/mmarco-mMiniLMv2-L12-H384-v1)...
VRAM avec A chargé : 2710.1 Mo alloués / 2736.8 Mo réservés
VRAM après déchargement de A (del + empty_cache) : 2239.6 Mo alloués / 2252.3 Mo réservés

Chargement candidat B (BAAI/bge-reranker-v2-m3, fp16)...
B chargé sur device=cuda:0, dtype=torch.float16
VRAM avec B chargé (fp16) : 3375.2 Mo alloués / 3393.2 Mo réservés

====================================================================================================
Q: À quel niveau de confiance et sur quel horizon temporel le SCR est-il calibré ?
Ancre(s) : ['99,5']  |  RRF top5 : rang 2  |  rerank A : rang 1
====================================================================================================

-- RERANK-B top5 --
  [Y1] Solvabilité II   p.51    'aboutissent  à un  capital de solvabilité  requis glo bal satisfaisant  aux  principes  én'
  [Y2] Solvabilité II   p.50    'avec un  niveau  de confiance  de 99,5\xa0% à  l’horizon  d’un  an.  4. Le  capital de solvab'
  [Y3] Solvabilité II   p.50    'portefeuille  dont  la souscription  est attendue  dans  les douze mois  à ven ir.  Pour c'
  [Y4] Solvabilité II   p.2     'le secteur de l’assuran ce,  est le «capital de solvab ilité  requis» (SCR). I l  conviend'
  [Y5] Solvabilité II   p.124   '17.12.2009 FR Journal officiel de l’Union européenne L 335/125 3.\xa0 Calcul du  module « ris'

Rang réel après rerank B (sur pool RRF de 37 candidats) : 1

====================================================================================================
Q: De quoi se composent les provisions techniques sous Solvabilité II ?
Ancre(s) : ['meilleure estimation', 'marge de risque']  |  RRF top5 : rang 5  |  rerank A : rang 18
====================================================================================================

-- RERANK-B top5 --
  [Y1] Solvabilité II   p.112   'aux parag raphe s \xa0 2  à \xa0 4  e s t in férieure  à l’exi\xad gence  de marg e  de solvab ilit'
  [Y2] Solvabilité II   p.111   'l’article\xa02, paragraphe\xa0 3, points\xa0 b)\xa0 iii), iv) et\xa0v), de ladite direc\xad tive, l’exig enc'
  [Y3] Solvabilité II   p.26    'a), ainsi  que la méthode de calcul uti\xad lisée pour étab lir  ces prévisions; d)  les prév'
  [Y4] Solvabilité II   p.53    'opérations,  en  termes d’encaissement  de primes et de provision s  techniques  détenues '
  [Y5] Solvabilité II   p.45    's’ajoutant  au taux d’intérêt  sans  risque pertinent,  que supporterait  une  en treprise'

Rang réel après rerank B (sur pool RRF de 34 candidats) : 13

====================================================================================================
Q: Qu'est-ce que la marge de service contractuelle sous IFRS 17 ?
Ancre(s) : ['contractual service margin', 'marge pour service contractuel']  |  RRF top5 : rang 1  |  rerank A : rang 1
====================================================================================================

-- RERANK-B top5 --
  [Y1] IFRS 17          p.27    'plus tôt dans la période aﬁn de pouvoir mesurer les éléments du passif selon IFRS 17, et p'
  [Y2] IFRS 17          p.23    '12 Chapitre 1. IFRS 17 rerie ajustés pour risques. Ils doivent être explicites, non biaisé'
  [Y3] IFRS 17          p.12    'IFRS 17 sont nombreux et leurs interprétations ne sont pas encore ﬁxées à l’heure actuelle'
  [Y4] IFRS 17          p.13    'tique l’approche. Ensuite, et par de-là les contraintes techniques que la norme impose, no'
  [Y5] IFRS 17          p.120   '3.5. Limites de l’étude & Ouvertures 109 de la norme chez les assureurs. Il est par ailleu'

Rang réel après rerank B (sur pool RRF de 32 candidats) : 1


####################################################################################################
TABLEAU COMPARATIF A vs B (Q1, Q3, Q4)
####################################################################################################
| Question | RRF top5 | +Rerank A | +Rerank B |
|---|---|---|---|
| À quel niveau de confiance et sur quel horizon tem... | rang 2 | rang 1 | rang 1 |
| De quoi se composent les provisions techniques sou... | rang 5 | absent (top5) — rang réel 18 | absent (top5) — rang réel 13 |
| Qu'est-ce que la marge de service contractuelle so... | rang 1 | rang 1 | rang 1 |
