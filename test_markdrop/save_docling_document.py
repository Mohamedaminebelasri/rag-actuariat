# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier lance la lecture complète du PDF une seule fois et sauvegarde
# le résultat brut, pour ne jamais avoir à relire tout le PDF depuis le
# début si une étape suivante doit être refaite.
# ------------------------------------------------------------------
"""save_docling_document.py — Reconvertit le PDF UNE SEULE FOIS et
sauvegarde IMMÉDIATEMENT le DoclingDocument complet via save_as_json(),
avant tout autre traitement — pour ne plus jamais avoir à reconvertir.

Réutilise convertir_document() d'extract_raw_structure.py telle quelle
(mêmes options TableFormer ACCURATE / modèles locaux), pas de logique de
conversion dupliquée — pour garantir que ce document est bien identique
à celui du run initial (mêmes 23 tables / 96 pictures attendus).

    python save_docling_document.py [fichier.pdf] [dossier_sortie]
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from extract_raw_structure import convertir_document, parse_cli


def main():
    args = parse_cli()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[conversion] {args.input_pdf} ... (>10 min attendu)")
    document = convertir_document(args.input_pdf)

    out_path = output_dir / "docling_document_complet.json"
    document.save_as_json(out_path)

    print(f"[sauvegarde] DoclingDocument complet écrit dans {out_path}")
    print(f"  texts={len(document.texts)}  tables={len(document.tables)}  "
          f"pictures={len(document.pictures)}")


if __name__ == "__main__":
    main()
