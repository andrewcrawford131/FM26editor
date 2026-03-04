from __future__ import annotations



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


class SingleTabUIMixin:
    def _build_single_tab(self) -> None:
        frm = self.single_body
        frm.columnconfigure(1, weight=1)

        self.single_clubs = tk.StringVar(value=str(self.fmdata_dir / "master_library.csv"))
        self.single_first = tk.StringVar(value=_preferred_name_csv_path(self.fmdata_dir, "male_first_names"))
        self.single_female_first = tk.StringVar(value=_preferred_name_csv_path(self.fmdata_dir, "female_first_names"))
        self.single_common_names = tk.StringVar(value=_preferred_name_csv_path(self.fmdata_dir, "common_names"))
        self.single_surn = tk.StringVar(value=_preferred_name_csv_path(self.fmdata_dir, "surnames"))
        self.single_out = tk.StringVar(value=str(self.fmdata_dir / "fm26_single_player.xml"))
        self.single_script = tk.StringVar(value=str(self.fmdata_dir / DEFAULT_GENERATE_SCRIPT))

        self.single_seed = tk.StringVar(value="123")
        self.single_base_year = tk.StringVar(value="2026")

        self.single_dob_mode = tk.StringVar(value="age")  # age|dob
        self.single_age = tk.StringVar(value="14")
        self.single_dob = tk.StringVar(value="2012-07-01")
        self.single_age_preview = tk.StringVar(value="Age (from DOB): 14")

        # XML date overrides (optional)
        self.single_moved_to_nation_mode = tk.StringVar(value="dob")  # dob|fixed
        self.single_moved_to_nation_date = tk.StringVar(value="")
        self.single_joined_club_mode = tk.StringVar(value="auto")  # auto|fixed
        self.single_joined_club_date = tk.StringVar(value="")
        self.single_contract_expires_mode = tk.StringVar(value="auto")  # auto|fixed
        self.single_contract_expires_date = tk.StringVar(value="")

        self.single_ca = tk.StringVar(value="120")
        self.single_pa = tk.StringVar(value="170")
        self.single_ca_dont_set = tk.BooleanVar(value=False)
        self.single_pa_dont_set = tk.BooleanVar(value=False)
        # Optional single-player CA/PA range overrides (leave blank to use fixed CA/PA above)
        self.single_ca_min = tk.StringVar(value="")
        self.single_ca_max = tk.StringVar(value="")
        self.single_pa_min = tk.StringVar(value="")
        self.single_pa_max = tk.StringVar(value="")

        self.single_height_mode = tk.StringVar(value="range")  # range|fixed
        self.single_height_min = tk.StringVar(value="150")
        self.single_height_max = tk.StringVar(value="210")
        self.single_height_fixed = tk.StringVar(value="")

        self.single_feet_mode = tk.StringVar(value="random")
        self.single_feet_dont_set = tk.BooleanVar(value=False)
        self.single_feet_override = tk.BooleanVar(value=False)
        self.single_left_foot = tk.StringVar(value="10")
        self.single_right_foot = tk.StringVar(value="20")

        self.single_wage_mode = tk.StringVar(value="range")
        self.single_wage_dont_set = tk.BooleanVar(value=False)
        self.single_wage_min = tk.StringVar(value="30")
        self.single_wage_max = tk.StringVar(value="80")
        self.single_wage_fixed = tk.StringVar(value="")

        self.single_rep_mode = tk.StringVar(value="range")
        self.single_rep_dont_set = tk.BooleanVar(value=False)
        self.single_rep_min = tk.StringVar(value="0")
        self.single_rep_max = tk.StringVar(value="200")
        self.single_rep_current = tk.StringVar(value="")
        self.single_rep_home = tk.StringVar(value="")
        self.single_rep_world = tk.StringVar(value="")

        self.single_tv_mode = tk.StringVar(value="auto")
        self.single_tv_dont_set = tk.BooleanVar(value=False)
        self.single_tv_fixed = tk.StringVar(value="")
        self.single_tv_min = tk.StringVar(value="")
        self.single_tv_max = tk.StringVar(value="")

        # Auto-clear dont-set checkboxes when user edits the field
        self._autoclear_dontset(self.single_ca_min, self.single_ca_dont_set)
        self._autoclear_dontset(self.single_ca_max, self.single_ca_dont_set)
        self._autoclear_dontset(self.single_pa_min, self.single_pa_dont_set)
        self._autoclear_dontset(self.single_pa_max, self.single_pa_dont_set)
        self._autoclear_dontset(self.single_feet_mode, self.single_feet_dont_set)
        self._autoclear_dontset(self.single_left_foot, self.single_feet_dont_set)
        self._autoclear_dontset(self.single_right_foot, self.single_feet_dont_set)
        self._autoclear_dontset(self.single_wage_mode, self.single_wage_dont_set)
        self._autoclear_dontset(self.single_wage_min, self.single_wage_dont_set)
        self._autoclear_dontset(self.single_wage_max, self.single_wage_dont_set)
        self._autoclear_dontset(self.single_rep_min, self.single_rep_dont_set)
        self._autoclear_dontset(self.single_rep_max, self.single_rep_dont_set)
        self._autoclear_dontset(self.single_tv_mode, self.single_tv_dont_set)
        self._autoclear_dontset(self.single_tv_min, self.single_tv_dont_set)
        self._autoclear_dontset(self.single_tv_max, self.single_tv_dont_set)
        self.single_positions_random = tk.BooleanVar(value=True)
        self.single_positions_dont_set = tk.BooleanVar(value=False)
        self.single_pos_vars: dict[str, tk.BooleanVar] = {p: tk.BooleanVar(value=False) for p in ALL_POS}

        # Development positions (extra positions added at 2..19)
        self.single_dev_enable = tk.BooleanVar(value=True)
        self.single_auto_dev_chance = tk.StringVar(value="15")  # percent (0..100)
        self.single_dev_mode = tk.StringVar(value="random")  # random|fixed|range
        self.single_dev_fixed = tk.StringVar(value="10")
        self.single_dev_min = tk.StringVar(value="2")
        self.single_dev_max = tk.StringVar(value="19")

        # File inputs (hidden by default)
        self.single_region_map_csv = tk.StringVar(value="")  # placeholder for future region mapping
        paths = ttk.LabelFrame(frm, text="File inputs")
        paths.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        paths.columnconfigure(1, weight=1)
        self.single_paths_frame = paths
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

        opt = ttk.LabelFrame(frm, text="Single player (fixed values)")
        opt.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 8))
        for c in range(8):
            opt.columnconfigure(c, weight=1)

        ttk.Label(opt, text="Seed").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_seed, width=10).grid(row=0, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(opt, text="Base year").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_base_year, width=10).grid(row=0, column=3, sticky="w", padx=6, pady=6)

        ttk.Label(opt, text="CA").grid(row=0, column=4, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_ca, width=10).grid(row=0, column=5, sticky="w", padx=6, pady=6)

        ttk.Label(opt, text="PA").grid(row=0, column=6, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_pa, width=10).grid(row=0, column=7, sticky="w", padx=6, pady=6)

        ttk.Separator(opt, orient="horizontal").grid(row=1, column=0, columnspan=8, sticky="ew", padx=6, pady=(2, 2))
        ttk.Label(opt, text="Single-player CA/PA range (optional)").grid(row=2, column=0, columnspan=8, sticky="w", padx=6, pady=(2, 0))
        ttk.Label(opt, text="CA min").grid(row=3, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_ca_min, width=10).grid(row=3, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(opt, text="CA max").grid(row=3, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_ca_max, width=10).grid(row=3, column=3, sticky="w", padx=6, pady=6)
        ttk.Label(opt, text="PA min").grid(row=3, column=4, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_pa_min, width=10).grid(row=3, column=5, sticky="w", padx=6, pady=6)
        ttk.Label(opt, text="PA max").grid(row=3, column=6, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_pa_max, width=10).grid(row=3, column=7, sticky="w", padx=6, pady=6)

        btnrow = ttk.Frame(opt)
        btnrow.grid(row=4, column=0, columnspan=8, sticky="w", padx=6, pady=(0, 6))
        ttk.Checkbutton(btnrow, text="Don't set CA", variable=self.single_ca_dont_set).grid(row=0, column=0, sticky="w", padx=(2, 12))
        ttk.Checkbutton(btnrow, text="Don't set PA", variable=self.single_pa_dont_set).grid(row=0, column=1, sticky="w", padx=(2, 12))

        # Height + feet (shared builder)
        self._add_height_feet_section(
            frm,
            row=7,
            height_mode_var=self.single_height_mode,
            height_min_var=self.single_height_min,
            height_max_var=self.single_height_max,
            height_fixed_var=self.single_height_fixed,
            feet_mode_var=self.single_feet_mode,
            feet_override_var=self.single_feet_override,
            left_foot_var=self.single_left_foot,
            right_foot_var=self.single_right_foot,
            show_height=False,
            feet_none_var=self.single_feet_dont_set,
        )

        # Wage + Reputation + Transfer Value
        money = ttk.LabelFrame(frm, text="Legacy Wage + Reputation + Transfer Value")
        money.grid(row=8, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(13):
            money.columnconfigure(c, weight=1)

        ttk.Label(money, text="Wage").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Random range", variable=self.single_wage_mode, value="range").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Fixed", variable=self.single_wage_mode, value="fixed").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Min").grid(row=0, column=3, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(money, text="Don't set", variable=self.single_wage_dont_set).grid(row=0, column=10, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_wage_min, width=6).grid(row=0, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Max").grid(row=0, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_wage_max, width=6).grid(row=0, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Fixed").grid(row=0, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_wage_fixed, width=8).grid(row=0, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="(min wage 30)", foreground="#444").grid(row=0, column=9, sticky="w", padx=8, pady=6)

        ttk.Label(money, text="Reputation (0–200)").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Random ordered", variable=self.single_rep_mode, value="range").grid(row=1, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Fixed", variable=self.single_rep_mode, value="fixed").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Range").grid(row=1, column=3, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(money, text="Don't set", variable=self.single_rep_dont_set).grid(row=1, column=10, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_rep_min, width=6).grid(row=1, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="to").grid(row=1, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_rep_max, width=6).grid(row=1, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Current").grid(row=1, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_rep_current, width=6).grid(row=1, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Home").grid(row=2, column=7, sticky="w", padx=8, pady=4)
        ttk.Entry(money, textvariable=self.single_rep_home, width=6).grid(row=2, column=8, sticky="w", padx=8, pady=4)
        ttk.Label(money, text="World").grid(row=3, column=7, sticky="w", padx=8, pady=4)
        ttk.Entry(money, textvariable=self.single_rep_world, width=6).grid(row=3, column=8, sticky="w", padx=8, pady=4)
        ttk.Label(money, text="(enforced: current > home > world)", foreground="#444").grid(row=2, column=0, columnspan=7, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(money, text="Transfer value").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Mode").grid(row=4, column=1, sticky="w", padx=8, pady=6)
        ttk.Combobox(money, textvariable=self.single_tv_mode, values=["auto", "fixed", "range"], state="normal", width=10).grid(row=4, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Fixed").grid(row=4, column=4, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(money, text="Don't set", variable=self.single_tv_dont_set).grid(row=4, column=11, columnspan=2, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_tv_fixed, width=12).grid(row=4, column=5, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Range").grid(row=4, column=6, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_tv_min, width=12).grid(row=4, column=7, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="to").grid(row=4, column=8, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_tv_max, width=12).grid(row=4, column=9, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="(auto uses PA, max 150,000,000)", foreground="#444").grid(row=4, column=10, sticky="w", padx=(0, 4), pady=6)

        # Club / City / Nation selection
        sel = ttk.LabelFrame(frm, text="Club")
        sel.grid(row=9, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        sel.columnconfigure(3, weight=1)

        self.single_club_mode = tk.StringVar(value="random")
        self.single_club_dont_set = tk.BooleanVar(value=False)
        self.single_city_mode = tk.StringVar(value="random")
        self.single_nation_mode = tk.StringVar(value="random")

        self.single_club_sel = tk.StringVar(value="")
        self.single_city_sel = tk.StringVar(value="")
        self.single_nation_sel = tk.StringVar(value="")

        ttk.Label(sel, text="Club (legacy - use Contract tab)").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        club_combo = ttk.Combobox(sel, textvariable=self.single_club_sel, values=[], state="normal", width=55)
        club_combo.grid(row=0, column=3, sticky="ew", padx=8, pady=6)
        self.single_club_combo = club_combo
        self.single_club_gender_filter = tk.StringVar(value="Any")
        ttk.Label(sel, text="Club filter").grid(row=0, column=4, sticky="e", padx=(8, 4), pady=6)
        self.single_club_filter_combo = ttk.Combobox(sel, textvariable=self.single_club_gender_filter, values=["Any", "Male", "Female"], state="normal", width=8)
        self.single_club_filter_combo.grid(row=0, column=5, sticky="w", padx=(0, 8), pady=6)
        self.single_club_filter_combo.bind("<<ComboboxSelected>>", lambda e: self._apply_club_filter('single'))
        ttk.Radiobutton(sel, text="Random", variable=self.single_club_mode, value="random", command=lambda mv=self.single_club_mode, cb=club_combo, ds=self.single_club_dont_set: (ds.set(False), self._combo_state_for_mode(mv, cb))).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(sel, text="Fixed", variable=self.single_club_mode, value="fixed", command=lambda mv=self.single_club_mode, cb=club_combo, ds=self.single_club_dont_set: (ds.set(False), self._combo_state_for_mode(mv, cb))).grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(sel, text="Don't set", variable=self.single_club_dont_set).grid(row=1, column=1, sticky="w", padx=8, pady=(0, 4))

        ttk.Button(sel, text="Reload from master_library.csv", command=self._reload_master_library).grid(row=2, column=0, columnspan=6, sticky="w", padx=8, pady=(4, 8))
        # Hide legacy Other-tab club selector; use Contract > Club Contract instead.
        try:
            sel.grid_remove()
        except Exception:
            pass


        # Positions
        pos = ttk.LabelFrame(frm, text="Positions")
        pos.grid(row=10, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        ttk.Checkbutton(pos, text="Random positions (ignore selections)", variable=self.single_positions_random).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(pos, text="Don't set", variable=self.single_positions_dont_set).grid(row=0, column=1, sticky="w", padx=8, pady=6)

        grid = ttk.Frame(pos)
        grid.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
        cols = 7
        for i, code in enumerate(ALL_POS):
            r = i // cols
            c = i % cols
            ttk.Checkbutton(grid, text=code, variable=self.single_pos_vars[code]).grid(row=r, column=c, sticky="w", padx=6, pady=2)

        # --- Extra position controls (keeps existing behaviour, just adds options) ---

        def _single_select_all_outfield():
            for k, v in self.single_pos_vars.items():
                v.set(k != "GK")

        def _single_clear_positions():
            for v in self.single_pos_vars.values():
                v.set(False)

        pos.columnconfigure(0, weight=1)

        tools = ttk.Frame(pos)
        tools.grid(row=2, column=0, sticky="e", padx=8, pady=(0, 6))
        ttk.Button(tools, text="Select all outfield", command=_single_select_all_outfield).pack(side="left", padx=(0, 6))
        ttk.Button(tools, text="Clear", command=_single_clear_positions).pack(side="left")
        wf = ttk.LabelFrame(frm, text="Random position distribution (fixed)")
        wf.grid(row=11, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(10):
            wf.columnconfigure(c, weight=1)

        ttk.Label(
            wf,
            text="Primary role split (%): GK 15 | DEF 35 | MID 35 | ST 15",
            foreground="#444"
        ).grid(row=0, column=0, columnspan=10, sticky="w", padx=8, pady=(6, 2))

        ttk.Label(wf, text="Outfield positions rated 20: chance (%)").grid(row=1, column=0, columnspan=10, sticky="w", padx=8, pady=(0, 4))

        headers = ["1","2","3","4","5","6","7","8–12","13"]
        values  = ["39","18","13","11","8","5.5","3.6","1.4","0.5"]

        for i, h in enumerate(headers):
            ttk.Label(wf, text=h).grid(row=2, column=i, sticky="w", padx=8, pady=2)
        for i, v in enumerate(values):
            ttk.Label(wf, text=v).grid(row=3, column=i, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(
            wf,
            text="Note: Distribution is built into fm26_bulk_youth_generator4.py (not editable here).",
            foreground="#444"
        ).grid(row=4, column=0, columnspan=10, sticky="w", padx=8, pady=(0, 6))
        # Development positions (2..19) - auto-selected by generator for multi-position profiles
        dev = ttk.LabelFrame(frm, text="Development positions (2–19)")
        dev.grid(row=12, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(8):
            dev.columnconfigure(c, weight=1)

        ttk.Checkbutton(
            dev,
            text="Enable dev positions (auto-picked; applies only to multi-position players)",
            variable=self.single_dev_enable
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=8, pady=(6, 4))

        ttk.Label(dev, text="Chance (%)").grid(row=0, column=5, sticky="w", padx=8, pady=(6, 4))
        ttk.Entry(dev, textvariable=self.single_auto_dev_chance, width=5).grid(row=0, column=6, sticky="w", padx=8, pady=(6, 4))

        ttk.Label(dev, text="Mode").grid(row=1, column=0, sticky="w", padx=8, pady=2)
        ttk.Combobox(
            dev, textvariable=self.single_dev_mode, values=["random", "fixed", "range"], width=8, state="normal"
        ).grid(row=1, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(dev, text="Fixed").grid(row=1, column=2, sticky="w", padx=8, pady=2)
        ttk.Entry(dev, textvariable=self.single_dev_fixed, width=5).grid(row=1, column=3, sticky="w", padx=8, pady=2)
        ttk.Label(dev, text="Min").grid(row=1, column=4, sticky="w", padx=8, pady=2)
        ttk.Entry(dev, textvariable=self.single_dev_min, width=5).grid(row=1, column=5, sticky="w", padx=8, pady=2)
        ttk.Label(dev, text="Max").grid(row=1, column=6, sticky="w", padx=8, pady=2)
        ttk.Entry(dev, textvariable=self.single_dev_max, width=5).grid(row=1, column=7, sticky="w", padx=8, pady=2)

        ttk.Label(
            dev,
            text="Note: If GK is primary, all other positions are forced to 1 (dev ignored). If outfield: GK stays 1.",
            foreground="#444"
        ).grid(row=2, column=0, columnspan=8, sticky="w", padx=8, pady=(0, 6))

