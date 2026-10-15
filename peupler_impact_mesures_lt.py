# -*- coding: utf-8 -*-
"""peupler_impact_mesures_lt.py — Impact des mesures relatives aux garanties
de long terme (correction pour volatilité, VA) et des mesures transitoires
sur les fonds propres et le SCR, pour les 41 sociétés (Décision 155).

Source : état S.22.01 (R0050 fonds propres éligibles au SCR, R0090 SCR ;
C0010 montant publié, C0030 impact de la mesure transitoire sur les
provisions techniques, C0050 transitoire sur les taux, C0070 impact d'une
VA fixée à zéro). Lu en texte natif quand c'est possible, sinon sur rendu
image de la page (rapport Aéma, BPCE IARD, Groupama : tableaux en image ;
Groupama imprimé tourné). Chaque C0010 a été recoupé avec
fonds_propres_eligibles / scr_total de kpis.db (égalité exacte pour les 30
sociétés à tableau), les impacts en points avec le texte des rapports quand
il en donne (MACIF SAM −5, Abeille Vie −10, Abeille Épargne Retraite −13,
Covéa −2 pts).

Approche par étapes de l'EIOPA : l'impact VA (C0070) est mesuré APRÈS
retrait des mesures transitoires. Pour une société qui applique la
transitoire sur provisions (BPCE Vie, La Mondiale, SGAM AG2R, Groupama),
le ratio « sans VA » calculé ici = ratio sans VA ET sans transitoire.

Sociétés sans S.22.01 : un organisme qui n'applique aucune mesure n'a pas
à publier cet état (impact nul). Generali Vie / IARD (annexes QRT sans
S.22.01) : ratio sans VA publié dans le texte seulement.

Rejouable (DROP + recréation de la table). Ordre : après
corrections_comparabilite.py, avant export_kpis_for_frontend.py.

    python peupler_impact_mesures_lt.py
"""
import sqlite3
from pathlib import Path

DB = Path(__file__).parent / "kpis.db"
YEAR = 2025

