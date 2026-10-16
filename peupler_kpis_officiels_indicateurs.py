# -*- coding: utf-8 -*-
"""peupler_kpis_officiels_indicateurs.py — 6 indicateurs calculés promus en
KPIs officiels de kpis.db (Décision 158).

Jusqu'ici, ces ratios n'existaient que dans `indicateursParSociete`
(calculés à la volée par comparabilite.py au moment de l'export). Ils
deviennent de vrais KPIs, avec le même statut que provisions_techniques ou
charge_sinistres : une ligne dans `kpis`, leurs composants dans
`kpi_composants` (valeur, page source, lien vers le KPI officiel quand le
composant en est un) et leur règle de calcul dans `kpi_formules`.

    ratio_scr_sans_mesures_lt  ratio SCR sans VA ni transitoires (%)
    impact_va                  effet de la correction pour volatilité (pts)
    impact_transitoires        effet des mesures transitoires (pts)
    marge_risque_sur_be        marge de risque ÷ best estimate × 100 (%)
    sp_nonvie                  sinistres ÷ primes, lignes non-vie (%)
    mcr_en_pct_scr             MCR ÷ SCR × 100 (%), solo seulement

Règles (Décision 158) :
- Rien de deviné : chaque composant est un KPI, une ligne de
  `kpi_composants` ou une valeur de `impact_mesures_lt` déjà en base.
- La valeur stockée est EXACTEMENT celle de l'indicateur d'origine
  (comparabilite.indicateurs, mêmes formules, mêmes signes, mêmes
  arrondis) ; le recalcul depuis les composants doit la retrouver à 0,05
  près. Un KPI sans donnée n'est pas créé (aucune ligne, jamais de NULL).
- `validated` = 1 seulement si TOUS les composants sont valides ET si le
  recalcul retrouve la valeur. Un avertissement porté par un composant est
  hérité ; un recalcul en écart pose un avertissement. Un composant
  simplement « non recoupé » rend le KPI non vérifié, sans avertissement
  de comparabilité. Lignes de primes / sinistres de sp_nonvie : valides
  si validate_kpis.py les a relues dans le PDF (contrôle 12, Décision
  159) — à lancer AVANT ce script, avec le Python du .venv.
- Société sans VA ni transitoire : ratio sans mesures = ratio publié,
  impact VA = 0, avec une note. `impact_transitoires` n'existe que pour
  les sociétés qui appliquent une mesure transitoire (comme l'indicateur).

Modèle de données (additif, rétro-compatible : les KPIs « somme » ne
changent pas) :
- `kpi_formules` (nouvelle table) : type 'ratio' (Σ num ÷ Σ den × facteur)
  ou 'difference' (Σ « + » − Σ « - »), texte de la règle, facteur, note.
- `kpi_composants`, 4 colonnes ajoutées (NULL pour les lignes existantes) :
  kpi_code (le composant est ce KPI officiel de la société),
  composant_detail (calcul d'un ratio intermédiaire),
  composant_source_pdf (PDF du composant ; NULL = PDF par défaut de la
  société), composant_valide (0/1).
- `operation` : '+' / '-' (comme avant) ou 'num' / 'den' (ratio).

Idempotent : supprime puis réinsère uniquement les lignes de ces 6
kpi_name ; aucune autre ligne n'est modifiée. Ordre de rejeu complet :
    ... -> peupler_impact_mesures_lt.py -> validate_kpis.py --all
        -> peupler_kpis_officiels_indicateurs.py -> export_kpis_for_frontend.py

    python peupler_kpis_officiels_indicateurs.py
"""
import re
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path

import comparabilite
from kpi_definitions import CATEGORIE_INDICATEURS, KPI_INDICATEURS_OFFICIELS

