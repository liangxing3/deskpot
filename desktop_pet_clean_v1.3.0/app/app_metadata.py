from __future__ import annotations

import sys

APP_DISPLAY_NAME = "桌宠助手"
APP_INTERNAL_NAME = "DesktopPetAssistantV1"
APP_EXE_NAME = f"{APP_INTERNAL_NAME}.exe"
APP_INSTALL_DIR_NAME = APP_INTERNAL_NAME
APP_SETUP_BASENAME = f"{APP_INTERNAL_NAME}-Setup"
APP_VERSION = "1.3.0"
APP_PUBLISHER = "liangxing3"
APP_COPYRIGHT = "Copyright (c) 2026 liangxing3"
APP_REPOSITORY_URL = "https://github.com/liangxing3/deskpot"
APP_RELEASES_URL = f"{APP_REPOSITORY_URL}/releases"
APP_LATEST_RELEASE_API_URL = "https://api.github.com/repos/liangxing3/deskpot/releases/latest"
APP_TAGS_API_URL = "https://api.github.com/repos/liangxing3/deskpot/tags?per_page=1"


def display_version(version: str = APP_VERSION) -> str:
    text = str(version).strip()
    if not text:
        return "v0.0.0"
    return text if text.lower().startswith("v") else f"v{text}"


def runtime_mode_label() -> str:
    return "已打包运行" if getattr(sys, "frozen", False) else "源码运行"


def tray_tooltip() -> str:
    return f"{APP_DISPLAY_NAME} {display_version()}"
