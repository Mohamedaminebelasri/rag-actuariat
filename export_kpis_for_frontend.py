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

import comparabilite
import corrections_comparabilite
from kpi_definitions import CATEGORIE_INDICATEURS, KPI_INDICATEURS_OFFICIELS, LIBELLE_CATEGORIE_INDICATEURS

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
        """SELECT company_id, year, kpi_name, value, unit, source_page, source_chapter, raw_value, raw_unit,
                  source_pdf, avertissement, note_avertissement
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
                # Décision 145 — cf. export_donnees_extraites() ci-dessous,
                # même sémantique (None = PDF par défaut de la société).
                "source_pdf": row["source_pdf"],
                "avertissement": bool(row["avertissement"]),
                "note_avertissement": row["note_avertissement"],
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
            # Décision 113 (nuit) — pas encore exposés jusqu'ici alors que
            # déjà réels en base depuis Décision 103 (pas des valeurs de
            # démo) : l'onglet Analyse en a besoin pour filtrer/avertir
            # sur la comparabilité entre sociétés.
            "typeActivite": c["type_activite"],
            "scrMethod": c["scr_method"],
            # Décisions 149/153 — métadonnées contrôlées (populate_company_metadata.py)
            # et groupe de pairs (activité × modèle × périmètre).
            "formeJuridique": c["forme_juridique"],
            "familleJuridique": c["famille_juridique"],
            "perimetre": c["type_document"],
            "modeleCapital": comparabilite.libelle_modele(c["scr_method"]),
            "groupeParent": c["groupe_parent"],
            "consolideDans": c["groupe_consolide_panel"],
            "groupePairs": comparabilite.groupe_pairs(c["type_activite"], c["scr_method"], c["type_document"]),
        })
        kpis_par_societe[c["name"]] = {}

    # Composants des KPIs "somme" (best_estimate, marge_risque,
    # primes_acquises_brutes, charge_sinistres, provisions_techniques —
    # table `kpi_composants`), regroupés par (company_id, year, kpi_name)
    # — pas de valeur devinée : un KPI sans ligne dans `kpi_composants`
    # reste `estCompose=False`, jamais un composant inventé.
    # Décision 158 — KPIs calculés : règle de calcul (kpi_formules) et
    # colonnes de composant ajoutées (NULL pour les composants « somme »).
    colonnes_composants = {r[1] for r in conn.execute("PRAGMA table_info(kpi_composants)")}
    colonnes_158 = ("kpi_code", "composant_detail", "composant_source_pdf", "composant_valide")
    avec_158 = all(c in colonnes_composants for c in colonnes_158)
    formules = {}
    if conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='kpi_formules'").fetchone()[0]:
        for row in conn.execute("SELECT * FROM kpi_formules"):
            formule = {"type": row["type"], "texte": row["texte"], "facteur": row["facteur"]}
            if row["note"]:
                formule["note"] = row["note"]
            formules[(row["company_id"], row["year"], row["kpi_name"])] = formule

    composants_par_cle = {}
    for row in conn.execute(
        f"""SELECT company_id, year, kpi_name, composant_label, composant_code_qrt,
                  composant_valeur, composant_unite, composant_page, operation
                  {', ' + ', '.join(colonnes_158) if avec_158 else ''}
           FROM kpi_composants ORDER BY company_id, year, kpi_name, composant_index"""
    ):
        cle = (row["company_id"], row["year"], row["kpi_name"])
        composant = {
            "label": row["composant_label"],
            "codeQrt": row["composant_code_qrt"],
            "valeur": row["composant_valeur"],
            "unite": row["composant_unite"],
            "pageSource": row["composant_page"],
            "operation": row["operation"],
        }
        if cle in formules and avec_158:
            # Composant d'un KPI calculé (Décision 158) : clés présentes
            # seulement ici, les composants « somme » restent inchangés.
            if row["kpi_code"]:
                composant["kpiCode"] = row["kpi_code"]
            if row["composant_detail"]:
                composant["detail"] = row["composant_detail"]
            # null = PDF par défaut de la société (pas celui du KPI).
            composant["sourcePdf"] = row["composant_source_pdf"]
            composant["valide"] = bool(row["composant_valide"])
        composants_par_cle.setdefault(cle, []).append(composant)

    id_vers_nom = {s["id"]: s["name"] for s in societes}
    for row in conn.execute(
        """SELECT company_id, year, kpi_name, value, unit, category, source_page, source_chapter, validated,
                  raw_value, raw_unit, source_pdf, avertissement, note_avertissement
           FROM kpis WHERE value IS NOT NULL ORDER BY company_id, year DESC"""
    ):
        nom = id_vers_nom.get(row["company_id"])
        if nom is None:
            continue
        composants = composants_par_cle.get((row["company_id"], row["year"], row["kpi_name"]))
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
            # KPIs composés (somme de sous-lignes QRT) — composants=None
            # tant qu'ils n'ont pas été vérifiés/insérés dans
            # `kpi_composants` (peupler_composants_*.py), jamais déduits.
            "estCompose": composants is not None,
            "composants": composants,
            # Décision 145 — PDF spécifique à CE KPI quand il diffère du
            # PDF par défaut de la société (PDF_PAR_SOCIETE côté
            # front-end) ; None = utiliser le PDF par défaut, comme pour
            # tous les KPIs qui ne surchargent rien.
            "sourcePdf": row["source_pdf"],
            # Décision 145 — KPI calculé sur une base non comparable aux
            # autres sociétés (ex. modèle interne, avant diversification/
            # impôt) : signalé à l'utilisateur côté front-end plutôt que
            # masqué ou laissé NULL. False/None pour l'immense majorité.
            "avertissement": bool(row["avertissement"]),
            "noteAvertissement": row["note_avertissement"],
        })
        if row["avertissement"]:
            # Décision 158 (bonus) — « Source : » en français simple ;
            # chapitreSource garde la base technique (Décision 157).
            lisible = corrections_comparabilite.source_lisible(nom, row["kpi_name"])
            if lisible and kpis_par_societe[nom][row["kpi_name"]]["annee"] == row["year"]:
                kpis_par_societe[nom][row["kpi_name"]]["sourceLisible"] = lisible
        formule = formules.get((row["company_id"], row["year"], row["kpi_name"]))
        if formule is not None and kpis_par_societe[nom][row["kpi_name"]]["annee"] == row["year"]:
            # Décision 158 — absent pour les KPIs « somme » (inchangés).
            kpis_par_societe[nom][row["kpi_name"]]["formule"] = formule
    # Décision 155 — impact des mesures de long terme (S.22.01), par société.
    impact_lt = {r["name"]: dict(r) for r in conn.execute(
        "SELECT c.name, i.* FROM impact_mesures_lt i JOIN companies c ON c.id = i.company_id WHERE i.year = 2025")}
    conn.close()

    # Décision 153 — libellé propre au « MCR » d'un groupe (ce n'en est pas un).
    for s in societes:
        if s["perimetre"] == "groupe":
            for kpi, libelle in (("mcr", "SCR minimal consolidé du groupe"),
                                 ("ratio_mcr", "Ratio de couverture du SCR minimal consolidé")):
                if kpi in kpis_par_societe[s["name"]]:
                    kpis_par_societe[s["name"]][kpi]["libelle"] = libelle

    # Décision 153 — indicateurs normalisés, groupes de pairs, matrice.
    indicateurs = {}
    for s in societes:
        kp = kpis_par_societe[s["name"]]
        valeurs = {k: v["valeur"] for k, v in kp.items()}
        comp = {k: [(c["codeQrt"], c["label"], c["valeur"]) for c in (v.get("composants") or [])] for k, v in kp.items()}
        indicateurs[s["name"]] = comparabilite.indicateurs(valeurs, comp, s["perimetre"], s["scrMethod"],
                                                           impact_lt.get(s["name"]))
    groupes = {}
    for s in societes:
        groupes.setdefault(s["groupePairs"], []).append(s["name"])

    export = {
        "genereLe": datetime.now().replace(microsecond=0).isoformat(),
        "societes": societes,
        "kpisParSociete": kpis_par_societe,
        "indicateursParSociete": indicateurs,
        "definitionsIndicateurs": comparabilite.DEFINITIONS_INDICATEURS,
        # Décision 158 — libellé, unité, catégorie, description et sens de
        # classement des KPIs calculés (kpi_definitions.KPI_INDICATEURS_OFFICIELS).
        "definitionsKpis": {
            d["kpi_name"]: {"label": d["label"], "unite": d["unit"], "categorie": CATEGORIE_INDICATEURS,
                            "libelleCategorie": LIBELLE_CATEGORIE_INDICATEURS, "description": d["description"],
                            "classement": d["classement"], "indicateur": d["indicateur"]}
            for d in KPI_INDICATEURS_OFFICIELS
        },
        "groupesPairs": [{"id": g, "societes": sorted(n), "n": len(n), "petitEchantillon": len(n) < 5}
                         for g, n in sorted(groupes.items(), key=lambda x: -len(x[1]))],
        "compatibilite": {
            "axes": list(comparabilite.AXES),
            "ordreVerdicts": comparabilite.ORDRE_VERDICTS,
            "classeSinistres": comparabilite.CLASSE_SINISTRES,
            "regle": "Pour un KPI et deux sociétés : pire verdict parmi les axes où elles diffèrent "
                     "(axe activité de charge_sinistres : comparer classeSinistres, pas l'activité brute).",
            "matrice": comparabilite.MATRICE,
            # Décision 158 — hors de ces activités, le KPI n'entre dans aucune comparaison.
            "activitesApplicables": comparabilite.ACTIVITES_APPLICABLES,
        },
    }

    OUT_PATH_DONNEES.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH_DONNEES, "w", encoding="utf-8") as f:
        json.dump(export, f, ensure_ascii=False, indent=2)

    n_kpis = sum(len(v) for v in kpis_par_societe.values())
    print(f"Exporté {n_kpis} KPIs pour {len(societes)} sociétés -> {OUT_PATH_DONNEES}")


if __name__ == "__main__":
    export_kpis()
    export_donnees_extraites()
