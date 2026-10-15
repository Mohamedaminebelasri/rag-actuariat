# -*- coding: utf-8 -*-
"""comparabilite.py — Règles de comparabilité des KPIs entre sociétés
(Décision 153), exportées vers le front-end par export_kpis_for_frontend.py.

Source : RAPPORT_comparabilite_KPIs.md § 3 (matrice KPI × axe) et § 4
(indicateurs normalisés). Trois éléments :
- MATRICE : pour chaque KPI et chacun des 4 axes (activité, forme juridique,
  modèle de capital, périmètre), un verdict C (comparable), R (comparable
  avec réserve), N (non comparable tel quel) ou NA (valeur structurellement
  nulle) et sa raison. Règle d'usage : pour un KPI et deux sociétés, prendre
  le pire verdict parmi les axes où elles diffèrent.
- groupe_pairs() : activité × modèle de capital × périmètre.
- indicateurs() : ratios normalisés calculés depuis kpis / kpi_composants.
"""

AXES = ("activite", "forme", "modele", "perimetre")

_MODULES = ("scr_marche", "scr_contrepartie", "scr_souscription_vie", "scr_souscription_sante",
            "scr_souscription_nonvie")


def _v(verdict, note=None):
    return {"verdict": verdict, "note": note}


_N_MODELE = _v("N", "Modèle interne : pas de modules standard, catégories et diversification propres au modèle.")
_R_PERIM = _v("R", "Groupe : calcul consolidé (diversification entre entités, fonds propres non disponibles).")
_R_BRUT = _v("R", "Montant brut (avant absorption des pertes par les provisions) : en vie il dépasse largement "
                  "le SCR net. Comparer en part de la somme des modules, pas du SCR.")

