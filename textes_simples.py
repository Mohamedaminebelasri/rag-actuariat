# -*- coding: utf-8 -*-
"""textes_simples.py — Textes de source en français simple (Décision 161).

Les extractions écrivent dans `kpis.source_chapter` une trace technique
(nom du fichier, codes de lignes et de colonnes des tableaux officiels,
numéros de décision) et dans `kpi_composants.composant_label` des libellés
avec codes de ligne et césures du PDF. Ces textes sont affichés tels quels
(Base de données, Analyse, export CSV). Ce module :

- `source_simple()` : réécrit une trace technique en français simple, par
  règles (même sens, mêmes réserves, rien d'inventé). Un texte inconnu lève
  une erreur plutôt que d'être réécrit au hasard.
- `nettoyer_libelle()` : retire codes de ligne, césures et identifiants des
  libellés de lignes de détail.
- `appliquer(conn)` : appelé en dernier par corrections_comparabilite.py,
  donc rejoué après chaque ré-extraction. La trace technique est conservée
  dans `kpis.source_chapter_technique` (non exportée). Idempotent : un
  texte déjà simple n'est plus touché.
- `contient_jargon()` : la recherche automatique utilisée partout (texte
  à réécrire, contrôle final, tests).
"""
import re

# --- Recherche du jargon --------------------------------------------------
_IDENTIFIANT = re.compile(r"\b[a-z0-9]+(?:_[a-z0-9]+)+\b")
_INTERDITS = (
    re.compile(r"\bNULL\b"),
    re.compile(r"\bD[ée]cisions?\s+\d{2,3}"),
    re.compile(r"\b[RrCc]\d{4}\b"),
    re.compile(r"\b[\w-]+\.(?:py|pdf|json|png|db|md)\b"),
    re.compile(r"picture_|pixel|parsable|parseur|regex|mapping|Own Funds|\(EN\)", re.I),
)
_QRT = re.compile(r"\bS\.\d{2}\.\d{2}(?:\.\d{2})*\b")
# Une référence à un tableau officiel est admise si elle est expliquée :
# « tableau officiel S.23.01 (fonds propres) », « … (état S.22.01) ».
_QRT_EXPLIQUE = re.compile(r"(?:tableau officiel|état) S\.\d{2}\.\d{2}\b", re.I)


def contient_jargon(texte):
    """Vrai si le texte contient un identifiant interne, NULL, un numéro de
    décision, un code de ligne / colonne, un nom de fichier, un code de
    tableau non expliqué ou un numéro de chapitre seul (« D.2 »)."""
    if not texte:
        return False
    if _IDENTIFIANT.search(texte) or any(rx.search(texte) for rx in _INTERDITS):
        return True
    if re.fullmatch(r"[A-E]\.\d", texte.strip()):
        return True
    return len(_QRT.findall(texte)) > len(_QRT_EXPLIQUE.findall(texte))


# --- Vocabulaire ----------------------------------------------------------
TABLEAUX = {
    "02.01": "bilan prudentiel",
    "05.01": "primes, sinistres et dépenses par ligne d'activité",
    "12.01": "provisions techniques vie et santé",
    "17.01": "provisions techniques non-vie",
    "22.01": "impact des mesures de long terme",
    "23.01": "fonds propres",
    "25.01": "SCR en formule standard",
    "25.05": "SCR calculé par le modèle interne",
    "28.01": "MCR",
}
CHAPITRES = {
    "A.2": "résultats de souscription",
    "D.2": "provisions techniques",
    "E.1": "fonds propres",
    "E.2": "capital de solvabilité requis et minimum de capital requis",
}
# Lignes « meilleure estimation » / « marge de risque » du bilan prudentiel.
LIGNES_BILAN = {
    "R0540": "non-vie hors santé", "R0550": "non-vie hors santé",
    "R0580": "santé similaire à la non-vie", "R0590": "santé similaire à la non-vie",
    "R0630": "santé similaire à la vie", "R0640": "santé similaire à la vie",
    "R0670": "vie hors santé et unités de compte", "R0680": "vie hors santé et unités de compte",
    "R0710": "unités de compte", "R0720": "unités de compte",
}

