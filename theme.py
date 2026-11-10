"""Design tokens and shared styling for Circle.

One palette, one type scale, one set of radii. Every window reads from here so
the launcher, the wheel, the switcher and the settings panel feel like one
piece of software instead of four.

Direction: cold glass, quiet ink. A near-black panel that floats over whatever
you were doing, a single hairline edge, one accent used only for the thing you
are about to act on.
"""

from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette
from PySide6.QtCore import Qt

# ---------------------------------------------------------------- palette ----

BG = "#101014"          # panel base (opaque fallback for non-composited areas)
BG_RGB = (16, 16, 20)
SURFACE = "#17171D"     # nested surfaces, inputs
SURFACE_HI = "#20202A"  # hover / selected row
HAIRLINE = "rgba(255, 255, 255, 22)"
HAIRLINE_STRONG = "rgba(255, 255, 255, 38)"

TEXT = "#EDEDF2"
TEXT_DIM = "#9C9CB0"    # 6.4:1 on SURFACE
TEXT_MUTE = "#71718A"   # decorative only: separators, key caps

ACCENT = "#8AB4FF"
ACCENT_HOVER = "#A6C6FF"
ACCENT_INK = "#0B1220"  # text on accent fills
DANGER = "#FF8095"
OK = "#8BE0A4"

SHADOW = QColor(0, 0, 0, 170)

# ------------------------------------------------------------------ type ----

# Windows first, then the macOS system faces, then a neutral fallback.
_UI_STACK = ["Segoe UI Variable Text", "Segoe UI", "SF Pro Text", "Helvetica Neue",
             "Inter", "Noto Sans", "DejaVu Sans"]
_DISPLAY_STACK = ["Segoe UI Variable Display", "Segoe UI", "SF Pro Display",
                  "Helvetica Neue", "Inter", "Noto Sans", "DejaVu Sans"]
_MONO_STACK = ["Cascadia Mono", "Consolas", "SF Mono", "Menlo",
               "JetBrains Mono", "DejaVu Sans Mono"]
_EMOJI_STACK = ["Segoe UI Emoji", "Apple Color Emoji", "Noto Color Emoji"]


def _families(wanted):
    """Keep only families that actually exist on this machine."""
    available = set(QFontDatabase.families())
    kept = [f for f in wanted if f in available]
    return kept or wanted[-1:]


def emoji_font(size=15):
    """Only for slots still carrying an emoji glyph from an older config."""
    f = QFont()
    f.setFamilies(_families(_EMOJI_STACK))
    f.setPixelSize(size)
    return f


def font(size=13, weight=QFont.Normal, display=False, mono=False, tracking=0.0):
    f = QFont()
    if mono:
        f.setFamilies(_families(_MONO_STACK))
    else:
        f.setFamilies(_families(_DISPLAY_STACK if display else _UI_STACK))
    f.setPixelSize(size)
    f.setWeight(weight)
    if tracking:
        f.setLetterSpacing(QFont.AbsoluteSpacing, tracking)
    f.setHintingPreference(QFont.PreferDefaultHinting)
    return f


# ------------------------------------------------------------------- qss -----

def _base_qss():
    return f"""
    QWidget {{
        color: {TEXT};
        selection-background-color: {ACCENT};
        selection-color: {ACCENT_INK};
    }}
    QToolTip {{
        background-color: {SURFACE_HI};
        color: {TEXT};
        border: 1px solid {HAIRLINE_STRONG};
        border-radius: 8px;
        padding: 6px 9px;
        font-size: 12px;
    }}
    QMenu {{
        background-color: {SURFACE};
        color: {TEXT};
        border: 1px solid {HAIRLINE_STRONG};
        border-radius: 10px;
        padding: 6px;
        font-size: 13px;
    }}
    QMenu::item {{
        padding: 7px 14px 7px 12px;
        border-radius: 6px;
    }}
    QMenu::item:selected {{
        background-color: {SURFACE_HI};
        color: {TEXT};
    }}
    QMenu::separator {{
        height: 1px;
        background: {HAIRLINE};
        margin: 6px 8px;
    }}
    QScrollBar:vertical {{
        background: transparent;
        width: 10px;
        margin: 4px 2px;
    }}
    QScrollBar::handle:vertical {{
        background: rgba(255, 255, 255, 46);
        border-radius: 4px;
        min-height: 32px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: rgba(255, 255, 255, 72);
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
        height: 0px;
        background: transparent;
    }}
    """


def search_qss():
    """The Spotlight panel."""
    return _base_qss() + f"""
    QFrame#panel {{
        background-color: rgba({BG_RGB[0]}, {BG_RGB[1]}, {BG_RGB[2]}, 236);
        border: 1px solid {HAIRLINE_STRONG};
        border-radius: 16px;
    }}
    QLineEdit#query {{
        background: transparent;
        border: none;
        color: {TEXT};
        padding: 0px;
    }}
    QListWidget#results {{
        background: transparent;
        border: none;
        outline: none;
        padding: 0px;
    }}
    QLabel#empty {{
        color: {TEXT_DIM};
    }}
    QLabel#footer {{
        color: {TEXT_DIM};
        font-size: 11px;
    }}
    """


