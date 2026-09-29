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

Ne couvre PAS les 13 entités Aéma (100% image, aucun texte natif
extractible sans OCR, cf. aema_entites.py) — traitées séparément par
vérification visuelle ciblée (hors de ce script, cf. NIGHT_LOG.md).

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

# 100% image, aucun texte natif — skip (cf. docstring). Traité à part.
AEMA_ENTITES_IMAGE = {
    "Aema Groupe", "MACIF SAM", "Macif Vie", "Macif Sante Prevoyance",
    "Themis", "Macifilia", "Aesio Mutuelle", "MNPAF", "MMJ", "Nuoma",
    "Abeille Vie", "Abeille Epargne Retraite", "Abeille IARD Sante",
}

# Bornes 1-indexées (page_debut, page_fin) dans le document AG2R combiné
# (repris de ag2r_entites.py::ENTITES_BORNES) — utilisées pour scoper la
# recherche et éviter un faux match dans le bloc d'une AUTRE entité.
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


def chercher_page(pages_texte, valeur, unite, page_min=1, page_max=None, est_pct=False, codes_ligne=None):
    """pages_texte : liste de texte normalisé par page (index 0 = page
    physique 1). Retourne (page_trouvee_ou_None, nb_candidats, raison).

    2 passes : (1) toutes les pages où la valeur apparaît ; (2) si
    plusieurs candidats, filtre sur celles qui contiennent AUSSI un des
    codes de ligne QRT connus pour ce KPI (KPI_QRT_MAPPING) — distingue
    une mention narrative répétée (résumé/synthèse) de la vraie ligne
    QRT, sans quoi une valeur reprise en résumé rend presque tout
    ambigu (constaté : 128 KPIs ambigus sur la 1re passe seule)."""
    if valeur is None or valeur == 0:
        return None, 0, "valeur nulle ou 0 (trop ambigu pour chercher)"

    page_max = page_max or len(pages_texte)
    formes = formes_nombre(valeur)
    if not formes:
        return None, 0, "aucune forme numérique générée"

    candidats = []
    for i in range(page_min - 1, min(page_max, len(pages_texte))):
        texte = pages_texte[i]
        for forme in formes:
            motif = re.escape(forme)
            if est_pct:
                motif = motif + r"\s*%"
            if re.search(motif, texte):
                candidats.append(i + 1)  # page physique 1-indexée
                break

    candidats = sorted(set(candidats))
    if len(candidats) == 1:
        return candidats[0], 1, "match unique"
    if len(candidats) == 0:
        return None, 0, "introuvable dans la plage cherchée"

    if codes_ligne:
        motif_codes = re.compile("|".join(re.escape(c) for c in codes_ligne))
        candidats_filtres = [p for p in candidats if motif_codes.search(pages_texte[p - 1])]
        if len(candidats_filtres) == 1:
            return candidats_filtres[0], 1, f"match unique après filtre code de ligne (parmi {candidats})"
        if len(candidats_filtres) > 1:
            return None, len(candidats_filtres), f"ambigu même après filtre code de ligne ({candidats_filtres})"

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
        "SELECT kpi_name, value, unit, raw_value, source_page FROM kpis WHERE company_id=? AND value IS NOT NULL",
        (company_id,),
    ):
        est_pct = row["unit"] == "pct"
        valeur_recherchee = row["value"] if est_pct else (row["raw_value"] if row["raw_value"] is not None else row["value"])
        page_trouvee, n_cand, raison = chercher_page(
            pages_texte, valeur_recherchee, row["unit"], page_min, page_max, est_pct=est_pct,
            codes_ligne=codes_ligne_pour(row["kpi_name"]),
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
    n_corriges = n_ambigu = n_introuvable = n_skip = 0

    societes = [r["name"] for r in conn.execute("SELECT name FROM companies ORDER BY name")]
    for nom in societes:
        if nom in AEMA_ENTITES_IMAGE:
            n_skip += conn.execute(
                "SELECT COUNT(*) FROM kpis k JOIN companies c ON c.id=k.company_id WHERE c.name=? AND value IS NOT NULL",
                (nom,),
            ).fetchone()[0]
            continue
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
        if nom in AG2R_BORNES:
            pd, pf = AG2R_BORNES[nom]
            page_min, page_max = pd, pf

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
    print(f"  ignorés (entités Aéma 100% image) : {n_skip}")

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