# Modèles internes (corrections_comparabilite.MODELES_INTERNES, GROUPAMA) :
# une réécriture par société de la base technique du jeu SCR cohérent.
MODELES_INTERNES = {
    "AXA France Vie": (
        "Modèle interne — tableau officiel S.25.05 (SCR calculé par le modèle interne), annexe page 10 : "
        "montants par risque après diversification à l'intérieur de chaque risque ; la diversification "
        "entre risques est le total moins la somme des risques (−1 728 M€, comme dans le rapport page 100) ; "
        "le risque vie inclut la santé, les deux ne sont pas séparables."),
    "AXA France IARD": (
        "Modèle interne — tableau officiel S.25.05 (SCR calculé par le modèle interne), annexe page 9 : "
        "montants par risque après diversification à l'intérieur de chaque risque ; la diversification "
        "entre risques est le total moins la somme des risques (−912 M€, comme dans le rapport page 89) ; "
        "le risque vie inclut la santé."),
    "Generali Vie": (
        "Modèle interne — rapport, chapitre E.2 (capital de solvabilité requis et minimum de capital requis), "
        "graphique du SCR par risque page 79 : montants avant diversification entre risques et avant impôt ; "
        "les autres ajustements du modèle (+88 et +735 M€) et l'effet des impôts (−552 M€) expliquent l'écart "
        "avec le SCR ; le risque vie (« Souscription ») inclut la santé."),
    "Generali IARD": (
        "Modèle interne — rapport, chapitre E.2 (capital de solvabilité requis et minimum de capital requis), "
        "graphique du SCR par risque page 72, lu sur une image : montants avant diversification entre risques "
        "et avant impôt ; les autres ajustements du modèle (+16 et +190 M€) et l'effet des impôts (−67 M€) "
        "expliquent l'écart avec le SCR."),
    "Allianz Vie": (
        "Modèle interne — rapport, tableau 25 page 69 : SCR par catégorie du modèle interne d'Allianz "
        "(diversification à l'intérieur de chaque catégorie incluse) ; le risque vie regroupe la souscription "
        "et le risque commercial (rachats, frais), rangés en souscription vie dans la formule standard ; le "
        "coussin de capital du modèle (+109 M€), les fonds cantonnés (+20 M€) et les impôts différés (−51 M€) "
        "expliquent l'écart avec le SCR."),
}
GROUPAMA = ("Rapport, chapitre E.2 (capital de solvabilité requis et minimum de capital requis), schéma du "
            "SCR par module page 74 : chaque module est net de la diversification entre ses sous-risques.")


def _tableau(code):
    """« Tableau officiel S.23.01 (fonds propres du groupe) » depuis un code complet."""
    m = re.match(r"S\.(\d{2}\.\d{2})(?:\.(\d{2}))?", code)
    nom = TABLEAUX[m.group(1)]
    groupe = m.group(2) == "22"
    return f"Tableau officiel S.{m.group(1)} ({nom}{' du groupe' if groupe else ''})"


def _chapitre(code):
    return f"Rapport, chapitre {code} ({CHAPITRES[code]})"


def _precisions(t):
    """Précisions utiles à l'utilisateur, tirées de la trace technique."""
    p = []
    if "Document combiné 'Aéma" in t:
        p.append("rapport unique du groupe Aéma, partie consacrée à la société")
    if "Document combiné 'AG2R" in t:
        p.append("rapport commun du groupe AG2R La Mondiale, partie consacrée à la société")
    if "rendu image" in t:
        p.append("lu sur une page image")
    # Bilan prudentiel : lignes additionnées.
    codes = [c for c in re.findall(r"R0\d{3}", t) if c in LIGNES_BILAN]
    if "S.02.01" in t:
        noms = list(dict.fromkeys(LIGNES_BILAN[c] for c in codes))
        if codes and " seul" in t:
            p.append(f"une seule ligne : {noms[0]}")
        elif codes:
            p.append(f"somme des lignes{' non nulles' if 'non-nulles' in t else ''} : {', '.join(noms)}")
        elif m := re.search(r"somme (\d+) (?:segments|lignes)", t):
            p.append(f"somme des {m.group(1)} lignes du tableau")
        elif "somme" in t:
            p.append("somme des lignes du tableau")
    # Primes et sinistres par ligne d'activité.
    if "S.05.01" in t:
        nonvie = re.search(r"R0[23][1-3]0|non-vie", t)
        vie = re.search(r"R1[56]10|S\.05\.01\.02\.02|\.01\+\.02|vie,|vie seule|\(vie", t)
        if "non-vie, seule activité" in t:
            p.append("activité non-vie seule")
        elif re.search(r"vie seule|vie, seule activité", t):
            p.append("activité vie seule")
        elif nonvie and vie:
            p.append("lignes non-vie et vie additionnées")
        if m := re.search(r"(\d+) lignes trouvées", t):
            p.append(f"{m.group(1)} lignes lues")
        if "rentes de sinistres non-vie converties" in t:
            p.append("y compris les rentes issues de sinistres non-vie")
        if "colonne Total lue manuellement" in t:
            p.append("colonne Total lue à la main")
    if "NÉGATIF, CONFIRMÉ" in t:
        p.append("montant négatif vérifié sur la page image 511 : la part des réassureurs est la même, la charge "
                 "nette est nulle (ligne entièrement réassurée)")
    if "imprimé « - »" in t or "Niveau 3 vide" in t:
        p.append("case vide ou « - » dans le tableau (zéro)")
    if "imprimé « 0 »" in t:
        p.append("imprimé « 0 » dans le tableau")
    pages = re.findall(r"(?:confirmé p\.|et p\.)(\d+)", t)
    if pages:
        p.append("recoupé avec la page " + pages[0] if len(pages) == 1
                 else "recoupé avec les pages " + " et ".join(pages))
    if "plancher absolu" in t:
        p.append("MCR fixé au plancher absolu réglementaire (supérieur au SCR), normal pour une petite structure")
    if re.search(r"somme des 4 tiers = total|= total \d", t):
        p.append("la somme des niveaux redonne le total publié")
    if "fonds propres auxiliaires (rappel de cotisations)" in t:
        p.append("niveau 2 : fonds propres auxiliaires (rappel de cotisations)")
    if "Σ modules" in t:
        p.append("la somme des modules et de la diversification redonne le SCR de base")
    if "Simplification life catastrophe" in t:
        p.append("calcul simplifié du risque catastrophe vie")
    if "autres secteurs financiers" in t:
        p.append("y compris les autres secteurs financiers")
    if m := re.search(r"signe d'une ligne corrigé p\.(\d+)", t):
        p.append(f"signe d'une ligne corrigé d'après la page {m.group(1)}")
    return p


