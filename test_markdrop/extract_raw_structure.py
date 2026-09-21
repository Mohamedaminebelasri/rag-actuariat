# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier lit le PDF du rapport avec l'outil d'extraction (Docling) et
# en sort la structure brute : titres, paragraphes, tableaux, images.
# C'est la toute première étape avant que le système puisse répondre à
# une question.
# ------------------------------------------------------------------
"""extract_raw_structure.py — Extraction de la structure BRUTE d'un
DoclingDocument (titres, paragraphes, listes, tableaux, images), dans
l'ordre de lecture réel du document.

    python extract_raw_structure.py [fichier.pdf] [dossier_sortie]

Étape volontairement isolée du découpage en chunks : on regarde d'abord
ce que Docling voit réellement, sans rien regrouper ni corriger, pour
juger ensuite si les niveaux de titre devinés (H1/H2/H3...) sont
exploitables tels quels.

Point clé : on parcourt l'arbre `body` du DoclingDocument via
document.iterate_items(), PAS la liste plate doc.texts — iterate_items()
descend récursivement dans les enfants de chaque noeud (children,
résolus via RefItem.resolve()) dans l'ordre où ils apparaissent dans le
document, donc un tableau ou une image intercalé au milieu d'une section
sort à sa vraie place dans le flux, pas regroupé à part par type comme le
ferait un simple parcours de doc.texts + doc.tables + doc.pictures.

Ne regroupe pas en sections (étape suivante du pipeline). Ne corrige
aucun niveau de titre deviné par Docling (attribut .level des
SectionHeaderItem) : la sortie doit rester brute pour pouvoir juger de sa
fiabilité avant de bâtir quoi que ce soit dessus.
"""

import argparse
import json
from collections import Counter
from pathlib import Path

from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions, TableFormerMode
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling_core.types.doc.document import PictureItem, SectionHeaderItem, TableItem

BASE_DIR = Path(__file__).parent

# Labels traités comme des "titres" pour le signal de titres consécutifs
# (sanity-check) : le titre unique du document (TITLE) et les en-têtes de
# section (SECTION_HEADER, H1..Hn). Le niveau H1/H2/H3 lui-même n'est lu
# que sur les items qui sont réellement des SectionHeaderItem (attribut
# .level) — TITLE n'a pas de niveau, ce n'est pas supposé ici.
LABELS_TITRE = {"title", "section_header"}

# Longueur de l'extrait de texte conservé pour les items textuels (titres,
# paragraphes, listes...). Pour les tableaux/images, aucun extrait de
# contenu n'est gardé ici — juste une référence (self_ref) : leur contenu
# détaillé est du ressort d'un index séparé dans le pipeline global.
LONGUEUR_EXTRAIT = 100


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "input_pdf", nargs="?",
        default=str(BASE_DIR.parent / "data" / "SFCR_2025_Groupe-Groupama.pdf"),
        help="PDF source à convertir (chemin du document réglementaire, ex. SFCR)",
    )
    p.add_argument(
        "output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"),
        help="Dossier de sortie (reçoit structure_brute.json)",
    )
    return p.parse_args()


def convertir_document(pdf_path):
    """Convertit le PDF en DoclingDocument. Mêmes options que le reste du
    pipeline (TableFormer ACCURATE, modèles locaux déjà téléchargés dans
    docling-models/ pour contourner le problème de symlinks Windows) —
    do_table_structure reste activé même si le contenu détaillé des
    tableaux n'est pas exploité ici, sinon Docling risque de ne pas les
    identifier correctement comme TableItem dans l'arbre body."""
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.mode = TableFormerMode.ACCURATE
    pipeline_options.artifacts_path = BASE_DIR / "docling-models"

    doc_converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    conv_res = doc_converter.convert(str(pdf_path))
    return conv_res.document


