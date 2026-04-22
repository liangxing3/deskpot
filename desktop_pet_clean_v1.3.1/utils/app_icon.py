from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon

from utils.paths import resource_path

ICON_CANDIDATES = (
    "assets/app_icon.ico",
    "assets/app_icon.png",
)


def app_icon_path() -> Path | None:
    for relative_path in ICON_CANDIDATES:
        candidate = resource_path(relative_path)
        if candidate.exists():
            return candidate
    return None


def load_app_icon() -> QIcon | None:
    icon_path = app_icon_path()
    if icon_path is None:
        return None
    icon = QIcon(str(icon_path))
    if icon.isNull():
        return None
    return icon
