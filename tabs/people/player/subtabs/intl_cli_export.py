# -*- coding: utf-8 -*-


from __future__ import annotations

class InternationalCliExportMixin:
    """Append International tab values to generator CLI args (no monkey-patching)."""

    def _append_international_data_cli_args(self, extra: list, prefix: str) -> None:
        def _gv(attr: str, default: str = "") -> str:
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
