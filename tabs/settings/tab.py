# -*- coding: utf-8 -*-
# Auto-generated from fm26_generator_gui_2.py
# Settings tab extracted into a mixin.


from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

# --- helper bridge (import from main GUI when available) ---
try:
    from __main__ import _bind_help, _attach_tooltip  # type: ignore
except Exception:
    def _bind_help(*_a, **_k):
        return
    def _attach_tooltip(*_a, **_k):
        return
# --- end helper bridge ---




class SettingsTabMixin:
    def _build_settings_tab(self) -> None:
        """Top-level Settings tab (global knobs). Uses existing tk variables so everything stays in sync."""
        try:
            frm = getattr(self, "settings_tab", None)
            if frm is None:
                return
            if getattr(self, "_settings_tab_built", False):
                return
            self._settings_tab_built = True

            frm.columnconfigure(0, weight=1)

            if not hasattr(self, "settings_club_assign_pct"):
                self.settings_club_assign_pct = tk.StringVar(value="50")  # % assigned to fixed club (players); rest free agents

            if not hasattr(self, "settings_name_local_bias"):
                self.settings_name_local_bias = tk.StringVar(value="85")
            if not hasattr(self, "settings_female_pct"):
                self.settings_female_pct = tk.StringVar(value="50")

            if not hasattr(self, "settings_extra_nation_pct"):
                self.settings_extra_nation_pct = tk.StringVar(value="5")
            if not hasattr(self, "settings_extra_nation_third_given_second_pct"):
                self.settings_extra_nation_third_given_second_pct = tk.StringVar(value="30")
            if not hasattr(self, "settings_extra_nation_fourth_given_third_pct"):
                self.settings_extra_nation_fourth_given_third_pct = tk.StringVar(value="33.333")
            if not hasattr(self, "settings_extra_nation_fifthplus_given_fourth_pct"):
                self.settings_extra_nation_fifthplus_given_fourth_pct = tk.StringVar(value="10")
            if not hasattr(self, "settings_extra_nation_chain_pct"):
                self.settings_extra_nation_chain_pct = tk.StringVar(value="20")
            if not hasattr(self, "settings_extra_nation_max"):
                self.settings_extra_nation_max = tk.StringVar(value="8")

            if not hasattr(self, "settings_appearance_mode"):
                self.settings_appearance_mode = tk.StringVar(value="nation")
            if not hasattr(self, "settings_appearance_global_ethnicity"):
                self.settings_appearance_global_ethnicity = tk.StringVar(value="0-10")
            if not hasattr(self, "settings_appearance_global_skin"):
                self.settings_appearance_global_skin = tk.StringVar(value="0-19")
            if not hasattr(self, "settings_appearance_global_hair_colour"):
                self.settings_appearance_global_hair_colour = tk.StringVar(value="0-6")
            if not hasattr(self, "settings_hair_length_weights_male"):
                self.settings_hair_length_weights_male = tk.StringVar(value="36,40,18,6")
            if not hasattr(self, "settings_hair_length_weights_female"):
                self.settings_hair_length_weights_female = tk.StringVar(value="8,20,34,38")
            if not hasattr(self, "settings_body_type_weights"):
                self.settings_body_type_weights = tk.StringVar(value="95,4,1")

            if not hasattr(self, "settings_intl_play_prob_mult"):
                self.settings_intl_play_prob_mult = tk.StringVar(value="1.0")
            if not hasattr(self, "settings_intl_opponent_mode"):
                self.settings_intl_opponent_mode = tk.StringVar(value="random")
            if not hasattr(self, "settings_intl_opponent_similarity"):
                self.settings_intl_opponent_similarity = tk.StringVar(value="0.75")



            gen = ttk.LabelFrame(frm, text="Generation Defaults")
            gen.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 8))
            for c in range(8):
                gen.columnconfigure(c, weight=1)

            ttk.Label(gen, text="Batch count").grid(row=0, column=0, sticky="w", padx=6, pady=6)
            _e_bc = ttk.Entry(gen, textvariable=self.batch_count, width=10)
            _e_bc.grid(row=0, column=1, sticky="w", padx=6, pady=6)
            _bind_help(_e_bc, "Batch count: how many people to generate. Example: 1000.")
            ttk.Label(gen, text="Seed").grid(row=0, column=2, sticky="w", padx=6, pady=6)
            _e_seed = ttk.Entry(gen, textvariable=self.batch_seed, width=10)
            _e_seed.grid(row=0, column=3, sticky="w", padx=6, pady=6)
            _bind_help(_e_seed, "Seed: makes generation reproducible. Same seed + same settings = same output.")
            ttk.Label(gen, text="Base year").grid(row=0, column=4, sticky="w", padx=6, pady=6)
            _e_year = ttk.Entry(gen, textvariable=self.batch_base_year, width=10)
            _e_year.grid(row=0, column=5, sticky="w", padx=6, pady=6)
            _bind_help(_e_year, "Base year: used when dates are Auto (contracts/international). Example: 2026.")
            ttk.Label(gen, text="Club assign % (random/fixed)").grid(row=0, column=6, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_club_assign_pct
            _w = ttk.Entry(gen, textvariable=self.settings_club_assign_pct, width=8)
            _w.grid(row=0, column=7, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, "Club assign % (random/fixed)\n\n0 = everyone is a free agent.\n80 = ~80% get a club record, ~20% free agents.\n100 = everyone has a club.\n\nThis only applies when Club is not 'Don't set'.")

            # [PATCH GUI SETTINGS PACK v3a] extra settings fields
            ttk.Label(gen, text="Name local bias %").grid(row=1, column=0, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_name_local_bias
            _w = ttk.Entry(gen, textvariable=self.settings_name_local_bias, width=10)
            _w.grid(row=1, column=1, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, "Name local bias %\n\nControls how often the name matches the player's PRIMARY nation when both local+foreign name rows exist.\n85 = ~85% local names, ~15% foreign.\n0 = always foreign.\n100 = always local.")

            ttk.Label(gen, text="Female % (random)").grid(row=1, column=2, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_female_pct
            _w = ttk.Entry(gen, textvariable=self.settings_female_pct, width=10)
            _w.grid(row=1, column=3, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Female % (random)\n\nWhen gender is NOT fixed, this is the probability of female.\n50 = even split.\n70 = ~70% female, ~30% male.')

            ttk.Label(gen, text="Extra nation %").grid(row=2, column=0, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_extra_nation_pct
            _w = ttk.Entry(gen, textvariable=self.settings_extra_nation_pct, width=10)
            _w.grid(row=2, column=1, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Extra nationality %\n\nChance a person has at least ONE extra nationality.\n5 = ~95% primary-only, ~5% have a 2nd nationality.\nThis then feeds the 3rd/4th/5+ chain probabilities.')

            ttk.Label(gen, text="3rd|2nd %").grid(row=2, column=2, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_extra_nation_third_given_second_pct
            _w = ttk.Entry(gen, textvariable=self.settings_extra_nation_third_given_second_pct, width=10)
            _w.grid(row=2, column=3, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, '3rd | 2nd (%)\n\nIf a person has a 2nd nationality, chance to also have a 3rd.\nExample: 30 = 30% of those with a 2nd also get a 3rd.')

            ttk.Label(gen, text="4th|3rd %").grid(row=2, column=4, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_extra_nation_fourth_given_third_pct
            _w = ttk.Entry(gen, textvariable=self.settings_extra_nation_fourth_given_third_pct, width=10)
            _w.grid(row=2, column=5, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, '4th | 3rd (%)\n\nIf a person has a 3rd nationality, chance to also have a 4th.')

            ttk.Label(gen, text="5+|4th %").grid(row=2, column=6, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_extra_nation_fifthplus_given_fourth_pct
            _w = ttk.Entry(gen, textvariable=self.settings_extra_nation_fifthplus_given_fourth_pct, width=10)
            _w.grid(row=2, column=7, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, '5+ | 4th (%)\n\nIf a person reaches a 4th nationality, chance to continue into 5+ total.\nChain % controls whether 6th/7th/... are added.')

            ttk.Label(gen, text="Chain %").grid(row=3, column=0, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_extra_nation_chain_pct
            _w = ttk.Entry(gen, textvariable=self.settings_extra_nation_chain_pct, width=10)
            _w.grid(row=3, column=1, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Chain (%)\n\nAfter reaching 5+ total, this is the chance to add EACH additional extra nationality until Max extra is reached.\nHigher = more extreme multi-national cases.')

            ttk.Label(gen, text="Max extra").grid(row=3, column=2, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_extra_nation_max
            _w = ttk.Entry(gen, textvariable=self.settings_extra_nation_max, width=10)
            _w.grid(row=3, column=3, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Max extra\n\nMaximum number of extra nationalities beyond primary.\n8 means up to 9 total nationalities (primary + 8 extras).')

            ttk.Label(gen, text="Appearance mode").grid(row=4, column=0, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_appearance_mode
            _w = ttk.Entry(gen, textvariable=self.settings_appearance_mode, width=10)
            _w.grid(row=4, column=1, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Appearance mode\n\nnation = use your per-nation appearance profile mapping.\nglobal = force the SAME ranges for everyone using the global ranges below.')

            ttk.Label(gen, text="Eth range").grid(row=4, column=2, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_appearance_global_ethnicity
            _w = ttk.Entry(gen, textvariable=self.settings_appearance_global_ethnicity, width=10)
            _w.grid(row=4, column=3, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Global ethnicity range (min-max)\n\nUsed only when appearance mode = global.\nFormat: 0-10\nWider ranges = more variety.')

            ttk.Label(gen, text="Skin range").grid(row=4, column=4, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_appearance_global_skin
            _w = ttk.Entry(gen, textvariable=self.settings_appearance_global_skin, width=10)
            _w.grid(row=4, column=5, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Global skin range (min-max)\n\nUsed only when appearance mode = global.\nFormat: 0-19')

            ttk.Label(gen, text="Hair range").grid(row=4, column=6, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_appearance_global_hair_colour
            _w = ttk.Entry(gen, textvariable=self.settings_appearance_global_hair_colour, width=10)
            _w.grid(row=4, column=7, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Global hair colour range (min-max)\n\nUsed only when appearance mode = global.\nFormat: 0-6')

            ttk.Label(gen, text="Hair w male").grid(row=5, column=0, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_hair_length_weights_male
            _w = ttk.Entry(gen, textvariable=self.settings_hair_length_weights_male, width=14)
            _w.grid(row=5, column=1, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Male hair length weights\n\nComma weights for hair length indexes [0,1,2,3].\nBigger weight = more common.\nExample: 36,40,18,6 means length 0/1 dominate.')

            ttk.Label(gen, text="Hair w female").grid(row=5, column=2, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_hair_length_weights_female
            _w = ttk.Entry(gen, textvariable=self.settings_hair_length_weights_female, width=14)
            _w.grid(row=5, column=3, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Female hair length weights\n\nComma weights for hair length indexes [0,1,2,3].')

            ttk.Label(gen, text="Body w").grid(row=5, column=4, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_body_type_weights
            _w = ttk.Entry(gen, textvariable=self.settings_body_type_weights, width=14)
            _w.grid(row=5, column=5, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'Body type weights\n\nThree numbers: weights for [types 1-3 group, type 4, type 5].\nExample: 95,4,1 means most are 1-3, few are 4, rare are 5.')

            ttk.Label(gen, text="Intl prob x").grid(row=6, column=0, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_intl_play_prob_mult
            _w = ttk.Entry(gen, textvariable=self.settings_intl_play_prob_mult, width=10)
            _w.grid(row=6, column=1, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'International probability multiplier\n\nMultiplies the auto-international selection probability.\n1.0 = default.\n2.0 = roughly twice as many internationals.\n0.5 = roughly half.')

            ttk.Label(gen, text="Intl opp mode").grid(row=6, column=2, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_intl_opponent_mode
            _w = ttk.Entry(gen, textvariable=self.settings_intl_opponent_mode, width=10)
            _w.grid(row=6, column=3, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'International opponent mode\n\nrandom = uniform random opponent.\nsimilar = prefer opponents of similar strength (controlled by similarity).')

            ttk.Label(gen, text="Intl opp sim").grid(row=6, column=4, sticky="w", padx=6, pady=6)
            # # [PATCH TOOLTIP SETTINGS v1] settings_intl_opponent_similarity
            _w = ttk.Entry(gen, textvariable=self.settings_intl_opponent_similarity, width=10)
            _w.grid(row=6, column=5, sticky="w", padx=6, pady=6)
            _attach_tooltip(_w, 'International opponent similarity (0..1)\n\nOnly used when mode = similar.\n0 = weak preference.\n1 = strong preference for similar-strength opponents.')

            # Keep Single seed/base-year in sync with Batch
            def _sync_seed(*_):
                try:
                    if hasattr(self, "single_seed") and self.single_seed.get() != self.batch_seed.get():
                        self.single_seed.set(self.batch_seed.get())
                except Exception:
                    pass
            def _sync_year(*_):
                try:
                    if hasattr(self, "single_base_year") and self.single_base_year.get() != self.batch_base_year.get():
                        self.single_base_year.set(self.batch_base_year.get())
                except Exception:
                    pass
            try:
                self.batch_seed.trace_add("write", _sync_seed)
                self.batch_base_year.trace_add("write", _sync_year)
            except Exception:
                pass

            pos = ttk.LabelFrame(frm, text="Positions (Random distribution + development)")
            pos.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
            for c in range(11):
                pos.columnconfigure(c, weight=1)

            ttk.Label(pos, text="Primary dist (GK/DEF/MID/ST %)").grid(row=0, column=0, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_dist_gk, width=6).grid(row=0, column=1, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_dist_def, width=6).grid(row=0, column=2, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_dist_mid, width=6).grid(row=0, column=3, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_dist_st, width=6).grid(row=0, column=4, sticky="w", padx=6, pady=6)

            ttk.Label(pos, text="N@20 dist (1,2,3,4,5,6,7,8-12,13)").grid(row=1, column=0, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_n20_1, width=6).grid(row=1, column=1, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_n20_2, width=6).grid(row=1, column=2, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_n20_3, width=6).grid(row=1, column=3, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_n20_4, width=6).grid(row=1, column=4, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_n20_5, width=6).grid(row=1, column=5, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_n20_6, width=6).grid(row=1, column=6, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_n20_7, width=6).grid(row=1, column=7, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_n20_8_12, width=6).grid(row=1, column=8, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_n20_13, width=6).grid(row=1, column=9, sticky="w", padx=6, pady=6)

            ttk.Checkbutton(pos, text="Enable dev positions", variable=self.batch_dev_enable).grid(row=2, column=0, sticky="w", padx=6, pady=6)
            ttk.Label(pos, text="Auto dev chance %").grid(row=2, column=1, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_auto_dev_chance, width=6).grid(row=2, column=2, sticky="w", padx=6, pady=6)

            ttk.Label(pos, text="Dev mode").grid(row=2, column=3, sticky="w", padx=6, pady=6)
            ttk.Combobox(pos, textvariable=self.batch_dev_mode, values=["random","fixed","range"], state="normal", width=10).grid(row=2, column=4, sticky="w", padx=6, pady=6)
            ttk.Label(pos, text="Fixed").grid(row=2, column=5, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_dev_fixed, width=6).grid(row=2, column=6, sticky="w", padx=6, pady=6)
            ttk.Label(pos, text="Min").grid(row=2, column=7, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_dev_min, width=6).grid(row=2, column=8, sticky="w", padx=6, pady=6)
            ttk.Label(pos, text="Max").grid(row=2, column=9, sticky="w", padx=6, pady=6)
            ttk.Entry(pos, textvariable=self.batch_dev_max, width=6).grid(row=2, column=10, sticky="w", padx=6, pady=6)

            ttk.Label(frm, text="Tip: Position settings affect Batch only when 'Random positions' is enabled.", foreground="#444").grid(
                row=2, column=0, sticky="w", padx=12, pady=(0, 10)
            )
        except Exception:
            pass

