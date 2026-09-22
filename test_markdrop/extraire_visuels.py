# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier sauvegarde, sous forme d'images, les tableaux et images qui
# apparaissent dans le rapport, pour qu'ils puissent être montrés tels
# quels dans une réponse.
# ------------------------------------------------------------------
"""extraire_visuels.py — Étape 3 + 4 : extrait et sauvegarde les fichiers
visuels réels (tableaux, images, pages QRT complètes), avec
déduplication par pHash sur les images.

⚠️ VÉRIFIÉ AVANT D'ÉCRIRE CE SCRIPT (pas supposé) : docling_document_
complet.json a été sauvegardé SANS generate_page_images/
generate_picture_images (cf. extract_raw_structure.convertir_document) —
`doc.pages[n].image` est None et `item.get_image(doc)` retourne None pour
tout le document. Reconvertir le PDF pour obtenir ces pixels aurait coûté
>10 minutes et risqué une renumérotation des self_ref (cf. la règle du
projet : jamais de reconversion sans confirmation explicite). ÉVITÉ
entièrement : chaque item Docling porte déjà son bbox (prov[0].bbox,
coord_origin BOTTOMLEFT) et le numéro de page — on ouvre directement le
PDF SOURCE (jamais reconverti) via PyMuPDF et on découpe nous-mêmes la
région exacte, sans passer par get_image(). Rotation des pages QRT :
réutilise detect_rotation_needed (ingest.py), déjà validé sur ce document,
pas réécrite.

Zones (PAGE_MIN_QRT = 77, identique à build_sections.py) :
- Pages < 77 (narratif) : un crop PNG par TableItem et par PictureItem,
  nommé depuis son self_ref (chemins_visuels.py) — les tableaux gardent
  EN PLUS leur représentation texte déjà utilisée pour l'embedding texte
  (ce script ne la touche pas, n'écrit que l'image).
- Pages >= 77 (QRT) : un rendu PLEINE PAGE par page (pas de crop par
  tableau) — l'embedding multimodal QRT se fera au niveau de la page.

Déduplication (pHash, bibliothèque déjà utilisée par dedup.py) :
appliquée UNIQUEMENT aux images (PictureItem) narratives — logos/éléments
décoratifs répétés, le cas déjà observé par dedup.py. Ni les tableaux ni
les pages QRT n'ont de raison d'être visuellement dupliqués. Seuil de
distance de Hamming FIXE (SEUIL_DEDUP_PHASH), pas de détection dynamique
du "plus grand saut" comme dans dedup.py (ce script traite le document
entier en une passe, pas un sous-ensemble de 16 images à inspecter à la
main) — à revalider si le taux de doublons détectés semble anormal.

Ne modifie jamais docling_document_complet.json ni le PDF source
(lecture seule sur les deux).

    python extraire_visuels.py [docling_document_complet.json] [pdf_source] [annee]
"""

import argparse
import json
import sys
from io import BytesIO
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import fitz  # PyMuPDF — déjà une dépendance du projet (ingest.py)
import imagehash  # déjà une dépendance du projet (dedup.py)
from PIL import Image

# docling_core DOIT être importé AVANT ingest : ingest importe
# indirectement markdrop (via extract_qrt_s05_gemini), qui mocke
# docling_core.types au moment de son propre import si docling_core n'a
# pas encore été chargé — piège déjà rencontré et documenté plus tôt
# dans ce projet (cf. build_leaf_chunks.py et consorts, qui importent
# toujours docling_core en premier pour la même raison).
from docling_core.types.doc.document import DoclingDocument

import chemins_visuels as cv
from ingest import RASTER_ZOOM, detect_rotation_needed  # réutilisées telles quelles, pas réécrites

BASE_DIR = Path(__file__).parent

# Échelle de rendu pour les crops tableau/image — alignée sur la
# convention déjà utilisée par build_final.py (images_scale = 2.0), pas
# sur RASTER_ZOOM=4.0 (réservée aux pages QRT pleines, où ingest.py s'en
# sert déjà) : un crop de tableau n'a pas besoin de la même résolution
# qu'une page entière à lire finement.
ECHELLE_CROP = 2.0

