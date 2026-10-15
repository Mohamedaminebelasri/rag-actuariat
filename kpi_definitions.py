"""kpi_definitions.py — Référence unique des 21 KPIs actuariels à extraire
(Phase 3, Décision 050), indépendante du RAG/Qdrant.

KPI_DEFINITIONS : liste de 21 dicts, 6 catégories (solvabilité, fonds
propres, scr, provisions, mcr, activité). Chaque KPI porte sa source QRT
et son chapitre SFCR narratif correspondant, pour guider l'extraction
(Phase 3, étapes suivantes) — ce fichier ne fait AUCUNE extraction
lui-même, c'est une table de référence statique.

`sign` : "positive" (montant/ratio toujours positif), "negative" (ex.
scr_diversification, un bénéfice de diversification qui SOUSTRAIT du SCR
total), ou "any" (peut légitimement être positif ou négatif).

Décision 144 (14/10/2026) : `resultat_technique` retiré du référentiel
(était 22 KPIs, Décision 137 l'avait gardé avec un flag `toujours_null`
après avoir chiffré le retrait à 28 fichiers pour un bénéfice jugé
cosmétique). Renversé : l'audit du 14/10 a confirmé qu'aucun gabarit QRT
EIOPA ne porte ce résultat — il existe bien en texte libre dans certains
rapports narratifs complets (ex. Generali Vie, Chapitre A.2), mais
l'obtenir pour les 41 sociétés demanderait de retrouver et dépouiller
~40 rapports complets supplémentaires (le pipeline ne lit que les
annexes QRT) pour un seul KPI — décision explicite de l'utilisateur de
ne pas poursuivre cette piste et de retirer le KPI plutôt que de le
garder NULL à 100%. La base passe donc à 21 KPIs.
"""

