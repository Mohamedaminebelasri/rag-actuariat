# -*- coding: utf-8 -*-
"""kpi_qrt_mapping.py — Mapping multi-variantes (solo/groupe × formule
standard/modèle interne) des 22 KPIs vers leurs emplacements QRT possibles
(Phase 3.7, Décision 055/056).

MÉTHODOLOGIE (aucune ligne ci-dessous n'est devinée) : chaque variante est
soit (a) vérifiée empiriquement sur Groupama 2025 (extraction réelle,
cf. extract_kpis.py et Décision 055), soit (b) vérifiée contre un QRT
annexe RÉEL et REMPLI d'un autre assureur, trouvé et lu directement (pas
un résumé IA d'un PDF compressé) :
- Bornholms Brandforsikring (Danemark, solo, S.23.01.01)
- AXA SA (solo, groupe pas consulté, S.02.01.02/S.05.01.02/S.23.01.01/
  S.25.01.01/S.28.01.01 — formule standard)
- Yuzzu (Belgique, solo, S.02.01.02/S.05.01.02/S.23.01.01/S.25.05.01/
  S.28.01.01 — modèle interne)
- solvencytool.com (EIOPA_S.25.01_group.pdf — groupe, formule standard)

CONSTAT IMPORTANT (empirique, pas supposé) : les codes de ligne QRT sont
FIXES et universels pour les templates "réglementaires purs" (S.23.01
Own Funds, S.28.01/S.28.02 MCR, S.25.01 formule standard — mêmes codes
chez Groupama, AXA, Bornholms, Yuzzu) MAIS PAS pour les templates de
répartition SCR en modèle interne (S.25.02 à S.25.05) : la comparaison
Groupama (groupe, S.25.05.22, diversification en R0060) vs Yuzzu (solo,
S.25.05.01, diversification en R0020) montre des codes DIFFÉRENTS pour
le même concept — chaque modèle interne a sa propre structure de risque,
non standardisée par l'EIOPA au-delà du format général. **Pour ces
templates, le code d'extraction doit résoudre par LIBELLÉ officiel
(libelle_officiel), jamais par un code de ligne supposé fixe** — c'est
déjà ce que fait lire_cellule() dans extract_kpis.py, donc AUCUNE entrée
"modèle interne" à code de ligne fixe n'est mise ici pour les 6 KPIs de
risque détaillé (scr_marche, scr_contrepartie, scr_souscription_vie,
scr_souscription_sante, scr_operationnel — scr_souscription_nonvie et
scr_diversification ont leur variante Groupama documentée à titre
d'exemple, PAS comme règle générale).

Chaque entrée : {"template": code EIOPA, "row": "R0xxx", "col": "C0xxx",
"libelle_attendu": sous-chaîne du libellé officiel à vérifier avant
d'accepter (même discipline que lire_cellule), "variante": description
courte, "verifie_contre": source de vérification}.

Le code d'extraction (extract_kpis.py / kpi_qrt_mapping.trouver_valeur)
essaie chaque variante DANS L'ORDRE et retient la première dont le
template est présent dans l'inventaire du document ET dont le libellé
concorde — jamais un code pris au hasard.
"""

