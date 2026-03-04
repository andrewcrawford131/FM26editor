# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from pathlib import Path
from ui.fm_paths import detect_fm26_editor_data_dir

class PathResolveMixin:
    def _resolve_fmdata_path(self, name: str) -> str:
        try:
            d = getattr(self, "fmdata_dir", self.base_dir / "fmdata")
            d.mkdir(parents=True, exist_ok=True)
            return str(d / name)
        except Exception:
            return str((getattr(self, "base_dir", Path.cwd())) / name)

    # ---------------- File pickers ----------------
    def _resolve_gui_file_candidate(self, p: str, *, script_hint: str = "") -> str:
        raw = (p or "").strip()
        if not raw:
            return raw
        if os.path.exists(raw):
            return raw
        candidates = []
        try:
            if script_hint:
                sd = str(Path(script_hint).resolve().parent)
                candidates.append(str(Path(sd) / raw))
                candidates.append(str(Path(sd) / "fmdata" / raw))
        except Exception:
            pass
        try:
            fm_dir = detect_fm26_editor_data_dir()
            if fm_dir:
                candidates.append(str(Path(fm_dir) / raw))
                candidates.append(str(Path(fm_dir) / "fmdata" / raw))
        except Exception:
            pass
        for c in candidates:
            if c and os.path.exists(c):
                return c
        return raw