MATRICE = {
    "ratio_scr": {
        "activite": _v("R", "Niveau habituel propre à chaque métier (médianes 2025 : santé 270 %, vie 202 %, non-vie 167 %)."),
        "forme": _v("R", "Mutuelles et SAM sans accès au marché des actions : structurellement plus capitalisées."),
        "modele": _v("R", "Calibrage propre au modèle interne ; correction pour volatilité parfois dynamique (jusqu'à +46 pts). "
                          "Comparer aussi ratio_scr_sans_mesures_lt_pct."),
        "perimetre": _R_PERIM,
    },
    "ratio_mcr": {
        "activite": _v("R", "Formule MCR différente vie / non-vie ; ratio surtout dicté par le corridor 25-45 % du SCR."),
        "forme": _v("R", "Plancher absolu du MCR pour les petites structures."),
        "modele": _v("R", "MCR en formule linéaire pour tous, mais corridor appliqué au SCR du modèle interne."),
        "perimetre": _v("N", "Groupe : ratio au « SCR minimal consolidé » (S.23.01.22 R0650), pas un ratio MCR."),
    },
    "mcr": {
        "activite": _v("R", "Formule linéaire différente vie / non-vie."),
        "forme": _v("R", "Plancher absolu pour les petites structures."),
        "modele": _v("R", "Corridor appliqué au SCR du modèle interne."),
        "perimetre": _v("N", "Groupe : « SCR minimal consolidé » (S.23.01.22 R0610 = somme des MCR solo), pas un MCR."),
    },
    "scr_total": {
        "activite": _v("R", "Taille et profil de risque."), "forme": _v("C"),
        "modele": _v("R", "Calibrage propre au modèle interne."), "perimetre": _v("R", "Pas la somme des SCR solo."),
    },
    "fonds_propres_eligibles": {
        "activite": _v("C"), "forme": _v("R", "Fonds d'établissement, rappels de cotisations, certificats mutualistes."),
        "modele": _v("C"), "perimetre": _v("R", "Tests de disponibilité au niveau du groupe."),
    },
    **{k: {
        "activite": _v("C"),
        "forme": _v("R", "Les mutuelles n'émettent pas d'actions ; T2/T3 peuvent être des fonds propres auxiliaires "
                         "(rappels de cotisations, engagements du groupe)."),
        "modele": _v("C"), "perimetre": _v("R", "Disponibilité au niveau du groupe."),
    } for k in ("fonds_propres_t1_nr", "fonds_propres_t1_r", "fonds_propres_t2", "fonds_propres_t3")},
    "scr_marche": {"activite": _R_BRUT, "forme": _v("C"), "modele": _N_MODELE, "perimetre": _R_PERIM},
    "scr_contrepartie": {"activite": _R_BRUT, "forme": _v("C"), "modele": _N_MODELE, "perimetre": _R_PERIM},
    "scr_souscription_vie": {
        "activite": _v("R", "Nul par construction pour un non-vie pur ; montant brut (cf. scr_marche)."),
        "forme": _v("C"), "modele": _v("N", "Modèle interne : vie ET santé confondus, catégories propres."),
        "perimetre": _R_PERIM,
    },
    "scr_souscription_sante": {
        "activite": _v("R", "Montant brut ; nul pour un assureur sans santé."),
        "forme": _v("C"), "modele": _v("N", "Modèle interne : inclus dans scr_souscription_vie (NULL)."),
        "perimetre": _R_PERIM,
    },
    "scr_souscription_nonvie": {
        "activite": _v("NA", "Nul par construction pour les assureurs vie et santé (la santé non-vie va dans le module santé)."),
        "forme": _v("C"), "modele": _N_MODELE, "perimetre": _R_PERIM,
    },
    "scr_operationnel": {
        "activite": _v("C", "Formule factorielle commune en formule standard."), "forme": _v("C"),
        "modele": _v("N", "Modèle interne : approche par scénarios."), "perimetre": _R_PERIM,
    },
    "scr_diversification": {
        "activite": _v("R", "Dépend du nombre de modules actifs (mono-activité ~24 %, groupes mixtes 30-43 % des modules)."),
        "forme": _v("C"), "modele": _v("N", "Modèle interne : diversification calculée sur d'autres catégories."),
        "perimetre": _v("R", "Inclut la diversification entre entités du groupe."),
    },
    "best_estimate": {
        "activite": _v("R", "Vie : participation aux bénéfices future, options, UC ≈ actifs ; non-vie : sinistres à court terme."),
        "forme": _v("C"), "modele": _v("C"), "perimetre": _v("R", "Éliminations intra-groupe."),
    },
    "marge_risque": {
        "activite": _v("R", "Rapport au BE structurel (médianes : vie 1 %, non-vie 6 %, santé 11 %)."),
        "forme": _v("C"), "modele": _v("R", "Calculée avec le SCR du modèle."), "perimetre": _v("R", "Éliminations intra-groupe."),
    },
    "provisions_techniques": {
        "activite": _v("R", "Cf. best_estimate ; mesure transitoire sur provisions chez La Mondiale / SGAM AG2R."),
        "forme": _v("C"), "modele": _v("C"), "perimetre": _v("R", "Éliminations intra-groupe."),
    },
    "primes_acquises_brutes": {
        "activite": _v("R", "Vie : surtout de la collecte d'épargne ; non-vie : prime de risque. Inclut la réassurance acceptée."),
        "forme": _v("C"), "modele": _v("C"), "perimetre": _v("R", "Montants consolidés."),
    },
    "charge_sinistres": {
        "activite": _v("N", "Vie (S.05.01 R1610) = prestations (rachats, échéances, rentes) ; non-vie = sinistres survenus."),
        "forme": _v("C"), "modele": _v("C"), "perimetre": _v("R", "Montants consolidés."),
    },
}

# Sur l'axe activité, "N" pour charge_sinistres ne s'applique qu'entre une
# activité « vie » et une activité « non-vie » (la santé non-vie se compare
# au non-vie). Le front-end compare les classes ci-dessous, pas l'activité brute.
CLASSE_SINISTRES = {"Vie": "vie", "Non-vie": "non-vie", "Santé/prévoyance": "non-vie", "Mixte": "mixte"}

ORDRE_VERDICTS = {"C": 0, "NA": 1, "R": 2, "N": 3}


def libelle_modele(scr_method):
    return "Formule standard" if scr_method == "formule_standard" else "Modèle interne"


