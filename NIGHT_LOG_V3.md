# NIGHT_LOG_V3.md — session de nuit 01/10/2026

Investigation forensique : 4 valeurs KPI signalées introuvables dans
leur PDF source. Diagnostic d'abord, correctif seulement pour les cas
triviaux et sûrs (comme demandé).

## STATUT : FAIT (Tâche 1, priorité absolue) + extension bonus ciblée

**Verdict global : 3 des 4 cas cités étaient en réalité CORRECTS**
(fausses alertes — "introuvable par pdftotext" ne veut pas dire
"inventé", comme déjà établi Décision 112). **1 cas était un vrai bug**
(MMJ). En vérifiant le même type d'erreur sur les entités voisines
utilisant le même gabarit de tableau, **1 bug supplémentaire non cité
a été trouvé** (Thémis, 2 valeurs). Les 3 valeurs fausses ont été
corrigées après vérification visuelle directe (rendu PNG + lecture),
jamais devinées. Voir Décision 116 (DECISIONS.md) pour le détail complet.

---

### Cas 1 : MMJ | charge_sinistres

- **Script source** : `aema_entites.py`, dict `ENTITES_KPIS["MMJ"]`
- **Méthode** : valeur codée en dur, lecture manuelle sur rendu image
  (page 554, 100% image — aucune couche texte, donc `pdftotext` ne
  peut RIEN trouver sur cette page, pour AUCUNE valeur, pas seulement
  celle-ci)
- **Traçabilité** : la ligne de code annonçait "R0310/Total" (Charge
  des sinistres, Brut – assurance directe) mais contenait en réalité
  la valeur de **R0300** (Primes acquises, Net) — 2 lignes adjacentes
  sur un tableau QRT tourné à 90°, faciles à confondre à la lecture.
- **Vérification visuelle** : rendu PNG de la page 554 (`S.05.01.02.01`,
  tableau "Primes, sinistres et dépenses par ligne d'activité - Non
  vie"). Lecture ligne par ligne confirmée : R0300 (Net, Primes
  acquises) = **69 127 735** (la valeur stockée) ; R0310 (Brut –
  assurance directe, Charge des sinistres) = **55 926 771** (la vraie
  valeur du KPI).
- **Verdict** : ❌ **Valeur incorrecte.** Corrigée : 69 127 735 → 55 926 771.
  (`primes_acquises_brutes` de la même entité, elle, était déjà
  correcte — vérifiée = R0210 = 70 690 019, confirmé sur le même rendu.)

### Cas 2 : Cardif Assurance Vie | charge_sinistres

- **Script source** : `extract_kpis_cardifvie.py`, via
  `ek.resoudre_variantes_qrt("charge_sinistres", ...)`
  (`kpi_qrt_mapping.py`)
- **Méthode** : somme automatique de 2 lignes QRT réelles, extraites
  nativement (texte, pas image) via `extract_qrt_native()` : R1610
  (vie, template S.05.01.02 page 6, colonne Total C0300) + R0310/R0320/
  R0330 (non-vie, même template page 5, colonne Total C0200).
- **Traçabilité** : corpus relu directement (pas supposé) —
  R1610/C0300 = 14 697 034 ; R0310/C0200 = 291 475 ; R0320 = R0330 = 0.
  Somme = 14 988 509 (±1 arrondi) ≈ **14 988 508** (valeur stockée).
- **Vérification visuelle** : non nécessaire, extraction texte native
  (pas d'image), valeurs relues directement dans le corpus structuré
  construit par `extract_qrt_native()`.
- **Verdict** : ✅ **Valeur correcte.** Normal qu'elle soit introuvable
  en tant que chaîne littérale dans le PDF : c'est une SOMME de 2
  cellules QRT réelles sur 2 pages différentes (5 et 6), jamais
  imprimée telle quelle nulle part. Limite mineure notée : le
  `source_page` stocké (5) ne couvre qu'une partie de la somme (la
  partie vie, dominante, vient de la page 6) — pas une erreur, mais
  incomplet pour la navigation PDF depuis le frontend (chantier futur
  possible, hors scope ce soir).

### Cas 3 : Crédit Agricole Assurances | primes_acquises_brutes

- **Script source** : `extract_kpis_creditagricole.py`, lignes 145-150
  (valeur codée en dur avec justification documentée en commentaire,
  pas une extraction automatique)
- **Méthode** : lecture manuelle directe de la colonne Total imprimée,
  S.05.01.02 (texte natif, pas image) : page 69 (2/3, non-vie) +
  page 70 (3/3, vie), puis somme.
- **Traçabilité et vérification visuelle** : rendu PNG des pages 69 et
  70. Page 69 confirmée être une page de DONNÉES réelles (pas une page
  de titre comme le prompt le supposait) : R0210 (Primes acquises,
  Brut – assurance directe, non-vie) = **7 440 062**, R0220 = 130 014,
  R0230 = 0 → sous-total non-vie = 7 570 076. Page 70 : R1510 (Primes
  acquises, Brut, vie, colonne Total C0300) = **41 602 922**. Somme
  = 7 570 076 + 41 602 922 = 49 172 998 K€ = 49 173,00 M€ — **exacte
  correspondance** avec la valeur stockée (49 173,00 M€).
