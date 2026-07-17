2626 chunks chargés depuis le docstore FAISS

====================================================================================================
Q: À quel niveau de confiance et sur quel horizon temporel le SCR est-il calibré ?
Ancre(s) recherchée(s) : ['99,5']
====================================================================================================

-- DENSE top5 (sur top20) --
  [D1] IFRS 17          p.19    'jacents au contrat selon la possibilité que la garantie promise ne soit signiﬁcativement s'
  [D2] Solvabilité II   p.124   '— SCR taux d’in térêt,  qui représente  le sous-module «risque de taux d’in té rêt»;  — SC'
  [D3] Solvabilité II   p.57    'à des portefeuilles de référen ce  pertinents,  en  utilisant  des  hypothèses fon dées  s'
  [D4] IFRS 17          p.13    'actuariellement à une nouvelle vision économique et comptable. A ce titre, les travaux men'
  [D5] IFRS 17          p.106   'niveau de garantievia ces taux, chaque niveau constituant un produit diﬀérent. L’étude que'

-- BM25 top5 (sur top20, tokenizer normalisé) --
  [B1] Solvabilité II   p.5     'En  particulier, les hypothè\xad ses concernant  l’entreprise  de référence  qui déterminent,'
  [B2] Solvabilité II   p.51    'aboutissent  à un  capital de solvabilité  requis glo bal satisfaisant  aux  principes  én'
  [B3] Solvabilité II   p.113   'de g arantie  visé à l’article\xa0 17, paragra\xad phe\xa0 2, de la directive\xa073/239/CE E,  de l’ob'
  [B4] IFRS 17          p.89    'des groupements de contrats. En eﬀet, l’assureur peut, du fait d’une loi ou d’une régulati'
  [B5] Solvabilité II   p.113   'ments  en  actions  pendant  une  période adaptée à la période  typique de con servation  '

-- RRF top5 (fusion 70% dense / 30% BM25) --
  [R1] Solvabilité II   p.124   '— SCR taux d’in térêt,  qui représente  le sous-module «risque de taux d’in té rêt»;  — SC'
  [R2] Solvabilité II   p.51    'aboutissent  à un  capital de solvabilité  requis glo bal satisfaisant  aux  principes  én'
  [R3] IFRS 17          p.19    'jacents au contrat selon la possibilité que la garantie promise ne soit signiﬁcativement s'
  [R4] Solvabilité II   p.57    'à des portefeuilles de référen ce  pertinents,  en  utilisant  des  hypothèses fon dées  s'
  [R5] IFRS 17          p.13    'actuariellement à une nouvelle vision économique et comptable. A ce titre, les travaux men'

Rang réel (sur top20) — DENSE: 14 | BM25: 2 | RRF: 2

====================================================================================================
Q: Entre quelles bornes le MCR doit-il se situer par rapport au SCR ?
Ancre(s) recherchée(s) : ['25 %', '45 %']
====================================================================================================

-- DENSE top5 (sur top20) --
  [D1] Solvabilité II   p.124   'qui représente  le sous-module «concentrations  du risque de\xa0marché»;  — SCR change,  qui '
  [D2] Solvabilité II   p.124   '— SCR taux d’in térêt,  qui représente  le sous-module «risque de taux d’in té rêt»;  — SC'
  [D3] Solvabilité II   p.123   'termes  doit couvrir toutes les comb inaisons  possibles  de i et j. Dan s  le calcul, SCR'
  [D4] Solvabilité II   p.123   'couvrir toutes les comb inaisons  possibles  de i et j. Dan s  le calcul, SCR i et SCRj so'
  [D5] Solvabilité II   p.2     'le secteur de l’assuran ce,  est le «capital de solvab ilité  requis» (SCR). I l  conviend'