def groupe_pairs(activite, scr_method, perimetre):
    return f"{activite} · {libelle_modele(scr_method)} · {perimetre}"


def _classe_composant(code, label):
    s = f"{code or ''} {label or ''}"
    if any(r in s for r in ("R0210", "R0220", "R0230", "R0310", "R0320", "R0330")):
        return "non-vie"
    if "R1510" in s or "R1610" in s:
        return "vie"
    low = s.lower()
    if "non-vie" in low or "assurance directe" in low or "acceptée" in low:
        return "non-vie"
    if "vie" in low or s.strip() == "Brut Brut":
        return "vie"
    return None


def indicateurs(kpis, composants, perimetre, scr_method, lt=None):
    """kpis : {kpi_name: valeur} ; composants : {kpi_name: [(code, label, valeur)]} ;
    lt : ligne de la table impact_mesures_lt (Décision 155) ou None."""
    def g(k):
        return kpis.get(k)

    out = {}
    fp, t1 = g("fonds_propres_eligibles"), g("fonds_propres_t1_nr")
    if fp and t1 is not None:
        out["part_t1_non_restreint_pct"] = round(t1 / fp * 100, 1)
    be, rm, scr = g("best_estimate"), g("marge_risque"), g("scr_total")
    if be and rm is not None:
        out["marge_risque_sur_be_pct"] = round(rm / be * 100, 2)

    modules = {m: g(m) for m in _MODULES if g(m) is not None}
    somme = sum(modules.values())
    div, op = g("scr_diversification"), g("scr_operationnel")
    if scr_method != "formule_standard":
        # Décision 157 : catégories propres au modèle interne, santé dans vie —
        # une composition en parts serait trompeuse à côté de la formule standard.
        out["composition_modules_pct"] = None
    elif somme > 0:
        out["composition_modules_pct"] = {m: round(v / somme * 100, 1) for m, v in modules.items()}
    if somme > 0 and div is not None:
        out["diversification_sur_modules_pct"] = round(-div / somme * 100, 1)
    if scr and somme > 0 and div is not None and op is not None and len(modules) >= 4:
        out["ajustements_sur_scr_pct"] = round((scr - somme - div - op) / scr * 100, 1) + 0.0

    pr = g("primes_acquises_brutes")
    if scr and be and pr:
        out["scr_sur_primes_plus_be_pct"] = round(scr / (pr + be) * 100, 2)

    def part_nonvie(kpi):
        lignes = composants.get(kpi) or []
        if not lignes or any(_classe_composant(c, l) is None for c, l, _ in lignes):
            return None
        return sum(v for c, l, v in lignes if _classe_composant(c, l) == "non-vie")
    p_nv, s_nv = part_nonvie("primes_acquises_brutes"), part_nonvie("charge_sinistres")
    # Pas de S/P sur un portefeuille non-vie marginal (< 10 % des primes) ou
    # minuscule (< 10 M€) : bruit (ex. Macifilia, 6 M€ de primes, −16 917 %).
    if p_nv and s_nv is not None and pr and p_nv >= 10 and p_nv / pr >= 0.10:
        out["sp_nonvie_pct"] = round(s_nv / p_nv * 100, 1)

    mcr = g("mcr")
    if perimetre == "solo" and mcr and scr:
        x = mcr / scr * 100
        out["position_mcr"] = ("plancher_25" if abs(x - 25) < 0.6 else "plafond_45" if abs(x - 45) < 0.6
                               else "plancher_absolu" if x > 45.6 else "entre_25_45")
    out["base_scr"] = "formule_standard" if scr_method == "formule_standard" else "modele_interne"
    if lt:
        out.update(_indicateurs_mesures_lt(lt, g("ratio_scr")))
    return out


