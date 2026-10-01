# -*- coding: utf-8 -*-
"""corriger_source_page.py — TÂCHE 1 (nuit 28/09/2026) : retrouve la
page PHYSIQUE réelle où chaque valeur de KPI apparaît dans son PDF
source, corrige `source_page` en conséquence.

CAUSE RACINE diagnostiquée (trace des scripts, cf. NIGHT_LOG.md) :
`_page_source(corpus, template_id)` — utilisée par extraire_un_pdf.py
et la plupart des scripts extract_kpis_*.py/ag2r_entites.py — retourne
la PREMIÈRE page où le TEMPLATE QRT commence dans le corpus, pas la
page où la LIGNE spécifique du KPI est réellement imprimée. Un
template QRT s'étend souvent sur 2+ pages physiques (ex. S.23.01 pour
Allianz Vie : page physique 88 = "fonds propres de base" (R0290),
page 89 = "fonds propres éligibles" (R0540, le KPI recherché) — même
template, pages différentes, confirmé par lecture directe du PDF).
`extract_kpis.py` (Groupama) a un mécanisme différent : pages codées
en dur. `extract_kpis_cnp.py` : jamais renseigné (None partout).

APPROCHE : recherche RÉTROACTIVE et GÉNÉRIQUE, pas une correction par
script (trop risqué/long sur 15+ scripts différents à ré-auditer un
par un) — recherche le texte natif de CHAQUE page physique du PDF
source pour la valeur BRUTE (raw_value pour M€, value pour pct) et
prend la page où elle apparaît EFFECTIVEMENT. Jamais une page devinée :
0 ou ≥2 pages candidates -> source_page laissé INCHANGÉ, journalisé
comme "ambigu"/"introuvable" pour revue humaine plutôt qu'un mauvais
pari.

MISE À JOUR (Décision 115, nuit 30/09) : couvre désormais AUSSI les 13
entités Aéma — leur annexe QRT (pages 439-621) est bien 100% image,
MAIS le chapitre narratif qui la précède (pages 1-438) a un texte natif
riche, avec une section dédiée par entité reprenant la plupart des
KPIs en clair (cf. AEMA_BORNES ci-dessous). Les 9 entités AG2R voient
leur recherche élargie au chapitre narratif équivalent (pages 1 à la
fin de leur bloc QRT), qui contient des sommes/totaux (ex.
best_estimate) absents de l'annexe QRT elle-même.

    python corriger_source_page.py            # applique les corrections
    python corriger_source_page.py --dry-run   # affiche sans écrire
"""
import argparse
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "kpis.db"
DATA_DIR = BASE_DIR / "data"

sys.path.insert(0, str(BASE_DIR))
from kpi_qrt_mapping import KPI_QRT_MAPPING  # noqa: E402

# Décision 115 — libellés français tels que lus DIRECTEMENT dans le
# chapitre narratif de 2 PDF réels avant d'écrire cette liste (pages
# 66/278/283/377 Aéma, 76-77 AG2R) — sert de désambiguïsation quand
# plusieurs pages contiennent la même valeur mais SANS code de ligne QRT à
# proximité (le chapitre narratif n'a pas de code R####, juste du texte).
# UNIQUEMENT les KPIs où le libellé observé est assez spécifique pour ne
# pas matcher autre chose par hasard — ex. "fonds_propres_t1_r" est
# délibérément ABSENT : son "libellé" serait juste "Niveau 1 – restreint",
# un en-tête de COLONNE partagé par toutes les lignes du tableau, qui
# n'aide pas à distinguer QUELLE ligne.
LABELS_NARRATIFS = {
    "best_estimate": ["Meilleure estimation"],
    "marge_risque": ["Marge de risque"],
    "provisions_techniques": ["Provisions techniques SII", "Total provisions techniques"],
    "scr_total": ["SCR net total", "SCR groupe complet", "SCR diversifié"],
    "scr_marche": ["SCR marché"],
    "scr_contrepartie": ["SCR contrepartie"],
    "scr_souscription_vie": ["SCR souscription vie"],
    "scr_souscription_sante": ["SCR souscription santé"],
    "scr_souscription_nonvie": ["SCR souscription non-vie"],
    "scr_operationnel": ["SCR opérationnel"],
    "scr_diversification": ["Diversification entre modules"],
    "charge_sinistres": ["Charge des sinistres", "Charge de sinistres"],
    "fonds_propres_eligibles": ["fonds propres éligibles", "fonds propres Solvabilité II disponibles"],
}


