from ui.cli_utils import _quote
from ui.path_utils import ensure_parent_dir

def _run_batch_generator(self) -> None:
    extra: list[str] = []
    # Player tab: force person type = 2 (player) in generator builds that support it
    extra.extend(["--person_type_value", "2"])

    # DOB (supports legacy batch modes + Details-tab shared mode values)
    mode = (self.batch_dob_mode.get() or "age").strip().lower()
    if mode == "none":
        extra.extend(["--omit-field", "dob"])
    elif mode == "fixed":
        d = self.batch_dob_fixed.get().strip()
        if not d:
            messagebox.showerror("Fixed DOB missing", "Fixed DOB is selected, but the date is blank.")
            return
        extra.extend(["--dob", d])
    elif mode in ("range", "dob"):  # "dob" kept for compatibility with earlier shared Details patch
        ds = self.batch_dob_start.get().strip()
        de = self.batch_dob_end.get().strip()
        if not ds or not de:
            messagebox.showerror("DOB range missing", "Please set both DOB Start and DOB End (YYYY-MM-DD).")
            return
        extra.extend(["--dob_start", ds, "--dob_end", de])

    self._apply_contract_tab_generation_overrides("batch", extra)
    self._append_international_cli_args(extra, "batch")
    # XML date overrides (optional)
    if self.batch_moved_to_nation_mode.get() == "fixed":
        d = self.batch_moved_to_nation_date.get().strip()
        if not d:
            messagebox.showerror("Date moved to nation missing", "Fixed Date moved to nation is selected, but the date is blank.")
            return
        extra.extend(["--moved_to_nation_date", d])

    if self.batch_joined_club_mode.get() == "fixed":
        d = self.batch_joined_club_date.get().strip()
        if not d:
            messagebox.showerror("Date joined club missing", "Fixed Date joined club is selected, but the date is blank.")
            return
        extra.extend(["--joined_club_date", d])

    if self.batch_contract_expires_mode.get() == "fixed":
        d = self.batch_contract_expires_date.get().strip()
        if not d:
            messagebox.showerror("Contract expires missing", "Fixed Contract expires is selected, but the date is blank.")
            return
        extra.extend(["--contract_expires_date", d])

    # Height
    _batch_height_mode = (self.batch_height_mode.get() or "random").strip().lower()
    if _batch_height_mode == "none":
        extra.extend(["--omit-field", "height"])
    elif _batch_height_mode == "fixed":
        h = self.batch_height_fixed.get().strip()
        if not h:
            messagebox.showerror("Height missing", "Fixed height selected, but Height is blank.")
            return
        extra.extend(["--height", h])
    else:
        extra.extend(["--height_min", self.batch_height_min.get().strip(), "--height_max", self.batch_height_max.get().strip()])

    # Feet
    if self.batch_feet_dont_set.get():
        extra.extend(["--omit-field", "feet"])
    else:
        extra.extend(["--feet", (self.batch_feet_mode.get().strip() or "random")])
        if self.batch_feet_override.get():
            lf = self.batch_left_foot.get().strip()
            rf = self.batch_right_foot.get().strip()
            if not lf or not rf:
                messagebox.showerror("Feet missing", "Override feet is ticked, but Left/Right values are blank.")
                return
            extra.extend(["--left_foot", lf, "--right_foot", rf])

    # Club/City/Nation fixed selections
    if self.batch_club_dont_set.get():
        extra.extend(["--omit-field", "club"])
    elif self.batch_club_mode.get() == "fixed":
        sel = self.batch_club_sel.get().strip()
        ids = self._get_fixed_ids("club", sel)
        if not ids:
            messagebox.showerror("Club missing", "Fixed Club is selected, but no club is chosen.")
            return
        extra.extend(["--club_dbid", ids[0], "--club_large", ids[1]])

    if self.batch_city_mode.get() == "fixed":
        sel = self.batch_city_sel.get().strip()
        ids = self._get_fixed_ids("city", sel)
        if not ids:
            messagebox.showerror("City missing", "Fixed City is selected, but no city is chosen.")
            return
        extra.extend(["--city_dbid", ids[0], "--city_large", ids[1]])

    if self.batch_nation_mode.get() == "fixed":
        sel = self.batch_nation_sel.get().strip()
        ids = self._get_fixed_ids("nation", sel)
        if not ids:
            messagebox.showerror("Nation missing", "Fixed Nation is selected, but no nation is chosen.")
            return
        extra.extend(["--nation_dbid", ids[0], "--nation_large", ids[1]])

    # Positions
    if self.batch_positions_dont_set.get():
        extra.extend(["--omit-field", "positions"])
        extra.extend(["--auto_dev_chance", "0"])
    elif self.batch_positions_random.get():
        # RANDOM positions: validate + pass editable distributions
        def _f(name: str, s: str) -> float:
            try:
                return float(s)
            except Exception:
                raise ValueError(f"{name} must be a number")

        try:
            gk = _f("GK %", self.batch_dist_gk.get().strip())
            de = _f("DEF %", self.batch_dist_def.get().strip())
            mi = _f("MID %", self.batch_dist_mid.get().strip())
            st = _f("ST %", self.batch_dist_st.get().strip())
            total = gk + de + mi + st
            if abs(total - 100.0) > 0.001:
                diff = 100.0 - total
                messagebox.showerror(
                    "Primary role split must total 100%",
                    f"Your GK/DEF/MID/ST totals {total:.3f}%. Difference: {diff:+.3f}%."
                )
                return

            n20_vals = [
                _f("N20(1)", self.batch_n20_1.get().strip()),
                _f("N20(2)", self.batch_n20_2.get().strip()),
                _f("N20(3)", self.batch_n20_3.get().strip()),
                _f("N20(4)", self.batch_n20_4.get().strip()),
                _f("N20(5)", self.batch_n20_5.get().strip()),
                _f("N20(6)", self.batch_n20_6.get().strip()),
                _f("N20(7)", self.batch_n20_7.get().strip()),
                _f("N20(8–12)", self.batch_n20_8_12.get().strip()),
                _f("N20(13)", self.batch_n20_13.get().strip()),
            ]
            total2 = sum(n20_vals)
            if abs(total2 - 100.0) > 0.001:
                diff2 = 100.0 - total2
                messagebox.showerror(
                    "N20 distribution must total 100%",
                    f"Your 1..7, 8–12, 13 totals {total2:.3f}%. Difference: {diff2:+.3f}%."
                )
                return
        except ValueError as e:
            messagebox.showerror("Invalid distribution value", str(e))
            return

        extra.extend(["--positions", "RANDOM"])
        extra.extend(["--pos_primary_dist", f"{gk},{de},{mi},{st}"])
        extra.extend(["--pos_n20_dist", ",".join([str(x) for x in n20_vals])])

        # Dev positions chance (auto-picked by generator)
        if self.batch_dev_enable.get():
            extra.extend(["--auto_dev_chance", (self.batch_auto_dev_chance.get().strip() or "0")])
        else:
            extra.extend(["--auto_dev_chance", "0"])
    else:
        sel = [code for code, v in self.batch_pos_vars.items() if v.get()]
        if not sel:
            messagebox.showerror("Positions missing", "Please select at least one position, or tick Random positions.")
            return
        if "GK" in sel and len(sel) > 1:
            messagebox.showerror("Invalid selection", "GK cannot be combined with outfield positions.")
            return

        primary = sel[0]
        extras = sel[1:]
        extra.extend(["--pos_primary", primary])
        if extras:
            extra.extend(["--pos_20", ",".join(extras)])

        # Manual profiles currently do not use auto dev chance; keep at 0
        extra.extend(["--auto_dev_chance", "0"])
    # Development positions (auto-picked by generator v4)
    mode = (self.batch_dev_mode.get() or "random").strip().lower()
    if mode not in ("random", "fixed", "range"):
        mode = "random"
    extra.extend(["--pos_dev_mode", mode])

    if mode == "fixed":
        try:
            v = int((self.batch_dev_fixed.get() or "10").strip())
        except Exception:
            messagebox.showerror("Dev value", "Dev fixed value must be an integer (2..19).")
            return
        extra.extend(["--pos_dev_value", str(v)])
    elif mode == "range":
        try:
            mn = int((self.batch_dev_min.get() or "2").strip())
            mx = int((self.batch_dev_max.get() or "19").strip())
        except Exception:
            messagebox.showerror("Dev range", "Dev min/max must be integers (2..19).")
            return
        extra.extend(["--pos_dev_min", str(mn), "--pos_dev_max", str(mx)])
    # Wage
    if self.batch_wage_dont_set.get():
        extra.extend(["--omit-field", "wage"])
    elif self.batch_wage_mode.get() == "fixed":
        w = self.batch_wage_fixed.get().strip()
        if not w:
            messagebox.showerror("Wage missing", "Fixed wage selected, but Wage is blank.")
            return
        extra.extend(["--wage", w])
    else:
        extra.extend(["--wage_min", self.batch_wage_min.get().strip(), "--wage_max", self.batch_wage_max.get().strip()])

    # Reputation
    if self.batch_rep_dont_set.get():
        extra.extend(["--omit-field", "reputation"])
    elif self.batch_rep_mode.get() == "fixed":
        rc = self.batch_rep_current.get().strip()
        rh = self.batch_rep_home.get().strip()
        rw = self.batch_rep_world.get().strip()
        if not rc or not rh or not rw:
            messagebox.showerror("Reputation missing", "Fixed reputation selected, but Current/Home/World are not all set.")
            return
        extra.extend(["--rep_current", rc, "--rep_home", rh, "--rep_world", rw])
    else:
        extra.extend(["--rep_min", self.batch_rep_min.get().strip(), "--rep_max", self.batch_rep_max.get().strip()])

    # Transfer value
    if self.batch_tv_dont_set.get():
        extra.extend(["--omit-field", "transfer_value"])
    else:
        tv_mode = self.batch_tv_mode.get().strip() or "auto"
        extra.extend(["--transfer_mode", tv_mode])
        if tv_mode == "fixed":
            tv = self.batch_tv_fixed.get().strip()
            if not tv:
                messagebox.showerror("Transfer value missing", "Transfer value mode is Fixed, but value is blank.")
                return
            extra.extend(["--transfer_value", tv])
        elif tv_mode == "range":
            tmin = self.batch_tv_min.get().strip()
            tmax = self.batch_tv_max.get().strip()
            if not tmin or not tmax:
                messagebox.showerror("Transfer value missing", "Transfer mode is Range, but min/max are blank.")
                return
            extra.extend(["--transfer_min", tmin, "--transfer_max", tmax])

    # Details section (supported exports + UI-ready placeholders)
    try:
        if self.batch_details_first_name_mode.get() == "custom" and self.batch_details_first_name_value.get().strip():
            extra.extend(["--first_name_text", self.batch_details_first_name_value.get().strip()])
        if self.batch_details_second_name_mode.get() == "custom" and self.batch_details_second_name_value.get().strip():
            extra.extend(["--second_name_text", self.batch_details_second_name_value.get().strip()])
        if self.batch_details_common_name_mode.get() == "custom" and self.batch_details_common_name_value.get().strip():
            extra.extend(["--common_name_text", self.batch_details_common_name_value.get().strip()])
        if self.batch_details_full_name_mode.get() == "custom" and self.batch_details_full_name_value.get().strip():
            extra.extend(["--full_name_text", self.batch_details_full_name_value.get().strip()])

        if self.batch_details_gender_mode.get() == "custom":
            gval = self.batch_details_gender_value.get().strip()
            if gval:
                try:
                    gv = self._details_gender_to_int(gval)
                except Exception as e:
                    messagebox.showerror("Gender", str(e))
                    return
                if gv is not None:
                    extra.extend(["--gender_value", str(gv)])

        if self.batch_details_ethnicity_mode.get() == "custom":
            eval_ = self.batch_details_ethnicity_value.get().strip()
            if eval_:
                try:
                    ev = self._details_ethnicity_to_int(eval_)
                except Exception as e:
                    messagebox.showerror("Ethnicity", str(e))
                    return
                if ev is not None:
                    extra.extend(["--ethnicity_value", str(ev)])

        # Primary nationality info (Details tab)
        _nat_info_added = False
        try:
            if self.batch_details_nationality_info_mode.get() == "custom":
                ni_label = self.batch_details_nationality_info_value.get().strip()
                if ni_label:
                    extra.extend(["--nationality_info", ni_label])
                    _nat_info_added = True
        except Exception:
            pass

        # International Data tab (custom values only)
        self._append_international_data_cli_args(extra, "batch")

        # Second Nations metadata export (editor values first, then first row as fallback)
        # NOTE: do NOT override the primary Details Nationality Info unless it is blank.
        try:
            _sn_editor_ni = (getattr(self, "batch_second_nations_nationality_info").get() or "").strip() if hasattr(self, "batch_second_nations_nationality_info") else ""
            _sn_editor_int_ret = bool(getattr(self, "batch_second_nations_international_retirement").get()) if hasattr(self, "batch_second_nations_international_retirement") else False
            _sn_editor_date = (getattr(self, "batch_second_nations_international_retirement_date").get() or "").strip() if hasattr(self, "batch_second_nations_international_retirement_date") else ""
            _sn_editor_retire_spell = bool(getattr(self, "batch_second_nations_retiring_after_spell_current_club").get()) if hasattr(self, "batch_second_nations_retiring_after_spell_current_club") else False

            _sn_items = list(getattr(self, "batch_second_nations_items", []) or [])
            _sn0 = dict(_sn_items[0] or {}) if _sn_items else {}

            # Export repeatable second nation list entries (nation + optional per-entry nationality info)
            for _sn in _sn_items:
                try:
                    _sn_nation = (dict(_sn or {}).get("nation") or "").strip()
                    if not _sn_nation:
                        continue
                    _sn_ni_item = (dict(_sn or {}).get("nationality_info") or "").strip()
                    _sn_spec = _sn_nation
                    if _sn_ni_item:
                        # Pass label through; generator resolves labels/numbers to FM ntin values
                        _sn_spec = f"{_sn_spec}|{_sn_ni_item}"
                    extra.extend(["--second_nation", _sn_spec])
                except Exception:
                    pass


            _sn_ni = _sn_editor_ni or (_sn0.get("nationality_info") or "").strip()
            if _sn_ni and not _nat_info_added and _sn_ni.lower() != "no info":
                extra.extend(["--nationality_info", _sn_ni])

            if _sn_editor_int_ret or bool(_sn0.get("international_retirement", False)):
                extra.append("--international_retirement")

            _sn_date = _sn_editor_date or (_sn0.get("international_retirement_date") or "").strip()
            if _sn_date:
                extra.extend(["--international_retirement_date", _sn_date])

            if _sn_editor_retire_spell or bool(_sn0.get("retiring_after_spell_current_club", False)):
                extra.append("--retiring_after_spell_current_club")
            try:
                _dy_mode = (getattr(self, "batch_details_declared_for_youth_nation_mode").get() or "random").strip().lower() if hasattr(self, "batch_details_declared_for_youth_nation_mode") else "random"
                _dy_sel = (getattr(self, "batch_details_declared_for_youth_nation_value").get() or "").strip() if hasattr(self, "batch_details_declared_for_youth_nation_value") else ""
                if _dy_mode == "custom" and _dy_sel:
                    extra.extend(["--declared_for_youth_nation", _dy_sel])
            except Exception:
                pass
        except Exception:
            pass

        if self.batch_ca_dont_set.get():
            extra.extend(["--omit-field", "ca"])
        if self.batch_pa_dont_set.get():
            extra.extend(["--omit-field", "pa"])
        self._append_details_dontset_cli_args(extra, "batch")

        if self.batch_details_date_of_birth_mode.get() == "custom":
            d = self.batch_details_date_of_birth_value.get().strip()
            if d:
                extra.extend(["--dob", d])
        elif self.batch_details_date_of_birth_mode.get() == "none":
            extra.extend(["--omit-field", "dob"])

        # Prefer new Details > Height block (range/fixed), fallback to legacy custom single-value height field
        details_height_handled = False
        try:
            h_mode2 = (self.batch_details_height_mode2.get() if hasattr(self, "batch_details_height_mode2") else "").strip()
            if h_mode2 == "none":
                details_height_handled = True
            elif h_mode2 == "fixed":
                h = self.batch_details_height_fixed.get().strip()
                if h:
                    extra.extend(["--height", h])
                    details_height_handled = True
            elif h_mode2 == "range":
                hmin = self.batch_details_height_min.get().strip()
                hmax = self.batch_details_height_max.get().strip()
                if hmin and hmax:
                    extra.extend(["--height_min", hmin, "--height_max", hmax])
                    details_height_handled = True
        except Exception:
            pass

        if (not details_height_handled) and self.batch_details_height_mode.get() == "custom":
            h = self.batch_details_height_value.get().strip()
            if h:
                extra.extend(["--height", h])

        if self.batch_details_city_of_birth_mode.get() == "custom":
            sel = self.batch_details_city_of_birth_value.get().strip()
            if sel:
                ids = self._get_fixed_ids("city", sel)
                if ids:
                    extra.extend(["--city_dbid", ids[0], "--city_large", ids[1]])
                else:
                    messagebox.showerror("City Of Birth", "Custom City Of Birth must be selected from the master_library city list.")
                    return

    except Exception:
        pass

    _batch_age_min_arg = self.batch_age_min.get().strip()
    _batch_age_max_arg = self.batch_age_max.get().strip()
    try:
        if (self.batch_dob_mode.get() or "age").strip().lower() == "none":
            _batch_age_min_arg = ""
            _batch_age_max_arg = ""
    except Exception:
        pass

    # [PATCH v20] DETAILS NATION FORCE-INJECT

    try:

        n_mode = (getattr(self, "batch_details_nation_mode").get() or "none").strip().lower()

        n_val  = (getattr(self, "batch_details_nation_value").get() or "").strip()

        print(f"[DEBUG v20] Batch Details Nation: mode={n_mode} value={n_val!r}")

        if n_mode == "custom" and n_val and "--nation_dbid" not in extra:

            ids = self._get_fixed_ids("nation", n_val)

            if ids:

                extra.extend(["--nation_dbid", ids[0], "--nation_large", ids[1]])

                print(f"[DEBUG v20] Batch injected nation -> DBID {ids[0]} LARGE {ids[1]}")

            else:

                messagebox.showerror("Nation", "Custom Nation must be selected from the master_library nation list.")

                return

    except Exception as e:

        print(f"[DEBUG v20] Batch nation inject error: {e}")



        # [PATCH v8] club_assign_pct from Settings (default 50)
        def _omitted(_field: str) -> bool:
            try:
                i = 0
                while i < len(extra) - 1:
                    if extra[i] == "--omit-field" and extra[i+1] == _field:
                        return True
                    i += 1
            except Exception:
                return False
            return False

        try:
            if not _omitted("club"):
                pct = "50"
                try:
                    if hasattr(self, "settings_club_assign_pct"):
                        pct = str(self.settings_club_assign_pct.get() or "50").strip() or "50"
                except Exception:
                    pct = "50"

                try:
                    iv = int(pct)
                    if iv < 0: iv = 0
                    if iv > 100: iv = 100
                    pct = str(iv)
                except Exception:
                    pct = "50"

                # remove any previous --club_assign_pct then set chosen one
                try:
                    while "--club_assign_pct" in extra:
                        k = extra.index("--club_assign_pct")
                        del extra[k:k+2]
                except Exception:
                    pass

                extra.extend(["--club_assign_pct", pct])

                # optional: show in output
                try:
                    self._log(f"[INFO] club_assign_pct = {pct}% (Settings)\n")

                    # [PATCH GUI SETTINGS PACK v3a FIX v1] pass extra settings flags to generator
                    try:
                        def _set_flag(flag: str, val: str) -> None:
                            while flag in extra:
                                k = extra.index(flag)
                                del extra[k:k+2]
                            v = (val or '').strip()
                            if v != '':
                                extra.extend([flag, v])

                        _set_flag('--name_local_bias', self.settings_name_local_bias.get() if hasattr(self, 'settings_name_local_bias') else '')
                        _set_flag('--female_pct', self.settings_female_pct.get() if hasattr(self, 'settings_female_pct') else '')

                        _set_flag('--extra_nation_pct', self.settings_extra_nation_pct.get() if hasattr(self, 'settings_extra_nation_pct') else '')
                        _set_flag('--extra_nation_third_given_second_pct', self.settings_extra_nation_third_given_second_pct.get() if hasattr(self, 'settings_extra_nation_third_given_second_pct') else '')
                        _set_flag('--extra_nation_fourth_given_third_pct', self.settings_extra_nation_fourth_given_third_pct.get() if hasattr(self, 'settings_extra_nation_fourth_given_third_pct') else '')
                        _set_flag('--extra_nation_fifthplus_given_fourth_pct', self.settings_extra_nation_fifthplus_given_fourth_pct.get() if hasattr(self, 'settings_extra_nation_fifthplus_given_fourth_pct') else '')
                        _set_flag('--extra_nation_chain_pct', self.settings_extra_nation_chain_pct.get() if hasattr(self, 'settings_extra_nation_chain_pct') else '')
                        _set_flag('--extra_nation_max', self.settings_extra_nation_max.get() if hasattr(self, 'settings_extra_nation_max') else '')

                        _set_flag('--appearance_mode', self.settings_appearance_mode.get() if hasattr(self, 'settings_appearance_mode') else '')
                        _set_flag('--appearance_global_ethnicity', self.settings_appearance_global_ethnicity.get() if hasattr(self, 'settings_appearance_global_ethnicity') else '')
                        _set_flag('--appearance_global_skin', self.settings_appearance_global_skin.get() if hasattr(self, 'settings_appearance_global_skin') else '')
                        _set_flag('--appearance_global_hair_colour', self.settings_appearance_global_hair_colour.get() if hasattr(self, 'settings_appearance_global_hair_colour') else '')
                        _set_flag('--hair_length_weights_male', self.settings_hair_length_weights_male.get() if hasattr(self, 'settings_hair_length_weights_male') else '')
                        _set_flag('--hair_length_weights_female', self.settings_hair_length_weights_female.get() if hasattr(self, 'settings_hair_length_weights_female') else '')
                        _set_flag('--body_type_weights', self.settings_body_type_weights.get() if hasattr(self, 'settings_body_type_weights') else '')

                        _set_flag('--intl_play_prob_mult', self.settings_intl_play_prob_mult.get() if hasattr(self, 'settings_intl_play_prob_mult') else '')
                        _set_flag('--intl_opponent_mode', self.settings_intl_opponent_mode.get() if hasattr(self, 'settings_intl_opponent_mode') else '')
                        _set_flag('--intl_opponent_similarity', self.settings_intl_opponent_similarity.get() if hasattr(self, 'settings_intl_opponent_similarity') else '')
                    except Exception:
                        pass

                except Exception:
                    pass
        except Exception:
            pass




    # [PATCH v9] SETTINGS CLUB_ASSIGN_PCT




    def _omitted(_field: str) -> bool:




        try:




            i = 0




            while i < len(extra) - 1:




                if extra[i] == "--omit-field" and extra[i+1] == _field:




                    return True




                i += 1




        except Exception:




            return False




        return False





    try:




        if not _omitted("club"):




            pct = "50"




            try:




                if hasattr(self, "settings_club_assign_pct"):




                    pct = str(self.settings_club_assign_pct.get() or "50").strip() or "50"




            except Exception:




                pct = "50"




            try:




                iv = int(pct)




                if iv < 0: iv = 0




                if iv > 100: iv = 100




                pct = str(iv)




            except Exception:




                pct = "50"




            try:




                while "--club_assign_pct" in extra:




                    k = extra.index("--club_assign_pct")




                    del extra[k:k+2]




            except Exception:




                pass




            extra.extend(["--club_assign_pct", pct])




    except Exception:




        pass





    self._run_generator_common(
        script_path=self.batch_script.get().strip(),
        clubs=self.batch_clubs.get().strip(),
        first=self.batch_first.get().strip(),
        female_first=self.batch_female_first.get().strip(),
        common_names=self.batch_common_names.get().strip(),
        surn=self.batch_surn.get().strip(),
        out_path=self.batch_out.get().strip(),
        count=self.batch_count.get().strip(),
        age_min=_batch_age_min_arg,
        age_max=_batch_age_max_arg,
        ca_min=self.batch_ca_min.get().strip(),
        ca_max=self.batch_ca_max.get().strip(),
        pa_min=self.batch_pa_min.get().strip(),
        pa_max=self.batch_pa_max.get().strip(),
        base_year=self.batch_base_year.get().strip(),
        seed=self.batch_seed.get().strip(),
        title="Batch Generator",
        extra_args=extra,
    )

