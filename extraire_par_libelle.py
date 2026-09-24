# -*- coding: utf-8 -*-
"""extraire_par_libelle.py — Extraction par libellé français, fallback
pour documents SANS code R0xxx/C0xxx (Phase 3.9, Décision 064 : MAIF,
Covéa — vérifié visuellement, vrais tableaux QRT complets mais
entièrement en libellé français).

Structure de page observée (vérifiée sur MAIF p.121-122 et Covéa
p.84-98, texte brut PyMuPDF, pas devinée) : un libellé (parfois replié
sur 2-3 lignes) est suivi d'une ligne de VALEUR(S) — un ou plusieurs
nombres séparés par de grands espaces (colonnes). Ex. :
    "Capital de solvabilité requis"
    "       2 344 989   "
Le classement LABEL vs VALEUR se fait en testant si la ligne, une fois
tokenisée par espaces multiples, ne contient QUE des tokens numériques
("-", "2 344 989", "227%", etc.).
"""

import re
import unicodedata

NOMBRE_TOKEN_RE = re.compile(r"^-?[\d\s ]*\d(?:,\d+)?%?$|^-$")
SPLIT_COLONNES_RE = re.compile(r"\s{2,}")


def _normaliser(s):
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.strip().lower())


def _est_ligne_valeur(ligne):
    tokens = [t for t in SPLIT_COLONNES_RE.split(ligne.strip()) if t.strip()]
    if not tokens:
        return False
    return all(NOMBRE_TOKEN_RE.match(t.strip()) for t in tokens)


def _parser_nombre(token):
    """'2 344 989' -> 2344989.0 ; '-' -> 0.0 ; '227%' -> 2.27 (même
    convention "décimal brut" que _vers_float dans extract_kpis.py, le
    code appelant multiplie par 100 pour les KPIs ratio_scr/ratio_mcr)."""
    t = token.strip().replace(" ", " ").replace(" ", "").replace(",", ".")
    if t == "-":
        return 0.0
    if t.endswith("%"):
        return float(t[:-1]) / 100
    return float(t)


def classifier_lignes(texte_page):
    """Retourne une liste de (libellé_normalisé, [valeurs_float]) — le
    libellé accumule les lignes non-numériques consécutives, la 1re
    ligne 100% numérique qui suit devient sa valeur (plusieurs colonnes
    possibles, ex. tableau à 5 niveaux de fonds propres)."""
    paires = []
    buffer_label = []
    for ligne in texte_page.split("\n"):
        ligne_stripped = ligne.strip()
        if not ligne_stripped:
            continue
        if _est_ligne_valeur(ligne_stripped):
            if buffer_label:
                label = _normaliser(" ".join(buffer_label))
                tokens = [t for t in SPLIT_COLONNES_RE.split(ligne_stripped) if t.strip()]
                try:
                    valeurs = [_parser_nombre(t) for t in tokens]
                except ValueError:
                    buffer_label = []
                    continue
                paires.append((label, valeurs))
                buffer_label = []
            # une ligne de valeur sans libellé accumulé (rare, ex. en-tête
            # de colonnes "Total / Niveau 1..." sans vrai label devant) —
            # ignorée, pas rattachable à un KPI
        else:
            buffer_label.append(ligne_stripped)
    return paires


def extraire_par_libelle(texte_page, labels_candidats, colonne=0, sommer_occurrences=False):
    """labels_candidats : liste de libellés (str) à chercher, dans l'ordre
    de priorité — le premier qui matche EXACTEMENT (après normalisation,
    jamais par sous-chaîne, cf. Décision 057) une ligne du texte de page
    est utilisé. `colonne` : index de la valeur à prendre si la ligne a
    plusieurs colonnes (0 = la 1re, généralement "Total"). Si
    `sommer_occurrences` : somme TOUTES les occurrences du label trouvé
    (nécessaire pour best_estimate/marge_risque, répétés par segment).
    Retourne (valeur, libelle_utilise) ou (None, None)."""
    paires = classifier_lignes(texte_page)
    labels_norm = [_normaliser(l) for l in labels_candidats]

    for label_orig, label_norm in zip(labels_candidats, labels_norm):
        # PRIORITÉ à l'égalité stricte — le suffixe (avec frontière
        # d'espace) n'est qu'un REPLI si aucune égalité stricte n'existe
        # sur la page. Bug réel trouvé et corrigé (Décision 064) : sans
        # cette priorité, un match par suffixe ("...pour couvrir LE
        # CAPITAL DE SOLVABILITÉ REQUIS", une ligne différente et non
        # voulue) pouvait passer AVANT le vrai match exact s'il apparaît
        # plus tôt dans la page (cas réel MAIF : scr_total et mcr faux,
        # tous deux récupérés depuis la mauvaise ligne). Le suffixe reste
        # nécessaire pour Covéa (en-tête de section collé sans ligne de
        # valeur intermédiaire, ex. "Risque opérationnel"), mais seulement
        # quand aucune ligne ne matche exactement.
        occurrences = [valeurs for lbl, valeurs in paires if lbl == label_norm]
        if not occurrences:
            occurrences = [
                valeurs for lbl, valeurs in paires
                if lbl.endswith(" " + label_norm)
            ]
        if not occurrences:
            continue
        try:
            if sommer_occurrences:
                total = sum(v[colonne] for v in occurrences if len(v) > colonne)
                return total, label_orig
            else:
                v = occurrences[0]
                if len(v) > colonne:
                    return v[colonne], label_orig
        except (IndexError, TypeError):
            continue
    return None, None
