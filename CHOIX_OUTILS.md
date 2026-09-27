# Choix d'outils — État actuel et axes d'amélioration payants

**Statut : Document vivant — mis à jour au fur et à mesure des décisions**
**Date de création : 2026-07-30**
**Dernière mise à jour : 2026-07-30**

---

## 1. Vue d'ensemble du pipeline

| # | Type de contenu | Outil actuel | Coût | Résultat mesuré |
|---|----------------|-------------|------|-----------------|
| 1 | Texte narratif (sections A-E) | Docling (IBM, open source) | Gratuit | 0 erreur numérique sur échantillon vérifié |
| 2 | Tableaux simples (données internes Groupama) | Docling/TableFormer mode ACCURATE | Gratuit | 94%+ (benchmark indépendant), 1 ligne perdue silencieusement (Hongrie) détectée par nos checks |
| 3 | Détection images dupliquées (logo) | imagehash/pHash | Gratuit | 15/16 logos regroupés correctement, 0 faux positif |
| 4 | Description d'images (organigramme, schémas) | Gemini (Google, free tier) | Gratuit (1 500 req/jour) | 10/10 détails structurels corrects (noms, %, flèches) |
| 5 | Tableaux QRT avec texte natif | Extracteur EIOPA custom (codes R/C) | Gratuit | 55/55 codes = 100% complétude |
| 6 | Tableaux QRT image-only | Gemini VLM + dictionnaire EIOPA | Gratuit (free tier) | 16/16 valeurs exactes, 2 décalages de colonne (détectables automatiquement) |

**Coût total actuel du pipeline : 0 € (hors temps de développement)**

---

## 2. Détail par type de contenu

### 2.1. Texte narratif (sections A-E)

**Outil actuel : Docling (IBM Research)**
- Licence : MIT (libre, usage commercial autorisé)
- Hébergement : local, aucune donnée ne sort du serveur
- Performance : 61 000+ étoiles GitHub, maintenu par Linux Foundation
- Résultat vérifié : 0 erreur sur les chiffres clés (SCR, ratios, montants)
  vérifiés manuellement sur 5 pages

**Meilleur outil payant identifié : Reducto**
- Spécialisé documents financiers (SEC filings, rapports réglementaires)
- Correction agentique : un LLM vérifie/corrige l'extraction en post-traitement
- Prix : sur devis, estimé ~0.05-0.10 $/page
- Gain estimé : faible sur le texte narratif propre (Docling est déjà à ~0%
  d'erreur sur ce type). Le gain réel serait sur les cas limites (texte à
  cheval sur deux colonnes, notes de bas de page complexes).
- **Gain estimé : +1-3% de précision sur les cas difficiles**
- **Priorité : BASSE — investir ici rapporte peu vu la qualité actuelle**

**Alternative open source plus récente : pdfmux**
- Score benchmark (mai 2026) : 0.903 vs Docling 0.877 (+3%)
- Très récent (v0.6), moins testé en production que Docling
- À surveiller pour une migration future si le projet mûrit

### 2.2. Tableaux simples (données propres à Groupama)

