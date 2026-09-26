"""individuelle.py — Sous-onglet "Analyse individuelle"."""

from __future__ import annotations

import reflex as rx

from . import data
from .charts import graphique_decomposition_scr
from .state import AnalyseState
from .theme import ivory, RADIUS_CARD, RADIUS_BTN, RADIUS_PILL, FONT_MONO, FONT_SANS, FONT_SERIF

_COULEUR_SEUIL = {
    "success": (ivory.success, ivory.success_bg),
    "warning": (ivory.warning, ivory.warning_bg),
    "danger": (ivory.danger, ivory.danger_bg),
    "neutre": (ivory.text_primary, ivory.bg_secondary),
}


def selecteur_pdf() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.icon("file-text", size=18, color=ivory.text_secondary),
            rx.select.root(
                rx.select.trigger(
                    placeholder="Sélectionnez un rapport SFCR…",
                    width="100%",
                    style={"font_family": FONT_SANS},
                ),
                rx.select.content(
                    rx.foreach(AnalyseState.sfcr_disponibles, lambda s: rx.select.item(s["label"], value=s["id"])),
                ),
                value=AnalyseState.societe_selectionnee,
                on_change=AnalyseState.selectionner_societe,
                size="3",
                width="100%",
            ),
            rx.cond(
                AnalyseState.a_une_societe_selectionnee,
                rx.box(
                    rx.hstack(
                        rx.icon("circle-check", size=13, color=ivory.success),
                        rx.text("Chargé", size="1", weight="medium", color=ivory.success, style={"font_family": FONT_SANS}),
                        spacing="1", align="center",
                    ),
                    background=ivory.success_bg,
                    padding="0.3em 0.75em",
                    border_radius=RADIUS_PILL,
                    white_space="nowrap",
                ),
                rx.fragment(),
            ),
            spacing="3", align="center", width="100%",
        ),
        background=ivory.bg_card,
        border=rx.color_mode_cond(light="1px solid #e4e5ea", dark="1px solid #3f3f46"),
        border_radius=RADIUS_CARD,
        padding="1em 1.2em",
        box_shadow=ivory.shadow_card,
        width="100%",
    )


def etat_vide() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.icon("file-search", size=36, color=ivory.text_muted),
            rx.text(
                "Sélectionnez un rapport SFCR pour voir l'analyse",
                size="4", weight="medium", color=ivory.text_secondary,
                style={"font_family": FONT_SANS}, margin_top="0.8em",
            ),
            spacing="2", align="center",
        ),
        min_height="40vh", width="100%",
    )


def badge_confiance(confiance: rx.Var, chapitre: rx.Var, page: rx.Var) -> rx.Component:
    est_verifie = confiance == "verified"
    return rx.tooltip(
        rx.box(
            rx.cond(
                est_verifie,
                rx.hstack(rx.icon("shield-check", size=11), rx.text("Vérifié", size="1"), spacing="1", align="center"),
                rx.hstack(rx.icon("sparkles", size=11), rx.text("Extrait par IA", size="1"), spacing="1", align="center"),
            ),
            color=rx.cond(est_verifie, ivory.success, ivory.warning),
            background=rx.cond(est_verifie, ivory.success_bg, ivory.warning_bg),
            padding="0.15em 0.55em",
            border_radius=RADIUS_PILL,
            font_weight="500",
            style={"font_family": FONT_SANS},
            width="fit-content",
        ),
        content=rx.cond(
            page != None,  # noqa: E711 - Var comparison, not Python identity
            f"Source : chapitre {chapitre}, page {page}",
            f"Source : chapitre {chapitre}",
        ),
    )