# Seuil de distance de Hamming (pHash) en dessous duquel 2 images sont
# considérées comme le même visuel — cf. note dans le docstring du
# module sur pourquoi ce seuil est FIXE ici (pas dynamique comme dans
# dedup.py). Valeur de départ raisonnable (imagehash.phash produit des
# hash de 64 bits ; <=5 bits différents = quasi-identique), à ajuster si
# le résultat sur ce document s'avère trop/pas assez agressif.
SEUIL_DEDUP_PHASH = 5


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("docling_document_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "docling_document_complet.json"))
    p.add_argument("pdf_source", nargs="?",
                    default=str(BASE_DIR.parent / "data" / "SFCR_2025_Groupe-Groupama.pdf"))
    p.add_argument("annee", nargs="?", type=int, default=2025)
    return p.parse_args()


def rect_depuis_bbox(bbox, hauteur_page):
    """Convertit un bbox Docling (coord_origin quelconque) en
    fitz.Rect (origine haut-gauche, requis par PyMuPDF) — réutilise
    to_top_left_origin du bbox lui-même plutôt que recalculer la
    conversion à la main."""
    b = bbox.to_top_left_origin(hauteur_page)
    return fitz.Rect(b.l, b.t, b.r, b.b)


def extraire_crop(page_fitz, rect, echelle):
    """Découpe et rend la région `rect` (en points PDF) de `page_fitz` à
    l'échelle donnée, retourne une image PIL — sans jamais passer par
    Docling.get_image() (indisponible, cf. docstring du module)."""
    mat = fitz.Matrix(echelle, echelle)
    pix = page_fitz.get_pixmap(matrix=mat, clip=rect)
    return Image.open(BytesIO(pix.tobytes("png")))


def rendre_page_qrt(doc_fitz, page_index):
    """Rendu PLEINE PAGE avec détection de rotation — EXACTEMENT la même
    logique que extract_qrt_gemini (ingest.py), extraite pour être
    réutilisable indépendamment de l'appel à Gemini."""
    page = doc_fitz[page_index]
    rotation_appliquee = detect_rotation_needed(doc_fitz, page_index)
    mat = fitz.Matrix(RASTER_ZOOM, RASTER_ZOOM)
    pix = page.get_pixmap(matrix=mat)
    image = Image.open(BytesIO(pix.tobytes("png")))
    if rotation_appliquee:
        image = image.rotate(90, expand=True)
    return image


def main():
    args = parse_cli()

    doc = DoclingDocument.load_from_json(args.docling_document_json)
    doc_fitz = fitz.open(args.pdf_source)

    racine_annee = cv.RACINE_VISUELS / str(args.annee)
    dossiers = {
        "tables": racine_annee / "tables",
        "images": racine_annee / "images",
        "qrt_pages": racine_annee / "qrt_pages",
    }
    for d in dossiers.values():
        d.mkdir(parents=True, exist_ok=True)

    # --- 1. Tableaux narratifs (page < PAGE_MIN_QRT) : crop + sauvegarde.
    # La représentation texte structurée existante (export_to_dataframe,
    # déjà utilisée pour l'embedding texte) n'est pas touchée — ce script
    # ajoute seulement l'image, il ne remplace rien. ---
    n_tables_sauvees, n_tables_qrt_ignorees = 0, 0
    for table in doc.tables:
        prov = table.prov[0]
        if prov.page_no >= cv.PAGE_MIN_QRT:
            n_tables_qrt_ignorees += 1  # couvert par le rendu pleine page QRT, pas de crop ici
            continue
        page_fitz = doc_fitz[prov.page_no - 1]  # fitz est 0-indexé, page_no Docling est 1-indexé
        rect = rect_depuis_bbox(prov.bbox, doc.pages[prov.page_no].size.height)
        image = extraire_crop(page_fitz, rect, ECHELLE_CROP)
        chemin_rel = cv.chemin_relatif_table_ou_image(table.self_ref, args.annee)
        image.save(cv.chemin_absolu(chemin_rel), "PNG")
        n_tables_sauvees += 1

    print(f"[tables] {n_tables_sauvees} crop(s) sauvegardé(s), "
          f"{n_tables_qrt_ignorees} table(s) en zone QRT ignorée(s) (couvertes par le rendu pleine page)")

    # --- 2. Images narratives (page < PAGE_MIN_QRT) : crop, pHash, puis
    # déduplication AVANT sauvegarde (on ne sauvegarde jamais 2 fois le
    # même visuel). ---
    images_a_traiter = []  # (picture, image_pil, hash)
    n_pict_qrt_ignorees = 0
    for picture in doc.pictures:
        prov = picture.prov[0]
        if prov.page_no >= cv.PAGE_MIN_QRT:
            n_pict_qrt_ignorees += 1
            continue
        page_fitz = doc_fitz[prov.page_no - 1]
        rect = rect_depuis_bbox(prov.bbox, doc.pages[prov.page_no].size.height)
        image = extraire_crop(page_fitz, rect, ECHELLE_CROP)
        h = imagehash.phash(image)
        images_a_traiter.append((picture, image, h))

    # Regroupement par seuil fixe (union-find simple) — même principe que
    # dedup.py, seuil fixé plutôt que détecté dynamiquement (cf. docstring).
    n = len(images_a_traiter)
    parent = list(range(n))

    def trouver(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(n):
        for j in range(i + 1, n):
            if images_a_traiter[i][2] - images_a_traiter[j][2] <= SEUIL_DEDUP_PHASH:
                ri, rj = trouver(i), trouver(j)
                if ri != rj:
                    parent[ri] = rj

    groupes = {}
    for i in range(n):
        groupes.setdefault(trouver(i), []).append(i)

    mapping_dedup = {}  # self_ref dupliqué -> self_ref canonique (le 1er du groupe)
    n_images_sauvees, n_doublons_evites = 0, 0
    for indices in groupes.values():
        indices_tries = sorted(indices, key=lambda i: images_a_traiter[i][0].self_ref)
        canonique_picture, canonique_image, _ = images_a_traiter[indices_tries[0]]
        chemin_rel = cv.chemin_relatif_table_ou_image(canonique_picture.self_ref, args.annee)
        canonique_image.save(cv.chemin_absolu(chemin_rel), "PNG")
        n_images_sauvees += 1
        for i in indices_tries[1:]:
            doublon_picture, _, _ = images_a_traiter[i]
            mapping_dedup[doublon_picture.self_ref] = canonique_picture.self_ref
            n_doublons_evites += 1

    if mapping_dedup:
        with open(cv.chemin_absolu(f"{args.annee}/images_dedup.json"), "w", encoding="utf-8") as f:
            json.dump(mapping_dedup, f, ensure_ascii=False, indent=2)

    print(f"[images] {n_images_sauvees} fichier(s) physique(s) sauvegardé(s), "
          f"{n_doublons_evites} doublon(s) évité(s) (pHash <= {SEUIL_DEDUP_PHASH}), "
          f"{n_pict_qrt_ignorees} image(s) en zone QRT ignorée(s) (couvertes par le rendu pleine page)")
    if mapping_dedup:
        print("  Doublons détectés (self_ref dupliqué -> self_ref canonique) :")
        for dup, canon in mapping_dedup.items():
            print(f"    {dup} -> {canon}")

    # --- 3. Pages QRT complètes (page >= PAGE_MIN_QRT) : un rendu par
    # page, quel que soit son contenu exact (table/image/texte). ---
    n_pages = len(doc.pages)
    n_qrt_sauvees = 0
    for page_no in range(cv.PAGE_MIN_QRT, n_pages + 1):
        image = rendre_page_qrt(doc_fitz, page_no - 1)
        chemin_rel = cv.chemin_relatif_page_qrt(page_no, args.annee)
        image.save(cv.chemin_absolu(chemin_rel), "PNG")
        n_qrt_sauvees += 1

    print(f"[qrt_pages] {n_qrt_sauvees} page(s) QRT rendue(s) en entier "
          f"(pages {cv.PAGE_MIN_QRT} à {n_pages})")

    doc_fitz.close()
    print(f"\n[export] fichiers écrits sous {racine_annee}")


if __name__ == "__main__":
    main()
