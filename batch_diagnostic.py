# -*- coding: utf-8 -*-
"""batch_diagnostic.py — Diagnostic RAPIDE du pipeline KPI sur tous les
PDF de data/ (Phase 3.10). AUCUN correctif, AUCUNE modification de
code existant, ne s'arrête jamais sur une erreur.

Ne construit PAS de dictionnaire QRT dédié par document (ce que fait
extraire_cnp.py/extraire_macsf.py, à la main, en lisant chaque PDF) —
impossible à faire pour 10+ documents inconnus en temps limité. À la
place, un dictionnaire SYNTHÉTIQUE est construit automatiquement à
partir de TOUTES les variantes déjà accumulées dans kpi_qrt_mapping.py
(Groupama + CNP + MACSF) : mêmes codes R/C, mêmes libellés attendus.
Un KPI dont le template/ligne/colonne ne correspond à AUCUNE variante
connue ressort NULL — c'est le signal diagnostique recherché, pas une
limite cachée.

Portée volontairement réduite pour rester rapide et gratuit :
- Pages QRT en TEXTE NATIF uniquement (extract_qrt_native, PyMuPDF pur).
- Pages QRT image-only NON traitées ici (nécessiteraient Gemini/
  PaddleOCR — coût et temps hors budget d'un diagnostic ×10 documents) —
  comptées et signalées, pas ignorées silencieusement.
"""

import json
import sys
import time
import traceback
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "test_markdrop"))
sys.path.insert(0, str(Path(__file__).parent))

DATA_DIR = Path(__file__).parent / "data"
REPORT_PATH = Path(__file__).parent / "batch_diagnostic_report.json"

EXCLUSIONS = {"ifrs17.pdf", "solva2.pdf"}  # pas des SFCR (doc réglementaire / norme comptable)

# Documents VÉRIFIÉS VISUELLEMENT (rendu image + lecture du texte brut,
# cf. session de diagnostic visuel) comme contenant de vrais tableaux QRT
# complets malgré l'absence de code R0xxx/C0xxx. SEULS ces documents
# passent par l'extraction par libellé — Décision 064 : un test sur MAAF
# a montré que le même mécanisme produit des FAUX POSITIFS sur un
# document purement narratif ("Meilleure estimation" matché dans un
# paragraphe méthodologique, valeur 910 sans rapport avec la réalité) —
# la densité de paires libellé/valeur ne suffit PAS à distinguer les 2 cas
# (347-415 paires dans les 2 catégories). Faute d'un détecteur fiable
# dans le temps imparti, la prudence "NULL si pas sûr" prime : pas de
# tentative d'extraction par libellé sur un document non vérifié à la main.
DOCUMENTS_LIBELLE_VERIFIES = {
    "rapport-solvabilite-maif-2025.pdf", "rapport-solvabilite-maif-2025 (1).pdf",
    "sfcr_covea_2025.pdf",
}

# Décision 070 : documents pour lesquels le pipeline RÉEL dédié
# (extract_kpis.py) résout déjà les pages QRT en image via PaddleOCR +
# cross-validation Gemini (cf. picture_75.png, S.25.05.22 Groupama) — ce
# diagnostic générique, lui, n'a PAS d'étape OCR et les compte comme
# "page_image_non_traitee". Sur ces documents précis, ce signal est un
# FAUX négatif du diagnostic, pas un vrai manque du pipeline : à ne pas
# confondre. Ne pas ajouter un document ici sans vérifier que son
# pipeline dédié résout réellement les KPIs concernés (ne pas deviner).
DOCUMENTS_IMAGE_RESOLUE_PAR_PIPELINE_REEL = {
    "SFCR_2025_Groupe-Groupama.pdf": "extract_kpis.py résout les 5 KPIs SCR via picture_75.png (PaddleOCR + relecture manuelle, Décision antérieure) — voir DECISIONS.md",
}


def lister_pdfs():
    """Tous les PDF de data/, sauf exclusions et doublons exacts (même
    taille en octets — ex. 'rapport-solvabilite-maif-2025 (1).pdf')."""
    vus_tailles = set()
    pdfs = []
    for p in sorted(DATA_DIR.glob("*.pdf")):
        if p.name in EXCLUSIONS:
            continue
        taille = p.stat().st_size
        if taille in vus_tailles:
            continue  # doublon exact, probablement un re-téléchargement
        vus_tailles.add(taille)
        pdfs.append(p)
    return pdfs


