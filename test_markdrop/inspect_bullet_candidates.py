# -*- coding: utf-8 -*-
"""inspect_bullet_candidates.py — Inspection EN LECTURE SEULE des
list_item, pour préparer (sans l'implémenter ici) la logique de découpage
de l'étape 3. Classe chaque list_item narratif selon le texte qui le
précède immédiatement dans l'ordre de lecture et son ORIGINE réelle, pour
distinguer :
- "candidat_titre" (bullet-titre, ex. "A.1.6 Emission de titres
  subordonnés") : uniquement les list_item dont la position fait partie
  des 53 SECTION_HEADER retypés par retype_bullet_headers.py (préfixés
  / à l'origine) — un fait vérifiable sur les données, pas une
  heuristique sur le texte.
- "détail_introduit" (bullet-détail) : précédé d'une phrase se terminant
  par ":" — fait partie d'une énumération, jamais un point de découpage
  isolé.
- "ambigu" : ni l'un ni l'autre — tout list_item natif (préfixé "-" ou
  autre, jamais retypé) qui n'est pas précédé d'un ":" tombe ici par
  défaut, jamais dans "candidat_titre".

ANCIENNE RÈGLE (b) ABANDONNÉE : un critère texte (<=10 mots, pas de
virgule/point-virgule final) laissait passer des fragments d'énumération
natifs qui se terminent par un point plutôt qu'une virgule/point-virgule
(ex. "-Activités Internationales.", "-les normes de provisionnement.") —
jamais des titres, juste des puces "-" courtes par coïncidence. Remplacée
par un critère d'origine, plus fiable : retype_bullet_headers.py ne
journalise ses 53 retypages qu'à l'affichage console (rien n'est
sauvegardé sur disque) — ce script réutilise directement sa fonction
`retyper()`, déjà validée, plutôt que de réinventer une détection, pour
retrouver exactement les mêmes 53 positions à partir de
structure_filtree.json (inchangé depuis).

Ne modifie ni n'exporte AUCUN fichier — affichage console uniquement,
pour validation manuelle avant d'écrire la vraie logique de découpage.

    python inspect_bullet_candidates.py [structure_finale_v4.json] [sections_directes.json] [docling_document_json] [structure_filtree.json]
"""

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

