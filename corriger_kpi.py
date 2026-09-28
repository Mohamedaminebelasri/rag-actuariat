# -*- coding: utf-8 -*-
"""corriger_kpi.py — Applique une correction manuelle saisie via le bouton
"Corriger" du modal KPI (frontend/src/components/donnees/kpi-pdf-modal.tsx,
Décision 111). Appelé synchronement par frontend/src/app/api/kpi/correct/
route.ts (child_process.execFile) — répond en JSON sur stdout, jamais
d'exception non gérée (toujours {"ok": false, "erreur": "..."} sur échec).

POINT IMPORTANT — l'utilisateur saisit la valeur BRUTE, pas M€ :
le champ "Valeur corrigée" du modal est juxtaposé à l'affichage de
kpi.valeurBrute (formatValeurBrute(), Décision 110 — "54 487 486 K€",
PAS "54,49 M€") avec un placeholder de la même forme ("Ex : 54 487
486"). La valeur saisie est donc traitée comme le nouveau raw_value,
dans l'unité déjà connue (raw_unit, K€/euros bruts) — reconvertie vers
value (M€) par la même arithmétique que le reste du pipeline, jamais
stockée telle quelle dans `value`. Pour un KPI sans raw_value (pct,
ratio_scr/ratio_mcr — formatValeurBrute() retombe alors sur
l'affichage M€/pct), la saisie représente directement la nouvelle
`value` dans son unité native, aucune conversion.

    python corriger_kpi.py --societe "..." --kpi-name "..." \
        --valeur-corrigee "54 487 486" --commentaire "..."
"""
import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"


def diviseur_pour_raw_unit(raw_unit):
    if raw_unit is None:
        return None
    if raw_unit.startswith("euros bruts") or raw_unit == "€":
        return 1_000_000
    if raw_unit.startswith("K€"):
        return 1000
    return None


def parser_nombre_fr(texte):
    """'54 487 486' / '54 487 486,5' / '54487486' / '54487486.5' -> float.
    Espaces (normaux ou insécables) = séparateur de milliers, retirés ;
    UNE seule virgule = séparateur décimal FR, convertie en point. Lève
    ValueError si le texte ne ressemble à aucun de ces formats (jamais un
    nombre deviné sur un texte ambigu)."""
    nettoye = texte.strip().replace(" ", " ").replace("\xa0", " ")
    nettoye = re.sub(r"(?<=\d) (?=\d)", "", nettoye)  # espaces entre chiffres = milliers
    nettoye = nettoye.replace(" ", "")
    if nettoye.count(",") == 1 and "." not in nettoye:
        nettoye = nettoye.replace(",", ".")
    return float(nettoye)


def corriger(societe, kpi_name, valeur_corrigee_brute, commentaire):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    row_company = conn.execute("SELECT id FROM companies WHERE name=?", (societe,)).fetchone()
    if row_company is None:
        return {"ok": False, "erreur": f"Société introuvable : {societe!r}"}
    company_id = row_company[0]

    # Dernière année connue pour ce (company_id, kpi_name) — même convention
    # que export_kpis_for_frontend.py (ORDER BY year DESC), cohérent avec ce
    # que le frontend affiche déjà (1 seule valeur par KPI, la plus récente).
    ligne = conn.execute(
        "SELECT year, value, unit, raw_value, raw_unit FROM kpis WHERE company_id=? AND kpi_name=? ORDER BY year DESC LIMIT 1",
        (company_id, kpi_name),
    ).fetchone()
    if ligne is None:
        return {"ok": False, "erreur": f"KPI introuvable : {kpi_name!r} pour {societe!r}"}
    year, ancienne_valeur, unit, ancien_raw_value, raw_unit = ligne

    try:
        nombre_saisi = parser_nombre_fr(valeur_corrigee_brute)
    except ValueError:
        return {"ok": False, "erreur": f"Valeur saisie non numérique : {valeur_corrigee_brute!r}"}

    diviseur = diviseur_pour_raw_unit(raw_unit) if unit == "M€" else None
    if diviseur is not None:
        # Saisie = nouveau chiffre brut (comme affiché) -> reconverti en M€,
        # même identité arithmétique que Décision 110 (value = raw/diviseur).
        nouveau_raw_value = nombre_saisi
        nouvelle_value = nombre_saisi / diviseur
    else:
        # Pas de raw_value pour ce KPI (pct, ou M€ sans raw_unit connu) —
        # la saisie représente directement la nouvelle value native.
        nouveau_raw_value = None
        nouvelle_value = nombre_saisi

    conn.execute(
        """INSERT INTO corrections (company_id, kpi_name, year, ancienne_valeur, ancienne_unite, nouvelle_valeur, commentaire)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (company_id, kpi_name, year, ancienne_valeur, unit, valeur_corrigee_brute, commentaire),
    )
    conn.execute(
        """UPDATE kpis SET value=?, validated=1, raw_value=COALESCE(?, raw_value)
           WHERE company_id=? AND year=? AND kpi_name=?""",
        (nouvelle_value, nouveau_raw_value, company_id, year, kpi_name),
    )
    conn.commit()
    conn.close()

    return {
        "ok": True,
        "ancienneValeur": ancienne_valeur,
        "nouvelleValeur": nouvelle_value,
        "nouveauRawValue": nouveau_raw_value,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--societe", required=True)
    parser.add_argument("--kpi-name", required=True, dest="kpi_name")
    parser.add_argument("--valeur-corrigee", required=True, dest="valeur_corrigee")
    parser.add_argument("--commentaire", default=None)
    args = parser.parse_args()

    try:
        resultat = corriger(args.societe, args.kpi_name, args.valeur_corrigee, args.commentaire)
    except Exception as e:
        resultat = {"ok": False, "erreur": f"Erreur inattendue : {e}"}

    print(json.dumps(resultat, ensure_ascii=False))


if __name__ == "__main__":
    main()
