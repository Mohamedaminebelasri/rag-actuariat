"""Assistant SFCR Groupama — interface Reflex consommant le pipeline
existant (fusion_reranking.py, generation.py, chemins_visuels.py) sans
en modifier la logique ni les collections Qdrant de production."""

# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier est l'application elle-même : l'interface que vous voyez
# à l'écran, qui reçoit la question, appelle dans l'ordre les étapes
# de recherche et de génération, et affiche la réponse avec sa source.
# ------------------------------------------------------------------

import asyncio
import base64
import json
import os
import re
import sys
from pathlib import Path

import reflex as rx

PARENT_DIR = Path(__file__).parent.parent
if str(PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(PARENT_DIR))

import fusion_reranking as fr  # noqa: E402
import generation as gen  # noqa: E402
import chemins_visuels as cv  # noqa: E402
from sfcr_app.analyse.page import page_analyse  # noqa: E402
from sfcr_app.analyse.theme import GOOGLE_FONTS_STYLESHEET  # noqa: E402

NOM_PROJET = "Iconcilio"
EXEMPLE_QUESTION = "Depuis quand le règlement DORA s'applique-t-il au Groupe Groupama ?"

# --- Étape de reformulation (en amont du pipeline existant, ne le touche pas) ---
# Interrupteur conservé comme filet de sécurité pour une désactivation
# d'urgence future (définir REFORMULATION_ACTIVEE=0 dans l'environnement),
# sans toucher au reste du code. ACTIVÉE PAR DÉFAUT (Décision 044) :
# history-aware query rewriting validé 3/3 en conditions réelles via de
# vrais clics utilisateur (pas de script JS), non-régression confirmée sur
# les 4 types de contenu (texte/tableau/image/QRT). Historique : bascule
# Gemini -> Claude Haiku 4.5 (Décision 039) ; prompt durci après 2 échecs
# de sens (Décision 040) ; extension historique ajoutée puis désactivée
# faute d'infra fiable pour la tester (Décisions 041-043) ; retest concluant
# le 2026-09-14 (Décision 044).
REFORMULATION_ACTIVEE = os.environ.get("REFORMULATION_ACTIVEE", "1") == "1"

REFORMULATION_MODELE = fr.CLAUDE_MODELE_JUGE  # claude-haiku-4-5-20251001, même modèle que le juge/la génération