def _run_single_generator(self) -> None:
    ca = self.single_ca.get().strip()
    pa = self.single_pa.get().strip()
    # Optional single-player range override (leave blank to use fixed CA/PA as min=max)
    ca_min = self.single_ca_min.get().strip()
    ca_max = self.single_ca_max.get().strip()
    pa_min = self.single_pa_min.get().strip()
    pa_max = self.single_pa_max.get().strip()
    if any([ca_min, ca_max, pa_min, pa_max]):
        if not all([ca_min, ca_max, pa_min, pa_max]):
            messagebox.showerror("CA/PA range missing", "If using Single-player CA/PA range, fill CA min/max and PA min/max (or leave all four blank).")
            return
    else:
        ca_min = ca_max = ca
        pa_min = pa_max = pa

    base_year = self.single_base_year.get().strip()

    extra: list[str] = []
    # Player tab: force person type = 2 (player) in generator builds that support it
    extra.extend(["--person_type_value", "2"])

    # Age / DOB (supports legacy Single tab + shared Details DOB block)
    age = self.single_age.get().strip()
    age_min = (getattr(self, "single_age_min", tk.StringVar(value=age or "14")).get() or "").strip()
    age_max = (getattr(self, "single_age_max", tk.StringVar(value=age or "14")).get() or "").strip()
    if not age_min:
        age_min = age or "14"
    if not age_max:
        age_max = age or age_min or "14"

    s_dob_mode = (self.single_dob_mode.get() or "age").strip().lower()

    # Legacy single uses mode "dob" for fixed DOB.
    # Shared Details block now uses "range" for DOB range, but we also accept "fixed" for compatibility.
    if s_dob_mode == "none":
        extra.extend(["--omit-field", "dob"])
        # Do not force age args when DOB is explicitly omitted.
        # Generator can use its own defaults internally if needed.
        age_min = ""
        age_max = ""
    elif s_dob_mode in ("dob", "fixed"):
        dob = (getattr(self, "single_dob_fixed", self.single_dob).get() if hasattr(self, "single_dob_fixed") else self.single_dob.get()).strip()
        if not dob:
            messagebox.showerror("DOB missing", "Use DOB / Fixed DOB is selected, but DOB is blank.")
            return
        extra.extend(["--dob", dob])
        try:
            by = int(base_year or "2026")
            a = max(0, by - int(dob[:4]))
            age = str(a)
            age_min = age_max = age
        except Exception:
            pass
    elif s_dob_mode == "range":
        ds = getattr(self, "single_dob_start", tk.StringVar(value="")).get().strip()
        de = getattr(self, "single_dob_end", tk.StringVar(value="")).get().strip()
        if not ds or not de:
            messagebox.showerror("DOB range missing", "Please set both DOB Start and DOB End (YYYY-MM-DD).")
            return
        extra.extend(["--dob_start", ds, "--dob_end", de])

    self._apply_contract_tab_generation_overrides("single", extra)
    self._append_international_cli_args(extra, "single")
    # XML date overrides (optional)
    if self.single_moved_to_nation_mode.get() == "fixed":
        d = self.single_moved_to_nation_date.get().strip()
        if not d:
            messagebox.showerror("Date moved to nation missing", "Fixed Date moved to nation is selected, but the date is blank.")
            return
        extra.extend(["--moved_to_nation_date", d])

    if self.single_joined_club_mode.get() == "fixed":
        d = self.single_joined_club_date.get().strip()
        if not d:
            messagebox.showerror("Date joined club missing", "Fixed Date joined club is selected, but the date is blank.")
            return
        extra.extend(["--joined_club_date", d])

    if self.single_contract_expires_mode.get() == "fixed":
        d = self.single_contract_expires_date.get().strip()
        if not d:
            messagebox.showerror("Contract expires missing", "Fixed Contract expires is selected, but the date is blank.")
            return
        extra.extend(["--contract_expires_date", d])

    # Height
    _single_height_mode = (self.single_height_mode.get() or "random").strip().lower()
    if _single_height_mode == "none":
        extra.extend(["--omit-field", "height"])
    elif _single_height_mode == "fixed":
        h = self.single_height_fixed.get().strip()
        if not h:
            messagebox.showerror("Height missing", "Fixed height selected, but Height is blank.")
            return
        extra.extend(["--height", h])
    else:
        extra.extend(["--height_min", self.single_height_min.get().strip(), "--height_max", self.single_height_max.get().strip()])

    # Feet
    if self.single_feet_dont_set.get():
        extra.extend(["--omit-field", "feet"])
    else:
        extra.extend(["--feet", (self.single_feet_mode.get().strip() or "random")])
        if self.single_feet_override.get():
            lf = self.single_left_foot.get().strip()
            rf = self.single_right_foot.get().strip()
            if not lf or not rf:
                messagebox.showerror("Feet missing", "Override feet is ticked, but Left/Right values are blank.")
                return
            extra.extend(["--left_foot", lf, "--right_foot", rf])

    # Club/City/Nation fixed selections
    if self.single_club_dont_set.get():
        extra.extend(["--omit-field", "club"])
    elif self.single_club_mode.get() == "fixed":
        sel = self.single_club_sel.get().strip()
        ids = self._get_fixed_ids("club", sel)
        if not ids:
            messagebox.showerror("Club missing", "Fixed Club is selected, but no club is chosen.")
            return
        extra.extend(["--club_dbid", ids[0], "--club_large", ids[1]])

    if self.single_city_mode.get() == "fixed":
        sel = self.single_city_sel.get().strip()
        ids = self._get_fixed_ids("city", sel)
        if not ids:
            messagebox.showerror("City missing", "Fixed City is selected, but no city is chosen.")
            return
        extra.extend(["--city_dbid", ids[0], "--city_large", ids[1]])

    if self.single_nation_mode.get() == "fixed":
        sel = self.single_nation_sel.get().strip()
        ids = self._get_fixed_ids("nation", sel)
        if not ids:
            messagebox.showerror("Nation missing", "Fixed Nation is selected, but no nation is chosen.")
            return
        extra.extend(["--nation_dbid", ids[0], "--nation_large", ids[1]])

    # Positions
    if self.single_positions_dont_set.get():
        extra.extend(["--omit-field", "positions"])
        extra.extend(["--auto_dev_chance", "0"])
    elif self.single_positions_random.get():
        extra.extend(["--positions", "RANDOM"])
        if self.single_dev_enable.get():
            extra.extend(["--auto_dev_chance", (self.single_auto_dev_chance.get().strip() or "0")])
        else:
            extra.extend(["--auto_dev_chance", "0"])
    else:
        sel = [code for code, v in self.single_pos_vars.items() if v.get()]
        if not sel:
            messagebox.showerror("Positions missing", "Please select at least one position, or tick Random positions.")
            return
        if "GK" in sel and len(sel) > 1:
            messagebox.showerror("Invalid selection", "GK cannot be combined with outfield positions.")
            return

        primary = sel[0]
        extras = sel[1:]
        extra.extend(["--pos_primary", primary])
        if extras:
            extra.extend(["--pos_20", ",".join(extras)])
        extra.extend(["--auto_dev_chance", "0"])
    # Development positions (auto-picked by generator v4)
    mode = (self.single_dev_mode.get() or "random").strip().lower()
    if mode not in ("random", "fixed", "range"):
        mode = "random"
    extra.extend(["--pos_dev_mode", mode])

    if mode == "fixed":
        try:
            v = int((self.single_dev_fixed.get() or "10").strip())
        except Exception:
            messagebox.showerror("Dev value", "Dev fixed value must be an integer (2..19).")
            return
        extra.extend(["--pos_dev_value", str(v)])
    elif mode == "range":
        try:
            mn = int((self.single_dev_min.get() or "2").strip())
            mx = int((self.single_dev_max.get() or "19").strip())
        except Exception:
            messagebox.showerror("Dev range", "Dev min/max must be integers (2..19).")
            return
        extra.extend(["--pos_dev_min", str(mn), "--pos_dev_max", str(mx)])
    # Wage
    if self.single_wage_dont_set.get():
        extra.extend(["--omit-field", "wage"])
    elif self.single_wage_mode.get() == "fixed":
        w = self.single_wage_fixed.get().strip()
        if not w:
            messagebox.showerror("Wage missing", "Fixed wage selected, but Wage is blank.")
            return
        extra.extend(["--wage", w])
    else:
        extra.extend(["--wage_min", self.single_wage_min.get().strip(), "--wage_max", self.single_wage_max.get().strip()])

    # Reputation
    if self.single_rep_dont_set.get():
        extra.extend(["--omit-field", "reputation"])
    elif self.single_rep_mode.get() == "fixed":
        rc = self.single_rep_current.get().strip()
        rh = self.single_rep_home.get().strip()
        rw = self.single_rep_world.get().strip()
        if not rc or not rh or not rw:
            messagebox.showerror("Reputation missing", "Fixed reputation selected, but Current/Home/World are not all set.")
            return
        extra.extend(["--rep_current", rc, "--rep_home", rh, "--rep_world", rw])
    else:
        extra.extend(["--rep_min", self.single_rep_min.get().strip(), "--rep_max", self.single_rep_max.get().strip()])

    # Transfer value
    if self.single_tv_dont_set.get():
        extra.extend(["--omit-field", "transfer_value"])
    else:
        tv_mode = self.single_tv_mode.get().strip() or "auto"
        extra.extend(["--transfer_mode", tv_mode])
        if tv_mode == "fixed":
            tv = self.single_tv_fixed.get().strip()
            if not tv:
                messagebox.showerror("Transfer value missing", "Transfer value mode is Fixed, but value is blank.")
                return
            extra.extend(["--transfer_value", tv])
        elif tv_mode == "range":
            tmin = self.single_tv_min.get().strip()
            tmax = self.single_tv_max.get().strip()
            if not tmin or not tmax:
                messagebox.showerror("Transfer value missing", "Transfer mode is Range, but min/max are blank.")
                return
            extra.extend(["--transfer_min", tmin, "--transfer_max", tmax])

    # Details section (supported exports + UI-ready placeholders)
    try:
        if self.single_details_first_name_mode.get() == "custom" and self.single_details_first_name_value.get().strip():
            extra.extend(["--first_name_text", self.single_details_first_name_value.get().strip()])
        if self.single_details_second_name_mode.get() == "custom" and self.single_details_second_name_value.get().strip():
            extra.extend(["--second_name_text", self.single_details_second_name_value.get().strip()])
        if self.single_details_common_name_mode.get() == "custom" and self.single_details_common_name_value.get().strip():
            extra.extend(["--common_name_text", self.single_details_common_name_value.get().strip()])
        if self.single_details_full_name_mode.get() == "custom" and self.single_details_full_name_value.get().strip():
            extra.extend(["--full_name_text", self.single_details_full_name_value.get().strip()])

        if self.single_details_gender_mode.get() == "custom":
            gval = self.single_details_gender_value.get().strip()
            if gval:
                try:
                    gv = self._details_gender_to_int(gval)
                except Exception as e:
                    messagebox.showerror("Gender", str(e))
                    return
                if gv is not None:
                    extra.extend(["--gender_value", str(gv)])

        if self.single_details_ethnicity_mode.get() == "custom":
            eval_ = self.single_details_ethnicity_value.get().strip()
            if eval_:
                try:
                    ev = self._details_ethnicity_to_int(eval_)
                except Exception as e:
                    messagebox.showerror("Ethnicity", str(e))
                    return
                if ev is not None:
                    extra.extend(["--ethnicity_value", str(ev)])

        # Primary nationality info (Details tab)
        _nat_info_added = False
        try:
            if self.single_details_nationality_info_mode.get() == "custom":
                ni_label = self.single_details_nationality_info_value.get().strip()
                if ni_label:
                    extra.extend(["--nationality_info", ni_label])
                    _nat_info_added = True
        except Exception:
            pass

        # International Data tab (custom values only)
        self._append_international_data_cli_args(extra, "single")

        # Second Nations metadata export (editor values first, then first row as fallback)
        # NOTE: do NOT override the primary Details Nationality Info unless it is blank.
        try:
            _sn_editor_ni = (getattr(self, "single_second_nations_nationality_info").get() or "").strip() if hasattr(self, "single_second_nations_nationality_info") else ""
            _sn_editor_int_ret = bool(getattr(self, "single_second_nations_international_retirement").get()) if hasattr(self, "single_second_nations_international_retirement") else False
            _sn_editor_date = (getattr(self, "single_second_nations_international_retirement_date").get() or "").strip() if hasattr(self, "single_second_nations_international_retirement_date") else ""
            _sn_editor_retire_spell = bool(getattr(self, "single_second_nations_retiring_after_spell_current_club").get()) if hasattr(self, "single_second_nations_retiring_after_spell_current_club") else False

            _sn_items = list(getattr(self, "single_second_nations_items", []) or [])
            _sn0 = dict(_sn_items[0] or {}) if _sn_items else {}

            # Export repeatable second nation list entries (nation + optional per-entry nationality info)
            for _sn in _sn_items:
                try:
                    _sn_nation = (dict(_sn or {}).get("nation") or "").strip()
                    if not _sn_nation:
                        continue
                    _sn_ni_item = (dict(_sn or {}).get("nationality_info") or "").strip()
                    _sn_spec = _sn_nation
                    if _sn_ni_item:
                        # Pass label through; generator resolves labels/numbers to FM ntin values
                        _sn_spec = f"{_sn_spec}|{_sn_ni_item}"
                    extra.extend(["--second_nation", _sn_spec])
                except Exception:
                    pass


            _sn_ni = _sn_editor_ni or (_sn0.get("nationality_info") or "").strip()
            if _sn_ni and not _nat_info_added and _sn_ni.lower() != "no info":
                extra.extend(["--nationality_info", _sn_ni])

            if _sn_editor_int_ret or bool(_sn0.get("international_retirement", False)):
                extra.append("--international_retirement")

            _sn_date = _sn_editor_date or (_sn0.get("international_retirement_date") or "").strip()
            if _sn_date:
                extra.extend(["--international_retirement_date", _sn_date])

            if _sn_editor_retire_spell or bool(_sn0.get("retiring_after_spell_current_club", False)):
                extra.append("--retiring_after_spell_current_club")

            try:
                _dy_mode = (getattr(self, "single_details_declared_for_youth_nation_mode").get() or "random").strip().lower() if hasattr(self, "single_details_declared_for_youth_nation_mode") else "random"
                _dy_sel = (getattr(self, "single_details_declared_for_youth_nation_value").get() or "").strip() if hasattr(self, "single_details_declared_for_youth_nation_value") else ""
                if _dy_mode == "custom" and _dy_sel:
                    extra.extend(["--declared_for_youth_nation", _dy_sel])
            except Exception:
                pass
        except Exception:
            pass

        if self.single_ca_dont_set.get():
            extra.extend(["--omit-field", "ca"])
        if self.single_pa_dont_set.get():
            extra.extend(["--omit-field", "pa"])
        self._append_details_dontset_cli_args(extra, "single")

        if self.single_details_date_of_birth_mode.get() == "custom":
            d = self.single_details_date_of_birth_value.get().strip()
            if d:
                extra.extend(["--dob", d])
        elif self.single_details_date_of_birth_mode.get() == "none":
            extra.extend(["--omit-field", "dob"])

        # Prefer new Details > Height block (range/fixed), fallback to legacy custom single-value height field
        details_height_handled = False
        try:
            h_mode2 = (self.single_details_height_mode2.get() if hasattr(self, "single_details_height_mode2") else "").strip()
            if h_mode2 == "none":
                details_height_handled = True
            elif h_mode2 == "fixed":
                h = self.single_details_height_fixed.get().strip()
                if h:
                    extra.extend(["--height", h])
                    details_height_handled = True
            elif h_mode2 == "range":
                hmin = self.single_details_height_min.get().strip()
                hmax = self.single_details_height_max.get().strip()
                if hmin and hmax:
                    extra.extend(["--height_min", hmin, "--height_max", hmax])
                    details_height_handled = True
        except Exception:
            pass

        if (not details_height_handled) and self.single_details_height_mode.get() == "custom":
            h = self.single_details_height_value.get().strip()
            if h:
                extra.extend(["--height", h])

        if self.single_details_city_of_birth_mode.get() == "custom":
            sel = self.single_details_city_of_birth_value.get().strip()
            if sel:
                ids = self._get_fixed_ids("city", sel)
                if ids:
                    extra.extend(["--city_dbid", ids[0], "--city_large", ids[1]])
                else:
                    messagebox.showerror("City Of Birth", "Custom City Of Birth must be selected from the master_library city list.")
                    return

    except Exception:
        pass

    # [PATCH v20] DETAILS NATION FORCE-INJECT

    try:

        n_mode = (getattr(self, "single_details_nation_mode").get() or "none").strip().lower()

        n_val  = (getattr(self, "single_details_nation_value").get() or "").strip()

        print(f"[DEBUG v20] Single Details Nation: mode={n_mode} value={n_val!r}")

        if n_mode == "custom" and n_val and "--nation_dbid" not in extra:

            ids = self._get_fixed_ids("nation", n_val)

            if ids:

                extra.extend(["--nation_dbid", ids[0], "--nation_large", ids[1]])

                print(f"[DEBUG v20] Single injected nation -> DBID {ids[0]} LARGE {ids[1]}")

            else:

                messagebox.showerror("Nation", "Custom Nation must be selected from the master_library nation list.")

                return

    except Exception as e:

        print(f"[DEBUG v20] Single nation inject error: {e}")



        # [PATCH v8] club_assign_pct from Settings (default 50)
        def _omitted(_field: str) -> bool:
            try:
                i = 0
                while i < len(extra) - 1:
                    if extra[i] == "--omit-field" and extra[i+1] == _field:
                        return True
                    i += 1
            except Exception:
                return False
            return False

        try:
            if not _omitted("club"):
                pct = "50"
                try:
                    if hasattr(self, "settings_club_assign_pct"):
                        pct = str(self.settings_club_assign_pct.get() or "50").strip() or "50"
                except Exception:
                    pct = "50"

                try:
                    iv = int(pct)
                    if iv < 0: iv = 0
                    if iv > 100: iv = 100
                    pct = str(iv)
                except Exception:
                    pct = "50"

                # remove any previous --club_assign_pct then set chosen one
                try:
                    while "--club_assign_pct" in extra:
                        k = extra.index("--club_assign_pct")
                        del extra[k:k+2]
                except Exception:
                    pass

                extra.extend(["--club_assign_pct", pct])

                # optional: show in output
                try:
                    self._log(f"[INFO] club_assign_pct = {pct}% (Settings)\n")

                    # [PATCH GUI SETTINGS PACK v3a FIX v1] pass extra settings flags to generator
                    try:
                        def _set_flag(flag: str, val: str) -> None:
                            while flag in extra:
                                k = extra.index(flag)
                                del extra[k:k+2]
                            v = (val or '').strip()
                            if v != '':
                                extra.extend([flag, v])

                        _set_flag('--name_local_bias', self.settings_name_local_bias.get() if hasattr(self, 'settings_name_local_bias') else '')
                        _set_flag('--female_pct', self.settings_female_pct.get() if hasattr(self, 'settings_female_pct') else '')

                        _set_flag('--extra_nation_pct', self.settings_extra_nation_pct.get() if hasattr(self, 'settings_extra_nation_pct') else '')
                        _set_flag('--extra_nation_third_given_second_pct', self.settings_extra_nation_third_given_second_pct.get() if hasattr(self, 'settings_extra_nation_third_given_second_pct') else '')
                        _set_flag('--extra_nation_fourth_given_third_pct', self.settings_extra_nation_fourth_given_third_pct.get() if hasattr(self, 'settings_extra_nation_fourth_given_third_pct') else '')
                        _set_flag('--extra_nation_fifthplus_given_fourth_pct', self.settings_extra_nation_fifthplus_given_fourth_pct.get() if hasattr(self, 'settings_extra_nation_fifthplus_given_fourth_pct') else '')
                        _set_flag('--extra_nation_chain_pct', self.settings_extra_nation_chain_pct.get() if hasattr(self, 'settings_extra_nation_chain_pct') else '')
                        _set_flag('--extra_nation_max', self.settings_extra_nation_max.get() if hasattr(self, 'settings_extra_nation_max') else '')

                        _set_flag('--appearance_mode', self.settings_appearance_mode.get() if hasattr(self, 'settings_appearance_mode') else '')
                        _set_flag('--appearance_global_ethnicity', self.settings_appearance_global_ethnicity.get() if hasattr(self, 'settings_appearance_global_ethnicity') else '')
                        _set_flag('--appearance_global_skin', self.settings_appearance_global_skin.get() if hasattr(self, 'settings_appearance_global_skin') else '')
                        _set_flag('--appearance_global_hair_colour', self.settings_appearance_global_hair_colour.get() if hasattr(self, 'settings_appearance_global_hair_colour') else '')
                        _set_flag('--hair_length_weights_male', self.settings_hair_length_weights_male.get() if hasattr(self, 'settings_hair_length_weights_male') else '')
                        _set_flag('--hair_length_weights_female', self.settings_hair_length_weights_female.get() if hasattr(self, 'settings_hair_length_weights_female') else '')
                        _set_flag('--body_type_weights', self.settings_body_type_weights.get() if hasattr(self, 'settings_body_type_weights') else '')

                        _set_flag('--intl_play_prob_mult', self.settings_intl_play_prob_mult.get() if hasattr(self, 'settings_intl_play_prob_mult') else '')
                        _set_flag('--intl_opponent_mode', self.settings_intl_opponent_mode.get() if hasattr(self, 'settings_intl_opponent_mode') else '')
                        _set_flag('--intl_opponent_similarity', self.settings_intl_opponent_similarity.get() if hasattr(self, 'settings_intl_opponent_similarity') else '')
                    except Exception:
                        pass

                except Exception:
                    pass
        except Exception:
            pass




    # [PATCH v9] SETTINGS CLUB_ASSIGN_PCT




    def _omitted(_field: str) -> bool:




        try:




            i = 0




            while i < len(extra) - 1:




                if extra[i] == "--omit-field" and extra[i+1] == _field:




                    return True




                i += 1




        except Exception:




            return False




        return False





    try:




        if not _omitted("club"):




            pct = "50"




            try:




                if hasattr(self, "settings_club_assign_pct"):




                    pct = str(self.settings_club_assign_pct.get() or "50").strip() or "50"




            except Exception:




                pct = "50"




            try:




                iv = int(pct)




                if iv < 0: iv = 0




                if iv > 100: iv = 100




                pct = str(iv)




            except Exception:




                pct = "50"




            try:




                while "--club_assign_pct" in extra:




                    k = extra.index("--club_assign_pct")




                    del extra[k:k+2]




            except Exception:




                pass




            extra.extend(["--club_assign_pct", pct])




    except Exception:




        pass





    self._run_generator_common(
        script_path=self.single_script.get().strip(),
        clubs=self.single_clubs.get().strip(),
        first=self.single_first.get().strip(),
        female_first=self.single_female_first.get().strip(),
        common_names=self.single_common_names.get().strip(),
        surn=self.single_surn.get().strip(),
        out_path=self.single_out.get().strip(),
        count="1",
        age_min=age_min,
        age_max=age_max,
        ca_min=ca_min,
        ca_max=ca_max,
        pa_min=pa_min,
        pa_max=pa_max,
        base_year=base_year,
        seed=self.single_seed.get().strip(),
        title="Single Generator",
        extra_args=extra,
    )

