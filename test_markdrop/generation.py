# -*- coding: utf-8 -*-
# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier écrit la réponse finale donnée à l'utilisateur, à partir du
# meilleur passage trouvé, en citant sa source.
# ------------------------------------------------------------------
"""generation.py — Assemble le contexte de génération à partir du
candidat GAGNANT (fusion RRF + reranking, Décision 028) et de la
résolution de marqueurs [TABLEAU:/IMAGE: self_ref] (Décision 025,
resolution_marqueurs.py), puis appelle le modèle de génération (Gemini,
même client que le juge de reranking) pour produire la réponse finale
citée. Ne touche PAS au retrieval/fusion/reranking — s'applique
strictement APRÈS la sélection du gagnant.

    python generation.py "question"
"""

import base64
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import chemins_visuels as cv
import fusion_reranking as fr
import resolution_marqueurs as rm

BASE_DIR = Path(__file__).parent
CHUNKS_PROPRES_JSON = BASE_DIR / "output_structure_brute" / "chunks_propres.json"

_chunks_cache = None


def _charger_chunks():
    global _chunks_cache
    if _chunks_cache is None:
        with open(CHUNKS_PROPRES_JSON, encoding="utf-8") as f:
            _chunks_cache = json.load(f)
    return _chunks_cache


def _texte_brut_du_chunk(payload):
    """Retrouve le texte brut (avec marqueurs intacts) du chunk gagnant —
    même logique de correspondance que fusion_reranking._contenu_candidat_pour_juge
    (position_header + position_origine + chemin_hierarchique, le payload
    Qdrant ne stocke pas index_corpus)."""
    candidats = [
        c for c in _charger_chunks()
        if c["position_header"] == payload["position_header"]
        and c.get("position_origine") == payload.get("position_origine")
        and c["chemin_hierarchique"] == payload["chemin_hierarchique"]
    ]
    if len(candidats) != 1:
        return None
    return candidats[0]["texte"]


def _image_vers_contenu(chemin_relatif):
    chemin_absolu = cv.chemin_absolu(chemin_relatif)
    with open(chemin_absolu, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}


def construire_contexte(candidat_gagnant):
    """Construit le contexte complet (contenu propre du gagnant + lien
    résolu, si applicable) — retourne (liste_de_blocs_contenu_pour_le_prompt,
    metadonnees) pour transparence/vérification. Dédup + plafond gérés
    par resolution_marqueurs (cf. son docstring)."""
    type_ = candidat_gagnant["type"]
    payload = candidat_gagnant["payload"]
    blocs = []
    metadonnees = {"gagnant_type": type_, "lien_resolu": None}

    # --- Contenu PROPRE du gagnant ---
    blocs.append({"type": "text", "text": f"[CANDIDAT GAGNANT — type={type_}]"})
    blocs.append(fr._contenu_candidat_pour_juge(candidat_gagnant))

    if type_ == "texte":
        # --- Résolution AVANT : marqueurs du chunk gagnant -> visuels liés ---
        texte_brut = _texte_brut_du_chunk(payload)
        if texte_brut is None:
            metadonnees["erreur_texte_brut"] = "chunk gagnant introuvable de façon non ambiguë"
        else:
            deja_inclus = set()  # le gagnant lui-même est du texte, rien à exclure côté visuel
            visuels_resolus = rm.resoudre_visuels_du_chunk(texte_brut, deja_inclus=deja_inclus)
            if visuels_resolus:
                metadonnees["lien_resolu"] = {"sens": "avant", "visuels": visuels_resolus}
                for v in visuels_resolus:
                    blocs.append({"type": "text", "text":
                        f"[VISUEL LIÉ AU TEXTE CI-DESSUS — self_ref {v['self_ref']}]"})
                    blocs.append(_image_vers_contenu(v["chemin_relatif"]))
    else:
        # --- Résolution INVERSE : visuel gagnant -> paragraphe narratif précis ---
        self_ref = payload.get("self_ref")
        lien = rm.resoudre_paragraphe_associe(self_ref)
        if lien is not None:
            metadonnees["lien_resolu"] = {"sens": "inverse", **lien}
            blocs.append({"type": "text", "text":
                f"[PARAGRAPHE NARRATIF LIÉ — {lien['chemin_hierarchique']}, pages {lien['pages']}]\n"
                f"{lien['paragraphe']}"})

    return blocs, metadonnees


