# -*- coding: utf-8 -*-
"""populate_company_metadata.py — Ajoute et remplit 4 colonnes de
métadonnées sur `companies` (Décision 103) : type_document, scr_method,
type_activite, unite_source.

Sources, PAR ORDRE DE FIABILITÉ (jamais deviné) :
- type_document/scr_method pour les 12 sociétés à PDF autonome :
  detecter_templates() ré-exécuté directement (résultat vérifié, pas
  supposé) — cf. `metadata_diagnostic.txt`.
- type_document/scr_method pour les 22 entités AG2R (9)/Aéma (13),
  extraites depuis un document combiné (pas de PDF autonome à
  re-diagnostiquer facilement) : repris des décisions déjà vérifiées
  (Décision 081/083/087 — "formule_standard" pour les 22, "entité
  consolidée" = groupe pour SGAM AG2R LA MONDIALE et Aema Groupe
  uniquement, "solo" pour les 20 autres entités).
- type_activite : déduit des KPIs déjà en base (règle demandée :
  vie+non-vie>0 -> Mixte, vie seul -> Vie, non-vie seul -> Non-vie,
  aucun des 2 -> Mutuelle/Santé, jamais résolus -> NULL).
- unite_source : connu précisément (Décisions 094/096) — 7 entités
  Aéma + Sogécap en euros bruts, les 26 autres en K€.

    python populate_company_metadata.py
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"

# --- type_document/scr_method, vérifiés par detecter_templates() direct
# (12 sociétés à PDF autonome) ---
META_PDF_AUTONOME = {
    "Groupama": ("groupe", "modele_interne_partiel"),
    "CNP Assurances": ("solo", "formule_standard"),
    "MACSF prévoyance": ("solo", "formule_standard"),
    "Predica": ("solo", "formule_standard"),
    "MGEN": ("solo", "formule_standard"),
    "Crédit Agricole Assurances": ("groupe", "formule_standard"),
    "Sogécap": ("groupe", "formule_standard"),
    "Cardif Assurance Vie": ("solo", "formule_standard"),
    "Cardif Assurances Risques Divers": ("solo", "formule_standard"),
    "MAIF": ("solo", None),  # scr_method non déterminable automatiquement (mode libelles_francais)
    "Covéa": ("groupe", "formule_standard"),
    # detecter_templates() retourne "inconnu" pour document_type sur ce
    # PDF précis (classification automatique ambiguë), mais le template
    # RÉELLEMENT utilisé pour l'extraction (Décision 101) est S.23.01.01,
    # le code EIOPA solo standard (le groupe utiliserait S.23.01.22) —
    # évidence directe et vérifiée, pas une supposition.
    "Allianz Vie": ("solo", "modele_interne_partiel"),
}

# --- AG2R (9 entités, Décision 087) : formule_standard pour toutes,
# SGAM = entité consolidée du groupe (groupe), les 8 autres = solo. ---
AG2R_SOLO = ["AG2R Prevoyance", "Arpege Prevoyance", "Prima", "AG.Mut",
             "VIASANTE Mutuelle", "La Mondiale", "La Mondiale Europartner", "La Mondiale Partenaire"]
for _nom in AG2R_SOLO:
    META_PDF_AUTONOME[_nom] = ("solo", "formule_standard")
META_PDF_AUTONOME["SGAM AG2R LA MONDIALE"] = ("groupe", "formule_standard")

# --- Aéma (13 entités, Décision 083/094) : formule_standard pour toutes,
# Aema Groupe = groupe, les 12 autres = solo. ---
AEMA_SOLO = ["MACIF SAM", "Macif Vie", "Macif Sante Prevoyance", "Themis", "Macifilia",
             "Aesio Mutuelle", "MNPAF", "MMJ", "Nuoma",
             "Abeille Vie", "Abeille Epargne Retraite", "Abeille IARD Sante"]
for _nom in AEMA_SOLO:
    META_PDF_AUTONOME[_nom] = ("solo", "formule_standard")
META_PDF_AUTONOME["Aema Groupe"] = ("groupe", "formule_standard")

# --- unite_source (Décisions 094/096) : € bruts confirmés sur ces 8
# sociétés précisément, K€ partout ailleurs (défaut). ---
SOCIETES_EUROS_BRUTS = {
    "Aesio Mutuelle", "MNPAF", "MMJ", "Nuoma",
    "Abeille Vie", "Abeille Epargne Retraite", "Abeille IARD Sante",
    "Sogécap",
}


def ajouter_colonnes(conn):
    colonnes_existantes = {r[1] for r in conn.execute("PRAGMA table_info(companies)").fetchall()}
    for col in ("type_document", "scr_method", "type_activite", "unite_source"):
        if col not in colonnes_existantes:
            conn.execute(f"ALTER TABLE companies ADD COLUMN {col} TEXT")
            print(f"  colonne ajoutée : {col}")
        else:
            print(f"  colonne déjà présente : {col}")
    conn.commit()


def deduire_type_activite(conn, company_id, year=2025):
    """Règle demandée : vie+non-vie>0 -> Mixte, vie seul -> Vie, non-vie
    seul -> Non-vie, aucun des 2 (souvent le cas santé/prévoyance pure)
    -> Mutuelle, l'un des 2 NULL et l'autre aussi -> NULL (jamais résolu)."""
    def valeur(kpi_name):
        row = conn.execute(
            "SELECT value FROM kpis WHERE company_id=? AND year=? AND kpi_name=?",
            (company_id, year, kpi_name),
        ).fetchone()
        return row[0] if row else None

    vie = valeur("scr_souscription_vie")
    nonvie = valeur("scr_souscription_nonvie")
    sante = valeur("scr_souscription_sante")

    if vie is None and nonvie is None:
        return None
    a_vie = (vie or 0) > 0
    a_nonvie = (nonvie or 0) > 0
    if a_vie and a_nonvie:
        return "Mixte"
    if a_vie:
        return "Vie"
    if a_nonvie:
        return "Non-vie"
    # Ni vie ni non-vie positif (souvent des mutuelles santé/prévoyance
    # pures, ex. Macifilia/Themis) — si santé significative, le signaler.
    if (sante or 0) > 0:
        return "Mutuelle"
    return "Mutuelle"


# Overrides ciblés, documentés — le PDF/nom de la société est plus fiable
# que la règle KPI quand le KPI source est NULL pour une raison
# STRUCTURELLE déjà connue (pas un manque de données réel) :
# - Allianz Vie : scr_souscription_vie est NULL car fusionné avec
#   scr_souscription_sante dans une seule ligne QRT modèle interne
#   (irréductible, Décision 084/101) — la règle KPI dérive à tort
#   "Mutuelle" faute de signal, alors que le document lui-même (et son
#   nom) confirment sans ambiguïté un assureur VIE pur.
TYPE_ACTIVITE_OVERRIDES = {
    "Allianz Vie": "Vie",
}


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")

    print("=== ajout des colonnes ===")
    ajouter_colonnes(conn)

    print("\n=== remplissage ===")
    societes = conn.execute("SELECT id, name FROM companies ORDER BY name").fetchall()
    resume = []
    for company_id, nom in societes:
        type_doc, scr_method = META_PDF_AUTONOME.get(nom, (None, None))
        type_activite = TYPE_ACTIVITE_OVERRIDES.get(nom) or deduire_type_activite(conn, company_id)
        unite = "euros bruts" if nom in SOCIETES_EUROS_BRUTS else "K€"

        conn.execute(
            "UPDATE companies SET type_document=?, scr_method=?, type_activite=?, unite_source=? WHERE id=?",
            (type_doc, scr_method, type_activite, unite, company_id),
        )
        resume.append((nom, type_doc, scr_method, type_activite, unite))

    conn.commit()

    print(f"\n{'société':34} {'type_doc':8} {'scr_method':22} {'type_activite':12} unite_source")
    for nom, td, sm, ta, us in resume:
        print(f"{nom:34} {str(td):8} {str(sm):22} {str(ta):12} {us}")

    n_null_td = sum(1 for r in resume if r[1] is None)
    n_null_sm = sum(1 for r in resume if r[2] is None)
    n_null_ta = sum(1 for r in resume if r[3] is None)
    print(f"\n{len(resume)} sociétés. NULL : type_document={n_null_td}, scr_method={n_null_sm}, type_activite={n_null_ta}")

    conn.close()


if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
