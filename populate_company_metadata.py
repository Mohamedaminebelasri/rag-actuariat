# -*- coding: utf-8 -*-
"""populate_company_metadata.py — Source de vérité UNIQUE des métadonnées
des 41 sociétés de `companies` (Décision 103, refondue en Décision 149).

À rejouer après toute (ré)extraction : il écrase les métadonnées posées
par les scripts extract_kpis_*.py / aema_entites.py par les valeurs
contrôlées ci-dessous.

Colonnes écrites :
- `type` : forme juridique courte, affichée telle quelle par le front-end
  (SA, SE, SAM, Mutuelle, Union de mutuelles, Institution de prévoyance,
  Groupe). Ne mélange plus forme juridique et appartenance à un groupe.
- `forme_juridique` : libellé complet ; `famille_juridique` : regroupement
  pour l'analyse (SA/SE, SAM, Mutuelle/UM (code mutualité), Institution
  de prévoyance, Groupe).
- `type_document` : périmètre du rapport, `solo` ou `groupe`.
- `scr_method` : `formule_standard`, `modele_interne_partiel`,
  `modele_interne_complet`.
- `type_activite` : Vie / Non-vie / Santé/prévoyance / Mixte.
- `country`, `unite_source`.
- `groupe_parent` : groupe économique d'appartenance (NULL si non vérifié).
- `groupe_consolide_panel` : nom de la société du panel qui CONSOLIDE
  déjà celle-ci (double comptage dans toute moyenne de panel), sinon NULL.

Méthode de contrôle (diagnostic du 15/10/2026, RAPPORT_comparabilite_KPIs.md
§ 2 et comparabilite_metadonnees_41.csv) :
- périmètre et modèle : codes de gabarits QRT présents dans la partie du
  PDF de chaque société (S.25.01 = formule standard, S.25.05 = modèle
  interne ; gabarits .22 / S.32.01 = groupe) ; partiel/complet lu dans le
  texte (AXA : « modèle interne intégral » ; Groupama : « modèle interne
  partiel groupe » ; Allianz Vie : tous les risques, y compris
  l'opérationnel, modélisés en interne, aucune mention de modèle partiel,
  rapport p.70/p.73).
- forme juridique : lue dans les rapports (sources dans FORME_SOURCE).
- activité : répartition du best estimate par ligne S.02.01 (`kpi_composants`)
  recoupée avec les primes S.05.01 — santé ≥ 60 % du BE → Santé/prévoyance ;
  sinon non-vie (y c. santé non-vie) ≥ 75 % → Non-vie ; sinon vie (y c.
  UC et santé similaire vie) ≥ 85 % ET primes non-vie < 50 % → Vie ;
  sinon Mixte.

    python populate_company_metadata.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"

# societe: (forme_juridique, type_activite, type_document, scr_method, pays)
METADONNEES = {
    "AG.Mut": ("Union de mutuelles", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "AG2R Prevoyance": ("Institution de prévoyance", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "AXA France IARD": ("SA", "Non-vie", "solo", "modele_interne_complet", "France"),
    "AXA France Vie": ("SA", "Vie", "solo", "modele_interne_complet", "France"),
    "Abeille Epargne Retraite": ("SA", "Vie", "solo", "formule_standard", "France"),
    "Abeille IARD Sante": ("SA", "Non-vie", "solo", "formule_standard", "France"),
    "Abeille Vie": ("SA", "Vie", "solo", "formule_standard", "France"),
    "Aema Groupe": ("Groupe (SGAM)", "Mixte", "groupe", "formule_standard", "France"),
    "Aesio Mutuelle": ("Mutuelle (Livre II)", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "Allianz Vie": ("SA", "Vie", "solo", "modele_interne_complet", "France"),
    "Arpege Prevoyance": ("Institution de prévoyance", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "BPCE Assurances IARD": ("SA", "Non-vie", "solo", "formule_standard", "France"),
    "BPCE Vie": ("SA", "Vie", "solo", "formule_standard", "France"),
    "CNP Assurances": ("SA", "Vie", "solo", "formule_standard", "France"),
    "Cardif Assurance Vie": ("SA", "Vie", "solo", "formule_standard", "France"),
    "Cardif Assurances Risques Divers": ("SA", "Non-vie", "solo", "formule_standard", "France"),
    "Covéa": ("Groupe (SGAM)", "Mixte", "groupe", "formule_standard", "France"),
    "Crédit Agricole Assurances": ("Groupe (SA holding)", "Vie", "groupe", "formule_standard", "France"),
    "Generali IARD": ("SA", "Non-vie", "solo", "modele_interne_complet", "France"),
    "Generali Vie": ("SA", "Vie", "solo", "modele_interne_complet", "France"),
    "Groupama": ("Groupe (tête : caisse de réassurance mutuelle)", "Mixte", "groupe", "modele_interne_partiel", "France"),
    "La Mondiale": ("SAM", "Vie", "solo", "formule_standard", "France"),
    "La Mondiale Europartner": ("SA (droit luxembourgeois)", "Vie", "solo", "formule_standard", "Luxembourg"),
    "La Mondiale Partenaire": ("SA", "Vie", "solo", "formule_standard", "France"),
    "MACIF SAM": ("SAM", "Non-vie", "solo", "formule_standard", "France"),
    "MACSF prévoyance": ("SAM", "Vie", "solo", "formule_standard", "France"),
    "MAIF": ("SAM (cotisations variables)", "Non-vie", "solo", "formule_standard", "France"),
    "MGEN": ("Mutuelle (Livre II)", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "MMJ": ("Mutuelle (Livre II)", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "MNPAF": ("Mutuelle (Livre II)", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "Macif Sante Prevoyance": ("Mutuelle (Livre II)", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "Macif Vie": ("SE (société européenne)", "Vie", "solo", "formule_standard", "France"),
    "Macifilia": ("SA", "Non-vie", "solo", "formule_standard", "France"),
    "Nuoma": ("Mutuelle (Livre II)", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "Predica": ("SA", "Vie", "solo", "formule_standard", "France"),
    "Prima": ("SA", "Santé/prévoyance", "solo", "formule_standard", "France"),
    "SGAM AG2R LA MONDIALE": ("Groupe (SGAM)", "Vie", "groupe", "formule_standard", "France"),
    "Sogécap": ("SA", "Vie", "solo", "formule_standard", "France"),
    "SwissLife Assurance et Patrimoine": ("SA", "Vie", "solo", "formule_standard", "France"),
    "Themis": ("SA", "Non-vie", "solo", "formule_standard", "France"),
    "VIASANTE Mutuelle": ("Mutuelle (Livre II)", "Santé/prévoyance", "solo", "formule_standard", "France"),
}

# Où la forme juridique a été lue (« dénomination » = non lisible dans le
# PDF disponible, annexe QRT seule).
FORME_SOURCE = {
    **{n: "AG2R p.9" for n in ("AG.Mut", "AG2R Prevoyance", "Arpege Prevoyance", "Prima", "VIASANTE Mutuelle",
                               "La Mondiale", "La Mondiale Europartner", "La Mondiale Partenaire", "SGAM AG2R LA MONDIALE")},
    **{n: "Aéma p.68" for n in ("MACIF SAM", "Macif Vie", "Macif Sante Prevoyance", "Macifilia", "Aesio Mutuelle",
                                "Abeille Vie", "Abeille Epargne Retraite", "Abeille IARD Sante")},
    "Themis": "Aéma p.104", "MMJ": "Aéma p.291", "MNPAF": "Aéma p.263", "Nuoma": "Aéma p.319", "Aema Groupe": "Aéma p.11",
    "Allianz Vie": "p.8", "BPCE Assurances IARD": "p.8", "BPCE Vie": "p.8", "CNP Assurances": "p.8", "Sogécap": "p.8",
    "Predica": "p.6", "MGEN": "p.7", "MAIF": "p.11", "MACSF prévoyance": "p.4", "SwissLife Assurance et Patrimoine": "p.10",
    "Covéa": "p.6", "Groupama": "p.9", "Crédit Agricole Assurances": "rapport de groupe",
    "Generali IARD": "RSSF Generali Iard p.4", "Generali Vie": "RSSF Generali Vie p.4",
    "AXA France IARD": "dénomination", "AXA France Vie": "dénomination",
    "Cardif Assurance Vie": "dénomination", "Cardif Assurances Risques Divers": "dénomination",
}

AG2R = ("AG.Mut", "AG2R Prevoyance", "Arpege Prevoyance", "Prima", "VIASANTE Mutuelle",
        "La Mondiale", "La Mondiale Europartner", "La Mondiale Partenaire")
AEMA = ("MACIF SAM", "Macif Vie", "Macif Sante Prevoyance", "Themis", "Macifilia", "Aesio Mutuelle",
        "MNPAF", "MMJ", "Nuoma", "Abeille Vie", "Abeille Epargne Retraite", "Abeille IARD Sante")

# Groupe économique d'appartenance — seulement quand le rapport le dit.
GROUPE_PARENT = {
    **{n: "AG2R La Mondiale" for n in AG2R + ("SGAM AG2R LA MONDIALE",)},
    **{n: "Aéma Groupe" for n in AEMA + ("Aema Groupe",)},
    "Crédit Agricole Assurances": "Crédit Agricole Assurances", "Predica": "Crédit Agricole Assurances",
    "Generali Vie": "Generali", "Generali IARD": "Generali",
    "AXA France Vie": "AXA", "AXA France IARD": "AXA",
    "BPCE Vie": "BPCE", "BPCE Assurances IARD": "BPCE",
    "Cardif Assurance Vie": "BNP Paribas Cardif", "Cardif Assurances Risques Divers": "BNP Paribas Cardif",
    "Sogécap": "Société Générale", "Allianz Vie": "Allianz", "MACSF prévoyance": "MACSF",
    "Covéa": "Covéa", "Groupama": "Groupama",
}

# Société du panel qui consolide déjà celle-ci (double comptage).
GROUPE_CONSOLIDE_PANEL = {
    **{n: "SGAM AG2R LA MONDIALE" for n in AG2R},
    **{n: "Aema Groupe" for n in AEMA},
    "Predica": "Crédit Agricole Assurances",
}

SOCIETES_EUROS_BRUTS = {
    "Aesio Mutuelle", "MNPAF", "MMJ", "Nuoma",
    "Abeille Vie", "Abeille Epargne Retraite", "Abeille IARD Sante",
    "Sogécap",
}

NOUVELLES_COLONNES = ("type_document", "scr_method", "type_activite", "unite_source",
                      "forme_juridique", "famille_juridique", "forme_juridique_source",
                      "groupe_parent", "groupe_consolide_panel")


def type_court(forme):
    for prefixe, court in (("Groupe", "Groupe"), ("SAM", "SAM"), ("SE", "SE"), ("SA", "SA"),
                           ("Union de mutuelles", "Union de mutuelles"), ("Mutuelle", "Mutuelle"),
                           ("Institution de prévoyance", "Institution de prévoyance")):
        if forme.startswith(prefixe):
            return court
    raise ValueError(forme)


def famille(forme):
    court = type_court(forme)
    return {"SA": "SA/SE", "SE": "SA/SE", "SAM": "SAM", "Groupe": "Groupe",
            "Institution de prévoyance": "Institution de prévoyance"}.get(court, "Mutuelle/UM (code mutualité)")


def ajouter_colonnes(conn):
    existantes = {r[1] for r in conn.execute("PRAGMA table_info(companies)").fetchall()}
    for col in NOUVELLES_COLONNES:
        if col not in existantes:
            conn.execute(f"ALTER TABLE companies ADD COLUMN {col} TEXT")
            print(f"  colonne ajoutée : {col}")


def main():
    conn = sqlite3.connect(DB_PATH)
    ajouter_colonnes(conn)
    noms_base = {r[0] for r in conn.execute("SELECT name FROM companies")}
    manquantes = noms_base - set(METADONNEES)
    if manquantes:
        raise SystemExit(f"Sociétés sans métadonnées contrôlées : {sorted(manquantes)} — à ajouter à METADONNEES")

    for nom, (forme, activite, perimetre, scr_method, pays) in sorted(METADONNEES.items()):
        if nom not in noms_base:
            print(f"  [absente de la base, ignorée] {nom}")
            continue
        conn.execute(
            """UPDATE companies SET type=?, forme_juridique=?, famille_juridique=?, forme_juridique_source=?,
                   type_activite=?, type_document=?, scr_method=?, country=?, unite_source=?,
                   groupe_parent=?, groupe_consolide_panel=?
               WHERE name=?""",
            (type_court(forme), forme, famille(forme), FORME_SOURCE[nom], activite, perimetre, scr_method, pays,
             "euros bruts" if nom in SOCIETES_EUROS_BRUTS else "K€",
             GROUPE_PARENT.get(nom), GROUPE_CONSOLIDE_PANEL.get(nom), nom),
        )
    conn.commit()

    print(f"{'société':34} {'type':26} {'activité':17} {'périm.':6} {'scr_method':24} pays")
    for r in conn.execute("SELECT name, type, type_activite, type_document, scr_method, country FROM companies ORDER BY name"):
        print(f"{r[0]:34} {r[1]:26} {r[2]:17} {r[3]:6} {r[4]:24} {r[5]}")
    conn.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
