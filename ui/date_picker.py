# -*- coding: utf-8 -*-

from __future__ import annotations

import calendar as _cal
import datetime as _dt

import tkinter as tk
from tkinter import ttk

try:
    from tkinter import messagebox
except Exception:
    messagebox = None

class DatePickerPopup(tk.Toplevel):
    """Calendar popup that writes YYYY-MM-DD into a StringVar (stdlib only).
    Improved UI: month dropdown + year spinbox + prev/next.
    """
    def __init__(self, parent: tk.Widget, var: tk.StringVar):
        super().__init__(parent)
        self.title("Pick a date")
        self.resizable(False, False)
        try:
            self.transient(parent)
            self.grab_set()
        except Exception:
            pass

        self.var = var

        # initial date from var if possible
        today = _dt.date.today()
        y, m, d = today.year, today.month, today.day
        try:
            s = (var.get() or "").strip()
            if len(s) >= 10:
                y = int(s[0:4]); m = int(s[5:7]); d = int(s[8:10])
        except Exception:
            pass

        self._year = int(y)
        self._month = int(m)
        self._selected_day = int(d)

        self._build_ui()
        self._render_days(select_day=self._selected_day)

        # place near mouse cursor if possible
        try:
            self.update_idletasks()
            x = self.winfo_pointerx() - 60
            y = self.winfo_pointery() - 20
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        top = ttk.Frame(self, padding=10)
        top.pack(fill="both", expand=True)

        nav = ttk.Frame(top)
        nav.pack(fill="x")

        ttk.Button(nav, text="◀", width=3, command=self._prev_month).pack(side="left")

        month_names = [(_cal.month_name[i] or str(i)) for i in range(1, 13)]
        self._month_name_to_num = {month_names[i-1]: i for i in range(1, 13)}

        self._month_cb = ttk.Combobox(nav, values=month_names, width=14, state="normal")
        try:
            self._month_cb.set(month_names[self._month - 1])
        except Exception:
            self._month_cb.set(month_names[0])
        self._month_cb.pack(side="left", padx=(8, 6))
        self._month_cb.bind("<<ComboboxSelected>>", lambda _e=None: self._on_month_year_change(), add="+")

        self._year_var = tk.StringVar(value=str(self._year))
        self._year_spin = ttk.Spinbox(nav, from_=1, to=9999, textvariable=self._year_var, width=6, command=self._on_month_year_change)
        self._year_spin.pack(side="left", padx=(0, 8))
        self._year_spin.bind("<Return>", lambda _e=None: self._on_month_year_change(), add="+")
        self._year_spin.bind("<FocusOut>", lambda _e=None: self._on_month_year_change(), add="+")

        ttk.Button(nav, text="▶", width=3, command=self._next_month).pack(side="left")

        self.gridfrm = ttk.Frame(top)
        self.gridfrm.pack(pady=(10, 0))

        for i, wd in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
            ttk.Label(self.gridfrm, text=wd, width=4, anchor="center").grid(row=0, column=i, padx=2, pady=2)

        self._day_btns: list[ttk.Button] = []
        for r in range(1, 7):
            for c in range(7):
                b = ttk.Button(self.gridfrm, text="", width=4)
                b.grid(row=r, column=c, padx=2, pady=2)
                self._day_btns.append(b)

        bottom = ttk.Frame(top)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text="Today", command=self._set_today).pack(side="left")
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right")

    def _on_month_year_change(self):
        try:
            mn = (self._month_cb.get() or "").strip()
            if mn in self._month_name_to_num:
                self._month = int(self._month_name_to_num[mn])
        except Exception:
            pass
        try:
            y = int(str(self._year_var.get() or "").strip())
            y = max(1, min(9999, y))
            self._year = y
        except Exception:
            pass
        self._render_days()

    def _prev_month(self):
        self._month -= 1
        if self._month <= 0:
            self._month = 12
            self._year = max(1, self._year - 1)
        try:
            self._month_cb.set(_cal.month_name[self._month])
            self._year_var.set(str(self._year))
        except Exception:
            pass
        self._render_days()

    def _next_month(self):
        self._month += 1
        if self._month >= 13:
            self._month = 1
            self._year = min(9999, self._year + 1)
        try:
            self._month_cb.set(_cal.month_name[self._month])
            self._year_var.set(str(self._year))
        except Exception:
            pass
        self._render_days()

    def _set_today(self):
        today = _dt.date.today()
        self._year, self._month = today.year, today.month
        try:
            self._month_cb.set(_cal.month_name[self._month])
            self._year_var.set(str(self._year))
        except Exception:
            pass
        self._render_days(select_day=today.day)

    def _render_days(self, select_day: int | None = None):
        try:
            first_weekday, num_days = _cal.monthrange(self._year, self._month)  # Monday=0
        except Exception:
            return

        for b in self._day_btns:
            b.configure(text="", state="disabled", command=lambda: None)

        day = 1
        start_index = first_weekday
        for i in range(start_index, start_index + num_days):
            btn = self._day_btns[i]
            dd = day
            btn.configure(text=str(dd), state="normal", command=lambda dd=dd: self._pick(dd))
            day += 1

        if select_day and 1 <= select_day <= num_days:
            try:
                idx = start_index + (select_day - 1)
                self._day_btns[idx].focus_set()
            except Exception:
                pass

    def _pick(self, day: int):
        try:
            dt = _dt.date(self._year, self._month, int(day))
            self.var.set(dt.strftime("%Y-%m-%d"))
        except Exception:
            pass
        self.destroy()


class DateInput(ttk.Frame):
    """Entry + calendar button (no pip)."""

    def __init__(self, parent: tk.Widget, var: tk.StringVar, width: int = 12):
        super().__init__(parent)
        self.var = var
        self.ent = ttk.Entry(self, textvariable=var, width=width)
        self.ent.pack(side="left")
        self.btn = ttk.Button(self, text="📅", width=3, command=self._open)
        self.btn.pack(side="left", padx=(4, 0))
        # Backward-compatible attribute names used elsewhere in the GUI
        self.entry = self.ent
        self.button = self.btn

    def _open(self):
        DatePickerPopup(self, self.var)
