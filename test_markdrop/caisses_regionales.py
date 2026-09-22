# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier contient simplement la liste des 13 Caisses régionales
# Groupama, utilisée par le fichier de correction ci-dessus pour
# reconnaître leurs noms.
# ------------------------------------------------------------------
"""Référentiel des 13 Caisses régionales Groupama (entités actionnaires de
Groupama Assurances Mutuelles), sur le modèle du dictionnaire EIOPA utilisé
pour les QRT (qrt_dictionary.json) : un identifiant canonique -> un libellé
de référence, plus une fonction de correspondance floue pour vérifier les
libellés extraits des tableaux narratifs (pages 10 et 12 du SFCR Groupama).

Contrairement au dictionnaire EIOPA, ce référentiel n'a de sens que pour
les tableaux dont les lignes SONT les 13 caisses (« Certificats
mutualistes », « Délégués »). Sur les autres tableaux narratifs (Filiales,
métiers, pays, marché, titres subordonnés), la plupart des libellés ne
correspondront à AUCUNE caisse — c'est attendu, pas une anomalie : ce
référentiel ne prétend pas couvrir toutes les entités possibles d'un SFCR,
seulement les 13 caisses régionales.

Module pur (aucun argparse, aucun effet de bord à l'import), réutilisable
depuis verify_final.py ou un script de test, comme qrt_checks.py.
"""

import re
import unicodedata

CAISSES_REGIONALES = {
    "ANTILLES_GUYANE": "Antilles Guyane",
    "CENTRE_ATLANTIQUE": "Centre Atlantique",
    "CENTRE_MANCHE": "Centre Manche",
    "GRAND_EST": "Grand Est",
    "LOIRE_BRETAGNE": "Loire Bretagne",
    "MEDITERRANEE": "Méditerranée",
    "NORD_EST": "Nord Est",
    "D_OC": "d'Oc",
    "OCEAN_INDIEN": "Océan Indien",
    "PARIS_VAL_DE_LOIRE": "Paris Val de Loire",
    "RHONE_ALPES_AUVERGNE": "Rhône Alpes Auvergne",
    "MISSO": "Misso",
    "PRODUCTEURS_DE_TABAC": "Producteurs de Tabac",
}

# Mots à ignorer dans un libellé avant comparaison : préfixes organisationnels
# qui varient d'un tableau à l'autre (ex. "Groupama Nord Est" page 10 vs
# "GROUPAMA NORD-EST" page 12 vs "Nord Est" seul) sans faire partie de
# l'identité de la caisse.
STOPWORDS = {"GROUPAMA", "CAISSE"}

# Ligne de total : même motif que verify_final.py::_est_ligne_total (dupliqué
# ici pour garder ce module autonome, sans dépendre d'un fichier qui exécute
# argparse à l'import).
TOTAL_LABEL_RE = re.compile(r"\btotal\b", re.IGNORECASE)


def _strip_accents(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


def normalize_label(label):
    """Normalise un libellé pour comparaison : accents supprimés, majuscules,
    apostrophes supprimées SANS espace (« d'Oc » -> « DOC », pour permettre
    un seul token plutôt que 2 mots trop courts et ambigus), tirets/virgules
    remplacés par des espaces, mots-outils (Groupama/Caisse) retirés,
    espaces multiples réduits. Retourne une liste de tokens."""
    s = _strip_accents(str(label)).upper()
    s = s.replace("'", "").replace("’", "")
    s = re.sub(r"[-,]", " ", s)
    tokens = [t for t in s.split() if t and t not in STOPWORDS]
    return tokens


_CANONICAL_TOKENS = {
    cid: normalize_label(nom.replace("d'Oc", "DOC"))
    for cid, nom in CAISSES_REGIONALES.items()
}


def _contient_sous_sequence_contigue(tokens, sous_tokens):
    n = len(sous_tokens)
    if n == 0 or n > len(tokens):
        return False
    return any(tokens[i:i + n] == sous_tokens for i in range(len(tokens) - n + 1))


def est_ligne_total(label):
    return bool(TOTAL_LABEL_RE.search(str(label)))


def match_caisses(label):
    """Retourne la liste des identifiants de caisses (CAISSES_REGIONALES)
    dont le nom apparaît comme sous-séquence contiguë de tokens dans le
    libellé donné. 0 résultat = aucune correspondance. 2+ résultats =
    correspondance ambiguë (ex. deux libellés fusionnés sur une ligne)."""
    tokens = normalize_label(label)
    if not tokens:
        return []
    return [cid for cid, sous_tokens in _CANONICAL_TOKENS.items()
            if _contient_sous_sequence_contigue(tokens, sous_tokens)]


def check_labels_vs_referentiel(table, page):
    """Vérifie chaque libellé de première colonne d'un tableau contre le
    référentiel des 13 caisses. Ignore les lignes de total (pas une caisse,
    pas une anomalie). Retourne une liste de signalements — un par ligne
    dont le libellé ne correspond à AUCUNE caisse (n_matches == 0) ou à
    PLUSIEURS (n_matches >= 2, fusion suspectée). Ne bloque rien, ne
    corrige rien."""
    signalements = []
    lignes = table.get("lignes", [])
    for i, ligne in enumerate(lignes):
        label = ligne[0] if ligne else ""
        if est_ligne_total(label):
            continue
        matches = match_caisses(label)
        if len(matches) == 1:
            continue
        signalements.append({
            "page": page,
            "table_index": table["index"],
            "ligne_index": i,
            "libelle": label,
            "n_correspondances": len(matches),
            "caisses_correspondantes": [CAISSES_REGIONALES[c] for c in matches],
            "flag": "VÉRIFICATION MANUELLE REQUISE",
            "detail": (f"ligne {i} : libellé '{label}' ne correspond à aucune caisse du référentiel"
                       if not matches else
                       f"ligne {i} : libellé '{label}' correspond à {len(matches)} caisses à la fois "
                       f"({', '.join(CAISSES_REGIONALES[c] for c in matches)}) — fusion suspectée"),
        })
    return signalements
