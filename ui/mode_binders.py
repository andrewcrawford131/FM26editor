# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

class ModeBindersMixin:
    def _bind_mode_enable(self, mode_var, custom_value, widgets, clear_on_random=False):
        """Enable widgets only when mode_var == custom_value.""" 
        def _set_state(*_):
            mode = ""
            try:
                mode = (mode_var.get() or "").strip().lower()
            except Exception:
                mode = ""
            enabled = (mode == str(custom_value).strip().lower())
            state = "normal" if enabled else "disabled"
            for w in widgets:
                try:
                    # ttk widgets usually use 'state', some custom widgets may need state() API.
                    w.configure(state=state)
                except Exception:
                    try:
                        if state == "disabled":
                            w.state(["disabled"])
                        else:
                            w.state(["!disabled"])
                    except Exception:
                        pass
                    continue
                if (not enabled) and clear_on_random:
                    try:
                        tv = str(w.cget("textvariable"))
                        if tv:
                            self.setvar(tv, "")
                    except Exception:
                        pass
        try:
            mode_var.trace_add("write", _set_state)
        except Exception:
            pass
        _set_state()
    def _bind_mode_showhide(self, mode_var, show_value, widgets, clear_vars=None):
        """Show widgets only when mode_var == show_value; otherwise grid_remove().
        Optionally clears StringVars when hidden.""" 
        def _apply(*_):
            try:
                v = (mode_var.get() or "").strip().lower()
            except Exception:
                v = ""
            show = (v == str(show_value).strip().lower())
            if show:
                for w in widgets:
                    try:
                        w.grid()
                    except Exception:
                        try:
                            w.grid_configure()
                        except Exception:
                            pass
            else:
                for w in widgets:
                    try:
                        w.grid_remove()
                    except Exception:
                        pass
                if clear_vars:
                    for sv in clear_vars:
                        try:
                            sv.set("")
                        except Exception:
                            pass
        try:
            mode_var.trace_add("write", lambda *_: _apply())
        except Exception:
            try:
                mode_var.trace("w", lambda *_: _apply())
            except Exception:
                pass
        _apply()