def _generator_script_supports_flag(self, script_path: str, flag: str) -> bool:
    try:
        txt = Path(script_path).read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return True  # don't block if unreadable
    return (flag in txt)

def _strip_unsupported_cli_flags(self, script_path: str, args: list[str]) -> list[str]:
    """
    Drop GUI flags that older generator scripts do not support, so generation still runs.
    We keep a log warning telling the user which fields were skipped.
    """
    if not args:
        return []
    # flags that take a following value
    value_flags = [
        "--omit-field",
        "--first_international_goal_date",
        "--first_international_goal_against",
        "--other_nation_caps_json",
        "--other_nation_youth_caps_json",
    ]
    unsupported = {f for f in value_flags if not self._generator_script_supports_flag(script_path, f)}
    if not unsupported:
        return list(args)

    out: list[str] = []
    i = 0
    while i < len(args):
        a = str(args[i])
        if a in unsupported:
            skipped = [a]
            if i + 1 < len(args):
                skipped.append(str(args[i + 1]))
                i += 2
            else:
                i += 1
            try:
                self._log(f"[WARN] Selected generator script does not support {a}; skipping this GUI option.\n")
            except Exception:
                pass
            continue
        out.append(args[i])
        i += 1
    return out

def _run_generator_common(
    self,
    script_path: str,
    clubs: str,
    first: str,
    female_first: str,
    common_names: str,
    surn: str,
    out_path: str,
    count: str,
    age_min: str,
    age_max: str,
    ca_min: str,
    ca_max: str,
    pa_min: str,
    pa_max: str,
    base_year: str,
    seed: str,
    title: str,
    extra_args: list[str] | None = None,
) -> None:
    if not script_path or not Path(script_path).exists():
        messagebox.showerror("Missing script", "Please choose a valid generator .py script.")
        return

    def must_exist(path: str, label: str) -> bool:
        if not path or not Path(path).exists():
            messagebox.showerror("Missing input", f"Please choose a valid {label} file.")
            return False
        return True

    if not must_exist(clubs, "master_library.csv"):
        return

    extra_joined = " ".join([str(x) for x in (extra_args or [])])
    has_manual_first = "--first_name_text" in extra_joined
    has_manual_second = "--second_name_text" in extra_joined

    if (not has_manual_first) and (not must_exist(first, "first names")):
        return
    if female_first and (not must_exist(female_first, "female first names")):
        return
    if common_names and (not must_exist(common_names, "common names")):
        return
    if (not has_manual_second) and (not must_exist(surn, "surnames")):
        return
    if not out_path:
        messagebox.showerror("Missing output", "Please choose an output XML path.")
        return

    try:
        ensure_parent_dir(out_path)
    except Exception as e:
        messagebox.showerror("Output folder error", "Could not create output folder: " + str(e))
        return

    cmd = [
        sys.executable,
        script_path,
        "--master_library", clubs,
        "--first_names", first,
        "--surnames", surn,
        "--count", count,
        "--output", out_path,
    ]
    if str(age_min or "").strip() != "":
        cmd.extend(["--age_min", str(age_min).strip()])
    if str(age_max or "").strip() != "":
        cmd.extend(["--age_max", str(age_max).strip()])

    _extra_scan = [str(x).strip().lower() for x in (extra_args or [])]
    _omit_fields = set()
    for i in range(len(_extra_scan) - 1):
        if _extra_scan[i] == "--omit-field":
            _omit_fields.add(_extra_scan[i + 1])

    if "ca" not in _omit_fields:
        cmd.extend(["--ca_min", ca_min, "--ca_max", ca_max])
    if "pa" not in _omit_fields:
        cmd.extend(["--pa_min", pa_min, "--pa_max", pa_max])
    cmd.extend(["--base_year", base_year])
    if female_first:
        cmd.extend(["--female_first_names", female_first])
    if common_names:
        cmd.extend(["--common_names", common_names])
    if seed:
        cmd.extend(["--seed", seed])
    if extra_args:
        extra_args = self._strip_unsupported_cli_flags(script_path, list(extra_args))
        cmd.extend([x for x in extra_args if x is not None and str(x) != ""])

    self._run_async_stream(title, cmd, must_create=out_path)

