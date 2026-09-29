# NIGHT_LOG.md — session de nuit 28/09→29/09/2026

Suivi de progression pour le prompt de nuit (3 tâches). Mis à jour au
fur et à mesure — permet de reprendre proprement en cas de coupure.

## Corrections faites au prompt avant de commencer

- Les chemins donnés (`test_markdrop/extract_kpis.py`,
  `test_markdrop/extraire_un_pdf.py`, `test_markdrop/extract_kpis_cnp.py`)
  sont FAUX — ces 3 scripts sont à la racine du dépôt
  (`extract_kpis.py`, `extraire_un_pdf.py`, `extract_kpis_cnp.py`),
  jamais dans `test_markdrop/`. Vérifié par `ls` avant de commencer,
  pas supposé. Travaillé sur les vrais chemins.
- Git config (email/nom) déjà strictement identique à ce qui était
  demandé — aucun changement nécessaire, aucune commande de
  configuration exécutée (règle absolue : ne jamais toucher git
  config).
- `git lfs env` montre un token GitHub en clair dans l'URL du remote
  LFS — signalé à l'utilisateur, jamais reproduit dans ce fichier ni
  ailleurs. `.gitattributes` n'existe pas (aucun tracking LFS
  configuré) : le hook pre-push (`git lfs pre-push`) est donc un
  no-op rapide. `git push` normal tenté en premier, `--no-verify`
  seulement si ça bloque réellement.

## TÂCHE 1 — Corriger les source_page

Statut : **FAIT** (voir Décision 112, DECISIONS.md, pour le détail complet)

Résumé :
- Outil rétroactif générique `corriger_source_page.py` : cherche la
  page réelle par valeur brute + code de ligne QRT (désambiguïsation),
  jamais une page devinée.
- **171 source_page corrigés** sur les sociétés à PDF texte natif
  (hors Aéma). 63 ambigus + 129 introuvables laissés inchangés
  (majoritairement des KPIs dérivés/sommés — best_estimate,
  marge_risque, provisions_techniques, primes_acquises_brutes,
  charge_sinistres — qui ne peuvent structurellement pas apparaître
  comme un nombre unique imprimé dans le PDF).
- **Catégorie A du prompt (Aéma, "le plus grave") RÉFUTÉE** : les 4
  exemples cités ont tous été vérifiés en rendant la page PDF réelle
  (image) — les 4 étaient DÉJÀ CORRECTS, pas des pages titre. Contrôle
  étendu programmatiquement aux 273 lignes KPI Aéma (nom d'entité +
  gabarit plausible dans le texte titre de la page) : 273/273 passent,
  aucune correction nécessaire.
- `extraire_un_pdf.py` : appel automatique à la même correction après
  toute future insertion (non bloquant), testé end-to-end.
- `source_page` NULL restants : 87 → 53 (concentré sur les KPIs
  dérivés/sommés, limite documentée, pas comblé ce soir).
- `donnees-extraites.json` régénéré.

Validation demandée (≥10 KPIs aléatoires) : faite en 2 passes
(échantillons de 14 et 12 KPIs aléatoires, seed fixée pour
reproductibilité) + les 2 exemples du prompt (Allianz Vie ratio_mcr,
Crédit Agricole fonds_propres_t3) vérifiés individuellement contre le
PDF réel. 100% de succès sur les KPIs structurellement trouvables,
0 régression, 0 fausse correction.

Fichiers modifiés : `corriger_source_page.py` (nouveau),
`extraire_un_pdf.py`, `kpis.db`, `frontend/src/data/donnees-extraites.json`
(régénéré), `frontend/src/data/kpi-sources.json` (régénéré).

## TÂCHE 2 — Scroll continu PdfPageViewer

Statut : PAS COMMENCÉE

## TÂCHE 3 — Métadonnées sociétés (type_activite, scr_method)

Statut : PAS COMMENCÉE
