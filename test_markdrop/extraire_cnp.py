import asyncio
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from ingest import process_qrt, BASE_DIR
import fitz

PDF = Path(r"C:\Users\PC\Documents\rag-actuariat\data\sfcr_cnp_assurances_2025.pdf")
WORK_DIR = BASE_DIR / "output_cnp"
WORK_DIR.mkdir(exist_ok=True)
CORPUS_PATH = WORK_DIR / "corpus_final.json"

# Pages QRT réelles (vérifiées manuellement, cf. Décision 059 — classify_pages()
# rate les pages de continuation sans code répété : 84/87/96/99, et donne un
# faux positif page 76 — mention narrative de "S.23.01.01", pas une vraie table).
PAGES_QRT_CNP = [
    (83, "S.02.01.02"), (84, "S.02.01.02"),
    (86, "S.05.01.02"), (87, "S.05.01.02"),
    (95, "S.23.01.01"), (96, "S.23.01.01"),
    (97, "S.25.01.21"),
    (98, "S.28.02.01"), (99, "S.28.02.01"),
]


async def main():
    t0 = time.time()
    doc = fitz.open(str(PDF))
    pages_qrt = []
    for num, template_id in PAGES_QRT_CNP:
        texte = doc[num - 1].get_text()
        pages_qrt.append({"page": num, "template_id": template_id, "n_caracteres": len(texte), "texte": texte})
    doc.close()

    with open(Path(__file__).parent / "qrt_dictionary_cnp.json", encoding="utf-8") as f:
        qrt_dict = json.load(f)

    elements, anomalies, t_qrt = await process_qrt(PDF, pages_qrt, qrt_dict, WORK_DIR)
    print(f"[qrt CNP] {len(elements)} element(s) en {t_qrt:.1f}s (total {time.time()-t0:.1f}s)")
    for e in elements:
        c = e["contenu"]
        n = len(c.get("lignes", c.get("entites", [])))
        print(f"  - {e['template_id']} (page {e['page_source']}) : {n} lignes, methode={c.get('methode_extraction')}")

    print("\nAnomalies:")
    print(json.dumps(anomalies, ensure_ascii=False, indent=2)[:3000])

    with open(CORPUS_PATH, "w", encoding="utf-8") as f:
        json.dump({"metadata": {"entite": "CNP Assurances", "annee": 2025}, "elements": elements}, f,
                   ensure_ascii=False, indent=2)
    print(f"\n{CORPUS_PATH} ecrit : {len(elements)} elements")


if __name__ == "__main__":
    asyncio.run(main())
