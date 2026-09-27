# Pipeline d'extraction des KPIs actuariels — Documentation de référence

**Généré le 27/09/2026.** Décrit l'état RÉEL du code à cette date (vérifié
par lecture directe du code et requêtes sur `kpis.db`, rien de supposé
ni de théorique) — première version de ce document, jamais créé
auparavant dans ce dépôt.

Ce document explique comment un rapport SFCR (PDF) devient une ligne
dans `kpis.db`, sans avoir à lire le code source. Pour l'historique des
décisions techniques (pourquoi tel choix, quels bugs trouvés), voir
`DECISIONS.md`. Pour l'architecture générale du projet (RAG
conversationnel, Qdrant), voir `ARCHITECTURE.md` — hors périmètre ici.

---

## 1. Vue d'ensemble — un pipeline HYBRIDE, pas un pipeline unique

**Point le plus important à comprendre avant tout le reste** : il
n'existe PAS un pipeline générique unique appliqué automatiquement à
chaque société. **Les 34 sociétés actuellement dans `kpis.db` ont
chacune un script d'extraction dédié** (`extract_kpis_<societe>.py`,
ou un script à plusieurs entités pour les groupes AG2R/Aéma). Ces 34
scripts partagent des BRIQUES COMMUNES (décrites ci-dessous), mais
aucune société n'est passée par un pipeline "boîte noire" sans
intervention ni vérification spécifique à son document.

```
                    ┌─────────────────────────────────────┐
                    │   PDF SFCR (rapport annuel société)  │
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │ classify_pages()  — repère les pages   │
                    │ QRT (annexes quantitatives) dans le PDF │
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │ detecter_templates() — mode du document :│
                    │  codes_eiopa (codes R/C standard)      │
                    │  vs libelles_francais (pas de code)    │
                    └───────────────────┬───────────────────┘
                                        │
              ┌─────────────────────────┼─────────────────────────┐
              │                         │                         │
    ┌─────────▼─────────┐   ┌───────────▼───────────┐   ┌─────────▼─────────┐
    │ mode codes_eiopa   │   │ mode libelles_francais │   │ document 100%     │
    │ extract_qrt_native │   │ classifier_lignes() +  │   │ image (aucun texte│
    │ + resoudre_        │   │ extraire_par_libelle() │   │ natif)            │
    │ variantes_qrt()    │   │ + KPI_LABELS_FR        │   │ lecture manuelle  │
    │ (kpi_qrt_mapping)  │   │                        │   │ sur rendu PNG     │
    └─────────┬─────────┘   └───────────┬───────────┘   └─────────┬─────────┘
              │                         │                         │
              └─────────────────────────┼─────────────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │  script extract_kpis_<societe>.py :    │
                    │  corrections/overrides scopés au       │
                    │  fichier + recoupement arithmétique    │
                    │  (jamais un chiffre non vérifié)       │
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │  INSERT/UPDATE dans kpis.db            │
                    │  (22 lignes par société, NULL si non   │
                    │  résolu — jamais une valeur devinée)   │
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │  validate_kpis.py — 46 contrôles       │
                    │  actuariels par société (cf. §4)       │
                    └───────────────────┬───────────────────┘
                                        │
                    ┌───────────────────▼───────────────────┐
                    │  kpi_service.py — couche de lecture    │
                    │  seule pour le futur dashboard         │
                    │  (get_kpi, compare, validation_summary)│
                    └─────────────────────────────────────────┘
```

### Les 3 voies d'extraction réellement utilisées

| Voie | Mécanisme | Sociétés (exemples) |
|---|---|---|
| **Texte natif, codes EIOPA** | `classify_pages()` → `extract_qrt_native()` → `resoudre_variantes_qrt()` (dictionnaire `kpi_qrt_mapping.py`, codes R0xxx/C0xxx standard) | Predica, MGEN, Crédit Agricole Assurances, Sogécap, Cardif Vie/RD, Allianz Vie, CNP (partiel), AG2R (9 entités) |
| **Texte natif, libellés français** | `classifier_lignes()` → `extraire_par_libelle()` (dictionnaire `kpi_labels_fr.py`, pas de code R/C — matching par texte exact) | MAIF, Covéa |
| **100% image** | Rendu PNG + lecture manuelle, vérifiée par recoupement arithmétique (jamais de simple "au jugé") | Les 13 entités du document combiné Aéma Groupe, Generali Iard/Vie (diagnostic seul), MACIF SAM |

