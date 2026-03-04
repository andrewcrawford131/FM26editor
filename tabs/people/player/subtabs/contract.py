# -*- coding: utf-8 -*-
# Auto-generated from fm26_generator_gui_2.py
# Player Contract tab extracted into a mixin to reduce main GUI file size.


from __future__ import annotations

import tkinter as tk
from tkinter import ttk


class ContractSubtabMixin:
    def _build_contract_tab_common(self, frm, prefix: str, mode_label: str) -> None:
            """
            Contract tab UI scaffold (expanded Club Contract fields).
            The four sub-tabs are only visible when the parent Contract tab is opened
            because they live inside this nested notebook.
            """
            try:
                frm.columnconfigure(0, weight=1)
            except Exception:
                pass
            # File inputs (hidden by default) — mirrored from Other/Details for convenience
            paths = ttk.LabelFrame(frm, text="File inputs")
            paths.grid(row=0, column=0, sticky="ew", padx=8, pady=(0, 8))
            paths.columnconfigure(1, weight=1)
            setattr(self, f"{prefix}_contract_paths_frame", paths)
            try:
                paths.grid_remove()
            except Exception:
                pass

            def row_file(r, label, var, is_save=False):
                ttk.Label(paths, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
                ttk.Entry(paths, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
                if is_save:
                    ttk.Button(paths, text="Browse…", command=lambda: self._pick_save_xml(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)
                else:
                    ttk.Button(paths, text="Browse…", command=lambda: self._pick_open_file(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

            if prefix == "batch":
                row_file(0, "master_library.csv:", self.batch_clubs, is_save=False)
                row_file(1, "Male first names CSV:", self.batch_first, is_save=False)
                row_file(2, "Female first names CSV:", self.batch_female_first, is_save=False)
                row_file(3, "Common names CSV:", self.batch_common_names, is_save=False)
                row_file(4, "Surnames CSV:", self.batch_surn, is_save=False)
                row_file(5, "Output XML:", self.batch_out, is_save=True)
                row_file(6, "Generator script:", self.batch_script, is_save=False)
                row_file(7, "Region mapping CSV (placeholder):", self.batch_region_map_csv, is_save=False)
            else:
                row_file(0, "master_library.csv:", self.single_clubs, is_save=False)
                row_file(1, "Male first names CSV:", self.single_first, is_save=False)
                row_file(2, "Female first names CSV:", self.single_female_first, is_save=False)
                row_file(3, "Common names CSV:", self.single_common_names, is_save=False)
                row_file(4, "Surnames CSV:", self.single_surn, is_save=False)
                row_file(5, "Output XML:", self.single_out, is_save=True)
                row_file(6, "Generator script:", self.single_script, is_save=False)
                row_file(7, "Region mapping CSV (placeholder):", self.single_region_map_csv, is_save=False)

            for _c in range(6):
                pass  # [AUTO_EMPTY_FOR_FIX]

            if prefix == "batch":
                pass  # [AUTO_EMPTY_BLOCK_FIX]
                # # [PATCH TOOLTIP MORE v2] batch_count



            subnb = ttk.Notebook(frm)
            subnb.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 8))
            frm.rowconfigure(2, weight=1)
            setattr(self, f"{prefix}_contract_subnotebook", subnb)

            tab_defs = [
                ("club_contract", "Club Contract"),
                ("loan", "Loan"),
                ("past_transfers", "Past Transfers"),
                ("future_transfer", "Future Transfer"),
            ]
            tabs = {}
            for key, label in tab_defs:
                tab = ttk.Frame(subnb)
                tab.columnconfigure(0, weight=1)
                subnb.add(tab, text=label)
                tabs[key] = tab
                setattr(self, f"{prefix}_{key}_tab", tab)

            # ---------- Club Contract (extended UI scaffold) ----------
            club_tab = tabs["club_contract"]
            club_tab.columnconfigure(0, weight=1)

            vars_store = {}
            setattr(self, f"{prefix}_club_contract_vars", vars_store)

            row_index = 0

            def _section(parent, title: str):
                nonlocal row_index
                lf = ttk.LabelFrame(parent, text=title)
                lf.grid(row=row_index, column=0, sticky="ew", padx=6, pady=(0, 8))
                lf.columnconfigure(0, weight=0)
                lf.columnconfigure(1, weight=0)
                lf.columnconfigure(2, weight=1)
                row_index += 1
                return lf

            def _set_widget_state(widget, state):
                # User preference: keep dropdowns typeable.
                try:
                    if isinstance(widget, ttk.Combobox):
                        widget.configure(state="normal")
                        return
                except Exception:
                    pass
                try:
                    widget.configure(state=state)
                    return
                except Exception:
                    pass
                try:
                    widget.state(["!disabled"] if state != "disabled" else ["disabled"])
                except Exception:
                    pass

            def _apply_mode(mode_var, custom_widgets, random_widgets=None):
                random_widgets = random_widgets or []
                m = (mode_var.get() or "not_set").strip().lower()
                if m == "custom":
                    for w in custom_widgets:
                        _set_widget_state(w, "normal")
                    for w in random_widgets:
                        _set_widget_state(w, "disabled")
                elif m == "random":
                    for w in custom_widgets:
                        _set_widget_state(w, "disabled")
                    for w in random_widgets:
                        _set_widget_state(w, "normal")
                else:  # not_set
                    for w in custom_widgets:
                        _set_widget_state(w, "disabled")
                    for w in random_widgets:
                        _set_widget_state(w, "disabled")

            def _mode_strip(parent, r, key):
                mode = tk.StringVar(value="not_set")
                vars_store[f"{key}_mode"] = mode
                wrap = ttk.Frame(parent)
                wrap.grid(row=r, column=1, sticky="w", padx=(0, 6), pady=2)
                ttk.Radiobutton(wrap, text="Random", value="random", variable=mode).pack(side="left", padx=(0, 4))
                ttk.Radiobutton(wrap, text="Custom", value="custom", variable=mode).pack(side="left", padx=(0, 4))
                ttk.Radiobutton(wrap, text="Don't set", value="not_set", variable=mode).pack(side="left")
                return mode

            def _row_entry(parent, r, label, key, width=30):
                ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=4)
                mode = _mode_strip(parent, r, key)
                v = tk.StringVar(value="")
                vars_store[f"{key}_var"] = v
                ent = ttk.Entry(parent, textvariable=v, width=width)
                ent.grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=4)
                def _sync(*_):
                    _apply_mode(mode, [ent])
                try:
                    mode.trace_add("write", _sync)
                except Exception:
                    pass
                _sync()
                return v


            def _row_wage(parent, r, label, key):
                """Wage row with Random range (min/max) and Custom fixed value, plus Don't set."""
                ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=4)
                mode = _mode_strip(parent, r, key)

                fixed = tk.StringVar(value="")
                vars_store[f"{key}_var"] = fixed

                # Defaults are harmless because the row defaults to Don't set (disabled)
                vmin = tk.StringVar(value="30")
                vmax = tk.StringVar(value="80")
                vars_store[f"{key}_min_var"] = vmin
                vars_store[f"{key}_max_var"] = vmax

                wrap = ttk.Frame(parent)
                wrap.grid(row=r, column=2, sticky="w", padx=(0, 8), pady=4)

                ttk.Label(wrap, text="Min").grid(row=0, column=0, sticky="w", padx=(0, 4))
                ent_min = ttk.Entry(wrap, textvariable=vmin, width=8)
                ent_min.grid(row=0, column=1, sticky="w", padx=(0, 10))

                ttk.Label(wrap, text="Max").grid(row=0, column=2, sticky="w", padx=(0, 4))
                ent_max = ttk.Entry(wrap, textvariable=vmax, width=8)
                ent_max.grid(row=0, column=3, sticky="w", padx=(0, 14))

                ttk.Label(wrap, text="Fixed").grid(row=0, column=4, sticky="w", padx=(0, 4))
                ent_fixed = ttk.Entry(wrap, textvariable=fixed, width=10)
                ent_fixed.grid(row=0, column=5, sticky="w")

                def _sync(*_):
                    m = (mode.get() or "").strip().lower()
                    if m == "random":
                        _set_widget_state(ent_min, "normal")
                        _set_widget_state(ent_max, "normal")
                        _set_widget_state(ent_fixed, "disabled")
                    elif m == "custom":
                        _set_widget_state(ent_min, "disabled")
                        _set_widget_state(ent_max, "disabled")
                        _set_widget_state(ent_fixed, "normal")
                    else:
                        _set_widget_state(ent_min, "disabled")
                        _set_widget_state(ent_max, "disabled")
                        _set_widget_state(ent_fixed, "disabled")
                try:
                    mode.trace_add("write", _sync)
                except Exception:
                    pass
                _sync()
                return fixed, vmin, vmax
            def _row_date(parent, r, label, key):
                ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=4)
                mode = _mode_strip(parent, r, key)
                v = tk.StringVar(value="")
                vars_store[f"{key}_var"] = v
                di = self._make_date_input(parent, v)
                di.grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=4)
                def _sync(*_):
                    _apply_mode(mode, [di.entry, di.button])
                try:
                    mode.trace_add("write", _sync)
                except Exception:
                    pass
                _sync()
                return v

            def _row_combo(parent, r, label, key, values=()):
                ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=4)
                mode = _mode_strip(parent, r, key)
                v = tk.StringVar(value="")
                vars_store[f"{key}_var"] = v
                cb = ttk.Combobox(parent, textvariable=v, values=list(values), state="normal")
                cb.grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=4)
                def _sync(*_):
                    if (mode.get() or "") == "custom":
                        _set_widget_state(cb, "readonly")
                    else:
                        _set_widget_state(cb, "disabled")
                try:
                    mode.trace_add("write", _sync)
                except Exception:
                    pass
                _sync()
                return v

            def _row_contract_club(parent, r):
                ttk.Label(parent, text="Club").grid(row=r, column=0, sticky="w", padx=(8, 6), pady=4)
                key = "club_contract_club"
                mode = _mode_strip(parent, r, key)
                v = tk.StringVar(value="")
                vars_store[f"{key}_var"] = v

                wrap = ttk.Frame(parent)
                wrap.grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=4)
                wrap.columnconfigure(0, weight=1)

                cb = ttk.Combobox(wrap, textvariable=v, state="normal")
                cb.grid(row=0, column=0, sticky="ew")
                ttk.Label(wrap, text="Club filter").grid(row=0, column=1, sticky="w", padx=(12, 6))
                filt = tk.StringVar(value="Any")
                filt_cb = ttk.Combobox(wrap, textvariable=filt, values=["Any", "Men", "Women"], state="normal", width=10)
                filt_cb.grid(row=0, column=2, sticky="w")

                setattr(self, f"{prefix}_contract_club_combo", cb)
                setattr(self, f"{prefix}_contract_club_sel", v)
                setattr(self, f"{prefix}_contract_club_gender_filter", filt)

                def _sync(*_):
                    m = (mode.get() or "").strip().lower()
                    if m == "custom":
                        _set_widget_state(cb, "readonly")
                        _set_widget_state(filt_cb, "readonly")
                    elif m == "random":
                        _set_widget_state(cb, "disabled")
                        _set_widget_state(filt_cb, "readonly")
                    else:
                        _set_widget_state(cb, "disabled")
                        _set_widget_state(filt_cb, "disabled")
                try:
                    mode.trace_add("write", _sync)
                except Exception:
                    pass

                def _refresh_contract_club(_event=None):
                    try:
                        self._apply_club_filter(f"{prefix}_contract")
                    except Exception:
                        try:
                            cb.configure(values=list(getattr(self, "_club_labels_all", []) or []))
                        except Exception:
                            pass
                try:
                    filt_cb.bind("<<ComboboxSelected>>", _refresh_contract_club)
                except Exception:
                    pass
                _refresh_contract_club()
                _sync()
                return v

            def _row_check(parent, r, label, key, with_value=False, value_label="Value"):
                ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=4)
                mode = _mode_strip(parent, r, key)
                v = tk.BooleanVar(value=False)
                vars_store[f"{key}_var"] = v
                controls = ttk.Frame(parent)
                controls.grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=2)
                controls.columnconfigure(0, weight=0)
                controls.columnconfigure(1, weight=1)
                chk = ttk.Checkbutton(controls, text="Enabled", variable=v)
                chk.grid(row=0, column=0, sticky="w")
                value_widgets = []
                if with_value:
                    vv = tk.StringVar(value="")
                    vars_store[f"{key}_value"] = vv
                    inner = ttk.Frame(controls)
                    inner.grid(row=0, column=1, sticky="ew", padx=(12, 0))
                    inner.columnconfigure(1, weight=1)
                    ttk.Label(inner, text=value_label).grid(row=0, column=0, sticky="w", padx=(0, 6))
                    ent = ttk.Entry(inner, textvariable=vv)
                    ent.grid(row=0, column=1, sticky="ew")
                    value_widgets.append(ent)

                def _sync(*_):
                    _apply_mode(mode, [chk] + value_widgets)
                    if (mode.get() or "not_set") == "not_set":
                        try:
                            v.set(False)
                        except Exception:
                            pass
                try:
                    mode.trace_add("write", _sync)
                except Exception:
                    pass
                _sync()
                return v

            def _row_dual_check(parent, r, label, key):
                ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=4)
                mode = _mode_strip(parent, r, key)
                v = tk.BooleanVar(value=False)
                vars_store[f"{key}_var"] = v
                box = ttk.Frame(parent)
                box.grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=2)
                box.columnconfigure(0, weight=0)
                chk = ttk.Checkbutton(box, variable=v)
                chk.grid(row=0, column=0, sticky="w")
                def _sync(*_):
                    _apply_mode(mode, [chk])
                    if (mode.get() or "not_set") == "not_set":
                        try:
                            v.set(False)
                        except Exception:
                            pass
                try:
                    mode.trace_add("write", _sync)
                except Exception:
                    pass
                _sync()
                return v

            def _list_placeholder(parent, title, columns, key=None):
                lf = ttk.LabelFrame(parent, text=title)
                lf.columnconfigure(0, weight=1)
                if key:
                    mode_row = ttk.Frame(lf)
                    mode_row.grid(row=0, column=0, sticky="w", padx=8, pady=(6, 2))
                    mode = tk.StringVar(value="not_set")
                    vars_store[f"{key}_mode"] = mode
                    ttk.Label(mode_row, text="Mode").pack(side="left", padx=(0, 8))
                    ttk.Radiobutton(mode_row, text="Random", value="random", variable=mode).pack(side="left", padx=(0, 4))
                    ttk.Radiobutton(mode_row, text="Custom", value="custom", variable=mode).pack(side="left", padx=(0, 4))
                    ttk.Radiobutton(mode_row, text="Don't set", value="not_set", variable=mode).pack(side="left")
                    toolbar_row = 1
                    hdr_row = 2
                    empty_row = 3
                else:
                    toolbar_row = 0
                    hdr_row = 1
                    empty_row = 2
                toolbar = ttk.Frame(lf)
                toolbar.grid(row=toolbar_row, column=0, sticky="ew", padx=8, pady=(6, 4))
                btns = []
                btn_labels = ["Add", "Duplicate", "Remove", "Copy", "Paste", "Clear", "Add Comment"]
                for i, bl in enumerate(btn_labels):
                    b = ttk.Button(toolbar, text=bl)
                    b.grid(row=0, column=i, padx=(0, 4), pady=2, sticky="w")
                    btns.append(b)
                hdr = ttk.Frame(lf)
                hdr.grid(row=hdr_row, column=0, sticky="ew", padx=8, pady=(4, 0))
                hdr_labels = []
                for i, c in enumerate(columns):
                    lbl = ttk.Label(hdr, text=c)
                    lbl.grid(row=0, column=i, sticky="w", padx=(0, 12))
                    hdr_labels.append(lbl)
                empty_lbl = ttk.Label(lf, text="0 items")
                empty_lbl.grid(row=empty_row, column=0, sticky="w", padx=8, pady=(6, 8))

                if key:
                    def _sync(*_):
                        m = (vars_store.get(f"{key}_mode").get() or "not_set")
                        enabled = (m == "custom")
                        for b in btns:
                            _set_widget_state(b, "normal" if enabled else "disabled")
                    try:
                        vars_store[f"{key}_mode"].trace_add("write", _sync)
                    except Exception:
                        pass
                    _sync()

                return lf

            # Core contract details
            core = _section(club_tab, "Club Contract")
            r = 0
            _row_contract_club(core, r); r += 1
            _row_combo(core, r, "Job", "club_contract_job", ["Player", "Coach", "Manager", "Staff"]); r += 1
            _row_combo(core, r, "Secondary Job", "club_contract_secondary_job", ["None", "Coach", "Manager", "Scout"]); r += 1
            _row_date(core, r, "Date Joined", "club_contract_date_joined"); r += 1
            _row_entry(core, r, "Based Nation", "club_contract_based_nation"); r += 1
            _row_date(core, r, "Date When Moved To Based Nation", "club_contract_moved_to_based_nation_date"); r += 1
            _row_date(core, r, "Date Last Contract Signed", "club_contract_last_contract_signed_date"); r += 1
            _row_date(core, r, "Contract Expires", "club_contract_expires_date"); r += 1
            _row_combo(core, r, "Contract Type", "club_contract_type", ["Full Time", "Part Time", "Youth", "Non-Contract"]); r += 1
            _row_wage(core, r, "Wage (per week)", "club_contract_wage_per_week"); r += 1
            _row_combo(core, r, "Squad Status", "club_contract_squad_status", [
                "", "Key Player", "Important Player", "Regular Starter", "Squad Player", "Fringe Player", "Emergency Backup"
            ]); r += 1
            _row_check(core, r, "On Rolling Contract", "club_contract_on_rolling_contract"); r += 1
            _row_date(core, r, "Forced Date For Initial Contract", "club_contract_forced_initial_contract_date"); r += 1
            _row_entry(core, r, "Squad Number", "club_contract_squad_number"); r += 1
            _row_entry(core, r, "Preferred Squad Number", "club_contract_preferred_squad_number"); r += 1

            # Contract bonuses (simple value fields)
            bonuses = _section(club_tab, "Contract Bonuses")
            bonus_fields = [
                ("Appearance Fee", "appearance_fee"),
                ("Goal Bonus", "goal_bonus"),
                ("Assist Bonus", "assist_bonus"),
                ("Clean Sheet Bonus", "clean_sheet_bonus"),
                ("International Cap Bonus", "international_cap_bonus"),
                ("Unused Substitute Fee", "unused_substitute_fee"),
            ]
            for r, (label, key) in enumerate(bonus_fields):
                _row_entry(bonuses, r, label, f"club_contract_bonus_{key}")

            # Contract clauses - list style placeholders from editor
            clauses_lists = _section(club_tab, "Contract Clauses (List-Type Bonuses)")
            clauses_lists.columnconfigure(0, weight=1)
            list_specs = [
                ("Wage After Reaching Club League Games", ["Wage (per week)", "Apps"], "club_contract_list_wage_after_league_games"),
                ("Wage After Reaching International Appearances", ["Wage (per week)", "International Apps"], "club_contract_list_wage_after_international_apps"),
                ("Seasonal Landmark Goal Bonus", ["Cash", "Goals"], "club_contract_list_seasonal_landmark_goal_bonus"),
                ("Seasonal Landmark Assist Bonus", ["Cash", "Assists"], "club_contract_list_seasonal_landmark_assist_bonus"),
                ("Seasonal Landmark Combined Goal And Assist Bonus", ["Cash", "Goals + Assists"], "club_contract_list_seasonal_landmark_combined_bonus"),
            ]
            for rr, (title, cols, lkey) in enumerate(list_specs):
                box = _list_placeholder(clauses_lists, title, cols, key=lkey)
                box.grid(row=rr, column=0, sticky="ew", padx=8, pady=(4, 6))

            # Contract clauses - checkbox + numeric/value fields
            clauses_values = _section(club_tab, "Contract Clauses (Value Fields)")
            value_clause_fields = [
                ("Yearly Wage Rise", "yearly_wage_rise"),
                ("Promotion Wage Rise", "promotion_wage_rise"),
                ("Top Division Promotion Wage Rise", "top_division_promotion_wage_rise"),
                ("Relegation Wage Drop", "relegation_wage_drop"),
                ("Top Division Relegation Wage Drop", "top_division_relegation_wage_drop"),
                ("Contract Extension After Promotion", "contract_extension_after_promotion"),
                ("One-Year Extension After League Games (Final Season)", "one_year_ext_after_league_games_final"),
                ("One-Year Extension After League Games (Promoted Final Season)", "one_year_ext_after_league_games_promoted_final"),
                ("One-Year Extension After League Games (Avoid Relegation Final Season)", "one_year_ext_after_league_games_avoid_relegation_final"),
                ("Optional Contract Extension By Club", "optional_contract_extension_by_club"),
                ("Minimum Fee Release Clause", "minimum_fee_release_clause"),
                ("Minimum Fee Release Clause (Foreign Clubs)", "minimum_fee_release_clause_foreign"),
                ("Minimum Fee Release Clause (Domestic Clubs)", "minimum_fee_release_clause_domestic"),
                ("Minimum Fee Release Clause (Domestic Clubs in Higher Division)", "minimum_fee_release_clause_domestic_higher_div"),
                ("Minimum Fee Release Clause (Clubs in a Continental Competition)", "minimum_fee_release_clause_continental"),
                ("Minimum Fee Release Clause (Clubs in a Major Continental Competition)", "minimum_fee_release_clause_major_continental"),
                ("Relegation Release Clause", "relegation_release_clause"),
                ("Non Promotion Release Clause", "non_promotion_release_clause"),
                ("Sell On Fee Percentage", "sell_on_fee_percentage"),
                ("Sell On Fee Profit Percentage", "sell_on_fee_profit_percentage"),
                ("Percentage Of Club Compensation Required For Managerial Role", "managerial_role_compensation_percentage"),
            ]
            rv = 0
            for label, key in value_clause_fields:
                _row_check(clauses_values, rv, label, f"club_contract_clause_{key}", with_value=True, value_label="Value")
                rv += 1

            # Contract clauses - boolean toggles
            clauses_flags = _section(club_tab, "Contract Clauses (Flags)")
            flag_clause_fields = [
                ("Match Highest Earner Clause", "match_highest_earner_clause"),
                ("Injury Release Clause", "injury_release_clause"),
                ("Non-Playing Job Offer Release Clause", "non_playing_job_offer_release_clause"),
                ("Waive Club Compensation For Managerial Role", "waive_club_comp_for_managerial_role"),
                ("Will Leave At End Of Contract", "will_leave_at_end_of_contract"),
                ("Will Explore Options At End Of Contract", "will_explore_options_at_end_of_contract"),
            ]
            for rr, (label, key) in enumerate(flag_clause_fields):
                _row_dual_check(clauses_flags, rr, label, f"club_contract_flag_{key}")

            # Competition bonuses / awards placeholders (visible in screenshots)
            comp_bonuses = _section(club_tab, "Competition Bonuses")
            comp_bonuses.columnconfigure(0, weight=1)
            comp_tbl = _list_placeholder(
                comp_bonuses, "Competition Bonuses",
                ["Competition", "Ranking", "Stage Name", "Sub-Stage Name", "Cash"],
                key="club_contract_competition_bonuses"
            )
            comp_tbl.grid(row=0, column=0, sticky="ew", padx=8, pady=(4, 6))
            awards_tbl = _list_placeholder(comp_bonuses, "Awards", ["Award", "Cash"], key="club_contract_awards")
            awards_tbl.grid(row=1, column=0, sticky="ew", padx=8, pady=(4, 8))

            # Placeholder "Club" section marker (seen below in screenshots)
            club_misc = _section(club_tab, "Club")
            ttk.Label(
                club_misc,
                text="Further Club-related contract fields can be added here next (UI scaffold placeholder).",
                justify="left",
                foreground="#444",
            ).grid(row=0, column=0, columnspan=3, sticky="w", padx=8, pady=8)

            # ---------- Other tabs (placeholder scaffold) ----------
            for key in ("loan", "past_transfers", "future_transfer"):
                label = dict(tab_defs)[key]
                tab = tabs[key]
                box = ttk.LabelFrame(tab, text=label)
                box.grid(row=0, column=0, sticky="ew", padx=6, pady=6)
                box.columnconfigure(1, weight=1)
                ttk.Label(box, text="Status").grid(row=0, column=0, sticky="w", padx=8, pady=6)
                ttk.Label(box, text="Scaffolded (UI placeholder)", foreground="#444").grid(row=0, column=1, sticky="w", padx=8, pady=6)
                ttk.Label(box, text="Next").grid(row=1, column=0, sticky="w", padx=8, pady=6)
                ttk.Label(
                    box,
                    text=f"Wire {label.lower()} fields + XML output/omit support when you’re ready.",
                    foreground="#444",
                    wraplength=900,
                    justify="left",
                ).grid(row=1, column=1, sticky="w", padx=8, pady=6)

    def _build_batch_contract_tab(self) -> None:
        self._build_contract_tab_common(self.batch_contract_body, prefix="batch", mode_label="Batch")

    def _build_single_contract_tab(self) -> None:
        self._build_contract_tab_common(self.single_contract_body, prefix="single", mode_label="Single Person")