def construire_qrt_dict_synthetique(kpi_mapping):
    """1 dictionnaire QRT couvrant TOUS les templates/lignes/colonnes déjà
    vérifiés (Groupama+CNP+MACSF, cf. kpi_qrt_mapping.py) — 1 seule
    sous-feuille par template (suffixe .DIAG), pas de résolution
    multi-sous-feuilles (hors scope d'un diagnostic rapide)."""
    qrt_dict = {}
    for variantes in kpi_mapping.values():
        for v in variantes:
            template = v.get("template")
            if not template:
                continue
            rows = v["row"] if isinstance(v["row"], list) else [v["row"]]
            col = v["col"]
            libelle = v["libelle_attendu"]
            sheet_key = f"{template}.DIAG"
            qrt_dict.setdefault(template, {}).setdefault(sheet_key, {
                "titre": sheet_key, "row_codes": {}, "col_codes": {}, "col_groups": {},
            })
            sheet = qrt_dict[template][sheet_key]
            for r in rows:
                # Bug réel trouvé et corrigé (fix colonnes, cette session) :
                # setdefault() ne gardait que le PREMIER libellé déclaré
                # pour un (template, row) donné — si une variante EN est
                # déclarée avant une variante FR pour le même code (cas
                # réel : S.25.01.22/R0010 a "Market risk" en EN puis
                # "Risque de marché" en FR), extract_qrt_native rapportait
                # TOUJOURS le libellé EN comme "trouvé", faisant échouer
                # le contrôle libelle_attendu de la variante FR même quand
                # la cellule existait réellement (Crédit Agricole : colonne
                # C0110 ajoutée mais toujours NULL, à cause de ce bug, pas
                # d'un problème de colonne). Corrigé en ACCUMULANT tous
                # les libellés connus pour ce code (séparés par " | "),
                # pour que la vérification par sous-chaîne de N'IMPORTE
                # QUELLE variante déclarée passe.
                deja = sheet["row_codes"].get(r, "")
                if libelle not in deja:
                    sheet["row_codes"][r] = f"{deja} | {libelle}" if deja else libelle
            if col != "toutes":
                sheet["col_codes"].setdefault(col, col)
                sheet["col_groups"].setdefault(col, col)
    return qrt_dict


