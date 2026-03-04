# -*- coding: utf-8 -*-
from __future__ import annotations

import re


class IdResolverMixin:
    def _get_fixed_ids(self, kind: str, label: str) -> tuple[str, str] | None:
        """Resolve a picker label to (dbid, large).

        Accepts either:
        - exact picker labels like 'Scotland (DBID 11)'
        - plain names like 'Scotland'
        - 'Nation DBID 11' / 'City DBID 123' fallbacks

        This is deliberately forgiving because some UI pickers store plain names.
        """
        if not label:
            return None

        label_s = str(label).strip()
        if not label_s:
            return None

        if kind == "club":
            mp = getattr(self, "_club_map", {}) or {}
        elif kind == "city":
            mp = getattr(self, "_city_map", {}) or {}
        elif kind == "nation":
            mp = getattr(self, "_nation_map", {}) or {}
        else:
            mp = {}

        # 1) exact match
        hit = mp.get(label_s)
        if hit:
            return hit

        # 2) match by DBID in label
        m = re.search(r"\bDBID\s*(\d+)\b", label_s, flags=re.I)
        if m:
            want = m.group(1)
            for k, v in mp.items():
                try:
                    if re.search(rf"\bDBID\s*{re.escape(want)}\b", str(k), flags=re.I):
                        return v
                except Exception:
                    continue

        # 3) plain-name match (case-insensitive) against the left side of ' (DBID …)'
        want_name = label_s.split("(")[0].strip().lower()
        if want_name:
            for k, v in mp.items():
                try:
                    kname = str(k).split("(")[0].strip().lower()
                except Exception:
                    continue
                if kname == want_name:
                    return v

        return None