def _ensure_output_visible(self) -> None:
    """Show output pane if hidden so runs do not look like 'nothing happened'."""
    try:
        if not getattr(self, "_output_visible", False):
            self._toggle_output()
    except Exception:
        pass

def _run_async_stream(self, title: str, cmd: list[str], must_create: str | None = None) -> None:
    self._ensure_output_visible()
    self._log("\n" + "=" * 100)
    self._log(f"{title} command:\n  " + " ".join([_quote(x) for x in cmd]))
    self._log(f"Working directory:\n  {self.base_dir}\n")

    def worker():
        try:
            p = subprocess.Popen(
                cmd,
                cwd=str(self.base_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            assert p.stdout is not None
            for line in p.stdout:
                self._log_threadsafe(line.rstrip("\n"))
            rc = p.wait()
        except Exception as e:
            self._ui_error(f"{title} failed", str(e))
            return

        if rc == 0 and must_create:
            try:
                outp = Path(must_create).expanduser()
                if not outp.exists():
                    self._ui_error("Output missing", f"{title} said OK, but output file was not found:\n{outp}")
                    return
                if outp.is_file() and outp.stat().st_size == 0:
                    self._ui_error("Empty output", f"Output file was created but is empty:\n{outp}")
                    return
                self._log_threadsafe(f"\n[OK] Output written:\n  {outp}\n  Size: {outp.stat().st_size:,} bytes\n")
            except Exception as e:
                self._log_threadsafe(f"[WARN] Could not verify output file: {e}\n")

        if rc == 0:
            self._log_threadsafe(f"\n[OK] {title} finished successfully.\n")
        else:
            self._log_threadsafe(f"\n[FAIL] {title} exited with code {rc}.\n")
            self._ui_error(f"{title} failed", f"{title} failed (exit code {rc}).\nCheck Output/Errors box for details.")

    threading.Thread(target=worker, daemon=True).start()

def _pick_py_script_var(self, var: tk.StringVar) -> None:
    p = filedialog.askopenfilename(
        title="Select Python script",
        initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)),
        filetypes=[("Python files", "*.py"), ("All files", "*.*")]
    )
    if p:
        var.set(p)

