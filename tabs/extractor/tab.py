# -*- coding: utf-8 -*-
# Auto-generated from fm26_generator_gui_2.py
# Extractor tab extracted into a mixin to reduce main GUI file size.


from __future__ import annotations

import sys
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# --- defaults bridge (import from main GUI when available) ---
try:
    from __main__ import DEFAULT_EXTRACT_SCRIPT, DEFAULT_GENERATE_SCRIPT, DEFAULT_XML_APPENDER_SCRIPT  # type: ignore
except Exception:
    DEFAULT_EXTRACT_SCRIPT = "fm26_db_extractor.py"
    DEFAULT_GENERATE_SCRIPT = "fm26_people_generator.py"
    DEFAULT_XML_APPENDER_SCRIPT = "fm26_xml_appender.py"
# --- end defaults bridge ---




def ensure_parent_dir(file_path: str) -> None:
    p = Path(file_path).expanduser()
    p.parent.mkdir(parents=True, exist_ok=True)


class ExtractorTabMixin:
    def _build_extractor_tab(self) -> None:
        frm = self.extract_tab
        frm.columnconfigure(1, weight=1)

        def row(parent, r, label, var, browse_cb):
            ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ent = ttk.Entry(parent, textvariable=var)
            ent.grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            ttk.Button(parent, text="Browse…", command=browse_cb).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        self.extract_xml = tk.StringVar(value="")
        self.extract_out = tk.StringVar(value=str(self.fmdata_dir / "master_library.csv"))
        self.extract_script = tk.StringVar(value=str(self.fmdata_dir / DEFAULT_EXTRACT_SCRIPT))

        row(frm, 0, "Input XML (db_changes):", self.extract_xml, self._pick_xml_for_extract)
        row(frm, 1, "Output CSV (master_library.csv):", self.extract_out, self._pick_csv_out)
        row(frm, 2, "Extractor script:", self.extract_script, self._pick_py_script)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 6))
        ttk.Button(btns, text="Run Extractor (Cities,Clubs,Nations and Regions)", command=self._run_extractor).pack(anchor="w")

        hint = (
            "Tip:\n"
            "- Output is ONE CSV containing clubs, cities, and nations.\n"
            "- *_text columns are Excel-safe for huge integers.\n"
        )
        ttk.Label(frm, text=hint, foreground="#444").grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))

    def _pick_xml_for_extract(self) -> None:
        p = filedialog.askopenfilename(
            title="Select db_changes XML",
            initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)),
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if p:
            self.extract_xml.set(p)

    def _pick_csv_out(self) -> None:
        p = filedialog.asksaveasfilename(
            title="Save CSV as",
            initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)),
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if p:
            self.extract_out.set(p)

    def _pick_py_script(self) -> None:
        p = filedialog.askopenfilename(
            title="Select Python script",
            initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)),
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )
        if p:
            self.extract_script.set(p)

    def _run_extractor(self) -> None:
        xml_path = self.extract_xml.get().strip()
        out_path = self.extract_out.get().strip()
        script_path = self.extract_script.get().strip()

        if not xml_path or not Path(xml_path).exists():
            messagebox.showerror("Missing input", "Please choose a valid input XML file.")
            return
        if not script_path or not Path(script_path).exists():
            messagebox.showerror("Missing script", "Please choose a valid extractor .py script.")
            return
        if not out_path:
            messagebox.showerror("Missing output", "Please choose an output CSV file path.")
            return

        try:
            ensure_parent_dir(out_path)
        except Exception as e:
            messagebox.showerror("Output folder error", f"Could not create output folder:\n{e}")
            return

        cmd = [sys.executable, script_path, "--xml", xml_path, "--out", out_path]
        self._run_async_stream("Extractor", cmd, must_create=out_path)

    # ---------------- Players (Batch) UI ----------------
