# Rapport — S/P non-vie « Vérifié » et pages source Covéa (Décisions 159 et 160)

Date : 16/10/2026. Tag de départ : `avant-sp-covea`. Sauvegardes (non
commitées) : `archive/kpis_avant_sp_covea_20261016.db`,
`archive/donnees-extraites_avant_sp_covea.json`,
`archive/kpi-sources_avant_sp_covea.json`.

## Mise à jour — tes deux décisions appliquées (Décision 160)

Tag `avant-maif-signe`. Sauvegardes : `archive/kpis_avant_maif_signe_20261016.db`,
`archive/donnees-extraites_avant_maif_signe.json`,
`archive/kpi-sources_avant_maif_signe.json`.

| | Avant | Après |
|---|---|---|
| Ligne MAIF « sinistres – réassurance non proportionnelle acceptée » | +2,097 M€ | **−2,097 M€** (comme p.113) |
| Charge de sinistres MAIF | 2 393,639 M€ | **2 389,445 M€** |
| S/P non-vie MAIF | 60,4 %, non vérifié | **60,3 %, « Vérifié »** |
| Échecs MAIF du contrôle | 4 | **0** |
| S/P non-vie vérifiés | 14 sur 25 | **15 sur 25** |
| Page source `best_estimate` / `marge_risque` Covéa | vide | **85** (le KPI et ses 5 lignes) |

- La correction est écrite dans `corrections_comparabilite.py` (sections 7
  et 8). Elle est donc rejouée après chaque réextraction. Si la ligne ne
  ressemble plus à celle attendue, le script s'arrête au lieu de corriger
  au hasard.
- La cause est le format comptable : le signe « - » est séparé du nombre,
  et le lecteur de libellés ne le voit pas. Le lecteur n'a pas été modifié.
- **Rien d'autre n'a changé** (comparaison avec la sauvegarde). Seuls deux
  autres contrôles bougent : signe et ordre de grandeur de la charge de
  sinistres MAIF. Ils prennent la nouvelle valeur et passent toujours.

**Le même défaut existe-t-il ailleurs ? Non.** J'ai cherché sur 1 187
montants positifs (pages avec texte) ceux qui sont imprimés avec un « - »
devant. En dehors de MAIF, il n'y a que 2 fausses alertes :

| Société | Montant | Explication |
|---|---|---|
| MAIF | fonds propres niveau 2 (9 725 K€) | le tiret est la case vide d'à côté ; 5 319 982 + 9 725 = 5 329 707 |
| AG.Mut | marge de risque (117 K€) | le « -117 » de la p.207 est une case du triangle des sinistres, sans rapport |

**Autre problème trouvé :** la page source de `marge_risque` d'AG.Mut
était la page 207 (le triangle des sinistres), alors que ses lignes sont
page 199. → **Corrigé depuis, à ta demande (voir ci-dessous).**

### AG.Mut : page source de la marge de risque 207 → 199

Tag `avant-agmut-page`, sauvegardes `archive/*_avant_agmut_page*`.

- **Vérifié avant de corriger.** La page 199 est le passif du bilan
  d'AG.Mut, dans la section AG.Mut du rapport du groupe AG2R (pages 198 à
  215). On y lit :
  - le best estimate (22 885) ;
  - la marge de risque : 116 + 1 = 117 K€, c'est-à-dire la valeur du KPI.

  Les 5 lignes de détail étaient déjà page 199. La page 207 est le
  triangle des sinistres.
- **Seule cette page a changé.** Elle change aux trois endroits où elle
  figure : le KPI `marge_risque`, et ses deux copies faites
  automatiquement par le calcul de `marge_risque_sur_be`. Aucune valeur,
  aucun contrôle et aucun statut « Vérifié » n'ont bougé.
- **Fichiers de données :** dans `donnees-extraites.json`, 3 pages et
  `genereLe` changent. Dans `kpi-sources.json`, 2 pages changent.
- **Laissé tel quel, comme demandé :** la ligne « Marge de risque » du
  détail de `provisions_techniques` d'AG.Mut indique encore la page 207.
  Elle est recopiée une seule fois, au moment de l'extraction. Je peux la
  corriger aussi si tu veux.
- **Tests :** `validate_kpis.py --all` (0 échec réel),
  `test_kpis_officiels.py` (OK avec les 3 sauvegardes) et
  `test_normalisation_signe.py` (OK).

Limite : 59 pages sont des images (annexes du rapport Aéma, Generali IARD,
Groupama…) et ne peuvent pas être relues de cette façon.

**Fichiers modifiés :**
- code : `corrections_comparabilite.py`, `peupler_kpis_officiels_indicateurs.py`
  (repli page 85 supprimé, devenu inutile) et `test_kpis_officiels.py` ;
- données : `kpis.db`, `donnees-extraites.json` et `kpi-sources.json`.

Les deux fichiers de données sont régénérés par le même export. Dans
`kpi-sources.json`, 6 champs changent : charge et S/P de MAIF, pages de
Covéa.

**Tests :**
- `validate_kpis.py --all` (Python du .venv) : 0 échec réel ;
- `test_kpis_officiels.py` : OK, avec les deux sauvegardes ;
- `test_normalisation_signe.py` : OK ;
- `corrections_comparabilite.py` rejoué deux fois : même résultat.

## A. S/P non-vie : 14 « Vérifié » sur 25 (0 avant) — 15 après la Décision 160

Nouveau contrôle dans `validate_kpis.py`. Pour chaque société, le script
ouvre la page source du tableau des primes et sinistres (S.05.01) et
vérifie trois choses :

1. chaque montant de primes et de sinistres utilisé est bien imprimé sur la
   page, dans la bonne partie du tableau (« Primes acquises » ou « Charge
   des sinistres ») ;
