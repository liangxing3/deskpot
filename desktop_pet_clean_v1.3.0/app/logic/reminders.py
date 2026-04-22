from __future__ import annotations

from dataclasses import dataclass

from data.models import AppConfig, PetVitals, WeatherSnapshot
from data.pet_models import PetStatus
from utils.time_utils import date_key, hour_key, is_within_hourly_window, minutes_since, now_local


@dataclass(slots=True)
class ReminderEvent:
    kind: str
    text: str
    ttl_ms: int = 5200


class ReminderEngine:
    def __init__(self) -> None:
        self._last_drink_reminder_at = None
        self._last_sedentary_reminder_at = None
        self._last_severe_weather_key: str | None = None

    def collect_due_events(
        self,
        *,
        config: AppConfig,
        status: PetStatus,
        vitals: PetVitals,
        last_activity_at,
        weather_snapshot: WeatherSnapshot | None = None,
        current_time=None,
    ) -> list[ReminderEvent]:
        now = current_time or now_local()
        if config.reminder_pause_until and now < config.reminder_pause_until:
            return []

        events: list[ReminderEvent] = []
        events.extend(self._maybe_drink(config, last_activity_at, now))
        events.extend(self._maybe_sedentary(config, last_activity_at, now))
        events.extend(self._maybe_hourly(config, vitals, now))
        events.extend(self._maybe_weather_monitor(config, vitals, now))
        events.extend(self._maybe_weather(config, vitals, weather_snapshot, now))
        events.extend(self._maybe_severe_weather(config, weather_snapshot, now))
        _ = status
        return events

    def note_activity(self, current_time=None) -> None:
        now = current_time or now_local()
        self._last_drink_reminder_at = now
        self._last_sedentary_reminder_at = now

    def _maybe_drink(self, config: AppConfig, last_activity_at, current_time) -> list[ReminderEvent]:
        if config.drink_remind_interval_minutes <= 0:
            return []
        if last_activity_at is None:
            return []
        elapsed = minutes_since(last_activity_at, current_time)
        since_last_emit = minutes_since(self._last_drink_reminder_at, current_time)
        if elapsed >= config.drink_remind_interval_minutes and since_last_emit >= max(
            5, config.drink_remind_interval_minutes - 1
        ):
            self._last_drink_reminder_at = current_time
            return [ReminderEvent("drink", "该喝点水了，先抿两口再继续忙。")]
        return []

    def _maybe_sedentary(self, config: AppConfig, last_activity_at, current_time) -> list[ReminderEvent]:
        if config.sedentary_remind_interval_minutes <= 0:
            return []
        if last_activity_at is None:
            return []
        elapsed = minutes_since(last_activity_at, current_time)
        since_last_emit = minutes_since(self._last_sedentary_reminder_at, current_time)
        if elapsed >= config.sedentary_remind_interval_minutes and since_last_emit >= max(
            10, config.sedentary_remind_interval_minutes - 1
        ):
            self._last_sedentary_reminder_at = current_time
            return [ReminderEvent("sedentary", "坐太久了，起来活动两分钟会更舒服。", ttl_ms=5800)]
        return []

    def _maybe_hourly(self, config: AppConfig, vitals: PetVitals, current_time) -> list[ReminderEvent]:
        if not config.hourly_report_enabled or not is_within_hourly_window(current_time):
            return []
        current_hour = hour_key(current_time)
        if vitals.last_hourly_report_hour == current_hour:
            return []
        vitals.last_hourly_report_hour = current_hour
        return [ReminderEvent("hourly", f"现在是 {current_time:%H}:00。把最重要的一件事推进一下。")]

    def _maybe_weather_monitor(
        self,
        config: AppConfig,
        vitals: PetVitals,
        current_time,
    ) -> list[ReminderEvent]:
        if not config.weather_enabled or not config.weather_background_monitor_enabled:
            return []
        interval_minutes = max(60, int(config.weather_update_interval_minutes or 60))
        last_checked_at = vitals.weather_alert_state.last_checked_at
        if last_checked_at is not None and minutes_since(last_checked_at, current_time) < interval_minutes:
            return []
        vitals.weather_alert_state.last_checked_at = current_time
        return [ReminderEvent("weather_monitor_tick", "")]

    def _maybe_weather(
        self,
        config: AppConfig,
        vitals: PetVitals,
        weather_snapshot: WeatherSnapshot | None,
        current_time,
    ) -> list[ReminderEvent]:
        if not config.weather_enabled or not config.weather_bubble_enabled:
            return []
        target_hour, target_minute = _parse_time_string(config.weather_broadcast_time)
        if (current_time.hour, current_time.minute) < (target_hour, target_minute):
            return []
        field_name = _weather_bucket_field(current_time.hour)
        if getattr(vitals, field_name) == date_key(current_time):
            return []
        setattr(vitals, field_name, date_key(current_time))
        if weather_snapshot is None:
            return [ReminderEvent("weather_broadcast", "到天气播报时间了，我去看一眼外面的情况。", ttl_ms=5600)]
        return [
            ReminderEvent(
                "weather_broadcast",
                f"今天天气：{weather_snapshot.summary or '已更新'}。",
                ttl_ms=5600,
            )
        ]

    def _maybe_severe_weather(
        self,
        config: AppConfig,
        weather_snapshot: WeatherSnapshot | None,
        current_time,
    ) -> list[ReminderEvent]:
        if not config.weather_enabled or not config.weather_severe_alert_enabled:
            return []
        if weather_snapshot is None:
            return []
        severe = _looks_severe(weather_snapshot)
        if not severe:
            return []
        dedupe_key = f"{date_key(current_time)}:{weather_snapshot.summary}"
        if dedupe_key == self._last_severe_weather_key:
            return []
        self._last_severe_weather_key = dedupe_key
        return [ReminderEvent("weather_severe", "天气状况偏激烈，出门前记得多看一眼。", ttl_ms=6200)]


def _parse_time_string(value: str) -> tuple[int, int]:
    try:
        hour_str, minute_str = value.split(":", 1)
        return max(0, min(23, int(hour_str))), max(0, min(59, int(minute_str)))
    except Exception:
        return 8, 0


def _weather_bucket_field(hour: int) -> str:
    if hour < 12:
        return "weather_morning_date"
    if hour < 18:
        return "weather_noon_date"
    return "weather_evening_date"


def _looks_severe(snapshot: WeatherSnapshot) -> bool:
    summary = (snapshot.summary or "").lower()
    keywords = ("暴雨", "雷", "大风", "高温", "寒潮", "沙尘", "storm", "thunder", "typhoon")
    if any(item in summary for item in keywords):
        return True
    try:
        code = int(snapshot.weather_code)
    except (TypeError, ValueError):
        return False
    return code >= 1001