KPI_DEFINITIONS = [
    # --- Solvabilité (2) ---
    {
        "kpi_name": "ratio_scr",
        "label": "Ratio de couverture du SCR",
        "category": "solvabilité",
        "unit": "pct",
        "qrt_source": "S.23.01",
        "sfcr_chapter": "E.1",
        "sign": "positive",
    },
    {
        "kpi_name": "ratio_mcr",
        "label": "Ratio de couverture du MCR",
        "category": "solvabilité",
        "unit": "pct",
        "qrt_source": "S.23.01",
        "sfcr_chapter": "E.1",
        "sign": "positive",
    },

    # --- Fonds propres (5) ---
    {
        "kpi_name": "fonds_propres_eligibles",
        "label": "Total des fonds propres éligibles",
        "category": "fonds_propres",
        "unit": "M€",
        "qrt_source": "S.23.01",
        "sfcr_chapter": "E.1",
        "sign": "positive",
    },
    {
        "kpi_name": "fonds_propres_t1_nr",
        "label": "Fonds propres de base Tier 1 non repris",
        "category": "fonds_propres",
        "unit": "M€",
        "qrt_source": "S.23.01",
        "sfcr_chapter": "E.1",
        "sign": "positive",
    },
    {
        "kpi_name": "fonds_propres_t1_r",
        "label": "Fonds propres de base Tier 1 repris",
        "category": "fonds_propres",
        "unit": "M€",
        "qrt_source": "S.23.01",
        "sfcr_chapter": "E.1",
        "sign": "positive",
    },
    {
        "kpi_name": "fonds_propres_t2",
        "label": "Fonds propres de base Tier 2",
        "category": "fonds_propres",
        "unit": "M€",
        "qrt_source": "S.23.01",
        "sfcr_chapter": "E.1",
        "sign": "positive",
    },
    {
        "kpi_name": "fonds_propres_t3",
        "label": "Fonds propres de base Tier 3",
        "category": "fonds_propres",
        "unit": "M€",
        "qrt_source": "S.23.01",
        "sfcr_chapter": "E.1",
        "sign": "positive",
    },

    # --- SCR (8) ---
    {
        "kpi_name": "scr_total",
        "label": "Capital de solvabilité requis (SCR total)",
        "category": "scr",
        "unit": "M€",
        "qrt_source": "S.25.01",
        "sfcr_chapter": "E.2",
        "sign": "positive",
    },
    {
        "kpi_name": "scr_marche",
        "label": "SCR — Risque de marché",
        "category": "scr",
        "unit": "M€",
        "qrt_source": "S.25.01",
        "sfcr_chapter": "E.2",
        "sign": "positive",
    },
    {
        "kpi_name": "scr_souscription_vie",
        "label": "SCR — Risque de souscription vie",
        "category": "scr",
        "unit": "M€",
        "qrt_source": "S.25.01",
        "sfcr_chapter": "E.2",
        "sign": "positive",
    },
    {
        "kpi_name": "scr_souscription_nonvie",
        "label": "SCR — Risque de souscription non-vie",
        "category": "scr",
        "unit": "M€",
        "qrt_source": "S.25.01",
        "sfcr_chapter": "E.2",
        "sign": "positive",
    },
    {
        "kpi_name": "scr_souscription_sante",
        "label": "SCR — Risque de souscription santé",
        "category": "scr",
        "unit": "M€",
        "qrt_source": "S.25.01",
        "sfcr_chapter": "E.2",
        "sign": "positive",
    },
    {
        "kpi_name": "scr_contrepartie",
        "label": "SCR — Risque de contrepartie (défaut)",
        "category": "scr",
        "unit": "M€",
        "qrt_source": "S.25.01",
        "sfcr_chapter": "E.2",
        "sign": "positive",
    },
    {
        "kpi_name": "scr_operationnel",
        "label": "SCR — Risque opérationnel",
        "category": "scr",
        "unit": "M€",
        "qrt_source": "S.25.01",
        "sfcr_chapter": "E.2",
        "sign": "positive",
    },
    {
        "kpi_name": "scr_diversification",
        "label": "SCR — Effet de diversification",
        "category": "scr",
        "unit": "M€",
        "qrt_source": "S.25.01",
        "sfcr_chapter": "E.2",
        "sign": "negative",
    },

    # --- Provisions (3) ---
    {
        "kpi_name": "best_estimate",
        "label": "Best estimate (provisions techniques)",
        "category": "provisions",
        "unit": "M€",
        "qrt_source": "S.02.01",
        "sfcr_chapter": "D.2",
        "sign": "positive",
    },
    {
        "kpi_name": "marge_risque",
        "label": "Marge de risque",
        "category": "provisions",
        "unit": "M€",
        "qrt_source": "S.02.01",
        "sfcr_chapter": "D.2",
        "sign": "positive",
    },
    {
        "kpi_name": "provisions_techniques",
        "label": "Provisions techniques totales",
        "category": "provisions",
        "unit": "M€",
        "qrt_source": "S.02.01",
        "sfcr_chapter": "D.2",
        "sign": "positive",
    },

    # --- MCR (1) ---
    {
        "kpi_name": "mcr",
        "label": "Capital minimum requis (MCR)",
        "category": "mcr",
        "unit": "M€",
        "qrt_source": "S.28.01",
        "sfcr_chapter": "E.2",
        "sign": "positive",
    },

    # --- Activité (3) ---
    {
        "kpi_name": "primes_acquises_brutes",
        "label": "Primes acquises brutes",
        "category": "activité",
        "unit": "M€",
        "qrt_source": "S.05.01",
        "sfcr_chapter": "A.2",
        "sign": "positive",
    },
    {
        "kpi_name": "charge_sinistres",
        "label": "Charge des sinistres",
        "category": "activité",
        "unit": "M€",
        "qrt_source": "S.05.01",
        "sfcr_chapter": "A.2",
        "sign": "positive",
    },
]


# Décision 158 — 6 indicateurs calculés promus en KPIs officiels de la base
# (table `kpis` + composants dans `kpi_composants` + règle dans
# `kpi_formules`), peuplés par peupler_kpis_officiels_indicateurs.py.
# Liste SÉPARÉE de KPI_DEFINITIONS : ces KPIs ne sont pas extraits des PDF
# mais calculés à partir de KPIs et de lignes déjà en base ; les contrôles
# d'extraction de validate_kpis.py (signe, complétude des 21) ne les
# concernent pas. `indicateur` = clé d'origine dans indicateursParSociete
# (comparabilite.py), dont la valeur doit être identique.
# `classement` : "higher"/"lower" (plus haut / plus bas = mieux), "neutre"
# (position affichée sans « mieux / moins bien ») ou "aucun" (jamais classé).
# Descriptions en français simple : aucun code QRT, aucun nom de société.
CATEGORIE_INDICATEURS = "indicateurs_comparables"
LIBELLE_CATEGORIE_INDICATEURS = "Indicateurs comparables"

