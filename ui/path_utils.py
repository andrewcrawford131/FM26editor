# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

def ensure_parent_dir(file_path: str) -> None:
    p = Path(file_path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)