def _pick_xml_target_open(self, var: tk.StringVar) -> None:
    p = filedialog.askopenfilename(
        title="Select target db_changes XML",
        initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)),
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )
    if p:
        var.set(p)

def _pick_xml_output_save(self, var: tk.StringVar) -> None:
    p = filedialog.asksaveasfilename(
        title="Save merged XML as",
        initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)),
        defaultextension=".xml",
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )
    if p:
        var.set(p)

def _appender_refresh_source_list(self) -> None:
    lb = getattr(self, "appender_sources_listbox", None)
    if lb is None:
        return
    try:
        lb.delete(0, "end")
        for p in getattr(self, "appender_sources", []):
            lb.insert("end", p)
        self.appender_sources_count.set(f"{len(getattr(self, 'appender_sources', []))} source file(s) selected")
    except Exception:
        pass

def _appender_add_sources(self) -> None:
    picks = filedialog.askopenfilenames(
        title="Select source XML file(s) to append",
        initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)),
        filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
    )
    if not picks:
        return
    seen = {str(Path(p).resolve()) for p in getattr(self, "appender_sources", [])}
    for p in picks:
        try:
            rp = str(Path(p).resolve())
        except Exception:
            rp = str(p)
        if rp not in seen:
            self.appender_sources.append(str(p))
            seen.add(rp)
    self._appender_refresh_source_list()

