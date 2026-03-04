# -*- coding: utf-8 -*-
from __future__ import annotations

class LibraryParsingHelpersMixin:
    def _mk_master_label(self, kind: str, name: str, dbid: str) -> str:
        kind_l = (kind or '').strip().lower()
        name = (name or '').strip()
        dbid = (dbid or '').strip()
        prefix = {'club':'Club','city':'City','nation':'Nation'}.get(kind_l, kind_l.title() or 'Item')
        if name:
            return f"{name} (DBID {dbid})"
        return f"{prefix} DBID {dbid}"

    def _normalize_club_gender(self, raw: str) -> str:
        cg = (raw or '').strip().lower()
        if cg in ('m','men','male','boys'):
            return 'male'
        if cg in ('f','women','female','girls'):
            return 'female'
        return ''

    def _apply_club_filter(self, which: str):
        try:
            all_clubs = list(getattr(self, "_club_labels_all", []))
            gender_map = getattr(self, "_club_gender_map", {})
            if which == "batch":
                combo = getattr(self, "batch_club_combo", None)
                sel_var = getattr(self, "batch_club_sel", None)
                filt_var = getattr(self, "batch_club_gender_filter", None)
            elif which == "single":
                combo = getattr(self, "single_club_combo", None)
                sel_var = getattr(self, "single_club_sel", None)
                filt_var = getattr(self, "single_club_gender_filter", None)
            elif which == "batch_contract":
                combo = getattr(self, "batch_contract_club_combo", None)
                sel_var = getattr(self, "batch_contract_club_sel", None)
                filt_var = getattr(self, "batch_contract_club_gender_filter", None)
            elif which == "single_contract":
                combo = getattr(self, "single_contract_club_combo", None)
                sel_var = getattr(self, "single_contract_club_sel", None)
                filt_var = getattr(self, "single_contract_club_gender_filter", None)
            else:
                combo = None
                sel_var = None
                filt_var = None
            if combo is None:
                return
            filt = (filt_var.get().strip().lower() if filt_var is not None else "any")
            if filt in ("", "any"):
                vals = all_clubs
            else:
                vals = [c for c in all_clubs if gender_map.get(c, "any") in (filt, "any", "")]
            combo["values"] = vals
            if sel_var is not None and sel_var.get() and sel_var.get() not in vals:
                sel_var.set("")
        except Exception:
            pass

