"""comparative.py — Sous-onglet "Analyse comparative"."""

from __future__ import annotations

import reflex as rx

from . import data
from .charts import bar_chart_comparatif, radar_comparatif
from .state import AnalyseState
from .theme import ivory, RADIUS_CARD, RADIUS_BTN, RADIUS_PILL, FONT_MONO, FONT_SANS, FONT_SERIF


def chip_societe(soc: rx.Var) -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.text(soc, size="2", weight="medium", style={"font_family": FONT_SANS}),
            rx.icon(
                "x", size=13, cursor="pointer",
                on_click=AnalyseState.retirer_societe_comparaison(soc),
            ),
            spacing="2", align="center",
        ),
        background=ivory.accent_bg,
        color=ivory.accent,
        padding="0.4em 0.5em 0.4em 0.85em",
        border_radius=RADIUS_PILL,
    )


def ajouter_societe() -> rx.Component:
    return rx.cond(
        AnalyseState.au_maximum,
        rx.fragment(),
        rx.select.root(
            rx.select.trigger(
                rx.hstack(rx.icon("plus", size=14), rx.text("Ajouter un assureur", size="2"), spacing="1", align="center"),
                variant="surface",
            ),
            rx.select.content(
                rx.foreach(
                    AnalyseState.societes_disponibles_a_ajouter,
                    lambda s: rx.select.item(s["label"], value=s["id"]),
                ),
            ),
            value="",
            on_change=AnalyseState.ajouter_societe_comparaison,
        ),
    )


def barre_selection_multi() -> rx.Component:
    return rx.box(
        rx.hstack(
            rx.foreach(AnalyseState.societes_comparees, chip_societe),
            ajouter_societe(),
            rx.spacer(),
            rx.text(
                AnalyseState.nb_societes_comparees.to_string() + "/8 assureurs sélectionnés",
                size="2", color=ivory.text_muted, style={"font_family": FONT_MONO}, white_space="nowrap",
            ),
            spacing="3", align="center", width="100%", wrap="wrap",
        ),
        background=ivory.bg_card,
        border=rx.color_mode_cond(light="1px solid #e4e5ea", dark="1px solid #3f3f46"),
        border_radius=RADIUS_CARD,
        padding="1em 1.2em",
        box_shadow=ivory.shadow_card,
        width="100%",
    )


def message_min_2() -> rx.Component:
    return rx.center(
        rx.vstack(
            rx.icon("users", size=32, color=ivory.text_muted),
            rx.text(
                "Sélectionnez au moins 2 assureurs pour comparer", size="4", weight="medium",
                color=ivory.text_secondary, style={"font_family": FONT_SANS}, margin_top="0.6em",
            ),
            spacing="2", align="center",
        ),
        min_height="30vh", width="100%",
    )


def rang_badge(rang: rx.Var) -> rx.Component:
    return rx.cond(
        rang > 0,
        rx.text(
            "#" + rang.to_string(), size="1", weight="bold", color=ivory.text_muted,
            style={"font_family": FONT_MONO}, margin_left="0.4em",
        ),
        rx.fragment(),
    )


def cellule_comparatif(cellule: rx.Var) -> rx.Component:
    couleur = rx.cond(cellule["est_meilleur"], ivory.success, rx.cond(cellule["est_pire"], ivory.danger, ivory.text_primary))
    poids = rx.cond(cellule["est_meilleur"] | cellule["est_pire"], "bold", "normal")
    return rx.table.cell(
        rx.hstack(
            rx.text(cellule["valeur_str"], size="2", weight=poids, color=couleur, style={"font_family": FONT_MONO}),
            rang_badge(cellule["rang"]),
            spacing="0", align="center",
        ),
        text_align="right",
    )