-- BM25 top5 (sur top20, tokenizer normalisé) --
  [B1] Solvabilité II   p.124   'de marché» Structure du module «risque de marché» Le module «risque de marché» défin i  à '
  [B2] Solvabilité II   p.124   'vie, qui représen te  le sous-module «risque de dépen ses  en  vie»;  — SCR révision,  qui'
  [B3] Solvabilité II   p.124   '17.12.2009 FR Journal officiel de l’Union européenne L 335/125 3.\xa0 Calcul du  module « ris'
  [B4] Solvabilité II   p.124   '— SCR taux d’in térêt,  qui représente  le sous-module «risque de taux d’in té rêt»;  — SC'
  [B5] Solvabilité II   p.124   'couvrir toutes les comb inaisons  possibles  de i et j. Dan s  le calcul, SCR i et SCRj so'

-- RRF top5 (fusion 70% dense / 30% BM25) --
  [R1] Solvabilité II   p.124   '— SCR taux d’in térêt,  qui représente  le sous-module «risque de taux d’in té rêt»;  — SC'
  [R2] Solvabilité II   p.123   'termes  doit couvrir toutes les comb inaisons  possibles  de i et j. Dan s  le calcul, SCR'
  [R3] Solvabilité II   p.124   'couvrir toutes les comb inaisons  possibles  de i et j. Dan s  le calcul, SCR i et SCRj so'
  [R4] Solvabilité II   p.123   'couvrir toutes les comb inaisons  possibles  de i et j. Dan s  le calcul, SCR i et SCRj so'
  [R5] Solvabilité II   p.123   '— SCR marché, qui représen te le module « risque de marché»;  — SCR défaut, qui représen t'

Rang réel (sur top20) — DENSE: None | BM25: None | RRF: None

====================================================================================================
Q: De quoi se composent les provisions techniques sous Solvabilité II ?
Ancre(s) recherchée(s) : ['meilleure estimation', 'marge de risque']
====================================================================================================

-- DENSE top5 (sur top20) --
  [D1] Solvabilité II   p.45    's’ajoutant  au taux d’intérêt  sans  risque pertinent,  que supporterait  une  en treprise'
  [D2] Solvabilité II   p.44    'et  les données  généralement  disponibles  sur les risques de souscrip\xad tion  (cohérence '
  [D3] Solvabilité II   p.60    'sont  pas établies,  par ces actifs.  Lorsque les prestation s  prévues par un   contrat  '
  [D4] Solvabilité II   p.5     'imposent  de constituer  des provisions  techniques  adéqua\xad tes. Les prin cipes  et les m'
  [D5] Solvabilité II   p.44    'veillen t  à ce que les en treprises  d’assu\xad rance  et de réassurance  établissent  des p'

-- BM25 top5 (sur top20, tokenizer normalisé) --
  [B1] Solvabilité II   p.76    'd’assurance  de participer à un e  coassu\xad rance  communautaire  ne  peut être subordonnée'
  [B2] Solvabilité II   p.44    'actuel  que les en treprises  d’assurance  et de réassuran ce  devraient  payer  si elles '
  [B3] Solvabilité II   p.110   'contrôle  visée à l’article\xa021 ter.  Article\xa0 17 ter Exigence de marge de solvabilité 1. S'
  [B4] Solvabilité II   p.44    'et  les données  généralement  disponibles  sur les risques de souscrip\xad tion  (cohérence '
  [B5] Solvabilité II   p.44    'veillen t  à ce que les en treprises  d’assu\xad rance  et de réassurance  établissent  des p'

-- RRF top5 (fusion 70% dense / 30% BM25) --
  [R1] Solvabilité II   p.44    'et  les données  généralement  disponibles  sur les risques de souscrip\xad tion  (cohérence '
  [R2] Solvabilité II   p.44    'veillen t  à ce que les en treprises  d’assu\xad rance  et de réassurance  établissent  des p'
  [R3] Solvabilité II   p.45    'durée de ceux-ci.  Article\xa0 78 Autres  éléments à prendre en considération dans le calcu l'
  [R4] Solvabilité II   p.44    'actuel  que les en treprises  d’assurance  et de réassuran ce  devraient  payer  si elles '
  [R5] Solvabilité II   p.44    'cul des provisions  techniques  est effectué conformément  aux arti\xad cles\xa077\xa0à\xa082 et\xa086. A'