def _generer_reformulations(question: str, historique_recent: list[dict] | None = None) -> list[str]:
    """Étape UI ajoutée en amont du pipeline (fusion + reranking +
    génération, fusion_reranking.py/generation.py inchangés) : propose 3
    reformulations via un appel Claude Haiku 4.5 isolé et bon marché,
    en réutilisant le client Anthropic déjà partagé par le pipeline
    (fr.get_client_claude()) -- ne modifie ni n'appelle rien d'autre du
    pipeline existant.

    historique_recent (Décision "history-aware query rewriting") : les
    1-2 derniers échanges {question, reponse} du workspace actif, pour
    résoudre les références à la conversation précédente (pronoms, "ce
    tableau", "et pour l'autre année"...) en question autonome -- SANS
    jamais inventer d'information absente de ces échanges. N'affecte
    pas la reformulation si la nouvelle question est déjà autonome."""
    client = fr.get_client_claude()

    contexte_historique = ""
    if historique_recent:
        blocs = [
            f"Échange précédent {i} -- question : {h.get('question', '')!r} / "
            f"réponse : {h.get('reponse', '')!r}"
            for i, h in enumerate(historique_recent, 1)
        ]
        contexte_historique = (
            "\n\nCONTEXTE DE CONVERSATION (les échanges précédents dans ce même "
            "workspace, à utiliser UNIQUEMENT pour résoudre une référence, jamais "
            "pour inventer une information qui n'y figure pas) :\n"
            + "\n".join(blocs)
            + "\n\nSi la NOUVELLE question ci-dessus fait référence à cet historique "
            "(pronom comme \"il\"/\"elle\"/\"ça\", expression comme \"ce tableau\", "
            "\"cette réponse\", \"et pour l'autre année\", \"et lui\"...), résous "
            "cette référence EXPLICITEMENT dans chacune des 3 reformulations, pour "
            "obtenir une question complète et autonome (compréhensible seule, sans "
            "le contexte), en te basant STRICTEMENT sur les échanges ci-dessus. "
            "Si la nouvelle question est déjà autonome et ne fait référence à rien "
            "de précédent, ignore ce contexte et reformule normalement -- ne force "
            "JAMAIS une référence au contexte qui n'existe pas."
        )

    prompt = (
        "Voici une question posée par un utilisateur à un assistant qui interroge le "
        "rapport SFCR du groupe d'assurance Groupama (Solvabilité II) :\n\n"
        f"Question originale : {question!r}"
        f"{contexte_historique}\n\n"
        "Propose exactement 3 reformulations de cette question : corrige l'orthographe "
        "et la grammaire, clarifie la formulation -- mais SANS jamais changer la nature "
        "de ce qui est demandé ni inventer un sens à un mot ambigu. Règles strictes :\n\n"
        "1. Ne change jamais la NATURE de l'information demandée. Si la question demande "
        "un comptage (\"combien de X\"), la reformulation doit rester un comptage -- "
        "jamais un montant, une liste, ou autre chose. Exemple à ne PAS reproduire : "
        "\"combien caisse regional\" ne doit JAMAIS devenir \"quel est le montant de la "
        "caisse régionale\" -- la bonne reformulation est \"Combien de caisses "
        "régionales y a-t-il ?\".\n\n"
        "2. Le document traite du groupe Groupama : tout mot ambigu, mal orthographié ou "
        "syntaxiquement isolé (comme \"la\", \"le\", un article seul en fin de phrase) "
        "doit être résolu en référence à Groupama, jamais interprété comme un nom propre "
        "inconnu. Exemple à ne PAS reproduire : \"parle moi du groupe la\" ne doit JAMAIS "
        "devenir \"le groupe LA\" -- la bonne reformulation est \"Parlez-moi du groupe "
        "Groupama\".\n\n"
        "3. En cas de doute réel sur l'intention (mot illisible, sens impossible à "
        "deviner) : préfère une reformulation minimale et littérale (correction "
        "orthographique seule) plutôt qu'une interprétation créative -- l'utilisateur "
        "garde toujours la possibilité de conserver sa question d'origine, inutile de "
        "deviner à tout prix.\n\n"
        "Réponds UNIQUEMENT avec un objet JSON de la forme "
        '{"reformulations": ["...", "...", "..."]}, sans aucun texte avant ou après.'
    )
    message = client.messages.create(
        model=REFORMULATION_MODELE,
        max_tokens=300,
        temperature=0.3,
        messages=[{"role": "user", "content": prompt}],
    )
    texte = message.content[0].text.strip()
    texte = re.sub(r"^```(?:json)?\s*|\s*```$", "", texte.strip())
    data = json.loads(texte)
    reformulations = data.get("reformulations", [])
    return [r.strip() for r in reformulations if isinstance(r, str) and r.strip()][:3]

_RE_TITRE_REPONSE = re.compile(r"^\s*#{1,3}\s*r[ée]ponse\s*\n+", re.IGNORECASE)
_RE_PARAGRAPHE_SOURCE = re.compile(r"\n\n\**source\s*:?\**.*$", re.IGNORECASE | re.DOTALL)


def _nettoyer_reponse(texte: str) -> str:
    """Nettoyage purement présentationnel côté UI (ne touche pas à
    generation.py) : Claude produit parfois un titre '# Réponse' redondant
    dans une bulle de chat, et sa propre ligne de citation en fin de texte
    fait doublon avec la citation sobre déjà calculée depuis les métadonnées
    du candidat gagnant -- on ne garde qu'une seule citation, la nôtre."""
    texte = _RE_TITRE_REPONSE.sub("", texte)
    texte = _RE_PARAGRAPHE_SOURCE.sub("", texte)
    return texte.strip()


