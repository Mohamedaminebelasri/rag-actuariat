# -*- coding: utf-8 -*-
"""filter_fake_headers.py — Retire de structure_corrigee.json les
SECTION_HEADER "suspects" : texte vide, ou uniquement composé de
caractères non imprimables / de la zone d'usage privé Unicode (Private
Use Area, U+E000-U+F8FF — c'est là que vit \\uf0a7, une puce de police
symbole/Wingdings non mappée par Docling), ou trop court pour être
exploitable même après nettoyage de ces caractères.

Critères VÉRIFIÉS CONTRE LES VRAIES DONNÉES (structure_corrigee.json, 253
SECTION_HEADER dont 81 sans numérotation reconnue), pas théoriques :
- texte vide, ou qui ne contient QUE des caractères PUA (rien d'autre)
- texte extrêmement court (<= 2 caractères) APRÈS nettoyage des
  caractères PUA, ET sans aucune lettre ni chiffre dans ce qui reste
Ces deux cas se résument à une seule vérification : que reste-t-il du
texte une fois les caractères PUA retirés ?

IMPORTANT — ce que ce script NE fait PAS, volontairement : les libellés
du type "\\uf0a7 Activité" (puce de liste mal classée en SECTION_HEADER
par Docling) NE sont PAS retirés par ce script, même si le \\uf0a7 est un
vrai défaut. Une fois le caractère PUA retiré, "Activité" reste un texte
parfaitement lisible et exploitable — ça ne correspond à AUCUN des 3
critères demandés (vide / PUA seul / illisible après nettoyage). Le
défaut ici est un mauvais TYPE d'item assigné par Docling (ça devrait
être un LIST_ITEM, pas un SECTION_HEADER), pas un texte illisible — ce
n'est pas le problème que ce script est censé traiter (cf. le
comparatif avant/après du script précédent, qui l'avait déjà noté comme
hors de portée d'une correction de NIVEAU). Repérer et déplacer les
puces mal typées serait un script séparé, avec ses propres critères,
pas improvisé ici en douce.

Ne touche à rien d'autre qu'aux SECTION_HEADER : tous les autres types
(text, table, picture, list_item...) sont conservés tels quels, jamais
évalués par ce filtre.

    python filter_fake_headers.py [structure_corrigee.json] [dossier_sortie]
"""

import argparse
import json
import sys
import unicodedata
from pathlib import Path

# Rend la console robuste aux caractères de la zone d'usage privé
# Unicode (ex. ) qui font planter l'affichage sous Windows/cp1252 —
# déjà rencontré avec fix_heading_levels.py. N'affecte que l'affichage,
# pas le JSON exporté (toujours écrit en UTF-8 complet).
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).parent

# Zone d'usage privé Unicode (Private Use Area) — U+E000 à U+F8FF. C'est
# là que vivent les glyphes de puces de polices symbole/Wingdings que
# Docling n'a pas su mapper vers un caractère réel (ex. , 
# observés dans structure_corrigee.json).
PUA_DEBUT, PUA_FIN = 0xE000, 0xF8FF

LONGUEUR_MIN_SANS_LETTRE_NI_CHIFFRE = 2  # "extrêmement court" = 1 ou 2 caractères


def parse_cli():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "structure_json", nargs="?",
        default=str(BASE_DIR / "output_structure_brute" / "structure_corrigee.json"),
        help="structure_corrigee.json déjà produit par fix_heading_levels.py",
    )
    p.add_argument(
        "output_dir", nargs="?", default=str(BASE_DIR / "output_structure_brute"),
        help="Dossier de sortie (reçoit structure_filtree.json)",
    )
    return p.parse_args()


def est_pua(caractere):
    return PUA_DEBUT <= ord(caractere) <= PUA_FIN


def nettoyer_pua(texte):
    """Retire les caractères de la zone d'usage privé Unicode, puis les
    espaces superflus qui en résultent. Sert à juger ce qu'il reste de
    contenu textuel réellement exploitable."""
    sans_pua = "".join(c for c in texte if not est_pua(c))
    return " ".join(sans_pua.split())  # normalise aussi les espaces multiples


def a_lettre_ou_chiffre(texte):
    return any(unicodedata.category(c).startswith(("L", "N")) for c in texte)


def evaluer_section_header(extrait):
    """Retourne (suspect: bool, raison: str|None). Conservateur par
    construction : dès qu'il reste un contenu textuel avec au moins une
    lettre ou un chiffre après nettoyage des caractères PUA, l'item est
    gardé — même partiel, même précédé d'une puce mal reconnue."""
    texte = extrait or ""

    if not texte.strip():
        return True, "texte vide"

    texte_nettoye = nettoyer_pua(texte)

    if not texte_nettoye:
        return True, ("texte composé UNIQUEMENT de caractères non imprimables / de la "
                       "zone d'usage privé Unicode (rien d'exploitable après nettoyage)")

    if len(texte_nettoye) <= LONGUEUR_MIN_SANS_LETTRE_NI_CHIFFRE and not a_lettre_ou_chiffre(texte_nettoye):
        return True, (f"texte extrêmement court après nettoyage ({texte_nettoye!r}, "
                       f"{len(texte_nettoye)} caractère(s)) et sans lettre ni chiffre")

    return False, None


def representation_diagnostic(texte):
    """repr() Python affiche déjà les caractères non imprimables sous
    forme d'échappement lisible (\\uf0a7 par ex.) — suffisant pour le log,
    pas besoin d'un vrai dump hexadécimal séparé pour ce cas."""
    return repr(texte) if texte else "(vide)"


def filtrer(items):
    """Retourne (items_conserves, journal_suppressions). Ne modifie et
    n'évalue QUE les items de type "section_header" — tout le reste
    (text, table, picture, list_item...) passe inchangé, jamais examiné
    par evaluer_section_header."""
    conserves = []
    journal = []

    for item in items:
        if item["type"] != "section_header":
            conserves.append(item)
            continue

        suspect, raison = evaluer_section_header(item["extrait"])
        if suspect:
            journal.append({
                "position": item["position"],
                "pages": item["pages"],
                "texte": representation_diagnostic(item["extrait"]),
                "raison": raison,
            })
        else:
            conserves.append(item)

    return conserves, journal


def main():
    args = parse_cli()
    with open(args.structure_json, encoding="utf-8") as f:
        items = json.load(f)

    n_section_header_avant = sum(1 for it in items if it["type"] == "section_header")

    conserves, journal = filtrer(items)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "structure_filtree.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(conserves, f, ensure_ascii=False, indent=2)

    print("=" * 70)
    print("JOURNAL DES SUPPRESSIONS")
    print("=" * 70)
    if not journal:
        print("\nAucun item supprimé — aucun SECTION_HEADER ne correspond aux "
              "critères (vide / PUA seul / illisible après nettoyage).")
    else:
        for entree in journal:
            print(f"\n  position {entree['position']} — page(s) {entree['pages']}")
            print(f"    texte  : {entree['texte']}")
            print(f"    raison : {entree['raison']}")

    n_section_header_apres = sum(1 for it in conserves if it["type"] == "section_header")

    print("\n" + "=" * 70)
    print("RÉSUMÉ")
    print("=" * 70)
    print(f"  Items retirés               : {len(journal)}")
    print(f"  SECTION_HEADER avant filtre : {n_section_header_avant}")
    print(f"  SECTION_HEADER après filtre : {n_section_header_apres}")
    print(f"\n[export] {len(conserves)} items écrits dans {out_path}")


if __name__ == "__main__":
    main()
