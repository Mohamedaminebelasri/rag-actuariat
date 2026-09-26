"""theme.py — Design tokens direction "Ivory" (onglet Analyse uniquement).

Palette et typographie auto-contenues, distinctes du thème existant du
reste de l'app (Georgia/vert olive) — cf. sfcr_app.py. Chaque token
couleur est exposé sous forme de fonction retournant un rx.Var conditionné
sur rx.color_mode (rx.color_mode_cond), jamais une valeur figée, pour que
CHAQUE composant supporte le dark mode sans logique dupliquée.
"""

import reflex as rx

# --- Polices (Google Fonts, chargées via stylesheets dans l'app) ---
FONT_SERIF = "'Instrument Serif', serif"
FONT_SANS = "'DM Sans', sans-serif"
FONT_MONO = "'JetBrains Mono', monospace"

GOOGLE_FONTS_STYLESHEET = (
    "https://fonts.googleapis.com/css2?"
    "family=Instrument+Serif:ital@0;1&"
    "family=DM+Sans:wght@400;500;600;700&"
    "family=JetBrains+Mono:wght@400;500;600&display=swap"
)


def _cond(light: str, dark: str) -> rx.Var:
    return rx.color_mode_cond(light=light, dark=dark)


class Ivory:
    """Tokens couleur — chaque attribut est une PROPRIÉTÉ pour re-évaluer
    rx.color_mode_cond à chaque accès (pas une valeur calculée une fois)."""

    # Fonds
    bg_page = property(lambda self: _cond("#fafafa", "#18181b"))
    bg_card = property(lambda self: _cond("#ffffff", "#27272a"))
    bg_secondary = property(lambda self: _cond("#f4f5f7", "#1f1f23"))
    bg_hover = property(lambda self: _cond("#f4f5f7", "#303034"))

    # Texte
    text_primary = property(lambda self: _cond("#18181b", "#fafafa"))
    text_secondary = property(lambda self: _cond("#52525b", "#a1a1aa"))
    text_muted = property(lambda self: _cond("#a1a1aa", "#71717a"))

    # Accent
    accent = property(lambda self: _cond("#2563eb", "#3b82f6"))
    accent_hover = property(lambda self: _cond("#1d4ed8", "#2563eb"))
    accent_bg = property(lambda self: _cond("#eff6ff", "#1e3a5f"))

    # Sémantique
    success = property(lambda self: _cond("#16a34a", "#22c55e"))
    success_bg = property(lambda self: _cond("#f0fdf4", "#14291c"))
    warning = property(lambda self: _cond("#d97706", "#f59e0b"))
    warning_bg = property(lambda self: _cond("#fffbeb", "#2b2210"))
    danger = property(lambda self: _cond("#dc2626", "#ef4444"))
    danger_bg = property(lambda self: _cond("#fef2f2", "#2b1616"))

    # Bordures / ombres
    border = property(lambda self: _cond("#e4e5ea", "#3f3f46"))
    shadow_card = property(lambda self: _cond("0 1px 3px rgba(0,0,0,0.04)", "0 1px 3px rgba(0,0,0,0.2)"))


ivory = Ivory()

RADIUS_CARD = "12px"
RADIUS_BTN = "8px"
RADIUS_PILL = "999px"
