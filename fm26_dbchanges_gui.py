#!/usr/bin/env python3
"""
fm26_dbchanges_gui.py

Cross-platform (Windows/macOS/Linux) GUI for:
1) Extracting clubs/cities from FM "db_changes" XML into clubs_cities.csv
2) Generating bulk youth players FM26 editor XML with stable (seeded) IDs.

Requires: Python 3.9+ with Tkinter available.
"""

from __future__ import annotations

import os
import sys
import threading
import subprocess
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "FM26 DBChanges Tools (Extractor + Youth Generator)"

DEFAULT_EXTRACT_SCRIPT = "fm_dbchanges_extract_fixed_v4.py"
DEFAULT_GENERATE_SCRIPT = "fm26_bulk_youth_generator.py"

@dataclass
class RunResult:
    rc: int
    out: str
    err: str


def _run_subprocess(cmd: list[str]) -> RunResult:
    p = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return RunResult(rc=p.returncode, out=p.stdout, err=p.stderr)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x680")
        self.minsize(880, 580)

        self.base_dir = Path(__file__).resolve().parent

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)

        self.extract_tab = ttk.Frame(self.notebook)
        self.gen_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.extract_tab, text="Extractor")
        self.notebook.add(self.gen_tab, text="Youth Generator")

        self._build_extractor_tab()
        self._build_generator_tab()

        # Shared output panel
        bottom = ttk.Frame(self)
        bottom.pack(fill="both", expand=False, padx=10, pady=(0, 10))

        ttk.Label(bottom, text="Log output:").pack(anchor="w")
        self.log = tk.Text(bottom, height=12, wrap="word")
        self.log.pack(fill="both", expand=True)
        self._log(f"{APP_TITLE}\nPython: {sys.version.split()[0]} ({sys.executable})\n")

    def _log(self, msg: str) -> None:
        self.log.insert("end", msg)
        if not msg.endswith("\n"):
            self.log.insert("end", "\n")
        self.log.see("end")

    # ---------------- Extractor UI ----------------
    def _build_extractor_tab(self) -> None:
        frm = self.extract_tab

        def row(parent, r, label, var, browse_cb):
            ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ent = ttk.Entry(parent, textvariable=var)
            ent.grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            ttk.Button(parent, text="Browse…", command=browse_cb).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        frm.columnconfigure(1, weight=1)

        self.extract_xml = tk.StringVar(value="")
        self.extract_out = tk.StringVar(value=str(self.base_dir / "clubs_cities.csv"))
        self.extract_script = tk.StringVar(value=str(self.base_dir / DEFAULT_EXTRACT_SCRIPT))

        row(frm, 0, "Input XML (db_changes):", self.extract_xml, self._pick_xml_for_extract)
        row(frm, 1, "Output CSV:", self.extract_out, self._pick_csv_out)
        row(frm, 2, "Extractor script:", self.extract_script, self._pick_py_script)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 6))
        btns.columnconfigure(0, weight=1)
        ttk.Button(btns, text="Run Extractor", command=self._run_extractor).grid(row=0, column=0, sticky="w")

        hint = ("Tip: output is a single CSV containing both clubs and cities.\n"
                "You can open it in Excel; the *_text columns are Excel-safe for large integers.")
        ttk.Label(frm, text=hint, foreground="#444").grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))

    def _pick_xml_for_extract(self) -> None:
        p = filedialog.askopenfilename(title="Select db_changes XML", filetypes=[("XML files", "*.xml"), ("All files", "*.*")])
        if p:
            self.extract_xml.set(p)

    def _pick_csv_out(self) -> None:
        p = filedialog.asksaveasfilename(title="Save CSV as", defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if p:
            self.extract_out.set(p)

    def _pick_py_script(self) -> None:
        p = filedialog.askopenfilename(title="Select Python script", filetypes=[("Python files", "*.py"), ("All files", "*.*")])
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

        cmd = [sys.executable, script_path, "--xml", xml_path, "--out", out_path]
        self._run_async("Extractor", cmd)

    # ---------------- Generator UI ----------------
    def _build_generator_tab(self) -> None:
        frm = self.gen_tab
        frm.columnconfigure(1, weight=1)

        self.gen_clubs = tk.StringVar(value=str(self.base_dir / "clubs_cities.csv"))
        self.gen_first = tk.StringVar(value=str(self.base_dir / "scottish_male_first_names_2500.csv"))
        self.gen_surn = tk.StringVar(value=str(self.base_dir / "scottish_surnames_2500.csv"))
        self.gen_out = tk.StringVar(value=str(self.base_dir / "fm26_youth.xml"))
        self.gen_script = tk.StringVar(value=str(self.base_dir / DEFAULT_GENERATE_SCRIPT))

        self.gen_count = tk.StringVar(value="1000")
        self.gen_seed = tk.StringVar(value="123")
        self.gen_age_min = tk.StringVar(value="14")
        self.gen_age_max = tk.StringVar(value="16")
        self.gen_ca_min = tk.StringVar(value="20")
        self.gen_ca_max = tk.StringVar(value="160")
        self.gen_pa_min = tk.StringVar(value="80")
        self.gen_pa_max = tk.StringVar(value="200")
        self.gen_base_year = tk.StringVar(value="2026")

        def row_file(r, label, var, is_save=False):
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ent = ttk.Entry(frm, textvariable=var)
            ent.grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            if is_save:
                btn = ttk.Button(frm, text="Browse…", command=lambda: self._pick_save_xml(var))
            else:
                btn = ttk.Button(frm, text="Browse…", command=lambda: self._pick_open_file(var))
            btn.grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "clubs_cities.csv:", self.gen_clubs, is_save=False)
        row_file(1, "First names CSV:", self.gen_first, is_save=False)
        row_file(2, "Surnames CSV:", self.gen_surn, is_save=False)
        row_file(3, "Output XML:", self.gen_out, is_save=True)
        row_file(4, "Generator script:", self.gen_script, is_save=False)

        # Options grid
        opt = ttk.LabelFrame(frm, text="Generation options")
        opt.grid(row=5, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 8))
        for c in range(6):
            opt.columnconfigure(c, weight=1)

        def opt_field(r, c, label, var, width=10):
            ttk.Label(opt, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=6)
            e = ttk.Entry(opt, textvariable=var, width=width)
            e.grid(row=r, column=c+1, sticky="w", padx=6, pady=6)

        opt_field(0, 0, "Count", self.gen_count)
        opt_field(0, 2, "Seed", self.gen_seed)
        opt_field(0, 4, "Base year", self.gen_base_year)

        opt_field(1, 0, "Age min", self.gen_age_min)
        opt_field(1, 2, "Age max", self.gen_age_max)
        opt_field(1, 4, "CA min", self.gen_ca_min)

        opt_field(2, 0, "CA max", self.gen_ca_max)
        opt_field(2, 2, "PA min", self.gen_pa_min)
        opt_field(2, 4, "PA max", self.gen_pa_max)

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 6))
        btns.columnconfigure(0, weight=1)
        ttk.Button(btns, text="Run Generator", command=self._run_generator).grid(row=0, column=0, sticky="w")

        hint = ("Note: Football Manager editor import only accepts one XML at a time for db_changes.\n"
                "This generator always produces ONE combined XML file.")
        ttk.Label(frm, text=hint, foreground="#444").grid(row=7, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))

    def _pick_open_file(self, var: tk.StringVar) -> None:
        p = filedialog.askopenfilename(title="Select file", filetypes=[("All files", "*.*")])
        if p:
            var.set(p)

    def _pick_save_xml(self, var: tk.StringVar) -> None:
        p = filedialog.asksaveasfilename(title="Save XML as", defaultextension=".xml", filetypes=[("XML files", "*.xml")])
        if p:
            var.set(p)

    def _run_generator(self) -> None:
        script_path = self.gen_script.get().strip()
        if not script_path or not Path(script_path).exists():
            messagebox.showerror("Missing script", "Please choose a valid generator .py script.")
            return

        def must_exist(path: str, label: str) -> bool:
            if not path or not Path(path).exists():
                messagebox.showerror("Missing input", f"Please choose a valid {label} file.")
                return False
            return True

        if not must_exist(self.gen_clubs.get().strip(), "clubs_cities.csv"):
            return
        if not must_exist(self.gen_first.get().strip(), "first names"):
            return
        if not must_exist(self.gen_surn.get().strip(), "surnames"):
            return

        out_path = self.gen_out.get().strip()
        if not out_path:
            messagebox.showerror("Missing output", "Please choose an output XML path.")
            return

        # Build CLI
        cmd = [
            sys.executable,
            script_path,
            "--clubs_cities", self.gen_clubs.get().strip(),
            "--first_names", self.gen_first.get().strip(),
            "--surnames", self.gen_surn.get().strip(),
            "--count", self.gen_count.get().strip(),
            "--output", out_path,
            "--age_min", self.gen_age_min.get().strip(),
            "--age_max", self.gen_age_max.get().strip(),
            "--ca_min", self.gen_ca_min.get().strip(),
            "--ca_max", self.gen_ca_max.get().strip(),
            "--pa_min", self.gen_pa_min.get().strip(),
            "--pa_max", self.gen_pa_max.get().strip(),
            "--base_year", self.gen_base_year.get().strip(),
        ]

        seed = self.gen_seed.get().strip()
        if seed:
            cmd.extend(["--seed", seed])

        self._run_async("Generator", cmd)

    # ---------------- Shared async runner ----------------
    def _run_async(self, title: str, cmd: list[str]) -> None:
        self._log("\n" + "=" * 80)
        self._log(f"{title} command:\n  " + " ".join([_quote(x) for x in cmd]) + "\n")

        def worker():
            try:
                res = _run_subprocess(cmd)
            except Exception as e:
                self.after(0, lambda: self._log(f"[ERROR] {e}\n"))
                return

            def finish():
                if res.out:
                    self._log(res.out)
                if res.err:
                    self._log(res.err)
                if res.rc == 0:
                    self._log(f"[OK] {title} finished successfully.\n")
                else:
                    self._log(f"[FAIL] {title} exited with code {res.rc}.\n")
                    messagebox.showerror(f"{title} failed", f"{title} failed (exit code {res.rc}).\nCheck the log output.")
            self.after(0, finish)

        threading.Thread(target=worker, daemon=True).start()


def _quote(s: str) -> str:
    if not s:
        return '""'
    if any(ch in s for ch in " \t\n\""):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def main() -> int:
    # Helpful message if tkinter isn't available
    try:
        app = App()
    except tk.TclError as e:
        print("Tkinter UI could not start. On Linux you may need to install Tk support, e.g.")
        print("  sudo apt-get install python3-tk")
        print(f"Error: {e}")
        return 2

    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