def _indicateurs_mesures_lt(lt, ratio_publie):
    """lt : ligne de impact_mesures_lt (M€). S.22.01 suit l'approche par
    étapes : l'impact VA est mesuré après retrait des transitoires."""
    out = {"utilise_va": bool(lt["utilise_va"]), "mesure_transitoire": bool(lt["mesure_transitoire"])}
    if lt["ratio_scr_sans_va_publie"] is not None:
        sans = lt["ratio_scr_sans_va_publie"]
        out["ratio_scr_sans_mesures_lt_pct"] = round(sans, 1)
        out["impact_va_pts"] = round(sans - ratio_publie, 1) if ratio_publie else None
        out["impact_mesures_lt_pts"] = out["impact_va_pts"]
        return out
    if lt["fp_avec"] is None:  # aucune mesure : ratio inchangé
        out.update(ratio_scr_sans_mesures_lt_pct=ratio_publie, impact_va_pts=0.0, impact_mesures_lt_pts=0.0)
        return out
    fp, scr = lt["fp_avec"], lt["scr_avec"]
    avec = fp / scr * 100
    sans_tr = (fp + lt["delta_fp_transitoires"]) / (scr + lt["delta_scr_transitoires"]) * 100
    sans_tout = ((fp + lt["delta_fp_transitoires"] + lt["delta_fp_va"])
                 / (scr + lt["delta_scr_transitoires"] + lt["delta_scr_va"]) * 100)
    out["ratio_scr_sans_mesures_lt_pct"] = round(sans_tout, 1)
    out["impact_va_pts"] = round(sans_tout - sans_tr, 1) + 0.0
    if lt["mesure_transitoire"]:
        out["impact_transitoires_pts"] = round(sans_tr - avec, 1)
    out["impact_mesures_lt_pts"] = round(sans_tout - avec, 1) + 0.0
    return out


DEFINITIONS_INDICATEURS = {
    "part_t1_non_restreint_pct": "Fonds propres T1 non restreint / fonds propres éligibles. Comparable avec réserve entre formes juridiques.",
    "marge_risque_sur_be_pct": "Marge de risque / best estimate. À comparer à l'intérieur d'une même activité seulement.",
    "composition_modules_pct": "Part de chaque module dans la somme des modules (pas dans le SCR). Formule standard entre elles ; null pour les sociétés en modèle interne.",
    "diversification_sur_modules_pct": "|Diversification| / somme des modules. Formule standard entre elles ; non comparable avec un modèle interne.",
    "ajustements_sur_scr_pct": "(SCR − modules − diversification − opérationnel) / SCR : absorption des pertes par les provisions et impôts différés (+ autres ajustements). Très négatif en vie.",
    "scr_sur_primes_plus_be_pct": "SCR / (primes acquises brutes + best estimate brut), proche de l'indicateur Milliman SCR / (cotisations + BE nets).",
    "sp_nonvie_pct": "Charge de sinistres / primes acquises, lignes non-vie (y c. santé non-vie) seulement ; calculé si ces lignes pèsent au moins 10 % des primes et 10 M€. Absent pour la vie.",
    "position_mcr": "Position du MCR dans le corridor réglementaire (plancher 25 %, plafond 45 % du SCR, plancher absolu). Si borné, le ratio MCR n'est qu'un multiple du ratio SCR.",
    "base_scr": "Base de calcul du SCR : formule_standard ou modele_interne.",
    "utilise_va": "La société applique la correction pour volatilité (VA, article 77 quinquies).",
    "mesure_transitoire": "La société applique une mesure transitoire (provisions techniques ou taux).",
    "ratio_scr_sans_mesures_lt_pct": "Ratio de couverture du SCR sans VA ni mesure transitoire (S.22.01 : fonds propres et SCR recalculés). Base homogène pour comparer les ratios SCR entre sociétés.",
    "impact_va_pts": "Effet de la VA sur le ratio SCR, en points (négatif = la VA améliore le ratio publié). Approche par étapes : mesuré après retrait des transitoires. Generali : VA stochastique du modèle interne, valeur publiée dans le texte.",
    "impact_transitoires_pts": "Effet des mesures transitoires sur le ratio SCR, en points (BPCE Vie, La Mondiale, SGAM AG2R, Groupama).",
    "impact_mesures_lt_pts": "Effet cumulé VA + transitoires sur le ratio SCR, en points.",
}