def ligne_kpi(ligne: rx.Var) -> rx.Component:
    return rx.table.row(
        rx.table.cell(
            rx.text(ligne["kpi_label"], size="2", weight="medium", color=ivory.text_primary, style={"font_family": FONT_SANS}),
        ),
        rx.foreach(ligne["cellules"], cellule_comparatif),
        rx.cond(
            AnalyseState.afficher_moyenne,
            rx.table.cell(rx.text(ligne["moyenne_str"], size="2", color=ivory.text_secondary, style={"font_family": FONT_MONO}), text_align="right"),
            rx.fragment(),
        ),
        rx.cond(
            AnalyseState.afficher_mediane,
            rx.table.cell(rx.text(ligne["mediane_str"], size="2", color=ivory.text_secondary, style={"font_family": FONT_MONO}), text_align="right"),
            rx.fragment(),
        ),
        rx.cond(
            AnalyseState.afficher_seuil,
            rx.table.cell(
                rx.cond(
                    ligne["a_seuil"],
                    rx.text(ligne["seuil_str"], size="2", color=ivory.warning, style={"font_family": FONT_MONO}),
                    rx.text("—", size="2", color=ivory.text_muted),
                ),
                text_align="right",
            ),
            rx.fragment(),
        ),
        _hover={"background": ivory.bg_hover},
    )


def en_tete_categorie(code: str, label: str) -> rx.Component:
    est_repliee = AnalyseState.categories_repliees.contains(code)
    n_colonnes_extra = 1 + AnalyseState.nb_societes_comparees
    return rx.table.row(
        rx.table.cell(
            rx.hstack(
                rx.icon(rx.cond(est_repliee, "chevron-right", "chevron-down"), size=14, color=ivory.text_secondary),
                rx.text(
                    f"{code} — {label}", size="1", weight="bold", color=ivory.text_secondary,
                    style={"font_family": FONT_SANS, "letter_spacing": "0.06em", "text_transform": "uppercase"},
                ),
                spacing="2", align="center",
            ),
            col_span=n_colonnes_extra + 1,
            on_click=AnalyseState.basculer_categorie_repliee(code),
            cursor="pointer",
        ),
        background=ivory.bg_secondary,
    )


def section_lignes_categorie(code: str, label: str) -> rx.Component:
    return rx.fragment(
        en_tete_categorie(code, label),
        rx.cond(
            AnalyseState.categories_repliees.contains(code),
            rx.fragment(),
            rx.foreach(AnalyseState.tableau_comparatif[code], ligne_kpi),
        ),
    )


def tableau_comparatif_ui() -> rx.Component:
    return rx.box(
        rx.table.root(
            rx.table.header(
                rx.table.row(
                    rx.table.column_header_cell(
                        rx.text("KPI", size="1", weight="bold", style={"font_family": FONT_SANS, "text_transform": "uppercase", "letter_spacing": "0.05em"}),
                    ),
                    rx.foreach(
                        AnalyseState.societes_comparees,
                        lambda soc: rx.table.column_header_cell(
                            rx.hstack(
                                rx.text(soc, size="1", weight="bold", style={"font_family": FONT_SANS, "text_transform": "uppercase", "letter_spacing": "0.05em"}),
                                rx.icon("arrow-up-down", size=11),
                                spacing="1", align="center", justify="end",
                            ),
                            on_click=AnalyseState.trier_par_colonne(soc),
                            cursor="pointer",
                            text_align="right",
                        ),
                    ),
                    rx.cond(AnalyseState.afficher_moyenne, rx.table.column_header_cell("Moyenne", text_align="right"), rx.fragment()),
                    rx.cond(AnalyseState.afficher_mediane, rx.table.column_header_cell("Médiane", text_align="right"), rx.fragment()),
                    rx.cond(AnalyseState.afficher_seuil, rx.table.column_header_cell("Seuil", text_align="right"), rx.fragment()),
                ),
            ),
            rx.table.body(
                *[section_lignes_categorie(c["code"], c["label"]) for c in data.CATEGORIES],
            ),
            variant="surface", width="100%",
        ),
        overflow_x="auto", width="100%",
        background=ivory.bg_card,
        border=rx.color_mode_cond(light="1px solid #e4e5ea", dark="1px solid #3f3f46"),
        border_radius=RADIUS_CARD,
        box_shadow=ivory.shadow_card,
    )