DB_PATH = Path(__file__).parent / "kpis.db"
YEAR = 2025
TOLERANCE = 0.05
NOMS = tuple(d["kpi_name"] for d in KPI_INDICATEURS_OFFICIELS)
DEFS = {d["kpi_name"]: d for d in KPI_INDICATEURS_OFFICIELS}

# Ratio sans VA publié seulement dans le rapport narratif (pas de S.22.01 dans
# l'annexe QRT). Vérifié : section B.3.4, RSSF_Generali_Vie_2025.pdf p.36 et
# RSSF_Generali_Iard_2025.pdf p.32 (cf. peupler_impact_mesures_lt.py).
PDF_RATIO_PUBLIE = {"Generali Vie": "RSSF_Generali_Vie_2025.pdf", "Generali IARD": "RSSF_Generali_Iard_2025.pdf"}
# MAIF : impacts lus dans le texte, fonds propres p.105 (E.1), SCR p.106 (E.2).
PAGE_DELTA_SCR = {"MAIF": 106}
# Covéa best_estimate / marge_risque : page 85 écrite en base depuis la
# Décision 160 (corrections_comparabilite.PAGES_VERIFIEES), plus de repli ici.

NOTE_SANS_MESURE = ("N'applique ni correction pour volatilité ni mesure transitoire : le ratio sans mesures est "
                    "le ratio publié et l'impact est nul.")
NOTE_VA_SEULE = "N'applique pas de mesure transitoire : seule la correction pour volatilité est retirée."
NOTE_PAR_ETAPES = ("Approche par étapes : la mesure transitoire est retirée d'abord, puis la correction pour "
                   "volatilité.")
NOTE_POSITION_MCR = {
    "plancher_25": "Le MCR est au plancher de 25 % du SCR : le ratio MCR n'est alors qu'un multiple du ratio SCR.",
    "plafond_45": "Le MCR est au plafond de 45 % du SCR : le ratio MCR n'est alors qu'un multiple du ratio SCR.",
    "entre_25_45": "Le MCR est calculé par la formule réglementaire, entre le plancher (25 %) et le plafond (45 %) "
                   "du SCR.",
    "plancher_absolu": "Le MCR est fixé par le plancher absolu réglementaire (un montant minimum en euros) : il "
                       "dépasse 45 % du SCR et le ratio MCR n'est pas significatif.",
}


@dataclass
class Composant:
    label: str
    valeur: float
    unite: str
    page: int | None
    operation: str
    code: str | None = None
    kpi_code: str | None = None
    detail: str | None = None
    source_pdf: str | None = None
    valide: bool = False
    note_avertissement: str | None = None  # non NULL = avertissement hérité


@dataclass
class KpiCalcule:
    kpi_name: str
    valeur: float
    formule: dict
    composants: list
    page: int | None
    chapitre: str
    source_pdf: str | None = None
    valide: bool = False
    avertissement: bool = False
    note_avertissement: str | None = None
    recalcul: float | None = None


def fr(x, d=3):
    """Nombre au format français (espace des milliers, virgule décimale)."""
    s = f"{x:,.{d}f}".replace(",", " ").replace(".", ",")
    return s.replace("-", "−")


def recalculer(formule, composants):
    if formule["type"] == "ratio":
        num = sum(c.valeur for c in composants if c.operation == "num")
        den = sum(c.valeur for c in composants if c.operation == "den")
        return num / den * formule["facteur"]
    return sum(c.valeur if c.operation == "+" else -c.valeur for c in composants) * formule["facteur"]


def comp_kpi(kp, kpi, label, operation, valeur=None):
    """Composant = un KPI officiel de la société (lien kpi_code)."""
    k = kp[kpi]
    return Composant(label=label, valeur=k["value"] if valeur is None else valeur, unite=k["unit"],
                     page=k["source_page"], operation=operation, kpi_code=kpi, source_pdf=k["source_pdf"],
                     valide=bool(k["validated"]),
                     note_avertissement=k["note_avertissement"] if k["avertissement"] else None)


