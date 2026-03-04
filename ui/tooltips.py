# -*- coding: utf-8 -*-

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

# [PATCH HOVER HELP STATUSBAR v2]
def _bind_help(widget, text: str):
    # Bind <Enter>/<Leave> to update App.status_var (status bar).
    try:
        top = widget.winfo_toplevel()
        if not hasattr(top, "status_var"):
            return

        def _set(_evt=None, t=text):
            try:
                top.status_var.set((t or "").strip())
            except Exception:
                pass

        def _clear(_evt=None):
            try:
                top.status_var.set("")
            except Exception:
                pass

        widget.bind("<Enter>", _set, add=True)
        widget.bind("<Leave>", _clear, add=True)
        widget.bind("<ButtonPress>", _clear, add=True)
    except Exception:
        pass


# [PATCH TOOLTIP HELPER v2 FIX v3]
class _ToolTip:
    """Robust hover tooltip for Tk/ttk widgets (no deps)."""

    def __init__(self, widget, text: str, delay_ms: int = 250, wraplength: int = 520):
        self.widget = widget
        self.text = text or ""
        self.delay_ms = int(delay_ms)
        self.wraplength = int(wraplength)
        self._after_id = None
        self._tw = None
        self._watch_id = None
        self._last_xy = None

        widget.bind("<Enter>", self._on_enter, add=True)
        widget.bind("<Leave>", self._on_leave, add=True)
        widget.bind("<Motion>", self._on_motion, add=True)
        widget.bind("<ButtonPress>", self._on_leave, add=True)

    def _on_enter(self, _evt=None):
        self._schedule()

    def _on_motion(self, _evt=None):
        try:
            self._last_xy = (self.widget.winfo_pointerx(), self.widget.winfo_pointery())
        except Exception:
            self._last_xy = None
        if self._tw is not None:
            try:
                self._position()
            except Exception:
                pass

    def _on_leave(self, _evt=None):
        self._unschedule()
        self._hide()

    def _schedule(self):
        self._unschedule()
        if not self.text:
            return
        try:
            self._after_id = self.widget.after(self.delay_ms, self._show)
        except Exception:
            self._after_id = None

    def _unschedule(self):
        if self._after_id is not None:
            try:
                self.widget.after_cancel(self._after_id)
            except Exception:
                pass
            self._after_id = None

    def _is_pointer_over_widget(self) -> bool:
        try:
            px = self.widget.winfo_pointerx()
            py = self.widget.winfo_pointery()
            w = self.widget.winfo_containing(px, py)
            if w is None:
                return False
            cur = w
            while cur is not None:
                if cur == self.widget:
                    return True
                parent_name = cur.winfo_parent()
                if not parent_name:
                    break
                try:
                    cur = cur.nametowidget(parent_name)
                except Exception:
                    break
        except Exception:
            return False
        return False

    def _position(self):
        if self._tw is None:
            return
        try:
            px, py = self._last_xy if self._last_xy else (self.widget.winfo_pointerx(), self.widget.winfo_pointery())
        except Exception:
            px, py = (self.widget.winfo_rootx(), self.widget.winfo_rooty())
        x = int(px) + 24
        y = int(py) + 28
        try:
            self._tw.wm_geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _show(self):
        if self._tw is not None or not self.text:
            return
        try:
            tw = tk.Toplevel(self.widget)
        except Exception:
            return
        self._tw = tw
        try:
            tw.wm_overrideredirect(True)
        except Exception:
            pass

        self._position()

        try:
            tw.attributes("-topmost", True)
        except Exception:
            pass
        try:
            tw.lift()
        except Exception:
            pass

        try:
            frm = tk.Frame(tw, borderwidth=1, relief="solid", background="#ffffe0")
            frm.pack(fill="both", expand=True)
            lbl = tk.Label(frm, text=self.text, justify="left", wraplength=self.wraplength, background="#ffffe0")
            lbl.pack(padx=8, pady=6)
        except Exception:
            try:
                frm = tk.Frame(tw, borderwidth=1, relief="solid")
                frm.pack(fill="both", expand=True)
                lbl = tk.Label(frm, text=self.text, justify="left", wraplength=self.wraplength)
                lbl.pack(padx=8, pady=6)
            except Exception:
                pass

        self._watch()

    def _watch(self):
        if self._tw is None:
            return
        try:
            if not self._is_pointer_over_widget():
                self._hide()
                return
        except Exception:
            pass

        try:
            self._position()
        except Exception:
            pass

        try:
            self._watch_id = self.widget.after(120, self._watch)
        except Exception:
            self._watch_id = None

    def _hide(self):
        if self._watch_id is not None:
            try:
                self.widget.after_cancel(self._watch_id)
            except Exception:
                pass
            self._watch_id = None

        if self._tw is not None:
            try:
                self._tw.destroy()
            except Exception:
                pass
            self._tw = None


def _attach_tooltip(widget, text: str):
    # Attach tooltip (if pop-up tooltips are working) AND update status bar (always works).
    try:
        _tt = _ToolTip(widget, text=text)
        setattr(widget, "_fm26_tooltip", _tt)
    except Exception:
        pass

    # Status bar hover help
    try:
        top = widget.winfo_toplevel()
        if hasattr(top, "status_var"):
            def _set(_evt=None, t=text):
                try:
                    top.status_var.set(t or "")
                except Exception:
                    pass

            def _clear(_evt=None):
                try:
                    top.status_var.set("")
                except Exception:
                    pass

            widget.bind("<Enter>", _set, add=True)
            widget.bind("<Leave>", _clear, add=True)
            widget.bind("<ButtonPress>", _clear, add=True)
    except Exception:
        pass

