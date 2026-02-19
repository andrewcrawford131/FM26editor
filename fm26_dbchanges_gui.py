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


try:
    # Optional: nice calendar picker (pip install tkcalendar)
    from tkcalendar import DateEntry  # type: ignore
    HAVE_TKCALENDAR = True
except Exception:
    DateEntry = None  # type: ignore
    HAVE_TKCALENDAR = False

APP_TITLE = "FM26 DBChanges Tools (Library Extractor + Players Generator)"

DEFAULT_EXTRACT_SCRIPT = "fm_dbchanges_extract_fixed_v4.py"
DEFAULT_GENERATE_SCRIPT = "fm26_bulk_youth_generator.py"

# Positions list must match the generator's internal POS map.
ALL_POS = ["GK","DL","DC","DR","WBL","WBR","DM","ML","MC","MR","AML","AMC","AMR","ST"]



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

        # Scrollable content frames (prevents Generate buttons from disappearing)
        self.batch_body = self._make_scrollable(self.batch_tab)
        self.single_body = self._make_scrollable(self.single_tab)

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


    def _make_scrollable(self, parent: ttk.Frame) -> ttk.Frame:
        """Return an inner frame inside a scrollable canvas placed in `parent`."""
        wrapper = ttk.Frame(parent)
        wrapper.pack(fill="both", expand=True)

        canvas = tk.Canvas(wrapper, highlightthickness=0)
        vsb = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = ttk.Frame(canvas)
        win = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_inner_config(_event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_config(event):
            canvas.itemconfig(win, width=event.width)

        inner.bind("<Configure>", _on_inner_config)
        canvas.bind("<Configure>", _on_canvas_config)

        # Mouse wheel support while pointer is over the scroll area
        def _on_mousewheel(event):
            try:
                if sys.platform.startswith("darwin"):
                    canvas.yview_scroll(int(-event.delta), "units")
                else:
                    delta = int(event.delta / 120) if event.delta else 0
                    if delta:
                        canvas.yview_scroll(-delta, "units")
            except Exception:
                pass

        def _bind(_event=None):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
            canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-3, "units"))
            canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(3, "units"))

        def _unbind(_event=None):
            canvas.unbind_all("<MouseWheel>")
            canvas.unbind_all("<Button-4>")
            canvas.unbind_all("<Button-5>")

        inner.bind("<Enter>", _bind)
        inner.bind("<Leave>", _unbind)
        canvas.bind("<Enter>", _bind)
        canvas.bind("<Leave>", _unbind)

        return inner

    def _make_date_input(self, parent, var: tk.StringVar):
            """Calendar-like date input (YYYY-MM-DD). Uses tkcalendar if installed, else a plain Entry."""
            if HAVE_TKCALENDAR and DateEntry is not None:
                try:
                    w = DateEntry(parent, textvariable=var, date_pattern="y-mm-dd", width=12)
                    return w
                except Exception:
                    pass
            return ttk.Entry(parent, textvariable=var, width=14)

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
        frm = self.batch_body
        frm.columnconfigure(1, weight=1)

        # Defaults: output to FM editor data folder
        self.batch_clubs = tk.StringVar(value=str(self.fm_dir / "master_library.csv"))
        self.batch_first = tk.StringVar(value=str(self.base_dir / "scottish_male_first_names_2500.csv"))
        self.batch_surn = tk.StringVar(value=str(self.base_dir / "scottish_surnames_2500.csv"))
        self.batch_out = tk.StringVar(value=str(self.fm_dir / "fm26_players.xml"))
        self.batch_script = tk.StringVar(value=str(self.base_dir / DEFAULT_GENERATE_SCRIPT))

        # Core batch settings
        self.batch_count = tk.StringVar(value="1000")
        self.batch_seed = tk.StringVar(value="123")
        self.batch_base_year = tk.StringVar(value="2026")

        # Age / CA / PA (used when DOB range not set)
        self.batch_age_min = tk.StringVar(value="14")
        self.batch_age_max = tk.StringVar(value="16")
        self.batch_ca_min = tk.StringVar(value="20")
        self.batch_ca_max = tk.StringVar(value="160")
        self.batch_pa_min = tk.StringVar(value="80")
        self.batch_pa_max = tk.StringVar(value="200")

        # DOB mode (age range OR DOB range OR fixed DOB)
        self.batch_dob_mode = tk.StringVar(value="age")  # age|range|fixed
        self.batch_dob_fixed = tk.StringVar(value="2012-07-01")
        self.batch_dob_start = tk.StringVar(value="2010-01-01")
        self.batch_dob_end = tk.StringVar(value="2012-12-31")

        # Height mode (random range OR fixed)
        self.batch_height_mode = tk.StringVar(value="range")  # range|fixed
        self.batch_height_min = tk.StringVar(value="150")
        self.batch_height_max = tk.StringVar(value="210")
        self.batch_height_fixed = tk.StringVar(value="")

        # Feet
        self.batch_feet_mode = tk.StringVar(value="random")  # random|right|left|both
        self.batch_feet_override = tk.BooleanVar(value=False)
        self.batch_left_foot = tk.StringVar(value="")
        self.batch_right_foot = tk.StringVar(value="")

        # Positions
        self.batch_positions_random = tk.BooleanVar(value=True)
        self.batch_pos_vars: dict[str, tk.BooleanVar] = {p: tk.BooleanVar(value=False) for p in ALL_POS}

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

        # DOB options
        dob = ttk.LabelFrame(frm, text="DOB (Age range OR calendar range)")
        dob.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        dob.columnconfigure(3, weight=1)

        ttk.Radiobutton(dob, text="Use age range", variable=self.batch_dob_mode, value="age").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(dob, text="Use DOB range", variable=self.batch_dob_mode, value="range").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(dob, text="Use fixed DOB (same for all)", variable=self.batch_dob_mode, value="fixed").grid(row=0, column=2, sticky="w", padx=8, pady=6)

        ttk.Label(dob, text="Fixed DOB").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.batch_dob_fixed).grid(row=1, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="Start").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.batch_dob_start).grid(row=2, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="End").grid(row=2, column=2, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.batch_dob_end).grid(row=2, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="(If DOB range is selected, Age min/max are ignored)", foreground="#444").grid(row=2, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 6))

        # Height + feet
        hf = ttk.LabelFrame(frm, text="Height + Feet")
        hf.grid(row=7, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(8):
            hf.columnconfigure(c, weight=1)

        ttk.Radiobutton(hf, text="Random height range", variable=self.batch_height_mode, value="range").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(hf, text="Fixed height", variable=self.batch_height_mode, value="fixed").grid(row=0, column=4, sticky="w", padx=8, pady=6)

        ttk.Label(hf, text="Min").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(hf, textvariable=self.batch_height_min, width=6).grid(row=1, column=1, sticky="w", padx=8, pady=4)
        ttk.Label(hf, text="Max").grid(row=1, column=2, sticky="w", padx=8, pady=4)
        ttk.Entry(hf, textvariable=self.batch_height_max, width=6).grid(row=1, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(hf, text="Height").grid(row=1, column=4, sticky="w", padx=8, pady=4)
        ttk.Entry(hf, textvariable=self.batch_height_fixed, width=6).grid(row=1, column=5, sticky="w", padx=8, pady=4)
        ttk.Label(hf, text="cm (150–210)", foreground="#444").grid(row=1, column=6, sticky="w", padx=8, pady=4)

        ttk.Label(hf, text="Feet").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(hf, textvariable=self.batch_feet_mode, values=["random", "right", "left", "both"], width=10, state="readonly").grid(row=2, column=1, sticky="w", padx=8, pady=6)

        # Positions
        pos = ttk.LabelFrame(frm, text="Positions")
        pos.grid(row=8, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        ttk.Checkbutton(pos, text="Random positions (ignore selections)", variable=self.batch_positions_random).grid(row=0, column=0, sticky="w", padx=8, pady=6)

        grid = ttk.Frame(pos)
        grid.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
        cols = 7
        for i, code in enumerate(ALL_POS):
            r = i // cols
            c = i % cols
            ttk.Checkbutton(grid, text=code, variable=self.batch_pos_vars[code]).grid(row=r, column=c, sticky="w", padx=6, pady=2)

        btns = ttk.Frame(frm)
        btns.grid(row=9, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 6))
        ttk.Button(btns, text="Run Batch Generator", command=self._run_batch_generator).pack(anchor="w")

        hint = """Note:
    - FM editor import only accepts ONE XML at a time.
    - The generator produces ONE combined XML file.
    """
        ttk.Label(frm, text=hint, foreground="#444").grid(row=10, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))

    # ---------------- Players (Single) UI ----------------
    def _build_single_tab(self) -> None:
        frm = self.single_body
        frm.columnconfigure(1, weight=1)

        # Single = same inputs but count forced to 1
        self.single_clubs = tk.StringVar(value=str(self.fm_dir / "master_library.csv"))
        self.single_first = tk.StringVar(value=str(self.base_dir / "scottish_male_first_names_2500.csv"))
        self.single_surn = tk.StringVar(value=str(self.base_dir / "scottish_surnames_2500.csv"))
        self.single_out = tk.StringVar(value=str(self.fm_dir / "fm26_single_player.xml"))
        self.single_script = tk.StringVar(value=str(self.base_dir / DEFAULT_GENERATE_SCRIPT))

        self.single_seed = tk.StringVar(value="123")
        self.single_base_year = tk.StringVar(value="2026")

        # Age/DOB
        self.single_dob_mode = tk.StringVar(value="age")  # age|dob
        self.single_age = tk.StringVar(value="14")
        self.single_dob = tk.StringVar(value="2012-07-01")
        self.single_age_preview = tk.StringVar(value="Age (from DOB): 14")

        # CA/PA fixed
        self.single_ca = tk.StringVar(value="120")
        self.single_pa = tk.StringVar(value="170")

        # Height
        self.single_height_mode = tk.StringVar(value="range")  # range|fixed
        self.single_height_min = tk.StringVar(value="150")
        self.single_height_max = tk.StringVar(value="210")
        self.single_height_fixed = tk.StringVar(value="")

        # Feet
        self.single_feet_mode = tk.StringVar(value="random")

        # Positions
        self.single_positions_random = tk.BooleanVar(value=True)
        self.single_pos_vars: dict[str, tk.BooleanVar] = {p: tk.BooleanVar(value=False) for p in ALL_POS}

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
        for c in range(8):
            opt.columnconfigure(c, weight=1)

        ttk.Label(opt, text="Seed").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_seed, width=10).grid(row=0, column=1, sticky="w", padx=6, pady=6)

        ttk.Label(opt, text="Base year").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_base_year, width=10).grid(row=0, column=3, sticky="w", padx=6, pady=6)

        ttk.Label(opt, text="CA").grid(row=0, column=4, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_ca, width=10).grid(row=0, column=5, sticky="w", padx=6, pady=6)

        ttk.Label(opt, text="PA").grid(row=0, column=6, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_pa, width=10).grid(row=0, column=7, sticky="w", padx=6, pady=6)

        # Age / DOB
        dob = ttk.LabelFrame(frm, text="Age / DOB")
        dob.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        dob.columnconfigure(3, weight=1)

        ttk.Radiobutton(dob, text="Use age", variable=self.single_dob_mode, value="age").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(dob, text="Age").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Entry(dob, textvariable=self.single_age, width=6).grid(row=0, column=2, sticky="w", padx=8, pady=6)

        ttk.Radiobutton(dob, text="Use DOB", variable=self.single_dob_mode, value="dob").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(dob, text="DOB").grid(row=1, column=1, sticky="w", padx=8, pady=6)
        dob_w = self._make_date_input(dob, self.single_dob)
        dob_w.grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(dob, textvariable=self.single_age_preview, foreground="#444").grid(row=1, column=3, sticky="w", padx=8, pady=6)

        def _update_age_preview(*_):
            try:
                # Age at base_year (approx, just year-based)
                by = int(self.single_base_year.get().strip() or "2026")
                y = int(self.single_dob.get().strip()[:4])
                a = max(0, by - y)
                self.single_age_preview.set(f"Age (from DOB): {a}")
            except Exception:
                self.single_age_preview.set("Age (from DOB): ?")

        # try to update on changes
        self.single_dob.trace_add("write", _update_age_preview)
        self.single_base_year.trace_add("write", _update_age_preview)
        _update_age_preview()

        # Height + feet
        hf = ttk.LabelFrame(frm, text="Height + Feet")
        hf.grid(row=7, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(8):
            hf.columnconfigure(c, weight=1)

        ttk.Radiobutton(hf, text="Random height range", variable=self.single_height_mode, value="range").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(hf, text="Fixed height", variable=self.single_height_mode, value="fixed").grid(row=0, column=4, sticky="w", padx=8, pady=6)

        ttk.Label(hf, text="Min").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        ttk.Entry(hf, textvariable=self.single_height_min, width=6).grid(row=1, column=1, sticky="w", padx=8, pady=4)
        ttk.Label(hf, text="Max").grid(row=1, column=2, sticky="w", padx=8, pady=4)
        ttk.Entry(hf, textvariable=self.single_height_max, width=6).grid(row=1, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(hf, text="Height").grid(row=1, column=4, sticky="w", padx=8, pady=4)
        ttk.Entry(hf, textvariable=self.single_height_fixed, width=6).grid(row=1, column=5, sticky="w", padx=8, pady=4)
        ttk.Label(hf, text="cm (150–210)", foreground="#444").grid(row=1, column=6, sticky="w", padx=8, pady=4)

        ttk.Label(hf, text="Feet").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(hf, textvariable=self.single_feet_mode, values=["random", "right", "left", "both"], width=10, state="readonly").grid(row=2, column=1, sticky="w", padx=8, pady=6)

        # Positions
        pos = ttk.LabelFrame(frm, text="Positions")
        pos.grid(row=8, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        ttk.Checkbutton(pos, text="Random positions (ignore selections)", variable=self.single_positions_random).grid(row=0, column=0, sticky="w", padx=8, pady=6)

        grid = ttk.Frame(pos)
        grid.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
        cols = 7
        for i, code in enumerate(ALL_POS):
            r = i // cols
            c = i % cols
            ttk.Checkbutton(grid, text=code, variable=self.single_pos_vars[code]).grid(row=r, column=c, sticky="w", padx=6, pady=2)

        btns = ttk.Frame(frm)
        btns.grid(row=9, column=0, columnspan=3, sticky="ew", padx=8, pady=(6, 6))
        ttk.Button(btns, text="Generate 1 Player", command=self._run_single_generator).pack(anchor="w")

        ttk.Label(frm, text="Tip: Set Age=14 and/or pick a DOB in 2012 for a 14-year-old in base year 2026.", foreground="#444").grid(row=10, column=0, columnspan=3, sticky="w", padx=8, pady=(6, 8))

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
        extra: list[str] = []

        # DOB
        mode = getattr(self, "batch_dob_mode", tk.StringVar(value="age")).get()
        if mode == "fixed":
            d = self.batch_dob_fixed.get().strip()
            if not d:
                messagebox.showerror("Fixed DOB missing", "Fixed DOB is selected, but the date is blank.")
                return
            extra.extend(["--dob", d])
        elif mode == "range":
            ds = self.batch_dob_start.get().strip()
            de = self.batch_dob_end.get().strip()
            if not ds or not de:
                messagebox.showerror("DOB range missing", "Please set both DOB Start and DOB End (YYYY-MM-DD).")
                return
            extra.extend(["--dob_start", ds, "--dob_end", de])

        # Height
        if getattr(self, "batch_height_mode", tk.StringVar(value="range")).get() == "fixed":
            h = self.batch_height_fixed.get().strip()
            if not h:
                messagebox.showerror("Height missing", "Fixed height selected, but Height is blank.")
                return
            extra.extend(["--height", h])
        else:
            extra.extend(["--height_min", self.batch_height_min.get().strip(), "--height_max", self.batch_height_max.get().strip()])

        # Feet
        extra.extend(["--feet", self.batch_feet_mode.get().strip() or "random"])
        if getattr(self, "batch_feet_override", tk.BooleanVar(value=False)).get():
            lf = self.batch_left_foot.get().strip()
            rf = self.batch_right_foot.get().strip()
            if not lf or not rf:
                messagebox.showerror("Feet missing", "Override feet is ticked, but Left/Right values are blank.")
                return
            extra.extend(["--left_foot", lf, "--right_foot", rf])

        # Positions
        if self.batch_positions_random.get():
            extra.extend(["--positions", "RANDOM"])
        else:
            sel = [code for code, v in self.batch_pos_vars.items() if v.get()]
            if not sel:
                messagebox.showerror("Positions missing", "Please select at least one position, or tick Random positions.")
                return
            extra.extend(["--positions", ",".join(sel)])

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
            extra_args=extra,
        )

    def _run_single_generator(self) -> None:
        # Single: count=1, min=max for CA/PA, and either Age or DOB fixed
        ca = self.single_ca.get().strip()
        pa = self.single_pa.get().strip()
        base_year = self.single_base_year.get().strip()

        extra: list[str] = []

        # Age / DOB
        age = self.single_age.get().strip()
        if self.single_dob_mode.get() == "dob":
            dob = self.single_dob.get().strip()
            if not dob:
                messagebox.showerror("DOB missing", "Use DOB is selected, but DOB is blank.")
                return
            extra.extend(["--dob", dob])
            # (age_min/max are ignored when --dob is fixed, but we keep age for sanity)
            try:
                by = int(base_year or "2026")
                a = max(0, by - int(dob[:4]))
                age = str(a)
            except Exception:
                pass

        # Height
        if self.single_height_mode.get() == "fixed":
            h = self.single_height_fixed.get().strip()
            if not h:
                messagebox.showerror("Height missing", "Fixed height selected, but Height is blank.")
                return
            extra.extend(["--height", h])
        else:
            extra.extend(["--height_min", self.single_height_min.get().strip(), "--height_max", self.single_height_max.get().strip()])

        # Feet
        extra.extend(["--feet", self.single_feet_mode.get().strip() or "random"])
        if getattr(self, "single_feet_override", tk.BooleanVar(value=False)).get():
            lf = self.single_left_foot.get().strip()
            rf = self.single_right_foot.get().strip()
            if not lf or not rf:
                messagebox.showerror("Feet missing", "Override feet is ticked, but Left/Right values are blank.")
                return
            extra.extend(["--left_foot", lf, "--right_foot", rf])

        # Positions
        if self.single_positions_random.get():
            extra.extend(["--positions", "RANDOM"])
        else:
            sel = [code for code, v in self.single_pos_vars.items() if v.get()]
            if not sel:
                messagebox.showerror("Positions missing", "Please select at least one position, or tick Random positions.")
                return
            extra.extend(["--positions", ",".join(sel)])

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
            base_year=base_year,
            seed=self.single_seed.get().strip(),
            title="Single Generator",
            extra_args=extra,
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
        extra_args: list[str] | None = None,
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
            messagebox.showerror("Output folder error", "Could not create output folder: " + str(e))
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
        if extra_args:
            cmd.extend([x for x in extra_args if x is not None and str(x) != ""])

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