2. le tableau tombe juste : brut − part des réassureurs = net, avec les
   montants imprimés. Ce calcul contrôle aussi les signes et les lignes à
   zéro ;
3. sinistres ÷ primes × 100 = la valeur du KPI (à 0,05 près).

Le KPI n'est « Vérifié » que si tout concorde.

| Résultat | Nombre | Sociétés | Pourquoi |
|---|---|---|---|
| Vérifié | 14 | AG.Mut, AG2R Prévoyance, AXA France IARD, AXA France Vie, Arpège Prévoyance, BPCE Assurances IARD, Cardif Risques Divers, Covéa, Crédit Agricole Assurances, La Mondiale, MGEN, Prima, SGAM AG2R LA MONDIALE, VIASANTE Mutuelle | tout concorde |
| Non vérifié | 8 | Aéma Groupe, MACIF SAM, Macif Santé Prévoyance, Aésio Mutuelle, MNPAF, MMJ, Nuoma, Abeille IARD Santé | les pages des tableaux du rapport Aéma sont des images : pas de texte à lire |
| Non vérifié | 2 | Generali IARD (p.4), Groupama (p.80) | page image, pas de texte à lire |
| Non vérifié | 1 | MAIF | **écart réel** sur les sinistres, voir ci-dessous (primes vérifiées) |

**Problème trouvé chez MAIF (pas corrigé, à décider).** Page 113, la ligne
« sinistres – réassurance non proportionnelle acceptée » est imprimée
**−2 097 milliers d'euros**. En base, on a **+2,097 M€** : le signe est
faux. Le tableau le prouve : 2 367 845 + 23 697 − 2 097 − 281 401 =
2 108 044, exactement le net imprimé. Avec +2 097, le calcul ne tombe pas
juste. Conséquence : le S/P non-vie de MAIF serait de 60,3 % au lieu de
60,4 %, et sa charge de sinistres est trop haute de 4,2 M€. → **Corrigé
depuis, à ta demande (voir la mise à jour en haut).**

## B. Covéa : la page 85 est la bonne, rien n'est changé

- J'ai cherché les montants dans les 99 pages du SFCR Covéa.
- Le best estimate total (84 032 648 K€) et la marge de risque totale
  (5 263 956 K€) ne sont imprimés **nulle part** sous forme de total.
- Les 10 lignes qui les composent (5 « Meilleure estimation », 5 « Marge
  de risque ») sont toutes à la **page 85** (bilan S.02.01.02, passif).
  Leur somme donne exactement les deux KPIs.
- Le chapitre D2.1 (p.65) donne des chiffres nets de réassurance, donc
  différents (24 416 + 47 991 + 8 179 M€) : ce n'est pas la bonne source.

| | Avant | Après |
|---|---|---|
| Page utilisée pour les composants | 85 | 85 (vérifiée, inchangée) |
| Page des KPIs `best_estimate` / `marge_risque` en base | vide | vide (inchangée) |
| `marge_risque_sur_be` Covéa (6,26 %) | Vérifié | Vérifié |

Le repli « page 85 » ne sert qu'à Covéa : aucune autre société ne
l'utilise. À savoir, sans lien avec ce repli : ces deux KPIs de Covéa et le
`ratio_mcr` de CNP n'ont pas de page source en base. Certaines lignes de
détail n'en ont pas non plus (`provisions_techniques` de 8 sociétés, primes
et sinistres de CNP). → **Page 85 écrite en base depuis, à ta demande.**

## Ce qui a changé (comparaison avant / après)

| Fichier | Changement |
|---|---|
| `frontend/src/data/donnees-extraites.json` | 14 `sp_nonvie.valide` passent à `true`, 75 `composants[].valide` passent à `true`, `genereLe`. Rien d'autre. |
| `frontend/src/data/kpi-sources.json` | inchangé |
| `kpis.db` | `validated` de 14 `sp_nonvie` ; `composant_valide` de 75 lignes ; 169 contrôles ajoutés dans `validation_checks`. Aucune valeur modifiée. |
| `validate_kpis.py` | nouveau contrôle 12 |
| `peupler_kpis_officiels_indicateurs.py` | les lignes de `sp_nonvie` sont valides si le contrôle 12 les a retrouvées |
| `test_kpis_officiels.py` | nouvelle section 6 |
| `DECISIONS.md`, `PIPELINE_EXTRACTION_KPIs.md`, ce rapport | documentation |

Les 21 KPIs extraits et les 5 autres KPIs calculés n'ont pas changé : mêmes
valeurs, même statut « Vérifié », mêmes contrôles 1 à 11.

## Tests lancés

| Test | Résultat |
|---|---|
| `validate_kpis.py --all` (Python du .venv) | OK ; seuls nouveaux échecs : les 4 contrôles des sinistres MAIF |
| `test_kpis_officiels.py` (avec la nouvelle section 6) | OK |
| `test_normalisation_signe.py` | OK |
| Comparaison base + JSON avec la sauvegarde | seuls les champs listés plus haut ont bougé |

## À savoir

- `validate_kpis.py` doit maintenant être lancé avec le Python du `.venv`
  (`.venv/Scripts/python.exe -I validate_kpis.py --all`), car il lit les
  PDF. Avec le Python système, aucun S/P n'est vérifié et un message le
  signale.
- Rien n'a été modifié dans `frontend/` à part le fichier de données
  exporté `donnees-extraites.json`.

## Commits

Voir `git log avant-sp-covea..HEAD` (Décision 159) et
`git log avant-maif-signe..HEAD` (Décision 160) ; page AG.Mut :
`git log avant-agmut-page..HEAD`.
