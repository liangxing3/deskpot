from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

import developer_config
from data.models import WeatherSnapshot
from utils.time_utils import now_local


class CityResolver(ABC):
    @abstractmethod
    def resolve_city(self, force_refresh: bool = False) -> str | None:
        raise NotImplementedError


class WeatherService(ABC):
    @abstractmethod
    def get_weather(self, force_refresh: bool = False) -> WeatherSnapshot | None:
        raise NotImplementedError


class IpCityResolver(CityResolver):
    CACHE_KEY = "city:last_lookup"

    def __init__(self, *, cache_service, logger: logging.Logger) -> None:
        self.cache_service = cache_service
        self.logger = logger

    def resolve_city(self, force_refresh: bool = False) -> str | None:
        _ = force_refresh
        if developer_config.WEATHER_DEFAULT_CITY:
            return developer_config.WEATHER_DEFAULT_CITY
        return None


class DeveloperConfiguredWeatherService(WeatherService):
    CACHE_KEY = "weather:last_snapshot"

    def __init__(self, *, cache_service, city_resolver: CityResolver, logger: logging.Logger) -> None:
        self.cache_service = cache_service
        self.city_resolver = city_resolver
        self.logger = logger
        self._client = None

    def has_cached_weather(self) -> bool:
        return bool(self.cache_service.get(self.CACHE_KEY, allow_expired=True))

    def get_cached_weather(self) -> WeatherSnapshot | None:
        cached = self.cache_service.get(self.CACHE_KEY, allow_expired=True)
        if not cached:
            return None
        snapshot = WeatherSnapshot.from_dict(cached)
        snapshot.source = "cache"
        return snapshot

    def get_weather(self, force_refresh: bool = False) -> WeatherSnapshot | None:
        if not force_refresh:
            cached = self.cache_service.get(self.CACHE_KEY)
            if cached:
                snapshot = WeatherSnapshot.from_dict(cached)
                snapshot.source = "cache"
                return snapshot

        try:
            city = self.city_resolver.resolve_city(force_refresh=force_refresh)
            response = developer_config.invoke_uapi_weather_operation(
                self._build_client(),
                developer_config.WEATHER_OPERATION,
                city=city,
                adcode=developer_config.WEATHER_DEFAULT_ADCODE or None,
            )
            snapshot = self._build_snapshot(response, city)
            self.cache_service.set(
                self.CACHE_KEY,
                snapshot.to_dict(),
                ttl_seconds=developer_config.DEFAULT_WEATHER_CACHE_TTL_SECONDS,
            )
            return snapshot
        except Exception as exc:
            self.logger.warning("Weather request failed: %s", exc)
            return self.get_cached_weather()

    def _build_client(self) -> Any:
        if self._client is not None:
            return self._client

        for module_name in ("uapi", "uapi_sdk_python"):
            try:
                module = __import__(module_name, fromlist=["UapiClient"])
                client_class = getattr(module, "UapiClient", None)
                if client_class is None:
                    continue
                self._client = client_class(
                    base_url=developer_config.WEATHER_BASE_URL,
                    token=developer_config.WEATHER_TOKEN,
                    timeout=developer_config.WEATHER_TIMEOUT,
                )
                return self._client
            except ImportError:
                continue

        raise RuntimeError("UAPI Python SDK is not installed.")

    def _build_snapshot(self, payload: Any, city: str | None) -> WeatherSnapshot:
        parsed = developer_config.parse_weather_response(payload, city or "")
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        forecast = data.get("forecast") if isinstance(data.get("forecast"), list) else None
        hourly = data.get("hourly") if isinstance(data.get("hourly"), list) else None
        life_indices = data.get("indices")
        precipitation_probability = (
            data.get("precipitation_probability")
            or data.get("pop")
            or (hourly[0].get("pop") if hourly and isinstance(hourly[0], dict) else None)
        )

        return WeatherSnapshot(
            city=parsed.get("city") or city or "当前位置",
            summary=parsed.get("summary") or "天气已更新",
            weather_code=parsed.get("weather_code"),
            current_temp=parsed.get("current_temp"),
            high_temp=parsed.get("high_temp"),
            low_temp=parsed.get("low_temp"),
            humidity=parsed.get("humidity"),
            wind=parsed.get("wind"),
            forecast=forecast,
            hourly=hourly,
            precipitation_probability=precipitation_probability,
            life_indices=life_indices if isinstance(life_indices, dict) else None,
            retrieved_at=now_local(),
            source="remote",
        )


