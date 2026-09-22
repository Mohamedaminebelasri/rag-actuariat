# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier fait la même chose que le précédent, mais pour les tableaux
# et les images, avec un modèle capable de comprendre le contenu visuel.
# ------------------------------------------------------------------
"""build_index_visuels.py — Construit l'INDEX RÉEL (pas un test de
comparaison) des 36 visuels du corpus SFCR 2025 (18 tableaux, 5 images
narratives, 13 pages QRT), avec leurs embeddings Cohere Embed v4 — modèle
retenu à l'étape 4 (cf. Décision 027, DECISIONS.md).

Réutilise la même logique d'encodage que comparer_cohere.py (client
cohere.ClientV2, embed-v4.0, input_type="image" — vérifié dans
comparer_cohere.py, pas deviné ici), mais sur la TOTALITÉ du corpus réel
sous output_structure_brute/visuels/2025/, pas seulement pour comparaison
à un golden set.

LECTURE SEULE sur les fichiers existants (chunks_avec_visuels.json,
images_dedup.json via chemins_visuels.py) — aucune écriture dans ces
fichiers. Seule sortie : index_visuels_cohere.json.

⚠️ Point de vigilance découvert en construisant ce script (pas supposé à
l'écriture, vérifié sur les données réelles) : un visuel narratif (tableau
ou image) peut être référencé par PLUSIEURS self_ref Docling différents,
dans PLUSIEURS chunks différents, à des endroits hiérarchiques distincts
— notamment les logos dédupliqués par pHash (images_dedup.json) qui se
répètent dans le document. Dans ce cas, chemin_hierarchique est laissé à
null plutôt que de choisir arbitrairement un des emplacements, et le
détail complet (chaque self_ref d'origine + son chemin_hierarchique +
ses pages) est conservé dans occurrences_narratives. Un visuel jamais
référencé dans chunks_avec_visuels.json (gap du step 3, ou visuel
purement décoratif non lié au texte) a aussi chemin_hierarchique=null et
occurrences_narratives=null, mais 0 occurrence — distingué explicitement
dans le résumé affiché, car la cause n'est pas la même.

Prérequis :
- pip install cohere numpy  (déjà fait, cf. comparer_cohere.py)
- variable d'environnement COHERE_API_KEY (déjà en place, réutilisée
  telle quelle — aucune nouvelle demande de clé)

    python build_index_visuels.py
"""

import base64
import json
import os
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import chemins_visuels as cv

BASE_DIR = Path(__file__).parent
ANNEE_DOCUMENT = 2025  # paramétrable — même champ que chunks_avec_visuels.json
MODELE_COHERE = "embed-v4.0"  # même modèle que comparer_cohere.py (Décision 027)
PAUSE_ENTRE_APPELS_S = 0.2  # même marge anti-rate-limit que comparer_cohere.py

CHUNKS_AVEC_VISUELS_JSON = BASE_DIR / "output_structure_brute" / "chunks_avec_visuels.json"
DOSSIER_SORTIE = BASE_DIR / "output_structure_brute"
INDEX_SORTIE = DOSSIER_SORTIE / "index_visuels_cohere.json"

N_TABLEAUX_ATTENDU = 18
N_IMAGES_ATTENDU = 5
N_QRT_ATTENDU = 13
N_TOTAL_ATTENDU = N_TABLEAUX_ATTENDU + N_IMAGES_ATTENDU + N_QRT_ATTENDU  # 36


