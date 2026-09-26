# Guide du projet — à lire pendant l'appel

Ce document explique, en langage simple, à quoi sert chaque fichier important
du projet. Il est écrit pour être lu à voix haute pendant un appel, sans
connaissance technique préalable.

L'idée générale : le système lit le rapport PDF une fois, le découpe en
petits morceaux faciles à chercher, range ces morceaux dans une base de
recherche, puis, quand quelqu'un pose une question, retrouve le bon morceau
et rédige une réponse en citant sa source.

Trois documents, à la racine du projet (un niveau au-dessus de ce dossier
`test_markdrop/`), racontent l'historique des décisions prises et pourquoi :
**DECISIONS.md**, **CHOIX_OUTILS.md** et **ARCHITECTURE.md**. Ils ne sont pas
dupliqués ici pour éviter d'avoir deux versions à jour.

---

## 1. Extraction — transformer le PDF en texte structuré

C'est la toute première étape : lire le PDF et en sortir un texte organisé
(titres, paragraphes, tableaux, images), avant tout traitement.

- **`extract_raw_structure.py`** — Lit le PDF avec l'outil d'extraction
  (Docling) et en sort la structure brute : titres, paragraphes, tableaux,
  images.
- **`save_docling_document.py`** — Lance la lecture complète du PDF une
  seule fois et sauvegarde le résultat brut, pour ne jamais avoir à relire
  tout le PDF si une étape suivante doit être refaite.
- **`convertir_2024_une_fois.py`** — Fait la même chose, pour le rapport de
  l'année 2024.
- **`ingest.py`** — Orchestre le traitement des pages spéciales appelées
  QRT (des tableaux réglementaires très normés), en s'appuyant sur les
  fichiers ci-dessous.
- **`extract_qrt_s23.py`** — Sait lire un type précis de tableau
  réglementaire.
- **`extract_qrt_s05_gemini.py`** — Lit un autre type de tableau
  réglementaire, plus complexe, avec un modèle d'IA capable de lire des
  images.
- **`qrt_checks.py`** — Vérifie que les tableaux réglementaires ont été lus
  dans le bon ordre de colonnes.
- **`parsers.py`** — Repère, dans le sommaire du rapport, à quelle section
  appartient chaque page.

## 2. Découpage — préparer des morceaux faciles à chercher

Le texte extrait est ensuite découpé en morceaux ("chunks") ni trop longs ni
trop courts, chacun rattaché à sa source exacte.

- **`build_sections.py`** — Regroupe le texte en sections, une par titre du
  document.
- **`build_leaf_chunks.py`** — Ajuste la frontière de chaque morceau pour
  qu'il s'arrête au bon endroit.
- **`split_and_merge_chunks.py`** — Sépare les morceaux trop longs et
  regroupe ceux qui sont trop courts.
- **`attach_metadata.py`** — Attache à chaque morceau les informations qui
  permettront de citer sa source (page, section).
- **`clean_final_text.py`** — Corrige quelques défauts de texte repérés lors
  des vérifications.
- **`retype_bullet_headers.py`** — Corrige un défaut où des puces de liste
  avaient été confondues avec des titres.
- **`detect_anomalies.py`** — Relit automatiquement tous les morceaux pour
  repérer les cas suspects avant une vérification humaine.
- **`extraire_visuels.py`** — Sauvegarde, sous forme d'images, les tableaux
  et images du rapport.
- **`associer_visuels_chunks.py`** — Relie chaque image sauvegardée à
  l'endroit du texte où elle apparaît.
- **`correction_fusion_caisses.py`** — Corrige un défaut précis où le nom
  d'une Caisse régionale et son chiffre avaient été fusionnés par erreur.
- **`caisses_regionales.py`** — Liste des 13 Caisses régionales Groupama,
  utilisée par le fichier de correction ci-dessus.

## 3. Indexation — ranger le contenu dans la base de recherche

Chaque morceau (texte, tableau, image) est transformé en une forme que la
base de données peut comparer à une question, puis rangé dans un espace
dédié.

- **`create_collection_texte.py`**, **`create_collection_tableaux.py`**,
  **`create_collection_images.py`**, **`create_collection_qrt.py`** —
  Créent, dans la base de recherche (Qdrant), un espace de rangement vide
  pour chaque type de contenu. Étape de préparation, faite une seule fois.
- **`build_index_texte_bge.py`** — Transforme chaque morceau de texte en
  une représentation numérique qui permet de le retrouver par le sens de la
  question, pas seulement par les mots exacts.
- **`build_index_visuels.py`** — Fait la même chose pour les tableaux et
  les images.
- **`ingest_qdrant.py`** — Range réellement tout le contenu préparé dans la
  base de recherche.
- **`ingest_qdrant_2024.py`** — Ajoute le rapport 2024 sans toucher à ce
  qui est déjà en place pour 2025.

## 4. Recherche et fusion — retrouver le bon passage

- **`recherche_collections.py`** — Interroge séparément chacun des 4
  espaces de rangement pour trouver les passages les plus proches de la
  question.
- **`fusion_reranking.py`** — Combine les résultats des 4 recherches et les
  classe pour ne garder que le meilleur candidat. C'est le cœur du système.

## 5. Résolution des marqueurs — remettre les vrais tableaux et images

- **`resolution_marqueurs.py`** — Remplace les renvois internes du texte
  (« voir tableau X ») par le vrai tableau ou la vraie image, au moment de
  préparer la réponse.

## 6. Génération — écrire la réponse

- **`generation.py`** — Écrit la réponse finale donnée à l'utilisateur, à
  partir du meilleur passage trouvé, en citant sa source.

## 7. Fichier partagé par plusieurs étapes

- **`chemins_visuels.py`** — Centralise la façon de nommer et de retrouver
  les fichiers d'images, pour que toutes les étapes s'y retrouvent de la
  même manière.

## 8. L'application — ce que vous voyez à l'écran

L'interface ne vit plus dans ce dossier `test_markdrop/` — elle a été
migrée vers `frontend/` (Next.js) et l'ancienne interface Reflex
(`sfcr_app/`) a été supprimée. Voir `frontend/src/app/{chat,analyse,
documents}` pour les 3 onglets. **Le chat n'est pas encore branché aux
étapes ci-dessus** (aucun appel backend) — seul l'onglet Analyse affiche
des données (100% mock pour l'instant, `frontend/src/data/analyse-demo.ts`).
Un futur backend devra appeler `fusion_reranking.py` (recherche + fusion
des 4 collections) puis `generation.py` (écriture de la réponse citée) pour
rendre le chat fonctionnel.

## 9. Données et questions-tests

- **`output_structure_brute/`** — Toutes les données produites par les
  étapes ci-dessus pour le rapport SFCR 2025, y compris les questions-tests
  de référence (golden set) utilisées pour vérifier la qualité du système.
- **`output_structure_brute_2024/`** — La même chose pour le rapport SFCR
  2024.

---

## Et le reste ?

Tout ce qui a servi une fois pendant le développement (scripts de
diagnostic, essais de modèles concurrents, dossiers de test ponctuels,
anciens journaux d'exécution) a été déplacé — jamais supprimé — dans le
dossier **`_historique_dev/`**, pour garder une trace complète sans
encombrer la vue pendant la démonstration.
