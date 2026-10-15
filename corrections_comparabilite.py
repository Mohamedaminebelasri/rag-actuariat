# -*- coding: utf-8 -*-
"""corrections_comparabilite.py — Corrections issues du diagnostic de
comparabilité du 15/10/2026 (RAPPORT_comparabilite_KPIs.md), Décisions
150, 152 et 154. Idempotent : valeurs explicites, vérifiées sur les PDF,
réécrites à chaque exécution.

Ordre de rejeu après toute ré-extraction :
    extract_kpis_*.py / aema_entites.py / ag2r_entites.py
    -> populate_company_metadata.py
    -> corrections_comparabilite.py
    -> peupler_impact_mesures_lt.py
    -> validate_kpis.py --all
    -> export_kpis_for_frontend.py

1. Modèles internes : un JEU SCR COHÉRENT par société, tiré d'une seule
   base (jamais des lignes « diversifiées » mélangées à des lignes non
   diversifiées), toutes les valeurs non nulles marquées `avertissement`.
   Convention de stockage (identique à la formule standard) :
   SCR = Σ modules + scr_diversification + scr_operationnel + ajustements.
2. Groupes : `mcr` / `ratio_mcr` sont le « SCR minimal consolidé du
   groupe » (S.23.01.22 R0610 / R0650), marqués `avertissement`.
3. Zéros vrais dont la page source manquait (CNP, MACSF prévoyance).
4. Valeurs imprimées restées NULL (Covéa, MAIF, SGAM AG2R).
5. AXA France IARD : primes et sinistres S.05.01 comptés deux fois.

    python corrections_comparabilite.py
"""
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(__file__).parent / "kpis.db"
YEAR = 2025
MODULES = ("scr_marche", "scr_contrepartie", "scr_souscription_vie", "scr_souscription_sante",
           "scr_souscription_nonvie", "scr_diversification", "scr_operationnel")

