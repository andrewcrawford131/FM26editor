# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox

class DetailsDontSetMixin:

    def _autoclear_dontset(self, src_var, dont_set_var) -> None:
        """When src_var changes, clear dont_set_var.
        Prevents accidental --omit-field when user selected Random/Range."""
        try:
            src_var.trace_add("write", lambda *_: dont_set_var.set(False))
        except Exception:
            pass

    def _append_details_dontset_cli_args(self, extra: list, prefix: str) -> None:
            """Append --omit-field flags for Details fields set to Don't set."""
            def _mode(name: str, default: str = "random") -> str:
                v = getattr(self, f"{prefix}_details_{name}_mode", None)
                if v is None:
                    return default
                try:
                    return str(v.get() or default).strip().lower()
                except Exception:
                    return default

            def _append_omit(name: str) -> None:
                extra.extend(["--omit-field", name])

            # Details rows that map directly to generator field keys.
            for key in (
                "first_name",
                "second_name",
                "common_name",
                "full_name",
                "gender",
                "ethnicity",
                "hair_colour",
                "hair_length",
                "skin_tone",
                "body_type",
                "city_of_birth",
                "nation",
                "nationality_info",
                "declared_for_youth_nation",
            ):
                if _mode(key) == "none":
                    _append_omit(key)

            # Shared DOB mode (used by Details compact DOB block)
            try:
                dob_mode = str(getattr(self, f"{prefix}_dob_mode").get() or "age").strip().lower()
                if dob_mode == "none":
                    _append_omit("dob")
            except Exception:
                pass

            # Preferred Details height block mode (mode2); fall back to legacy details_height_mode if present
            try:
                h_mode = ""
                if hasattr(self, f"{prefix}_details_height_mode2"):
                    h_mode = str(getattr(self, f"{prefix}_details_height_mode2").get() or "").strip().lower()
                elif hasattr(self, f"{prefix}_details_height_mode"):
                    h_mode = str(getattr(self, f"{prefix}_details_height_mode").get() or "").strip().lower()
                if h_mode == "none":
                    _append_omit("height")
            except Exception:
                pass

            def _append_international_data_cli_args(self, extra: list, prefix: str) -> None:
                """Append International Data tab fields (custom values only) to generator CLI args."""
            def _gv(attr: str, default: str = "") -> str:
                v = getattr(self, attr, None)
                if v is None:
                    return default
                try:
                    return v.get()
                except Exception:
                    return default

            # Integer counters
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
                elif mode == "custom" and val != "":
                    try:
                        extra.extend([arg, str(int(val))])
                    except Exception:
                        raise ValueError(f"{key.replace('_', ' ').title()} must be an integer")
                else:
                    # random/auto => generator estimates based on age/PA/nation strength
                    extra.extend([arg, "-2"])

            # Date strings (generator validates/parses YYYY-MM-DD)
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

            # Nation strings (GUI passes display text; generator resolves via master library nations)
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

            # Other Nation Caps / Youth Caps list payloads (JSON strings)
            import json as _json
            for list_key, arg in [
                ("other_nation_caps", "--other_nation_caps_json"),
                ("other_nation_youth_caps", "--other_nation_youth_caps_json"),
            ]:
                mode = str(getattr(self, f"{prefix}_{list_key}_mode", tk.StringVar(value="none")).get() or "none").strip().lower()
                items = getattr(self, f"{prefix}_{list_key}_items", None) or []
                if mode == "none":
                    continue
                if mode == "random":
                    # Not yet implemented: treat Random as 'auto' (no fixed list sent)
                    continue

                payload = []
                for rec in items:
                    if not isinstance(rec, dict):
                        continue
                    nation = str(rec.get("nation", "") or "").strip()
                    if not nation:
                        continue
                    apps = str(rec.get("apps", "0") or "0").strip()
                    goals = str(rec.get("goals", "0") or "0").strip()
                    try:
                        apps_i = int(float(apps)) if apps != "" else 0
                        goals_i = int(float(goals)) if goals != "" else 0
                    except Exception:
                        raise ValueError(f"{list_key.replace('_', ' ').title()} values must be integers")
                    payload.append({"nation": nation, "apps": apps_i, "goals": goals_i})
                if payload:
                    extra.extend([arg, _json.dumps(payload, separators=(",", ":"))])