def _appender_add_folder_xml(self) -> None:
    d = filedialog.askdirectory(title="Select folder containing XML files", initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)))
    if not d:
        return
    folder = Path(d)
    files = sorted([p for p in folder.glob("*.xml") if p.is_file()])
    if not files:
        messagebox.showinfo("No XML files", f"No .xml files were found in:\n{folder}")
        return
    seen = {str(Path(p).resolve()) for p in getattr(self, "appender_sources", [])}
    added = 0
    for p in files:
        rp = str(p.resolve())
        if rp not in seen:
            self.appender_sources.append(str(p))
            seen.add(rp)
            added += 1
    self._appender_refresh_source_list()
    self._log(f"[OK] XML Appender: added {added} XML file(s) from folder:\n  {folder}\n")

def _appender_remove_selected(self) -> None:
    lb = getattr(self, "appender_sources_listbox", None)
    if lb is None:
        return
    sel = list(lb.curselection())
    if not sel:
        return
    keep = []
    selset = set(int(i) for i in sel)
    for idx, p in enumerate(getattr(self, "appender_sources", [])):
        if idx not in selset:
            keep.append(p)
    self.appender_sources = keep
    self._appender_refresh_source_list()

def _appender_clear_sources(self) -> None:
    self.appender_sources = []
    self._appender_refresh_source_list()