# --------------------------------------------------------------------------
# 1. Jeux SCR cohérents des sociétés en modèle interne (montants en M€).
#    None = laissé NULL (inclus dans un autre poste, cf. note).
# --------------------------------------------------------------------------
_K = 1000.0
MODELES_INTERNES = {
    "AXA France Vie": {
        "page": 10, "source_pdf": None,  # annexe QRT par défaut
        "valeurs": {
            "scr_marche": 3_168_161.75 / _K,          # R0080 Market & Credit risk - diversified
            "scr_contrepartie": 628_286.57 / _K,      # R0200 Credit event risk not covered - diversified
            "scr_souscription_vie": 2_969_159.36 / _K,  # R0410 Life & Health underwriting - diversified
            "scr_souscription_sante": None,           # inclus dans R0410
            "scr_souscription_nonvie": 0.0,           # R0320 = 0,00
            "scr_operationnel": 431_976.44 / _K,      # R0490 Operational risk - diversified
            "scr_diversification": (5_469_627.16 - 7_197_584.12) / _K,  # R0030 - Σ lignes diversifiées
        },
        "base": "S.25.05.21 (annexe QRT p.10), lignes « - diversified » (diversification intra-catégorie "
                "déjà appliquée) ; scr_diversification = diversification ENTRE catégories = R0030 − somme "
                "des lignes diversifiées (−1 728 M€, identique au tableau E.2.3 du rapport narratif p.100). "
                "scr_souscription_vie = vie ET santé (R0410, non séparables).",
    },
    "AXA France IARD": {
        "page": 9, "source_pdf": None,
        "valeurs": {
            "scr_marche": 1_306_938.49 / _K,          # R0080
            "scr_contrepartie": 282_324.51 / _K,      # R0200
            "scr_souscription_vie": 96_948.65 / _K,   # R0410 (vie et santé)
            "scr_souscription_sante": None,
            "scr_souscription_nonvie": 1_584_787.06 / _K,  # R0320 Non-life underwriting - diversified
            "scr_operationnel": 262_915.65 / _K,      # R0490
            "scr_diversification": (2_621_462.87 - 3_533_914.36) / _K,  # R0030 - Σ diversifiées
        },
        "base": "S.25.05.21 (annexe QRT p.9), lignes « - diversified » ; scr_diversification = R0030 − "
                "somme des lignes diversifiées (−912 M€, identique au tableau E.2.3 du rapport narratif "
                "p.89). scr_souscription_vie = vie ET santé (R0410).",
    },
    "Generali Vie": {
        "page": 79, "source_pdf": "RSSF_Generali_Vie_2025.pdf",
        "valeurs": {
            "scr_marche": 1509.0, "scr_contrepartie": 1146.0,
            "scr_souscription_vie": 1045.0,           # « Souscription » (vie et santé, non séparables)
            "scr_souscription_sante": None,
            "scr_souscription_nonvie": 0.0,
            "scr_operationnel": 424.0,
            "scr_diversification": -1327.0,           # « Diversification inter-risques »
        },
        "base": "Graphique E.2.1 du rapport narratif (p.79), avant diversification inter-risques et avant "
                "impact fiscal ; les cross-terms (+88), Model Adjustments (+735) et l'impact fiscal (−552) "
                "restent dans l'écart avec le SCR. scr_souscription_vie = « Souscription » (vie et santé).",
    },
    "Generali IARD": {
        "page": 72, "source_pdf": "RSSF_Generali_Iard_2025.pdf",
        "valeurs": {
            "scr_marche": 385.0, "scr_contrepartie": 250.0, "scr_souscription_vie": 11.0,
            "scr_souscription_sante": None,           # santé non-vie incluse dans « Souscription Non-Vie »
            "scr_souscription_nonvie": 702.0,
            "scr_operationnel": 174.0,
            "scr_diversification": -375.0,
        },
        "base": "Graphique E.2.1 du rapport narratif (p.72, lu sur rendu image), avant diversification "
                "inter-risques et avant impact fiscal ; cross-terms (+16), Model Adjustments (+190) et impact "
                "fiscal (−67) restent dans l'écart avec le SCR.",
    },
    "Allianz Vie": {
        "page": 69, "source_pdf": None,
        "valeurs": {
            "scr_marche": 1_653_208 / _K,
            "scr_contrepartie": 270_016 / _K,
            "scr_souscription_vie": (328_565 + 681_608) / _K,  # « souscription » + « commercial »
            "scr_souscription_sante": None,
            "scr_souscription_nonvie": 0.0,
            "scr_operationnel": 119_644 / _K,
            "scr_diversification": -912_286 / _K,
        },
        "base": "Tableau 25 du rapport (p.69), catégories du modèle interne Allianz (diversification "
                "intra-catégorie incluse) ; scr_souscription_vie = « Risque de souscription » + « Risque "
                "commercial » (rachats/frais, rangés en souscription vie dans la formule standard) ; "
                "IM Capital Buffer (+109), fonds cantonnés (+20) et impôts différés (−51) restent dans "
                "l'écart avec le SCR.",
    },
}

NOTE_MI = ("Valeur de modèle interne ({societe}) : non comparable au même KPI des sociétés en formule "
           "standard (calibrage, taxonomie des risques et diversification propres au modèle). Base : {base}")

# Groupama : modèle interne PARTIEL (souscription non-vie modélisée). Jeu
# cohérent = schéma E.2.1 p.74 (modules nets de la diversification entre
# sous-modules) ; scr_diversification = SCR de base − Σ modules.
GROUPAMA = {
    "page": 74,
    "valeurs": {
        "scr_marche": 4_675_236 / _K, "scr_souscription_sante": 1_271_055 / _K,
        "scr_contrepartie": 785_108 / _K, "scr_souscription_vie": 1_455_724 / _K,
        "scr_souscription_nonvie": 2_474_794 / _K, "scr_operationnel": 677_423 / _K,
        "scr_diversification": (9_412_239 - (4_675_236 + 1_271_055 + 785_108 + 1_455_724 + 2_474_794)) / _K,
    },
    "avertir": ("scr_souscription_nonvie", "scr_diversification"),
    "note": ("Groupama utilise un modèle interne PARTIEL (souscription non-vie modélisée, cf. S.25.05.22 p.87 "
             "« montant modélisé ») : cette valeur dépend du modèle interne et n'est pas directement "
             "comparable à la formule standard. Base : schéma E.2.1 p.74 ; scr_diversification = SCR de "
             "base (9 412 M€) − somme des modules (l'ancienne valeur −4 612 M€ venait du S.25.05.22, "
             "calculée sur des composantes non diversifiées, incohérente avec ces modules)."),
}

