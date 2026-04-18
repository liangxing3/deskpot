from __future__ import annotations

import sys
from pathlib import Path


def _inject_local_dependencies() -> None:
    dependency_root = Path(__file__).resolve().parent / "_pydeps"
    if dependency_root.exists():
        dependency_path = str(dependency_root)
        if dependency_path not in sys.path:
            sys.path.insert(0, dependency_path)


_inject_local_dependencies()