def finaliser(kc):
    kc.recalcul = recalculer(kc.formule, kc.composants)
    ok = abs(kc.recalcul - kc.valeur) <= TOLERANCE + 1e-9
    notes = []
    for c in kc.composants:
        if c.note_avertissement and c.note_avertissement not in notes:
            notes.append(c.note_avertissement)
    if not ok:
        notes.append(f"Le recalcul à partir des composants donne {fr(kc.recalcul, 2)}, différent de la valeur "
                     f"affichée : valeur à vérifier.")
    kc.valide = ok and all(c.valide for c in kc.composants)
    kc.avertissement = bool(notes)
    kc.note_avertissement = " ".join(notes) or None
    return kc


def kpis_mesures_lt(nom, kp, lt, ind):
    """ratio_scr_sans_mesures_lt, impact_va, impact_transitoires (S.22.01)."""
    out = []
    ratio_publie = kp.get("ratio_scr")
    if lt["ratio_scr_sans_va_publie"] is not None:
        # Modèle interne : ratio sans VA publié dans le texte du rapport.
        sans, page, pdf = lt["ratio_scr_sans_va_publie"], lt["source_page"], PDF_RATIO_PUBLIE[nom]
        chapitre = "Rapport narratif : ratio sans correction pour volatilité publié dans le texte"
        r = finaliser(KpiCalcule(
            "ratio_scr_sans_mesures_lt", ind["ratio_scr_sans_mesures_lt_pct"],
            {"type": "difference", "texte": "Ratio publié par la société sans correction pour volatilité",
             "facteur": 1, "note": "La correction pour volatilité est calculée par le modèle interne de la "
                                   "société, qui publie directement le ratio sans elle. Pas de mesure transitoire."},
            [Composant("Ratio SCR sans correction pour volatilité, publié dans le rapport", sans, "pct", page, "+",
                       detail="Valeur lue dans le texte du rapport (le tableau détaillé n'est pas publié)",
                       source_pdf=pdf, valide=False)],
            page, chapitre, pdf))
        out.append(r)
        if ind.get("impact_va_pts") is not None and ratio_publie:
            out.append(finaliser(KpiCalcule(
                "impact_va", ind["impact_va_pts"],
                {"type": "difference", "texte": "Ratio SCR sans mesures de long terme − Ratio SCR publié",
                 "facteur": 1, "note": "Pas de mesure transitoire : seul l'effet de la correction pour volatilité "
                                       "est mesuré, tel que publié par la société."},
                [Composant("Ratio SCR sans mesures de long terme", sans, "pct", page, "+",
                           kpi_code="ratio_scr_sans_mesures_lt", source_pdf=pdf, valide=r.valide),
                 comp_kpi(kp, "ratio_scr", "Ratio SCR publié", "-")],
                page, chapitre, pdf)))
        return out

    if lt["fp_avec"] is None:
        # Aucune mesure de long terme (pas de S.22.01 publié).
        k = kp["ratio_scr"]
        chapitre = "Ratio SCR publié : aucune mesure de long terme appliquée"
        r = finaliser(KpiCalcule(
            "ratio_scr_sans_mesures_lt", ind["ratio_scr_sans_mesures_lt_pct"],
            {"type": "difference", "texte": "Ratio SCR publié (aucune mesure de long terme à retirer)",
             "facteur": 1, "note": NOTE_SANS_MESURE},
            [comp_kpi(kp, "ratio_scr", "Ratio SCR publié", "+")],
            k["source_page"], chapitre, k["source_pdf"]))
        out.append(r)
        out.append(finaliser(KpiCalcule(
            "impact_va", ind["impact_va_pts"],
            {"type": "difference", "texte": "Ratio SCR sans mesures de long terme − Ratio SCR publié",
             "facteur": 1, "note": NOTE_SANS_MESURE},
            [Composant("Ratio SCR sans mesures de long terme", r.valeur, "pct", k["source_page"], "+",
                       kpi_code="ratio_scr_sans_mesures_lt", source_pdf=k["source_pdf"], valide=r.valide),
             comp_kpi(kp, "ratio_scr", "Ratio SCR publié", "-")],
            k["source_page"], chapitre, k["source_pdf"])))
        return out

    # Tableau S.22.01 (ou impacts publiés dans le texte, MAIF), montants en M€.
    fp, scr = lt["fp_avec"], lt["scr_avec"]
    dfv, dsv, dft, dst = lt["delta_fp_va"], lt["delta_scr_va"], lt["delta_fp_transitoires"], lt["delta_scr_transitoires"]
    transitoire = bool(lt["mesure_transitoire"])
    page = lt["source_page"]
    page_dsv = PAGE_DELTA_SCR.get(nom, page)
    tableau = "S.22.01" in (lt["source"] or "")
    chapitre = ("Impact des mesures de long terme (état S.22.01)" if tableau
                else "Impact des mesures de long terme (publié dans le texte du rapport)")
    # Contrôle : les montants publiés du tableau = KPI officiels (même extraction).
    recoupe = (abs(fp - kp["fonds_propres_eligibles"]["value"]) <= 0.01
               and abs(scr - kp["scr_total"]["value"]) <= 0.01)
    code = (lambda c: c) if tableau else (lambda c: None)

    num = [comp_kpi(kp, "fonds_propres_eligibles", "Fonds propres éligibles publiés", "num", valeur=fp)]
    den = [comp_kpi(kp, "scr_total", "SCR publié", "den", valeur=scr)]
    num[0].code, den[0].code = code("R0050 C0010"), code("R0090 C0010")
    if tableau:
        # Montants publiés lus dans le même tableau que les effets des mesures
        # (égaux aux KPI officiels, cf. `recoupe`) : page du tableau.
        num[0].page = den[0].page = page
    if transitoire:
        num.append(Composant("Effet du retrait de la mesure transitoire sur les fonds propres", dft, "M€", page,
                             "num", code=code("R0050 C0030+C0050"), valide=recoupe))
        den.append(Composant("Effet du retrait de la mesure transitoire sur le SCR", dst, "M€", page, "den",
                             code=code("R0090 C0030+C0050"), valide=recoupe))
    num.append(Composant("Effet du retrait de la correction pour volatilité sur les fonds propres", dfv, "M€", page,
                         "num", code=code("R0050 C0070"), valide=recoupe))
    den.append(Composant("Effet du retrait de la correction pour volatilité sur le SCR", dsv, "M€", page_dsv, "den",
                         code=code("R0090 C0070"), valide=recoupe))
    r = finaliser(KpiCalcule(
        "ratio_scr_sans_mesures_lt", ind["ratio_scr_sans_mesures_lt_pct"],
        {"type": "ratio", "texte": "(Fonds propres + effets du retrait des mesures) ÷ (SCR + effets du retrait "
                                   "des mesures) × 100",
         "facteur": 100, "note": NOTE_PAR_ETAPES if transitoire else NOTE_VA_SEULE},
        num + den, page, chapitre))
    out.append(r)

    # Ratios intermédiaires arrondis à 4 décimales (écart négligeable devant la
    # tolérance de 0,05 ; l'indicateur de référence garde le calcul exact).
    avec = round(fp / scr * 100, 4)
    sans_tr = round((fp + dft) / (scr + dst) * 100, 4)
    sans_tout = round((fp + dft + dfv) / (scr + dst + dsv) * 100, 4)
    detail_avec = f"{fr(fp)} ÷ {fr(scr)} × 100"
    detail_sans_tr = f"({fr(fp)} + {fr(dft)}) ÷ ({fr(scr)} + {fr(dst)}) × 100".replace("+ −", "− ")
    detail_sans_tout = (f"({fr(fp)} + {fr(dft)} + {fr(dfv)}) ÷ ({fr(scr)} + {fr(dst)} + {fr(dsv)}) × 100"
                        if transitoire else f"({fr(fp)} + {fr(dfv)}) ÷ ({fr(scr)} + {fr(dsv)}) × 100"
                        ).replace("+ −", "− ")
    avant_va = Composant(
        "Ratio SCR sans mesure transitoire, avec correction pour volatilité" if transitoire
        else "Ratio SCR avec correction pour volatilité (fonds propres ÷ SCR publiés)",
        sans_tr if transitoire else avec, "pct", page, "-",
        detail=detail_sans_tr if transitoire else detail_avec, valide=recoupe)
    out.append(finaliser(KpiCalcule(
        "impact_va", ind["impact_va_pts"],
        {"type": "difference", "texte": "Ratio SCR sans mesures de long terme − Ratio SCR avant retrait de la "
                                        "correction pour volatilité",
         "facteur": 1, "note": "Mesuré après retrait de la mesure transitoire (approche par étapes)." if transitoire
         else NOTE_VA_SEULE},
        [Composant("Ratio SCR sans mesures de long terme", sans_tout, "pct", page, "+",
                   kpi_code="ratio_scr_sans_mesures_lt", detail=detail_sans_tout, valide=r.valide), avant_va],
        page, chapitre)))
    if transitoire and ind.get("impact_transitoires_pts") is not None:
        out.append(finaliser(KpiCalcule(
            "impact_transitoires", ind["impact_transitoires_pts"],
            {"type": "difference", "texte": "Ratio SCR sans mesure transitoire − Ratio SCR publié", "facteur": 1,
             "note": "La mesure transitoire s'éteint progressivement jusqu'en 2032 : le ratio publié baissera "
                     "mécaniquement d'autant."},
            [Composant("Ratio SCR sans mesure transitoire", sans_tr, "pct", page, "+", detail=detail_sans_tr,
                       valide=recoupe),
             Composant("Ratio SCR publié (fonds propres ÷ SCR)", avec, "pct", page, "-", detail=detail_avec,
                       valide=recoupe)],
            page, chapitre)))
    return out


