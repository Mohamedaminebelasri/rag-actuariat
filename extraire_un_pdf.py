# -*- coding: utf-8 -*-
"""extraire_un_pdf.py — Extraction à chaud des 22 KPIs sur UN PDF SFCR
arbitraire, jamais vu par le système (Décision 106), pour le nouvel
onglet frontend "Ajouter un PDF" (PR commit f90e74f).

CORRECTIF IMPORTANT sur la demande d'origine (frontend, ce soir) :
le pipeline d'extraction KPI de ce dépôt n'appelle PAS de cascade
Gemini/Mistral/Groq — c'est le fallback LLM du chatbot RAG sur la
directive 2009/138/CE (src/rag.py, décrit dans CLAUDE.md), un système
SÉPARÉ. L'extraction de KPI (34 sociétés déjà en base) repose sur un
appariement de gabarits QRT en texte natif (Docling/PyMuPDF, PAS de
LLM sauf 1 fallback vision Gemini très ponctuel sur une image
spécifique de Groupama, extract_kpis.py::lire_picture_75). Ce script
réutilise donc la VRAIE logique déjà testée — detecter_templates() +
classify_pages()/extract_qrt_native() (test_markdrop/ingest.py) +
resoudre_variantes_qrt()/valeur_principale() (extract_kpis.py,
dictionnaire KPI_QRT_MAPPING) — sans aucune nouvelle méthode
d'extraction, comme demandé. L'étape "appel_modele" du contrat JSON
est conservée telle quelle (même nom d'étape pour ne pas casser le
frontend déjà écrit autour de ce contrat) mais son message décrit
honnêtement ce qui se passe réellement.

LIMITE ASSUMÉE, explicite dans chaque job : contrairement aux 34
sociétés déjà en base — CHACUNE relue manuellement au moins une fois
et souvent corrigée (bugs positionnels, unités, KPIs fusionnés —
Décisions 093 à 101) — ce script tourne SANS intervention humaine sur
un document jamais vu. Conformément à la demande explicite du
frontend, tous les KPIs sont donc insérés avec validated=0 (forcé,
même si les contrôles automatiques passent) et unite_source enregistre
l'hypothèse K€ comme NON VÉRIFIÉE (vs. les 8 sociétés confirmées en
euros bruts par recoupement, Décisions 094/096). "Refus exact, jamais
d'invention" reste respecté : tout KPI non résolu par le mapping reste
NULL, jamais deviné.

    python extraire_un_pdf.py --pdf "data/<nom>.pdf" --societe "<nom>" --annee 2025 --job-id <id>

Écrit la progression dans jobs/<job-id>.json à chaque étape (jamais
seulement à la fin), insère dans kpis.db (nouvelle société), régénère
les 2 exports frontend déjà en place (kpi-sources.json,
donnees-extraites.json) en cas de succès. Ne lève JAMAIS d'exception
non gérée : toute erreur est capturée et écrite dans le job
(statut="erreur") — le process Node qui lance ce script en détaché ne
doit jamais le voir planter sans trace.
"""
import argparse
import json
import re
import sqlite3
import sys
import traceback
from pathlib import Path

BASE_DIR = Path(__file__).parent
JOBS_DIR = BASE_DIR / "jobs"
DB_PATH = BASE_DIR / "kpis.db"

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "test_markdrop"))

DIVISEUR_MONTANT = 1000  # hypothèse K€ par défaut — NON vérifiée (cf. docstring)


# ---------------------------------------------------------------------
# Suivi de job — jobs/<job-id>.json, réécrit en entier à chaque étape
# ---------------------------------------------------------------------

