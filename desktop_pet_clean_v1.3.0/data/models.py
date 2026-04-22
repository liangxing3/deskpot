from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from utils.time_utils import parse_datetime, serialize_datetime


VALID_WEATHER_ALERT_SENSITIVITIES = {"low", "standard", "high"}


def _normalize_weather_alert_sensitivity(value: Any) -> str:
    normalized = str(value or "standard").strip().lower()
    if normalized in VALID_WEATHER_ALERT_SENSITIVITIES:
        return normalized
    return "standard"


class PetState(str, Enum):
    IDLE = "IDLE"
    DRAGGING = "DRAGGING"
    INTERACTING = "INTERACTING"
    MANUAL_ACTION = "MANUAL_ACTION"
    GROWING = "GROWING"
    RANDOM_ANIMATING = "RANDOM_ANIMATING"
    REMINDING_DRINK = "REMINDING_DRINK"
    REMINDING_SEDENTARY = "REMINDING_SEDENTARY"
    TIME_REPORTING = "TIME_REPORTING"
    WEATHER_SHOWING = "WEATHER_SHOWING"


class EmotionState(str, Enum):
    NORMAL = "NORMAL"
    WORKING = "WORKING"
    HUNGRY = "HUNGRY"
    TIRED = "TIRED"
    DIRTY = "DIRTY"
    LOW_ENERGY = "LOW_ENERGY"
    LOW_HAPPINESS = "LOW_HAPPINESS"
    DRAINED = "DRAINED"
    BORED = "BORED"


@dataclass(slots=True)
class WindowPosition:
    x: int = 1200
    y: int = 700
    first_shown: bool = True

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WindowPosition":
        payload = payload or {}
        return cls(
            x=int(payload.get("x", 1200)),
            y=int(payload.get("y", 700)),
            first_shown=bool(payload.get("first_shown", True)),
        )

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "x": self.x,
            "y": self.y,
            "first_shown": self.first_shown,
        }