def settings_qss():
    return _base_qss() + f"""
    QMainWindow, QWidget#root {{
        background-color: {BG};
    }}
    QGroupBox {{
        border: 1px solid {HAIRLINE};
        border-radius: 12px;
        margin-top: 16px;
        padding: 16px 12px 12px 12px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 12px;
        padding: 0 6px;
        color: {TEXT_DIM};
    }}
    QLineEdit, QComboBox, QSpinBox {{
        background-color: {SURFACE};
        border: 1px solid {HAIRLINE_STRONG};
        border-radius: 8px;
        padding: 7px 10px;
        color: {TEXT};
        selection-background-color: {ACCENT};
        selection-color: {ACCENT_INK};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
        border: 1px solid {ACCENT};
    }}
    QCheckBox {{
        color: {TEXT};
        font-weight: 500;
        spacing: 8px;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 5px;
        border: 1px solid {HAIRLINE_STRONG};
        background: {SURFACE};
    }}
    QCheckBox::indicator:checked {{
        background: {ACCENT};
        border: 1px solid {ACCENT};
    }}
    QPushButton {{
        background-color: {SURFACE_HI};
        border: 1px solid {HAIRLINE_STRONG};
        border-radius: 8px;
        padding: 7px 10px;
        color: {TEXT};
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: #2A2A36;
        border: 1px solid {HAIRLINE_STRONG};
    }}
    QPushButton:pressed {{
        background-color: #13131A;
    }}
    QPushButton:checked {{
        background-color: {SURFACE_HI};
        border: 1px solid {ACCENT};
    }}
    QPushButton#presetBtn {{
        background-color: {SURFACE};
        border: 1px solid {HAIRLINE};
        text-align: left;
        padding: 7px 10px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton#presetBtn:hover {{
        background-color: {SURFACE_HI};
        border: 1px solid {HAIRLINE_STRONG};
    }}
    QPushButton#saveBtn {{
        background-color: {ACCENT};
        color: {ACCENT_INK};
        border: none;
        padding: 9px 20px;
    }}
    QPushButton#saveBtn:hover {{
        background-color: {ACCENT_HOVER};
    }}
    QPushButton#testBtn {{
        background-color: transparent;
        border: 1px solid {HAIRLINE_STRONG};
        color: {TEXT};
    }}
    QPushButton#testBtn:hover {{
        border: 1px solid {ACCENT};
        color: {ACCENT};
    }}
    QTabWidget::pane {{
        border: 1px solid {HAIRLINE};
        border-radius: 10px;
        background: {SURFACE};
        top: -1px;
    }}
    QTabBar::tab {{
        background: transparent;
        color: {TEXT_DIM};
        padding: 8px 14px;
        margin-right: 2px;
        border-radius: 8px;
    }}
    QTabBar::tab:selected {{
        background: {SURFACE_HI};
        color: {TEXT};
        font-weight: 600;
    }}
    QTabBar::tab:hover:!selected {{
        color: {TEXT};
    }}
    QScrollArea {{
        border: none;
        background: transparent;
    }}
    QScrollArea > QWidget > QWidget {{
        background: transparent;
    }}
    """


def switcher_qss():
    return _base_qss() + f"""
    QFrame#panel {{
        background-color: rgba({BG_RGB[0]}, {BG_RGB[1]}, {BG_RGB[2]}, 236);
        border: 1px solid {HAIRLINE_STRONG};
        border-radius: 16px;
    }}
    QLineEdit#query {{
        background: transparent;
        border: none;
        color: {TEXT};
    }}
    QListWidget#results {{
        background: transparent;
        border: none;
        outline: none;
    }}
    """


def apply_app_theme(app):
    """Global defaults: palette, base font, control styles."""
    pal = app.palette()
    pal.setColor(QPalette.Window, QColor(BG))
    pal.setColor(QPalette.WindowText, QColor(TEXT))
    pal.setColor(QPalette.Base, QColor(SURFACE))
    pal.setColor(QPalette.AlternateBase, QColor(SURFACE_HI))
    pal.setColor(QPalette.Text, QColor(TEXT))
    pal.setColor(QPalette.PlaceholderText, QColor(TEXT_DIM))
    pal.setColor(QPalette.Button, QColor(SURFACE_HI))
    pal.setColor(QPalette.ButtonText, QColor(TEXT))
    pal.setColor(QPalette.Highlight, QColor(ACCENT))
    pal.setColor(QPalette.HighlightedText, QColor(ACCENT_INK))
    pal.setColor(QPalette.ToolTipBase, QColor(SURFACE_HI))
    pal.setColor(QPalette.ToolTipText, QColor(TEXT))
    app.setPalette(pal)
    app.setFont(font(13))
    app.setStyleSheet(_base_qss())


def panel_shadow(widget, blur=64, y_offset=18, alpha=170, spread=0):
    """Soft, offset shadow. Elevation is declared once, never stacked with a
    second inset ring."""
    from PySide6.QtWidgets import QGraphicsDropShadowEffect

    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(blur)
    eff.setOffset(0, y_offset)
    eff.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(eff)
    return eff
