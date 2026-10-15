# Progression — nuit « KPIs officiels » (3 phases)

Prompt : `Claude outputs/prompt-nuit-kpis-officiels-3-phases.md`.
Tag de départ : `avant-nuit-kpis-officiels` (voir toute la nuit :
`git diff avant-nuit-kpis-officiels..HEAD --stat`).

## Étape 0 — Protection et baseline
- [x] `git status` / `git log` / `git diff --stat` : aucune modification suivie non commitée au départ
- [x] Tag `avant-nuit-kpis-officiels` sur HEAD (9d49dce)
- [x] Sauvegardes (non commitées) : `archive/kpis_avant_nuit_kpis_officiels_20261015.db`,
      `archive/donnees-extraites_avant_nuit_kpis_officiels.json`
- [x] Baseline `tsc` : 0 erreur dans `src/` (2 erreurs dans `.next/types`, page de test périmée `zz-test-groupe`)
- [x] Baseline `eslint src` : 0 erreur, 2 warnings (`layout.tsx` police, `kpi-pdf-modal.tsx` `Composant` inutilisé)
- [x] Baseline `next build` (copie isolée, le serveur de dev de l'utilisateur tourne sur :3000) : OK, mêmes 2 warnings
- [x] Baseline `buildAlertes` : 15 alertes pour les 41 sociétés + 41 paires (sauvegarde hors dépôt)

## Phase 1 — Back-end
- [x] Définitions (`kpi_definitions.py`)
- [x] Modèle composants + formule (table `kpi_formules`, colonnes ajoutées à `kpi_composants`)
- [x] `peupler_kpis_officiels_indicateurs.py`
- [x] Export (`kpisParSociete`, `kpi-sources.json`, `definitionsIndicateurs` simplifiées)
- [x] Matrice de comparabilité des 6 KPIs
- [x] `test_kpis_officiels.py`
- [x] Décision dans `DECISIONS.md`
- [x] PORTE 1 + `RAPPORT_nuit_phase1.md` + push
- [ ] Bonus : `chapitreSource` des cartes à avertissement en français simple

## Phase 2 — Front (Base de données, Analyse individuelle et comparative)
- [ ] Types et utilitaires
- [ ] Fenêtre de détail (mode additif)
- [ ] Base de données
- [ ] Analyse individuelle (alertes identiques)
- [ ] Analyse comparative
- [ ] Aide « i »
- [ ] Qualité (tsc, eslint, build, captures)
- [ ] PORTE 2 + `RAPPORT_nuit_phase2.md` + push

## Phase 3 — Position parmi les pairs
- [ ] Réécriture de `position-marche.tsx` et réactivation
- [ ] Tests sur les sociétés listées
- [ ] PORTE 3 + push

## Rapport final
- [ ] `RAPPORT_nuit_kpis_officiels.md`
