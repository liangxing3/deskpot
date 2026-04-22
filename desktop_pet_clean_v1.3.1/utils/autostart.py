from __future__ import annotations

import sys
from pathlib import Path

import developer_config

try:
    import winreg
except ImportError:  # pragma: no cover - non-Windows safeguard.
    winreg = None

RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def _quote_windows(value: Path) -> str:
    text = str(value)
    return f'"{text}"' if " " in text else text


def _build_source_command(main_script: Path) -> str:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    python_cmd = pythonw if pythonw.exists() else Path(sys.executable)
    return f"{_quote_windows(python_cmd)} {_quote_windows(main_script)}"


def resolve_autostart_command(main_script: Path) -> str:
    if getattr(sys, "frozen", False):
        return _quote_windows(Path(sys.executable).resolve())
    return _build_source_command(main_script)


def is_autostart_enabled() -> bool:
    if winreg is None:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, developer_config.APP_NAME)
            return True
    except (FileNotFoundError, OSError):
        return False


def set_autostart(command: str) -> None:
    if winreg is None:
        return
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        winreg.SetValueEx(key, developer_config.APP_NAME, 0, winreg.REG_SZ, command)


def disable_autostart() -> None:
    if winreg is None:
        return
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, developer_config.APP_NAME)
    except (FileNotFoundError, OSError):
        return