def libelle_ligne(label, prefixe):
    """Libellé d'une ligne de primes / sinistres, sans commentaire technique entre crochets."""
    propre = re.sub(r"\s*\[.*?\]", "", label or "").strip()
    return propre if prefixe.lower()[:6] in propre.lower() else f"{prefixe} : {propre}"


def kpi_sp_nonvie(kp, lignes, ind, lignes_verifiees):
    """`lignes_verifiees` : {(kpi, composant_index)} des lignes relues dans
    le PDF par validate_kpis.py (contrôle 12, Décision 159)."""
    if ind.get("sp_nonvie_pct") is None:
        return None
    comps = []
    for kpi, op, prefixe in (("charge_sinistres", "num", "Sinistres"), ("primes_acquises_brutes", "den", "Primes")):
        parent = kp[kpi]
        for code, label, valeur, unite, page, index in lignes[kpi]:
            if comparabilite._classe_composant(code, label) != "non-vie":
                continue
            comps.append(Composant(
                libelle_ligne(label, prefixe), valeur, unite, page, op,
                code=code if code and code.startswith("R") else None, source_pdf=parent["source_pdf"],
                valide=(kpi, index) in lignes_verifiees,
                note_avertissement=parent["note_avertissement"] if parent["avertissement"] else None))
    k = kp["charge_sinistres"]
    return finaliser(KpiCalcule(
        "sp_nonvie", ind["sp_nonvie_pct"],
        {"type": "ratio", "texte": "Sinistres non-vie ÷ Primes non-vie × 100", "facteur": 100,
         "note": "Lignes non-vie seulement (santé non-vie comprise) ; les lignes vie sont exclues."},
        comps, k["source_page"], "Calculé à partir des primes et des sinistres par ligne d'activité",
        k["source_pdf"]))