def codes_ligne_pour(kpi_name):
    """Tous les codes de ligne (R####) connus pour ce KPI, toutes
    variantes confondues (KPI_QRT_MAPPING, déjà vérifié/utilisé par
    l'extraction réelle) — sert de signal de désambiguïsation quand une
    valeur apparaît sur plusieurs pages (ex. mention narrative en plus
    de la ligne QRT réelle) : jamais un code inventé, uniquement ceux
    déjà déclarés dans le mapping."""
    codes = set()
    for variante in KPI_QRT_MAPPING.get(kpi_name, []):
        row = variante.get("row")
        if isinstance(row, list):
            codes.update(row)
        elif row:
            codes.add(row)
    return codes

# Copié depuis frontend/src/lib/pdf-par-societe.ts (généré 2026-09-27
# depuis kpis.db) — lu comme référence, pas modifié depuis ce script.
PDF_PAR_SOCIETE = {
    "AG.Mut": "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
    "AG2R Prevoyance": "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
    "Abeille Epargne Retraite": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Abeille IARD Sante": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Abeille Vie": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Aema Groupe": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Aesio Mutuelle": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Allianz Vie": "Rapport_de_solvabilité_Allianz_Vie_2025.pdf",
    "Arpege Prevoyance": "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
    "CNP Assurances": "sfcr_cnp_assurances_2025.pdf",
    "Cardif Assurance Vie": "Cardif-Assurance-Vie-–-Annexes-2025.pdf",
    "Cardif Assurances Risques Divers": "cardif-assurances-risques-divers-–-annexes-2025.pdf",
    "Covéa": "sfcr_covea_2025.pdf",
    "Crédit Agricole Assurances": "Groupe-Credit-Agricole-Assurances-–-SFCR-2025.pdf",
    "Groupama": "SFCR_2025_Groupe-Groupama.pdf",
    "La Mondiale": "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
    "La Mondiale Europartner": "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
    "La Mondiale Partenaire": "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
    "MACIF SAM": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "MACSF prévoyance": "RAPPORT_SFCR_MACSF_prevoyance_2025.pdf",
    "MAIF": "rapport-solvabilite-maif-2025.pdf",
    "MGEN": "MGEN_SFCR_2025.pdf",
    "MMJ": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "MNPAF": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Macif Sante Prevoyance": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Macif Vie": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Macifilia": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Nuoma": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "Predica": "PREDICA-–-SFCR-2025.pdf",
    "Prima": "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
    "SGAM AG2R LA MONDIALE": "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
    "Sogécap": "Rapport_de_solvabilite_2025_Sogécap_01.pdf",
    "Themis": "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "VIASANTE Mutuelle": "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
}

# Décision 115 (nuit 30/09) — CORRECTIF DU CORRECTIF : la nuit du 28/09,
# les 13 entités Aéma étaient entièrement SKIPPÉES ici en les croyant
# "100% image, aucun texte natif" — vrai pour l'annexe QRT (pages 439-621)
# mais FAUX pour le chapitre narratif qui la précède (pages 1-438) : CHAQUE
# entité y a sa propre section (ex. "Abeille Vie" p.344-379) avec un
# tableau natif "ÉVOLUTION DES SCR ET MCR (EN MILLIERS D'EUROS)" qui
# reprend la plupart des KPIs en clair — vérifié en lisant directement le
# texte de ces pages avant d'écrire ce correctif, pas supposé (cf.
# Décision 115, DECISIONS.md). Bornes 1-indexées découvertes en
# recherchant, pour chaque entité, les pages dont la 1re ligne EST
# exactement son nom (en-tête de section) — contiguës et sans chevauchement
# pour les 13.
AEMA_BORNES = {
    "Aema Groupe": (6, 71),
    "MACIF SAM": (73, 104),
    "Macif Vie": (107, 135),
    "Macif Sante Prevoyance": (138, 173),
    "Themis": (176, 193),
    "Macifilia": (196, 214),
    "Aesio Mutuelle": (217, 256),
    "MNPAF": (259, 284),
    "MMJ": (287, 312),
    "Nuoma": (314, 341),
    "Abeille Vie": (344, 379),
    "Abeille Epargne Retraite": (382, 407),
    "Abeille IARD Sante": (410, 436),
}

