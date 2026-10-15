# Rapport de nuit — Phase 1 (back-end) : 6 indicateurs promus en KPIs officiels

Décision 158 (`DECISIONS.md`). Script : `peupler_kpis_officiels_indicateurs.py`.
Tests : `test_kpis_officiels.py` (résultat : **OK, 0 écart**).

## PORTE 1

| Critère | Résultat |
|---|---|
| Tests (recalcul, égalité avec `indicateursParSociete`, diff « ajouts seulement », aucun KPI nul, décompte) | OK, 0 écart non justifié |
| KPI existants modifiés | 0 — 861 lignes `kpis` et 669 lignes `kpi_composants` identiques à la sauvegarde (toutes colonnes) ; `companies`, `impact_mesures_lt`, `validation_checks`, `corrections` identiques |
| `indicateursParSociete` | strictement identique |
| JSON régénéré | valide (lu par les tests, `tsc` 0 erreur dans `src/`, `eslint` inchangé) |
| Diff avec l'ancien `donnees-extraites.json` | uniquement des ajouts, sauf `genereLe` et les textes de `definitionsIndicateurs` (simplification demandée, mêmes clés) |
| Diff avec l'ancien `kpi-sources.json` | uniquement des ajouts |
| Idempotence | 2 exécutions → contenu des tables identique |
| `validate_kpis.py --all` (sur une copie) | 0 échec réel, `validated` et `validation_checks` identiques |

## KPI × sociétés

| KPI | Unité | Créés | Non créés | Valide vrai | Valide faux |
|---|---|---|---|---|---|
| `ratio_scr_sans_mesures_lt` | % | 41 | 0 | 39 | 2 (Generali Vie, Generali IARD : ratio lu dans le texte, non recoupé) |
| `impact_va` | pts | 41 | 0 | 39 | 2 (idem) |
| `impact_transitoires` | pts | 4 | 37 (pas de mesure transitoire) | 4 | 0 |
| `marge_risque_sur_be` | % | 41 | 0 | 41 | 0 |
| `sp_nonvie` | % | 25 | 16 (activité non-vie absente ou < 10 % / 10 M€) | 0 | 25 (lignes de primes et sinistres jamais couvertes par `validate_kpis.py`) |
| `mcr_en_pct_scr` | % | 36 | 5 (groupes : Aéma, Covéa, CAA, Groupama, SGAM AG2R) | 34 | 2 (Macifilia, Thémis : MCR et SCR non vérifiés) |

Total : 188 KPIs ajoutés (856 → 1 044). Aucun avertissement posé (aucun
composant n'en porte, aucun recalcul en écart). Écart maximal recalcul /
valeur : 0,0485 (arrondi à 1 décimale, tolérance 0,05).

Par société : La Mondiale a les 6 ; 4 ou 5 pour les autres (ex. Generali
Vie 4, AXA France Vie 5, MGEN 5 — sans VA ni transitoire).

## Ce qui a été fait

- `kpi_definitions.py` : `KPI_INDICATEURS_OFFICIELS` (libellé, unité,
  description en français simple, sens de classement), liste séparée des
  21 KPIs extraits.
- `peupler_kpis_officiels_indicateurs.py` : nouvelle table `kpi_formules`,
  4 colonnes ajoutées à `kpi_composants`, 188 KPIs + composants + règles.
- `comparabilite.py` : 6 lignes de matrice, `ACTIVITES_APPLICABLES`,
  `DEFINITIONS_INDICATEURS` réécrites (plus de code QRT ni de nom de société).
- `export_kpis_for_frontend.py` : `formule`, champs de composant
  (`kpiCode`, `detail`, `sourcePdf`, `valide`) seulement pour les KPIs
  calculés, `definitionsKpis`, `compatibilite.activitesApplicables`.
- `validate_kpis.py` : ne charge que les 21 KPIs extraits.
- `test_kpis_officiels.py`, `DECISIONS.md` (158), `PIPELINE_EXTRACTION_KPIs.md`.

## Lectures retenues (seul, sans pouvoir demander)

1. `impact_transitoires` créé seulement pour les 4 sociétés qui appliquent
   une mesure transitoire (formule et périmètre actuels de
   `comparabilite.py`, égalité stricte avec l'indicateur) ; la règle
   « société sans VA ni transitoire → impact = 0 » est appliquée à
   `impact_va` (comme l'indicateur actuel).
2. « valide = false + avertissement » : l'avertissement n'est posé que pour
   un avertissement hérité ou un recalcul en écart. Un composant
   simplement non recoupé rend le KPI « non vérifié » sans avertissement
   de comparabilité ; sinon `sp_nonvie` (lignes jamais vérifiées) serait
   exclu de toute comparaison, contrairement à la Phase 3.
3. `mcr_en_pct_scr` : solo seulement (périmètre de `position_mcr`).
4. `sp_nonvie` : créé partout où l'indicateur existe (y compris 4 sociétés
   Vie / Mixte avec une activité non-vie significative) ; comparé
   seulement entre Non-vie et Santé/prévoyance (`activitesApplicables`).
5. Note de formule (`formule.note`) pour les mentions « n'applique ni VA
   ni transitoire » et plancher / plafond du MCR.
6. `kpi_labels_fr.py` non modifié : il sert à l'extraction par libellé
   des PDF, sans objet pour des KPIs calculés.

## Écarts prompt / code réel

- Prompt : « catégorie textuelle `position_mcr` remplacée ». Réel :
  `position_mcr` reste dans `indicateursParSociete` (alerte R7 et
  consigne « indicateurs inchangés ») ; le KPI `mcr_en_pct_scr` s'ajoute.
- Covéa : `best_estimate` et `marge_risque` sans page source en base
  (lacune antérieure) ; page 85 retrouvée dans le PDF et utilisée pour
  les composants seulement. **À corriger côté KPI existant** si souhaité
  (non fait : interdiction de modifier un KPI existant).

## Bonus (après la porte)

Voir `RAPPORT_nuit_kpis_officiels.md` (reformulation de `chapitreSource`
des cartes à avertissement).
