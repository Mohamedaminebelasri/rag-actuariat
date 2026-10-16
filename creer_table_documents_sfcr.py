# -*- coding: utf-8 -*-
"""creer_table_documents_sfcr.py — Crée et remplit la table `documents_sfcr`
de kpis.db : le PDF par défaut de chaque société (problème P1 de
ETAT_DES_LIEUX_CHAT.md). Jusqu'ici, cette correspondance n'existait que
côté front (`frontend/src/lib/pdf-par-societe.ts`, `PDF_PAR_SOCIETE`).

Source unique : `pdf-par-societe.ts`, lu tel quel (le front n'est pas
modifié). Une ligne par société et par année. Aucune autre table n'est
touchée. Idempotent : les lignes de l'année sont réécrites à chaque
exécution.

- `pdf_path` : chemin relatif depuis la racine du projet (`data/...`).
- `type_document` : `annexe_qrt` pour les 6 sociétés reliées seulement à
  une annexe QRT (inventaire 0.3), sinon `rapport_complet`.
- `rapport_groupe` : 1 pour les rapports communs Aéma et AG2R (plusieurs
  entités dans un même PDF), sinon 0.
- Les extraits `_entite_*.pdf` sont refusés (doublons du PDF AG2R).

Un PDF secondaire utilisé pour un KPI précis reste dans `kpis.source_pdf`
(Décision 145) : cette table ne donne que le PDF par défaut.

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
    PRIMARY KEY (societe_id, annee),
    FOREIGN KEY (societe_id) REFERENCES companies(id)
)
"""


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

    inconnues = sorted(set(mapping) - set(ids))
    if inconnues:
        raise ValueError(f"sociétés absentes de companies : {inconnues}")

    pages = {}
    lignes = []
    for societe, fichier in sorted(mapping.items()):
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