WEATHER_ICON_MAP: dict[int, str] = {
    100: "☀️",
    101: "⛅",
    102: "🌤️",
    103: "⛅",
    104: "☁️",
    150: "🌙",
    151: "🌙",
    152: "🌙",
    153: "🌙",
    300: "🌦️",
    301: "🌧️",
    302: "⛈️",
    303: "⛈️",
    304: "⛈️",
    305: "🌧️",
    306: "🌧️",
    307: "🌧️",
    308: "🌧️",
    309: "🌧️",
    310: "🌊",
    311: "🌊",
    312: "🌊",
    313: "🧊",
    314: "🌧️",
    315: "🌧️",
    316: "🌊",
    317: "🌊",
    318: "🌊",
    350: "🌙",
    351: "🌙",
    399: "🌧️",
    400: "🌨️",
    401: "🌨️",
    402: "❄️",
    403: "❄️",
    404: "🌨️",
    405: "🌨️",
    406: "🌨️",
    407: "🌨️",
    408: "🌨️",
    409: "❄️",
    410: "❄️",
    456: "🌙",
    457: "🌙",
    499: "❄️",
    500: "🌫️",
    501: "🌫️",
    502: "😶‍🌫️",
    503: "💨",
    504: "💨",
    507: "🏜️",
    508: "🏜️",
    509: "🌫️",
    510: "🌫️",
    511: "😶‍🌫️",
    512: "😶‍🌫️",
    513: "😶‍🌫️",
    514: "🌫️",
    515: "🌫️",
    800: "🌑",
    801: "🌒",
    802: "🌓",
    803: "🌔",
    804: "🌕",
    805: "🌖",
    806: "🌗",
    807: "🌘",
    900: "🥵",
    901: "🥶",
    999: "❓",
    1001: "🌀",
    1002: "🌪️",
    1003: "🌊",
    1004: "❄️",
    1005: "🥶",
    1006: "💨",
    1007: "🏜️",
    1008: "🧊",
    1009: "🌡️",
    1010: "🥵",
    1014: "⚡",
    1015: "🧊",
    1017: "🌫️",
    1019: "😶‍🌫️",
    1020: "⛈️",
    1021: "🧊",
    1022: "☀️",
    1024: "🥵",
    1029: "😶‍🌫️",
    1030: "🌨️",
    1031: "⛈️",
    1035: "🌧️",
    1038: "🌧️",
    1039: "🌡️",
}


def _weather_icon(weather_code: str | int | None) -> str:
    if weather_code is None:
        return ""
    try:
        normalized = int(weather_code)
    except (TypeError, ValueError):
        return ""
    if normalized in WEATHER_ICON_MAP:
        return WEATHER_ICON_MAP[normalized]
    if normalized >= 1001:
        return "⚠️"
    return ""


def format_weather_summary(snapshot: WeatherSnapshot | None) -> str:
    if snapshot is None:
        return "天气暂时获取失败。"

    summary = snapshot.summary or "天气已更新"
    icon = _weather_icon(snapshot.weather_code)
    weather_text = f"{icon} {summary}".strip() if icon else summary

    parts: list[str] = []
    if snapshot.city:
        parts.append(snapshot.city)
    parts.append(weather_text)

    if snapshot.current_temp is not None:
        parts.append(f"{snapshot.current_temp}°C")

    high_low: list[str] = []
    if snapshot.high_temp is not None:
        high_low.append(f"高 {snapshot.high_temp}°C")
    if snapshot.low_temp is not None:
        high_low.append(f"低 {snapshot.low_temp}°C")
    if high_low:
        parts.append(" / ".join(high_low))

    if snapshot.humidity is not None:
        parts.append(f"湿度 {snapshot.humidity}%")
    if snapshot.wind:
        parts.append(snapshot.wind)

    return " | ".join(part for part in parts if part)
