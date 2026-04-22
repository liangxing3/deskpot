from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    import developer_config

    APP_NAME = getattr(developer_config, "APP_NAME", "DesktopPetAssistantV1")
except Exception:
    APP_NAME = "DesktopPetAssistantV1"


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def runtime_root() -> Path:
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        return Path(bundle_root).resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return project_root()


def resource_path(relative_path: str) -> Path:
    return runtime_root() / relative_path


def assets_dir() -> Path:
    return resource_path("assets")


def app_data_dir() -> Path:
    appdata = os.getenv("APPDATA")
    candidates = []
    if appdata:
        candidates.append(Path(appdata) / APP_NAME)
    candidates.append(Path.home() / "AppData" / "Roaming" / APP_NAME)
    candidates.append(project_root() / ".appdata" / APP_NAME)

    for target in candidates:
        try:
            target.mkdir(parents=True, exist_ok=True)
            probe = target / "write_test.tmp"
            probe.write_text("ok", encoding="utf-8")
            return target
        except OSError:
            continue
    raise PermissionError("No writable application data directory is available.")


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


def default_gif_path() -> Path | None:
    candidates = [
        resource_path("assets/GIF/normal.gif"),
        resource_path("assets/GIF/normal2.gif"),
        resource_path("assets/GIF/appear.gif"),
        resource_path("assets/GIF/working.gif"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    gif_dir = assets_dir() / "GIF"
    if gif_dir.exists():
        gifs = sorted(gif_dir.glob("*.gif"))
        if gifs:
            return gifs[0]

    return None