def kpi_marge_sur_be(kp, ind):
    if ind.get("marge_risque_sur_be_pct") is None:
        return None
    k = kp["marge_risque"]
    return finaliser(KpiCalcule(
        "marge_risque_sur_be", ind["marge_risque_sur_be_pct"],
        {"type": "ratio", "texte": "Marge de risque ÷ Best estimate × 100", "facteur": 100, "note": None},
        [comp_kpi(kp, "marge_risque", "Marge de risque", "num"), comp_kpi(kp, "best_estimate", "Best estimate", "den")],
        k["source_page"], "Calculé à partir des provisions techniques du bilan prudentiel", k["source_pdf"]))


def kpi_mcr_sur_scr(kp, ind, perimetre):
    """Solo seulement, comme position_mcr : pour un groupe, le « MCR » est le
    SCR minimal consolidé (somme des MCR des filiales), pas un MCR."""
    mcr, scr = (kp.get("mcr") or {}).get("value"), (kp.get("scr_total") or {}).get("value")
    if perimetre != "solo" or not mcr or not scr:
        return None
    k = kp["mcr"]
    return finaliser(KpiCalcule(
        "mcr_en_pct_scr", round(mcr / scr * 100, 2),
        {"type": "ratio", "texte": "MCR ÷ SCR × 100", "facteur": 100,
         "note": NOTE_POSITION_MCR.get(ind.get("position_mcr"))},
        [comp_kpi(kp, "mcr", "MCR", "num"), comp_kpi(kp, "scr_total", "SCR", "den")],
        k["source_page"], "Calculé à partir du MCR et du SCR", k["source_pdf"]))


