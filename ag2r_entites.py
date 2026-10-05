# -*- coding: utf-8 -*-
"""ag2r_entites.py — Décision 085 : intégration multi-entités du document
combiné AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf (288 pages, 9 entités
juridiques). Contrairement à Aéma Groupe (100% image, aema_entites.py),
ce document est confirmé TEXTE NATIF (mode="codes_eiopa",
scr_method="formule_standard", cf. detecter_templates) — chaque entité
est donc extraite par le même mécanisme que extract_kpis_predica.py
(classify_pages+extract_qrt_native construit un corpus à la volée,
resoudre_variantes_qrt le résout), pas par lecture manuelle d'image.

Frontières d'entités trouvées via classify_pages() sur le document
entier : 9 blocs QRT contigus, chacun précédé d'une page narrative
"Identification de l'entreprise" portant le nom juridique — vérifié
manuellement pour les 9 (cf. Décision 085/session Task 3).

    python ag2r_entites.py
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "test_markdrop"))

import extract_kpis as ek  # noqa: E402
from ingest import classify_pages, extract_qrt_native, NATIVE_TEXT_THRESHOLD, extraire_entite  # noqa: E402
from detecter_templates import detecter_templates  # noqa: E402
from batch_diagnostic import construire_qrt_dict_synthetique  # noqa: E402
from extraire_par_libelle import classifier_lignes  # noqa: E402
import fitz  # noqa: E402

# Bug réel trouvé (Task 3, Décision 085) : les pages S.05.01.02 de ce
# document utilisent du texte natif TOURNÉ 90° (dir=(0,-1) sur les
# spans PyMuPDF, vérifié) — extract_qrt_native() suppose un texte
# horizontal (appariement colonne par position x croissante), donc
# n'y trouve AUCUNE valeur (valeurs={} pour toutes les lignes),
# silencieusement, sur les 9 entités. Même famille de limite que MAIF
# page 114 (Décision 084, "colonnes rotées non parsable
# automatiquement"). Corrigé ici SANS toucher extract_qrt_native ni
# classifier_lignes (déjà utilisés tels quels pour MAIF/Covéa) : sur
# du texte tourné, PyMuPDF imprime chaque valeur sur SA PROPRE LIGNE
# (au lieu d'une ligne espacée par colonnes) — classifier_lignes()
# accumule déjà ce pattern correctement (Décision 073), il suffit de
# lui donner le texte brut de la page et de chercher les lignes dont
# le libellé normalisé SE TERMINE par le code R0xxx voulu (le libellé
# se retrouve fusionné avec le code, ex. "primes acquises brutes –
# assurance directe r0210"), puis de prendre la DERNIÈRE valeur
# (colonne Total). Vérifié sur AG2R Prévoyance : R0210 Total=2 339 198
# (= 1 343 253+995 945+0×10, exact).
LIGNES_PRIMES_NONVIE = ("r0210", "r0220", "r0230")
LIGNES_SINISTRES_NONVIE = ("r0310", "r0320", "r0330")
LIGNE_PRIMES_VIE = "r1510"
LIGNE_SINISTRES_VIE = "r1610"


def _somme_lignes_total(paires, codes_suffixes, capturer=None, page=None):
    """paires : sortie de classifier_lignes(). Retourne (somme, n_trouvees)
    des valeurs[-1] (colonne Total) des lignes dont le libellé normalisé
    se termine par un des codes de `codes_suffixes`.

    `capturer`, si fourni (liste), est complétée de façon PUREMENT
    ADDITIVE (aucun changement de la somme retournée) par 1 dict par
    ligne trouvée — {"code", "libelle", "valeur", "page"} — pour
    reconstituer le détail composant par composant (table
    `kpi_composants`)."""
    total, n = 0.0, 0
    for label, valeurs in paires:
        for code in codes_suffixes:
            if label.endswith(code) and valeurs:
                total += valeurs[-1]
                n += 1
                if capturer is not None:
                    capturer.append({
                        "code": code.upper(), "libelle": label,
                        "valeur": valeurs[-1], "page": page,
                    })
                break
    return total, n


def resoudre_primes_sinistres_ag2r(sous_pdf_path, pages_qrt, capturer_primes=None, capturer_sinistres=None):
    """Scanne toutes les pages S.05.01.02 de l'entité (texte brut, pas
    extract_qrt_native) et somme les colonnes Total des lignes "Brut"
    non-vie (R0210+R0220+R0230) et vie (R1510) pour primes_acquises_
    brutes, même logique pour charge_sinistres (R0310+R0320+R0330 +
    R1610). Retourne (primes, charge, n_lignes_trouvees) — n_lignes
    sert de garde-fou : si 0, ne rien insérer plutôt que 0,00 trompeur.

    `capturer_primes`/`capturer_sinistres`, si fournis (listes), voir
    _somme_lignes_total — purement additif."""
    doc = fitz.open(str(sous_pdf_path))
    primes_total, sinistres_total, n_trouve = 0.0, 0.0, 0
    for page in pages_qrt:
        if page["template_id"] != "S.05.01.02":
            continue
        texte = doc[page["page"] - 1].get_text()
        paires = classifier_lignes(texte)
        p, n1 = _somme_lignes_total(paires, LIGNES_PRIMES_NONVIE + (LIGNE_PRIMES_VIE,),
                                     capturer=capturer_primes, page=page["page"])
        s, n2 = _somme_lignes_total(paires, LIGNES_SINISTRES_NONVIE + (LIGNE_SINISTRES_VIE,),
                                     capturer=capturer_sinistres, page=page["page"])
        primes_total += p
        sinistres_total += s
        n_trouve += n1 + n2
    doc.close()
    return primes_total, sinistres_total, n_trouve

SOURCE_PDF = BASE_DIR / "data" / "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf"
YEAR = 2025
COMPANY_TYPE = "entité (Groupe AG2R La Mondiale)"

# (nom, page_debut, page_fin) — bornes 1-indexées inclusives des 9 blocs
# QRT contigus détectés par classify_pages() sur le document entier,
# chaque bloc vérifié précédé d'une page "Identification de l'entreprise"
# portant ce nom exact.
ENTITES_BORNES = [
    ("SGAM AG2R LA MONDIALE", 122, 134),  # entité consolidée du groupe
    ("AG2R Prevoyance", 139, 157),
    ("Arpege Prevoyance", 159, 177),
    ("Prima", 179, 196),
    ("AG.Mut", 198, 215),
    ("VIASANTE Mutuelle", 217, 235),
    ("La Mondiale", 237, 254),
    ("La Mondiale Europartner", 256, 271),
    ("La Mondiale Partenaire", 273, 286),
]


def construire_corpus_entite(sous_pdf_path, qrt_dict_synth):
    classification = classify_pages(sous_pdf_path)
    pages_qrt = [p for p in classification if p["type"] == "qrt"]
    if not pages_qrt:
        raise RuntimeError(f"0 page QRT détectée par classify_pages() sur {sous_pdf_path}")

    corpus = []
    pages_ignorees, templates_inconnus = [], []
    doc = fitz.open(str(sous_pdf_path))
    for page in pages_qrt:
        template_id = page["template_id"]
        if page["n_caracteres"] <= NATIVE_TEXT_THRESHOLD:
            pages_ignorees.append((template_id, page["page"]))
            continue
        if template_id not in qrt_dict_synth:
            templates_inconnus.append((template_id, page["page"]))
            continue
        sheet_key = next(iter(qrt_dict_synth[template_id]))
        sheet_dict = qrt_dict_synth[template_id][sheet_key]
        pdf_page = doc[page["page"] - 1]
        r = extract_qrt_native(pdf_page, sheet_dict, sheet_key)
        corpus.append({
            "template_id": template_id, "page_source": page["page"],
            "contenu": {"lignes": r["lignes"]},
        })
    doc.close()
    return corpus, pages_ignorees, templates_inconnus


def _page_source(corpus, template_id):
    return next((e["page_source"] for e in corpus if e["template_id"] == template_id), None)


def extraire_tout_entite(corpus):
    templates_presents = {e["template_id"] for e in corpus}
    valeurs = {}

    for kpi_name, diviseur, multiplicateur in [
        ("ratio_scr", 1, 100), ("ratio_mcr", 1, 100),
        ("scr_total", 1000, 1), ("mcr", 1000, 1),
        ("fonds_propres_eligibles", 1000, 1), ("fonds_propres_t1_nr", 1000, 1),
        ("fonds_propres_t1_r", 1000, 1), ("fonds_propres_t2", 1000, 1), ("fonds_propres_t3", 1000, 1),
    ]:
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if not resultats:
            valeurs[kpi_name] = (None, None, "aucune variante du mapping ne matche")
            continue
        valeur, template_id, variante = resultats[0]
        valeurs[kpi_name] = (
            valeur * multiplicateur / diviseur, _page_source(corpus, template_id),
            f"{template_id}/{variante['row']}/{variante['col']} ({variante['variante']})",
        )

    for kpi_name, diviseur in [("best_estimate", 1000), ("marge_risque", 1000)]:
        try:
            valeur, template_id, variante = ek.valeur_principale(kpi_name, corpus, templates_presents)
            valeurs[kpi_name] = (valeur / diviseur, _page_source(corpus, template_id), f"{template_id}, somme (mapping)")
        except ek.KpiIntrouvable as e:
            valeurs[kpi_name] = (None, None, str(e))

    if valeurs.get("best_estimate", (None,))[0] is not None and valeurs.get("marge_risque", (None,))[0] is not None:
        valeurs["provisions_techniques"] = (
            valeurs["best_estimate"][0] + valeurs["marge_risque"][0],
            valeurs["best_estimate"][1], "best_estimate + marge_risque",
        )
    else:
        valeurs["provisions_techniques"] = (None, None, "best_estimate ou marge_risque NULL")

    # primes_acquises_brutes/charge_sinistres : PAS via resoudre_variantes_qrt
    # ici — extract_qrt_native() échoue silencieusement sur ces pages
    # (texte tourné 90°, cf. commentaire en tête de fichier), donc le
    # corpus ne contient AUCUNE valeur pour S.05.01.02 (valeurs={} pour
    # toutes les lignes) et resoudre_variantes_qrt renverrait à tort 0,00
    # plutôt que NULL. Résolu séparément par resoudre_primes_sinistres_ag2r()
    # (texte brut, pas le corpus), appelé depuis __main__ après cette
    # fonction — placeholders ici, écrasés ensuite si des lignes sont
    # trouvées, sinon laissés NULL (jamais 0,00 par défaut).
    valeurs["primes_acquises_brutes"] = (None, None, "résolu séparément (texte tourné, cf. resoudre_primes_sinistres_ag2r)")
    valeurs["charge_sinistres"] = (None, None, "résolu séparément (texte tourné, cf. resoudre_primes_sinistres_ag2r)")

    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie", "scr_diversification"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            valeur, template_id, variante = resultats[0]
            valeurs[kpi_name] = (valeur / 1000, _page_source(corpus, template_id),
                                  f"{template_id}/{variante['row']} (mapping, formule standard)")
        else:
            valeurs[kpi_name] = (None, None, "aucune source disponible (pas de picture_75 équivalent)")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec Groupama/CNP/Predica)")

    return valeurs


def inserer_en_base(nom_entite, valeurs, db_path="kpis.db"):
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT OR IGNORE INTO companies (name, type, country) VALUES (?, ?, 'France')",
                  (nom_entite, COMPANY_TYPE))
    conn.commit()
    company_id = conn.execute("SELECT id FROM companies WHERE name = ?", (nom_entite,)).fetchone()[0]

    defs_par_nom = {d["kpi_name"]: d for d in ek.KPI_DEFINITIONS}
    lignes_resume = []
    for kpi_name, (valeur, source_page, note) in valeurs.items():
        d = defs_par_nom[kpi_name]
        conn.execute(
            """INSERT INTO kpis (company_id, year, category, kpi_name, value, unit, source_page, source_chapter, validated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
               ON CONFLICT(company_id, year, kpi_name) DO UPDATE SET
                 value=excluded.value, unit=excluded.unit,
                 source_page=excluded.source_page, source_chapter=excluded.source_chapter""",
            (company_id, YEAR, d["category"], kpi_name, valeur, d["unit"], source_page,
             f"Document combiné 'AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf' (288p), entité isolée — {note}"),
        )
        lignes_resume.append((kpi_name, d["category"], valeur, d["unit"], source_page, note))
    conn.commit()
    conn.close()
    return lignes_resume


def afficher_resume(nom_entite, lignes_resume):
    print(f"\n{'='*100}\nRÉSUMÉ — {nom_entite}\n{'='*100}")
    n_null = 0
    for kpi_name, categorie, valeur, unite, page, note in lignes_resume:
        if valeur is None:
            n_null += 1
            val_str = "NULL"
        else:
            val_str = f"{valeur:,.2f}"
        print(f"  {kpi_name:28} {categorie:14} {val_str:>16} {unite:6} {str(page or '-'):5}  {note}")
    print(f"  Total : {len(lignes_resume)} KPIs, {len(lignes_resume) - n_null} valeurs, {n_null} NULL")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    qrt_dict_synth = construire_qrt_dict_synthetique(ek.KPI_QRT_MAPPING)

    for nom, pd, pf in ENTITES_BORNES:
        sous_pdf = extraire_entite(SOURCE_PDF, pd, pf, nom_entite=nom)
        corpus, pages_ignorees, templates_inconnus = construire_corpus_entite(sous_pdf, qrt_dict_synth)
        if pages_ignorees:
            print(f"  [{nom}] pages ignorées (texte insuffisant) : {pages_ignorees}")
        if templates_inconnus:
            print(f"  [{nom}] templates hors dictionnaire : {templates_inconnus}")
        valeurs = extraire_tout_entite(corpus)

        pages_qrt = [p for p in classify_pages(sous_pdf) if p["type"] == "qrt"]
        primes, sinistres, n_trouve = resoudre_primes_sinistres_ag2r(sous_pdf, pages_qrt)
        if n_trouve > 0:
            valeurs["primes_acquises_brutes"] = (
                primes / 1000, None,
                f"S.05.01.02 (texte tourné, lecture ligne brute), somme R0210+R0220+R0230(non-vie)+R1510(vie), {n_trouve} lignes trouvées")
            valeurs["charge_sinistres"] = (
                sinistres / 1000, None,
                f"S.05.01.02 (texte tourné, lecture ligne brute), somme R0310+R0320+R0330(non-vie)+R1610(vie), {n_trouve} lignes trouvées")
        else:
            print(f"  [{nom}] primes/sinistres : 0 ligne R0210/R0220/R0230/R0310/R0320/R0330/R1510/R1610 trouvée — NULL conservé")

        lignes_resume = inserer_en_base(nom, valeurs)
        afficher_resume(nom, lignes_resume)
