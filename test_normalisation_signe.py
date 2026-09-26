# -*- coding: utf-8 -*-
"""test_normalisation_signe.py — Décision 091 : tests unitaires de la
détection générale du "bug de signe détaché" (NUMERIC_FRAGMENT_RE dans
ingest.py + _vers_float dans extract_kpis.py) — à lancer AVANT toute
extraction réelle, conformément à la consigne "teste-la unitairement sur
des exemples de chaque variante avant de l'intégrer".

Couvre :
1. Les 2 variantes réellement rencontrées dans le pipeline extract_qrt_native
   (Predica = parenthèses, MGEN = espace Unicode invisible).
2. Non-régression : tous les formats déjà gérés avant Décision 091 doivent
   continuer à donner EXACTEMENT le même résultat.
3. Faux positifs : du texte non-numérique ne doit jamais matcher.

    python test_normalisation_signe.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent / "test_markdrop"))

from extract_kpis import _vers_float  # noqa: E402
from ingest import NUMERIC_FRAGMENT_RE  # noqa: E402
from extract_qrt_s23 import merge_numeric_fragments  # noqa: E402

echecs = []


def verifier(nom, condition):
    statut = "OK" if condition else "ÉCHEC"
    if not condition:
        echecs.append(nom)
    print(f"  [{statut}] {nom}")


print("=" * 90)
print("1. NUMERIC_FRAGMENT_RE — les fragments décorés doivent être RECONNUS")
print("=" * 90)
verifier('match "-\\u2009452" (MGEN, signe+espace fine+chiffres)', bool(NUMERIC_FRAGMENT_RE.match("- 452")))
verifier('match "(10" (Predica, fragment ouvrant)', bool(NUMERIC_FRAGMENT_RE.match("(10")))
verifier('match "550)" (Predica, fragment fermant)', bool(NUMERIC_FRAGMENT_RE.match("550)")))
verifier('match "(196476)" (parenthèse complète, un seul mot)', bool(NUMERIC_FRAGMENT_RE.match("(196476)")))
verifier('match "-\\u00a0452" (espace insécable)', bool(NUMERIC_FRAGMENT_RE.match("- 452")))

print("\n" + "=" * 90)
print("2. NUMERIC_FRAGMENT_RE — pas de faux positif sur du texte non-numérique")
print("=" * 90)
verifier('rejette "(Diversification"', not NUMERIC_FRAGMENT_RE.match("(Diversification"))
verifier('rejette "année)"', not NUMERIC_FRAGMENT_RE.match("année)"))
verifier('rejette "-vie" (signe collé à du texte, pas un chiffre)', not NUMERIC_FRAGMENT_RE.match("-vie"))
verifier('rejette "(" seul (aucun chiffre)', not NUMERIC_FRAGMENT_RE.match("("))
verifier('rejette ")" seul (aucun chiffre)', not NUMERIC_FRAGMENT_RE.match(")"))

print("\n" + "=" * 90)
print("3. NUMERIC_FRAGMENT_RE — non-régression sur les formats déjà gérés")
print("=" * 90)
verifier('match "2160259" (entier simple)', bool(NUMERIC_FRAGMENT_RE.match("2160259")))
verifier('match "2,74" (décimal virgule)', bool(NUMERIC_FRAGMENT_RE.match("2,74")))
verifier('match "521%" (pourcentage collé)', bool(NUMERIC_FRAGMENT_RE.match("521%")))
verifier('match "%" seul', bool(NUMERIC_FRAGMENT_RE.match("%")))
verifier('match "-" seul (tiret EIOPA)', bool(NUMERIC_FRAGMENT_RE.match("-")))
verifier('match "-14137" (négatif collé, déjà géré)', bool(NUMERIC_FRAGMENT_RE.match("-14137")))

print("\n" + "=" * 90)
print("4. Bout en bout — merge_numeric_fragments + _vers_float reproduisent le fix réel")
print("=" * 90)
# Simule les fragments PyMuPDF réels de chaque cas déjà documenté (x0, x1, texte).
predica_frags = [(0.0, 5.0, "(10"), (6.0, 11.0, "475"), (12.0, 18.0, "550)")]
merged = merge_numeric_fragments(predica_frags)
valeur = _vers_float(merged[0][1])
verifier(f"Predica bout en bout : (10 475 550) -> {valeur} == -10475550.0", valeur == -10475550.0)

mgen_frags = [(0.0, 6.0, "- 452"), (7.0, 11.0, "163")]
merged = merge_numeric_fragments(mgen_frags)
valeur = _vers_float(merged[0][1])
verifier(f"MGEN bout en bout : -\\u2009452 163 -> {valeur} == -452163.0", valeur == -452163.0)

macsf_frag = [(0.0, 8.0, "(196476)")]
merged = merge_numeric_fragments(macsf_frag)
valeur = _vers_float(merged[0][1])
verifier(f"Parenthèse complète 1 mot : (196476) -> {valeur} == -196476.0", valeur == -196476.0)

print("\n" + "=" * 90)
print("5. _vers_float — non-régression sur les formats déjà gérés (valeur ET signe identiques)")
print("=" * 90)
verifier('_vers_float("2160259") == 2160259.0', _vers_float("2160259") == 2160259.0)
verifier('_vers_float("2,74") == 2.74', _vers_float("2,74") == 2.74)
verifier('_vers_float("521%") == 5.21', _vers_float("521%") == 5.21)
verifier('_vers_float("-") == 0.0', _vers_float("-") == 0.0)
verifier('_vers_float("-14137") == -14137.0', _vers_float("-14137") == -14137.0)
verifier('_vers_float(1234.5) == 1234.5 (float natif JSON)', _vers_float(1234.5) == 1234.5)
verifier('_vers_float("1 234 567") == 1234567.0 (espaces milliers ASCII)', _vers_float("1 234 567") == 1234567.0)

print("\n" + "=" * 90)
if echecs:
    print(f"ÉCHEC — {len(echecs)} test(s) en échec : {echecs}")
    sys.exit(1)
else:
    print("TOUS LES TESTS PASSENT.")
