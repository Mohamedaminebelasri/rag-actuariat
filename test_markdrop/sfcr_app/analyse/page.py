"""page.py — Point d'entrée de l'onglet Analyse (2 sous-onglets + nav)."""

from __future__ import annotations

import reflex as rx

from .comparative import analyse_comparative
from .individuelle import analyse_individuelle
from .state import AnalyseState
from .theme import ivory, FONT_SANS, FONT_SERIF, GOOGLE_FONTS_STYLESHEET


def bandeau_demo() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.icon("info", size=15, color=ivory.warning),
            rx.text(
                "Données de démonstration — l'onglet Analyse n'est pas encore connecté au backend réel.",
                size="2", weight="medium", color=ivory.warning, style={"font_family": FONT_SANS},
            ),
            spacing="2", align="center",
        ),
        background=ivory.warning_bg,
        border=rx.color_mode_cond(light="1px solid #fde68a", dark="1px solid #92400e"),
        border_radius="10px",
        padding="0.6em 1em",
        width="100%",
        margin_bottom="1.2em",
    )


def bouton_dark_mode() -> rx.Component:
    return rx.icon_button(
        rx.color_mode_cond(
            light=rx.icon("moon", size=16),
            dark=rx.icon("sun", size=16),
        ),
        on_click=rx.toggle_color_mode,
        variant="outline", size="2", cursor="pointer",
        style={"border_radius": "8px"},
    )


def onglet_nav(label: str, valeur: str, icone: str) -> rx.Component:
    est_actif = AnalyseState.sous_onglet == valeur
    return rx.box(
        rx.hstack(
            rx.icon(icone, size=15),
            rx.text(label, size="2", weight="medium", style={"font_family": FONT_SANS}),
            spacing="2", align="center",
        ),
        on_click=AnalyseState.changer_sous_onglet(valeur),
        padding="0.65em 1.1em",
        border_radius="8px",
        cursor="pointer",
        color=rx.cond(est_actif, ivory.accent, ivory.text_secondary),
        background=rx.cond(est_actif, ivory.accent_bg, "transparent"),
        _hover={"background": rx.cond(est_actif, ivory.accent_bg, ivory.bg_hover)},
        transition="background 0.12s ease, color 0.12s ease",
    )


def barre_sous_onglets() -> rx.Component:
    return rx.hstack(
        onglet_nav("Analyse individuelle", "individuelle", "file-bar-chart"),
        onglet_nav("Analyse comparative", "comparative", "columns-3"),
        spacing="2",
        padding="0.35em",
        background=ivory.bg_secondary,
        border_radius="12px",
        width="fit-content",
    )


def entete_analyse() -> rx.Component:
    return rx.hstack(
        rx.vstack(
            rx.text(
                "SOLVABILITÉ II", size="1", weight="bold", color=ivory.accent,
                style={"font_family": FONT_SANS, "letter_spacing": "0.12em"},
            ),
            rx.heading(
                "Analyse", size="8", weight="medium", color=ivory.text_primary,
                style={"font_family": FONT_SERIF}, font_style="italic", margin_top="0.1em",
            ),
            spacing="0", align="start",
        ),
        rx.spacer(),
        bouton_dark_mode(),
        width="100%", align="center", margin_bottom="1.3em",
    )


def page_analyse() -> rx.Component:
    return rx.box(
        rx.vstack(
            entete_analyse(),
            bandeau_demo(),
            barre_sous_onglets(),
            rx.box(
                rx.cond(
                    AnalyseState.sous_onglet == "individuelle",
                    analyse_individuelle(),
                    analyse_comparative(),
                ),
                width="100%", margin_top="1.5em",
            ),
            width="100%", align="start", spacing="0",
        ),
        width="92%", max_width="1500px", margin="0 auto",
        padding="2em 1.5em 4em 1.5em",
        min_height="100%",
        background=ivory.bg_page,
    )


__all__ = ["page_analyse", "AnalyseState", "GOOGLE_FONTS_STYLESHEET"]
