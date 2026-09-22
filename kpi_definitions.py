"""kpi_definitions.py — Référence unique des 22 KPIs actuariels à extraire
(Phase 3, Décision 050), indépendante du RAG/Qdrant.

KPI_DEFINITIONS : liste de 22 dicts, 6 catégories (solvabilité, fonds
propres, scr, provisions, mcr, activité). Chaque KPI porte sa source QRT
et son chapitre SFCR narratif correspondant, pour guider l'extraction
(Phase 3, étapes suivantes) — ce fichier ne fait AUCUNE extraction
lui-même, c'est une table de référence statique.

`sign` : "positive" (montant/ratio toujours positif), "negative" (ex.
scr_diversification, un bénéfice de diversification qui SOUSTRAIT du SCR
total), ou "any" (peut légitimement être positif ou négatif — ex.
resultat_technique, un solde qui peut être une perte).
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
    {
        "kpi_name": "resultat_technique",
        "label": "Résultat technique",
        "category": "activité",
        "unit": "M€",
        "qrt_source": "S.05.01",
        "sfcr_chapter": "A.2",
        "sign": "any",
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
