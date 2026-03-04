# -*- coding: utf-8 -*-
# Auto-generated from fm26_generator_gui_2.py
# Player Details tab extracted into a mixin to reduce main GUI file size.


from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox


class DetailsSubtabMixin:
    def _add_details_section(self, parent, row: int, prefix: str):
        """
        Shared Details UI block for Batch/Single.
        Adds compact DOB controls in Details with:
        Random(age min/max) / DOB range(start/end) / Fixed(date).
        """
        # Backward-compatible vars for older single-tab state
        if prefix == "single":
            if not hasattr(self, "single_age_min"):
                age_default = getattr(self, "single_age", tk.StringVar(value="14")).get()
                self.single_age_min = tk.StringVar(value=age_default)
            if not hasattr(self, "single_age_max"):
                age_default = getattr(self, "single_age", tk.StringVar(value="14")).get()
                self.single_age_max = tk.StringVar(value=age_default)
            if not hasattr(self, "single_dob_fixed"):
                self.single_dob_fixed = getattr(self, "single_dob", tk.StringVar(value="2012-07-01"))
            if not hasattr(self, "single_dob_start"):
                self.single_dob_start = tk.StringVar(value="2010-01-01")
            if not hasattr(self, "single_dob_end"):
                self.single_dob_end = tk.StringVar(value="2012-12-31")

        _ethnicity_labels = globals().get("_ETHNICITY_LABELS", [
            "Unknown", "Northern European", "Mediterranean/Hispanic",
            "North African/Middle Eastern", "African/Caribbean", "Asian",
            "South East Asian", "Pacific Islander", "Native American",
            "Native Australian", "Mixed Race", "East Asian",
        ])
        _skin_tone_labels = globals().get("_SKIN_TONE_LABELS", ["Unknown"] + [f"Skin Tone {i}" for i in range(1, 21)])
        _body_type_labels = globals().get("_BODY_TYPE_LABELS", ["Ectomorph (Slim/Lean)", "Ecto-Mesomorph (Lean/Athletic)", "Mesomorph (Athletic/Muscular)", "Meso-Endomorph (Stocky/Athletic)", "Endomorph (Heavyset)"])
        _nat_info_labels = globals().get("_NATIONALITY_INFO_LABELS", [
            "No info",
            "Born In Nation",
            "Relative Born In Nation",
            "Declared For Nation",
            "Eligible For Nation",
            "Not Eligible For Nation",
            "Has Played For Nation",
            "Gained Citizenship Through Relative",
            "Gained Citizenship But Not Eligible For Nation Yet",
            "Gained Citizenship But Treated As Foreign",
            "Gained Citizenship And Declared For Nation",
            "Gained Citizenship Through Relative But Not Eligible For Nation Yet",
        ])

        detailsf = ttk.LabelFrame(parent, text="Details")
        detailsf.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        detailsf.columnconfigure(2, weight=1)

        rows = [
            ("First Name", "first_name", "entry", None),
            ("Second Name", "second_name", "entry", None),
            ("Common Name", "common_name", "entry", None),
            ("Full Name", "full_name", "entry", None),
            ("Gender", "gender", "combo", ["Male", "Female"]),
            ("Ethnicity", "ethnicity", "combo", _ethnicity_labels),
            ("Hair Colour", "hair_colour", "combo", ["Black", "Blond(e)", "Light Blond(e)", "Brown", "Light Brown", "Grey", "Red"]),
            ("Hair Length", "hair_length", "combo", ["Bald", "Short", "Medium", "Long"]),
            ("Skin Tone", "skin_tone", "combo", _skin_tone_labels),
            ("Body Type", "body_type", "combo", _body_type_labels),
            ("City Of Birth", "city_of_birth", "picker_city", None),
            ("Nation", "nation", "picker_nation", None),
            ("Region Of Birth", "region_of_birth", "disabled", None),
            ("Nationality Info", "nationality_info", "combo", _nat_info_labels),
        ]

        r = 0
        for label, key, kind, options in rows:
            mode_var = getattr(self, f"{prefix}_details_{key}_mode", None)
            value_var = getattr(self, f"{prefix}_details_{key}_value", None)
            if mode_var is None:
                mode_var = tk.StringVar(value="random")
                setattr(self, f"{prefix}_details_{key}_mode", mode_var)
            if value_var is None:
                value_var = tk.StringVar(value="")
                setattr(self, f"{prefix}_details_{key}_value", value_var)

            ttk.Label(detailsf, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            rb_rand = ttk.Radiobutton(detailsf, text="Random", variable=mode_var, value="random")
            rb_custom = ttk.Radiobutton(detailsf, text="Custom", variable=mode_var, value="custom")
            rb_none = ttk.Radiobutton(detailsf, text="Don\'t set", variable=mode_var, value="none")
            rb_rand.grid(row=r, column=1, sticky="w", padx=(6, 2))
            rb_custom.grid(row=r, column=1, sticky="w", padx=(85, 2))
            rb_none.grid(row=r, column=1, sticky="w", padx=(165, 2))

            # [AUTO] First Name random -> Gender random
            if key == "first_name":
                def _sync_gender_from_first_name(*_a, _p=prefix, _mv=mode_var):
                    try:
                        if _mv.get() == "random":
                            _g = getattr(self, f"{_p}_details_gender_mode", None)
                            if _g is not None:
                                _g.set("random")
                    except Exception:
                        pass
                try:
                    mode_var.trace_add("write", _sync_gender_from_first_name)
                except Exception:
                    pass

            if kind == "disabled":
                rb_rand.configure(state="disabled")
                rb_custom.configure(state="disabled")
                rb_none.configure(state="disabled")
                w = ttk.Entry(detailsf, textvariable=value_var, state="disabled")
                w.grid(row=r, column=2, sticky="ew", padx=6, pady=3)
                r += 1
                continue

            if kind == "entry":
                w = ttk.Entry(detailsf, textvariable=value_var)
            elif kind == "combo":
                w = self._make_searchable_picker(detailsf, value_var, list(options or []), width=48)
            elif kind == "picker_city":
                # Prefer labels already built by _reload_master_library (includes DBID fallback)
                city_labels = list(getattr(self, "_city_map", {}).keys())
                if not city_labels:
                    city_rows = list(self._load_master_library_rows(kind="city"))
                    for x in city_rows:
                        nm = (x.get("city_name") or x.get("name") or "").strip()
                        dbid = (x.get("city_dbid") or x.get("dbid") or "").strip()
                        if nm:
                            city_labels.append(f"{nm} (DBID {dbid})" if dbid else nm)
                        elif dbid:
                            city_labels.append(f"City DBID {dbid}")
                w = self._make_searchable_picker(detailsf, value_var, city_labels, width=48)
            elif kind == "picker_nation":
                nation_rows = list(self._load_master_library_rows(kind="nation"))
                nation_labels = []
                for x in nation_rows:
                    nm = (x.get("nation_name") or x.get("name") or "").strip()
                    dbid = str((x.get("nation_dbid") or x.get("dbid") or "") or "").strip()
                    if not nm and dbid:
                        nm = f"Nation DBID {dbid}"
                    if nm:
                        nation_labels.append(f"{nm} (DBID {dbid})" if dbid else nm)
                # De-dup + sort for nicer UX
                nation_labels = sorted(set([s for s in nation_labels if s]), key=lambda s: s.lower())
                w = self._make_searchable_picker(detailsf, value_var, nation_labels, width=48)
                try:
                    w.bind("<<ComboboxSelected>>", lambda e, mv=mode_var: mv.set("custom"))
                except Exception:
                    pass
            else:
                w = ttk.Entry(detailsf, textvariable=value_var)

            w.grid(row=r, column=2, sticky="ew", padx=6, pady=3)
            self._bind_mode_enable(mode_var, "custom", [w], clear_on_random=True)
            r += 1

        # Second Nations block in Details (FM-style multi-row editor/list)
        snf = ttk.LabelFrame(detailsf, text="Second Nations")
        snf.grid(row=r, column=0, columnspan=3, sticky="ew", padx=6, pady=(8, 4))
        snf.columnconfigure(0, weight=1)

        # Second Nations mode (Random / Custom / Don't set)
        sn_mode_attr = f"{prefix}_second_nations_mode"
        sn_mode_var = getattr(self, sn_mode_attr, None)
        if sn_mode_var is None:
            sn_mode_var = tk.StringVar(value="none")
            setattr(self, sn_mode_attr, sn_mode_var)
        modef = ttk.Frame(snf)
        modef.grid(row=0, column=0, sticky="w", padx=6, pady=(6, 2))
        ttk.Label(modef, text="Mode:").grid(row=0, column=0, sticky="w")
        ttk.Radiobutton(modef, text="Random", variable=sn_mode_var, value="random").grid(row=0, column=1, sticky="w", padx=(10, 0))
        ttk.Radiobutton(modef, text="Don't set", variable=sn_mode_var, value="none").grid(row=0, column=2, sticky="w", padx=(10, 0))

        # Shared option lists
        _sn_nation_rows = list(self._load_master_library_rows(kind="nation"))
        _sn_nation_labels = [x.get("nation_name") or x.get("name") or "" for x in _sn_nation_rows]
        _sn_nation_labels = [x for x in _sn_nation_labels if x]

        # Persistent per-prefix state/vars
        sn_items = getattr(self, f"{prefix}_second_nations_items", None)
        if sn_items is None:
            sn_items = []
            setattr(self, f"{prefix}_second_nations_items", sn_items)
        if not hasattr(self, f"{prefix}_second_nations_clipboard"):
            setattr(self, f"{prefix}_second_nations_clipboard", None)

        def _sn_var(name: str, default="", boolvar: bool = False):
            attr = f"{prefix}_second_nations_{name}"
            v = getattr(self, attr, None)
            if v is None:
                v = tk.BooleanVar(value=bool(default)) if boolvar else tk.StringVar(value=str(default))
                setattr(self, attr, v)
            return v

        sn_nation_var = _sn_var("nation", "")
        sn_nat_info_var = _sn_var("nationality_info", _nat_info_labels[0] if _nat_info_labels else "No info")
        sn_declared_var = _sn_var("nation_declared_for", "")
        sn_declared_youth_var = _sn_var("nation_declared_for_youth", "")
        sn_int_ret_var = _sn_var("international_retirement", False, boolvar=True)
        sn_int_ret_date_var = _sn_var("international_retirement_date", "")
        sn_retire_spell_var = _sn_var("retiring_after_spell_current_club", False, boolvar=True)
        sn_comment_var = _sn_var("comment", "")

        btnbar = ttk.Frame(snf)
        btnbar.grid(row=1, column=0, sticky="ew", padx=6, pady=(6, 4))
        for _c in range(12):
            btnbar.columnconfigure(_c, weight=0)
        btnbar.columnconfigure(11, weight=1)

        listwrap = ttk.Frame(snf)
        listwrap.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 6))
        listwrap.columnconfigure(0, weight=1)
        listwrap.rowconfigure(1, weight=1)

        sn_count_var = tk.StringVar(value=f"{len(sn_items)} items")
        ttk.Label(listwrap, textvariable=sn_count_var).grid(row=0, column=0, sticky="w", pady=(0, 3))

        treefrm = ttk.Frame(listwrap)
        treefrm.grid(row=1, column=0, sticky="nsew")
        treefrm.columnconfigure(0, weight=1)
        treefrm.rowconfigure(0, weight=1)

        sn_tree = ttk.Treeview(treefrm, columns=("nation", "nationality_info"), show="headings", height=6, selectmode="browse")
        sn_tree.heading("nation", text="Nation")
        sn_tree.heading("nationality_info", text="Nationality Info")
        sn_tree.column("nation", width=220, anchor="w")
        sn_tree.column("nationality_info", width=260, anchor="w")
        sn_tree.grid(row=0, column=0, sticky="nsew")
        sn_scroll = ttk.Scrollbar(treefrm, orient="vertical", command=sn_tree.yview)
        sn_scroll.grid(row=0, column=1, sticky="ns")
        sn_tree.configure(yscrollcommand=sn_scroll.set)

        setattr(self, f"{prefix}_second_nations_tree", sn_tree)

        editf = ttk.Frame(snf)
        editf.grid(row=3, column=0, sticky="ew", padx=6, pady=(0, 6))
        for _c in range(5):
            editf.columnconfigure(_c, weight=1 if _c in (1, 3) else 0)

        ttk.Label(editf, text="Nation").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        sn_nation_picker = self._make_searchable_picker(editf, sn_nation_var, _sn_nation_labels, width=34)
        sn_nation_picker.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=3)

        ttk.Label(editf, text="Nationality Info").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=3)
        sn_nat_info_picker = self._make_searchable_picker(editf, sn_nat_info_var, list(_nat_info_labels), width=34)
        sn_nat_info_picker.grid(row=0, column=3, sticky="ew", padx=(0, 10), pady=3)
        # International retirement controls are shown in a separate section below.

        # Comment is stored but kept compact/hidden from the layout; Add Comment button marks selected item.
        _sn_syncing = {"on": False}

        def _sn_record_from_editor():
            return {
                "nation": (sn_nation_var.get() or "").strip(),
                "nationality_info": (sn_nat_info_var.get() or "").strip(),
                "nation_declared_for": (sn_declared_var.get() or "").strip(),
                "nation_declared_for_youth": (sn_declared_youth_var.get() or "").strip(),
                "international_retirement": bool(sn_int_ret_var.get()),
                "international_retirement_date": (sn_int_ret_date_var.get() or "").strip(),
                "retiring_after_spell_current_club": bool(sn_retire_spell_var.get()),
                "comment": (sn_comment_var.get() or "").strip(),
            }

        def _sn_set_editor(rec: dict | None):
            _sn_syncing["on"] = True
            try:
                rec = rec or {}
                sn_nation_var.set(rec.get("nation", "") or "")
                sn_nat_info_var.set(rec.get("nationality_info", (_nat_info_labels[0] if _nat_info_labels else "No info")) or "")
                sn_declared_var.set(rec.get("nation_declared_for", "") or "")
                sn_declared_youth_var.set(rec.get("nation_declared_for_youth", "") or "")
                sn_int_ret_var.set(bool(rec.get("international_retirement", False)))
                sn_int_ret_date_var.set(rec.get("international_retirement_date", "") or "")
                sn_retire_spell_var.set(bool(rec.get("retiring_after_spell_current_club", False)))
                sn_comment_var.set(rec.get("comment", "") or "")
            finally:
                _sn_syncing["on"] = False

        def _sn_selected_index():
            sel = sn_tree.selection()
            if not sel:
                return None
            try:
                return int(str(sel[0]))
            except Exception:
                return None

        def _sn_refresh_tree(select_idx=None):
            try:
                for iid in sn_tree.get_children():
                    sn_tree.delete(iid)
            except Exception:
                pass
            for idx, rec in enumerate(sn_items):
                sn_tree.insert("", "end", iid=str(idx), values=(
                    rec.get("nation", "") or "",
                    rec.get("nationality_info", "") or "",
                ))
            sn_count_var.set(f"{len(sn_items)} items")
            if select_idx is not None and 0 <= int(select_idx) < len(sn_items):
                iid = str(int(select_idx))
                try:
                    sn_tree.selection_set(iid)
                    sn_tree.focus(iid)
                    sn_tree.see(iid)
                except Exception:
                    pass

        def _sn_on_select(event=None):
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            _sn_set_editor(dict(sn_items[idx]))

        def _sn_update_selected_from_editor(*_):
            if _sn_syncing["on"]:
                return
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            sn_items[idx] = _sn_record_from_editor()
            _sn_refresh_tree(select_idx=idx)

        def _sn_add():
            rec = _sn_record_from_editor()
            sn_items.append(dict(rec))
            _sn_refresh_tree(select_idx=len(sn_items) - 1)

        def _sn_insert():
            rec = _sn_record_from_editor()
            idx = _sn_selected_index()
            if idx is None:
                sn_items.append(dict(rec))
                idx = len(sn_items) - 1
            else:
                sn_items.insert(idx, dict(rec))
            _sn_refresh_tree(select_idx=idx)

        def _sn_duplicate():
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            sn_items.insert(idx + 1, dict(sn_items[idx]))
            _sn_refresh_tree(select_idx=idx + 1)

        def _sn_move(delta: int):
            idx = _sn_selected_index()
            if idx is None:
                return
            new_idx = idx + delta
            if new_idx < 0 or new_idx >= len(sn_items):
                return
            sn_items[idx], sn_items[new_idx] = sn_items[new_idx], sn_items[idx]
            _sn_refresh_tree(select_idx=new_idx)

        def _sn_sort():
            if not sn_items:
                return
            idx = _sn_selected_index()
            current = None
            if idx is not None and 0 <= idx < len(sn_items):
                current = dict(sn_items[idx])
            sn_items.sort(key=lambda rec: ((rec.get("nation") or "").lower(), (rec.get("nationality_info") or "").lower()))
            new_idx = None
            if current is not None:
                for i, rec in enumerate(sn_items):
                    if rec == current:
                        new_idx = i
                        break
            _sn_refresh_tree(select_idx=new_idx if new_idx is not None else 0)

        def _sn_remove():
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            del sn_items[idx]
            new_idx = min(idx, len(sn_items) - 1)
            _sn_refresh_tree(select_idx=new_idx if new_idx >= 0 else None)
            if not sn_items:
                _sn_set_editor(None)

        def _sn_copy():
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            setattr(self, f"{prefix}_second_nations_clipboard", dict(sn_items[idx]))

        def _sn_paste():
            clip = getattr(self, f"{prefix}_second_nations_clipboard", None)
            if not isinstance(clip, dict):
                return
            idx = _sn_selected_index()
            if idx is None:
                sn_items.append(dict(clip))
                idx = len(sn_items) - 1
            else:
                sn_items.insert(idx + 1, dict(clip))
                idx = idx + 1
            _sn_refresh_tree(select_idx=idx)

        def _sn_clear():
            sn_items.clear()
            _sn_refresh_tree()
            _sn_set_editor(None)

        def _sn_add_comment():
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                try:
                    messagebox.showinfo("Second Nations", "Select an item first, then click Add Comment.")
                except Exception:
                    pass
                return
            rec = dict(sn_items[idx])
            existing = (rec.get("comment") or "").strip()
            rec["comment"] = existing if existing else "Comment"
            sn_items[idx] = rec
            _sn_set_editor(rec)
            _sn_refresh_tree(select_idx=idx)

        _sn_buttons = [
            ("Add", _sn_add),
            ("Insert", _sn_insert),
            ("Duplicate", _sn_duplicate),
            ("Move Up", lambda: _sn_move(-1)),
            ("Move Down", lambda: _sn_move(1)),
            ("Sort", _sn_sort),
            ("Remove", _sn_remove),
            ("Copy", _sn_copy),
            ("Paste", _sn_paste),
            ("Clear", _sn_clear),
            ("Add Comment", _sn_add_comment),
        ]
        for _i, (_txt, _cmd) in enumerate(_sn_buttons):
            ttk.Button(btnbar, text=_txt, command=_cmd).grid(row=0, column=_i, sticky="w", padx=(0, 4), pady=0)

        sn_tree.bind("<<TreeviewSelect>>", _sn_on_select, add="+")
        for _v in (sn_nation_var, sn_nat_info_var, sn_declared_var, sn_declared_youth_var, sn_int_ret_date_var, sn_comment_var):
            try:
                _v.trace_add("write", _sn_update_selected_from_editor)
            except Exception:
                pass
        for _bv in (sn_int_ret_var, sn_retire_spell_var):
            try:
                _bv.trace_add("write", _sn_update_selected_from_editor)
            except Exception:
                pass

        _sn_refresh_tree()
        if sn_items:
            _sn_refresh_tree(select_idx=0)

        r += 1

        # Declared For Nation At Youth Level (separate FM field; not inside Second Nations list rows)
        dyf = ttk.LabelFrame(detailsf, text="Declared For Nation At Youth Level")
        dyf.grid(row=r, column=0, columnspan=3, sticky="ew", padx=6, pady=(8, 4))
        dyf.columnconfigure(4, weight=1)

        dy_mode_var = getattr(self, f"{prefix}_details_declared_for_youth_nation_mode", None)
        if dy_mode_var is None:
            dy_mode_var = tk.StringVar(value="none")
            setattr(self, f"{prefix}_details_declared_for_youth_nation_mode", dy_mode_var)

        dy_value_var = getattr(self, f"{prefix}_details_declared_for_youth_nation_value", None)
        if dy_value_var is None:
            dy_value_var = tk.StringVar(value="")
            setattr(self, f"{prefix}_details_declared_for_youth_nation_value", dy_value_var)
        ttk.Radiobutton(dyf, text="Random", variable=dy_mode_var, value="random").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(dyf, text="Custom", variable=dy_mode_var, value="custom").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(dyf, text="Don't set", variable=dy_mode_var, value="none").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(dyf, text="Nation").grid(row=0, column=3, sticky="e", padx=(10, 6), pady=6)
        dy_picker = self._make_searchable_picker(dyf, dy_value_var, _sn_nation_labels, width=34)
        dy_picker.grid(row=0, column=4, sticky="ew", padx=(0, 8), pady=6)

        try:
            self._bind_mode_enable(dy_mode_var, "custom", [dy_picker], clear_on_random=False)
        except Exception:
            pass

        r += 1

        # International Retirement (separate from Second Nations editor)
        irf = ttk.LabelFrame(detailsf, text="International Retirement")
        irf.grid(row=r, column=0, columnspan=3, sticky="ew", padx=6, pady=(8, 4))
        for _c in range(5):
            irf.columnconfigure(_c, weight=1 if _c == 3 else 0)

        ttk.Checkbutton(irf, text="International Retirement", variable=sn_int_ret_var).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=6
        )
        ttk.Label(irf, text="International Retirement Date").grid(row=0, column=2, sticky="e", padx=(10, 6), pady=6)
        sn_int_ret_date_entry = ttk.Entry(irf, textvariable=sn_int_ret_date_var, width=16)
        sn_int_ret_date_entry.grid(row=0, column=3, sticky="w", pady=6)
        sn_int_ret_date_btn = ttk.Button(irf, text="📅", width=3, command=lambda v=sn_int_ret_date_var: self._open_calendar(v))
        sn_int_ret_date_btn.grid(row=0, column=4, sticky="w", padx=(4, 8), pady=6)

        ttk.Checkbutton(irf, text="Retiring After Spell At Current Club", variable=sn_retire_spell_var).grid(
            row=1, column=0, columnspan=5, sticky="w", padx=8, pady=(0, 6)
        )

        r += 1

        # Height block in Details (same layout style as Other tab height controls)
        hbox = ttk.LabelFrame(detailsf, text="Height")
        hbox.grid(row=r, column=0, columnspan=3, sticky="ew", padx=6, pady=(8, 4))
        for c in range(7):
            hbox.columnconfigure(c, weight=0)

        # New preferred Details height vars (kept separate from legacy details_height_mode/value)
        h_mode_var = getattr(self, f"{prefix}_details_height_mode2", None)
        if h_mode_var is None:
            h_mode_var = tk.StringVar(value="none")
            setattr(self, f"{prefix}_details_height_mode2", h_mode_var)

        h_min_var = getattr(self, f"{prefix}_details_height_min", None)
        if h_min_var is None:
            h_min_var = tk.StringVar(value="150")
            setattr(self, f"{prefix}_details_height_min", h_min_var)

        h_max_var = getattr(self, f"{prefix}_details_height_max", None)
        if h_max_var is None:
            h_max_var = tk.StringVar(value="210")
            setattr(self, f"{prefix}_details_height_max", h_max_var)

        h_fixed_var = getattr(self, f"{prefix}_details_height_fixed", None)
        if h_fixed_var is None:
            legacy_h = getattr(self, f"{prefix}_details_height_value", tk.StringVar(value="")).get()
            h_fixed_var = tk.StringVar(value=legacy_h)
            setattr(self, f"{prefix}_details_height_fixed", h_fixed_var)

        ttk.Radiobutton(hbox, text="Random height range", variable=h_mode_var, value="range").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(hbox, text="Don't set", variable=h_mode_var, value="none").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(hbox, text="Fixed height", variable=h_mode_var, value="fixed").grid(row=0, column=4, sticky="w", padx=8, pady=6)

        ttk.Label(hbox, text="Min").grid(row=1, column=0, sticky="e", padx=(8, 2), pady=4)
        h_min_entry = ttk.Entry(hbox, textvariable=h_min_var, width=6)
        h_min_entry.grid(row=1, column=1, sticky="w", padx=8, pady=4)
        ttk.Label(hbox, text="Max").grid(row=1, column=2, sticky="e", padx=(8, 2), pady=4)
        h_max_entry = ttk.Entry(hbox, textvariable=h_max_var, width=6)
        h_max_entry.grid(row=1, column=3, sticky="w", padx=8, pady=4)
        ttk.Label(hbox, text="Height").grid(row=1, column=4, sticky="e", padx=(8, 2), pady=4)
        h_fixed_entry = ttk.Entry(hbox, textvariable=h_fixed_var, width=6)
        h_fixed_entry.grid(row=1, column=5, sticky="w", padx=8, pady=4)

        # Height converter (ft/in) for Fixed height
        # - Adds Feet/Inches inputs under the Fixed height cm field
        # - Syncs: cm -> ft/in always, ft/in -> cm only when mode == fixed
        try:
            ttk.Label(hbox, text="cm").grid(row=1, column=6, sticky="w", padx=(2, 0), pady=4)
        except Exception:
            pass

        ft_var = getattr(self, f"{prefix}_details_height_ft", None)
        if ft_var is None:
            ft_var = tk.StringVar(value="")
            setattr(self, f"{prefix}_details_height_ft", ft_var)

        in_var = getattr(self, f"{prefix}_details_height_in", None)
        if in_var is None:
            in_var = tk.StringVar(value="")
            setattr(self, f"{prefix}_details_height_in", in_var)

        # UI row: Feet / Inches
        ttk.Label(hbox, text="Feet").grid(row=2, column=0, sticky="e", padx=(8, 2), pady=(0, 6))
        ft_entry = ttk.Entry(hbox, textvariable=ft_var, width=4)
        ft_entry.grid(row=2, column=1, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(hbox, text="Inches").grid(row=2, column=2, sticky="e", padx=(8, 2), pady=(0, 6))
        in_entry = ttk.Entry(hbox, textvariable=in_var, width=4)
        in_entry.grid(row=2, column=3, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(hbox, text="(updates Fixed cm)").grid(row=2, column=4, columnspan=3, sticky="w", padx=(8, 2), pady=(0, 6))

        lock_attr = f"__{prefix}_height_ftin_lock"

        def _cm_to_ftin(cm_val: float) -> tuple[int, int]:
            total_inches = cm_val / 2.54
            ft = int(total_inches // 12)
            inch = int(round(total_inches - (ft * 12)))
            if inch >= 12:
                ft += 1
                inch = 0
            if inch < 0:
                inch = 0
            return ft, inch

        def _ftin_to_cm(ft: int, inch: int) -> int:
            if inch >= 12:
                ft += int(inch // 12)
                inch = int(inch % 12)
            if inch < 0:
                inch = 0
            if ft < 0:
                ft = 0
            cm = (ft * 12 + inch) * 2.54
            return int(round(cm))

        def _sync_from_cm(*_):
            try:
                if getattr(self, lock_attr, False):
                    return
            except Exception:
                pass
            try:
                raw = (h_fixed_var.get() or "").strip()
                if not raw:
                    return
                cm_val = float(raw)
            except Exception:
                return
            try:
                setattr(self, lock_attr, True)
            except Exception:
                pass
            try:
                ft, inch = _cm_to_ftin(cm_val)
                ft_var.set(str(ft))
                in_var.set(str(inch))
            finally:
                try:
                    setattr(self, lock_attr, False)
                except Exception:
                    pass

        def _sync_from_ftin(*_):
            # Only drive cm when Fixed height mode is selected
            try:
                mode = (h_mode_var.get() or "").strip().lower()
            except Exception:
                mode = ""
            if mode != "fixed":
                return
            try:
                if getattr(self, lock_attr, False):
                    return
            except Exception:
                pass

            try:
                ft_raw = (ft_var.get() or "").strip()
                in_raw = (in_var.get() or "").strip()
                if ft_raw == "" and in_raw == "":
                    return
                ft = int(ft_raw) if ft_raw != "" else 0
                inch = int(in_raw) if in_raw != "" else 0
            except Exception:
                return

            cm_int = _ftin_to_cm(ft, inch)
            try:
                setattr(self, lock_attr, True)
            except Exception:
                pass
            try:
                h_fixed_var.set(str(cm_int))
            finally:
                try:
                    setattr(self, lock_attr, False)
                except Exception:
                    pass

        def _refresh_ftin_state(*_):
            try:
                mode = (h_mode_var.get() or "range").strip().lower()
            except Exception:
                mode = "range"
            st = "normal" if mode == "fixed" else "disabled"
            for w in (ft_entry, in_entry):
                try:
                    w.configure(state=st)
                except Exception:
                    pass

        try:
            h_fixed_var.trace_add("write", _sync_from_cm)
        except Exception:
            pass
        try:
            ft_var.trace_add("write", _sync_from_ftin)
            in_var.trace_add("write", _sync_from_ftin)
        except Exception:
            pass

        try:
            h_mode_var.trace_add("write", _refresh_ftin_state)
        except Exception:
            pass

        # Initialise display + state
        _sync_from_cm()
        _refresh_ftin_state()

        # Height range converter (ft/in) for Random height range
        # Adds Min/Max Feet/Inches inputs that sync with Range Min/Max cm
        # Sync rules:
        # - cm -> ft/in always
        # - ft/in -> cm only when mode == "range"

        min_ft_var = getattr(self, f"{prefix}_details_height_min_ft", None)
        if min_ft_var is None:
            min_ft_var = tk.StringVar(value="")
            setattr(self, f"{prefix}_details_height_min_ft", min_ft_var)

        min_in_var = getattr(self, f"{prefix}_details_height_min_in", None)
        if min_in_var is None:
            min_in_var = tk.StringVar(value="")
            setattr(self, f"{prefix}_details_height_min_in", min_in_var)

        max_ft_var = getattr(self, f"{prefix}_details_height_max_ft", None)
        if max_ft_var is None:
            max_ft_var = tk.StringVar(value="")
            setattr(self, f"{prefix}_details_height_max_ft", max_ft_var)

        max_in_var = getattr(self, f"{prefix}_details_height_max_in", None)
        if max_in_var is None:
            max_in_var = tk.StringVar(value="")
            setattr(self, f"{prefix}_details_height_max_in", max_in_var)

        # Layout rows (below the Fixed converter row)
        # Row 3: Min ft/in
        ttk.Label(hbox, text="Min ft").grid(row=3, column=0, sticky="e", padx=(8, 2), pady=(0, 2))
        min_ft_entry = ttk.Entry(hbox, textvariable=min_ft_var, width=4)
        min_ft_entry.grid(row=3, column=1, sticky="w", padx=8, pady=(0, 2))
        ttk.Label(hbox, text="in").grid(row=3, column=2, sticky="e", padx=(8, 2), pady=(0, 2))
        min_in_entry = ttk.Entry(hbox, textvariable=min_in_var, width=4)
        min_in_entry.grid(row=3, column=3, sticky="w", padx=8, pady=(0, 2))

        # Row 4: Max ft/in
        ttk.Label(hbox, text="Max ft").grid(row=4, column=0, sticky="e", padx=(8, 2), pady=(0, 6))
        max_ft_entry = ttk.Entry(hbox, textvariable=max_ft_var, width=4)
        max_ft_entry.grid(row=4, column=1, sticky="w", padx=8, pady=(0, 6))
        ttk.Label(hbox, text="in").grid(row=4, column=2, sticky="e", padx=(8, 2), pady=(0, 6))
        max_in_entry = ttk.Entry(hbox, textvariable=max_in_var, width=4)
        max_in_entry.grid(row=4, column=3, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(hbox, text="(updates Range Min/Max cm)").grid(row=3, column=4, columnspan=3, sticky="w", padx=(8, 2), pady=(0, 2))

        range_lock_attr = f"__{prefix}_height_range_ftin_lock"

        def _cm_to_ftin2(cm_val: float) -> tuple[int, int]:
            total_inches = cm_val / 2.54
            ft = int(total_inches // 12)
            inch = int(round(total_inches - (ft * 12)))
            if inch >= 12:
                ft += 1
                inch = 0
            if inch < 0:
                inch = 0
            return ft, inch

        def _ftin_to_cm2(ft: int, inch: int) -> int:
            if inch >= 12:
                ft += int(inch // 12)
                inch = int(inch % 12)
            if inch < 0:
                inch = 0
            if ft < 0:
                ft = 0
            cm = (ft * 12 + inch) * 2.54
            return int(round(cm))

        def _range_sync_from_cm(*_):
            try:
                if getattr(self, range_lock_attr, False):
                    return
            except Exception:
                pass

            try:
                mn = (h_min_var.get() or "").strip()
                mx = (h_max_var.get() or "").strip()
                mn_f = float(mn) if mn else None
                mx_f = float(mx) if mx else None
            except Exception:
                return

            try:
                setattr(self, range_lock_attr, True)
            except Exception:
                pass
            try:
                if mn_f is not None:
                    ft, inch = _cm_to_ftin2(mn_f)
                    min_ft_var.set(str(ft))
                    min_in_var.set(str(inch))
                if mx_f is not None:
                    ft, inch = _cm_to_ftin2(mx_f)
                    max_ft_var.set(str(ft))
                    max_in_var.set(str(inch))
            finally:
                try:
                    setattr(self, range_lock_attr, False)
                except Exception:
                    pass

        def _range_sync_from_ftin(*_):
            try:
                mode = (h_mode_var.get() or "range").strip().lower()
            except Exception:
                mode = "range"
            if mode != "range":
                return

            try:
                if getattr(self, range_lock_attr, False):
                    return
            except Exception:
                pass

            def _parse(a: str) -> int | None:
                a = (a or "").strip()
                if a == "":
                    return None
                return int(a)

            try:
                mn_ft = _parse(min_ft_var.get())
                mn_in = _parse(min_in_var.get())
                mx_ft = _parse(max_ft_var.get())
                mx_in = _parse(max_in_var.get())
            except Exception:
                return

            try:
                setattr(self, range_lock_attr, True)
            except Exception:
                pass
            try:
                if mn_ft is not None or mn_in is not None:
                    cm = _ftin_to_cm2(mn_ft or 0, mn_in or 0)
                    h_min_var.set(str(cm))
                if mx_ft is not None or mx_in is not None:
                    cm = _ftin_to_cm2(mx_ft or 0, mx_in or 0)
                    h_max_var.set(str(cm))
            finally:
                try:
                    setattr(self, range_lock_attr, False)
                except Exception:
                    pass

        def _refresh_range_ftin_state(*_):
            try:
                mode = (h_mode_var.get() or "range").strip().lower()
            except Exception:
                mode = "range"
            st = "normal" if mode == "range" else "disabled"
            for w in (min_ft_entry, min_in_entry, max_ft_entry, max_in_entry):
                try:
                    w.configure(state=st)
                except Exception:
                    pass

        try:
            h_min_var.trace_add("write", _range_sync_from_cm)
            h_max_var.trace_add("write", _range_sync_from_cm)
        except Exception:
            pass
        try:
            min_ft_var.trace_add("write", _range_sync_from_ftin)
            min_in_var.trace_add("write", _range_sync_from_ftin)
            max_ft_var.trace_add("write", _range_sync_from_ftin)
            max_in_var.trace_add("write", _range_sync_from_ftin)
        except Exception:
            pass

        try:
            h_mode_var.trace_add("write", _refresh_range_ftin_state)
        except Exception:
            pass

        _range_sync_from_cm()
        _refresh_range_ftin_state()


        def _refresh_details_height_mode(*_):
            mode = (h_mode_var.get() or "range").strip().lower()
            range_state = "normal" if mode == "range" else "disabled"
            fixed_state = "normal" if mode == "fixed" else "disabled"
            for w in (h_min_entry, h_max_entry):
                try:
                    w.configure(state=range_state)
                except Exception:
                    pass
            try:
                h_fixed_entry.configure(state=fixed_state)
            except Exception:
                pass

        try:
            h_mode_var.trace_add("write", _refresh_details_height_mode)
        except Exception:
            pass
        _refresh_details_height_mode()
        r += 1

        # Compact DOB block in Details (uses main batch/single DOB vars)
        dobf = ttk.LabelFrame(detailsf, text="DOB (Age range / DOB range / Fixed)")
        dobf.grid(row=r, column=0, columnspan=3, sticky="ew", padx=6, pady=(8, 4))
        for c in range(11):
            dobf.columnconfigure(c, weight=0)

        mode_var = getattr(self, f"{prefix}_dob_mode")
        age_min_var = getattr(self, f"{prefix}_age_min", None)
        age_max_var = getattr(self, f"{prefix}_age_max", None)
        if age_min_var is None:
            age_seed = getattr(self, f"{prefix}_age", tk.StringVar(value="14")).get()
            age_min_var = tk.StringVar(value=age_seed)
            setattr(self, f"{prefix}_age_min", age_min_var)
        if age_max_var is None:
            age_seed = getattr(self, f"{prefix}_age", tk.StringVar(value="14")).get()
            age_max_var = tk.StringVar(value=age_seed)
            setattr(self, f"{prefix}_age_max", age_max_var)

        dob_fixed_var = getattr(self, f"{prefix}_dob_fixed", None)
        if dob_fixed_var is None:
            dob_fixed_var = getattr(self, f"{prefix}_dob", tk.StringVar(value="2012-07-01"))
            setattr(self, f"{prefix}_dob_fixed", dob_fixed_var)
        dob_start_var = getattr(self, f"{prefix}_dob_start", None)
        if dob_start_var is None:
            dob_start_var = tk.StringVar(value="2010-01-01")
            setattr(self, f"{prefix}_dob_start", dob_start_var)
        dob_end_var = getattr(self, f"{prefix}_dob_end", None)
        if dob_end_var is None:
            dob_end_var = tk.StringVar(value="2012-12-31")
            setattr(self, f"{prefix}_dob_end", dob_end_var)

        # Layout requested:
        # Random [radio] - Age[min/max] - DOB Range[start/end] - DOB Fix[date]
        # Keep legacy mode compatibility:
        # - Batch legacy uses "range"/"fixed"
        # - Single legacy uses "age"/"dob" (where "dob" means fixed DOB)
        dob_range_value = "range"
        dob_fixed_value = "dob" if prefix == "single" else "fixed"

        ttk.Radiobutton(dobf, text="Random", variable=mode_var, value="age").grid(row=0, column=0, sticky="w", padx=(6, 10), pady=(6, 2))
        ttk.Label(dobf, text="Age").grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Label(dobf, text="Min").grid(row=0, column=2, sticky="e", padx=(0, 4))
        age_min_entry = ttk.Entry(dobf, textvariable=age_min_var, width=7)
        age_min_entry.grid(row=0, column=3, sticky="w", padx=(0, 12), pady=(6, 2))
        ttk.Label(dobf, text="Max").grid(row=1, column=2, sticky="e", padx=(0, 4))
        age_max_entry = ttk.Entry(dobf, textvariable=age_max_var, width=7)
        age_max_entry.grid(row=1, column=3, sticky="w", padx=(0, 12), pady=(2, 6))

        ttk.Radiobutton(dobf, text="DOB Range", variable=mode_var, value=dob_range_value).grid(row=0, column=4, sticky="w", padx=(0, 8), pady=(6, 2))
        ttk.Label(dobf, text="Start").grid(row=0, column=5, sticky="e", padx=(0, 4))
        start_entry = ttk.Entry(dobf, textvariable=dob_start_var, width=12)
        start_entry.grid(row=0, column=6, sticky="w", pady=(6, 2))
        start_btn = ttk.Button(dobf, text="📅", width=3, command=lambda v=dob_start_var: self._open_calendar(v))
        start_btn.grid(row=0, column=7, sticky="w", padx=(4, 12), pady=(6, 2))

        ttk.Label(dobf, text="End").grid(row=1, column=5, sticky="e", padx=(0, 4))
        end_entry = ttk.Entry(dobf, textvariable=dob_end_var, width=12)
        end_entry.grid(row=1, column=6, sticky="w", pady=(2, 6))
        end_btn = ttk.Button(dobf, text="📅", width=3, command=lambda v=dob_end_var: self._open_calendar(v))
        end_btn.grid(row=1, column=7, sticky="w", padx=(4, 12), pady=(2, 6))

        ttk.Radiobutton(dobf, text="DOB Fix", variable=mode_var, value=dob_fixed_value).grid(row=0, column=8, sticky="w", padx=(0, 8), pady=(6, 2))
        ttk.Radiobutton(dobf, text="Don\'t set", variable=mode_var, value="none").grid(row=0, column=10, sticky="w", padx=(12, 6), pady=(6, 2))
        ttk.Label(dobf, text="Date").grid(row=0, column=9, sticky="w", padx=(0, 4), pady=(6, 2))
        fixed_entry = ttk.Entry(dobf, textvariable=dob_fixed_var, width=12)
        fixed_entry.grid(row=1, column=8, sticky="w", padx=(0, 4), pady=(2, 6))
        fixed_btn = ttk.Button(dobf, text="📅", width=3, command=lambda v=dob_fixed_var: self._open_calendar(v))
        fixed_btn.grid(row=1, column=9, sticky="w", pady=(2, 6))

        def _refresh_dob_mode(*_):
            mode = (mode_var.get() or "age").strip().lower()
            age_state = "normal" if mode == "age" else "disabled"
            range_state = "normal" if mode == dob_range_value else "disabled"
            fixed_state = "normal" if mode == dob_fixed_value else "disabled"
            for w in (age_min_entry, age_max_entry):
                try:
                    w.configure(state=age_state)
                except Exception:
                    pass
            for w in (start_entry, end_entry, start_btn, end_btn):
                try:
                    w.configure(state=range_state)
                except Exception:
                    pass
            for w in (fixed_entry, fixed_btn):
                try:
                    w.configure(state=fixed_state)
                except Exception:
                    pass

        try:
            mode_var.trace_add("write", _refresh_dob_mode)
        except Exception:
            pass
        _refresh_dob_mode()

        # Move Details blocks to requested positions:
        # - Height above Body Type
        # - DOB above City Of Birth
        def _find_details_row_by_label_text(text: str):
            for _w in detailsf.grid_slaves():
                try:
                    if str(_w.cget("text")) == text:
                        gi = _w.grid_info()
                        return int(gi.get("row", 0))
                except Exception:
                    continue
            return None

        def _move_row_widget_above(_widget, target_row: int):
            try:
                giw = _widget.grid_info()
                src_row = int(giw.get("row", 0))
            except Exception:
                return
            if target_row is None or src_row <= int(target_row):
                return
            target_row = int(target_row)
            # Shift every widget row in [target_row, src_row-1] down by one, then place widget at target_row
            for _child in detailsf.grid_slaves():
                if _child is _widget:
                    continue
                try:
                    gic = _child.grid_info()
                    crow = int(gic.get("row", 0))
                except Exception:
                    continue
                if target_row <= crow < src_row:
                    try:
                        _child.grid_configure(row=crow + 1)
                    except Exception:
                        pass
            try:
                _widget.grid_configure(row=target_row)
            except Exception:
                pass

        _body_row = _find_details_row_by_label_text("Body Type")
        if _body_row is not None:
            _move_row_widget_above(hbox, _body_row)

        _city_row = _find_details_row_by_label_text("City Of Birth")
        if _city_row is not None:
            _move_row_widget_above(dobf, _city_row)

    def _build_batch_details_tab(self) -> None:
        frm = self.batch_details_body
        for c in range(3):
            frm.columnconfigure(c, weight=1)

        # Mirrored file inputs on Details tab (same vars as Other tab)
        paths = ttk.LabelFrame(frm, text="File inputs")
        paths.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        paths.columnconfigure(1, weight=1)
        self.batch_details_paths_frame = paths
        paths.grid_remove()

        def row_file(r, label, var, is_save=False):
            ttk.Label(paths, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ttk.Entry(paths, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            if is_save:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_save_xml(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)
            else:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_open_file(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "master_library.csv:", self.batch_clubs, is_save=False)
        row_file(1, "Male first names CSV:", self.batch_first, is_save=False)
        row_file(2, "Female first names CSV:", self.batch_female_first, is_save=False)
        row_file(3, "Common names CSV:", self.batch_common_names, is_save=False)
        row_file(4, "Surnames CSV:", self.batch_surn, is_save=False)
        row_file(5, "Output XML:", self.batch_out, is_save=True)
        row_file(6, "Generator script:", self.batch_script, is_save=False)
        row_file(7, "Region mapping CSV (placeholder):", self.batch_region_map_csv, is_save=False)


        # # [PATCH TOOLTIP MORE v2] batch_count

        # # [PATCH TOOLTIP MORE v2b] label:genf:Seed

        # # [PATCH TOOLTIP MORE v2] batch_seed

        # # [PATCH TOOLTIP MORE v2b] label:genf:Base year

        # # [PATCH TOOLTIP MORE v2] batch_base_year

        # Player tab: Person Type and Job are locked to Player
        rolef = ttk.LabelFrame(frm, text="Person Type / Job (locked)")
        rolef.grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        rolef.columnconfigure(1, weight=1)
        ttk.Label(rolef, text="Person Type:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Label(rolef, text="Player").grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(rolef, text="Job / Role:").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Label(rolef, text="Player").grid(row=0, column=3, sticky="w", padx=6, pady=6)

        self._add_details_section(frm, row=3, prefix="batch")
        try:
            ttk.Label(
                frm,
                text="Details settings for Batch generation. Region Of Birth is disabled until custom region mapping is configured.",
                foreground="#444",
                wraplength=900,
                justify="left",
            ).grid(row=4, column=0, sticky="w", padx=8, pady=(0, 8))
        except Exception:
            pass

    def _build_single_details_tab(self) -> None:
        frm = self.single_details_body
        for c in range(3):
            frm.columnconfigure(c, weight=1)

        # Mirrored file inputs on Details tab (same vars as Other tab)
        paths = ttk.LabelFrame(frm, text="File inputs")
        paths.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        paths.columnconfigure(1, weight=1)
        self.single_details_paths_frame = paths
        paths.grid_remove()

        def row_file(r, label, var, is_save=False):
            ttk.Label(paths, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ttk.Entry(paths, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            if is_save:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_save_xml(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)
            else:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_open_file(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "master_library.csv:", self.single_clubs, is_save=False)
        row_file(1, "Male first names CSV:", self.single_first, is_save=False)
        row_file(2, "Female first names CSV:", self.single_female_first, is_save=False)
        row_file(3, "Common names CSV:", self.single_common_names, is_save=False)
        row_file(4, "Surnames CSV:", self.single_surn, is_save=False)
        row_file(5, "Output XML:", self.single_out, is_save=True)
        row_file(6, "Generator script:", self.single_script, is_save=False)
        row_file(7, "Region mapping CSV (placeholder):", self.single_region_map_csv, is_save=False)


        # Player tab: Person Type and Job are locked to Player
        rolef = ttk.LabelFrame(frm, text="Person Type / Job (locked)")
        rolef.grid(row=2, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        rolef.columnconfigure(1, weight=1)
        ttk.Label(rolef, text="Person Type:").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Label(rolef, text="Player").grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(rolef, text="Job / Role:").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Label(rolef, text="Player").grid(row=0, column=3, sticky="w", padx=6, pady=6)

        self._add_details_section(frm, row=3, prefix="single")
        try:
            ttk.Label(
                frm,
                text="Details settings for Single-player generation. Region Of Birth is disabled until custom region mapping is configured.",
                foreground="#444",
                wraplength=900,
                justify="left",
            ).grid(row=4, column=0, sticky="w", padx=8, pady=(0, 8))
        except Exception:
            pass

    # ---------------- Master library cache (clubs/cities/nations) ----------------