- **Verdict** : ✅ **Valeur correcte.** Le prompt avait mal identifié
  la page 69 comme "titre du tableau" — en réalité la page 69 EST déjà
  les données non-vie (le tableau S.05.01.02 est étalé sur 3 pages
  1/3-2/3-3/3 dans ce PDF, p.68=1/3 sans doute vide/présentation,
  p.69=2/3 non-vie, p.70=3/3 vie). Introuvable comme chaîne littérale
  pour la même raison que le Cas 2 : somme de 2 cellules réelles sur 2
  pages.

### Cas 4 : Abeille Vie | fonds_propres_t2

- **Script source** : `aema_entites.py`, dict
  `ENTITES_KPIS["Abeille Vie"]`
- **Méthode** : valeur codée en dur, lecture manuelle sur rendu image
  (page 588, 100% image comme tout le bloc QRT Aéma 439-621 — AUCUNE
  valeur de cette page n'est trouvable par `pdftotext`, pas seulement
  celle-ci).
- **Traçabilité** : S.23.01.01.01, ligne R0540 ("Total des fonds
  propres éligibles pour couvrir le capital de solvabilité requis"),
  colonne "Niveau 2".
- **Vérification visuelle** : rendu PNG de la page 588. Lu
  explicitement dans le tableau : ligne R0540, colonne Niveau 2 =
  **998 728 480** — correspond EXACTEMENT à la valeur stockée.
  Recoupement interne supplémentaire (avant même le rendu) :
  fonds_propres_t1_nr (4 093 145 214) + t1_r (0) + t2 (998 728 480) +
  t3 (0) = 5 091 873 694 = fonds_propres_eligibles stocké, à l'euro
  près — cohérence interne parfaite, peu probable par coïncidence si
  une des 4 valeurs était fausse.
- **Verdict** : ✅ **Valeur correcte.** Introuvable par construction :
  page 100% image, aucune couche texte, confirmé par le fait qu'AUCUNE
  valeur de cette page (ni R0290, ni R0500, ni aucune autre) n'apparaît
  dans le texte natif du PDF — pas spécifique à ce KPI.

---

## Bug supplémentaire trouvé (hors 4 cas cités, même classe de risque)

Après avoir confirmé le Cas 1 (MMJ), j'ai vérifié par prudence si le
même type d'erreur (ligne adjacente confondue sur un tableau QRT
tourné 90°) existait sur les autres entités Aéma utilisant exactement
le même gabarit "non-vie seule, S.05.01.02.01" : Thémis, Macifilia,
MNPAF, Nuoma (5 entités au total avec MMJ). Macifilia, MNPAF et Nuoma
ont été vérifiées CORRECTES (rendu PNG + lecture ligne par ligne).
**Thémis avait 2 valeurs fausses**, trouvées et corrigées :

- `primes_acquises_brutes` : stockait en réalité R0110 (Primes
  **émises**, Brut – assurance directe = 1 899) au lieu de R0210
  (Primes **acquises**, Brut – assurance directe = 1 920) — confusion
  entre les 2 sections "Primes émises" / "Primes acquises" du même
  tableau, qui partagent le même libellé de première ligne. Corrigé :
  1 899 → 1 920 (K€).
- `charge_sinistres` : stockait R0300 (Primes acquises, Net = 1 920,
  qui vaut la même chose que R0210 ici car pas de réassurance) au lieu
  de R0310 (Charge des sinistres, Brut = 386). Corrigé : 1 920 → 386
  (K€).

Les deux ont été vérifiées sur le rendu PNG de la page 497 avant toute
correction.

**Portée de cette vérification bonus : limitée aux 5 entités du
gabarit "non-vie seule"** (sur les 13 entités Aéma au total). Un audit
complet des 273 KPIs "rendu image" (Tâche 2 du prompt) n'a PAS été
fait — hors du temps disponible ce soir, cf. section suivante.

---

## Tâches 2 et 3 (bonus, "si temps") : NON FAITES

Priorité donnée entièrement à la Tâche 1 (explicitement "PRIORITÉ
ABSOLUE" dans le prompt) et à la vérification ciblée ci-dessus, qui a
déjà révélé 1 bug non cité. Un audit systématique des 273 KPIs
"rendu image" ou un échantillon de 20 KPIs aléatoires n'a pas été
entamé — reste à faire dans une session future si souhaité. Étant
donné que la méthode de vérification (rendu PNG + lecture manuelle
page par page) est coûteuse en temps par KPI, un audit complet des 273
prendrait plusieurs sessions.

## Fichiers modifiés

`aema_entites.py` (3 valeurs corrigées : MMJ/charge_sinistres,
Thémis/primes_acquises_brutes, Thémis/charge_sinistres — chacune
commentée avec sa justification et renvoi à Décision 116), `kpis.db`
(mêmes 3 corrections), `frontend/src/data/donnees-extraites.json` +
`kpi-sources.json` (régénérés).
