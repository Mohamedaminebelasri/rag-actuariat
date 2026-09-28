# Idées KPI à faire plus tard

Document créé le 28/09/2026 — ne couvre pour l'instant que la section
"Bugs à corriger — Backend" (seule section dont le contenu est connu
avec certitude au moment de la création). D'autres sections (frontend,
idées produit) peuvent être ajoutées par la suite.

## Bugs à corriger — Backend

### ~~BUG CRITIQUE : Valeurs converties au lieu de brutes~~ — RÉSOLU (28/09/2026)

Signalé : le modèle d'extraction convertit les valeurs au lieu de les
stocker telles quelles (ex. Allianz Vie : PDF dit "4 266 905" en
milliers d'euros → l'extraction stockait "4266,9 M€").

**Vérification faite avant correction** : la conversion K€→M€ est
mathématiquement correcte (4 266 905 K€ = 4266,905 M€, exactement la
valeur stockée) et résulte de ~10 décisions de vérification (094-107,
DECISIONS.md) — ce n'était pas un bug de calcul. Le besoin réel était
de pouvoir voir le chiffre brut tel qu'imprimé dans le PDF, en plus de
la valeur convertie.

**Résolu** (Décision 110, DECISIONS.md) : colonnes `raw_value`/
`raw_unit` ajoutées sur `kpis` (additif — `value`/`unit` M€ restent la
source de vérité pour tout calcul/contrôle). Câblé côté frontend
(Cowork) : `valeurBrute`/`uniteBrute` affichés dans le modal KPI
(`formatValeurBrute()`).

### Décalage page PDF (-1) — corrigé côté frontend (28/09/2026)

`pageSource` dans kpis.db stocke le numéro de page imprimé, le PDF
physique est décalé de +1 (couverture non numérotée). Fix appliqué
côté frontend (`kpi-pdf-modal.tsx` : `initialPage = pageSource - 1`).
Amélioration possible plus tard : stocker directement le numéro de
page physique côté backend plutôt que de compenser à l'affichage — pas
fait, non bloquant.

### Endpoint de correction manuelle — ajouté (28/09/2026)

`POST /api/kpi/correct` créé (Décision 111, DECISIONS.md) pour les
corrections manuelles saisies via le bouton "Corriger" du modal KPI :
- Table `corrections` sur kpis.db — journal, jamais purgé, sert à
  analyser les erreurs du modèle d'extraction.
- `corriger_kpi.py` : applique la correction (parseur de nombre
  FR + reconversion raw→M€ selon l'unité), appelé synchronement par
  la route Next.js.
- Après une correction, relancer `npm run regenerate-json` (dans
  `frontend/`) pour que `donnees-extraites.json` reflète le
  changement — pas automatique (Option B), à documenter/rappeler côté
  usage.

## Points d'attention

- Le type d'activité et le modèle de capital des sociétés de
  démonstration (onglet Analyse, `analyse-demo.ts`) sont des attributs
  inventés — à remplacer par les vraies métadonnées
  (`kpis_export.json`, Décision 105, déjà prêt côté backend mais pas
  encore câblé côté frontend).
- Différenciateur produit à mettre en avant : badges de fiabilité
  (triple validation) et lien de chaque KPI vers sa page source.
