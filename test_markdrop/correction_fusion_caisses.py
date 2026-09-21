# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier corrige un défaut précis où deux lignes d'un tableau (le nom
# d'une Caisse régionale et son chiffre) avaient été fusionnées par
# erreur lors de l'extraction.
# ------------------------------------------------------------------
"""Correction ciblée et prudente du motif de fusion de libellés observé sur
le tableau « Délégués » (Décision 019), reproduit à l'identique sur les
documents SFCR Groupama 2024 et 2025 : une ligne à libellé vide adjacente à
une ligne dont le libellé est la concaténation de 2 noms de caisses
canoniques adjacents dans l'ordre de référence (ex. "Groupama Nord Est
Groupama d'Oc").

Module séparé de caisses_regionales.py (référentiel + correspondance
purs) : ceci est une correction ACTIVE, à n'appliquer que si les 2
garde-fous stricts définis avec l'utilisateur sont satisfaits. NON
intégré au pipeline de production tant que non validé explicitement.

Garde-fou 1 — déclenchement scopé (voir confirme_type_13_caisses et
detecter_motif_fusion) : la correction ne s'active que sur un tableau
confirmé "13 caisses + Total" ET où le motif exact (1 ligne vide + 1
ligne fusionnée adjacentes) est détecté sans ambiguïté.

Garde-fou 2 — correction par POSITION dans l'ordre canonique, jamais par
supposition : si le calcul positionnel ne peut pas être établi sans
ambiguïté (essai raté, écart ≠ 2, ou incohérence avec les 2 noms lus dans
le libellé fusionné), la fonction échoue proprement (retourne None) et le
signalement existant (Méthode 1 + Méthode 2) reste inchangé.

Garde-fou 3 — traçabilité : toute correction appliquée est journalisée
avec le détail avant/après. Niveau de confiance explicite selon que les 2
lignes corrigées avaient ou non la même valeur avant correction (risque
d'inversion plus élevé si les valeurs diffèrent — cf. DECISIONS.md).
"""

from caisses_regionales import CAISSES_REGIONALES, est_ligne_total, match_caisses

ORDRE_CANONIQUE = list(CAISSES_REGIONALES.keys())  # ordre fixe, déjà vérifié identique sur les 2 documents
MIN_ENTITES_RECONNUES = 11  # Garde-fou 1(a) : au moins 11/13


def _sous_sequence_croissante(indices):
    return all(indices[i] < indices[i + 1] for i in range(len(indices) - 1))


def confirme_type_13_caisses(table):
    """Garde-fou 1(a). True si au moins MIN_ENTITES_RECONNUES lignes (hors
    Total) correspondent chacune à EXACTEMENT une caisse canonique, ET que
    leurs positions dans l'ordre canonique sont strictement croissantes —
    pas juste présentes en vrac, mais dans l'ordre de référence."""
    lignes = [l for l in table.get("lignes", []) if l and not est_ligne_total(l[0])]
    indices = []
    for ligne in lignes:
        matches = match_caisses(ligne[0])
        if len(matches) == 1:
            indices.append(ORDRE_CANONIQUE.index(matches[0]))
    if len(indices) < MIN_ENTITES_RECONNUES:
        return False
    return _sous_sequence_croissante(indices)


