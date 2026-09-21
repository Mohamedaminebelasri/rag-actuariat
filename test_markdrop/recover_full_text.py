# -*- coding: utf-8 -*-
"""recover_full_text.py — Étape A : cherche une sauvegarde exploitable du
DoclingDocument complet (produite par doc.save_as_json()) quelque part
dans le projet, pour éviter une reconversion du PDF (>10 min). Étape B :
si trouvée et valide, régénère sections_brutes.json avec le texte intégral
à la place des extraits à 100 caractères — sinon, s'arrête et explique,
SANS reconvertir automatiquement.

Détection d'un DoclingDocument sauvegardé : ses champs de premier niveau
(vérifiés sur docling_core.types.doc.document.DoclingDocument installé :
schema_name, version, name, origin, furniture, body, groups, texts,
pictures, tables, key_value_items, pages) forment un schéma natif bien
différent de nos formats custom (structure_brute.json etc., qui sont de
simples LISTES d'objets, jamais des dicts avec ce schéma) — pas
d'ambiguïté possible entre les deux.

Étape B : réutilise TEL QUEL le regroupement déjà validé de
build_sections.py (mêmes fonctions, importées, pas dupliquées) — seule
différence, le texte de chaque item est remplacé par son texte intégral
(résolu via son self_ref dans le DoclingDocument rechargé) AVANT le
regroupement en chunks, plutôt que patché après coup. Mêmes chunks, même
chemin hiérarchique, aucun changement de logique de découpage.

Ne modifie jamais structure_finale_v2.json ni structure_brute.json.
Ne reconvertit JAMAIS le PDF ici, quelle que soit l'issue de la recherche.

    python recover_full_text.py [dossier_racine]
"""

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

# Schéma natif d'un export DoclingDocument (vérifié sur l'installation
# réelle du projet, docling-core 2.16.0) — présence de TOUTES ces clés de
# premier niveau = signature suffisante pour distinguer un vrai
# DoclingDocument de nos formats custom.
CLES_DOCLING_DOCUMENT = {"schema_name", "version", "body", "texts", "tables", "pictures"}

# Repères du sanity-check de l'étape 1 (extract_raw_structure.py), sur la
# conversion BRUTE d'origine — sert à valider qu'une sauvegarde retrouvée
# correspond bien à CE document.
N_TABLES_ATTENDU = 23
N_PICTURES_ATTENDU = 96

STRUCTURE_FINALE_V2_PATH = BASE_DIR / "output_structure_brute" / "structure_finale_v2.json"
SECTIONS_BRUTES_PATH = BASE_DIR / "output_structure_brute" / "sections_brutes.json"


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("racine", nargs="?", default=str(BASE_DIR),
                    help="Dossier à partir duquel chercher une sauvegarde DoclingDocument")
    return p.parse_args()


def ressemble_a_docling_document(data):
    """True si le JSON chargé a le schéma natif d'un DoclingDocument
    exporté (pas une de nos listes custom)."""
    return isinstance(data, dict) and CLES_DOCLING_DOCUMENT.issubset(data.keys())