def filtre_et_options() -> rx.Component:
    def _checkbox(label: str, checked: rx.Var, on_change) -> rx.Component:
        return rx.hstack(
            rx.checkbox(checked=checked, on_change=on_change),
            rx.text(label, size="2", style={"font_family": FONT_SANS}), spacing="1", align="center",
        )

    return rx.hstack(
        rx.select.root(
            rx.select.trigger(placeholder="Catégorie", width="160px"),
            rx.select.content(
                rx.foreach(
                    AnalyseState.categories_filtre,
                    lambda c: rx.select.item(
                        rx.match(
                            c,
                            ("E", "Capital"), ("D", "Valorisation"), ("C", "Risques"), ("A", "Activité"),
                            "Tous",
                        ),
                        value=c,
                    ),
                ),
            ),
            value=AnalyseState.filtre_categorie_comparaison,
            on_change=AnalyseState.changer_filtre_categorie,
        ),
        rx.spacer(),
        _checkbox("Moyenne", AnalyseState.afficher_moyenne, AnalyseState.basculer_moyenne),
        _checkbox("Médiane", AnalyseState.afficher_mediane, AnalyseState.basculer_mediane),
        _checkbox("Seuil réglementaire", AnalyseState.afficher_seuil, AnalyseState.basculer_seuil),
        spacing="4", align="center", width="100%", wrap="wrap",
    )


def icone_alerte(type_: rx.Var) -> rx.Component:
    return rx.match(
        type_,
        ("critique", rx.icon("circle-alert", size=16, color=ivory.danger)),
        ("conforme", rx.icon("circle-check", size=16, color=ivory.success)),
        rx.icon("triangle-alert", size=16, color=ivory.warning),
    )


def ligne_alerte(a: rx.Var) -> rx.Component:
    return rx.hstack(
        icone_alerte(a["type"]),
        rx.text(a["texte"], size="2", color=ivory.text_primary, style={"font_family": FONT_SANS}),
        spacing="2", align="center", padding="0.6em 0",
        border_bottom=rx.color_mode_cond(light="1px solid #f0f0f2", dark="1px solid #303034"),
        width="100%",
    )


def section_alertes() -> rx.Component:
    return rx.cond(
        AnalyseState.alertes.length() > 0,
        rx.box(
            rx.text(
                "Alertes et points d'attention", size="4", weight="medium", color=ivory.text_primary,
                style={"font_family": FONT_SERIF}, font_style="italic", margin_bottom="0.7em",
            ),
            rx.foreach(AnalyseState.alertes, ligne_alerte),
            background=ivory.bg_card,
            border=rx.color_mode_cond(light="1px solid #e4e5ea", dark="1px solid #3f3f46"),
            border_radius=RADIUS_CARD,
            padding="1.2em 1.3em",
            box_shadow=ivory.shadow_card,
            width="100%",
        ),
        rx.fragment(),
    )


def bouton_exporter_comparatif() -> rx.Component:
    return rx.button(
        rx.icon("download", size=15), "Exporter (CSV)",
        on_click=AnalyseState.exporter_comparatif_csv,
        size="2", variant="outline",
        style={"font_family": FONT_SANS, "font_weight": "500", "border_radius": RADIUS_BTN},
    )


def analyse_comparative() -> rx.Component:
    return rx.vstack(
        barre_selection_multi(),
        rx.cond(
            AnalyseState.peut_comparer,
            rx.vstack(
                rx.hstack(
                    rx.box(),
                    rx.spacer(),
                    bouton_exporter_comparatif(),
                    width="100%", align="center",
                ),
                radar_comparatif(),
                bar_chart_comparatif(),
                filtre_et_options(),
                tableau_comparatif_ui(),
                section_alertes(),
                width="100%", align="start", spacing="4",
            ),
            message_min_2(),
        ),
        width="100%", align="start", spacing="4",
    )