**Une seule société (Groupama)** utilise en plus une 4e voie, historique
et non généralisée : triple validation Docling + PaddleOCR + Gemini
Vision sur une image de page QRT (`picture_75.png`), pour 5-6 KPIs de
détail SCR uniquement — ce n'est PAS un mécanisme systématique
réutilisé pour les autres sociétés, contrairement à ce qu'un ancien
document aurait pu laisser penser.

---

## 2. Étapes numérotées, du PDF à la base

1. **`classify_pages(pdf)`** (`test_markdrop/ingest.py`) — parcourt
   toutes les pages du PDF, tague chaque page `"qrt"` (annexe
   quantitative) ou non, et identifie le `template_id` (ex.
   `S.23.01.01`) par reconnaissance de motifs dans le texte/titre de
   page.
2. **`detecter_templates(pdf)`** (`detecter_templates.py`) — détermine
   `document_type` (`solo`/`groupe`), `scr_method`
   (`formule_standard`/`modele_interne`) et surtout `mode`
   (`codes_eiopa` si de vrais codes R0xxx/C0xxx sont trouvés,
   `libelles_francais` sinon).
3. **Extraction page par page** :
   - Mode `codes_eiopa` : `extract_qrt_native(page, sheet_dict)`
     découpe chaque page en lignes (codées R0xxx) et colonnes (codées
     C0xxx), construit un "corpus" structuré.
   - Mode `libelles_francais` : `classifier_lignes(texte_page)`
     regroupe le texte en paires (libellé, valeurs) sans code.
   - 100% image : rendu PNG (`fitz`, zoom ×2.5), lecture visuelle
     directe.
4. **Résolution des 22 KPIs** :
   - `resoudre_variantes_qrt(kpi_name, corpus, templates_presents)`
     (`extract_kpis.py`) essaie chaque variante connue du KPI (codes
     EN/FR, colonnes possibles) déclarée dans `kpi_qrt_mapping.py`,
     retourne la 1re qui matche un libellé officiel vérifié.
   - `extraire_par_libelle(texte, labels_candidats)`
     (`extraire_par_libelle.py`) fait l'équivalent pour le mode
     libellé français, avec priorité à l'égalité stricte du libellé.
5. **Corrections scopées au document** (dans chaque
   `extract_kpis_<societe>.py`, JAMAIS dans le code partagé sans test
   de régression complet) — ex. conversion d'unité (€ bruts vs K€,
   cf. §6), lecture manuelle d'une colonne Total quand l'extraction
   automatique échoue silencieusement sur une ligne précise.
6. **Insertion** — `INSERT ... ON CONFLICT DO UPDATE` dans `kpis.db`
   (idempotent, un ré-lancement du script met juste à jour).
7. **Validation** — `validate_kpis.py --company X` ou `--all` : 46
   contrôles actuariels par société (cf. §4), jamais silencieux,
   chaque résultat écrit et lisible.
8. **Lecture** — `kpi_service.py`, couche 100% lecture seule pour le
   futur dashboard (aucune écriture, `extract_kpis*.py`/
   `validate_kpis.py` restent les seuls écrivains sur `kpis.db`).

---

## 3. Les 22 KPIs et leur source QRT

