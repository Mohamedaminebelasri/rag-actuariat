import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingest import process_qrt, BASE_DIR
import fitz

PDF = Path(r"C:\Users\PC\Documents\rag-actuariat\data\RAPPORT_SFCR_MACSF_prevoyance_2025.pdf")
WORK_DIR = BASE_DIR / "output_macsf"
WORK_DIR.mkdir(exist_ok=True)
CORPUS_PATH = WORK_DIR / "corpus_final.json"

PAGES_QRT_MACSF = [
    (54, "S.02.01.02"), (55, "S.02.01.02"),
    (56, "S.05.01.02"), (57, "S.05.01.02"), (58, "S.05.01.02"),
    (61, "S.23.01.01"),
    (62, "S.25.01.21"),
    (63, "S.28.01.01"),
]


async def main():
    t0 = time.time()
    doc = fitz.open(str(PDF))
    pages_qrt = []
    for num, template_id in PAGES_QRT_MACSF:
        texte = doc[num - 1].get_text()
        pages_qrt.append({"page": num, "template_id": template_id, "n_caracteres": len(texte), "texte": texte})
    doc.close()

    with open(Path(__file__).parent / "qrt_dictionary_macsf.json", encoding="utf-8") as f:
        qrt_dict = json.load(f)

    elements, anomalies, t_qrt = await process_qrt(PDF, pages_qrt, qrt_dict, WORK_DIR)
    print(f"[qrt MACSF] {len(elements)} element(s) en {t_qrt:.1f}s (total {time.time()-t0:.1f}s)")
    for e in elements:
        c = e["contenu"]
        n = len(c.get("lignes", c.get("entites", [])))
        print(f"  - {e['template_id']} (page {e['page_source']}) : {n} lignes")

    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump({"metadata": {"entite": "MACSF prévoyance", "annee": 2025}, "elements": elements}, f,
                   ensure_ascii=False, indent=2)
    print(f"\n{CORPUS_PATH} ecrit : {len(elements)} elements")


if __name__ == "__main__":
    asyncio.run(main())
