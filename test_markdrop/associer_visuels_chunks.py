# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier relie chaque image de tableau ou d'image sauvegardée à
# l'endroit du texte où elle apparaît dans le rapport.
# ------------------------------------------------------------------
"""associer_visuels_chunks.py — Étape 5 : associe à chaque chunk narratif
de chunks_propres.json les fichiers visuels réels (extraits par
extraire_visuels.py) référencés par ses marqueurs [TABLEAU: self_ref] /
[IMAGE: self_ref] déjà présents dans son texte (insérés à l'étape de
chunking, build_sections.assembler_contenu).

PÉRIMÈTRE VÉRIFIÉ AVANT D'ÉCRIRE CE SCRIPT : la zone QRT (page >= 77) est
EXCLUE de chunks_propres.json depuis le tout début du pipeline de
chunking (bs.est_zone_qrt, appliqué dès build_sections.py) — il n'existe
donc AUCUN chunk QRT ici auquel associer les pages QRT rendues par
extraire_visuels.py. Ce n'est pas un oubli : l'association des pages QRT
à leurs éléments de corpus concerne le pipeline ingest.py/corpus_final.json
(distinct de ce pipeline de chunking narratif), hors périmètre de ce
script.

Pour chaque chunk, chaque marqueur trouvé résout vers un chemin réel via
chemins_visuels.py (self_ref -> chemin, en tenant compte du mapping de
déduplication écrit par extraire_visuels.py s'il existe) — AUCUNE
nouvelle table de correspondance construite ici. Le fichier résolu est
vérifié comme existant sur disque avant d'être attaché ; sinon, signalé
explicitement plutôt que d'attacher une référence vers un fichier absent.

Le champ chemin_hierarchique existant n'est jamais modifié — la référence
visuelle est un champ ADDITIONNEL ("visuels"), jamais un remplacement.

Ne modifie jamais chunks_propres.json (lecture seule) — exporte
chunks_avec_visuels.json.

    python associer_visuels_chunks.py [chunks_propres.json] [dossier_sortie]
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import chemins_visuels as cv

BASE_DIR = Path(__file__).parent

# Format exact des marqueurs, tel qu'inséré par build_sections.assembler_contenu :
# "[TABLEAU: #/tables/16]" ou "[IMAGE: #/pictures/75]" — LEGENDE/INDEX
# n'ont pas de fichier physique (hors périmètre de la tâche 3), ignorés ici.
MOTIF_MARQUEUR_VISUEL = re.compile(r"\[(TABLEAU|IMAGE): (#/(?:tables|pictures)/\d+)\]")

ETIQUETTE_VERS_TYPE = {"TABLEAU": "tableau", "IMAGE": "image"}


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("chunks_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "chunks_propres.json"))
    p.add_argument("output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"))
    return p.parse_args()


def main():
    args = parse_cli()
    with open(args.chunks_json, encoding="utf-8") as f:
        chunks = json.load(f)

    # Un mapping de dédup par année rencontrée (chargé une seule fois par
    # année, pas à chaque chunk).
    mappings_par_annee = {}

    chunks_avec_visuels = []
    n_chunks_avec_visuel, n_marqueurs_resolus, n_fichiers_manquants = 0, 0, 0
    fichiers_manquants_log = []

    for chunk in chunks:
        texte = chunk.get("texte") or ""
        marqueurs = MOTIF_MARQUEUR_VISUEL.findall(texte)

        nouveau = dict(chunk)
        if not marqueurs:
            nouveau["visuels"] = []
            chunks_avec_visuels.append(nouveau)
            continue

        annee = chunk.get("annee_document")
        if annee not in mappings_par_annee:
            mappings_par_annee[annee] = cv.charger_mapping_dedup(annee)
        mapping_dedup = mappings_par_annee[annee]

        visuels = []
        for etiquette, self_ref in marqueurs:
            chemin_rel = cv.resoudre_chemin_self_ref(self_ref, annee, mapping_dedup)
            chemin_abs = cv.chemin_absolu(chemin_rel)
            existe = chemin_abs.exists()
            visuels.append({
                "self_ref": self_ref,
                "type": ETIQUETTE_VERS_TYPE[etiquette],
                "chemin_relatif": chemin_rel,
                "fichier_trouve": existe,
            })
            n_marqueurs_resolus += 1
            if not existe:
                n_fichiers_manquants += 1
                fichiers_manquants_log.append({
                    "chunk_titre": chunk["titre"], "chemin_hierarchique": chunk["chemin_hierarchique"],
                    "self_ref": self_ref, "chemin_attendu": str(chemin_abs),
                })

        nouveau["visuels"] = visuels
        n_chunks_avec_visuel += 1
        chunks_avec_visuels.append(nouveau)

    print("=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Chunks traités                          : {len(chunks)}")
    print(f"  Chunks avec au moins 1 visuel associé    : {n_chunks_avec_visuel}")
    print(f"  Marqueurs résolus (tableau + image)      : {n_marqueurs_resolus}")
    print(f"  Fichiers manquants (marqueur résolu mais fichier absent du disque) : {n_fichiers_manquants}")

    if fichiers_manquants_log:
        print("\n" + "=" * 70)
        print(">>> FICHIERS MANQUANTS — à examiner (extraire_visuels.py a-t-il bien tourné pour cette année ?)")
        print("=" * 70)
        for m in fichiers_manquants_log:
            print(f"  chunk={m['chunk_titre']!r}  self_ref={m['self_ref']}  attendu={m['chemin_attendu']}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "chunks_avec_visuels.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks_avec_visuels, f, ensure_ascii=False, indent=2)
    print(f"\n[export] {len(chunks_avec_visuels)} chunks écrits dans {out_path}")


if __name__ == "__main__":
    main()
