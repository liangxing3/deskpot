from __future__ import annotations

from PySide6.QtCore import QObject, Signal


class SignalBus(QObject):
    """Global application event bus used to reduce hard references."""

    pet_state_changed = Signal()
    pet_mood_changed = Signal(str)
    animation_request = Signal(str)
    bubble_show = Signal(str, int)

    weather_updated = Signal(object)
    weather_error = Signal(str)

    dialog_open_request = Signal(str)
    theme_changed = Signal()

    app_quit_request = Signal()


_bus: SignalBus | None = None


def get_bus() -> SignalBus:
    global _bus
    if _bus is None:
        _bus = SignalBus()
    return _bus
