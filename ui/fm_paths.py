# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sys
from pathlib import Path


def detect_fm26_editor_data_dir() -> Path:
    """
    Auto-detect FM26 "editor data" directory.
    We try common locations per platform; if none exist, we create the first candidate.
    """
    home = Path.home()
    candidates: list[Path] = []

    if sys.platform.startswith("win"):
        onedrive = os.environ.get("OneDrive")
        if onedrive:
            candidates.append(Path(onedrive) / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "OneDrive" / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")

    elif sys.platform == "darwin":
        candidates.append(home / "Library" / "Application Support" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")

    else:
        candidates.append(home / ".local" / "share" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")

    for c in candidates:
        if c.exists():
            return c

    # If nothing exists yet, create first candidate
    try:
        candidates[0].mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return candidates[0]