def _traiter_question(question: str, annee: int) -> dict:
    """Appelle le pipeline complet REEL (fusion RRF + reranking Claude
    Haiku + generation) -- fonction module-level (pas une methode de
    State) pour rester utilisable proprement via asyncio.to_thread."""
    top, _cout_juge = fr.pipeline_complet_claude(question, annee=annee)
    gagnant = top[0]
    reponse, _metadonnees, _cout_gen = gen.generer_reponse_claude(question, gagnant)
    reponse = _nettoyer_reponse(reponse)

    type_gagnant = gagnant["type"]
    payload = gagnant["payload"]

    if type_gagnant == "texte":
        chemin = payload.get("chemin_hierarchique") or ""
        segments = chemin.split(" > ")
        dernier_segment = segments[-1] if segments else ""
        pages = payload.get("pages") or []
        pages_str = ", ".join(str(p) for p in pages)
        citation = f"Source : {dernier_segment}" + (f", page{'s' if len(pages) > 1 else ''} {pages_str}" if pages_str else "")
        return {
            "question": question, "annee": str(annee), "type_gagnant": type_gagnant,
            "reponse": reponse, "citation": citation, "image_src": "", "erreur": False,
        }

    chemin_relatif = payload.get("chemin_relatif")
    chemin_absolu = cv.chemin_absolu(chemin_relatif)
    donnees = Path(chemin_absolu).read_bytes()
    b64 = base64.b64encode(donnees).decode("ascii")
    return {
        "question": question, "annee": str(annee), "type_gagnant": type_gagnant,
        "reponse": reponse, "citation": "", "image_src": f"data:image/png;base64,{b64}", "erreur": False,
    }


def _charger_historique_demo_2025() -> list[dict]:
    """Pré-remplissage de démonstration pour le workspace SFCR 2025 --
    10 échanges réellement passés dans le pipeline de production (pas
    de réponse écrite à la main), voir _seed_historique_2025.py et
    DECISIONS.md. Le workspace 2024 n'est volontairement pas concerné."""
    chemin = Path(__file__).parent / "seed_historique_2025.json"
    if chemin.exists():
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    return []


