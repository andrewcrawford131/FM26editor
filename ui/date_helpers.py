# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as _dt
import tkinter as tk
from tkinter import ttk
from ui.date_picker import DatePickerPopup, DateInput

class DateHelpersMixin:
    def _parse_date_yyyy_mm_dd(self, s: str) -> _dt.date:
        """Parse YYYY-MM-DD (ISO) dates used by Contract tab fields."""
        s = (s or "").strip()
        if not s:
            raise ValueError("blank date")
        try:
            return _dt.date.fromisoformat(s)
        except Exception:
            # Fallback (should rarely be needed)
            return _dt.datetime.strptime(s, "%Y-%m-%d").date()
    def _make_date_input(self, parent, var: tk.StringVar) -> ttk.Frame:
        """
        Calendar-like date input (YYYY-MM-DD).
        Always stdlib only: Entry + calendar popup button.
        """
        return DateInput(parent, var)
    def _open_calendar(self, var: tk.StringVar) -> None:
        """Open stdlib date picker popup and write YYYY-MM-DD into the given StringVar."""
        try:
            DatePickerPopup(self, var)
        except Exception:
            pass

    # ---------------- Height + Feet section (shared) ----------------