# Bornes 1-indexées (page_debut, page_fin) de l'annexe QRT dans le document
# AG2R combiné (repris de ag2r_entites.py::ENTITES_BORNES). Décision 115 :
# le chapitre narratif QUI PRÉCÈDE (pages 1-121, vérifié — ex. Prima
# "Meilleure estimation... Total... 550 081" en page 77, texte natif)
# contient aussi des valeurs absentes de l'annexe QRT (sommes/totaux,
# ex. best_estimate) — structure moins régulière que pour Aéma (mini-blocs
# par entité dispersés sur plusieurs sections, pas un chapitre contigu par
# entité), donc pas de bornes précises par entité ici : la recherche est
# élargie à TOUT le chapitre narratif (page 1) jusqu'à la fin du bloc QRT
# de l'entité, la désambiguïsation par valeur+code de ligne reste le
# garde-fou contre un faux match.
AG2R_BORNES = {
    "SGAM AG2R LA MONDIALE": (122, 134),
    "AG2R Prevoyance": (139, 157),
    "Arpege Prevoyance": (159, 177),
    "Prima": (179, 196),
    "AG.Mut": (198, 215),
    "VIASANTE Mutuelle": (217, 235),
    "La Mondiale": (237, 254),
    "La Mondiale Europartner": (256, 271),
    "La Mondiale Partenaire": (273, 286),
}


def normaliser_espaces(texte):
    """Espaces insécables/étroits -> espace normal, pour un match texte
    fiable indépendamment de l'encodage d'espace utilisé par le PDF."""
    texte = texte.replace("\xa0", " ").replace(" ", " ").replace(" ", " ")
    return unicodedata.normalize("NFKC", texte)


def formes_nombre(valeur):
    """Représentations plausibles d'un nombre tel qu'imprimé dans un
    tableau QRT (espace = séparateur de milliers, entier si proche d'un
    entier). Retourne une liste de regex-safe patterns, du plus au
    moins spécifique."""
    formes = []
    # ×100/÷diviseur introduit des artefacts flottants (ex. 430.99999999999994
    # pour 431) — comparer à l'ARRONDI, pas tronquer, sinon "431" imprimé au
    # PDF ne matche jamais (bug réel trouvé sur Allianz Vie/ratio_mcr).
    entier = abs(abs(valeur) - round(abs(valeur))) < 1e-6
    v = int(round(abs(valeur))) if entier else abs(valeur)
    s = f"{v:,}".replace(",", " ") if entier else None
    if s:
        formes.append(s)
        formes.append(s.replace(" ", ""))  # sans séparateur (certains PDF)
    if not entier:
        s2 = f"{abs(valeur):,.3f}".replace(",", " ")
        formes.append(s2)
    return formes


