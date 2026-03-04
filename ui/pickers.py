# -*- coding: utf-8 -*-
from __future__ import annotations

import fnmatch
import re
import tkinter as tk
from tkinter import ttk


class PickerWidgetsMixin:
    def _install_global_combobox_patches(self) -> None:
        """Global live-search combobox patches (Windows-safe).

        Behaviour:
        - Click in entry area: focus+select (typing works), do NOT auto-open.
        - Typing: filters values; auto-opens dropdown and refreshes it (Unpost->Post).
        - Focus stays in entry while dropdown is open.
        - Arrow click: normal dropdown behaviour.
        """
        if getattr(self, "_global_combobox_patches_installed", False):
            return
        self._global_combobox_patches_installed = True

        def _popdown(w: ttk.Combobox):
            try:
                return w.tk.call("ttk::combobox::PopdownWindow", str(w))
            except Exception:
                return None

        def _is_open(w: ttk.Combobox) -> bool:
            pop = _popdown(w)
            if not pop:
                return False
            try:
                return bool(int(w.tk.call("winfo", "ismapped", pop)))
            except Exception:
                return False

        def _unpost(w: ttk.Combobox) -> None:
            try:
                w.tk.call("ttk::combobox::Unpost", str(w))
            except Exception:
                pass

        def _refocus(w: ttk.Combobox) -> None:
            # Re-assert focus (Windows sometimes steals it to the listbox)
            try:
                w.tk.call("focus", str(w))
            except Exception:
                pass
            try:
                w.focus_set()
            except Exception:
                pass
            try:
                w.icursor("end")
            except Exception:
                pass

        def _post(w: ttk.Combobox) -> None:
            try:
                w.tk.call("ttk::combobox::Post", str(w))
            except Exception:
                return
            # Aggressive re-focus
            try:
                w.after_idle(lambda: _refocus(w))
                w.after(1, lambda: _refocus(w))
                w.after(25, lambda: _refocus(w))
            except Exception:
                _refocus(w)

        def _is_arrow_click(w: ttk.Combobox, event) -> bool:
            try:
                width = int(w.winfo_width())
                x = int(getattr(event, "x", 0))
                return x >= max(0, width - 24)
            except Exception:
                return False

        def _match(val: str, query: str) -> bool:
            s = (val or "").lower()
            q = (query or "").strip().lower()
            if not q:
                return True

            # wildcard support
            if any(ch in q for ch in ("*", "?", "[")):
                try:
                    return fnmatch.fnmatch(s, q)
                except Exception:
                    return q in s

            # token AND-match
            tokens = [t for t in re.split(r"[\s,;]+", q) if t]
            return all(t in s for t in tokens)

        def _ensure_all_values(w: ttk.Combobox) -> None:
            # capture base list; refresh if values changed significantly
            try:
                cur_vals = list(w.cget("values") or [])
            except Exception:
                cur_vals = []
            sig = (len(cur_vals), str(cur_vals[:3]), str(cur_vals[-3:]) if cur_vals else "")
            old_sig = getattr(w, "_all_values_sig", None)
            if not hasattr(w, "_all_values") or old_sig != sig:
                try:
                    w._all_values = cur_vals[:]  # type: ignore[attr-defined]
                    w._all_values_sig = sig      # type: ignore[attr-defined]
                except Exception:
                    pass

        def _apply_filter(w: ttk.Combobox) -> None:
            _ensure_all_values(w)
            try:
                base = list(getattr(w, "_all_values", []) or [])
            except Exception:
                base = []
            if not base:
                return

            try:
                q = (w.get() or "").strip()
            except Exception:
                q = ""

            if not q:
                try:
                    w["values"] = base
                except Exception:
                    pass
                return

            filtered = [v for v in base if _match(str(v), q)]
            try:
                w["values"] = filtered if filtered else base
            except Exception:
                pass

        def _on_click(event):
            w = getattr(event, "widget", None)
            if not isinstance(w, ttk.Combobox):
                return None

            # entry click: allow typing, prevent auto-post
            if not _is_arrow_click(w, event):
                try:
                    w.configure(state="normal")
                except Exception:
                    pass
                try:
                    w.focus_set()
                    w.selection_range(0, "end")
                except Exception:
                    pass
                return "break"
            return None

        def _on_keyrelease(event):
            w = getattr(event, "widget", None)
            if not isinstance(w, ttk.Combobox):
                return None

            ks = str(getattr(event, "keysym", "") or "").lower()
            if ks in ("up", "down", "left", "right", "prior", "next", "home", "end", "escape", "return"):
                return None

            try:
                w.configure(state="normal")
            except Exception:
                pass

            _apply_filter(w)

            # live search: force popdown refresh so the list updates immediately
            try:
                q = (w.get() or "").strip()
            except Exception:
                q = ""

            if q:
                # If open, re-post to refresh visible list; if closed, post.
                try:
                    _unpost(w)
                    _post(w)
                except Exception:
                    pass
            else:
                # empty query: close dropdown
                try:
                    _unpost(w)
                    _refocus(w)
                except Exception:
                    pass

            return None

        try:
            self.bind_class("TCombobox", "<Button-1>", _on_click, add="+")
            self.bind_class("TCombobox", "<KeyRelease>", _on_keyrelease, add="+")
        except Exception:
            pass

    def _combo_state_for_mode(self, mode_var: tk.StringVar, combo: ttk.Combobox) -> None:
        # User preference: always typeable
        try:
            combo.configure(state="normal")
        except Exception:
            pass

    def _make_searchable_picker(self, parent, textvariable, values, width=48):
        """Create a searchable picker combobox.

        Uses the global patches for live filtering and focus behaviour.
        """
        vals = list(dict.fromkeys([v for v in (values or []) if str(v).strip() != ""]))
        cb = ttk.Combobox(parent, textvariable=textvariable, values=vals, width=width, state="normal")
        try:
            cb["exportselection"] = False
        except Exception:
            pass

        # seed base list for global filter
        try:
            cb._all_values = vals[:]       # type: ignore[attr-defined]
            cb._all_values_sig = (len(vals), str(vals[:3]), str(vals[-3:]) if vals else "")  # type: ignore[attr-defined]
        except Exception:
            pass

        # let user open with arrow/Down if they want
        def _show(event=None):
            try:
                cb.tk.call("ttk::combobox::Post", str(cb))
            except Exception:
                pass
            try:
                cb.after_idle(lambda: (cb.focus_set(), cb.icursor("end")))
            except Exception:
                pass
            return "break"

        cb.bind("<Down>", _show, add="+")
        cb.bind("<Alt-Down>", _show, add="+")
        cb.bind("<F4>", _show, add="+")
        return cb