Rang réel (sur top20) — DENSE: 7 | BM25: 8 | RRF: 5

====================================================================================================
Q: Qu'est-ce que la marge de service contractuelle sous IFRS 17 ?
Ancre(s) recherchée(s) : ['contractual service margin', 'marge pour service contractuel']
====================================================================================================

-- DENSE top5 (sur top20) --
  [D1] IFRS 17          p.23    '12 Chapitre 1. IFRS 17 rerie ajustés pour risques. Ils doivent être explicites, non biaisé'
  [D2] IFRS 17          p.27    'plus tôt dans la période aﬁn de pouvoir mesurer les éléments du passif selon IFRS 17, et p'
  [D3] IFRS 17          p.12    'IFRS 17 sont nombreux et leurs interprétations ne sont pas encore ﬁxées à l’heure actuelle'
  [D4] IFRS 17          p.120   '3.5. Limites de l’étude & Ouvertures 109 de la norme chez les assureurs. Il est par ailleu'
  [D5] IFRS 17          p.105   'Nous avons vu que la norme IFRS 17 préconise [76] une segmentation des contrats émis par u'

-- BM25 top5 (sur top20, tokenizer normalisé) --
  [B1] IFRS 17          p.27    'plus tôt dans la période aﬁn de pouvoir mesurer les éléments du passif selon IFRS 17, et p'
  [B2] IFRS 17          p.23    '12 Chapitre 1. IFRS 17 rerie ajustés pour risques. Ils doivent être explicites, non biaisé'
  [B3] IFRS 17          p.12    'IFRS 17 sont nombreux et leurs interprétations ne sont pas encore ﬁxées à l’heure actuelle'
  [B4] IFRS 17          p.38    'autre contrat d’assurance à la date de reconnaissance avec l’objectif toutefois de reﬂéter'
  [B5] IFRS 17          p.13    'tique l’approche. Ensuite, et par de-là les contraintes techniques que la norme impose, no'

-- RRF top5 (fusion 70% dense / 30% BM25) --
  [R1] IFRS 17          p.23    '12 Chapitre 1. IFRS 17 rerie ajustés pour risques. Ils doivent être explicites, non biaisé'
  [R2] IFRS 17          p.27    'plus tôt dans la période aﬁn de pouvoir mesurer les éléments du passif selon IFRS 17, et p'
  [R3] IFRS 17          p.12    'IFRS 17 sont nombreux et leurs interprétations ne sont pas encore ﬁxées à l’heure actuelle'
  [R4] IFRS 17          p.13    'tique l’approche. Ensuite, et par de-là les contraintes techniques que la norme impose, no'
  [R5] IFRS 17          p.120   '3.5. Limites de l’étude & Ouvertures 109 de la norme chez les assureurs. Il est par ailleu'

Rang réel (sur top20) — DENSE: 1 | BM25: 1 | RRF: 1


####################################################################################################
TABLEAU RÉCAPITULATIF (position dans le top 5 de chaque méthode)
####################################################################################################
| Question | Dense top5 | BM25 top5 | RRF top5 | +Rerank top5 |
|---|---|---|---|---|
| Q1: À quel niveau de confiance et sur quel horizon tem... | absent (top5) — rang réel 14 | rang 2 | rang 2 | *(en attente — étape 3)* |
| Q2: Entre quelles bornes le MCR doit-il se situer par ... | absent | absent | absent | *(en attente — étape 3)* |
| Q3: De quoi se composent les provisions techniques sou... | absent (top5) — rang réel 7 | absent (top5) — rang réel 8 | rang 5 | *(en attente — étape 3)* |
| Q4: Qu'est-ce que la marge de service contractuelle so... | rang 1 | rang 1 | rang 1 | *(en attente — étape 3)* |
