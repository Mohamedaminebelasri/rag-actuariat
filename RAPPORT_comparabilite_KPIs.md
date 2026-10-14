# Rapport — Comparabilité des KPIs entre les 41 sociétés

**Date** : 15/10/2026 · **Périmètre** : 41 sociétés, 21 KPIs, exercice 2025 ·
**Mode** : diagnostic en lecture seule (`kpis.db` ouvert en `mode=ro`, aucun
export ni fichier front-end modifié) · **Annexe** :
`comparabilite_metadonnees_41.csv` (métadonnées contrôlées, une ligne par société).

**Légende des tags** : [Vérifié PDF p.X] = lu dans le rapport SFCR de la
société ; [Vérifié base] = calculé sur `kpis.db` / `kpi_composants` ;
[Source : URL] = source externe consultée ; [Raisonnement, à confirmer] =
déduction non vérifiée directement.

---

## 1. Résumé pour décision

**Verdict : problème MOYEN — mais GRAND pour l'onglet Analyse comparative tel
qu'il fonctionne aujourd'hui.** Le pipeline d'extraction n'est pas à jeter :
les chiffres sont en grande majorité justes et cohérents entre eux (le ratio
SCR recalculé = ratio publié pour les 41 sociétés, écart ≤ 0,5 pt
[Vérifié base]). Le problème est ailleurs : l'outil met côte à côte, sans
garde-fou, des sociétés qui ne se comparent pas, et les étiquettes qui
permettraient de les regrouper correctement sont fausses dans plus d'un cas
sur deux.

**Ce qu'il faut retenir, en 6 points :**

1. **Les étiquettes de regroupement sont fausses pour 23 sociétés sur 41**
   [Vérifié PDF + base]. Surtout l'activité (16 cas) : « Mutuelle » est
   utilisé comme une activité alors que c'est une forme juridique ; 11
   sociétés étiquetées « Vie » ou « Mutuelle » sont en réalité de la
   santé/prévoyance ; MAIF, MACIF SAM, Abeille IARD & Santé sont des
   assureurs non-vie étiquetés « Mixte » ; Sogécap est un rapport **solo**
   d'assureur vie, rangé en « groupe/Mixte ».
2. **87,6 % des 820 comparaisons possibles** entre deux sociétés croisent au
   moins une différence d'activité, de modèle de capital, de périmètre ou
   de forme juridique [Vérifié base]. Seules **3 « familles » de pairs ont au
   moins 5 membres** : vie / formule standard / solo (13), santé-prévoyance
   / formule standard / solo (11), non-vie / formule standard / solo (7).
3. **Le ratio SCR reste comparable, avec réserves.** Même définition
   réglementaire pour tous, mais la correction pour volatilité le gonfle de
   +2 pts (Covéa) à **+46 pts (Generali Vie)** et une mesure transitoire
   ajoute +8 pts à SGAM AG2R [Vérifié PDF] ; les mutuelles/SAM sont
   structurellement plus capitalisées (médiane ~276-302 % contre 195 % pour
   les SA) ; les modèles internes ne se calibrent pas comme la formule
   standard.
4. **Trois familles de KPIs ne sont pas comparables telles qu'affichées** :
   - les **modules du SCR** (marché, contrepartie, souscriptions,
     opérationnel, diversification) entre formule standard et modèle
     interne — et même, pour AXA France Vie, mélangés entre deux bases
     différentes dans la même société (diversification = 114 % des modules,
     artefact démontré au § 4.5) ;
   - la **charge de sinistres** entre vie et non-vie (en vie, ce sont des
     rachats, échéances et rentes, pas des sinistres) — 57,8 % des paires ;
   - le **MCR / ratio MCR des 5 groupes** : c'est un « SCR minimal consolidé
     de groupe » (S.23.01.22/R0610), pas un MCR [Vérifié base].
5. **Le ratio MCR apporte peu d'information** : pour 27 des 36 sociétés solo,
   le MCR est collé à une borne réglementaire (25 % ou 45 % du SCR, ou
   plancher absolu) [Vérifié base] ; le ratio MCR n'est alors qu'une
   transformation mécanique du ratio SCR (médiane 942 % en santé contre 490 %
   en vie, pour cette seule raison).
6. **Deux erreurs de données trouvées en passant** (hors périmètre, NON
   corrigées — lecture seule) : (a) **Crédit Agricole Assurances** :
   `best_estimate`, `marge_risque` et `provisions_techniques` stockés
   1 000 fois trop petits (342,6 M€ au lieu de 342 577 M€) [Vérifié PDF
   p.53 et p.66] ; (b) **ma Décision 147 d'hier est à revoir** : Allianz
   Vie y est traitée comme « modèle interne partiel » pour justifier
   l'absence de symbole d'avertissement, alors que son rapport décrit un
   modèle couvrant tous les risques [Vérifié PDF p.70, p.73].