class SuiviJob:
    def __init__(self, job_id, societe, annee):
        self.job_id = job_id
        self.etat = {
            "statut": "en_cours", "etape": None, "message": "démarrage...",
            "societe": societe, "annee": annee, "kpis": [], "erreur": None,
        }
        self._ecrire()

    def _ecrire(self):
        JOBS_DIR.mkdir(exist_ok=True)
        chemin = JOBS_DIR / f"{self.job_id}.json"
        tmp = chemin.with_suffix(".json.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(self.etat, f, ensure_ascii=False, indent=2)
            tmp.replace(chemin)
        except Exception as e:  # jamais bloquant : au pire, pas de suivi visible
            print(f"!!! échec écriture jobs/{self.job_id}.json : {e}", file=sys.stderr)

    def etape(self, etape, message):
        print(f"[{etape}] {message}")
        self.etat["etape"] = etape
        self.etat["message"] = message
        self._ecrire()

    def kpis_maj(self, kpis):
        self.etat["kpis"] = kpis
        self._ecrire()

    def succes(self, message):
        self.etat["statut"] = "termine"
        self.etat["message"] = message
        self._ecrire()

    def echec(self, message, exception=None):
        self.etat["statut"] = "erreur"
        self.etat["message"] = message
        self.etat["erreur"] = str(exception) if exception else message
        self._ecrire()


# ---------------------------------------------------------------------
# Construction du corpus — même logique que les 34 scripts extract_kpis_*.py
# (ex. extraire_un_pdf reprend fidèlement construire_corpus() de
# extract_kpis_allianzvie.py, déjà générique : aucun nom de société en dur)
# ---------------------------------------------------------------------

def construire_corpus(pdf_path, ek, suivi):
    from ingest import classify_pages, extract_qrt_native, NATIVE_TEXT_THRESHOLD
    from detecter_templates import detecter_templates
    from batch_diagnostic import construire_qrt_dict_synthetique
    import fitz

    qrt_dict_synth = construire_qrt_dict_synthetique(ek.KPI_QRT_MAPPING)
    classification = classify_pages(pdf_path)
    pages_qrt = [p for p in classification if p["type"] == "qrt"]
    if not pages_qrt:
        raise RuntimeError(
            "0 page QRT détectée dans ce PDF — document non reconnu comme un "
            "rapport SFCR/QRT standard (ou entièrement scanné/image, non géré "
            "par ce pipeline sans intervention manuelle)"
        )

    inventaire = detecter_templates(pdf_path)
    suivi.etape(
        "extraction_pdf",
        f"Document classifié : type={inventaire['document_type']!r}, "
        f"méthode SCR={inventaire['scr_method']!r}, mode={inventaire['mode']!r}, "
        f"{len(pages_qrt)} page(s) QRT détectée(s)",
    )

    corpus = []
    pages_ignorees, templates_inconnus = [], []
    doc = fitz.open(str(pdf_path))
    try:
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
    finally:
        doc.close()

    note = f"{len(corpus)} page(s) exploitée(s)"
    if pages_ignorees:
        note += f", {len(pages_ignorees)} ignorée(s) (texte natif insuffisant, probable image/scan)"
    if templates_inconnus:
        note += f", {len(templates_inconnus)} template(s) hors dictionnaire connu"
    suivi.etape("extraction_pdf", note)

    return corpus, inventaire


def _page_source(corpus, template_id):
    return next((e["page_source"] for e in corpus if e["template_id"] == template_id), None)


# ---------------------------------------------------------------------
# Résolution des 22 KPIs — dictionnaire de mapping générique uniquement
# (aucun override manuel : document jamais vu, contrairement aux 34
# sociétés déjà en base). Tout ce qui ne matche pas reste NULL.
# ---------------------------------------------------------------------

def extraire_kpis(corpus, ek, suivi):
    templates_presents = {e["template_id"] for e in corpus}
    valeurs = {}

    suivi.etape(
        "appel_modele",
        "Résolution des 22 KPIs par appariement de gabarits QRT (dictionnaire "
        "de mapping générique KPI_QRT_MAPPING, aucune correction manuelle "
        "possible sur un document inédit)...",
    )

    for kpi_name, diviseur, multiplicateur in [
        ("ratio_scr", 1, 100), ("ratio_mcr", 1, 100),
        ("scr_total", DIVISEUR_MONTANT, 1), ("mcr", DIVISEUR_MONTANT, 1),
        ("fonds_propres_eligibles", DIVISEUR_MONTANT, 1), ("fonds_propres_t1_nr", DIVISEUR_MONTANT, 1),
        ("fonds_propres_t1_r", DIVISEUR_MONTANT, 1), ("fonds_propres_t2", DIVISEUR_MONTANT, 1),
        ("fonds_propres_t3", DIVISEUR_MONTANT, 1),
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

    for kpi_name in ("best_estimate", "marge_risque"):
        try:
            valeur, template_id, variante = ek.valeur_principale(kpi_name, corpus, templates_presents)
            valeurs[kpi_name] = (valeur / DIVISEUR_MONTANT, _page_source(corpus, template_id), f"{template_id}, mapping")
        except ek.KpiIntrouvable as e:
            valeurs[kpi_name] = (None, None, str(e))

    if valeurs.get("best_estimate", (None,))[0] is not None and valeurs.get("marge_risque", (None,))[0] is not None:
        valeurs["provisions_techniques"] = (
            valeurs["best_estimate"][0] + valeurs["marge_risque"][0],
            valeurs["best_estimate"][1], "best_estimate + marge_risque",
        )
    else:
        valeurs["provisions_techniques"] = (None, None, "best_estimate ou marge_risque NULL")

    # primes_acquises_brutes/charge_sinistres sont CUMULATIFS (vie et
    # non-vie sont 2 variantes COMPLÉMENTAIRES du mapping, pas 2 façons
    # alternatives d'obtenir le même nombre — cf. docstring de
    # resoudre_variantes_qrt) : somme de TOUS les résultats, jamais le
    # premier seul, même pattern que extract_kpis_cnp.py (vérifié,
    # Décision 059) — un bug initial ici (resultats[0] seul) sous-comptait
    # d'un facteur ~23× sur un assureur mixte vie+non-vie lors du test de
    # ce script (CNP Assurances, cf. Décision 106).
    for kpi_name in ("primes_acquises_brutes", "charge_sinistres"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            total = sum(v for v, _t, _var in resultats)
            template_id = resultats[0][1]
            valeurs[kpi_name] = (total / DIVISEUR_MONTANT, _page_source(corpus, template_id),
                                  f"{template_id}, somme {len(resultats)} variante(s) (mapping)")
        else:
            valeurs[kpi_name] = (None, None, "aucune variante du mapping ne matche")

    for kpi_name in ("scr_operationnel", "scr_marche", "scr_souscription_sante",
                      "scr_contrepartie", "scr_souscription_vie", "scr_souscription_nonvie",
                      "scr_diversification"):
        resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents)
        if resultats:
            valeur, template_id, variante = resultats[0]
            valeurs[kpi_name] = (valeur / DIVISEUR_MONTANT, _page_source(corpus, template_id),
                                  f"{template_id}/{variante['row']} (mapping)")
        else:
            valeurs[kpi_name] = (None, None, "aucune variante du mapping ne matche (modèle interne possible, non testé automatiquement)")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent QRT standardisé (Décision 051)")
    return valeurs


def deduire_type_activite(valeurs):
    """Même règle que Décision 103 (populate_company_metadata.py), depuis
    les valeurs tout juste résolues plutôt que depuis kpis.db."""
    vie = valeurs.get("scr_souscription_vie", (None,))[0]
    nonvie = valeurs.get("scr_souscription_nonvie", (None,))[0]
    if vie is None and nonvie is None:
        return None
    a_vie, a_nonvie = (vie or 0) > 0, (nonvie or 0) > 0
    if a_vie and a_nonvie:
        return "Mixte"
    if a_vie:
        return "Vie"
    if a_nonvie:
        return "Non-vie"
    return "Mutuelle"


# ---------------------------------------------------------------------
# Écriture en base + contrôles — validated FORCÉ à 0 (Décision 106,
# demande explicite : pas de checkpoint humain avant demain matin)
# ---------------------------------------------------------------------

def inserer_en_base(company_name, year, valeurs, inventaire, kpi_definitions):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    type_activite = deduire_type_activite(valeurs)
    conn.execute(
        """INSERT OR IGNORE INTO companies
           (name, type, country, type_document, scr_method, type_activite, unite_source)
           VALUES (?, 'à déterminer', 'France', ?, ?, ?, ?)""",
        (company_name, inventaire.get("document_type"), inventaire.get("scr_method"),
         type_activite, "K€ (hypothèse par défaut, NON vérifiée — extraction à chaud sans revue)"),
    )
    conn.commit()
    company_id = conn.execute("SELECT id FROM companies WHERE name=?", (company_name,)).fetchone()[0]

    defs_par_nom = {d["kpi_name"]: d for d in kpi_definitions}
    kpis_pour_job = []
    for kpi_name, (valeur, source_page, note) in valeurs.items():
        d = defs_par_nom[kpi_name]
        conn.execute(
            """INSERT INTO kpis (company_id, year, category, kpi_name, value, unit, source_page, source_chapter, validated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
               ON CONFLICT(company_id, year, kpi_name) DO UPDATE SET
                 value=excluded.value, unit=excluded.unit, source_page=excluded.source_page,
                 source_chapter=excluded.source_chapter, validated=0""",
            (company_id, year, d["category"], kpi_name, valeur, d["unit"], source_page, d["sfcr_chapter"]),
        )
        kpis_pour_job.append({
            "kpi_name": kpi_name, "value": valeur, "unit": d["unit"], "category": d["category"],
            "source_page": source_page, "source_chapter": d["sfcr_chapter"], "validated": False,
        })
    conn.commit()
    conn.close()
    return company_id, kpis_pour_job


def valider(company_name, year):
    from validate_kpis import valider_societe
    conn = sqlite3.connect(DB_PATH)
    n_passed, controles = valider_societe(conn, company_name, year, afficher_detail=False)
    # Forcé APRÈS valider_societe() (qui appelle marquer_valides() et
    # marquerait validated=1 les KPIs dont tous les contrôles passent) —
    # un contrôle mécanique n'est PAS une revue humaine, cf. docstring.
    company_id = conn.execute("SELECT id FROM companies WHERE name=?", (company_name,)).fetchone()[0]
    conn.execute("UPDATE kpis SET validated=0 WHERE company_id=? AND year=?", (company_id, year))
    conn.commit()
    conn.close()
    return n_passed, (controles or [])


def _valider_job_id(job_id):
    if not re.fullmatch(r"[A-Za-z0-9_-]+", job_id):
        raise ValueError(f"--job-id invalide (lettres/chiffres/-/_ uniquement) : {job_id!r}")
    return job_id


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", required=True)
    parser.add_argument("--societe", required=True)
    parser.add_argument("--annee", required=True, type=int)
    parser.add_argument("--job-id", required=True, dest="job_id")
    args = parser.parse_args()

    # Le job-id devient un nom de fichier : validé AVANT toute écriture,
    # sinon impossible d'écrire un statut d'erreur au bon endroit.
    try:
        job_id = _valider_job_id(args.job_id)
    except ValueError as e:
        print(f"!!! {e}", file=sys.stderr)
        sys.exit(1)

    suivi = SuiviJob(job_id, args.societe, args.annee)

    try:
        pdf_path = Path(args.pdf)
        if not pdf_path.is_absolute():
            pdf_path = BASE_DIR / pdf_path
        if not pdf_path.exists():
            raise FileNotFoundError(f"PDF introuvable : {pdf_path}")

        suivi.etape("extraction_pdf", f"Lecture du PDF ({pdf_path.name})...")

        import extract_kpis as ek  # import lourd (Docling/PaddleOCR) — ici, pas au niveau module
        from kpi_definitions import KPI_DEFINITIONS

        corpus, inventaire = construire_corpus(pdf_path, ek, suivi)
        valeurs = extraire_kpis(corpus, ek, suivi)

        defs_par_nom = {d["kpi_name"]: d for d in KPI_DEFINITIONS}
        apercu = [
            {"kpi_name": k, "value": v, "unit": defs_par_nom[k]["unit"], "category": defs_par_nom[k]["category"],
             "source_page": p, "source_chapter": defs_par_nom[k]["sfcr_chapter"], "validated": False}
            for k, (v, p, _n) in valeurs.items()
        ]
        suivi.kpis_maj(apercu)

        suivi.etape("ecriture_db", f"Écriture dans kpis.db ({args.societe}, {args.annee})...")
        _company_id, kpis_pour_job = inserer_en_base(args.societe, args.annee, valeurs, inventaire, KPI_DEFINITIONS)
        suivi.kpis_maj(kpis_pour_job)

        suivi.etape("validation", "Exécution des contrôles actuariels (cohérence interne, signes, magnitude)...")
        n_passed, controles = valider(args.societe, args.annee)

        suivi.etape("ecriture_db", "Régénération des exports frontend (kpi-sources.json, donnees-extraites.json)...")
        from export_kpis_for_frontend import export_kpis, export_donnees_extraites
        export_kpis()
        export_donnees_extraites()

        n_non_null = sum(1 for k in kpis_pour_job if k["value"] is not None)
        suivi.succes(
            f"Extraction terminée : {n_non_null}/22 KPIs remplis, "
            f"{n_passed}/{len(controles)} contrôles passés. Tous les KPIs restent "
            f"'à vérifier' (validated=false) — aucune revue humaine effectuée."
        )

    except Exception as e:
        traceback.print_exc()
        suivi.echec(f"Échec de l'extraction : {e}", e)
        # PAS de re-raise : le statut d'erreur est déjà écrit, le process
        # doit se terminer proprement pour ne jamais faire planter le
        # process Node qui l'a lancé en détaché.


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
