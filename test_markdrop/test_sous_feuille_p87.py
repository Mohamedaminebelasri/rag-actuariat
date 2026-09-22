import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingest import classify_pages, resoudre_sous_feuille, BASE_DIR

PDF = Path(r"C:\Users\PC\Documents\rag-actuariat\data\SFCR_2025_Groupe-Groupama.pdf")

classification = classify_pages(PDF)
page87 = next(p for p in classification if p["page"] == 87)
print("page 87 classification:", {k: v for k, v in page87.items() if k != "texte"})
print("n_caracteres:", page87["n_caracteres"])

with open(BASE_DIR / "output_sectionE_QRT" / "qrt_dictionary.json", encoding="utf-8") as f:
    qrt_dict = json.load(f)

template_id = page87["template_id"]
print("template_id:", template_id)
print("sous-feuilles connues pour ce template_id:", list(qrt_dict.get(template_id, {}).keys()))

candidats = resoudre_sous_feuille(page87, template_id, qrt_dict)
print(f"\n{len(candidats)} candidat(s) retourné(s):")
for sheet_key, methode, override in candidats:
    print(f"  - sheet_key={sheet_key!r}")
    print(f"    methode={methode!r}")
    print(f"    override={'oui (fusionné)' if override is not None else 'non'}")
