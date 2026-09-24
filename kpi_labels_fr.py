# -*- coding: utf-8 -*-
"""kpi_labels_fr.py — Libellés français pour l'extraction par libellé
(Phase 3.9, Décision 064), fallback pour les documents SANS code R0xxx/
C0xxx (MAIF, Covéa — vérifié visuellement, cf. diagnostic session
précédente : tableaux QRT réels et complets, mais entièrement rédigés en
libellé français, code du template seulement dans le titre de section).

CHAQUE libellé listé ici a été VU DIRECTEMENT (rendu image ou texte
brut PyMuPDF) sur au moins un document réel — aucun n'est deviné :
- MAIF 2025 (pages 121-123, texte natif pour S.23.01.01 uniquement —
  S.17.01.02/S.22.01.21/S.25.01.21/S.28.01.01 sont en image, non
  couvertes par l'extraction texte, cf. Décision 064)
- Covéa 2025 (pages 84-98, texte natif pour TOUT l'annexe)
- Groupama/CNP/MACSF (libellés français déjà vérifiés dans
  kpi_qrt_mapping.py pour les variantes "(FR)")

L'ordre compte : 1re variante trouvée dans le texte de la page = celle
utilisée. Le matching est EXACT (après normalisation espaces/casse/
accents optionnelle), JAMAIS par sous-chaîne — Décision 057 a trouvé un
vrai bug où "Life underwriting risk" matchait "Non-life underwriting
risk" par inclusion ; même règle ici pour "vie"/"non-vie" et "MCR"/"SCR"."""

KPI_LABELS_FR = {
    "ratio_scr": [
        "Ratio fonds propres éligibles sur capital de solvabilité requis",  # CNP, MACSF
        "Ratio des fonds propres éligibles sur le capital de solvabilité requis",  # variante orthographe
        "Ratio de couverture du SCR",
        "Ratio fonds propres éligibles sur capital de solvabilité requis du groupe (y compris autres secteurs financiers et entreprises incluses par déduction et agrégation)",  # Covéa (groupe)
    ],
    "ratio_mcr": [
        "Ratio fonds propres éligibles sur minimum de capital requis",  # CNP, MACSF
        "Ratio des fonds propres éligibles sur le minimum de capital requis",
        "Ratio de couverture du MCR",
        "Ratio fonds propres éligibles sur minimum de capital de solvabilité requis du groupe sur base consolidée",  # Covéa (groupe)
    ],
    "fonds_propres_eligibles": [
        "Total des fonds propres éligibles pour couvrir le capital de solvabilité requis",  # CNP
        "Total des fonds propres éligibles pour couvrir le capital de solvabilité requis au 31/12/2025",  # MAIF
        "Fonds propres totaux éligibles pour le calcul du capital de solvabilité requis",  # MAIF variante
        "Total fonds propres éligibles et disponibles",
        "Total des fonds propres éligibles servant à couvrir le capital de solvabilité requis du groupe (y compris fonds propres des autres secteurs financiers et entreprises incluses par déduction et agrégation)",  # Covéa (groupe) — apparié au ratio_scr ci-dessus, même base
    ],
    "scr_total": [
        "Capital de solvabilité requis",  # MAIF p.122, Covéa p.95 — vu tel quel, ligne finale du tableau SCR
        "Capital de solvabilité requis du groupe sur base consolidée",  # Covéa (groupe)
    ],
    "mcr": [
        "Minimum de capital requis",  # MAIF p.122, S.23.01.01
        "Minimum de capital de solvabilité requis du groupe sur base consolidée",  # Covéa (groupe, S.25.01.22)
    ],
    "scr_diversification": [
        "Diversification",  # MAIF p.123, Covéa p.95 — ligne isolée du tableau SCR
    ],
    "scr_marche": [
        "Risque de marché",  # MAIF p.123, Covéa p.95
    ],
    "scr_souscription_vie": [
        "Risque de souscription en vie",  # MAIF p.123, Covéa p.95
    ],
    "scr_souscription_nonvie": [
        "Risque de souscription en non-vie",  # MAIF p.123, Covéa p.95
    ],
    "scr_souscription_sante": [
        "Risque de souscription en santé",  # MAIF p.123, Covéa p.95
    ],
    "scr_contrepartie": [
        "Risque de défaut de la contrepartie",  # MAIF p.123, Covéa p.95
    ],
    "scr_operationnel": [
        "Risque opérationnel",  # MAIF p.123, Covéa p.95
    ],
    "best_estimate": [
        "Meilleure estimation",  # Groupama/CNP/MACSF/Covéa S.02.01 — ATTENTION : répété plusieurs fois
        # par segment (non-vie/santé/vie/UC) sur la même page — la somme
        # de TOUTES les occurrences est nécessaire, pas la 1re seule
        # (cf. extraire_par_libelle, mode "sommer_toutes_occurrences").
    ],
    "marge_risque": [
        "Marge de risque",  # idem best_estimate — répété par segment, à sommer
    ],
    "primes_acquises_brutes": [
        "Primes acquises",  # Covéa p.86-88 — section avec sous-lignes "Brut – ..." à sommer
    ],
    "charge_sinistres": [
        "Charge des sinistres",  # Covéa p.86-88, même structure
    ],
}
