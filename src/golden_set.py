# Golden set — source de vérité unique (importé par evaluate.py et test.py).
#
# "page" = numéro renvoyé par PyPDFLoader (metadata["page"], 0-indexé),
# donc le même numéro que celui affiché dans les citations de rag.py.
# Pour vérifier dans un lecteur PDF classique (1-indexé) : page affichée = page + 1.
# "norme" = None pour les pièges (rien à trouver, donc pas de source à citer).

GOLDEN = [
    # ══════════════════════════════════════════════════════════════
    # IFRS 17 · 5 questions (déjà validées précédemment)
    # ══════════════════════════════════════════════════════════════
    # p.27 (viewer p.28) : "La marge pour service contractuel (Contractual
    # Service Margin, CSM) est «une composante de l'actif ou du passif pour
    # un groupe de contrats d'assurance...»"
    {"q": "Qu'est-ce que la CSM selon IFRS 17 ?", "a": "TROUVE",
     "m": ["profit", "marge", "margin", "csm", "service contractuel"], "page": 27, "norme": "IFRS 17"},

    # p.29 (viewer p.30) : "Les contrats onéreux sont à grouper avec leurs
    # semblables, séparément des autres contrats..." (traitement) ;
    # définition en p.28 : "Un contrat est dit onéreux à la date de
    # reconnaissance si le «Fulfillment Cash Flows»..."
    {"q": "Comment sont traités les contrats onéreux ?", "a": "TROUVE",
     "m": ["perte", "onéreux"], "page": 29, "norme": "IFRS 17"},

    # p.26 (viewer p.27) : "L'ajustement pour risque (Risk Adjustement,
    # abrégé en RA) est dans une certaine mesure..."
    {"q": "Qu'est-ce que l'ajustement pour risque ?", "a": "TROUVE",
     "m": ["risque"], "page": 26, "norme": "IFRS 17"},

    # p.36 (viewer p.37) : section 1.5 "L'approche par commission variable" —
    # intro de la Variable Fee Approach (VFA).
    {"q": "Qu'est-ce que l'approche par commission variable (VFA) ?", "a": "TROUVE",
     "m": ["commission", "variable"], "page": 36, "norme": "IFRS 17"},

    # p.22 (viewer p.23) : "Le Fulfillment Cash Flows : représente la valeur
    # actuelle des flux futurs de la trésorerie..."
    {"q": "Qu'est-ce que le Fulfillment Cash Flows ?", "a": "TROUVE",
     "m": ["flux", "trésorerie"], "page": 22, "norme": "IFRS 17"},

    # ══════════════════════════════════════════════════════════════
    # SOLVABILITÉ II · 7 questions (formulées à l'oral, pas en
    # recopiant le vocabulaire du texte — testent le retrieval sémantique)
    # ══════════════════════════════════════════════════════════════
    # SCR — p.6 (viewer p.7) recital (62) : "Le capital de solvabilité requis
    # devrait correspondre à un niveau de fonds propres éligibles permettant
    # aux entreprises d'assurance et de réassurance d'absorber des pertes
    # significatives, et devrait donner l'assurance raisonnable aux preneurs
    # et bénéficiaires que les paiements interviendront à leur échéance."
    {"q": "Combien de capital une compagnie d'assurance doit-elle détenir pour pouvoir absorber un choc grave sans mettre en péril les assurés ?",
     "a": "TROUVE", "m": ["capital", "solvabilité", "requis", "pertes"],
     "page": 6, "norme": "Solvabilité II"},

    # MCR — p.5 (viewer p.6) recital : "...un niveau minimum de sécurité en
    # dessous duquel le montant des ressources financières ne devrait pas
    # tomber («minimum de capital requis»)."
    {"q": "En dessous de quel niveau de ressources financières l'autorité de contrôle doit-elle intervenir en urgence pour protéger les assurés ?",
     "a": "TROUVE", "m": ["minimum", "capital", "requis", "ressources"],
     "page": 5, "norme": "Solvabilité II"},

    # Provisions techniques — p.44 (viewer p.45) Art.77 : "La valeur des
    # provisions techniques est égale à la somme de la meilleure estimation
    # et de la marge de risque respectivement décrites aux paragraphes 2 et 3."
    # vrai échec partiel — ne couvre jamais le volet Solvabilité II. Ne pas
    # "réparer" par les mots-clés.
    {"q": "Comment calcule-t-on le montant que l'assureur doit mettre de côté pour couvrir ses engagements futurs envers les assurés ?",
     "a": "TROUVE", "m": ["provisions", "techniques", "meilleure estimation", "marge", "provision"],
     "page": 44, "norme": "Solvabilité II"},

    # Marge de risque — p.45 (viewer p.46) Art.77 §3 : "La marge de risque
    # est calculée de manière à garantir que la valeur des provisions
    # techniques est équivalente au montant [que les entreprises
    # d'assurance] demanderaient pour reprendre et honorer les engagements..."
    {"q": "Pourquoi ajoute-t-on un coussin de prudence au-dessus de la meilleure estimation des flux futurs dans le bilan d'un assureur ?",
     "a": "TROUVE", "m": ["marge", "risque", "coût du capital"],
     "page": 45, "norme": "Solvabilité II"},

    # Fonds propres éligibles — p.49 (viewer p.50) : classification par
    # niveaux ("Les éléments des fonds propres auxiliaires sont classés au
    # niveau 2 lorsqu'ils présentent...") + limites par tier.
    {"q": "Quels éléments de son bilan une compagnie d'assurance peut-elle réellement mobiliser pour couvrir ses exigences réglementaires de capital ?",
     "a": "TROUVE", "m": ["fonds propres", "éligibles", "niveau"],
     "page": 49, "norme": "Solvabilité II"},

    # Formule standard vs modèle interne — p.14 (viewer p.15), sommaire :
    # "Capital de solvabilité requis, calculé à l'aide de la formule standard
    # ou d'un modèle interne — Articles 100 à 102."
    {"q": "Une compagnie d'assurance peut-elle construire son propre outil de calcul du capital réglementaire plutôt que d'utiliser la méthode imposée par défaut à tout le marché ?",
     "a": "TROUVE", "m": ["modèle interne", "formule standard", "approbation"],
     "page": 14, "norme": "Solvabilité II"},

    # ORSA — p.33 (viewer p.34) Art.45 : "chaque entreprise d'assurance et de
    # réassurance procède à une évaluation interne des risques et de la
    # solvabilité. Cette évaluation porte au moins sur les éléments suivants..."
    {"q": "Quelle démarche l'assureur doit-il mener en interne pour vérifier que son profil de risque propre correspond bien à ce que capte le calcul réglementaire standard ?",
     "a": "TROUVE", "m": ["évaluation interne", "risques", "solvabilité"],
     "page": 33, "norme": "Solvabilité II"},

    # ══════════════════════════════════════════════════════════════
    # COMPARATIVES · 3 questions (mobilisent les deux corpus)
    # ══════════════════════════════════════════════════════════════
    # IFRS17 p.27 (CSM) + Solva2 p.45 (marge de risque) : deux notions de
    # "marge" au sens et au calcul très différents (profit futur vs coût du
    # capital pour transférer le risque).
    {"q": "Quelle est la différence entre la marge pour service contractuel d'IFRS 17 et la marge de risque de Solvabilité II ?",
     "a": "TROUVE", "m": ["service contractuel", "marge de risque", "profit", "risque"],
     "page": None, "norme": "IFRS 17 & Solvabilité II"},

    # IFRS17 p.26 (ajustement pour risque + flux) + Solva2 p.44 (meilleure
    # estimation + marge de risque) : les deux référentiels décomposent le
    # passif en (flux futurs actualisés) + (chargement pour risque).
    {"q": "Sous les deux référentiels, comment le passif d'assurance est-il décomposé entre la meilleure estimation des flux futurs et un chargement pour risque ?",
     "a": "TROUVE", "m": ["meilleure estimation", "ajustement pour risque", "marge de risque", "flux de trésorerie"],
     "page": None, "norme": "IFRS 17 & Solvabilité II"},

    # Solva2 p.6 (SCR = exigence de capital) vs IFRS17 p.26 (RA = composante
    # du passif) : deux notions de "risque" qui ne jouent pas le même rôle
    # (capital réglementaire vs élément de valorisation du passif).
    {"q": "Le capital que Solvabilité II impose de détenir (le SCR) joue-t-il le même rôle que l'ajustement pour risque sous IFRS 17 ?",
     "a": "TROUVE", "m": ["capital de solvabilité requis", "ajustement pour risque", "risque"],
     "page": None, "norme": "IFRS 17 & Solvabilité II"},

    # ══════════════════════════════════════════════════════════════
    # PIÈGES · 3 questions existantes (déjà validées)
    # ══════════════════════════════════════════════════════════════
    # hors périmètre — rien à voir avec l'actuariat
    {"q": "Quel est le taux de TVA des croissants ?", "a": "REFUSE",
     "m": None, "page": None, "norme": None},

    # concept inventé — n'existe dans aucune des deux normes
    {"q": "Explique le 'coussin de solvabilité dynamique' d'IFRS 17.", "a": "REFUSE",
     "m": None, "page": None, "norme": None},

    # faux chiffre — aucun taux d'actualisation fixe de 4,5 % dans les textes
    {"q": "Pourquoi le taux d'actualisation est-il fixé à 4,5% ?", "a": "REFUSE",
     "m": None, "page": None, "norme": None},

    # ══════════════════════════════════════════════════════════════
    # PIÈGES · 7 questions supplémentaires (4 modes, formulations variées)
    # ══════════════════════════════════════════════════════════════
    # mauvaise norme — le ratio combiné est une notion d'assurance
    # non-vie/souscription, absente d'IFRS 17 comme de Solvabilité II
    {"q": "Quelle est la formule du ratio combiné selon IFRS 17 ?", "a": "REFUSE",
     "m": None, "page": None, "norme": None},

    # concept inventé — terminologie plausible mais absente des deux corpus
    {"q": "Qu'est-ce que le ratio de couverture dynamique du risque de mortalité sous Solvabilité II ?",
     "a": "REFUSE", "m": None, "page": None, "norme": None},

    # concept inventé — variante formulée différemment
    {"q": "Expliquez le mécanisme de lissage contra-cyclique de la CSM prévu par IFRS 17.",
     "a": "REFUSE", "m": None, "page": None, "norme": None},

    # faux chiffre — le SCR est calibré à 99,5 % (VaR à 1 an), pas 99,9 %
    {"q": "Pourquoi le SCR est-il calibré sur un intervalle de confiance de 99,9 % à horizon 1 an ?",
     "a": "REFUSE", "m": None, "page": None, "norme": None},

    # faux chiffre — la marge de risque est calculée par coût du capital
    # (6 %), pas par un forfait de 10 % des provisions
    {"q": "Le chargement pour risque sous Solvabilité II est-il fixé forfaitairement à 10 % des provisions techniques ?",
     "a": "REFUSE", "m": None, "page": None, "norme": None},

    # mauvaise norme — le MCR est une notion de Solvabilité II, pas d'IFRS 17
    {"q": "Selon quelle méthode IFRS 17 calcule-t-il le minimum de capital requis (MCR) ?",
     "a": "REFUSE", "m": None, "page": None, "norme": None},

    # hors périmètre — fiscalité française, aucun rapport avec les deux normes
    {"q": "Quelles sont les règles de calcul de la taxe sur les conventions d'assurance en France ?",
     "a": "REFUSE", "m": None, "page": None, "norme": None},
]
