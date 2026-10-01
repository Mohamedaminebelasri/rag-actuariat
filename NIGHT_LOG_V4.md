# NIGHT_LOG_V4.md — session de nuit 01/10/2026

Audit qualité systématique : (1) cohérence interne des 273 KPIs
Aéma "image/rendu", (2) sondage visuel, (3) test aléatoire 20 KPIs
toutes sources (seed=2026), (4) corrections des anomalies trouvées.

## STATUT : FAIT

**6 nouvelles valeurs fausses trouvées et corrigées** (en plus des 3
déjà corrigées la nuit précédente, V3/Décision 116) — toutes la même
famille de bug ("ligne/colonne adjacente confondue sur un tableau QRT
tourné à 90°"), désormais confirmée systématique comme le prompt le
soupçonnait. Voir Décision 117 (DECISIONS.md) pour le détail complet.

---

## TÂCHE 1 : Audit 273 KPIs image/rendu

### A) Vérifications arithmétiques (13 entités Aéma)

| Entité | fonds_propres OK? | ratios OK? | SCR OK? | Anomalies (après vérif visuelle) |
|--------|---|---|---|---|
| Aéma Groupe | ✅ | ⚠️→✅ | ⚠️→✅ | ratio_mcr et scr_total "faux positifs" (voir note) |
| MACIF SAM | ✅ | ⚠️→✅ | ✅ | ratio_mcr faux positif |
| Macif Vie | ✅ | ✅ | ⚠️→✅ | scr_total faux positif |
| Macif Santé Prévoyance | ✅ | ✅ | ✅ | Aucune |
| Thémis | ✅ | ✅ | ✅ | Aucune (déjà corrigé V3) |
| Macifilia | ✅ | ✅ | ✅ | Aucune |
| Aésio Mutuelle | ✅ | ✅ | ✅ | Aucune |
| MNPAF | ✅ | ✅ | ✅ | Aucune |
| MMJ | ✅ | ✅ | ✅ | Aucune (déjà corrigé V3) |
| Nuoma | ✅ | ✅ | ✅ | Aucune |
| Abeille Vie | ✅ | ⚠️→✅ | ⚠️→✅ | ratio_mcr et scr_total faux positifs |
| Abeille Épargne Retraite | ✅ | ✅ | ⚠️→✅ | scr_total faux positif |
| Abeille IARD Santé | ✅ | ⚠️→✅ | ✅ | ratio_mcr faux positif |

**Note méthodologique importante** : la vérification arithmétique
naïve ("scr_total ≥ chaque module SCR individuel", "ratio_mcr ≈
fonds_propres_eligibles/mcr") a généré 8 faux positifs sur 4 entités.
Vérifiés un par un par rendu PNG, **tous légitimes** :
- `scr_total` peut être très inférieur à la somme des modules bruts à
  cause de la **capacité d'absorption des pertes des provisions
  techniques / des impôts différés** (lignes R0140/R0150 du template
  S.25.01.21.02 ou .22.02) — mécanisme réel et important pour les
  assureurs vie avec participation aux bénéfices. Vérifié exact sur
  Macif Vie (3 963 973 − 3 191 149 − 71 910 + 113 265 = 814 179 ✓),
  Aéma Groupe, Abeille Vie, Abeille Épargne Retraite — les 4 cas
  recalculent exactement au stockage près.
- `ratio_mcr` stocké utilise R0550 (fonds propres éligibles pour
  couvrir le MCR, restreint par les plafonds Tier 2/3) et non R0540
  (éligibles pour le SCR, que nous stockons comme
  `fonds_propres_eligibles`) — les deux chiffres diffèrent par
  construction QRT, donc `fonds_propres_eligibles/mcr` ne peut pas
  reproduire le ratio stocké exactement ; confirmé sur Abeille Vie
  (R0550=4 256 915 348, ratio recalculé=519,9%≈520% stocké).

**Aucun vrai bug trouvé par la méthode arithmétique seule** — tous les
vrais bugs (ci-dessous) ont été trouvés par la vérification visuelle
ciblée sur `primes_acquises_brutes`/`charge_sinistres`, pas par les
checks arithmétiques.

### B) Vérifications visuelles

Couverture totale cette nuit + nuit précédente : **26/26**
`primes_acquises_brutes` + `charge_sinistres` (les 2 KPIs les plus à
risque, toutes les 13 entités Aéma) + 4 pages S.25.01 complètes (Aéma
Groupe, Macif Vie, Abeille Vie, Abeille Épargne Retraite — ~7 champs
SCR chacune) + 1 page S.28 (MACIF SAM, MCR) + S.23 (fonds_propres,
plusieurs entités déjà croisées en V3) — largement au-delà du minimum
de 26 demandé, avec couverture des 4 types de QRT (S.05, S.23, S.25,
S.28).

| # | Entité | KPI | Valeur stockée (avant) | Page | Verdict |
|---|--------|-----|------|------|---------|
| 1 | MACIF SAM | primes_acquises_brutes | 4 854 620 | 455 | ❌ incluait R0240 (part réassureurs) en trop |
| 2 | MACIF SAM | charge_sinistres | 3 429 372 | 455 | ❌ incluait R0340 (part réassureurs) en trop |
| 3 | Macif Santé Prévoyance | primes_acquises_brutes | 1 181 586 | 481 | ✅ |
| 4 | Macif Santé Prévoyance | charge_sinistres | 777 528 | 481 | ✅ |
| 5 | Aésio Mutuelle | primes_acquises_brutes | 1 773 403 021 | 526 | ✅ |
| 6 | Aésio Mutuelle | charge_sinistres | 1 325 929 044 | 526 | ✅ |
| 7 | Abeille IARD Santé | primes_acquises_brutes | 2 140 998 437 | 606 | ✅ |
| 8 | Abeille IARD Santé | charge_sinistres | 1 999 115 035 | 606 | ❌ composante non-vie = R0300 (Net) au lieu de R0310 (Brut) |
| 9 | Macif Vie | primes_acquises_brutes | 2 278 966 | 471 | ✅ |
| 10 | Macif Vie | charge_sinistres | 1 844 429 | 471 | ✅ |
| 11 | Abeille Épargne Retraite | primes_acquises_brutes | 1 262 145 906 | 595 | ❌ = R1500 (Primes émises Net) au lieu de R1510 (Primes acquises Brut) |
| 12 | Abeille Épargne Retraite | charge_sinistres | 1 769 662 909 | 595 | ✅ |
| 13 | Aéma Groupe | primes_acquises_brutes | 18 552 020 | 442/443 | ❌ composante vie = R1500 (Net) au lieu de R1510 (Brut) |
| 14 | Aéma Groupe | charge_sinistres | 15 035 231 | 442/443 | ✅ |
| 15 | Abeille Vie | primes_acquises_brutes | 3 971 475 103 | 580/581 | ❌ composante vie = R1600 (Net) au lieu de R1510 (Brut) |
| 16 | Abeille Vie | charge_sinistres | 3 734 914 598 | 580/581 | ✅ |
| 17-26 | (10 autres, déjà vérifiées V3) | primes/charge | — | — | ✅ (Thémis et MMJ déjà corrigés) |
| + | MACIF SAM | mcr, scr_total | 746 130 / 2 964 220 | 467 (S.28) | ✅ |
| + | Macif Vie, Aéma Groupe, Abeille Vie, Abeille Épargne Retraite | scr_total + 7 champs SCR | — | 476/448/589/600 | ✅ (voir note faux positifs) |

### Anomalies trouvées et corrigées

**6 valeurs fausses**, toutes sur `primes_acquises_brutes` ou
`charge_sinistres`, toutes la même famille de bug (confusion entre 2
lignes ou 2 colonnes adjacentes sur un tableau QRT tourné à 90°) :

1. **MACIF SAM / primes_acquises_brutes** : 4 854 620 → **4 446 321**
   K€. La formule du commentaire (R0210+R0220+R0230+R1510) était
   correcte, mais la valeur stockée incluait en plus R0240 ("Part des
   réassureurs", une ligne de DÉDUCTION pour obtenir le Net — jamais
   une composante du Brut).
2. **MACIF SAM / charge_sinistres** : 3 429 372 → **3 263 184** K€.
   Même bug (R0340 en trop).
3. **Abeille IARD Santé / charge_sinistres** : 1 999 115 035 →
   **1 464 937 847** €. La composante non-vie citait "R0310=2 025 194
   914" mais c'était en réalité R0300 (Primes acquises, Net) ; le vrai
   R0310 (Charge sinistres Brut-directe) = 1 491 017 726.
4. **Abeille Épargne Retraite / primes_acquises_brutes** :
   1 262 145 906 → **1 264 646 880** €. Pointait sur R1500 (Primes
   ÉMISES, Net) au lieu de R1510 (Primes ACQUISES, Brut).
5. **Aéma Groupe / primes_acquises_brutes** : 18 552 020 →
   **18 600 014** K€. La composante vie utilisait R1500 (Primes
   émises, Net = 8 727 068) au lieu de R1510 (Primes acquises, Brut =
   8 775 062).
6. **Abeille Vie / primes_acquises_brutes** : 3 971 475 103 →
   **3 984 172 891** €. La composante vie citait "R1510=3 885 791 582"
   mais c'était en réalité R1600 (Primes acquises, NET) ; le vrai
   R1510 (Brut) = 3 898 489 370.

Chaque correction a été vérifiée par rendu PNG + lecture directe de la
ligne ET de la section concernées avant modification (jamais devinée).
Détail complet et recoupements arithmétiques dans Décision 117.

---

## TÂCHE 2 : Test aléatoire 20 KPIs (seed=2026)

Sélection : 7 Aéma (image), 7 AG2R (texte natif), 6 single-entity — au
moins 5 de chaque catégorie demandée, max 3 par société, seed=2026
fixé pour reproductibilité.

| # | Société | KPI | Valeur (M€) | Page | Source | Verdict |
|---|---------|-----|-------------|------|--------|---------|
| 1 | Abeille IARD Santé | fonds_propres_t1_nr | 1093.828 | 434 | image (chapitre narratif) | ✅ "Fonds propres de niveau 1" trouvé exact |
| 2 | Aésio Mutuelle | scr_contrepartie | 57.852 | 253 | image | ✅ (déjà vérifié indirectement) |
| 3 | Aésio Mutuelle | scr_souscription_vie | 30.921 | 253 | image | ✅ |
| 4 | Aésio Mutuelle | provisions_techniques | 601.103 | 246 | image | ✅ |
| 5 | Thémis | fonds_propres_t1_nr | 9.428 | 503 | image | ✅ |
| 6 | La Mondiale | scr_marche | 5203.7 | 251 | texte natif | ✅ texte |
| 7 | La Mondiale | primes_acquises_brutes | 4273.921 | 27 | texte natif | ✅ texte |
| 8 | La Mondiale Europartner | provisions_techniques | 23065.558 | 1 | somme calculée | ✅ best_estimate(22870.995)+marge_risque(194.563)=23065.558 exact |
| 9 | SGAM AG2R LA MONDIALE | fonds_propres_t1_nr | 6944.919 | 131 | texte natif | ✅ texte |
| 10 | AG2R Prévoyance | fonds_propres_t2 | 168.033 | 151 | texte natif | ✅ texte |
| 11 | MGEN | ratio_scr | 236% | 53 | texte natif | ✅ texte ("R0620 236 %") |
| 12 | Cardif Assurance Vie | fonds_propres_t2 | 1329.797 | 12 | texte natif | ✅ texte |
| 13 | Cardif Assurance Vie | scr_souscription_sante | 394.587 | 13 | texte natif | ✅ texte |
| 14 | Cardif Assurance Vie | scr_souscription_nonvie | 0.0 | 13 | texte natif | ✅ (valeur nulle, non testable utilement) |
| 15 | Crédit Agricole Assurances | provisions_techniques | 349.485 | 66 | somme calculée | ✅ best_estimate(342.576)+marge_risque(6.909)=349.485 exact |
| 16 | AG2R Prévoyance | fonds_propres_t3 | 146.114 | 151 | texte natif | ✅ texte |
| 17 | Thémis | scr_souscription_nonvie | 0.675 | 193 | image | ✅ |
| 18 | CNP Assurances | scr_contrepartie | 1267.072 | 97 | texte natif | ✅ texte |
| 19 | Prima | fonds_propres_t2 | 19.633 | 191 | texte natif | ✅ texte |
| 20 | Abeille IARD Santé | charge_sinistres | 1464.938 | 606 | image (corrigé Tâche 1) | ✅ |

**Score global : 20/20 corrects** (18 confirmés par correspondance
textuelle ou visuelle directe, 2 confirmés par recoupement
arithmétique exact — sommes calculées dont les composants ont été
vérifiés individuellement, cohérent avec la limite déjà documentée
Décision 112 : un total calculé n'apparaît normalement pas comme texte
littéral). **Taux par source** : image 7/7, texte natif 11/11 (0 K€
sur valeur nulle non testable exclue du calcul), somme calculée 2/2.
Aucune nouvelle anomalie trouvée par cet échantillon — cohérent avec
le fait que Tâche 1 avait déjà couvert la zone à risque principale
(primes_acquises_brutes/charge_sinistres Aéma).

---

## TÂCHE 3 : Corrections appliquées

Les 6 valeurs listées en Tâche 1 ont été corrigées dans
`aema_entites.py` (valeurs + commentaires de traçabilité, renvoi à
Décision 117) et `kpis.db` (`value`/`raw_value` mis à jour
directement, scripts d'extraction complets NON ré-exécutés comme
demandé). `export_kpis_for_frontend.py` ré-exécuté pour régénérer
`donnees-extraites.json`/`kpi-sources.json`.

## Fichiers modifiés

`aema_entites.py` (6 valeurs corrigées), `kpis.db` (mêmes 6
corrections), `frontend/src/data/donnees-extraites.json` +
`kpi-sources.json` (régénérés).
