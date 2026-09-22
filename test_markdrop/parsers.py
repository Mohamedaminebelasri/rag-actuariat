# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier aide à repérer, dans le sommaire du rapport, à quelle
# section appartient chaque page.
# ------------------------------------------------------------------
"""Parseurs neufs pour ingest.py (point 5) :

1. parse_sommaire_lignes(texte) : transforme le texte brut d'une page
   sommaire en liste de {"section_id", "titre", "page"} — pour la couche
   de routage hiérarchique (IDEES_SCALE_UP.md, idée 001).

2. attribuer_section_id(pages_narratives) : associe à chaque page
   narrative (texte déjà passé par Docling, avec titres "## X.Y. ...")
   le dernier section_id rencontré, y compris sur les pages de
   continuation qui ne répètent pas de titre.

Testés sur du texte réel (pages sommaire du document test, pages
narratives du résultat déjà produit) — pas de données inventées.
"""

import re

# Un code de section EIOPA/SFCR ressemble à "A.", "A.1.", "A.1.3.",
# "B.1.2.1.1." (lettre + 0..N groupes ".NOMBRE" + point final) — ou, plus
# rarement dans ce document, sans point final ("A.3 Résultats...").
_CODE = r"[A-Z](?:\.\d+)+\.?|[A-Z]\."
ENTRY_RE = re.compile(rf"^(?:(?P<code>{_CODE})\s+)?(?P<titre>.+?)\s*\.{{4,}}\s*(?P<page>\d{{1,4}})\s*$")
CODE_PREFIX_RE = re.compile(rf"^(?P<code>{_CODE})\s+(?P<reste>.+)$")
FOOTER_RE = re.compile(r"^Groupama\s*[–-]\s*SFCR", re.IGNORECASE)


def parse_sommaire_lignes(texte):
    """Retourne une liste de {"section_id": str|None, "titre": str, "page": int}.
    Gère les titres qui s'étalent sur plusieurs lignes physiques (le code
    de section, s'il existe, est sur la 1ère ligne du titre, pas
    forcément sur celle qui porte le numéro de page)."""
    entries = []
    pending_code = None
    pending_titre_parts = []

    for raw_line in texte.split("\n"):
        line = raw_line.strip()
        if not line or line.upper() == "SOMMAIRE" or FOOTER_RE.match(line) or line.isdigit():
            continue

        m = ENTRY_RE.match(line)
        if m:
            code = m.group("code") or pending_code
            parts = pending_titre_parts + [m.group("titre")]
            titre = " ".join(p for p in parts if p).strip()
            entries.append({"section_id": code, "titre": titre, "page": int(m.group("page"))})
            pending_code, pending_titre_parts = None, []
        else:
            cm = CODE_PREFIX_RE.match(line)
            if cm and pending_code is None:
                pending_code = cm.group("code")
                pending_titre_parts.append(cm.group("reste"))
            else:
                pending_titre_parts.append(line)

    return entries, pending_titre_parts  # 2e valeur : résidu non attaché (devrait être vide)


# Titres narratifs : "## E.2.1. Capital de solvabilité requis (SCR)" —
# même famille de code que le sommaire, en tête de ligne markdown "##".
HEADING_RE = re.compile(rf"^#{{1,3}}\s*(?P<code>{_CODE})\s+(?P<titre>.+?)\s*$", re.MULTILINE)


def attribuer_section_id(pages_narratives):
    """pages_narratives : liste de {"page": int, "texte": str} (texte déjà
    exporté par Docling, avec titres markdown). Retourne {page: section_id},
    en reportant vers l'avant le dernier titre rencontré pour les pages de
    continuation qui n'ouvrent pas de nouvelle section."""
    resultat = {}
    section_courante = None
    for p in pages_narratives:
        titres_page = HEADING_RE.findall(p["texte"])
        if titres_page:
            section_courante = titres_page[-1][0]  # dernier titre ouvert sur cette page
        resultat[p["page"]] = section_courante
    return resultat


if __name__ == "__main__":
    import json
    from pathlib import Path

    import fitz

    BASE_DIR = Path(__file__).parent

    print("=" * 70)
    print("TEST 1 — parse_sommaire_lignes sur les vraies pages sommaire (2-6)")
    print("=" * 70)
    doc = fitz.open(str(BASE_DIR / "input" / "SFCR_2025_Groupe-Groupama_2.pdf"))
    total_entries = 0
    for page_no in range(2, 7):
        texte = doc[page_no - 1].get_text()
        entries, residu = parse_sommaire_lignes(texte)
        print(f"\n--- page {page_no} : {len(entries)} entrées ---")
        for e in entries:
            print(f"  {e['section_id'] or '(sans code)':12} {e['titre'][:70]:70} p.{e['page']}")
        if residu:
            print(f"  [RÉSIDU NON ATTACHÉ] {residu}")
        total_entries += len(entries)
    print(f"\nTotal entrées extraites : {total_entries}")
    doc.close()

    print("\n" + "=" * 70)
    print("TEST 2 — attribuer_section_id sur le résultat narratif déjà produit")
    print("=" * 70)
    with open(BASE_DIR / "output_sectionE_QRT" / "resultat_final.json", encoding="utf-8") as f:
        data = json.load(f)
    pages = data["pages"]
    mapping = attribuer_section_id(pages)
    for p in pages:
        print(f"  page {p['page']:2}  -> section_id = {mapping[p['page']]}")
