# -*- coding: utf-8 -*-
"""peupler_composants_libelles_fr.py — Remplit `kpi_composants` pour
Covéa et MAIF (mode "libellés français", pas de code R/C EIOPA) :
- Covéa : primes_acquises_brutes/charge_sinistres via
  `resoudre_primes_sinistres_covea` (instrumentée additivement) ;
  best_estimate/marge_risque via `extraire_par_libelle(...,
  sommer_occurrences=True)` (instrumentée additivement).
- MAIF : primes_acquises_brutes/charge_sinistres (non-vie uniquement,
  la composante vie de charge_sinistres est explicitement EXCLUE —
  Décision 084, tableau p.114 non parsable, ~1,3% du total, jamais
  deviné) via `extraire_par_libelle` instrumentée ; best_estimate/
  marge_risque sont des valeurs déjà hardcodées et vérifiées dans
  `batch_diagnostic.resoudre_scr_mcr_maif` (p.111, lecture manuelle
  image, Décision 084) — reprises telles quelles dans
  `peupler_composants_manuels.py`, pas ici.

    python peupler_composants_libelles_fr.py
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

_MARKDROP_STUB = Path(
    r"C:\Users\PC\AppData\Local\Temp\claude\C--Users-PC-Documents-rag-actuariat"
    r"\53a61e33-e73b-46b6-98c5-e27b3b547fb6\scratchpad\markdrop_stub"
)
if _MARKDROP_STUB.exists():
    sys.path.insert(0, str(_MARKDROP_STUB))

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "test_markdrop"))

import fitz  # noqa: E402
from ingest import classify_pages  # noqa: E402
from batch_diagnostic import resoudre_primes_sinistres_covea  # noqa: E402
from extraire_par_libelle import extraire_par_libelle, extraire_section  # noqa: E402
from kpi_labels_fr import KPI_LABELS_FR  # noqa: E402

DB_PATH = BASE_DIR / "kpis.db"
YEAR = 2025
TOLERANCE_PCT = 1.0
TOLERANCE_ABS_MIN = 0.5  # M€


def _inserer_si_coherent(cur, company_id, kpi_name, capturer, valeur_recomposee_m, valeur_stockee, unite, nom):
    if not capturer:
        return
    tolerance = max(abs(valeur_stockee) * TOLERANCE_PCT / 100, TOLERANCE_ABS_MIN)
    if abs(valeur_recomposee_m - valeur_stockee) > tolerance:
        print(f"  [{nom}/{kpi_name}] ÉCART : recomposé={valeur_recomposee_m:.3f} vs "
              f"stocké={valeur_stockee:.3f} (tolérance {tolerance:.3f}) — IGNORÉ, rien inséré")
        return
    cur.execute("DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?",
                (company_id, YEAR, kpi_name))
    lignes = [
        (company_id, YEAR, kpi_name, i, c["libelle"] or c["code"], c["code"],
         c["valeur"] / 1000, unite, c["page"], "+")
        for i, c in enumerate(capturer, start=1)
    ]
    cur.executemany(
        """INSERT INTO kpi_composants
           (company_id, year, kpi_name, composant_index, composant_label,
            composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        lignes,
    )
    print(f"  [{nom}/{kpi_name}] {len(lignes)} composant(s) insérés "
          f"(recomposé={valeur_recomposee_m:.3f} vs stocké={valeur_stockee:.3f})")


