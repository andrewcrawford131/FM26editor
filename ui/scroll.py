# -*- coding: utf-8 -*-

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
import sys


class ScrollMixin:
    def _make_scrollable(self, parent: ttk.Frame) -> ttk.Frame:
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill="both", expand=True)

        canvas = tk.Canvas(wrapper, highlightthickness=0)
        vsb = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = ttk.Frame(canvas)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_config(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_config(event):
            canvas.itemconfig(win, width=event.width)

        inner.bind("<Configure>", _on_inner_config)
        canvas.bind("<Configure>", _on_canvas_config)

        # Mouse wheel support (Windows/macOS/Linux) – works while cursor is over any child widget
        def _is_descendant_of(widget, ancestor) -> bool:
            try:
                w = widget
                while w is not None:
                    if w == ancestor:
                        return True
                    parent_name = w.winfo_parent()
                    if not parent_name:
                        break
                    w = w.nametowidget(parent_name)
            except Exception:
                return False
            return False

        def _pointer_over_this_scroll_area() -> bool:
            try:
                px = self.winfo_pointerx()
                py = self.winfo_pointery()
                w = self.winfo_containing(px, py)
                return _is_descendant_of(w, wrapper)
            except Exception:
                return False

        def _scroll_units(units: int):
            try:
                if not _pointer_over_this_scroll_area():
                    return
                if units:
                    canvas.yview_scroll(units, "units")
            except Exception:
                pass

        def _on_mousewheel(event):
            try:
                if not _pointer_over_this_scroll_area():
                    return
                # macOS often reports small deltas; Windows is usually +/-120 multiples
                if sys.platform.startswith("darwin"):
                    delta = int(event.delta)
                    if delta != 0:
                        canvas.yview_scroll(-delta, "units")
                else:
                    delta = int(event.delta)
                    if delta == 0:
                        return
                    steps = int(delta / 120)
                    if steps == 0:
                        steps = 1 if delta > 0 else -1
                    canvas.yview_scroll(-steps, "units")
            except Exception:
                pass

        # Bind globally once per scroll area; handler self-filters by mouse position.
        # This avoids <Leave> unbinding when moving between child widgets inside the form.
        self.bind_all("<MouseWheel>", _on_mousewheel, add="+")
        self.bind_all("<Button-4>", lambda e: _scroll_units(-3), add="+")  # Linux up
        self.bind_all("<Button-5>", lambda e: _scroll_units(3), add="+")   # Linux down

        return inner

    # ---------------- Date input (no pip) ----------------

