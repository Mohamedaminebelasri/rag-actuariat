# Frontend — Iconcilio (Next.js)

Ce fichier est lu automatiquement par toute session Claude Code ouverte dans
ce dossier ou dans la racine du repo. Il couvre uniquement le front-end
(`frontend/`). Pour le contexte RAG/back-end (Python, kpis.db, src/rag.py),
voir le `CLAUDE.md` à la racine — il ne concerne pas les tâches front-end.

## Stack

Next.js 15 (App Router), TypeScript, Tailwind CSS 4 (`@import "tailwindcss"`).
Composants client (`"use client"`), pas de librairie de graphiques (barres,
radar en SVG maison), icônes `lucide-react`. Aucune nouvelle dépendance sans
accord explicite.

Scripts : `npm run dev`, `npm run build`, `npm run lint`, `npx tsc --noEmit`.
`npm run lint` lint parfois `.next/**` (build généré) si le dossier existe —
ignorer ces erreurs-là, ce n'est jamais une vraie régression de code source.

## Flux de données — piège de nommage

`kpis.db` (SQLite, back-end Python) est exporté en JSON statique, **pas une
connexion live**. Deux pipelines distincts à ne pas confondre :

- **Onglet Analyse** (`analyse/page.tsx`) : lit `frontend/src/data/analyse-demo.ts`.
  Malgré son nom, ce fichier lit aujourd'hui les **vraies données** depuis
  `donnees-extraites.json` (plus des données de démo inventées — nom
  historique jamais renommé). Expose `kpisSociete()`, `listeSfcrDisponibles()`,
  `KPI_DEFINITIONS`, le type `KpiValeur` (`valeur: number`, jamais `null` —
  un KPI non extrait est simplement une clé **absente** de l'objet `kpis`,
  jamais stockée à `null` ni à `0`).
- **Onglet Base de données** (`base-donnees/page.tsx`) : lit directement
  `donnees-extraites.json` via `frontend/src/lib/donnees-extraites-utils.ts`
  (type `KpiExtrait`, plus riche : `pageSource`, `chapitreSource`, `valide`,
  `valeurBrute`/`uniteBrute`, `estCompose`/`composants`).