# [PATCH HOVERHELP AUTOBIND v1]
def _hoverhelp_autobind(app):
    """Auto-bind status-bar hover help for key widgets by matching Tk variable names.

    This avoids fragile regex edits of .grid() lines; it walks the widget tree after UI build
    and binds <Enter>/<Leave> to update the bottom status bar.
    """
    try:
        # We rely on the status bar existing on the toplevel.
        if not hasattr(app, "status_var"):
            return
    except Exception:
        return

    help_by_var: dict[str, str] = {}

    def _add(var_obj, text: str):
        if var_obj is None:
            return
        try:
            key = str(var_obj)
        except Exception:
            return
        if not key:
            return
        help_by_var[key] = (text or "").strip()

    # --- Batch: position distributions (RANDOM positions) ---
    primary_common = (
        "Used when 'Random positions' is enabled.\n"
        "These four percentages must total 100 across GK/DEF/MID/ST.\n\n"
        "This controls which *group* the primary position comes from (then the generator picks an exact position inside that group)."
    )
    try:
        _add(getattr(app, "batch_dist_gk", None), "GK %\n\n" + primary_common)
        _add(getattr(app, "batch_dist_def", None), "DEF %\n\n" + primary_common)
        _add(getattr(app, "batch_dist_mid", None), "MID %\n\n" + primary_common)
        _add(getattr(app, "batch_dist_st", None), "ST %\n\n" + primary_common)
    except Exception:
        pass

    n20_common = (
        "Outfield positions rated 20: chance (%) when primary is outfield.\n"
        "These nine values must total 100.\n\n"
        "1..7 = exact number of outfield positions at 20.\n"
        "8–12 = bucket (generator chooses 8..12 randomly when picked).\n"
        "13 = all outfield positions at 20 (everything except GK)."
    )
    try:
        _add(getattr(app, "batch_n20_1", None), "N20(1)\n\n" + n20_common)
        _add(getattr(app, "batch_n20_2", None), "N20(2)\n\n" + n20_common)
        _add(getattr(app, "batch_n20_3", None), "N20(3)\n\n" + n20_common)
        _add(getattr(app, "batch_n20_4", None), "N20(4)\n\n" + n20_common)
        _add(getattr(app, "batch_n20_5", None), "N20(5)\n\n" + n20_common)
        _add(getattr(app, "batch_n20_6", None), "N20(6)\n\n" + n20_common)
        _add(getattr(app, "batch_n20_7", None), "N20(7)\n\n" + n20_common)
        _add(getattr(app, "batch_n20_8_12", None), "N20(8–12)\n\n" + n20_common)
        _add(getattr(app, "batch_n20_13", None), "N20(13)\n\n" + n20_common)
    except Exception:
        pass

    dev_common = (
        "Development positions (2–19).\n\n"
        "Only applies when the player ends up multi-position (typically 2..12 outfield positions at 20).\n"
        "Chance is a percent (0..100). The generator also accepts 0..1, but the GUI uses percent."
    )
    dev_mode_common = (
        "Dev value mode:\n"
        "- random: pick a value 2..19\n"
        "- fixed: use Fixed\n"
        "- range: pick a random value between Min and Max (clamped to 2..19)"
    )
    try:
        # Checkbuttons use 'variable'
        _add(getattr(app, "batch_dev_enable", None), "Enable dev positions\n\n" + dev_common)
        _add(getattr(app, "single_dev_enable", None), "Enable dev positions\n\n" + dev_common)
    except Exception:
        pass
    try:
        _add(getattr(app, "batch_auto_dev_chance", None), "Auto dev chance (%)\n\n" + dev_common)
        _add(getattr(app, "single_auto_dev_chance", None), "Auto dev chance (%)\n\n" + dev_common)
    except Exception:
        pass
    try:
        _add(getattr(app, "batch_dev_mode", None), "Dev mode\n\n" + dev_mode_common)
        _add(getattr(app, "single_dev_mode", None), "Dev mode\n\n" + dev_mode_common)
        _add(getattr(app, "batch_dev_fixed", None), "Dev fixed\n\nUsed when Mode=fixed. Value 2..19.")
        _add(getattr(app, "single_dev_fixed", None), "Dev fixed\n\nUsed when Mode=fixed. Value 2..19.")
        _add(getattr(app, "batch_dev_min", None), "Dev min\n\nUsed when Mode=range. Minimum value 2..19.")
        _add(getattr(app, "single_dev_min", None), "Dev min\n\nUsed when Mode=range. Minimum value 2..19.")
        _add(getattr(app, "batch_dev_max", None), "Dev max\n\nUsed when Mode=range. Maximum value 2..19.")
        _add(getattr(app, "single_dev_max", None), "Dev max\n\nUsed when Mode=range. Maximum value 2..19.")
    except Exception:
        pass

    def _walk(w):
        try:
            kids = list(w.winfo_children())
        except Exception:
            kids = []
        for ch in kids:
            yield from _walk(ch)
        yield w

    def _try_bind(widget):
        # Entries/comboboxes use 'textvariable'; checkbuttons use 'variable'
        for opt in ("textvariable", "variable"):
            try:
                key = str(widget.cget(opt))
            except Exception:
                key = ""
            if key and key in help_by_var:
                _bind_help(widget, help_by_var[key])

    try:
        for w in _walk(app):
            _try_bind(w)
    except Exception:
        pass

