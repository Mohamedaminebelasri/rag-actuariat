"""charts.py — Graphiques recharts : décomposition SCR, radar, barres comparatives."""

from __future__ import annotations

import reflex as rx

from . import data
from .state import AnalyseState
from .theme import ivory, FONT_SANS, FONT_MONO

COULEURS_SCR_MODULE = {
    "SCR non-vie": "#2563eb", "SCR vie": "#7c3aed", "SCR marché": "#0891b2",
    "SCR contrepartie": "#d97706", "SCR opérationnel": "#65a30d", "Diversification": "#dc2626",
}


def graphique_decomposition_scr() -> rx.Component:
    """Barres horizontales : répartition du SCR par module de risque."""
    return rx.cond(
        AnalyseState.scr_decomposition.length() > 0,
        rx.box(
            rx.recharts.bar_chart(
                rx.recharts.cartesian_grid(stroke_dasharray="3 3", horizontal=True, vertical=False),
                rx.recharts.x_axis(type_="number", tick={"font_family": FONT_MONO, "font_size": 11}),
                rx.recharts.y_axis(data_key="module", type_="category", width=140, tick={"font_family": FONT_SANS, "font_size": 12}),
                rx.recharts.graphing_tooltip(),
                rx.recharts.bar(data_key="valeur", radius=[0, 6, 6, 0]),
                data=AnalyseState.scr_decomposition,
                layout="vertical",
                width="100%", height=320,
            ),
            background=ivory.bg_card,
            border=rx.color_mode_cond(light="1px solid #e4e5ea", dark="1px solid #3f3f46"),
            border_radius="12px",
            padding="1.2em",
            width="100%",
        ),
        rx.fragment(),
    )


def radar_comparatif() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(
                "Profil de risque comparé", size="4", weight="medium", color=ivory.text_primary,
                style={"font_family": FONT_SANS},
            ),
            rx.spacer(),
            rx.foreach(
                AnalyseState.societes_comparees,
                lambda soc: rx.box(
                    rx.hstack(
                        rx.box(width="9px", height="9px", border_radius="999px",
                                background=AnalyseState.couleurs_societes[soc]),
                        rx.text(soc, size="1", style={"font_family": FONT_SANS}),
                        spacing="1", align="center",
                    ),
                    on_click=AnalyseState.basculer_visibilite_radar(soc),
                    cursor="pointer",
                    opacity=rx.cond(AnalyseState.societes_radar_masquees.contains(soc), 0.35, 1),
                    padding="0.15em 0.5em",
                    border_radius="999px",
                    _hover={"background": ivory.bg_hover},
                ),
            ),
            spacing="3", width="100%", align="center", wrap="wrap",
        ),
        rx.recharts.radar_chart(
            rx.recharts.polar_grid(),
            rx.recharts.polar_angle_axis(data_key="axe", tick={"font_family": FONT_SANS, "font_size": 12}),
            rx.recharts.polar_radius_axis(tick={"font_family": FONT_MONO, "font_size": 10}),
            rx.recharts.graphing_tooltip(),
            *[
                rx.cond(
                    ~AnalyseState.societes_radar_masquees.contains(soc),
                    rx.recharts.radar(
                        data_key=soc, stroke=AnalyseState.couleurs_societes[soc],
                        fill=AnalyseState.couleurs_societes[soc], fill_opacity=0.15, stroke_width=2,
                    ),
                    rx.fragment(),
                )
                for soc in ["Groupama", "AXA France", "CNP Assurances", "Covéa", "MACSF"]
            ],
            data=AnalyseState.radar_data,
            width="100%", height=340,
        ),
        background=ivory.bg_card,
        border=rx.color_mode_cond(light="1px solid #e4e5ea", dark="1px solid #3f3f46"),
        border_radius="12px",
        padding="1.2em",
        width="100%",
    )


def bar_chart_comparatif() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text("Comparaison par KPI", size="4", weight="medium", color=ivory.text_primary,
                     style={"font_family": FONT_SANS}),
            rx.spacer(),
            rx.select.root(
                rx.select.trigger(placeholder="Choisir un KPI", width="220px"),
                rx.select.content(
                    *[rx.select.item(k["label"], value=k["id"]) for k in data.KPI_DEFINITIONS],
                ),
                value=AnalyseState.kpi_graphique_selectionne,
                on_change=AnalyseState.changer_kpi_graphique,
            ),
            width="100%", align="center", margin_bottom="1em",
        ),
        rx.recharts.bar_chart(
            rx.recharts.cartesian_grid(stroke_dasharray="3 3", vertical=False),
            rx.recharts.x_axis(data_key="societe", tick={"font_family": FONT_SANS, "font_size": 11}),
            rx.recharts.y_axis(tick={"font_family": FONT_MONO, "font_size": 11}),
            rx.recharts.graphing_tooltip(),
            rx.cond(
                AnalyseState.seuil_kpi_graphique >= 0,
                rx.recharts.reference_line(
                    y=AnalyseState.seuil_kpi_graphique, stroke=ivory.danger,
                    stroke_dasharray="4 4", label="Seuil réglementaire",
                ),
                rx.fragment(),
            ),
            rx.recharts.bar(data_key="valeur", fill=ivory.accent, radius=[6, 6, 0, 0]),
            data=AnalyseState.bar_chart_data,
            width="100%", height=300,
        ),
        background=ivory.bg_card,
        border=rx.color_mode_cond(light="1px solid #e4e5ea", dark="1px solid #3f3f46"),
        border_radius="12px",
        padding="1.2em",
        width="100%",
    )