**Recommandation (détail § 7)** : d'abord corriger les métadonnées et
l'erreur CAA (effort faible, prérequis à tout le reste) ; ensuite des
**groupes de pairs par défaut dans l'Analyse comparative, avec KPI grisés
quand une comparaison franchit un axe non comparable** et des **indicateurs
normalisés** à la place des montants bruts ; enfin, deux extractions
complémentaires ciblées (impact de la correction pour volatilité S.22.01,
ajustement d'absorption des pertes S.25.01 R0140/R0150).

---

## 2. Les 41 sociétés : métadonnées contrôlées et erreurs

**Méthode.** Pour chaque société, j'ai détecté automatiquement les codes de
gabarits QRT présents dans la partie du PDF qui la concerne (bornes
d'entité pour les rapports combinés Aéma et AG2R) [Vérifié PDF] :
- **périmètre** : un gabarit de groupe (`S.25.01.22`, `S.25.05.22`,
  `S.32.01.22`) = rapport de groupe ; sinon solo (`.21` / `.01`, et
  présence d'un gabarit MCR `S.28`, qui n'existe qu'en solo) ;
- **modèle de capital** : `S.25.01` = formule standard ; `S.25.05` = modèle
  interne (depuis la réforme du reporting, S.25.02/S.25.03 sont remplacés
  par S.25.05 « partiel ou intégral » [Vérifié PDF Allianz Vie p.90]) ;
  partiel/complet lu dans le texte (AXA : « modèle interne intégral »
  [Vérifié PDF annexe AFV p.1] ; Groupama : « modèle interne partiel
  groupe » [Vérifié PDF p.8]) ;
- **forme juridique** : lue dans le rapport (tableau AG2R p.9, liste des
  entités Aéma p.68, section A.1 des rapports autonomes) ;
- **activité** : recalculée à partir de la répartition du best estimate par
  ligne (`kpi_composants`, lignes S.02.01 R0540 non-vie, R0580 santé
  similaire non-vie, R0630 santé similaire vie, R0670 vie, R0710 UC)
  [Vérifié base], recoupée avec la répartition des primes. Règle : santé ≥
  60 % du BE → Santé/prévoyance ; sinon non-vie ≥ 75 % → Non-vie ; sinon vie
  ≥ 85 % → Vie ; sinon Mixte.

**Résultat** : 4 axes contrôlés, **23 sociétés sur 41 avec au moins une
erreur** — 16 erreurs d'activité, 7 champs `type` contradictoires avec la
forme juridique (« mutuelle » pour des SA/SE), 1 erreur de périmètre
(Sogécap), 1 erreur de pays (La Mondiale Europartner est luxembourgeoise,
contrôlée par le CAA [Vérifié PDF AG2R p.9]), 1 modèle de capital à
confirmer (Allianz Vie).

**Ce que veut dire « Mutuelle » dans `type_activite`** (AG.Mut, MMJ, MNPAF,
Nuoma, Prima) : rien de cohérent. MMJ, MNPAF et Nuoma sont des mutuelles
Livre II à 100 % santé non-vie [Vérifié PDF Aéma p.263, 291, 319 + base] ;
AG.Mut est une **union de mutuelles** santé [Vérifié PDF AG2R p.9] ; **Prima
est une SA** (dépendance, santé similaire vie) [Vérifié PDF AG2R p.9 et
p.53]. C'est une forme juridique (et fausse pour Prima) qui a fui dans le
champ activité.

**Le champ `type` mélange forme juridique et appartenance à un groupe**
(« entité (Groupe AG2R) », « mutuelle (Aéma Groupe) ») et se trompe pour 6
filiales Aéma qui sont des SA ou une SE (Abeille Vie, Abeille Épargne
Retraite, Abeille IARD & Santé, Macifilia, Thémis ; Macif Vie = SE)
[Vérifié PDF Aéma p.68, p.104] et pour Sogécap (« groupe » alors que le
rapport est solo : S.25.01.21 + S.28.01.01 [Vérifié PDF p.40-41]).

**Répartition contrôlée** : Activité — Vie 18, Santé/prévoyance 11,
Non-vie 9, Mixte 3 · Forme — SA/SE 22, Mutuelles/UM (code de la
mutualité) 8, SAM 4, Institutions de prévoyance 2, Groupes 5 · Périmètre —
solo 36, groupe 5 · Modèle — formule standard 35, modèle interne complet 4,
partiel 1, indéterminé 1 (Allianz Vie).

*vie = vie + UC + santé similaire vie ; non-vie = non-vie + santé similaire non-vie ; santé = santé similaire vie + non-vie (les colonnes se recoupent). Aéma Groupe est classé Mixte malgré 92 % de BE vie car 53 % de ses primes sont non-vie [Vérifié base].


| # | Société | Activité (base → contrôlée) | Part du BE : vie* / non-vie* / santé (%) | Forme juridique contrôlée [source] | Périmètre (gabarits) | Modèle de capital (gabarit SCR) | Erreurs de métadonnées |
|---|---|---|---|---|---|---|---|
| 1 | AG.Mut | Mutuelle → **Santé/prévoyance** | 0 / 100 / 100 | Union de mutuelles [Vérifié PDF AG2R p.9] | solo | FS — S.25.01 | activité Mutuelle→Santé/prévoyance |
| 2 | AG2R Prevoyance | Vie → **Santé/prévoyance** | 59 / 41 / 80 | Institution de prévoyance [Vérifié PDF AG2R p.9] | solo | FS — S.25.01 | activité Vie→Santé/prévoyance |
| 3 | AXA France IARD | Non-vie | 8 / 92 / 1 | SA [Raisonnement — non vérifiable (annexe QRT seule) — dénomination] | solo | MI complet — S.25.05 | — |
| 4 | AXA France Vie | Vie | 93 / 7 / 10 | SA [Raisonnement — non vérifiable (annexe QRT seule) — dénomination] | solo | MI complet — S.25.05 | — |
| 5 | Abeille Epargne Retraite | Vie | 100 / 0 / 0 | SA [Vérifié PDF Aéma p.68] | solo | FS — S.25.01 | type 'mutuelle (Aéma Groupe)' alors que forme SA |
| 6 | Abeille IARD Sante | Mixte → **Non-vie** | 4 / 96 / 2 | SA [Vérifié PDF Aéma p.68] | solo | FS — S.25.01 | activité Mixte→Non-vie; type 'mutuelle (Aéma Groupe)' alors que forme SA |
| 7 | Abeille Vie | Vie | 100 / 0 / 1 | SA [Vérifié PDF Aéma p.68] | solo | FS — S.25.01 | type 'mutuelle (Aéma Groupe)' alors que forme SA |
| 8 | Aema Groupe | Mixte | 92 / 8 / 2 | Groupe (SGAM) [Vérifié PDF Aéma p.11] | groupe | FS — S.25.01 | — |
| 9 | Aesio Mutuelle | Vie → **Santé/prévoyance** | 26 / 74 / 82 | Mutuelle (Livre II) [Vérifié PDF Aéma p.68] | solo | FS — S.25.01 | activité Vie→Santé/prévoyance |
| 10 | Allianz Vie | Vie | 100 / 0 / 6 | SA [Vérifié PDF p.8] | solo | MI (partiel/complet ?) — S.25.05 | scr_method partiel à confirmer (texte : tous risques modélisés) |
| 11 | Arpege Prevoyance | Vie → **Santé/prévoyance** | 63 / 37 / 76 | Institution de prévoyance [Vérifié PDF AG2R p.9] | solo | FS — S.25.01 | activité Vie→Santé/prévoyance |
| 12 | BPCE Assurances IARD | Non-vie | 1 / 99 / 12 | SA [Vérifié PDF p.8] | solo | FS — S.25.01 | — |
| 13 | BPCE Vie | Vie | 100 / 0 / 0 | SA [Vérifié PDF p.8] | solo | FS — S.25.01 | — |
| 14 | CNP Assurances | Vie | 99 / 1 / 2 | SA [Vérifié PDF p.8] | solo | FS — S.25.01 | — |
| 15 | Cardif Assurance Vie | Vie | 100 / 0 / 0 | SA [Raisonnement — non vérifiable (annexe QRT seule)] | solo | FS — S.25.01 | — |
| 16 | Cardif Assurances Risques Divers | Non-vie | 19 / 81 / 47 | SA [Raisonnement — non vérifiable (annexe QRT seule)] | solo | FS — S.25.01 | — |
| 17 | Covéa | Mixte | 67 / 33 / 3 | Groupe (SGAM) [Vérifié PDF p.6/p.9] | groupe | FS — S.25.01 | — |
| 18 | Crédit Agricole Assurances | Mixte → **Vie** | 98 / 2 / 1 | Groupe (SA holding) [Vérifié PDF rapport groupe] | groupe | FS — S.25.01 | activité Mixte→Vie |
| 19 | Generali IARD | Non-vie | 6 / 94 / 0 | SA [Vérifié PDF RSSF Generali Iard p.4] | solo | MI complet — S.25.05 (annexe scannée ; modèle interne confirmé [Vérifié PDF RSSF p.72/p.79]) | — |
| 20 | Generali Vie | Vie | 100 / 0 / 6 | SA [Vérifié PDF RSSF Generali Vie p.4] | solo | MI complet — S.25.05 (annexe scannée ; modèle interne confirmé [Vérifié PDF RSSF p.72/p.79]) | — |
| 21 | Groupama | Mixte | 76 / 24 / 8 | Groupe (tête : SAM / caisse de réassurance mutuelle) [Vérifié PDF p.9] | groupe | MI partiel — S.25.05 | — |
| 22 | La Mondiale | Vie | 98 / 2 / 4 | SAM [Vérifié PDF AG2R p.9] | solo | FS — S.25.01 | — |
| 23 | La Mondiale Europartner | Vie | 100 / 0 / 0 | SA (droit luxembourgeois) [Vérifié PDF AG2R p.9] | solo | FS — S.25.01 | pays France→Luxembourg |
| 24 | La Mondiale Partenaire | Vie | 100 / 0 / 0 | SA [Vérifié PDF AG2R p.9] | solo | FS — S.25.01 | — |
| 25 | MACIF SAM | Mixte → **Non-vie** | 20 / 80 / 14 | SAM [Vérifié PDF Aéma p.68] | solo | FS — S.25.01 | activité Mixte→Non-vie |
| 26 | MACSF prévoyance | Vie | 100 / 0 / 0 | SAM [Vérifié PDF p.4] | solo | FS — S.25.01 | — |
| 27 | MAIF | Mixte → **Non-vie** | 12 / 88 / 5 | SAM (cotisations variables) [Vérifié PDF p.11] | solo | FS — S.25.01 | activité Mixte→Non-vie |
| 28 | MGEN | Mixte → **Santé/prévoyance** | 40 / 60 / 92 | Mutuelle (Livre II) [Vérifié PDF p.7] | solo | FS — S.25.01 | activité Mixte→Santé/prévoyance |
| 29 | MMJ | Mutuelle → **Santé/prévoyance** | 0 / 100 / 100 | Mutuelle (Livre II) [Vérifié PDF Aéma p.291] | solo | FS — S.25.01 | activité Mutuelle→Santé/prévoyance |
| 30 | MNPAF | Mutuelle → **Santé/prévoyance** | 0 / 100 / 100 | Mutuelle (Livre II) [Vérifié PDF Aéma p.263] | solo | FS — S.25.01 | activité Mutuelle→Santé/prévoyance |
| 31 | Macif Sante Prevoyance | Vie → **Santé/prévoyance** | 88 / 12 / 62 | Mutuelle (Livre II) [Vérifié PDF Aéma p.68] | solo | FS — S.25.01 | activité Vie→Santé/prévoyance |
| 32 | Macif Vie | Vie | 100 / 0 / 0 | SE (société européenne) [Vérifié PDF Aéma p.68] | solo | FS — S.25.01 | type 'mutuelle (Aéma Groupe)' alors que forme SE (société européenne) |
| 33 | Macifilia | Non-vie | 15 / 85 / 0 | SA [Vérifié PDF Aéma p.68] | solo | FS — S.25.01 | type 'mutuelle (Aéma Groupe)' alors que forme SA |
| 34 | Nuoma | Mutuelle → **Santé/prévoyance** | 0 / 100 / 100 | Mutuelle (Livre II) [Vérifié PDF Aéma p.319] | solo | FS — S.25.01 | activité Mutuelle→Santé/prévoyance |
| 35 | Predica | Vie | 100 / 0 / 1 | SA [Vérifié PDF p.6] | solo | FS — S.25.01 | — |
| 36 | Prima | Mutuelle → **Santé/prévoyance** | 85 / 15 / 100 | SA [Vérifié PDF AG2R p.9] | solo | FS — S.25.01 | activité Mutuelle→Santé/prévoyance |
| 37 | SGAM AG2R LA MONDIALE | Vie | 95 / 5 / 9 | Groupe (SGAM) [Vérifié PDF AG2R p.9] | groupe | FS — S.25.01 | — |
| 38 | Sogécap | Mixte → **Vie** | 100 / 0 / 0 | SA [Vérifié PDF p.8] | solo (base : groupe) | FS — S.25.01 | périmètre groupe→solo; activité Mixte→Vie; type 'groupe' alors que rapport solo |
| 39 | SwissLife Assurance et Patrimoine | Vie | 100 / 0 / 0 | SA [Vérifié PDF p.10 ('société d'assurance mixte')] | solo | FS — S.25.01 | — |
| 40 | Themis | Non-vie | 0 / 100 / 0 | SA [Vérifié PDF Aéma p.104] | solo | FS — S.25.01 | type 'mutuelle (Aéma Groupe)' alors que forme SA |
| 41 | VIASANTE Mutuelle | Vie → **Santé/prévoyance** | 57 / 43 / 62 | Mutuelle (Livre II) [Vérifié PDF AG2R p.9] | solo | FS — S.25.01 | activité Vie→Santé/prévoyance |

---

## 3. Matrice KPI × axe

**Codes** : **C** comparable · **R** comparable avec réserve (même
définition, lecture à encadrer) · **N** non comparable tel quel · **NA** non
applicable (valeur structurellement nulle pour ce groupe).

| KPI | Activité | Forme juridique | Modèle de capital | Périmètre solo/groupe |
|---|---|---|---|---|
| ratio_scr | **R** — niveau « normal » propre à chaque métier (médiane santé 270 %, vie 202 %, non-vie 167 %) [Vérifié base] | **R** — mutuelles/SAM sans accès au marché des actions, structurellement plus capitalisées (médiane 276-302 % vs 195 % SA) [Vérifié base] | **R** — calibrage propre ; correction pour volatilité dynamique en modèle interne (Generali Vie : +46 pts) [Vérifié PDF RSSF Generali Vie p.9, p.36] | **R** — diversification intra-groupe, fonds propres non disponibles déduits |
| ratio_mcr | **R** — formule MCR différente vie / non-vie ; ratio dicté par le corridor | **R** — plancher absolu pour les petites structures (AG.Mut, Macifilia, Thémis) | **R** — MCR toujours en formule linéaire, mais corridor appliqué au SCR du modèle | **N** — en groupe, c'est le ratio au « SCR minimal consolidé » (S.23.01.22/R0650) [Vérifié base] |
| mcr | **R** | **R** | **R** | **N** — S.23.01.22/R0610 = somme des MCR solo, pas un MCR [Vérifié base] |
| scr_total | **R** — taille et profil | **C** | **R** — calibrage | **R** — pas la somme des SCR solo |
| fonds_propres_eligibles | **C** | **R** — fonds d'établissement, rappels de cotisations, certificats mutualistes | **C** | **R** — tests de disponibilité au niveau groupe |
| fonds_propres_t1_nr / t1_r / t2 / t3 | **C** | **R** — T1 restreint quasi inexistant chez les mutuelles ; T2/T3 peuvent être des fonds propres **auxiliaires** (Generali Vie : 500 M€ d'engagements du groupe classés T2+T3 [Vérifié PDF RSSF Generali Vie p.9] ; MAIF : rappel de cotisations possible [Vérifié PDF p.9]) | **C** | **R** |
| scr_marche, scr_contrepartie | **R** — extraits en **brut** (S.25.01 colonne C0110, avant absorption par les provisions) : en vie le module dépasse largement le SCR net (§ 4.4) | **C** | **N** — S.25.05 n'a pas ces modules ; valeurs de modèle interne issues des rapports narratifs, sur une autre base (§ 4.5) | **R** |
| scr_souscription_vie | **R / NA** — 0 structurel pour un non-vie pur | **C** | **N** | **R** |
| scr_souscription_sante | **R / NA** | **C** | **N** | **R** |
| scr_souscription_nonvie | **NA** pour les assureurs vie et santé (25 valeurs à 0, vrais zéros, cf. § 4.6) | **C** | **N** | **R** |
| scr_operationnel | **C** — formule factorielle commune en formule standard | **C** | **N** — scénarios en modèle interne ; AXA : ligne non diversifiée R0480 (§ 4.5) | **R** |
| scr_diversification | **R** — dépend du nombre de modules actifs (mono-santé ~24 %, groupes mixtes 30-43 % de la somme des modules) [Vérifié base] | **C** | **N** — base différente ; artefact AXA France Vie 114 % (§ 4.5) | **R** — inclut la diversification entre entités |
| best_estimate | **R** — vie : participation aux bénéfices future, options et garanties, UC ≈ actifs (0 à 70 % du BE selon les sociétés) ; non-vie : sinistres à court terme | **C** | **C** | **R** — éliminations intra-groupe |
| marge_risque | **R** — rapport RM/BE structurel : vie 1 %, non-vie 6 %, santé 11 % (médianes) [Vérifié base] | **C** | **R** — calculée avec le SCR du modèle | **R** |
| provisions_techniques | **R** — idem BE ; **mesure transitoire** sur provisions chez La Mondiale / SGAM AG2R (+8 pts de ratio au niveau SGAM) [Vérifié PDF AG2R p.84, p.93] | **C** | **C** | **R** |
| primes_acquises_brutes | **R** — en vie c'est surtout de la collecte d'épargne, en non-vie une prime de risque ; inclut la réassurance acceptée, y compris intra-groupe | **C** | **C** | **R** — consolidé |
| charge_sinistres | **N** — vie (S.05.01 R1610) = prestations : rachats, échéances, rentes ; non-vie = sinistres survenus. Un ratio S/P n'a de sens qu'en non-vie / santé non-vie | **C** | **C** | **R** |

### Réponses aux 8 questions du brief

**1. ratio_scr — formule standard vs modèle interne, mesures transitoires,
correction pour volatilité.** Comparable avec réserve. Le ratio a partout la
même définition et nos valeurs sont exactes, mais : (a) les modèles internes
(6 sociétés) ont une médiane plus basse (180 % vs 231 % en formule standard
[Vérifié base]) qui ne dit rien de la solidité relative — Gen Re, Moody's et
Fitch convergent sur ce point (§ 5) ; (b) la correction pour volatilité
pèse de +2 pts (Covéa [Vérifié PDF p.8, p.67]), +3 (MAIF [p.107]), +5
(Groupama [p.68]), +7 (CNP [p.6]), +11 (Generali IARD [RSSF p.8]), +15 (AXA
France IARD [rapport p.79]) à **+46 pts (Generali Vie, VA stochastique en
modèle interne [RSSF p.9, p.36])** ; (c) mesure transitoire sur provisions :
+8 pts pour SGAM AG2R [Vérifié PDF p.93]. Aéma (6 entités avec VA, aucune
mesure transitoire [Vérifié PDF p.57-58]), SwissLife, AXA France IARD,
Predica, Generali : pas de mesure transitoire [Vérifié PDF]. Un « ratio sans
mesures » n'est pas extrait aujourd'hui (S.22.01).

**2. mcr / ratio_mcr — même formule pour tous ?** La formule linéaire existe
en deux variantes (vie / non-vie, gabarits S.28.01 / S.28.02), puis le
résultat est borné entre 25 % et 45 % du SCR avec un plancher absolu
[Vérifié PDF MAIF p.107 : « Plancher (25 % SCR) », « Plafond (45 % SCR) »].
Sur nos 36 solos : **12 au plancher 25 %, 12 au plafond 45 %, 3 au plancher
absolu, 9 seulement entre les deux** [Vérifié base]. Pour 27 sociétés sur
36, le ratio MCR n'est donc qu'un multiple fixe du ratio SCR (×4 ou ×2,2)
— d'où la médiane de 942 % en santé. Pour les 5 groupes, ce n'est pas un
MCR (cf. matrice).

**3. Modules du SCR — que contient scr_marche, etc. ?**
- *Formule standard (35)* : S.25.01.21 (solo) / S.25.01.22 (groupe),
  lignes R0010-R0050, colonne **C0110 « capital de solvabilité requis
  brut »** — c'est-à-dire **avant** l'ajustement d'absorption des pertes par
  les provisions (R0140) et les impôts différés (R0150) [Vérifié PDF AG2R
  p.153 ; source_chapter « S.25.01.21/R00x0 » en base].
- *Modèle interne partiel (Groupama)* : 5 modules lus sur un schéma
  narratif p.74, `scr_souscription_nonvie` et `scr_diversification` sur le
  S.25.05.22 p.87 [Vérifié base] — deux sources différentes dans la même
  société [Raisonnement, à confirmer : même base ?].
- *Modèle interne complet (AXA ×2, Generali ×2)* : **S.25.03 n'existe
  plus** ; le gabarit S.25.05.21 ne contient pas de modules standard, mais
  des « risk types » propres (« Total market & credit risk », « Total Life
  & Health underwriting risk ») [Vérifié PDF annexe AFV p.10]. Nos
  scr_marche / scr_contrepartie / scr_souscription_vie viennent des rapports
  narratifs (Décisions 145-146), avec symbole d'avertissement.
- *Allianz Vie* : « Tableau 25 » du rapport, catégories propres
  (souscription, commercial, marché, contrepartie, opérationnel)
  [Vérifié PDF p.69].

**4. scr_diversification — comparable ? indicateur normalisé ?** Pas en
montant (dépend de la taille). Normalisé en **|diversification| / somme des
modules**, il est comparable **entre sociétés en formule standard
seulement** : 34 sociétés, de 3 % à 34 %, médiane 22 % [Vérifié base]. En
modèle interne la diversification n'est pas calculée sur les mêmes modules
(AXA France Vie : 114 %, artefact) — à exclure.

**5. primes_acquises_brutes, charge_sinistres — quelles lignes ?** Pour
toutes les sociétés : S.05.01 R0210 + R0220 + R0230 (non-vie, y compris
santé non-vie : affaires directes + réassurance proportionnelle + non
proportionnelle acceptées) + R1510 (vie) pour les primes ; R0310 + R0320 +
R0330 + R1610 pour les sinistres [Vérifié base, `kpi_composants`]. Le
sens diffère : en vie, R1510 inclut la collecte d'épargne et R1610 les
rachats/échéances/rentes. **Le S/P (sinistres / primes) n'a de sens que sur
les lignes non-vie (R03x0 / R02x0)** — calculable dès aujourd'hui depuis
`kpi_composants` pour les sociétés non-vie, santé et mixtes. Sur le total
actuel, le S/P va de 23 % (Cardif RD) à 140 % (Abeille Épargne Retraite,
assureur vie pur) — ce dernier n'a aucune signification [Vérifié base].

**6. best_estimate, marge_risque, provisions_techniques — même définition
vie / non-vie ?** Même définition légale (art. 77), contenu économique très
différent : en vie, le BE intègre les participations aux bénéfices futures
et les options (modèles stochastiques), et la part en unités de compte (BE ≈
valeur des actifs) varie de 0 à 70 % ; en non-vie ce sont des provisions
pour sinistres courtes. La marge de risque rapportée au BE est structurelle
(vie 1 %, non-vie 6 %, santé 11 %) — le comparer entre métiers ne mesure
rien. Milliman utilise d'ailleurs RM/BE **à l'intérieur** d'un panel
homogène (7 % en prévoyance-santé [Source : Milliman 2024, § 5]).

**7. Fonds propres et mutuelles.** Les mutuelles et SAM n'ont pas de
capital social : fonds d'établissement et réserve de réconciliation (T1),
rappels de cotisations pour les SAM à cotisations variables (fonds propres
auxiliaires T2, sur autorisation), certificats mutualistes (Groupama).
Médiane de la part T1 non restreint : 100 % chez les mutuelles du code de la
mutualité contre 85 % chez les SA [Vérifié base]. Ratio de structure
(T1/total) comparable avec réserve ; les montants par tier ne disent pas la
même chose selon la forme juridique.

**8. Solo vs groupe — même sens ?** Non pour le MCR (cf. matrice). Pour le
SCR et les fonds propres, même nature mais calcul consolidé
(diversification entre entités, intérêts minoritaires, fonds propres non
disponibles). Problème supplémentaire : **double comptage** — 21 entités
solo du panel sont des filiales de 3 groupes du panel (Aéma Groupe ⊃ 12
entités, SGAM AG2R ⊃ 8, Crédit Agricole Assurances ⊃ Predica). Toute
moyenne ou somme « du panel » compte deux fois ces activités.


---

## 4. Constats sur les données

### 4.1 Cohérence interne (bonne nouvelle)

- **Ratio SCR** : fonds propres éligibles / SCR recalculé = ratio stocké pour
  les 41 sociétés, écart maximal 0,5 pt (arrondi de publication)
  [Vérifié base].
- **MCR / SCR** : toutes les sociétés solo dans le corridor 25-45 % sauf 3
  au plancher absolu (AG.Mut 80 %, Macifilia 207 %, Thémis 256 %, déjà
  documentés Décision 085) [Vérifié base].
- **Rapport BE / SCR** cohérent avec l'activité partout (vie 12-65×, non-vie
  1-7×, santé 0,1-2×) **sauf Crédit Agricole Assurances : 0,02×** → erreur
  d'unité (§ 4.7).

### 4.2 Couverture et distributions par groupe

Groupes = métadonnées **contrôlées** (pas celles de la base). Format des
cellules : min / **médiane** / max (n). ⚠ n<5 : **aucune conclusion à
tirer**. `best_estimate`, `marge_risque` et `provisions_techniques` de
Crédit Agricole Assurances exclus (erreur d'unité).


#### Axe activité

| Groupe | n | KPIs non-NULL (moyenne sur 21) | KPIs NULL (détail) |
|---|---|---|---|
| Mixte | 3 | 19,7 | fonds_propres_t1_nr×1, fonds_propres_t1_r×1, fonds_propres_t2×1, fonds_propres_t3×1 |
| Non-vie | 9 | 20,4 | fonds_propres_t1_r×1, fonds_propres_t2×1, fonds_propres_t3×1, scr_souscription_sante×2 |
| Santé/prévoyance | 11 | 21,0 | — |
| Vie | 18 | 20,6 | fonds_propres_t3×1, scr_diversification×1, scr_souscription_nonvie×1, scr_souscription_sante×3, scr_souscription_vie×2 |

| Indicateur | Mixte (n) | Non-vie (n) | Santé/prévoyance (n) | Vie (n) |
|---|---|---|---|---|
| ratio_scr | 212 / **221** / 274 (3) ⚠n<5 | 128 / **167** / 953 (9) | 169 / **270** / 710 (11) | 144 / **202** / 521 (18) |
| ratio_mcr | 379 / **390** / 511 (3) ⚠n<5 | 213 / **355** / 1 125 (9) | 324 / **942** / 1 397 (11) | 351 / **490** / 2 084 (18) |
| scr_total (M€) | 6 021 / **6 063** / 15 058 (3) ⚠n<5 | 1 / **931** / 2 964 (9) | 5 / **101** / 1 461 (11) | 354 / **2 700** / 14 257 (18) |
| fonds_propres_eligibles (M€) | 12 861 / **16 481** / 33 252 (3) ⚠n<5 | 9 / **1 559** / 9 443 (9) | 34 / **274** / 3 441 (11) | 638 / **6 505** / 36 778 (18) |
| best_estimate (M€) | 69 035 / **84 033** / 105 865 (3) ⚠n<5 | 1 / **2 527** / 16 371 (9) | 3 / **445** / 7 573 (11) | 88 / **53 811** / 277 594 (17) |
| MCR/SCR (%) | 43 / **47** / 64 (3) ⚠n<5 | 25 / **42** / 256 (9) | 25 / **25** / 81 (11) | 25 / **44** / 45 (18) |
| part T1 non restreint (%) | 81 / **82** / 84 (2) ⚠n<5 | 66 / **93** / 100 (9) | 74 / **100** / 100 (11) | 66 / **82** / 100 (18) |
| marge_risque / BE (%) | 2 / **3** / 6 (3) ⚠n<5 | 0 / **6** / 13 (9) | 1 / **11** / 36 (11) | 1 / **1** / 16 (17) |
| diversification / somme modules (%) | 26 / **34** / 43 (3) ⚠n<5 | 5 / **23** / 91 (9) | 21 / **24** / 27 (11) | 3 / **20** / 114 (17) |
| ajustement LAC / SCR (%) | -149 / **-42** / -12 (3) ⚠n<5 | -35 / **-13** / -0 (7) | -10 / **-3** / 0 (11) | -524 / **-219** / -15 (14) |

#### Axe forme juridique (famille)

| Groupe | n | KPIs non-NULL (moyenne sur 21) | KPIs NULL (détail) |
|---|---|---|---|
| Groupe | 5 | 19,6 | fonds_propres_t1_nr×1, fonds_propres_t1_r×1, fonds_propres_t2×1, fonds_propres_t3×2, scr_diversification×1, scr_souscription_nonvie×1 |
| Institution de prévoyance | 2 | 21,0 | — |
| Mutuelle/UM (code mutualité) | 8 | 21,0 | — |
| SA/SE | 22 | 20,7 | scr_souscription_sante×5, scr_souscription_vie×2 |
| SAM | 4 | 20,2 | fonds_propres_t1_r×1, fonds_propres_t2×1, fonds_propres_t3×1 |

| Indicateur | Groupe (n) | Institution de prévoyance (n) | Mutuelle/UM (code mutualité) (n) | SA/SE (n) | SAM (n) |
|---|---|---|---|---|---|
| ratio_scr | 191 / **212** / 274 (5) | 169 / **220** / 271 (2) ⚠n<5 | 227 / **276** / 710 (8) | 128 / **195** / 953 (22) | 227 / **302** / 521 (4) ⚠n<5 |
| ratio_mcr | 366 / **390** / 511 (5) | 324 / **530** / 736 (2) ⚠n<5 | 882 / **1 056** / 1 397 (8) | 213 / **430** / 845 (22) | 757 / **997** / 2 084 (4) ⚠n<5 |
| scr_total (M€) | 5 234 / **6 063** / 15 058 (5) | 101 / **538** / 974 (2) ⚠n<5 | 5 / **137** / 1 461 (8) | 1 / **1 490** / 14 257 (22) | 440 / **2 393** / 2 964 (4) ⚠n<5 |
| fonds_propres_eligibles (M€) | 10 005 / **16 481** / 33 252 (5) | 274 / **960** / 1 646 (2) ⚠n<5 | 34 / **469** / 3 441 (8) | 9 / **2 334** / 36 778 (22) | 2 291 / **6 128** / 9 443 (4) ⚠n<5 |
| best_estimate (M€) | 69 035 / **79 854** / 105 865 (4) ⚠n<5 | 445 / **4 009** / 7 573 (2) ⚠n<5 | 3 / **160** / 1 906 (8) | 1 / **27 464** / 277 594 (22) | 88 / **5 189** / 31 439 (4) ⚠n<5 |
| MCR/SCR (%) | 31 / **44** / 64 (5) | 35 / **40** / 45 (2) ⚠n<5 | 25 / **25** / 81 (8) | 25 / **45** / 256 (22) | 25 / **26** / 32 (4) ⚠n<5 |
| part T1 non restreint (%) | 69 / **79** / 84 (4) ⚠n<5 | 74 / **84** / 94 (2) ⚠n<5 | 97 / **100** / 100 (8) | 66 / **85** / 100 (22) | 66 / **92** / 100 (4) ⚠n<5 |
| marge_risque / BE (%) | 1 / **3** / 6 (4) ⚠n<5 | 3 / **4** / 5 (2) ⚠n<5 | 1 / **12** / 36 (8) | 0 / **1** / 13 (22) | 1 / **7** / 16 (4) ⚠n<5 |
| diversification / somme modules (%) | 24 / **30** / 43 (4) ⚠n<5 | 25 / **25** / 26 (2) ⚠n<5 | 21 / **24** / 27 (8) | 5 / **21** / 114 (22) | 3 / **18** / 26 (4) ⚠n<5 |
| ajustement LAC / SCR (%) | -222 / **-95** / -12 (4) ⚠n<5 | -10 / **-6** / -3 (2) ⚠n<5 | -9 / **-1** / 0 (8) | -524 / **-168** / -0 (17) | -137 / **-19** / -13 (4) ⚠n<5 |

#### Axe modèle de capital

| Groupe | n | KPIs non-NULL (moyenne sur 21) | KPIs NULL (détail) |
|---|---|---|---|
| Formule standard | 35 | 20,7 | fonds_propres_t1_nr×1, fonds_propres_t1_r×2, fonds_propres_t2×2, fonds_propres_t3×3, scr_diversification×1, scr_souscription_nonvie×1 |
| Modèle interne | 6 | 19,8 | scr_souscription_sante×5, scr_souscription_vie×2 |

| Indicateur | Formule standard (n) | Modèle interne (n) |
|---|---|---|
| ratio_scr | 128 / **231** / 953 (35) | 153 / **180** / 274 (6) |
| ratio_mcr | 213 / **543** / 2 084 (35) | 351 / **373** / 431 (6) |
| scr_total (M€) | 1 / **877** / 15 058 (35) | 1 287 / **2 845** / 6 021 (6) |
| fonds_propres_eligibles (M€) | 9 / **1 801** / 36 778 (35) | 1 965 / **5 237** / 16 481 (6) |
| best_estimate (M€) | 1 / **5 189** / 277 594 (34) | 5 004 / **61 423** / 138 213 (6) |
| MCR/SCR (%) | 25 / **35** / 256 (35) | 40 / **45** / 64 (6) |
| part T1 non restreint (%) | 66 / **85** / 100 (34) | 81 / **94** / 100 (6) |
| marge_risque / BE (%) | 0 / **3** / 36 (34) | 1 / **2** / 3 (6) |
| diversification / somme modules (%) | 3 / **22** / 34 (34) | 18 / **45** / 114 (6) |
| ajustement LAC / SCR (%) | -524 / **-19** / 0 (34) | -12 / **-12** / -12 (1) ⚠n<5 |

#### Axe périmètre

| Groupe | n | KPIs non-NULL (moyenne sur 21) | KPIs NULL (détail) |
|---|---|---|---|
| groupe | 5 | 19,6 | fonds_propres_t1_nr×1, fonds_propres_t1_r×1, fonds_propres_t2×1, fonds_propres_t3×2, scr_diversification×1, scr_souscription_nonvie×1 |
| solo | 36 | 20,7 | fonds_propres_t1_r×1, fonds_propres_t2×1, fonds_propres_t3×1, scr_souscription_sante×5, scr_souscription_vie×2 |

| Indicateur | groupe (n) | solo (n) |
|---|---|---|
| ratio_scr | 191 / **212** / 274 (5) | 128 / **229** / 953 (36) |
| ratio_mcr | 366 / **390** / 511 (5) | 213 / **532** / 2 084 (36) |
| scr_total (M€) | 5 234 / **6 063** / 15 058 (5) | 1 / **904** / 14 257 (36) |
| fonds_propres_eligibles (M€) | 10 005 / **16 481** / 33 252 (5) | 9 / **1 821** / 36 778 (36) |
| best_estimate (M€) | 69 035 / **79 854** / 105 865 (4) ⚠n<5 | 1 / **5 487** / 277 594 (36) |
| MCR/SCR (%) | 31 / **44** / 64 (5) | 25 / **38** / 256 (36) |
| part T1 non restreint (%) | 69 / **79** / 84 (4) ⚠n<5 | 66 / **92** / 100 (36) |
| marge_risque / BE (%) | 1 / **3** / 6 (4) ⚠n<5 | 0 / **3** / 36 (36) |
| diversification / somme modules (%) | 24 / **30** / 43 (4) ⚠n<5 | 3 / **22** / 114 (36) |
| ajustement LAC / SCR (%) | -222 / **-95** / -12 (4) ⚠n<5 | -524 / **-15** / 0 (31) |


### 4.3 Ce que disent ces distributions

- **Taille** : le SCR va de 1 M€ (Thémis, Macifilia) à 15 Md€ (Covéa) —
  4 ordres de grandeur. Comparer des **montants** entre ces sociétés
  n'informe que sur la taille ; seuls des ratios ont un sens hors d'un
  groupe de taille homogène [Vérifié base].
- **Ratio MCR** : médiane 942 % en santé, 1 056 % chez les mutuelles du code
  de la mutualité, contre 490 % en vie — effet mécanique du plancher MCR à
  25 % du SCR (§ 3, question 2), pas une différence de solidité.
- **Marge de risque / BE** : vie 1 %, non-vie 6 %, santé 11 % — structurel.
- **Modèle interne** : n = 6 (4 complets, Groupama partiel, Allianz Vie) —
  à peine au-dessus du seuil de 5 et hétérogène (2 non-vie, 3 vie, 1 groupe
  mixte) : la médiane MI de 180 % n'est pas interprétable comme « les
  modèles internes sont moins solvables ».
- **Groupes** (n = 5) : le seul indicateur où ils se distinguent nettement
  est la taille.

### 4.4 Somme des modules ≠ SCR : l'ajustement d'absorption des pertes

Pour les 35 sociétés où tous les modules sont présents, j'ai calculé
**ajustement = SCR − (somme des modules + diversification + opérationnel)**
[Vérifié base]. Ce résidu correspond à l'absorption des pertes par les
provisions techniques (S.25.01 R0140) et par les impôts différés (R0150),
**non extraits**. Il vaut, en médiane : **−219 % du SCR en vie** (jusqu'à
−524 % pour Abeille Épargne Retraite, −401 % Macif Vie, −341 % BPCE Vie),
−13 % en non-vie, −3 % en santé.

Conséquence : en vie, les modules « bruts » (colonne C0110) sont plusieurs
fois plus grands que le SCR réellement exigé ; un graphique « composition
du SCR » qui rapporte les modules au SCR total, ou qui compare la part du
risque de marché entre un assureur vie et un assureur non-vie, est faux par
construction. La composition n'est comparable qu'en part de la **somme des
modules** (BSCR avant diversification), pas du SCR.

### 4.5 AXA France Vie : deux bases mélangées dans la même société

Dans le gabarit S.25.05.21 d'AXA France Vie [Vérifié PDF annexe AFV p.10],
chaque catégorie existe en deux versions : non diversifiée et
« diversified ». En base, nous avons :

| KPI | Valeur en base | Ligne S.25.05.21 correspondante | Base |
|---|---|---|---|
| scr_marche | 3 168 M€ | R0080 « Market & Credit risk - diversified » 3 168 162 k€ | diversifiée (intra-catégorie) |
| scr_contrepartie | 628 M€ | R0200 « Credit event risk… - diversified » 628 287 k€ | diversifiée |
| scr_souscription_vie | 2 969 M€ | R0410 « Total Life & Health… - diversified » 2 969 159 k€ | diversifiée |
| scr_operationnel | 956 M€ | R0480 « Total Operational risk » 955 999 k€ | **non diversifiée** |
| scr_diversification | −7 723 M€ | R0020 « Total diversification » (rapportée à R0110, 13 192 168 k€ de composantes non diversifiées) | **non diversifiée** |

Les trois premières valeurs (avec symbole d'avertissement, Décision 146)
viennent du tableau narratif E.2.3 [Vérifié PDF rapport AFV p.100], qui
coïncide exactement avec les lignes « diversified » ; les deux dernières
(sans symbole) viennent des lignes non diversifiées. D'où une
diversification égale à **114 % de la somme des modules** — un artefact. Le
même mélange existe très probablement chez AXA France IARD (opérationnel
620 M€ en base contre 263 M€ dans le tableau narratif) [Raisonnement, à
confirmer sur l'annexe AFI p.9]. **Les valeurs SCR d'un modèle interne qui
n'ont pas le symbole d'avertissement ne sont pas pour autant comparables à
la formule standard.**

### 4.6 Les zéros de scr_souscription_nonvie

25 sociétés ont `scr_souscription_nonvie = 0` [Vérifié base]. Pour 23 la
page source est citée (ligne S.25.01 R0050 lue à « 0 » ou « - », ou ligne
modèle interne lue à 0,00) : **vrais zéros**. Pour 2 (CNP Assurances,
MACSF prévoyance), aucune page n'est citée ; le zéro est cohérent avec
leur BE non-vie hors santé nul (R0540 = 0 [Vérifié base]) mais **n'est pas
traçable**. Attention : un assureur vie qui fait de la santé non-vie (CNP :
1,8 Md€ de BE santé non-vie) l'a dans le **module santé**, pas non-vie —
le zéro est légitime. Ce sont des zéros **structurels** : à afficher, mais à
exclure de toute moyenne « par module » qui mélange vie et non-vie.
MACSF prévoyance a 5 zéros sans page source (dont `scr_souscription_sante`
et 3 tiers de fonds propres) — à re-tracer.

### 4.7 Erreur de données : Crédit Agricole Assurances ×1/1000

`best_estimate` = 342,576, `marge_risque` = 6,909, `provisions_techniques`
= 349,485 « M€ » en base. Le tableau narratif D.2.1 dit explicitement
« (en millions d'euros) … Total Best Estimate brut 342 577 … Marge de
risque 6 909 » [Vérifié PDF p.53]. Cause : le gabarit S.02.01.02 p.66 est
étiqueté « En milliers d'euros » par la société alors que ses montants
sont en millions (290 602 d'investissements = 290 Md€) [Vérifié PDF p.66].
Valeurs correctes : 342 577 / 6 909 / 349 486 M€. Les autres KPIs CAA
(SCR, fonds propres, primes, sinistres) sont cohérents. **Non corrigé
(mission en lecture seule)**. Aucun contrôle actuel ne l'a vu : le plafond
de magnitude ne détecte que les valeurs trop grandes ; un contrôle
« BE / SCR dans une fourchette par activité » l'aurait attrapé.

### 4.8 Auto-correction : Décision 147 (Allianz Vie) à revoir

Hier, j'ai inséré scr_marche, scr_contrepartie et scr_diversification
d'Allianz Vie **sans** symbole d'avertissement, au motif que la société
utilise un modèle interne **partiel**. Ce motif est fragile : le gabarit
s'intitule « modèle interne (partiel ou intégral) » [Vérifié PDF p.90] et
le rapport dit que le modèle interne d'Allianz « permet de capter et de
modéliser correctement l'ensemble des risques financiers et assurantiels »
et modélise aussi le risque opérationnel par scénarios [Vérifié PDF p.70,
p.73] — ce qui ressemble à un modèle complet. Le tableau source (Tableau 25)
est un tableau de **modèle interne** (catégories propres, diversification
intra-catégorie incluse). Les 3 valeurs sont cohérentes entre elles (même
tableau, recoupement exact jusqu'au SCR) mais **de même nature que celles
d'AXA et Generali**. Recommandation : leur ajouter le symbole
d'avertissement et marquer `scr_method` « à confirmer » (décision n° 8).

### 4.9 Gravité : part des comparaisons concernées

Sur les **820 paires** possibles entre 41 sociétés : **87,6 %** diffèrent
sur au moins un des 4 axes (contrôlés) ; seulement **102 paires (12,4 %)**
sont identiques sur les 4 [Vérifié base]. Part des paires qui franchissent
un axe **non comparable (N)** pour chaque KPI :


| KPI | Sociétés avec valeur | Paires | % paires franchissant un axe **N** | % paires différant sur ≥ 1 axe (N ou R) |
|---|---|---|---|---|
| charge_sinistres | 41 | 820 | **57,8 %** | 87,6 % |
| scr_souscription_nonvie | 40 | 780 | **26,2 %** | 87,1 % |
| scr_diversification | 40 | 780 | **26,2 %** | 87,1 % |
| scr_marche | 41 | 820 | **25,6 %** | 87,6 % |
| scr_contrepartie | 41 | 820 | **25,6 %** | 87,6 % |
| scr_operationnel | 41 | 820 | **25,6 %** | 87,6 % |
| ratio_mcr | 41 | 820 | **22,0 %** | 87,6 % |
| mcr | 41 | 820 | **22,0 %** | 87,6 % |
| scr_souscription_vie | 39 | 741 | **18,9 %** | 86,6 % |
| scr_souscription_sante | 36 | 630 | **5,6 %** | 84,4 % |
| ratio_scr | 41 | 820 | **0,0 %** | 87,6 % |
| fonds_propres_eligibles | 41 | 820 | **0,0 %** | 87,6 % |
| scr_total | 41 | 820 | **0,0 %** | 87,6 % |
| primes_acquises_brutes | 41 | 820 | **0,0 %** | 87,6 % |
| best_estimate | 40 | 780 | **0,0 %** | 87,1 % |
| marge_risque | 40 | 780 | **0,0 %** | 87,1 % |
| provisions_techniques | 40 | 780 | **0,0 %** | 87,1 % |
| fonds_propres_t1_nr | 40 | 780 | **0,0 %** | 87,1 % |
| fonds_propres_t1_r | 39 | 741 | **0,0 %** | 86,5 % |
| fonds_propres_t2 | 39 | 741 | **0,0 %** | 86,5 % |
| fonds_propres_t3 | 38 | 703 | **0,0 %** | 85,9 % |


**Impact sur les KPIs clés.** Le **ratio SCR** n'a aucun axe « N » mais
87,6 % de ses comparaisons franchissent un axe « R » (VA de 2 à 46 pts,
forme juridique, modèle interne) : il reste le meilleur indicateur
transversal à condition d'être lu par groupe de pairs. **La charge de
sinistres** est le KPI le plus touché (57,8 % des paires non
comparables). **Les modules du SCR** : ~25 % des paires opposent formule
standard et modèle interne — et, en plus, la composition « brute » n'est
pas comparable entre vie et non-vie (§ 4.4). **MCR / ratio MCR** : 22 % des
paires opposent un groupe à un solo, et le ratio MCR est mécanique pour
75 % des solos.

**Taille des groupes de pairs possibles** (4 axes contrôlés) :


| Cellule de pairs (activité · modèle · périmètre · forme) | n |
|---|---|
| Vie · FS · solo · SA/SE | 11 |
| Santé/prévoyance · FS · solo · Mutuelle/UM (code mutualité) | 8 |
| Non-vie · FS · solo · SA/SE | 5 |
| Vie · MI · solo · SA/SE | 3 ⚠ n<5 |
| Santé/prévoyance · FS · solo · Institution de prévoyance | 2 ⚠ n<5 |
| Non-vie · MI · solo · SA/SE | 2 ⚠ n<5 |
| Mixte · FS · groupe · Groupe | 2 ⚠ n<5 |
| Vie · FS · groupe · Groupe | 2 ⚠ n<5 |
| Vie · FS · solo · SAM | 2 ⚠ n<5 |
| Non-vie · FS · solo · SAM | 2 ⚠ n<5 |
| Mixte · MI · groupe · Groupe | 1 ⚠ n<5 |
| Santé/prévoyance · FS · solo · SA/SE | 1 ⚠ n<5 |


Seules **3 cellules ont au moins 5 sociétés**. Si on ne retient que
activité × modèle × périmètre (la forme juridique devenant une simple
réserve), on obtient 3 groupes de pairs exploitables — **Vie / formule
standard / solo (13)**, **Santé-prévoyance / formule standard / solo (11)**,
**Non-vie / formule standard / solo (7)** — qui couvrent 31 sociétés ; les 10
autres (5 groupes, 5 sociétés en modèle interne) sont dans des groupes de
moins de 5.

---

## 5. Recherche externe — comment font les autres

| Source | Groupes de pairs | KPIs comparés / évités | Mises en garde | Échantillon |
|---|---|---|---|---|
| **Milliman — Étude SFCR 2024 Prévoyance & Santé** (sept. 2025) [Source : [PDF](https://edge.sitecorecloud.io/millimaninc5660-milliman6442-prod27d5-0001/media/Milliman/PDFs/2025-Articles/9-12-25_Etude-MLM-SFCR-2024.pdf), lu] | Par **type d'organisme** : assureurs / mutuelles / institutions de prévoyance ; panel restreint aux entités à dominante prévoyance-santé, **toutes en formule standard** | Ratios SCR/MCR par type (assureurs 261 %, mutuelles 259 %, IP 245 %) ; indicateurs **normalisés** : SCR / (cotisations + BE nets), marge de risque en % du BE (7 %), répartition des modules ; sinistralité par type | Exclut les entités « non représentatives » ; note que la VA concerne 25 entités sur 194 (+1 pt en moyenne) ; panel variable d'une année à l'autre | 194 entités (26 / 140 / 28) |
| **Milliman — Étude SFCR 2024 marché non-vie français** [Source : [page](https://www.milliman.com/fr-FR/insight/etude-sfcr-2024-sur-le-marche-francais-non-vie), lue] | Par **modèle d'affaires** : bancassureurs / mutualistes / traditionnels / spécialisés ; santé exclue | Principaux indicateurs S2 par groupe | Pas de mise en garde explicite sur la page | 54 acteurs (9 / 18 / 12 / 15), ~80 % du marché non-vie hors santé |
| **Milliman — 2025 SFCR life UK & EU** [Source : [page](https://www.milliman.com/fr-FR/insight/2025-sfcr-life-uk-eu), lue] | Assureurs **vie seulement**, par pays (UE vs Royaume-Uni) | Fonds propres, couverture SCR/MCR, **mesures de garanties de long terme (LTG)** traitées à part | Différences de gabarits UE/UK signalées | 652 sociétés, 32 pays |
| **EIOPA — Insurance Statistics, note Solo/Annual** [Source : [PDF](https://www.eiopa.europa.eu/assets/insurance-statistics/SA_Accompanying_note.pdf), lu] et **European Insurance Overview 2025** [Source : [page](https://www.eiopa.europa.eu/assets/insurance-overview-report/European_Insurance_Overview_2025.html), non lue en entier — trop volumineuse] | Statistiques **solo et groupe publiées séparément** ; provisions ventilées en 5 catégories (vie, UC, non-vie, santé similaire vie, santé similaire non-vie) ; d'après le résumé de recherche, l'édition 2024 présente le ratio SCR par type d'entreprise | Ratios SCR/MCR en **moyenne pondérée + intervalle interquartile** | Distributions non pondérées dans l'Overview (chaque entreprise compte pareil) | Ensemble du marché EEE |
| **Gen Re (2016)** [Source : [article](https://www.genre.com/us/knowledge/publications/2016/september/solvency-ii-why-we-must-be-rational-when-comparing-solvency-ratios-en), lu] | — | Ratio SCR | Comparable seulement à **méthode identique et profils proches** ; un ratio isolé ne suffit jamais ; le lien ratio ↔ probabilité de défaut n'est pas linéaire | — |
| **Moody's (mars 2016)** [Source : [Bermuda Re Magazine](https://www.bermudareinsurancemagazine.com/news/solvency-ii-ratio-comparability-hindered-by-diverging-choices-says-moody-s-2460), lu] | — | Ratio SCR | Modèles internes : hypothèses incohérentes ; mesures transitoires ; choix divergents sur VA / ajustement égalisateur, **rarement quantifiés** | — |
| **Fitch (mai 2016)** [Source : [Life Insurance International](https://www.lifeinsuranceinternational.com/news/fitch-check-under-the-bonnet-of-solvency-ii-ratios-4891706), lu] | — | Ratio SCR **« fully loaded »** (sans mesures transitoires) + sensibilités | Même sans transitoires, pas forcément comparables ; Fitch s'appuie sur son propre modèle (Prism) | — |
| **AM Best** [Source : [Post Online](https://postonline.co.uk/regulation/3220571/solvency-ii-ratios-not-comparable-across-eu-and-wont-be-used-in-ratings-says-am-best) — d'après résumé de recherche, non ouvert] | — | — | Ratios S2 jugés non comparables entre pays (approbation des modèles internes, VA, ajustement égalisateur), non utilisés en notation | — |
| **EIOPA — étude comparative des modèles internes non-vie (2024)** [Source : [page](https://www.eiopa.europa.eu/eiopa-analyses-internal-models-non-life-underwriting-risk-2024-01-04_et) — d'après résumé de recherche] | Modèles internes entre eux | Risque de souscription non-vie | Entreprises « hors norme » signalées aux superviseurs | 75 entreprises, 31 groupes |
| **Fræris / Onepoint — Benchmark SFCR 2025** [Source : liste fournie par l'utilisateur dans cette session ; **non retrouvée en ligne**] | **Entités solo uniquement** (57), FRPS traités à part | — | — | 57 solo + FRPS |

**Non trouvés** malgré recherche : étude Nexialog, « Internal Model
Comparator » de Solvency II Wire. Les avis d'agences de notation datent de
2016 [à confirmer avec leurs méthodologies actuelles].

**Ce qui se dégage (reformulé)** : aucun de ces travaux ne compare
« tout le monde avec tout le monde ». Tous (1) **segmentent** — par métier
(vie seule, non-vie hors santé, prévoyance-santé), par type d'organisme ou
par modèle d'affaires ; (2) **séparent solo et groupe** ; (3) restreignent
souvent à la **formule standard** pour les comparaisons fines ; (4)
privilégient des **indicateurs normalisés** (SCR / (primes + BE), RM % BE,
répartition des modules) aux montants ; (5) côté agences, demandent un
ratio **sans mesures transitoires** et se méfient des modèles internes.
Aucune source ne fixe explicitement un échantillon minimum ; les plus
petits groupes publiés par Milliman ont 9 entités — notre seuil de 5 est
un plancher, pas une cible.

---

## 6. Options

| # | Option | Effort | Risques | Ce que l'interface recevrait |
|---|---|---|---|---|
| 0 | **Prérequis : corriger les métadonnées** (23 sociétés) et l'erreur CAA ; scinder `type` en `forme_juridique` + `groupe_parent` ; nouvelle taxonomie d'activité à 4 classes | **F** | Faible ; règles d'activité à valider (frontières, ex. CAA, SGAM AG2R) | Champs propres par société |
| 1 | **Avertissements seulement** (étendre le symbole actuel) | **F** | Les comparaisons trompeuses restent possibles, l'utilisateur doit lire chaque note | Notes par KPI/société |
| 2 | **Groupes de pairs par défaut + KPI grisés** : l'Analyse comparative s'ouvre sur le groupe de pairs de la société choisie ; quand la sélection franchit un axe « N » pour un KPI, ce KPI est grisé avec la raison ; « n < 5 » affiché | **M** | Petits groupes (10 sociétés hors des 3 groupes ≥ 5) ; règles de la matrice à maintenir | `groupe_pairs` par société + matrice de compatibilité |
| 3 | **Indicateurs normalisés** à la place des montants dans les vues transversales : ratio SCR (+ sans VA quand connu), composition en % de la somme des modules (formule standard seulement), diversification / somme des modules, RM / BE, part T1, SCR / (primes + BE), S/P non-vie seulement, position du MCR dans le corridor | **M** | Certains ratios n'ont de sens que dans un groupe (RM/BE, S/P) | Nouveaux champs dérivés, calculés côté back-end |
| 4 | **Changements d'extraction** : (a) S.25.01 R0140/R0150 (absorption des pertes) ; (b) S.22.01 (impact VA / transitoires → ratio « fully loaded ») ; (c) modèle interne : un **jeu cohérent** de lignes S.25.05 (toutes « diversified » + diversification inter-risques, ou toutes non diversifiées), jamais un mélange ; (d) S/P non-vie à partir de `kpi_composants` ; (e) contrôle « BE / SCR par activité » | **D** | Volume (41 sociétés, PDF scannés pour certains) ; correspondance catégories modèle interne → modules standard toujours approximative | Champs supplémentaires + `base_calcul` par KPI |

**Format d'export proposé (non implémenté)** — un bloc à ajouter à
`donnees-extraites.json` :

```json
{
  "metadonnees": {
    "AXA France Vie": {
      "activite": "Vie", "forme_juridique": "SA", "perimetre": "solo",
      "modele_capital": "modele_interne_complet", "groupe_parent": null,
      "pays": "France", "groupe_pairs": "vie-MI-solo",
      "va": {"utilise": true, "impact_ratio_pts": null},
      "mesure_transitoire_pt": false
    }
  },
  "compatibilite": {
    "charge_sinistres": {
      "activite": {"verdict": "N", "note": "Vie = prestations (rachats, échéances), non-vie = sinistres"},
      "forme": {"verdict": "C"}, "modele": {"verdict": "C"}, "perimetre": {"verdict": "R"}
    }
  },
  "kpisParSociete": { "...": { "scr_marche": { "...": "...", "base_calcul": "MI_diversifie_avant_impot" } } }
}
```

Le front n'aurait alors qu'une règle à appliquer : pour un KPI et deux
sociétés, prendre le pire verdict sur les axes où elles diffèrent.

---

## 7. Recommandation et décisions à prendre

**Recommandation** : **Option 0 tout de suite** (sans elle, aucun
regroupement n'est fiable), puis **2 + 3 ensemble** (groupes de pairs par
défaut, KPI grisés, indicateurs normalisés), puis **4a + 4b** (absorption
des pertes et ratio sans VA), qui lèvent les deux plus grosses réserves sur
le ratio SCR et les modules. L'option 1 seule ne suffit pas : elle laisse
l'outil afficher par défaut des comparaisons fausses (charge de sinistres
vie vs non-vie, MCR de groupe vs MCR solo).

**DÉCISIONS À PRENDRE** (réponse oui / non ou choix fermé) :

1. Corriger les métadonnées des **23 sociétés** listées au § 2 ? (oui / non)
2. Corriger l'erreur d'unité **Crédit Agricole Assurances** (BE, RM, PT ×1000) ? (oui / non)
3. Adopter la taxonomie d'activité **Vie / Non-vie / Santé-prévoyance / Mixte** (calculée sur la répartition du BE) à la place de `type_activite` ? (oui / non)
4. Remplacer le champ `type` par deux champs `forme_juridique` et `groupe_parent` ? (oui / non)
5. Analyse comparative : groupe de pairs **par défaut** (activité × modèle × périmètre) ? (oui / non)
6. **Griser** un KPI quand la comparaison franchit un axe « N » de la matrice ? (oui / non)
7. MCR des 5 groupes : (a) renommer « SCR minimal consolidé », (b) masquer, (c) laisser tel quel ?
8. **Revoir la Décision 147** : ajouter le symbole d'avertissement aux 3 valeurs SCR d'Allianz Vie et marquer `scr_method` « à confirmer » ? (oui / non)
9. Modules SCR des modèles internes (AXA, Generali, Allianz, Groupama) : (a) garder les valeurs narratives avec avertissement, (b) passer à un jeu cohérent issu du S.25.05, (c) masquer hors de la fiche individuelle ?
10. Lancer l'extraction **S.22.01** (impact VA / transitoires, ratio « fully loaded ») ? (oui / non)
11. Lancer l'extraction **S.25.01 R0140/R0150** (absorption des pertes) ? (oui / non)
12. Exclure les **groupes** des moyennes de panel (double comptage avec 21 filiales) ? (oui / non)
13. Seuil minimal d'un groupe de pairs pour afficher une médiane : **5** ou **9** (plus petit groupe Milliman) ?

---

## 8. Limites

- **Activité** : la règle de classement repose sur la répartition du BE
  (proxy des engagements) recoupée avec les primes ; elle peut se discuter
  aux frontières (Crédit Agricole Assurances et SGAM AG2R classés « Vie »,
  AXA France Vie « Vie » malgré 40 % de primes santé/prévoyance) [Raisonnement].
- **Formes juridiques non vérifiables dans nos PDF** : AXA France Vie/IARD
  et Cardif ×2 (annexes QRT seules) — « SA » d'après la dénomination
  [Raisonnement, à confirmer].
- **Allianz Vie** : partiel ou complet non tranché (§ 4.8).
- **Groupama** : modules issus de deux pages différentes (schéma p.74 et
  S.25.05.22 p.87) — base commune non vérifiée.
- **AXA France IARD** : le mélange de bases (§ 4.5) est déduit par analogie
  avec AXA France Vie, non vérifié ligne à ligne ; son S/P de 119,5 % n'a
  pas été vérifié.
- **PDF image** : une partie du rapport Aéma et les annexes Generali sont
  scannées ; la détection automatique des gabarits n'y fonctionne pas (bornes
  d'entité utilisées pour Aéma, périmètre Generali déduit).
- **Effet VA** : relevé en points de ratio pour 7 sociétés seulement (celles qui le chiffrent
  en texte) ; pour les autres il faudrait le gabarit S.22.01 (option 4b).
- **Matrice** : les verdicts R/N sont un jugement d'actuaire argumenté, pas
  une règle réglementaire ; la mesure de gravité (§ 4.9) en dépend
  directement.
- **Sources externes** : les avis d'agences datent de 2016 ; l'EIOPA
  Overview 2025 n'a pu être lu en entier ; Fræris/Onepoint, Nexialog et
  Solvency II Wire non retrouvés en ligne.
- **Lecture seule** : rien n'a été corrigé dans la base, les exports ou le
  front-end ; toutes les corrections proposées sont soumises aux décisions
  ci-dessus.
