from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class EventBus(QObject):
    bubble_requested = Signal(object)
    weather_updated = Signal(object)
    config_updated = Signal(object)
    state_changed = Signal(object, object)
    vitals_updated = Signal(object)
    pet_status_updated = Signal(object)
    emotion_changed = Signal(object)
