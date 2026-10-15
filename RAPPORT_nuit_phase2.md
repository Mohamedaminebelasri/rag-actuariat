# Rapport de nuit — Phase 2 (front) : Base de données, Analyse individuelle et comparative

Décision 158. Dossier `frontend/`, design Ivory, couleurs neutres pour les 6 KPIs calculés.

## PORTE 2

| Critère | Résultat |
|---|---|
| `tsc --noEmit` | 0 erreur dans `src/` (les 2 erreurs de `.next/types`, page de test périmée, préexistaient) |
| `eslint src` | 0 erreur, 1 warning (préexistant, `layout.tsx`) ; le warning `Composant` inutilisé a disparu (type maintenant utilisé) |
| `next build` | OK (copie isolée, le serveur de dev de l'utilisateur tourne sur :3000) |
| Alertes | sortie brute de `buildAlertes` (société, niveau, texte) **identique octet pour octet** : 41 sociétés ensemble (15 alertes) + 41 paires |
| Anciens KPIs | `buildTableauComparatif` (valeurs, rangs, moyennes, notes) sur 8 sélections, définitions des 21 KPIs, couvertures « x/21 extraits, y vérifiés », statistiques globales : **identiques** (ancien code au tag + ancien JSON vs nouveau code + nouveau JSON) |
| Fenêtre de détail des KPIs « somme » | branche d'origine inchangée ; vérifiée à l'écran (provisions techniques La Mondiale) |

## Ce qui a été fait

1. **Types et utilitaires** (`donnees-extraites-utils.ts`) : `FormuleKpi`,
   `DefinitionKpiCalcule`, champs de `Composant` (`kpiCode`, `detail`,
   `sourcePdf`, `valide`), `formule` / `sourceLisible` sur `KpiExtrait`,
   `labelKpi()`, `estKpiExtrait()`, `recalculerKpi()`, `DECIMALES_KPIS`,
   format « pts ». Compteurs « extraits / vérifiés » limités aux 21 KPIs
   extraits (sinon « 27/21 »).
2. **Fenêtre de détail** (`kpi-pdf-modal.tsx`), mode additif : si
   `formule` existe, « Règle de calcul » (texte, numérateur /
   dénominateur ou termes ±, chaque composant avec code, détail du calcul,
   valeur, page cliquable sur le bon PDF, « Voir le KPI » quand c'est un KPI
   officiel, vérifié / non vérifié), recalcul en direct « = X ✓ cohérent
   avec la valeur affichée » (message neutre sinon) et note. « Valeur
   calculée » au lieu de « Valeur extraite », pas de crayon de correction.
3. **Base de données** : grand titre « Indicateurs comparables » avec les
   seuls KPIs présents, badges « Calculé » + « Vérifié » / « Non
   vérifié », description en bas de carte.
4. **Analyse individuelle** : catégorie « I — Indicateurs comparables »
   (vraies `KpiCard`, description, clic → même fenêtre).
5. **Analyse comparative** : 6 KPIs dans `KPI_DEFINITIONS` (tableau,
   barres, sélecteur, vues agrandies) ; catégorie fermée par défaut comme
   les autres ; filtre « Indicateurs comparables » ; verdicts lus dans la
   matrice ; avertissements exclus des agrégats et périmètre majoritaire
   (logique existante) ; S/P non-vie « sans objet » hors Non-vie /
   Santé-prévoyance. Export CSV toujours masqué.
6. **Aide « i »** : données (21 extraits + 6 calculés), cartes
   « Indicateurs comparables », comparaison en points, S/P « sans objet »,
   catégories du tableau.
7. **Bonus Phase 1** : « Source : » en français simple pour les cartes à
   avertissement (`sourceLisible`).

## Vérification visuelle

- La Mondiale (les 6 KPIs) : Base de données, fenêtre de détail du ratio
  sans mesures (6 composants, recalcul cohérent), lien « Voir le KPI
  SCR total », Analyse individuelle (catégorie I), détail de l'impact VA.
- Generali Vie (4 KPIs, modèle interne) : bascule de PDF dans la fenêtre
  (rapport narratif p. 36 → annexe QRT p. 9).
- MGEN (sans VA ni transitoire) : mobile 375 px en mode sombre, note
  « n'applique ni correction pour volatilité ni mesure transitoire ».
- Analyse comparative (pairs de MAIF, Non-vie) : catégorie I fermée puis
  ouverte (5 KPIs), barres du S/P non-vie (n/d pour Macifilia, Thémis).

## Écarts prompt / code réel, lectures retenues

- L'ancien bloc `indicateurs-comparables.tsx` n'affichait **que** les 6
  indicateurs promus (dont `position_mcr`) : il n'y avait pas « d'autres
  indicateurs » à y laisser. Son rendu est masqué (commenté, comme
  `PositionMarche` l'était), le fichier est conservé (non supprimé).
- Le tableau comparatif ne classe pas les nouveaux KPIs (pas de rang ni de
  vert / rouge meilleur-pire) : la coloration meilleur / pire du tableau
  utilise le rouge et le vert, réservés au feu tricolore. Le classement
  vient en Phase 3 (« Position parmi les pairs »).
- Les cartes existantes de l'Analyse individuelle ne sont pas rendues
  cliquables (seules les 6 nouvelles le sont, comme demandé).