GROUPES_MCR = ("Aema Groupe", "Covéa", "Crédit Agricole Assurances", "Groupama", "SGAM AG2R LA MONDIALE")
NOTE_MCR = ("Pour un groupe, ce chiffre est le « SCR minimal consolidé du groupe » (S.23.01.22 R0610, somme "
            "des MCR des entités) — pas un MCR au sens d'une société solo ; non comparable au MCR des "
            "sociétés solo.")
NOTE_RATIO_MCR = ("Pour un groupe, ratio de couverture du « SCR minimal consolidé du groupe » (S.23.01.22 "
                  "R0650) — pas un ratio MCR au sens d'une société solo ; non comparable.")

# 3. Zéros vrais, page vérifiée (« 0 » ou « - » imprimé).
ZEROS_TRACES = {
    ("CNP Assurances", "scr_souscription_nonvie"): (97, "S.25.01.21/R0050 imprimé « 0 » (p.97)"),
    ("MACSF prévoyance", "scr_souscription_sante"): (62, "S.25.01.21/R0040 imprimé « - » (p.62)"),
    ("MACSF prévoyance", "scr_souscription_nonvie"): (62, "S.25.01.21/R0050 imprimé « - » (p.62)"),
    ("MACSF prévoyance", "fonds_propres_t1_r"): (61, "S.23.01.01/R0540/C0030 imprimé « - » (p.61)"),
    ("MACSF prévoyance", "fonds_propres_t2"): (61, "S.23.01.01/R0540/C0040 imprimé « - » (p.61)"),
    ("MACSF prévoyance", "fonds_propres_t3"): (61, "S.23.01.01/R0540/C0050 imprimé « - » (p.61)"),
}


# 4. Valeurs restées NULL alors qu'elles sont imprimées (parseur : libellés
#    français / mapping groupe incomplet). Lues sur la page, recoupées avec
#    un total déjà en base. (valeur M€, page, chapitre)
VALEURS_RECUPEREES = {
    ("Covéa", "fonds_propres_t1_nr"): (32_616.281, 93, "S.23.01.22 « fonds propres éligibles pour couvrir le SCR du groupe », colonne Niveau 1 non restreint ; somme des 4 tiers = total 33 251 714 k€"),
    ("Covéa", "fonds_propres_t1_r"): (134.394, 93, "S.23.01.22, même ligne, Niveau 1 restreint"),
    ("Covéa", "fonds_propres_t2"): (384.326, 93, "S.23.01.22, même ligne, Niveau 2"),
    ("Covéa", "fonds_propres_t3"): (116.712, 93, "S.23.01.22, même ligne, Niveau 3"),
    ("MAIF", "fonds_propres_t1_r"): (0.0, 122, "S.23.01.01/R0540, Niveau 1 restreint imprimé « - »"),
    ("MAIF", "fonds_propres_t2"): (9.725, 122, "S.23.01.01/R0540, Niveau 2 = fonds propres auxiliaires (rappel de cotisations) ; 5 319 982 + 9 725 = total 5 329 707 k€"),
    ("MAIF", "fonds_propres_t3"): (0.0, 122, "S.23.01.01/R0540, Niveau 3 imprimé « - »"),
    ("SGAM AG2R LA MONDIALE", "fonds_propres_t3"): (0.0, 131, "S.23.01.22/R0660, Niveau 3 vide ; T1nr + T1r + T2 = total 10 005 273 k€ exactement"),
    ("SGAM AG2R LA MONDIALE", "scr_souscription_nonvie"): (0.139, 133, "S.25.01.22/R0050 = 139 k€"),
    ("SGAM AG2R LA MONDIALE", "scr_diversification"): (-1_539.439, 133, "S.25.01.22/R0060 ; Σ modules + R0060 = R0100 (6 743 149 k€)"),
}


