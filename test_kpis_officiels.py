# -*- coding: utf-8 -*-
"""test_kpis_officiels.py — Décision 158 : contrôles des 6 KPIs calculés
promus en KPIs officiels (peupler_kpis_officiels_indicateurs.py), sur le
JSON exporté pour le front-end.

1. Pour chaque KPI et société : recalcul depuis les composants = valeur
   affichée (tolérance 0,05) ; `valide` = tous les composants valides ET
   recalcul exact ; composant `kpiCode` = KPI officiel de la société.
2. Égalité avec l'indicateur d'origine (indicateursParSociete), et
   cohérence de mcr_en_pct_scr avec position_mcr.
3. Diff avec l'ancien JSON (sauvegarde d'avant la promotion) : uniquement
   des ajouts, sauf `genereLe` et les textes de `definitionsIndicateurs`
   (simplification demandée). Même contrôle pour kpi-sources.json si
   l'ancienne version est fournie.
4. Aucun KPI nul créé (base et JSON), aucune page source manquante.
5. Décompte par KPI et par société ; textes sans code QRT ni nom de société.

    python test_kpis_officiels.py [ancien_donnees-extraites.json] [ancien_kpi-sources.json]

Par défaut, l'ancien JSON est archive/donnees-extraites_avant_nuit_kpis_officiels.json
(sauvegarde locale non suivie par git) ; le contrôle 3 est sauté s'il manque.
"""
import json
import math
import re
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = Path(__file__).parent
sys.path.insert(0, str(RACINE))
from kpi_definitions import KPI_INDICATEURS_OFFICIELS  # noqa: E402

TOLERANCE = 0.05
JSON_NOUVEAU = RACINE / "frontend" / "src" / "data" / "donnees-extraites.json"
SOURCES_NOUVEAU = RACINE / "frontend" / "src" / "data" / "kpi-sources.json"
JSON_ANCIEN = Path(sys.argv[1]) if len(sys.argv) > 1 else RACINE / "archive" / "donnees-extraites_avant_nuit_kpis_officiels.json"
SOURCES_ANCIEN = Path(sys.argv[2]) if len(sys.argv) > 2 else None
NOMS = [d["kpi_name"] for d in KPI_INDICATEURS_OFFICIELS]
INDICATEUR = {d["kpi_name"]: d["indicateur"] for d in KPI_INDICATEURS_OFFICIELS}
ATTENDUS = {"ratio_scr_sans_mesures_lt": 41, "impact_va": 41, "impact_transitoires": 4,
            "marge_risque_sur_be": 41, "sp_nonvie": 25, "mcr_en_pct_scr": 36}

echecs = []


def verifier(nom, condition, detail=""):
    if not condition:
        echecs.append(f"{nom} {detail}".strip())
        print(f"  [ÉCHEC] {nom} {detail}")


def recalculer(formule, composants):
    if formule["type"] == "ratio":
        num = sum(c["valeur"] for c in composants if c["operation"] == "num")
        den = sum(c["valeur"] for c in composants if c["operation"] == "den")
        return num / den * formule["facteur"]
    return sum(c["valeur"] if c["operation"] == "+" else -c["valeur"] for c in composants) * formule["facteur"]


def diff_ajouts(ancien, nouveau, chemin, ignores, ecarts):
    """Liste les chemins de `ancien` absents ou modifiés dans `nouveau`."""
    if any(re.fullmatch(motif, chemin) for motif in ignores):
        return
    if isinstance(ancien, dict) and isinstance(nouveau, dict):
        for k, v in ancien.items():
            if k not in nouveau:
                ecarts.append(f"supprimé : {chemin}/{k}")
            else:
                diff_ajouts(v, nouveau[k], f"{chemin}/{k}", ignores, ecarts)
    elif isinstance(ancien, list) and isinstance(nouveau, list):
        if len(ancien) != len(nouveau):
            ecarts.append(f"liste de longueur différente : {chemin}")
        for i, (a, n) in enumerate(zip(ancien, nouveau)):
            diff_ajouts(a, n, f"{chemin}[{i}]", ignores, ecarts)
    elif ancien != nouveau:
        ecarts.append(f"modifié : {chemin} : {ancien!r} -> {nouveau!r}")