| KPI | Catégorie | Unité | Source QRT | Chapitre SFCR | Signe attendu |
|---|---|---|---|---|---|
| `ratio_scr` | solvabilité | % | S.23.01 | E.1 | positif |
| `ratio_mcr` | solvabilité | % | S.23.01 | E.1 | positif |
| `fonds_propres_eligibles` | fonds propres | M€ | S.23.01 | E.1 | positif |
| `fonds_propres_t1_nr` | fonds propres | M€ | S.23.01 | E.1 | positif |
| `fonds_propres_t1_r` | fonds propres | M€ | S.23.01 | E.1 | positif |
| `fonds_propres_t2` | fonds propres | M€ | S.23.01 | E.1 | positif |
| `fonds_propres_t3` | fonds propres | M€ | S.23.01 | E.1 | positif |
| `scr_total` | scr | M€ | S.25.01 | E.2 | positif |
| `scr_marche` | scr | M€ | S.25.01 | E.2 | positif |
| `scr_souscription_vie` | scr | M€ | S.25.01 | E.2 | positif |
| `scr_souscription_nonvie` | scr | M€ | S.25.01 | E.2 | positif |
| `scr_souscription_sante` | scr | M€ | S.25.01 | E.2 | positif |
| `scr_contrepartie` | scr | M€ | S.25.01 | E.2 | positif |
| `scr_operationnel` | scr | M€ | S.25.01 | E.2 | positif |
| `scr_diversification` | scr | M€ | S.25.01 | E.2 | **négatif** |
| `best_estimate` | provisions | M€ | S.02.01 | D.2 | positif |
| `marge_risque` | provisions | M€ | S.02.01 | D.2 | positif |
| `provisions_techniques` | provisions | M€ | S.02.01 (calculé) | D.2 | positif |
| `mcr` | mcr | M€ | S.28.01 | E.2 | positif |
| `primes_acquises_brutes` | activité | M€ | S.05.01 | A.2 | positif |
| `charge_sinistres` | activité | M€ | S.05.01 | A.2 | positif |
| `resultat_technique` | activité | M€ | S.05.01 | A.2 | any (NULL par construction, aucun équivalent QRT standardisé trouvé) |

`provisions_techniques` = `best_estimate` + `marge_risque` (calculé,
jamais lu directement — identité vérifiée par le contrôle 1, cf. §4).

---

## 4. `validate_kpis.py` — 46 contrôles actuariels (par société complète)

Le nombre exact varie selon les KPIs réellement non-NULL pour la
société (un KPI NULL fait sauter proprement les contrôles qui en ont
besoin, jamais de calcul sur `None`). **46 est le nombre pour une
société avec 21/22 KPIs remplis** (le cas le plus fréquent) ; Groupama
en a 49 (3 contrôles supplémentaires qui lui sont spécifiques, cf.
ci-dessous).

| # | Contrôle | Description |
|---|---|---|
| 1 | `provisions_techniques_somme` | `best_estimate + marge_risque = provisions_techniques` (identité de construction) |
| 2 | `fonds_propres_eligibles_somme_tiers` | Somme des 4 tiers = `fonds_propres_eligibles` |
| 3 | `ratio_scr_recalcule` | `fonds_propres_eligibles / scr_total × 100` vs `ratio_scr` publié, tolérance 1% |
| 4 | `ratio_mcr_recalcule` | Idem pour MCR — **Groupama uniquement** (seule société avec une source indépendante du numérateur MCR-éligible) |
| 5 | `mcr_inferieur_scr_total` | Invariant de base : MCR < SCR total |
| 6-7 | Croisements SCR codés en dur | **Groupama uniquement** (valeurs vérifiées manuellement en 2025, Décision 051) |
| 8 | `signe_<kpi_name>` | 1 contrôle par KPI non-NULL : signe conforme à `kpi_definitions.py` (~16-20 contrôles selon la société) |
| 9 | `completude_22_kpis` + `completude_null_attendu` | Exactement 22 lignes, exactement les NULL attendus (`resultat_technique` seul, sauf limites documentées) |
| 10 | **`magnitude_<kpi_name>`** (Décision 095, nouveau) | 1 contrôle par KPI en M€ non-NULL : plafond de 100 000 M€ (SCR/MCR/fonds propres/primes/sinistres) ou 1 000 000 M€ (best_estimate/marge_risque/provisions_techniques — structurellement plus grands) |

### Pourquoi le contrôle de magnitude (10) a été ajouté

