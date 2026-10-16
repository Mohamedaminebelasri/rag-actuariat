# -*- coding: utf-8 -*-
"""creer_table_documents_sfcr.py — Crée et remplit la table `documents_sfcr`
de kpis.db : le PDF par défaut de chaque société (problème P1 de
ETAT_DES_LIEUX_CHAT.md). Jusqu'ici, cette correspondance n'existait que
côté front (`frontend/src/lib/pdf-par-societe.ts`, `PDF_PAR_SOCIETE`).

Source unique : `pdf-par-societe.ts`, lu tel quel (le front n'est pas
modifié), complété par `RAPPORTS_COMPLETS_SUPPLEMENTAIRES` (P3). Une ligne
par société, par année et par type de document : une société reliée à une
annexe QRT peut avoir aussi une ligne `rapport_complet`. Aucune autre table
n'est touchée. Idempotent : les lignes de l'année sont réécrites à chaque
exécution. Une table créée avec l'ancienne clé (`societe_id`, `annee`) est
migrée vers la nouvelle, lignes conservées.

- `pdf_path` : chemin relatif depuis la racine du projet (`data/...`).
- `type_document` : `annexe_qrt` pour les 6 sociétés reliées seulement à
  une annexe QRT (inventaire 0.3), sinon `rapport_complet`.
- `rapport_groupe` : 1 pour les rapports communs Aéma et AG2R (plusieurs
  entités dans un même PDF), sinon 0.
- Les extraits `_entite_*.pdf` sont refusés (doublons du PDF AG2R).

Un PDF secondaire utilisé pour un KPI précis reste aussi dans
`kpis.source_pdf` (Décision 145).

    python creer_table_documents_sfcr.py
"""
import re
import sqlite3
from pathlib import Path

import pymupdf

RACINE = Path(__file__).parent
DB_PATH = RACINE / "kpis.db"
MAPPING_TS = RACINE / "frontend" / "src" / "lib" / "pdf-par-societe.ts"
ANNEE = 2025

ANNEXES_QRT = {
    "afv-annexes-2025-etats-quantitatifs.pdf",
    "Annexe-QRT-Publics-AFI-2025-ok.pdf",
    "Annexe_RSSF_QRT_GVIE_2025.pdf",
    "Annexe_RSSF_QRT_GIARD_2025.pdf",
    "Cardif-Assurance-Vie-–-Annexes-2025.pdf",
    "cardif-assurances-risques-divers-–-annexes-2025.pdf",
}
# P3 : rapport SFCR complet 2025 des sociétés dont le PDF par défaut est une
# annexe QRT (entité, exercice 2025 et chapitres A à E vérifiés dans le texte).
# Cardif : téléchargés le 16/10/2026 depuis bnpparibascardif.com
# (/investisseurs/informations-financieres-2/, rubrique « Rapports de solvabilité »).
RAPPORTS_COMPLETS_SUPPLEMENTAIRES = {
    "AXA France Vie": "AXA_France_Vie-Rapport_2025_sur_la_solvabilite_et_la_situation_financiere.pdf",
    "AXA France IARD": "AXA_France_IARD-Rapport_2025_sur_la_solvabilite_et_la_situation_financiere.pdf",
    "Generali Vie": "RSSF_Generali_Vie_2025.pdf",
    "Generali IARD": "RSSF_Generali_Iard_2025.pdf",
    "Cardif Assurance Vie": "Cardif_Assurance_Vie_SFCR_2025.pdf",
    "Cardif Assurances Risques Divers": "Cardif_Assurances_Risques_Divers_SFCR_2025.pdf",
}
RAPPORTS_GROUPE = {
    "Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf",
    "AG2R-LA-MONDIALE-RSSF-Groupe-2025.pdf",
}

SQL_CREATION = """
CREATE TABLE IF NOT EXISTS documents_sfcr (
    societe_id INTEGER NOT NULL,
    pdf_path TEXT NOT NULL,
    type_document TEXT NOT NULL
        CHECK (type_document IN ('rapport_complet', 'annexe_qrt')),
    nb_pages INTEGER NOT NULL,
    rapport_groupe INTEGER NOT NULL CHECK (rapport_groupe IN (0, 1)),
    annee INTEGER NOT NULL,
    PRIMARY KEY (societe_id, annee, type_document),
    FOREIGN KEY (societe_id) REFERENCES companies(id)
)
"""


