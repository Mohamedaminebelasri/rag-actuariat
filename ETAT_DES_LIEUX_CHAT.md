# État des lieux — Chat AI (agent IA sur les SFCR)

## 0.3 Inventaire des PDF

Rédigé le 2026-10-16, en lecture seule (aucun fichier, code ou base modifié).

### Avertissement sur le périmètre vérifié

- L'inventaire a été fait dans un **conteneur cloud, sur le clone Git du
  dépôt** (`/home/user/rag-actuariat`, branche `claude/loving-ride-kmdtls`),
  **pas sur `C:\Users\PC\Documents\rag-actuariat\`**, qui n'est pas accessible
  depuis cet environnement.
- Les 39 PDF trouvés sont tous suivis par Git (`git ls-files -z | tr '\0' '\n' | grep -i '\.pdf$' | wc -l` → 39).
  Un PDF présent sur le disque local mais **non suivi** (par exemple
  `test_markdrop/input/*.pdf`, exclu par `.gitignore`) n'apparaît pas ici.
- Les sorties Docling sont **toutes exclues de Git** (`.gitignore` :
  `test_markdrop/output_structure_brute/`, `output_structure_brute_2024/`,
  `output_cnp/`, `output_cnp_full/`, `output_macsf/`). Leur présence est donc
  déduite du code et de DECISIONS.md. **Elle n'a pas été vérifiée sur le disque.**

### Méthode (commandes réellement exécutées)

| Étape | Commande / source |
|---|---|
| Recherche des PDF | `find . -prune (node_modules, .venv, .git) -type f -iname '*.pdf'` |
| Taille et nombre de pages | `os.path.getsize` + `len(pypdf.PdfReader(p).pages)` (pypdf 6.17.0 ; `fitz` non installé ici) |
| Sociétés | `kpis.db` ouvert en lecture seule (`mode=ro`), table `companies` (41 lignes) |
| Champ « fichier source » | `companies` n'a **aucun** champ de fichier source. `kpis.source_pdf` est NULL partout, sauf 9 lignes Generali IARD et 8 lignes Generali Vie (document secondaire). `kpi_composants.composant_source_pdf` n'est rempli que pour Generali (2 + 2 lignes). |
| Correspondance société → PDF | `frontend/src/lib/pdf-par-societe.ts` (`PDF_PAR_SOCIETE`, 41 entrées, une par société de `kpis.db`) |
| Entités des PDF de groupe | `aema_entites.py` (`ENTITES_BORNES`, 13 entités) et `ag2r_entites.py` (`ENTITES_BORNES`, 9 entités) |
| Sorties Docling | `find` sur `*docling*`, `structure_*.json`, `chunks_*.json`, `corpus*.json` ; `grep '"schema_name": "DoclingDocument"'` sur tous les `.json` → **aucun résultat dans le clone** |

### Emplacement

Les 39 PDF se trouvent dans un seul dossier : **`data/`**. Aucun PDF ailleurs
dans le dépôt cloné (hors `node_modules` et `.venv`).

### Tableau

Légende de la colonne Docling :
- **oui / partiel** = sortie attendue d'après le code ou DECISIONS.md, absente du clone ;
- **non trouvé** = aucune trace dans le clone, le code ou DECISIONS.md.

| PDF (`data/`) | Société(s) `kpis.db` | Pages | Taille (Mo) | Groupe multi-entités | Sortie Docling |
|---|---|---:|---:|---|---|
| `Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf` | 13 : Aema Groupe, MACIF SAM, Macif Vie, Macif Sante Prevoyance, Themis, Macifilia, Aesio Mutuelle, MNPAF, MMJ, Nuoma, Abeille Vie, Abeille Epargne Retraite, Abeille IARD Sante | 621 | 20,78 | **oui** (blocs entités p. 439-621) | non trouvé |
| `AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf` | 9 : SGAM AG2R LA MONDIALE, AG2R Prevoyance, Arpege Prevoyance, Prima, AG.Mut, VIASANTE Mutuelle, La Mondiale, La Mondiale Europartner, La Mondiale Partenaire | 288 | 1,77 | **oui** (blocs entités p. 122-286) | non trouvé |
| `SFCR_2025_Groupe-Groupama.pdf` | Groupama | 89 | 4,64 | non | **oui**, complète (`test_markdrop/output_structure_brute/`, code + Déc. 048) |
| `SFCR_2024_Groupe-Groupama.pdf` | aucune (année 2024 ; `kpis.db` ne contient que 2025) | 86 | 1,46 | non | **oui**, complète (`test_markdrop/output_structure_brute_2024/`, `convertir_2024_une_fois.py` + Déc. 045) |
| `sfcr_cnp_assurances_2025.pdf` | CNP Assurances | 108 | 2,63 | non | **partiel** : 2 conversions Docling faites, chaîne bloquée ensuite (`test_markdrop/output_cnp_full/`, Déc. 092) |
| `RAPPORT_SFCR_MACSF_prevoyance_2025.pdf` | MACSF prévoyance | 64 | 1,68 | non | **partiel** : pages QRT seulement, ancien pipeline (`test_markdrop/output_macsf/corpus_final.json`, Déc. 085 et 091 ; contredit par Déc. 090, voir anomalies) |
| `Groupe-Credit-Agricole-Assurances-–-SFCR-2025.pdf` | Crédit Agricole Assurances | 121 | 3,74 | non (1 seule société en base ; contenu par filiale non vérifié) | non trouvé |
| `sfcr_covea_2025.pdf` | Covéa | 99 | 2,45 | non (1 seule société en base ; contenu par filiale non vérifié) | non trouvé |
| `PREDICA-–-SFCR-2025.pdf` | Predica | 73 | 1,87 | non | non trouvé |
| `MGEN_SFCR_2025.pdf` | MGEN | 56 | 1,16 | non | non trouvé |
| `rapport-solvabilite-maif-2025.pdf` | MAIF | 126 | 4,92 | non | non trouvé |
| `Rapport_de_solvabilite_2025_Sogécap_01.pdf` | Sogécap | 42 | 1,98 | non | non trouvé |
| `Rapport_de_solvabilité_Allianz_Vie_2025.pdf` | Allianz Vie | 93 | 2,57 | non | non trouvé |
| `SL_AP_Narrative_Report_PdfProof.pdf` | SwissLife Assurance et Patrimoine | 109 | 1,20 | non | non trouvé |
| `bpce-vie-rapport-sfcr-2025.pdf` | BPCE Vie | 88 | 1,48 | non | non trouvé |
| `bpcea-iard-sfcr-2025.pdf` | BPCE Assurances IARD | 81 | 1,75 | non | non trouvé |
| `afv-annexes-2025-etats-quantitatifs.pdf` | AXA France Vie (annexe QRT, PDF du mapping) | 11 | 0,28 | non | non trouvé |
| `AXA_France_Vie-Rapport_2025_sur_la_solvabilite_et_la_situation_financiere.pdf` | AXA France Vie (rapport narratif, document secondaire, Déc. 146 ; absent du mapping) | 107 | 1,79 | non | non trouvé |
| `Annexe-QRT-Publics-AFI-2025-ok.pdf` | AXA France IARD (annexe QRT, PDF du mapping) | 10 | 1,02 | non | non trouvé |
| `AXA_France_IARD-Rapport_2025_sur_la_solvabilite_et_la_situation_financiere.pdf` | AXA France IARD (rapport narratif, document secondaire, Déc. 146 ; absent du mapping) | 96 | 1,79 | non | non trouvé |
| `Annexe_RSSF_QRT_GVIE_2025.pdf` | Generali Vie (annexe QRT, PDF du mapping) | 11 | 1,64 | non | non trouvé |
| `RSSF_Generali_Vie_2025.pdf` | Generali Vie (rapport, document secondaire : `kpis.source_pdf` sur 8 lignes ; absent du mapping) | 91 | 2,09 | non | non trouvé |
| `Annexe_RSSF_QRT_GIARD_2025.pdf` | Generali IARD (annexe QRT, PDF du mapping) | 15 | 1,86 | non | non trouvé |
| `RSSF_Generali_Iard_2025.pdf` | Generali IARD (rapport, document secondaire : `kpis.source_pdf` sur 9 lignes ; absent du mapping) | 83 | 2,50 | non | non trouvé |
| `Cardif-Assurance-Vie-–-Annexes-2025.pdf` | Cardif Assurance Vie (annexe) | 14 | 1,09 | non | non trouvé |
| `cardif-assurances-risques-divers-–-annexes-2025.pdf` | Cardif Assurances Risques Divers (annexe) | 14 | 1,02 | non | non trouvé |
| `Pacifica-–-SFCR-2025.pdf` | **aucune** | 69 | 1,80 | non | non trouvé |
| `Rapport_de_solvabilité_Allianz_IARD_2025.pdf` | **aucune** | 106 | 2,22 | non | non trouvé |
| `en-Allianz-Group-SFCR-2024.pdf` | **aucune** (groupe Allianz, 2024 d'après le nom) | 240 | 6,21 | non trouvé (non examiné) | non trouvé |
| `are-annexes-2025-etats-quantitatifs.pdf` | **aucune** (« ARE » ; nom complet de l'entité : non trouvé) | 4 | 0,20 | non | non trouvé |
| `_entite_SGAM_AG2R_LA_MONDIALE.pdf` | SGAM AG2R LA MONDIALE (extrait p. 122-134 du PDF AG2R) | 13 | 0,08 | non (extrait d'une entité) | non trouvé |
| `_entite_AG2R_Prevoyance.pdf` | AG2R Prevoyance (extrait p. 139-157) | 19 | 0,11 | non (extrait) | non trouvé |
| `_entite_Arpege_Prevoyance.pdf` | Arpege Prevoyance (extrait p. 159-177) | 19 | 0,11 | non (extrait) | non trouvé |
| `_entite_Prima.pdf` | Prima (extrait p. 179-196) | 18 | 0,10 | non (extrait) | non trouvé |
| `_entite_AG_Mut.pdf` | AG.Mut (extrait p. 198-215) | 18 | 0,10 | non (extrait) | non trouvé |
| `_entite_VIASANTE_Mutuelle.pdf` | VIASANTE Mutuelle (extrait p. 217-235) | 19 | 0,11 | non (extrait) | non trouvé |
| `_entite_La_Mondiale.pdf` | La Mondiale (extrait p. 237-254) | 18 | 0,11 | non (extrait) | non trouvé |
| `_entite_La_Mondiale_Europartner.pdf` | La Mondiale Europartner (extrait p. 256-271) | 16 | 0,08 | non (extrait) | non trouvé |
| `_entite_La_Mondiale_Partenaire.pdf` | La Mondiale Partenaire (extrait p. 273-286) | 14 | 0,08 | non (extrait) | non trouvé |

Pour chaque fichier `_entite_*.pdf`, le nombre de pages est égal à la largeur
des bornes de `ag2r_entites.py::ENTITES_BORNES` (par exemple 122-134 = 13 pages).
Ce sont donc des extraits du PDF AG2R de groupe, produits par
`test_markdrop/ingest.py::extraire_entite()` (préfixe `_entite_`).

### Correspondance avec `kpis.db`

- **Sociétés de `kpis.db` sans PDF trouvé : aucune.** Les 41 sociétés ont une
  entrée dans `PDF_PAR_SOCIETE`, et les 21 fichiers distincts qu'elle
  référence existent tous dans `data/`.
- **PDF qui ne correspondent à aucune société de `kpis.db` (5)** :
  - `Pacifica-–-SFCR-2025.pdf` ;
  - `Rapport_de_solvabilité_Allianz_IARD_2025.pdf` ;
  - `en-Allianz-Group-SFCR-2024.pdf` ;
  - `are-annexes-2025-etats-quantitatifs.pdf` ;
  - `SFCR_2024_Groupe-Groupama.pdf` (même société que Groupama, mais année 2024
    absente de `kpis.db` ; utilisé par le RAG Qdrant via `ingest_qdrant_2024.py`).
- **PDF rattachés à une société mais absents du mapping front (13)** :
  - 4 documents secondaires : `AXA_France_Vie-Rapport…`, `AXA_France_IARD-Rapport…`,
    `RSSF_Generali_Vie_2025.pdf`, `RSSF_Generali_Iard_2025.pdf` ;
  - 9 extraits `_entite_*.pdf` du PDF AG2R.
- **PDF de groupe couvrant plusieurs sociétés de `kpis.db` (2)** :
  - **Aéma** (`Aema-Groupe_…_2025.pdf`, 621 pages) : 13 entités (liste dans le tableau).
  - **AG2R La Mondiale** (`AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf`, 288 pages) :
    9 entités (liste dans le tableau).
  - Groupama, Covéa, Crédit Agricole Assurances et Allianz Group sont aussi des
    rapports de groupe, mais chacun ne correspond qu'à une société au plus dans
    `kpis.db`. Leur couverture par filiale n'a pas été vérifiée.

### Totaux

| Indicateur | Valeur |
|---|---|
| Nombre de PDF | **39**, dont 30 documents « source » et 9 extraits `_entite_*` |
| Nombre total de pages | **3 169** (dont 154 pages d'extraits `_entite_*`, en double avec le PDF AG2R) |
| Volume total | 82,4 Mo |
| PDF distincts utilisés par les 41 sociétés (mapping front) | 21 PDF, 2 133 pages |
| Déjà traités par Docling (d'après code et DECISIONS.md, non vérifié sur disque) | **2 complets** (Groupama 2025 et 2024), **1 conversion faite mais chaîne bloquée** (CNP 2025), **1 partiel QRT seulement** (MACSF) |

### Estimation du temps Docling restant

Le forfait de **≈ 31 min par document** vient du cas CNP (Déc. 092) : deux
conversions Docling du même PDF de 108 pages, 948,9 s + 938,5 s ≈ 31,5 min.
Comme ce temps dépend du nombre de pages, une variante **au prorata**
(31 min / 108 pages ≈ 0,29 min/page) est aussi donnée, à titre indicatif.

Documents considérés comme déjà convertis : Groupama 2025, Groupama 2024 et CNP 2025
(Déc. 092 : la reprise ne nécessite pas de reconvertir). MACSF est compté comme
restant, car seules ses pages QRT ont été traitées.

| Périmètre | Documents | Pages | Forfait 31 min/doc | Au prorata des pages |
|---|---:|---:|---:|---:|
| **A. Sociétés de `kpis.db`** (21 PDF du mapping − Groupama 2025 − CNP) | 19 | 1 936 | 589 min ≈ **9 h 49** | ≈ 556 min ≈ 9 h 16 |
| B. Tous les PDF sauf les extraits `_entite_*` | 27 | 2 732 | 837 min ≈ 13 h 57 | ≈ 784 min ≈ 13 h 04 |
| C. Tous les PDF de `data/` | 36 | 2 886 | 1 116 min ≈ 18 h 36 | ≈ 828 min ≈ 13 h 48 |

Au prorata, le PDF Aéma (621 pages) représente à lui seul ≈ 178 min, et le
PDF AG2R (288 pages) ≈ 83 min. Le forfait par document les sous-estime donc
fortement, et il surestime les petites annexes de 4 à 15 pages.

### Anomalies

1. **Inventaire fait sur le clone cloud, pas sur le disque local**
   (`C:\Users\PC\...` inaccessible). Les PDF non suivis par Git et toutes les
   sorties Docling (exclues de Git) n'ont pas pu être vérifiés.
2. **Aucune sortie Docling dans le clone.** Les statuts « oui / partiel » du
   tableau reposent uniquement sur le code et DECISIONS.md.
3. **`kpis.db` ne stocke pas le fichier source par société.** `companies` n'a
   pas de champ de ce type. `kpis.source_pdf` n'est rempli que pour Generali
   (17 lignes sur 1 049). La seule correspondance complète est dans le front
   (`frontend/src/lib/pdf-par-societe.ts`).
4. **9 fichiers `_entite_*.pdf` (AG2R) présents et suivis par Git**, ajoutés par
   le commit `07c85c9` du 2026-10-15 (« feat(export): champ sourceLisible… »,
   sans rapport avec ces fichiers). Pourtant, la Déc. 089 indique que les
   `_entite_*.pdf` temporaires ont été « supprimés de `data/` après usage ».
   Leur contenu est un doublon des pages 122-286 du PDF AG2R : à ne pas ingérer
   en plus dans le chat, sous peine de doublons.
5. **5 PDF sans société dans `kpis.db`** : Pacifica 2025, Allianz IARD 2025,
   Allianz Group 2024, ARE (annexes à nomenclature nationale, « hors périmètre »,
   Déc. 070), Groupama 2024.
6. **6 sociétés ne sont reliées qu'à une annexe QRT de 10 à 15 pages**
   (AXA France Vie et IARD, Generali Vie et IARD, Cardif Assurance Vie, Cardif
   Assurances Risques Divers). Ces annexes contiennent peu de texte narratif
   pour un chat. Un rapport narratif existe dans `data/` pour AXA et Generali
   (documents secondaires, hors mapping) ; pour les 2 entités Cardif : **non trouvé**.
7. **Contradiction dans DECISIONS.md sur les `corpus_final.json`.** La Déc. 085
   (l. 5433) dit qu'ils existent pour « Groupama/CNP/MACSF » ; la Déc. 090
   (l. 5817) dit qu'un tel fichier « n'existe QUE pour Groupama ». Non tranchable
   sans accès au disque local.
8. **Fichiers documentés mais absents.** ARCHITECTURE.md (l. 115) cite
   `data/solva2.pdf` et `data/ifrs17.pdf`, introuvables dans `data/`
   (`ls` → « No such file or directory »).
9. **Nom complet de l'entité « ARE » : non trouvé** dans les fichiers lus.
10. **`en-Allianz-Group-SFCR-2024.pdf`** : langue et couverture par entité non
    vérifiées. Le préfixe « en- » et l'année 2024 viennent seulement du nom du fichier.

### P1 — résolu (16/10)

La correspondance société → PDF est maintenant dans `kpis.db`, table
**`documents_sfcr`**. Elle est créée et remplie par
`creer_table_documents_sfcr.py`, à partir de `pdf-par-societe.ts` lu tel
quel (le front n'est pas modifié). Le script est idempotent : il réécrit les
lignes de l'année à chaque exécution. Avant l'écriture, `kpis.db` a été
sauvegardée dans `archive/kpis_avant_documents_sfcr_20261016_212635.db`
(SHA-256 `bb416d3badcb1f766c3a966e34a72760903603f60cca91e9484d5e27cda8472e`).

| Colonne | Contenu |
|---|---|
| `societe_id` | `companies.id` (clé étrangère) |
| `pdf_path` | chemin relatif depuis la racine, par exemple `data/SFCR_2025_Groupe-Groupama.pdf` |
| `type_document` | `annexe_qrt` (6 sociétés) ou `rapport_complet` (35) ; contrainte `CHECK` |
| `nb_pages` | nombre de pages lu dans le fichier (PyMuPDF : un PDF chiffré en AES n'est pas lisible par pypdf sans `cryptography`) |
| `rapport_groupe` | 1 pour les rapports communs Aéma et AG2R (22 sociétés), sinon 0 |
| `annee` | 2025 |

La clé primaire est (`societe_id`, `annee`) : une société a un seul PDF par
défaut par année. Les PDF secondaires utilisés pour un KPI précis (AXA,
Generali) restent dans `kpis.source_pdf` (Décision 145) et ne sont pas dans
cette table. Les extraits `_entite_*.pdf` sont refusés par le script.

**Contrôles** (base ouverte en `mode=ro`) :

| Contrôle | Résultat |
|---|---|
| 41 sociétés, aucune en double | ✅ 41 lignes, 41 sociétés distinctes, 0 doublon, 0 société de `companies` absente, 0 `_entite_` |
| Chaque `pdf_path` existe sur le disque | ✅ 41/41 (21 PDF distincts) |
| Même correspondance que `pdf-par-societe.ts` | ✅ 41 entrées de chaque côté, 0 différence |
| `type_document` = inventaire 0.3 | ✅ les 6 `annexe_qrt` sont exactement AXA France Vie, AXA France IARD, Generali Vie, Generali IARD, Cardif Assurance Vie, Cardif Assurances Risques Divers |
| `rapport_groupe` = inventaire 0.3 | ✅ 22 lignes à 1 = les 13 entités Aéma + les 9 AG2R, chacune sur le PDF de son groupe |
| `nb_pages` = inventaire 0.3 | ✅ échantillon identique (Aéma 621, AG2R 288, Groupama 89, AFV 11, Cardif Vie 14), total des 21 PDF 2 133 pages comme au 0.3 |
| Autres tables inchangées | ✅ seule `documents_sfcr` est ajoutée ; pour les 8 autres tables, nombre de lignes, contenu et schéma identiques à la sauvegarde (`companies` 41, `kpis` 1 049, `kpi_composants` 1 169, `kpi_formules` 188, `validation_checks` 2 171, `impact_mesures_lt` 41, `corrections` 0, `sqlite_sequence` 5) |

Limite : `pdf-par-societe.ts` reste la source de cette table. Si le front
change de PDF pour une société, il faut relancer
`creer_table_documents_sfcr.py`. `kpi_service.py` ne lit pas encore la
table (cela relève du titre 3, outils de l'agent).

### P2 — vérification (16/10)

Vérification en lecture seule sur le poste local : rien n'a été supprimé ni
modifié. **L'anomalie 4 ci-dessus est inexacte sur un point** : le commit
`07c85c9` n'a pas ajouté les extraits.

**1. Commit `07c85c9`.** Auteur Mohamed Amine Belasri, 2026-10-15 23:17
(UTC). Message : « feat(export): champ sourceLisible pour les cartes à
avertissement (Décision 158, bonus) », avec la mention Claude Opus 5.5
comme co-auteur. Il ne modifie qu'**un seul fichier**,
`export_kpis_for_frontend.py` (+7 lignes), et **aucun PDF**. Cause probable
de l'erreur du 0.3 (à vérifier) : un clone cloud superficiel, où le
premier commit visible semble ajouter tous les fichiers.

**2. Chronologie** (`git log --all -- 'data/_entite_*'`) :
- 25/09 (`a2c3a42`, Décision 089) : 20 extraits temporaires (Aéma et AG2R)
  sont supprimés **du disque** (`data/`). Ils n'avaient jamais été dans Git :
  aucun commit antérieur ne les contient.
- Entre le 25/09 et le 27/09 : les 9 extraits AG2R sont recréés dans `data/`.
  En effet, `ag2r_entites.py` (l. 269) et `peupler_composants_ag2r.py`
  (l. 51) appellent `extraire_entite()` (`test_markdrop/ingest.py`, l. 132-162),
  qui écrit `_entite_<nom>.pdf` à côté du PDF source. Aucun de ces scripts ne
  les supprime ensuite.
- 27/09 (`049c80c`, « Ajoute les PDF source SFCR/RSSF des 34 sociétés… ») :
  les 9 extraits entrent dans Git **pour la seule et unique fois**, avec 28
  autres PDF de `data/` (37 fichiers dans ce commit).
- Depuis : aucun commit ne les supprime ni ne les modifie. Le contenu sur le
  disque est identique à celui de Git (`git status` propre). La date des
  fichiers (05/10) n'est pas concluante, car Git la réécrit à chaque checkout.

**3. Références** (fichiers suivis par Git, aucun fichier Python non suivi
concerné) :

| Où | Référence | Rôle |
|---|---|---|
| `test_markdrop/ingest.py:142, 159` | `_entite_{slug}.pdf` | **Crée** les extraits (`extraire_entite()`) |
| `ag2r_entites.py:269` | `extraire_entite(SOURCE_PDF, …)` | Recrée l'extrait, puis le lit pour extraire les KPIs de l'entité |
| `peupler_composants_ag2r.py:51` | `extraire_entite(ag.SOURCE_PDF, …)` | Idem pour les composants ; pages relatives converties en pages absolues (Décision 133) |
| `creer_table_documents_sfcr.py:17, 86-87` | `_entite_` | **Refuse** les extraits (P1) |
| `batch_diagnostic.py:456` | `DATA_DIR.glob("*.pdf")` | Pas de référence explicite, mais parcourt **tous** les PDF de `data/` : `EXCLUSIONS` ne contient que `ifrs17.pdf` et `solva2.pdf`, donc les 9 extraits y sont comptés comme 9 documents à part entière (la « pollution » décrite par la Décision 089) |
| Front (`frontend/`, hors `node_modules` et `.next`), y compris `pdf-par-societe.ts` et `frontend/src/data/*.json` | aucune | — |
| Ingestion Qdrant (`test_markdrop/ingest_qdrant*.py`, `run_pipeline.py`) | aucune | — |
| `kpis.db` : `kpis.source_pdf`, `source_chapter`, `source_chapter_technique`, `kpi_composants.composant_source_pdf`, `composant_detail`, `validation_checks.details`, `documents_sfcr.pdf_path` | aucune (0 ligne) | `kpis.source_pdf` ne contient que `RSSF_Generali_Iard_2025.pdf` (9) et `RSSF_Generali_Vie_2025.pdf` (8) |

Les mentions dans les fichiers `.md` (DECISIONS.md, ce rapport) sont de la
documentation et n'ont pas été comptées.

**4. Contenu.** Comparaison du texte page par page (PyMuPDF, espaces
normalisés, empreinte SHA-256 par page). Les **9 extraits sont des copies
exactes** des pages du rapport complet `AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf`
données par `ag2r_entites.py::ENTITES_BORNES` : 154 pages sur 154 sont
identiques, et aucune page n'est sans texte. Deux exemples :
- `_entite_AG2R_Prevoyance.pdf` (19 p.) = **pages 139 à 157** du rapport. Il
  commence par « S.02.01.02 - Bilan » et finit par « Calcul du montant
  notionnel du MCR en non-vie et en vie ».
- `_entite_La_Mondiale_Partenaire.pdf` (14 p.) = **pages 273 à 286**. Il
  commence par « S.02.01.02 - Bilan » et finit sur le tableau des
  « Meilleure estimation et PT calculées comme un tout ».

Ce sont uniquement les blocs QRT de chaque entité, sans texte narratif.

**5. Décision 089** (DECISIONS.md, l. 5740-5743) :
« Nettoyage : les 20 fichiers `_entite_*.pdf` temporaires (isolation
Aéma/AG2R, régénérables via `extraire_entite()`) supprimés de `data/` après
usage — ils polluaient le diagnostic générique en étant scannés comme des
documents à part entière. »

**6. Conclusion.**
- **Utilisés ? Non**, en tant que fichiers suivis par Git. Aucun lecteur ne
  dépend de leur présence. Les deux scripts qui les lisent
  (`ag2r_entites.py`, `peupler_composants_ag2r.py`) les **recréent juste
  avant** de les lire. Le front, l'export, Qdrant et `kpis.db` ne les
  citent pas.
- **Qu'est-ce qui casserait si on les retirait de Git ? Rien.**
  Conséquences à prévoir :
  - toute nouvelle exécution des deux scripts AG2R les recrée dans `data/`.
    Sans règle `.gitignore` (aucune ne couvre `data/_entite_*.pdf`
    aujourd'hui), ils réapparaîtraient comme fichiers non suivis et
    pourraient être recommités par un `git add data/` ;
  - tant qu'ils sont dans `data/`, `batch_diagnostic.py` les compte comme
    des documents.
- Pour le Chat AI : ne jamais les indexer (rappel du 0.3). `documents_sfcr`
  les exclut déjà.

### P2 — résolu (16/10)

- **Retrait.** Les 9 extraits sont retirés de Git et du disque (`git rm`) :
  `_entite_AG2R_Prevoyance`, `_entite_AG_Mut`, `_entite_Arpege_Prevoyance`,
  `_entite_La_Mondiale`, `_entite_La_Mondiale_Europartner`,
  `_entite_La_Mondiale_Partenaire`, `_entite_Prima`,
  `_entite_SGAM_AG2R_LA_MONDIALE`, `_entite_VIASANTE_Mutuelle` (`.pdf`).
  `data/` contient désormais **30 PDF** (39 − 9). Aucun autre PDF n'est touché.
- **Retour empêché.** Une règle `data/_entite_*.pdf` est ajoutée à
  `.gitignore`, avec un commentaire qui renvoie à la Décision 089 ; elle est
  testée avec `git check-ignore`. `ag2r_entites.py` et
  `peupler_composants_ag2r.py` continueront de recréer ces fichiers quand on
  les lance, mais Git les ignorera.
- **`batch_diagnostic.py`.** Deux lignes ajoutées dans `lister_pdfs()` : tout
  fichier dont le nom contient `_entite_` est ignoré. Le diagnostic complet a
  été relancé sans erreur : 30 PDF, 42 s, aucun `_entite_` dans la sortie. Le
  rapport du 26/09 en comptait 35, dont les 9 extraits. Le filtre a aussi été
  testé sur un dossier temporaire contenant un faux `_entite_Test.pdf`, qui
  est bien écarté. La relance a réécrit `batch_diagnostic_report.json`
  (fichier local non suivi) ; l'ancien est copié dans le scratchpad.
- **DECISIONS.md.** Une note « Suivi du 16/10/2026 » est ajoutée à la fin de
  la Décision 089.
- **Contrôles.**
  - `git ls-files | grep _entite_` : rien ;
  - `data/AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf` est présent et inchangé ;
  - `documents_sfcr` est intacte (41 lignes, 0 `_entite_`, 41 chemins
    existants), et `kpis.db` n'a pas changé.

### P3 — résolu (16/10)

**Sociétés concernées** (`type_document = annexe_qrt`) :

| `societe_id` | Société | Annexe actuelle |
|---:|---|---|
| 116 | AXA France Vie | `data/afv-annexes-2025-etats-quantitatifs.pdf` (11 p.) |
| 117 | AXA France IARD | `data/Annexe-QRT-Publics-AFI-2025-ok.pdf` (10 p.) |
| 103 | Cardif Assurance Vie | `data/Cardif-Assurance-Vie-–-Annexes-2025.pdf` (14 p.) |
| 104 | Cardif Assurances Risques Divers | `data/cardif-assurances-risques-divers-–-annexes-2025.pdf` (14 p.) |
| 121 | Generali IARD | `data/Annexe_RSSF_QRT_GIARD_2025.pdf` (15 p.) |
| 122 | Generali Vie | `data/Annexe_RSSF_QRT_GVIE_2025.pdf` (11 p.) |

**Recherche par le contenu** (PyMuPDF, texte natif) dans les 9 PDF de
`data/` absents de `documents_sfcr`. Trois critères : nom de l'entité,
exercice 2025, chapitres A à E.

| Société | Rapport complet | Vérification |
|---|---|---|
| AXA France Vie | ✅ `data/AXA_France_Vie-Rapport_2025_sur_la_solvabilite_et_la_situation_financiere.pdf` (107 p.) | « AXA France Vie » 145 fois ; « pour l'exercice 2025 », « 31 décembre 2025 » 20 fois ; chapitres A à E |
| AXA France IARD | ✅ `data/AXA_France_IARD-Rapport_2025_sur_la_solvabilite_et_la_situation_financiere.pdf` (96 p.) | « AXA France IARD » 110 fois ; « 31 décembre 2025 » 24 fois ; chapitres A (« Activité et résultat », p. 12) à E |
| Generali Vie | ✅ `data/RSSF_Generali_Vie_2025.pdf` (91 p.) | « Generali Vie » 119 fois ; « Exercice 2025 » ; chapitres A à E |
| Generali IARD | ✅ `data/RSSF_Generali_Iard_2025.pdf` (83 p.) | « Generali Iard » 103 fois ; « Exercice 2025 » ; chapitres A à E |
| Cardif Assurance Vie | ❌ absent | Aucun PDF de `data/` ne cite « Cardif » sur ses 5 premières pages, hors les deux annexes |
| Cardif Assurances Risques Divers | ❌ absent | Idem |

Les 4 rapports trouvés sont ceux déjà utilisés comme documents secondaires
(Décisions 145 et 146).

**Structure.** La clé primaire est passée de (`societe_id`, `annee`) à
(`societe_id`, `annee`, `type_document`), à la demande de l'utilisateur.
SQLite ne sait pas modifier une clé en place : la table est recopiée, puis
remplacée, dans une même transaction. Les 41 lignes d'origine sont
conservées à l'identique. Sauvegarde préalable :
`archive/kpis_avant_p3_rapports_complets_20261016_214030.db` (SHA-256
`983e9119c564634b9279607794eacec6c8a3ea1948b25e859a65993f525406cf`).

**Lignes ajoutées.** Une ligne `rapport_complet` (`rapport_groupe = 0`) est
ajoutée pour les 4 sociétés, et leur ligne `annexe_qrt` est gardée.
`creer_table_documents_sfcr.py` les recrée grâce au dictionnaire
`RAPPORTS_COMPLETS_SUPPLEMENTAIRES`, et fait la migration de clé si
nécessaire. Le script a été relancé une seconde fois : le contenu est
identique (même empreinte, 45 lignes, aucune nouvelle migration).

**Contrôles.**
- `documents_sfcr` : 41 → **45 lignes**, 41 sociétés distinctes, dont 4 avec
  2 lignes. Les 41 lignes d'origine sont identiques, 4 sont ajoutées et
  aucune n'est supprimée.
- Les 45 `pdf_path` existent, et aucun n'est un `_entite_`.
- Les 8 autres tables sont identiques à la sauvegarde (nombre de lignes,
  contenu et schéma).

**Cardif : rapports complets téléchargés (suite du 16/10).** Les deux
rapports manquants (« ❌ absent » dans le tableau ci-dessus) ont été trouvés
sur le site officiel de BNP Paribas Cardif. Page source :
`https://www.bnpparibascardif.com/investisseurs/informations-financieres-2/`,
rubrique « Rapports de solvabilité ». Les annexes listées sur cette même
page portent les noms des fichiers déjà présents dans `data/`. Les deux
fichiers ont été téléchargés avec l'accord de l'utilisateur, vérifiés, puis
copiés dans `data/` :

| Fichier (`data/`) | Adresse d'origine | Taille | Pages |
|---|---|---:|---:|
| `Cardif_Assurance_Vie_SFCR_2025.pdf` | `…/wp-content/uploads/sites/28/2026/04/Cardif-Assurance-Vie-–-SFCR-2025.pdf` | 3 165 177 octets | 57 |
| `Cardif_Assurances_Risques_Divers_SFCR_2025.pdf` | `…/wp-content/uploads/sites/28/2026/04/Cardif-Assurances-Risques-Divers-–-SFCR-2025.pdf` | 2 356 681 octets | 54 |

Vérifications sur le texte (PyMuPDF), pour les deux fichiers :
- **Entité** : la page de titre porte « RAPPORT SUR LA SOLVABILITE ET LA
  SITUATION FINANCIERE SFCR Cardif Assurance Vie » (ou « Cardif Assurances
  Risques Divers »). Le nom de l'entité revient 170 et 141 fois, et l'autre
  entité seulement 2 fois. Ce n'est pas le rapport du groupe BNP Paribas
  Cardif.
- **Exercice** : « 31 décembre 2025 » sur la page de titre (37 et 30
  occurrences).
- **Rapport complet** : chapitres A à E au sommaire et dans le corps (par
  exemple D p. 46, E p. 54 pour Cardif Assurance Vie), et aucune page QRT
  (aucun code S.xx.xx.xx). Ce n'est pas l'annexe.

**Lignes ajoutées.** `RAPPORTS_COMPLETS_SUPPLEMENTAIRES` contient maintenant
6 sociétés. Le script a été relancé après une sauvegarde
(`archive/kpis_avant_p3_cardif_20261016_221116.db`, SHA-256
`8fae407ae7c86085657fe07a71b0f505152f413af65636a21a6ccff455585501`).
- `documents_sfcr` : 45 → **47 lignes** (27 PDF distincts). Les 45 lignes
  précédentes sont identiques, 2 sont ajoutées (Cardif Assurance Vie 57 p.,
  Cardif Assurances Risques Divers 54 p.) et aucune n'est supprimée.
- Les 47 `pdf_path` existent, et les 8 autres tables sont identiques à la
  sauvegarde.
- **Les 41 sociétés ont désormais un rapport complet** : aucune ne reste avec
  une annexe seule.

### P4 — résolu (16/10)

**Vérification.** `data/` contient 32 PDF et `documents_sfcr` en cite 27.
Les 27 chemins existent tous. **Exactement 5 PDF sont absents** de la table :
ni les deux Cardif ajoutés au P3, ni les autres nouveaux fichiers n'y
figurent. Aucune de ces entités n'est dans `companies`. Les seules sociétés
voisines en base sont Allianz Vie, AXA France Vie et AXA France IARD, et
Groupama pour l'exercice 2025.

| Fichier (`data/`) | Entité (page de titre) | Exercice | Type | Pages | Raison |
|---|---|---|---|---:|---|
| `SFCR_2024_Groupe-Groupama.pdf` | Groupe Groupama (Groupama Assurances Mutuelles) | 2024 (« au 31 décembre 2024 ») | rapport complet (A à E) | 86 | année 2024 |
| `en-Allianz-Group-SFCR-2024.pdf` | Allianz Group (en anglais) | 2024 (« 31 December 2024 ») | rapport complet (A à E) | 240 | année 2024, et entité de groupe absente de `kpis.db` |
| `Pacifica-–-SFCR-2025.pdf` | Pacifica | 2025 (« 31/12/2025 ») | rapport complet (A à E, annexes QRT incluses) | 69 | entité absente de `kpis.db` |
| `Rapport_de_solvabilité_Allianz_IARD_2025.pdf` | Allianz Iard | 2025 (« 31 décembre 2025 ») | rapport complet (A à E, annexes QRT incluses) | 106 | entité absente de `kpis.db` |
| `are-annexes-2025-etats-quantitatifs.pdf` | AXA Retraite Entreprise | 2025 (d'après le titre ; aucune date 31/12 dans le texte) | annexe QRT seule, nomenclature nationale RC (Décision 070) | 4 | entité absente de `kpis.db` |

**Règle.** La **Décision 162** (« Périmètre d'indexation du Chat AI ») fixe
que l'ingestion Qdrant du Chat AI n'indexe que les PDF de `documents_sfcr` ;
ces 5 fichiers ne sont jamais indexés. Ils restent dans `data/` : les
rapports 2024 servent aux futures questions N-1, et l'ajout des 3 autres
entités à `kpis.db` est reporté (à discuter avec le fondateur). Rien n'a été
modifié : ni `kpis.db`, ni le code, ni les PDF.

**Écart à traiter au 0.2.** D'après la Décision 031 et `ingest_qdrant_2024.py`,
les collections Qdrant actuelles contiennent déjà des points Groupama 2024,
ce qui n'est pas conforme à la Décision 162. Je ne l'ai pas encore vérifié
sur le serveur.

**Découverte au passage (anomalie 9).** `are-annexes-2025-etats-quantitatifs.pdf`
est l'annexe QRT 2025 d'**AXA Retraite Entreprise** (première page :
« AXA Retraite Entreprise — Rapport sur la Solvabilité et la Situation
Financière 2025 — Annexe 2 : États annuels quantitatifs (QRT) »). Cette
société n'est pas dans `kpis.db`.

---

## 0.4 kpis.db et kpi_service.py

Rédigé le 2026-10-16, en lecture seule.

- `kpis.db` a été ouvert en `mode=ro`. Les appels à `kpi_service.py` ont été
  faits sur une **copie** de la base dans le scratchpad, parce que
  `KpiService._connexion()` ouvre la base en lecture-écriture
  (`sqlite3.connect(self.db_path)`, `kpi_service.py:31`).
- L'empreinte SHA-256 de `kpis.db` est identique avant et après :
  `438e0475…0bbc9b`.
- Scripts utilisés (scratchpad, hors dépôt) : `appels_kpi_service.py`,
  `verif_pages.py`, `verif_num_imprime.py`.

### Bilan

| Point | Statut | En une phrase |
|---|---|---|
| 1. Schéma de `kpis.db` | ✅ | 7 tables utiles, 41 sociétés, 1 049 KPIs, année 2025 uniquement |
| 2a. `get_kpis` | ✅ | Marche, mais renvoie `{}` aussi bien pour une société inconnue que pour une année absente |
| 2b. `get_kpi` | ⚠️ | Marche, mais **lève une exception** sur une société inconnue (contrat différent des autres fonctions) |
| 2c. `compare_kpis` | ⚠️ | Marche sur les 41 sociétés, sans filtre ni information de comparabilité |
| 2d. `get_corpus_stats` | ⚠️ | Marche, mais mélange groupes et entités solo, modèles internes signalés et zéros |
| 2e. `get_validation_report` | ⚠️ | Marche, mais compte les contrôles « NON CONTRÔLABLE » comme des échecs |
| 2f. Champs renvoyés | ⚠️ | Valeur, unité et page présentes ; fiabilité éclatée en 3 champs ; nom de société, fichier PDF, libellé, composants absents |
| 3. Cas limites | ⚠️ | Trois comportements différents selon la fonction (exception, `None`, `{}`) |
| 4. Page physique ou imprimée | ⚠️ | `source_page` est la **page physique**. La « correction −1 dans le front » : **non trouvée** |
| 5. 6 KPIs officiels (15/10) | ⚠️ | Valeurs accessibles ; composants et formules **non accessibles** |

### 1. Schéma de `kpis.db`

Source : `sqlite_master` et `pragma table_info`, base en lecture seule.

| Table | Lignes | Colonnes |
|---|---:|---|
| `companies` | 41 | id INTEGER, name TEXT, type TEXT, country TEXT, type_document TEXT, scr_method TEXT, type_activite TEXT, unite_source TEXT, forme_juridique TEXT, famille_juridique TEXT, forme_juridique_source TEXT, groupe_parent TEXT, groupe_consolide_panel TEXT |
| `kpis` | 1 049 | id INTEGER, company_id INTEGER, year INTEGER, category TEXT, kpi_name TEXT, value REAL, unit TEXT, source_page INTEGER, source_chapter TEXT, validated BOOLEAN, raw_value, raw_unit, source_pdf TEXT, avertissement INTEGER, note_avertissement TEXT |
| `kpi_composants` | 1 169 | id INTEGER, company_id INTEGER, year INTEGER, kpi_name TEXT, composant_index INTEGER, composant_label TEXT, composant_code_qrt TEXT, composant_valeur REAL, composant_unite TEXT, composant_page INTEGER, operation TEXT, kpi_code TEXT, composant_detail TEXT, composant_source_pdf TEXT, composant_valide INTEGER |
| `kpi_formules` | 188 | company_id INTEGER, year INTEGER, kpi_name TEXT, type TEXT, texte TEXT, facteur REAL, note TEXT |
| `validation_checks` | 2 171 | id INTEGER, company_id INTEGER, year INTEGER, check_name TEXT, expected_value REAL, computed_value REAL, passed BOOLEAN, details TEXT, legitime INTEGER, note_legitimite TEXT |
| `impact_mesures_lt` | 41 | company_id INTEGER, year INTEGER, utilise_va INTEGER, mesure_transitoire INTEGER, fp_avec REAL, scr_avec REAL, delta_fp_va REAL, delta_scr_va REAL, delta_fp_transitoires REAL, delta_scr_transitoires REAL, ratio_scr_sans_va_publie REAL, source_page INTEGER, source TEXT |
| `corrections` | 0 | id INTEGER, company_id INTEGER, kpi_name TEXT, year INTEGER, ancienne_valeur REAL, ancienne_unite TEXT, nouvelle_valeur TEXT, commentaire TEXT, date_correction TEXT |

`sqlite_sequence` (5 lignes) est une table interne de SQLite.

Index présents : `idx_kpis_company_year`, `idx_kpis_kpi_name`,
`idx_kpi_composants_company_kpi`.

Répartition des KPIs par catégorie (27 noms distincts au total) :

| Catégorie | KPIs distincts | Lignes |
|---|---:|---:|
| `scr` | 8 | 328 |
| `fonds_propres` | 5 | 205 |
| `indicateurs_comparables` | 6 | 188 |
| `provisions` | 3 | 123 |
| `activité` | 2 | 82 |
| `solvabilité` | 2 | 82 |
| `mcr` | 1 | 41 |

Années présentes dans `kpis` : 2025 uniquement (41 sociétés).

### 2. Les 5 fonctions de `kpi_service.py`

**Signatures.** Résultat de `inspect.signature`. Les 5 fonctions sont des
méthodes de la classe `KpiService(db_path=DB_PATH)`, **sans aucune annotation
de type** (`__annotations__` vide pour les 5).

| Fonction | Signature | Retour (d'après le code et l'appel) |
|---|---|---|
| `get_kpis` | `(self, company_name, year)` | `dict {kpi_name: ligne}`, ou `{}` si société inconnue (`kpi_service.py:174`) |
| `get_kpi` | `(self, company_name, year, kpi_name)` | `dict` (ligne `kpis` complète), ou `None` ; lève `KpiIntrouvable` si société inconnue (`:54`) |
| `compare_kpis` | `(self, kpi_name, year)` | `dict {société: ligne ou None}` pour toutes les sociétés de `companies` (`:189`) |
| `get_corpus_stats` | `(self, kpi_name, year)` | `{n, moyenne, mediane, min, max}` sur les valeurs non NULL (`:195`) |
| `get_validation_report` | `(self, company_name, year)` | `{summary: {n_checks, n_passed, n_failed, checks_echoues}, checks: [...]}` (`:216`) |

**Appels réels sur Groupama et sur une entité Aéma (MACIF SAM), année 2025.**

- `get_kpis("Groupama", 2025)` → dict de 26 KPIs.
  `get_kpis("MACIF SAM", 2025)` → dict de 26 KPIs.
  Clés de chaque ligne : `id, company_id, year, category, kpi_name, value,
  unit, source_page, source_chapter, validated, raw_value, raw_unit,
  source_pdf, avertissement, note_avertissement`.
- `get_kpi("Groupama", 2025, "ratio_scr")` →
  `{"value": 274.0, "unit": "pct", "source_page": 85, "source_chapter": "E.1", "validated": 1, "source_pdf": null, "avertissement": 0, …}`
- `get_kpi("MACIF SAM", 2025, "ratio_scr")` →
  `{"value": 319.0, "unit": "pct", "source_page": 463, "source_chapter": "Document combiné 'Aéma Groupe RAPPORT UNIQUE...' (621p), entité isolée pages 452-467 (…) — S.23.01.01.01/R0620", "validated": 1, …}`
- `compare_kpis("ratio_scr", 2025)` → 41 sociétés, 0 `None`. Extrait :
  `{"Groupama": {"value": 274.0, "source_page": 85, …}, "MACIF SAM": {"value": 319.0, "source_page": 463, …}}`
- `get_corpus_stats("ratio_scr", 2025)` →
  `{"n": 41, "moyenne": 276.94, "mediane": 227.0, "min": 128.0, "max": 953.0}`
- `get_validation_report("Groupama", 2025)` →
  `summary = {"n_checks": 59, "n_passed": 53, "n_failed": 6, "checks_echoues": ["sp_nonvie_ligne_primes_acquises_brutes_1", …, "sp_nonvie_ligne_charge_sinistres_3"]}`
- `get_validation_report("MACIF SAM", 2025)` →
  `summary = {"n_checks": 56, "n_passed": 50, "n_failed": 6, …}`, mêmes 6 contrôles.
  - Le détail de ces « échecs » est
    `"NON CONTRÔLABLE — … aucune section « Primes acquises » lisible p.80 de SFCR_2025_Groupe-Groupama.pdf (page image, sans texte)"`,
    avec `passed=0` et `legitime=0`.
  - Sur toute la base : 36 contrôles `sp_nonvie_ligne_*` sont dans ce cas,
    répartis sur 10 sociétés.

**Champs renvoyés : ce qui est là, ce qui manque.**

| Champ attendu | Statut | Où / pourquoi |
|---|---|---|
| Valeur | ✅ | `value` (REAL) ; `raw_value` / `raw_unit` = chiffre brut du PDF (par exemple 14 256 819 K€ pour le SCR de CNP) |
| Unité | ✅ | `unit` : `pct`, `pts` ou `M€` |
| Page source | ✅ | `source_page`. NULL sur 6 lignes sur 1 049. C'est une page **physique** (voir point 4) |
| Statut de fiabilité | ⚠️ | Éclaté en trois champs : `validated` (0/1), `avertissement` (0/1) et `note_avertissement`. Il n'existe pas de statut unique (« Vérifié » / « Calculé » / « Non comparable »). Les contrôles sont dans une autre fonction, et le champ `legitime` n'est pas pris en compte dans le résumé |
| Nom de la société | ❌ | Seul `company_id` est renvoyé dans la ligne |
| Fichier PDF source | ❌ | `source_pdf` est NULL partout sauf 17 lignes Generali. La correspondance société → PDF n'existe que dans `frontend/src/lib/pdf-par-societe.ts` |
| Libellé et définition du KPI | ❌ | Ils existent dans `kpi_definitions.py` et `kpi_labels_fr.py`, mais ne sont pas exposés par `KpiService` |
| Composants et formule | ❌ | Les tables `kpi_composants` (1 169 lignes) et `kpi_formules` (188 lignes) ne sont lues par **aucune** méthode de `KpiService` |
| Comparabilité | ❌ | `type`, `scr_method` et `groupe_parent` (table `companies`) ne sont pas joints aux résultats de `compare_kpis` ni de `get_corpus_stats` |
| Page imprimée | ❌ | Non stockée |

### 3. Cas limites (appels réels)

| Cas | `get_kpis` | `get_kpi` | `compare_kpis` | `get_corpus_stats` | `get_validation_report` |
|---|---|---|---|---|---|
| **KPI à valeur NULL** (`scr_souscription_sante`, 5 sociétés en base, par exemple AXA France IARD) | ligne présente avec `value: null` | ligne avec `value: null`, `source_page: null`, et l'explication dans `source_chapter` (« NULL : inclus dans un autre poste… ») | 5 lignes `value: null`, 36 non NULL, 0 `None` | NULL ignorés : `n=36`, mais `min=0.0` (des zéros sont comptés) | sans objet |
| **Société inexistante** (`"Société Inexistante"`) | `{}` | **exception** `KpiIntrouvable: Entreprise 'Société Inexistante' absente de companies` | sans objet (porte sur toutes les sociétés) | sans objet | `{"summary": {"n_checks": 0, …}, "checks": []}` |
| **KPI inexistant** (`"kpi_bidon"`) | sans objet | `None` | 41 entrées, toutes `None` | `{"n": 0, "moyenne": null, …}` | sans objet |
| **Année absente** (`Groupama`, 2024) | `{}` (identique au cas « société inexistante ») | non testé | non testé | non testé | non testé |
| **Casse ou accent différent** (`"groupama"`, `"Aéma Groupe"`) | non testé | **exception** `KpiIntrouvable`. La recherche se fait par `name =` exact ; la société s'appelle `"Aema Groupe"`, alors que `groupe_parent` vaut `"Aéma Groupe"` | non testé | non testé | non testé |

Conséquences pour un agent :
- un KPI inexistant, un KPI absent pour une société et une société absente
  d'une comparaison donnent tous la même réponse (`None`) ;
- une année absente et une société inexistante donnent toutes deux `{}` ;
- `get_kpi` est la seule fonction qui interrompt l'appelant par une exception.

### 4. Page physique ou page imprimée

| Vérification | Résultat |
|---|---|
| Convention déclarée | `corriger_source_page.py` (l. 2-4) : `source_page` = « page PHYSIQUE réelle où chaque valeur de KPI apparaît dans son PDF source » |
| Test empirique (`verif_pages.py`) | 204 lignes testées (`ratio_scr`, `ratio_mcr`, `scr_total`, `mcr`, `fonds_propres_eligibles`) dans le texte natif des pages physiques `p-1`, `p` et `p+1` (pypdf, numérotation à partir de 1). **74 trouvées sur la page physique `p`, 0 seulement sur `p-1`, 0 seulement sur `p+1`**. 117 non retrouvées (pages image comme Aéma, ou format de nombre non reconnu : non concluant), 13 non testables |
| Bornes Aéma | `aema_entites.py` : MACIF SAM couvre les pages 452-467 du PDF original ; son `source_page` vaut 463, ce qui est cohérent avec une page physique |
| Écart entre numéro imprimé et page physique (`verif_num_imprime.py`, numéro isolé en en-tête ou en pied de page) | **Varie selon le document** : 0 pour CNP, MACSF et SwissLife ; −1 pour l'annexe QRT d'AXA France IARD ; −2 pour MGEN (4 pages sur 5) ; non détecté pour les 14 autres PDF testés |
| « Décalage −1 corrigé seulement dans le front » | **Non trouvé.** `export_kpis_for_frontend.py` recopie `source_page` tel quel (`"pageSource": row["source_page"]`, l. 211). Le front l'affiche tel quel (« p. N », `kpi-ligne.tsx:46`) et le passe tel quel au lecteur pdf.js (`initialPage` → `doc.getPage(currentPage)`, numérotation à partir de 1, `pdf-page-viewer.tsx:88-117`). Aucune opération `± 1` sur la page trouvée dans `frontend/src` |

Conclusion :
- la page renvoyée par `kpi_service.py` est la **page physique** du PDF ;
- elle ouvre la bonne page dans un lecteur PDF ;
- elle peut différer du numéro imprimé sur le document (−1 ou −2 sur certains
  PDF, 0 sur d'autres) ;
- un agent qui cite « p. N » doit préciser qu'il s'agit de la page du fichier
  PDF, ou disposer du numéro imprimé, qui n'est stocké nulle part.

### 5. Les 6 KPIs officiels (Décision 158, ajoutés le 15/10)

Date confirmée par `git log` : `peupler_kpis_officiels_indicateurs.py` apparaît
dans le commit `07c85c9` du 2026-10-15.

Ils sont stockés dans `kpis` (catégorie `indicateurs_comparables`). Ils sont
donc **accessibles** par `get_kpi`, `get_kpis`, `compare_kpis` et
`get_corpus_stats` :

| KPI | Unité | Lignes (non NULL) | Groupama (valeur, page, `validated`) | MACIF SAM | `get_corpus_stats` (n, médiane) |
|---|---|---:|---|---|---|
| `ratio_scr_sans_mesures_lt` | pct | 41 (41) | 217,6 · p. 84 · 1 | 313,4 · p. 462 · 1 | 41 · 217,6 |
| `impact_va` | pts | 41 (41) | −4,2 · p. 84 · 1 | −5,2 · p. 462 · 1 | 41 · −2,4 |
| `impact_transitoires` | pts | 4 (4) | −51,9 · p. 84 · 1 | `None` (absent) | 4 · −35,4 |
| `marge_risque_sur_be` | pct | 41 (41) | 3,45 · p. 79 · 1 | 5,71 · p. 453 · 1 | 41 · 2,73 |
| `mcr_en_pct_scr` | pct | 36 (36) | `None` (absent ; Groupama est un groupe) | 25,17 · p. 463 · 1 | 36 · 37,825 |
| `sp_nonvie` | pct | 25 (25) | 63,1 · p. 80 · **0** | 73,1 · p. 455 · **0** | 25 · 70,7 |

Limites :
- leurs **composants et formules** (`kpi_composants`, `kpi_formules`) ne sont
  exposés par aucune méthode ;
- `sp_nonvie` a `validated=0` pour Groupama et MACIF SAM ;
- l'absence d'un KPI (`None`) n'est pas expliquée : `mcr_en_pct_scr` est
  calculé « solo seulement », `impact_transitoires` ne concerne que 4 sociétés
  (Décision 158).

### Ce qui manque pour en faire un outil d'agent

1. **Résolution des noms de société.** Aujourd'hui, seule une correspondance
   exacte sur `companies.name` fonctionne (`"groupama"` et `"Aéma Groupe"`
   échouent). Il faut :
   - un outil « lister les sociétés » (`liste_entreprises()` existe, mais ne
     fait pas partie des 5 fonctions) ;
   - une gestion des alias (accents, casse, nom du groupe).
2. **Catalogue des KPIs.** Noms techniques, libellé français, unité,
   définition et catégorie, à partir de `kpi_definitions.py` et
   `kpi_labels_fr.py`. Sans ce catalogue, l'agent doit deviner `kpi_name`.
3. **Contrat d'erreur unique et explicite.** Distinguer société inconnue,
   année absente, KPI inconnu, KPI non applicable et valeur NULL, au lieu
   d'un mélange d'exception, de `None` et de `{}`.
4. **Réponse auto-suffisante pour citer.** Ajouter le nom de la société, le
   **fichier PDF** (reprendre `PDF_PAR_SOCIETE` côté Python), la page physique
   clairement nommée (et la page imprimée si on la veut), le libellé et un
   statut de fiabilité unique (validé, avertissement + note).
5. **Traçabilité.** Exposer `kpi_composants` et `kpi_formules`, pour que
   l'agent puisse expliquer un KPI calculé (par exemple les 6 KPIs officiels).
6. **Comparaisons honnêtes.** Ajouter des filtres et des métadonnées de
   comparabilité dans `compare_kpis` et `get_corpus_stats` :
   - type groupe ou solo, `scr_method`, `avertissement` ;
   - exclusion optionnelle des zéros.

   Les statistiques actuelles mélangent tout : par exemple `n=36` avec
   `min=0.0` sur `scr_souscription_sante`.
7. **Résumé de validation fiable.** Séparer les contrôles « NON CONTRÔLABLE »
   des vrais échecs, et tenir compte de `legitime`.
8. **Technique.**
   - annotations de type et schémas JSON des paramètres et retours, pour la
     définition des outils ;
   - connexion SQLite en lecture seule (`mode=ro`) ;
   - un seul millésime (2025) en base : toute question sur l'évolution d'une
     année à l'autre est hors de portée de `kpis.db`.

### Mise à jour après Décision 161 (16/10)

Rédigé le 2026-10-16, en lecture seule, sur le poste local (master à
`e9147a0`). Ce qui précède décrit la base **d'avant** la Décision 161
(empreinte `438e0475…`, récupérée par `git show 4d341d4:kpis.db`). La base
actuelle a l'empreinte `bb416d3b…` (commit `732193b`). Les deux ont été
comparées sur des **copies** de scratchpad ouvertes en `mode=ro`. Les appels
à `kpi_service.py` ont été faits sur deux autres copies, et l'original est
resté intact (empreinte inchangée). Scripts (scratchpad, hors dépôt) :
`comparer_db.py`, `appels_kpi_service_161.py`.

**Schéma.** Aucune table ajoutée ni supprimée. Une seule colonne ajoutée :
`kpis.source_chapter_technique` (TEXT), d'où **16 colonnes** dans `kpis` au
lieu de 15. Aucune colonne supprimée ni renommée, ordre conservé. Même
nombre de lignes dans toutes les tables (`kpis` 1 049, `kpi_composants`
1 169, `validation_checks` 2 171, etc.).

**Comparaison des lignes**, faite sur une clé métier et non sur `id` :
188 lignes de `kpis` (les 6 KPIs officiels), 508 de `kpi_composants` et les
2 171 de `validation_checks` ont été réinsérées avec un **nouvel `id`**
(les rejeux font avancer `sqlite_sequence`). Un agent ne doit donc pas
garder un `id` d'une extraction à l'autre.

| Table | Clé de comparaison | Identiques | Différentes | Colonne modifiée |
|---|---|---:|---:|---|
| `kpis` | société, année, `kpi_name` | 188 | 861 | `source_chapter` seulement |
| `kpi_composants` | société, année, `kpi_name`, `composant_index` | 956 | 213 | `composant_label` seulement |
| `validation_checks` | société, année, `check_name` | 2 134 | 37 | `details` seulement (contrôles `sp_nonvie_ligne_*`) |
| `companies`, `kpi_formules`, `impact_mesures_lt`, `corrections` | — | toutes | 0 | — |

- **Valeurs, unités et pages de `kpis` : identiques sur les 1 049 lignes**
  (`value`, `unit`, `source_page`), ainsi que `raw_value`, `raw_unit`,
  `validated`, `avertissement`, `note_avertissement`, `source_pdf` et
  `category`. Il n'y a donc pas d'exemple de différence à donner.
- Les 188 lignes non modifiées sont exactement les 6 KPIs officiels
  (catégorie `indicateurs_comparables`). Leur `source_chapter` était déjà
  en français (par exemple « Impact des mesures de long terme (état
  S.22.01) ») et leur `source_chapter_technique` est NULL.
- Exemples hors `kpis` : libellé de composant « Meilleure estimation
  (best_estimate) » → « Meilleure estimation (best estimate) » ; détail
  de contrôle « primes acquises brutes – assurance directe r0210 = … » →
  même texte sans le code de ligne `r0210`. Les 36 contrôles
  « NON CONTRÔLABLE » sont toujours là (P10 inchangé).

**`source_chapter` et `source_chapter_technique`.**
- `source_chapter` contient maintenant le texte en français simple qu'affiche
  le front. Il a été réécrit sur 861 lignes, dont 5 KPIs à valeur NULL.
- `source_chapter_technique` contient l'**ancien `source_chapter`, à
  l'identique**, sur ces 861 lignes : il est égal à l'ancienne valeur dans
  861 cas sur 861. Il vaut NULL sur les 188 lignes des KPIs officiels.

| Société · KPI | `source_chapter` (actuel) | `source_chapter_technique` |
|---|---|---|
| Groupama · `ratio_scr` | « Rapport, chapitre E.1 (fonds propres) » | « E.1 » |
| MACIF SAM · `ratio_scr` | « Tableau officiel S.23.01 (fonds propres) — rapport unique du groupe Aéma, partie consacrée à la société ; lu sur une page image » | « Document combiné 'Aéma Groupe RAPPORT UNIQUE...' (621p), entité isolée pages 452-467 (extraction manuelle sur rendu image, cf. Décision 083) — S.23.01.01.01/R0620 » |
| AXA France IARD · `scr_souscription_sante` (valeur NULL) | « Pas de montant séparé : inclus dans un autre risque (modèle interne). » | « NULL : inclus dans un autre poste — S.25.05.21 (annexe QRT p.9), lignes « - diversified » ; … » (texte complet plus long) |

Les extraits du point 2 (MACIF SAM) et du point 3 (« NULL : inclus dans un
autre poste… ») montrent donc l'ancien texte. Ce texte se lit désormais dans
`source_chapter_technique`.

**`kpi_service.py` (Groupama, 2025) : format inchangé, sauf une clé ajoutée.**

| Fonction | Résultat actuel | Changement |
|---|---|---|
| `get_kpis` | 26 KPIs | clé `source_chapter_technique` ajoutée à chaque ligne |
| `get_kpi(…, "ratio_scr")` | `value` 274.0, `unit` pct, `source_page` 85, `validated` 1, `avertissement` 0 | même clé ajoutée ; `source_chapter` = « Rapport, chapitre E.1 (fonds propres) » |
| `compare_kpis("ratio_scr")` | 41 sociétés, 0 `None` | même clé ajoutée à chaque ligne |
| `get_corpus_stats("ratio_scr")` | `n=41`, moyenne 276,94, médiane 227,0, min 128,0, max 953,0 | aucun (identique au chiffre près) |
| `get_validation_report` | 59 contrôles, 53 réussis, 6 échoués | aucun : mêmes clés, mêmes 6 contrôles échoués |

En dehors de `source_chapter_technique`, la structure renvoyée (clés et
types) est identique pour les 5 fonctions. Les constats des points 2 à 5
restent valables. Une conséquence pour l'agent : il a maintenant deux textes
de source par KPI, un lisible (`source_chapter`) et un technique
(`source_chapter_technique`, NULL pour les 6 KPIs officiels). Le choix de
celui à citer reste à décider.

### P5 — résolu (16/10)

Revérifié **en local**, en lecture seule. **Aucun fichier n'a été modifié**,
car aucune correction de page n'existe encore.

**Recherche dans `frontend/src`** (`- 1`, `-1`, `initialPage`,
`pageSource`, `source_page`) :
- `kpi-pdf-modal.tsx:60` : `useState(kpi.pageSource ?? 1)`, puis
  `initialPage={viewingPage}` (l. 430) ; `naviguerVersPage(page)` (l. 65-69)
  passe aussi la page sans changement.
- `pdf-page-viewer.tsx:88, 117` : `doc.getPage(currentPage)` (pdf.js, pages
  numérotées à partir de 1), sans décalage. Les `cible - 1` (l. 392, 522)
  convertissent la page en indice de tableau (base 0) : ce n'est pas un
  décalage.
- `app/documents/page.tsx:45-48, 209` : `initialPage={pageCible ?? 1}`, avec
  la page lue telle quelle dans `kpi-sources.json` ou
  `donnees-extraites.json`.
- `kpi-ligne.tsx:45-47`, `csv-export.ts:99` : la page est affichée ou
  exportée telle quelle.
- `KpiPdfModal` est ouvert par `base-donnees/page.tsx` et
  `analyse/individual-tab.tsx`, qui ne transforment pas la page.

**Chronologie Git** (`git log -G` sur `frontend/src`) :
- 28/09 à 03:09 (`ef51401`, « fix: adjust PDF page offset (-1) for printed
  vs physical page numbers ») : `initialPage={Math.max(1, (kpi.pageSource ?? 1) - 1)}`.
- 28/09 à 15:38 (`f5d0c6e`, « fix(kpi-modal): remove off-by-one page number
  in PdfPageViewer ») : retour à `initialPage={kpi.pageSource ?? 1}`.
- Depuis, aucun commit ne réintroduit de décalage. L'erreur du 0.4
  (« non trouvé ») venait de la recherche dans le seul état actuel du code,
  sans l'historique.

**Conclusion.** Au clic sur un KPI, le lecteur ouvre **exactement la page
stockée dans `kpis.db`** (page physique). Contrôle sur 3 KPI : page en base,
page des deux JSON exportés, puis présence de la valeur dans le texte de la
page physique (PyMuPDF).

| KPI | `kpis.db` | `donnees-extraites.json` | `kpi-sources.json` | Valeur sur la page physique |
|---|---:|---:|---:|---|
| Groupama · `ratio_scr` (274 %) | 85 | 85 | 85 | ✅ « 2,74 », ligne R0690 (S.23.01) ; numéro imprimé « 85 » |
| La Mondiale · `scr_total` (rapport de groupe AG2R) | 251 | 251 | 251 | ✅ « 2 441 979 » (K€), absent des pages 250 et 252 |
| MGEN · `fonds_propres_eligibles` | 53 | 53 | 53 | ✅ « 3 441 361 » (K€), absent des pages 52 et 54 |

L'écart entre numéro imprimé et page physique (0, −1 ou −2 selon le PDF,
voir le point 4) reste vrai. L'agent doit donc citer la page physique (P6),
mais le front ne corrige plus rien.

### P6 — résolu (16/10)

La règle de citation est fixée par écrit dans la **Décision 163**
(« Numéro de page cité par le Chat AI »). Le Chat AI cite toujours la page
**physique** du PDF, celle de `kpis.source_page`, sous la forme « page N du
PDF ». Il ne cite jamais le numéro imprimé et n'applique aucune correction
fixe, car l'écart varie selon le document (point 4 : 0 pour CNP, MACSF et
SwissLife ; −1 pour l'annexe QRT d'AXA France IARD ; −2 pour MGEN). Le
format exact de la citation sera fixé au titre 5 du plan. Rien d'autre n'a
été modifié : ni `kpis.db`, ni le code, ni CLAUDE.md.

### P7 — résolu (16/10)

**Avant le changement.**
- **Requêtes :** `kpi_service.py` ne contient que des `SELECT` (13 appels
  `execute`). Il n'a aucun `INSERT`, `UPDATE`, `DELETE`, `CREATE`, `PRAGMA`
  ni `commit` explicite.
- **Appelants :** le seul fichier du dépôt qui l'importe est
  `export_kpis_json.py`, en lecture seule. Ce script est obsolète
  (Décision 157 : « ne pas relancer », car il écrit `kpis_export.json`).
  `ajouter_valeurs_brutes.py` ne le cite que dans un commentaire. Aucun
  fichier non suivi ne l'importe, et le front ne l'appelle pas. Personne
  n'a donc besoin d'écrire par sa connexion.
- **Référence « avant » :** elle a été capturée sur une **copie** de
  `kpis.db`. Elle couvre les 5 fonctions sur Groupama, MACIF SAM et Abeille
  Vie (Aéma), `compare_kpis` et `get_corpus_stats` sur `ratio_scr`,
  `scr_total` et `sp_nonvie`, les 3 cas limites du point 3, et
  `export_kpis_json.construire_export()` en mémoire (sans écrire de
  fichier).

**Changement.** Seule `_connexion()` est modifiée (+5 lignes, −1). La
connexion devient
`sqlite3.connect(f"{Path(db_path).resolve().as_uri()}?mode=ro", uri=True)`,
soit `file:///C:/Users/PC/Documents/rag-actuariat/kpis.db?mode=ro`. Si le
fichier est absent, `FileNotFoundError("Base KPI introuvable : …")` est levée
avant la connexion. La gestion des erreurs des fonctions n'est pas touchée
(P8).

**Contrôles.**

| Contrôle | Résultat |
|---|---|
| 5 fonctions + `construire_export()` : avant (copie, ancien code) / après (original, `mode=ro`) | ✅ 22 entrées identiques, aucune différence (les cas limites aussi : `{}`, `None`, `KpiIntrouvable`) |
| `UPDATE` puis `INSERT` sur une copie, avec `_connexion()` du service | ✅ tous deux refusés : `sqlite3.OperationalError: attempt to write a readonly database` ; la copie est inchangée (`cmp`) |
| Base absente | ✅ `FileNotFoundError : Base KPI introuvable : …\base_absente.db`, aucun fichier créé |
| Chemin avec espace et accent (`Dossier avec espace é`) | ✅ lecture correcte (Groupama `ratio_scr` 274.0, p. 85) |
| Chemin par défaut, script lancé depuis un autre dossier | ✅ lecture correcte |
| Empreinte de l'original `kpis.db` | ✅ identique avant et après (`08b6fa17846d7adb…`), aucune modification Git |
| Scripts appelants | `export_kpis_json.py` est vérifié par `construire_export()` en mémoire (identique). Son `main()` n'a pas été relancé, car il réécrirait `kpis_export.json`, supprimé par la Décision 157 |

Remarque, sans correction (hors périmètre) : les méthodes utilisent
`with self._connexion() as conn:`. Ce bloc gère une transaction, mais ne
**ferme** pas la connexion : elle reste ouverte jusqu'au ramasse-miettes.
C'est sans risque en lecture seule, mais à reprendre au titre 3 si l'agent
appelle le service très souvent.

### P8 — résolu (format fixé, code au titre 3) (16/10)

Comportement **actuel** de `kpi_service.py`, mesuré en exécutant chaque cas
sur une **copie** de `kpis.db` (année 2025, sauf mention). L'original est
inchangé (`08b6fa17846d7adb…`). `kpi_service.py` n'est pas modifié.

| Cas | `get_kpis` | `get_kpi` | `compare_kpis` | `get_corpus_stats` | `get_validation_report` |
|---|---|---|---|---|---|
| Société inexistante (« Société Inexistante ») | `{}` | exception `KpiIntrouvable` : « Entreprise 'Société Inexistante' absente de companies » | sans objet (pas de paramètre société) | sans objet | résumé vide : `n_checks=0, n_passed=0, n_failed=0`, `checks=[]` |
| Mal orthographiée (« groupamma ») | `{}` | exception `KpiIntrouvable` : « Entreprise 'groupamma' absente de companies » | sans objet | sans objet | résumé vide |
| Nom partiel (« Macif » au lieu de « MACIF SAM ») | `{}` | exception `KpiIntrouvable` : « Entreprise 'Macif' absente de companies » | sans objet | sans objet | résumé vide |
| Casse différente (« groupama ») | `{}` | exception `KpiIntrouvable` | sans objet | sans objet | (non testé ; même requête exacte) |
| KPI inexistant (« kpi_bidon ») | sans objet (renvoie tous les KPI) | `None` | dict de 41 sociétés, toutes `None` | `{n: 0, moyenne: None, mediane: None, min: None, max: None}` | sans objet |
| KPI existant à valeur NULL (AXA France IARD · `scr_souscription_sante`) | ligne présente, `value: None` | ligne complète, `value: None`, `source_page: None` | 41 lignes, dont 5 à `value: None` | NULL ignorés : `n=36`, mais `min=0.0` (zéros comptés) | sans objet |
| KPI absent pour la société (Groupama · `mcr_en_pct_scr`, aucune ligne) | clé absente (26 KPI) | `None`, comme un KPI inexistant | — | — | sans objet |
| Année absente (2024) | `{}`, comme une société inexistante | `None` | 41 `None` | `n: 0`, le reste `None` | résumé vide |
| Base introuvable | exception `FileNotFoundError` : « Base KPI introuvable : … » (depuis P7, aucun fichier créé) | idem | idem | idem | idem |

Ce qui rend ces réponses inutilisables telles quelles par un agent :
- **Société inconnue :** elle donne trois réponses différentes selon la
  fonction (`{}`, une exception ou un résumé vide), sans aucune suggestion
  de nom proche.
- **Réponses identiques pour des cas différents :**
  - `{}` veut dire « société inconnue » ou « année absente » ;
  - `None` veut dire « KPI inexistant » ou « KPI absent pour cette
    société » ;
  - un résumé de validation vide veut dire « société inconnue » ou
    « aucun contrôle ».
- **Valeur NULL :** elle n'est pas distinguée d'un échec, et son
  explication est seulement dans `source_chapter`.

**Format cible : Décision 164** (« Format des réponses et des erreurs des
outils de l'agent »). Aucune exception n'est remontée à l'agent ; chaque
réponse porte un champ `statut` parmi `ok`, `societe_inconnue` (avec des
noms proches), `kpi_inconnu` (avec les KPI disponibles), `valeur_absente`
(KPI NULL, qui n'est pas une erreur) et `erreur_technique`. Avec `ok`, la
réponse contient au minimum la valeur, l'unité, la page physique, le
fichier PDF et le statut de fiabilité. Le code sera écrit au titre 3, dans
les outils de l'agent, sans modifier `kpi_service.py`.

### P9 — résolu (16/10)

**Inventaire** (lecture seule ; il y a **21** KPI extraits et non 22 depuis
la Décision 144, plus 6 KPI calculés, soit 27 `kpi_name` dans `kpis`) :

| Information | Où elle existe avant P9 | Couverture | Côté Python ? |
|---|---|---|---|
| Nom de la société | `kpis.db`, `companies.name` | 41/41 | ✅ |
| Fichier PDF | `kpis.db`, `documents_sfcr` (P1, P3) ; `kpis.source_pdf` pour 17 lignes | 41/41 | ✅ |
| Libellé lisible | `kpi_definitions.py` : `KPI_DEFINITIONS[].label` (21) et `KPI_INDICATEURS_OFFICIELS[].label` (6). Front : `KPI_LABELS_REELS` (`lib/donnees-extraites-utils.ts:180`, 21), `definitionsKpis` du JSON (6, recopié de Python), `KPI_LABELS` (`app/documents/page.tsx:34`, 6) | 27/27 | ✅, mais avec des **différences** (voir plus bas) |
| Définition courte | 6 calculés : `KPI_INDICATEURS_OFFICIELS[].description` (Python, exporté à l'identique). 21 extraits : **seulement** `DESCRIPTIONS` (`data/analyse-demo.ts:88`) | 27/27, dont 21 **dans le front seulement** | ❌ pour les 21 |
| Unité | `kpis.unit` (une seule par KPI), `KPI_DEFINITIONS[].unit`, `KPI_INDICATEURS_OFFICIELS[].unit` : identiques. Le front affiche `pct` comme `%` | 27/27 | ✅ |
| Formule | `kpis.db`, `kpi_formules` (188 lignes, par société) : les 6 calculés seulement. La fenêtre de formule du front (`kpi-pdf-modal.tsx:470-570`) lit `formule` du JSON, c'est-à-dire cette table. **`ratio_scr` n'a pas de formule stockée** : il est lu directement (S.23.01, R0620) ; seule la définition du front dit « Fonds propres éligibles / SCR » | 6/27 | ✅ |
| Composants | `kpis.db`, `kpi_composants` (1 169 lignes) : 6 calculés + 5 sommes (`best_estimate`, `marge_risque`, `provisions_techniques`, `primes_acquises_brutes`, `charge_sinistres`) | 11/27 | ✅ |
| Sens (plus haut = mieux) | 6 calculés : `KPI_INDICATEURS_OFFICIELS[].classement` (Python). Extraits : **seulement** `SENS_KPI` (`lib/analyse-utils.ts`), pour 3 KPI (`ratio_scr`, `ratio_mcr` = higher ; `scr_diversification` = lower). Le champ Python `sign` (signe attendu) n'est pas un sens | 9/27, dont 3 **dans le front seulement** | ❌ pour les 3 |

**Différences entre deux sources** (signalées, rien n'a été corrigé) :
- **Libellés des 21 extraits : 17 diffèrent** entre `KPI_DEFINITIONS.label`
  et le libellé affiché (`KPI_LABELS_REELS`). Exemples : « Ratio de
  couverture du SCR » / « Ratio SCR » ; « Capital minimum requis (MCR) » /
  « MCR ». **`kpi_definitions.py` écrit « Tier 1 non repris / repris »**
  alors que le front écrit « Tier 1 non restreint / restreint », qui est le
  terme réglementaire : le libellé Python est probablement faux.
- `app/documents/page.tsx` écrit « Best Estimate » ; `KPI_LABELS_REELS`
  écrit « Best estimate ».
- `DESCRIPTIONS` (front) :
  - pour les 4 KPI Tier, la définition est identique au libellé : il n'y a
    pas de vraie définition ;
  - `primes_acquises_brutes` est décrit comme « Primes brutes **émises** sur
    l'exercice », alors que le KPI porte sur les primes **acquises**.

  Les deux textes sont recopiés tels quels.

**Créé.** Comme deux informations n'existaient que dans le front, la table
**`catalogue_kpis`** a été ajoutée à `kpis.db`. Elle est remplie par
`creer_table_catalogue_kpis.py`, qui lit les fichiers du front sans les
modifier, sur le modèle de `creer_table_documents_sfcr.py`. Colonnes :
- `kpi_id` (clé) ;
- `libelle` (libellé affiché par le front) ;
- `definition` ;
- `unite` (`kpis.unit`) ;
- `formule` (textes distincts de `kpi_formules`, séparés par « | ») ;
- `composants` (« par société dans kpi_composants (N sociétés, M lignes) ») ;
- `sens`.

Aucune valeur n'est inventée : 21 formules, 16 composants et 18 sens sont
vides (NULL), faute de source.
- **Sauvegarde :** `archive/kpis_avant_catalogue_kpis_20261016_230134.db`
  (SHA-256 `08b6fa17846d7adbdca3f9cc97f484761999e92c408a74311c21b835c6577228`).
- **Relance :** le script, relancé une seconde fois, donne un contenu
  identique.

**Contrôles.**
- **Correspondance :** les 27 `kpi_name` de `kpis` ont une ligne au
  catalogue, et le catalogue n'a aucune ligne en trop.
- **Front :** 0 différence avec le front (libellé affiché, définition, sens,
  unité des KPI calculés).
- **Unités :** elles concordent avec les 1 049 lignes de `kpis`.
- **Autres tables :** les 9 autres tables sont identiques à la sauvegarde
  (nombre de lignes, contenu et schéma), et le front n'est pas modifié.

**Où l'agent lira chaque information (titre 3) :**
- nom : `companies.name` ;
- PDF : `documents_sfcr` (ou `kpis.source_pdf` s'il est renseigné) ;
- libellé, définition, unité, sens et formule générique : `catalogue_kpis` ;
- formule et composants exacts d'une société : `kpi_formules` et
  `kpi_composants` ;
- page : `kpis.source_page` (Décision 163).

Limite : le catalogue recopie le front. Si le front change un libellé ou
une définition, il faut relancer le script.

### P10 — résolu (16/10)

**Stockage** (copie de `kpis.db`, lecture seule) : il n'y a **pas de
colonne de statut**. `validation_checks` porte `passed` (0/1) et `legitime`
(0/1) :

| `passed` | `legitime` | Lignes | Sens |
|---:|---:|---:|---|
| 1 | 0 | 2 127 | réussi |
| 0 | 0 | 36 | tous « NON CONTRÔLABLE » (texte `details` commençant par « NON CONTRÔLABLE — ») |
| 0 | 1 | 8 | échec connu et jugé légitime (Décision 136) |

Le seul marqueur d'un contrôle non contrôlable est ce préfixe de texte. Il
est écrit par `validate_kpis.py:569` et testé de la même façon par
`test_kpis_officiels.py:311`. Les 36 lignes sont toutes des contrôles
`sp_nonvie_ligne_*` (18 sur les primes, 18 sur les sinistres), répartis sur
10 sociétés.

**Où le nombre d'échecs est calculé.**
- **Python :** seulement dans `KpiService.validation_summary()`, qui
  alimente `get_validation_report()`.
- **Exports :** `export_kpis_for_frontend.py` n'exporte pas
  `validation_checks`. `donnees-extraites.json` et `kpi-sources.json` ne
  contiennent aucun « NON CONTRÔLABLE » ni aucun compte d'échecs.
- **Front :** il n'affiche **aucun compte d'échecs ni score de contrôle**.
  Il affiche seulement, par KPI, « Vérifié » ou « À vérifier / Non vérifié »
  (`kpi-ligne.tsx:86-99`, `kpi-pdf-modal.tsx:171-181`), et pour chaque
  composant « vérifié » ou « non vérifié » (`kpi-pdf-modal.tsx:635-638`),
  d'après `kpis.validated` et `composant_valide`. Pour les 10 sociétés
  concernées, `sp_nonvie` est à `validated=0` et ses 36 composants à
  `composant_valide=0`. Le front les montre donc « non vérifiés », ce qui
  est **exact**, et non comme des échecs.
- **Conclusion :** le front n'a pas le même mauvais compte. Rien n'est à
  corriger côté front ni côté exports.

**Correction** (`kpi_service.py`, calcul seulement, +12 lignes, −3).
`validation_summary()` sépare désormais les contrôles non réussis selon le
préfixe « NON CONTRÔLABLE ». Les clés existantes sont gardées : `n_checks`,
`n_passed`, `n_failed` (sans les non contrôlables) et `checks_echoues`.
Deux clés sont ajoutées : `n_non_controlables` et `checks_non_controlables`.
On a toujours `n_passed + n_failed + n_non_controlables = n_checks`. Le
résumé vide renvoyé pour une société inconnue porte les mêmes clés. Le
format des erreurs (Décision 164) n'est pas touché.

**Contrôles** (avant : ancien code ; après : nouveau code ; même copie de
la base) :
- **Sociétés modifiées :** seules les **10 sociétés** qui ont des « NON
  CONTRÔLABLE » changent. Pour chacune, l'écart de `n_failed` est
  exactement leur nombre en base (36 au total). `n_passed`, `n_checks` et la
  liste `checks` sont inchangés pour les 41 sociétés.

| Société | Échoués avant | Échoués après | Non contrôlables |
|---|---:|---:|---:|
| Aema Groupe | 6 | 0 | 6 |
| Groupama | 6 | 0 | 6 |
| MACIF SAM | 6 | 0 | 6 |
| Generali IARD | 7 | 1 | 6 |
| Abeille IARD Sante | 2 | 0 | 2 |
| Aesio Mutuelle | 2 | 0 | 2 |
| MMJ | 2 | 0 | 2 |
| MNPAF | 2 | 0 | 2 |
| Macif Sante Prevoyance | 2 | 0 | 2 |
| Nuoma | 2 | 0 | 2 |
| AXA France IARD, AXA France Vie, Allianz Vie, Generali Vie, Themis | 1 chacune | 1 chacune | 0 |
| Macifilia | 2 | 2 | 0 |
| Les 24 autres sociétés | 0 | 0 | 0 |

- **Échecs restants :** il en reste 8, et ce sont exactement les 8 échecs
  `legitime=1` (par exemple `completude_aucun_null` : seul NULL,
  `scr_souscription_sante` inclus dans un autre poste). Le résumé ne tient
  toujours pas compte de `legitime` : ce point n'était pas demandé et n'a
  pas été traité.
- **4 autres fonctions :** les 218 appels (`get_kpis`, `get_kpi`,
  `compare_kpis`, `get_corpus_stats`, sur les 41 sociétés et les 27 KPI) sont
  **identiques** avant et après.
- **Empreinte de `kpis.db` :** identique (`02ef32a38a4e6a84…`). La
  démonstration intégrée à `kpi_service.py` (`python kpi_service.py`)
  tourne sur l'original en lecture seule : « Contrôles Groupama 2025 :
  53/59 passés », sans liste d'échecs.

### P14 — résolu (16/10)

Vérification d'abord, en lecture seule (points 1 à 3), puis correction
(point 4). Le tableau ci-dessous montre les libellés **avant** la
correction.

**1. Libellés des 27 KPI** : `label` de `kpi_definitions.py` comparé à
`catalogue_kpis.libelle`, qui est le libellé affiché par le front. Il y a
**10 libellés identiques sur 27** : les 4 identiques parmi les 21 extraits,
et les 6 KPI officiels, que le front reçoit justement de Python.

| kpi_id | Libellé Python (`kpi_definitions.py`) | Libellé front (`catalogue_kpis`) | Identiques |
|---|---|---|---|
| `ratio_scr` | Ratio de couverture du SCR | Ratio SCR | non |
| `ratio_mcr` | Ratio de couverture du MCR | Ratio MCR | non |
| `fonds_propres_eligibles` | Total des fonds propres éligibles | Fonds propres éligibles | non |
| `fonds_propres_t1_nr` | Fonds propres de base Tier 1 non repris | Fonds propres Tier 1 non restreint | non |
| `fonds_propres_t1_r` | Fonds propres de base Tier 1 repris | Fonds propres Tier 1 restreint | non |
| `fonds_propres_t2` | Fonds propres de base Tier 2 | Fonds propres Tier 2 | non |
| `fonds_propres_t3` | Fonds propres de base Tier 3 | Fonds propres Tier 3 | non |
| `scr_total` | Capital de solvabilité requis (SCR total) | SCR total | non |
| `scr_marche` | SCR — Risque de marché | SCR — Risque de marché | oui |
| `scr_souscription_vie` | SCR — Risque de souscription vie | SCR — Souscription vie | non |
| `scr_souscription_nonvie` | SCR — Risque de souscription non-vie | SCR — Souscription non-vie | non |
| `scr_souscription_sante` | SCR — Risque de souscription santé | SCR — Souscription santé | non |
| `scr_contrepartie` | SCR — Risque de contrepartie (défaut) | SCR — Risque de contrepartie | non |
| `scr_operationnel` | SCR — Risque opérationnel | SCR — Risque opérationnel | oui |
| `scr_diversification` | SCR — Effet de diversification | Effet de diversification | non |
| `best_estimate` | Best estimate (provisions techniques) | Best estimate | non |
| `marge_risque` | Marge de risque | Marge de risque | oui |
| `provisions_techniques` | Provisions techniques totales | Provisions techniques | non |
| `mcr` | Capital minimum requis (MCR) | MCR | non |
| `primes_acquises_brutes` | Primes acquises brutes | Primes acquises brutes | oui |
| `charge_sinistres` | Charge des sinistres | Charge de sinistres | non |
| `ratio_scr_sans_mesures_lt` | Ratio SCR sans mesures de long terme | Ratio SCR sans mesures de long terme | oui |
| `impact_va` | Impact de la correction pour volatilité | Impact de la correction pour volatilité | oui |
| `impact_transitoires` | Impact des mesures transitoires | Impact des mesures transitoires | oui |
| `marge_risque_sur_be` | Marge de risque / best estimate | Marge de risque / best estimate | oui |
| `sp_nonvie` | Ratio sinistres / primes non-vie | Ratio sinistres / primes non-vie | oui |
| `mcr_en_pct_scr` | MCR en % du SCR | MCR en % du SCR | oui |

**2. Qui lit les libellés Python.** Méthode :
- recherche de tous les fichiers `.py` qui importent `kpi_definitions` :
  29 fichiers, tous suivis par Git, aucun non suivi ;
- recherche de chaque accès au champ `label` ;
- recherche des champs lus via les définitions : `unit` 52 fois,
  `category` 41, `kpi_name` 35, `sfcr_chapter` 19, `sign` 1, et `label`
  **1 seule fois**.

| Endroit | Ce qui est lu | Rôle |
|---|---|---|
| `export_kpis_for_frontend.py:280` | `KPI_INDICATEURS_OFFICIELS[].label` (les **6 officiels**) | écrit dans `definitionsKpis` de `donnees-extraites.json`, affiché par le front (`labelKpi()`) |
| `creer_table_catalogue_kpis.py:92` | `KPI_INDICATEURS_OFFICIELS[].label` (les **6 officiels**) | écrit dans `catalogue_kpis.libelle` |
| Les 27 autres importeurs (`extract_kpis*.py`, `aema_entites.py`, `ag2r_entites.py`, `validate_kpis.py`, `corrections_comparabilite.py`, `batch_diagnostic.py`, `export_kpis_json.py`, `peupler_kpis_officiels_indicateurs.py`, `test_kpis_officiels.py`) | `kpi_name`, `unit`, `category`, `sfcr_chapter`, `sign`, `indicateur` ; **jamais `label`** | extraction, conversion d'unité, contrôles, export |

**Les libellés `KPI_DEFINITIONS[].label` des 21 KPI extraits ne sont lus
par aucun code.** Ce sont eux qui diffèrent du front, dont « Tier 1 non
repris / repris ». En particulier :
- **Prompt LLM d'extraction : non.** Le seul appel à un LLM qui touche
  `kpi_definitions` (`extract_kpis.py:615` et `:654`, Gemini ou Claude sur
  `picture_75.png`) a un prompt écrit en dur : libellés « SCR Marché »,
  « SCR Vie »… et clés `kpi_name`. Le pipeline RAG (`test_markdrop/`)
  n'importe pas `kpi_definitions`.
- **Écrits dans `kpis.db` ou les JSON : non.** Recherche des 17 libellés
  différents dans `kpis.db`, `donnees-extraites.json` et `kpi-sources.json` :
  les seules occurrences sont des textes identiques d'une autre origine,
  pas une copie de `kpi_definitions.py`. Il s'agit des libellés de lignes
  des PDF (« Charge des sinistres Brut — Vie », dans `kpi_composants` et
  `validation_checks`), de la définition du front recopiée dans
  `catalogue_kpis`, et de « Ratio de couverture du SCR minimal consolidé »
  (écrit en dur dans `export_kpis_for_frontend.py:255`).
- **Clé de correspondance : non.** Toutes les recherches passent par
  `kpi_name`. Les chaînes recherchées dans les PDF sont d'autres constantes,
  indépendantes de `kpi_definitions.py`. Il s'agit de `kpi_labels_fr.py`
  (« Ratio de couverture du SCR »…), de `corriger_source_page.py:75`
  (« Charge des sinistres », « Charge de sinistres ») et de
  `batch_diagnostic.py:174-219`.

**3. Ce qui changerait** si l'on remplaçait les libellés Python par ceux du
front :
- **Les 21 libellés extraits :** rien dans le comportement. Aucun script ne
  les lit : ni extraction, ni base, ni export, ni front, ni LLM. Seuls la
  documentation et le texte de `kpi_definitions.py` changent. Le risque est
  nul pour les recherches, qui n'en dépendent pas.
- **Les 6 libellés officiels :** ils sont déjà identiques ; rien ne
  changerait. Pour information, les modifier changerait le libellé affiché
  par le front après `export_kpis_for_frontend.py`, et `catalogue_kpis`
  après `creer_table_catalogue_kpis.py`.
- **`catalogue_kpis` :** inchangé, car il prend déjà le libellé du front
  pour les 21.
- **Point d'attention :** les constantes de recherche dans les PDF
  (`kpi_labels_fr.py` etc.) sont un sujet distinct. Elles reproduisent le
  texte imprimé dans les rapports, et ne doivent **pas** être alignées sur
  les libellés d'affichage.

**4. Correction.** Les 17 libellés différents de `KPI_DEFINITIONS` dans
`kpi_definitions.py` sont remplacés par le libellé du front (colonne
« Libellé front » du tableau, identique à `catalogue_kpis`). Le diff fait
17 lignes, uniquement des champs `label`. En particulier, « Fonds propres
de base Tier 1 non repris / repris » devient « Fonds propres Tier 1 non
restreint / restreint ». `kpi_labels_fr.py` n'est pas modifié.

Contrôles :
- **Libellés :** les 27 libellés de `kpi_definitions.py` (21 extraits et 6
  officiels) sont désormais identiques à `catalogue_kpis.libelle`.
- **Autres clés :** aucune autre clé n'a changé, par comparaison des
  définitions avant et après. `kpi_name`, `category`, `unit`, `qrt_source`,
  `sfcr_chapter`, `sign` et, pour les officiels, `indicateur`, `classement`
  et `description` sont identiques. Le nombre et l'ordre des KPI aussi. Le
  contrôle intégré (`python kpi_definitions.py`) passe.
- **Catalogue :** `kpis.db` a été sauvegardée
  (`archive/kpis_avant_p14_libelles_20261016_231903.db`, SHA-256
  `5647a3df62f7e09ec1a96878c6e549c1f37ad64fe774f59132439bdc98ffdc99`), puis
  `creer_table_catalogue_kpis.py` a été relancé. `catalogue_kpis` et les 9
  autres tables sont **strictement identiques**. Comme le script réécrit la
  table et change les octets du fichier sans changer son contenu, le
  fichier sauvegardé a été remis en place : `kpis.db` n'est pas modifiée
  par ce changement.
- **Anciens termes :** il ne reste aucune occurrence de « non repris » ni
  de « Tier 1 repris » dans le code Python du projet (recherche sur tous
  les `.py`, hors `.venv`).

### P15 — résolu (16/10)

**Source et affichage.** Les 5 définitions sont dans `DESCRIPTIONS`
(`frontend/src/data/analyse-demo.ts:88-110`) :
- l. 92-95 : `fonds_propres_t1_nr`, `t1_r`, `t2`, `t3`. La définition était
  identique au libellé (par exemple « Fonds propres Tier 1 non restreint ») ;
- l. 108 : `primes_acquises_brutes`, « Primes brutes émises sur l'exercice ».

Elles ne sont lues qu'à un seul endroit, `def.description` dans
`components/analyse/kpi-card.tsx:163`. `KpiCard` n'est affiché que par
`individual-tab.tsx`, donc dans l'**onglet Analyse** seulement
(`app/analyse/page.tsx`). Aucun autre onglet ni l'export CSV ne lit ce
champ. Le même texte « Fonds propres Tier 1 non restreint » figure aussi à
`lib/donnees-extraites-utils.ts:184`, mais c'est le **libellé**
(`KPI_LABELS_REELS`) : il n'a pas été touché.

**Changement.** Les 5 textes validés remplacent les anciens, dans
`analyse-demo.ts` uniquement (5 lignes ; aucun identifiant, libellé ou
autre texte changé) :
- `primes_acquises_brutes` : « Primes correspondant à la couverture de
  l'exercice (primes émises corrigées de la variation des primes non
  acquises), avant réassurance. »
- `fonds_propres_t1_nr` : « Fonds propres de la meilleure qualité
  (capital, réserve de réconciliation…), éligibles sans limite. »
- `fonds_propres_t1_r` : « Fonds propres de Tier 1 dont l'éligibilité est
  limitée à 20 % du Tier 1 total. »
- `fonds_propres_t2` : « Fonds propres de qualité intermédiaire (par
  exemple des dettes subordonnées), éligibles dans certaines limites. »
- `fonds_propres_t3` : « Fonds propres de qualité la plus faible (par
  exemple des impôts différés actifs nets), éligibles au plus à 15 % du
  SCR. »

Ensuite, `kpis.db` a été sauvegardée
(`archive/kpis_avant_p15_definitions_20261016_231100.db`, SHA-256
`02ef32a38a4e6a8406cdadeb4b05ae83d2a1a8246cec0d402c2d0663975e8084`), puis
`creer_table_catalogue_kpis.py` a été relancé.

**Contrôles.**
- **`catalogue_kpis` :** 27 lignes avant et après, et **exactement 5 cases
  modifiées**, toutes dans la colonne `definition` de ces 5 KPI.
- **Autres tables :** les 9 autres tables sont identiques à la sauvegarde.
- **Compilation :** `npm run build` réussit (code 0, 93 s : compilation,
  lint, types, 10 pages). Le seul avertissement (polices, dans
  `src/app/layout.tsx`, fichier inchangé depuis le 26/09) existait déjà.
