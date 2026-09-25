# -*- coding: utf-8 -*-
"""aema_entites.py — Décision 083 : intégration multi-entités du document
combiné "Aéma Groupe" (621 pages, 13 entités juridiques) dans le pipeline
KPI. Le document est 100% image (confirmé par test automatisé, cf.
POINT_ETAPE_PAUSE.md) — chaque entité nécessite une lecture manuelle
sur rendu PNG avec recoupement interne entre pages indépendantes du
même bloc, comme pour Generali Iard/Vie (Décision 080) et MACIF SAM
(Décision 081).

Généralisation : `extraire_entite()` dans test_markdrop/ingest.py isole
n'importe quel bloc [page_debut, page_fin] en sous-PDF autonome via
fitz.insert_pdf — technique réutilisable pour d'autres documents
combinés futurs, pas seulement Aéma.

État (voir DECISIONS.md, Décision 083 pour le détail complet) :
2 des 13 entités sont complètes et vérifiées (MACIF SAM, Aéma Groupe),
11 restent à faire — bornes de pages déjà connues ci-dessous, prêtes à
être traitées avec la même méthode dès qu'une session aura le temps.
"""

AEMA_SOURCE = "data/Aema-Groupe_RAPPORT-UNIQUE-SUR-LA-SOLVABILITE-ET-LA-SITUATION-FINANCIERE_2025.pdf"

# Bornes de pages (1-indexées, inclusives) des 13 entités dans le
# document original — vérifiées via les en-têtes "Entité : ..." /
# noms affichés sur chaque bloc (Décision 083).
ENTITES_BORNES = {
    "Aema Groupe": (439, 451),
    "MACIF SAM": (452, 467),
    "Macif Vie": (468, 478),
    "Macif Sante Prevoyance": (479, 493),
    "Themis": (494, 507),
    "Macifilia": (508, 522),
    "Aesio Mutuelle": (523, 538),
    "MNPAF": (539, 550),
    "MMJ": (551, 563),
    "Nuoma": (564, 576),
    "Abeille Vie": (577, 592),
    "Abeille Epargne Retraite": (593, 602),
    "Abeille IARD Sante": (603, 621),
}

