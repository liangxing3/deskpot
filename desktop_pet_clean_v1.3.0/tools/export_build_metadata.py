from __future__ import annotations

import json
import runpy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_METADATA_PATH = PROJECT_ROOT / "app" / "app_metadata.py"


def load_build_metadata() -> dict[str, str]:
    payload = runpy.run_path(str(APP_METADATA_PATH))
    internal_name = str(payload["APP_INTERNAL_NAME"])
    return {
        "display_name": str(payload["APP_DISPLAY_NAME"]),
        "internal_name": internal_name,
        "exe_name": str(payload.get("APP_EXE_NAME") or f"{internal_name}.exe"),
        "install_dir_name": str(payload.get("APP_INSTALL_DIR_NAME") or internal_name),
        "setup_basename": str(payload.get("APP_SETUP_BASENAME") or f"{internal_name}-Setup"),
        "version": str(payload["APP_VERSION"]),
        "publisher": str(payload.get("APP_PUBLISHER") or ""),
        "copyright": str(payload.get("APP_COPYRIGHT") or ""),
        "repository_url": str(payload.get("APP_REPOSITORY_URL") or ""),
        "releases_url": str(payload.get("APP_RELEASES_URL") or ""),
    }


def main() -> int:
    print(json.dumps(load_build_metadata(), ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
