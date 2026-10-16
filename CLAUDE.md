# KPIs SFCR des assureurs français (Iconcilio)

Ancien CLAUDE.md (RAG sur la directive Solvabilité II) : `archive/CLAUDE_ancien_projet_directive.md`.

## 1. Le projet
- Extraction des KPIs des rapports SFCR (Solvabilité II) d'assureurs français, depuis les PDF de `data/`.
- Résultat dans `kpis.db` (SQLite) : 41 sociétés, année 2025 seulement, 1 049 KPIs.
- Affichage dans une interface Next.js (`frontend/`), qui lit des exports JSON statiques de `kpis.db`.
- Un RAG Qdrant (4 collections : texte, tableaux, images, qrt) existe, mais seul le SFCR Groupama y est indexé.
- Un Chat AI (agent IA avec outils) est en conception (voir § 5).

## 2. Dossiers et fichiers clés
| Fichier / dossier | Rôle |
|---|---|
| `data/` | Les 39 PDF SFCR et annexes QRT (dont 9 extraits `_entite_*.pdf` d'AG2R, à ne jamais indexer) |
| `kpis.db` | Base des KPIs : `companies`, `kpis`, `kpi_composants`, `kpi_formules`, `validation_checks`, `impact_mesures_lt`, `corrections` |
| `kpi_service.py` | Couche de lecture de `kpis.db` (`KpiService`) ; ouvre la base en lecture-écriture malgré sa docstring (P7) |
| `kpi_definitions.py`, `kpi_labels_fr.py` | Référentiel des KPIs et libellés français |
| `extract_kpis.py`, `extract_kpis_*.py` | Extraction des KPIs, un script par société (Groupama pour `extract_kpis.py`) |
| `aema_entites.py`, `ag2r_entites.py` | Extraction des entités des rapports de groupe Aéma (13) et AG2R (9) |
| `populate_company_metadata.py` | Métadonnées des 41 sociétés (Décision 149) |
| `corrections_comparabilite.py` | Corrections rejouées après chaque extraction ; sa docstring donne l'ordre complet de rejeu |
| `comparabilite.py` | Règles de comparabilité entre sociétés (Décision 153), exportées vers le front |
| `textes_simples.py` | Réécriture des textes de source en français simple (Décision 161), appelée par `corrections_comparabilite.py` |
| `peupler_impact_mesures_lt.py` | Impact de la correction pour volatilité et des mesures transitoires (Décision 155) |
| `validate_kpis.py` | Contrôles actuariels, écrit `validation_checks` et `kpis.validated` |
| `export_kpis_for_frontend.py` | Exporte `kpis.db` vers `frontend/src/data/kpi-sources.json` et `donnees-extraites.json` |
| `test_markdrop/` | Pipeline RAG SFCR (Docling, index, Qdrant) ; a son propre `.venv` |
| `test_markdrop/run_pipeline.py` | Orchestrateur du pipeline RAG : narratif + QRT + indexation (Décision 048) |
| `test_markdrop/ingest_qdrant.py` | Ingestion des 4 collections Qdrant (`localhost:6333`) |
| `test_markdrop/fusion_reranking.py` | Fusion RRF des 4 collections + reranking par juge LLM (Décision 028) |
| `frontend/` | Interface Next.js 15 ; lire `frontend/CLAUDE.md` (non chargé automatiquement) |
| `frontend/src/lib/pdf-par-societe.ts` | Seule correspondance société → PDF (41 entrées) ; absente de `kpis.db` (P1) |
| `DECISIONS.md` | Historique des décisions numérotées (001 à 161) |
| `ETAT_DES_LIEUX_CHAT.md` | État des lieux du Chat AI (titre 0 du plan) |

Fichiers de l'ancien projet encore présents : `app.py` (Streamlit), `app_gradio.py`, `src/`
(à vérifier : non utilisés par le projet SFCR).

## 3. Commandes utiles
Front (dans `frontend/`) :
```bash
npm run dev
```
```bash
npm run build
```
```bash
npm run lint
```
```bash
npx tsc --noEmit
```

Régénérer les exports JSON du front, depuis `frontend/` (lance `python ../export_kpis_for_frontend.py`) :
```bash
npm run regenerate-json
```

Ordre de rejeu complet après une ré-extraction (docstring de `corrections_comparabilite.py`) :
`extract_kpis_*.py` / `aema_entites.py` / `ag2r_entites.py` → `populate_company_metadata.py`
→ `corrections_comparabilite.py` → `peupler_impact_mesures_lt.py` → `validate_kpis.py --all`
→ `export_kpis_for_frontend.py`.

Qdrant : serveur local dans `test_markdrop/qdrant_server/` (`qdrant.exe` et `storage/`, hors Git),
écoute sur `localhost:6333`. Commande de lancement non documentée dans le dépôt, à vérifier :
```bash
cd test_markdrop/qdrant_server && ./qdrant.exe
```

## 4. Règles de travail
- Répondre en français. Indiquer son niveau de confiance ; ne jamais deviner.
- Vérifier chaque affirmation contre les fichiers réels ou une commande exécutée, pas contre la mémoire.
- Ne jamais afficher la valeur d'une clé API ou d'un secret (seulement leur nom).
- Toute tâche de plus de 30 minutes est réservée au shift de nuit : s'arrêter et le signaler.
- Ne jamais inventer un chiffre : un KPI NULL reste NULL. Les chiffres viennent de `kpis.db`.
- La page citée est la page physique du PDF (`source_page`), pas le numéro imprimé (écart 0, −1 ou −2 selon le PDF).
- Ne pas reprendre la recherche hybride (BM25 : Décisions 010, 015, 037, 038) ni Self-RAG
  (à vérifier : la décision la plus proche est la 016, auto-évaluation du retrieval, rejetée)
  sans nouveau test sur le golden set.
- Pour tester une base, travailler sur une copie, jamais sur `kpis.db` d'origine.
- Ni commit ni push sans accord explicite de l'utilisateur.

## 5. Chat AI
- Objectif validé : « Un analyste actuariel IA qui répond en français aux questions chiffrées,
  comparatives et qualitatives sur les SFCR des assureurs français, avec pour chaque affirmation
  sa source exacte, son statut de fiabilité, et l'aveu clair quand l'information manque. »
- Plan : 0 État des lieux → 1 Golden set → 2 Préparer les données → 3 Outils de l'agent → 4 Agent
  → 5 Format des réponses → 6 API FastAPI → 7 Onglet Chat → 8 Mesurer et améliorer → 9 Démo au fondateur.
- État d'avancement : voir `ETAT_DES_LIEUX_CHAT.md`.

## 6. Où trouver plus
- `DECISIONS.md` : toutes les décisions numérotées, avec leur justification.
- `ARCHITECTURE.md` : encadré « État actuel » en tête ; le reste décrit encore l'ancien projet.
