# -*- mode: python ; coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import runpy

from PyInstaller.utils.hooks import collect_submodules
from PyInstaller.utils.win32.versioninfo import (
    VSVersionInfo,
    FixedFileInfo,
    StringFileInfo,
    StringStruct,
    StringTable,
    VarFileInfo,
    VarStruct,
)

PROJECT_ROOT = Path(SPECPATH)
ASSETS_DIR = PROJECT_ROOT / "assets"
CONFIG_PATH = PROJECT_ROOT / "config.json"
ICON_PATH = ASSETS_DIR / "app_icon.ico"
APP_METADATA = runpy.run_path(str(PROJECT_ROOT / "app" / "app_metadata.py"))
APP_DISPLAY_NAME = str(APP_METADATA["APP_DISPLAY_NAME"])
APP_INTERNAL_NAME = str(APP_METADATA["APP_INTERNAL_NAME"])
APP_EXE_NAME = str(APP_METADATA.get("APP_EXE_NAME") or f"{APP_INTERNAL_NAME}.exe")
APP_VERSION = str(APP_METADATA["APP_VERSION"])
APP_PUBLISHER = str(APP_METADATA.get("APP_PUBLISHER") or "")
APP_COPYRIGHT = str(APP_METADATA.get("APP_COPYRIGHT") or "")


def _version_tuple(version: str) -> tuple[int, int, int, int]:
    parts: list[int] = []
    for raw_part in str(version).split("."):
        try:
            parts.append(int(raw_part))
        except ValueError:
            parts.append(0)
    while len(parts) < 4:
        parts.append(0)
    return tuple(parts[:4])


VERSION_TUPLE = _version_tuple(APP_VERSION)
VERSION_INFO = VSVersionInfo(
    ffi=FixedFileInfo(
        filevers=VERSION_TUPLE,
        prodvers=VERSION_TUPLE,
        mask=0x3F,
        flags=0x0,
        OS=0x40004,
        fileType=0x1,
        subtype=0x0,
        date=(0, 0),
    ),
    kids=[
        StringFileInfo(
            [
                StringTable(
                    "080404B0",
                    [
                        StringStruct("CompanyName", APP_PUBLISHER),
                        StringStruct("FileDescription", APP_DISPLAY_NAME),
                        StringStruct("FileVersion", APP_VERSION),
                        StringStruct("InternalName", APP_INTERNAL_NAME),
                        StringStruct("LegalCopyright", APP_COPYRIGHT),
                        StringStruct("OriginalFilename", APP_EXE_NAME),
                        StringStruct("ProductName", APP_DISPLAY_NAME),
                        StringStruct("ProductVersion", APP_VERSION),
                    ],
                )
            ]
        ),
        VarFileInfo([VarStruct("Translation", [2052, 1200])]),
    ],
)

datas = [
    (str(ASSETS_DIR), "assets"),
    (str(CONFIG_PATH), "."),
]

hiddenimports = ["PySide6.QtSvg"]
for package_name in ("uapi", "uapi_sdk_python"):
    try:
        hiddenimports.extend(collect_submodules(package_name))
    except Exception:
        hiddenimports.append(package_name)

hiddenimports = sorted(set(hiddenimports))


a = Analysis(
    ["main.py"],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_INTERNAL_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(ICON_PATH) if ICON_PATH.exists() else None,
    version=VERSION_INFO,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name=APP_INTERNAL_NAME,
)
