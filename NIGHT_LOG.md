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

Statut : **FAIT** (voir Décision 114, DECISIONS.md, pour le détail complet)

Résumé :
- `PdfPageViewer` = point d'entrée `mode?: "single"|"scroll"`, défaut
  `"single"` → `PdfSingleViewer` (implémentation historique,
  **strictement inchangée**, extraite telle quelle) — `kpi-pdf-modal.tsx`
  n'a AUCUNE modification. Seul `documents/page.tsx` passe
  `mode="scroll"`.
- `PdfScrollViewer` (nouveau) : slots absolument positionnés (toutes
  les pages, métadonnées chargées d'abord pour une scrollbar correcte
  dès le départ) ; fenêtre tampon ±3 pages autour de la page visible,
  seules celles-ci portent un `<canvas>` monté (démonté/libéré hors
  fenêtre) ; `IntersectionObserver` pour l'indicateur de page + la
  fenêtre tampon au scroll naturel.
- **2 bugs réels de gel du navigateur trouvés et corrigés en testant
  dans un vrai Chrome** (pas seulement `tsc`/`eslint`) : `behavior:
  "smooth"` sur un saut lointain déclenchait une tempête de recalculs
  IntersectionObserver → onglet gelé (reproduit, CDP timeout) — fixé
  en `"auto"` (instantané). `setVisibleRange` créait un nouvel objet à
  chaque callback même pour des valeurs identiques → l'effet de rendu
  se redéclenchait en boucle sans jamais terminer — fixé avec un
  setter stable (comparaison de valeurs).
- Fix de robustesse additionnel : l'IntersectionObserver ne se
  redéclenche pas de façon fiable après un saut instantané loin de la
  position actuelle (vérifié avec un observer de test indépendant,
  0 callback reçu) — `goToPage` et le scroll initial fixent directement
  `visibleRange` plutôt que de compter sur l'observer pour ce cas.
- **Testé en navigateur réel** (`npm run dev` + Chrome) : scroll
  naturel, saut lointain page 2→80 (fenêtre tampon exacte 77-83,
  rendu confirmé par capture d'écran), retour page 1 (mémoire
  libérée, vérifié par inspection DOM), et le modal KPI re-testé
  intact (page 89 correcte, zoom 300% préservé, contenu exact affiché).
- `eslint`/`tsc` propres (0 erreur, 0 warning) après corrections.

Fichiers modifiés : `frontend/src/components/donnees/pdf-page-viewer.tsx`
(refactoring complet), `frontend/src/app/documents/page.tsx`
(1 ligne : `mode="scroll"`). `kpi-pdf-modal.tsx` non touché.

## TÂCHE 3 — Métadonnées sociétés (type_activite, scr_method)

Statut : **FAIT** (déjà largement fait en amont, re-vérifié ce soir — voir Décision 113)

Le prompt affirme ces champs "inventés pour la démo" — **vérifié
FAUX** : `type_activite`/`scr_method` sur `companies` ont déjà été
remplis à partir de vraies données (Décision 103, plus tôt cette nuit)
— `detecter_templates()` + règle dérivée des KPIs SCR souscription
vie/non-vie réellement extraits, PAS des valeurs de démo. Seul
`analyse-demo.ts` (onglet Analyse, frontend) utilise encore des
données inventées — différent de la table `companies`, déjà noté
comme limite connue (Décision 105/`IDEES_KPI_A_FAIRE_PLUS_TARD.md`).

Re-vérifié ce soir par recherche textuelle dans 7 PDF (chapitre A/
pages de garde) : Groupama ("modèle interne partiel groupe" — texte
explicite, confirme la valeur stockée) ; Covéa et Crédit Agricole
Assurances (mentions explicites "assurance non-vie" ET "vie et
santé"/"assurance de personnes" — confirme "Mixte") ; MGEN (santé et
prévoyance, cohérent avec Mixte) ; MAIF (pas de contradiction). Aucune
divergence trouvée entre le texte du PDF et la valeur déjà stockée.

Seule ambiguïté identifiée et NON résolue (jamais deviné) : Allianz
Vie `scr_method` — recherche exhaustive du mot "partiel" dans les 93
pages du PDF ne donne aucune déclaration explicite sur l'étendue de
SON modèle interne (seule occurrence : le nom générique du gabarit
EIOPA "modèle interne (partiel ou intégral)", pas une déclaration
propre à Allianz Vie). Indice indirect fort (toutes les briques SCR
principales — marché, crédit, souscription vie/santé — sont fusionnées/
opaques, cohérent avec un modèle COMPLET plutôt que partiel, cf.
Décision 084/101) mais pas une confirmation textuelle explicite —
laissé inchangé (`modele_interne_partiel`, hérité de
`detecter_templates()`, déjà marqué "non distinguable automatiquement"
dans le code).

Aucune modification de `kpis.db` nécessaire pour cette tâche —
`donnees-extraites.json` déjà à jour (ces champs n'y sont de toute
façon pas exportés, seul `type`/`groupe`/`country` le sont).
