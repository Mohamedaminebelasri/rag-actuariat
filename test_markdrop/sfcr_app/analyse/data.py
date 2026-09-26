"""data.py — Définition des 20 KPIs SFCR + DONNÉES DE DÉMONSTRATION.

⚠️ Toutes les valeurs ci-dessous sont des DONNÉES MOCK (inventées pour le
développement de l'interface) — jamais de vraies valeurs extraites d'un
rapport SFCR. Un bandeau "Données de démonstration" est affiché dans
l'UI tant que le backend réel n'est pas branché (cf. page.py).
"""

from __future__ import annotations

# --- Les 4 catégories, dans l'ordre d'affichage demandé ---
CATEGORIES = [
    {"code": "E", "label": "Gestion du capital"},
    {"code": "D", "label": "Valorisation Solvabilité II"},
    {"code": "C", "label": "Profil de risque"},
    {"code": "A", "label": "Activité et résultats"},
]

# --- Les 20 KPIs (id, catégorie, code d'affichage, label, unité, description) ---
KPI_DEFINITIONS: list[dict] = [
    # E — Gestion du capital
    {"id": "ratio_scr", "categorie": "E", "code": "E1", "label": "Ratio SCR", "unite": "%",
     "description": "Fonds propres éligibles / SCR", "seuil_reglementaire": 100.0},
    {"id": "ratio_mcr", "categorie": "E", "code": "E2", "label": "Ratio MCR", "unite": "%",
     "description": "Fonds propres éligibles / MCR", "seuil_reglementaire": 100.0},
    {"id": "scr", "categorie": "E", "code": "E3", "label": "SCR", "unite": "Md€",
     "description": "Capital de solvabilité requis", "seuil_reglementaire": None},
    {"id": "mcr", "categorie": "E", "code": "E4", "label": "MCR", "unite": "Md€",
     "description": "Minimum de capital requis", "seuil_reglementaire": None},
    {"id": "fonds_propres_eligibles", "categorie": "E", "code": "E5", "label": "Fonds propres éligibles", "unite": "Md€",
     "description": "Total des fonds propres éligibles", "seuil_reglementaire": None},
    {"id": "fonds_propres_t1", "categorie": "E", "code": "E6", "label": "Fonds propres Tier 1", "unite": "Md€",
     "description": "Fonds propres de meilleure qualité", "seuil_reglementaire": None},
    {"id": "fonds_propres_t2", "categorie": "E", "code": "E7", "label": "Fonds propres Tier 2", "unite": "Md€",
     "description": "Fonds propres de qualité intermédiaire", "seuil_reglementaire": None},
    {"id": "surplus_capital", "categorie": "E", "code": "E8", "label": "Surplus de capital", "unite": "Md€",
     "description": "Fonds propres − SCR", "seuil_reglementaire": None},
    # D — Valorisation Solvabilité II
    {"id": "best_estimate", "categorie": "D", "code": "D1", "label": "Best Estimate total", "unite": "Md€",
     "description": "Provisions techniques — meilleure estimation", "seuil_reglementaire": None},
    {"id": "marge_risque", "categorie": "D", "code": "D2", "label": "Marge de risque", "unite": "Md€",
     "description": "Marge de risque réglementaire", "seuil_reglementaire": None},
    {"id": "provisions_techniques", "categorie": "D", "code": "D3", "label": "Total provisions techniques", "unite": "Md€",
     "description": "Best Estimate + marge de risque", "seuil_reglementaire": None},
    {"id": "total_actifs", "categorie": "D", "code": "D4", "label": "Total actifs (Solva II)", "unite": "Md€",
     "description": "Total actifs en valeur Solvabilité II", "seuil_reglementaire": None},
    # C — Profil de risque
    {"id": "scr_nonvie", "categorie": "C", "code": "C1", "label": "SCR souscription non-vie", "unite": "Md€",
     "description": "Risque de souscription non-vie", "seuil_reglementaire": None},
    {"id": "scr_vie", "categorie": "C", "code": "C2", "label": "SCR souscription vie", "unite": "Md€",
     "description": "Risque de souscription vie", "seuil_reglementaire": None},
    {"id": "scr_marche", "categorie": "C", "code": "C3", "label": "SCR risque de marché", "unite": "Md€",
     "description": "Risque de marché", "seuil_reglementaire": None},
    {"id": "scr_contrepartie", "categorie": "C", "code": "C4", "label": "SCR risque de contrepartie", "unite": "Md€",
     "description": "Risque de défaut de contrepartie", "seuil_reglementaire": None},
    {"id": "scr_operationnel", "categorie": "C", "code": "C5", "label": "SCR risque opérationnel", "unite": "Md€",
     "description": "Risque opérationnel", "seuil_reglementaire": None},
    {"id": "diversification", "categorie": "C", "code": "C6", "label": "Effet de diversification", "unite": "%",
     "description": "Réduction du SCR grâce à la diversification", "seuil_reglementaire": None},
    # A — Activité et résultats
    {"id": "primes_brutes", "categorie": "A", "code": "A1", "label": "Primes brutes émises", "unite": "Md€",
     "description": "Primes brutes émises sur l'exercice", "seuil_reglementaire": None},
    {"id": "ratio_sp", "categorie": "A", "code": "A2", "label": "Ratio S/P", "unite": "%",
     "description": "Sinistres / Primes (ratio combiné)", "seuil_reglementaire": 100.0},
]

