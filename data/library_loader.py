# -*- coding: utf-8 -*-
from __future__ import annotations


import tkinter as tk

import csv
from pathlib import Path


class LibraryLoaderMixin:
    def _get_current_master_library_path(self) -> str:
        try:
            p = (getattr(self, "batch_clubs", None).get() or "").strip() if hasattr(self, "batch_clubs") else ""
        except Exception:
            p = ""
        if not p:
            try:
                p = (getattr(self, "single_clubs", None).get() or "").strip() if hasattr(self, "single_clubs") else ""
            except Exception:
                p = ""
        return p

    def _current_master_library_sig(self):
        try:
            p = self._get_current_master_library_path()
            if not p:
                return None
            pp = Path(p)
            if not pp.exists():
                return None
            st = pp.stat()
            return (str(pp), int(st.st_mtime_ns), int(st.st_size))
        except Exception:
            return None

    def _reload_master_library(self) -> None:
        path = ""
        if hasattr(self, "batch_clubs"):
            path = self.batch_clubs.get().strip()
        if not path and hasattr(self, "single_clubs"):
            path = self.single_clubs.get().strip()

        if not path or not Path(path).exists():
            self._log("[WARN] master_library.csv not found — cannot populate club/city/nation pickers.\n")
            self._master_library_last_sig = None
            return

        clubs: list[str] = []
        cities: list[str] = []
        nations: list[str] = []
        club_map: dict[str, tuple[str, str]] = {}
        city_map: dict[str, tuple[str, str]] = {}
        nation_map: dict[str, tuple[str, str]] = {}

        try:
            with open(path, newline="", encoding="utf-8-sig") as f:
                rdr = csv.DictReader(f)
                for row in rdr:
                    kind = (row.get("kind") or "").strip().lower()
                    if kind == "club":
                        dbid = (row.get("club_dbid") or "").strip()
                        lg = (row.get("ttea_large") or "").strip()
                        name = (row.get("club_name") or "").strip()
                        if not dbid or not lg:
                            continue
                        label = self._mk_master_label("club", name, dbid)
                        clubs.append(label)
                        club_map[label] = (dbid, lg)
                        cg = self._normalize_club_gender(row.get("club_gender") or row.get("gender") or "")
                        if cg in ("m", "men", "male", "boys"):
                            cg = "male"
                        elif cg in ("f", "women", "woman", "female", "girls", "ladies"):
                            cg = "female"
                        else:
                            cg = "any"
                        if not hasattr(self, "_club_gender_map"):
                            self._club_gender_map = {}
                        self._club_gender_map[label] = cg
                    elif kind == "city":
                        dbid = (row.get("city_dbid") or "").strip()
                        lg = (row.get("city_large") or "").strip()
                        name = (row.get("city_name") or "").strip()
                        if not dbid or not lg:
                            continue
                        label = self._mk_master_label("city", name, dbid)
                        cities.append(label)
                        city_map[label] = (dbid, lg)
                    elif kind == "nation":
                        dbid = (row.get("nation_dbid") or "").strip()
                        lg = ((row.get("nnat_large") or "") or (row.get("nation_large") or "") or (row.get("large") or "") or (row.get("large_id") or "")).strip()
                        name = (row.get("nation_name") or "").strip()
                        if not dbid or not lg:
                            continue
                        label = self._mk_master_label("nation", name, dbid)
                        nations.append(label)
                        nation_map[label] = (dbid, lg)
        except Exception as e:
            self._log("[ERROR] Failed to read master_library.csv for pickers: " + str(e) + "\n")
            return

        clubs.sort(key=lambda x: x.lower())
        cities.sort(key=lambda x: x.lower())
        nations.sort(key=lambda x: x.lower())

        self._club_map = club_map
        self._city_map = city_map
        self._nation_map = nation_map
        self._club_labels_all = list(clubs)
        if not hasattr(self, "_club_gender_map"):
            self._club_gender_map = {}

        for attr, values in [
            ("batch_city_combo", cities),
            ("batch_nation_combo", nations),
            ("batch_details_city_combo", cities),
            ("batch_details_region_combo", nations),
            ("single_city_combo", cities),
            ("single_nation_combo", nations),
            ("single_details_city_combo", cities),
            ("single_details_region_combo", nations),
        ]:
            cb = getattr(self, attr, None)
            if cb is not None:
                try:
                    cb["values"] = values
                except Exception:
                    pass
        self._apply_club_filter('batch')
        self._apply_club_filter('single')
        self._apply_club_filter('batch_contract')
        self._apply_club_filter('single_contract')

        try:
            self._master_library_last_sig = self._current_master_library_sig()
        except Exception:
            pass
        self._log(f"[OK] Loaded library pickers: clubs={len(clubs)}, cities={len(cities)}, nations={len(nations)}\n")

    def _poll_master_library_changes(self) -> None:
        try:
            p = Path(self._get_current_master_library_path())
            if p.exists():
                mt = p.stat().st_mtime
                if getattr(self, "_master_last_mtime", None) is None:
                    self._master_last_mtime = mt
                elif mt != self._master_last_mtime:
                    self._master_last_mtime = mt
                    self._reload_master_library()
        except Exception:
            pass
        try:
            self.after(1200, self._poll_master_library_changes)
        except Exception:
            pass


    def _load_master_library_rows(self, kind="city"):
        """Load rows from master_library.csv and yield dict rows filtered by kind."""
        path = ""
        try:
            if hasattr(self, "batch_clubs"):
                path = (self.batch_clubs.get() or "").strip()
        except Exception:
            path = ""
        if not path:
            try:
                if hasattr(self, "single_clubs"):
                    path = (self.single_clubs.get() or "").strip()
            except Exception:
                path = ""
        if not path:
            # Best-effort default in SI editor data folder
            try:
                base = (self.fm_data_dir.get() or "").strip()
                if base:
                    candidate = Path(base) / "master_library.csv"
                    if candidate.exists():
                        path = str(candidate)
            except Exception:
                pass
        if not path or not Path(path).exists():
            return []

        norm_kind = (kind or "").strip().lower()
        out = []
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as f:
                rdr = csv.DictReader(f)
                for row in rdr:
                    row_kind = (row.get("kind") or row.get("type") or row.get("item_type") or "").strip().lower()
                    if row_kind != norm_kind:
                        continue
                    # Prefer names only; keep row raw for mapping later
                    out.append(row)
        except Exception as e:
            try:
                self._log(f"[WARN] Failed reading master_library.csv for {norm_kind}: {e}\n")
            except Exception:
                pass
            return []
        return out

    def _init_batch_single_file_sync(self) -> None:
        """Sync shared file/script inputs between Batch and Single and auto-reload master library on change."""
        self._path_sync_guard = False
        self._master_reload_job = None

        pairs = [
            ("batch_clubs", "single_clubs", True),            # master_library.csv
            ("batch_first", "single_first", False),           # first names csv
            ("batch_female_first", "single_female_first", False),  # female first names csv
            ("batch_common_names", "single_common_names", False),   # common names csv
            ("batch_surn", "single_surn", False),             # surnames csv
            ("batch_script", "single_script", False),         # generator script
            ("batch_region_map_csv", "single_region_map_csv", False),  # region mapping csv placeholder
        ]

        for a_name, b_name, is_master in pairs:
            if not (hasattr(self, a_name) and hasattr(self, b_name)):
                continue
            a_var = getattr(self, a_name)
            b_var = getattr(self, b_name)
            try:
                a_var.trace_add("write", lambda *args, s=a_var, d=b_var, m=is_master: self._sync_path_vars(s, d, m))
                b_var.trace_add("write", lambda *args, s=b_var, d=a_var, m=is_master: self._sync_path_vars(s, d, m))
            except Exception:
                pass

    def _sync_path_vars(self, src_var: tk.StringVar, dst_var: tk.StringVar, is_master: bool = False) -> None:
        if getattr(self, "_path_sync_guard", False):
            return
        try:
            self._path_sync_guard = True
            v = src_var.get()
            try:
                if dst_var.get() != v:
                    dst_var.set(v)
            except Exception:
                pass
        finally:
            self._path_sync_guard = False

        if is_master:
            self._schedule_master_library_reload()

    def _start_master_library_watch(self, interval_ms: int = 1200) -> None:
        try:
            old = getattr(self, "_master_library_watch_job", None)
            if old:
                self.after_cancel(old)
        except Exception:
            pass

        def _tick():
            self._master_library_watch_job = None
            try:
                sig = self._current_master_library_sig()
                last = getattr(self, "_master_library_last_sig", None)
                if sig and last and sig != last:
                    self._reload_master_library()
                elif sig and last is None:
                    self._master_library_last_sig = sig
            except Exception:
                pass
            finally:
                try:
                    self._master_library_watch_job = self.after(max(500, int(interval_ms)), _tick)
                except Exception:
                    pass

        try:
            self._master_library_watch_job = self.after(max(500, int(interval_ms)), _tick)
        except Exception:
            pass

    def _schedule_master_library_reload(self, delay_ms: int = 350) -> None:
        """Debounced auto-reload for master_library when path changes (including manual typing/paste)."""
        try:
            job = getattr(self, "_master_reload_job", None)
            if job:
                self.after_cancel(job)
        except Exception:
            pass

        def _run():
            self._master_reload_job = None
            try:
                path = ""
                if hasattr(self, "batch_clubs"):
                    path = (self.batch_clubs.get() or "").strip()
                if not path and hasattr(self, "single_clubs"):
                    path = (self.single_clubs.get() or "").strip()
                if path and Path(path).exists():
                    self._reload_master_library()
            except Exception as e:
                try:
                    self._log(f"[WARN] Auto-reload master_library.csv failed: {e}\n")
                except Exception:
                    pass

        try:
            self._master_reload_job = self.after(max(50, int(delay_ms)), _run)
        except Exception:
            self._master_reload_job = None