# nom : (unité, FP C0010, SCR C0010, ΔFP VA, ΔSCR VA, ΔFP transitoires,
#        ΔSCR transitoires, page, source)
S2201 = {
    "AG.Mut": ("K€", 34_399, 4_843, -2, 2, 0, 0, 208, "S.22.01.21 (texte)"),
    "AG2R Prevoyance": ("K€", 1_645_670, 974_095, -29_673, 4_438, 0, 0, 149, "S.22.01.21 (texte)"),
    "AXA France IARD": ("K€", 4_390_846, 2_621_463, -86_406, 192_998, 0, 0, 7, "S.22.01.21 (texte)"),
    "AXA France Vie": ("K€", 8_671_479, 5_469_627, -216_078, 504_809, 0, 0, 8, "S.22.01.21 (texte, vérifié sur image)"),
    "Abeille Epargne Retraite": ("€", 1_729_978_700, 438_900_678, -1_682_295, 15_058_767, 0, 0, 598, "S.22.01.21 (image, tableau tourné)"),
    "Abeille IARD Sante": ("€", 1_559_491_555, 931_326_706, -10_780_214, 7_087_872, 0, 0, 613, "S.22.01.21 (image)"),
    "Abeille Vie": ("€", 5_091_873_694, 1_997_456_960, -28_528_720, 70_167_673, 0, 0, 587, "S.22.01.21 (image)"),
    "Aema Groupe": ("K€", 12_860_966, 6_063_105, -120_972, 130_444, 0, 0, 444, "S.22.01.22 (image, tableau tourné)"),
    "Allianz Vie": ("K€", 4_266_905, 2_218_591, -116_600, 513_297, 0, 0, 87, "S.22.01.21 format complet, C0070 (texte)"),
    "Arpege Prevoyance": ("K€", 273_578, 101_118, -2_985, 265, 0, 0, 169, "S.22.01.21 (texte)"),
    "BPCE Assurances IARD": ("K€", 678_325, 527_994, -5_875, 748, 0, 0, 75, "S.22.01.01 (image)"),
    "BPCE Vie": ("K€", 7_363_314, 2_957_205, -95_584, -22_828, -2_590_951, 0, 83, "S.22.01.21 (texte, vérifié sur image)"),
    "CNP Assurances": ("K€", 36_778_134, 14_256_819, -197_093, 305_899, 0, 0, 94, "S.22.01.21 (texte)"),
    "Cardif Assurance Vie": ("K€", 11_254_371, 6_610_740, -155_845, -14_040, 0, 0, 11, "S.22.01.21 (texte)"),
    "Cardif Assurances Risques Divers": ("K€", 617_813, 423_853, -738, -12, 0, 0, 11, "S.22.01.21 (texte)"),
    "Covéa": ("K€", 33_251_714, 15_058_209, -152_577, 82_817, 0, 0, 91, "S.22.01.22 (texte) ; tableau 17 p.67"),
    "Crédit Agricole Assurances": ("K€", 27_400_137, 14_087_440, -324_760, -24_768, 0, 0, 73, "S.22.01.22 (texte, vérifié sur image)"),
    "Groupama": ("K€", 16_481_186, 6_020_977, -145_939, 62_451, -1_763_676, 612_778, 84, "S.22.01.22 (image, tableau tourné)"),
    "La Mondiale": ("K€", 6_927_162, 2_441_979, -42_440, 15_511, -462_650, 0, 247, "S.22.01.21 (texte)"),
    "La Mondiale Europartner": ("K€", 637_645, 354_330, -1_288, 1_122, 0, 0, 264, "S.22.01.21 (texte)"),
    "La Mondiale Partenaire": ("K€", 1_260_938, 877_352, -7_806, 7_906, 0, 0, 279, "S.22.01.21 (texte)"),
    "MACIF SAM": ("K€", 9_443_143, 2_964_220, -121_743, 10_373, 0, 0, 462, "S.22.01.21 (image) ; texte p.96 : −5 pts"),
    "Macif Sante Prevoyance": ("K€", 948_561, 366_181, -16_678, 1_947, 0, 0, 489, "S.22.01.21 (image)"),
    "Macif Vie": ("K€", 1_801_400, 814_179, -15_636, 16_210, 0, 0, 474, "S.22.01.21 (image)"),
    "Predica": ("K€", 20_992_468, 10_178_708, -299_987, -59_405, 0, 0, 67, "S.22.01.21 (texte)"),
    "Prima": ("K€", 209_001, 90_366, -1_604, 692, 0, 0, 189, "S.22.01.21 (texte)"),
    "SGAM AG2R LA MONDIALE": ("K€", 10_005_273, 5_234_451, -92_431, 23_995, -408_393, 323, 128, "S.22.01.22 (texte)"),
    "Sogécap": ("€", 9_190_405_053, 4_259_413_627, -98_696_850, -36_004_653, 0, 0, 39, "S.22.01.21 (texte)"),
    "SwissLife Assurance et Patrimoine": ("K€", 2_703_042, 1_692_097, -56_652, 41_782, 0, 0, 104, "S.22.01.21 (texte)"),
    "VIASANTE Mutuelle": ("K€", 841_430, 240_414, -2_412, 619, 0, 0, 227, "S.22.01.21 (texte)"),
    # S.22.01 en image non retrouvé dans l'annexe ; impacts donnés dans le texte (E.1/E.2).
    "MAIF": ("K€", 5_329_707, 2_344_989, -28_945, 15_362, 0, 0, 105,
             "texte E.1 p.105 (fonds propres de base −28 945 K€) et E.2 p.106 (SCR +15 362 K€)"),
}
# Ratio sans VA publié dans le texte seulement (annexes QRT sans S.22.01).
RATIO_PUBLIE = {
    "Generali Vie": (152.0, 36, "RSSF p.36 (et p.9) : 198 % → 152 % sans volatility adjustment (−46 pts, VA stochastique du modèle interne)"),
    "Generali IARD": (141.0, 32, "RSSF p.32 : 153 % → 141 % sans volatility adjustment (−11 pts publiés, VA stochastique du modèle interne)"),
}
SANS_MESURE = {
    "Aesio Mutuelle": "aucun S.22.01 publié (pas de mesure de long terme)",
    "MMJ": "aucun S.22.01 publié (pas de mesure de long terme)",
    "MNPAF": "aucun S.22.01 publié (pas de mesure de long terme)",
    "Nuoma": "aucun S.22.01 publié (pas de mesure de long terme)",
    "Macifilia": "n'utilise pas la VA (rapport Aéma p.209), aucun S.22.01",
    "Themis": "n'utilise pas la VA (rapport Aéma p.188), aucun S.22.01",
    "MGEN": "aucun S.22.01 publié, aucune mention de VA ni de mesure transitoire",
    "MACSF prévoyance": "courbe « sans correction pour volatilité » (rapport p.40, p.45)",
}
DIVISEUR = {"K€": 1_000, "€": 1_000_000}


