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
