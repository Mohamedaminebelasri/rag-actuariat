# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier ajuste la taille des morceaux de texte : il sépare ceux qui
# sont trop longs et regroupe ceux qui sont trop courts, pour que chaque
# morceau ne soit ni trop vague ni trop fragmenté.
# ------------------------------------------------------------------
"""split_and_merge_chunks.py — Étape 3 (définitive) : découpe les chunks
de sections_directes.json selon les 2 motifs validés, laisse tout le
reste inchangé.

MOTIF 1 (bullet-titre) : les list_item dont l'origine est un
SECTION_HEADER retypé par retype_bullet_headers.py (préfixé /
à l'origine, cf. inspect_bullet_candidates.py) sont de vrais points de
découpage. Chaque chunk parent qui en contient au moins un est éclaté en
(a) le texte AVANT le premier bullet-titre, sous le titre du parent seul
(s'il y en a), puis (b) un sous-chunk par bullet-titre, dont le texte du
bullet devient le titre direct du sous-chunk — le chemin hiérarchique
complet du parent est conservé TEL QUEL sur chaque sous-chunk.

MOTIF 2 (paragraphe, "type 2") : les chunks indexables > 600 mots SANS
aucun bullet-titre parmi leurs list_item sont découpés par paragraphe
narratif, jusqu'à ~400-500 mots par sous-chunk. La coupe ne se fait
JAMAIS à l'intérieur du texte d'un item (chaque item reste entier), ni au
milieu d'une énumération liée par ":" — la phrase introductive et TOUS
les list_item qui la suivent immédiatement forment un bloc indivisible
(construire_unites). Tous les sous-chunks répètent le même chemin
hiérarchique ET le même titre que le parent (pas de sous-titre naturel
ici).

Les deux ensembles (chunks à bullet-titre, chunks "type 2") sont
RECALCULÉS ici avec exactement la même logique déjà validée dans
inspect_bullet_candidates.py (fonctions réutilisées via import, jamais
réécrites), puis comparés aux comptes annoncés — tout écart est signalé,
jamais ajusté silencieusement.

NOTE — écart déjà repéré AVANT d'écrire ce script : le tour précédent
annonçait "20 chunks parents" à bullet-titre. Un recomptage exact du
journal console de ce tour précédent en donne 18 (51 bullet-titre
répartis sur 18 parents indexables, 0 cas hors chunk indexable) — erreur
de comptage dans mon propre résumé de ce tour-là, pas un changement de
règle ni une divergence des données. Ce script recalcule le compte réel
plutôt que de se fier au chiffre annoncé, et le signale explicitement au
lancement.

Ne modifie ni n'écrit jamais sections_directes.json, structure_finale_v4.json,
structure_filtree.json ni docling_document_complet.json (lecture seule).

    python split_and_merge_chunks.py [structure_finale_v4.json] [sections_directes.json] [docling_document_json] [structure_filtree.json] [dossier_sortie]
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

SEUIL_MOTS_TYPE2 = 600          # seuil de sélection des chunks "type 2" (identique à l'inspection précédente)
SEUIL_BAS_PARAGRAPHE = 400      # cible basse de mots par sous-chunk "type 2"
SEUIL_HAUT_PARAGRAPHE = 500     # cible haute de mots par sous-chunk "type 2"

# Comptes annoncés au tour précédent, gardés ici uniquement pour détecter
# et signaler l'écart (cf. NOTE en tête de module) — jamais utilisés comme
# vérité, seul le recalcul réel pilote le découpage.
N_CHUNKS_BULLET_ANNONCE = 20
N_BULLETS_ANNONCE = 51
N_CHUNKS_TYPE2_ANNONCE = 5


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("structure_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "structure_finale_v4.json"))
    p.add_argument("sections_directes_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "sections_directes.json"))
    p.add_argument("docling_document_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "docling_document_complet.json"))
    p.add_argument("structure_filtree_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "structure_filtree.json"))
    p.add_argument("output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"))
    return p.parse_args()


def obtenir_span(header, headers, i, items_tries, blc):
    """Contenu DIRECT de `header` (même frontière que build_leaf_chunks.py :
    jusqu'au tout prochain header, quel que soit son niveau), header
    lui-même exclu."""
    fin_idx = blc.trouver_fin_chunk_direct(headers, i)
    position_fin = headers[fin_idx]["position"] if fin_idx < len(headers) else None
    return [
        it for it in items_tries
        if it["position"] > header["position"]
        and (position_fin is None or it["position"] < position_fin)
    ]


def decouper_bullet_titre(header, chemin, span, positions_bullet_titre, bs, blc):
    """MOTIF 1. Découpe `span` à chaque item dont la position est dans
    `positions_bullet_titre` (déjà filtré à CE chunk parent). Retourne
    (sous_chunks, mots_titres_promus) — le 2e élément sert uniquement à
    la réconciliation finale des mots (cf. RÉSUMÉ) : le texte des
    bullet-titre quitte le décompte "nb_mots" pour devenir un "titre",
    exactement comme le texte d'un section_header n'a jamais été compté
    comme contenu de son propre chunk."""
    bullets = sorted(
        (it for it in span if it["position"] in positions_bullet_titre),
        key=lambda it: it["position"],
    )

    sous_chunks = []
    mots_titres_promus = 0

    # (a) texte AVANT le premier bullet-titre, s'il y en a — sous le titre du parent seul.
    premiere_pos = bullets[0]["position"] if bullets else None
    avant = [it for it in span if premiere_pos is None or it["position"] < premiere_pos]
    if avant:
        texte, nb_mots, pages = bs.assembler_contenu(avant)
        sous_chunks.append({
            "titre": header["extrait"],
            "chemin_hierarchique": chemin,
            "niveau": header["niveau"],
            "position_header": header["position"],
            "position_origine": header["position"],
            "pages": sorted(set(header.get("pages", [])) | set(pages)),
            "nb_mots": nb_mots,
            "texte": texte,
            "categorie": "indexable" if nb_mots >= blc.SEUIL_MOTS_INDEXABLE else "structurel",
            "origine_decoupage": "bullet_titre",
        })

    # (b) un sous-chunk par bullet-titre : le bullet devient le titre
    # direct, exclu du texte/décompte du sous-chunk.
    for k, bullet in enumerate(bullets):
        mots_titres_promus += len((bullet.get("extrait") or "").split())
        fin_pos = bullets[k + 1]["position"] if k + 1 < len(bullets) else None
        contenu = [
            it for it in span
            if it["position"] > bullet["position"]
            and (fin_pos is None or it["position"] < fin_pos)
        ]
        texte, nb_mots, pages = bs.assembler_contenu(contenu)
        sous_chunks.append({
            "titre": bullet["extrait"],
            "chemin_hierarchique": chemin,
            "niveau": None,  # comme les list_item d'origine (retype_bullet_headers.py) : pas de niveau de titre officiel
            "position_header": header["position"],
            "position_origine": bullet["position"],
            "pages": sorted(set(bullet.get("pages", [])) | set(pages)),
            "nb_mots": nb_mots,
            "texte": texte,
            "categorie": "indexable" if nb_mots >= blc.SEUIL_MOTS_INDEXABLE else "structurel",
            "origine_decoupage": "bullet_titre",
        })

    return sous_chunks, mots_titres_promus


def construire_unites(span):
    """Regroupe `span` en unités ATOMIQUES, jamais coupées entre elles à
    l'intérieur : un item se terminant par ':' est fusionné avec TOUS les
    list_item qui le suivent immédiatement (énumération liée) en une
    seule unité indivisible ; tout le reste forme une unité d'un seul
    item. Ne coupe jamais À L'INTÉRIEUR du texte d'un item — chaque item
    reste entier dans son unité, donc jamais au milieu d'une phrase."""
    unites = []
    i, n = 0, len(span)
    while i < n:
        item = span[i]
        texte = (item.get("extrait") or "").rstrip()
        if texte.endswith(":"):
            bloc = [item]
            j = i + 1
            while j < n and span[j]["type"] == "list_item":
                bloc.append(span[j])
                j += 1
            unites.append(bloc)
            i = j
        else:
            unites.append([item])
            i += 1
    return unites


def decouper_paragraphe(header, chemin, span, bs, blc):
    """MOTIF 2. Regroupe `span` en unités indivisibles (construire_unites),
    puis les répartit par accumulation gloutonne en sous-chunks visant
    ~400-500 mots : ne clôt un sous-chunk que s'il a déjà atteint le
    seuil bas ET que l'unité suivante le ferait dépasser le seuil haut —
    jamais au milieu d'une unité. Répète le même titre/chemin sur chaque
    sous-chunk (pas de sous-titre naturel dans ce motif)."""
    unites = construire_unites(span)
    unites_assemblees = [bs.assembler_contenu(u) for u in unites]  # (texte, nb_mots, pages) par unité

    groupes = []
    lignes_courantes, mots_courants, pages_courantes = [], 0, set()
    for texte_u, mots_u, pages_u in unites_assemblees:
        if lignes_courantes and mots_courants >= SEUIL_BAS_PARAGRAPHE \
                and mots_courants + mots_u > SEUIL_HAUT_PARAGRAPHE:
            groupes.append((lignes_courantes, mots_courants, pages_courantes))
            lignes_courantes, mots_courants, pages_courantes = [], 0, set()
        if texte_u:
            lignes_courantes.append(texte_u)
        mots_courants += mots_u
        pages_courantes = pages_courantes | set(pages_u)
    if lignes_courantes or mots_courants:
        groupes.append((lignes_courantes, mots_courants, pages_courantes))

    sous_chunks = []
    for lignes, nb_mots, pages in groupes:
        sous_chunks.append({
            "titre": header["extrait"],
            "chemin_hierarchique": chemin,
            "niveau": header["niveau"],
            "position_header": header["position"],
            "position_origine": header["position"],
            # Pages RÉELLEMENT couvertes par le contenu de CE sous-chunk
            # précis (déjà assemblées unité par unité ci-dessus, via les
            # "pages" de chaque item narratif) — la page du section_header
            # PARENT n'est plus ajoutée automatiquement (elle l'était via
            # `set(header.get("pages", [])) | pages`, ce qui faussait la
            # citation : tous les sous-chunks d'un même parent portaient à
            # tort sa page, même ceux qui ne la touchent plus). Limite
            # identifiée lors de l'attache des métadonnées (attach_metadata.py).
            "pages": sorted(pages),
            "nb_mots": nb_mots,
            "texte": "\n".join(lignes),
            "categorie": "indexable" if nb_mots >= blc.SEUIL_MOTS_INDEXABLE else "structurel",
            "origine_decoupage": "paragraphe_type2",
        })
    return sous_chunks


def main():
    args = parse_cli()

    import build_sections as bs
    import build_leaf_chunks as blc
    from docling_core.types.doc.document import DoclingDocument
    from recover_full_text import enrichir_avec_texte_integral
    from retype_bullet_headers import retyper
    from inspect_bullet_candidates import classer_list_item, trouver_header_parent

    with open(args.structure_json, encoding="utf-8") as f:
        items = json.load(f)
    with open(args.sections_directes_json, encoding="utf-8") as f:
        chunks_existants = json.load(f)
    with open(args.structure_filtree_json, encoding="utf-8") as f:
        items_filtres = json.load(f)

    # --- Reconstitution des items narratifs enrichis (texte intégral),
    # identique à build_leaf_chunks.py / inspect_bullet_candidates.py ---
    doc = DoclingDocument.load_from_json(args.docling_document_json)
    items_narratifs = [it for it in items if not bs.est_zone_qrt(it)]
    items_enrichis = enrichir_avec_texte_integral(doc, items_narratifs)
    items_tries = sorted(items_enrichis, key=lambda it: it["position"])
    headers = [it for it in items_tries if it["type"] == "section_header"]
    chemins = bs.construire_chemins_hierarchiques(headers)

    chunks_par_position_header = {c["position_header"]: c for c in chunks_existants}
    if len(headers) != len(chunks_existants):
        print(f">>> ARRÊT — {len(headers)} section_header recalculés mais "
              f"{len(chunks_existants)} chunks dans sections_directes.json : ne correspond "
              "pas. structure_finale_v4.json a peut-être changé depuis la dernière "
              "régénération de sections_directes.json. Rien exporté.")
        return

    # --- Origine réelle des bullet-titre (positions retypées par
    # retype_bullet_headers.py, recalculées depuis structure_filtree.json,
    # jamais régénérées sur disque) ---
    _, journal = retyper(items_filtres)
    positions_retypees = {e["position"] for e in journal}

    # --- Item précédent, dans l'ordre de lecture RÉEL (robuste aux trous
    # de position laissés par final_corrections.py) ---
    par_position_precedent = {}
    precedent = None
    for it in items_tries:
        par_position_precedent[it["position"]] = precedent
        precedent = it

    # --- Classement des list_item + regroupement des candidat_titre par
    # chunk parent INDEXABLE — même logique que inspect_bullet_candidates.py,
    # réutilisée via import, pas réécrite. ---
    list_items = [it for it in items_tries if it["type"] == "list_item"]
    candidats_par_header = {}  # position_header -> set(positions bullet-titre)
    for it in list_items:
        item_precedent = par_position_precedent[it["position"]]
        texte_precedent = item_precedent["extrait"] if item_precedent else None
        categorie = classer_list_item(texte_precedent, it["position"], positions_retypees)
        if categorie != "candidat_titre":
            continue
        hp = trouver_header_parent(it["position"], headers)
        if hp is None:
            continue
        chunk = chunks_par_position_header.get(hp["position"])
        if chunk is None or chunk["categorie"] != "indexable":
            continue
        candidats_par_header.setdefault(hp["position"], set()).add(it["position"])

    n_bullets_total = sum(len(v) for v in candidats_par_header.values())

    print("=" * 70)
    print("RECALCUL DES DEUX ENSEMBLES (même logique que inspect_bullet_candidates.py)")
    print("=" * 70)
    print(f"  Motif 1 (bullet-titre) : {n_bullets_total} bullet(s) sur "
          f"{len(candidats_par_header)} chunk(s) parent(s)")
    if len(candidats_par_header) != N_CHUNKS_BULLET_ANNONCE or n_bullets_total != N_BULLETS_ANNONCE:
        print(f"  >>> Écart avec les chiffres annoncés au tour précédent "
              f"({N_CHUNKS_BULLET_ANNONCE} chunks, {N_BULLETS_ANNONCE} bullets) — voir NOTE "
              "en tête de ce script : recomptage exact du tour précédent = 18 chunks/51 "
              "bullets, erreur dans mon résumé de ce tour-là, pas un changement de règle. "
              "Le script continue avec le compte RÉEL recalculé ci-dessus.")

    # --- Motif 2 : chunks indexables > 600 mots, 0 bullet-titre ---
    positions_avec_bullet = set(candidats_par_header.keys())
    chunks_type2 = [
        c for c in chunks_existants
        if c["categorie"] == "indexable"
        and c["nb_mots"] > SEUIL_MOTS_TYPE2
        and c["position_header"] not in positions_avec_bullet
    ]
    positions_type2 = {c["position_header"] for c in chunks_type2}
    print(f"  Motif 2 (paragraphe)    : {len(chunks_type2)} chunk(s)")
    if len(chunks_type2) != N_CHUNKS_TYPE2_ANNONCE:
        print(f"  >>> Écart avec le chiffre annoncé ({N_CHUNKS_TYPE2_ANNONCE}) — recompte "
              f"réel = {len(chunks_type2)}. Le script continue avec ce compte réel.")

    # --- Charge l'ancien chunks_finaux.json (s'il existe), UNIQUEMENT pour
    # l'affichage avant/après des pages "type 2" ci-dessous — jamais utilisé
    # pour le calcul, qui repart entièrement des items narratifs. Clé
    # (position_header, texte) : le texte de chaque sous-chunk type 2 est
    # inchangé par cette correction (seul "pages" change), donc c'est une
    # clé stable pour retrouver la valeur "avant" de chaque sous-chunk. ---
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "chunks_finaux.json"
    pages_avant_type2 = {}
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            ancien_chunks_finaux = json.load(f)
        for c in ancien_chunks_finaux:
            if c.get("origine_decoupage") == "paragraphe_type2":
                pages_avant_type2[(c["position_header"], c["texte"])] = c["pages"]

    # --- Construction du résultat final, dans l'ordre de lecture d'origine ---
    chunks_finaux = []
    mots_titres_promus_total = 0
    ecarts_locaux = 0

    for i, header in enumerate(headers):
        pos = header["position"]
        chunk_origine = chunks_par_position_header[pos]

        if pos in candidats_par_header:
            span = obtenir_span(header, headers, i, items_tries, blc)
            sous_chunks, mots_promus = decouper_bullet_titre(
                header, chemins[pos], span, candidats_par_header[pos], bs, blc)
            mots_titres_promus_total += mots_promus
            total_verif = sum(c["nb_mots"] for c in sous_chunks) + mots_promus
            if total_verif != chunk_origine["nb_mots"]:
                print(f"  >>> ÉCART LOCAL (bullet) sur {header['extrait']!r} : "
                      f"{total_verif} (sous-chunks + titres promus) != "
                      f"{chunk_origine['nb_mots']} (chunk d'origine)")
                ecarts_locaux += 1
            chunks_finaux.extend(sous_chunks)

        elif pos in positions_type2:
            span = obtenir_span(header, headers, i, items_tries, blc)
            sous_chunks = decouper_paragraphe(header, chemins[pos], span, bs, blc)
            total_verif = sum(c["nb_mots"] for c in sous_chunks)
            if total_verif != chunk_origine["nb_mots"]:
                print(f"  >>> ÉCART LOCAL (paragraphe) sur {header['extrait']!r} : "
                      f"{total_verif} (sous-chunks) != {chunk_origine['nb_mots']} (chunk d'origine)")
                ecarts_locaux += 1
            chunks_finaux.extend(sous_chunks)

        else:
            chunks_finaux.append({**chunk_origine, "origine_decoupage": None})

    if ecarts_locaux:
        print(f"\n>>> ARRÊT — {ecarts_locaux} écart(s) local(aux) détecté(s) ci-dessus "
              "(mots perdus/gagnés pendant un découpage). Rien exporté.")
        return

    # --- Avant/après des pages des 12 sous-chunks "type 2" (seul champ
    # corrigé par ce passage) — affiché AVANT l'export pour vérification
    # visuelle directe. ---
    sous_chunks_type2 = [c for c in chunks_finaux if c.get("origine_decoupage") == "paragraphe_type2"]
    if sous_chunks_type2:
        print("\n" + "=" * 70)
        print(f"AVANT / APRÈS — pages des {len(sous_chunks_type2)} sous-chunks \"type 2\" "
              "(seul champ corrigé)")
        print("=" * 70)
        for c in sous_chunks_type2:
            cle = (c["position_header"], c["texte"])
            avant = pages_avant_type2.get(cle, "? (pas de sous-chunk correspondant dans l'ancien fichier)")
            print(f"  {c['titre']!r} (p.{c['pages']})")
            print(f"    avant : {avant}")
            print(f"    après : {c['pages']}")

    # --- Export ---
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks_finaux, f, ensure_ascii=False, indent=2)

    # --- Réconciliation globale du nombre de mots ---
    total_final_nb_mots = sum(c["nb_mots"] for c in chunks_finaux)
    _, nb_mots_avant_premier = blc.construire_chunks_directs(items_enrichis, bs)
    total_reference = blc.calculer_total_mots_reference(items_enrichis, bs)
    total_reconcilie = total_final_nb_mots + mots_titres_promus_total + nb_mots_avant_premier

    n_indexable = sum(1 for c in chunks_finaux if c["categorie"] == "indexable")
    n_structurel = sum(1 for c in chunks_finaux if c["categorie"] == "structurel")
    mots_indexables = [c["nb_mots"] for c in chunks_finaux if c["categorie"] == "indexable"]

    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Chunks d'origine (sections_directes.json)         : {len(chunks_existants)}")
    print(f"  Chunks finaux (chunks_finaux.json)                 : {len(chunks_finaux)}")
    print(f"    dont issus d'un découpage bullet-titre           : "
          f"{sum(1 for c in chunks_finaux if c.get('origine_decoupage') == 'bullet_titre')}")
    print(f"    dont issus d'un découpage paragraphe (type 2)    : "
          f"{sum(1 for c in chunks_finaux if c.get('origine_decoupage') == 'paragraphe_type2')}")
    print(f"    inchangés                                        : "
          f"{sum(1 for c in chunks_finaux if c.get('origine_decoupage') is None)}")
    print(f"  Indexable / structurel                             : {n_indexable} / {n_structurel}")

    print(f"\n  Total mots (chunks finaux)                         : {total_final_nb_mots}")
    print(f"  + mots de titres bullet-titre promus (hors nb_mots) : {mots_titres_promus_total}")
    print(f"  + mots avant le 1er header (hors chunk, cf. build_leaf_chunks.py) : "
          f"{nb_mots_avant_premier}")
    print(f"  = total réconcilié                                 : {total_reconcilie}")
    print(f"  Total de référence (items narratifs hors section_header) : {total_reference}")
    if total_reconcilie == total_reference:
        print("  OK — aucun mot perdu ni dupliqué.")
    else:
        ecart = total_reconcilie - total_reference
        print(f"  >>> ÉCART GLOBAL DÉTECTÉ : {ecart:+d} mots — à examiner.")

    if mots_indexables:
        print(f"\n  Distribution des mots (chunks INDEXABLES uniquement, {len(mots_indexables)} chunks) :")
        print(f"    min={min(mots_indexables)}  max={max(mots_indexables)}  "
              f"médiane={statistics.median(mots_indexables):.0f}")

    print(f"\n[export] {len(chunks_finaux)} chunks écrits dans {out_path}")


if __name__ == "__main__":
    main()