def migrer_ancienne_cle(conn):
    """Passe de la clé (societe_id, annee) à (societe_id, annee,
    type_document) en recopiant les lignes telles quelles (SQLite ne sait
    pas modifier une clé primaire en place)."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'documents_sfcr'"
    ).fetchone()
    if row is None or "PRIMARY KEY (societe_id, annee)," not in row[0]:
        return 0
    conn.execute("ALTER TABLE documents_sfcr RENAME TO documents_sfcr_ancienne_cle")
    conn.execute(SQL_CREATION)
    conn.execute("INSERT INTO documents_sfcr SELECT * FROM documents_sfcr_ancienne_cle")
    n = conn.execute("SELECT COUNT(*) FROM documents_sfcr").fetchone()[0]
    conn.execute("DROP TABLE documents_sfcr_ancienne_cle")
    return n


def lire_mapping_ts():
    """{société: nom de fichier} depuis PDF_PAR_SOCIETE."""
    texte = MAPPING_TS.read_text(encoding="utf-8")
    bloc = texte.split("PDF_PAR_SOCIETE", 1)[1]
    paires = re.findall(r'^\s*"([^"]+)"\s*:\s*"([^"]+)"\s*,?\s*$', bloc, re.M)
    mapping = dict(paires)
    if len(mapping) != len(paires):
        raise ValueError("société en double dans pdf-par-societe.ts")
    return mapping


def main():
    mapping = lire_mapping_ts()
    conn = sqlite3.connect(DB_PATH)
    ids = {nom: i for i, nom in conn.execute("SELECT id, name FROM companies")}

    inconnues = sorted((set(mapping) | set(RAPPORTS_COMPLETS_SUPPLEMENTAIRES)) - set(ids))
    if inconnues:
        raise ValueError(f"sociétés absentes de companies : {inconnues}")

    for societe in RAPPORTS_COMPLETS_SUPPLEMENTAIRES:
        if mapping[societe] not in ANNEXES_QRT:
            raise ValueError(f"{societe} : le PDF par défaut n'est pas une annexe QRT")

    documents = sorted(mapping.items()) + sorted(RAPPORTS_COMPLETS_SUPPLEMENTAIRES.items())
    pages = {}
    lignes = []
    for societe, fichier in documents:
        if fichier.startswith("_entite_"):
            raise ValueError(f"extrait _entite_ refusé : {fichier}")
        chemin = RACINE / "data" / fichier
        if not chemin.is_file():
            raise FileNotFoundError(chemin)
        if fichier not in pages:
            with pymupdf.open(chemin) as doc:
                pages[fichier] = doc.page_count
        lignes.append((
            ids[societe],
            f"data/{fichier}",
            "annexe_qrt" if fichier in ANNEXES_QRT else "rapport_complet",
            pages[fichier],
            1 if fichier in RAPPORTS_GROUPE else 0,
            ANNEE,
        ))

    with conn:
        migrees = migrer_ancienne_cle(conn)
        if migrees:
            print(f"clé primaire migrée vers (societe_id, annee, type_document) : {migrees} lignes recopiées")
        conn.execute(SQL_CREATION)
        conn.execute("DELETE FROM documents_sfcr WHERE annee = ?", (ANNEE,))
        conn.executemany(
            "INSERT INTO documents_sfcr (societe_id, pdf_path, type_document,"
            " nb_pages, rapport_groupe, annee) VALUES (?, ?, ?, ?, ?, ?)",
            lignes,
        )
    n = conn.execute(
        "SELECT COUNT(*) FROM documents_sfcr WHERE annee = ?", (ANNEE,)
    ).fetchone()[0]
    conn.close()
    print(f"documents_sfcr : {n} lignes ({len(pages)} PDF distincts), année {ANNEE}")


if __name__ == "__main__":
    main()