def extraire_structure_brute(document):
    """Parcourt l'arbre `body` du DoclingDocument dans l'ordre de lecture
    réel (document.iterate_items(), pas doc.texts à plat) et retourne une
    liste d'objets, un par item rencontré, dans cet ordre. Ne regroupe
    rien en sections, ne corrige aucun niveau de titre."""
    items = []

    for position, (item, _profondeur_arbre) in enumerate(document.iterate_items()):
        # item.label est un DocItemLabel (enum str) : 'title',
        # 'section_header', 'text', 'paragraph', 'list_item', 'table',
        # 'picture', 'caption', 'page_header', 'page_footer', etc.
        type_item = item.label.value if hasattr(item.label, "value") else str(item.label)

        # item.prov : liste de ProvenanceItem (un par page couverte par cet
        # item — presque toujours une seule, mais on ne suppose pas).
        pages = sorted({prov.page_no for prov in item.prov}) if item.prov else []

        # Le niveau hiérarchique (H1=1, H2=2...) n'existe QUE sur les
        # SectionHeaderItem — on vérifie le type réel de l'item, pas le
        # label seul, pour ne jamais inventer un niveau qui n'existe pas
        # (ex. sur TITLE, qui n'a pas cet attribut).
        niveau = item.level if isinstance(item, SectionHeaderItem) else None

        if isinstance(item, (TableItem, PictureItem)):
            # Pas de contenu détaillé ici, volontairement : un index séparé
            # du pipeline global s'occupe des tableaux/images. On garde
            # juste de quoi les retrouver et les recroiser plus tard.
            extrait = None
            reference = item.self_ref
        else:
            texte = getattr(item, "text", "") or ""
            extrait = texte[:LONGUEUR_EXTRAIT]
            reference = item.self_ref

        items.append({
            "position": position,
            "type": type_item,
            "niveau": niveau,
            "pages": pages,
            "extrait": extrait,
            "self_ref": reference,
        })

    return items


def sanity_check(items):
    """Résumé de contrôle affiché en console : comptage par type, comptage
    des titres par niveau, et repérage des titres consécutifs sans aucun
    contenu entre eux. C'est un signal simple à vérifier manuellement, pas
    une détection d'anomalie aboutie — ne tranche rien automatiquement."""
    print("=" * 70)
    print("SANITY-CHECK — structure brute")
    print("=" * 70)

    compte_types = Counter(it["type"] for it in items)
    print(f"\n{len(items)} items au total, par type :")
    for type_, n in compte_types.most_common():
        print(f"  {type_:20} {n}")

    compte_niveaux = Counter(it["niveau"] for it in items if it["niveau"] is not None)
    n_section_header = sum(compte_niveaux.values())
    print(f"\nTitres SECTION_HEADER par niveau ({n_section_header} au total) :")
    for niveau, n in sorted(compte_niveaux.items()):
        print(f"  H{niveau} : {n}")
    n_title = sum(1 for it in items if it["type"] == "title")
    print(f"  TITLE (pas de niveau, titre unique du document) : {n_title}")

    print("\nTitres consécutifs sans aucun contenu entre eux "
          "(signal à vérifier manuellement, pas une conclusion) :")
    n_signales = 0
    for i in range(len(items) - 1):
        if items[i]["type"] in LABELS_TITRE and items[i + 1]["type"] in LABELS_TITRE:
            n_signales += 1
            a, b = items[i], items[i + 1]
            suffixe_a = f" H{a['niveau']}" if a["niveau"] is not None else ""
            suffixe_b = f" H{b['niveau']}" if b["niveau"] is not None else ""
            print(f"  position {a['position']} [{a['type']}{suffixe_a}]"
                  f" p.{a['pages']} « {a['extrait']!r} »")
            print(f"    -> directement suivi de position {b['position']} "
                  f"[{b['type']}{suffixe_b}]"
                  f" p.{b['pages']} « {b['extrait']!r} »")
    if n_signales == 0:
        print("  aucun cas détecté")
    else:
        print(f"\n  -> {n_signales} cas signalé(s)")


def main():
    args = parse_cli()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[conversion] {args.input_pdf} ...")
    document = convertir_document(args.input_pdf)

    items = extraire_structure_brute(document)

    out_path = output_dir / "structure_brute.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    print(f"[export] {len(items)} items écrits dans {out_path}")

    sanity_check(items)


if __name__ == "__main__":
    main()