class State(rx.State):
    vue: str = "accueil"  # "accueil" | "solva2" | "sfcr2025" | "sfcr2024"
    question: str = ""
    chargement: bool = False
    historique_2025: list[dict] = _charger_historique_demo_2025()
    historique_2024: list[dict] = []

    # --- Étape de reformulation (ajoutée en amont ; cf. REFORMULATION_ACTIVEE) ---
    chargement_reformulation: bool = False
    attente_choix: bool = False
    reformulations: list[str] = []
    question_en_attente: str = ""

    @rx.event
    def changer_vue(self, valeur: str):
        self.vue = valeur

    @rx.event
    def changer_question(self, valeur: str):
        self.question = valeur

    async def _executer_pipeline(self, question_finale: str):
        """Chemin de pipeline EXISTANT et déjà validé (fusion RRF +
        reranking Claude Haiku + génération), strictement inchangé --
        factorisé ici pour être appelé À L'IDENTIQUE que la reformulation
        soit activée ou non (REFORMULATION_ACTIVEE)."""
        question_finale = question_finale.strip()
        if not question_finale or self.chargement or self.vue not in ("sfcr2025", "sfcr2024"):
            return
        self.chargement = True
        yield
        annee_choisie = 2025 if self.vue == "sfcr2025" else 2024
        try:
            item = await asyncio.to_thread(_traiter_question, question_finale, annee_choisie)
        except Exception as e:
            print(f"[sfcr_app] ERREUR pipeline sur {question_finale!r} (annee={annee_choisie}): {type(e).__name__}: {e}")
            item = {
                "question": question_finale, "annee": str(annee_choisie), "type_gagnant": "",
                "reponse": "Une erreur est survenue lors du traitement de votre question. Merci de réessayer.",
                "citation": "", "image_src": "", "erreur": True,
            }
        if annee_choisie == 2025:
            self.historique_2025 = self.historique_2025 + [item]
        else:
            self.historique_2024 = self.historique_2024 + [item]
        self.chargement = False

    @rx.event
    async def soumettre(self):
        question = self.question.strip()
        if not question or self.chargement or self.chargement_reformulation or self.attente_choix:
            return
        self.question = ""

        if not REFORMULATION_ACTIVEE:
            async for _ in self._executer_pipeline(question):
                yield
            return

        historique_actif = self.historique_2025 if self.vue == "sfcr2025" else self.historique_2024
        historique_recent = [
            {"question": h["question"], "reponse": h["reponse"]}
            for h in historique_actif[-2:]
        ]

        self.question_en_attente = question
        self.chargement_reformulation = True
        yield
        reformulations = []
        try:
            reformulations = await asyncio.to_thread(_generer_reformulations, question, historique_recent)
        except Exception as e:
            print(f"[sfcr_app] ERREUR reformulation sur {question!r}: {type(e).__name__}: {e}")
        self.chargement_reformulation = False

        if reformulations:
            self.reformulations = reformulations
            self.attente_choix = True
        else:
            # Reformulation indisponible : ne jamais bloquer l'utilisateur,
            # on part directement sur la question d'origine.
            async for _ in self._executer_pipeline(question):
                yield

    @rx.event
    async def choisir_reformulation(self, texte_choisi: str):
        self.attente_choix = False
        self.reformulations = []
        self.question_en_attente = ""
        async for _ in self._executer_pipeline(texte_choisi):
            yield


COULEUR_FOND = "#faf9f7"
COULEUR_ACCENT = "#5b6b4f"
COULEUR_TEXTE = "#2b2a28"
COULEUR_TEXTE_DOUX = "#6b6a66"
COULEUR_BORDURE = "#e4e1da"
COULEUR_CARTE = "#ffffff"
COULEUR_FOND_LATERAL = "#f5f4f0"

ICONE_ACCUEIL_SVG = """
<svg viewBox="0 0 200 200" width="150" height="150" xmlns="http://www.w3.org/2000/svg">
  <path d="M55 20 H128 L152 44 V178 H55 Z" stroke="#5b6b4f" stroke-width="4" fill="#eef0ec"/>
  <path d="M128 20 V44 H152 Z" stroke="#5b6b4f" stroke-width="4" fill="#eef0ec"/>
  <line x1="72" y1="72" x2="118" y2="72" stroke="#5b6b4f" stroke-width="4" stroke-linecap="round"/>
  <line x1="72" y1="92" x2="118" y2="92" stroke="#5b6b4f" stroke-width="4" stroke-linecap="round"/>
  <line x1="72" y1="112" x2="102" y2="112" stroke="#5b6b4f" stroke-width="4" stroke-linecap="round"/>
  <circle cx="129" cy="142" r="19" stroke="#5b6b4f" stroke-width="5" fill="#faf9f7"/>
  <line x1="143" y1="156" x2="161" y2="174" stroke="#5b6b4f" stroke-width="5" stroke-linecap="round"/>
</svg>
"""

DOCUMENTS = [
    {
        "nom": "Solvabilité II",
        "description": "Directive 2009/138/CE — 312 articles",
        "statut": "Bientôt disponible",
        "vue": "solva2",
        "disponible": False,
    },
    {
        "nom": "SFCR Groupama 2025",
        "description": "Rapport sur la solvabilité et la situation financière — plus de 75 pages",
        "statut": "Disponible",
        "vue": "sfcr2025",
        "disponible": True,
    },
    {
        "nom": "SFCR Groupama 2024",
        "description": "Rapport sur la solvabilité et la situation financière — plus de 70 pages",
        "statut": "Disponible",
        "vue": "sfcr2024",
        "disponible": True,
    },
    {
        "nom": "Analyse",
        "description": "20 KPIs par rapport SFCR — analyse individuelle et comparaison multi-assureurs",
        "statut": "Disponible",
        "vue": "analyse",
        "disponible": True,
    },
]