def _build_appender_tab(self) -> None:
    frm = self.appender_body
    frm.columnconfigure(0, weight=1)

    # State
    self.appender_script = tk.StringVar(value=str(self.fmdata_dir / DEFAULT_XML_APPENDER_SCRIPT))
    self.appender_target_xml = tk.StringVar(value=str(self.fmdata_dir / "fm26_players.xml"))
    self.appender_output_xml = tk.StringVar(value=str(self.fmdata_dir / "fm26_merged.xml"))
    self.appender_sources = []  # list[str]
    self.appender_sources_count = tk.StringVar(value="0 source file(s) selected")

    self.appender_create_target = tk.BooleanVar(value=False)
    self.appender_backup = tk.BooleanVar(value=True)
    self.appender_skip_self = tk.BooleanVar(value=True)
    self.appender_dry_run = tk.BooleanVar(value=False)
    self.appender_verbose = tk.BooleanVar(value=True)
    self.appender_dedupe = tk.StringVar(value="create")

    # File inputs (hidden by default)
    paths = ttk.LabelFrame(frm, text="File inputs")
    paths.grid(row=0, column=0, sticky="ew", padx=8, pady=(0, 8))
    paths.columnconfigure(1, weight=1)
    self.appender_paths_frame = paths
    paths.grid_remove()

    def row_file(r: int, label: str, var: tk.StringVar, picker):
        ttk.Label(paths, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
        ttk.Entry(paths, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
        ttk.Button(paths, text="Browse…", command=lambda: picker(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

    row_file(0, "Appender script:", self.appender_script, self._pick_py_script_var)
    row_file(1, "Target XML:", self.appender_target_xml, self._pick_xml_target_open)
    row_file(2, "Output XML (optional):", self.appender_output_xml, self._pick_xml_output_save)

    # Source files selector (always visible)
    srcf = ttk.LabelFrame(frm, text="Source XML files to append (multi-select)")
    srcf.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
    srcf.columnconfigure(0, weight=1)
    srcf.rowconfigure(1, weight=1)

    ttk.Label(srcf, text="Select multiple XML files and append them into the target (or output file).").grid(
        row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 4)
    )

    list_wrap = ttk.Frame(srcf)
    list_wrap.grid(row=1, column=0, sticky="nsew", padx=(8, 6), pady=(0, 8))
    list_wrap.columnconfigure(0, weight=1)
    list_wrap.rowconfigure(0, weight=1)

    self.appender_sources_listbox = tk.Listbox(list_wrap, height=10, selectmode="extended")
    self.appender_sources_listbox.grid(row=0, column=0, sticky="nsew")
    lb_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.appender_sources_listbox.yview)
    lb_scroll.grid(row=0, column=1, sticky="ns")
    self.appender_sources_listbox.configure(yscrollcommand=lb_scroll.set)

    btns = ttk.Frame(srcf)
    btns.grid(row=1, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))
    ttk.Button(btns, text="Add XML file(s)…", command=self._appender_add_sources).pack(fill="x", pady=(0, 6))
    ttk.Button(btns, text="Add Folder (*.xml)…", command=self._appender_add_folder_xml).pack(fill="x", pady=(0, 6))
    ttk.Button(btns, text="Remove Selected", command=self._appender_remove_selected).pack(fill="x", pady=(0, 6))
    ttk.Button(btns, text="Clear List", command=self._appender_clear_sources).pack(fill="x", pady=(0, 6))

    ttk.Label(srcf, textvariable=self.appender_sources_count, foreground="#444").grid(
        row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8)
    )

    # Options
    opt = ttk.LabelFrame(frm, text="Appender options")
    opt.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
    for c in range(4):
        opt.columnconfigure(c, weight=1)

    ttk.Checkbutton(opt, text="Create target if missing", variable=self.appender_create_target).grid(row=0, column=0, sticky="w", padx=8, pady=6)
    ttk.Checkbutton(opt, text="Backup output/target (.bak)", variable=self.appender_backup).grid(row=0, column=1, sticky="w", padx=8, pady=6)
    ttk.Checkbutton(opt, text="Skip source if same as target", variable=self.appender_skip_self).grid(row=0, column=2, sticky="w", padx=8, pady=6)
    ttk.Checkbutton(opt, text="Verbose per-file output", variable=self.appender_verbose).grid(row=0, column=3, sticky="w", padx=8, pady=6)

    ttk.Checkbutton(opt, text="Dry run (no write)", variable=self.appender_dry_run).grid(row=1, column=0, sticky="w", padx=8, pady=6)
    ttk.Label(opt, text="Dedupe mode:").grid(row=1, column=1, sticky="e", padx=(8, 6), pady=6)
    ded_cb = ttk.Combobox(opt, textvariable=self.appender_dedupe, values=["none", "exact", "create"], state="normal", width=12)
    ded_cb.grid(row=1, column=2, sticky="w", padx=(0, 8), pady=6)
    ttk.Label(opt, text="create = skip duplicate player create-record IDs").grid(row=1, column=3, sticky="w", padx=8, pady=6)

    hint = (
        "Tip: Use this to merge multiple generated XML files (single-player and batch outputs) into one db_changes XML.\n"
        "You can select multiple files at once, or add a whole folder of XML files."
    )
    ttk.Label(frm, text=hint, foreground="#444").grid(row=3, column=0, sticky="w", padx=8, pady=(0, 8))

