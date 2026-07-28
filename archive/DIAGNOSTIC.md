# DIAGNOSTIC.md — Qualité de data/articles.jsonl

Date : 2026-07-25
Portée : les 312 articles écrits par `src/ingest.py`. Diagnostic seul, **aucune correction appliquée**.

## Constat prioritaire (au-delà des 5 catégories demandées)

En creusant la catégorie "titres suspects", un bug structurel est apparu dans
`split_title_and_body()` (fonction utilisée par `ingest.py` pour séparer
titre et corps) : elle cherche la première ligne qui commence par `N. `
(chiffre + point) pour savoir où finit le titre et où commence le corps.
Or de très nombreux articles de Solvabilité II énumèrent leurs points avec
`1)`, `a)`, ou ne sont pas énumérés du tout (simple prose) — pas `1. `.

**Conséquence : pour 142 articles sur 312 (45 %), le champ "titre" contient
en réalité TOUT le corps de l'article** (parfois plusieurs milliers de
caractères), parce qu'aucune ligne "N. " n'a jamais été trouvée pour marquer
la fin du titre. Exemple : le "titre" de l'Article 1 est actuellement :
`"Objet La présente directive établit des règles concernant: 1) l'accès aux activités n on salariées..."`
(tout l'article), au lieu de simplement `"Objet"`.

C'est **bloquant** : ce sont ces titres qui s'afficheront dans les citations
`[Article X — page Y]`, et une citation ne peut pas être un pavé de 2000
caractères.

**Cas aggravé : l'Article 312** (le dernier article détecté) cumule ce bug
avec un second bug de bornage : comme c'est le dernier élément de la liste
`final_starts`, `build_articles()` fixe sa fin de texte à `len(full_text)`
— c'est-à-dire la fin littérale du PDF, bien après la borne d'annexe
(page 126). Résultat vérifié en relisant le fichier :
- `titre` de l'Article 312 contient le vrai (court) texte de l'article
  ("Destinataires... Les États membres sont destinataires de la présente
  directive. Fait à Strasbourg...") suivi de la signature du texte officiel.
- `texte` de l'Article 312 (69 514 caractères, le plus long de tous)
  contient en réalité le contenu des **annexes I à VII** (classification
  des branches d'assurance, tableaux de correspondance), pas le corps de
  l'article. On y trouve même des fragments de texte à l'envers
  ("e vitcerid etnesérp EC/44/7002", artefact d'extraction d'un tableau
  pivoté) : preuve que le "corps" de l'Article 312 est entièrement le mauvais
  contenu.

---

## 1. Espaces parasites dans les mots (corps)

- **310 / 312 articles** contiennent au moins un mot cassé par un espace
  parasite (ex. "techniqu es", "requ is").
- **~4 754 occurrences** estimées au total sur l'ensemble du corpus.
- 15 exemples réels (mot cassé — article) :
  1. "activités n" — Art. 1
  2. "directive s" — Art. 2
  3. "territoire d" — Art. 2
  4. "désiren t" — Art. 2
  5. "applique ég" — Art. 2
  6. "fin s" — Art. 2
  7. "activité con" — Art. 2
  8. "fourn ir" — Art. 2
  9. "déplacemen ts" — Art. 2
  10. "paiemen t" — Art. 2
  11. "immédiatemen t" — Art. 2
  12. "suite d" — Art. 2
  13. "dan s" — Art. 2
  14. "requ is" — Art. 129 (titre)
  15. "techniqu es" — Art. 77 (titre)

**Gravité : gênant.** Ne casse pas la recherche sémantique (le sens reste
globalement présent) mais dégrade la lisibilité des citations affichées à
l'utilisateur et peut légèrement nuire à la qualité des embeddings sur les
mots concernés.

---

## 2. Caractères anormaux

- **`\xad` (césure) et `\xa0` (espace insécable) : 0 article concerné.**
  Le nettoyage `clean_page` appliqué lors de l'écriture fonctionne
  correctement pour ces deux caractères précis.
- **Séquences illisibles de type pied de page** ("R F9002.21.71",
  "e vitcerid etnesérp EC/44/7002") : ma détection automatique par regex
  stricte n'en a trouvé aucune (0), car ces codes ont des espaces insérés de
  façon irrégulière entre chaque caractère et ne correspondent à aucun motif
  fixe. Mais elles sont bien présentes — visibles manuellement dans les
  mêmes articles que la catégorie 5 ci-dessous (ex. Article 5 : "R F9 0 0 2 .
  2 1 . 7 1"), et massivement dans le corps corrompu de l'Article 312
  (fragments de texte à l'envers issus des tableaux d'annexe).

**Gravité : gênant** pour les ~97 articles concernés (recoupe la catégorie
5) ; **bloquant** pour l'Article 312 spécifiquement, où ces fragments
remplacent le vrai contenu.

---

## 3. Intégrité des articles

- **Articles < 100 caractères : 0.** Aucun article anormalement court.
- **Articles > 6000 caractères : 5**
  - Article 13 : 14 680 caractères — légitime (article "Définitions",
    ~39 points énumérés, déjà vérifié en détail lors du diagnostic).
  - Article 105 : 8 790 caractères — à vérifier, pas d'anomalie détectée.
  - Article 248 : 6 349 caractères — à vérifier, pas d'anomalie détectée.
  - Article 303 : 19 229 caractères — à vérifier ; aucun signe de bug de
    bornage détecté (le suivant, Article 304, existe bien dans la liste),
    probablement un article de modification légitimement long.
  - **Article 312 : 69 514 caractères — confirmé corrompu** (voir constat
    prioritaire ci-dessus : contient les annexes I-VII, pas le corps réel).
- **Titres vides : 0.**
- **Titres suspects (bug de séparation titre/corps) : 151**, décomposés en
  142 titres > 200 caractères (corps quasi entier avalé) et 9 titres entre
  120 et 200 caractères (swallow partiel probable).

**Gravité : bloquant** pour l'Article 312 et pour les 142 titres corrompus ;
**cosmétique** pour Article 105/248/303 (simple vérification recommandée,
pas d'anomalie avérée).

---

## 4. Titres avec espaces parasites

**201 / 312 titres** contiennent au moins un mot cassé. Cette catégorie
recoupe largement la catégorie 3 : sur les 142 titres déjà corrompus par le
bug titre/corps, la quasi-totalité contient aussi des espaces parasites
(logique, puisqu'ils contiennent tout le corps de l'article). Parmi les 161
titres de longueur normale, une partie non négligeable est également
affectée — exemples concrets tirés du corpus :
- Article 4 : "Exclusion du champ d'application en raison de la taille" →
  "champ d" cassé
- Article 17 : "Forme juridique de l'entreprise d'assu rance ou de
  réassurance" → "entreprise d'assu rance"
- Article 24 : "Actionnaires et associés détenant u ne participation
  qualifiée" → "détenant u ne"
- Article 32 : "Interdiction de refu ser des contrats de réassu rance ou de
  rétrocession" → "refu ser", "réassu rance"
- Article 36 : "Processus de contrôle pru dentiel" → "pru dentiel"
- Article 37 : "Exigence de capital su pplémentaire" → "capital su
  pplémentaire"

La liste complète des 201 numéros n'est pas reproduite ici (trop longue) ;
elle est reconstructible en relançant l'analyse sur `data/articles.jsonl`.

**Gravité : bloquant** pour les titres qui sont en réalité tout le corps
(cf. catégorie 3) ; **gênant** pour les titres de longueur normale mais avec
un mot cassé (lisibilité des citations).

---

## 5. Pieds/en-têtes de page dans le corps

**97 / 312 articles** contiennent, en plein milieu de leur texte, un
fragment d'en-tête ou de pied de page du Journal officiel de l'Union
européenne (date de publication, marque de pagination "L 335/xx", ou code
imprimeur du type "R F9002.21.71"). Ces fragments s'insèrent car
`PyPDFLoader` concatène le texte page par page sans retirer les en-têtes/
pieds de page, et un article qui s'étend sur deux pages du PDF hérite du
pied de la première page et de l'en-tête de la seconde, en plein milieu
d'une phrase ou d'une énumération.

Exemples :
- Article 5 : "...est l'assureur. **R F9002.21.71 Journal officiel de
  l'Union européenne 17.12.2009** 3) les activités exercées dan..."
- Article 9 : "...provisions mathématiques; **R F02/533L Journal officiel de
  l'Union européenne L 335/21** 3) les activités exercées dan..."
- Article 13 : "...ou plusieurs autres entreprises du groupe dont elle fait
  partie; **R F9002.21.71 Journal officiel de l'Union européenne
  17.12.2009** 6) «entreprise de réassurance d'un pays tiers»..."
- Article 61 : "...aux sociétés cotées à une bourse de valeurs. **R
  F04/533L Journal officiel de l'Union européenne L 335/41**" (fragment en
  toute fin de corps)

**Gravité : bloquant.** Ces fragments coupent des phrases juridiques en
plein milieu et polluent le texte qui sera embeddé et cité — un modèle
pourrait citer un extrait contenant "R F9002.21.71 Journal officiel..." au
milieu d'une réponse, ou la césure de phrase peut nuire à la qualité de la
recherche sémantique sur ce passage précis.

---

## Résumé — gravité par catégorie

| # | Catégorie | Articles touchés | Gravité |
|---|---|---|---|
| — | **Titre = corps entier (bug titre/corps)** | **142 / 312 (+ 9 partiels)** | **Bloquant** |
| — | **Article 312 : corps = annexes I-VII, titre = vrai corps** | **1 / 312** | **Bloquant** |
| 5 | Fragments d'en-tête/pied de page du Journal officiel en plein corps | 97 / 312 | Bloquant |
| 4 | Titres avec espaces parasites (mots cassés) | 201 / 312 | Bloquant (si titre corrompu) / Gênant (sinon) |
| 1 | Espaces parasites dans les mots (corps) | 310 / 312 (~4 754 occurrences) | Gênant |
| 3 | Articles > 6000 caractères à vérifier manuellement (13, 105, 248, 303) | 4 / 312 | Cosmétique |
| 2 | \xad / \xa0 restants | 0 / 312 | Résolu |
| 2 | Codes de pied de page illisibles ("R F9002.21.71"...) | recoupe la catégorie 5 | Bloquant |
| 3 | Articles < 100 caractères, titres vides | 0 / 312 | Résolu |
