# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier corrige quelques défauts de texte identifiés lors des
# vérifications, pour que les réponses données plus tard soient bien
# écrites.
# ------------------------------------------------------------------
"""clean_final_text.py — Corrige 3 problèmes de texte confirmés par
detect_anomalies.py sur chunks_avec_metadata.json, SANS toucher à
chemin_hierarchique, pages ni annee_document :

1. PUA résiduel en tête du "titre" des sous-chunks bullet-titre (51 cas
   détectés) — RÉGRESSION : enrichir_avec_texte_integral
   (split_and_merge_chunks.py) réécrit "extrait" depuis le texte BRUT du
   DoclingDocument (jamais nettoyé), ce qui annule le travail déjà fait
   par retype_bullet_headers.py. Corrigé ici avec EXACTEMENT la même
   fonction (commence_par_puce_pua + retirer_puce, importées, pas
   réécrites), réappliquée pour de bon sur le champ "titre" final.

2. PUA résiduel À L'INTÉRIEUR du corps du texte (12 cas détectés) — des
   puces décoratives qui n'ont jamais été des SECTION_HEADER, donc jamais
   couvertes par aucun nettoyage existant. Retiré où qu'il apparaisse
   dans "texte" (chunks indexables), sans toucher au mot qui suit.

3. Fragment de pied de page PDF ("Groupama - SFCR Groupe au 31 décembre
   2025" + numéro de page) collé dans le texte — un artefact de
   pagination, jamais du contenu réel. Vérifié sur les données réelles
   AVANT d'écrire le motif : 70 occurrences dans tout le corpus (pages 7
   à 76, une par page), pas seulement les quelques cas visibles en fin de
   chunk que detect_anomalies.py avait signalés via "texte_coupure_
   suspecte" — retiré partout où il apparaît, pas seulement en fin de
   texte.

nb_mots est RECALCULÉ sur le texte nettoyé pour chaque chunk modifié (pas
dans la liste des champs protégés de la consigne — le laisser tel quel
serait une INCOHÉRENCE avec le texte réellement présent, pas une
neutralité).

Ne corrige PAS les "trop_court" ni les "texte_coupure_suspecte" sans lien
avec le footer (ex. "Néant" ailleurs, légitimement court) — laissés pour
la vérification manuelle de l'étape 6, conformément à la consigne.

Ne modifie jamais chunks_avec_metadata.json (lecture seule) — exporte
chunks_propres.json.

    python clean_final_text.py [chunks_avec_metadata.json] [dossier_sortie]
"""

import argparse
import json
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

# Réutilisées telles quelles depuis retype_bullet_headers.py — même
# logique de nettoyage PUA-en-tête, pas réécrite une 2e fois.
from retype_bullet_headers import commence_par_puce_pua, retirer_puce

# PUA isolé n'importe où dans le texte, + UN espace qui le suit
# immédiatement s'il y en a (même idée que retirer_puce, appliquée ici de
# façon répétée sur tout le corps, pas seulement en tête) — ne retire
# jamais de caractère au-delà de ce seul espace, donc jamais le mot qui suit.
MOTIF_PUA_CORPS = re.compile("[-] ?")

# Pied de page PDF — vérifié sur les données réelles (70 occurrences sur
# SFCR 2025, même forme confirmée sur SFCR 2024 avec "2024" à la place de
# "2025") : "Groupama - SFCR Groupe au 31 décembre <année>" suivi
# d'espaces puis du numéro de page. Classe de caractères [-–] pour
# couvrir tiret simple (confirmé dans le texte extrait) et tiret cadratin
# (orthographe de la consigne) sans dépendre de l'un ou l'autre. \d{4}
# plutôt qu'une année codée en dur : l'année du footer est un fait vérifié
# du texte lui-même (toujours entouré du même contexte exact), pas une
# supposition — ce document n'a que 2 valeurs possibles vérifiées (2024,
# 2025) mais rien n'empêche un futur exercice d'en avoir une 3e.
MOTIF_PIED_DE_PAGE = re.compile(
    r"Groupama\s*[-–]\s*SFCR\s+Groupe\s+au\s+31\s+d[ée]cembre\s+\d{4}[ \t]*\d*"
)


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("chunks_json", nargs="?",
                    default=str(BASE_DIR / "output_structure_brute" / "chunks_avec_metadata.json"))
    p.add_argument("output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"))
    return p.parse_args()


def identifiant(c, idx):
    """Identifiant de log, lisible : index de chargement (toujours
    unique) + position du header parent / position d'origine du
    sous-chunk (absente pour les chunks "inchangés", repli sur
    position_header)."""
    return f"#{idx} (position_header={c['position_header']}, position_origine={c.get('position_origine', c['position_header'])})"


def nettoyer_titre_bullet(titre):
    """Bug #1 : retire un caractère PUA en tête du titre, si présent —
    même fonction que retype_bullet_headers.py."""
    if commence_par_puce_pua(titre):
        return retirer_puce(titre)
    return titre


def nettoyer_pua_corps(texte):
    """Bug #2 : retire tout caractère PUA isolé (+ l'espace qui le suit
    immédiatement, s'il y en a) où qu'il apparaisse dans le texte."""
    return MOTIF_PUA_CORPS.sub("", texte)


