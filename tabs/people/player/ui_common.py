# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class PlayerUiCommonMixin:
    def _add_height_feet_section(
        self,
        parent: ttk.Frame,
        *,
        row: int,
        height_mode_var: tk.StringVar,
        height_min_var: tk.StringVar,
        height_max_var: tk.StringVar,
        height_fixed_var: tk.StringVar,
        feet_mode_var: tk.StringVar,
        feet_override_var: tk.BooleanVar,
        left_foot_var: tk.StringVar,
        right_foot_var: tk.StringVar,
        show_height: bool = True,
        feet_none_var: tk.BooleanVar | None = None,
    ) -> None:
        hf = ttk.LabelFrame(parent, text=("Height + Feet" if show_height else "Feet"))
        hf.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(8):
            hf.columnconfigure(c, weight=1)

        feet_row0 = 0

        if show_height:
            # Height
            ttk.Radiobutton(hf, text="Random height range", variable=height_mode_var, value="range").grid(row=0, column=0, sticky="w", padx=8, pady=6)
            ttk.Radiobutton(hf, text="Fixed height", variable=height_mode_var, value="fixed").grid(row=0, column=4, sticky="w", padx=8, pady=6)

            ttk.Label(hf, text="Min").grid(row=1, column=0, sticky="w", padx=8, pady=4)
            ttk.Entry(hf, textvariable=height_min_var, width=6).grid(row=1, column=1, sticky="w", padx=8, pady=4)
            ttk.Label(hf, text="Max").grid(row=1, column=2, sticky="w", padx=8, pady=4)
            ttk.Entry(hf, textvariable=height_max_var, width=6).grid(row=1, column=3, sticky="w", padx=8, pady=4)

            ttk.Label(hf, text="Height").grid(row=1, column=4, sticky="w", padx=8, pady=4)
            ttk.Entry(hf, textvariable=height_fixed_var, width=6).grid(row=1, column=5, sticky="w", padx=8, pady=4)
            ttk.Label(hf, text="cm (150–210)", foreground="#444").grid(row=1, column=6, sticky="w", padx=8, pady=4)

            feet_row0 = 2

        # Feet mode
        ttk.Label(hf, text="Feet").grid(row=feet_row0, column=0, sticky="w", padx=8, pady=6)
        feet_combo = ttk.Combobox(hf, textvariable=feet_mode_var, values=["random", "left_only", "left", "right_only", "right", "both"], width=14, state="normal")
        feet_combo.grid(row=feet_row0, column=1, sticky="w", padx=8, pady=6)

        if feet_none_var is not None:
            ttk.Checkbutton(hf, text="Don't set", variable=feet_none_var).grid(row=feet_row0, column=2, sticky="w", padx=8, pady=6)
            _feet_override_col = 3
            _feet_override_span = 2
        else:
            _feet_override_col = 2
            _feet_override_span = 3

        # Feet override
        feet_override_chk = ttk.Checkbutton(hf, text="Override foot ratings (1–20)", variable=feet_override_var)
        feet_override_chk.grid(row=feet_row0, column=_feet_override_col, columnspan=_feet_override_span, sticky="w", padx=8, pady=6)

        ttk.Label(hf, text="Left").grid(row=feet_row0 + 1, column=0, sticky="w", padx=8, pady=4)
        left_spin = ttk.Spinbox(hf, from_=1, to=20, textvariable=left_foot_var, width=6)
        left_spin.grid(row=feet_row0 + 1, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(hf, text="Right").grid(row=feet_row0 + 1, column=2, sticky="w", padx=8, pady=4)
        right_spin = ttk.Spinbox(hf, from_=1, to=20, textvariable=right_foot_var, width=6)
        right_spin.grid(row=feet_row0 + 1, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(hf, text="Rule: at least one foot will be forced to 20", foreground="#444").grid(row=feet_row0 + 1, column=4, columnspan=4, sticky="w", padx=8, pady=4)

        def _as_int(s: str, default: int) -> int:
            try:
                return int(str(s).strip())
            except Exception:
                return default

        def _set_state():
            feet_disabled = bool(feet_none_var.get()) if feet_none_var is not None else False
            try:
                feet_combo.configure(state=("disabled" if feet_disabled else "normal"))
            except Exception:
                pass
            try:
                feet_override_chk.configure(state=("disabled" if feet_disabled else "normal"))
            except Exception:
                pass
            state = ("normal" if (feet_override_var.get() and not feet_disabled) else "disabled")
            try:
                left_spin.configure(state=state)
                right_spin.configure(state=state)
            except Exception:
                pass

        def _enforce_one_20(*_):
            # Only enforce when override is ON and feet are not omitted
            if (feet_none_var is not None and bool(feet_none_var.get())) or (not feet_override_var.get()):
                _set_state()
                return

            mode = (feet_mode_var.get() or "random").strip().lower()
            lf = max(1, min(20, _as_int(left_foot_var.get(), 10)))
            rf = max(1, min(20, _as_int(right_foot_var.get(), 10)))

            # Force rules aligned to generator v6 feet modes
            if mode == "both":
                lf = 20
                rf = 20
            elif mode == "left_only":
                lf = 20
                rf = max(1, min(5, rf))
            elif mode == "left":
                lf = 20
                rf = max(6, min(14, rf))
            elif mode == "right_only":
                rf = 20
                lf = max(1, min(5, lf))
            elif mode == "right":
                rf = 20
                lf = max(6, min(14, lf))
            else:
                # random mode: ensure at least one foot is 20
                if lf < 20 and rf < 20:
                    rf = 20

            left_foot_var.set(str(lf))
            right_foot_var.set(str(rf))
            _set_state()

        feet_override_var.trace_add("write", _enforce_one_20)
        feet_mode_var.trace_add("write", _enforce_one_20)
        left_foot_var.trace_add("write", _enforce_one_20)
        right_foot_var.trace_add("write", _enforce_one_20)
        if feet_none_var is not None:
            try:
                feet_none_var.trace_add("write", _enforce_one_20)
            except Exception:
                pass
        _enforce_one_20()

    # ---------------- Details (Random / Custom) ----------------

    def _hide_widgets_with_text(self, root, text_matches):
        """Hide any widget (and its row/frame) whose displayed text matches one of the supplied titles."""
        try:
            children = list(root.winfo_children())
        except Exception:
            children = []
        for w in children:
            # recurse first so nested containers are handled even if parent text is unavailable
            try:
                self._hide_widgets_with_text(w, text_matches)
            except Exception:
                pass
            try:
                txt = str(w.cget("text") or "").strip().lower()
            except Exception:
                txt = ""
            if txt and txt in text_matches:
                # try hiding the widget itself
                hidden = False
                for fn in ("grid_remove", "pack_forget", "place_forget"):
                    try:
                        getattr(w, fn)()
                        hidden = True
                        break
                    except Exception:
                        pass
                # also try the immediate parent row container (common pattern in this GUI)
                try:
                    parent = w.nametowidget(w.winfo_parent())
                except Exception:
                    parent = None
                if parent is not None:
                    for fn in ("grid_remove", "pack_forget", "place_forget"):
                        try:
                            getattr(parent, fn)()
                            hidden = True
                            break
                        except Exception:
                            pass

    def _hide_labelframes_by_title(self, root, keywords):
        try:
            children = list(root.winfo_children())
        except Exception:
            children = []
        for w in children:
            try:
                cls = w.winfo_class()
            except Exception:
                cls = ""
            title = ""
            if cls in ("TLabelframe", "Labelframe", "TLabelFrame", "LabelFrame"):
                try:
                    title = str(w.cget("text") or "").strip().lower()
                except Exception:
                    title = ""
                if title and any(k in title for k in keywords):
                    try:
                        w.grid_remove()
                    except Exception:
                        try:
                            w.pack_forget()
                        except Exception:
                            pass
            # recurse into containers
            self._hide_labelframes_by_title(w, keywords)

    def _hide_rows_by_label_text(self, root, keywords):
        try:
            children = list(root.winfo_children())
        except Exception:
            children = []
        for w in children:
            try:
                cls = w.winfo_class()
            except Exception:
                cls = ""
            if cls in ("TLabel", "Label"):
                try:
                    t = str(w.cget("text") or "").strip().lower()
                except Exception:
                    t = ""
                if t and any(k in t for k in keywords):
                    try:
                        row = w.grid_info().get("row")
                        parent = w.nametowidget(w.winfo_parent())
                        for sib in parent.winfo_children():
                            try:
                                if sib.grid_info().get("row") == row:
                                    sib.grid_remove()
                            except Exception:
                                pass
                    except Exception:
                        try:
                            w.grid_remove()
                        except Exception:
                            pass
            self._hide_rows_by_label_text(w, keywords)

    def _cleanup_other_tabs_fields(self):
        """Best-effort cleanup to hide duplicated DOB sections/rows from Other tabs."""
        try:
            targets = []
            for name in (
                "player_batch_other_tab", "player_single_other_tab", "batch_other_tab", "single_other_tab",
                "batch_tab", "single_tab", "batch_body", "single_body",
                "nonplayer_batch_contract_tab", "nonplayer_single_contract_tab", "player_nonplayer_batch_contract_tab", "player_nonplayer_single_contract_tab",
            ):
                w = getattr(self, name, None)
                if w is not None:
                    targets.append(w)
            # de-dup widgets by Tcl path if possible
            seen = set()
            uniq = []
            for w in targets:
                try:
                    key = str(w)
                except Exception:
                    key = id(w)
                if key in seen:
                    continue
                seen.add(key)
                uniq.append(w)

            for root in uniq:
                try:
                    # Hide DOB sections/rows duplicated on Other tabs
                    self._hide_labelframes_by_title(root, {"dob", "age / dob"})
                    self._hide_rows_by_label_text(root, {"dob", "date of birth", "fixed dob", "use dob", "age / dob"})
                    self._hide_widgets_with_text(root, {"dob (calendar range or fixed)", "age / dob"})
                    # Hide City/Nation rows on Other tabs (keep Club row)
                    try:
                        rname = str(root).lower()
                    except Exception:
                        rname = ""
                    if "other" in rname:
                        self._hide_rows_by_label_text(root, {"city of birth", "nation"})
                except Exception:
                    pass
        except Exception:
            pass

