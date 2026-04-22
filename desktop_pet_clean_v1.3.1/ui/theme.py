from __future__ import annotations

from PySide6.QtGui import QColor, QFont

from utils.font_loader import ui_font_stack


class Colors:
    # Lineart dog theme palette (from lineart_dog_theme_ui.html)
    CREAM = QColor("#FDF8F3")
    BLUSH = QColor("#F2C4C4")
    BLUSH_SOFT = QColor("#F8E0E0")
    ROSE = QColor("#D98C8C")
    ROSE_DARK = QColor("#A85C5C")
    SAGE = QColor("#A8BFAA")
    SAGE_SOFT = QColor("#E4EEE5")
    SAGE_DARK = QColor("#5C7A5E")
    INK = QColor("#3A2E2E")
    INK_SOFT = QColor("#7A6060")
    INK_HINT = QColor("#B09090")

    PRIMARY = ROSE
    PRIMARY_HOVER = BLUSH
    PRIMARY_PRESSED = ROSE_DARK
    PRIMARY_TEXT = ROSE_DARK

    BG_WINDOW = QColor(CREAM.red(), CREAM.green(), CREAM.blue(), 236)
    BG_MENU = QColor(CREAM.red(), CREAM.green(), CREAM.blue(), 244)
    BG_CARD = QColor(CREAM.red(), CREAM.green(), CREAM.blue(), 248)
    BG_INPUT = QColor(CREAM.red(), CREAM.green(), CREAM.blue(), 252)

    TEXT_PRIMARY = INK
    TEXT_SECONDARY = INK_SOFT
    TEXT_HINT = INK_HINT
    TEXT_ON_PRIMARY = QColor("#FFFFFF")

    BORDER_DEFAULT = QColor(BLUSH.red(), BLUSH.green(), BLUSH.blue(), 120)
    BORDER_FOCUS = ROSE
    BORDER_DIALOG = QColor(BLUSH.red(), BLUSH.green(), BLUSH.blue(), 180)

    SUCCESS = QColor("#70C080")
    WARNING = QColor("#F0B050")
    DANGER = QColor("#E07070")
    INFO = QColor("#70A8E0")

    BUBBLE_BG = QColor(255, 248, 252, 240)
    BUBBLE_BORDER = ROSE

    ACCENT_BLUE = QColor("#4E88B5")
    ACCENT_BROWN = QColor("#8A6040")
    ACCENT_GRAY = QColor("#906070")
    ACCENT_PET = QColor("#C05878")


class Metrics:
    RADIUS_SM = 8
    RADIUS_MD = 12
    RADIUS_LG = 20
    RADIUS_PILL = 999

    PADDING_XS = 4
    PADDING_SM = 8
    PADDING_MD = 14
    PADDING_LG = 20
    PADDING_XL = 28

    ICON_SM = 16
    ICON_MD = 20
    ICON_LG = 28

    DIALOG_MIN_W = 300
    DIALOG_MIN_H = 200
    SHADOW_BLUR = 28
    SHADOW_OPACITY = 0.18


class Typography:
    FAMILY_PRIMARY = "Microsoft YaHei UI"
    FAMILY_FALLBACK = "Segoe UI"

    SIZE_H1 = 17
    SIZE_H2 = 14
    SIZE_BODY = 13
    SIZE_SMALL = 11
    SIZE_CAPTION = 10

    WEIGHT_NORMAL = QFont.Weight.Normal
    WEIGHT_MEDIUM = QFont.Weight.Medium
    WEIGHT_BOLD = QFont.Weight.Bold

    @staticmethod
    def font(size: int, weight=QFont.Weight.Normal) -> QFont:
        font = QFont(Typography.FAMILY_PRIMARY, size)
        font.setWeight(weight)
        return font


def _rgba(color: QColor, alpha: int | None = None) -> str:
    resolved_alpha = color.alpha() if alpha is None else int(alpha)
    return f"rgba({color.red()},{color.green()},{color.blue()},{resolved_alpha})"


def base_font_stack(*, include_emoji: bool = False) -> str:
    return ui_font_stack(prefer_custom=True, include_emoji=include_emoji)


def menu_font_size_for_bubble(size_px: int) -> int:
    return max(12, min(18, int(size_px)))


