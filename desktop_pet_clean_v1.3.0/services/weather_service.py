from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any

import developer_config
import requests
from data.models import WeatherSnapshot
from utils.log_exceptions import log_exceptions
from utils.time_utils import now_local


class CityResolver(ABC):
    @abstractmethod
    @log_exceptions(signal_name="weather_error", fallback=None)
    def resolve_city(self, force_refresh: bool = False) -> str | None:
        raise NotImplementedError


class WeatherService(ABC):
    @abstractmethod
    @log_exceptions(signal_name="weather_error", fallback=None)
    def get_weather(self, force_refresh: bool = False) -> WeatherSnapshot | None:
        raise NotImplementedError


class IpCityResolver(CityResolver):
    CACHE_KEY = "city:last_lookup"

    def __init__(self, *, cache_service, logger: logging.Logger) -> None:
        self.cache_service = cache_service
        self.logger = logger

    def resolve_city(self, force_refresh: bool = False) -> str | None:
        if not force_refresh:
            cached = self.cache_service.get(self.CACHE_KEY)
            if isinstance(cached, str) and cached.strip():
                return cached.strip()

        try:
            request = developer_config.build_ip_city_request()
            response = requests.get(
                request["url"],
                params=request.get("params"),
                headers=request.get("headers"),
                timeout=request.get("timeout"),
            )
            response.raise_for_status()
            city = developer_config.parse_ip_city_response(response.json())
            if city:
                self.cache_service.set(
                    self.CACHE_KEY,
                    city,
                    ttl_seconds=developer_config.DEFAULT_CITY_CACHE_TTL_SECONDS,
                )
                return city
            raise ValueError("IP city response did not contain a city name.")
        except Exception as exc:
            self.logger.warning("IP city lookup failed: %s", exc)
            cached = self.cache_service.get(self.CACHE_KEY, allow_expired=True)
            if isinstance(cached, str) and cached.strip():
                return cached.strip()
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

        last_error: Exception | None = None
        for delay_seconds in (0, 30, 60, 120):
            if delay_seconds:
                time.sleep(delay_seconds)
            try:
                city = self.city_resolver.resolve_city(force_refresh=force_refresh)
                adcode = None if city else (developer_config.WEATHER_DEFAULT_ADCODE or None)
                response = developer_config.invoke_uapi_weather_operation(
                    self._build_client(),
                    developer_config.WEATHER_OPERATION,
                    city=city,
                    adcode=adcode,
                )
                snapshot = self._build_snapshot(response, city)
                self.cache_service.set(
                    self.CACHE_KEY,
                    snapshot.to_dict(),
                    ttl_seconds=developer_config.DEFAULT_WEATHER_CACHE_TTL_SECONDS,
                )
                return snapshot
            except Exception as exc:
                last_error = exc
                self.logger.warning("Weather request failed: %s", exc)

        cached = self.get_cached_weather()
        if cached is not None and cached.retrieved_at is not None:
            try:
                minutes = max(1, int((now_local() - cached.retrieved_at).total_seconds() // 60))
                cached.summary = f"{cached.summary}（上次获取于 {minutes} 分钟前）"
            except Exception:
                pass
        elif last_error is not None:
            self.cache_service.set(
                f"{self.CACHE_KEY}:last_error",
                {"message": str(last_error), "at": str(now_local())},
                ttl_seconds=developer_config.DEFAULT_WEATHER_CACHE_TTL_SECONDS,
            )
        return cached

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
        data = payload.get("data", payload) if isinstance(payload, dict) else {}
        now_data = _first_dict(data.get("now"), data.get("current"), data.get("realtime")) or data
        forecast = data.get("forecast") if isinstance(data.get("forecast"), list) else None
        hourly = (
            data.get("hourly_forecast")
            if isinstance(data.get("hourly_forecast"), list)
            else data.get("hourly")
            if isinstance(data.get("hourly"), list)
            else None
        )
        first_hourly = hourly[0] if hourly and isinstance(hourly[0], dict) else {}
        life_indices = (
            data.get("life_indices")
            if isinstance(data.get("life_indices"), dict)
            else data.get("indices")
            if isinstance(data.get("indices"), dict)
            else None
        )
        air_quality = _first_dict(data.get("air_quality"), data.get("air"), data.get("aqi")) or {}
        alerts = _extract_alerts(data)
        warning_texts = _warning_texts(alerts)
        precipitation_probability = _pick_first(
            data.get("precipitation_probability"),
            data.get("pop"),
            now_data.get("precipitation_probability") if isinstance(now_data, dict) else None,
            now_data.get("pop") if isinstance(now_data, dict) else None,
            first_hourly.get("pop") if isinstance(first_hourly, dict) else None,
        )
        precipitation = _pick_first(
            data.get("precipitation"),
            data.get("precip"),
            data.get("rainfall"),
            now_data.get("precipitation") if isinstance(now_data, dict) else None,
            now_data.get("precip") if isinstance(now_data, dict) else None,
            first_hourly.get("precipitation") if isinstance(first_hourly, dict) else None,
            first_hourly.get("precip") if isinstance(first_hourly, dict) else None,
        )
        first_forecast = forecast[0] if forecast and isinstance(forecast[0], dict) else {}

        city_name = _pick_first(
            data.get("city"),
            now_data.get("city") if isinstance(now_data, dict) else None,
            city,
            "当前位置",
        )
        district = data.get("district")
        if district and district != city_name:
            city_name = f"{city_name} · {district}"

        wind_direction = _pick_first(
            data.get("wind_direction"),
            data.get("wind_dir"),
            now_data.get("wind_direction") if isinstance(now_data, dict) else None,
            now_data.get("wind_dir") if isinstance(now_data, dict) else None,
        )
        wind_scale = _pick_first(
            data.get("wind_power"),
            data.get("wind_scale"),
            now_data.get("wind_power") if isinstance(now_data, dict) else None,
            now_data.get("wind_scale") if isinstance(now_data, dict) else None,
        )
        wind_speed = _pick_first(
            data.get("wind_speed"),
            now_data.get("wind_speed") if isinstance(now_data, dict) else None,
            now_data.get("wind_velocity") if isinstance(now_data, dict) else None,
        )
        wind_parts = [str(part).strip() for part in (wind_direction, wind_scale) if part not in (None, "")]
        if wind_speed not in (None, ""):
            wind_parts.append(f"{wind_speed} km/h")

        captured_at = now_local()
        summary = _pick_first(
            data.get("weather"),
            data.get("summary"),
            data.get("text"),
            now_data.get("weather") if isinstance(now_data, dict) else None,
            now_data.get("summary") if isinstance(now_data, dict) else None,
            now_data.get("text") if isinstance(now_data, dict) else None,
            "天气已更新",
        )
        condition_code = _pick_first(
            data.get("weather_icon"),
            data.get("weather_code"),
            now_data.get("weather_icon") if isinstance(now_data, dict) else None,
            now_data.get("weather_code") if isinstance(now_data, dict) else None,
            now_data.get("icon") if isinstance(now_data, dict) else None,
            now_data.get("code") if isinstance(now_data, dict) else None,
        )

        return WeatherSnapshot(
            city=city_name,
            location=city_name,
            summary=summary,
            condition_text=summary,
            condition_code=condition_code,
            weather_code=condition_code,
            current_temp=_pick_first(
                data.get("temperature"),
                data.get("current_temp"),
                data.get("temp"),
                now_data.get("temperature") if isinstance(now_data, dict) else None,
                now_data.get("current_temp") if isinstance(now_data, dict) else None,
                now_data.get("temp") if isinstance(now_data, dict) else None,
            ),
            high_temp=data.get("temp_max") or data.get("high_temp") or first_forecast.get("temp_max"),
            low_temp=data.get("temp_min") or data.get("low_temp") or first_forecast.get("temp_min"),
            feels_like=_pick_first(
                data.get("feels_like"),
                data.get("feelslike"),
                data.get("apparent_temperature"),
                now_data.get("feels_like") if isinstance(now_data, dict) else None,
                now_data.get("feelslike") if isinstance(now_data, dict) else None,
                now_data.get("apparent_temperature") if isinstance(now_data, dict) else None,
            ),
            humidity=_pick_first(
                data.get("humidity"),
                now_data.get("humidity") if isinstance(now_data, dict) else None,
            ),
            wind=" / ".join(wind_parts),
            wind_direction=wind_direction,
            wind_scale=wind_scale,
            wind_speed=wind_speed,
            precipitation=precipitation,
            forecast=forecast,
            hourly=hourly,
            precipitation_probability=precipitation_probability,
            pressure=_pick_first(
                data.get("pressure"),
                data.get("press"),
                now_data.get("pressure") if isinstance(now_data, dict) else None,
                now_data.get("press") if isinstance(now_data, dict) else None,
            ),
            visibility=_pick_first(
                data.get("visibility"),
                data.get("vis"),
                now_data.get("visibility") if isinstance(now_data, dict) else None,
                now_data.get("vis") if isinstance(now_data, dict) else None,
                first_hourly.get("visibility") if isinstance(first_hourly, dict) else None,
            ),
            aqi=_pick_first(
                air_quality.get("aqi") if isinstance(air_quality, dict) else None,
                data.get("aqi"),
                now_data.get("aqi") if isinstance(now_data, dict) else None,
            ),
            alerts=alerts,
            warning_texts=warning_texts,
            now=now_data if isinstance(now_data, dict) else None,
            raw_payload=data if isinstance(data, dict) else None,
            life_indices=life_indices,
            captured_at=captured_at,
            retrieved_at=captured_at,
            source="remote",
        )


def _first_dict(*candidates: Any) -> dict[str, Any] | None:
    for candidate in candidates:
        if isinstance(candidate, dict):
            return candidate
    return None


def _pick_first(*values: Any) -> Any:
    for value in values:
        if value not in (None, ""):
            return value
    return None


def _extract_alerts(data: dict[str, Any]) -> list[dict[str, Any]] | None:
    raw_alerts = _pick_first(
        data.get("alerts"),
        data.get("alert"),
        data.get("warnings"),
        data.get("warning"),
    )
    if raw_alerts is None:
        return None
    if isinstance(raw_alerts, dict):
        return [raw_alerts]
    if isinstance(raw_alerts, list):
        return [item for item in raw_alerts if isinstance(item, dict)] or None
    return None


def _warning_texts(alerts: list[dict[str, Any]] | None) -> list[str] | None:
    if not alerts:
        return None
    texts: list[str] = []
    for alert in alerts:
        text = _pick_first(
            alert.get("title"),
            alert.get("name"),
            alert.get("warning"),
            alert.get("text"),
            alert.get("content"),
            alert.get("description"),
        )
        if text in (None, ""):
            continue
        rendered = str(text).strip()
        if rendered:
            texts.append(rendered)
    return texts or None


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
