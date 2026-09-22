# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier fait la même chose que les deux précédents, mais pour le
# rapport de l'année 2024, en une seule fois pour ne pas relire deux fois
# un PDF de plusieurs centaines de pages.
# ------------------------------------------------------------------
"""convertir_2024_une_fois.py — Convertit SFCR_2024_Groupe-Groupama.pdf
UNE SEULE FOIS (ACCURATE, >10 min attendu) et produit à la fois
docling_document_complet.json (rôle de save_docling_document.py) et
structure_brute.json (rôle de extract_raw_structure.py) dans
output_structure_brute_2024/ — sans reconvertir deux fois comme le
ferait l'enchaînement séparé des 2 scripts d'origine. Réutilise
convertir_document/extraire_structure_brute/sanity_check TELLES QUELLES
(pas de logique de conversion dupliquée)."""
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from extract_raw_structure import convertir_document, extraire_structure_brute, sanity_check
import json

BASE_DIR = Path(__file__).parent
INPUT_PDF = BASE_DIR.parent / "data" / "SFCR_2024_Groupe-Groupama.pdf"
OUTPUT_DIR = BASE_DIR / "output_structure_brute_2024"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"[conversion] {INPUT_PDF} ... (>10 min attendu, ACCURATE)")
document = convertir_document(INPUT_PDF)

docling_path = OUTPUT_DIR / "docling_document_complet.json"
document.save_as_json(docling_path)
print(f"[sauvegarde] DoclingDocument complet écrit dans {docling_path}")
print(f"  texts={len(document.texts)}  tables={len(document.tables)}  pictures={len(document.pictures)}")

items = extraire_structure_brute(document)
structure_path = OUTPUT_DIR / "structure_brute.json"
with open(structure_path, "w", encoding="utf-8") as f:
    json.dump(items, f, ensure_ascii=False, indent=2)
print(f"[export] {len(items)} items écrits dans {structure_path}")

sanity_check(items)
