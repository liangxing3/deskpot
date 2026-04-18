from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from utils.time_utils import parse_datetime, serialize_datetime


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

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "WindowPosition":
        payload = payload or {}
        return cls(x=int(payload.get("x", 1200)), y=int(payload.get("y", 700)))

    def to_dict(self) -> dict[str, int]:
        return {"x": self.x, "y": self.y}


@dataclass(slots=True)
class AppConfig:
    window_position: WindowPosition = field(default_factory=WindowPosition)
    drink_remind_interval_minutes: int = 45
    sedentary_remind_interval_minutes: int = 90
    random_dialog_enabled: bool = True
    hourly_report_enabled: bool = True
    weather_enabled: bool = True
    dialog_cooldown_seconds: int = 3
    weather_update_interval_minutes: int = 60
    auto_start: bool = False
    reminder_pause_until: object | None = None

    @classmethod
    def default(cls) -> "AppConfig":
        return cls()

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AppConfig":
        return cls(
            window_position=WindowPosition.from_dict(payload.get("window_position")),
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
            auto_start=bool(payload.get("auto_start", False)),
            reminder_pause_until=parse_datetime(payload.get("reminder_pause_until")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "window_position": self.window_position.to_dict(),
            "drink_remind_interval_minutes": self.drink_remind_interval_minutes,
            "sedentary_remind_interval_minutes": self.sedentary_remind_interval_minutes,
            "random_dialog_enabled": self.random_dialog_enabled,
            "hourly_report_enabled": self.hourly_report_enabled,
            "weather_enabled": self.weather_enabled,
            "dialog_cooldown_seconds": self.dialog_cooldown_seconds,
            "weather_update_interval_minutes": self.weather_update_interval_minutes,
            "auto_start": self.auto_start,
            "reminder_pause_until": serialize_datetime(self.reminder_pause_until),
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
    weather_code: str | int | None = None
    current_temp: str | int | float | None = None
    high_temp: str | int | float | None = None
    low_temp: str | int | float | None = None
    humidity: str | int | float | None = None
    wind: str | None = None
    forecast: list[dict[str, Any]] | None = None
    hourly: list[dict[str, Any]] | None = None
    precipitation_probability: str | int | float | None = None
    life_indices: dict[str, Any] | None = None
    retrieved_at: object | None = None
    source: str = "remote"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WeatherSnapshot":
        return cls(
            city=str(payload.get("city", "")),
            summary=str(payload.get("summary", "")),
            weather_code=payload.get("weather_code"),
            current_temp=payload.get("current_temp"),
            high_temp=payload.get("high_temp"),
            low_temp=payload.get("low_temp"),
            humidity=payload.get("humidity"),
            wind=payload.get("wind"),
            forecast=payload.get("forecast"),
            hourly=payload.get("hourly"),
            precipitation_probability=payload.get("precipitation_probability"),
            life_indices=payload.get("life_indices"),
            retrieved_at=parse_datetime(payload.get("retrieved_at")),
            source=str(payload.get("source", "remote")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "city": self.city,
            "summary": self.summary,
            "weather_code": self.weather_code,
            "current_temp": self.current_temp,
            "high_temp": self.high_temp,
            "low_temp": self.low_temp,
            "humidity": self.humidity,
            "wind": self.wind,
            "forecast": self.forecast,
            "hourly": self.hourly,
            "precipitation_probability": self.precipitation_probability,
            "life_indices": self.life_indices,
            "retrieved_at": serialize_datetime(self.retrieved_at),
            "source": self.source,
        }