def image_vers_data_url(chemin):
    """Identique à comparer_cohere.py — Cohere Embed v4 attend une image
    encodée en data URL base64, pas un chemin de fichier."""
    with open(chemin, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def encoder_image(co, chemin):
    """Un appel API par image, comme comparer_cohere.py — une image
    corrompue/rejetée reste identifiable individuellement plutôt que de
    devoir deviner laquelle, parmi un lot, a fait échouer l'appel entier."""
    resp = co.embed(
        model=MODELE_COHERE,
        input_type="image",
        embedding_types=["float"],
        images=[image_vers_data_url(chemin)],
    )
    return resp.embeddings.float[0]


def charger_occurrences_narratives():
    """Construit, à partir de chunks_avec_visuels.json (LECTURE SEULE),
    un dictionnaire self_ref_canonique -> liste d'occurrences
    {self_ref_original, chemin_hierarchique, pages}. Un visuel narratif
    peut apparaître dans plusieurs chunks (logos dédupliqués) — on
    construit la liste complète, sans en perdre aucune, le choix d'un
    chemin_hierarchique unique ou non se fait ensuite dans
    resoudre_chemin_hierarchique."""
    with open(CHUNKS_AVEC_VISUELS_JSON, encoding="utf-8") as f:
        chunks = json.load(f)

    mapping_dedup = cv.charger_mapping_dedup(ANNEE_DOCUMENT)
    occurrences = {}
    for chunk in chunks:
        for visuel in chunk.get("visuels", []):
            self_ref_original = visuel["self_ref"]
            self_ref_canonique = mapping_dedup.get(self_ref_original, self_ref_original)
            occurrences.setdefault(self_ref_canonique, []).append({
                "self_ref_original": self_ref_original,
                "chemin_hierarchique": chunk["chemin_hierarchique"],
                "pages": chunk["pages"],
            })
    return occurrences


def resoudre_chemin_hierarchique(self_ref_canonique, occurrences):
    """Retourne (chemin_hierarchique, occurrences_narratives, statut) :
    - statut="unique" : exactement 1 emplacement narratif distinct —
      chemin_hierarchique = cette valeur.
    - statut="ambigu" : plusieurs emplacements narratifs DISTINCTS
      référencent ce même visuel (ex. logo dédupliqué) —
      chemin_hierarchique=None, détail complet dans occurrences_narratives.
    - statut="absent" : aucune occurrence trouvée — chemin_hierarchique=None,
      occurrences_narratives=None.
    Jamais de choix arbitraire entre plusieurs chemins distincts."""
    liste = occurrences.get(self_ref_canonique, [])
    if not liste:
        return None, None, "absent"
    chemins_distincts = sorted({o["chemin_hierarchique"] for o in liste})
    if len(chemins_distincts) == 1:
        return chemins_distincts[0], liste, "unique"
    return None, liste, "ambigu"


def construire_entrees_tableaux_et_images(occurrences):
    """Une entrée par FICHIER PHYSIQUE réel sur disque (pas par self_ref
    Docling — plusieurs self_ref peuvent partager un même fichier après
    dédup des logos). self_ref canonique déduit du nom de fichier,
    cohérent avec la convention de chemins_visuels.py."""
    entrees = []

    for chemin_png in sorted((cv.RACINE_VISUELS / str(ANNEE_DOCUMENT) / "tables").glob("table_*.png")):
        indice = int(chemin_png.stem.split("_")[1])
        self_ref = f"#/tables/{indice}"
        chemin_hier, occ, statut = resoudre_chemin_hierarchique(self_ref, occurrences)
        entrees.append({
            "self_ref": self_ref,
            "chemin_relatif": f"{ANNEE_DOCUMENT}/tables/table_{indice}.png",
            "type": "tableau",
            "pages": sorted({p for o in (occ or []) for p in o["pages"]}),
            "chemin_hierarchique": chemin_hier,
            "occurrences_narratives": occ,
            "statut_narratif": statut,
            "year": ANNEE_DOCUMENT,
        })

    for chemin_png in sorted((cv.RACINE_VISUELS / str(ANNEE_DOCUMENT) / "images").glob("picture_*.png")):
        indice = int(chemin_png.stem.split("_")[1])
        self_ref = f"#/pictures/{indice}"
        chemin_hier, occ, statut = resoudre_chemin_hierarchique(self_ref, occurrences)
        entrees.append({
            "self_ref": self_ref,
            "chemin_relatif": f"{ANNEE_DOCUMENT}/images/picture_{indice}.png",
            "type": "image",
            "pages": sorted({p for o in (occ or []) for p in o["pages"]}),
            "chemin_hierarchique": chemin_hier,
            "occurrences_narratives": occ,
            "statut_narratif": statut,
            "year": ANNEE_DOCUMENT,
        })

    return entrees


def construire_entrees_qrt():
    """Pages QRT : pas d'item Docling (rendu pleine page, pas un élément
    extrait) — self_ref et chemin_hierarchique sont donc None par
    construction, pas par absence de donnée (cf. chemins_visuels.py)."""
    entrees = []
    for chemin_png in sorted((cv.RACINE_VISUELS / str(ANNEE_DOCUMENT) / "qrt_pages").glob("page_*.png")):
        page_no = int(chemin_png.stem.split("_")[1])
        entrees.append({
            "self_ref": None,
            "chemin_relatif": f"{ANNEE_DOCUMENT}/qrt_pages/page_{page_no}.png",
            "type": "page_qrt",
            "pages": [page_no],
            "chemin_hierarchique": None,
            "occurrences_narratives": None,
            "statut_narratif": "hors_texte_narratif",
            "year": ANNEE_DOCUMENT,
        })
    return entrees


def main():
    cle_api = os.environ.get("COHERE_API_KEY")
    if not cle_api:
        print(">>> ARRÊT — variable d'environnement COHERE_API_KEY absente. "
              "Définis-la avant de relancer ce script. Rien exécuté, rien exporté.")
        return

    import cohere
    co = cohere.ClientV2(api_key=cle_api)

    occurrences = charger_occurrences_narratives()
    entrees = construire_entrees_tableaux_et_images(occurrences) + construire_entrees_qrt()

    print(f"Visuels trouvés sur disque : {len(entrees)} (attendu : {N_TOTAL_ATTENDU})")
    if len(entrees) != N_TOTAL_ATTENDU:
        print("  >>> ARRÊT — compte différent de l'attendu avant même l'encodage — "
              "vérifie le corpus avant de continuer. Rien exporté.")
        return

    absents = [e for e in entrees if e["statut_narratif"] == "absent"]
    ambigus = [e for e in entrees if e["statut_narratif"] == "ambigu"]
    if absents:
        print(f"  >>> {len(absents)} visuel(s) narratif(s) JAMAIS référencé(s) dans "
              f"chunks_avec_visuels.json (chemin_hierarchique=null) : "
              f"{[e['self_ref'] for e in absents]}")
    if ambigus:
        print(f"  >>> {len(ambigus)} visuel(s) narratif(s) référencé(s) à PLUSIEURS "
              "emplacements hiérarchiques DISTINCTS (logos dédupliqués) — "
              "chemin_hierarchique laissé à null, détail dans occurrences_narratives : "
              f"{[(e['self_ref'], len({o['chemin_hierarchique'] for o in e['occurrences_narratives']})) for e in ambigus]}")

    print(f"\nEncodage des {len(entrees)} visuels (Cohere {MODELE_COHERE})...")
    for i, entree in enumerate(entrees):
        chemin_absolu = cv.chemin_absolu(entree["chemin_relatif"])
        entree["embedding"] = encoder_image(co, chemin_absolu)
        print(f"  [{i + 1}/{len(entrees)}] {entree['chemin_relatif']} encodé")
        time.sleep(PAUSE_ENTRE_APPELS_S)

    # Vérification de doublon : par chemin_relatif (identifiant réel et
    # unique de chaque fichier physique — self_ref vaut None pour toutes
    # les pages QRT, donc pas un identifiant utilisable pour ce contrôle).
    chemins = [e["chemin_relatif"] for e in entrees]
    doublons = sorted({c for c in chemins if chemins.count(c) > 1})
    if doublons:
        print(f"\n>>> ERREUR — doublon(s) détecté(s) par chemin_relatif : {doublons}. Rien exporté.")
        return

    par_type = {}
    for e in entrees:
        par_type[e["type"]] = par_type.get(e["type"], 0) + 1
    print("\nRésumé par type :")
    for t, n in sorted(par_type.items()):
        print(f"  {t:10} : {n}")
    print(f"  {'TOTAL':10} : {len(entrees)} (attendu : {N_TOTAL_ATTENDU}) — 0 doublon, 0 manquant")

    with open(INDEX_SORTIE, "w", encoding="utf-8") as f:
        json.dump(entrees, f, ensure_ascii=False, indent=2)
    print(f"\n[export] index écrit dans {INDEX_SORTIE}")


if __name__ == "__main__":
    main()