def chercher_sauvegarde(racine):
    """Parcourt tous les .json sous `racine` et retourne la liste des
    fichiers dont le contenu a le schéma d'un DoclingDocument. Ignore
    silencieusement tout JSON illisible/malformé — ce n'est pas ce qu'on
    cherche, pas une erreur à signaler ici."""
    candidats = []
    for chemin in racine.rglob("*.json"):
        try:
            with open(chemin, encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
        if ressemble_a_docling_document(data):
            candidats.append(chemin)
    return candidats


def valider_candidat(chemin):
    """Tente DoclingDocument.load_from_json() sur le candidat, puis
    compare le nombre de tables/pictures aux repères de l'étape 1.
    Retourne (doc, ok, message) — ok=False si le chargement échoue ou si
    les comptes ne correspondent pas (signalé, jamais corrigé
    silencieusement)."""
    from docling_core.types.doc.document import DoclingDocument

    try:
        doc = DoclingDocument.load_from_json(chemin)
    except Exception as e:
        return None, False, f"échec du chargement DoclingDocument.load_from_json() : {e!r}"

    n_texts, n_tables, n_pictures = len(doc.texts), len(doc.tables), len(doc.pictures)
    message = (f"{n_texts} texts, {n_tables} tables (attendu {N_TABLES_ATTENDU}), "
               f"{n_pictures} pictures (attendu {N_PICTURES_ATTENDU})")

    if n_tables != N_TABLES_ATTENDU or n_pictures != N_PICTURES_ATTENDU:
        return doc, False, f"écart avec les repères de l'étape 1 — {message}"

    return doc, True, f"conforme aux repères de l'étape 1 — {message}"


def enrichir_avec_texte_integral(doc, items):
    """Retourne une COPIE de `items` où le champ "extrait" de chaque item
    textuel (tout sauf table/picture/caption/document_index, déjà traités
    à part par build_sections.py) est remplacé par son texte intégral,
    résolu via son self_ref dans le DoclingDocument rechargé — plus de
    troncature à 100 caractères. Si un self_ref ne se résout pas (ne
    devrait pas arriver, mais on ne suppose rien), l'extrait tronqué
    existant est conservé tel quel et le cas est compté pour être
    signalé, jamais silencieux."""
    import build_sections as bs  # réutilise TYPES_NON_TEXTUELS, pas dupliqué

    texte_par_ref = {t.self_ref: t.text for t in doc.texts}

    enrichis = []
    n_resolus, n_fallback = 0, 0
    for it in items:
        nouvel_it = dict(it)
        if it["type"] not in bs.TYPES_NON_TEXTUELS:
            texte_complet = texte_par_ref.get(it.get("self_ref"))
            if texte_complet is not None:
                nouvel_it["extrait"] = texte_complet
                n_resolus += 1
            else:
                n_fallback += 1
        enrichis.append(nouvel_it)

    print(f"  {n_resolus} item(s) texte enrichi(s) avec le texte intégral")
    if n_fallback:
        print(f"  ATTENTION : {n_fallback} item(s) resté(s) sur l'extrait tronqué "
              "(self_ref non résolu dans le DoclingDocument rechargé)")
    return enrichis


def regenerer_sections_brutes(doc, structure_path=STRUCTURE_FINALE_V2_PATH):
    """Étape B complète : charge le fichier structure_finale_*.json donné
    (structure_finale_v2.json par défaut, pour compatibilité), exclut la
    zone QRT, enrichit avec le texte intégral, puis regroupe en chunks
    avec EXACTEMENT la même logique que build_sections.py (fonctions
    importées, pas réimplémentées) — seule différence : le texte n'est
    plus tronqué à 100 caractères. `structure_path` paramétrable pour
    pouvoir régénérer depuis une version plus récente (ex.
    structure_finale_v3.json) sans dupliquer cette fonction."""
    import build_sections as bs

    with open(structure_path, encoding="utf-8") as f:
        items = json.load(f)

    items_narratifs = [it for it in items if not bs.est_zone_qrt(it)]
    print(f"  Items narratifs (hors annexes QRT) : {len(items_narratifs)}")

    items_enrichis = enrichir_avec_texte_integral(doc, items_narratifs)
    sections = bs.construire_sections(items_enrichis)

    with open(SECTIONS_BRUTES_PATH, "w", encoding="utf-8") as f:
        json.dump(sections, f, ensure_ascii=False, indent=2)

    nb_mots_liste = [s["nb_mots"] for s in sections]
    print(f"\n  Chunks régénérés : {len(sections)}")
    if nb_mots_liste:
        print(f"  Nombre de mots (texte intégral, non tronqué) : "
              f"min={min(nb_mots_liste)}  max={max(nb_mots_liste)}  "
              f"médiane={statistics.median(nb_mots_liste):.0f}")
    print(f"\n[export] {len(sections)} chunks écrits dans {SECTIONS_BRUTES_PATH}")


def main():
    args = parse_cli()
    racine = Path(args.racine)

    print("=" * 70)
    print("ÉTAPE A — RECHERCHE D'UNE SAUVEGARDE DoclingDocument")
    print("=" * 70)
    print(f"Recherche sous : {racine.resolve()}")

    candidats = chercher_sauvegarde(racine)

    if not candidats:
        print("\n[RÉSULTAT] Aucun fichier au schéma DoclingDocument trouvé dans le projet.")
        print("\n" + "=" * 70)
        print("ARRÊT — AUCUNE RECONVERSION LANCÉE")
        print("=" * 70)
        print(
            "Aucune sauvegarde exploitable n'a été trouvée. Confirmé en relisant "
            "fix_heading_levels.py lui-même : ce script travaille uniquement sur "
            "structure_brute.json (le format simplifié à 100 caractères) et ne charge, "
            "ne convertit, ni ne sauvegarde jamais de DoclingDocument — la consigne de "
            "sauvegarde donnée à ce tour-là n'a donc jamais pu s'appliquer, puisque ce "
            "script n'a jamais eu de DoclingDocument en main pour commencer.\n"
            "\nPour obtenir le texte intégral, il faut reconvertir le PDF UNE FOIS "
            "(>10 minutes), avec un appel à doc.save_as_json(...) immédiatement après "
            "la conversion et avant tout autre traitement, pour ne plus jamais avoir à "
            "reconvertir ensuite.\n"
            "\nJe ne lance PAS cette reconversion automatiquement. Dites-moi si vous "
            "voulez que je la lance."
        )
        return

    print(f"\n[RÉSULTAT] {len(candidats)} fichier(s) au schéma DoclingDocument trouvé(s) :")
    for c in candidats:
        print(f"  - {c}")

    doc_valide = None
    for chemin in candidats:
        print(f"\nValidation de {chemin} ...")
        doc, ok, message = valider_candidat(chemin)
        print(f"  {message}")
        if ok:
            doc_valide = doc
            print("  -> VALIDE, utilisé pour l'étape B.")
            break
        print("  -> REJETÉ (ne correspond pas aux repères attendus).")

    if doc_valide is None:
        print("\n" + "=" * 70)
        print("ARRÊT — AUCUNE RECONVERSION LANCÉE")
        print("=" * 70)
        print(
            "Des fichiers au schéma DoclingDocument existent mais aucun n'a passé la "
            "validation (chargement ou comptes tables/pictures non conformes). Je ne "
            "reconvertis PAS automatiquement. Dites-moi comment vous voulez procéder."
        )
        return

    print("\n" + "=" * 70)
    print("ÉTAPE B — RÉGÉNÉRATION AVEC TEXTE INTÉGRAL")
    print("=" * 70)
    regenerer_sections_brutes(doc_valide)


if __name__ == "__main__":
    main()
