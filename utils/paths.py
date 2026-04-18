from __future__ import annotations

import os
import sys
from pathlib import Path

import developer_config


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


def resource_path(relative_path: str) -> Path:
    return runtime_root() / relative_path


def app_data_dir() -> Path:
    appdata = os.getenv("APPDATA")
    base_dir = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    target = base_dir / developer_config.APP_NAME
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".write_test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return target
    except OSError:
        fallback = runtime_root() / ".appdata" / developer_config.APP_NAME
        fallback.mkdir(parents=True, exist_ok=True)
        return fallback


def logs_dir() -> Path:
    target = app_data_dir() / "logs"
    target.mkdir(parents=True, exist_ok=True)
    return target


def cache_dir() -> Path:
    target = app_data_dir() / "cache"
    target.mkdir(parents=True, exist_ok=True)
    return target


def config_path() -> Path:
    return app_data_dir() / "config.json"


def default_config_template_path() -> Path:
    return resource_path("config.json")


def cache_path() -> Path:
    return cache_dir() / "cache.json"


def manifest_path() -> Path:
    return resource_path("assets/manifest.json")


def runtime_state_path() -> Path:
    return app_data_dir() / "runtime_state.json"


def pet_status_path() -> Path:
    return app_data_dir() / "pet_status.json"
