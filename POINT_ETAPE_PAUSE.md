# Point d'étape — pause connexion (session interrompue)

Session en cours : **"Intégrer MACIF au pipeline + améliorer MAIF et Allianz Vie"**
(2 tâches demandées). Interrompue pendant la **Tâche 1**, avant même de commencer
la Tâche 2 (MAIF/Allianz Vie — **pas touchée du tout**, entièrement à faire).

## Ce qui est FAIT et COMMITÉ

- Commit `d776a8f` : fonction réutilisable `extraire_entite(pdf_path, page_debut,
  page_fin, nom_entite=None, out_dir=None)` ajoutée dans `test_markdrop/ingest.py`
  (juste après le header "ISOLATION D'ENTITÉ", avant `build_annexe_index`).
  Généralise la technique déjà validée sur MACIF SAM (Décision 081) et Generali
  (Décision 080) — isole `[page_debut, page_fin]` (1-indexées, inclusives) d'un
  PDF combiné en un sous-PDF physique autonome via `fitz.insert_pdf`. **Testée et
  fonctionnelle** (vérifiée sur MACIF SAM : 16 pages, contenu correct).

- **Découverte importante, confirmée par test automatisé** : les 13 sous-PDF des
  13 entités Aéma ont été isolés et passés dans le pipeline standard
  (`diagnostiquer_pdf`) — **tous à 0/20**, mode `libelles_francais`. Ça confirme
  que **les 13 entités sont 100% image**, y compris MACIF SAM elle-même (dont
  l'extraction de la Décision 081 était en fait une lecture manuelle/OCR sur
  rendu PNG, pas du texte natif comme le récapitulatif précédent le laissait
  penser). **Chaque entité nécessite la même méthode manuelle que Generali**
  (rendu PNG + lecture visuelle + recoupement interne entre pages), pas un
  raccourci automatique.

- Rien d'autre n'a été modifié dans le dépôt (git status vérifié avant ce commit —
  seul `ingest.py` était touché parmi les fichiers suivis).

## Ce qui était EN COURS (pas fini, pas committé, à refaire ou reprendre)

Traitement manuel de l'entité **Aéma Groupe** (la consolidée, pages 439-451 de
l'original, 13 pages isolées). Sous-PDF **pas sauvegardé de façon permanente** —
il était dans le scratchpad temporaire de session (probablement effacé/inaccessible
à la reprise). **Il faudra ré-isoler via `extraire_entite(...)`** :

```python
import sys; sys.path.insert(0, 'test_markdrop')
from ingest import extraire_entite
p = extraire_entite(
    'data/Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf',
    439, 451, 'Aema_Groupe'
)
```

Puis re-render en PNG (`doc[i].get_pixmap(matrix=fitz.Matrix(1.4,1.4))`) et relire
visuellement — **valeurs déjà lues ci-dessous, à VÉRIFIER avant de les réutiliser**
(lues une seule fois, pas encore recoupées deux fois comme l'exige la méthodologie
du projet) :

- **Page 1/13 (page 439 originale)** : S.02.01.02.01 BILAN — Actifs. Total de
  l'actif R0500 = 128 217 659.
- **Page 2/13 (page 440)** : S.02.01.02.01 BILAN — Passifs. Lu :
  - `best_estimate` = 6 933 945 (non-vie) + 965 908 (santé non-vie) + 1 041 504
    (santé vie) + 69 434 607 (vie) + 27 489 222 (UC) = **105 865 186** (à vérifier)
  - `marge_risque` = 416 581 + 91 004 + 69 044 + 1 025 613 + 658 473 = **2 260 715**
    (à vérifier)
- **Page 3/13 (page 441)** : S.05.01.02.01 Primes/sinistres NON-VIE, tableau 1/2
  (LoB proportionnelles) — PAS de colonne Total sur cette page, lue mais pas
  exploitée seule.
- **Page 4/13 (page 442)** : S.05.01.02.01 suite, tableau 2/2 (LoB non
  proportionnelles) AVEC colonne Total (C0200) — **image vue mais valeurs pas
  encore extraites précisément** (lecture interrompue à ce moment précis). Il
  faudra lire R0210 (Primes acquises Brut-directe), R0220 (Brut-réass
  proportionnelle), R0230 (Brut-réass non-proportionnelle), R0310/R0320/R0330
  (Charge des sinistres, mêmes 3 sous-lignes) — colonne Total (C0200) — PUIS
  chercher la page "VIE" (S.05.01.02.02, pas encore localisée dans les 13 pages,
  probablement après la page 4) pour les composantes vie de primes/charge.
