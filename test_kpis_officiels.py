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
6. Décision 159 — S/P non-vie relu dans le PDF (validate_kpis.py, contrôle
   12) : lecture des montants et identité brut − réassurance = net sur des
   extraits réels (dont la ligne MAIF imprimée −2 097 K€) ; cohérence entre
   validation_checks, kpis.db et le JSON ; 15 sp_nonvie vérifiés sur 25 ;
   Décision 160 : ligne MAIF à −2,097 M€, S/P MAIF 60,3 %, page 85 de
   Covéa. Si la sauvegarde d'avant existe, seuls `validated` de sp_nonvie,
   `composant_valide` de ses lignes et les corrections de la Décision 160
   (CORRECTIONS_160) ont changé dans la base.

    python test_kpis_officiels.py [ancien_donnees-extraites.json] [ancien_kpi-sources.json]

Par défaut, l'ancien JSON est archive/donnees-extraites_avant_nuit_kpis_officiels.json
(sauvegarde locale non suivie par git) ; le contrôle 3 est sauté s'il manque.
Contrôle 6, comparaison avec archive/kpis_avant_sp_covea_20261016.db : sautée
si la sauvegarde manque.
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
# Décision 159 — sp_nonvie vérifiés : pages S.05.01 avec texte, identité
# brut − réassurance = net retrouvée pour les primes et les sinistres.
SP_VERIFIES = {"AG.Mut", "AG2R Prevoyance", "AXA France IARD", "AXA France Vie", "Arpege Prevoyance",
               "BPCE Assurances IARD", "Cardif Assurances Risques Divers", "Covéa", "Crédit Agricole Assurances",
               "La Mondiale", "MAIF", "MGEN", "Prima", "SGAM AG2R LA MONDIALE", "VIASANTE Mutuelle"}
DB_AVANT_159 = RACINE / "archive" / "kpis_avant_sp_covea_20261016.db"
# Décision 160 — corrections voulues depuis les sauvegardes : signe d'une
# ligne de sinistres MAIF (p.113), page 85 de Covéa. (société, kpi) ->
# colonnes de `kpis` autorisées à changer.
CORRECTIONS_160 = {("MAIF", "charge_sinistres"): {"value", "raw_value", "source_chapter"},
                   ("MAIF", "sp_nonvie"): {"value", "validated"},
                   ("Covéa", "best_estimate"): {"source_page"}, ("Covéa", "marge_risque"): {"source_page"},
                   # AG.Mut : page de marge_risque 207 -> 199, recopiée dans marge_risque_sur_be.
                   ("AG.Mut", "marge_risque"): {"source_page"}, ("AG.Mut", "marge_risque_sur_be"): {"source_page"},
                   # Ligne « Marge de risque » du détail de provisions_techniques : page 207 -> 199 seulement.
                   ("AG.Mut", "provisions_techniques"): set()}
IGNORES_160 = [r"/kpisParSociete/MAIF/charge_sinistres/.*", r"/kpisParSociete/Covéa/(best_estimate|marge_risque)/.*",
               r"/indicateursParSociete/MAIF/sp_nonvie_pct", r"/kpisParSociete/AG\.Mut/marge_risque/pageSource",
               r"/kpisParSociete/AG\.Mut/provisions_techniques/composants\[1\]/pageSource"]
IGNORES_160_SOURCES = [r"/MAIF/charge_sinistres/(value|raw_value|source_chapter)", r"/MAIF/sp_nonvie/value",
                       r"/Covéa/(best_estimate|marge_risque)/source_page",
                       r"/AG\.Mut/(marge_risque|marge_risque_sur_be)/source_page"]
# Décision 161 — textes affichés réécrits en français simple : seuls ces
# champs de texte peuvent différer des sauvegardes (jamais une valeur, un
# statut ou une page).
IGNORES_161 = [r"/kpisParSociete/[^/]+/[^/]+/chapitreSource", r"/kpisParSociete/[^/]+/[^/]+/composants\[\d+\]/label",
               r"/compatibilite/matrice/[^/]+/[^/]+/note", r"/compatibilite/regle"]
