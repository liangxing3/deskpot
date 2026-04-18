from __future__ import annotations

import random

from PySide6.QtCore import QObject, QTimer, Signal


class Scheduler(QObject):
    heartbeat = Signal()
    activity_tick = Signal()
    clock_tick = Signal()
    growth_tick = Signal()
    random_animation_due = Signal()
    random_dialog_due = Signal()
    delayed_hourly_due = Signal()
    startup_weather_due = Signal()
    weather_refresh_due = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.activity_timer = QTimer(self)
        self.activity_timer.setInterval(5_000)
        self.activity_timer.timeout.connect(self.activity_tick.emit)
        self.activity_timer.timeout.connect(self.heartbeat.emit)

        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(15_000)
        self.clock_timer.timeout.connect(self.clock_tick.emit)

        self.random_animation_timer = QTimer(self)
        self.random_animation_timer.setSingleShot(True)
        self.random_animation_timer.timeout.connect(self._on_random_animation_due)

        self.random_dialog_timer = QTimer(self)
        self.random_dialog_timer.setSingleShot(True)
        self.random_dialog_timer.timeout.connect(self._on_random_dialog_due)

        self.growth_timer = QTimer(self)
        self.growth_timer.setInterval(15 * 60 * 1000)
        self.growth_timer.timeout.connect(self.growth_tick.emit)

        self.delayed_hourly_timer = QTimer(self)
        self.delayed_hourly_timer.setSingleShot(True)
        self.delayed_hourly_timer.timeout.connect(self.delayed_hourly_due.emit)

        self.startup_weather_timer = QTimer(self)
        self.startup_weather_timer.setSingleShot(True)
        self.startup_weather_timer.timeout.connect(self.startup_weather_due.emit)

        self.weather_refresh_timer = QTimer(self)
        self.weather_refresh_timer.setSingleShot(True)
        self.weather_refresh_timer.timeout.connect(self.weather_refresh_due.emit)

    def start(self) -> None:
        self.activity_timer.start()
        self.clock_timer.start()
        self.growth_timer.start()
        self.schedule_startup_weather()
        self.schedule_next_animation_check()
        self.schedule_next_random_dialog()

    def stop(self) -> None:
        self.activity_timer.stop()
        self.clock_timer.stop()
        self.growth_timer.stop()
        self.random_animation_timer.stop()
        self.random_dialog_timer.stop()
        self.delayed_hourly_timer.stop()
        self.startup_weather_timer.stop()
        self.weather_refresh_timer.stop()

    def schedule_next_animation_check(self) -> None:
        seconds = random.randint(20, 60)
        self.random_animation_timer.start(seconds * 1000)

    def schedule_next_random_dialog(self) -> None:
        minutes = random.randint(8, 15)
        self.random_dialog_timer.start(minutes * 60 * 1000)

    def delay_hourly_report(self, milliseconds: int = 30_000) -> None:
        self.delayed_hourly_timer.start(milliseconds)

    def cancel_delayed_hourly_report(self) -> None:
        self.delayed_hourly_timer.stop()

    def schedule_startup_weather(self, milliseconds: int = 90 * 60 * 1000) -> None:
        self.startup_weather_timer.start(milliseconds)

    def schedule_weather_refresh(self, milliseconds: int) -> None:
        if milliseconds <= 0:
            self.weather_refresh_due.emit()
            return
        self.weather_refresh_timer.start(milliseconds)

    def cancel_weather_refresh(self) -> None:
        self.weather_refresh_timer.stop()

    def _on_random_animation_due(self) -> None:
        self.random_animation_due.emit()
        self.schedule_next_animation_check()

    def _on_random_dialog_due(self) -> None:
        self.random_dialog_due.emit()
        self.schedule_next_random_dialog()