KPI_QRT_MAPPING = {
    # --- Solvabilité ---
    "ratio_scr": [
        {"template": "S.23.01.22", "row": "R0690", "col": "C0010",
         "libelle_attendu": "Ratio of Total Eligible own funds to Total group SCR",
         "variante": "groupe", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0620", "col": "C0010",
         "libelle_attendu": "Ratio of Eligible own funds to SCR",
         "variante": "solo (EN)", "verifie_contre": "Bornholms Brand + AXA SA (QRT réels)"},
        {"template": "S.23.01.01", "row": "R0620", "col": "C0010",
         "libelle_attendu": "Ratio fonds propres éligibles sur capital de solvabilité requis",
         "variante": "solo (FR)", "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
    ],
    "ratio_mcr": [
        {"template": "S.23.01.22", "row": "R0650", "col": "C0010",
         "libelle_attendu": "Ratio of Eligible own funds to Minimum Consolidated Group SCR",
         "variante": "groupe", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0640", "col": "C0010",
         "libelle_attendu": "Ratio of Eligible own funds to MCR",
         "variante": "solo (EN)", "verifie_contre": "Bornholms Brand + AXA SA (QRT réels)"},
        {"template": "S.23.01.01", "row": "R0640", "col": "C0010",
         "libelle_attendu": "Ratio fonds propres éligibles sur minimum de capital requis",
         "variante": "solo (FR)", "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
    ],

    # --- Fonds propres ---
    "fonds_propres_eligibles": [
        {"template": "S.23.01.22", "row": "R0660", "col": "C0010",
         "libelle_attendu": "Total eligible own funds to meet the total group SCR",
         "variante": "groupe", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0010",
         "libelle_attendu": "Total eligible own funds to meet the SCR",
         "variante": "solo (EN)", "verifie_contre": "Bornholms Brand + AXA SA (QRT réels)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0010",
         "libelle_attendu": "Total des fonds propres éligibles pour couvrir le capital de solvabilité requis",
         "variante": "solo (FR)", "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0060",
         "libelle_attendu": "Total des fonds propres éligibles pour couvrir le capital de solvabilité requis",
         "variante": "solo (FR), colonne C0060", "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
    ],
    "fonds_propres_t1_nr": [
        {"template": "S.23.01.22", "row": "R0660", "col": "C0020", "libelle_attendu": "Total eligible own funds",
         "variante": "groupe", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0020", "libelle_attendu": "Total eligible own funds",
         "variante": "solo (EN)", "verifie_contre": "Bornholms Brand + AXA SA (QRT réels)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0020", "libelle_attendu": "Total des fonds propres éligibles",
         "variante": "solo (FR)", "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
    ],
    "fonds_propres_t1_r": [
        {"template": "S.23.01.22", "row": "R0660", "col": "C0030", "libelle_attendu": "Total eligible own funds",
         "variante": "groupe", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0030", "libelle_attendu": "Total eligible own funds",
         "variante": "solo (EN)", "verifie_contre": "Bornholms Brand + AXA SA (QRT réels)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0030", "libelle_attendu": "Total des fonds propres éligibles",
         "variante": "solo (FR)", "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
    ],
    "fonds_propres_t2": [
        {"template": "S.23.01.22", "row": "R0660", "col": "C0040", "libelle_attendu": "Total eligible own funds",
         "variante": "groupe", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0040", "libelle_attendu": "Total eligible own funds",
         "variante": "solo (EN)", "verifie_contre": "Bornholms Brand + AXA SA (QRT réels)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0040", "libelle_attendu": "Total des fonds propres éligibles",
         "variante": "solo (FR)", "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
    ],
    "fonds_propres_t3": [
        {"template": "S.23.01.22", "row": "R0660", "col": "C0050", "libelle_attendu": "Total eligible own funds",
         "variante": "groupe", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0050", "libelle_attendu": "Total eligible own funds",
         "variante": "solo (EN)", "verifie_contre": "Bornholms Brand + AXA SA (QRT réels)"},
        {"template": "S.23.01.01", "row": "R0540", "col": "C0050", "libelle_attendu": "Total des fonds propres éligibles",
         "variante": "solo (FR)", "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
    ],

    # --- SCR ---
    "scr_total": [
        {"template": "S.23.01.22", "row": "R0680", "col": "C0010", "libelle_attendu": "Total Group SCR",
         "variante": "groupe (source Own Funds, la plus fiable)", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0580", "col": "C0010", "libelle_attendu": "SCR",
         "variante": "solo (source Own Funds)", "verifie_contre": "Bornholms Brand + AXA SA (QRT réels)"},
        {"template": "S.23.01.01", "row": "R0580", "col": "C0060", "libelle_attendu": "Capital de solvabilité requis",
         "variante": "solo (FR), colonne C0060 (taxonomie MACSF — 3e variante de colonne observée pour ce concept)",
         "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
        {"template": "S.25.01.22", "row": "R0220", "col": "C0100", "libelle_attendu": "Solvency capital requirement",
         "variante": "groupe, formule standard", "verifie_contre": "solvencytool.com EIOPA_S.25.01_group.pdf"},
        {"template": "S.25.01.01", "row": "R0220", "col": "C0100", "libelle_attendu": "Solvency capital requirement",
         "variante": "solo, formule standard", "verifie_contre": "AXA SA (QRT réel)"},
        {"template": "S.25.01.21", "row": "R0220", "col": "C0110", "libelle_attendu": "Capital de solvabilité requis",
         "variante": "solo, formule standard, suffixe .21 (taxonomie EIOPA 2025 — colonne C0110 pas C0100, "
                     "constat empirique : même concept, layout de colonnes différent d'AXA/2023)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle, croisé contre S.23.01.01/R0580, écart 0%)"},
        {"template": "S.25.01.21", "row": "R0220", "col": "C0090", "libelle_attendu": "Capital de solvabilité requis",
         "variante": "solo, formule standard, colonne C0080 (net, taxonomie MACSF)",
         "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
        {"template": "S.25.05.22", "row": "R0220", "col": "C0100", "libelle_attendu": "Group SCR",
         "variante": "groupe, modèle interne — CODE SPÉCIFIQUE GROUPAMA, pas garanti universel",
         "verifie_contre": "Groupama 2025 (extraction réelle)"},
    ],
    "scr_marche": [
        {"template": "S.25.01.22", "row": "R0010", "col": "C0040", "libelle_attendu": "Market risk",
         "variante": "groupe, formule standard", "verifie_contre": "solvencytool.com EIOPA_S.25.01_group.pdf"},
        {"template": "S.25.01.01", "row": "R0010", "col": "C0040", "libelle_attendu": "Market risk",
         "variante": "solo, formule standard", "verifie_contre": "AXA SA (QRT réel)"},
        {"template": "S.25.01.21", "row": "R0010", "col": "C0110", "libelle_attendu": "Risque de marché",
         "variante": "solo, formule standard, suffixe .21 (taxonomie 2025)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
        {"template": "S.25.01.21", "row": "R0010", "col": "C0090", "libelle_attendu": "Risque de marché",
         "variante": "solo, formule standard, colonne C0080 (net, taxonomie MACSF)",
         "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
        # Modèle interne (S.25.02-S.25.05) : PAS de code fixe universel
        # (constat Groupama vs Yuzzu, cf. docstring) — résolution par
        # libellé uniquement, via picture narrative ou lecture QRT label-
        # matchée au cas par cas (cf. extract_kpis.py, lire_picture_75).
    ],
    "scr_souscription_vie": [
        {"template": "S.25.01.22", "row": "R0030", "col": "C0040", "libelle_attendu": "Life underwriting risk",
         "variante": "groupe, formule standard", "verifie_contre": "solvencytool.com EIOPA_S.25.01_group.pdf"},
        {"template": "S.25.01.01", "row": "R0030", "col": "C0040", "libelle_attendu": "Life underwriting risk",
         "variante": "solo, formule standard", "verifie_contre": "AXA SA (QRT réel)"},
        {"template": "S.25.01.21", "row": "R0030", "col": "C0110", "libelle_attendu": "Risque de souscription en vie",
         "variante": "solo, formule standard, suffixe .21 (taxonomie 2025)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
        {"template": "S.25.01.21", "row": "R0030", "col": "C0090", "libelle_attendu": "Risque de souscription en vie",
         "variante": "solo, formule standard, colonne C0080 (net, taxonomie MACSF)",
         "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
    ],
    "scr_souscription_nonvie": [
        {"template": "S.25.01.22", "row": "R0050", "col": "C0040", "libelle_attendu": "Non-life underwriting risk",
         "variante": "groupe, formule standard", "verifie_contre": "solvencytool.com EIOPA_S.25.01_group.pdf"},
        {"template": "S.25.01.01", "row": "R0050", "col": "C0040", "libelle_attendu": "Non-life underwriting risk",
         "variante": "solo, formule standard", "verifie_contre": "AXA SA (QRT réel)"},
        {"template": "S.25.01.21", "row": "R0050", "col": "C0110", "libelle_attendu": "Risque de souscription en non-vie",
         "variante": "solo, formule standard, suffixe .21 (taxonomie 2025)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
        {"template": "S.25.01.21", "row": "R0050", "col": "C0090", "libelle_attendu": "Risque de souscription en non-vie",
         "variante": "solo, formule standard, colonne C0080 (net, taxonomie MACSF)",
         "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
        {"template": "S.25.05.22", "row": "R0310", "col": "C0010", "libelle_attendu": "Total Net Non-life underwriting risk",
         "variante": "groupe, modèle interne — CODE SPÉCIFIQUE GROUPAMA", "verifie_contre": "Groupama 2025 (extraction réelle)"},
    ],
    "scr_souscription_sante": [
        {"template": "S.25.01.22", "row": "R0040", "col": "C0040", "libelle_attendu": "Health underwriting risk",
         "variante": "groupe, formule standard", "verifie_contre": "solvencytool.com EIOPA_S.25.01_group.pdf"},
        {"template": "S.25.01.01", "row": "R0040", "col": "C0040", "libelle_attendu": "Health underwriting risk",
         "variante": "solo, formule standard", "verifie_contre": "AXA SA (QRT réel)"},
        {"template": "S.25.01.21", "row": "R0040", "col": "C0110", "libelle_attendu": "Risque de souscription en santé",
         "variante": "solo, formule standard, suffixe .21 (taxonomie 2025)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
        {"template": "S.25.01.21", "row": "R0040", "col": "C0090", "libelle_attendu": "Risque de souscription en santé",
         "variante": "solo, formule standard, colonne C0080 (net, taxonomie MACSF)",
         "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
    ],
    "scr_contrepartie": [
        {"template": "S.25.01.22", "row": "R0020", "col": "C0040", "libelle_attendu": "Counterparty default risk",
         "variante": "groupe, formule standard", "verifie_contre": "solvencytool.com EIOPA_S.25.01_group.pdf"},
        {"template": "S.25.01.01", "row": "R0020", "col": "C0040", "libelle_attendu": "Counterparty default risk",
         "variante": "solo, formule standard", "verifie_contre": "AXA SA (QRT réel)"},
        {"template": "S.25.01.21", "row": "R0020", "col": "C0110", "libelle_attendu": "Risque de défaut de la contrepartie",
         "variante": "solo, formule standard, suffixe .21 (taxonomie 2025)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
        {"template": "S.25.01.21", "row": "R0020", "col": "C0090", "libelle_attendu": "Risque de défaut de la contrepartie",
         "variante": "solo, formule standard, colonne C0080 (net, taxonomie MACSF)",
         "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
    ],
    "scr_operationnel": [
        {"template": "S.25.01.22", "row": "R0130", "col": "C0100", "libelle_attendu": "Operational risk",
         "variante": "groupe, formule standard", "verifie_contre": "solvencytool.com EIOPA_S.25.01_group.pdf"},
        {"template": "S.25.01.01", "row": "R0130", "col": "C0100", "libelle_attendu": "Operational risk",
         "variante": "solo, formule standard", "verifie_contre": "AXA SA (QRT réel)"},
        {"template": "S.25.01.21", "row": "R0130", "col": "C0110", "libelle_attendu": "Risque opérationnel",
         "variante": "solo, formule standard, suffixe .21 (taxonomie 2025)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
        {"template": "S.25.01.21", "row": "R0130", "col": "C0090", "libelle_attendu": "Risque opérationnel",
         "variante": "solo, formule standard, colonne C0080 (net, taxonomie MACSF)",
         "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
    ],
    "scr_diversification": [
        {"template": "S.25.01.22", "row": "R0060", "col": "C0040", "libelle_attendu": "Diversification",
         "variante": "groupe, formule standard", "verifie_contre": "solvencytool.com EIOPA_S.25.01_group.pdf"},
        {"template": "S.25.01.01", "row": "R0060", "col": "C0040", "libelle_attendu": "Diversification",
         "variante": "solo, formule standard", "verifie_contre": "AXA SA (QRT réel)"},
        {"template": "S.25.01.21", "row": "R0060", "col": "C0110", "libelle_attendu": "Diversification",
         "variante": "solo, formule standard, suffixe .21 (taxonomie 2025)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
        {"template": "S.25.01.21", "row": "R0060", "col": "C0090", "libelle_attendu": "Diversification",
         "variante": "solo, formule standard, colonne C0080 (net, taxonomie MACSF)",
         "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
        {"template": "S.25.05.22", "row": "R0060", "col": "C0100", "libelle_attendu": "Diversification",
         "variante": "groupe, modèle interne — CODE SPÉCIFIQUE GROUPAMA (Yuzzu, solo modèle interne, a R0020 pour le même concept : PAS un code universel)",
         "verifie_contre": "Groupama 2025 (extraction réelle) — cf. Décision 055"},
    ],

    # --- Provisions (codes IDENTIQUES solo/groupe, vérifié : Groupama,
    # AXA et Yuzzu utilisent tous S.02.01.02 avec les mêmes R0540/R0550/
    # R0630/R0640/R0670/R0680/R0710/R0720) ---
    "best_estimate": [
        {"template": "S.02.01.02", "row": ["R0540", "R0580", "R0630", "R0670", "R0710"], "col": "C0010",
         "libelle_attendu": "Best Estimate", "variante": "solo ET groupe, même codes (EN)",
         "verifie_contre": "Groupama 2025 + AXA SA + Yuzzu (3 QRT réels concordants)"},
        {"template": "S.02.01.02", "row": ["R0540", "R0580", "R0630", "R0670", "R0710"], "col": "C0010",
         "libelle_attendu": "Meilleure estimation", "variante": "solo ET groupe, même codes (FR)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
    ],
    "marge_risque": [
        {"template": "S.02.01.02", "row": ["R0550", "R0590", "R0640", "R0680", "R0720"], "col": "C0010",
         "libelle_attendu": "Risk margin", "variante": "solo ET groupe, même codes (EN)",
         "verifie_contre": "Groupama 2025 + AXA SA + Yuzzu (3 QRT réels concordants)"},
        {"template": "S.02.01.02", "row": ["R0550", "R0590", "R0640", "R0680", "R0720"], "col": "C0010",
         "libelle_attendu": "Marge de risque", "variante": "solo ET groupe, même codes (FR)",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)"},
    ],
    "provisions_techniques": [
        {"template": None, "row": None, "col": None, "libelle_attendu": None,
         "variante": "best_estimate + marge_risque, pas une cellule QRT dédiée",
         "verifie_contre": "calcul interne"},
    ],

    # --- MCR ---
    "mcr": [
        {"template": "S.23.01.22", "row": "R0610", "col": "C0010", "libelle_attendu": "Minimum consolidated Group SCR",
         "variante": "groupe (source Own Funds)", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.23.01.01", "row": "R0600", "col": "C0010", "libelle_attendu": "MCR",
         "variante": "solo (source Own Funds)", "verifie_contre": "Bornholms Brand + AXA SA (QRT réels)"},
        {"template": "S.23.01.01", "row": "R0600", "col": "C0060", "libelle_attendu": "Minimum de capital requis",
         "variante": "solo (FR), colonne C0060", "verifie_contre": "MACSF prévoyance 2025 (extraction réelle)"},
        {"template": "S.28.01.01", "row": "R0400", "col": "C0070", "libelle_attendu": "Minimum Capital Requirement",
         "variante": "solo, activité vie OU non-vie exclusivement", "verifie_contre": "AXA SA + Yuzzu (QRT réels)"},
        {"template": "S.28.02.01", "row": "R0400", "col": "C0130", "libelle_attendu": "Minimum de capital requis",
         "variante": "solo, activité vie ET non-vie (composite) — désormais vérifié",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle, croisé contre S.23.01.01/R0600, écart 0%, cf. Décision 059)"},
        {"template": "S.25.05.22", "row": "R0470", "col": "C0100",
         "libelle_attendu": "Minimum consolidated group solvency capital requirement",
         "variante": "groupe, modèle interne — CODE SPÉCIFIQUE GROUPAMA", "verifie_contre": "Groupama 2025 (extraction réelle)"},
    ],

    # --- Activité (codes IDENTIQUES solo/groupe, vérifié Groupama/AXA/Yuzzu) ---
    "primes_acquises_brutes": [
        {"template": "S.05.01.02", "row": ["R0210", "R0220", "R0230"], "col": "toutes", "libelle_attendu": "Premiums earned",
         "variante": "non-vie, solo ET groupe, même codes (EN)", "verifie_contre": "Groupama 2025 + AXA SA + Yuzzu (3 QRT réels)"},
        {"template": "S.05.01.02", "row": ["R1510"], "col": "toutes", "libelle_attendu": "Premiums earned",
         "variante": "vie, solo ET groupe, même codes (EN)", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.05.01.02", "row": ["R0210", "R0220", "R0230"], "col": "toutes", "libelle_attendu": "Primes acquises",
         "variante": "non-vie, même codes (FR) — colonne Total déjà peuplée chez CNP, exclue pour éviter le double-comptage",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)", "exclure_total": True},
        {"template": "S.05.01.02", "row": ["R1510"], "col": "toutes", "libelle_attendu": "Primes acquises",
         "variante": "vie, même codes (FR) — colonne Total déjà peuplée chez CNP, exclue pour éviter le double-comptage",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)", "exclure_total": True},
    ],
    "charge_sinistres": [
        {"template": "S.05.01.02", "row": ["R0310", "R0320", "R0330"], "col": "toutes", "libelle_attendu": "Claims incurred",
         "variante": "non-vie, solo ET groupe, même codes (EN)", "verifie_contre": "Groupama 2025 + AXA SA + Yuzzu (3 QRT réels)"},
        {"template": "S.05.01.02", "row": ["R1610"], "col": "toutes", "libelle_attendu": "Claims incurred",
         "variante": "vie, solo ET groupe, même codes (EN)", "verifie_contre": "Groupama 2025 (extraction réelle)"},
        {"template": "S.05.01.02", "row": ["R0310", "R0320", "R0330"], "col": "toutes", "libelle_attendu": "Charge des sinistres",
         "variante": "non-vie, même codes (FR) — colonne Total déjà peuplée chez CNP, exclue pour éviter le double-comptage",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)", "exclure_total": True},
        {"template": "S.05.01.02", "row": ["R1610"], "col": "toutes", "libelle_attendu": "Charge des sinistres",
         "variante": "vie, même codes (FR) — colonne Total déjà peuplée chez CNP, exclue pour éviter le double-comptage",
         "verifie_contre": "CNP Assurances 2025 (extraction réelle)", "exclure_total": True},
    ],
    "resultat_technique": [
        # Aucun équivalent QRT standardisé trouvé (Décision 051, audit
        # exhaustif) — reste NULL par construction, jamais deviné.
    ],
}


def templates_utilises(kpi_name):
    """Liste des codes de template (sans suffixe .01/.02/...) référencés
    pour un KPI donné, dans l'ordre de priorité."""
    return [v["template"] for v in KPI_QRT_MAPPING.get(kpi_name, []) if v.get("template")]


def variantes_disponibles(kpi_name, templates_presents):
    """Filtre les variantes d'un KPI à celles dont le template (préfixe,
    ex. "S.25.01.22" matche "S.25.01.22.01") est présent dans
    `templates_presents` (ensemble de préfixes de template détectés dans
    le document, cf. detecter_templates.py) — conserve l'ordre de
    priorité déclaré dans KPI_QRT_MAPPING."""
    return [
        v for v in KPI_QRT_MAPPING.get(kpi_name, [])
        if v.get("template") and any(t.startswith(v["template"]) for t in templates_presents)
    ]


if __name__ == "__main__":
    print(f"{len(KPI_QRT_MAPPING)} KPIs mappés")
    for kpi, variantes in KPI_QRT_MAPPING.items():
        print(f"  {kpi:28} : {len(variantes)} variante(s)")