def menu_stylesheet(font_size: int = Typography.SIZE_BODY) -> str:
    sub_font_size = max(Typography.SIZE_SMALL, int(font_size) - 1)
    c = Colors
    m = Metrics
    return f"""
    QMenu {{
        background: {_rgba(c.BG_MENU)};
        border: 1px solid {_rgba(c.BORDER_DIALOG)};
        border-radius: {m.RADIUS_MD}px;
        padding: 6px 4px;
        color: {c.TEXT_PRIMARY.name()};
        font-size: {int(font_size)}px;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QMenu::item {{
        padding: 7px {m.PADDING_MD}px;
        border-radius: {m.RADIUS_SM}px;
        margin: 1px 4px;
        background: transparent;
    }}
    QMenu::item:selected {{
        background: {_rgba(c.PRIMARY, 40)};
        color: {c.PRIMARY_PRESSED.name()};
    }}
    QMenu::item:checked {{
        background: {_rgba(c.PRIMARY, 60)};
        color: {c.PRIMARY_PRESSED.name()};
        font-weight: 600;
    }}
    QMenu::item:checked:selected {{
        background: {_rgba(c.PRIMARY, 84)};
        color: {c.PRIMARY_PRESSED.name()};
    }}
    QMenu::separator {{
        height: 1px;
        background: {_rgba(c.BORDER_DEFAULT, 80)};
        margin: 4px 12px;
    }}
    QMenu QMenu {{
        font-size: {sub_font_size}px;
    }}
    """


def dialog_shell_stylesheet() -> str:
    c = Colors
    m = Metrics
    return f"""
    QDialog {{
        background: transparent;
        border: none;
        outline: none;
    }}
    QWidget#DialogSurface {{
        background: {_rgba(c.BG_WINDOW)};
        border: none;
        border-radius: {m.RADIUS_LG}px;
        outline: none;
    }}
    QWidget#DialogHeader {{
        background: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {_rgba(c.BLUSH_SOFT, 255)},
            stop:0.6 {_rgba(c.CREAM, 255)}
        );
        border: none;
        outline: none;
    }}
    QLabel#DialogTitle {{
        color: {c.TEXT_PRIMARY.name()};
        font-size: {Typography.SIZE_H2}px;
        font-weight: 500;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QPushButton#DialogClose {{
        background: {_rgba(c.BLUSH_SOFT, 245)};
        border: none;
        border-radius: 10px;
        outline: none;
        color: {c.ROSE_DARK.name()};
        min-width: 22px;
        max-width: 22px;
        min-height: 22px;
        max-height: 22px;
        font-size: 11px;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QPushButton#DialogClose:hover {{
        background: {_rgba(c.BLUSH, 235)};
        color: {c.ROSE_DARK.name()};
    }}
    QPushButton#DialogClose:pressed {{
        background: {_rgba(c.BLUSH, 210)};
        color: {c.ROSE_DARK.name()};
    }}
    """


def soft_card_stylesheet() -> str:
    c = Colors
    m = Metrics
    return f"""
    background: {_rgba(c.BG_CARD)};
    border: none;
    border-radius: {m.RADIUS_MD}px;
    outline: none;
    """


def pill_stylesheet() -> str:
    c = Colors
    return f"""
    background: {_rgba(c.PRIMARY)};
    border: none;
    border-radius: 999px;
    color: {c.TEXT_ON_PRIMARY.name()};
    padding: 4px 10px;
    """


def soft_button_stylesheet(*, primary: bool = True) -> str:
    c = Colors
    if primary:
        bg = _rgba(c.BLUSH_SOFT, 245)
        fg = c.ROSE_DARK.name()
        hover = _rgba(c.BLUSH, 230)
        pressed = _rgba(c.ROSE, 80)
        disabled_bg = _rgba(c.BLUSH_SOFT, 165)
    else:
        bg = _rgba(c.CREAM, 235)
        fg = c.TEXT_SECONDARY.name()
        hover = _rgba(c.BLUSH_SOFT, 220)
        pressed = _rgba(c.BLUSH, 120)
        disabled_bg = _rgba(c.BORDER_DEFAULT, 35)
    return f"""
    QPushButton {{
        background: {bg};
        border: none;
        border-radius: {Metrics.RADIUS_SM}px;
        outline: none;
        color: {fg};
        padding: 9px 12px;
        font-size: {Typography.SIZE_BODY}px;
        font-weight: 500;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QPushButton:hover {{
        background: {hover};
    }}
    QPushButton:pressed {{
        background: {pressed};
    }}
    QPushButton:disabled {{
        background: {disabled_bg};
        color: {_rgba(c.TEXT_SECONDARY, 180)};
        border: none;
    }}
    """


