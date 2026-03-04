from __future__ import annotations




from ui.tooltips import _attach_tooltip

from ui.player_constants import ALL_POS

from ui.defaults import DEFAULT_GENERATE_SCRIPT

from ui.name_paths import _preferred_name_csv_path

# -*- coding: utf-8 -*-

import os
import sys
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class BatchTabUIMixin:
    def _build_batch_tab(self) -> None:
        frm = self.batch_body
        frm.columnconfigure(1, weight=1)

        self.batch_clubs = tk.StringVar(value=str(self.fmdata_dir / "master_library.csv"))
        self.batch_first = tk.StringVar(value=_preferred_name_csv_path(self.fmdata_dir, "male_first_names"))
        self.batch_female_first = tk.StringVar(value=_preferred_name_csv_path(self.fmdata_dir, "female_first_names"))
        self.batch_common_names = tk.StringVar(value=_preferred_name_csv_path(self.fmdata_dir, "common_names"))
        self.batch_surn = tk.StringVar(value=_preferred_name_csv_path(self.fmdata_dir, "surnames"))
        self.batch_out = tk.StringVar(value=str(self.fmdata_dir / "fm26_players.xml"))
        self.batch_script = tk.StringVar(value=str(self.fmdata_dir / DEFAULT_GENERATE_SCRIPT))

        self.batch_count = tk.StringVar(value="1000")
        self.batch_seed = tk.StringVar(value="123")
        self.batch_base_year = tk.StringVar(value="2026")

        # Details (Random / Custom section vars are created by _add_details_section)

        self.batch_age_min = tk.StringVar(value="14")
        self.batch_age_max = tk.StringVar(value="16")
        self.batch_ca_min = tk.StringVar(value="20")
        self.batch_ca_max = tk.StringVar(value="160")
        self.batch_pa_min = tk.StringVar(value="80")
        self.batch_pa_max = tk.StringVar(value="200")
        self.batch_ca_dont_set = tk.BooleanVar(value=False)
        self.batch_pa_dont_set = tk.BooleanVar(value=False)

        # DOB mode
        self.batch_dob_mode = tk.StringVar(value="age")  # age|range|fixed (Age range controls moved to Details tab)
        self.batch_dob_fixed = tk.StringVar(value="2012-07-01")
        self.batch_dob_start = tk.StringVar(value="2010-01-01")
        self.batch_dob_end = tk.StringVar(value="2012-12-31")

        # XML date overrides (optional)
        self.batch_moved_to_nation_mode = tk.StringVar(value="dob")  # dob|fixed
        self.batch_moved_to_nation_date = tk.StringVar(value="")
        self.batch_joined_club_mode = tk.StringVar(value="auto")  # auto|fixed
        self.batch_joined_club_date = tk.StringVar(value="")
        self.batch_contract_expires_mode = tk.StringVar(value="auto")  # auto|fixed
        self.batch_contract_expires_date = tk.StringVar(value="")

        # Height
        self.batch_height_mode = tk.StringVar(value="range")  # range|fixed
        self.batch_height_min = tk.StringVar(value="150")
        self.batch_height_max = tk.StringVar(value="210")
        self.batch_height_fixed = tk.StringVar(value="")

        # Feet
        self.batch_feet_mode = tk.StringVar(value="random")
        self.batch_feet_dont_set = tk.BooleanVar(value=False)
        self.batch_feet_override = tk.BooleanVar(value=False)
        self.batch_left_foot = tk.StringVar(value="10")
        self.batch_right_foot = tk.StringVar(value="20")

        # Wage / Reputation / Transfer value
        self.batch_wage_mode = tk.StringVar(value="range")  # range|fixed
        self.batch_wage_dont_set = tk.BooleanVar(value=False)
        self.batch_wage_min = tk.StringVar(value="30")
        self.batch_wage_max = tk.StringVar(value="80")
        self.batch_wage_fixed = tk.StringVar(value="")

        self.batch_rep_mode = tk.StringVar(value="range")  # range|fixed
        self.batch_rep_dont_set = tk.BooleanVar(value=False)
        self.batch_rep_min = tk.StringVar(value="0")
        self.batch_rep_max = tk.StringVar(value="200")
        self.batch_rep_current = tk.StringVar(value="")
        self.batch_rep_home = tk.StringVar(value="")
        self.batch_rep_world = tk.StringVar(value="")

        self.batch_tv_mode = tk.StringVar(value="auto")  # auto|fixed|range
        self.batch_tv_dont_set = tk.BooleanVar(value=False)
        self.batch_tv_fixed = tk.StringVar(value="")
        self.batch_tv_min = tk.StringVar(value="")
        self.batch_tv_max = tk.StringVar(value="")

        # Auto-clear dont-set checkboxes when user edits the field
        self._autoclear_dontset(self.batch_ca_min, self.batch_ca_dont_set)
        self._autoclear_dontset(self.batch_ca_max, self.batch_ca_dont_set)
        self._autoclear_dontset(self.batch_pa_min, self.batch_pa_dont_set)
        self._autoclear_dontset(self.batch_pa_max, self.batch_pa_dont_set)
        self._autoclear_dontset(self.batch_feet_mode, self.batch_feet_dont_set)
        self._autoclear_dontset(self.batch_left_foot, self.batch_feet_dont_set)
        self._autoclear_dontset(self.batch_right_foot, self.batch_feet_dont_set)
        self._autoclear_dontset(self.batch_wage_mode, self.batch_wage_dont_set)
        self._autoclear_dontset(self.batch_wage_min, self.batch_wage_dont_set)
        self._autoclear_dontset(self.batch_wage_max, self.batch_wage_dont_set)
        self._autoclear_dontset(self.batch_rep_min, self.batch_rep_dont_set)
        self._autoclear_dontset(self.batch_rep_max, self.batch_rep_dont_set)
        self._autoclear_dontset(self.batch_tv_mode, self.batch_tv_dont_set)
        self._autoclear_dontset(self.batch_tv_min, self.batch_tv_dont_set)
        self._autoclear_dontset(self.batch_tv_max, self.batch_tv_dont_set)
        # Positions
        self.batch_positions_random = tk.BooleanVar(value=True)
        self.batch_positions_dont_set = tk.BooleanVar(value=False)
        self.batch_pos_vars: dict[str, tk.BooleanVar] = {p: tk.BooleanVar(value=False) for p in ALL_POS}

        # Development positions (extra positions added at 2..19)
        self.batch_dev_enable = tk.BooleanVar(value=True)
        self.batch_auto_dev_chance = tk.StringVar(value="15")  # percent (0..100)

        # Position distributions (used only when Random positions is ON)
        self.batch_dist_gk = tk.StringVar(value="15")
        self.batch_dist_def = tk.StringVar(value="35")
        self.batch_dist_mid = tk.StringVar(value="35")
        self.batch_dist_st = tk.StringVar(value="15")
        self.batch_n20_1 = tk.StringVar(value="39")
        self.batch_n20_2 = tk.StringVar(value="18")
        self.batch_n20_3 = tk.StringVar(value="13")
        self.batch_n20_4 = tk.StringVar(value="11")
        self.batch_n20_5 = tk.StringVar(value="8")
        self.batch_n20_6 = tk.StringVar(value="5.5")
        self.batch_n20_7 = tk.StringVar(value="3.6")
        self.batch_n20_8_12 = tk.StringVar(value="1.4")
        self.batch_n20_13 = tk.StringVar(value="0.5")
        self.batch_dev_mode = tk.StringVar(value="random")  # random|fixed|range
        self.batch_dev_fixed = tk.StringVar(value="10")
        self.batch_dev_min = tk.StringVar(value="2")
        self.batch_dev_max = tk.StringVar(value="19")

        # File inputs (hidden by default)
        self.batch_region_map_csv = tk.StringVar(value="")  # placeholder for future region mapping
        paths = ttk.LabelFrame(frm, text="File inputs")
        paths.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        paths.columnconfigure(1, weight=1)
        self.batch_paths_frame = paths
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

        opt = ttk.LabelFrame(frm, text="Batch options")
        opt.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 8))
        for c in range(6):
            opt.columnconfigure(c, weight=1)

        def opt_field(r, c, label, var, width=10):
            ttk.Label(opt, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=6)
            ttk.Entry(opt, textvariable=var, width=width).grid(row=r, column=c + 1, sticky="w", padx=6, pady=6)

        opt_field(0, 0, "Count", self.batch_count)
        opt_field(0, 2, "Seed", self.batch_seed)
        opt_field(0, 4, "Base year", self.batch_base_year)

        # Age min/max moved to Details tab (DOB block)
        opt_field(1, 0, "CA min", self.batch_ca_min)
        opt_field(1, 2, "CA max", self.batch_ca_max)
        opt_field(1, 4, "PA min", self.batch_pa_min)

        opt_field(2, 0, "PA max", self.batch_pa_max)

        btnrow = ttk.Frame(opt)
        btnrow.grid(row=3, column=0, columnspan=6, sticky="w", padx=6, pady=(0, 6))
        ttk.Checkbutton(btnrow, text="Don't set CA", variable=self.batch_ca_dont_set).grid(row=0, column=0, sticky="w", padx=(2, 12))
        ttk.Checkbutton(btnrow, text="Don't set PA", variable=self.batch_pa_dont_set).grid(row=0, column=1, sticky="w", padx=(2, 12))

        # Height + feet (shared builder)
        self._add_height_feet_section(
            frm,
            row=7,
            height_mode_var=self.batch_height_mode,
            height_min_var=self.batch_height_min,
            height_max_var=self.batch_height_max,
            height_fixed_var=self.batch_height_fixed,
            feet_mode_var=self.batch_feet_mode,
            feet_override_var=self.batch_feet_override,
            left_foot_var=self.batch_left_foot,
            right_foot_var=self.batch_right_foot,
            show_height=False,
            feet_none_var=self.batch_feet_dont_set,
        )

        # Wage + Reputation + Transfer Value
        money = ttk.LabelFrame(frm, text="Legacy Wage + Reputation + Transfer Value")
        money.grid(row=8, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(13):
            money.columnconfigure(c, weight=1)

        # Wage
        ttk.Label(money, text="Wage").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Random range", variable=self.batch_wage_mode, value="range").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Fixed", variable=self.batch_wage_mode, value="fixed").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Min").grid(row=0, column=3, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(money, text="Don't set", variable=self.batch_wage_dont_set).grid(row=0, column=10, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_wage_min, width=6).grid(row=0, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Max").grid(row=0, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_wage_max, width=6).grid(row=0, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Fixed").grid(row=0, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_wage_fixed, width=8).grid(row=0, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="(min wage 30)", foreground="#444").grid(row=0, column=9, sticky="w", padx=8, pady=6)

        # Wage has moved to the Contract tab; hide the legacy wage controls by default.
        for _w in money.grid_slaves(row=0):
            _w.grid_remove()

        # Reputation
        ttk.Label(money, text="Reputation (0–200)").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Random ordered", variable=self.batch_rep_mode, value="range").grid(row=1, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Fixed", variable=self.batch_rep_mode, value="fixed").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Range").grid(row=1, column=3, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(money, text="Don't set", variable=self.batch_rep_dont_set).grid(row=1, column=10, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_rep_min, width=6).grid(row=1, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="to").grid(row=1, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_rep_max, width=6).grid(row=1, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Current").grid(row=1, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_rep_current, width=6).grid(row=1, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Home").grid(row=2, column=7, sticky="w", padx=8, pady=4)
        ttk.Entry(money, textvariable=self.batch_rep_home, width=6).grid(row=2, column=8, sticky="w", padx=8, pady=4)
        ttk.Label(money, text="World").grid(row=3, column=7, sticky="w", padx=8, pady=4)
        ttk.Entry(money, textvariable=self.batch_rep_world, width=6).grid(row=3, column=8, sticky="w", padx=8, pady=4)
        ttk.Label(money, text="(enforced: current > home > world)", foreground="#444").grid(row=2, column=0, columnspan=7, sticky="w", padx=8, pady=(0, 6))

        # Transfer value
        ttk.Label(money, text="Transfer value").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Mode").grid(row=4, column=1, sticky="w", padx=8, pady=6)
        ttk.Combobox(money, textvariable=self.batch_tv_mode, values=["auto", "fixed", "range"], state="normal", width=10).grid(row=4, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Fixed").grid(row=4, column=4, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(money, text="Don't set", variable=self.batch_tv_dont_set).grid(row=4, column=11, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_tv_fixed, width=12).grid(row=4, column=5, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Range").grid(row=4, column=6, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_tv_min, width=12).grid(row=4, column=7, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="to").grid(row=4, column=8, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_tv_max, width=12).grid(row=4, column=9, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="(auto uses PA, max 150,000,000)", foreground="#444").grid(row=4, column=10, sticky="w", padx=(0, 4), pady=6)

        # Club / City / Nation selection
        sel = ttk.LabelFrame(frm, text="Club")
        sel.grid(row=9, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        sel.columnconfigure(3, weight=1)

        self.batch_club_mode = tk.StringVar(value="random")
        self.batch_club_dont_set = tk.BooleanVar(value=False)
        self.batch_city_mode = tk.StringVar(value="random")
        self.batch_nation_mode = tk.StringVar(value="random")

        self.batch_club_sel = tk.StringVar(value="")
        self.batch_city_sel = tk.StringVar(value="")
        self.batch_nation_sel = tk.StringVar(value="")

        ttk.Label(sel, text="Club (legacy - use Contract tab)").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        club_combo = ttk.Combobox(sel, textvariable=self.batch_club_sel, values=[], state="normal", width=55)
        club_combo.grid(row=0, column=3, sticky="ew", padx=8, pady=6)
        self.batch_club_combo = club_combo
        self.batch_club_gender_filter = tk.StringVar(value="Any")
        ttk.Label(sel, text="Club filter").grid(row=0, column=4, sticky="e", padx=(8, 4), pady=6)
        self.batch_club_filter_combo = ttk.Combobox(sel, textvariable=self.batch_club_gender_filter, values=["Any", "Male", "Female"], state="normal", width=8)
        self.batch_club_filter_combo.grid(row=0, column=5, sticky="w", padx=(0, 8), pady=6)
        self.batch_club_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_club_filter('batch'))
        ttk.Radiobutton(sel, text="Random", variable=self.batch_club_mode, value="random", command=lambda mv=self.batch_club_mode, cb=club_combo, ds=self.batch_club_dont_set: (ds.set(False), self._combo_state_for_mode(mv, cb))).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(sel, text="Fixed", variable=self.batch_club_mode, value="fixed", command=lambda mv=self.batch_club_mode, cb=club_combo, ds=self.batch_club_dont_set: (ds.set(False), self._combo_state_for_mode(mv, cb))).grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(sel, text="Don't set", variable=self.batch_club_dont_set).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 4))

        ttk.Button(sel, text="Reload from master_library.csv", command=self._reload_master_library).grid(row=2, column=0, columnspan=6, sticky="w", padx=8, pady=(4, 8))
        # Hide legacy Other-tab club selector; use Contract > Club Contract instead.
        try:
            sel.grid_remove()
        except Exception:
            pass


        # Positions
        pos = ttk.LabelFrame(frm, text="Positions")
        pos.grid(row=10, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        ttk.Checkbutton(pos, text="Random positions (ignore selections)", variable=self.batch_positions_random).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(pos, text="Don't set", variable=self.batch_positions_dont_set).grid(row=0, column=1, sticky="w", padx=8, pady=6)

        grid = ttk.Frame(pos)
        grid.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
        cols = 7
        for i, code in enumerate(ALL_POS):
            r = i // cols
            c = i % cols
            ttk.Checkbutton(grid, text=code, variable=self.batch_pos_vars[code]).grid(row=r, column=c, sticky="w", padx=6, pady=2)

        # --- Extra position controls (keeps existing behaviour, just adds options) ---

        def _batch_select_all_outfield():
            for k, v in self.batch_pos_vars.items():
                v.set(k != "GK")

        def _batch_clear_positions():
            for v in self.batch_pos_vars.values():
                v.set(False)

        tools = ttk.Frame(pos)
        tools.grid(row=1, column=2, columnspan=5, sticky="e", padx=8, pady=6)
        ttk.Button(tools, text="Select all outfield", command=_batch_select_all_outfield).pack(side="left", padx=(0, 6))
        ttk.Button(tools, text="Clear", command=_batch_clear_positions).pack(side="left")
        wf = ttk.LabelFrame(frm, text="Random position distribution (editable)")
        wf.grid(row=11, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(10):
            wf.columnconfigure(c, weight=1)

        ttk.Label(
            wf,
            text="Used ONLY when 'Random positions' is ON. Totals must equal 100%.",
            foreground="#444"
        ).grid(row=0, column=0, columnspan=10, sticky="w", padx=8, pady=(6, 2))

        ttk.Label(wf, text="Primary role split (%)").grid(row=1, column=0, columnspan=10, sticky="w", padx=8, pady=(0, 2))

        # # [PATCH TOOLTIP MORE v2b] label:wf:GK
        _lbl_GK = ttk.Label(wf, text='GK')
        _lbl_GK.grid(row=2, column=0, sticky="w", padx=8)
        _attach_tooltip(_lbl_GK, "Primary role split (%)\n\nUsed ONLY when 'Random positions' is ON.\nTotals across GK/DEF/MID/ST should equal 100%.")

        ttk.Entry(wf, textvariable=self.batch_dist_gk, width=6).grid(row=3, column=0, sticky="w", padx=8, pady=(0, 6))

        # # [PATCH TOOLTIP MORE v2b] label:wf:DEF
        _lbl_DEF = ttk.Label(wf, text='DEF')
        _lbl_DEF.grid(row=2, column=1, sticky="w", padx=8)
        _attach_tooltip(_lbl_DEF, "Primary role split (%)\n\nUsed ONLY when 'Random positions' is ON.\nTotals across GK/DEF/MID/ST should equal 100%.")

        ttk.Entry(wf, textvariable=self.batch_dist_def, width=6).grid(row=3, column=1, sticky="w", padx=8, pady=(0, 6))

        # # [PATCH TOOLTIP MORE v2b] label:wf:MID
        _lbl_MID = ttk.Label(wf, text='MID')
        _lbl_MID.grid(row=2, column=2, sticky="w", padx=8)
        _attach_tooltip(_lbl_MID, "Primary role split (%)\n\nUsed ONLY when 'Random positions' is ON.\nTotals across GK/DEF/MID/ST should equal 100%.")

        ttk.Entry(wf, textvariable=self.batch_dist_mid, width=6).grid(row=3, column=2, sticky="w", padx=8, pady=(0, 6))

        # # [PATCH TOOLTIP MORE v2b] label:wf:ST
        _lbl_ST = ttk.Label(wf, text='ST')
        _lbl_ST.grid(row=2, column=3, sticky="w", padx=8)
        _attach_tooltip(_lbl_ST, "Primary role split (%)\n\nUsed ONLY when 'Random positions' is ON.\nTotals across GK/DEF/MID/ST should equal 100%.")

        ttk.Entry(wf, textvariable=self.batch_dist_st, width=6).grid(row=3, column=3, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(wf, text="Outfield positions rated 20: chance (%)").grid(row=4, column=0, columnspan=10, sticky="w", padx=8, pady=(0, 2))

        headers = ["1","2","3","4","5","6","7","8–12","13"]
        vars_ = [
            self.batch_n20_1, self.batch_n20_2, self.batch_n20_3, self.batch_n20_4,
            self.batch_n20_5, self.batch_n20_6, self.batch_n20_7, self.batch_n20_8_12, self.batch_n20_13
        ]

        for i, h in enumerate(headers):
            ttk.Label(wf, text=h).grid(row=5, column=i, sticky="w", padx=8, pady=2)
        for i, v in enumerate(vars_):
            ttk.Entry(wf, textvariable=v, width=6).grid(row=6, column=i, sticky="w", padx=8, pady=(0, 6))

        def _reset_pos_dists():
            self.batch_dist_gk.set("15"); self.batch_dist_def.set("35"); self.batch_dist_mid.set("35"); self.batch_dist_st.set("15")
            self.batch_n20_1.set("39"); self.batch_n20_2.set("18"); self.batch_n20_3.set("13"); self.batch_n20_4.set("11")
            self.batch_n20_5.set("8"); self.batch_n20_6.set("5.5"); self.batch_n20_7.set("3.6"); self.batch_n20_8_12.set("1.4"); self.batch_n20_13.set("0.5")

        ttk.Button(wf, text="Reset defaults", command=_reset_pos_dists).grid(row=7, column=0, sticky="w", padx=8, pady=(0, 6))

# Development positions (2..19) - auto-selected by generator for multi-position profiles
        dev = ttk.LabelFrame(frm, text="Development positions (2–19)")
        dev.grid(row=12, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(8):
            dev.columnconfigure(c, weight=1)

        ttk.Checkbutton(
            dev,
            text="Enable dev positions (auto-picked; applies only to multi-position players)",
            variable=self.batch_dev_enable
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=8, pady=(6, 4))

        ttk.Label(dev, text="Chance (%)").grid(row=0, column=5, sticky="w", padx=8, pady=(6, 4))
        ttk.Entry(dev, textvariable=self.batch_auto_dev_chance, width=5).grid(row=0, column=6, sticky="w", padx=8, pady=(6, 4))

        ttk.Label(dev, text="Mode").grid(row=1, column=0, sticky="w", padx=8, pady=2)
        # # [PATCH TOOLTIP MORE v2] combobox:batch_dev_mode
        _w_batch_dev_mode = ttk.Combobox(dev, textvariable=self.batch_dev_mode, values=["random", "fixed", "range"], width=8, state="normal"
        )
        _w_batch_dev_mode.grid(row=1, column=1, sticky="w", padx=8, pady=2)
        _attach_tooltip(_w_batch_dev_mode, 'Dev positions mode\n\nrandom: choose extra positions randomly.\nfixed: always use Fixed.\nrange: choose a random number between Min and Max.')

        ttk.Label(dev, text="Fixed").grid(row=1, column=2, sticky="w", padx=8, pady=2)
        # # [PATCH TOOLTIP MORE v2] batch_dev_fixed
        _w_batch_dev_fixed = ttk.Entry(dev, textvariable=self.batch_dev_fixed, width=5)
        _w_batch_dev_fixed.grid(row=1, column=3, sticky="w", padx=8, pady=2)
        _attach_tooltip(_w_batch_dev_fixed, 'Dev positions: Fixed\n\nUsed when Mode=fixed.\nNumber of extra positions to add (2..19).')

        ttk.Label(dev, text="Min").grid(row=1, column=4, sticky="w", padx=8, pady=2)
        # # [PATCH TOOLTIP MORE v2] batch_dev_min
        _w_batch_dev_min = ttk.Entry(dev, textvariable=self.batch_dev_min, width=5)
        _w_batch_dev_min.grid(row=1, column=5, sticky="w", padx=8, pady=2)
        _attach_tooltip(_w_batch_dev_min, 'Dev positions: Min\n\nUsed when Mode=range.\nMinimum extra positions to add (2..19).')

        ttk.Label(dev, text="Max").grid(row=1, column=6, sticky="w", padx=8, pady=2)
        # # [PATCH TOOLTIP MORE v2] batch_dev_max
        _w_batch_dev_max = ttk.Entry(dev, textvariable=self.batch_dev_max, width=5)
        _w_batch_dev_max.grid(row=1, column=7, sticky="w", padx=8, pady=2)
        _attach_tooltip(_w_batch_dev_max, 'Dev positions: Max\n\nUsed when Mode=range.\nMaximum extra positions to add (2..19).')

        ttk.Label(
            dev,
            text="Note: If GK is primary, all other positions are forced to 1 (dev ignored). If outfield: GK stays 1.",
            foreground="#444"
        ).grid(row=2, column=0, columnspan=8, sticky="w", padx=8, pady=(0, 6))



    # ---------------- Players (Single) UI ----------------

