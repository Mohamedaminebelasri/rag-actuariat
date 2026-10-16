# -*- coding: utf-8 -*-
"""creer_table_catalogue_kpis.py — Crée et remplit la table `catalogue_kpis`
de kpis.db : une ligne par KPI (les 21 extraits + les 6 KPIs calculés de la
Décision 158), pour que l'agent puisse citer un KPI sans lire le front
(problème P9 de ETAT_DES_LIEUX_CHAT.md).

Rien n'est inventé : chaque colonne est recopiée d'une source existante, et
une information absente partout reste NULL.

- `libelle` : le libellé affiché par le front (`labelKpi()`) :
  `KPI_LABELS_REELS` (frontend/src/lib/donnees-extraites-utils.ts) pour les
  21 extraits, `kpi_definitions.KPI_INDICATEURS_OFFICIELS` (exporté tel quel
  dans `definitionsKpis`) pour les 6 calculés. Les libellés de
  `kpi_definitions.KPI_DEFINITIONS` diffèrent pour 17 KPIs et ne sont pas
  affichés.
- `definition` : `DESCRIPTIONS` (frontend/src/data/analyse-demo.ts) pour les
  21 extraits, `description` de `KPI_INDICATEURS_OFFICIELS` pour les 6.
- `unite` : `kpis.unit` (une seule unité par KPI en base : `pct`, `pts`, `M€`).
- `formule` : textes distincts de `kpi_formules` (par société en base),
  séparés par « | » ; NULL pour un KPI sans ligne dans `kpi_formules`.
- `composants` : où lire les composants par société (`kpi_composants`), avec
  le nombre de sociétés et de lignes ; NULL si aucun.
- `sens` : `classement` de `KPI_INDICATEURS_OFFICIELS` pour les 6 calculés,
  `SENS_KPI` (frontend/src/lib/analyse-utils.ts) pour les extraits ; NULL
  ailleurs.

Les fichiers du front sont lus tels quels, jamais modifiés. Idempotent : la
table est réécrite à chaque exécution. Aucune autre table n'est touchée.

    python creer_table_catalogue_kpis.py
"""
import re
import sqlite3
from pathlib import Path

from kpi_definitions import KPI_DEFINITIONS, KPI_INDICATEURS_OFFICIELS

RACINE = Path(__file__).parent
DB_PATH = RACINE / "kpis.db"
FRONT = RACINE / "frontend" / "src"

SQL_CREATION = """
CREATE TABLE IF NOT EXISTS catalogue_kpis (
    kpi_id TEXT PRIMARY KEY,
    libelle TEXT NOT NULL,
    definition TEXT,
    unite TEXT NOT NULL,
    formule TEXT,
    composants TEXT,
    sens TEXT
)
"""


def objet_ts(fichier, nom):
    """{clé: "texte"} d'un objet TypeScript `const NOM ... = { ... };`."""
    texte = (FRONT / fichier).read_text(encoding="utf-8")
    m = re.search(r"const %s\b[^=]*=\s*\{(.*?)\n\};" % nom, texte, re.S)
    if m is None:
        raise ValueError(f"{nom} introuvable dans {fichier}")
    return dict(re.findall(r'^\s*(\w+):\s*"([^"]*)"', m.group(1), re.M))


def main():
    libelles = objet_ts("lib/donnees-extraites-utils.ts", "KPI_LABELS_REELS")
    descriptions = objet_ts("data/analyse-demo.ts", "DESCRIPTIONS")
    sens_front = objet_ts("lib/analyse-utils.ts", "SENS_KPI")
    extraits = [d["kpi_name"] for d in KPI_DEFINITIONS]
    officiels = {d["kpi_name"]: d for d in KPI_INDICATEURS_OFFICIELS}
    if set(libelles) != set(extraits):
        raise ValueError("KPI_LABELS_REELS et KPI_DEFINITIONS ne couvrent pas les mêmes KPIs")

    conn = sqlite3.connect(DB_PATH)
    unites = dict(conn.execute("SELECT kpi_name, MAX(unit) FROM kpis GROUP BY kpi_name"))
    multi = [k for (k,) in conn.execute(
        "SELECT kpi_name FROM kpis GROUP BY kpi_name HAVING COUNT(DISTINCT unit) > 1")]
    if multi:
        raise ValueError(f"plusieurs unités en base pour : {multi}")
    formules = {}
    for k, texte in conn.execute(
            "SELECT kpi_name, texte FROM kpi_formules GROUP BY kpi_name, texte ORDER BY kpi_name, MIN(rowid)"):
        formules.setdefault(k, []).append(texte)
    composants = {k: (n_soc, n_lignes) for k, n_soc, n_lignes in conn.execute(
        "SELECT kpi_name, COUNT(DISTINCT company_id), COUNT(*) FROM kpi_composants GROUP BY kpi_name")}

    lignes = []
    for kpi in extraits + list(officiels):
        off = officiels.get(kpi)
        comp = composants.get(kpi)
        lignes.append((
            kpi,
            off["label"] if off else libelles[kpi],
            off["description"] if off else descriptions.get(kpi),
            unites[kpi],
            " | ".join(formules[kpi]) if kpi in formules else None,
            f"par société dans kpi_composants ({comp[0]} sociétés, {comp[1]} lignes)" if comp else None,
            off["classement"] if off else sens_front.get(kpi),
        ))

    with conn:
        conn.execute(SQL_CREATION)
        conn.execute("DELETE FROM catalogue_kpis")
        conn.executemany("INSERT INTO catalogue_kpis VALUES (?, ?, ?, ?, ?, ?, ?)", lignes)
    n = conn.execute("SELECT COUNT(*) FROM catalogue_kpis").fetchone()[0]
    conn.close()
    print(f"catalogue_kpis : {n} KPIs ({len(extraits)} extraits + {len(officiels)} calculés)")


if __name__ == "__main__":
    main()
