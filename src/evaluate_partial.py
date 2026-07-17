"""Évaluation partielle : Solvabilité II (7) + comparatives (3) + pièges
'mauvaise norme' (2) = 12 questions, comparées en mode="dense" vs
mode="hybrid_rerank". Utilise le même golden_set.py que evaluate.py.
"""
from rag import poser_question
from golden_set import GOLDEN

# les 2 pièges "mauvaise norme" n'ont pas de champ dédié dans golden_set.py
# (REFUSE générique, norme=None) — identifiés par leur texte, cf. commentaires
# dans golden_set.py juste au-dessus de ces deux entrées.
MAUVAISE_NORME = {
    "Quelle est la formule du ratio combiné selon IFRS 17 ?",
    "Selon quelle méthode IFRS 17 calcule-t-il le minimum de capital requis (MCR) ?",
}

SUBSET = [
    c for c in GOLDEN
    if c["norme"] in ("Solvabilité II", "IFRS 17 & Solvabilité II")
    or c["q"] in MAUVAISE_NORME
]


def run(mode, k=5):
    results = []
    for c in SUBSET:
        r = poser_question(c["q"], k=k, mode=mode, verbose=False)
        refus = r.strip().lower().startswith("je ne trouve pas")
        ok = refus if c["a"] == "REFUSE" else (not refus and any(m in r.lower() for m in c["m"]))
        results.append(ok)
    return results


def main():
    print(f"{len(SUBSET)} questions dans le sous-ensemble "
          f"(Solvabilité II: {sum(1 for c in SUBSET if c['norme']=='Solvabilité II')}, "
          f"comparatives: {sum(1 for c in SUBSET if c['norme']=='IFRS 17 & Solvabilité II')}, "
          f"mauvaise norme: {sum(1 for c in SUBSET if c['q'] in MAUVAISE_NORME)})\n")

    dense = run("dense")
    hybrid = run("hybrid_rerank")

    print("| # | Question | PASS/FAIL dense | PASS/FAIL hybrid | delta |")
    print("|---|---|---|---|---|")
    for i, (c, d, h) in enumerate(zip(SUBSET, dense, hybrid), 1):
        d_s = "PASS" if d else "FAIL"
        h_s = "PASS" if h else "FAIL"
        if d == h:
            delta = "="
        elif h and not d:
            delta = "+ (hybrid corrige)"
        else:
            delta = "- (hybrid casse)"
        print(f"| {i} | {c['q'][:60]} | {d_s} | {h_s} | {delta} |")

    print(f"\nTOTAL dense  : {sum(dense)}/{len(SUBSET)}")
    print(f"TOTAL hybrid : {sum(hybrid)}/{len(SUBSET)}")


if __name__ == "__main__":
    main()