def item_nav(label: str, vue_cible: str, sous_titre: str | None = None) -> rx.Component:
    est_actif = State.vue == vue_cible
    contenu = [rx.text(label, size="2", weight="medium", color=rx.cond(est_actif, COULEUR_TEXTE, COULEUR_TEXTE_DOUX))]
    if sous_titre:
        contenu.append(rx.text(sous_titre, size="1", color=COULEUR_TEXTE_DOUX))
    return rx.box(
        rx.vstack(*contenu, spacing="0", align="start"),
        on_click=State.changer_vue(vue_cible),
        width="100%",
        padding="0.65em 0.9em",
        border_radius="8px",
        background=rx.cond(est_actif, "#eef0ec", "transparent"),
        border_left=rx.cond(est_actif, f"3px solid {COULEUR_ACCENT}", "3px solid transparent"),
        cursor="pointer",
        _hover={"background": "#eef0ec"},
        transition="background 0.1s ease",
    )


def barre_laterale() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.box(
                rx.heading(NOM_PROJET, size="4", weight="bold", color=COULEUR_TEXTE),
                rx.text("Assistant réglementaire", size="1", color=COULEUR_TEXTE_DOUX, margin_top="0.1em"),
                padding="1.4em 1.1em 1.2em 1.1em",
                on_click=State.changer_vue("accueil"),
                cursor="pointer",
                width="100%",
                _hover={"background": "#eef0ec"},
                transition="background 0.1s ease",
            ),
            rx.box(height="1px", background=COULEUR_BORDURE, width="100%", margin_bottom="0.7em"),
            rx.vstack(
                item_nav("Solvabilité II", "solva2", sous_titre="Bientôt disponible"),
                item_nav("SFCR Groupama 2025", "sfcr2025"),
                item_nav("SFCR Groupama 2024", "sfcr2024"),
                item_nav("Analyse", "analyse"),
                spacing="1",
                width="100%",
                padding_x="0.6em",
            ),
            spacing="0",
            width="100%",
            align="start",
        ),
        width="230px",
        min_width="230px",
        height="100%",
        border_right=f"1px solid {COULEUR_BORDURE}",
        background=COULEUR_FOND_LATERAL,
    )


def carte_document(doc: dict) -> rx.Component:
    return rx.vstack(
        rx.box(
            rx.text(
                doc["statut"],
                size="2",
                weight="medium",
                color=COULEUR_ACCENT if doc["disponible"] else COULEUR_TEXTE_DOUX,
            ),
            background="#eef0ec" if doc["disponible"] else "#eeeeee",
            padding="0.3em 0.85em",
            border_radius="999px",
            white_space="nowrap",
        ),
        rx.text(doc["nom"], size="5", weight="medium", color=COULEUR_TEXTE, margin_top="0.9em"),
        rx.text(doc["description"], size="3", color=COULEUR_TEXTE_DOUX, margin_top="0.4em", line_height="1.5"),
        on_click=State.changer_vue(doc["vue"]),
        align="start",
        spacing="0",
        width="100%",
        min_height="150px",
        padding="1.6em 1.8em",
        border=f"1px solid {COULEUR_BORDURE}",
        border_radius="12px",
        background=COULEUR_CARTE,
        cursor="pointer",
        _hover={"border_color": COULEUR_ACCENT},
        transition="border-color 0.15s ease",
    )