def line_edit_stylesheet() -> str:
    c = Colors
    return f"""
    QLineEdit, QComboBox, QSpinBox, QTextEdit {{
        background: {_rgba(c.CREAM, 248)};
        border: none;
        border-radius: {Metrics.RADIUS_SM}px;
        outline: none;
        padding: 8px 10px;
        color: {c.TEXT_PRIMARY.name()};
        font-size: {Typography.SIZE_BODY}px;
        min-height: 16px;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus {{
        border: none;
        background: {_rgba(c.BLUSH_SOFT, 215)};
    }}
    QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QTextEdit:disabled {{
        color: {_rgba(c.TEXT_SECONDARY, 150)};
        background: {_rgba(c.BG_INPUT, 200)};
        border: none;
    }}
    QComboBox::drop-down, QSpinBox::up-button, QSpinBox::down-button {{
        border: none;
        background: transparent;
        width: 18px;
    }}
    QComboBox QAbstractItemView {{
        border: none;
        outline: none;
        background: {_rgba(c.BG_CARD, 252)};
        selection-background-color: {_rgba(c.PRIMARY, 60)};
        color: {c.TEXT_PRIMARY.name()};
    }}
    """


def segmented_button_stylesheet() -> str:
    c = Colors
    return f"""
    QPushButton {{
        background: {_rgba(c.BLUSH_SOFT, 145)};
        border: none;
        border-radius: 10px;
        outline: none;
        color: {c.TEXT_SECONDARY.name()};
        padding: 6px 14px;
        font-size: {Typography.SIZE_SMALL}px;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QPushButton:checked {{
        background: {_rgba(c.BLUSH_SOFT, 245)};
        border: none;
        color: {c.ROSE_DARK.name()};
        font-weight: 600;
    }}
    QPushButton:hover:!checked {{
        background: {_rgba(c.BLUSH_SOFT, 220)};
        border: none;
        color: {c.TEXT_PRIMARY.name()};
    }}
    """


def toggle_button_stylesheet() -> str:
    c = Colors
    return f"""
    QPushButton {{
        border: none;
        border-radius: 12px;
        outline: none;
        min-width: 58px;
        max-width: 58px;
        min-height: 26px;
        max-height: 26px;
        padding: 0px;
        background: {_rgba(c.BLUSH_SOFT, 235)};
        color: {c.TEXT_SECONDARY.name()};
        font-size: {Typography.SIZE_SMALL}px;
        font-weight: 600;
        font-family: {base_font_stack(include_emoji=True)};
    }}
    QPushButton:checked {{
        background: {c.ROSE.name()};
        border: none;
        color: {c.TEXT_ON_PRIMARY.name()};
    }}
    """


def progress_bar_stylesheet() -> str:
    c = Colors
    return f"""
    QProgressBar {{
        border: none;
        border-radius: 4px;
        background: {_rgba(c.BORDER_DEFAULT, 40)};
        min-height: 8px;
        max-height: 8px;
    }}
    QProgressBar::chunk {{
        border-radius: 4px;
        background: {c.PRIMARY.name()};
    }}
    """


SURFACE_BG = Colors.BG_WINDOW.name()
SURFACE_BG_SOFT = _rgba(Colors.BG_WINDOW)
SURFACE_CARD = _rgba(Colors.BG_CARD)
SURFACE_BORDER = _rgba(Colors.BORDER_DEFAULT, 128)
SURFACE_BORDER_SOFT = _rgba(Colors.BORDER_DEFAULT, 72)
SURFACE_HOVER = _rgba(Colors.PRIMARY, 60)
SURFACE_ACTIVE = _rgba(Colors.PRIMARY, 30)
TEXT_PRIMARY = Colors.TEXT_PRIMARY.name()
TEXT_SECONDARY = Colors.TEXT_SECONDARY.name()
TEXT_MUTED = _rgba(Colors.TEXT_SECONDARY, 190)
ACCENT = Colors.PRIMARY_PRESSED.name()
ACCENT_BLUE = Colors.ACCENT_BLUE.name()
ACCENT_BROWN = Colors.ACCENT_BROWN.name()
ACCENT_GRAY = Colors.ACCENT_GRAY.name()
ACCENT_PET = Colors.ACCENT_PET.name()
SUCCESS = Colors.SUCCESS.name()
RADIUS_MENU = Metrics.RADIUS_MD
RADIUS_DIALOG = Metrics.RADIUS_LG
RADIUS_CARD = Metrics.RADIUS_MD
