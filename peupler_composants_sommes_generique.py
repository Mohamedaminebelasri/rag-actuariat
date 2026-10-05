# -*- coding: utf-8 -*-
"""peupler_composants_sommes_generique.py — Remplit `kpi_composants` pour
les sociétés dont best_estimate/marge_risque/primes_acquises_brutes/
charge_sinistres passent par le mécanisme GÉNÉRIQUE de
`resoudre_variantes_qrt()`/`sommer_toutes_colonnes()`/
`sommer_cellules_tolerant()` (extract_kpis.py) — PAS une ré-extraction :
on réutilise le corpus déjà construit par chaque script
`extract_kpis_<societe>.py` existant (`construire_corpus*`/
`charger_corpus*`), on relit la MÊME résolution via le mapping, en
activant simplement la capture additive du détail ligne par ligne
(`capturer_composants=...`, ajoutée à extract_kpis.py) — zéro nouvelle
lecture de PDF, zéro changement de la valeur déjà stockée dans `kpis`.

Sociétés couvertes ici : Groupama (extract_kpis.py), Predica, Cardif
Assurance Vie, Cardif Assurances Risques Divers, CNP Assurances, MACSF
prévoyance, MGEN, Sogécap. Chacune : best_estimate/marge_risque
(sommer_cellules_tolerant, 5 lignes R05x0) et primes_acquises_brutes/
charge_sinistres (sommer_toutes_colonnes, lignes R02x0/R1510 ou
R03x0/R1610).

Avant TOUTE insertion : vérifie que somme(composants) == valeur déjà
stockée dans `kpis.value` (tolérance 1% ou 0.5 M€ dans l'absolu, le
plus grand des deux — même tolérance que validate_kpis.py) — si ça ne
colle pas, la société/KPI est ignorée et signalée, JAMAIS un composant
inséré sur une somme qui ne reconstitue pas le total officiel.

    python peupler_composants_sommes_generique.py
"""
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent

# Stub local hors-dépôt (voir ce fichier) pour satisfaire l'import
# `markdrop` fait par test_markdrop/extract_qrt_s05_gemini.py (chemin VLM
# Gemini jamais exercé ici — on ne lit que le texte natif QRT) sans
# installer la vraie dépendance (conflit torch avec le venv RAG existant).
_MARKDROP_STUB = Path(
    r"C:\Users\PC\AppData\Local\Temp\claude\C--Users-PC-Documents-rag-actuariat"
    r"\53a61e33-e73b-46b6-98c5-e27b3b547fb6\scratchpad\markdrop_stub"
)
if _MARKDROP_STUB.exists():
    sys.path.insert(0, str(_MARKDROP_STUB))

sys.path.insert(0, str(BASE_DIR))
sys.path.insert(0, str(BASE_DIR / "test_markdrop"))

import extract_kpis as ek  # noqa: E402

DB_PATH = BASE_DIR / "kpis.db"
TOLERANCE_PCT = 1.0
TOLERANCE_ABS_MIN = 0.5  # M€

KPIS_SOMMES = ("best_estimate", "marge_risque", "primes_acquises_brutes", "charge_sinistres")

# Sociétés où primes_acquises_brutes/charge_sinistres sont des OVERRIDES
# MANUELS documentés (Décision 093/101 — extract_qrt_native() échoue
# silencieusement sur ces pages précises) : la résolution générique
# retombe parfois par COÏNCIDENCE dans la tolérance de 1% (vu en
# pratique sur Crédit Agricole Assurances : 30 510,74 recomposé vs
# 30 255,38 stocké/vérifié, écart 255 K€ < tolérance mais PAS la bonne
# donnée) — à exclure explicitement plutôt que de se fier à la
# tolérance seule. Leurs composants viennent de
# peupler_composants_manuels.py (valeurs déjà vérifiées, documentées en
# commentaire dans les scripts eux-mêmes).
KPIS_SOMMES_EXCLUS_PAR_SOCIETE = {
    "Allianz Vie": {"primes_acquises_brutes", "charge_sinistres"},
    "Crédit Agricole Assurances": {"primes_acquises_brutes", "charge_sinistres"},
}


def _corpus_groupama():
    return ek.charger_corpus()


def _corpus_predica():
    import extract_kpis_predica as m
    return m.construire_corpus_predica()


def _corpus_cardifrd():
    import extract_kpis_cardifrd as m
    return m.construire_corpus()


def _corpus_cardifvie():
    import extract_kpis_cardifvie as m
    return m.construire_corpus()


def _corpus_cnp():
    import extract_kpis_cnp as m
    return m.charger_corpus_cnp()


def _corpus_macsf():
    import extract_kpis_macsf as m
    return m.charger_corpus_macsf()


def _corpus_mgen():
    import extract_kpis_mgen as m
    return m.construire_corpus_mgen()


def _corpus_sogecap():
    import extract_kpis_sogecap as m
    return m.construire_corpus()


