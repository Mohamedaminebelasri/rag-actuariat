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