# Valeurs en K€ BRUT (telles que lues sur la page, devise "KEUR" —
# converties en M€ uniquement au moment de l'insertion en base, cf.
# `inserer_entite_en_base`, pour rester auditable contre le PDF).
# ratio_scr/ratio_mcr sont déjà en points de pourcentage (ex. 212 pour
# 212%), pas de conversion.
ENTITES_KPIS = {
    "MACIF SAM": {
        "best_estimate": (5969795.0, 453, "S.02.01.02.01 Bilan, somme 5 segments Meilleure estimation"),
        "marge_risque": (341059.0, 453, "S.02.01.02.01 Bilan, somme 5 segments Marge de risque"),
        "primes_acquises_brutes": (4854620.0, 455, "S.05.01.02.01+.02, R0210+R0220+R0230 (non-vie) + R1510 (vie), colonne Total"),
        "charge_sinistres": (3429372.0, 455, "S.05.01.02.01+.02, R0310+R0320+R0330 (non-vie) + R1610 (vie), colonne Total"),
        "fonds_propres_eligibles": (9443143.0, 463, "S.23.01.01.01/R0540/Total"),
        "fonds_propres_t1_nr": (7872072.0, 463, "S.23.01.01.01/R0540/Niveau1 non restreint"),
        "fonds_propres_t1_r": (374465.0, 463, "S.23.01.01.01/R0540/Niveau1 restreint"),
        "fonds_propres_t2": (751973.0, 463, "S.23.01.01.01/R0540/Niveau2"),
        "fonds_propres_t3": (444633.0, 463, "S.23.01.01.01/R0540/Niveau3"),
        "scr_total": (2964220.0, 463, "S.23.01.01.01/R0580 — confirmé p.464 (S.25.01.21.02/R0220) et p.467 (S.28.01.01.05/R0310)"),
        "mcr": (746130.0, 463, "S.23.01.01.01/R0600 — confirmé p.467 (S.28.01.01.05/R0400)"),
        "ratio_scr": (319.0, 463, "S.23.01.01.01/R0620"),
        "ratio_mcr": (1125.0, 463, "S.23.01.01.01/R0640"),
        "scr_marche": (2713693.0, 464, "S.25.01.21.01/R0010"),
        "scr_contrepartie": (63361.0, 464, "S.25.01.21.01/R0020"),
        "scr_souscription_vie": (40522.0, 464, "S.25.01.21.01/R0030"),
        "scr_souscription_sante": (235321.0, 464, "S.25.01.21.01/R0040"),
        "scr_souscription_nonvie": (1464010.0, 464, "S.25.01.21.01/R0050"),
        "scr_diversification": (-1035321.0, 464, "S.25.01.21.01/R0060"),
        "scr_operationnel": (148152.0, 465, "S.25.01.21.02/R0130"),
    },
    "Aema Groupe": {
        "best_estimate": (105865186.0, 440, "S.02.01.02.01 Bilan, somme 5 segments Meilleure estimation"),
        "marge_risque": (2260715.0, 440, "S.02.01.02.01 Bilan, somme 5 segments Marge de risque"),
        "primes_acquises_brutes": (18552020.0, 442, "S.05.01.02.01+.02, R0210+R0220+R0230 (non-vie) + R1510 (vie), colonne Total"),
        "charge_sinistres": (15035231.0, 442, "S.05.01.02.01+.02, R0310+R0320+R0330 (non-vie) + R1610 (vie), colonne Total"),
        "fonds_propres_eligibles": (12860966.0, 446, "S.23.01.22.01/R0660/Total (y compris autres secteurs financiers)"),
        "fonds_propres_t1_nr": (10741242.0, 446, "S.23.01.22.01/R0660/Niveau1 non restreint"),
        "fonds_propres_t1_r": (374466.0, 446, "S.23.01.22.01/R0660/Niveau1 restreint"),
        "fonds_propres_t2": (1259990.0, 446, "S.23.01.22.01/R0660/Niveau2"),
        "fonds_propres_t3": (485268.0, 446, "S.23.01.22.01/R0660/Niveau3"),
        "scr_total": (6063105.0, 446, "S.23.01.22.01/R0680 — confirmé p.444 (S.22.01.22.01/R0090) et p.448 (S.25.01.22.02/R0220 et R0570)"),
        "mcr": (2836823.0, 446, "S.23.01.22.01/R0610 — confirmé p.448 (S.25.01.22.02/R0470)"),
        "ratio_scr": (212.0, 446, "S.23.01.22.01/R0690"),
        "ratio_mcr": (390.0, 446, "S.23.01.22.01/R0650"),
        "scr_marche": (10837399.0, 448, "S.25.01.22.01/R0010"),
        "scr_contrepartie": (264007.0, 448, "S.25.01.22.01/R0020"),
        "scr_souscription_vie": (6245084.0, 448, "S.25.01.22.01/R0030"),
        "scr_souscription_sante": (590138.0, 448, "S.25.01.22.01/R0040"),
        "scr_souscription_nonvie": (1706195.0, 448, "S.25.01.22.01/R0050"),
        "scr_diversification": (-5127701.0, 448, "S.25.01.22.01/R0060"),
        "scr_operationnel": (586048.0, 448, "S.25.01.22.02/R0130"),
    },
    # 11 entités restantes : bornes connues (ENTITES_BORNES ci-dessus),
    # extraction manuelle pas encore faite. Ne PAS deviner de valeurs —
    # absence délibérée de ces clés, traitée comme "non traité" par
    # calculer_score() ci-dessous, jamais comme un score de 0/20 (ce qui
    # laisserait croire à un vrai échec d'extraction plutôt qu'à un
    # travail non fait).
}