- **Onglet Documents** : lit `frontend/src/data/kpi-sources.json` (mapping
  page/chapitre par société/KPI) avec repli sur `donnees-extraites.json`.
  Le vrai point d'entrée du clic KPI → PDF est `KpiPdfModal`
  (`base-donnees/page.tsx` lui passe toujours `onSelect`, donc la
  restriction "Groupama uniquement" historique de `kpi-ligne.tsx` est du
  code mort en pratique, cf. Décision 142 — ne pas s'y fier).

### Règle non négociable — le PDF affiché doit toujours être celui qui a servi à l'extraction

`PDF_PAR_SOCIETE` (`pdf-par-societe.ts`) donne le PDF **par défaut** d'une
société. Mais depuis la Décision 145, un KPI individuel peut avoir son
propre PDF source (`kpi.sourcePdf` dans `donnees-extraites.json` /
`kpi-sources.json`), **prioritaire** sur le défaut de la société —
utilisé quand un 2e document a servi pour CE KPI précis (ex. un KPI
`avertissement` venant d'un rapport narratif complémentaire à l'annexe
QRT habituelle). `null`/absent = pas de surcharge, PDF par défaut.
`KpiPdfModal` et `documents/page.tsx` (`pdfSourceKpi()`) résolvent déjà
ce cas — tout nouveau composant qui ouvre un PDF depuis un KPI doit
faire pareil (`kpi.sourcePdf ?? PDF_PAR_SOCIETE[societe]`), jamais
PDF_PAR_SOCIETE seul.

### KPI `avertissement` — valeur sur une base non comparable

Un KPI peut porter `avertissement: true` + `noteAvertissement` (texte
actuariel expliquant pourquoi, ex. "calculé avant diversification
inter-risques et avant impôt, modèle interne"). **Doit être signalé
visuellement partout où le KPI apparaît** (Base de données, Analyse
individuelle, Analyse comparative) — un petit symbole d'alerte à côté
de la valeur, de couleur distincte, cliquable pour afficher
`noteAvertissement`. Ne jamais masquer ce KPI ni le traiter comme une
valeur normale : la donnée est réelle et utile, juste pas directement
comparable aux mêmes KPIs des autres sociétés.

### Comparabilité entre sociétés (Décisions 149-155)

`donnees-extraites.json` porte les règles de comparaison — le front-end
les applique, il ne les recalcule pas :

- Par société : `type` = forme juridique courte (SA, SE, SAM, Mutuelle,
  Union de mutuelles, Institution de prévoyance, Groupe) ;
  `typeActivite` (Vie / Non-vie / Santé/prévoyance / Mixte) ;
  `modeleCapital` (Formule standard / Modèle interne) ; `perimetre`
  (solo / groupe) ; `groupePairs` (activité · modèle · périmètre) ;
  `consolideDans` (société du panel qui la consolide déjà : à exclure des
  agrégats avec ce groupe, sinon double comptage).
- `groupesPairs` (avec `n`, `petitEchantillon` si n < 5),
  `compatibilite.matrice[kpi][axe]` (verdict C / R / N / NA + note ; règle
  dans `compatibilite.regle`), `indicateursParSociete` +
  `definitionsIndicateurs` (ratios normalisés, dont
  `ratio_scr_sans_mesures_lt_pct` = ratio SCR sans correction pour
  volatilité ni transitoire).
- KPI de groupe `mcr` / `ratio_mcr` : champ `libelle` (« SCR minimal
  consolidé ») à afficher à la place du nom générique.

Ces 2 fichiers JSON (`frontend/src/data/donnees-extraites.json` et
`kpi-sources.json` ; l'ancien `kpis_export.json` a été supprimé) sont des snapshots —
à régénérer côté back-end après toute mise à jour de `kpis.db`. Une session
front-end ne les régénère pas elle-même sauf consigne explicite.

Unités : toutes les valeurs de KPI sont déjà normalisées en `M€` ou `pct`
dans le JSON (y compris pour les 8 sociétés dont la source est en
"euros bruts") — ne jamais refaire une conversion d'unité dans un composant.
`valeurBrute`/`uniteBrute` ne servent qu'à l'affichage de la valeur brute
PDF (voir `formatValeurBrute()` dans `donnees-extraites-utils.ts`).

## Seuils et couleurs — règle non négociable

`frontend/src/lib/seuils-config.ts` définit `SEUIL_LEGAL` (100 %, verrouillé)
et `SEUIL_VERT_SCR_DEFAUT` (200 %, modifiable par l'utilisateur, persisté en
localStorage). `frontend/src/lib/analyse-utils.ts` (`couleurSeuil()`,
`statutKpi()`, `texteInfobulleSeuil()`) est la **seule** source de vérité
pour la coloration par seuil — ne jamais dupliquer cette logique ailleurs.
`kpi-card.tsx` exporte `COULEUR_VALEUR`/`ICONE_STATUT`, réutilisés tels
quels par `comparative-table.tsx` pour une cohérence stricte carte ↔ tableau.

**Rouge/orange/vert (`text-success`/`text-warning`/`text-danger`) sont
réservés exclusivement au feu tricolore des ratios SCR/MCR.** Tout autre
graphique (radar comparatif, décomposition du SCR par module) doit utiliser
une palette neutre sans signification de risque — voir la palette
bleu/violet/turquoise/gris ardoise dans `radar-chart.tsx` et
`scr-breakdown-chart.tsx`. Un montant n'est jamais "bon" ou "mauvais" en soi.

La feature "anneau pointillé proche du seuil" a été implémentée puis
**définitivement retirée** (décision explicite de l'utilisateur) — ne pas la
réintroduire sauf demande explicite et non ambiguë.

## Design system "Ivory" (tokens CSS, `globals.css`)

Variables CSS (`:root`, + variante `@media (prefers-color-scheme: dark)` et
`:root[data-theme="dark"]`) : `--surface`, `--surface-secondary`,
`--surface-hover`, `--border`, `--text-primary`, `--text-secondary`,
`--text-tertiary`, `--accent`, `--success`/`--warning`/`--danger` (+ variantes
`-light`), `--radius-lg`/`--radius-md`, `--shadow-sm`/`-md`/`-lg`. Toujours
réutiliser ces tokens (classes Tailwind `text-text-secondary`,
`bg-surface-secondary`, `border-border`, etc. ou `var(--token)` en style
inline pour le SVG) — ne jamais coder une couleur en dur hors palette neutre
des graphiques.

## Composants désactivés — ne pas réactiver sans accord

`PositionMarche` et `ConfidenceBadge` sont commentés/désactivés dans le code
(décision séparée, pas un oubli). Ne pas les réactiver au passage d'une
autre tâche.

## Style de mission attendu

L'utilisateur donne des briefs très cadrés (fichiers autorisés/interdits,
limite de temps, critères de validation avec de vraies sociétés, format de
résumé attendu). Respecter strictement le périmètre annoncé ("ne touche pas
à X"), même si une correction connexe semble tentante — proposer plutôt que
d'agir hors scope. Toujours vérifier `npx tsc --noEmit` + lint, et tester
dans le navigateur (`npm run dev`) quand un rendu visuel est en jeu.

## Git

Commits en français, un commit séparé par correctif. Toujours pousser sur
`origin/master` une fois la tâche terminée et vérifiée (tsc/lint/tests OK) —
ne pas attendre qu'on te le demande.