def _run_xml_appender(self) -> None:
    script = self.appender_script.get().strip()
    target = self.appender_target_xml.get().strip()
    out_xml = self.appender_output_xml.get().strip()

    if not script:
        messagebox.showerror("Appender script missing", "Please select the XML Appender Python script.")
        return
    if not Path(script).exists():
        messagebox.showerror("Appender script not found", f"File not found:\n{script}")
        return
    if not target:
        messagebox.showerror("Target XML missing", "Please select or enter a Target XML file.")
        return
    if not getattr(self, "appender_sources", []):
        messagebox.showerror("Source files missing", "Please add one or more source XML files to append.")
        return

    cmd = [sys.executable, script, "--target", target]
    for s in self.appender_sources:
        if str(s).strip():
            cmd.extend(["--source", str(s)])

    if out_xml:
        cmd.extend(["--output", out_xml])
    if self.appender_create_target.get():
        cmd.append("--create-target")
    if self.appender_backup.get():
        cmd.append("--backup")
    if self.appender_skip_self.get():
        cmd.append("--skip-self")
    if self.appender_dry_run.get():
        cmd.append("--dry-run")
    if self.appender_verbose.get():
        cmd.append("--verbose")

    dedupe = (self.appender_dedupe.get() or "none").strip().lower()
    if dedupe not in ("none", "exact", "create"):
        dedupe = "none"
    cmd.extend(["--dedupe", dedupe])

    must_create = None if self.appender_dry_run.get() else (out_xml or target)
    self._run_async_stream("XML Appender", cmd, must_create=must_create)



# ===================== intl cli args hotfix v1 =====================
# Ensure International Data tab modes are exported to generator CLI.
# - Random => pass -2 for counts (generator auto)
# - Custom => pass explicit values
# - Don't set => --omit-field <field>

def _append_international_data_cli_args(self, extra: list, prefix: str) -> None:
    # Append International Data tab fields to generator CLI args.
    def _gv(attr: str, default: str = '') -> str:
        v = getattr(self, attr, None)
        if v is None:
            return default
        try:
            return v.get()
        except Exception:
            return default

    # Integer counters: Random/Auto is -2 (generator estimates based on age/PA/nation strength)
    for key, arg in [
        ("international_apps", "--international_apps"),
        ("international_goals", "--international_goals"),
        ("u21_international_apps", "--u21_international_apps"),
        ("u21_international_goals", "--u21_international_goals"),
    ]:
        mode = str(_gv(f"{prefix}_intl_{key}_mode", "random") or "random").strip().lower()
        val = str(_gv(f"{prefix}_intl_{key}_value", "") or "").strip()
        if mode == "none":
            extra.extend(["--omit-field", key])
        elif mode == "custom":
            if val == "":
                raise ValueError(f"{key.replace('_', ' ').title()} is Custom, but the value is blank")
            try:
                extra.extend([arg, str(int(val))])
            except Exception:
                raise ValueError(f"{key.replace('_', ' ').title()} must be an integer")
        else:
            extra.extend([arg, "-2"])

    # Date strings: Random => omit (generator auto-fills when caps/goals > 0)
    for key, arg in [
        ("international_debut_date", "--international_debut_date"),
        ("first_international_goal_date", "--first_international_goal_date"),
    ]:
        mode = str(_gv(f"{prefix}_intl_{key}_mode", "random") or "random").strip().lower()
        val = str(_gv(f"{prefix}_intl_{key}_value", "") or "").strip()
        if mode == "none":
            extra.extend(["--omit-field", key])
        elif mode == "custom" and val:
            extra.extend([arg, val])

    # Nation strings: Random => omit (generator auto-fills opponent when caps/goals > 0)
    for key, arg in [
        ("international_debut_against", "--international_debut_against"),
        ("first_international_goal_against", "--first_international_goal_against"),
    ]:
        mode = str(_gv(f"{prefix}_intl_{key}_mode", "random") or "random").strip().lower()
        val = str(_gv(f"{prefix}_intl_{key}_value", "") or "").strip()
        if mode == "none":
            extra.extend(["--omit-field", key])
        elif mode == "custom" and val:
            extra.extend([arg, val])

try:
    App._append_international_data_cli_args = _append_international_data_cli_args
except Exception:
    pass
# =================== end intl cli args hotfix v1 ===================
# --- v58 hotfix: restore methods accidentally nested inside _apply_contract_tab_generation_overrides ---
try:
    App._get_contract_tab_field_mode_value = _get_contract_tab_field_mode_value
    App._apply_contract_tab_generation_overrides = _apply_contract_tab_generation_overrides
except Exception:
    pass

try:
    App._run_batch_generator = _run_batch_generator
    App._run_single_generator = _run_single_generator
    App._generator_script_supports_flag = _generator_script_supports_flag
    App._strip_unsupported_cli_flags = _strip_unsupported_cli_flags
    App._run_generator_common = _run_generator_common
    # [RUNNER_MOVED] App._ensure_output_visible provided by RunnerMixin
    # [RUNNER_MOVED] App._run_async_stream provided by RunnerMixin
    App._pick_py_script_var = _pick_py_script_var
    App._pick_xml_target_open = _pick_xml_target_open
    App._pick_xml_output_save = _pick_xml_output_save
    App._appender_refresh_source_list = _appender_refresh_source_list
    App._appender_add_sources = _appender_add_sources
    App._appender_add_folder_xml = _appender_add_folder_xml
    App._appender_remove_selected = _appender_remove_selected
    App._appender_clear_sources = _appender_clear_sources
    App._build_appender_tab = _build_appender_tab
    App._run_xml_appender = _run_xml_appender
except Exception:
    pass