def preparer_schema(conn):
    conn.execute("""CREATE TABLE IF NOT EXISTS kpi_formules (
        company_id INTEGER NOT NULL REFERENCES companies(id),
        year INTEGER NOT NULL,
        kpi_name TEXT NOT NULL,
        type TEXT NOT NULL CHECK (type IN ('ratio', 'difference')),
        texte TEXT NOT NULL,
        facteur REAL NOT NULL DEFAULT 1,
        note TEXT,
        PRIMARY KEY (company_id, year, kpi_name))""")
    existantes = {r[1] for r in conn.execute("PRAGMA table_info(kpi_composants)")}
    for col, typ in (("kpi_code", "TEXT"), ("composant_detail", "TEXT"), ("composant_source_pdf", "TEXT"),
                     ("composant_valide", "INTEGER")):
        if col not in existantes:
            conn.execute(f"ALTER TABLE kpi_composants ADD COLUMN {col} {typ}")


def calculer_societe(conn, c, lt):
    kp = {r["kpi_name"]: dict(r) for r in conn.execute(
        """SELECT kpi_name, value, unit, source_page, source_pdf, validated, avertissement, note_avertissement
           FROM kpis WHERE company_id=? AND year=? AND value IS NOT NULL AND kpi_name NOT IN ({})""".format(
            ",".join("?" * len(NOMS))), (c["id"], YEAR, *NOMS))}
    lignes = {}
    for r in conn.execute(
            """SELECT kpi_name, composant_code_qrt, composant_label, composant_valeur, composant_unite, composant_page,
                      composant_index
               FROM kpi_composants WHERE company_id=? AND year=? AND kpi_name IN ('primes_acquises_brutes',
               'charge_sinistres') ORDER BY kpi_name, composant_index""", (c["id"], YEAR)):
        lignes.setdefault(r[0], []).append(tuple(r[1:]))
    # Décision 159 — lignes de primes / sinistres relues dans le PDF
    # (validate_kpis.py, contrôle 12, check « sp_nonvie_ligne_<kpi>_<index> »).
    lignes_verifiees = set()
    for (nom_check,) in conn.execute(
            "SELECT check_name FROM validation_checks WHERE company_id=? AND year=? AND passed=1 "
            "AND check_name LIKE 'sp_nonvie_ligne_%'", (c["id"], YEAR)):
        kpi, _, index = nom_check.removeprefix("sp_nonvie_ligne_").rpartition("_")
        lignes_verifiees.add((kpi, int(index)))
    # Indicateur de référence : mêmes entrées que export_kpis_for_frontend.py.
    valeurs = {k: v["value"] for k, v in kp.items()}
    comp = {k: [(code, label, v) for code, label, v, *_ in ls] for k, ls in lignes.items()}
    ind = comparabilite.indicateurs(valeurs, comp, c["type_document"], c["scr_method"], lt)

    calcules = kpis_mesures_lt(c["name"], kp, lt, ind) if lt else []
    for kc in (kpi_marge_sur_be(kp, ind), kpi_sp_nonvie(kp, lignes, ind, lignes_verifiees),
               kpi_mcr_sur_scr(kp, ind, c["type_document"])):
        if kc is not None:
            calcules.append(kc)
    return calcules