def nettoyer_pied_de_page(texte):
    """Bug #3 : retire le fragment de pied de page partout où il
    apparaît, puis recolle proprement les lignes (sans laisser de ligne
    vide ni de double espace à sa place)."""
    texte = MOTIF_PIED_DE_PAGE.sub("", texte)
    texte = re.sub(r"[ \t]*\n[ \t]*\n+", "\n", texte)  # lignes devenues vides -> fusionnées
    texte = re.sub(r"[ \t]{2,}", " ", texte)           # espaces multiples résiduels -> un seul
    return texte.strip()


def main():
    args = parse_cli()
    with open(args.chunks_json, encoding="utf-8") as f:
        chunks = json.load(f)

    log = []  # une entrée par (chunk, type de correction) avec occurrence(s)
    chunks_propres = []
    total_mots_avant, total_mots_apres = 0, 0

    for idx, chunk in enumerate(chunks):
        nouveau = dict(chunk)  # copie — ne modifie jamais l'entrée d'origine
        total_mots_avant += chunk.get("nb_mots", 0)
        id_log = identifiant(chunk, idx)

        # --- Bug #1 : PUA en tête du titre, UNIQUEMENT sur les
        # sous-chunks bullet-titre (les autres titres n'ont jamais eu ce
        # préfixe, donc rien à faire — nettoyer_titre_bullet est sans
        # effet sur eux de toute façon, mais on limite le champ d'action
        # à ce que demande la consigne). ---
        if chunk.get("origine_decoupage") == "bullet_titre":
            titre_avant = nouveau["titre"]
            titre_apres = nettoyer_titre_bullet(titre_avant)
            if titre_apres != titre_avant:
                nouveau["titre"] = titre_apres
                log.append({
                    "chunk": id_log, "type": "PUA-titre",
                    "avant": titre_avant, "apres": titre_apres,
                })

        # --- Bug #2 (chunks indexables uniquement) + Bug #3 (tous les
        # chunks : le pied de page est un artefact de pagination, sans
        # rapport avec le statut indexable/structurel du chunk). ---
        texte_avant = nouveau.get("texte") or ""
        texte_travail = texte_avant

        n_occurrences_footer = len(MOTIF_PIED_DE_PAGE.findall(texte_travail))
        if n_occurrences_footer:
            avant_extrait = MOTIF_PIED_DE_PAGE.search(texte_travail)
            contexte_avant = texte_travail[max(0, avant_extrait.start() - 40):avant_extrait.end() + 10]
            texte_travail = nettoyer_pied_de_page(texte_travail)
            log.append({
                "chunk": id_log, "type": "footer",
                "occurrences": n_occurrences_footer,
                "avant": contexte_avant, "apres": "(retiré)",
            })

        if chunk["categorie"] == "indexable":
            n_occurrences_pua = len(MOTIF_PUA_CORPS.findall(texte_travail))
            if n_occurrences_pua:
                m = MOTIF_PUA_CORPS.search(texte_travail)
                contexte_avant = texte_travail[max(0, m.start() - 30):m.end() + 30]
                texte_nettoye = nettoyer_pua_corps(texte_travail)
                contexte_apres = texte_nettoye[max(0, m.start() - 30):m.start() + 30]
                texte_travail = texte_nettoye
                log.append({
                    "chunk": id_log, "type": "PUA-corps",
                    "occurrences": n_occurrences_pua,
                    "avant": contexte_avant, "apres": contexte_apres,
                })

        if texte_travail != texte_avant:
            nouveau["texte"] = texte_travail
            nouveau["nb_mots"] = len(texte_travail.split())

        total_mots_apres += nouveau.get("nb_mots", 0)
        chunks_propres.append(nouveau)

    # --- Export ---
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "chunks_propres.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(chunks_propres, f, ensure_ascii=False, indent=2)

    # --- Log détaillé, groupé par type de correction ---
    for type_correction in ("PUA-titre", "PUA-corps", "footer"):
        entrees = [l for l in log if l["type"] == type_correction]
        print("=" * 70)
        print(f"{type_correction} — {len(entrees)} chunk(s) corrigé(s)")
        print("=" * 70)
        for l in entrees:
            occ = f" ({l['occurrences']} occurrence(s))" if "occurrences" in l else ""
            print(f"\n  {l['chunk']}{occ}")
            print(f"    avant : {l['avant']!r}")
            print(f"    après : {l['apres']!r}")
        print()

    # --- Réconciliation : on RETIRE du contenu cette fois, donc pas
    # d'égalité stricte attendue — on affiche l'écart exact plutôt que de
    # viser 0. ---
    print("=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Chunks traités                         : {len(chunks_propres)}")
    print(f"  Corrections PUA-titre                   : {sum(1 for l in log if l['type'] == 'PUA-titre')}")
    print(f"  Corrections PUA-corps                   : {sum(1 for l in log if l['type'] == 'PUA-corps')}")
    print(f"  Corrections footer                      : {sum(1 for l in log if l['type'] == 'footer')} "
          f"({sum(l['occurrences'] for l in log if l['type'] == 'footer')} occurrence(s) au total)")
    print(f"\n  Total mots avant nettoyage : {total_mots_avant}")
    print(f"  Total mots après nettoyage : {total_mots_apres}")
    print(f"  Écart (mots retirés)       : {total_mots_avant - total_mots_apres}")
    print(f"\n[export] {len(chunks_propres)} chunks écrits dans {out_path}")


if __name__ == "__main__":
    main()