def main():
    d = json.loads(JSON_NOUVEAU.read_text(encoding="utf-8"))
    kps, ind_par_soc = d["kpisParSociete"], d["indicateursParSociete"]
    societes = {s["name"]: s for s in d["societes"]}

    print("=" * 90)
    print("1-2. Recalcul, validité, égalité avec les indicateurs d'origine")
    print("=" * 90)
    decompte = {k: {"crees": [], "non_crees": [], "valide": 0, "non_valide": 0} for k in NOMS}
    ecart_max = 0.0
    for nom, kp in kps.items():
        ind = ind_par_soc[nom]
        for k in NOMS:
            kpi = kp.get(k)
            source = INDICATEUR[k]
            if kpi is None:
                decompte[k]["non_crees"].append(nom)
                if source:
                    verifier(f"{nom}/{k} absent alors que l'indicateur existe", ind.get(source) is None)
                continue
            decompte[k]["crees"].append(nom)
            decompte[k]["valide" if kpi["valide"] else "non_valide"] += 1
            verifier(f"{nom}/{k} valeur numérique", isinstance(kpi["valeur"], (int, float))
                     and math.isfinite(kpi["valeur"]))
            verifier(f"{nom}/{k} formule et composants", kpi.get("formule") and kpi.get("estCompose")
                     and kpi.get("composants"))
            verifier(f"{nom}/{k} catégorie", kpi["categorie"] == "indicateurs_comparables")
            recalc = recalculer(kpi["formule"], kpi["composants"])
            ecart = abs(recalc - kpi["valeur"])
            ecart_max = max(ecart_max, ecart)
            verifier(f"{nom}/{k} recalcul", ecart <= TOLERANCE + 1e-9, f"{recalc} vs {kpi['valeur']}")
            attendu_valide = ecart <= TOLERANCE + 1e-9 and all(c["valide"] for c in kpi["composants"])
            verifier(f"{nom}/{k} règle de validité", kpi["valide"] == attendu_valide)
            for c in kpi["composants"]:
                verifier(f"{nom}/{k} composant {c['label']!r} : page source", c["pageSource"] is not None)
                verifier(f"{nom}/{k} composant {c['label']!r} : opération",
                         c["operation"] in (("num", "den") if kpi["formule"]["type"] == "ratio" else ("+", "-")))
                if c.get("kpiCode"):
                    ref = kp.get(c["kpiCode"])
                    verifier(f"{nom}/{k} kpiCode {c['kpiCode']} existe", ref is not None)
                    if ref:
                        verifier(f"{nom}/{k} kpiCode {c['kpiCode']} = valeur du KPI",
                                 abs(ref["valeur"] - c["valeur"]) <= TOLERANCE + 0.011,
                                 f"{c['valeur']} vs {ref['valeur']}")
                        verifier(f"{nom}/{k} kpiCode {c['kpiCode']} validité", c["valide"] == ref["valide"])
            heritee = [c for c in kpi["composants"] if c.get("kpiCode") and kp[c["kpiCode"]].get("avertissement")]
            if heritee:
                verifier(f"{nom}/{k} avertissement hérité", kpi["avertissement"])
            if source:
                verifier(f"{nom}/{k} = indicateur {source}", ind.get(source) is not None
                         and abs(ind[source] - kpi["valeur"]) <= TOLERANCE, f"{ind.get(source)} vs {kpi['valeur']}")
        # mcr_en_pct_scr : même périmètre et même corridor que position_mcr.
        m = kp.get("mcr_en_pct_scr")
        verifier(f"{nom}/mcr_en_pct_scr ⇔ position_mcr", (m is not None) == (ind.get("position_mcr") is not None))
        if m:
            x = kp["mcr"]["valeur"] / kp["scr_total"]["valeur"] * 100
            verifier(f"{nom}/mcr_en_pct_scr recalcul direct", abs(x - m["valeur"]) <= TOLERANCE)
            verifier(f"{nom}/mcr_en_pct_scr solo", societes[nom]["perimetre"] == "solo")
        # sans mesure : ratio sans mesures = ratio publié, impact VA nul
        if ind.get("utilise_va") is False and ind.get("mesure_transitoire") is False:
            verifier(f"{nom} sans mesure : ratio = publié",
                     abs(kp["ratio_scr_sans_mesures_lt"]["valeur"] - kp["ratio_scr"]["valeur"]) <= TOLERANCE)
            verifier(f"{nom} sans mesure : impact VA nul", kp["impact_va"]["valeur"] == 0)
            verifier(f"{nom} sans mesure : note", "ni correction pour volatilité" in
                     kp["ratio_scr_sans_mesures_lt"]["formule"].get("note", ""))
    print(f"  écart maximal recalcul / valeur : {ecart_max:.4f} (tolérance {TOLERANCE})")

    print("=" * 90)
    print("3. Diff avec l'ancien JSON : uniquement des ajouts")
    print("=" * 90)
    if JSON_ANCIEN.exists():
        ancien = json.loads(JSON_ANCIEN.read_text(encoding="utf-8"))
        ecarts = []
        diff_ajouts(ancien, d, "", [r"/genereLe", r"/definitionsIndicateurs/[^/]+"], ecarts)
        for e in ecarts:
            print(f"    {e}")
        verifier("donnees-extraites.json : aucun retrait ni modification", not ecarts, f"({len(ecarts)} écarts)")
        verifier("indicateursParSociete strictement identique", ancien["indicateursParSociete"] == d["indicateursParSociete"])
        verifier("definitionsIndicateurs : mêmes clés", ancien["definitionsIndicateurs"].keys() == d["definitionsIndicateurs"].keys())
        n_ancien = sum(len(v) for v in ancien["kpisParSociete"].values())
        n_nouveau = sum(len(v) for v in kps.values())
        print(f"  KPIs : {n_ancien} -> {n_nouveau} (+{n_nouveau - n_ancien})")
        verifier("ajouts = KPIs calculés seulement",
                 n_nouveau - n_ancien == sum(len(v["crees"]) for v in decompte.values()))
    else:
        print(f"  (sauté : {JSON_ANCIEN} introuvable)")
    if SOURCES_ANCIEN and SOURCES_ANCIEN.exists():
        ecarts = []
        diff_ajouts(json.loads(SOURCES_ANCIEN.read_text(encoding="utf-8")),
                    json.loads(SOURCES_NOUVEAU.read_text(encoding="utf-8")), "", [], ecarts)
        verifier("kpi-sources.json : aucun retrait ni modification", not ecarts, f"({len(ecarts)} écarts)")

    print("=" * 90)
    print("4. Aucun KPI nul créé")
    print("=" * 90)
    conn = sqlite3.connect(RACINE / "kpis.db")
    marques = ",".join("?" * len(NOMS))
    n_null = conn.execute(f"SELECT COUNT(*) FROM kpis WHERE kpi_name IN ({marques}) AND value IS NULL", NOMS).fetchone()[0]
    verifier("aucune valeur NULL en base", n_null == 0, f"({n_null})")
    n_base = conn.execute(f"SELECT COUNT(*) FROM kpis WHERE kpi_name IN ({marques})", NOMS).fetchone()[0]
    verifier("base = JSON", n_base == sum(len(v["crees"]) for v in decompte.values()))
    conn.close()

    print("=" * 90)
    print("5. Textes et matrice")
    print("=" * 90)
    noms_societes = [n for n in societes if len(n) > 3] + ["Generali", "AXA", "Aéma", "AG2R", "BPCE"]
    qrt = re.compile(r"\bS\.\d{2}\.\d{2}|\b[RC]\d{4}\b")
    textes = {**{f"definitionsKpis/{k}": v["description"] for k, v in d["definitionsKpis"].items()},
              **{f"definitionsIndicateurs/{k}": v for k, v in d["definitionsIndicateurs"].items()}}
    for cle, texte in textes.items():
        verifier(f"{cle} sans code QRT", not qrt.search(texte), texte)
        verifier(f"{cle} sans nom de société", not any(n in texte for n in noms_societes), texte)
    for k in NOMS:
        verifier(f"matrice {k}", set(d["compatibilite"]["matrice"].get(k, {})) == set(d["compatibilite"]["axes"]))
        verifier(f"définition {k}", k in d["definitionsKpis"])

    print("=" * 90)
    print("Décompte par KPI")
    print("=" * 90)
    print(f"  {'KPI':28} {'créés':>6} {'non créés':>10} {'valide vrai':>12} {'valide faux':>12}")
    for k, v in decompte.items():
        print(f"  {k:28} {len(v['crees']):>6} {len(v['non_crees']):>10} {v['valide']:>12} {v['non_valide']:>12}")
        verifier(f"décompte {k}", len(v["crees"]) == ATTENDUS[k], f"({len(v['crees'])} au lieu de {ATTENDUS[k]})")
    print("  Par société :")
    for nom in kps:
        presents = [k for k in NOMS if k in kps[nom]]
        print(f"    {nom:36} {len(presents)}  {', '.join(presents)}")

    print("=" * 90)
    print(f"RÉSULTAT : {'OK' if not echecs else f'{len(echecs)} ÉCHEC(S)'}")
    return 0 if not echecs else 1


if __name__ == "__main__":
    sys.exit(main())
