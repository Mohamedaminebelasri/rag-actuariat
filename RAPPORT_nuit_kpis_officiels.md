# Rapport final — nuit « Indicateurs calculés → KPIs officiels » (3 phases)

Prompt : `Claude outputs/prompt-nuit-kpis-officiels-3-phases.md`. Décision 158.
Rapports de phase : `RAPPORT_nuit_phase1.md`, `RAPPORT_nuit_phase2.md` ;
progression : `NUIT_PROGRESS.md`. Les 3 portes sont franchies, tout est poussé
sur `origin/master`.

## Revoir toute la nuit

```bash
git diff avant-nuit-kpis-officiels..HEAD --stat
```

41 commits entre `avant-nuit-kpis-officiels` (9d49dce) et `a76137b` (+ ce rapport),
30 fichiers. Revenir en arrière : le tag reste en place ; sauvegardes locales
(non commitées) dans `archive/` : `kpis_avant_nuit_kpis_officiels_20261015.db`,
`donnees-extraites_avant_nuit_kpis_officiels.json`.

## Résultat

| KPI | Unité | Sociétés | Vérifiés | Non créés |
|---|---|---|---|---|
| `ratio_scr_sans_mesures_lt` | % | 41 | 39 | 0 |
| `impact_va` | pts | 41 | 39 | 0 |
| `impact_transitoires` | pts | 4 | 4 | 37 (pas de mesure transitoire) |
| `marge_risque_sur_be` | % | 41 | 41 | 0 |
| `sp_nonvie` | % | 25 | 0 | 16 (activité non-vie absente ou marginale) |
| `mcr_en_pct_scr` | % | 36 | 34 | 5 (groupes) |

188 KPIs ajoutés (856 → 1 044), valeurs identiques aux indicateurs d'origine,
recalcul depuis les composants à 0,0485 près au plus (tolérance 0,05).

Contrôles : `test_kpis_officiels.py` OK ; 0 ligne existante de `kpis` /
`kpi_composants` modifiée ; diff des JSON = ajouts seulement (sauf `genereLe`
et les textes de `definitionsIndicateurs`, simplifiés à la demande) ;
`validate_kpis.py --all` (sur copie) inchangé ; `tsc` 0 erreur ; `eslint`
1 warning préexistant (un autre warning préexistant a disparu) ; `next build`
OK ; sortie brute de `buildAlertes` identique (41 sociétés + 41 paires) ;
tableau comparatif des 21 KPIs existants identique ; position parmi les
pairs testée sur les 10 sociétés du brief.

## Fichiers déjà existants modifiés, et pourquoi

| Fichier | Pourquoi |
|---|---|
| `kpi_definitions.py` | définitions des 6 KPIs (liste séparée des 21 extraits) |
| `validate_kpis.py` | ne charger que les 21 KPIs extraits : sinon KeyError au contrôle de signe et complétude faussée |
| `comparabilite.py` | 6 lignes de matrice, activités applicables, textes de `definitionsIndicateurs` en français simple |
| `corrections_comparabilite.py` | bonus : libellé de source lisible pour les 40 KPIs à avertissement |
| `export_kpis_for_frontend.py` | `formule`, composants enrichis, `definitionsKpis`, `activitesApplicables`, `sourceLisible` |
| `kpis.db`, `donnees-extraites.json`, `kpi-sources.json` | données régénérées (ajouts) |
| `DECISIONS.md`, `PIPELINE_EXTRACTION_KPIs.md`, `frontend/CLAUDE.md` | documentation (Décision 158, ordre de rejeu, contrat JSON, PositionMarche réactivé) |
| `donnees-extraites-utils.ts`, `analyse-demo.ts`, `analyse-utils.ts`, `comparabilite.ts` | types, catégorie I, décimales, « sans objet » du S/P, `classement()` corrigé |
| `kpi-pdf-modal.tsx`, `kpi-ligne.tsx`, `base-donnees/page.tsx` | fenêtre de détail additive, badges, section « Indicateurs comparables » |
| `kpi-card.tsx`, `individual-tab.tsx`, `comparative-table.tsx`, `comparison-bar-chart.tsx`, `aide-panel.tsx` | cartes cliquables, catégorie I, filtre, « sans objet », aide |
| `position-marche.tsx` | réécrit (demandé par la Phase 3) |

Rien de ce qu'avait ajouté l'utilisateur n'a été retiré : vues agrandies,
catégories fermées par défaut, absence des colonnes médiane / seuil,
alertes regroupées par société, pastille compteur retirée, bouton
« Réinitialiser », filtres (vérifié à l'écran et par comparaison des sorties).

## Écarts entre le prompt et le code réel

1. L'ancien bloc `indicateurs-comparables.tsx` n'affichait que les 6
   indicateurs promus : aucun « autre indicateur » à y laisser. Rendu masqué
   (commenté), fichier conservé.
2. `position_mcr` reste dans `indicateursParSociete` (alerte R7) ; le KPI
   `mcr_en_pct_scr` s'y ajoute, sa catégorie devient la note de la formule.
3. `kpi_labels_fr.py` sert à l'extraction par libellé : sans objet pour des
   KPIs calculés, non modifié.
4. Covéa : `best_estimate` / `marge_risque` sans page source en base ; page 85
   retrouvée dans le PDF, utilisée pour les composants (KPI existants non
   modifiés — correction à faire si souhaité).
5. `chapitreSource` des cartes à avertissement : la Décision 157 y garde la
   base technique ; le texte simple est un champ ajouté (`sourceLisible`).

## Décisions prises seul (lectures retenues)

- `impact_transitoires` seulement pour les 4 sociétés à mesure transitoire
  (égalité stricte avec l'indicateur) ; « impact = 0 » appliqué à `impact_va`.
- Un composant non recoupé rend le KPI « non vérifié » sans avertissement de
  comparabilité (sinon `sp_nonvie` serait exclu de tout classement).
- `mcr_en_pct_scr` solo seulement ; `sp_nonvie` comparé seulement entre
  Non-vie et Santé/prévoyance ; `marge_risque_sur_be` N sur l'axe activité.
- Pas de rang ni de couleur meilleur / pire pour les 6 KPIs dans le tableau
  comparatif (vert / rouge réservés au feu tricolore).
- Position parmi les pairs : modèles internes et groupes jamais classés ;
  neutres par défaut : diversification, SCR / (primes + BE), RM / BE, impacts
  VA et transitoires.

## Pas fait / à suivre

- Les cartes des 21 KPIs existants de l'Analyse individuelle ne sont pas
  cliquables (seules les 6 nouvelles le sont).
- `sp_nonvie` n'est jamais « Vérifié » : `validate_kpis.py` ne contrôle pas
  les primes et sinistres (contrôle à ajouter si souhaité).
- Page source des KPIs `best_estimate` / `marge_risque` de Covéa à compléter.
