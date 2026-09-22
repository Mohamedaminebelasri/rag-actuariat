# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier enchaîne, dans le bon ordre, TOUTES les étapes nécessaires
# pour transformer un PDF SFCR en contenu interrogeable dans la base de
# recherche — une seule commande au lieu d'une vingtaine.
# ------------------------------------------------------------------
"""run_pipeline.py — Orchestrateur unique du pipeline SFCR complet (Phase
2, Décision 048) : narratif (12 étapes) + QRT (ingest.py) + indexation
finale (ingest_qdrant.py), avec --pdf/--company/--type/--year propagés de
bout en bout.

    python run_pipeline.py --pdf chemin/vers/sfcr.pdf --company "Groupama" \
        --type "mutuelle" --year 2025 [--source-file NOM.pdf] \
        [--work-dir output_structure_brute] [--verifier-delta-uniquement] \
        [--skip-narratif] [--skip-qrt] [--skip-index]

CE QUI EST RÉELLEMENT AUTOMATISÉ ET CE QUI NE L'EST PAS (lu avant de se
fier à une exécution "verte" sur un NOUVEAU document, pas seulement sur
Groupama 2025/2024 déjà connus) :

1. **`fix_unnumbered_levels.py` et `final_corrections.py` ont des LISTES
   BLANCHES codées en dur** (positions + textes exacts, vérifiées un par un
   avec l'utilisateur sur CE document précis — cf. leurs propres docstrings)
   pour Groupama 2025. `fix_unnumbered_levels_2024.py` en a une distincte
   pour 2024. Sur un 3e document, ces 2 scripts s'ARRÊTENT PROPREMENT
   (aucune correction devinée) dès qu'un cas non couvert apparaît — c'est
   le comportement VOULU, pas un bug de cet orchestrateur : une nouvelle
   liste blanche doit être construite à la main pour chaque nouveau
   document avant de pouvoir continuer. Cet orchestrateur ne contourne pas
   ce garde-fou et NE DEVINE RIEN à la place.

2. **`build_index_texte_bge.py` et `build_index_visuels.py` (+ la racine
   `chemins_visuels.RACINE_VISUELS` qu'ils partagent) n'ont AUCUN argument
   CLI** — chemins d'entrée/sortie câblés en dur sur
   `output_structure_brute/`, PAS paramétrables par `--work-dir`. Cet
   orchestrateur les appelle tels quels (cohérent avec le seul usage réel
   à ce jour : un `work_dir` = `output_structure_brute/`) ; une vraie
   isolation multi-documents (30 fichiers SFCR, cf. IDEES_SCALE_UP.md)
   demandera de les paramétrer d'abord — PAS fait ici, hors périmètre
   explicite de la Phase 2 actuelle (cf. Décision 046).

3. **`extraire_visuels.py` écrit sous une racine PARTAGÉE PAR ANNÉE**
   (`RACINE_VISUELS/<année>/...`), pas par entreprise — deux entreprises
   différentes avec la MÊME année entreraient en collision de chemin. Sans
   conséquence pour Groupama 2025/2024 (une seule entreprise à ce jour),
   mais À CORRIGER avant d'ingérer un 2e émetteur.

4. **Coût réel** : `extract_raw_structure.py` ET `save_docling_document.py`
   reconvertissent CHACUN le PDF séparément (>10 min ×2, aucun partage de
   résultat entre les deux scripts) — buget à prévoir avant de lancer sur
   un nouveau document. `--skip-narratif`/`--skip-qrt`/`--skip-index`
   permettent de rejouer un seul bloc (ex. après avoir corrigé une liste
   blanche) sans repayer les blocs déjà réussis.

ORDRE RÉEL (reconstitué et VÉRIFIÉ byte-pour-byte contre le corpus 2025 en
production, cf. Décision 045) — PAS l'ordre documenté dans GUIDE_PROJET.md
seul, qui omet les 7 scripts de correction restaurés par cette même
décision :

  BLOC narratif :
    extract_raw_structure.py, save_docling_document.py
    -> fix_heading_levels.py            (structure_brute -> corrigee)
    -> filter_fake_headers.py           (corrigee -> filtree)
    -> retype_bullet_headers.py         (filtree -> finale)
    -> final_corrections.py             (finale + structure_brute -> v3)
    -> fix_unnumbered_levels[_2024].py  (v3 -> v4)
    -> recover_full_text.regenerer_sections_brutes(v4)  (-> sections_brutes,
       appelée en Python, pas en subprocess : pas de CLI pour choisir sa
       structure source, cf. son docstring)
    -> build_leaf_chunks.py (v4 explicite, PAS son défaut v2 périmé,
       cf. Décision 045)                (-> sections_directes)
    -> split_and_merge_chunks.py        (-> chunks_finaux)
    -> attach_metadata.py --year        (-> chunks_avec_metadata)
    -> clean_final_text.py              (-> chunks_propres)
    -> extraire_visuels.py              (-> PNG + images_dedup.json)
    -> associer_visuels_chunks.py       (-> chunks_avec_visuels)
    -> build_index_texte_bge.py         (-> index_texte_bge, index_tableaux_texte_bge)
    -> build_index_visuels.py           (-> index_visuels_cohere ; COHERE_API_KEY requise)

  BLOC QRT :
    ingest.py <pdf> <work_dir>          (-> work_dir/corpus_final.json,
       diagnostic — QRT uniquement, cf. Décision 045 : process_narrative()
       et process_sommaire() ne sont plus appelées)

  BLOC indexation finale :
    ingest_qdrant.py --company --type --year --source-file
       (-> upsert dans les 4 collections Qdrant EXISTANTES, jamais de
       nouvelle collection créée — cf. son propre docstring)
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent
PYTHON = sys.executable


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--pdf", required=True, help="Chemin du PDF SFCR source")
    p.add_argument("--company", required=True, dest="company_name", help="Nom de l'entreprise (ex. Groupama)")
    p.add_argument("--type", required=True, dest="company_type", help="Type d'entreprise (ex. mutuelle, SA)")
    p.add_argument("--year", required=True, type=int, help="Année du document")
    p.add_argument("--source-file", default=None,
                    help="Nom du fichier PDF source pour le payload Qdrant (défaut : basename de --pdf)")
    p.add_argument("--work-dir", default=str(BASE_DIR / "output_structure_brute"),
                    help="Dossier de travail (défaut : output_structure_brute/, seul emplacement supporté "
                         "par build_index_texte_bge.py/build_index_visuels.py, cf. point 2 du docstring)")
    p.add_argument("--skip-narratif", action="store_true", help="Sauter le bloc narratif (déjà produit)")
    p.add_argument("--skip-qrt", action="store_true", help="Sauter le bloc QRT (déjà produit)")
    p.add_argument("--skip-index", action="store_true", help="Sauter le bloc indexation finale Qdrant")
    p.add_argument("--salt-ids", action="store_true",
                    help="Sale les IDs de point Qdrant avec --year (cf. id_deterministe, ingest_qdrant.py) — "
                         "à utiliser SEULEMENT pour ingérer un document dont les IDs pourraient entrer en "
                         "collision avec un document DÉJÀ présent dans les collections (numérotation Docling "
                         "repartant de 0 à chaque document). NE JAMAIS l'utiliser pour ré-indexer un document "
                         "dont les points existants ont été créés SANS salage (ex. Groupama 2025, le tout "
                         "premier document ingéré) : ça créerait des points EN DOUBLE (nouveaux UUID salés) "
                         "au lieu d'un upsert en place sur les UUID non salés déjà présents.")
    p.add_argument("--verifier-delta-uniquement", action="store_true",
                    help="Transmis à ingest_qdrant.py — à utiliser quand les collections contiennent "
                         "déjà d'autres documents (cf. ingest_qdrant_2024.py)")
    p.add_argument("--n-texte-attendu", type=int, default=None)
    p.add_argument("--n-tableaux-attendu", type=int, default=None)
    p.add_argument("--n-images-attendu", type=int, default=None)
    p.add_argument("--n-qrt-attendu", type=int, default=None)
    return p.parse_args()


def executer(*args, cwd=BASE_DIR):
    """Exécute une commande, ARRÊTE tout l'orchestrateur au premier échec
    (subprocess.run(check=True) lève CalledProcessError, jamais avalée
    silencieusement) — cohérent avec le comportement de chaque script
    individuel (ex. final_corrections.py qui refuse une correction douteuse
    plutôt que de deviner)."""
    cmd = [str(a) for a in args]
    print(f"\n$ {' '.join(cmd)}")
    t0 = time.time()
    subprocess.run(cmd, cwd=str(cwd), check=True)
    print(f"  [{time.time() - t0:.1f}s]")


def bloc_narratif(pdf_path, work_dir, annee):
    print("\n" + "=" * 70)
    print("BLOC NARRATIF")
    print("=" * 70)

    executer(PYTHON, "extract_raw_structure.py", pdf_path, work_dir)
    executer(PYTHON, "save_docling_document.py", pdf_path, work_dir)

    structure_brute = work_dir / "structure_brute.json"
    executer(PYTHON, "fix_heading_levels.py", structure_brute, work_dir)

    structure_corrigee = work_dir / "structure_corrigee.json"
    executer(PYTHON, "filter_fake_headers.py", structure_corrigee, work_dir)

    structure_filtree = work_dir / "structure_filtree.json"
    executer(PYTHON, "retype_bullet_headers.py", structure_filtree, work_dir)

    structure_finale = work_dir / "structure_finale.json"
    executer(PYTHON, "final_corrections.py", structure_finale, structure_brute, work_dir)

    structure_finale_v3 = work_dir / "structure_finale_v3.json"
    # fix_unnumbered_levels_2024.py existe comme variante DISTINCTE pour
    # 2024 (liste blanche propre à ce document) — cf. point 1 du docstring.
    # Pas de variante générique : sur un 3e document, ce sera un 3e script
    # à écrire après inspection manuelle, pas une branche automatique ici.
    script_niveaux = "fix_unnumbered_levels_2024.py" if annee == 2024 else "fix_unnumbered_levels.py"
    executer(PYTHON, script_niveaux, structure_finale_v3, work_dir)

    structure_finale_v4 = work_dir / "structure_finale_v4.json"
    docling_json = work_dir / "docling_document_complet.json"

    # recover_full_text.regenerer_sections_brutes : appelée en Python, pas
    # en subprocess CLI — le script n'expose pas `structure_path` en
    # argument (cf. son docstring, Décision 045) ; l'appeler autrement
    # utiliserait silencieusement le défaut périmé structure_finale_v2.json.
    print(f"\n[Python] recover_full_text.regenerer_sections_brutes(structure_path={structure_finale_v4})")
    t0 = time.time()
    sys.path.insert(0, str(BASE_DIR))
    from docling_core.types.doc.document import DoclingDocument
    import recover_full_text as rft
    doc = DoclingDocument.load_from_json(str(docling_json))
    rft.SECTIONS_BRUTES_PATH = work_dir / "sections_brutes.json"
    rft.regenerer_sections_brutes(doc, structure_path=str(structure_finale_v4))
    print(f"  [{time.time() - t0:.1f}s]")

    sections_brutes = work_dir / "sections_brutes.json"
    executer(PYTHON, "build_leaf_chunks.py", structure_finale_v4, docling_json, sections_brutes, work_dir)

    sections_directes = work_dir / "sections_directes.json"
    executer(PYTHON, "split_and_merge_chunks.py", structure_finale_v4, sections_directes, docling_json,
              structure_filtree, work_dir)

    chunks_finaux = work_dir / "chunks_finaux.json"
    executer(PYTHON, "attach_metadata.py", chunks_finaux, sections_directes, work_dir, "--year", annee)

    chunks_avec_metadata = work_dir / "chunks_avec_metadata.json"
    executer(PYTHON, "clean_final_text.py", chunks_avec_metadata, work_dir)

    executer(PYTHON, "extraire_visuels.py", docling_json, pdf_path, annee)

    chunks_propres = work_dir / "chunks_propres.json"
    executer(PYTHON, "associer_visuels_chunks.py", chunks_propres, work_dir)

    # build_index_texte_bge.py / build_index_visuels.py : AUCUN argument
    # CLI (cf. point 2 du docstring) — toujours output_structure_brute/,
    # quel que soit --work-dir passé à cet orchestrateur.
    executer(PYTHON, "build_index_texte_bge.py")
    executer(PYTHON, "build_index_visuels.py")


def bloc_qrt(pdf_path, work_dir):
    print("\n" + "=" * 70)
    print("BLOC QRT")
    print("=" * 70)
    executer(PYTHON, "ingest.py", pdf_path, work_dir)


def bloc_index(args, work_dir):
    print("\n" + "=" * 70)
    print("BLOC INDEXATION FINALE (Qdrant)")
    print("=" * 70)
    cmd = [
        PYTHON, "ingest_qdrant.py",
        "--company", args.company_name,
        "--type", args.company_type,
        "--source-file", args.source_file,
        "--index-texte", str(work_dir / "index_texte_bge.json"),
        "--index-tableaux-texte", str(work_dir / "index_tableaux_texte_bge.json"),
        "--index-visuels", str(work_dir / "index_visuels_cohere.json"),
    ]
    # --year N'EST PAS TOUJOURS PASSÉ ICI : le champ payload "year" est déjà
    # correct indépendamment (lu depuis les fichiers index_*.json régénérés
    # par attach_metadata.py --year, cf. enrichir_payload_phase2). --year sur
    # CETTE commande ne contrôle QUE le salage d'ID (cf. --salt-ids) —
    # confusion réelle rencontrée et documentée en Décision 048.
    if args.salt_ids:
        cmd += ["--year", str(args.year)]
    if args.verifier_delta_uniquement:
        cmd.append("--verifier-delta-uniquement")
    for nom_arg, valeur in (
        ("--n-texte-attendu", args.n_texte_attendu),
        ("--n-tableaux-attendu", args.n_tableaux_attendu),
        ("--n-images-attendu", args.n_images_attendu),
        ("--n-qrt-attendu", args.n_qrt_attendu),
    ):
        if valeur is not None:
            cmd += [nom_arg, str(valeur)]
    print(f"\n$ {' '.join(cmd)}")
    t0 = time.time()
    subprocess.run(cmd, cwd=str(BASE_DIR), check=True)
    print(f"  [{time.time() - t0:.1f}s]")


def main():
    args = parse_cli()
    pdf_path = Path(args.pdf)
    work_dir = Path(args.work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    if args.source_file is None:
        args.source_file = pdf_path.name

    t_start = time.time()
    print(f"run_pipeline.py — pdf={pdf_path} company={args.company_name!r} "
          f"type={args.company_type!r} year={args.year} source_file={args.source_file!r} "
          f"work_dir={work_dir}")

    if not args.skip_narratif:
        bloc_narratif(pdf_path, work_dir, args.year)
    else:
        print("\n[SKIP] bloc narratif")

    if not args.skip_qrt:
        bloc_qrt(pdf_path, work_dir)
    else:
        print("\n[SKIP] bloc QRT")

    if not args.skip_index:
        bloc_index(args, work_dir)
    else:
        print("\n[SKIP] bloc indexation finale")

    print(f"\n{'=' * 70}\nPIPELINE TERMINÉ en {time.time() - t_start:.1f}s\n{'=' * 70}")


if __name__ == "__main__":
    main()