def kpi_card(kpi: rx.Var) -> rx.Component:
    couleur_valeur = rx.match(
        kpi["couleur_seuil"],
        ("success", ivory.success),
        ("warning", ivory.warning),
        ("danger", ivory.danger),
        ivory.text_primary,
    )
    return rx.box(
        rx.hstack(
            rx.text(kpi["code"], size="1", weight="bold", color=ivory.text_muted, style={"font_family": FONT_MONO}),
            rx.spacer(),
            badge_confiance(kpi["confiance"], kpi["chapitre_source"], kpi["page_source"]),
            width="100%", align="center",
        ),
        rx.text(
            kpi["label"], size="2", weight="medium", color=ivory.text_secondary,
            style={"font_family": FONT_SANS}, margin_top="0.6em",
        ),
        rx.text(
            kpi["valeur_str"], size="7", weight="bold", color=couleur_valeur,
            style={"font_family": FONT_MONO}, margin_top="0.15em", line_height="1.15",
        ),
        rx.cond(
            kpi["a_variation"],
            rx.hstack(
                rx.icon(
                    rx.cond(kpi["variation_positive"], "trending-up", "trending-down"),
                    size=13,
                    color=rx.cond(kpi["variation_positive"], ivory.success, ivory.danger),
                ),
                rx.text(
                    kpi["variation_str"], size="2", weight="medium",
                    color=rx.cond(kpi["variation_positive"], ivory.success, ivory.danger),
                    style={"font_family": FONT_MONO},
                ),
                rx.text("vs N-1", size="1", color=ivory.text_muted, style={"font_family": FONT_SANS}),
                spacing="1", align="center", margin_top="0.35em",
            ),
            rx.box(height="1.4em", margin_top="0.35em"),
        ),
        rx.text(
            kpi["description"], size="1", color=ivory.text_muted,
            style={"font_family": FONT_SANS}, margin_top="0.5em", line_height="1.4",
        ),
        background=ivory.bg_card,
        border=rx.color_mode_cond(light="1px solid #e4e5ea", dark="1px solid #3f3f46"),
        border_radius=RADIUS_CARD,
        padding="1.1em 1.2em",
        box_shadow=ivory.shadow_card,
        transition="box-shadow 0.15s ease, transform 0.15s ease",
        _hover={"box_shadow": "0 4px 12px rgba(0,0,0,0.08)", "transform": "translateY(-1px)"},
        height="100%",
    )


def section_categorie(code: str, label: str) -> rx.Component:
    return rx.vstack(
        rx.heading(
            f"{code} — {label}", size="4", weight="medium", color=ivory.text_primary,
            style={"font_family": FONT_SERIF}, font_style="italic",
        ),
        rx.grid(
            rx.foreach(AnalyseState.kpis_par_categorie[code], kpi_card),
            columns=rx.breakpoints(initial="1", sm="2", lg="4"),
            spacing="4", width="100%",
        ),
        spacing="3", width="100%", align="start", margin_bottom="2em",
    )


def bouton_exporter() -> rx.Component:
    return rx.button(
        rx.icon("download", size=15),
        "Exporter (CSV)",
        on_click=AnalyseState.exporter_csv,
        size="2", variant="outline",
        style={"font_family": FONT_SANS, "font_weight": "500", "border_radius": RADIUS_BTN},
    )


def analyse_individuelle() -> rx.Component:
    return rx.vstack(
        selecteur_pdf(),
        rx.cond(
            AnalyseState.a_une_societe_selectionnee,
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        AnalyseState.label_societe_selectionnee, size="6", weight="medium",
                        color=ivory.text_primary, style={"font_family": FONT_SERIF}, font_style="italic",
                    ),
                    rx.spacer(),
                    bouton_exporter(),
                    width="100%", align="center", margin_top="1.5em", margin_bottom="0.5em",
                ),
                *[section_categorie(c["code"], c["label"]) for c in data.CATEGORIES],
                rx.divider(margin_y="1em"),
                rx.text(
                    "Décomposition du SCR par module de risque", size="4", weight="medium",
                    color=ivory.text_primary, style={"font_family": FONT_SERIF}, font_style="italic",
                    margin_bottom="1em",
                ),
                graphique_decomposition_scr(),
                width="100%", align="start",
            ),
            etat_vide(),
        ),
        width="100%", align="start", spacing="4",
    )
