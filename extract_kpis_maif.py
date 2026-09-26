# -*- coding: utf-8 -*-
"""extract_kpis_maif.py — Extraction réelle des 22 KPIs MAIF 2025,
insertion dans kpis.db.

Document en mode="libelles_francais" (pas de codes R/C standard EIOPA) —
contrairement à Predica/MGEN/Crédit Agricole/Sogécap/Cardif (natif
codes_eiopa), MAIF passe par `resoudre_scr_mcr_maif()`
(`batch_diagnostic.py`, Décision 074/084), déjà construite et vérifiée
manuellement page par page : lit les pages narratives S.23.01.01
équivalentes (106-108, "Gestion du capital"), la page S.23.01.01 réelle
(121, pour fonds_propres_t1_nr), et les pages S.02.01.02/S.05.01.02
(111-114) pour best_estimate/marge_risque/primes/charge_sinistres —
toutes ces valeurs déjà croisées manuellement (Décision 074/084),
reprises ici SANS relecture (aucune nouvelle valeur devinée, uniquement
la fonction déjà éprouvée, appelée et insérée).

Irréductibles CONFIRMÉS, restent NULL (Décision 074/084, jamais forcés) :
- fonds_propres_t1_r/t2/t3 : colonnes vides sans placeholder sur
  S.23.01.01, ambigu entre "0" et "non imprimé".
- charge_sinistres exclut la composante vie (30 615 K€, ~1,3% du total,
  tableau p.114 en colonnes rotées non parsable) — DOCUMENTÉ dans la
  note, pas une exclusion silencieuse.

    python extract_kpis_maif.py
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "test_markdrop"))

import extract_kpis as ek  # noqa: E402
from batch_diagnostic import resoudre_scr_mcr_maif  # noqa: E402
from extraire_par_libelle import extraire_par_libelle  # noqa: E402
import fitz  # noqa: E402

COMPANY_NAME = "MAIF"
COMPANY_TYPE = "mutuelle"
YEAR = 2025
PDF_PATH = BASE_DIR / "data" / "rapport-solvabilite-maif-2025.pdf"


def extraire_tout():
    resultats = resoudre_scr_mcr_maif(PDF_PATH, fitz, extraire_par_libelle)

    # resoudre_scr_mcr_maif() retourne les valeurs BRUTES telles que lues
    # (K€ pour les montants — vérifié par cohérence : fonds_propres_
    # eligibles/scr_total×100 = 5 329 707/2 344 989×100 = 227,28%, très
    # proche du ratio_scr brut lu 2,27×100 = 227% — donc K€, pas €
    # bruts, contrairement à Sogécap/Décision 096 ; décimal fraction pour
    # les ratios — ex. "2,27" imprimé signifie 227%, pas 2,27%). Conversion
    # ici, jamais dans la fonction partagée (qui reste utilisée telle
    # quelle par batch_diagnostic.py pour le comptage diagnostic, pas
    # touchée pour éviter toute régression sur son usage existant).
    RATIOS = {"ratio_scr", "ratio_mcr"}
    valeurs = {}
    for kpi_name, (v, note) in resultats.items():
        if v is None:
            valeurs[kpi_name] = (None, None, "non résolu (resoudre_scr_mcr_maif)")
        elif kpi_name in RATIOS:
            valeurs[kpi_name] = (v * 100, None, f"{note} — ×100 (décimal fraction -> points de %)")
        else:
            valeurs[kpi_name] = (v / 1000, None, f"{note} — ÷1000 (K€ -> M€, vérifié par cohérence ratio_scr)")

    # Irréductibles confirmés (Décision 074/084) — jamais tentés, jamais
    # forcés à 0 (ambigu entre "0" et "non imprimé" sur le document).
    for kpi_name in ("fonds_propres_t1_r", "fonds_propres_t2", "fonds_propres_t3"):
        if kpi_name not in valeurs or valeurs[kpi_name][0] is None:
            valeurs[kpi_name] = (None, None,
                "irréductible confirmé (Décision 074) : colonne vide sans placeholder sur S.23.01.01 p.121, "
                "ambigu entre 0 et non-imprimé — NULL plutôt que deviné")

    if valeurs.get("best_estimate", (None,))[0] is not None and valeurs.get("marge_risque", (None,))[0] is not None:
        valeurs["provisions_techniques"] = (
            valeurs["best_estimate"][0] + valeurs["marge_risque"][0],
            valeurs["best_estimate"][1], "best_estimate + marge_risque",
        )
    else:
        valeurs["provisions_techniques"] = (None, None, "best_estimate ou marge_risque NULL")

    valeurs["resultat_technique"] = (None, None, "aucun équivalent standardisé (cohérent avec les autres sociétés)")

    # Complète les 22 : toute clé absente de resoudre_scr_mcr_maif() est NULL.
    defs_par_nom = {d["kpi_name"]: d for d in ek.KPI_DEFINITIONS}
    for kpi_name in defs_par_nom:
        if kpi_name not in valeurs:
            valeurs[kpi_name] = (None, None, "non couvert par resoudre_scr_mcr_maif()")

    return valeurs


def inserer_en_base(valeurs):
    conn = sqlite3.connect(ek.DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("INSERT OR IGNORE INTO companies (name, type, country) VALUES (?, ?, 'France')", (COMPANY_NAME, COMPANY_TYPE))
    conn.commit()
    company_id = conn.execute("SELECT id FROM companies WHERE name = ?", (COMPANY_NAME,)).fetchone()[0]

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
            (company_id, YEAR, d["category"], kpi_name, valeur, d["unit"], source_page, d["sfcr_chapter"]),
        )
        lignes_resume.append((kpi_name, d["category"], valeur, d["unit"], source_page, note))
    conn.commit()
    conn.close()
    return lignes_resume


def afficher_resume(lignes_resume):
    print("\n" + "=" * 100)
    print(f"RÉSUMÉ — 22 KPIs {COMPANY_NAME} 2025")
    print("=" * 100)
    print(f"  {'kpi_name':28} {'catégorie':14} {'valeur':>14} {'unité':6} {'page':5}  source")
    n_null = 0
    for kpi_name, categorie, valeur, unite, page, note in lignes_resume:
        if valeur is None:
            n_null += 1
            val_str = "NULL"
        else:
            val_str = f"{valeur:,.2f}"
        print(f"  {kpi_name:28} {categorie:14} {val_str:>14} {unite:6} {str(page or '-'):5}  {note}")
    print(f"\n  Total : {len(lignes_resume)} KPIs, {len(lignes_resume) - n_null} valeurs, {n_null} NULL")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    valeurs = extraire_tout()
    lignes_resume = inserer_en_base(valeurs)
    afficher_resume(lignes_resume)