def diagnostiquer_pdf(pdf_path, qrt_dict_synth, ek, extract_qrt_native, classify_pages,
                       detecter_templates, NATIVE_TEXT_THRESHOLD, fitz,
                       extraire_par_libelle=None, KPI_LABELS_FR=None):
    """Traite 1 PDF de bout en bout, capture TOUT. Ne lève jamais."""
    t0 = time.time()
    resultat = {
        "fichier": pdf_path.name, "pages_total": None, "pages_qrt": 0,
        "mode": None, "document_type": None, "scr_method": None,
        "kpis_ok": 0, "kpis_null": [], "kpis_via_libelle": [], "erreurs": [], "problemes": [],
        "pages_images_ignorees": 0, "temps_s": None, "crash": None,
    }
    try:
        doc = fitz.open(str(pdf_path))
        resultat["pages_total"] = doc.page_count
        doc.close()

        classification = classify_pages(pdf_path)
        pages_qrt = [p for p in classification if p["type"] == "qrt"]
        resultat["pages_qrt"] = len(pages_qrt)

        if not pages_qrt:
            resultat["problemes"].append({"type": "QRT_absent", "detail": "0 page QRT détectée par classify_pages()"})
            resultat["temps_s"] = round(time.time() - t0, 1)
            return resultat

        inventaire = detecter_templates(pdf_path)
        resultat["mode"] = inventaire["mode"]
        resultat["document_type"] = inventaire["document_type"]
        resultat["scr_method"] = inventaire["scr_method"]

        doc = fitz.open(str(pdf_path))
        corpus_diag = []
        templates_vus = set()
        for page in pages_qrt:
            template_id = page["template_id"]
            templates_vus.add(template_id)
            if page["n_caracteres"] <= NATIVE_TEXT_THRESHOLD:
                resultat["pages_images_ignorees"] += 1
                probleme = {"type": "page_image_non_traitee", "detail": f"{template_id} page {page['page']}"}
                note_pipeline_reel = DOCUMENTS_IMAGE_RESOLUE_PAR_PIPELINE_REEL.get(pdf_path.name)
                if note_pipeline_reel:
                    probleme["note"] = f"FAUX SIGNAL pour ce document : {note_pipeline_reel}"
                resultat["problemes"].append(probleme)
                continue
            if template_id not in qrt_dict_synth:
                resultat["problemes"].append({"type": "template_inconnu", "detail": template_id, "page": page["page"]})
                continue
            sheet_key = next(iter(qrt_dict_synth[template_id]))
            sheet_dict = qrt_dict_synth[template_id][sheet_key]
            try:
                pdf_page = doc[page["page"] - 1]
                r = extract_qrt_native(pdf_page, sheet_dict, sheet_key)
                corpus_diag.append({
                    "template_id": f"{template_id}.DIAG", "page_source": page["page"],
                    "contenu": {"lignes": r["lignes"]},
                })
                # Colonnes présentes sur la page mais absentes de toute
                # variante connue pour ce template — signal "colonne
                # inconnue" même si la ligne elle-même a été lue.
                cols_connues = set(sheet_dict["col_codes"].keys())
                for code, row in r["lignes"].items():
                    cols_trouvees = set(row["valeurs"].keys())
                    cols_extra = cols_trouvees - cols_connues
                    if cols_extra and not cols_trouvees & cols_connues:
                        resultat["problemes"].append({
                            "type": "colonne_inconnue",
                            "detail": f"{template_id}/{code} : colonnes trouvées {sorted(cols_extra)}, "
                                      f"aucune ne correspond aux colonnes connues {sorted(cols_connues)}",
                        })
            except Exception as e:
                resultat["erreurs"].append({
                    "page": page["page"], "template": template_id,
                    "type": type(e).__name__, "message": str(e)[:200],
                })
        doc.close()

        if inventaire["mode"] == "libelles_francais" and pdf_path.name not in DOCUMENTS_LIBELLE_VERIFIES:
            resultat["problemes"].append({
                "type": "libelle_non_tente_document_non_verifie",
                "detail": "mode=libelles_francais mais document non vérifié visuellement — extraction par "
                          "libellé NON tentée par prudence (cf. Décision 064, risque de faux positifs narratifs)",
            })

        templates_inconnus = templates_vus - set(qrt_dict_synth.keys())
        for t in templates_inconnus:
            pass  # déjà loggé ci-dessus par page

        templates_presents = {e["template_id"] for e in corpus_diag}
        for d in ek.KPI_DEFINITIONS:
            kpi_name = d["kpi_name"]
            if kpi_name == "resultat_technique":
                continue  # NULL par construction (Décision 051), pas un signal diagnostique
            if kpi_name == "provisions_techniques":
                continue  # calculé, pas une cellule QRT directe
            try:
                res = ek.resoudre_variantes_qrt(kpi_name, corpus_diag, templates_presents)
                if res:
                    resultat["kpis_ok"] += 1
                else:
                    resultat["kpis_null"].append(kpi_name)
            except Exception as e:
                resultat["kpis_null"].append(kpi_name)
                resultat["erreurs"].append({"kpi": kpi_name, "type": type(e).__name__, "message": str(e)[:200]})

        # Repli par libellé français (Décision 064, Phase 3.9) — UNIQUEMENT
        # pour les KPIs encore NULL après le mode codes_eiopa (jamais un
        # remplacement, un vrai code R/C reste toujours prioritaire s'il a
        # fonctionné). N'aide QUE les documents ayant de vrais tableaux QRT
        # sans code (MAIF, Covéa, vérifié visuellement) — pour les
        # documents 100% narratifs (MAAF, MMA, etc.), aucun libellé ne sera
        # trouvé nulle part, comportement inchangé (toujours NULL, honnête).
        if (extraire_par_libelle and KPI_LABELS_FR and resultat["kpis_null"]
                and pdf_path.name in DOCUMENTS_LIBELLE_VERIFIES):
            texte_toutes_pages_qrt = "\n".join(p["texte"] for p in pages_qrt)
            encore_null = []
            for kpi_name in resultat["kpis_null"]:
                labels = KPI_LABELS_FR.get(kpi_name)
                if not labels:
                    encore_null.append(kpi_name)
                    continue
                sommer = kpi_name in ("best_estimate", "marge_risque")
                try:
                    v, lbl = extraire_par_libelle(texte_toutes_pages_qrt, labels, sommer_occurrences=sommer)
                except Exception as e:
                    resultat["erreurs"].append({"kpi": kpi_name, "type": type(e).__name__, "message": str(e)[:200]})
                    encore_null.append(kpi_name)
                    continue
                if v is not None:
                    resultat["kpis_ok"] += 1
                    resultat["kpis_via_libelle"].append({"kpi": kpi_name, "libelle": lbl, "valeur": v})
                else:
                    encore_null.append(kpi_name)
            resultat["kpis_null"] = encore_null

    except Exception as e:
        resultat["crash"] = f"{type(e).__name__}: {str(e)[:300]}"
        resultat["erreurs"].append({"type": type(e).__name__, "message": str(e)[:300],
                                     "traceback": traceback.format_exc()[-1000:]})
    resultat["temps_s"] = round(time.time() - t0, 1)
    return resultat


