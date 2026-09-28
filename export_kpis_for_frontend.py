# -*- coding: utf-8 -*-
"""export_kpis_for_frontend.py — Exporte kpis.db vers 2 JSON statiques
consommés par le frontend :
- frontend/src/data/kpi-sources.json (export_kpis(), existant)
- frontend/src/data/donnees-extraites.json (export_donnees_extraites(),
  Décision 106 — l'onglet "Base de données" lisait jusqu'ici un snapshot
  généré une fois par une requête SQL ad hoc, jamais par un script
  commité/rejouable ; c'est ce générateur qui en tient désormais lieu).

Pourquoi un export statique plutôt qu'une connexion live SQLite depuis
Next.js : évite une dépendance native (better-sqlite3) dont la
compilation peut échouer sur cet environnement Windows sans toolchain
de build, pour des données qui ne changent pas à chaque requête. À
re-exécuter après chaque mise à jour de kpis.db (ex. après une
extraction/insertion d'un nouvel assureur) pour garder le frontend à
jour — automatique depuis extraire_un_pdf.py (Décision 106), toujours
disponible en manuel sinon (`python export_kpis_for_frontend.py`).
"""
import json
import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"
OUT_PATH = Path(__file__).parent / "frontend" / "src" / "data" / "kpi-sources.json"
OUT_PATH_DONNEES = Path(__file__).parent / "frontend" / "src" / "data" / "donnees-extraites.json"

# Membres des 2 groupes multi-entités (mêmes listes que populate_company_metadata.py,
# Décision 103) — toute société absente des 2 est indépendante (groupe=None),
# ce qui inclut par construction toute nouvelle société ajoutée via
# extraire_un_pdf.py (jamais dans ces listes).
AG2R_MEMBRES = {
    "AG.Mut", "AG2R Prevoyance", "Arpege Prevoyance", "Prima", "VIASANTE Mutuelle",
    "La Mondiale", "La Mondiale Europartner", "La Mondiale Partenaire", "SGAM AG2R LA MONDIALE",
}
AEMA_MEMBRES = {
    "MACIF SAM", "Macif Vie", "Macif Sante Prevoyance", "Themis", "Macifilia",
    "Aesio Mutuelle", "MNPAF", "MMJ", "Nuoma", "Abeille Vie",
    "Abeille Epargne Retraite", "Abeille IARD Sante", "Aema Groupe",
}


def _groupe_pour(nom_societe):
    if nom_societe in AG2R_MEMBRES:
        return "Groupe AG2R La Mondiale"
    if nom_societe in AEMA_MEMBRES:
        return "Aéma Groupe"
    return None


def export_kpis():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    companies = {row["id"]: row["name"] for row in conn.execute("SELECT id, name FROM companies")}

    resultat = {}
    for row in conn.execute(
        """SELECT company_id, year, kpi_name, value, unit, source_page, source_chapter, raw_value, raw_unit
           FROM kpis WHERE value IS NOT NULL ORDER BY company_id, year DESC"""
    ):
        nom_entreprise = companies.get(row["company_id"])
        if nom_entreprise is None:
            continue
        entreprise = resultat.setdefault(nom_entreprise, {})
        # garde la 1re occurrence par kpi_name = l'année la plus récente
        # (ORDER BY year DESC), n'écrase pas si un doublon d'année existe
        entreprise.setdefault(
            row["kpi_name"],
            {
                "value": row["value"],
                "unit": row["unit"],
                "year": row["year"],
                "source_page": row["source_page"],
                "source_chapter": row["source_chapter"],
                # Décision 110 — chiffre brut tel qu'imprimé dans le PDF
                # (avant ÷1000/÷1 000 000), None pour les KPIs pct.
                "raw_value": row["raw_value"],
                "raw_unit": row["raw_unit"],
            },
        )
    conn.close()

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(resultat, f, ensure_ascii=False, indent=2)

    n_entreprises = len(resultat)
    n_kpis = sum(len(v) for v in resultat.values())
    print(f"Exporté {n_kpis} KPIs pour {n_entreprises} entreprises -> {OUT_PATH}")


def export_donnees_extraites():
    """Génère donnees-extraites.json — même filtre (value IS NOT NULL)
    et même forme que le snapshot déjà consommé par l'onglet "Base de
    données" (commit 2a71854), pour rester un remplacement transparent."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    societes = []
    kpis_par_societe = {}
    for c in conn.execute("SELECT * FROM companies ORDER BY name"):
        groupe = _groupe_pour(c["name"])
        # companies.type a dérivé depuis le commit 2a71854 : la valeur en
        # base porte désormais un suffixe "(Nom du groupe)" que le JSON
        # ALORS committé (et donc le frontend actuellement déployé) n'a
        # jamais eu — société.type est affiché tel quel côté frontend
        # (base-donnees/page.tsx:179). On retire ce suffixe s'il est déjà
        # présent pour reproduire fidèlement l'affichage actuellement en
        # place plutôt que de le changer silencieusement via un export.
        type_brut = c["type"]
        suffixe = f" ({groupe})"
        if groupe and type_brut.endswith(suffixe):
            type_brut = type_brut[: -len(suffixe)]
        societes.append({
            "id": c["id"],
            "name": c["name"],
            "type": type_brut,
            "groupe": groupe,
            "country": c["country"],
        })
        kpis_par_societe[c["name"]] = {}

    id_vers_nom = {s["id"]: s["name"] for s in societes}
    for row in conn.execute(
        """SELECT company_id, year, kpi_name, value, unit, category, source_page, source_chapter, validated, raw_value, raw_unit
           FROM kpis WHERE value IS NOT NULL ORDER BY company_id, year DESC"""
    ):
        nom = id_vers_nom.get(row["company_id"])
        if nom is None:
            continue
        # 1re occurrence par kpi_name = année la plus récente (ORDER BY year DESC),
        # même convention que export_kpis() ci-dessus.
        kpis_par_societe[nom].setdefault(row["kpi_name"], {
            "valeur": row["value"],
            "unite": row["unit"],
            "categorie": row["category"],
            "annee": row["year"],
            "pageSource": row["source_page"],
            "chapitreSource": row["source_chapter"],
            "valide": bool(row["validated"]),
            # Décision 110 — chiffre brut tel qu'imprimé dans le PDF
            # (avant ÷1000/÷1 000 000), None pour les KPIs pct.
            "valeurBrute": row["raw_value"],
            "uniteBrute": row["raw_unit"],
        })
    conn.close()

    export = {
        "genereLe": datetime.now().replace(microsecond=0).isoformat(),
        "societes": societes,
        "kpisParSociete": kpis_par_societe,
    }

    OUT_PATH_DONNEES.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH_DONNEES, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    n_kpis = sum(len(v) for v in kpis_par_societe.values())
    print(f"Exporté {n_kpis} KPIs pour {len(societes)} sociétés -> {OUT_PATH_DONNEES}")


if __name__ == "__main__":
    export_kpis()
    export_donnees_extraites()
