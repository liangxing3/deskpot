from __future__ import annotations

import logging

from PySide6.QtGui import QFont, QFontDatabase
from PySide6.QtWidgets import QApplication

from utils.paths import resource_path

FONT_RELATIVE_PATH = "assets/fonts/XiangJiaoXiuZhengDaiLingGanTi-2.ttf"

_loaded_font_family: str | None = None


def install_application_font(logger: logging.Logger | None = None) -> str | None:
    """Load the bundled custom font and return the resolved family name."""

    global _loaded_font_family
    if _loaded_font_family:
        return _loaded_font_family

    font_path = resource_path(FONT_RELATIVE_PATH)
    if not font_path.exists():
        if logger:
            logger.warning("Custom font file is missing: %s", font_path)
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


def primary_ui_font_family() -> str:
    return _loaded_font_family or "Microsoft YaHei UI"


def ui_font_stack(*, include_emoji: bool = False) -> str:
    families: list[str] = []
    if _loaded_font_family:
        families.append(_loaded_font_family)
    if include_emoji:
        families.append("Segoe UI Emoji")
    families.extend(["Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"])
    seen: set[str] = set()
    ordered = [family for family in families if not (family in seen or seen.add(family))]
    return ", ".join(f'"{family}"' for family in ordered)


def build_ui_font(point_size: int | float = 10, *, include_emoji: bool = False) -> QFont:
    font = QFont(primary_ui_font_family())
    font.setPointSizeF(float(point_size))
    if include_emoji:
        QFont.insertSubstitutions(primary_ui_font_family(), ["Segoe UI Emoji", "Microsoft YaHei UI"])
    return font


def configure_application_font(app: QApplication, logger: logging.Logger | None = None) -> str | None:
    family = install_application_font(logger)
    if family:
        font = app.font()
        font.setFamily(family)
        if font.pointSizeF() < 10:
            font.setPointSizeF(10.0)
        app.setFont(font)
    return family
