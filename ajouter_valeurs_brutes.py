# -*- coding: utf-8 -*-
"""ajouter_valeurs_brutes.py — Ajoute raw_value/raw_unit sur `kpis`
(Décision 110), à côté de value/unit (M€/pct) qui restent inchangés.

CONTEXTE : signalé comme "bug critique" côté frontend/fondateur — en
réalité la conversion K€→M€ existante est mathématiquement correcte
(vérifiée par ~10 décisions ce soir, 094-107), mais l'utilisateur ne
peut nulle part voir le chiffre BRUT tel qu'imprimé dans le PDF source
(ex. Allianz Vie : "4 266 905" en milliers d'euros → stocké 4266,905
M€, correct, mais invisible). Ajout ADDITIF, pas un remplacement —
value/unit restent la source de vérité pour tous les calculs/contrôles
existants (validate_kpis.py, kpi_service.py, etc.), raw_value/raw_unit
ne servent qu'à l'affichage "comme dans le PDF".

Portée : uniquement les KPIs `unit='M€'` (montants) — c'est là que la
conversion (÷1000 ou ÷1 000 000) perd le chiffre brut. Les KPIs `pct`
(ratio_scr, ratio_mcr) restent sans raw_value : aucune perte
d'information équivalente (multiplier par 100 un ratio décimal n'est
pas une conversion d'unité au sens où l'entend le signalement).

Pour les 34 sociétés déjà en base : raw_value est RECONSTRUIT par
arithmétique inverse (value × diviseur connu, depuis unite_source —
Décision 103) plutôt que re-extrait du PDF — reconstruction exacte
(l'insertion d'origine faisait déjà value = raw/diviseur), pas une
nouvelle lecture. `extraire_un_pdf.py` (Décision 106+) est modifié
séparément pour capturer le VRAI raw_value en direct sur toute future
extraction, sans reconstruction.

    python ajouter_valeurs_brutes.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"


def ajouter_colonnes(conn):
    colonnes = {r[1] for r in conn.execute("PRAGMA table_info(kpis)").fetchall()}
    for col in ("raw_value", "raw_unit"):
        if col not in colonnes:
            conn.execute(f"ALTER TABLE kpis ADD COLUMN {col}")
            print(f"  colonne ajoutée : {col}")
        else:
            print(f"  colonne déjà présente : {col}")
    conn.commit()


def diviseur_pour(unite_source):
    if unite_source is None:
        return None
    if unite_source.startswith("euros bruts"):
        return 1_000_000
    if unite_source.startswith("K€"):
        return 1000
    return None  # unite_source ambigu/non vérifié (Décision 107) — pas de reconstruction fiable


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    print("=== ajout des colonnes ===")
    ajouter_colonnes(conn)

    print("\n=== reconstruction (34 sociétés existantes) ===")
    n_maj, n_ambigu, n_skip = 0, 0, 0
    for row in conn.execute(
        """SELECT k.id, k.value, c.unite_source, c.name
           FROM kpis k JOIN companies c ON c.id = k.company_id
           WHERE k.unit = 'M€' AND k.value IS NOT NULL"""
    ):
        kpi_id, value, unite_source, nom = row
        diviseur = diviseur_pour(unite_source)
        if diviseur is None:
            n_ambigu += 1
            continue
        raw_value = value * diviseur
        conn.execute(
            "UPDATE kpis SET raw_value=?, raw_unit=? WHERE id=?",
            (raw_value, unite_source, kpi_id),
        )
        n_maj += 1
    conn.commit()

    n_pct = conn.execute("SELECT COUNT(*) FROM kpis WHERE unit='pct' AND value IS NOT NULL").fetchone()[0]
    print(f"  {n_maj} lignes M€ reconstruites, {n_ambigu} ignorées (unite_source ambigu/non vérifié), "
          f"{n_pct} lignes pct laissées sans raw_value (pas de perte d'unité équivalente)")

    conn.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