def _corpus_allianzvie():
    import extract_kpis_allianzvie as m
    return m.construire_corpus()


def _corpus_creditagricole():
    import extract_kpis_creditagricole as m
    return m.construire_corpus_creditagricole()


SOCIETES = {
    "Groupama": (_corpus_groupama, 1000),
    "Predica": (_corpus_predica, 1000),
    "Cardif Assurance Vie": (_corpus_cardifvie, 1000),
    "Cardif Assurances Risques Divers": (_corpus_cardifrd, 1000),
    "CNP Assurances": (_corpus_cnp, 1000),
    "MACSF prévoyance": (_corpus_macsf, 1000),
    "MGEN": (_corpus_mgen, 1000),
    # Décision 096 : Sogécap est en euros bruts, pas K€ — diviseur
    # 1 000 000 (même constante DIVISEUR_MONTANT que extract_kpis_sogecap.py),
    # pas 1000 comme les autres sociétés texte natif.
    "Sogécap": (_corpus_sogecap, 1_000_000),
    # Allianz Vie / Crédit Agricole : primes_acquises_brutes/charge_sinistres
    # sont des overrides manuels (pas via resoudre_variantes_qrt, cf.
    # Décision 093/101) — seuls best_estimate/marge_risque sont couverts
    # ici ; le reste est résolu séparément (cf. peupler_composants_manuels.py).
    "Allianz Vie": (_corpus_allianzvie, 1000),
    "Crédit Agricole Assurances": (_corpus_creditagricole, 1000),
}


def resoudre_kpi_avec_composants(kpi_name, corpus, templates_presents):
    """Retourne (valeur_brute_totale, [composants]) où chaque composant
    est {"code", "libelle", "valeur" (brute, même unité que valeur_brute_totale),
    "page"}. Lève ek.KpiIntrouvable si rien ne matche."""
    capturer = []
    if kpi_name in ("best_estimate", "marge_risque"):
        valeur, _, _ = ek.valeur_principale(kpi_name, corpus, templates_presents,
                                             capturer_composants=capturer)
        return valeur, capturer
    resultats = ek.resoudre_variantes_qrt(kpi_name, corpus, templates_presents,
                                           capturer_composants=capturer)
    if not resultats:
        raise ek.KpiIntrouvable(f"{kpi_name} : aucune variante ne matche")
    valeur = sum(v for v, _, _ in resultats)
    return valeur, capturer


def traiter_societe(conn, nom, corpus_fn, diviseur):
    cur = conn.cursor()
    row = cur.execute("SELECT id FROM companies WHERE name=?", (nom,)).fetchone()
    if row is None:
        print(f"  [{nom}] absente de companies — ignorée")
        return
    company_id = row[0]

    try:
        corpus = corpus_fn()
    except Exception as e:
        print(f"  [{nom}] corpus indisponible ({type(e).__name__}: {str(e)[:150]}) — ignorée")
        return
    templates_presents = {e["template_id"] for e in corpus}

    exclus = KPIS_SOMMES_EXCLUS_PAR_SOCIETE.get(nom, set())
    for kpi_name in KPIS_SOMMES:
        if kpi_name in exclus:
            continue
        stored = cur.execute(
            "SELECT year, value, unit FROM kpis WHERE company_id=? AND kpi_name=? AND value IS NOT NULL",
            (company_id, kpi_name),
        ).fetchone()
        if stored is None:
            print(f"  [{nom}/{kpi_name}] pas de valeur stockée (NULL) — ignoré")
            continue
        year, valeur_stockee, unite = stored

        try:
            valeur_brute, composants = resoudre_kpi_avec_composants(kpi_name, corpus, templates_presents)
        except ek.KpiIntrouvable as e:
            print(f"  [{nom}/{kpi_name}] résolution générique impossible ({e}) — ignoré "
                  f"(probablement un override manuel scopé au script, hors périmètre générique)")
            continue

        if not composants:
            continue

        valeur_recomposee = valeur_brute / diviseur
        tolerance = max(abs(valeur_stockee) * TOLERANCE_PCT / 100, TOLERANCE_ABS_MIN)
        if abs(valeur_recomposee - valeur_stockee) > tolerance:
            print(f"  [{nom}/{kpi_name}] ÉCART : recomposé={valeur_recomposee:.3f} vs "
                  f"stocké={valeur_stockee:.3f} (tolérance {tolerance:.3f}) — IGNORÉ, rien inséré")
            continue

        cur.execute(
            "DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?",
            (company_id, year, kpi_name),
        )
        lignes = []
        for i, c in enumerate(composants, start=1):
            lignes.append((
                company_id, year, kpi_name, i, c["libelle"] or c["code"],
                c["code"], c["valeur"] / diviseur, unite, c["page"], "+",
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
    for nom, (corpus_fn, diviseur) in SOCIETES.items():
        print(f"=== {nom} ===")
        traiter_societe(conn, nom, corpus_fn, diviseur)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
