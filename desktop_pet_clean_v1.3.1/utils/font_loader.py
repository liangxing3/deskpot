from __future__ import annotations

import logging

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from utils.paths import resource_path

FONT_RELATIVE_CANDIDATES = (
    "assets/fonts/YiXinMengYuanTi.ttf",
    "assets/fonts/XiangJiaoXiuZhengDaiLingGanTi-2.ttf",
)
SYSTEM_UI_FALLBACKS = ["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"]

_loaded_font_family: str | None = None


def install_application_font(logger: logging.Logger | None = None) -> str | None:
    """Load the bundled custom font and return the resolved family name."""

    global _loaded_font_family
    if _loaded_font_family:
        return _loaded_font_family

    font_path = None
    for candidate in FONT_RELATIVE_CANDIDATES:
        resolved = resource_path(candidate)
        if resolved.exists():
            font_path = resolved
            break
    if font_path is None:
        if logger:
            logger.warning("No bundled UI font file was found: %s", FONT_RELATIVE_CANDIDATES)
        return None

    font_id = QFontDatabase.addApplicationFont(str(font_path))
    if font_id < 0:
        if logger:
            logger.warning("Failed to load custom font: %s", font_path)
        return None

    families = QFontDatabase.applicationFontFamilies(font_id)
    if not families:
        if logger:
            logger.warning("Custom font loaded but no font families were returned: %s", font_path)
        return None

    _loaded_font_family = families[0]
    if logger:
        logger.info("Loaded custom UI font: %s", _loaded_font_family)
    return _loaded_font_family


def primary_ui_font_family(*, prefer_custom: bool = True) -> str:
    if prefer_custom and _loaded_font_family:
        return _loaded_font_family
    return SYSTEM_UI_FALLBACKS[0]

def ui_font_stack(*, include_emoji: bool = False, prefer_custom: bool = True) -> str:
    families: list[str] = []
    if prefer_custom and _loaded_font_family:
        families.append(_loaded_font_family)
    families.extend(SYSTEM_UI_FALLBACKS)
    if include_emoji:
        families.append("Segoe UI Emoji")
    if not prefer_custom and _loaded_font_family:
        families.append(_loaded_font_family)
    seen: set[str] = set()
    ordered = [family for family in families if not (family in seen or seen.add(family))]
    return ", ".join(f'"{family}"' for family in ordered)


def build_ui_font(
    point_size: int | float = 10,
    *,
    include_emoji: bool = False,
    prefer_custom: bool = True,
) -> QFont:
    family = primary_ui_font_family(prefer_custom=prefer_custom)
    font = QFont(family)
    font.setPointSizeF(float(point_size))
    substitutions: list[str] = []
    if _loaded_font_family:
        substitutions.append(_loaded_font_family)
    substitutions.extend(SYSTEM_UI_FALLBACKS)
    if include_emoji:
        substitutions.append("Segoe UI Emoji")
    QFont.insertSubstitutions(family, substitutions)
    return font


def configure_application_font(app: QApplication, logger: logging.Logger | None = None) -> str | None:
    family = install_application_font(logger)
    font = build_ui_font(max(10.0, app.font().pointSizeF()), include_emoji=False, prefer_custom=True)
    app.setFont(font)
    return family
