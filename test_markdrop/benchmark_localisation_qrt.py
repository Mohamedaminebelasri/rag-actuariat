# -*- coding: utf-8 -*-
"""benchmark_localisation_qrt.py — Compare 3 méthodes de localisation des
pages QRT dans un SFCR (Phase 3.7 -> CNP, Décision 058), toutes basées
sur PyMuPDF (texte brut, pas de rendering ni Docling — rapide par
construction). Utilisé une fois par document pour choisir la méthode par
défaut, pas relancé 3x en production."""

import re
import time
import fitz

CODE_EIOPA_RE = re.compile(r"S\.\d{2}\.\d{2}")
MOTS_SOMMAIRE_RE = re.compile(r"annexes|QRT|Quantitative Reporting|tableaux r[ée]glementaires", re.IGNORECASE)
PAGE_NUM_RE = re.compile(r"(\d{1,3})\s*$")


def methode_a_sommaire(pdf_path, n_pages_a_lire=5):
    t0 = time.time()
    doc = fitz.open(pdf_path)
    pages_candidates = []
    for i in range(min(n_pages_a_lire, doc.page_count)):
        texte = doc[i].get_text()
        if MOTS_SOMMAIRE_RE.search(texte):
            for ligne in texte.split("\n"):
                if MOTS_SOMMAIRE_RE.search(ligne):
                    m = PAGE_NUM_RE.search(ligne.strip())
                    if m:
                        pages_candidates.append(int(m.group(1)))
    doc.close()
    return {"methode": "A (sommaire)", "temps_s": time.time() - t0, "pages_qrt": sorted(set(pages_candidates))}


def methode_b_scan_fin(pdf_path, n_debut=20, n_max=80):
    t0 = time.time()
    doc = fitz.open(pdf_path)
    n = n_debut
    pages_trouvees = []
    while n <= min(n_max, doc.page_count):
        pages_trouvees = []
        debut = max(0, doc.page_count - n)
        for i in range(debut, doc.page_count):
            texte = doc[i].get_text()
            if CODE_EIOPA_RE.search(texte):
                pages_trouvees.append(i + 1)
        if pages_trouvees and pages_trouvees[0] > debut + 1:
            # la 1re page QRT n'est pas tout au début de la fenêtre —
            # fenêtre probablement suffisante
            break
        n *= 2
    doc.close()
    return {"methode": "B (scan par la fin)", "temps_s": time.time() - t0, "pages_qrt": pages_trouvees}


def methode_c_scan_complet(pdf_path):
    t0 = time.time()
    doc = fitz.open(pdf_path)
    pages_trouvees = []
    for i in range(doc.page_count):
        texte = doc[i].get_text()
        if CODE_EIOPA_RE.search(texte):
            pages_trouvees.append(i + 1)
    doc.close()
    return {"methode": "C (scan complet)", "temps_s": time.time() - t0, "pages_qrt": pages_trouvees}


if __name__ == "__main__":
    import sys
    pdf_path = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\PC\Documents\rag-actuariat\data\sfcr_cnp_assurances_2025.pdf"

    resultats = [methode_a_sommaire(pdf_path), methode_b_scan_fin(pdf_path), methode_c_scan_complet(pdf_path)]

    print(f"{'Méthode':22} {'Temps':>10}  {'N pages QRT':>12}  Pages")
    for r in resultats:
        pages_str = str(r["pages_qrt"][:10]) + ("..." if len(r["pages_qrt"]) > 10 else "")
        print(f"{r['methode']:22} {r['temps_s']*1000:>8.1f}ms  {len(r['pages_qrt']):>12}  {pages_str}")

    ref = set(resultats[2]["pages_qrt"])  # méthode C = référence (scan exhaustif)
    for r in resultats:
        trouve = set(r["pages_qrt"])
        manque = ref - trouve
        r["fiable"] = (len(manque) == 0 and len(trouve) > 0)
        print(f"  {r['methode']:22} fiable={r['fiable']}  (manque {len(manque)}/{len(ref)} pages vs référence C)")