- **Pages 5-13/13** : **PAS DU TOUT vues.** Contiennent presque certainement :
  S.05.01.02.02 (Primes/sinistres VIE), S.23.01.01 (Fonds propres — 2 pages comme
  pour MACIF SAM/Generali), S.25.01.21 ou S.25.05.xx (SCR — à déterminer, formule
  standard ou modèle interne inconnu à ce stade pour Aéma Groupe consolidé),
  S.28.01.01 ou S.28.02.01 (MCR). Repartir de zéro sur ces pages.

## Ce qu'il reste à faire (dans l'ordre)

### Tâche 1 (en cours, ~5% fait sur les 13 entités)

1. **Finir Aéma Groupe** : re-render, reprendre à la page 5, trouver et lire
   S.05.01.02.02 (vie), S.23.01.01 (fonds propres), S.25.xx (SCR — identifier le
   template précis), S.28.xx (MCR). Recouper chaque grand chiffre (SCR, MCR) sur
   au moins 2 pages indépendantes avant de le retenir (méthodologie Décision
   080/081 — ex. chercher une page S.22.01.21 "impact mesures LT" si elle existe,
   comme pour Generali, qui donne un recoupement gratuit).
2. **MACIF SAM** : déjà documentée (Décision 081, 20/20) — valeurs déjà connues,
   il "suffit" de les insérer dans le pipeline/`kpis.db` (pas encore fait, voir
   ci-dessous).
3. **11 entités restantes**, bornes de pages déjà connues (voir tableau
   ci-dessous) — chacune nécessite le même traitement manuel complet (rendu PNG +
   lecture + recoupement), estimé ~15-20 min chacune sur la base de l'expérience
   Generali/MACIF SAM/Aéma Groupe.
4. **Insertion dans `kpis.db`** : PAS COMMENCÉE. Il faut regarder le schéma
   (`companies(id, name, type, country)`, `kpis(id, company_id, year, category,
   kpi_name, value, unit, source_page, source_chapter, validated)`, contrainte
   unique `(company_id, year, kpi_name)`) et le pattern `inserer_en_base()` dans
   `extract_kpis.py` (lignes ~787-811) pour écrire un script d'insertion
   équivalent pour chaque entité Aéma, avec une note dans `source_chapter` (ou un
   champ dédié) indiquant "extrait du document combiné Aéma Groupe, entité X,
   pages Y-Z".
5. **Câblage pipeline** : décider comment `batch_diagnostic.py` doit représenter
   ces entités (probablement un dict statique type `GENERALI_KPIS` déjà utilisé
   pour Generali, à étendre ou dupliquer pour chaque entité Aéma — voir la
   fonction `diagnostiquer_generali()` existante comme modèle direct).
6. **Vérifier zéro régression** sur Groupama, CNP, MACSF, Pacifica, SwissLife
   (demandé explicitement par la tâche).
7. **Commit** avec le message exact demandé : "Intégration multi-entités Aéma —
   pipeline généralisé, 13 entités extraites" (probablement à adapter si toutes
   les 13 ne sont pas finies — être honnête sur le nombre réellement traité).

**Bornes de pages des 13 entités (originales, document Aéma 621 pages) :**

| Entité | Début | Fin (= début suivant - 1) |
|---|---|---|
| Aéma Groupe | 439 | 451 |
| MACIF SAM | 452 | 467 |
| Macif Vie | 468 | 478 |
| Macif Santé Prévoyance | 479 | 493 |
| Thémis | 494 | 507 |
| Macifilia | 508 | 522 |
| Aésio Mutuelle | 523 | 538 |
| MNPAF | 539 | 550 |
| MMJ | 551 | 563 |
| Nuoma | 564 | 576 |
| Abeille Vie | 577 | 592 |
| Abeille Épargne Retraite | 593 | 602 |
| Abeille IARD & Santé | 603 | 621 (fin du document) |

### Tâche 2 (pas commencée du tout)

Améliorer MAIF (13/20) et Allianz Vie (15/20) — lister les KPIs NULL restants,
diagnostiquer chacun (vérifier d'abord qu'il est vraiment NULL, pas du bruit),
corriger seulement les cas sûrs, tester la non-régression, documenter
l'irréductible. Commit : "Amélioration MAIF et Allianz Vie — KPIs supplémentaires
débloqués". **Rien fait, à démarrer de zéro** quand la Tâche 1 sera close ou
explicitement mise en pause par l'utilisateur.

## Reprise

Ne pas deviner les valeurs partielles ci-dessus sans les revérifier — elles n'ont
été lues qu'une fois (pas de recoupement à 2 sources indépendantes comme l'exige
la méthodologie du projet pour ce type d'extraction OCR/manuelle). Reprendre par
un nouveau rendu PNG d'Aéma Groupe via `extraire_entite()` (fonction déjà commitée
et fonctionnelle) et continuer la lecture à la page 5/13.