KPIS_IRREDUCTIBLES = set()  # aucun, les 2 entités faites utilisent la formule standard (aucune fusion)


def calculer_score(nom_entite):
    """Retourne (kpis_ok, total, statut) pour une entité. statut :
    'fait' si présente dans ENTITES_KPIS, 'non_traite' sinon."""
    if nom_entite not in ENTITES_KPIS:
        return None, None, "non_traite"
    kpis = ENTITES_KPIS[nom_entite]
    return len(kpis), 20, "fait"


def afficher_scores():
    print("=" * 90)
    print(f"{'Entité':28} {'Pages (orig.)':15} {'Score':8} {'Statut'}")
    print("=" * 90)
    for nom, (pd, pf) in ENTITES_BORNES.items():
        ok, total, statut = calculer_score(nom)
        score_str = f"{ok}/{total}" if statut == "fait" else "—"
        libelle_statut = "Fait (vérifié)" if statut == "fait" else "Non traité (bornes connues, à faire)"
        print(f"{nom:28} {f'{pd}-{pf}':15} {score_str:8} {libelle_statut}")
    print("=" * 90)
    n_fait = sum(1 for n in ENTITES_BORNES if n in ENTITES_KPIS)
    print(f"\n{n_fait}/13 entités traitées et vérifiées.")


def inserer_entite_en_base(nom_entite, db_path="kpis.db", year=2025, company_type="mutuelle (Aéma Groupe)"):
    """Insère une entité comme société séparée dans kpis.db, avec une
    note dans source_chapter indiquant sa provenance (document combiné
    Aéma Groupe + pages d'origine). Convertit K€ -> M€ (÷1000) pour les
    montants, laisse les ratios (déjà en points de %) inchangés — même
    convention que extract_kpis.py (cf. Décision 083)."""
    import sqlite3
    from kpi_definitions import KPI_DEFINITIONS

    if nom_entite not in ENTITES_KPIS:
        raise ValueError(f"{nom_entite!r} pas encore traitée (voir ENTITES_KPIS) — rien à insérer")

    pd, pf = ENTITES_BORNES[nom_entite]
    note_origine = (f"Document combiné 'Aéma Groupe RAPPORT UNIQUE...' (621p), "
                     f"entité isolée pages {pd}-{pf} (extraction manuelle sur rendu image, cf. Décision 083)")
    defs_par_nom = {d["kpi_name"]: d for d in KPI_DEFINITIONS}

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    row = conn.execute("SELECT id FROM companies WHERE name = ?", (nom_entite,)).fetchone()
    if row is None:
        conn.execute("INSERT INTO companies (name, type, country) VALUES (?, ?, ?)",
                      (nom_entite, company_type, "France"))
        company_id = conn.execute("SELECT id FROM companies WHERE name = ?", (nom_entite,)).fetchone()[0]
    else:
        company_id = row[0]

    lignes = []
    for kpi_name, (valeur_brute, source_page, note) in ENTITES_KPIS[nom_entite].items():
        d = defs_par_nom[kpi_name]
        valeur = valeur_brute if d["unit"] == "pct" else valeur_brute / 1000.0
        conn.execute(
            """INSERT INTO kpis (company_id, year, category, kpi_name, value, unit, source_page, source_chapter, validated)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
               ON CONFLICT(company_id, year, kpi_name) DO UPDATE SET
                 value=excluded.value, unit=excluded.unit,
                 source_page=excluded.source_page, source_chapter=excluded.source_chapter""",
            (company_id, year, d["category"], kpi_name, valeur, d["unit"], source_page,
             f"{note_origine} — {note}"),
        )
        lignes.append((kpi_name, valeur, d["unit"]))
    conn.commit()
    conn.close()
    return lignes


if __name__ == "__main__":
    afficher_scores()
