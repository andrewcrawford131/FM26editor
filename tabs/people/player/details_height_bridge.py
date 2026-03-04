# -*- coding: utf-8 -*-
from __future__ import annotations

from tkinter import messagebox


class DetailsHeightBridgeMixin:
    """Build final Height CLI args from Details Height (mode2) and override legacy blocks."""

    def _apply_details_height_override(self, prefix: str, extra: list[str]) -> None:
        # Read mode var (support both *_mode2 and *_mode)
        def _get_mode() -> str:
            for attr in (f"{prefix}_details_height_mode2", f"{prefix}_details_height_mode"):
                mv = getattr(self, attr, None)
                if mv is None:
                    continue
                try:
                    return str(mv.get() or "").strip().lower()
                except Exception:
                    continue
            return ""

        mode = _get_mode()
        if mode not in ("none", "fixed", "range"):
            # If details mode isn't set, do nothing (caller removed legacy height, so this would mean no height args)
            # We default to "range" using details vars if available, else silently do nothing.
            mode = "range"

        # Remove any existing height args first (prevents duplicates / wrong precedence)
        cleaned: list[str] = []
        i = 0
        while i < len(extra):
            a = str(extra[i])
            if a in ("--height", "--height_min", "--height_max"):
                i += 2 if (i + 1) < len(extra) else 1
                continue
            if a == "--omit-field" and (i + 1) < len(extra) and str(extra[i + 1]) == "height":
                i += 2
                continue
            cleaned.append(extra[i])
            i += 1
        extra[:] = cleaned

        def _to_int_cm(val: str, label: str) -> int:
            s = (val or "").strip()
            if not s:
                raise ValueError(f"{label} is blank")
            try:
                return int(float(s))
            except Exception:
                raise ValueError(f"{label} must be a number (cm)")

        if mode == "none":
            extra.extend(["--omit-field", "height"])
            return

        if mode == "fixed":
            try:
                v = getattr(self, f"{prefix}_details_height_fixed").get()
            except Exception:
                v = ""
            try:
                cm = _to_int_cm(v, "Fixed height")
            except Exception as e:
                messagebox.showerror("Height", str(e))
                raise
            extra.extend(["--height", str(cm)])
            return

        # range
        try:
            mn = getattr(self, f"{prefix}_details_height_min").get()
        except Exception:
            mn = ""
        try:
            mx = getattr(self, f"{prefix}_details_height_max").get()
        except Exception:
            mx = ""

        try:
            cm_min = _to_int_cm(mn, "Height min")
            cm_max = _to_int_cm(mx, "Height max")
            if cm_min > cm_max:
                raise ValueError(f"Height min cannot be greater than max ({cm_min} > {cm_max})")
        except Exception as e:
            messagebox.showerror("Height", str(e))
            raise

        extra.extend(["--height_min", str(cm_min), "--height_max", str(cm_max)])
