# Rapport — Textes de source et de comparabilité en français simple (Décision 161)

Date : 16/10/2026. Tag de départ : `avant-notes-simples`. Sauvegardes (non
commitées) : `archive/kpis_avant_notes_simples_20261016.db`,
`archive/donnees-extraites_avant_notes_simples.json`,
`archive/kpi-sources_avant_notes_simples.json`.

## En bref

- **381 textes distincts réécrits.** Ils apparaissent 1 077 fois dans
  `donnees-extraites.json` :

  | Texte | Textes distincts | Occurrences |
  |---|---|---|
  | `chapitreSource` (la « Source : » d'un KPI) | 338 | 856 KPIs |
  | Libellés des lignes de détail | 35 | 213 lignes |
  | Notes de la matrice de compatibilité | 7 | 7 |
  | Règle de compatibilité | 1 | 1 |

- **Déjà propres, non modifiés :** les notes d'avertissement, `sourceLisible`,
  les définitions des indicateurs et des KPIs calculés, et les règles et
  notes de calcul.
- **Recherche finale :** aucun jargon dans les 3 894 textes affichés des deux
  JSON. 61 sources citent encore un tableau officiel, toujours avec son nom
  en clair, par exemple « Tableau officiel S.23.01 (fonds propres) ».
- **Aucune valeur, aucun statut « Vérifié » et aucune page n'ont changé.**

## Comment

- **Où :** `corrections_comparabilite.py` applique les réécritures en
  dernière étape (nouveau fichier `textes_simples.py`). Elles sont donc
  rejouées après chaque réextraction. Si un texte ne correspond à aucune
  règle connue, le script s'arrête au lieu de réécrire au hasard.
- **Trace technique gardée :** l'ancien texte est conservé à l'identique en
  base, dans une nouvelle colonne `source_chapter_technique` (non exportée),
  pour les 861 lignes.
- **Libellés de lignes :** un garde-fou vérifie que chaque ligne reste
  classée de la même façon (vie ou non-vie). Sinon le S/P non-vie
  bougerait.

## 10 exemples avant → après

| # | Avant | Après |
|---|---|---|
| 1 | `D.2` | Rapport, chapitre D.2 (provisions techniques) |
| 2 | Document combiné 'AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf' (288p), entité isolée — S.25.01.21/R0010 (mapping, formule standard) | Tableau officiel S.25.01 (SCR en formule standard) — rapport commun du groupe AG2R La Mondiale, partie consacrée à la société |
| 3 | Document combiné 'Aéma Groupe RAPPORT UNIQUE...' (621p), entité isolée pages 452-467 (extraction manuelle sur rendu image, cf. Décision 083) — S.23.01.01.01/R0580 — confirmé p.464 (S.25.01.21.02/R0220) et p.467 (S.28.01.01.05/R0310) | Tableau officiel S.23.01 (fonds propres) — rapport unique du groupe Aéma, partie consacrée à la société ; lu sur une page image ; recoupé avec les pages 464 et 467 |
| 4 | … (Décision 093)) — S.02.01.02.01 Bilan, R0590 seul | Tableau officiel S.02.01 (bilan prudentiel) — … ; une seule ligne : santé similaire à la non-vie |
| 5 | S.23.01.01/R0540/C0030 imprimé « - » (p.61) | Tableau officiel S.23.01 (fonds propres) — case vide ou « - » dans le tableau (zéro) |
| 6 | Jeu SCR cohérent modèle interne (Décision 150) — S.25.05.21 (annexe QRT p.9), lignes « - diversified » ; scr_diversification = R0030 − somme des lignes diversifiées (−912 M€…). scr_souscription_vie = vie ET santé (R0410). | Modèle interne — tableau officiel S.25.05 (SCR calculé par le modèle interne), annexe page 9 : montants par risque après diversification à l'intérieur de chaque risque ; la diversification entre risques est le total moins la somme des risques (−912 M€, comme dans le rapport page 89) ; le risque vie inclut la santé. |
| 7 | A.2 — signe d'une ligne corrigé p.113 (Décision 160) | Rapport, chapitre A.2 (résultats de souscription) — signe d'une ligne corrigé d'après la page 113 |
| 8 | Libellé : Primes : brutes – reassu- rance proportion- nelle acceptee r0220 | Primes : brutes – réassurance proportionnelle acceptée |
| 9 | Libellé : Brut – assurance directe [composante vie (~30 615 K€, p.114) exclue — colonnes rotées non parsable, Décision 084] | Brut – assurance directe [sans la part vie, environ 30 615 K€ page 114, non lue : tableau illisible] |
| 10 | Matrice : Modèle interne : inclus dans scr_souscription_vie (NULL). | Modèle interne : inclus dans le risque de souscription vie (pas de montant séparé). |

Règle de compatibilité, avant : « Pour un KPI et deux sociétés : pire
verdict parmi les axes où elles diffèrent (axe activité de
charge_sinistres : comparer classeSinistres, pas l'activité brute). »

Après : « Pour un indicateur et deux sociétés, on retient le verdict le
plus prudent parmi les critères où elles diffèrent. Pour la charge de
sinistres, on compare la nature des sinistres (vie ou non-vie), pas
l'activité déclarée. »

## Comparaison avant / après (toute la base, les deux JSON)

| Où | Changé | Identique |
|---|---|---|
| `kpis` | `source_chapter` (861 lignes) + nouvelle colonne `source_chapter_technique` | valeurs, statuts, pages, avertissements |
| `kpi_composants` | `composant_label` (213 lignes) | valeurs, pages, statuts |
| `validation_checks` | `details` (37 lignes du contrôle du S/P, qui citent les libellés) | résultats des contrôles |
| `kpi_formules`, `companies`, `impact_mesures_lt` | — | identiques |
| `donnees-extraites.json` | 856 `chapitreSource`, 213 `label`, 7 notes de matrice, la règle, `genereLe` | tout le reste |
| `kpi-sources.json` | 856 `source_chapter` | tout le reste |

Le compteur interne d'identifiants de SQLite (`sqlite_sequence`) avance,
comme à chaque rejeu. Ce n'est pas une donnée.

## Tests

| Test | Résultat |
|---|---|
| `validate_kpis.py --all` (Python du .venv) | 0 échec réel |
| `test_kpis_officiels.py` (nouvelle section 7 : recherche du jargon, trace gardée) | OK, avec les 3 sauvegardes |
| `test_normalisation_signe.py` | OK |
| Réécriture rejouée deux fois sur une copie | résultat identique |

## Problèmes / à savoir

- **Revient sur la Décision 157,** qui gardait la base technique dans
  `chapitreSource`. Ce n'est plus le cas, la trace est maintenant dans
  `source_chapter_technique`.
- **Pour la fenêtre front :** le commentaire de
  `frontend/src/lib/donnees-extraites-utils.ts` (ligne 151) dit que
  `chapitreSource` « garde la base technique ». Ce n'est plus vrai. Je n'y
  ai pas touché.
- Les codes de ligne retirés des libellés restent dans le champ `codeQrt`,
  qui est fait pour cela.

## Commits

Voir `git log avant-notes-simples..HEAD`.