def page_accueil() -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.html(ICONE_ACCUEIL_SVG),
            rx.heading(NOM_PROJET, size="9", weight="medium", color=COULEUR_TEXTE, margin_top="0.5em"),
            rx.text(
                "Assistant réglementaire",
                size="5",
                color=COULEUR_ACCENT,
                weight="medium",
                margin_top="0.3em",
            ),
            rx.text(
                "Interrogez des rapports réglementaires (SFCR, Solvabilité II) en langage "
                "naturel et retrouvez directement l'information pertinente — texte, tableau, "
                "image ou annexe QRT selon où se trouve la réponse — avec sa source précise.",
                size="4",
                color=COULEUR_TEXTE_DOUX,
                text_align="center",
                max_width="700px",
                margin_top="1.3em",
                line_height="1.65",
            ),
            rx.text(
                "Documents disponibles",
                size="2",
                weight="medium",
                letter_spacing="0.08em",
                color=COULEUR_TEXTE_DOUX,
                margin_top="3em",
                margin_bottom="1em",
            ),
            rx.grid(
                *[carte_document(doc) for doc in DOCUMENTS],
                columns="3",
                spacing="5",
                width="100%",
            ),
            spacing="0",
            align="center",
            width="90%",
            max_width="1300px",
            margin="0 auto",
            padding_y="3.5em",
        ),
        width="100%",
        min_height="100%",
        background=(
            "linear-gradient(rgba(250,249,247,0.93), rgba(250,249,247,0.93)), "
            "url('/accueil_fond.jpg')"
        ),
        background_size="cover",
        background_position="center",
    )


def page_solva2() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.icon("clock", size=30, color=COULEUR_TEXTE_DOUX),
            rx.heading("Solvabilité II", size="6", weight="medium", color=COULEUR_TEXTE, margin_top="0.7em"),
            rx.text(
                "Cet espace donnera bientôt accès à la directive 2009/138/CE. "
                "Le branchement technique sera réalisé dans une prochaine étape.",
                size="3",
                color=COULEUR_TEXTE_DOUX,
                text_align="center",
                max_width="380px",
                margin_top="0.6em",
                line_height="1.6",
            ),
            spacing="0",
            align="center",
        ),
        width="100%",
        min_height="100%",
    )


def badge_type(type_gagnant: str) -> rx.Component:
    """Badge à couleurs fixes (pas rx.badge) : le thème clair/sombre de
    Radix suit par défaut la préférence système du navigateur (constaté :
    localStorage 'theme'='system'), ce qui rendait le texte du badge
    presque invisible sur fond blanc quand le système est en mode sombre.
    Des couleurs explicites garantissent un rendu sobre et stable,
    indépendant du thème du poste utilisé pour la démo."""
    return rx.box(
        rx.match(
            type_gagnant,
            ("texte", "Texte"),
            ("tableau", "Tableau"),
            ("image", "Image"),
            ("page_qrt", "Annexe QRT"),
            "",
        ),
        background="#eef0ec",
        color=COULEUR_TEXTE_DOUX,
        font_size="0.75em",
        font_weight="500",
        padding="0.2em 0.7em",
        border_radius="999px",
        display="inline-block",
    )


def bulle_question(item: dict) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(
                rx.match(item["annee"], ("2024", "SFCR 2024"), ("SFCR 2025")),
                size="2",
                weight="medium",
                color=COULEUR_ACCENT,
            ),
            justify="start",
            margin_bottom="0.4em",
        ),
        rx.text(item["question"], size="5", weight="medium", color=COULEUR_TEXTE),
        align_self="flex-end",
        max_width="80%",
        background=COULEUR_ACCENT,
        background_color="#eef1ea",
        padding="1em 1.3em",
        border_radius="14px 14px 3px 14px",
        margin_left="auto",
    )


