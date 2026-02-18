#!/usr/bin/env python3
"""
fm26_dbchanges_gui.py

Cross-platform (Windows/macOS/Linux) GUI for:
1) Extracting clubs/cities from FM "db_changes" XML into master_library.csv
2) Generating bulk youth players FM26 editor XML with stable (seeded) IDs.

This version FIXES:
- Output/Errors box restored (scrollable + resizable)
- Live stdout/stderr streaming into the output box
- Ensures output directories exist (creates folders automatically)
- Defaults output paths to the correct FM26 editor data folder (auto-detect per OS)
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

APP_TITLE = "FM26 DBChanges Tools (Library Extractor + Players Generator)"

DEFAULT_EXTRACT_SCRIPT = "fm_dbchanges_extract_fixed_v4.py"
DEFAULT_GENERATE_SCRIPT = "fm26_bulk_youth_generator.py"


def _quote(s: str) -> str:
    if not s:
        return '""'
    if any(ch in s for ch in " \t\n\""):
        return '"' + s.replace('"', '\\"') + '"'
    return s


def detect_fm26_editor_data_dir() -> Path:
    """
    Auto-detect FM26 "editor data" directory.
    We try common locations per platform; if none exist, we create the first candidate.
    """
    home = Path.home()
    candidates: list[Path] = []

    if sys.platform.startswith("win"):
        # OneDrive path if available
        onedrive = os.environ.get("OneDrive")
        if onedrive:
            candidates.append(Path(onedrive) / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "OneDrive" / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")

    elif sys.platform == "darwin":
        # macOS commonly uses Application Support
        candidates.append(home / "Library" / "Application Support" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")

    else:
        # Linux commonly uses ~/.local/share
        candidates.append(home / ".local" / "share" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")

    for c in candidates:
        if c.exists():
            return c

    # If nothing exists yet, create first candidate
    try:
        candidates[0].mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return candidates[0]


def ensure_parent_dir(file_path: str) -> None:
    p = Path(file_path).expanduser()
    parent = p.parent
    parent.mkdir(parents=True, exist_ok=True)


@dataclass
class StreamResult:
    rc: int


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1060x720")
        self.minsize(980, 620)

        self.base_dir = Path(__file__).resolve().parent
        self.fm_dir = detect_fm26_editor_data_dir()

        # Vertical paned window: top (tabs) + bottom (log)
        self.paned = ttk.Panedwindow(self, orient="vertical")
        self.paned.pack(fill="both", expand=True, padx=10, pady=10)

        # Top area
        top = ttk.Frame(self.paned)
        self.paned.add(top, weight=4)

        self.notebook = ttk.Notebook(top)
        self.notebook.pack(fill="both", expand=True)

        # Tabs
        self.extract_tab = ttk.Frame(self.notebook)
        self.gen_tab = ttk.Frame(self.notebook)

        # Rename labels as requested earlier (library / players)
        self.notebook.add(self.extract_tab, text="Library Extractor (Clubs/Cities)")
        self.notebook.add(self.gen_tab, text="Players Generator")

        # Players sub-tabs (Batch / Single)
        self.players_notebook = ttk.Notebook(self.gen_tab)
        self.players_notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.batch_tab = ttk.Frame(self.players_notebook)
        self.single_tab = ttk.Frame(self.players_notebook)
        self.players_notebook.add(self.batch_tab, text="Batch")
        self.players_notebook.add(self.single_tab, text="Single (1 Player)")

        # Bottom log area
        log_frame = ttk.Frame(self.paned)
        self.paned.add(log_frame, weight=2)

        ttk.Label(log_frame, text="Output / Errors (live):").pack(anchor="w")

        # Scrollable text
        text_wrap = ttk.Frame(log_frame)
        text_wrap.pack(fill="both", expand=True)

        self.log = tk.Text(text_wrap, height=14, wrap="word")
        yscroll = ttk.Scrollbar(text_wrap, orient="vertical", command=self.log.yview)
        self.log.configure(yscrollcommand=yscroll.set)

        self.log.pack(side="left", fill="both", expand=True)
        yscroll.pack(side="right", fill="y")

        self._log(f"{APP_TITLE}\n")
        self._log(f"Python: {sys.version.split()[0]} ({sys.executable})\n")
        self._log(f"Default FM26 editor data folder:\n  {self.fm_dir}\n")

        # Build UI
        self._build_extractor_tab()
        self._build_batch_tab()
        self._build_single_tab()

    def _log(self, msg: str) -> None:
        self.log.insert("end", msg)
        if not msg.endswith("\n"):
            self.log.insert("end", "\n")
        self.log.see("end")

    def _log_threadsafe(self, msg: str) -> None:
        self.after(0, lambda: self._log(msg))

    def _ui_error(self, title: str, message: str) -> None:
        # Always show on UI thread
        def _show():
            self._log(f"[ERROR] {title}: {message}")
            messagebox.showerror(title, message)
        self.after(0, _show)

    # ---------------- Extractor UI ----------------
    def _build_extractor_tab(self) -> None:
        frm = self.extract_tab
        frm.columnconfigure(1, weight=1)

        def row(parent, r, label, var, browse_cb):
            ttk.Label(parent, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ent = ttk.Entry(parent, textvariable=var)
            ent.grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            ttk.Button(parent, text="Browse…", command=browse_cb).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        self.extract_xml = tk.StringVar(value="")
        self.extract_out = tk.StringVar(value=str(self.fm_dir / "master_library.csv"))
        self.extract_script = tk.StringVar(value=str(self.base_dir / DEFAULT_EXTRACT_SCRIPT))

        row(frm, 0, "Input XML (db_changes):", self.extract_xml, self._pick_xml_for_extract)
        row(frm, 1, "Output CSV (master_library.csv):", self.extract_out, self._pick_csv_out)
        row(frm, 2, "Extractor script:", self.extract_script, self._pick_py_script)

        btns = ttk.Frame(frm)
        btns.grid(row=3, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 6))
        ttk.Button(btns, text="Run Library Extractor", command=self._run_extractor).pack(anchor="w")

        hint = (
            "Tip:\n"
            "- Output is ONE CSV containing both clubs and cities.\n"
            "- *_text columns are Excel-safe for huge integers.\n"
        )
        ttk.Label(frm, text=hint, foreground="#444").grid(row=4, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))

    def _pick_xml_for_extract(self) -> None:
        p = filedialog.askopenfilename(
            title="Select db_changes XML",
            initialdir=str(self.fm_dir),
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if p:
            self.extract_xml.set(p)

    def _pick_csv_out(self) -> None:
        p = filedialog.asksaveasfilename(
            title="Save CSV as",
            initialdir=str(self.fm_dir),
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if p:
            self.extract_out.set(p)

    def _pick_py_script(self) -> None:
        p = filedialog.askopenfilename(
            title="Select Python script",
            initialdir=str(self.base_dir),
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

        # Ensure output directory exists
        try:
            ensure_parent_dir(out_path)
        except Exception as e:
            messagebox.showerror("Output folder error", f"Could not create output folder:\n{e}")
            return

        cmd = [sys.executable, script_path, "--xml", xml_path, "--out", out_path]
        self._run_async_stream("Extractor", cmd, must_create=out_path)

    # ---------------- Players (Batch) UI ----------------
    def _build_batch_tab(self) -> None:
        frm = self.batch_tab
        frm.columnconfigure(1, weight=1)

        # Defaults: output to FM editor data folder
        self.batch_clubs = tk.StringVar(value=str(self.fm_dir / "master_library.csv"))
        self.batch_first = tk.StringVar(value=str(self.base_dir / "scottish_male_first_names_2500.csv"))
        self.batch_surn = tk.StringVar(value=str(self.base_dir / "scottish_surnames_2500.csv"))
        self.batch_out = tk.StringVar(value=str(self.fm_dir / "fm26_players.xml"))
        self.batch_script = tk.StringVar(value=str(self.base_dir / DEFAULT_GENERATE_SCRIPT))

        self.batch_count = tk.StringVar(value="1000")
        self.batch_seed = tk.StringVar(value="123")
        self.batch_age_min = tk.StringVar(value="14")
        self.batch_age_max = tk.StringVar(value="16")
        self.batch_ca_min = tk.StringVar(value="20")
        self.batch_ca_max = tk.StringVar(value="160")
        self.batch_pa_min = tk.StringVar(value="80")
        self.batch_pa_max = tk.StringVar(value="200")
        self.batch_base_year = tk.StringVar(value="2026")

        def row_file(r, label, var, is_save=False):
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ent = ttk.Entry(frm, textvariable=var)
            ent.grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            if is_save:
                btn = ttk.Button(frm, text="Browse…", command=lambda: self._pick_save_xml(var))
            else:
                btn = ttk.Button(frm, text="Browse…", command=lambda: self._pick_open_file(var))
            btn.grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "master_library.csv:", self.batch_clubs, is_save=False)
        row_file(1, "First names CSV:", self.batch_first, is_save=False)
        row_file(2, "Surnames CSV:", self.batch_surn, is_save=False)
        row_file(3, "Output XML:", self.batch_out, is_save=True)
        row_file(4, "Generator script:", self.batch_script, is_save=False)

        opt = ttk.LabelFrame(frm, text="Batch options")
        opt.grid(row=5, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 8))
        for c in range(6):
            opt.columnconfigure(c, weight=1)

        def opt_field(r, c, label, var, width=10):
            ttk.Label(opt, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=6)
            e = ttk.Entry(opt, textvariable=var, width=width)
            e.grid(row=r, column=c + 1, sticky="w", padx=6, pady=6)

        opt_field(0, 0, "Count", self.batch_count)
        opt_field(0, 2, "Seed", self.batch_seed)
        opt_field(0, 4, "Base year", self.batch_base_year)

        opt_field(1, 0, "Age min", self.batch_age_min)
        opt_field(1, 2, "Age max", self.batch_age_max)
        opt_field(1, 4, "CA min", self.batch_ca_min)

        opt_field(2, 0, "CA max", self.batch_ca_max)
        opt_field(2, 2, "PA min", self.batch_pa_min)
        opt_field(2, 4, "PA max", self.batch_pa_max)

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 6))
        ttk.Button(btns, text="Run Batch Generator", command=self._run_batch_generator).pack(anchor="w")

        hint = (
            "Note:\n"
            "- FM editor import only accepts ONE XML at a time.\n"
            "- The generator produces ONE combined XML file.\n"
        )
        ttk.Label(frm, text=hint, foreground="#444").grid(row=7, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))

    # ---------------- Players (Single) UI ----------------
    def _build_single_tab(self) -> None:
        frm = self.single_tab
        frm.columnconfigure(1, weight=1)

        # Single = same inputs but count forced to 1
        self.single_clubs = tk.StringVar(value=str(self.fm_dir / "master_library.csv"))
        self.single_first = tk.StringVar(value=str(self.base_dir / "scottish_male_first_names_2500.csv"))
        self.single_surn = tk.StringVar(value=str(self.base_dir / "scottish_surnames_2500.csv"))
        self.single_out = tk.StringVar(value=str(self.fm_dir / "fm26_single_player.xml"))
        self.single_script = tk.StringVar(value=str(self.base_dir / DEFAULT_GENERATE_SCRIPT))

        self.single_seed = tk.StringVar(value="123")
        self.single_age = tk.StringVar(value="14")
        self.single_ca = tk.StringVar(value="120")
        self.single_pa = tk.StringVar(value="170")
        self.single_base_year = tk.StringVar(value="2026")

        def row_file(r, label, var, is_save=False):
            ttk.Label(frm, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ent = ttk.Entry(frm, textvariable=var)
            ent.grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            if is_save:
                btn = ttk.Button(frm, text="Browse…", command=lambda: self._pick_save_xml(var))
            else:
                btn = ttk.Button(frm, text="Browse…", command=lambda: self._pick_open_file(var))
            btn.grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "master_library.csv:", self.single_clubs, is_save=False)
        row_file(1, "First names CSV:", self.single_first, is_save=False)
        row_file(2, "Surnames CSV:", self.single_surn, is_save=False)
        row_file(3, "Output XML:", self.single_out, is_save=True)
        row_file(4, "Generator script:", self.single_script, is_save=False)

        opt = ttk.LabelFrame(frm, text="Single player (fixed values)")
        opt.grid(row=5, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 8))
        for c in range(6):
            opt.columnconfigure(c, weight=1)

        def opt_field(r, c, label, var, width=10):
            ttk.Label(opt, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=6)
            e = ttk.Entry(opt, textvariable=var, width=width)
            e.grid(row=r, column=c + 1, sticky="w", padx=6, pady=6)

        opt_field(0, 0, "Seed", self.single_seed)
        opt_field(0, 2, "Base year", self.single_base_year)

        opt_field(1, 0, "Age", self.single_age)
        opt_field(1, 2, "CA", self.single_ca)
        opt_field(1, 4, "PA", self.single_pa)

        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 6))
        ttk.Button(btns, text="Generate 1 Player", command=self._run_single_generator).pack(anchor="w")

        ttk.Label(
            frm,
            text="(Next step later: height, calendar DOB picker, nation/city selector, positions etc.)",
            foreground="#444"
        ).grid(row=7, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))

    def _pick_open_file(self, var: tk.StringVar) -> None:
        p = filedialog.askopenfilename(title="Select file", initialdir=str(self.fm_dir), filetypes=[("All files", "*.*")])
        if p:
            var.set(p)

    def _pick_save_xml(self, var: tk.StringVar) -> None:
        p = filedialog.asksaveasfilename(
            title="Save XML as",
            initialdir=str(self.fm_dir),
            defaultextension=".xml",
            filetypes=[("XML files", "*.xml")]
        )
        if p:
            var.set(p)

    def _run_batch_generator(self) -> None:
        self._run_generator_common(
            script_path=self.batch_script.get().strip(),
            clubs=self.batch_clubs.get().strip(),
            first=self.batch_first.get().strip(),
            surn=self.batch_surn.get().strip(),
            out_path=self.batch_out.get().strip(),
            count=self.batch_count.get().strip(),
            age_min=self.batch_age_min.get().strip(),
            age_max=self.batch_age_max.get().strip(),
            ca_min=self.batch_ca_min.get().strip(),
            ca_max=self.batch_ca_max.get().strip(),
            pa_min=self.batch_pa_min.get().strip(),
            pa_max=self.batch_pa_max.get().strip(),
            base_year=self.batch_base_year.get().strip(),
            seed=self.batch_seed.get().strip(),
            title="Batch Generator",
        )

    def _run_single_generator(self) -> None:
        # Single: count=1, min=max for age/CA/PA
        age = self.single_age.get().strip()
        ca = self.single_ca.get().strip()
        pa = self.single_pa.get().strip()

        self._run_generator_common(
            script_path=self.single_script.get().strip(),
            clubs=self.single_clubs.get().strip(),
            first=self.single_first.get().strip(),
            surn=self.single_surn.get().strip(),
            out_path=self.single_out.get().strip(),
            count="1",
            age_min=age,
            age_max=age,
            ca_min=ca,
            ca_max=ca,
            pa_min=pa,
            pa_max=pa,
            base_year=self.single_base_year.get().strip(),
            seed=self.single_seed.get().strip(),
            title="Single Generator",
        )

    def _run_generator_common(
        self,
        script_path: str,
        clubs: str,
        first: str,
        surn: str,
        out_path: str,
        count: str,
        age_min: str,
        age_max: str,
        ca_min: str,
        ca_max: str,
        pa_min: str,
        pa_max: str,
        base_year: str,
        seed: str,
        title: str,
    ) -> None:
        if not script_path or not Path(script_path).exists():
            messagebox.showerror("Missing script", "Please choose a valid generator .py script.")
            return

        def must_exist(path: str, label: str) -> bool:
            if not path or not Path(path).exists():
                messagebox.showerror("Missing input", f"Please choose a valid {label} file.")
                return False
            return True

        if not must_exist(clubs, "master_library.csv"):
            return
        if not must_exist(first, "first names"):
            return
        if not must_exist(surn, "surnames"):
            return
        if not out_path:
            messagebox.showerror("Missing output", "Please choose an output XML path.")
            return

        # Ensure output dir exists
        try:
            ensure_parent_dir(out_path)
        except Exception as e:
            messagebox.showerror("Output folder error", f"Could not create output folder:\n{e}")
            return

        cmd = [
            sys.executable,
            script_path,
            "--master_library", clubs,
            "--first_names", first,
            "--surnames", surn,
            "--count", count,
            "--output", out_path,
            "--age_min", age_min,
            "--age_max", age_max,
            "--ca_min", ca_min,
            "--ca_max", ca_max,
            "--pa_min", pa_min,
            "--pa_max", pa_max,
            "--base_year", base_year,
        ]
        if seed:
            cmd.extend(["--seed", seed])

        self._run_async_stream(title, cmd, must_create=out_path)

    # ---------------- Shared async runner (LIVE STREAM) ----------------
    def _run_async_stream(self, title: str, cmd: list[str], must_create: str | None = None) -> None:
        self._log("\n" + "=" * 100)
        self._log(f"{title} command:\n  " + " ".join([_quote(x) for x in cmd]))
        self._log(f"Working directory:\n  {Path.cwd()}\n")

        def worker():
            try:
                # Stream stdout+stderr live into log
                p = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )

                assert p.stdout is not None
                for line in p.stdout:
                    self._log_threadsafe(line.rstrip("\n"))

                rc = p.wait()

            except Exception as e:
                self._ui_error(f"{title} failed", str(e))
                return

            # Final check: did the output file actually get created?
            if rc == 0 and must_create:
                try:
                    outp = Path(must_create).expanduser()
                    if not outp.exists():
                        self._ui_error("Output missing", f"{title} said OK, but output file was not found:\n{outp}")
                        return
                    if outp.is_file() and outp.stat().st_size == 0:
                        self._ui_error("Empty output", f"Output file was created but is empty:\n{outp}")
                        return
                    self._log_threadsafe(f"\n[OK] Output written:\n  {outp}\n  Size: {outp.stat().st_size:,} bytes\n")
                except Exception as e:
                    self._log_threadsafe(f"[WARN] Could not verify output file: {e}\n")

            if rc == 0:
                self._log_threadsafe(f"\n[OK] {title} finished successfully.\n")
            else:
                self._log_threadsafe(f"\n[FAIL] {title} exited with code {rc}.\n")
                self._ui_error(f"{title} failed", f"{title} failed (exit code {rc}).\nCheck Output/Errors box for details.")

        threading.Thread(target=worker, daemon=True).start()


def main() -> int:
    try:
        app = App()
    except tk.TclError as e:
        print("Tkinter UI could not start. On Linux you may need Tk support, e.g.:")
        print("  sudo apt-get install python3-tk")
        print(f"Error: {e}")
        return 2

    app.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
