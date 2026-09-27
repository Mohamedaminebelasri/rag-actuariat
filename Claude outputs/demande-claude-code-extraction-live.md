# Demande pour ce soir : extraction KPI en direct sur un PDF unique, arbitraire

Contexte : demain, le fondateur va uploader un PDF SFCR jamais vu par le système,
via un nouvel onglet "Ajouter un PDF" (déjà construit côté frontend, PR au commit
f90e74f). Le frontend écrit déjà le PDF confirmé dans data/. Il manque le pont vers
le pipeline d'extraction pour que ce PDF précis soit traité automatiquement.

## Ce qu'il faut construire

Un script (ex. extraire_un_pdf.py), appelable en ligne de commande avec :
  python extraire_un_pdf.py --pdf "data/<nom_confirme>.pdf" --societe "<nom fourni par le fondateur>" --annee <annee fournie> --job-id <id>

en réutilisant la logique déjà existante et testée d'extract_kpis.py (pas de
nouvelle méthode d'extraction — même pipeline Docling + cascade Gemini/Mistral/Groq).

## Contrat d'échange (pour que le frontend puisse suivre la progression sans bloquer)

Le script doit écrire, au fur et à mesure, un fichier de statut JSON à :
  jobs/<job-id>.json

avec cette forme (à mettre à jour à chaque étape, pas seulement à la fin) :
  {
    "statut": "en_cours" | "termine" | "erreur",
    "etape": "extraction_pdf" | "appel_modele" | "validation" | "ecriture_db",
    "message": "texte court, ex. 'Lecture du PDF (Docling)...'",
    "societe": "<nom>",
    "annee": <int ou null>,
    "kpis": [ { "kpi_name": "...", "value": ..., "unit": "...", "category": "...",
                "source_page": <int>, "source_chapter": "...", "validated": false } ],
    "erreur": "texte si statut = erreur, sinon null"
  }

- "validated": false par défaut pour tout KPI issu de cette extraction à chaud
  (pas de checkpoint humain avant demain matin) — le frontend affichera un badge
  "à vérifier" tant que ce n'est pas passé à true.
- Écrire aussi les résultats définitifs dans kpis.db (table companies + kpis),
  avec un company_id nouveau, exactement comme pour les 34 sociétés existantes,
  pour que "Base de données" les affiche après un rechargement normal.
- Le script doit tourner en arrière-plan (le process Node le lance en détaché)
  et ne doit jamais faire planter le serveur Next.js s'il échoue : toujours
  écrire "statut": "erreur" avec un message clair plutôt que de crasher sans trace.

## Ce que je fais de mon côté (frontend, ce soir)

- J'ajoute au formulaire de confirmation du PDF deux champs : nom de la société
  et année (remplis par le fondateur avant de lancer l'extraction) — pour éviter
  de faire deviner ces infos au script sur un PDF inconnu.
- J'ajoute une route API qui lance ce script en arrière-plan et une autre qui lit
  jobs/<id>.json pour afficher la progression en direct.
- J'ajoute un badge "Nouveau" sur la société dans Base de données et Documents,
  et un badge "extraction automatique — à vérifier" sur chaque KPI tant que
  "validated" n'est pas passé à true dans kpis.db.

Si le nom du script, l'emplacement du dossier jobs/, ou la forme exacte des
colonnes kpis.db doivent être différents, dis-le et j'ajuste mon côté en
conséquence — l'essentiel est qu'on soit d'accord sur ce contrat avant de coder
chacun de notre côté ce soir.

## Point important ajouté après coup

Le frontend affiche "Base de données" à partir d'un export JSON statique
(frontend/src/data/donnees-extraites.json), pas d'une connexion live à kpis.db
— c'est le fonctionnement déjà en place pour les 34 sociétés. Pour que la
nouvelle société apparaisse dans l'interface sans étape manuelle en plus
demain matin, merci de faire relancer automatiquement
export_kpis_for_frontend.py (ou l'équivalent) par le script d'extraction une
fois l'écriture dans kpis.db terminée avec succès — même mécanisme que
d'habitude, juste déclenché tout seul à la fin plutôt qu'à la main.
