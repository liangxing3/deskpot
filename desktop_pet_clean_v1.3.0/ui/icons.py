from __future__ import annotations

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from ui.theme import ACCENT_BLUE, ACCENT_BROWN, ACCENT_GRAY, ACCENT_PET

ICON_SPECS = {
    "weather": {
        "color": ACCENT_BLUE,
        "path": '<path d="M4.406 3.342A5.53 5.53 0 0 1 8 2c2.69 0 4.923 2 5.166 4.579C14.758 6.804 16 8.137 16 9.773 16 11.569 14.502 13 12.687 13H3.781C1.708 13 0 11.366 0 9.318c0-1.763 1.266-3.223 2.942-3.593.143-.863.698-1.723 1.464-2.383z"/>',
    },
    "answerbook": {
        "color": ACCENT_BROWN,
        "path": '<path d="M1 2.5A1.5 1.5 0 0 1 2.5 1h8A1.5 1.5 0 0 1 12 2.5v11A1.5 1.5 0 0 1 10.5 15h-8A1.5 1.5 0 0 1 1 13.5v-11zM2.5 2a.5.5 0 0 0-.5.5v11a.5.5 0 0 0 .5.5h8a.5.5 0 0 0 .5-.5v-11a.5.5 0 0 0-.5-.5h-8zm9 .5v11a.5.5 0 0 0 .5.5h1a.5.5 0 0 0 .5-.5v-11a.5.5 0 0 0-.5-.5h-1a.5.5 0 0 0-.5.5z"/><path d="M3 4.5h5v1H3v-1zm0 2h5v1H3v-1zm0 2h3v1H3v-1z"/>',
    },
    "settings": {
        "color": ACCENT_GRAY,
        "path": '<path d="M8 4.754a3.246 3.246 0 1 0 0 6.492 3.246 3.246 0 0 0 0-6.492zM5.754 8a2.246 2.246 0 1 1 4.492 0 2.246 2.246 0 0 1-4.492 0z"/><path d="M9.796 1.343c-.527-1.79-3.065-1.79-3.592 0l-.094.319a.873.873 0 0 1-1.255.52l-.292-.16c-1.64-.892-3.433.902-2.54 2.541l.159.292a.873.873 0 0 1-.52 1.255l-.319.094c-1.79.527-1.79 3.065 0 3.592l.319.094a.873.873 0 0 1 .52 1.255l-.16.292c-.892 1.64.901 3.434 2.541 2.54l.292-.159a.873.873 0 0 1 1.255.52l.094.319c.527 1.79 3.065 1.79 3.592 0l.094-.319a.873.873 0 0 1 1.255-.52l.292.16c1.64.893 3.434-.902 2.54-2.541l-.159-.292a.873.873 0 0 1 .52-1.255l.319-.094c1.79-.527 1.79-3.065 0-3.592l-.319-.094a.873.873 0 0 1-.52-1.255l.16-.292c.893-1.64-.902-3.433-2.541-2.54l-.292.159a.873.873 0 0 1-1.255-.52l-.094-.319z"/>',
    },
    "pet": {
        "color": ACCENT_PET,
        "path": '<path d="M6.5 1.5a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm3 0a1.5 1.5 0 1 0 0 3 1.5 1.5 0 0 0 0-3zm-5.5 4a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm9 0a1 1 0 1 0 0 2 1 1 0 0 0 0-2zM4.5 8C3.12 8 2 9.12 2 10.5c0 2.5 2.5 4.5 6 4.5s6-2 6-4.5C14 9.12 12.88 8 11.5 8h-7z"/>',
    },
    "feed": {
        "color": ACCENT_BROWN,
        "path": '<path d="M2.2 8.2A5.8 5.8 0 0 0 8 14a5.8 5.8 0 0 0 5.8-5.8H2.2zm1.1 1h9.4a4.7 4.7 0 0 1-9.4 0z"/><path d="M5 4.6a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm3-1a1 1 0 1 0 0 2 1 1 0 0 0 0-2zm3 1a1 1 0 1 0 0 2 1 1 0 0 0 0-2z"/>',
    },
    "play": {
        "color": ACCENT_PET,
        "path": '<path d="M8 1.2a6.8 6.8 0 1 0 0 13.6A6.8 6.8 0 0 0 8 1.2zm0 1a5.8 5.8 0 1 1 0 11.6A5.8 5.8 0 0 1 8 2.2z"/><path d="M8 3.3 5.7 5l.9 2.7L9.4 8.6l1.6-2.3L8.8 4.8 8 3.3zm-3.5 2.4L3.1 8l1.5 2.5 2.3-.5L6.1 7.7 4.5 5.7zm7 0L9.9 7.7l-.8 2.3 2.3.5L12.9 8l-1.4-2.3zM7.2 10.6l-1.8.4 1.6 1.7.9-.5.7-1.4-1.4-.2zm1.6 0-1.4.2.7 1.4.9.5 1.6-1.7-1.8-.4z"/>',
    },
    "clean": {
        "color": ACCENT_BLUE,
        "path": '<path d="M8 1.4C6.8 3.3 4.1 6 4.1 8.8a3.9 3.9 0 1 0 7.8 0C11.9 6 9.2 3.3 8 1.4zm0 11.2A2.8 2.8 0 0 1 5.2 9.8C5.2 8 6.9 5.8 8 4.2c1.1 1.6 2.8 3.8 2.8 5.6A2.8 2.8 0 0 1 8 12.6z"/><path d="M12 1.8l.3 1 .9.3-.9.3-.3 1-.3-1-.9-.3.9-.3.3-1z"/>',
    },
    "rest": {
        "color": ACCENT_GRAY,
        "path": '<path d="M10.7 1.4a6.8 6.8 0 1 0 4 9.8A5.8 5.8 0 1 1 10.7 1.4z"/>',
    },
    "status": {
        "color": ACCENT_PET,
        "path": '<path d="M2 13h12v1H2v-1zm1-2h2v2H3v-2zm4-4h2v6H7V7zm4-3h2v9h-2V4z"/>',
    },
}

_pixmap_cache: dict[tuple[str, int], QPixmap] = {}
_icon_cache: dict[tuple[str, int], QIcon] = {}


def make_icon(name: str, *, size: int = 16) -> QIcon:
    cache_key = (name, int(size))
    if cache_key not in _icon_cache:
        _icon_cache[cache_key] = QIcon(make_pixmap(name, size=size))
    return QIcon(_icon_cache[cache_key])


def make_pixmap(name: str, *, size: int = 16) -> QPixmap:
    cache_key = (name, int(size))
    if cache_key in _pixmap_cache:
        return QPixmap(_pixmap_cache[cache_key])

    spec = ICON_SPECS[name]
    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 16 16" fill="{spec["color"]}">'
        f'{spec["path"]}</svg>'
    )
    renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    _pixmap_cache[cache_key] = QPixmap(pixmap)
    return QPixmap(pixmap)
