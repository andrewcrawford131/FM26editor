# -*- coding: utf-8 -*-
"""XML Appender actions extracted from fm26_generator_gui_2.py

This mixin supplies picker helpers + list management + Run button handler.
No App monkey-patching.
"""

from __future__ import annotations



import sys
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox


class XmlAppenderActionsMixin:
    def _pick_py_script_var(self, var: tk.StringVar) -> None:
        p = filedialog.askopenfilename(
            title="Select Python script",
            initialdir=str(getattr(self, "fmdata_dir", getattr(self, "fm_dir", Path.cwd()))),
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
        )
        if p:
            var.set(p)

    def _pick_xml_target_open(self, var: tk.StringVar) -> None:
        p = filedialog.askopenfilename(
            title="Select target db_changes XML",
            initialdir=str(getattr(self, "fmdata_dir", getattr(self, "fm_dir", Path.cwd()))),
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
        )
        if p:
            var.set(p)

    def _pick_xml_output_save(self, var: tk.StringVar) -> None:
        p = filedialog.asksaveasfilename(
            title="Save merged XML as",
            initialdir=str(getattr(self, "fmdata_dir", getattr(self, "fm_dir", Path.cwd()))),
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
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
            if hasattr(self, "appender_sources_count"):
                self.appender_sources_count.set(f"{len(getattr(self, 'appender_sources', []))} source file(s) selected")
        except Exception:
            pass

    def _appender_add_sources(self) -> None:
        picks = filedialog.askopenfilenames(
            title="Select source XML file(s) to append",
            initialdir=str(getattr(self, "fmdata_dir", getattr(self, "fm_dir", Path.cwd()))),
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")],
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
        d = filedialog.askdirectory(
            title="Select folder containing XML files",
            initialdir=str(getattr(self, "fmdata_dir", getattr(self, "fm_dir", Path.cwd()))),
        )
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
        try:
            self._log(f"[OK] XML Appender: added {added} XML file(s) from folder:\n  {folder}\n")
        except Exception:
            pass

    def _appender_remove_selected(self) -> None:
        lb = getattr(self, "appender_sources_listbox", None)
        if lb is None:
            return
        sel = list(lb.curselection())
        if not sel:
            return
        selset = set(int(i) for i in sel)
        keep = [p for idx, p in enumerate(getattr(self, "appender_sources", [])) if idx not in selset]
        self.appender_sources = keep
        self._appender_refresh_source_list()

    def _appender_clear_sources(self) -> None:
        self.appender_sources = []
        self._appender_refresh_source_list()

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