def generer_reponse(question, candidat_gagnant):
    """Assemble le contexte (candidat gagnant + lien résolu) et appelle
    Gemini (même client que le reranking) pour produire la réponse finale
    citée. Retourne (reponse_texte, metadonnees_contexte)."""
    blocs_contexte, metadonnees = construire_contexte(candidat_gagnant)

    contenu = [{"type": "text", "text":
        f"Question : {question!r}\n\n"
        "Réponds à cette question en te basant UNIQUEMENT sur le contexte fourni ci-dessous "
        "(extrait(s) de texte et/ou image(s) d'un rapport réglementaire SFCR Solvabilité II). "
        "Cite précisément la source de ta réponse (chemin_hierarchique ou self_ref/type de "
        "visuel). Si le contexte ne permet pas de répondre, dis-le explicitement plutôt que "
        "d'inventer.\n\nContexte :"
    }]
    contenu.extend(blocs_contexte)

    client = fr.get_client_gemini()
    completion = client.chat.completions.create(
        model=fr.GEMINI_MODELE,
        messages=[{"role": "user", "content": contenu}],
        max_tokens=500,
        temperature=0,
    )
    return completion.choices[0].message.content.strip(), metadonnees


def generer_reponse_claude(question, candidat_gagnant):
    """MÊME construction de contexte que generer_reponse (construire_contexte,
    inchangée), mais appelle Claude Haiku 4.5 (bascule suite à
    l'épuisement du quota gratuit Gemini, cf. Décision 031) au lieu de
    Gemini. Convertit les blocs image via fr._convertir_blocs_pour_claude
    (format Anthropic natif, différent d'OpenAI-compatible — cf. sa
    docstring). Retourne (reponse_texte, metadonnees, cout_usd)."""
    blocs_contexte, metadonnees = construire_contexte(candidat_gagnant)

    # Le nom du document n'était jamais transmis explicitement au modèle
    # (seule la formulation générique "rapport réglementaire SFCR
    # Solvabilité II" apparaissait dans le prompt) : le modèle devait
    # deviner/inventer la source depuis le contenu, ce qui produisait
    # parfois "Solvabilité II" ou la mauvaise année. year est
    # déjà présent dans le payload (même champ que le filtre Qdrant,
    # cf. fusion_reranking._filtre_annee) -- on l'injecte ici directement.
    annee_document = candidat_gagnant["payload"].get("year")
    nom_document = f"SFCR Groupama {annee_document}" if annee_document else "le rapport fourni"

    contenu = [{"type": "text", "text":
        f"Question : {question!r}\n\n"
        f"Réponds à cette question en te basant UNIQUEMENT sur le contexte fourni ci-dessous "
        f"(extrait(s) de texte et/ou image(s) du document {nom_document}). "
        f"Le document interrogé est précisément \"{nom_document}\" : commence ta réponse en "
        f"mentionnant explicitement ce nom exact (\"{nom_document}\"), même pour une réponse "
        f"courte ou un simple chiffre, jamais un autre document, une autre année, ni une "
        f"formulation générique comme \"Solvabilité II\" seul. "
        "Cite précisément la source de ta réponse (chemin_hierarchique ou self_ref/type de "
        "visuel). Si le contexte ne permet pas de répondre, dis-le explicitement plutôt que "
        "d'inventer.\n\nContexte :"
    }]
    contenu.extend(blocs_contexte)
    contenu_claude = fr._convertir_blocs_pour_claude(contenu)

    client = fr.get_client_claude()
    message = client.messages.create(
        model=fr.CLAUDE_MODELE_JUGE,
        max_tokens=500,
        temperature=0,
        messages=[{"role": "user", "content": contenu_claude}],
    )
    cout = fr.cout_usd_claude(message.usage)
    return message.content[0].text.strip(), metadonnees, cout


def repondre(question, top_k_final=1):
    """Pipeline complet de bout en bout : fusion RRF + reranking (Décision
    028, inchangé) -> résolution de marqueurs (ce module) -> génération.
    Utilise le candidat en rang 1 du reranking comme gagnant."""
    candidats = fr.pipeline_complet(question, top_k_final=top_k_final)
    gagnant = candidats[0]
    reponse, metadonnees = generer_reponse(question, gagnant)
    return reponse, gagnant, metadonnees


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python generation.py \"question\"")
        sys.exit(1)
    question = " ".join(sys.argv[1:])
    reponse, gagnant, metadonnees = repondre(question)
    print(f"Question : {question}\n")
    print(f"Candidat gagnant : type={gagnant['type']}, payload={gagnant['payload']}\n")
    print(f"Lien résolu : {metadonnees['lien_resolu']}\n")
    print(f"Réponse générée :\n{reponse}")
