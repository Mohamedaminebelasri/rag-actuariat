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
    libellé accumule les lignes non-numériques consécutives, puis TOUTES
    les lignes 100% numériques qui suivent immédiatement deviennent ses
    valeurs (plusieurs colonnes possibles, ex. tableau à 5 niveaux de
    fonds propres). Décision 073 : sur un tableau large (ex. Covéa
    S.05.01.02, plusieurs colonnes par ligne d'activité), PyMuPDF imprime
    souvent CHAQUE colonne sur sa propre ligne de texte plutôt qu'une
    seule ligne espacée — sans accumulation, seule la 1re colonne était
    gardée et les suivantes (dont la colonne Total, la dernière) étaient
    silencieusement perdues."""
    paires = []
    buffer_label = []
    peut_etendre = False  # True juste après avoir démarré un nouveau (label, valeurs)
    for ligne in texte_page.split("\n"):
        ligne_stripped = ligne.strip()
        if not ligne_stripped:
            continue
        if _est_ligne_valeur(ligne_stripped):
            tokens = [t for t in SPLIT_COLONNES_RE.split(ligne_stripped) if t.strip()]
            try:
                valeurs = [_parser_nombre(t) for t in tokens]
            except ValueError:
                buffer_label = []
                peut_etendre = False
                continue
            if buffer_label:
                label = _normaliser(" ".join(buffer_label))
                paires.append([label, valeurs])
                buffer_label = []
                peut_etendre = True
            elif peut_etendre and paires:
                paires[-1][1].extend(valeurs)
            # sinon : ligne de valeur sans libellé du tout (rare, ex.
            # en-tête de colonnes "Total / Niveau 1...") — ignorée
        else:
            buffer_label.append(ligne_stripped)
            peut_etendre = False
    return [(label, valeurs) for label, valeurs in paires]
    # Décision 079 (tentative abandonnée) : un essai de réattacher un "-"
    # isolé (signe détaché) à la magnitude adjacente a été tenté ici pour
    # BPCE IARD (scr_diversification), puis IMMÉDIATEMENT ANNULÉ — testé
    # sur Covéa, où il a corrompu scr_total (15 058 209 -> -15 058 209,
    # une valeur impossible) : sur S.22.01.22, un "-" adjacent à une
    # magnitude signifie parfois une CELLULE VOISINE VIDE, pas un signe
    # détaché — ambiguïté non résoluble sans connaître la vraie position
    # de colonne, que classifier_lignes() ne suit pas. Régression réelle
    # détectée avant commit, fix annulé conformément à la règle "zéro
    # régression". scr_diversification reste NULL pour BPCE IARD.


def extraire_section(texte_page, debut, fin=None):
    """Retourne le sous-texte compris entre la 1re ligne EXACTEMENT égale
    à `debut` (normalisée) et la 1re ligne égale à `fin` qui la suit (ou
    la fin de page si `fin` est absent/introuvable). Décision 073 : sert
    à restreindre classifier_lignes()/extraire_par_libelle() à UNE SEULE
    section d'une page qui répète les mêmes libellés dans plusieurs
    sections (ex. Covéa S.05.01.02 : "Brut – Assurance directe" apparaît
    identiquement sous "Primes émises", "Primes acquises" ET "Charge des
    sinistres") — sans ça, le 1er match sur la page gagne toujours, donc
    systématiquement la mauvaise section (la 1re, "Primes émises")."""
    debut_norm = _normaliser(debut)
    fin_norm = _normaliser(fin) if fin else None
    lignes = texte_page.split("\n")
    lignes_norm = [_normaliser(l) for l in lignes]
    try:
        i_debut = next(i for i, l in enumerate(lignes_norm) if l == debut_norm)
    except StopIteration:
        return ""
    i_fin = len(lignes)
    if fin_norm:
        for i in range(i_debut + 1, len(lignes)):
            if lignes_norm[i] == fin_norm:
                i_fin = i
                break
    return "\n".join(lignes[i_debut:i_fin])


def extraire_par_libelle(texte_page, labels_candidats, colonne=0, sommer_occurrences=False, capturer=None):
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
                valides = [v[colonne] for v in occurrences if len(v) > colonne]
                total = sum(valides)
                if capturer is not None:
                    for i, v in enumerate(valides, start=1):
                        capturer.append({
                            "code": f"{label_orig} (occurrence {i}/{len(valides)})",
                            "libelle": label_orig, "valeur": v, "page": None,
                        })
                return total, label_orig
            else:
                v = occurrences[0]
                if len(v) > colonne:
                    return v[colonne], label_orig
        except (IndexError, TypeError):
            continue
    return None, None
