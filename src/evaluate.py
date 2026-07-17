import unicodedata
from rag import poser_question
from golden_set import GOLDEN

def _fold(text):
    """minuscule + accents retirés, pour un matching de mots-clés robuste."""
    text = unicodedata.normalize("NFKD", text)
    return "".join(c for c in text if not unicodedata.combining(c)).lower()

def evaluer(k=5):
    res = []
    for i, c in enumerate(GOLDEN, 1):
        r = poser_question(c["q"], k=k, verbose=False)
        refus = r.strip().lower().startswith("je ne trouve pas")
        ok = refus if c["a"] == "REFUSE" else (not refus and any(_fold(m) in _fold(r) for m in c["m"]))
        res.append(ok)
        print(f"[{i:2}] {'PASS' if ok else 'FAIL'}  {c['a']:<7} {c['q'][:48]}")

    val = [r for r, c in zip(res, GOLDEN) if c["a"] == "TROUVE"]
    pie = [r for r, c in zip(res, GOLDEN) if c["a"] == "REFUSE"]
    print(f"\nRappel     : {sum(val)}/{len(val)}")
    print(f"Robustesse : {sum(pie)}/{len(pie)}   ← doit être 100%")
    print(f"TOTAL      : {sum(res)}/{len(res)}")
    return res

if __name__ == "__main__":
    evaluer()