def bulle_reponse(item: dict) -> rx.Component:
    return rx.box(
        rx.cond(
            item["erreur"],
            rx.hstack(
                rx.icon("triangle-alert", size=16, color="#a35a3a"),
                rx.text(item["reponse"], size="3", color="#7a4a30"),
                spacing="2",
                align="center",
            ),
            rx.vstack(
                rx.hstack(
                    badge_type(item["type_gagnant"]),
                    spacing="2",
                ),
                rx.cond(
                    item["image_src"] != "",
                    rx.vstack(
                        rx.image(
                            src=item["image_src"],
                            max_width="100%",
                            border_radius="8px",
                            border=f"1px solid {COULEUR_BORDURE}",
                        ),
                        rx.markdown(
                            item["reponse"],
                            margin_top="0.6em",
                            color=COULEUR_TEXTE,
                            font_size="1.1em",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    rx.vstack(
                        rx.markdown(item["reponse"], color=COULEUR_TEXTE, font_size="1.1em"),
                        rx.text(item["citation"], size="2", color=COULEUR_TEXTE_DOUX, margin_top="0.5em"),
                        spacing="1",
                        width="100%",
                    ),
                ),
                spacing="3",
                width="100%",
            ),
        ),
        max_width="80%",
        background=COULEUR_CARTE,
        padding="1.1em 1.3em",
        border_radius="3px 14px 14px 14px",
        border=f"1px solid {COULEUR_BORDURE}",
        box_shadow="0 1px 2px rgba(0,0,0,0.04)",
    )


def echange(item: dict) -> rx.Component:
    return rx.vstack(
        bulle_question(item),
        bulle_reponse(item),
        spacing="2",
        width="100%",
        margin_bottom="1.6em",
    )


def indicateur_chargement() -> rx.Component:
    return rx.hstack(
        rx.spinner(size="2", color=COULEUR_ACCENT),
        rx.text("Analyse du rapport en cours…", size="2", color=COULEUR_TEXTE_DOUX),
        spacing="2",
        align="center",
        padding="0.8em 0",
    )


def zone_historique(historique) -> rx.Component:
    return rx.cond(
        (historique.length() == 0) & ~State.chargement,
        rx.center(
            rx.vstack(
                rx.icon("message-circle-question", size=28, color=COULEUR_TEXTE_DOUX),
                rx.text(
                    "Posez une question sur le rapport SFCR pour commencer.",
                    size="4",
                    color=COULEUR_TEXTE_DOUX,
                ),
                spacing="3",
                align="center",
            ),
            min_height="30vh",
            width="100%",
        ),
        rx.vstack(
            rx.foreach(historique, echange),
            rx.cond(State.chargement, indicateur_chargement()),
            width="100%",
        ),
    )


def zone_saisie() -> rx.Component:
    desactive = State.chargement_reformulation | State.attente_choix
    return rx.box(
        rx.hstack(
            rx.input(
                value=State.question,
                on_change=State.changer_question,
                placeholder=EXEMPLE_QUESTION,
                size="3",
                width="100%",
                variant="surface",
                disabled=desactive,
                on_key_down=lambda k: rx.cond(k == "Enter", State.soumettre(), rx.noop()),
            ),
            rx.button(
                "Envoyer",
                on_click=State.soumettre,
                loading=State.chargement,
                disabled=desactive,
                size="3",
                color_scheme="gray",
                variant="solid",
                style={"background_color": COULEUR_ACCENT},
            ),
            spacing="3",
            width="100%",
            align="center",
        ),
        width="100%",
        padding_top="1.2em",
        border_top=f"1px solid {COULEUR_BORDURE}",
        margin_top="1em",
        background=COULEUR_FOND,
        position="sticky",
        bottom="0",
    )


def zone_reformulation() -> rx.Component:
    return rx.cond(
        State.chargement_reformulation,
        rx.hstack(
            rx.spinner(size="2", color=COULEUR_ACCENT),
            rx.text("Reformulation de la question en cours…", size="3", color=COULEUR_TEXTE_DOUX),
            spacing="2",
            align="center",
            padding="1em 0",
        ),
        rx.cond(
            State.attente_choix,
            rx.box(
                rx.text("Votre question :", size="2", color=COULEUR_TEXTE_DOUX),
                rx.text(
                    State.question_en_attente,
                    size="3",
                    color=COULEUR_TEXTE,
                    font_style="italic",
                    margin_top="0.2em",
                    margin_bottom="1.1em",
                ),
                rx.text(
                    "Choisissez une reformulation, ou gardez votre question telle quelle :",
                    size="2",
                    weight="medium",
                    color=COULEUR_TEXTE_DOUX,
                    margin_bottom="0.8em",
                ),
                rx.vstack(
                    rx.foreach(
                        State.reformulations,
                        lambda r: rx.box(
                            rx.text(r, size="3", color=COULEUR_TEXTE),
                            on_click=State.choisir_reformulation(r),
                            width="100%",
                            padding="0.9em 1.2em",
                            border=f"1px solid {COULEUR_BORDURE}",
                            border_radius="10px",
                            background=COULEUR_CARTE,
                            cursor="pointer",
                            _hover={"border_color": COULEUR_ACCENT},
                            transition="border-color 0.15s ease",
                        ),
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.box(
                    rx.text(
                        "Garder ma question telle quelle →",
                        size="2",
                        weight="medium",
                        color=COULEUR_ACCENT,
                    ),
                    on_click=State.choisir_reformulation(State.question_en_attente),
                    margin_top="1.1em",
                    cursor="pointer",
                    _hover={"text_decoration": "underline"},
                ),
                width="100%",
                padding="1.3em 1.4em",
                border=f"1px solid {COULEUR_BORDURE}",
                border_radius="12px",
                background="#f5f4f0",
                margin_bottom="1.5em",
            ),
            rx.fragment(),
        ),
    )


def entete(annee_label: str) -> rx.Component:
    return rx.box(
        rx.vstack(
            rx.text(
                f"GROUPAMA · SFCR {annee_label}",
                size="2",
                weight="medium",
                letter_spacing="0.12em",
                color=COULEUR_ACCENT,
            ),
            rx.heading(
                "Assistant SFCR",
                size="8",
                weight="medium",
                color=COULEUR_TEXTE,
                margin_top="0.15em",
            ),
            rx.text(
                "Interrogez le rapport sur la solvabilité et la situation financière du Groupe.",
                size="4",
                color=COULEUR_TEXTE_DOUX,
                margin_top="0.3em",
            ),
            align="start",
            spacing="0",
        ),
        width="100%",
        padding_bottom="2em",
        border_bottom=f"1px solid {COULEUR_BORDURE}",
        margin_bottom="2em",
    )


def page_sfcr(annee_label: str, historique) -> rx.Component:
    return rx.box(
        entete(annee_label),
        zone_historique(historique),
        zone_reformulation(),
        zone_saisie(),
        width="90%",
        max_width="1000px",
        margin="0 auto",
        padding_x="1.5em",
        padding_y="2em",
    )


def contenu_principal() -> rx.Component:
    return rx.match(
        State.vue,
        ("solva2", page_solva2()),
        ("sfcr2025", page_sfcr("2025", State.historique_2025)),
        ("sfcr2024", page_sfcr("2024", State.historique_2024)),
        ("analyse", page_analyse()),
        page_accueil(),
    )


def index() -> rx.Component:
    return rx.hstack(
        barre_laterale(),
        rx.box(
            contenu_principal(),
            flex="1",
            height="100vh",
            overflow_y="auto",
            background=COULEUR_FOND,
        ),
        spacing="0",
        width="100%",
        height="100vh",
        align="stretch",
    )


app = rx.App(
    style={
        "font_family": "'Georgia', 'Iowan Old Style', serif",
    },
    stylesheets=[GOOGLE_FONTS_STYLESHEET],
)
app.add_page(index, title=NOM_PROJET)