def appliquer_valeurs_recuperees(conn):
    for (societe, kpi), (valeur, page, chapitre) in VALEURS_RECUPEREES.items():
        cid = _cid(conn, societe)
        n = conn.execute(
            """UPDATE kpis SET value=?, source_page=?, source_chapter=?, raw_value=?, raw_unit='K€'
               WHERE company_id=? AND year=? AND kpi_name=?""",
            (valeur, page, chapitre + " (Décision 152)", valeur * 1000, cid, YEAR, kpi),
        ).rowcount
        if n != 1:
            raise SystemExit(f"Ligne KPI introuvable : {societe}/{kpi}")
    print(f"  {len(VALEURS_RECUPEREES)} valeurs récupérées")


# 5. AXA France IARD, S.05.01.02 p.3 : lignes comptées deux fois par
#    l'extraction par position (Décision 154). Mêmes valeurs que
#    PRIMES_COMPOSANTS / SINISTRES_COMPOSANTS d'extract_kpis_afi.py (K€).
AFI_S0501 = {
    "primes_acquises_brutes": [
        ("R0210", "Primes acquises brutes — directe (non-vie, Total)", 8_921_270.19),
        ("R0220", "Primes acquises brutes — réassurance proportionnelle acceptée (non-vie, Total)", 715_080.34),
        ("R0230", "Primes acquises brutes — réassurance non proportionnelle acceptée (non-vie, Total)", 488.66),
        ("R1510", "Primes acquises brutes (vie, Total)", 0.0),
    ],
    "charge_sinistres": [
        ("R0310", "Charge de sinistres — directe (non-vie, Total)", 5_577_862.90),
        ("R0320", "Charge de sinistres — réassurance proportionnelle acceptée (non-vie, Total)", 346_611.98),
        ("R0330", "Charge de sinistres — réassurance non proportionnelle acceptée (non-vie, Total)", -12_038.51),
        ("R1610", "Charge de sinistres (vie, Total)", 0.0),
    ],
}


def appliquer_afi_s0501(conn):
    cid = _cid(conn, "AXA France IARD")
    for kpi, composants in AFI_S0501.items():
        total_k = sum(v for _, _, v in composants)
        conn.execute(
            """UPDATE kpis SET value=?, raw_value=?, raw_unit='K€', source_page=3,
                   source_chapter='S.05.01.02 p.3, colonne Total lue manuellement — Décision 154'
               WHERE company_id=? AND year=? AND kpi_name=?""",
            (total_k / 1000, total_k, cid, YEAR, kpi))
        conn.execute("DELETE FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name=?", (cid, YEAR, kpi))
        conn.executemany(
            """INSERT INTO kpi_composants (company_id, year, kpi_name, composant_index, composant_label,
                   composant_code_qrt, composant_valeur, composant_unite, composant_page, operation)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'M€', 3, '+')""",
            [(cid, YEAR, kpi, i, l, c, v / 1000) for i, (c, l, v) in enumerate(composants, start=1)])
        print(f"  AXA France IARD {kpi} = {total_k / 1000:,.3f} M€")


def _cid(conn, nom):
    row = conn.execute("SELECT id FROM companies WHERE name=?", (nom,)).fetchone()
    if row is None:
        raise SystemExit(f"Société absente : {nom}")
    return row[0]


def _maj(conn, cid, kpi, valeur, page, chapitre, source_pdf, avert, note):
    n = conn.execute(
        """UPDATE kpis SET value=?, source_page=?, source_chapter=?, source_pdf=?, avertissement=?,
               note_avertissement=?, raw_value=?, raw_unit=CASE WHEN ? IS NULL THEN NULL ELSE 'M€' END
           WHERE company_id=? AND year=? AND kpi_name=?""",
        (valeur, page if valeur is not None else None, chapitre, source_pdf, avert, note,
         valeur, valeur, cid, YEAR, kpi),
    ).rowcount
    if n != 1:
        raise SystemExit(f"Ligne KPI introuvable : company_id={cid} {kpi}")