@dataclass(slots=True)
class AppConfig:
    window_position: WindowPosition = field(default_factory=WindowPosition)
    dialog_positions: dict[str, WindowPosition] = field(default_factory=dict)
    drink_remind_interval_minutes: int = 45
    sedentary_remind_interval_minutes: int = 90
    random_dialog_enabled: bool = True
    hourly_report_enabled: bool = True
    weather_enabled: bool = True
    dialog_cooldown_seconds: int = 3
    weather_update_interval_minutes: int = 60
    weather_city_override: str = ""
    weather_auto_location: bool = True
    weather_temperature_unit: str = "C"
    weather_bubble_enabled: bool = True
    weather_broadcast_time: str = "08:00"
    weather_severe_alert_enabled: bool = False
    weather_background_monitor_enabled: bool = True
    weather_change_alert_enabled: bool = True
    weather_change_alert_sensitivity: str = "standard"
    ui_font_size_px: int = 13
    auto_start: bool = False
    reminder_pause_until: object | None = None

    @classmethod
    def default(cls) -> "AppConfig":
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppConfig":
        dialog_positions_payload = payload.get("dialog_positions") or {}
        return cls(
            window_position=WindowPosition.from_dict(payload.get("window_position")),
            dialog_positions={
                str(key): WindowPosition.from_dict(value)
                for key, value in dialog_positions_payload.items()
                if isinstance(value, dict)
            },
            drink_remind_interval_minutes=int(payload.get("drink_remind_interval_minutes", 45)),
            sedentary_remind_interval_minutes=int(
                payload.get("sedentary_remind_interval_minutes", 90)
            ),
            random_dialog_enabled=bool(payload.get("random_dialog_enabled", True)),
            hourly_report_enabled=bool(payload.get("hourly_report_enabled", True)),
            weather_enabled=bool(payload.get("weather_enabled", True)),
            dialog_cooldown_seconds=int(payload.get("dialog_cooldown_seconds", 3)),
            weather_update_interval_minutes=int(
                payload.get("weather_update_interval_minutes", 60)
            ),
            weather_city_override=str(payload.get("weather_city_override", "")),
            weather_auto_location=bool(payload.get("weather_auto_location", True)),
            weather_temperature_unit=str(payload.get("weather_temperature_unit", "C")).upper(),
            weather_bubble_enabled=bool(payload.get("weather_bubble_enabled", True)),
            weather_broadcast_time=str(payload.get("weather_broadcast_time", "08:00")),
            weather_severe_alert_enabled=bool(
                payload.get("weather_severe_alert_enabled", False)
            ),
            weather_background_monitor_enabled=bool(
                payload.get("weather_background_monitor_enabled", True)
            ),
            weather_change_alert_enabled=bool(
                payload.get("weather_change_alert_enabled", True)
            ),
            weather_change_alert_sensitivity=_normalize_weather_alert_sensitivity(
                payload.get("weather_change_alert_sensitivity", "standard")
            ),
            ui_font_size_px=int(payload.get("ui_font_size_px", 13)),
            auto_start=bool(payload.get("auto_start", False)),
            reminder_pause_until=parse_datetime(payload.get("reminder_pause_until")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_position": self.window_position.to_dict(),
            "dialog_positions": {
                key: value.to_dict() for key, value in self.dialog_positions.items()
            },
            "drink_remind_interval_minutes": self.drink_remind_interval_minutes,
            "sedentary_remind_interval_minutes": self.sedentary_remind_interval_minutes,
            "random_dialog_enabled": self.random_dialog_enabled,
            "hourly_report_enabled": self.hourly_report_enabled,
            "weather_enabled": self.weather_enabled,
            "dialog_cooldown_seconds": self.dialog_cooldown_seconds,
            "weather_update_interval_minutes": self.weather_update_interval_minutes,
            "weather_city_override": self.weather_city_override,
            "weather_auto_location": self.weather_auto_location,
            "weather_temperature_unit": self.weather_temperature_unit,
            "weather_bubble_enabled": self.weather_bubble_enabled,
            "weather_broadcast_time": self.weather_broadcast_time,
            "weather_severe_alert_enabled": self.weather_severe_alert_enabled,
            "weather_background_monitor_enabled": self.weather_background_monitor_enabled,
            "weather_change_alert_enabled": self.weather_change_alert_enabled,
            "weather_change_alert_sensitivity": _normalize_weather_alert_sensitivity(
                self.weather_change_alert_sensitivity
            ),
            "ui_font_size_px": self.ui_font_size_px,
            "auto_start": self.auto_start,
            "reminder_pause_until": serialize_datetime(self.reminder_pause_until),
        }


@dataclass(slots=True)
class WeatherAlertState:
    last_checked_at: object | None = None
    last_snapshot: "WeatherSnapshot | None" = None
    last_context_key: str | None = None
    cooldown_signatures: dict[str, object] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WeatherAlertState":
        payload = payload or {}
        raw_cooldowns = payload.get("cooldown_signatures") or {}
        cooldown_signatures = {
            str(signature): parse_datetime(timestamp)
            for signature, timestamp in raw_cooldowns.items()
            if str(signature).strip()
        }
        last_snapshot_payload = payload.get("last_snapshot")
        return cls(
            last_checked_at=parse_datetime(payload.get("last_checked_at")),
            last_snapshot=WeatherSnapshot.from_dict(last_snapshot_payload)
            if isinstance(last_snapshot_payload, dict)
            else None,
            last_context_key=str(payload.get("last_context_key", "")).strip() or None,
            cooldown_signatures=cooldown_signatures,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "last_checked_at": serialize_datetime(self.last_checked_at),
            "last_snapshot": self.last_snapshot.to_dict() if self.last_snapshot is not None else None,
            "last_context_key": self.last_context_key,
            "cooldown_signatures": {
                signature: serialize_datetime(timestamp)
                for signature, timestamp in self.cooldown_signatures.items()
            },
        }


@dataclass(slots=True)
class PetVitals:
    happiness: int = 80
    energy: int = 80
    last_updated_at: object | None = None
    last_hourly_report_hour: str | None = None
    last_manual_action: str | None = None
    status_bar_visible: bool = True
    weather_morning_date: str | None = None
    weather_noon_date: str | None = None
    weather_evening_date: str | None = None
    weather_alert_state: WeatherAlertState = field(default_factory=WeatherAlertState)

    @classmethod
    def default(cls) -> "PetVitals":
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "PetVitals":
        return cls(
            happiness=int(payload.get("happiness", 80)),
            energy=int(payload.get("energy", 80)),
            last_updated_at=parse_datetime(payload.get("last_updated_at")),
            last_hourly_report_hour=payload.get("last_hourly_report_hour"),
            last_manual_action=payload.get("last_manual_action"),
            status_bar_visible=bool(payload.get("status_bar_visible", True)),
            weather_morning_date=payload.get("weather_morning_date"),
            weather_noon_date=payload.get("weather_noon_date"),
            weather_evening_date=payload.get("weather_evening_date"),
            weather_alert_state=WeatherAlertState.from_dict(payload.get("weather_alert_state")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "happiness": self.happiness,
            "energy": self.energy,
            "last_updated_at": serialize_datetime(self.last_updated_at),
            "last_hourly_report_hour": self.last_hourly_report_hour,
            "last_manual_action": self.last_manual_action,
            "status_bar_visible": self.status_bar_visible,
            "weather_morning_date": self.weather_morning_date,
            "weather_noon_date": self.weather_noon_date,
            "weather_evening_date": self.weather_evening_date,
            "weather_alert_state": self.weather_alert_state.to_dict(),
        }


@dataclass(slots=True)
class AnimationManifestEntry:
    id: str
    path: str
    state: PetState | None = None
    emotion_state: EmotionState | None = None
    variant: str | None = None
    weight: int = 1
    loop: bool = True
    min_duration_ms: int = 3000

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnimationManifestEntry":
        state = payload.get("state")
        emotion_state = payload.get("emotion_state")
        return cls(
            id=str(payload["id"]),
            path=str(payload["path"]),
            state=PetState(str(state).upper()) if state else None,
            emotion_state=EmotionState(str(emotion_state).upper()) if emotion_state else None,
            variant=str(payload.get("variant")) if payload.get("variant") else None,
            weight=int(payload.get("weight", 1)),
            loop=bool(payload.get("loop", True)),
            min_duration_ms=int(payload.get("min_duration_ms", 3000)),
        )


@dataclass(slots=True)
class DialogMessage:
    text: str
    category: str
    source: str
    expires_in_seconds: int = 4
    message_id: str | None = None


@dataclass(slots=True)
class UiMessage:
    text: str
    category: str
    source: str = "system"
    priority: int = 0
    ttl_ms: int = 4000
    cooldown_key: str | None = None
    cooldown_ms: int = 0
    dedupe_key: str | None = None
    dedupe_ms: int = 0
    drop_if_state_at_least: int | None = None

    def to_dialog_message(self) -> DialogMessage:
        expires_in_seconds = max(1, int((self.ttl_ms + 999) / 1000))
        return DialogMessage(
            text=self.text,
            category=self.category,
            source=self.source,
            expires_in_seconds=expires_in_seconds,
        )


@dataclass(slots=True)
class AnswerBookResult:
    question: str
    answer: str
    source: str = "remote"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AnswerBookResult":
        return cls(
            question=str(payload.get("question", "")),
            answer=str(payload.get("answer", "")),
            source=str(payload.get("source", "remote")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "question": self.question,
            "answer": self.answer,
            "source": self.source,
        }


@dataclass(slots=True)
class WeatherAdviceResult:
    advice_type: str
    dialog_category: str
    suggest_take_umbrella: bool = False
    suggest_extra_layer: bool = False
    suggest_light_clothing: bool = False


@dataclass(slots=True)
class WeatherSnapshot:
    city: str
    summary: str
    location: str | None = None
    condition_text: str | None = None
    condition_code: str | int | None = None
    weather_code: str | int | None = None
    current_temp: str | int | float | None = None
    high_temp: str | int | float | None = None
    low_temp: str | int | float | None = None
    feels_like: str | int | float | None = None
    humidity: str | int | float | None = None
    wind: str | None = None
    wind_direction: str | None = None
    wind_scale: str | int | float | None = None
    wind_speed: str | int | float | None = None
    precipitation: str | int | float | None = None
    forecast: list[dict[str, Any]] | None = None
    hourly: list[dict[str, Any]] | None = None
    precipitation_probability: str | int | float | None = None
    pressure: str | int | float | None = None
    visibility: str | int | float | None = None
    aqi: str | int | float | None = None
    alerts: list[dict[str, Any]] | None = None
    warning_texts: list[str] | None = None
    now: dict[str, Any] | None = None
    raw_payload: dict[str, Any] | None = None
    life_indices: dict[str, Any] | None = None
    captured_at: object | None = None
    retrieved_at: object | None = None
    source: str = "remote"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WeatherSnapshot":
        captured_at = parse_datetime(payload.get("captured_at") or payload.get("retrieved_at"))
        return cls(
            city=str(payload.get("city", "")),
            summary=str(payload.get("summary", "")),
            location=payload.get("location"),
            condition_text=payload.get("condition_text") or payload.get("summary"),
            condition_code=payload.get("condition_code", payload.get("weather_code")),
            weather_code=payload.get("weather_code"),
            current_temp=payload.get("current_temp"),
            high_temp=payload.get("high_temp"),
            low_temp=payload.get("low_temp"),
            feels_like=payload.get("feels_like"),
            humidity=payload.get("humidity"),
            wind=payload.get("wind"),
            wind_direction=payload.get("wind_direction"),
            wind_scale=payload.get("wind_scale"),
            wind_speed=payload.get("wind_speed"),
            precipitation=payload.get("precipitation"),
            forecast=payload.get("forecast"),
            hourly=payload.get("hourly"),
            precipitation_probability=payload.get("precipitation_probability"),
            pressure=payload.get("pressure"),
            visibility=payload.get("visibility"),
            aqi=payload.get("aqi"),
            alerts=payload.get("alerts"),
            warning_texts=payload.get("warning_texts"),
            now=payload.get("now"),
            raw_payload=payload.get("raw_payload"),
            life_indices=payload.get("life_indices"),
            captured_at=captured_at,
            retrieved_at=parse_datetime(payload.get("retrieved_at")) or captured_at,
            source=str(payload.get("source", "remote")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "summary": self.summary,
            "location": self.location,
            "condition_text": self.condition_text,
            "condition_code": self.condition_code,
            "weather_code": self.weather_code,
            "current_temp": self.current_temp,
            "high_temp": self.high_temp,
            "low_temp": self.low_temp,
            "feels_like": self.feels_like,
            "humidity": self.humidity,
            "wind": self.wind,
            "wind_direction": self.wind_direction,
            "wind_scale": self.wind_scale,
            "wind_speed": self.wind_speed,
            "precipitation": self.precipitation,
            "forecast": self.forecast,
            "hourly": self.hourly,
            "precipitation_probability": self.precipitation_probability,
            "pressure": self.pressure,
            "visibility": self.visibility,
            "aqi": self.aqi,
            "alerts": self.alerts,
            "warning_texts": self.warning_texts,
            "now": self.now,
            "raw_payload": self.raw_payload,
            "life_indices": self.life_indices,
            "captured_at": serialize_datetime(self.captured_at or self.retrieved_at),
            "retrieved_at": serialize_datetime(self.retrieved_at),
            "source": self.source,
        }