def detecter_motif_fusion(table):
    """Garde-fou 1(b) + Garde-fou 2. Retourne (correction, raison_echec) :
    - (dict, None) si le motif est détecté sans ambiguïté et la correction
      calculable ;
    - (None, None) si le tableau est sain (aucun signal d'anomalie —
      rien à signaler, pas un échec) ;
    - (None, raison) si un signal d'anomalie existe mais ne peut pas être
      résolu sans ambiguïté (échec propre, traçable)."""
    lignes = table.get("lignes", [])
    analyse = []  # (index, type, donnee) — type in {total, vide, aucune_correspondance, unique, fusion}
    for i, ligne in enumerate(lignes):
        label = ligne[0] if ligne else ""
        if est_ligne_total(label):
            analyse.append((i, "total", None))
            continue
        matches = match_caisses(label)
        if len(matches) == 0:
            type_ = "vide" if not str(label).strip() else "aucune_correspondance"
            analyse.append((i, type_, None))
        elif len(matches) == 1:
            analyse.append((i, "unique", matches[0]))
        else:
            analyse.append((i, "fusion", matches))

    lignes_vides = [i for i, t, _ in analyse if t == "vide"]
    lignes_fusion = [i for i, t, _ in analyse if t == "fusion"]
    lignes_sans_correspondance = [i for i, t, _ in analyse if t == "aucune_correspondance"]

    if not lignes_vides and not lignes_fusion and not lignes_sans_correspondance:
        return None, None  # tableau sain : rien à signaler

    if lignes_sans_correspondance:
        return None, (f"ligne(s) non vide(s) sans aucune correspondance à une caisse : "
                       f"{lignes_sans_correspondance} — motif non reconnu, échec propre")

    if len(lignes_vides) != 1 or len(lignes_fusion) != 1:
        return None, (f"motif attendu = exactement 1 ligne vide + 1 ligne fusionnée ; "
                       f"trouvé {len(lignes_vides)} vide(s), {len(lignes_fusion)} fusionnée(s) "
                       "— ambigu, échec propre")

    idx_vide = lignes_vides[0]
    idx_fusion = lignes_fusion[0]
    if abs(idx_vide - idx_fusion) != 1:
        return None, (f"ligne vide (index {idx_vide}) et ligne fusionnée (index {idx_fusion}) "
                       "non adjacentes — échec propre")

    idx_min, idx_max = min(idx_vide, idx_fusion), max(idx_vide, idx_fusion)
    positions_avant = [ORDRE_CANONIQUE.index(cid) for i, t, cid in analyse if t == "unique" and i < idx_min]
    positions_apres = [ORDRE_CANONIQUE.index(cid) for i, t, cid in analyse if t == "unique" and i > idx_max]
    if not positions_avant or not positions_apres:
        return None, "contexte positionnel insuffisant (pas de ligne unique avant ou après) — échec propre"

    k_avant, k_apres = max(positions_avant), min(positions_apres)
    manquants = list(range(k_avant + 1, k_apres))
    if len(manquants) != 2:
        return None, (f"écart positionnel entre la dernière caisse reconnue avant (position "
                       f"canonique {k_avant}) et la première après (position {k_apres}) ne "
                       f"correspond pas à exactement 2 caisses manquantes "
                       f"({len(manquants)} trouvée(s)) — échec propre")

    ids_positionnels = {ORDRE_CANONIQUE[p] for p in manquants}
    ids_fusion = set(next(cid for i, t, cid in analyse if i == idx_fusion))
    if ids_positionnels != ids_fusion:
        return None, (f"caisses attendues par position ({sorted(ids_positionnels)}) différentes "
                       f"des caisses lues dans le libellé fusionné ({sorted(ids_fusion)}) — "
                       "échec propre, pas de correction forcée")

    premiere_pos, seconde_pos = sorted(manquants)
    return {
        "idx_ligne_vide": idx_vide,
        "idx_ligne_fusion": idx_fusion,
        "nom_pour_ligne_vide": CAISSES_REGIONALES[ORDRE_CANONIQUE[premiere_pos]],
        "nom_pour_ligne_fusion": CAISSES_REGIONALES[ORDRE_CANONIQUE[seconde_pos]],
    }, None


def appliquer_correction(table, page, document="?"):
    """Point d'entrée complet. Retourne (table_resultat, log_entry) :
    - table_resultat est une COPIE corrigée si la correction s'applique,
      sinon la table originale (jamais modifiée en place) ;
    - log_entry est None si rien à signaler (hors scope, ou tableau sain),
      ou un dict journalisant soit une correction appliquée (Garde-fou 3),
      soit un échec propre traçable (signal d'anomalie vu mais non résolu)."""
    if not confirme_type_13_caisses(table):
        return table, None  # Garde-fou 1(a) non rempli : hors scope, silencieux

    correction, raison_echec = detecter_motif_fusion(table)
    if correction is None:
        if raison_echec is None:
            return table, None  # tableau sain, rien à signaler
        return table, {
            "document": document, "page": page, "table_index": table.get("index"),
            "statut": "ÉCHEC PROPRE — aucune correction appliquée",
            "raison": raison_echec,
        }

    idx_vide = correction["idx_ligne_vide"]
    idx_fusion = correction["idx_ligne_fusion"]
    ligne_vide_avant = list(table["lignes"][idx_vide])
    ligne_fusion_avant = list(table["lignes"][idx_fusion])

    lignes_corrigees = [list(l) for l in table["lignes"]]
    lignes_corrigees[idx_vide][0] = "Groupama " + correction["nom_pour_ligne_vide"]
    lignes_corrigees[idx_fusion][0] = "Groupama " + correction["nom_pour_ligne_fusion"]

    table_corrigee = dict(table)
    table_corrigee["lignes"] = lignes_corrigees

    valeurs_vide = tuple(ligne_vide_avant[1:])
    valeurs_fusion = tuple(ligne_fusion_avant[1:])
    meme_valeur = valeurs_vide == valeurs_fusion
    confiance = (
        "normale — les 2 lignes avaient la même valeur avant correction, risque d'inversion faible"
        if meme_valeur else
        "RÉDUITE — les 2 lignes avaient des valeurs DIFFÉRENTES avant correction ; l'attribution "
        "reste faite par position (pas par valeur), mais une inversion serait ici silencieuse et "
        "fausserait 2 valeurs réelles — vérification humaine recommandée sur ce cas (cf. "
        "DECISIONS.md, point de vigilance Garde-fou 3)"
    )

    log_entry = {
        "document": document, "page": page, "table_index": table.get("index"),
        "statut": "CORRECTION APPLIQUÉE",
        "ligne_libelle_vide": {"index": idx_vide, "avant": ligne_vide_avant, "apres": lignes_corrigees[idx_vide]},
        "ligne_libelle_fusionne": {"index": idx_fusion, "avant": ligne_fusion_avant, "apres": lignes_corrigees[idx_fusion]},
        "confiance": confiance,
    }
    return table_corrigee, log_entry