SEUIL_MOTS_CHUNK_TYPE2 = 600   # chunks > 600 mots sans bullet-titre : candidats découpage "type 2"


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("structure_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "structure_finale_v4.json"))
    p.add_argument("sections_directes_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "sections_directes.json"))
    p.add_argument("docling_document_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "docling_document_complet.json"))
    p.add_argument("structure_filtree_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "structure_filtree.json"),
                    help="Entrée d'origine de retype_bullet_headers.py, pour reconstituer "
                         "les 53 positions retypées via sa fonction retyper().")
    return p.parse_args()


def classer_list_item(texte_precedent, position_item, positions_retypees):
    """Applique les règles, dans l'ordre de priorité :
    (a) item précédent terminé par ':' -> détail_introduit (énumération).
    (b) position retypée par retype_bullet_headers.py (ex-SECTION_HEADER
        PUA devenu list_item) -> candidat_titre, sur l'origine réelle,
        jamais sur une heuristique de texte.
    (c) sinon -> ambigu.
    `texte_precedent` peut être None (item non textuel juste avant, ou
    tout début de section) — traité comme ne terminant jamais par ":",
    donc ne déclenche jamais la règle (a) par erreur."""
    if (texte_precedent or "").rstrip().endswith(":"):
        return "détail_introduit"

    if position_item in positions_retypees:
        return "candidat_titre"

    return "ambigu"


def trouver_header_parent(position_item, headers_tries):
    """Le section_header dont dépend directement l'item : celui dont la
    position est la plus grande parmi celles STRICTEMENT inférieures à
    `position_item` — c'est exactement la même règle d'appartenance que
    build_leaf_chunks.py (le tout prochain header AVANT l'item, dans
    l'ordre de lecture). None si aucun header ne précède (contenu avant
    le tout premier titre)."""
    parent = None
    for h in headers_tries:
        if h["position"] >= position_item:
            break
        parent = h
    return parent


def main():
    args = parse_cli()

    import build_sections as bs
    from docling_core.types.doc.document import DoclingDocument
    from recover_full_text import enrichir_avec_texte_integral
    from retype_bullet_headers import retyper

    with open(args.structure_json, encoding="utf-8") as f:
        items = json.load(f)
    with open(args.sections_directes_json, encoding="utf-8") as f:
        chunks = json.load(f)

    # Origine réelle des candidat_titre : les positions retypées par
    # retype_bullet_headers.py (fonction réutilisée telle quelle, pas
    # réimplémentée) à partir de structure_filtree.json, son entrée
    # d'origine — aucun fichier n'est écrit ici, juste recalculé en
    # mémoire à partir d'une entrée qui n'a pas changé.
    with open(args.structure_filtree_json, encoding="utf-8") as f:
        items_filtres = json.load(f)
    _, journal_retypages = retyper(items_filtres)
    positions_retypees = {entree["position"] for entree in journal_retypages}
    print(f"{len(positions_retypees)} position(s) retypée(s) par retype_bullet_headers.py "
          "(recalculées depuis structure_filtree.json, pas régénérées sur disque)")

    # Texte INTÉGRAL requis ici, pas les extraits à 100 caractères de
    # structure_finale_v4.json : un ":" de fin de phrase introductive peut
    # très bien tomber après le 100e caractère, faussant la règle (a) si
    # on ne récupère pas le texte complet. Lecture seule : ni
    # structure_finale_v4.json ni le DoclingDocument ne sont modifiés.
    doc = DoclingDocument.load_from_json(args.docling_document_json)
    items_narratifs = [it for it in items if not bs.est_zone_qrt(it)]
    items_enrichis = enrichir_avec_texte_integral(doc, items_narratifs)
    items_tries = sorted(items_enrichis, key=lambda it: it["position"])

    # "position - 1" interprété comme "l'item immédiatement précédent DANS
    # L'ORDRE DE LECTURE", pas littéralement la position numérique - 1 :
    # 3 positions ont été supprimées plus tôt dans le pipeline
    # (final_corrections.py), créant des trous dans la numérotation — une
    # recherche par arithmétique stricte position-1 tomberait parfois sur
    # un item inexistant juste après un trou. La recherche par ordre réel
    # (ci-dessous) est robuste à ces trous.
    par_position_precedent = {}
    precedent = None
    for it in items_tries:
        par_position_precedent[it["position"]] = precedent
        precedent = it

    headers_tries = [it for it in items_tries if it["type"] == "section_header"]
    list_items = [it for it in items_tries if it["type"] == "list_item"]

    print(f"Total list_item (hors zone QRT) : {len(list_items)}")

    # --- Classement ---
    resultats = []  # liste de dicts : item, categorie, texte_precedent, header_parent
    for it in list_items:
        item_precedent = par_position_precedent[it["position"]]
        texte_precedent = item_precedent["extrait"] if item_precedent else None
        categorie = classer_list_item(texte_precedent, it["position"], positions_retypees)
        header_parent = trouver_header_parent(it["position"], headers_tries)
        resultats.append({
            "item": it, "categorie": categorie,
            "texte_precedent": texte_precedent, "header_parent": header_parent,
        })

    compte = Counter(r["categorie"] for r in resultats)

    # --- 3. Regroupement des candidat_titre par chunk parent INDEXABLE ---
    chunks_par_position_header = {c["position_header"]: c for c in chunks}

    candidats_par_header = {}
    candidats_hors_indexable = []
    for r in resultats:
        if r["categorie"] != "candidat_titre":
            continue
        hp = r["header_parent"]
        if hp is None:
            candidats_hors_indexable.append((r, "aucun header parent (avant le 1er titre)"))
            continue
        chunk = chunks_par_position_header.get(hp["position"])
        if chunk is None or chunk["categorie"] != "indexable":
            candidats_hors_indexable.append(
                (r, f"parent {hp['extrait']!r} non indexable ou introuvable dans sections_directes.json")
            )
            continue
        candidats_par_header.setdefault(hp["position"], {"header": hp, "chunk": chunk, "items": []})
        candidats_par_header[hp["position"]]["items"].append(r["item"])

    print("\n" + "=" * 70)
    print("CANDIDAT_TITRE PAR CHUNK PARENT (indexable)")
    print("=" * 70)
    for entry in sorted(candidats_par_header.values(), key=lambda e: e["header"]["position"]):
        chunk = entry["chunk"]
        print(f"\n[{chunk['titre']}] — {chunk['nb_mots']} mots au total dans ce chunk")
        for it in sorted(entry["items"], key=lambda x: x["position"]):
            print(f"    p.{it['pages']} pos {it['position']:5} : {it['extrait']!r}")

    if candidats_hors_indexable:
        print(f"\n({len(candidats_hors_indexable)} candidat_titre hors chunk indexable, non affichés "
              "ci-dessus — cf. détail) :")
        for r, raison in candidats_hors_indexable:
            print(f"    p.{r['item']['pages']} pos {r['item']['position']} : "
                  f"{r['item']['extrait']!r} — {raison}")

    # --- 4. Liste des "ambigu" ---
    ambigus = [r for r in resultats if r["categorie"] == "ambigu"]
    print("\n" + "=" * 70)
    print(f"AMBIGU ({len(ambigus)}) — à vérifier manuellement, non classé")
    print("=" * 70)
    for r in sorted(ambigus, key=lambda r: r["item"]["position"]):
        it = r["item"]
        print(f"  p.{it['pages']} pos {it['position']:5} : {it['extrait']!r}")
        print(f"      (item précédent : {r['texte_precedent']!r})")

    # --- 5. Résumé chiffré ---
    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Total list_item      : {len(resultats)}")
    for cat in ("candidat_titre", "détail_introduit", "ambigu"):
        print(f"    {cat:20} : {compte.get(cat, 0)}")

    # --- 6. Chunks indexables > 600 mots SANS aucun candidat_titre ---
    print("\n" + "=" * 70)
    print(f"CHUNKS INDEXABLES > {SEUIL_MOTS_CHUNK_TYPE2} MOTS SANS AUCUN candidat_titre "
          "(candidats découpage \"type 2\")")
    print("=" * 70)
    positions_avec_candidat_titre = set(candidats_par_header.keys())
    chunks_type2 = [
        c for c in chunks
        if c["categorie"] == "indexable"
        and c["nb_mots"] > SEUIL_MOTS_CHUNK_TYPE2
        and c["position_header"] not in positions_avec_candidat_titre
    ]
    for c in sorted(chunks_type2, key=lambda c: -c["nb_mots"]):
        print(f"  {c['nb_mots']:5} mots | p.{c['pages']} | {c['titre']}")
    print(f"\n  -> {len(chunks_type2)} chunk(s) candidat(s) au découpage type 2")


if __name__ == "__main__":
    main()
