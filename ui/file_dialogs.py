# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

class FileDialogsMixin:
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
    def _pick_open_file(self, var: tk.StringVar) -> None:
        p = filedialog.askopenfilename(title="Select file", initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)), filetypes=[("All files", "*.*")])
        if p:
            var.set(p)
            try:
                is_master_var = (
                    (hasattr(self, "batch_clubs") and var is self.batch_clubs) or
                    (hasattr(self, "single_clubs") and var is self.single_clubs)
                )
            except Exception:
                is_master_var = False
            if is_master_var:
                try:
                    # Keep both tabs in sync if one master_library path is changed from Browse…
                    if hasattr(self, "batch_clubs") and hasattr(self, "single_clubs"):
                        if var is self.batch_clubs:
                            self.single_clubs.set(p)
                        elif var is self.single_clubs:
                            self.batch_clubs.set(p)
                except Exception:
                    pass
                try:
                    self._reload_master_library()
                except Exception as e:
                    try:
                        self._log(f"[WARN] Auto-reload master_library.csv failed: {e}\n")
                    except Exception:
                        pass


    def _pick_save_xml(self, var: tk.StringVar) -> None:
        p = filedialog.asksaveasfilename(
            title="Save XML as",
            initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)),
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml")]
        )
        if p:
            var.set(p)

    # ---------------- Run: Batch ----------------
