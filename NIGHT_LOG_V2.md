# NIGHT_LOG_V2.md — session de nuit 30/09→01/10/2026

Suivi de progression pour le prompt de nuit (tâche unique : source_page
des PDFs multi-entités). Mis à jour au fur et à mesure.

## Vérification préalable (avant toute correction)

Les 5 exemples cités dans le prompt ont été vérifiés un par un contre
`kpis.db` et le texte réel des 2 PDF concernés, AVANT d'écrire une
seule ligne de correctif — même discipline que la nuit précédente.
**Cette fois les 5 claims se sont confirmés exacts** (contrairement au
prompt du 28/09, où 4/4 exemples "Catégorie A" s'étaient révélés faux
à la vérification). Voir Décision 115 (DECISIONS.md) pour le détail
complet.

## STATUT : FAIT

Résumé :
- Cause racine confirmée par lecture directe du PDF : la Décision 112
  avait skippé entièrement les 13 entités Aéma en les croyant "100%
  image" — vrai pour l'annexe QRT (pages 439-621) mais FAUX pour le
  chapitre narratif qui la précède (pages 1-438), où chaque entité a
  sa propre section avec un tableau natif reprenant la plupart des
  KPIs en clair. Même logique pour AG2R (sommes/totaux absents de
  l'annexe QRT, présents dans un chapitre "Bilan" antérieur).
- `corriger_source_page.py` : `AEMA_BORNES` (bornes narratives précises
  par entité, découvertes programmatiquement) remplace le skip total ;
  `AG2R_BORNES` élargi à 1..fin-du-bloc-QRT ; alternative K€ (+ forme
  arrondie) pour les 7 entités Aéma + Sogécap en euros bruts.
- **2 bugs de désambiguïsation trouvés et corrigés EN TESTANT** (pas
  supposés) : fenêtre de proximité pour les codes de ligne trop large
  (faux positif réel sur Allianz Vie/scr_total, pages 89 vs 90) ; repli
  "dernière occurrence" aveugle produisant un résultat faux par pure
  coïncidence numérique (MNPAF/marge_risque, "1 741" apparaît 2 fois
  sans rapport). Le repli aveugle a été supprimé, remplacé par
  `LABELS_NARRATIFS` (libellés français observés directement dans les
  PDF) + une tolérance "≤2 pages, déjà confirmé par libellé" beaucoup
  plus sûre.
- **171 `source_page` corrigés**, 98 ambigus + 209 introuvables laissés
  inchangés (jamais devinés). `source_page` NULL : 53 → 44 (reste
  concentré sur les KPIs dérivés/sommés sans total imprimé nulle part,
  limite déjà documentée).
- `donnees-extraites.json`/`kpi-sources.json` régénérés.

## Validation (15 KPIs demandés : 5 Aéma, 5 AG2R/mix, 3 single-entity, 2 Crédit Agricole)

Vérifié par lecture directe du texte PDF à la page stockée (pas de
confiance aveugle dans le script lui-même) :

| Société | KPI | Page | Statut |
|---|---|---|---|
| Aéma Groupe | scr_contrepartie | 66 | OK |
| Abeille Vie | mcr | 377 | OK |
| MNPAF | marge_risque | 279 | OK |
| Macifilia | fonds_propres_eligibles | 213 | OK |
| Nuoma | scr_total | 340 | OK |
| AG2R Prevoyance | fonds_propres_t1_r | 151 | OK |
| La Mondiale | ratio_mcr | 249 | OK |
| Prima | best_estimate | 77 | OK |
| SGAM AG2R LA MONDIALE | scr_total | 8 | **ÉCHEC — pré-existant, pas une régression (vérifié identique au commit précédent)** |
| AG.Mut | best_estimate | 79 | OK |
| Allianz Vie | ratio_scr | 89 | OK |
| Sogécap | scr_diversification | 40 | OK |
| Groupama | ratio_scr | 85 | **ÉCHEC — pré-existant (hérité du hardcodage historique de extract_kpis.py), "274%" apparaît dans 5 contextes narratifs différents sans code de ligne pour trancher, correctement laissé ambigu plutôt que deviné** |
| Crédit Agricole Assurances | scr_total | 74 | **ÉCHEC — pré-existant** |
| Crédit Agricole Assurances | fonds_propres_eligibles | 76 | OK |

**12/15 corrects.** Les 3 échecs sont vérifiés PRÉ-EXISTANTS (valeurs
identiques bit-à-bit à l'état du commit précédent, `git show` à
l'appui) — zéro régression introduite ce soir, simplement 3 gaps que
ce correctif n'a pas réussi à résoudre (restent `ambigu`/`introuvable`
en interne, pas une valeur fausse écrite). Chantier futur possible :
étendre `LABELS_NARRATIFS` pour couvrir `ratio_scr` (actuellement
absent du dictionnaire — raison probable de l'échec Groupama).

Les 5 KPIs cités dans le prompt comme référence "déjà bons" (AG2R
Prévoyance/fonds_propres_t1_r p.151, La Mondiale/ratio_mcr p.249,
Cardif Assurances RD/scr_souscription_nonvie p.13, Allianz Vie/
ratio_scr p.89, Sogécap/scr_diversification p.40) ont été re-vérifiés
explicitement inchangés — zéro régression.

## Fichiers modifiés

`corriger_source_page.py` (AEMA_BORNES, AG2R_BORNES élargi,
LABELS_NARRATIFS, fenêtre de proximité resserrée, suppression du repli
aveugle), `kpis.db` (171 source_page corrigés),
`frontend/src/data/donnees-extraites.json` + `kpi-sources.json`
(régénérés).
