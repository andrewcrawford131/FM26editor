# -*- coding: utf-8 -*-

from __future__ import annotations

class ContractOverridesMixin:
    def _get_contract_tab_field_mode_value(self, prefix: str, key: str):
        """Return (mode, value) from contract-tab field registry for batch/single."""
        store = getattr(self, f"{prefix}_club_contract_vars", {}) or {}
        mode_var = store.get(f"{key}_mode")
        value_var = store.get(f"{key}_var")
        mode = "not_set"
        value = ""
        try:
            if mode_var is not None:
                mode = str(mode_var.get() or "not_set")
        except Exception:
            mode = "not_set"
        try:
            if value_var is not None:
                value = str(value_var.get() or "")
        except Exception:
            value = ""
        return mode, value

    def _apply_contract_tab_generation_overrides(self, prefix: str, extra: list[str]) -> None:
        """Bridge Contract tab fields to generator CLI and legacy batch/single vars."""
        # Club (Contract tab replaces legacy Other-tab club selector for generation)
        club_mode, club_value = self._get_contract_tab_field_mode_value(prefix, "club_contract_club")
        try:
            contract_filt = getattr(self, f"{prefix}_contract_club_gender_filter", None)
            legacy_filt = getattr(self, f"{prefix}_club_gender_filter", None)
            if contract_filt is not None and legacy_filt is not None:
                legacy_filt.set(contract_filt.get() or "Any")
        except Exception:
            pass
        try:
            if hasattr(self, f"{prefix}_club_mode"):
                if club_mode == "custom":
                    getattr(self, f"{prefix}_club_mode").set("fixed")
                    getattr(self, f"{prefix}_club_dont_set").set(False)
                    getattr(self, f"{prefix}_club_sel").set(club_value)
                elif club_mode == "random":
                    getattr(self, f"{prefix}_club_mode").set("random")
                    getattr(self, f"{prefix}_club_dont_set").set(False)
                else:
                    getattr(self, f"{prefix}_club_mode").set("random")
                    getattr(self, f"{prefix}_club_dont_set").set(True)
        except Exception:
            pass

        # Date fields (map contract-tab random/custom/not_set to existing fixed/random/none vars)
        date_bridge = [
            ("club_contract_moved_to_based_nation_date", f"{prefix}_moved_to_nation_mode", f"{prefix}_moved_to_nation_date", "moved_to_nation_date"),
            ("club_contract_date_joined", f"{prefix}_joined_club_mode", f"{prefix}_joined_club_date", "joined_club_date"),
            ("club_contract_expires_date", f"{prefix}_contract_expires_mode", f"{prefix}_contract_expires_date", "contract_expires_date"),
        ]
        for ckey, mode_attr, date_attr, omit_key in date_bridge:
            mode, value = self._get_contract_tab_field_mode_value(prefix, ckey)
            try:
                if hasattr(self, mode_attr):
                    if mode == "custom":
                        getattr(self, mode_attr).set("fixed")
                    elif mode == "random":
                        getattr(self, mode_attr).set("random")
                    else:
                        getattr(self, mode_attr).set("none")
                if hasattr(self, date_attr):
                    getattr(self, date_attr).set(value)
            except Exception:
                pass
            if mode == "not_set":
                extra.extend(["--omit-field", omit_key])

        # Last signed date (new CLI bridge)
        last_mode, last_value = self._get_contract_tab_field_mode_value(prefix, "club_contract_last_contract_signed_date")
        if last_mode == "not_set":
            extra.extend(["--omit-field", "date_last_signed"])
        elif last_mode == "custom":
            try:
                self._parse_date_yyyy_mm_dd(last_value)
            except Exception:
                raise ValueError(f"Contract tab: invalid Date Last Contract Signed (use YYYY-MM-DD): {last_value}")
            extra.extend(["--date_last_signed", last_value])

        # Wage (per week) bridge (Contract tab controls wage)
        wage_mode, wage_value = self._get_contract_tab_field_mode_value(prefix, "club_contract_wage_per_week")
        store = getattr(self, f"{prefix}_club_contract_vars", {}) or {}
        wage_min_v = store.get("club_contract_wage_per_week_min_var")
        wage_max_v = store.get("club_contract_wage_per_week_max_var")

        if wage_mode == "not_set":
            extra.extend(["--omit-field", "wage"])
        elif wage_mode == "custom":
            try:
                getattr(self, f"{prefix}_wage_dont_set").set(False)
            except Exception:
                pass

            wv = (wage_value or "").strip()
            if not wv:
                raise ValueError("Contract tab: Wage (per week) is set to Custom but no value was entered")
            try:
                int(wv)
            except Exception:
                raise ValueError(f"Contract tab: invalid Wage (per week): {wv}")
            if prefix == "batch":
                self.batch_wage_mode.set("fixed")
                self.batch_wage_fixed.set(wv)
            else:
                self.single_wage_mode.set("fixed")
                self.single_wage_fixed.set(wv)
        elif wage_mode == "random":
            try:
                getattr(self, f"{prefix}_wage_dont_set").set(False)
            except Exception:
                pass

            wmin = ""
            wmax = ""
            try:
                if wage_min_v is not None:
                    wmin = str(wage_min_v.get() or "").strip()
            except Exception:
                wmin = ""
            try:
                if wage_max_v is not None:
                    wmax = str(wage_max_v.get() or "").strip()
            except Exception:
                wmax = ""

            # If blank, fall back to safe defaults
            if not wmin:
                wmin = "30"
            if not wmax:
                wmax = "80"

            try:
                wmin_i = int(float(wmin))
                wmax_i = int(float(wmax))
            except Exception:
                raise ValueError(f"Contract tab: invalid Wage range (min/max): {wmin} to {wmax}")

            if wmin_i > wmax_i:
                raise ValueError(f"Contract tab: Wage range min cannot be greater than max: {wmin_i} > {wmax_i}")

            if prefix == "batch":
                self.batch_wage_mode.set("random")
                self.batch_wage_min.set(str(wmin_i))
                self.batch_wage_max.set(str(wmax_i))
            else:
                self.single_wage_mode.set("random")
                self.single_wage_min.set(str(wmin_i))
                self.single_wage_max.set(str(wmax_i))

    # Squad status (new CLI bridge)
        squad_mode, squad_value = self._get_contract_tab_field_mode_value(prefix, "club_contract_squad_status")
        if squad_mode == "not_set":
            extra.extend(["--omit-field", "squad_status"])
        elif squad_mode == "custom":
            squad_map = {
                "Key Player": 6,
                "Important Player": 7,
                "Regular Starter": 8,
                "Squad Player": 9,
                "Fringe Player": 10,
                "Emergency Backup": 11,
            }
            sv = (squad_value or "").strip()
            if sv.isdigit():
                squad_id = int(sv)
            else:
                if sv not in squad_map:
                    raise ValueError(f"Contract tab: unknown Squad Status '{sv}'")
                squad_id = squad_map[sv]
            extra.extend(["--squad_status", str(squad_id)])