Les contrôles 1-9 sont tous des **ratios entre 2 KPIs de la même
société** — un bug qui multiplie 2 KPIs par le même facteur (ex. tout
en €, pas en K€) laisse le ratio recalculé inchangé et **passe
inaperçu**. C'est exactement ce qui s'est produit : un bug d'unité
(€ bruts confondus avec K€) a inflaté ×1000 tous les KPIs de 7 entités
du groupe Aéma, et un bug de double-comptage a gonflé
`primes_acquises_brutes`/`charge_sinistres` de ×2 à ×3,95 sur
Groupama/Predica/MGEN — sans qu'AUCUN des 9 contrôles précédents ne le
détecte, sur plusieurs sessions. Le contrôle de magnitude compare
chaque valeur à un plafond absolu (pas relatif à une autre valeur de
la même société), et a depuis attrapé un 3e cas en conditions réelles
dès sa mise en service (Sogécap : `scr_total` calculé à 4,26 billions
d'euros, détecté immédiatement).

**Limite assumée** : un facteur ×2 à ×4 sur un KPI déjà petit reste
indétectable par un plafond absolu (le seuil doit rester au-dessus du
maximum légitime observé) — ce contrôle attrape la classe de bug la
plus grave (erreur d'ordre de grandeur), pas toutes les erreurs
possibles.

---

## 5. État actuel réel (vérifié par requête directe, 27/09/2026)

- **34 sociétés** dans `kpis.db`.
- **748 lignes KPI** au total (34 × 22), **50 NULL**, **698 valeurs
  remplies** — **93,3 % de taux de remplissage global**.
- **1 521 / 1 529 contrôles actuariels passés (99,5 %)** sur
  l'ensemble des 34 sociétés (`validate_kpis.py --all`).
- Les 8 échecs restants sont **tous légitimes et documentés** (aucun
  bug non résolu) : 4 cas de complétude attendue (sociétés avec des
  KPIs structurellement irréductibles, cf. §6), 2 cas de plancher MCR
  absolu (petites structures), 1 cas de signe négatif vérifié
  (reprise de provision), 1 cas combinant les deux derniers.

---

## 6. Limites connues — honnêtes, pas cachées

- **Une seule société a eu un audit manuel humain complet** : Predica
  (relecture ligne par ligne du PDF contre `kpis.db`, qui a trouvé et
  corrigé le bug de signe détaché à l'origine de la Décision 091). Les
  33 autres reposent sur la cohérence interne (recoupements
  arithmétiques, contrôles actuariels) mais pas sur une relecture
  humaine indépendante systématique.
- **KPIs structurellement irréductibles** (jamais résolus, quel que
  soit l'effort — pas un manque d'investigation) :
  - **Allianz Vie** : `scr_marche`/`scr_contrepartie` fusionnés dans
    une seule ligne QRT (modèle interne), `scr_souscription_vie`/
    `scr_souscription_sante` fusionnés de même, `scr_diversification`
    bloqué par un signe détaché non couvert par le détecteur générique.
  - **MAIF** : `fonds_propres_t1_r`/`t2`/`t3` (colonnes vides
    ambiguës), composante vie de `charge_sinistres` (tableau à
    libellés tournés 90°, non parsable).
  - **Covéa** : les 4 tiers de fonds propres détaillés (aucun libellé
    connu pour eux sur ce document précis).
  - **AFV/AFI (AXA France Vie/IARD)** : côté modèle interne comme
    Allianz — **non extraites à ce jour**, diagnostiquées seulement
    (16/20 chacune), jamais insérées dans `kpis.db`.
- **4 des 15 groupes du marché français visés n'ont AUCUNE extraction
  réelle en base** (diagnostic ancien seulement, jamais migré) : AXA
  (AFV/AFI), BPCE (BPCE Vie/IARD), Generali (Iard/Vie), SwissLife —
  cf. Décision 102 pour le détail. **11 groupes sur 15** ont au moins
  une entité réellement dans `kpis.db`.
- **4 bugs positionnels connus, non généralisés** (le même type
  d'échec silencieux de `extract_qrt_native()` sur une ligne précise,
  rencontré sur Crédit Agricole Assurances et Allianz Vie) — corrigés
  au cas par cas par lecture manuelle vérifiée de la colonne Total,
  jamais dans le code partagé (trop rare à ce jour, 2 documents sur
  34, pour justifier le risque d'une généralisation).
