from __future__ import annotations

import logging
import random
from datetime import datetime
from typing import Callable

from PySide6.QtCore import QObject, QThreadPool, QTimer

from core.state_manager import STATE_PRIORITIES
from data.models import PetState, UiMessage, WeatherSnapshot
from services.weather_service import format_weather_summary
from utils.async_runner import submit_task
from utils.time_utils import date_key, now_local


class WeatherCoordinator(QObject):
    """Coordinates refresh, auto reporting, and care advice around structured weather data."""

    def __init__(
        self,
        *,
        logger: logging.Logger,
        thread_pool: QThreadPool,
        state_manager,
        scheduler,
        interaction_manager,
        daypart_weather_reporter,
        weather_care_advisor,
        weather_service,
        dialog_service,
        notification_center,
        get_config: Callable[[], object],
        runtime_state,
        save_runtime_state: Callable[[], None],
    ) -> None:
        super().__init__()
        self.logger = logger
        self.thread_pool = thread_pool
        self.state_manager = state_manager
        self.scheduler = scheduler
        self.interaction_manager = interaction_manager
        self.daypart_weather_reporter = daypart_weather_reporter
        self.weather_care_advisor = weather_care_advisor
        self.weather_service = weather_service
        self.dialog_service = dialog_service
        self.notification_center = notification_center
        self.get_config = get_config
        self.runtime_state = runtime_state
        self.save_runtime_state = save_runtime_state

        self._weather_in_flight = False
        self._started_weather_refresh = False
        self._last_weather_attempt_at: datetime | None = None
        self._pending_request: dict[str, object] | None = None
        self._weather_advice_ticket = 0

    def startup_auto_weather(self) -> None:
        if self._started_weather_refresh:
            return
        self._started_weather_refresh = True
        self.request_announcement("startup_auto", manual=False)

    def on_startup_weather_due(self) -> None:
        self.request_announcement("startup_90min_auto", manual=False)

    def on_clock_tick(self, current: datetime | None = None) -> None:
        now = current or now_local()
        if self.daypart_weather_reporter.should_auto_report(now):
            self.request_announcement("daypart_auto", manual=False)

    def on_weather_refresh_due(self) -> None:
        self.refresh_weather(force=True, announce_context=None)

    def request_announcement(self, source: str, *, manual: bool) -> None:
        current = now_local()
        config = self.get_config()
        if not config.weather_enabled:
            if manual:
                self.notification_center.publish(
                    UiMessage(
                        text="天气功能当前已关闭。",
                        category="weather",
                        priority=60,
                        ttl_ms=3000,
                        cooldown_key="weather:disabled",
                        cooldown_ms=3000,
                    )
                )
            return

        if not manual and not self._can_trigger_automatic_weather(source, current):
            return

        snapshot = self.weather_service.get_cached_weather()
        request = self._build_request_context(source, manual=manual, requested_at=current)
        if snapshot is not None:
            self._announce_snapshot(snapshot, request)
            return

        if self._weather_in_flight:
            if manual:
                self.notification_center.publish(
                    UiMessage(
                        text="天气正在更新，稍等一下。",
                        category="weather",
                        priority=55,
                        ttl_ms=2500,
                        cooldown_key="weather:loading",
                        cooldown_ms=2500,
                    )
                )
            return

        self.refresh_weather(force=True, announce_context=request)

    def refresh_weather(
        self,
        *,
        force: bool,
        announce_context: dict[str, object] | None,
    ) -> None:
        config = self.get_config()
        if self._weather_in_flight or not config.weather_enabled:
            return

        self._weather_in_flight = True
        self._pending_request = announce_context
        self._last_weather_attempt_at = now_local()
        submit_task(
            self.thread_pool,
            self.weather_service.get_weather,
            kwargs={"force_refresh": force},
            on_success=self._on_weather_ready,
            on_error=self._on_weather_failed,
        )

    def schedule_next_refresh(self, *, from_time: datetime | None = None) -> None:
        config = self.get_config()
        if not config.weather_enabled:
            self.scheduler.cancel_weather_refresh()
            return
        interval_ms = max(15, int(config.weather_update_interval_minutes)) * 60 * 1000
        self.scheduler.schedule_weather_refresh(interval_ms)

    def _build_request_context(
        self,
        source: str,
        *,
        manual: bool,
        requested_at: datetime,
    ) -> dict[str, object]:
        daypart = self.daypart_weather_reporter.current_daypart(requested_at)
        consume_daypart = (
            not manual
            and daypart is not None
            and not self.daypart_weather_reporter.has_reported(daypart, requested_at)
        )
        return {
            "source": source,
            "manual": manual,
            "daypart": daypart,
            "requested_at": requested_at,
            "consume_daypart": consume_daypart,
            "with_advice": True,
        }

    def _can_trigger_automatic_weather(self, source: str, current: datetime) -> bool:
        if not self._can_display_automatic_weather():
            return False
        if source == "daypart_auto":
            return self.daypart_weather_reporter.should_auto_report(current)

        daypart = self.daypart_weather_reporter.current_daypart(current)
        if daypart is None:
            return True
        return not self.daypart_weather_reporter.has_reported(daypart, current)

    def _can_display_automatic_weather(self) -> bool:
        return self.state_manager.current_priority() < STATE_PRIORITIES[PetState.REMINDING_DRINK]

    def _mark_daypart_reported(self, daypart: str, requested_at: datetime) -> None:
        field_name = self.daypart_weather_reporter.FIELD_MAP.get(daypart)
        if not field_name:
            return
        setattr(self.runtime_state, field_name, date_key(requested_at))
        self.save_runtime_state()

    def _on_weather_ready(self, snapshot: WeatherSnapshot | None) -> None:
        self._weather_in_flight = False
        request = self._pending_request
        self._pending_request = None
        self.schedule_next_refresh(from_time=now_local())

        if snapshot is None:
            if request is not None:
                fallback = self.dialog_service.fetch_message("weather_fallback", prefer_remote=False)
                self.notification_center.publish(
                    UiMessage(
                        text=fallback.text,
                        category=fallback.category,
                        source=fallback.source,
                        priority=55,
                        ttl_ms=4000,
                        cooldown_key="weather:fallback",
                        cooldown_ms=3000,
                        dedupe_key="weather:fallback",
                        dedupe_ms=5000,
                    )
                )
            return

        self.interaction_manager.mark_weather_updated(snapshot.retrieved_at or now_local())
        if request is not None:
            self._announce_snapshot(snapshot, request)

    def _on_weather_failed(self, exc: Exception) -> None:
        self._weather_in_flight = False
        request = self._pending_request
        self._pending_request = None
        self.schedule_next_refresh(from_time=now_local())
        self.logger.warning("Weather worker failed: %s", exc)
        if request is not None:
            fallback = self.dialog_service.fetch_message("weather_fallback", prefer_remote=False)
            self.notification_center.publish(
                UiMessage(
                    text=fallback.text,
                    category=fallback.category,
                    source=fallback.source,
                    priority=55,
                    ttl_ms=4000,
                    cooldown_key="weather:fallback",
                    cooldown_ms=3000,
                    dedupe_key="weather:fallback",
                    dedupe_ms=5000,
                )
            )

    def _announce_snapshot(
        self,
        snapshot: WeatherSnapshot,
        request: dict[str, object],
    ) -> None:
        manual = bool(request.get("manual", False))
        if not manual and not self._can_display_automatic_weather():
            return

        self._weather_advice_ticket += 1
        self.state_manager.request_state(
            PetState.WEATHER_SHOWING,
            ttl_ms=4500,
            queue_if_blocked=manual,
            max_wait_ms=1500 if manual else None,
        )
        self.notification_center.publish(
            UiMessage(
                text=format_weather_summary(snapshot),
                category="weather",
                source=snapshot.source,
                priority=60 if manual else 50,
                ttl_ms=5000,
                cooldown_key="weather:summary",
                cooldown_ms=2500,
                dedupe_key=f"weather:summary:{snapshot.city}:{snapshot.summary}",
                dedupe_ms=2000,
                drop_if_state_at_least=None
                if manual
                else STATE_PRIORITIES[PetState.REMINDING_DRINK],
            )
        )

        if request.get("consume_daypart"):
            daypart = request.get("daypart")
            requested_at = request.get("requested_at")
            if isinstance(daypart, str) and isinstance(requested_at, datetime):
                self._mark_daypart_reported(daypart, requested_at)

        if request.get("with_advice", True):
            advice = self.weather_care_advisor.evaluate(snapshot)
            if advice is not None:
                self._schedule_weather_advice(advice.dialog_category)

    def _schedule_weather_advice(self, category: str) -> None:
        ticket = self._weather_advice_ticket
        delay_ms = random.randint(500, 1500)
        QTimer.singleShot(delay_ms, lambda: self._emit_weather_advice(ticket, category))

    def _emit_weather_advice(self, ticket: int, category: str) -> None:
        if ticket != self._weather_advice_ticket:
            return
        if self.state_manager.current_priority() >= STATE_PRIORITIES[PetState.REMINDING_DRINK]:
            return
        message = self.dialog_service.fetch_message(category, prefer_remote=False)
        self.notification_center.publish(
            UiMessage(
                text=message.text,
                category=message.category,
                source=message.source,
                priority=45,
                ttl_ms=max(3000, message.expires_in_seconds * 1000),
                cooldown_key=f"weather:advice:{category}",
                cooldown_ms=5000,
                dedupe_key=f"weather:advice:{category}",
                dedupe_ms=8000,
                drop_if_state_at_least=STATE_PRIORITIES[PetState.REMINDING_DRINK],
            )
        )
