import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingest import classify_pages, process_qrt, BASE_DIR

PDF = Path(r"C:\Users\PC\Documents\rag-actuariat\data\SFCR_2025_Groupe-Groupama.pdf")
CORPUS_PATH = BASE_DIR / "output_structure_brute" / "corpus_final.json"
WORK_DIR = BASE_DIR / "output_structure_brute"


async def main():
    classification = classify_pages(PDF)
    page87 = next(p for p in classification if p["page"] == 87)

    with open(BASE_DIR / "output_sectionE_QRT" / "qrt_dictionary.json", encoding="utf-8") as f:
        qrt_dict = json.load(f)

    elements, anomalies, t_qrt = await process_qrt(PDF, [page87], qrt_dict, WORK_DIR)
    print(f"[qrt page 87] {len(elements)} element(s) en {t_qrt:.1f}s")
    for e in elements:
        c = e["contenu"]
        n = len(c.get("lignes", c.get("entites", [])))
        print(f"  - {e['template_id']} (page {e['page_source']}) : {n} lignes, methode={c.get('methode_extraction')}")

    print("\nAnomalies:")
    print(json.dumps(anomalies, ensure_ascii=False, indent=2))

    with open(CORPUS_PATH, encoding="utf-8") as f:
        data = json.load(f)
    els = data["elements"] if isinstance(data, dict) else data

    els_sans_p87 = [e for e in els if e.get("page_source") != 87]
    nouveaux = els_sans_p87 + elements
    if isinstance(data, dict):
        data["elements"] = nouveaux
    else:
        data = nouveaux

    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\ncorpus_final.json mis a jour : {len(nouveaux)} elements (page 87 remplacee par {len(elements)} nouveaux)")


if __name__ == "__main__":
    asyncio.run(main())