**Outil actuel : Docling/TableFormer ACCURATE**
- Résultat : bon sur les tableaux classiques (certificats mutualistes,
  filiales, chiffre d'affaires par métier)
- Faiblesse identifiée et documentée : perte silencieuse de lignes
  (cas Hongrie, -687 sur le total) + fusion de cellules (Nord Est/d'Oc)
- Compensé par : check des totaux automatique + comptage de lignes

**Meilleur outil payant identifié : Azure Document Intelligence**
- Table extraction avec confidence score par cellule (score de confiance)
- Détection automatique des cellules fusionnées (merged cells)
- Prix : ~0.01-0.065 $/page selon la fonction
- **Gain estimé : +5-10% de détection d'anomalies structurelles** (le
  confidence score aurait signalé la cellule Nord Est/d'Oc fusionnée
  automatiquement, sans besoin de comptage de lignes manuel)
- **Priorité : MOYENNE — utile quand on passe à 30 fichiers, le volume
  rend le check manuel de chaque tableau impraticable**

**Alternative payante : LlamaParse**
- Meilleure reconstruction visuelle de la structure des tableaux
- MAIS : benchmark indépendant (BoringBot) montre que la précision des
  *valeurs numériques* est inférieure à Docling ("LlamaParse is excellent
  at making things look like tables. But the data inside? Needs more
  cleaning.") — contre-indiqué pour notre cas où les chiffres comptent
  plus que le rendu visuel.

### 2.3. Détection d'images dupliquées (logo)

**Outil actuel : imagehash / pHash (Python)**
- Licence : BSD, gratuit
- Résultat : séparation parfaite (saut Hamming net : 20 vs 34)
- Temps : < 1 seconde pour 16 images

**Meilleur outil payant identifié : aucun nécessaire**
- Recherche académique (avril 2026) confirme : pHash est le meilleur
  compromis dès lors que les duplications sont visuellement similaires
  (notre cas exact : même logo redimensionné/recompressé).
- CLIP embeddings (plus puissant) ne se justifie que pour les "doublons
  sémantiques" (même sujet, angle différent) — pas notre cas.
- **Gain estimé d'un outil payant : 0%**
- **Priorité : AUCUNE — problème résolu**

### 2.4. Description d'images (organigramme, schémas)

**Outil actuel : Gemini (Google, free tier)**
- Résultat : 10/10 détails corrects sur l'organigramme (noms, %, liens)
- Coût : 0 € (free tier : ~1 500 requêtes/jour)
- Benchmark avril 2026 : "Gemini domine le traitement d'images : meilleure
  précision, coût le plus bas, vitesse la plus élevée"

**Meilleur outil payant pour la précision : Claude Sonnet**
- Précision extraction documents structurés : 97.6% vs Gemini ~95.2%
- Prix : ~8x plus cher que Gemini par image
- **Gain estimé : +2-3% de précision sur les détails fins**
- **Priorité : BASSE — le gain ne justifie pas le surcoût pour des
  descriptions d'organigrammes/schémas simples. À reconsidérer si les
  documents contiennent des graphiques financiers complexes (courbes,
  camemberts avec légendes denses)**

**Note sur la confidentialité (free tier Gemini) :**
Le free tier de Google permet l'utilisation des données pour l'entraînement
des modèles. Pour des documents publics (SFCR publiés sur le site de
Groupama), ce n'est pas un problème. Pour des documents internes/
confidentiels des clients d'Iconcilio, il faudra passer au tier payant de
Gemini (qui exclut l'utilisation pour l'entraînement) ou à Claude API.
Coût estimé : ~0.001-0.005 $/image selon le modèle.

### 2.5. Tableaux QRT avec texte natif dans le PDF

**Outil actuel : extracteur custom basé sur les codes EIOPA (R00xx/C00xx)**
- Résultat : 55/55 = 100% de complétude sur S.23.01.22
- Avantage unique : utilise la connaissance du template officiel comme
  ancrage, au lieu de deviner la structure visuellement
- Source de référence : EIOPA Annotated Templates 2.8.2 (fichier Excel
  officiel, gratuit, sous licence EIOPA)

**Meilleur outil payant identifié : aucun équivalent direct**
- Aucun produit commercial ne propose un extracteur spécialisé QRT/SFCR
  basé sur les codes DPM d'EIOPA (recherché, non trouvé).
- Les outils génériques (Textract, Azure DI, LlamaParse) extraient les
  tableaux sans connaître la sémantique EIOPA → moins précis par
  construction sur ce cas spécifique.
- **Gain estimé d'un outil payant : NÉGATIF (moins bon qu'un extracteur
  qui connaît le template)**
- **Priorité : AUCUNE — c'est un avantage compétitif pour Iconcilio**

### 2.6. Tableaux QRT image-only (pas de texte natif)

**Outil actuel : Gemini VLM + dictionnaire EIOPA post-vérification**
- Résultat : 16/16 valeurs numériques exactes, 2 décalages de colonne
  détectés automatiquement par le check EIOPA
- Coût : 0 € (free tier)

**Meilleur outil payant identifié : Claude Sonnet (vision)**
- Benchmark : "best-in-class accuracy on charts, diagrams, screenshots,
  scanned PDFs" (97.6% extraction accuracy)
- Prix : ~8x Gemini par image
- **Gain estimé : +2-5% de précision sur l'alignement des colonnes**
  (pourrait éliminer les 2 décalages observés, non testé)
- **Priorité : MOYENNE-HAUTE — à tester sur les tableaux QRT les plus
  larges (Annexe 2, S.05.01.02 avec 17 colonnes) où le décalage risque
  d'être plus fréquent. Test recommandé : même protocole que notre test
  Gemini (comparer au dictionnaire EIOPA), sur 1 tableau large, avant
  de décider.**

**Alternative spécialisée : Reducto**
- "Strongest option for enterprise document workflows involving financial
  statements" (source indépendante Firecrawl, avril 2026)
- Correction agentique post-extraction (un LLM vérifie chaque cellule)
- Prix : sur devis
- **Gain estimé : +5-10% sur les tableaux financiers complexes**
- **Priorité : HAUTE pour la phase de production si le volume dépasse
  100+ documents/an**

---

## 3. Tableau récapitulatif des gains potentiels

| Type de contenu | Outil actuel (gratuit) | Meilleur payant | Gain estimé | Priorité | Coût estimé |
|----------------|----------------------|----------------|-------------|----------|-------------|
| Texte narratif | Docling | Reducto | +1-3% | Basse | ~0.05-0.10 $/page |
| Tableaux simples | TableFormer ACCURATE | Azure Doc Intel | +5-10% | Moyenne | ~0.01-0.065 $/page |
| Images dupliquées | pHash | — | 0% | Aucune | — |
| Description images | Gemini free | Claude Sonnet | +2-3% | Basse | ~8x Gemini |
| QRT texte natif | Extracteur EIOPA | — (aucun équivalent) | Négatif | Aucune | — |
| QRT image-only | Gemini + EIOPA | Claude ou Reducto | +2-10% | Moyenne-Haute | ~0.01-0.10 $/page |

**Investissement recommandé en premier (meilleur ROI) :**
1. **QRT image-only → tester Claude Sonnet sur 1 tableau large** (coût :
   quelques centimes, gain potentiel le plus élevé sur le cas le plus
   critique)
2. **Tableaux simples → activer Azure Document Intelligence** quand on
   passe à 30 fichiers (le confidence score élimine le besoin de
   vérification manuelle ligne par ligne)

**Investissement non recommandé à ce stade :**
- Texte narratif (Docling suffit)
- Images dupliquées (pHash parfait)
- QRT texte natif (notre extracteur est meilleur que le marché)

---

## 4. Roadmap d'amélioration progressive

### Phase 1 — Actuelle (gratuit, 0 €)
Pipeline complet fonctionnel avec les 6 outils gratuits ci-dessus.
Suffisant pour : prototype, démonstration client, premiers 30 fichiers
Groupama.

### Phase 2 — Premier investissement ciblé (~50-100 €/mois)
- Gemini tier payant (confidentialité garantie pour documents clients)
- OU Claude API crédits pour les QRT image-only les plus larges
- Déclencheur : premier client avec documents confidentiels (non publics)

### Phase 3 — Montée en qualité (~200-500 €/mois)
- Azure Document Intelligence pour les tableaux simples (confidence score)
- Objectif : éliminer toute vérification manuelle de tableaux sur le
  volume de production
- Déclencheur : volume > 50 documents/mois

### Phase 4 — Excellence (~500+ €/mois)
- Reducto pour l'extraction complète (texte + tableaux + agentique)
- Remplacerait potentiellement Docling + TableFormer en un seul outil
- Déclencheur : exigence client de 99%+ de précision garantie avec
  audit trail