KPI_INDICATEURS_OFFICIELS = [
    {
        "kpi_name": "ratio_scr_sans_mesures_lt",
        "label": "Ratio SCR sans mesures de long terme",
        "unit": "pct",
        "indicateur": "ratio_scr_sans_mesures_lt_pct",
        "classement": "higher",
        "description": "Ratio de couverture du SCR recalculé sans la correction pour volatilité ni les mesures "
                       "transitoires. Toutes les sociétés n'appliquent pas ces mécanismes, qui améliorent le "
                       "ratio publié : sans eux, les ratios se comparent sur une base homogène.",
    },
    {
        "kpi_name": "impact_va",
        "label": "Impact de la correction pour volatilité",
        "unit": "pts",
        "indicateur": "impact_va_pts",
        "classement": "neutre",
        "description": "Effet de la correction pour volatilité sur le ratio SCR, en points. Négatif : sans "
                       "cette correction, le ratio serait plus bas. Mesuré après retrait des mesures "
                       "transitoires.",
    },
    {
        "kpi_name": "impact_transitoires",
        "label": "Impact des mesures transitoires",
        "unit": "pts",
        "indicateur": "impact_transitoires_pts",
        "classement": "neutre",
        "description": "Effet des mesures transitoires sur le ratio SCR, en points. Négatif : sans elles, le "
                       "ratio serait plus bas. Ces mesures s'éteignent progressivement jusqu'en 2032 ; seules "
                       "quelques sociétés les appliquent.",
    },
    {
        "kpi_name": "marge_risque_sur_be",
        "label": "Marge de risque / best estimate",
        "unit": "pct",
        "indicateur": "marge_risque_sur_be_pct",
        "classement": "neutre",
        "description": "Marge de risque rapportée au best estimate des provisions techniques. Elle dépend "
                       "surtout du métier (faible en vie, élevée en santé) : à comparer entre sociétés de même "
                       "activité.",
    },
    {
        "kpi_name": "sp_nonvie",
        "label": "Ratio sinistres / primes non-vie",
        "unit": "pct",
        "indicateur": "sp_nonvie_pct",
        "classement": "lower",
        "description": "Charge de sinistres rapportée aux primes acquises, sur les seules activités non-vie "
                       "(santé non-vie comprise). Calculé quand ces activités pèsent au moins 10 % des primes "
                       "et 10 M€.",
    },
    {
        "kpi_name": "mcr_en_pct_scr",
        "label": "MCR en % du SCR",
        "unit": "pct",
        "indicateur": None,  # remplace la catégorie textuelle position_mcr (conservée dans les indicateurs)
        "classement": "aucun",
        "description": "Minimum de capital requis rapporté au SCR. La réglementation l'encadre entre 25 % et "
                       "45 % du SCR, avec un plancher absolu en euros : un MCR collé à une borne rend le ratio "
                       "MCR peu informatif. Ce n'est pas un indicateur de solidité.",
    },
]


if __name__ == "__main__":
    print(f"{len(KPI_DEFINITIONS)} KPIs définis")
    from collections import Counter
    par_categorie = Counter(k["category"] for k in KPI_DEFINITIONS)
    for cat, n in par_categorie.items():
        print(f"  {cat:15} : {n}")
    noms = [k["kpi_name"] for k in KPI_DEFINITIONS]
    assert len(noms) == len(set(noms)), "kpi_name dupliqué détecté"
    print("  kpi_name tous uniques : OK")
    noms_calcules = [k["kpi_name"] for k in KPI_INDICATEURS_OFFICIELS]
    assert not set(noms) & set(noms_calcules), "KPI calculé homonyme d'un KPI extrait"
    print(f"{len(KPI_INDICATEURS_OFFICIELS)} KPIs calculés (Décision 158) : {', '.join(noms_calcules)}")
