# Idée de conception — Réponse directe vs orientation seule, selon la confiance

**Statut : idée de conception, NON implémentée — à intégrer dans la
conception du golden set et du futur moteur RAG**
**Date : 2026-08-18**

---

## Le principe

Deux modes de réponse possibles pour le futur système RAG, à choisir
automatiquement selon la fiabilité de la source :

**Mode A — Réponse directe.** Le système donne le chiffre lui-même, avec
sa source précise (fichier, page, template/section).
Exemple : "Le SCR total est de 6 020 977 k€ (S.23.01.22, page 85,
Groupe Groupama, 31/12/2025)."

**Mode B — Orientation seule.** Le système ne donne PAS le chiffre — il
indique uniquement où le trouver, et laisse l'utilisateur vérifier de ses
yeux sur l'image/page source.
Exemple : "La réponse se trouve dans le tableau S.02.01.02 (Bilan),
page 78, ligne R0500."

## Pourquoi ce n'est pas un choix binaire pour tout le système

Le mode B est quasiment sans risque d'erreur (le système ne prétend rien,
il oriente juste), mais plus lent pour l'utilisateur et incapable de
calculs/comparaisons ("compare le SCR entre 2024 et 2025"). Le mode A est
plus utile mais hérite du risque d'erreur d'extraction déjà documenté
(décalage de colonne, hallucination de code, omission silencieuse...).

## La règle de décision proposée : router selon la confiance déjà mesurée

On a déjà, pour chaque élément du corpus, des signaux de confiance
construits pendant ce projet — pas besoin d'en inventer de nouveaux :

| Signal disponible | Confiance | Mode recommandé |
|---|---|---|
| Texte natif du PDF (pas de VLM), complétude 100% | Haute | **Mode A** — réponse directe + source |
| Extraction VLM (Gemini) + complétude 100% + aucun signalement (décalage colonne, code inattendu) | Moyenne-haute | **Mode A** avec mention "extrait automatiquement" |
| Extraction VLM avec au moins un signalement (décalage, code manquant, omission détectée) | Basse | **Mode B** — orientation uniquement, jamais le chiffre lui-même |
| Résolution de sous-feuillet non fiable (cas S.05.02.04 documenté) | Basse | **Mode B** obligatoire |
| Entité/année non vérifiées (heuristique testée sur 1 seul document) | Basse | **Mode B** pour toute métadonnée entité/année tant que non validée sur un 2ème document |

## Ce que ça change pour le golden set (à faire)

Chaque question du golden set doit maintenant prévoir DEUX vérités
attendues, pas une seule :
1. La réponse attendue (le chiffre, si applicable)
2. Le mode attendu (A ou B) — un système qui répond en Mode A sur une
   source à confiance basse serait un échec du golden set MÊME SI le
   chiffre donné est correct par coïncidence (sur-confiance dangereuse,
   pas juste une erreur de valeur)

## Prochaine étape (pas commencée)

Décider et documenter le seuil exact déclenchant Mode A vs Mode B (ex:
"0 signalement = A, 1+ signalement = B" est un point de départ simple,
à affiner une fois qu'on aura plus de données réelles sur combien de
signalements sont de vrais faux positifs vs vrais problèmes).