def traiter_covea(conn):
    nom = "Covéa"
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM companies WHERE name=?", (nom,)).fetchone()
    if row is None:
        print(f"  [{nom}] absente de companies")
        return
    company_id = row[0]
    pdf_path = BASE_DIR / "data" / "sfcr_covea_2025.pdf"
    pages_qrt = [p for p in classify_pages(pdf_path) if p["type"] == "qrt"]

    # --- primes_acquises_brutes / charge_sinistres ---
    capturer_ps = {}
    resoudre_primes_sinistres_covea(pages_qrt, extraire_section, extraire_par_libelle, capturer=capturer_ps)
    for kpi_name in ("primes_acquises_brutes", "charge_sinistres"):
        stored = cur.execute(
            "SELECT value, unit FROM kpis WHERE company_id=? AND year=? AND kpi_name=? AND value IS NOT NULL",
            (company_id, YEAR, kpi_name),
        ).fetchone()
        if stored is None:
            continue
        valeur_stockee, unite = stored
        composants = capturer_ps.get(kpi_name, [])
        total_m = sum(c["valeur"] for c in composants) / 1000
        _inserer_si_coherent(cur, company_id, kpi_name, composants, total_m, valeur_stockee, unite, nom)

    # --- best_estimate / marge_risque (sommer_occurrences) ---
    texte_toutes_pages_qrt = "\n".join(p["texte"] for p in pages_qrt)
    for kpi_name in ("best_estimate", "marge_risque"):
        stored = cur.execute(
            "SELECT value, unit FROM kpis WHERE company_id=? AND year=? AND kpi_name=? AND value IS NOT NULL",
            (company_id, YEAR, kpi_name),
        ).fetchone()
        if stored is None:
            continue
        valeur_stockee, unite = stored
        labels = KPI_LABELS_FR.get(kpi_name)
        if not labels:
            continue
        capturer = []
        extraire_par_libelle(texte_toutes_pages_qrt, labels, sommer_occurrences=True, capturer=capturer)
        total_m = sum(c["valeur"] for c in capturer) / 1000
        _inserer_si_coherent(cur, company_id, kpi_name, capturer, total_m, valeur_stockee, unite, nom)


def traiter_maif(conn):
    nom = "MAIF"
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM companies WHERE name=?", (nom,)).fetchone()
    if row is None:
        print(f"  [{nom}] absente de companies")
        return
    company_id = row[0]
    pdf_path = BASE_DIR / "data" / "rapport-solvabilite-maif-2025.pdf"
    doc = fitz.open(str(pdf_path))

    # Mêmes pages/sous-libellés que batch_diagnostic.resoudre_scr_mcr_maif
    # (Décision 084) — reproduits ici pour CAPTURER le détail, pas
    # réinventés : page 113 = S.05.01.02.01 2/2 (seule avec colonne Total).
    PAGE_NONVIE = 113
    texte_page2 = doc[PAGE_NONVIE - 1].get_text()
    sous_labels_nonvie = ["Brut – assurance directe", "Brut – Réassurance proportionnelle acceptée",
                           "Brut – Réassurance non proportionnelle acceptée"]
    sec_pa = extraire_section(texte_page2, "Primes acquises", "Charge des sinistres")
    sec_cs = extraire_section(texte_page2, "Charge des sinistres", "Dépenses engagées")
    doc.close()

    for kpi_name, section in (("primes_acquises_brutes", sec_pa), ("charge_sinistres", sec_cs)):
        stored = cur.execute(
            "SELECT value, unit FROM kpis WHERE company_id=? AND year=? AND kpi_name=? AND value IS NOT NULL",
            (company_id, YEAR, kpi_name),
        ).fetchone()
        if stored is None:
            continue
        valeur_stockee, unite = stored
        composants = []
        for lbl in sous_labels_nonvie:
            v, used = extraire_par_libelle(section, [lbl], colonne=-1)
            if v is not None:
                composants.append({"code": used, "libelle": used, "valeur": v, "page": PAGE_NONVIE})
        if kpi_name == "charge_sinistres":
            # Décision 084 : composante vie (30 615 K€, p.114) vérifiée
            # visuellement mais NON incluse dans la valeur stockée — pas
            # ajoutée comme composant (romprait somme==valeur stockée),
            # documentée dans le label du 1er composant à la place.
            if composants:
                composants[0]["libelle"] += (
                    " [composante vie (~30 615 K€, p.114) exclue — colonnes rotées non parsable, Décision 084]"
                )
        else:
            composants.append({"code": "vie (p.114)", "libelle": "Primes acquises Brut — Vie (vérifié =0 visuellement)",
                                "valeur": 0.0, "page": 114})
        total_m = sum(c["valeur"] for c in composants) / 1000
        _inserer_si_coherent(cur, company_id, kpi_name, composants, total_m, valeur_stockee, unite, nom)


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    print("=== Covéa ===")
    traiter_covea(conn)
    print("=== MAIF ===")
    traiter_maif(conn)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