def inserer(conn, company_id, kc):
    d = DEFS[kc.kpi_name]
    conn.execute(
        """INSERT INTO kpis (company_id, year, category, kpi_name, value, unit, source_page, source_chapter,
               validated, raw_value, raw_unit, source_pdf, avertissement, note_avertissement)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)""",
        (company_id, YEAR, CATEGORIE_INDICATEURS, kc.kpi_name, kc.valeur, d["unit"], kc.page, kc.chapitre,
         int(kc.valide), kc.source_pdf, int(kc.avertissement), kc.note_avertissement))
    f = kc.formule
    conn.execute("INSERT INTO kpi_formules VALUES (?, ?, ?, ?, ?, ?, ?)",
                 (company_id, YEAR, kc.kpi_name, f["type"], f["texte"], f["facteur"], f.get("note")))
    conn.executemany(
        """INSERT INTO kpi_composants (company_id, year, kpi_name, composant_index, composant_label,
               composant_code_qrt, composant_valeur, composant_unite, composant_page, operation,
               kpi_code, composant_detail, composant_source_pdf, composant_valide)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(company_id, YEAR, kc.kpi_name, i, c.label, c.code, c.valeur, c.unite, c.page, c.operation,
          c.kpi_code, c.detail, c.source_pdf, int(c.valide)) for i, c in enumerate(kc.composants, start=1)])


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    preparer_schema(conn)
    marques = ",".join("?" * len(NOMS))
    for table in ("kpis", "kpi_composants", "kpi_formules"):
        conn.execute(f"DELETE FROM {table} WHERE year=? AND kpi_name IN ({marques})", (YEAR, *NOMS))
    impact_lt = {r["company_id"]: dict(r) for r in conn.execute("SELECT * FROM impact_mesures_lt WHERE year=?", (YEAR,))}

    bilan = {k: [0, 0, 0] for k in NOMS}  # créés, validés, avertissements
    ecart_max = 0.0
    for c in conn.execute("SELECT * FROM companies ORDER BY name").fetchall():
        for kc in calculer_societe(conn, c, impact_lt.get(c["id"])):
            inserer(conn, c["id"], kc)
            b = bilan[kc.kpi_name]
            b[0] += 1
            b[1] += kc.valide
            b[2] += kc.avertissement
            ecart_max = max(ecart_max, abs(kc.recalcul - kc.valeur))
            if kc.avertissement:
                print(f"  avertissement {c['name']} / {kc.kpi_name} : {kc.note_avertissement}")
    conn.commit()
    conn.close()
    print(f"{'KPI':28} {'créés':>6} {'vérifiés':>9} {'avertis.':>9}")
    for k, (n, v, a) in bilan.items():
        print(f"{k:28} {n:>6} {v:>9} {a:>9}")
    print(f"Écart maximal recalcul / valeur : {ecart_max:.4f} (tolérance {TOLERANCE})")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