def appliquer_modeles_internes(conn):
    for societe, spec in MODELES_INTERNES.items():
        cid = _cid(conn, societe)
        note = NOTE_MI.format(societe=societe, base=spec["base"])
        for kpi in MODULES:
            v = spec["valeurs"][kpi]
            if v == 0:
                # Vrai zéro déjà lu sur le QRT (page/PDF d'origine conservés) :
                # un 0 reste comparable, pas d'avertissement.
                conn.execute("""UPDATE kpis SET value=0, avertissement=0, note_avertissement=NULL
                                WHERE company_id=? AND year=? AND kpi_name=?""", (cid, YEAR, kpi))
                continue
            avert = 1 if v is not None else 0
            chapitre = (f"Jeu SCR cohérent modèle interne (Décision 150) — {spec['base']}" if v is not None
                        else f"NULL : inclus dans un autre poste — {spec['base']}")
            _maj(conn, cid, kpi, v, spec["page"], chapitre, spec["source_pdf"], avert, note if avert else None)
        somme = sum(spec["valeurs"][k] or 0 for k in MODULES)
        scr = conn.execute("SELECT value FROM kpis WHERE company_id=? AND year=? AND kpi_name='scr_total'",
                           (cid, YEAR)).fetchone()[0]
        print(f"  {societe:22} Σ modules+div+op = {somme:9.1f}  SCR = {scr:9.1f}  écart = {scr - somme:+8.1f}")

    cid = _cid(conn, "Groupama")
    for kpi in MODULES:
        v = GROUPAMA["valeurs"][kpi]
        avert = 1 if kpi in GROUPAMA["avertir"] else 0
        _maj(conn, cid, kpi, v, GROUPAMA["page"],
             "Schéma E.2.1 p.74 (modules nets de la diversification entre sous-modules) — Décision 150",
             None, avert, GROUPAMA["note"] if avert else None)
    somme = sum(GROUPAMA["valeurs"].values())
    scr = conn.execute("SELECT value FROM kpis WHERE company_id=? AND year=? AND kpi_name='scr_total'",
                       (cid, YEAR)).fetchone()[0]
    print(f"  {'Groupama':22} Σ modules+div+op = {somme:9.1f}  SCR = {scr:9.1f}  écart = {scr - somme:+8.1f}")


def appliquer_mcr_groupes(conn):
    for societe in GROUPES_MCR:
        cid = _cid(conn, societe)
        for kpi, note in (("mcr", NOTE_MCR), ("ratio_mcr", NOTE_RATIO_MCR)):
            conn.execute("UPDATE kpis SET avertissement=1, note_avertissement=? WHERE company_id=? AND year=? AND kpi_name=?",
                         (note, cid, YEAR, kpi))
    print(f"  avertissement MCR/ratio MCR posé sur {len(GROUPES_MCR)} groupes")


def appliquer_zeros(conn):
    for (societe, kpi), (page, chapitre) in ZEROS_TRACES.items():
        cid = _cid(conn, societe)
        row = conn.execute("SELECT value FROM kpis WHERE company_id=? AND year=? AND kpi_name=?", (cid, YEAR, kpi)).fetchone()
        if row is None or row[0] != 0:
            raise SystemExit(f"{societe}/{kpi} n'est plus à 0 ({row}) — à revoir")
        conn.execute("UPDATE kpis SET source_page=?, source_chapter=? WHERE company_id=? AND year=? AND kpi_name=?",
                     (page, chapitre, cid, YEAR, kpi))
    print(f"  {len(ZEROS_TRACES)} zéros rendus traçables (page source vérifiée)")


def main():
    conn = sqlite3.connect(DB_PATH)
    print("=== 1. Jeux SCR cohérents (modèles internes) ===")
    appliquer_modeles_internes(conn)
    print("=== 2. MCR des groupes ===")
    appliquer_mcr_groupes(conn)
    print("=== 3. Zéros traçables ===")
    appliquer_zeros(conn)
    print("=== 4. Valeurs imprimées mais restées NULL ===")
    appliquer_valeurs_recuperees(conn)
    print("=== 5. AXA France IARD, primes et sinistres (S.05.01) ===")
    appliquer_afi_s0501(conn)
    conn.commit()
    conn.close()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