def source_simple(societe, kpi, t):
    """Trace technique -> texte simple. Lève ValueError sur un texte inconnu."""
    if t.startswith("Jeu SCR cohérent modèle interne"):
        return MODELES_INTERNES[societe]
    if t.startswith("NULL : inclus dans un autre poste"):
        return "Pas de montant séparé : inclus dans un autre risque (modèle interne)."
    if t.startswith("Schéma E.2.1 p.74"):
        return GROUPAMA
    if t.startswith("valeur imprimée '0'"):
        return "Valeur imprimée « 0 » (assureur vie : pas de risque non-vie)."
    if "best_estimate + marge_risque" in t:
        lieu = "Calculé : best estimate + marge de risque"
    elif m := re.match(r"([A-E]\.\d)(?: —|$)", t):
        lieu = _chapitre(m.group(1))
    elif m := _QRT.search(t):
        lieu = _tableau(m.group(0))
    else:
        raise ValueError(f"Texte de source non reconnu ({societe} / {kpi}) : {t!r}")
    precisions = _precisions(t)
    simple = lieu + (" — " + " ; ".join(precisions) if precisions else "")
    if contient_jargon(simple):
        raise ValueError(f"Réécriture encore technique ({societe} / {kpi}) : {simple!r}")
    return simple


# --- Libellés des lignes de détail ----------------------------------------
def nettoyer_libelle(label):
    if not label:
        return label
    s = re.sub(r"\s*\[composante vie \(~([\d ]+) K€, p\.(\d+)\) exclue[^\]]*\]",
               r" [sans la part vie, environ \1 K€ page \2, non lue : tableau illisible]", label)
    s = re.sub(r"(\w)- (\w)", r"\1\2", s)  # césures du PDF (« reassu- rance »)
    s = s.replace("reassurance", "réassurance").replace("acceptee", "acceptée")
    s = re.sub(r"\s*\(?\b[Rr]\d{4}\)?\s*$", "", s)
    s = s.replace("(best_estimate)", "(best estimate)").replace(" (marge_risque)", "")
    s = re.sub(r"^BE ", "Best estimate ", s)
    s = re.sub(r"^RM ", "Marge de risque ", s)
    s = s.replace("UC et indexés", "unités de compte et indexés").replace("santé/UC/indexés", "santé et unités de compte")
    return s


# --- Application (rejouée par corrections_comparabilite.py) ---------------
def appliquer(conn, kpis_extraits, classe_composant, annee):
    """Réécrit source_chapter (trace gardée dans source_chapter_technique)
    et les libellés de lignes des KPIs extraits. `classe_composant` :
    comparabilite._classe_composant, pour vérifier qu'aucun nettoyage de
    libellé ne change le classement vie / non-vie d'une ligne (sinon le
    S/P non-vie bougerait)."""
    if "source_chapter_technique" not in {r[1] for r in conn.execute("PRAGMA table_info(kpis)")}:
        conn.execute("ALTER TABLE kpis ADD COLUMN source_chapter_technique TEXT")
    marques = ",".join("?" * len(kpis_extraits))
    n_sources = 0
    for rowid, societe, kpi, chapitre in conn.execute(
            f"""SELECT k.rowid, c.name, k.kpi_name, k.source_chapter FROM kpis k JOIN companies c ON c.id = k.company_id
                WHERE k.year=? AND k.kpi_name IN ({marques}) AND k.source_chapter IS NOT NULL""",
            (annee, *kpis_extraits)).fetchall():
        if not contient_jargon(chapitre):
            continue
        conn.execute("UPDATE kpis SET source_chapter=?, source_chapter_technique=? WHERE rowid=?",
                     (source_simple(societe, kpi, chapitre), chapitre, rowid))
        n_sources += 1
    n_libelles = 0
    for rowid, code, label in conn.execute(
            f"""SELECT rowid, composant_code_qrt, composant_label FROM kpi_composants
                WHERE year=? AND kpi_name IN ({marques})""", (annee, *kpis_extraits)).fetchall():
        propre = nettoyer_libelle(label)
        if propre == label:
            continue
        if classe_composant(code, label) != classe_composant(code, propre):
            raise SystemExit(f"Nettoyage du libellé {label!r} : classement vie / non-vie modifié — à revoir")
        conn.execute("UPDATE kpi_composants SET composant_label=? WHERE rowid=?", (propre, rowid))
        n_libelles += 1
    print(f"  {n_sources} sources et {n_libelles} libellés de lignes réécrits en français simple")