KPI_PAR_ID = {k["id"]: k for k in KPI_DEFINITIONS}
KPI_IDS_PAR_CATEGORIE = {
    cat["code"]: [k["id"] for k in KPI_DEFINITIONS if k["categorie"] == cat["code"]]
    for cat in CATEGORIES
}

# Les 5 axes du radar chart (sous-ensemble du profil de risque C1-C5)
AXES_RADAR = ["scr_nonvie", "scr_vie", "scr_marche", "scr_contrepartie", "scr_operationnel"]


def _kpi(valeur, variation=None, variation_unit="pts", chapitre="", page=None, confiance="extracted"):
    return {
        "valeur": valeur, "variation": variation, "variation_unit": variation_unit,
        "chapitre_source": chapitre, "page_source": page, "confiance": confiance,
        "date_extraction": "2026-09-25",
    }


# --- DONNÉES DE DÉMONSTRATION — 5 assureurs mock, aucune valeur réelle ---
_DEMO_SFCR: dict[str, dict] = {
    "Groupama": {
        "annee": 2023,
        "kpis": {
            "ratio_scr": _kpi(267.0, 12.0, "pts", "E.2", 89, "verified"),
            "ratio_mcr": _kpi(589.0, 8.0, "pts", "E.2", 90, "verified"),
            "scr": _kpi(6.02, -0.3, "Md€", "E.2", 89, "verified"),
            "mcr": _kpi(2.71, 0.1, "Md€", "E.2", 90, "extracted"),
            "fonds_propres_eligibles": _kpi(16.08, 1.1, "Md€", "E.1", 87, "verified"),
            "fonds_propres_t1": _kpi(13.4, 0.9, "Md€", "E.1", 87, "extracted"),
            "fonds_propres_t2": _kpi(2.68, 0.2, "Md€", "E.1", 87, "extracted"),
            "surplus_capital": _kpi(10.06, 1.4, "Md€", "E.2", 89, "verified"),
            "best_estimate": _kpi(69.0, 2.1, "Md€", "D.2", 78, "verified"),
            "marge_risque": _kpi(2.38, 0.1, "Md€", "D.2", 79, "extracted"),
            "provisions_techniques": _kpi(71.4, 2.2, "Md€", "D.2", 78, "verified"),
            "total_actifs": _kpi(94.6, 3.5, "Md€", "D.1", 75, "extracted"),
            "scr_nonvie": _kpi(2.47, 0.15, "Md€", "C.1", 85, "verified"),
            "scr_vie": _kpi(1.46, -0.05, "Md€", "C.1", 85, "extracted"),
            "scr_marche": _kpi(4.68, 0.3, "Md€", "C.1", 85, "verified"),
            "scr_contrepartie": _kpi(0.79, 0.02, "Md€", "C.1", 85, "extracted"),
            "scr_operationnel": _kpi(0.68, 0.04, "Md€", "C.1", 85, "extracted"),
            "diversification": _kpi(-38.0, -1.5, "pts", "C.1", 85, "verified"),
            "primes_brutes": _kpi(16.9, 0.8, "Md€", "A.1", 12, "verified"),
            "ratio_sp": _kpi(94.2, -1.8, "pts", "A.1", 14, "extracted"),
        },
    },
    "AXA France": {
        "annee": 2023,
        "kpis": {
            "ratio_scr": _kpi(198.0, -5.0, "pts", "E.2", 91, "extracted"),
            "ratio_mcr": _kpi(410.0, 3.0, "pts", "E.2", 92, "extracted"),
            "scr": _kpi(9.8, 0.4, "Md€", "E.2", 91, "verified"),
            "mcr": _kpi(4.4, 0.2, "Md€", "E.2", 92, "extracted"),
            "fonds_propres_eligibles": _kpi(19.4, 0.5, "Md€", "E.1", 88, "verified"),
            "fonds_propres_t1": _kpi(15.9, 0.4, "Md€", "E.1", 88, "extracted"),
            "fonds_propres_t2": _kpi(3.5, 0.1, "Md€", "E.1", 88, "extracted"),
            "surplus_capital": _kpi(9.6, 0.1, "Md€", "E.2", 91, "verified"),
            "best_estimate": _kpi(102.0, 4.5, "Md€", "D.2", 80, "extracted"),
            "marge_risque": _kpi(3.1, 0.2, "Md€", "D.2", 81, "extracted"),
            "provisions_techniques": _kpi(105.1, 4.7, "Md€", "D.2", 80, "verified"),
            "total_actifs": _kpi(138.2, 5.1, "Md€", "D.1", 76, "extracted"),
            "scr_nonvie": _kpi(3.1, 0.2, "Md€", "C.1", 86, "extracted"),
            "scr_vie": _kpi(2.9, -0.1, "Md€", "C.1", 86, "extracted"),
            "scr_marche": _kpi(6.2, 0.5, "Md€", "C.1", 86, "verified"),
            "scr_contrepartie": _kpi(1.1, 0.05, "Md€", "C.1", 86, "extracted"),
            "scr_operationnel": _kpi(0.9, 0.03, "Md€", "C.1", 86, "extracted"),
            "diversification": _kpi(-29.0, 1.0, "pts", "C.1", 86, "extracted"),
            "primes_brutes": _kpi(24.3, -0.6, "Md€", "A.1", 13, "verified"),
            "ratio_sp": _kpi(101.5, 2.1, "pts", "A.1", 15, "extracted"),
        },
    },
    "CNP Assurances": {
        "annee": 2023,
        "kpis": {
            "ratio_scr": _kpi(228.0, 6.0, "pts", "E.2", 90, "verified"),
            "ratio_mcr": _kpi(470.0, 10.0, "pts", "E.2", 91, "extracted"),
            "scr": _kpi(13.9, -0.2, "Md€", "E.2", 90, "verified"),
            "mcr": _kpi(6.2, -0.1, "Md€", "E.2", 91, "extracted"),
            "fonds_propres_eligibles": _kpi(31.7, 1.8, "Md€", "E.1", 87, "verified"),
            "fonds_propres_t1": _kpi(27.1, 1.5, "Md€", "E.1", 87, "extracted"),
            "fonds_propres_t2": _kpi(4.6, 0.3, "Md€", "E.1", 87, "extracted"),
            "surplus_capital": _kpi(17.8, 2.0, "Md€", "E.2", 90, "verified"),
            "best_estimate": _kpi(280.0, 6.2, "Md€", "D.2", 77, "extracted"),
            "marge_risque": _kpi(5.9, 0.3, "Md€", "D.2", 78, "extracted"),
            "provisions_techniques": _kpi(285.9, 6.5, "Md€", "D.2", 77, "verified"),
            "total_actifs": _kpi(410.5, 8.9, "Md€", "D.1", 74, "extracted"),
            "scr_nonvie": _kpi(0.4, 0.02, "Md€", "C.1", 84, "extracted"),
            "scr_vie": _kpi(9.8, 0.4, "Md€", "C.1", 84, "verified"),
            "scr_marche": _kpi(7.1, 0.2, "Md€", "C.1", 84, "verified"),
            "scr_contrepartie": _kpi(0.6, 0.01, "Md€", "C.1", 84, "extracted"),
            "scr_operationnel": _kpi(0.7, 0.02, "Md€", "C.1", 84, "extracted"),
            "diversification": _kpi(-34.0, -0.5, "pts", "C.1", 84, "verified"),
            "primes_brutes": _kpi(35.6, 1.9, "Md€", "A.1", 11, "verified"),
            "ratio_sp": _kpi(89.7, -0.9, "pts", "A.1", 13, "extracted"),
        },
    },
    "Covéa": {
        "annee": 2023,
        "kpis": {
            "ratio_scr": _kpi(305.0, 15.0, "pts", "E.2", 92, "verified"),
            "ratio_mcr": _kpi(640.0, 20.0, "pts", "E.2", 93, "extracted"),
            "scr": _kpi(5.4, 0.1, "Md€", "E.2", 92, "verified"),
            "mcr": _kpi(2.4, 0.05, "Md€", "E.2", 93, "extracted"),
            "fonds_propres_eligibles": _kpi(16.5, 1.9, "Md€", "E.1", 89, "verified"),
            "fonds_propres_t1": _kpi(14.2, 1.6, "Md€", "E.1", 89, "extracted"),
            "fonds_propres_t2": _kpi(2.3, 0.3, "Md€", "E.1", 89, "extracted"),
            "surplus_capital": _kpi(11.1, 1.8, "Md€", "E.2", 92, "verified"),
            "best_estimate": _kpi(28.5, 0.9, "Md€", "D.2", 79, "extracted"),
            "marge_risque": _kpi(1.2, 0.05, "Md€", "D.2", 80, "extracted"),
            "provisions_techniques": _kpi(29.7, 1.0, "Md€", "D.2", 79, "verified"),
            "total_actifs": _kpi(41.3, 1.5, "Md€", "D.1", 75, "extracted"),
            "scr_nonvie": _kpi(2.9, 0.1, "Md€", "C.1", 85, "verified"),
            "scr_vie": _kpi(0.5, 0.01, "Md€", "C.1", 85, "extracted"),
            "scr_marche": _kpi(2.6, 0.1, "Md€", "C.1", 85, "verified"),
            "scr_contrepartie": _kpi(0.5, 0.01, "Md€", "C.1", 85, "extracted"),
            "scr_operationnel": _kpi(0.4, 0.01, "Md€", "C.1", 85, "extracted"),
            "diversification": _kpi(-25.0, 0.8, "pts", "C.1", 85, "extracted"),
            "primes_brutes": _kpi(14.1, 0.5, "Md€", "A.1", 12, "verified"),
            "ratio_sp": _kpi(97.8, 3.2, "pts", "A.1", 14, "extracted"),
        },
    },
    "MACSF": {
        "annee": 2023,
        "kpis": {
            "ratio_scr": _kpi(521.0, 22.0, "pts", "E.2", 88, "verified"),
            "ratio_mcr": _kpi(2084.0, 60.0, "pts", "E.2", 89, "extracted"),
            "scr": _kpi(0.44, 0.02, "Md€", "E.2", 88, "verified"),
            "mcr": _kpi(0.11, 0.005, "Md€", "E.2", 89, "extracted"),
            "fonds_propres_eligibles": _kpi(2.29, 0.15, "Md€", "E.1", 86, "verified"),
            "fonds_propres_t1": _kpi(2.29, 0.15, "Md€", "E.1", 86, "extracted"),
            "fonds_propres_t2": _kpi(0.0, 0.0, "Md€", "E.1", 86, "extracted"),
            "surplus_capital": _kpi(1.85, 0.13, "Md€", "E.2", 88, "verified"),
            "best_estimate": _kpi(0.88, 0.04, "Md€", "D.2", 76, "extracted"),
            "marge_risque": _kpi(0.14, 0.01, "Md€", "D.2", 77, "extracted"),
            "provisions_techniques": _kpi(1.02, 0.05, "Md€", "D.2", 76, "verified"),
            "total_actifs": _kpi(3.4, 0.2, "Md€", "D.1", 73, "extracted"),
            "scr_nonvie": _kpi(0.0, 0.0, "Md€", "C.1", 83, "extracted"),
            "scr_vie": _kpi(0.02, 0.001, "Md€", "C.1", 83, "extracted"),
            "scr_marche": _kpi(0.5, 0.03, "Md€", "C.1", 83, "verified"),
            "scr_contrepartie": _kpi(0.004, 0.0, "Md€", "C.1", 83, "extracted"),
            "scr_operationnel": _kpi(0.002, 0.0, "Md€", "C.1", 83, "extracted"),
            "diversification": _kpi(-12.0, 0.3, "pts", "C.1", 83, "extracted"),
            "primes_brutes": _kpi(0.43, 0.02, "Md€", "A.1", 10, "verified"),
            "ratio_sp": _kpi(76.4, -2.1, "pts", "A.1", 12, "extracted"),
        },
    },
}


def liste_sfcr_disponibles() -> list[dict]:
    """Format attendu par le sélecteur : {id, label, annee, disponible}."""
    return [
        {"id": nom, "label": f"{nom} — SFCR {info['annee']}", "annee": info["annee"], "disponible": True}
        for nom, info in _DEMO_SFCR.items()
    ]


def kpis_societe(nom: str) -> dict:
    return _DEMO_SFCR.get(nom, {}).get("kpis", {})


def toutes_les_societes() -> list[str]:
    return list(_DEMO_SFCR.keys())