def chercher_page(pages_texte, valeur, unite, page_min=1, page_max=None, est_pct=False, codes_ligne=None,
                   valeurs_alternatives=None, libelles=None):
    """pages_texte : liste de texte normalisé par page (index 0 = page
    physique 1). Retourne (page_trouvee_ou_None, nb_candidats, raison).

    `valeurs_alternatives` : autres nombres à chercher EN PLUS de
    `valeur` (même KPI, écrit différemment ailleurs dans le document) —
    sert notamment aux 7 entités Aéma + Sogécap en euros bruts
    (Décision 094/096) : leur annexe QRT est en euros bruts mais le
    chapitre NARRATIF du même document reste en milliers d'euros comme
    le reste du rapport (constaté : "MCR 818 851" narratif pour Abeille
    Vie vs raw_value=818850670 en euros bruts — 818850670/1000=818850,67,
    seule la forme K€ apparaît dans le texte narratif).

    2 passes : (1) toutes les pages où une des valeurs apparaît ; (2) si
    plusieurs candidats, filtre sur celles qui contiennent AUSSI un des
    codes de ligne QRT connus pour ce KPI (KPI_QRT_MAPPING) — distingue
    une mention narrative répétée (résumé/synthèse) de la vraie ligne
    QRT, sans quoi une valeur reprise en résumé rend presque tout
    ambigu (constaté : 128 KPIs ambigus sur la 1re passe seule)."""
    if valeur is None or valeur == 0:
        return None, 0, "valeur nulle ou 0 (trop ambigu pour chercher)"

    page_max = page_max or len(pages_texte)
    formes = formes_nombre(valeur)
    for v in (valeurs_alternatives or []):
        if v:
            formes.extend(formes_nombre(v))
    if not formes:
        return None, 0, "aucune forme numérique générée"

    # positions_valeur[page] = liste des positions (index caractère) où une
    # forme de la valeur apparaît sur cette page — nécessaire pour la
    # désambiguïsation par PROXIMITÉ ci-dessous (pas seulement "le code
    # apparaît quelque part sur la page", trop large : un code de ligne
    # générique comme R0220 peut légitimement apparaître ailleurs sur la
    # page pour un AUTRE champ — constaté, faux positif réel trouvé en
    # testant Allianz Vie/scr_total, cf. Décision 115).
    positions_valeur = {}
    for i in range(page_min - 1, min(page_max, len(pages_texte))):
        texte = pages_texte[i]
        positions = []
        for forme in formes:
            motif = re.escape(forme)
            if est_pct:
                motif = motif + r"\s*%"
            positions.extend(m.start() for m in re.finditer(motif, texte))
        if positions:
            positions_valeur[i + 1] = positions

    candidats = sorted(positions_valeur)
    if len(candidats) == 1:
        return candidats[0], 1, "match unique"
    if len(candidats) == 0:
        return None, 0, "introuvable dans la plage cherchée"

    if codes_ligne:
        motif_codes = re.compile("|".join(re.escape(c) for c in codes_ligne))
        # 150 caractères s'est avéré trop large sur une page QRT dense :
        # un code SANS RAPPORT (ex. R0220 d'une tout autre ligne) tombait
        # parfois dans la fenêtre par coïncidence (faux positif réel trouvé
        # sur Allianz Vie/scr_total, page 90). Le motif réel observé
        # partout est "CODE\n    VALEUR" (le code précède la valeur de
        # quelques caractères seulement, ex. "R0580\n    2 218 591" = 10
        # caractères) — 40 reste une marge confortable sans élargir au
        # point de recapter des codes d'autres lignes.
        FENETRE = 40
        candidats_filtres = []
        for p in candidats:
            texte = pages_texte[p - 1]
            for pos_valeur in positions_valeur[p]:
                debut = max(0, pos_valeur - FENETRE)
                fin = min(len(texte), pos_valeur + FENETRE)
                if motif_codes.search(texte[debut:fin]):
                    candidats_filtres.append(p)
                    break
        if len(candidats_filtres) == 1:
            return candidats_filtres[0], 1, f"match unique après filtre code de ligne à proximité (parmi {candidats})"
        if len(candidats_filtres) > 1:
            # AMBIGUÏTÉ RÉELLE, pas de repli : plusieurs pages ont chacune
            # un code QRT associé de près à la valeur — un cas vécu
            # (Allianz Vie/scr_total, pages 89 ET 90 chacune avec un code de
            # la liste à proximité d'une occurrence différente de la valeur)
            # a montré qu'un repli "dernière occurrence" choisit alors
            # parfois la MAUVAISE page (90, un renvoi de calcul MCR,
            # au lieu de 89, la vraie ligne SCR). Contrairement au cas
            # "aucun code trouvé" ci-dessous (texte narratif, pas de risque
            # de confondre 2 LIGNES QRT différentes), ici deviner serait
            # plus dangereux que de laisser inchangé.
            return None, len(candidats_filtres), f"ambigu même après filtre code de ligne à proximité ({candidats_filtres})"

    # Repli : UNIQUEMENT pour le chapitre narratif (pas de code R#### —
    # texte brut) — libellé français spécifique au KPI (LABELS_NARRATIFS),
    # MÊME logique de proximité que les codes de ligne ci-dessus. PAS de
    # "dernière occurrence" aveugle : un essai précédent choisissait parfois
    # un nombre identique mais SANS RAPPORT (ex. MNPAF/marge_risque : la
    # vraie valeur "1 741" en page 278, à côté du libellé "Marge de
    # risque" — mais "1 741" réapparaît par pure coïncidence en page 283
    # comme variation annuelle d'un tout autre poste, le SCR ; choisir
    # "la dernière page" aurait retenu 283, la mauvaise). Jamais un KPI
    # deviné sans libellé de confiance (cf. LABELS_NARRATIFS, volontairement
    # incomplet).
    if libelles:
        motif_libelles = re.compile("|".join(re.escape(l) for l in libelles), re.IGNORECASE)
        FENETRE_LIBELLE = 80  # un libellé français est plus long qu'un code R####
        candidats_filtres = []
        for p in candidats:
            texte = pages_texte[p - 1]
            for pos_valeur in positions_valeur[p]:
                debut = max(0, pos_valeur - FENETRE_LIBELLE)
                fin = min(len(texte), pos_valeur + FENETRE_LIBELLE)
                if motif_libelles.search(texte[debut:fin]):
                    candidats_filtres.append(p)
                    break
        if len(candidats_filtres) == 1:
            return candidats_filtres[0], 1, f"match unique après filtre libellé narratif à proximité (parmi {candidats})"
        if len(candidats_filtres) > 1:
            # Contrairement au repli "dernière occurrence" aveugle supprimé
            # plus haut : ICI chaque candidat a DÉJÀ été confirmé par un
            # libellé pertinent à proximité (pas une coïncidence numérique
            # nue) — s'ils sont adjacents (≤2 pages d'écart), c'est très
            # probablement la MÊME donnée répétée dans 2 tableaux voisins du
            # même sous-chapitre (ex. Prima/best_estimate : "Meilleure
            # estimation... 550 081" en page 76 ET 77, 2 lignes vérifiées du
            # même bloc "Provisions techniques", pas 2 faits différents).
            # Au-delà de 2 pages, reste une vraie ambiguïté.
            if candidats_filtres[-1] - candidats_filtres[0] <= 2:
                return candidats_filtres[-1], 1, f"dernière occurrence confirmée par libellé parmi {candidats_filtres} (≤2 pages d'écart)"
            return None, len(candidats_filtres), f"ambigu même après filtre libellé narratif ({candidats_filtres})"

    return None, len(candidats), f"ambigu ({len(candidats)} pages candidates : {candidats[:6]})"


