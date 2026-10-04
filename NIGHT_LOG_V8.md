# NIGHT LOG V8 — Vérification finale exhaustive

Statut global : EN COURS

## Résumé (mis à jour au fur et à mesure)
- **RÉSERVE 1** : 0/273 KPIs Aéma vérifiés (en cours)
- **RÉSERVE 2** : déjà résolue en V6/Décision 119 — re-vérification rapide en cours
- **RÉSERVE 3** : pas commencée
- **Bugs corrigés cette nuit** : 0 (jusqu'ici)

## Progression RÉSERVE 1 (coché = entité terminée)
- [x] MACIF SAM — 20/20 ✅, 0 erreur (pages 453,455,463,464 rendues ; 465 pas nécessaire, R0130 déjà visible sur 464)
- [x] Aéma Groupe — 20/20 ✅, 0 erreur (pages 440,442,446,448 rendues, tous recoupements exacts)
- [x] Macif Vie — 20/20 ✅, **1 bug trouvé et corrigé** : best_estimate/marge_risque pointaient page 468 (recto Actifs du bilan) au lieu de 469 (verso Passifs, où sont réellement les lignes Meilleure estimation/Marge de risque) — valeurs elles-mêmes déjà correctes, uniquement la page. Corrigé dans kpis.db ET aema_entites.py (Décision 121).
- [x] Macif Santé Prévoyance — 20/20 ✅, 0 erreur
- [x] Thémis — 20/20 ✅, 0 erreur
- [x] Macifilia — 20/20 ✅, 0 erreur
- [x] Aésio Mutuelle — 20/20 ✅, 0 erreur
- [x] MNPAF — 20/20 ✅, 0 erreur
- [x] MMJ — 20/20 ✅, 0 erreur (best_estimate/marge_risque p.552 confirmés frais ; primes/charge p.554, fonds propres p.559, SCR p.560 déjà confirmés V3/V4)

## ARRÊT SESSION (limite d'usage atteinte) — reprendre ici

7/13 entités Aéma terminées : MACIF SAM, Aéma Groupe, Macif Vie, Macif Santé Prévoyance,
Thémis, Macifilia, Aésio Mutuelle, MNPAF, MMJ (9 en fait, liste ci-dessus à jour).
**Reste à faire RÉSERVE 1** : Nuoma, Abeille Vie, Abeille Épargne Retraite, Abeille IARD Santé
(4 entités Aéma), puis RÉSERVE 2 (déjà résolue V6, re-confirmation rapide seulement),
RÉSERVE 3 (sommes calculées — motif déjà bien établi par les KPIs sommes rencontrés
ci-dessus, tous vérifiés exacts), puis TÂCHE 4 (20 KPIs seed=42).

**Bilan jusqu'ici : 180/273 KPIs Aéma vérifiés (9 entités × 20), 1 bug trouvé et corrigé**
(Macif Vie best_estimate/marge_risque : page 468→469, Décision 121, déjà commité dans
kpis.db ET aema_entites.py). Méthode : rendu PNG 200 DPI par page unique (plusieurs KPIs
partagent la même page), lecture ligne QRT par ligne QRT, comparaison exacte à la valeur
stockée. 0 autre écart trouvé sur les 8 autres entités.
- [ ] Nuoma
- [ ] Abeille Vie
- [ ] Abeille Épargne Retraite
- [ ] Abeille IARD Santé