def grouper_problemes(resultats):
    groupes = defaultdict(lambda: {"pdfs": [], "exemples": []})
    for r in resultats:
        for p in r["problemes"]:
            cle = p["type"] if p["type"] != "colonne_inconnue" and p["type"] != "template_inconnu" else f"{p['type']}:{p['detail'].split('/')[0].split(' ')[0]}"
            g = groupes[cle]
            if r["fichier"] not in g["pdfs"]:
                g["pdfs"].append(r["fichier"])
            if len(g["exemples"]) < 3:
                g["exemples"].append({"pdf": r["fichier"], "detail": p["detail"]})
        for e in r["erreurs"]:
            cle = f"exception:{e['type']}"
            g = groupes[cle]
            if r["fichier"] not in g["pdfs"]:
                g["pdfs"].append(r["fichier"])
            if len(g["exemples"]) < 3:
                g["exemples"].append({"pdf": r["fichier"], "detail": e.get("message", "")})
    return dict(groupes)


def main():
    import extract_kpis as ek
    from ingest import classify_pages, extract_qrt_native, NATIVE_TEXT_THRESHOLD
    from detecter_templates import detecter_templates
    from extraire_par_libelle import extraire_par_libelle
    from kpi_labels_fr import KPI_LABELS_FR
    import fitz

    qrt_dict_synth = construire_qrt_dict_synthetique(ek.KPI_QRT_MAPPING)
    print(f"[dictionnaire synthétique] {len(qrt_dict_synth)} templates connus : {sorted(qrt_dict_synth.keys())}\n")

    pdfs = lister_pdfs()
    print(f"{len(pdfs)} PDF à diagnostiquer :")
    for p in pdfs:
        print(f"  - {p.name}")
    print()

    resultats = []
    for i, pdf_path in enumerate(pdfs, 1):
        print(f"[{i}/{len(pdfs)}] {pdf_path.name} ...", end=" ", flush=True)
        r = diagnostiquer_pdf(pdf_path, qrt_dict_synth, ek, extract_qrt_native, classify_pages,
                               detecter_templates, NATIVE_TEXT_THRESHOLD, fitz,
                               extraire_par_libelle=extraire_par_libelle, KPI_LABELS_FR=KPI_LABELS_FR)
        resultats.append(r)
        n_null = len(r["kpis_null"])
        statut = "CRASH" if r["crash"] else f"{r['kpis_ok']}/{r['kpis_ok']+n_null} KPIs"
        print(f"{statut} en {r['temps_s']}s")

    groupes = grouper_problemes(resultats)

    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        json.dump({"resultats": resultats, "problemes_groupes": groupes}, f, ensure_ascii=False, indent=2)

    print(f"\nRapport sauvegardé : {REPORT_PATH}\n")

    print("=" * 130)
    print(f"{'#':3} {'Fichier':45} {'Mode':17} {'Type':10} {'SCR':16} {'KPIs':>8} {'ViaLib':>7} {'NULL':>5} {'Temps':>7}")
    print("=" * 130)
    for i, r in enumerate(resultats, 1):
        total_kpi = r["kpis_ok"] + len(r["kpis_null"])
        kpis_str = f"{r['kpis_ok']}/{total_kpi}" if total_kpi else "-"
        print(f"{i:<3} {r['fichier'][:45]:45} {(r['mode'] or '-')[:17]:17} "
              f"{(r['document_type'] or '-')[:10]:10} {(r['scr_method'] or '-')[:16]:16} "
              f"{kpis_str:>8} {len(r['kpis_via_libelle']):>7} {len(r['kpis_null']):>5} {r['temps_s']:>6}s")

    print("\n" + "=" * 120)
    print("PROBLÈMES GROUPÉS PAR TYPE")
    print("=" * 120)
    for cle, g in sorted(groupes.items(), key=lambda kv: -len(kv[1]["pdfs"])):
        print(f"\nPROBLÈME \"{cle}\" → {len(g['pdfs'])} PDF : {g['pdfs']}")
        for ex in g["exemples"]:
            print(f"    ex. {ex['pdf']} : {ex['detail']}")


if __name__ == "__main__":
    t0 = time.time()
    main()
    print(f"\nTemps total : {time.time()-t0:.1f}s")
