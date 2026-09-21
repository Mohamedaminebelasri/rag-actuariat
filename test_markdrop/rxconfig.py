# ------------------------------------------------------------------
# EXPLICATION SIMPLE (pour la démonstration au fondateur) :
# Ce fichier contient la configuration technique de base de l'application
# (son nom, son port). Il n'y a normalement jamais besoin d'y toucher.
# ------------------------------------------------------------------
import reflex as rx

config = rx.Config(
    app_name="sfcr_app",
    show_built_with_reflex=False,
    plugins=[
        rx.plugins.SitemapPlugin(),
        rx.plugins.TailwindV4Plugin(),
        rx.plugins.RadixThemesPlugin(theme=rx.theme(color_mode="light", accent_color="gray")),
    ]
)