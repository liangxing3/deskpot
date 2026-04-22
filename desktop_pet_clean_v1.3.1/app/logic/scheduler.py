from __future__ import annotations

from PySide6.QtCore import QObject, QTimer, Signal

from app.logic.reminders import ReminderEngine
from utils.time_utils import now_local


class AppScheduler(QObject):
    events_ready = Signal(object)

    def __init__(
        self,
        *,
        engine: ReminderEngine,
        config_getter,
        status_getter,
        vitals_getter,
        weather_getter,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self.engine = engine
        self._config_getter = config_getter
        self._status_getter = status_getter
        self._vitals_getter = vitals_getter
        self._weather_getter = weather_getter
        self._last_activity_at = now_local()

        self._timer = QTimer(self)
        self._timer.setInterval(60_000)
        self._timer.timeout.connect(self.poll_due)

    def start(self) -> None:
        self._timer.start()
        self.poll_due()

    def stop(self) -> None:
        self._timer.stop()

    def note_activity(self, when=None) -> None:
        self._last_activity_at = when or now_local()
        self.engine.note_activity(self._last_activity_at)

    def poll_due(self) -> None:
        events = self.engine.collect_due_events(
            config=self._config_getter(),
            status=self._status_getter(),
            vitals=self._vitals_getter(),
            last_activity_at=self._last_activity_at,
            weather_snapshot=self._weather_getter(),
        )
        if events:
            self.events_ready.emit(events)