def main():
    conn = sqlite3.connect(DB)
    conn.execute("DROP TABLE IF EXISTS impact_mesures_lt")
    conn.execute("""CREATE TABLE impact_mesures_lt (
        company_id INTEGER NOT NULL REFERENCES companies(id), year INTEGER NOT NULL,
        utilise_va INTEGER NOT NULL, mesure_transitoire INTEGER NOT NULL,
        fp_avec REAL, scr_avec REAL,
        delta_fp_va REAL, delta_scr_va REAL,
        delta_fp_transitoires REAL, delta_scr_transitoires REAL,
        ratio_scr_sans_va_publie REAL,
        source_page INTEGER, source TEXT,
        PRIMARY KEY (company_id, year))""")
    ids = dict(conn.execute("SELECT name, id FROM companies"))
    vus = set()
    for nom, (u, fp, scr, dfv, dsv, dft, dst, page, src) in S2201.items():
        k = DIVISEUR[u]
        conn.execute("INSERT INTO impact_mesures_lt VALUES (?,?,1,?,?,?,?,?,?,?,NULL,?,?)",
                     (ids[nom], YEAR, int(bool(dft or dst)), fp / k, scr / k, dfv / k, dsv / k,
                      dft / k, dst / k, page, src))
        vus.add(nom)
    for nom, (ratio, page, src) in RATIO_PUBLIE.items():
        conn.execute("INSERT INTO impact_mesures_lt VALUES (?,?,1,0,NULL,NULL,NULL,NULL,0,0,?,?,?)",
                     (ids[nom], YEAR, ratio, page, src))
        vus.add(nom)
    for nom, src in SANS_MESURE.items():
        conn.execute("INSERT INTO impact_mesures_lt VALUES (?,?,0,0,NULL,NULL,0,0,0,0,NULL,NULL,?)",
                     (ids[nom], YEAR, src))
        vus.add(nom)
    manquants = set(ids) - vus
    assert not manquants, f"sociétés sans donnée S.22.01 : {sorted(manquants)}"

    # Contrôle : C0010 = valeurs de kpis (même extraction, autre état QRT).
    ecarts = conn.execute("""
        SELECT c.name, i.fp_avec, f.value, i.scr_avec, s.value FROM impact_mesures_lt i
        JOIN companies c ON c.id = i.company_id
        JOIN kpis f ON f.company_id = i.company_id AND f.year = i.year AND f.kpi_name = 'fonds_propres_eligibles'
        JOIN kpis s ON s.company_id = i.company_id AND s.year = i.year AND s.kpi_name = 'scr_total'
        WHERE i.fp_avec IS NOT NULL AND (ABS(i.fp_avec - f.value) > 0.01 OR ABS(i.scr_avec - s.value) > 0.01)""").fetchall()
    assert not ecarts, f"S.22.01 C0010 ≠ kpis : {ecarts}"
    conn.commit()
    n_va = conn.execute("SELECT COUNT(*) FROM impact_mesures_lt WHERE utilise_va = 1").fetchone()[0]
    n_tr = conn.execute("SELECT COUNT(*) FROM impact_mesures_lt WHERE mesure_transitoire = 1").fetchone()[0]
    print(f"impact_mesures_lt : {len(vus)} sociétés, {n_va} utilisent la VA, {n_tr} une mesure transitoire")
    conn.close()


if __name__ == "__main__":
    main()
