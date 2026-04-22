from __future__ import annotations

from dataclasses import dataclass
import logging
import re

import requests

from app.app_metadata import (
    APP_INTERNAL_NAME,
    APP_LATEST_RELEASE_API_URL,
    APP_RELEASES_URL,
    APP_TAGS_API_URL,
    APP_VERSION,
)

_VERSION_RE = re.compile(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?(?:\.(\d+))?")


@dataclass(slots=True)
class UpdateCheckResult:
    current_version: str
    latest_version: str
    update_available: bool
    release_page_url: str
    download_url: str
    summary: str
    published_at: str | None = None
    source: str = "release"


class UpdateService:
    def __init__(self, logger: logging.Logger) -> None:
        self.logger = logger

    def check_for_updates(self) -> UpdateCheckResult:
        release_payload = self._fetch_latest_release()
        if release_payload is not None:
            return self._build_release_result(release_payload)
        tag_payload = self._fetch_latest_tag()
        if tag_payload is not None:
            return self._build_tag_result(tag_payload)
        return self._build_unpublished_result()

    def _fetch_latest_release(self) -> dict | None:
        response = requests.get(
            APP_LATEST_RELEASE_API_URL,
            headers=self._headers(),
            timeout=6.0,
        )
        if response.status_code == 404:
            self.logger.info("GitHub latest release endpoint returned 404; falling back to tags.")
            return None
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else None

    def _fetch_latest_tag(self) -> dict | None:
        response = requests.get(
            APP_TAGS_API_URL,
            headers=self._headers(),
            timeout=6.0,
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list) or not payload:
            self.logger.info("GitHub tags endpoint returned no tags; treating repository as unpublished.")
            return None
        latest = payload[0]
        if not isinstance(latest, dict):
            self.logger.warning("GitHub tags endpoint returned an unexpected payload item: %r", latest)
            return None
        return latest

    def _build_release_result(self, payload: dict) -> UpdateCheckResult:
        latest_version = _coerce_version_text(payload.get("tag_name") or payload.get("name"))
        if not latest_version:
            raise RuntimeError("发布页缺少版本号。")
        release_page_url = str(payload.get("html_url") or APP_RELEASES_URL)
        assets = payload.get("assets") if isinstance(payload.get("assets"), list) else []
        first_asset = assets[0] if assets and isinstance(assets[0], dict) else {}
        download_url = str(first_asset.get("browser_download_url") or release_page_url)
        return UpdateCheckResult(
            current_version=APP_VERSION,
            latest_version=latest_version,
            update_available=_is_remote_newer(latest_version, APP_VERSION),
            release_page_url=release_page_url,
            download_url=download_url,
            summary=_release_summary(payload),
            published_at=_coerce_optional_text(payload.get("published_at")),
            source="release",
        )

    def _build_tag_result(self, payload: dict) -> UpdateCheckResult:
        latest_version = _coerce_version_text(payload.get("name"))
        if not latest_version:
            self.logger.info("GitHub tag payload had no usable version; treating repository as unpublished.")
            return self._build_unpublished_result()
        return UpdateCheckResult(
            current_version=APP_VERSION,
            latest_version=latest_version,
            update_available=_is_remote_newer(latest_version, APP_VERSION),
            release_page_url=APP_RELEASES_URL,
            download_url=APP_RELEASES_URL,
            summary="已从 Git 标签获取到最新版本信息。",
            source="tag",
        )

    def _build_unpublished_result(self) -> UpdateCheckResult:
        return UpdateCheckResult(
            current_version=APP_VERSION,
            latest_version=APP_VERSION,
            update_available=False,
            release_page_url=APP_RELEASES_URL,
            download_url=APP_RELEASES_URL,
            summary="当前仓库还没有发布正式版本，暂时无法提供远端更新比较。",
            source="unpublished",
        )

    @staticmethod
    def _headers() -> dict[str, str]:
        return {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{APP_INTERNAL_NAME}/{APP_VERSION}",
        }


def _coerce_version_text(value) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    match = _VERSION_RE.search(text)
    return match.group(0) if match else text.lstrip("vV")


def _coerce_optional_text(value) -> str | None:
    text = str(value).strip() if value is not None else ""
    return text or None


def _version_tuple(value: str) -> tuple[int, ...]:
    match = _VERSION_RE.search(str(value))
    if match is None:
        return ()
    parts = [int(part) if part is not None else 0 for part in match.groups()]
    while parts and parts[-1] == 0:
        parts.pop()
    return tuple(parts or [0])


def _is_remote_newer(remote: str, current: str) -> bool:
    remote_parts = _version_tuple(remote)
    current_parts = _version_tuple(current)
    width = max(len(remote_parts), len(current_parts), 3)
    remote_parts = remote_parts + (0,) * (width - len(remote_parts))
    current_parts = current_parts + (0,) * (width - len(current_parts))
    return remote_parts > current_parts


def _release_summary(payload: dict) -> str:
    candidates = [
        _coerce_optional_text(payload.get("name")),
        _coerce_optional_text(payload.get("body")),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        compact = " ".join(line.strip() for line in candidate.splitlines() if line.strip())
        if compact:
            return compact[:160] + ("…" if len(compact) > 160 else "")
    return "GitHub 发布页上有可用的版本说明。"
