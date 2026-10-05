# -*- coding: utf-8 -*-
"""peupler_composants_ag2r.py — Remplit `kpi_composants` pour les 9
entités AG2R La Mondiale (best_estimate/marge_risque via le mapping
générique `ek.valeur_principale`, primes_acquises_brutes/charge_sinistres
via `resoudre_primes_sinistres_ag2r`, instrumentée de façon additive
dans ag2r_entites.py pour capturer le détail ligne par ligne).

Réutilise EXACTEMENT le même découpage/extraction que
`ag2r_entites.py` (même fonctions, mêmes bornes de page) — aucune
nouvelle lecture de PDF inventée, aucune valeur devinée. Vérifie que
somme(composants) == kpis.value déjà stocké (tolérance 1%/0.5 M€)
avant toute insertion.

    python peupler_composants_ag2r.py
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

import extract_kpis as ek  # noqa: E402
import ag2r_entites as ag  # noqa: E402
from ingest import classify_pages, extraire_entite  # noqa: E402
from batch_diagnostic import construire_qrt_dict_synthetique  # noqa: E402

DB_PATH = BASE_DIR / "kpis.db"
YEAR = ag.YEAR
TOLERANCE_PCT = 1.0
TOLERANCE_ABS_MIN = 0.5  # M€


def traiter_entite(conn, nom, pd, pf, qrt_dict_synth):
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM companies WHERE name=?", (nom,)).fetchone()
    if row is None:
        print(f"  [{nom}] absente de companies — ignorée")
        return
    company_id = row[0]

    sous_pdf = extraire_entite(ag.SOURCE_PDF, pd, pf, nom_entite=nom)
    corpus, _, _ = ag.construire_corpus_entite(sous_pdf, qrt_dict_synth)
    templates_presents = {e["template_id"] for e in corpus}

    # --- best_estimate / marge_risque (mapping générique) ---
    for kpi_name in ("best_estimate", "marge_risque"):
        stored = cur.execute(
            "SELECT value, unit FROM kpis WHERE company_id=? AND year=? AND kpi_name=? AND value IS NOT NULL",
            (company_id, YEAR, kpi_name),
        ).fetchone()
        if stored is None:
            continue
        valeur_stockee, unite = stored
        capturer = []
        try:
            valeur_brute, _, _ = ek.valeur_principale(kpi_name, corpus, templates_presents,
                                                        capturer_composants=capturer)
        except ek.KpiIntrouvable as e:
            print(f"  [{nom}/{kpi_name}] résolution impossible ({e}) — ignoré")
            continue
        _inserer_si_coherent(cur, company_id, kpi_name, capturer, valeur_brute / 1000,
                              valeur_stockee, unite, nom, pd)

    # --- primes_acquises_brutes / charge_sinistres (fonction dédiée AG2R) ---
    pages_qrt = [p for p in classify_pages(sous_pdf) if p["type"] == "qrt"]
    capturer_primes, capturer_sinistres = [], []
    primes, sinistres, n_trouve = ag.resoudre_primes_sinistres_ag2r(
        sous_pdf, pages_qrt, capturer_primes=capturer_primes, capturer_sinistres=capturer_sinistres)
    if n_trouve > 0:
        for kpi_name, capturer, valeur_brute in (
            ("primes_acquises_brutes", capturer_primes, primes),
            ("charge_sinistres", capturer_sinistres, sinistres),
        ):
            stored = cur.execute(
                "SELECT value, unit FROM kpis WHERE company_id=? AND year=? AND kpi_name=? AND value IS NOT NULL",
                (company_id, YEAR, kpi_name),
            ).fetchone()
            if stored is None:
                continue
            valeur_stockee, unite = stored
            _inserer_si_coherent(cur, company_id, kpi_name, capturer, valeur_brute / 1000,
                                  valeur_stockee, unite, nom, pd)


def _inserer_si_coherent(cur, company_id, kpi_name, capturer, valeur_recomposee, valeur_stockee, unite, nom,
                          page_debut):
    """`page_debut` : borne de début du bloc de l'entité dans le document
    combiné (ENTITES_BORNES) — nécessaire pour convertir les pages
    capturées par `construire_corpus_entite()`/`resoudre_primes_sinistres_ag2r()`,
    qui sont RELATIVES au sous-PDF extrait par `extraire_entite()` (1-indexées
    depuis le début du bloc), en pages ABSOLUES du document combiné
    (page_absolue = page_relative + page_debut - 1) — bug trouvé en
    vérifiant VIASANTE Mutuelle/charge_sinistres (composants pointaient
    vers les pages 3/4 du document entier, soit couverture/sommaire/lexique,
    au lieu des pages 219/220 réelles)."""
    if not capturer:
        return
    tolerance = max(abs(valeur_stockee) * TOLERANCE_PCT / 100, TOLERANCE_ABS_MIN)
    if abs(valeur_recomposee - valeur_stockee) > tolerance:
        print(f"  [{nom}/{kpi_name}] ÉCART : recomposé={valeur_recomposee:.3f} vs "
              f"stocké={valeur_stockee:.3f} (tolérance {tolerance:.3f}) — IGNORÉ, rien inséré")
        return
    cur.execute(
        "DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?",
        (company_id, YEAR, kpi_name),
    )
    lignes = []
    for i, c in enumerate(capturer, start=1):
        page_absolue = c["page"] + page_debut - 1 if c["page"] is not None else None
        lignes.append((
            company_id, YEAR, kpi_name, i, c["libelle"] or c["code"],
            c["code"], c["valeur"] / 1000, unite, page_absolue, "+",
        ))
    cur.executemany(
        """INSERT INTO kpi_composants
           (company_id, year, kpi_name, composant_index, composant_label,
            composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        lignes,
    )
    print(f"  [{nom}/{kpi_name}] {len(lignes)} composant(s) insérés "
          f"(recomposé={valeur_recomposee:.3f} vs stocké={valeur_stockee:.3f})")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    qrt_dict_synth = construire_qrt_dict_synthetique(ek.KPI_QRT_MAPPING)
    for nom, pd, pf in ag.ENTITES_BORNES:
        print(f"=== {nom} ===")
        traiter_entite(conn, nom, pd, pf, qrt_dict_synth)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