IGNORES_161_SOURCES = [r"/[^/]+/[^/]+/source_chapter"]
TEXTES_161 = {"source_chapter", "composant_label"}
# Extrait réel, rapport-solvabilite-maif-2025.pdf p.113 (texte PyMuPDF).
EXTRAIT_MAIF = """Primes acquises
 Brut – assurance directe
         69 964            275 152                4 247
       3 918 623
Charge des sinistres
 Brut – assurance directe
          16 633            132 168                2 952
       2 367 845
 Brut – Réassurance proportionnelle acceptée
                   -                        -                        -
             23 697
 Brut – Réassurance non proportionnelle
acceptée
-                26   -              150
                     -     -             1 920   -             2 097
 Part des réassureurs
                   -             167 839
                   -                        -                        -                          -                          -                281 401
 Net
          16 633   -         35 671                2 952   -                26   -              150
                     -     -             1 920          2 108 044
Dépenses engagées
         68 094            124 818                  598
"""

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
        diff_ajouts(ancien, d, "", [r"/genereLe", r"/definitionsIndicateurs/[^/]+", *IGNORES_160, *IGNORES_161], ecarts)
        for e in ecarts:
            print(f"    {e}")
        verifier("donnees-extraites.json : aucun retrait ni modification", not ecarts, f"({len(ecarts)} écarts)")
        ecarts = []
        diff_ajouts(ancien["indicateursParSociete"], d["indicateursParSociete"], "/indicateursParSociete",
                    IGNORES_160, ecarts)
        verifier("indicateursParSociete identique (hors S/P MAIF, Décision 160)", not ecarts, f"{ecarts}")
        verifier("indicateursParSociete : mêmes clés", all(
            ancien["indicateursParSociete"][s].keys() == d["indicateursParSociete"].get(s, {}).keys()
            for s in ancien["indicateursParSociete"]) and ancien["indicateursParSociete"].keys()
            == d["indicateursParSociete"].keys())
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
                    json.loads(SOURCES_NOUVEAU.read_text(encoding="utf-8")), "",
                    IGNORES_160_SOURCES + IGNORES_161_SOURCES, ecarts)
        for e in ecarts:
            print(f"    {e}")
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
    print("6. S/P non-vie relu dans le PDF (validate_kpis.py, contrôle 12)")
    print("=" * 90)
    import validate_kpis as vk
    for case, attendu in (("1 610 869", (1610869.0, 0)), ("12 038,51 ", (12038.51, 2)), ("2 097", (2097.0, 0)),
                          ("1.234.567", (1234567.0, 0)), ("(1 234)", (1234.0, 0)), ("0,5", (0.5, 1)),
                          ("-", None), ("R0210", None), ("C0200", None), ("Net", None)):
        verifier(f"lire_montant({case!r})", vk.lire_montant(case) == attendu, f"{vk.lire_montant(case)} au lieu de {attendu}")
    sections = vk.montants_par_section(EXTRAIT_MAIF)
    verifier("sections primes / sinistres", [x for x, _ in sections["primes"]] == [69964, 275152, 4247, 3918623]
             and (2108044.0, 0) in sections["sinistres"] and (68094.0, 0) not in sections["sinistres"])
    verifier("identité MAIF avec la ligne en base (+2 097) : refusée",
             vk.identite_s0501(sections["sinistres"], [2367845, 23697, 2097]) is None)
    verifier("identité MAIF avec la ligne imprimée (−2 097) : brut − 281 401 = 2 108 044",
             vk.identite_s0501(sections["sinistres"], [2367845, 23697, -2097]) == (281401.0, 2108044.0, 1))

    conn = sqlite3.connect(RACINE / "kpis.db")
    ids = {n: i for i, n in conn.execute("SELECT id, name FROM companies")}
    sp_verifies = set()
    for nom, kp in kps.items():
        sp = kp.get("sp_nonvie")
        checks = {c: (p, d) for c, p, d in conn.execute(
            "SELECT check_name, passed, details FROM validation_checks WHERE company_id=? AND year=2025 "
            "AND check_name LIKE 'sp_nonvie_%'", (ids[nom],))}
        lignes = {c: v for c, v in checks.items() if c.startswith("sp_nonvie_ligne_")}
        if sp is None:
            verifier(f"{nom} sans sp_nonvie : pas de contrôle 12", not checks)
            continue
        verifier(f"{nom}/sp_nonvie : une ligne contrôlée par composant", len(lignes) == len(sp["composants"]),
                 f"({len(lignes)} contrôles, {len(sp['composants'])} composants)")
        verifier(f"{nom}/sp_nonvie : composants valides = lignes relues",
                 sum(c["valide"] for c in sp["composants"]) == sum(p for p, _ in lignes.values()))
        verifier(f"{nom}/sp_nonvie : recalcul contrôlé", checks.get("sp_nonvie_recalcul", (0,))[0] == 1)
        for groupe, kpi in (("primes", "primes_acquises_brutes"), ("sinistres", "charge_sinistres")):
            identite = checks.get(f"sp_nonvie_identite_{groupe}")
            for c, (p, d) in lignes.items():
                if kpi in c and p:
                    verifier(f"{nom}/{c} vérifiée sans identité", identite is not None and identite[0] == 1)
                if kpi in c and identite is None:
                    verifier(f"{nom}/{c} : raison écrite si non contrôlable", not p and d.startswith("NON CONTRÔLABLE"))
        verifier(f"{nom}/sp_nonvie : valide ⇔ toutes les lignes relues",
                 sp["valide"] == all(p for p, _ in lignes.values()))
        if sp["valide"]:
            sp_verifies.add(nom)
    print(f"  sp_nonvie vérifiés : {len(sp_verifies)} / {sum(1 for kp in kps.values() if 'sp_nonvie' in kp)}")
    verifier("sp_nonvie vérifiés = liste attendue", sp_verifies == SP_VERIFIES,
             f"(en trop {sorted(sp_verifies - SP_VERIFIES)}, manquants {sorted(SP_VERIFIES - sp_verifies)})")

    # Décision 160 : la correction MAIF et la page Covéa sont bien en base.
    cid_maif, cid_covea = ids["MAIF"], ids["Covéa"]
    lignes_maif = conn.execute("SELECT composant_index, composant_valeur FROM kpi_composants WHERE company_id=? "
                               "AND year=2025 AND kpi_name='charge_sinistres' ORDER BY composant_index",
                               (cid_maif,)).fetchall()
    total_maif = conn.execute("SELECT value FROM kpis WHERE company_id=? AND year=2025 AND kpi_name='charge_sinistres'",
                              (cid_maif,)).fetchone()[0]
    verifier("MAIF : ligne 3 des sinistres = −2,097 M€ (imprimé p.113)", dict(lignes_maif).get(3) == -2.097)
    verifier("MAIF : charge_sinistres = somme des lignes", abs(total_maif - sum(v for _, v in lignes_maif)) < 1e-6)
    verifier("MAIF : S/P non-vie = 60,3 %", kps["MAIF"]["sp_nonvie"]["valeur"] == 60.3)
    for kpi in ("best_estimate", "marge_risque"):
        pages = conn.execute("SELECT source_page FROM kpis WHERE company_id=? AND year=2025 AND kpi_name=? UNION ALL "
                             "SELECT composant_page FROM kpi_composants WHERE company_id=? AND year=2025 AND kpi_name=?",
                             (cid_covea, kpi, cid_covea, kpi)).fetchall()
        verifier(f"Covéa/{kpi} : page 85 (KPI et ses 5 lignes)", pages == [(85,)] * 6, f"{pages}")
        verifier(f"Covéa/{kpi} : page 85 dans le JSON", kps["Covéa"][kpi]["pageSource"] == 85)
    # AG.Mut : marge_risque p.199 (bilan S.02.01.02), comme ses 5 lignes, et sa copie dans marge_risque_sur_be.
    rm = kps["AG.Mut"]["marge_risque"]
    verifier("AG.Mut/marge_risque : page 199 (KPI et lignes)",
             rm["pageSource"] == 199 and all(c["pageSource"] == 199 for c in rm["composants"]))
    verifier("AG.Mut/marge_risque_sur_be : page 199 recopiée", kps["AG.Mut"]["marge_risque_sur_be"]["pageSource"] == 199
             and kps["AG.Mut"]["marge_risque_sur_be"]["composants"][0]["pageSource"] == 199)
    pt = [(c["label"], c["pageSource"]) for c in kps["AG.Mut"]["provisions_techniques"]["composants"]]
    verifier("AG.Mut/provisions_techniques : ligne « Marge de risque » p.199, best estimate inchangé p.79",
             pt == [("Meilleure estimation (best estimate)", 79), ("Marge de risque", 199)], f"{pt}")

    if DB_AVANT_159.exists():
        avant = sqlite3.connect(DB_AVANT_159)
        noms_par_id = {i: n for n, i in ids.items()}
        cols = ("company_id", "year", "kpi_name", "value", "unit", "source_page", "source_chapter", "validated",
                "raw_value", "raw_unit", "source_pdf", "avertissement", "note_avertissement")
        q = f"SELECT {', '.join(cols)} FROM kpis ORDER BY company_id, kpi_name"
        a, b = avant.execute(q).fetchall(), conn.execute(q).fetchall()
        verifier("kpis : mêmes lignes qu'avant", len(a) == len(b))
        for x, y in zip(a, b):
            changees = {c for c, u, v in zip(cols, x, y) if u != v}
            permises = CORRECTIONS_160.get((noms_par_id[x[0]], x[2]), set()) | (
                {"validated"} if x[2] == "sp_nonvie" else set()) | TEXTES_161
            verifier(f"kpis {noms_par_id[x[0]]}/{x[2]} : seules les corrections voulues", changees <= permises,
                     f"{sorted(changees - permises)}")
        # Sans `id` : peupler_kpis_officiels_indicateurs.py réinsère ses lignes.
        cols = ("company_id", "year", "kpi_name", "composant_index", "composant_label", "composant_code_qrt",
                "composant_valeur", "composant_unite", "composant_page", "operation", "kpi_code", "composant_detail",
                "composant_source_pdf", "composant_valide")
        q = f"SELECT {', '.join(cols)} FROM kpi_composants ORDER BY company_id, kpi_name, composant_index"
        a, b = avant.execute(q).fetchall(), conn.execute(q).fetchall()
        verifier("kpi_composants : mêmes lignes qu'avant", len(a) == len(b))
        for x, y in zip(a, b):
            changees = {c for c, u, v in zip(cols, x, y) if u != v}
            societe, kpi = noms_par_id[x[0]], x[2]
            permises = ({"composant_valide"} if kpi == "sp_nonvie" else set()) | (
                {"composant_valeur"} if (societe, kpi, x[3]) in (("MAIF", "charge_sinistres", 3), ("MAIF", "sp_nonvie", 3))
                else set()) | ({"composant_page"} if (societe, kpi) in CORRECTIONS_160 and kpi != "sp_nonvie" else set()) \
                | TEXTES_161
            verifier(f"kpi_composants {societe}/{kpi}#{x[3]} : seules les corrections voulues", changees <= permises,
                     f"{sorted(changees - permises)}")
        q = ("SELECT company_id, check_name, expected_value, computed_value, passed, details FROM validation_checks "
             "WHERE check_name NOT LIKE 'sp_nonvie_%' ORDER BY company_id, check_name")
        a, b = avant.execute(q).fetchall(), conn.execute(q).fetchall()
        # (les détails des contrôles 1-11 ne citent aucun libellé : inchangés malgré la Décision 161)
        verifier("validation_checks : contrôles 1-11 inchangés (hors charge de sinistres MAIF)", len(a) == len(b) and all(
            x == y or (noms_par_id[x[0]] == "MAIF" and x[1] in ("signe_charge_sinistres", "magnitude_charge_sinistres")
                       and x[4] == y[4] == 1) for x, y in zip(a, b)))
        avant.close()
    else:
        print(f"  (comparaison sautée : {DB_AVANT_159} introuvable)")

    print("=" * 90)
    print("7. Textes affichés en français simple (Décision 161)")
    print("=" * 90)
    from textes_simples import contient_jargon, nettoyer_libelle, source_simple
    for t, attendu in (("scr_marche", True), ("NULL", True), ("Décision 150", True), ("R0540/C0010", True),
                       ("sfcr_covea_2025.pdf", True), ("D.2", True), ("S.23.01.01.01/R0540/Total", True),
                       ("Tableau officiel S.23.01 (fonds propres)", False), ("Rapport, chapitre D.2 (provisions techniques)",
                                                                           False), ("Primes : brut – non-vie", False)):
        verifier(f"contient_jargon({t!r})", contient_jargon(t) == attendu)
    verifier("source_simple : ligne du tableau des fonds propres",
             source_simple("X", "fonds_propres_t2", "S.23.01.01/R0540/C0040 imprimé « - » (p.61)")
             == "Tableau officiel S.23.01 (fonds propres) — case vide ou « - » dans le tableau (zéro)")
    verifier("nettoyer_libelle : code et césures retirés",
             nettoyer_libelle("Primes : brutes – reassu- rance proportion- nelle acceptee r0220")
             == "Primes : brutes – réassurance proportionnelle acceptée")
    textes = []
    for nom, kp in kps.items():
        for k, v in kp.items():
            textes += [v.get(c) for c in ("chapitreSource", "noteAvertissement", "sourceLisible", "libelle")]
            textes += [(v.get("formule") or {}).get(c) for c in ("texte", "note")]
            textes += [c.get(x) for c in (v.get("composants") or []) for x in ("label", "detail")]
    dj = json.loads(JSON_NOUVEAU.read_text(encoding="utf-8"))  # `d` est réutilisé plus haut
    textes += [v.get("note") for axes in dj["compatibilite"]["matrice"].values() for v in axes.values()]
    textes += [dj["compatibilite"]["regle"], *dj["definitionsIndicateurs"].values()]
    textes += [v["description"] for v in dj["definitionsKpis"].values()]
    restes = [t for t in textes if t and contient_jargon(t)]
    print(f"  {sum(1 for t in textes if t)} textes affichés, avec jargon : {len(restes)}")
    verifier("aucun jargon dans les textes affichés", not restes, f"{restes[:3]}")
    n_sans_trace = conn.execute("SELECT COUNT(*) FROM kpis WHERE source_chapter_technique IS NULL AND source_chapter "
                                "LIKE 'Tableau officiel%'").fetchone()[0]
    verifier("trace technique gardée pour chaque source réécrite", n_sans_trace == 0, f"({n_sans_trace})")
    conn.close()

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