def extraire_pages_texte(pdf_path):
    import fitz
    doc = fitz.open(str(pdf_path))
    try:
        return [normaliser_espaces(doc[i].get_text()) for i in range(doc.page_count)]
    finally:
        doc.close()


def corriger_pour_societe(conn, nom, pdf_path, page_min=1, page_max=None, pages_texte=None, dry_run=False):
    """Réutilisable — appelé par ce script pour les 34 sociétés en base,
    ET par extraire_un_pdf.py juste après l'insertion d'une nouvelle
    société (Décision 112) pour que toute future extraction à chaud
    bénéficie de la même correction, pas seulement les 34 déjà en
    base. Retourne (journal, n_corriges, n_ambigu, n_introuvable)."""
    if pages_texte is None:
        pages_texte = extraire_pages_texte(pdf_path)
    page_max = page_max or len(pages_texte)

    journal = []
    n_corriges = n_ambigu = n_introuvable = 0
    company_id = conn.execute("SELECT id FROM companies WHERE name=?", (nom,)).fetchone()[0]
    for row in conn.execute(
        "SELECT kpi_name, value, unit, raw_value, raw_unit, source_page FROM kpis WHERE company_id=? AND value IS NOT NULL",
        (company_id,),
    ):
        est_pct = row["unit"] == "pct"
        valeur_recherchee = row["value"] if est_pct else (row["raw_value"] if row["raw_value"] is not None else row["value"])
        # Décision 115 — le chapitre NARRATIF reste en milliers d'euros même
        # pour les entités dont l'annexe QRT (et donc raw_value) est en
        # euros bruts (7 entités Aéma + Sogécap, Décision 094/096) : essaie
        # aussi la forme K€ (raw_value/1000) et la valeur M€ elle-même.
        alternatives = [row["value"]]
        if not est_pct and row["raw_unit"] and row["raw_unit"].startswith("euros bruts") and row["raw_value"]:
            # forme décimale ET forme arrondie au K€ entier (le texte
            # narratif affiche un arrondi, ex. "818 851" pour 818850,67 —
            # constaté sur Abeille Vie/mcr, pas une supposition).
            alternatives.append(row["raw_value"] / 1000)
            alternatives.append(round(row["raw_value"] / 1000))
        page_trouvee, n_cand, raison = chercher_page(
            pages_texte, valeur_recherchee, row["unit"], page_min, page_max, est_pct=est_pct,
            codes_ligne=codes_ligne_pour(row["kpi_name"]), valeurs_alternatives=alternatives,
            libelles=LABELS_NARRATIFS.get(row["kpi_name"]),
        )
        ancien = row["source_page"]
        if page_trouvee is None:
            if n_cand == 0:
                n_introuvable += 1
            else:
                n_ambigu += 1
            journal.append((nom, row["kpi_name"], ancien, None, raison))
            continue
        if page_trouvee != ancien:
            n_corriges += 1
            journal.append((nom, row["kpi_name"], ancien, page_trouvee, raison))
            if not dry_run:
                conn.execute(
                    "UPDATE kpis SET source_page=? WHERE company_id=? AND kpi_name=?",
                    (page_trouvee, company_id, row["kpi_name"]),
                )
    return journal, n_corriges, n_ambigu, n_introuvable


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    cache_pages = {}  # chemin PDF -> liste de textes par page (évite de rouvrir)
    journal = []  # (societe, kpi_name, ancien, nouveau, raison)
    n_corriges = n_ambigu = n_introuvable = 0

    societes = [r["name"] for r in conn.execute("SELECT name FROM companies ORDER BY name")]
    for nom in societes:
        nom_pdf = PDF_PAR_SOCIETE.get(nom)
        if not nom_pdf:
            print(f"!!! pas de PDF connu pour {nom!r}, ignoré")
            continue
        pdf_path = DATA_DIR / nom_pdf
        if not pdf_path.exists():
            print(f"!!! PDF introuvable : {pdf_path}, {nom!r} ignoré")
            continue

        if pdf_path not in cache_pages:
            print(f"[lecture] {nom_pdf} ...")
            cache_pages[pdf_path] = extraire_pages_texte(pdf_path)
        pages_texte = cache_pages[pdf_path]

        page_min, page_max = 1, len(pages_texte)
        if nom in AEMA_BORNES:
            # Chapitre narratif, contigu et précis par entité (cf. commentaire
            # AEMA_BORNES) — jamais l'annexe QRT (aucun texte natif là-bas).
            page_min, page_max = AEMA_BORNES[nom]
        elif nom in AG2R_BORNES:
            # Élargi à 1..fin-de-bloc-QRT (cf. commentaire AG2R_BORNES) :
            # couvre le chapitre narratif ET l'annexe QRT de cette entité.
            page_min, page_max = 1, AG2R_BORNES[nom][1]

        j, c, a, i = corriger_pour_societe(conn, nom, pdf_path, page_min, page_max, pages_texte, args.dry_run)
        journal.extend(j)
        n_corriges += c
        n_ambigu += a
        n_introuvable += i

    if not args.dry_run:
        conn.commit()
    conn.close()

    print(f"\n{'[DRY-RUN] ' if args.dry_run else ''}Résumé :")
    print(f"  corrigés (page différente trouvée) : {n_corriges}")
    print(f"  ambigus (plusieurs pages candidates, inchangé) : {n_ambigu}")
    print(f"  introuvables (0 page candidate, inchangé) : {n_introuvable}")

    print("\n--- détail des corrections ---")
    for nom, kpi, ancien, nouveau, raison in journal:
        if nouveau is not None:
            print(f"  {nom:34} {kpi:28} {str(ancien):>6} -> {nouveau:<6} ({raison})")

    print("\n--- détail des cas non résolus (ambigu/introuvable) ---")
    for nom, kpi, ancien, nouveau, raison in journal:
        if nouveau is None:
            print(f"  {nom:34} {kpi:28} actuel={str(ancien):>6}  {raison}")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
