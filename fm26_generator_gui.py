#!/usr/bin/env python3
"""
fm26_dbchanges_gui2.py

Cross-platform (Windows/macOS/Linux) GUI for:
1) Extracting clubs/cities/nations from FM "db_changes" XML into master_library.csv
2) Generating batch + single FM26 editor XML youth players using generator2.

Friendly UI features:
- Output/Errors pane is hidden by default (Show/Hide button)
- File input paths are hidden by default (Show/Hide button)
- Live stdout/stderr streaming into the output box
- Auto-detects FM26 editor data folder and sets good defaults

No pip required:
- Built-in calendar picker for DOB fields (no tkcalendar dependency)
"""

from __future__ import annotations

import os
import sys
import csv
import threading
import subprocess
import calendar as _cal
import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

APP_TITLE = "FM26 Generator — Friendly v23 (fmdata defaults + declared youth export)"
DEFAULT_EXTRACT_SCRIPT = "fm26_db_extractor.py"
DEFAULT_GENERATE_SCRIPT = "fm26_people_generator8_fmdata_ready.py"
DEFAULT_XML_APPENDER_SCRIPT = "fm26_xml_appender.py"

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
        onedrive = os.environ.get("OneDrive")
        if onedrive:
            candidates.append(Path(onedrive) / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "OneDrive" / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")

    elif sys.platform == "darwin":
        candidates.append(home / "Library" / "Application Support" / "Sports Interactive" / "Football Manager 26" / "editor data")
        candidates.append(home / "Documents" / "Sports Interactive" / "Football Manager 26" / "editor data")

    else:
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
    p.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class StreamResult:
    rc: int


class DatePickerPopup(tk.Toplevel):
    """A tiny calendar popup that writes YYYY-MM-DD into a StringVar (stdlib only)."""

    def __init__(self, parent: tk.Widget, var: tk.StringVar):
        super().__init__(parent)
        self.title("Pick a date")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.var = var

        # initial date from var if possible
        today = _dt.date.today()
        y, m, d = today.year, today.month, today.day
        try:
            s = (var.get() or "").strip()
            if len(s) >= 10:
                y = int(s[0:4]); m = int(s[5:7]); d = int(s[8:10])
        except Exception:
            pass

        self._year = y
        self._month = m
        self._build_ui()
        self._render_days(select_day=d)

        # place near mouse cursor if possible
        try:
            self.update_idletasks()
            x = self.winfo_pointerx() - 40
            y = self.winfo_pointery() - 10
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

    def _build_ui(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill="both", expand=True)

        nav = ttk.Frame(top)
        nav.pack(fill="x")

        ttk.Button(nav, text="◀", width=3, command=self._prev_month).pack(side="left")
        self.lbl = ttk.Label(nav, text="", width=20, anchor="center")
        self.lbl.pack(side="left", padx=8)
        ttk.Button(nav, text="▶", width=3, command=self._next_month).pack(side="left")

        self.gridfrm = ttk.Frame(top)
        self.gridfrm.pack(pady=(8, 0))

        # weekday header
        for i, wd in enumerate(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]):
            ttk.Label(self.gridfrm, text=wd, width=4, anchor="center").grid(row=0, column=i, padx=2, pady=2)

        # day buttons placeholder
        self._day_btns: list[ttk.Button] = []
        for r in range(1, 7):  # up to 6 weeks
            for c in range(7):
                b = ttk.Button(self.gridfrm, text="", width=4)
                b.grid(row=r, column=c, padx=2, pady=2)
                self._day_btns.append(b)

        # bottom
        bottom = ttk.Frame(top)
        bottom.pack(fill="x", pady=(10, 0))
        ttk.Button(bottom, text="Today", command=self._set_today).pack(side="left")
        ttk.Button(bottom, text="Close", command=self.destroy).pack(side="right")

    def _month_label(self) -> str:
        return f"{_cal.month_name[self._month]} {self._year}"

    def _prev_month(self):
        self._month -= 1
        if self._month <= 0:
            self._month = 12
            self._year -= 1
        self._render_days()

    def _next_month(self):
        self._month += 1
        if self._month >= 13:
            self._month = 1
            self._year += 1
        self._render_days()

    def _set_today(self):
        today = _dt.date.today()
        self._year, self._month = today.year, today.month
        self._render_days(select_day=today.day)

    def _render_days(self, select_day: int | None = None):
        self.lbl.configure(text=self._month_label())

        # Monday=0..Sunday=6
        first_weekday, num_days = _cal.monthrange(self._year, self._month)  # Monday=0
        # Our header is Mon..Sun already, so index aligns.
        # Clear all
        for b in self._day_btns:
            b.configure(text="", state="disabled", command=lambda: None)

        day = 1
        start_index = first_weekday  # 0..6
        for i in range(start_index, start_index + num_days):
            btn = self._day_btns[i]
            dd = day
            btn.configure(
                text=str(dd),
                state="normal",
                command=lambda dd=dd: self._pick(dd),
            )
            day += 1

        if select_day and 1 <= select_day <= num_days:
            # Optional: focus a day button
            try:
                idx = start_index + (select_day - 1)
                self._day_btns[idx].focus_set()
            except Exception:
                pass

    def _pick(self, day: int):
        try:
            dt = _dt.date(self._year, self._month, int(day))
            self.var.set(dt.strftime("%Y-%m-%d"))
        except Exception:
            pass
        self.destroy()


class DateInput(ttk.Frame):
    """Entry + calendar button (no pip)."""

    def __init__(self, parent: tk.Widget, var: tk.StringVar, width: int = 12):
        super().__init__(parent)
        self.var = var
        self.ent = ttk.Entry(self, textvariable=var, width=width)
        self.ent.pack(side="left")
        self.btn = ttk.Button(self, text="📅", width=3, command=self._open)
        self.btn.pack(side="left", padx=(4, 0))

    def _open(self):
        DatePickerPopup(self, self.var)


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1060x720")
        self.minsize(980, 620)

        # Top bar toggles (friendlier UI)
        topbar = ttk.Frame(self)
        topbar.pack(fill="x", padx=10, pady=(10, 0))

        self.btn_toggle_paths = ttk.Button(topbar, text="Show File Inputs", command=self._toggle_paths)
        self.btn_toggle_paths.pack(side="left")

        self.btn_toggle_output = ttk.Button(topbar, text="Show Output", command=self._toggle_output)
        self.btn_toggle_output.pack(side="left", padx=(8, 0))

        ttk.Label(topbar, text="(Clean view by default — reveal only when needed)").pack(side="left", padx=(12, 0))

        self._paths_visible = False
        self._output_visible = False

        self.base_dir = Path(__file__).resolve().parent
        self.fm_dir = detect_fm26_editor_data_dir()
        self.fmdata_dir = self.base_dir / "fmdata"
        try:
            self.fmdata_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

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
        self.appender_tab = ttk.Frame(self.notebook)
        self.gen_tab = ttk.Frame(self.notebook)  # visible label renamed to People

        self.notebook.add(self.extract_tab, text="Extractor (Cities,Clubs,Nations and Regions)")
        self.notebook.add(self.appender_tab, text="XML Appender")
        self.notebook.add(self.gen_tab, text="People")

        # People -> Player / Non-player
        self.people_kind_notebook = ttk.Notebook(self.gen_tab)
        self.people_kind_notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.player_people_tab = ttk.Frame(self.people_kind_notebook)
        self.nonplayer_people_tab = ttk.Frame(self.people_kind_notebook)
        self.people_kind_notebook.add(self.player_people_tab, text="Player")
        self.people_kind_notebook.add(self.nonplayer_people_tab, text="Non-player")

        # Player -> Batch / Single Person
        self.players_notebook = ttk.Notebook(self.player_people_tab)
        self.players_notebook.pack(fill="both", expand=True)

        self.player_batch_parent = ttk.Frame(self.players_notebook)
        self.player_single_parent = ttk.Frame(self.players_notebook)
        self.players_notebook.add(self.player_batch_parent, text="Batch")
        self.players_notebook.add(self.player_single_parent, text="Single Person")

        # Player > Batch -> Other / Details
        self.player_batch_notebook = ttk.Notebook(self.player_batch_parent)
        self.player_batch_notebook.pack(fill="both", expand=True)
        self.batch_tab = ttk.Frame(self.player_batch_notebook)           # Other
        self.batch_details_tab = ttk.Frame(self.player_batch_notebook)   # Details
        self.player_batch_notebook.add(self.batch_tab, text="Other")
        self.player_batch_notebook.add(self.batch_details_tab, text="Details")

        # Player > Single Person -> Other / Details
        self.player_single_notebook = ttk.Notebook(self.player_single_parent)
        self.player_single_notebook.pack(fill="both", expand=True)
        self.single_tab = ttk.Frame(self.player_single_notebook)         # Other
        self.single_details_tab = ttk.Frame(self.player_single_notebook) # Details
        self.player_single_notebook.add(self.single_tab, text="Other")
        self.player_single_notebook.add(self.single_details_tab, text="Details")

        # Non-player scaffolding tabs (requested layout)
        self.nonplayer_modes_notebook = ttk.Notebook(self.nonplayer_people_tab)
        self.nonplayer_modes_notebook.pack(fill="both", expand=True)

        self.nonplayer_batch_parent = ttk.Frame(self.nonplayer_modes_notebook)
        self.nonplayer_single_parent = ttk.Frame(self.nonplayer_modes_notebook)
        self.nonplayer_modes_notebook.add(self.nonplayer_batch_parent, text="Batch")
        self.nonplayer_modes_notebook.add(self.nonplayer_single_parent, text="Single Person")

        self.nonplayer_batch_notebook = ttk.Notebook(self.nonplayer_batch_parent)
        self.nonplayer_batch_notebook.pack(fill="both", expand=True)
        self.nonplayer_batch_other_tab = ttk.Frame(self.nonplayer_batch_notebook)
        self.nonplayer_batch_details_tab = ttk.Frame(self.nonplayer_batch_notebook)
        self.nonplayer_batch_notebook.add(self.nonplayer_batch_other_tab, text="Other")
        self.nonplayer_batch_notebook.add(self.nonplayer_batch_details_tab, text="Details")

        self.nonplayer_single_notebook = ttk.Notebook(self.nonplayer_single_parent)
        self.nonplayer_single_notebook.pack(fill="both", expand=True)
        self.nonplayer_single_other_tab = ttk.Frame(self.nonplayer_single_notebook)
        self.nonplayer_single_details_tab = ttk.Frame(self.nonplayer_single_notebook)
        self.nonplayer_single_notebook.add(self.nonplayer_single_other_tab, text="Other")
        self.nonplayer_single_notebook.add(self.nonplayer_single_details_tab, text="Details")

        for _parent, _msg in (
            (self.nonplayer_batch_other_tab, "Non-player batch controls tab scaffolded.\n(Generator wiring can be added next.)"),
            (self.nonplayer_batch_details_tab, "Non-player details tab scaffolded.\nPerson Type selector removed by design."),
            (self.nonplayer_single_other_tab, "Non-player single-person controls tab scaffolded.\n(Generator wiring can be added next.)"),
            (self.nonplayer_single_details_tab, "Non-player details tab scaffolded.\nPerson Type selector removed by design."),
        ):
            wrap = ttk.Frame(_parent, padding=16)
            wrap.pack(fill="both", expand=True)
            ttk.Label(wrap, text=_msg, justify="left").pack(anchor="w")

        # Sticky action bars + scrollable content (PLAYER tabs)
        self.batch_actionbar = ttk.Frame(self.batch_tab)
        self.batch_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.batch_actionbar, text="Run Batch Generator", command=self._run_batch_generator_safe).pack(side="left")

        batch_holder = ttk.Frame(self.batch_tab)
        batch_holder.pack(side="top", fill="both", expand=True)
        self.batch_body = self._make_scrollable(batch_holder)

        self.single_actionbar = ttk.Frame(self.single_tab)
        self.single_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.single_actionbar, text="Generate 1 Player", command=self._run_single_generator_safe).pack(side="left")

        single_holder = ttk.Frame(self.single_tab)
        single_holder.pack(side="top", fill="both", expand=True)
        self.single_body = self._make_scrollable(single_holder)

        self.batch_details_actionbar = ttk.Frame(self.batch_details_tab)
        self.batch_details_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.batch_details_actionbar, text="Run Batch Generator", command=self._run_batch_generator_safe).pack(side="left")

        batch_details_holder = ttk.Frame(self.batch_details_tab)
        batch_details_holder.pack(side="top", fill="both", expand=True)
        self.batch_details_body = self._make_scrollable(batch_details_holder)

        self.single_details_actionbar = ttk.Frame(self.single_details_tab)
        self.single_details_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.single_details_actionbar, text="Generate 1 Player", command=self._run_single_generator_safe).pack(side="left")

        single_details_holder = ttk.Frame(self.single_details_tab)
        single_details_holder.pack(side="top", fill="both", expand=True)
        self.single_details_body = self._make_scrollable(single_details_holder)

        # Top-level XML Appender (moved next to Library Extractor)
        self.appender_actionbar = ttk.Frame(self.appender_tab)
        self.appender_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.appender_actionbar, text="Run XML Appender", command=self._run_xml_appender).pack(side="left")
        ttk.Button(self.appender_actionbar, text="Show Output", command=self._toggle_output).pack(side="right")

        appender_holder = ttk.Frame(self.appender_tab)
        appender_holder.pack(side="top", fill="both", expand=True)
        self.appender_body = self._make_scrollable(appender_holder)

        # Bottom log area (hidden by default)
        log_frame = ttk.Frame(self.paned)
        self.log_frame = log_frame

        ttk.Label(log_frame, text="Output / Errors (live):").pack(anchor="w")
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
        self._log(f"Working fmdata folder (scripts/csv/xml defaults):\n  {self.fmdata_dir}\n")

        # Build UI
        self._build_extractor_tab()
        self._build_batch_tab()
        self._build_single_tab()
        self._build_batch_details_tab()
        self._build_single_details_tab()
        self._build_appender_tab()
        self._init_batch_single_file_sync()
        self.after(200, self._reload_master_library)

    # ---------------- Logging helpers ----------------

    def _log(self, msg: str) -> None:
        self.log.insert("end", msg)
        if not msg.endswith("\n"):
            self.log.insert("end", "\n")
        self.log.see("end")

    def _log_threadsafe(self, msg: str) -> None:
        self.after(0, lambda: self._log(msg))

    def _ui_error(self, title: str, message: str) -> None:
        def _show():
            self._log(f"[ERROR] {title}: {message}")
            messagebox.showerror(title, message)
        self.after(0, _show)

    # ---------------- Show/Hide panes ----------------

    def _toggle_output(self) -> None:
        """Show/hide Output/Errors pane (hidden by default)."""
        if getattr(self, "_output_visible", False):
            try:
                self.paned.forget(self.log_frame)
            except Exception:
                pass
            self._output_visible = False
            try:
                self.btn_toggle_output.configure(text="Show Output")
            except Exception:
                pass
        else:
            try:
                self.paned.add(self.log_frame, weight=2)
            except Exception:
                pass
            self._output_visible = True
            try:
                self.btn_toggle_output.configure(text="Hide Output")
            except Exception:
                pass

        # Watch master_library.csv for external edits (same path, changed contents)
        self._master_library_last_sig = None
        self._master_library_watch_job = None
        try:
            self._start_master_library_watch()
        except Exception:
            pass

    def _toggle_paths(self) -> None:
        """Show/hide the file path inputs (hidden by default)."""
        target = not getattr(self, "_paths_visible", False)

        # Do not force-switch tabs when toggling file inputs.
        # File inputs are mirrored on both Other and Details tabs for Batch/Single.

        for fr in (
            getattr(self, "batch_paths_frame", None),
            getattr(self, "batch_details_paths_frame", None),
            getattr(self, "single_paths_frame", None),
            getattr(self, "single_details_paths_frame", None),
            getattr(self, "appender_paths_frame", None),
        ):
            if fr is None:
                continue
            try:
                if target:
                    fr.grid()
                else:
                    fr.grid_remove()
            except Exception:
                pass

        self._paths_visible = target
        try:
            self.btn_toggle_paths.configure(text=("Hide File Inputs" if target else "Show File Inputs"))
        except Exception:
            pass

    # ---------------- Scroll helper ----------------

    def _make_scrollable(self, parent: ttk.Frame) -> ttk.Frame:
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

        # Mouse wheel support (Windows/macOS/Linux) – works while cursor is over any child widget
        def _is_descendant_of(widget, ancestor) -> bool:
            try:
                w = widget
                while w is not None:
                    if w == ancestor:
                        return True
                    parent_name = w.winfo_parent()
                    if not parent_name:
                        break
                    w = w.nametowidget(parent_name)
            except Exception:
                return False
            return False

        def _pointer_over_this_scroll_area() -> bool:
            try:
                px = self.winfo_pointerx()
                py = self.winfo_pointery()
                w = self.winfo_containing(px, py)
                return _is_descendant_of(w, wrapper)
            except Exception:
                return False

        def _scroll_units(units: int):
            try:
                if not _pointer_over_this_scroll_area():
                    return
                if units:
                    canvas.yview_scroll(units, "units")
            except Exception:
                pass

        def _on_mousewheel(event):
            try:
                if not _pointer_over_this_scroll_area():
                    return
                # macOS often reports small deltas; Windows is usually +/-120 multiples
                if sys.platform.startswith("darwin"):
                    delta = int(event.delta)
                    if delta != 0:
                        canvas.yview_scroll(-delta, "units")
                else:
                    delta = int(event.delta)
                    if delta == 0:
                        return
                    steps = int(delta / 120)
                    if steps == 0:
                        steps = 1 if delta > 0 else -1
                    canvas.yview_scroll(-steps, "units")
            except Exception:
                pass

        # Bind globally once per scroll area; handler self-filters by mouse position.
        # This avoids <Leave> unbinding when moving between child widgets inside the form.
        self.bind_all("<MouseWheel>", _on_mousewheel, add="+")
        self.bind_all("<Button-4>", lambda e: _scroll_units(-3), add="+")  # Linux up
        self.bind_all("<Button-5>", lambda e: _scroll_units(3), add="+")   # Linux down

        return inner

    # ---------------- Date input (no pip) ----------------

    def _make_date_input(self, parent, var: tk.StringVar) -> ttk.Frame:
        """
        Calendar-like date input (YYYY-MM-DD).
        Always stdlib only: Entry + calendar popup button.
        """
        return DateInput(parent, var)

    def _open_calendar(self, var: tk.StringVar) -> None:
        """Open stdlib date picker popup and write YYYY-MM-DD into the given StringVar."""
        try:
            DatePickerPopup(self, var)
        except Exception:
            pass

    # ---------------- Height + Feet section (shared) ----------------

    def _add_height_feet_section(
        self,
        parent: ttk.Frame,
        *,
        row: int,
        height_mode_var: tk.StringVar,
        height_min_var: tk.StringVar,
        height_max_var: tk.StringVar,
        height_fixed_var: tk.StringVar,
        feet_mode_var: tk.StringVar,
        feet_override_var: tk.BooleanVar,
        left_foot_var: tk.StringVar,
        right_foot_var: tk.StringVar,
        show_height: bool = True,
    ) -> None:
        hf = ttk.LabelFrame(parent, text=("Height + Feet" if show_height else "Feet"))
        hf.grid(row=row, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(8):
            hf.columnconfigure(c, weight=1)

        feet_row0 = 0

        if show_height:
            # Height
            ttk.Radiobutton(hf, text="Random height range", variable=height_mode_var, value="range").grid(row=0, column=0, sticky="w", padx=8, pady=6)
            ttk.Radiobutton(hf, text="Fixed height", variable=height_mode_var, value="fixed").grid(row=0, column=4, sticky="w", padx=8, pady=6)

            ttk.Label(hf, text="Min").grid(row=1, column=0, sticky="w", padx=8, pady=4)
            ttk.Entry(hf, textvariable=height_min_var, width=6).grid(row=1, column=1, sticky="w", padx=8, pady=4)
            ttk.Label(hf, text="Max").grid(row=1, column=2, sticky="w", padx=8, pady=4)
            ttk.Entry(hf, textvariable=height_max_var, width=6).grid(row=1, column=3, sticky="w", padx=8, pady=4)

            ttk.Label(hf, text="Height").grid(row=1, column=4, sticky="w", padx=8, pady=4)
            ttk.Entry(hf, textvariable=height_fixed_var, width=6).grid(row=1, column=5, sticky="w", padx=8, pady=4)
            ttk.Label(hf, text="cm (150–210)", foreground="#444").grid(row=1, column=6, sticky="w", padx=8, pady=4)

            feet_row0 = 2

        # Feet mode
        ttk.Label(hf, text="Feet").grid(row=feet_row0, column=0, sticky="w", padx=8, pady=6)
        ttk.Combobox(hf, textvariable=feet_mode_var, values=["random", "left_only", "left", "right_only", "right", "both"], width=14, state="readonly").grid(row=feet_row0, column=1, sticky="w", padx=8, pady=6)

        # Feet override
        ttk.Checkbutton(hf, text="Override foot ratings (1–20)", variable=feet_override_var).grid(row=feet_row0, column=2, columnspan=3, sticky="w", padx=8, pady=6)

        ttk.Label(hf, text="Left").grid(row=feet_row0 + 1, column=0, sticky="w", padx=8, pady=4)
        left_spin = ttk.Spinbox(hf, from_=1, to=20, textvariable=left_foot_var, width=6)
        left_spin.grid(row=feet_row0 + 1, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(hf, text="Right").grid(row=feet_row0 + 1, column=2, sticky="w", padx=8, pady=4)
        right_spin = ttk.Spinbox(hf, from_=1, to=20, textvariable=right_foot_var, width=6)
        right_spin.grid(row=feet_row0 + 1, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(hf, text="Rule: at least one foot will be forced to 20", foreground="#444").grid(row=feet_row0 + 1, column=4, columnspan=4, sticky="w", padx=8, pady=4)

        def _as_int(s: str, default: int) -> int:
            try:
                return int(str(s).strip())
            except Exception:
                return default

        def _set_state():
            state = ("normal" if feet_override_var.get() else "disabled")
            try:
                left_spin.configure(state=state)
                right_spin.configure(state=state)
            except Exception:
                pass

        def _enforce_one_20(*_):
            # Only enforce when override is ON
            if not feet_override_var.get():
                _set_state()
                return

            mode = (feet_mode_var.get() or "random").strip().lower()
            lf = max(1, min(20, _as_int(left_foot_var.get(), 10)))
            rf = max(1, min(20, _as_int(right_foot_var.get(), 10)))

            # Force rules aligned to generator v6 feet modes
            if mode == "both":
                lf = 20
                rf = 20
            elif mode == "left_only":
                lf = 20
                rf = max(1, min(5, rf))
            elif mode == "left":
                lf = 20
                rf = max(6, min(14, rf))
            elif mode == "right_only":
                rf = 20
                lf = max(1, min(5, lf))
            elif mode == "right":
                rf = 20
                lf = max(6, min(14, lf))
            else:
                # random mode: ensure at least one foot is 20
                if lf < 20 and rf < 20:
                    rf = 20

            left_foot_var.set(str(lf))
            right_foot_var.set(str(rf))
            _set_state()

        feet_override_var.trace_add("write", _enforce_one_20)
        feet_mode_var.trace_add("write", _enforce_one_20)
        left_foot_var.trace_add("write", _enforce_one_20)
        right_foot_var.trace_add("write", _enforce_one_20)
        _enforce_one_20()

    # ---------------- Details (Random / Custom) ----------------



    def _bind_mode_enable(self, mode_var, custom_value, widgets, clear_on_random=False):
        """Enable widgets only when mode_var == custom_value."""
        def _set_state(*_):
            mode = ""
            try:
                mode = (mode_var.get() or "").strip().lower()
            except Exception:
                mode = ""
            enabled = (mode == str(custom_value).strip().lower())
            state = "normal" if enabled else "disabled"
            for w in widgets:
                try:
                    # ttk widgets usually use 'state', some custom widgets may need state() API.
                    w.configure(state=state)
                except Exception:
                    try:
                        if state == "disabled":
                            w.state(["disabled"])
                        else:
                            w.state(["!disabled"])
                    except Exception:
                        pass
                    continue
                if (not enabled) and clear_on_random:
                    try:
                        tv = str(w.cget("textvariable"))
                        if tv:
                            self.setvar(tv, "")
                    except Exception:
                        pass
        try:
            mode_var.trace_add("write", _set_state)
        except Exception:
            pass
        _set_state()

    def _make_searchable_picker(self, parent, textvariable, values, width=48):
        """
        Searchable combobox that:
        - opens dropdown when clicking anywhere
        - filters dynamically as user types
        - Enter picks highlighted/first result
        - click-to-type can overwrite existing value
        """
        vals = list(dict.fromkeys([v for v in (values or []) if str(v).strip() != ""]))
        cb = ttk.Combobox(parent, textvariable=textvariable, values=vals, width=width, state="normal")
        try:
            cb["exportselection"] = False
        except Exception:
            pass

        # Keep an original immutable list on the widget
        cb._all_values = vals  # type: ignore[attr-defined]
        cb._typed_mode = False  # type: ignore[attr-defined]

        def _show_dropdown(event=None):
            # Safe combobox open for Python 3.13/3.14 + Tk on Windows.
            # Avoid event_generate("<Down>") because it can trigger Tcl '??' parsing errors.
            try:
                if str(cb.cget("state")) == "disabled":
                    return None
            except Exception:
                return None

            def _do_post():
                try:
                    cb.tk.call("ttk::combobox::Post", str(cb))
                except Exception:
                    pass
                return None

            try:
                cb.after_idle(_do_post)
            except Exception:
                _do_post()
            return None

        def _filter_now(event=None):
            try:
                current = textvariable.get() if textvariable is not None else cb.get()
            except Exception:
                current = cb.get()
            needle = (current or "").strip().lower()
            all_vals = getattr(cb, "_all_values", vals)
            if not needle:
                filtered = all_vals
            else:
                filtered = [v for v in all_vals if needle in str(v).lower()]
            try:
                cb["values"] = filtered if filtered else all_vals
            except Exception:
                pass
            # open dynamically while typing
            _show_dropdown()

        def _enter_select(event=None):
            current_values = list(cb.cget("values") or [])
            if current_values:
                # If current text exactly matches an option, keep it. Otherwise choose first visible match.
                cur = (cb.get() or "").strip()
                if cur and any(str(v) == cur for v in current_values):
                    return
                try:
                    cb.set(str(current_values[0]))
                except Exception:
                    pass
            return "break"

        def _on_click(event):
            # Click anywhere to browse all options, but also prepare text overwrite on next keypress.
            try:
                all_vals = getattr(cb, "_all_values", vals)
                cb["values"] = all_vals
            except Exception:
                pass
            try:
                cb.focus_set()
            except Exception:
                pass
            try:
                cb.selection_range(0, "end")
                cb.icursor("end")
            except Exception:
                pass
            # Open the dropdown after click processing.
            try:
                cb.after(1, _show_dropdown)
            except Exception:
                _show_dropdown()
            return None

        def _on_focus_in(event=None):
            # Select all so typing overwrites default value without manual delete.
            try:
                cb.selection_range(0, "end")
            except Exception:
                pass

        cb.bind("<Button-1>", _on_click, add="+")
        cb.bind("<KeyRelease>", _filter_now, add="+")
        cb.bind("<Return>", _enter_select, add="+")
        cb.bind("<KP_Enter>", _enter_select, add="+")
        cb.bind("<FocusIn>", _on_focus_in, add="+")
        # Clicking field and dropping with mouse works on Windows by posting list
        return cb

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

    def _add_details_section(self, parent, row: int, prefix: str):
        """
        Shared Details UI block for Batch/Single.
        Adds compact DOB controls in Details with:
        Random(age min/max) / DOB range(start/end) / Fixed(date).
        """
        # Backward-compatible vars for older single-tab state
        if prefix == "single":
            if not hasattr(self, "single_age_min"):
                age_default = getattr(self, "single_age", tk.StringVar(value="14")).get()
                self.single_age_min = tk.StringVar(value=age_default)
            if not hasattr(self, "single_age_max"):
                age_default = getattr(self, "single_age", tk.StringVar(value="14")).get()
                self.single_age_max = tk.StringVar(value=age_default)
            if not hasattr(self, "single_dob_fixed"):
                self.single_dob_fixed = getattr(self, "single_dob", tk.StringVar(value="2012-07-01"))
            if not hasattr(self, "single_dob_start"):
                self.single_dob_start = tk.StringVar(value="2010-01-01")
            if not hasattr(self, "single_dob_end"):
                self.single_dob_end = tk.StringVar(value="2012-12-31")

        _ethnicity_labels = globals().get("_ETHNICITY_LABELS", [
            "Unknown", "Northern European", "Mediterranean/Hispanic",
            "North African/Middle Eastern", "African/Caribbean", "Asian",
            "South East Asian", "Pacific Islander", "Native American",
            "Native Australian", "Mixed Race", "East Asian",
        ])
        _skin_tone_labels = globals().get("_SKIN_TONE_LABELS", ["Unknown"] + [f"Skin Tone {i}" for i in range(1, 21)])
        _body_type_labels = globals().get("_BODY_TYPE_LABELS", ["Ectomorph", "Ecto-Mesomorph", "Mesomorph", "Meso-Endomorph", "Endomorph"])
        _nat_info_labels = globals().get("_NATIONALITY_INFO_LABELS", [
            "No info",
            "Born In Nation",
            "Relative Born In Nation",
            "Declared For Nation",
            "Eligible For Nation",
            "Not Eligible For Nation",
            "Has Played For Nation",
            "Gained Citizenship Through Relative",
            "Gained Citizenship But Not Eligible For Nation Yet",
            "Gained Citizenship But Treated As Foreign",
            "Gained Citizenship And Declared For Nation",
            "Gained Citizenship Through Relative But Not Eligible For Nation Yet",
        ])

        detailsf = ttk.LabelFrame(parent, text="Details")
        detailsf.grid(row=row, column=0, sticky="ew", padx=4, pady=4)
        detailsf.columnconfigure(2, weight=1)

        rows = [
            ("First Name", "first_name", "entry", None),
            ("Second Name", "second_name", "entry", None),
            ("Common Name", "common_name", "entry", None),
            ("Full Name", "full_name", "entry", None),
            ("Gender", "gender", "combo", ["Male", "Female"]),
            ("Ethnicity", "ethnicity", "combo", _ethnicity_labels),
            ("Hair Colour", "hair_colour", "combo", ["Black", "Blond(e)", "Light Blond(e)", "Brown", "Light Brown", "Grey", "Red"]),
            ("Hair Length", "hair_length", "combo", ["Bald", "Short", "Medium", "Long"]),
            ("Skin Tone", "skin_tone", "combo", _skin_tone_labels),
            ("Body Type", "body_type", "combo", _body_type_labels),
            ("City Of Birth", "city_of_birth", "picker_city", None),
            ("Nation Of Birth", "nation_of_birth", "picker_nation", None),
            ("Nation", "nation", "picker_nation", None),
            ("Region Of Birth", "region_of_birth", "disabled", None),
            ("Nationality Info", "nationality_info", "combo", _nat_info_labels),
        ]

        r = 0
        for label, key, kind, options in rows:
            mode_var = getattr(self, f"{prefix}_details_{key}_mode", None)
            value_var = getattr(self, f"{prefix}_details_{key}_value", None)
            if mode_var is None:
                mode_var = tk.StringVar(value="random")
                setattr(self, f"{prefix}_details_{key}_mode", mode_var)
            if value_var is None:
                value_var = tk.StringVar(value="")
                setattr(self, f"{prefix}_details_{key}_value", value_var)

            ttk.Label(detailsf, text=label).grid(row=r, column=0, sticky="w", padx=6, pady=3)
            rb_rand = ttk.Radiobutton(detailsf, text="Random", variable=mode_var, value="random")
            rb_custom = ttk.Radiobutton(detailsf, text="Custom", variable=mode_var, value="custom")
            rb_rand.grid(row=r, column=1, sticky="w", padx=(6, 2))
            rb_custom.grid(row=r, column=1, sticky="w", padx=(85, 2))

            if kind == "disabled":
                rb_rand.configure(state="disabled")
                rb_custom.configure(state="disabled")
                w = ttk.Entry(detailsf, textvariable=value_var, state="disabled")
                w.grid(row=r, column=2, sticky="ew", padx=6, pady=3)
                r += 1
                continue

            if kind == "entry":
                w = ttk.Entry(detailsf, textvariable=value_var)
            elif kind == "combo":
                w = self._make_searchable_picker(detailsf, value_var, list(options or []), width=48)
            elif kind == "picker_city":
                city_rows = list(self._load_master_library_rows(kind="city"))
                city_labels = [x.get("city_name") or x.get("name") or "" for x in city_rows]
                city_labels = [x for x in city_labels if x]
                w = self._make_searchable_picker(detailsf, value_var, city_labels, width=48)
            elif kind == "picker_nation":
                nation_rows = list(self._load_master_library_rows(kind="nation"))
                nation_labels = [x.get("nation_name") or x.get("name") or "" for x in nation_rows]
                nation_labels = [x for x in nation_labels if x]
                w = self._make_searchable_picker(detailsf, value_var, nation_labels, width=48)
            else:
                w = ttk.Entry(detailsf, textvariable=value_var)

            w.grid(row=r, column=2, sticky="ew", padx=6, pady=3)
            self._bind_mode_enable(mode_var, "custom", [w], clear_on_random=False)
            r += 1

        # Second Nations block in Details (FM-style multi-row editor/list)
        snf = ttk.LabelFrame(detailsf, text="Second Nations")
        snf.grid(row=r, column=0, columnspan=3, sticky="ew", padx=6, pady=(8, 4))
        snf.columnconfigure(0, weight=1)

        # Shared option lists
        _sn_nation_rows = list(self._load_master_library_rows(kind="nation"))
        _sn_nation_labels = [x.get("nation_name") or x.get("name") or "" for x in _sn_nation_rows]
        _sn_nation_labels = [x for x in _sn_nation_labels if x]

        # Persistent per-prefix state/vars
        sn_items = getattr(self, f"{prefix}_second_nations_items", None)
        if sn_items is None:
            sn_items = []
            setattr(self, f"{prefix}_second_nations_items", sn_items)
        if not hasattr(self, f"{prefix}_second_nations_clipboard"):
            setattr(self, f"{prefix}_second_nations_clipboard", None)

        def _sn_var(name: str, default="", boolvar: bool = False):
            attr = f"{prefix}_second_nations_{name}"
            v = getattr(self, attr, None)
            if v is None:
                v = tk.BooleanVar(value=bool(default)) if boolvar else tk.StringVar(value=str(default))
                setattr(self, attr, v)
            return v

        sn_nation_var = _sn_var("nation", "")
        sn_nat_info_var = _sn_var("nationality_info", _nat_info_labels[0] if _nat_info_labels else "No info")
        sn_declared_var = _sn_var("nation_declared_for", "")
        sn_declared_youth_var = _sn_var("nation_declared_for_youth", "")
        sn_int_ret_var = _sn_var("international_retirement", False, boolvar=True)
        sn_int_ret_date_var = _sn_var("international_retirement_date", "")
        sn_retire_spell_var = _sn_var("retiring_after_spell_current_club", False, boolvar=True)
        sn_comment_var = _sn_var("comment", "")

        btnbar = ttk.Frame(snf)
        btnbar.grid(row=0, column=0, sticky="ew", padx=6, pady=(6, 4))
        for _c in range(12):
            btnbar.columnconfigure(_c, weight=0)
        btnbar.columnconfigure(11, weight=1)

        listwrap = ttk.Frame(snf)
        listwrap.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))
        listwrap.columnconfigure(0, weight=1)
        listwrap.rowconfigure(1, weight=1)

        sn_count_var = tk.StringVar(value=f"{len(sn_items)} items")
        ttk.Label(listwrap, textvariable=sn_count_var).grid(row=0, column=0, sticky="w", pady=(0, 3))

        treefrm = ttk.Frame(listwrap)
        treefrm.grid(row=1, column=0, sticky="nsew")
        treefrm.columnconfigure(0, weight=1)
        treefrm.rowconfigure(0, weight=1)

        sn_tree = ttk.Treeview(treefrm, columns=("nation", "nationality_info"), show="headings", height=6, selectmode="browse")
        sn_tree.heading("nation", text="Nation")
        sn_tree.heading("nationality_info", text="Nationality Info")
        sn_tree.column("nation", width=220, anchor="w")
        sn_tree.column("nationality_info", width=260, anchor="w")
        sn_tree.grid(row=0, column=0, sticky="nsew")
        sn_scroll = ttk.Scrollbar(treefrm, orient="vertical", command=sn_tree.yview)
        sn_scroll.grid(row=0, column=1, sticky="ns")
        sn_tree.configure(yscrollcommand=sn_scroll.set)

        setattr(self, f"{prefix}_second_nations_tree", sn_tree)

        editf = ttk.Frame(snf)
        editf.grid(row=2, column=0, sticky="ew", padx=6, pady=(0, 6))
        for _c in range(5):
            editf.columnconfigure(_c, weight=1 if _c in (1, 3) else 0)

        ttk.Label(editf, text="Nation").grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        sn_nation_picker = self._make_searchable_picker(editf, sn_nation_var, _sn_nation_labels, width=34)
        sn_nation_picker.grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=3)

        ttk.Label(editf, text="Nationality Info").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=3)
        sn_nat_info_picker = self._make_searchable_picker(editf, sn_nat_info_var, list(_nat_info_labels), width=34)
        sn_nat_info_picker.grid(row=0, column=3, sticky="ew", padx=(0, 10), pady=3)

        sn_int_ret_chk = ttk.Checkbutton(editf, text="International Retirement", variable=sn_int_ret_var)
        sn_int_ret_chk.grid(row=1, column=0, columnspan=2, sticky="w", pady=3)

        ttk.Label(editf, text="International Retirement Date").grid(row=1, column=2, sticky="w", padx=(0, 6), pady=3)
        sn_int_ret_date_entry = ttk.Entry(editf, textvariable=sn_int_ret_date_var, width=16)
        sn_int_ret_date_entry.grid(row=1, column=3, sticky="w", pady=3)
        sn_int_ret_date_btn = ttk.Button(editf, text="📅", width=3, command=lambda v=sn_int_ret_date_var: self._open_calendar(v))
        sn_int_ret_date_btn.grid(row=1, column=4, sticky="w", padx=(4, 0), pady=3)

        sn_retire_spell_chk = ttk.Checkbutton(editf, text="Retiring After Spell At Current Club", variable=sn_retire_spell_var)
        sn_retire_spell_chk.grid(row=2, column=0, columnspan=4, sticky="w", pady=(3, 1))

        # Comment is stored but kept compact/hidden from the layout; Add Comment button marks selected item.
        _sn_syncing = {"on": False}

        def _sn_record_from_editor():
            return {
                "nation": (sn_nation_var.get() or "").strip(),
                "nationality_info": (sn_nat_info_var.get() or "").strip(),
                "nation_declared_for": (sn_declared_var.get() or "").strip(),
                "nation_declared_for_youth": (sn_declared_youth_var.get() or "").strip(),
                "international_retirement": bool(sn_int_ret_var.get()),
                "international_retirement_date": (sn_int_ret_date_var.get() or "").strip(),
                "retiring_after_spell_current_club": bool(sn_retire_spell_var.get()),
                "comment": (sn_comment_var.get() or "").strip(),
            }

        def _sn_set_editor(rec: dict | None):
            _sn_syncing["on"] = True
            try:
                rec = rec or {}
                sn_nation_var.set(rec.get("nation", "") or "")
                sn_nat_info_var.set(rec.get("nationality_info", (_nat_info_labels[0] if _nat_info_labels else "No info")) or "")
                sn_declared_var.set(rec.get("nation_declared_for", "") or "")
                sn_declared_youth_var.set(rec.get("nation_declared_for_youth", "") or "")
                sn_int_ret_var.set(bool(rec.get("international_retirement", False)))
                sn_int_ret_date_var.set(rec.get("international_retirement_date", "") or "")
                sn_retire_spell_var.set(bool(rec.get("retiring_after_spell_current_club", False)))
                sn_comment_var.set(rec.get("comment", "") or "")
            finally:
                _sn_syncing["on"] = False

        def _sn_selected_index():
            sel = sn_tree.selection()
            if not sel:
                return None
            try:
                return int(str(sel[0]))
            except Exception:
                return None

        def _sn_refresh_tree(select_idx=None):
            try:
                for iid in sn_tree.get_children():
                    sn_tree.delete(iid)
            except Exception:
                pass
            for idx, rec in enumerate(sn_items):
                sn_tree.insert("", "end", iid=str(idx), values=(
                    rec.get("nation", "") or "",
                    rec.get("nationality_info", "") or "",
                ))
            sn_count_var.set(f"{len(sn_items)} items")
            if select_idx is not None and 0 <= int(select_idx) < len(sn_items):
                iid = str(int(select_idx))
                try:
                    sn_tree.selection_set(iid)
                    sn_tree.focus(iid)
                    sn_tree.see(iid)
                except Exception:
                    pass

        def _sn_on_select(event=None):
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            _sn_set_editor(dict(sn_items[idx]))

        def _sn_update_selected_from_editor(*_):
            if _sn_syncing["on"]:
                return
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            sn_items[idx] = _sn_record_from_editor()
            _sn_refresh_tree(select_idx=idx)

        def _sn_add():
            rec = _sn_record_from_editor()
            sn_items.append(dict(rec))
            _sn_refresh_tree(select_idx=len(sn_items) - 1)

        def _sn_insert():
            rec = _sn_record_from_editor()
            idx = _sn_selected_index()
            if idx is None:
                sn_items.append(dict(rec))
                idx = len(sn_items) - 1
            else:
                sn_items.insert(idx, dict(rec))
            _sn_refresh_tree(select_idx=idx)

        def _sn_duplicate():
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            sn_items.insert(idx + 1, dict(sn_items[idx]))
            _sn_refresh_tree(select_idx=idx + 1)

        def _sn_move(delta: int):
            idx = _sn_selected_index()
            if idx is None:
                return
            new_idx = idx + delta
            if new_idx < 0 or new_idx >= len(sn_items):
                return
            sn_items[idx], sn_items[new_idx] = sn_items[new_idx], sn_items[idx]
            _sn_refresh_tree(select_idx=new_idx)

        def _sn_sort():
            if not sn_items:
                return
            idx = _sn_selected_index()
            current = None
            if idx is not None and 0 <= idx < len(sn_items):
                current = dict(sn_items[idx])
            sn_items.sort(key=lambda rec: ((rec.get("nation") or "").lower(), (rec.get("nationality_info") or "").lower()))
            new_idx = None
            if current is not None:
                for i, rec in enumerate(sn_items):
                    if rec == current:
                        new_idx = i
                        break
            _sn_refresh_tree(select_idx=new_idx if new_idx is not None else 0)

        def _sn_remove():
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            del sn_items[idx]
            new_idx = min(idx, len(sn_items) - 1)
            _sn_refresh_tree(select_idx=new_idx if new_idx >= 0 else None)
            if not sn_items:
                _sn_set_editor(None)

        def _sn_copy():
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                return
            setattr(self, f"{prefix}_second_nations_clipboard", dict(sn_items[idx]))

        def _sn_paste():
            clip = getattr(self, f"{prefix}_second_nations_clipboard", None)
            if not isinstance(clip, dict):
                return
            idx = _sn_selected_index()
            if idx is None:
                sn_items.append(dict(clip))
                idx = len(sn_items) - 1
            else:
                sn_items.insert(idx + 1, dict(clip))
                idx = idx + 1
            _sn_refresh_tree(select_idx=idx)

        def _sn_clear():
            sn_items.clear()
            _sn_refresh_tree()
            _sn_set_editor(None)

        def _sn_add_comment():
            idx = _sn_selected_index()
            if idx is None or idx < 0 or idx >= len(sn_items):
                try:
                    messagebox.showinfo("Second Nations", "Select an item first, then click Add Comment.")
                except Exception:
                    pass
                return
            rec = dict(sn_items[idx])
            existing = (rec.get("comment") or "").strip()
            rec["comment"] = existing if existing else "Comment"
            sn_items[idx] = rec
            _sn_set_editor(rec)
            _sn_refresh_tree(select_idx=idx)

        _sn_buttons = [
            ("Add", _sn_add),
            ("Insert", _sn_insert),
            ("Duplicate", _sn_duplicate),
            ("Move Up", lambda: _sn_move(-1)),
            ("Move Down", lambda: _sn_move(1)),
            ("Sort", _sn_sort),
            ("Remove", _sn_remove),
            ("Copy", _sn_copy),
            ("Paste", _sn_paste),
            ("Clear", _sn_clear),
            ("Add Comment", _sn_add_comment),
        ]
        for _i, (_txt, _cmd) in enumerate(_sn_buttons):
            ttk.Button(btnbar, text=_txt, command=_cmd).grid(row=0, column=_i, sticky="w", padx=(0, 4), pady=0)

        sn_tree.bind("<<TreeviewSelect>>", _sn_on_select, add="+")
        for _v in (sn_nation_var, sn_nat_info_var, sn_declared_var, sn_declared_youth_var, sn_int_ret_date_var, sn_comment_var):
            try:
                _v.trace_add("write", _sn_update_selected_from_editor)
            except Exception:
                pass
        for _bv in (sn_int_ret_var, sn_retire_spell_var):
            try:
                _bv.trace_add("write", _sn_update_selected_from_editor)
            except Exception:
                pass

        _sn_refresh_tree()
        if sn_items:
            _sn_refresh_tree(select_idx=0)

        r += 1

        # Declared For Nation At Youth Level (separate FM field; not inside Second Nations list rows)
        dyf = ttk.LabelFrame(detailsf, text="Declared For Nation At Youth Level")
        dyf.grid(row=r, column=0, columnspan=3, sticky="ew", padx=6, pady=(8, 4))
        dyf.columnconfigure(4, weight=1)

        dy_mode_var = getattr(self, f"{prefix}_details_declared_for_youth_nation_mode", None)
        if dy_mode_var is None:
            dy_mode_var = tk.StringVar(value="random")
            setattr(self, f"{prefix}_details_declared_for_youth_nation_mode", dy_mode_var)

        dy_value_var = getattr(self, f"{prefix}_details_declared_for_youth_nation_value", None)
        if dy_value_var is None:
            dy_value_var = tk.StringVar(value="")
            setattr(self, f"{prefix}_details_declared_for_youth_nation_value", dy_value_var)

        ttk.Radiobutton(dyf, text="Random", variable=dy_mode_var, value="random").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(dyf, text="Custom", variable=dy_mode_var, value="custom").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Label(dyf, text="Nation").grid(row=0, column=2, sticky="e", padx=(10, 6), pady=6)
        dy_picker = self._make_searchable_picker(dyf, dy_value_var, _sn_nation_labels, width=34)
        dy_picker.grid(row=0, column=3, sticky="ew", padx=(0, 8), pady=6)

        try:
            self._bind_mode_enable(dy_mode_var, "custom", [dy_picker], clear_on_random=False)
        except Exception:
            pass

        r += 1

        # Height block in Details (same layout style as Other tab height controls)
        hbox = ttk.LabelFrame(detailsf, text="Height")
        hbox.grid(row=r, column=0, columnspan=3, sticky="ew", padx=6, pady=(8, 4))
        for c in range(6):
            hbox.columnconfigure(c, weight=0)

        # New preferred Details height vars (kept separate from legacy details_height_mode/value)
        h_mode_var = getattr(self, f"{prefix}_details_height_mode2", None)
        if h_mode_var is None:
            h_mode_var = tk.StringVar(value="range")
            setattr(self, f"{prefix}_details_height_mode2", h_mode_var)

        h_min_var = getattr(self, f"{prefix}_details_height_min", None)
        if h_min_var is None:
            h_min_var = tk.StringVar(value="150")
            setattr(self, f"{prefix}_details_height_min", h_min_var)

        h_max_var = getattr(self, f"{prefix}_details_height_max", None)
        if h_max_var is None:
            h_max_var = tk.StringVar(value="210")
            setattr(self, f"{prefix}_details_height_max", h_max_var)

        h_fixed_var = getattr(self, f"{prefix}_details_height_fixed", None)
        if h_fixed_var is None:
            legacy_h = getattr(self, f"{prefix}_details_height_value", tk.StringVar(value="")).get()
            h_fixed_var = tk.StringVar(value=legacy_h)
            setattr(self, f"{prefix}_details_height_fixed", h_fixed_var)

        ttk.Radiobutton(hbox, text="Random height range", variable=h_mode_var, value="range").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(hbox, text="Fixed height", variable=h_mode_var, value="fixed").grid(row=0, column=4, sticky="w", padx=8, pady=6)

        ttk.Label(hbox, text="Min").grid(row=1, column=0, sticky="e", padx=(8, 2), pady=4)
        h_min_entry = ttk.Entry(hbox, textvariable=h_min_var, width=6)
        h_min_entry.grid(row=1, column=1, sticky="w", padx=8, pady=4)
        ttk.Label(hbox, text="Max").grid(row=1, column=2, sticky="e", padx=(8, 2), pady=4)
        h_max_entry = ttk.Entry(hbox, textvariable=h_max_var, width=6)
        h_max_entry.grid(row=1, column=3, sticky="w", padx=8, pady=4)
        ttk.Label(hbox, text="Height").grid(row=1, column=4, sticky="e", padx=(8, 2), pady=4)
        h_fixed_entry = ttk.Entry(hbox, textvariable=h_fixed_var, width=6)
        h_fixed_entry.grid(row=1, column=5, sticky="w", padx=8, pady=4)

        def _refresh_details_height_mode(*_):
            mode = (h_mode_var.get() or "range").strip()
            range_state = "normal" if mode == "range" else "disabled"
            fixed_state = "normal" if mode == "fixed" else "disabled"
            for w in (h_min_entry, h_max_entry):
                try:
                    w.configure(state=range_state)
                except Exception:
                    pass
            try:
                h_fixed_entry.configure(state=fixed_state)
            except Exception:
                pass

        try:
            h_mode_var.trace_add("write", _refresh_details_height_mode)
        except Exception:
            pass
        _refresh_details_height_mode()
        r += 1

        # Compact DOB block in Details (uses main batch/single DOB vars)
        dobf = ttk.LabelFrame(detailsf, text="DOB (Age range / DOB range / Fixed)")
        dobf.grid(row=r, column=0, columnspan=3, sticky="ew", padx=6, pady=(8, 4))
        for c in range(10):
            dobf.columnconfigure(c, weight=0)

        mode_var = getattr(self, f"{prefix}_dob_mode")
        age_min_var = getattr(self, f"{prefix}_age_min", None)
        age_max_var = getattr(self, f"{prefix}_age_max", None)
        if age_min_var is None:
            age_seed = getattr(self, f"{prefix}_age", tk.StringVar(value="14")).get()
            age_min_var = tk.StringVar(value=age_seed)
            setattr(self, f"{prefix}_age_min", age_min_var)
        if age_max_var is None:
            age_seed = getattr(self, f"{prefix}_age", tk.StringVar(value="14")).get()
            age_max_var = tk.StringVar(value=age_seed)
            setattr(self, f"{prefix}_age_max", age_max_var)

        dob_fixed_var = getattr(self, f"{prefix}_dob_fixed", None)
        if dob_fixed_var is None:
            dob_fixed_var = getattr(self, f"{prefix}_dob", tk.StringVar(value="2012-07-01"))
            setattr(self, f"{prefix}_dob_fixed", dob_fixed_var)
        dob_start_var = getattr(self, f"{prefix}_dob_start", None)
        if dob_start_var is None:
            dob_start_var = tk.StringVar(value="2010-01-01")
            setattr(self, f"{prefix}_dob_start", dob_start_var)
        dob_end_var = getattr(self, f"{prefix}_dob_end", None)
        if dob_end_var is None:
            dob_end_var = tk.StringVar(value="2012-12-31")
            setattr(self, f"{prefix}_dob_end", dob_end_var)

        # Layout requested:
        # Random [radio] - Age[min/max] - DOB Range[start/end] - DOB Fix[date]
        # Keep legacy mode compatibility:
        # - Batch legacy uses "range"/"fixed"
        # - Single legacy uses "age"/"dob" (where "dob" means fixed DOB)
        dob_range_value = "range"
        dob_fixed_value = "dob" if prefix == "single" else "fixed"

        ttk.Radiobutton(dobf, text="Random", variable=mode_var, value="age").grid(row=0, column=0, sticky="w", padx=(6, 10), pady=(6, 2))
        ttk.Label(dobf, text="Age").grid(row=0, column=1, sticky="w", padx=(0, 4))
        ttk.Label(dobf, text="Min").grid(row=0, column=2, sticky="e", padx=(0, 4))
        age_min_entry = ttk.Entry(dobf, textvariable=age_min_var, width=7)
        age_min_entry.grid(row=0, column=3, sticky="w", padx=(0, 12), pady=(6, 2))
        ttk.Label(dobf, text="Max").grid(row=1, column=2, sticky="e", padx=(0, 4))
        age_max_entry = ttk.Entry(dobf, textvariable=age_max_var, width=7)
        age_max_entry.grid(row=1, column=3, sticky="w", padx=(0, 12), pady=(2, 6))

        ttk.Radiobutton(dobf, text="DOB Range", variable=mode_var, value=dob_range_value).grid(row=0, column=4, sticky="w", padx=(0, 8), pady=(6, 2))
        ttk.Label(dobf, text="Start").grid(row=0, column=5, sticky="e", padx=(0, 4))
        start_entry = ttk.Entry(dobf, textvariable=dob_start_var, width=12)
        start_entry.grid(row=0, column=6, sticky="w", pady=(6, 2))
        start_btn = ttk.Button(dobf, text="📅", width=3, command=lambda v=dob_start_var: self._open_calendar(v))
        start_btn.grid(row=0, column=7, sticky="w", padx=(4, 12), pady=(6, 2))

        ttk.Label(dobf, text="End").grid(row=1, column=5, sticky="e", padx=(0, 4))
        end_entry = ttk.Entry(dobf, textvariable=dob_end_var, width=12)
        end_entry.grid(row=1, column=6, sticky="w", pady=(2, 6))
        end_btn = ttk.Button(dobf, text="📅", width=3, command=lambda v=dob_end_var: self._open_calendar(v))
        end_btn.grid(row=1, column=7, sticky="w", padx=(4, 12), pady=(2, 6))

        ttk.Radiobutton(dobf, text="DOB Fix", variable=mode_var, value=dob_fixed_value).grid(row=0, column=8, sticky="w", padx=(0, 8), pady=(6, 2))
        ttk.Label(dobf, text="Date").grid(row=0, column=9, sticky="w", padx=(0, 4), pady=(6, 2))
        fixed_entry = ttk.Entry(dobf, textvariable=dob_fixed_var, width=12)
        fixed_entry.grid(row=1, column=8, sticky="w", padx=(0, 4), pady=(2, 6))
        fixed_btn = ttk.Button(dobf, text="📅", width=3, command=lambda v=dob_fixed_var: self._open_calendar(v))
        fixed_btn.grid(row=1, column=9, sticky="w", pady=(2, 6))

        def _refresh_dob_mode(*_):
            mode = (mode_var.get() or "age").strip()
            age_state = "normal" if mode == "age" else "disabled"
            range_state = "normal" if mode == dob_range_value else "disabled"
            fixed_state = "normal" if mode == dob_fixed_value else "disabled"
            for w in (age_min_entry, age_max_entry):
                try:
                    w.configure(state=age_state)
                except Exception:
                    pass
            for w in (start_entry, end_entry, start_btn, end_btn):
                try:
                    w.configure(state=range_state)
                except Exception:
                    pass
            for w in (fixed_entry, fixed_btn):
                try:
                    w.configure(state=fixed_state)
                except Exception:
                    pass

        try:
            mode_var.trace_add("write", _refresh_dob_mode)
        except Exception:
            pass
        _refresh_dob_mode()

        # Move Details blocks to requested positions:
        # - Height above Body Type
        # - DOB above City Of Birth
        def _find_details_row_by_label_text(text: str):
            for _w in detailsf.grid_slaves():
                try:
                    if str(_w.cget("text")) == text:
                        gi = _w.grid_info()
                        return int(gi.get("row", 0))
                except Exception:
                    continue
            return None

        def _move_row_widget_above(_widget, target_row: int):
            try:
                giw = _widget.grid_info()
                src_row = int(giw.get("row", 0))
            except Exception:
                return
            if target_row is None or src_row <= int(target_row):
                return
            target_row = int(target_row)
            # Shift every widget row in [target_row, src_row-1] down by one, then place widget at target_row
            for _child in detailsf.grid_slaves():
                if _child is _widget:
                    continue
                try:
                    gic = _child.grid_info()
                    crow = int(gic.get("row", 0))
                except Exception:
                    continue
                if target_row <= crow < src_row:
                    try:
                        _child.grid_configure(row=crow + 1)
                    except Exception:
                        pass
            try:
                _widget.grid_configure(row=target_row)
            except Exception:
                pass

        _body_row = _find_details_row_by_label_text("Body Type")
        if _body_row is not None:
            _move_row_widget_above(hbox, _body_row)

        _city_row = _find_details_row_by_label_text("City Of Birth")
        if _city_row is not None:
            _move_row_widget_above(dobf, _city_row)

    def _build_batch_details_tab(self) -> None:
        frm = self.batch_details_body
        for c in range(3):
            frm.columnconfigure(c, weight=1)

        # Mirrored file inputs on Details tab (same vars as Other tab)
        paths = ttk.LabelFrame(frm, text="File inputs")
        paths.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        paths.columnconfigure(1, weight=1)
        self.batch_details_paths_frame = paths
        paths.grid_remove()

        def row_file(r, label, var, is_save=False):
            ttk.Label(paths, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ttk.Entry(paths, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            if is_save:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_save_xml(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)
            else:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_open_file(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "master_library.csv:", self.batch_clubs, is_save=False)
        row_file(1, "First names CSV:", self.batch_first, is_save=False)
        row_file(2, "Surnames CSV:", self.batch_surn, is_save=False)
        row_file(3, "Output XML:", self.batch_out, is_save=True)
        row_file(4, "Generator script:", self.batch_script, is_save=False)
        row_file(5, "Region mapping CSV (placeholder):", self.batch_region_map_csv, is_save=False)

        genf = ttk.LabelFrame(frm, text="Generation settings (synced with Other)")
        genf.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for _c in range(6):
            genf.columnconfigure(_c, weight=1)
        ttk.Label(genf, text="Count").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(genf, textvariable=self.batch_count, width=10).grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(genf, text="Seed").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(genf, textvariable=self.batch_seed, width=10).grid(row=0, column=3, sticky="w", padx=6, pady=6)
        ttk.Label(genf, text="Base year").grid(row=0, column=4, sticky="w", padx=6, pady=6)
        ttk.Entry(genf, textvariable=self.batch_base_year, width=10).grid(row=0, column=5, sticky="w", padx=6, pady=6)

        self._add_details_section(frm, row=2, prefix="batch")
        try:
            ttk.Label(
                frm,
                text="Details settings for Batch generation. Region Of Birth is disabled until custom region mapping is configured.",
                foreground="#444",
                wraplength=900,
                justify="left",
            ).grid(row=3, column=0, sticky="w", padx=8, pady=(0, 8))
        except Exception:
            pass

    def _build_single_details_tab(self) -> None:
        frm = self.single_details_body
        for c in range(3):
            frm.columnconfigure(c, weight=1)

        # Mirrored file inputs on Details tab (same vars as Other tab)
        paths = ttk.LabelFrame(frm, text="File inputs")
        paths.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        paths.columnconfigure(1, weight=1)
        self.single_details_paths_frame = paths
        paths.grid_remove()

        def row_file(r, label, var, is_save=False):
            ttk.Label(paths, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ttk.Entry(paths, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            if is_save:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_save_xml(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)
            else:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_open_file(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "master_library.csv:", self.single_clubs, is_save=False)
        row_file(1, "First names CSV:", self.single_first, is_save=False)
        row_file(2, "Surnames CSV:", self.single_surn, is_save=False)
        row_file(3, "Output XML:", self.single_out, is_save=True)
        row_file(4, "Generator script:", self.single_script, is_save=False)
        row_file(5, "Region mapping CSV (placeholder):", self.single_region_map_csv, is_save=False)

        genf = ttk.LabelFrame(frm, text="Generation settings (synced with Other)")
        genf.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for _c in range(4):
            genf.columnconfigure(_c, weight=1)
        ttk.Label(genf, text="Seed").grid(row=0, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(genf, textvariable=self.single_seed, width=10).grid(row=0, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(genf, text="Base year").grid(row=0, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(genf, textvariable=self.single_base_year, width=10).grid(row=0, column=3, sticky="w", padx=6, pady=6)

        self._add_details_section(frm, row=2, prefix="single")
        try:
            ttk.Label(
                frm,
                text="Details settings for Single-player generation. Region Of Birth is disabled until custom region mapping is configured.",
                foreground="#444",
                wraplength=900,
                justify="left",
            ).grid(row=3, column=0, sticky="w", padx=8, pady=(0, 8))
        except Exception:
            pass

    # ---------------- Master library cache (clubs/cities/nations) ----------------


    def _init_batch_single_file_sync(self) -> None:
        """Sync shared file/script inputs between Batch and Single and auto-reload master library on change."""
        self._path_sync_guard = False
        self._master_reload_job = None

        pairs = [
            ("batch_clubs", "single_clubs", True),            # master_library.csv
            ("batch_first", "single_first", False),           # first names csv
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
                        label = f"{name} (DBID {dbid})" if name else f"Club DBID {dbid}"
                        clubs.append(label)
                        club_map[label] = (dbid, lg)
                    elif kind == "city":
                        dbid = (row.get("city_dbid") or "").strip()
                        lg = (row.get("city_large") or "").strip()
                        name = (row.get("city_name") or "").strip()
                        if not dbid or not lg:
                            continue
                        label = f"{name} (DBID {dbid})" if name else f"City DBID {dbid}"
                        cities.append(label)
                        city_map[label] = (dbid, lg)
                    elif kind == "nation":
                        dbid = (row.get("nation_dbid") or "").strip()
                        lg = (row.get("nnat_large") or "").strip()
                        name = (row.get("nation_name") or "").strip()
                        if not dbid or not lg:
                            continue
                        label = f"{name} (DBID {dbid})" if name else f"Nation DBID {dbid}"
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

        for attr, values in [
            ("batch_club_combo", clubs),
            ("batch_city_combo", cities),
            ("batch_nation_combo", nations),
            ("batch_details_city_combo", cities),
            ("batch_details_region_combo", nations),
            ("single_club_combo", clubs),
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

        try:
            self._master_library_last_sig = self._current_master_library_sig()
        except Exception:
            pass
        self._log(f"[OK] Loaded library pickers: clubs={len(clubs)}, cities={len(cities)}, nations={len(nations)}\n")

    def _combo_state_for_mode(self, mode_var: tk.StringVar, combo: ttk.Combobox) -> None:
        try:
            combo.configure(state=("readonly" if mode_var.get() == "fixed" else "disabled"))
        except Exception:
            pass

    def _get_fixed_ids(self, kind: str, label: str) -> tuple[str, str] | None:
        if not label:
            return None
        if kind == "club":
            return getattr(self, "_club_map", {}).get(label)
        if kind == "city":
            return getattr(self, "_city_map", {}).get(label)
        if kind == "nation":
            return getattr(self, "_nation_map", {}).get(label)
        return None

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

    def _build_batch_tab(self) -> None:
        frm = self.batch_body
        frm.columnconfigure(1, weight=1)

        self.batch_clubs = tk.StringVar(value=str(self.fmdata_dir / "master_library.csv"))
        self.batch_first = tk.StringVar(value=str(self.fmdata_dir / "scottish_male_first_names_2500.csv"))
        self.batch_surn = tk.StringVar(value=str(self.fmdata_dir / "scottish_surnames_2500.csv"))
        self.batch_out = tk.StringVar(value=str(self.fmdata_dir / "fm26_players.xml"))
        self.batch_script = tk.StringVar(value=str(self.fmdata_dir / DEFAULT_GENERATE_SCRIPT))

        self.batch_count = tk.StringVar(value="1000")
        self.batch_seed = tk.StringVar(value="123")
        self.batch_base_year = tk.StringVar(value="2026")

        # Details (Random / Custom section vars are created by _add_details_section)

        self.batch_age_min = tk.StringVar(value="14")
        self.batch_age_max = tk.StringVar(value="16")
        self.batch_ca_min = tk.StringVar(value="20")
        self.batch_ca_max = tk.StringVar(value="160")
        self.batch_pa_min = tk.StringVar(value="80")
        self.batch_pa_max = tk.StringVar(value="200")

        # DOB mode
        self.batch_dob_mode = tk.StringVar(value="range")  # age|range|fixed (Age range controls moved to Details tab)
        self.batch_dob_fixed = tk.StringVar(value="2012-07-01")
        self.batch_dob_start = tk.StringVar(value="2010-01-01")
        self.batch_dob_end = tk.StringVar(value="2012-12-31")

        # XML date overrides (optional)
        self.batch_moved_to_nation_mode = tk.StringVar(value="dob")  # dob|fixed
        self.batch_moved_to_nation_date = tk.StringVar(value="")
        self.batch_joined_club_mode = tk.StringVar(value="auto")  # auto|fixed
        self.batch_joined_club_date = tk.StringVar(value="")
        self.batch_contract_expires_mode = tk.StringVar(value="auto")  # auto|fixed
        self.batch_contract_expires_date = tk.StringVar(value="")

        # Height
        self.batch_height_mode = tk.StringVar(value="range")  # range|fixed
        self.batch_height_min = tk.StringVar(value="150")
        self.batch_height_max = tk.StringVar(value="210")
        self.batch_height_fixed = tk.StringVar(value="")

        # Feet
        self.batch_feet_mode = tk.StringVar(value="random")
        self.batch_feet_override = tk.BooleanVar(value=False)
        self.batch_left_foot = tk.StringVar(value="10")
        self.batch_right_foot = tk.StringVar(value="20")

        # Wage / Reputation / Transfer value
        self.batch_wage_mode = tk.StringVar(value="range")  # range|fixed
        self.batch_wage_min = tk.StringVar(value="30")
        self.batch_wage_max = tk.StringVar(value="80")
        self.batch_wage_fixed = tk.StringVar(value="")

        self.batch_rep_mode = tk.StringVar(value="range")  # range|fixed
        self.batch_rep_min = tk.StringVar(value="0")
        self.batch_rep_max = tk.StringVar(value="200")
        self.batch_rep_current = tk.StringVar(value="")
        self.batch_rep_home = tk.StringVar(value="")
        self.batch_rep_world = tk.StringVar(value="")

        self.batch_tv_mode = tk.StringVar(value="auto")  # auto|fixed|range
        self.batch_tv_fixed = tk.StringVar(value="")
        self.batch_tv_min = tk.StringVar(value="")
        self.batch_tv_max = tk.StringVar(value="")

        # Positions
        self.batch_positions_random = tk.BooleanVar(value=True)
        self.batch_pos_vars: dict[str, tk.BooleanVar] = {p: tk.BooleanVar(value=False) for p in ALL_POS}

        # Development positions (extra positions added at 2..19)
        self.batch_dev_enable = tk.BooleanVar(value=True)
        self.batch_auto_dev_chance = tk.StringVar(value="15")  # percent (0..100)

        # Position distributions (used only when Random positions is ON)
        self.batch_dist_gk = tk.StringVar(value="15")
        self.batch_dist_def = tk.StringVar(value="35")
        self.batch_dist_mid = tk.StringVar(value="35")
        self.batch_dist_st = tk.StringVar(value="15")
        self.batch_n20_1 = tk.StringVar(value="39")
        self.batch_n20_2 = tk.StringVar(value="18")
        self.batch_n20_3 = tk.StringVar(value="13")
        self.batch_n20_4 = tk.StringVar(value="11")
        self.batch_n20_5 = tk.StringVar(value="8")
        self.batch_n20_6 = tk.StringVar(value="5.5")
        self.batch_n20_7 = tk.StringVar(value="3.6")
        self.batch_n20_8_12 = tk.StringVar(value="1.4")
        self.batch_n20_13 = tk.StringVar(value="0.5")
        self.batch_dev_mode = tk.StringVar(value="random")  # random|fixed|range
        self.batch_dev_fixed = tk.StringVar(value="10")
        self.batch_dev_min = tk.StringVar(value="2")
        self.batch_dev_max = tk.StringVar(value="19")

        # File inputs (hidden by default)
        self.batch_region_map_csv = tk.StringVar(value="")  # placeholder for future region mapping
        paths = ttk.LabelFrame(frm, text="File inputs")
        paths.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        paths.columnconfigure(1, weight=1)
        self.batch_paths_frame = paths
        paths.grid_remove()

        def row_file(r, label, var, is_save=False):
            ttk.Label(paths, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ttk.Entry(paths, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            if is_save:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_save_xml(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)
            else:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_open_file(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "master_library.csv:", self.batch_clubs, is_save=False)
        row_file(1, "First names CSV:", self.batch_first, is_save=False)
        row_file(2, "Surnames CSV:", self.batch_surn, is_save=False)
        row_file(3, "Output XML:", self.batch_out, is_save=True)
        row_file(4, "Generator script:", self.batch_script, is_save=False)
        row_file(5, "Region mapping CSV (placeholder):", self.batch_region_map_csv, is_save=False)

        opt = ttk.LabelFrame(frm, text="Batch options")
        opt.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 8))
        for c in range(6):
            opt.columnconfigure(c, weight=1)

        def opt_field(r, c, label, var, width=10):
            ttk.Label(opt, text=label).grid(row=r, column=c, sticky="w", padx=6, pady=6)
            ttk.Entry(opt, textvariable=var, width=width).grid(row=r, column=c + 1, sticky="w", padx=6, pady=6)

        opt_field(0, 0, "Count", self.batch_count)
        opt_field(0, 2, "Seed", self.batch_seed)
        opt_field(0, 4, "Base year", self.batch_base_year)

        # Age min/max moved to Details tab (DOB block)
        opt_field(1, 0, "CA min", self.batch_ca_min)
        opt_field(1, 2, "CA max", self.batch_ca_max)
        opt_field(1, 4, "PA min", self.batch_pa_min)

        opt_field(2, 0, "PA max", self.batch_pa_max)

        btnrow = ttk.Frame(opt)
        btnrow.grid(row=3, column=0, columnspan=6, sticky="w", padx=6, pady=(0, 6))


        # DOB options
        dob = ttk.LabelFrame(frm, text="DOB (Calendar range OR fixed)")
        dob.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        dob.columnconfigure(3, weight=1)

        ttk.Radiobutton(dob, text="Use DOB range", variable=self.batch_dob_mode, value="range").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(dob, text="Use fixed DOB (same for all)", variable=self.batch_dob_mode, value="fixed").grid(row=0, column=1, sticky="w", padx=8, pady=6)

        ttk.Label(dob, text="Fixed DOB").grid(row=1, column=0, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.batch_dob_fixed).grid(row=1, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="Start").grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.batch_dob_start).grid(row=2, column=1, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="End").grid(row=2, column=2, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.batch_dob_end).grid(row=2, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="Age range controls moved to Details tab.", foreground="#444").grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(2, 6))

        ttk.Separator(dob, orient="horizontal").grid(row=4, column=0, columnspan=4, sticky="ew", padx=8, pady=(2, 6))
        ttk.Label(dob, text="XML date overrides (optional)").grid(row=5, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 4))

        ttk.Label(dob, text="Date moved to nation").grid(row=6, column=0, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Use DOB", variable=self.batch_moved_to_nation_mode, value="dob").grid(row=6, column=1, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Fixed date", variable=self.batch_moved_to_nation_mode, value="fixed").grid(row=6, column=2, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.batch_moved_to_nation_date).grid(row=6, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="Date joined club").grid(row=7, column=0, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Auto (1 Jul base year)", variable=self.batch_joined_club_mode, value="auto").grid(row=7, column=1, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Fixed date", variable=self.batch_joined_club_mode, value="fixed").grid(row=7, column=2, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.batch_joined_club_date).grid(row=7, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="Contract expires").grid(row=8, column=0, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Auto (+3 years)", variable=self.batch_contract_expires_mode, value="auto").grid(row=8, column=1, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Fixed date", variable=self.batch_contract_expires_mode, value="fixed").grid(row=8, column=2, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.batch_contract_expires_date).grid(row=8, column=3, sticky="w", padx=8, pady=4)

        # Height + feet (shared builder)
        self._add_height_feet_section(
            frm,
            row=7,
            height_mode_var=self.batch_height_mode,
            height_min_var=self.batch_height_min,
            height_max_var=self.batch_height_max,
            height_fixed_var=self.batch_height_fixed,
            feet_mode_var=self.batch_feet_mode,
            feet_override_var=self.batch_feet_override,
            left_foot_var=self.batch_left_foot,
            right_foot_var=self.batch_right_foot,
            show_height=False,
        )

        # Wage + Reputation + Transfer Value
        money = ttk.LabelFrame(frm, text="Wage + Reputation + Transfer Value")
        money.grid(row=8, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(10):
            money.columnconfigure(c, weight=1)

        # Wage
        ttk.Label(money, text="Wage").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Random range", variable=self.batch_wage_mode, value="range").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Fixed", variable=self.batch_wage_mode, value="fixed").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Min").grid(row=0, column=3, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_wage_min, width=6).grid(row=0, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Max").grid(row=0, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_wage_max, width=6).grid(row=0, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Fixed").grid(row=0, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_wage_fixed, width=8).grid(row=0, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="(min wage 30)", foreground="#444").grid(row=0, column=9, sticky="w", padx=8, pady=6)

        # Reputation
        ttk.Label(money, text="Reputation (0–200)").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Random ordered", variable=self.batch_rep_mode, value="range").grid(row=1, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Fixed", variable=self.batch_rep_mode, value="fixed").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Range").grid(row=1, column=3, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_rep_min, width=6).grid(row=1, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="to").grid(row=1, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_rep_max, width=6).grid(row=1, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Current").grid(row=1, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_rep_current, width=6).grid(row=1, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Home").grid(row=2, column=7, sticky="w", padx=8, pady=4)
        ttk.Entry(money, textvariable=self.batch_rep_home, width=6).grid(row=2, column=8, sticky="w", padx=8, pady=4)
        ttk.Label(money, text="World").grid(row=3, column=7, sticky="w", padx=8, pady=4)
        ttk.Entry(money, textvariable=self.batch_rep_world, width=6).grid(row=3, column=8, sticky="w", padx=8, pady=4)
        ttk.Label(money, text="(enforced: current > home > world)", foreground="#444").grid(row=2, column=0, columnspan=7, sticky="w", padx=8, pady=(0, 6))

        # Transfer value
        ttk.Label(money, text="Transfer value").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Mode").grid(row=4, column=1, sticky="w", padx=8, pady=6)
        ttk.Combobox(money, textvariable=self.batch_tv_mode, values=["auto", "fixed", "range"], state="readonly", width=10).grid(row=4, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Fixed").grid(row=4, column=3, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_tv_fixed, width=12).grid(row=4, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Range").grid(row=4, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_tv_min, width=12).grid(row=4, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="to").grid(row=4, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.batch_tv_max, width=12).grid(row=4, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="(auto uses PA, max 150,000,000)", foreground="#444").grid(row=4, column=9, sticky="w", padx=8, pady=6)

        # Club / City / Nation selection
        sel = ttk.LabelFrame(frm, text="Club / City / Nation")
        sel.grid(row=9, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        sel.columnconfigure(3, weight=1)

        self.batch_club_mode = tk.StringVar(value="random")
        self.batch_city_mode = tk.StringVar(value="random")
        self.batch_nation_mode = tk.StringVar(value="random")

        self.batch_club_sel = tk.StringVar(value="")
        self.batch_city_sel = tk.StringVar(value="")
        self.batch_nation_sel = tk.StringVar(value="")

        ttk.Label(sel, text="Club").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        club_combo = ttk.Combobox(sel, textvariable=self.batch_club_sel, values=[], state="disabled", width=55)
        club_combo.grid(row=0, column=3, sticky="ew", padx=8, pady=6)
        self.batch_club_combo = club_combo
        ttk.Radiobutton(sel, text="Random", variable=self.batch_club_mode, value="random", command=lambda mv=self.batch_club_mode, cb=club_combo: self._combo_state_for_mode(mv, cb)).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(sel, text="Fixed", variable=self.batch_club_mode, value="fixed", command=lambda mv=self.batch_club_mode, cb=club_combo: self._combo_state_for_mode(mv, cb)).grid(row=0, column=2, sticky="w", padx=8, pady=6)

        ttk.Label(sel, text="City of birth").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        city_combo = ttk.Combobox(sel, textvariable=self.batch_city_sel, values=[], state="disabled", width=55)
        city_combo.grid(row=1, column=3, sticky="ew", padx=8, pady=6)
        self.batch_city_combo = city_combo
        ttk.Radiobutton(sel, text="Random", variable=self.batch_city_mode, value="random", command=lambda mv=self.batch_city_mode, cb=city_combo: self._combo_state_for_mode(mv, cb)).grid(row=1, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(sel, text="Fixed", variable=self.batch_city_mode, value="fixed", command=lambda mv=self.batch_city_mode, cb=city_combo: self._combo_state_for_mode(mv, cb)).grid(row=1, column=2, sticky="w", padx=8, pady=6)

        ttk.Label(sel, text="Nation").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        nation_combo = ttk.Combobox(sel, textvariable=self.batch_nation_sel, values=[], state="disabled", width=55)
        nation_combo.grid(row=2, column=3, sticky="ew", padx=8, pady=6)
        self.batch_nation_combo = nation_combo
        ttk.Radiobutton(sel, text="Random", variable=self.batch_nation_mode, value="random", command=lambda mv=self.batch_nation_mode, cb=nation_combo: self._combo_state_for_mode(mv, cb)).grid(row=2, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(sel, text="Fixed", variable=self.batch_nation_mode, value="fixed", command=lambda mv=self.batch_nation_mode, cb=nation_combo: self._combo_state_for_mode(mv, cb)).grid(row=2, column=2, sticky="w", padx=8, pady=6)

        ttk.Button(sel, text="Reload from master_library.csv", command=self._reload_master_library).grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 8))

        # Positions
        pos = ttk.LabelFrame(frm, text="Positions")
        pos.grid(row=10, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        ttk.Checkbutton(pos, text="Random positions (ignore selections)", variable=self.batch_positions_random).grid(row=0, column=0, sticky="w", padx=8, pady=6)

        grid = ttk.Frame(pos)
        grid.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
        cols = 7
        for i, code in enumerate(ALL_POS):
            r = i // cols
            c = i % cols
            ttk.Checkbutton(grid, text=code, variable=self.batch_pos_vars[code]).grid(row=r, column=c, sticky="w", padx=6, pady=2)

        # --- Extra position controls (keeps existing behaviour, just adds options) ---

        def _batch_select_all_outfield():
            for k, v in self.batch_pos_vars.items():
                v.set(k != "GK")

        def _batch_clear_positions():
            for v in self.batch_pos_vars.values():
                v.set(False)

        tools = ttk.Frame(pos)
        tools.grid(row=1, column=2, columnspan=5, sticky="e", padx=8, pady=6)
        ttk.Button(tools, text="Select all outfield", command=_batch_select_all_outfield).pack(side="left", padx=(0, 6))
        ttk.Button(tools, text="Clear", command=_batch_clear_positions).pack(side="left")
        wf = ttk.LabelFrame(frm, text="Random position distribution (editable)")
        wf.grid(row=11, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(10):
            wf.columnconfigure(c, weight=1)

        ttk.Label(
            wf,
            text="Used ONLY when 'Random positions' is ON. Totals must equal 100%.",
            foreground="#444"
        ).grid(row=0, column=0, columnspan=10, sticky="w", padx=8, pady=(6, 2))

        ttk.Label(wf, text="Primary role split (%)").grid(row=1, column=0, columnspan=10, sticky="w", padx=8, pady=(0, 2))

        ttk.Label(wf, text="GK").grid(row=2, column=0, sticky="w", padx=8)
        ttk.Entry(wf, textvariable=self.batch_dist_gk, width=6).grid(row=3, column=0, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(wf, text="DEF").grid(row=2, column=1, sticky="w", padx=8)
        ttk.Entry(wf, textvariable=self.batch_dist_def, width=6).grid(row=3, column=1, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(wf, text="MID").grid(row=2, column=2, sticky="w", padx=8)
        ttk.Entry(wf, textvariable=self.batch_dist_mid, width=6).grid(row=3, column=2, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(wf, text="ST").grid(row=2, column=3, sticky="w", padx=8)
        ttk.Entry(wf, textvariable=self.batch_dist_st, width=6).grid(row=3, column=3, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(wf, text="Outfield positions rated 20: chance (%)").grid(row=4, column=0, columnspan=10, sticky="w", padx=8, pady=(0, 2))

        headers = ["1","2","3","4","5","6","7","8–12","13"]
        vars_ = [
            self.batch_n20_1, self.batch_n20_2, self.batch_n20_3, self.batch_n20_4,
            self.batch_n20_5, self.batch_n20_6, self.batch_n20_7, self.batch_n20_8_12, self.batch_n20_13
        ]

        for i, h in enumerate(headers):
            ttk.Label(wf, text=h).grid(row=5, column=i, sticky="w", padx=8, pady=2)
        for i, v in enumerate(vars_):
            ttk.Entry(wf, textvariable=v, width=6).grid(row=6, column=i, sticky="w", padx=8, pady=(0, 6))

        def _reset_pos_dists():
            self.batch_dist_gk.set("15"); self.batch_dist_def.set("35"); self.batch_dist_mid.set("35"); self.batch_dist_st.set("15")
            self.batch_n20_1.set("39"); self.batch_n20_2.set("18"); self.batch_n20_3.set("13"); self.batch_n20_4.set("11")
            self.batch_n20_5.set("8"); self.batch_n20_6.set("5.5"); self.batch_n20_7.set("3.6"); self.batch_n20_8_12.set("1.4"); self.batch_n20_13.set("0.5")

        ttk.Button(wf, text="Reset defaults", command=_reset_pos_dists).grid(row=7, column=0, sticky="w", padx=8, pady=(0, 6))

# Development positions (2..19) - auto-selected by generator for multi-position profiles
        dev = ttk.LabelFrame(frm, text="Development positions (2–19)")
        dev.grid(row=12, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(8):
            dev.columnconfigure(c, weight=1)

        ttk.Checkbutton(
            dev,
            text="Enable dev positions (auto-picked; applies only to multi-position players)",
            variable=self.batch_dev_enable
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=8, pady=(6, 4))

        ttk.Label(dev, text="Chance (%)").grid(row=0, column=5, sticky="w", padx=8, pady=(6, 4))
        ttk.Entry(dev, textvariable=self.batch_auto_dev_chance, width=5).grid(row=0, column=6, sticky="w", padx=8, pady=(6, 4))

        ttk.Label(dev, text="Mode").grid(row=1, column=0, sticky="w", padx=8, pady=2)
        ttk.Combobox(
            dev, textvariable=self.batch_dev_mode, values=["random", "fixed", "range"], width=8, state="readonly"
        ).grid(row=1, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(dev, text="Fixed").grid(row=1, column=2, sticky="w", padx=8, pady=2)
        ttk.Entry(dev, textvariable=self.batch_dev_fixed, width=5).grid(row=1, column=3, sticky="w", padx=8, pady=2)
        ttk.Label(dev, text="Min").grid(row=1, column=4, sticky="w", padx=8, pady=2)
        ttk.Entry(dev, textvariable=self.batch_dev_min, width=5).grid(row=1, column=5, sticky="w", padx=8, pady=2)
        ttk.Label(dev, text="Max").grid(row=1, column=6, sticky="w", padx=8, pady=2)
        ttk.Entry(dev, textvariable=self.batch_dev_max, width=5).grid(row=1, column=7, sticky="w", padx=8, pady=2)

        ttk.Label(
            dev,
            text="Note: If GK is primary, all other positions are forced to 1 (dev ignored). If outfield: GK stays 1.",
            foreground="#444"
        ).grid(row=2, column=0, columnspan=8, sticky="w", padx=8, pady=(0, 6))



    # ---------------- Players (Single) UI ----------------

    def _build_single_tab(self) -> None:
        frm = self.single_body
        frm.columnconfigure(1, weight=1)

        self.single_clubs = tk.StringVar(value=str(self.fmdata_dir / "master_library.csv"))
        self.single_first = tk.StringVar(value=str(self.fmdata_dir / "scottish_male_first_names_2500.csv"))
        self.single_surn = tk.StringVar(value=str(self.fmdata_dir / "scottish_surnames_2500.csv"))
        self.single_out = tk.StringVar(value=str(self.fmdata_dir / "fm26_single_player.xml"))
        self.single_script = tk.StringVar(value=str(self.fmdata_dir / DEFAULT_GENERATE_SCRIPT))

        self.single_seed = tk.StringVar(value="123")
        self.single_base_year = tk.StringVar(value="2026")

        self.single_dob_mode = tk.StringVar(value="age")  # age|dob
        self.single_age = tk.StringVar(value="14")
        self.single_dob = tk.StringVar(value="2012-07-01")
        self.single_age_preview = tk.StringVar(value="Age (from DOB): 14")

        # XML date overrides (optional)
        self.single_moved_to_nation_mode = tk.StringVar(value="dob")  # dob|fixed
        self.single_moved_to_nation_date = tk.StringVar(value="")
        self.single_joined_club_mode = tk.StringVar(value="auto")  # auto|fixed
        self.single_joined_club_date = tk.StringVar(value="")
        self.single_contract_expires_mode = tk.StringVar(value="auto")  # auto|fixed
        self.single_contract_expires_date = tk.StringVar(value="")

        self.single_ca = tk.StringVar(value="120")
        self.single_pa = tk.StringVar(value="170")
        # Optional single-player CA/PA range overrides (leave blank to use fixed CA/PA above)
        self.single_ca_min = tk.StringVar(value="")
        self.single_ca_max = tk.StringVar(value="")
        self.single_pa_min = tk.StringVar(value="")
        self.single_pa_max = tk.StringVar(value="")

        self.single_height_mode = tk.StringVar(value="range")  # range|fixed
        self.single_height_min = tk.StringVar(value="150")
        self.single_height_max = tk.StringVar(value="210")
        self.single_height_fixed = tk.StringVar(value="")

        self.single_feet_mode = tk.StringVar(value="random")
        self.single_feet_override = tk.BooleanVar(value=False)
        self.single_left_foot = tk.StringVar(value="10")
        self.single_right_foot = tk.StringVar(value="20")

        self.single_wage_mode = tk.StringVar(value="range")
        self.single_wage_min = tk.StringVar(value="30")
        self.single_wage_max = tk.StringVar(value="80")
        self.single_wage_fixed = tk.StringVar(value="")

        self.single_rep_mode = tk.StringVar(value="range")
        self.single_rep_min = tk.StringVar(value="0")
        self.single_rep_max = tk.StringVar(value="200")
        self.single_rep_current = tk.StringVar(value="")
        self.single_rep_home = tk.StringVar(value="")
        self.single_rep_world = tk.StringVar(value="")

        self.single_tv_mode = tk.StringVar(value="auto")
        self.single_tv_fixed = tk.StringVar(value="")
        self.single_tv_min = tk.StringVar(value="")
        self.single_tv_max = tk.StringVar(value="")

        self.single_positions_random = tk.BooleanVar(value=True)
        self.single_pos_vars: dict[str, tk.BooleanVar] = {p: tk.BooleanVar(value=False) for p in ALL_POS}

        # Development positions (extra positions added at 2..19)
        self.single_dev_enable = tk.BooleanVar(value=True)
        self.single_auto_dev_chance = tk.StringVar(value="15")  # percent (0..100)
        self.single_dev_mode = tk.StringVar(value="random")  # random|fixed|range
        self.single_dev_fixed = tk.StringVar(value="10")
        self.single_dev_min = tk.StringVar(value="2")
        self.single_dev_max = tk.StringVar(value="19")

        # File inputs (hidden by default)
        self.single_region_map_csv = tk.StringVar(value="")  # placeholder for future region mapping
        paths = ttk.LabelFrame(frm, text="File inputs")
        paths.grid(row=0, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        paths.columnconfigure(1, weight=1)
        self.single_paths_frame = paths
        paths.grid_remove()

        def row_file(r, label, var, is_save=False):
            ttk.Label(paths, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ttk.Entry(paths, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            if is_save:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_save_xml(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)
            else:
                ttk.Button(paths, text="Browse…", command=lambda: self._pick_open_file(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "master_library.csv:", self.single_clubs, is_save=False)
        row_file(1, "First names CSV:", self.single_first, is_save=False)
        row_file(2, "Surnames CSV:", self.single_surn, is_save=False)
        row_file(3, "Output XML:", self.single_out, is_save=True)
        row_file(4, "Generator script:", self.single_script, is_save=False)
        row_file(5, "Region mapping CSV (placeholder):", self.single_region_map_csv, is_save=False)

        opt = ttk.LabelFrame(frm, text="Single player (fixed values)")
        opt.grid(row=1, column=0, columnspan=3, sticky="ew", padx=8, pady=(10, 8))
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

        ttk.Separator(opt, orient="horizontal").grid(row=1, column=0, columnspan=8, sticky="ew", padx=6, pady=(2, 2))
        ttk.Label(opt, text="Single-player CA/PA range (optional)").grid(row=2, column=0, columnspan=8, sticky="w", padx=6, pady=(2, 0))
        ttk.Label(opt, text="CA min").grid(row=3, column=0, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_ca_min, width=10).grid(row=3, column=1, sticky="w", padx=6, pady=6)
        ttk.Label(opt, text="CA max").grid(row=3, column=2, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_ca_max, width=10).grid(row=3, column=3, sticky="w", padx=6, pady=6)
        ttk.Label(opt, text="PA min").grid(row=3, column=4, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_pa_min, width=10).grid(row=3, column=5, sticky="w", padx=6, pady=6)
        ttk.Label(opt, text="PA max").grid(row=3, column=6, sticky="w", padx=6, pady=6)
        ttk.Entry(opt, textvariable=self.single_pa_max, width=10).grid(row=3, column=7, sticky="w", padx=6, pady=6)

        btnrow = ttk.Frame(opt)
        btnrow.grid(row=4, column=0, columnspan=8, sticky="w", padx=6, pady=(0, 6))


        # Age / DOB
        dob = ttk.LabelFrame(frm, text="Age / DOB")
        dob.grid(row=6, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        dob.columnconfigure(3, weight=1)

        ttk.Radiobutton(dob, text="Use age", variable=self.single_dob_mode, value="age").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(dob, text="Age").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Entry(dob, textvariable=self.single_age, width=6).grid(row=0, column=2, sticky="w", padx=8, pady=6)

        ttk.Radiobutton(dob, text="Use DOB", variable=self.single_dob_mode, value="dob").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(dob, text="DOB").grid(row=1, column=1, sticky="w", padx=8, pady=6)
        self._make_date_input(dob, self.single_dob).grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(dob, textvariable=self.single_age_preview, foreground="#444").grid(row=1, column=3, sticky="w", padx=8, pady=6)

        def _update_age_preview(*_):
            try:
                by = int(self.single_base_year.get().strip() or "2026")
                y = int(self.single_dob.get().strip()[:4])
                a = max(0, by - y)
                self.single_age_preview.set(f"Age (from DOB): {a}")
            except Exception:
                self.single_age_preview.set("Age (from DOB): ?")

        self.single_dob.trace_add("write", _update_age_preview)
        self.single_base_year.trace_add("write", _update_age_preview)
        _update_age_preview()

        ttk.Separator(dob, orient="horizontal").grid(row=2, column=0, columnspan=4, sticky="ew", padx=8, pady=(2, 6))
        ttk.Label(dob, text="XML date overrides (optional)").grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(0, 4))

        ttk.Label(dob, text="Date moved to nation").grid(row=4, column=0, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Use DOB", variable=self.single_moved_to_nation_mode, value="dob").grid(row=4, column=1, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Fixed date", variable=self.single_moved_to_nation_mode, value="fixed").grid(row=4, column=2, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.single_moved_to_nation_date).grid(row=4, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="Date joined club").grid(row=5, column=0, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Auto (1 Jul base year)", variable=self.single_joined_club_mode, value="auto").grid(row=5, column=1, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Fixed date", variable=self.single_joined_club_mode, value="fixed").grid(row=5, column=2, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.single_joined_club_date).grid(row=5, column=3, sticky="w", padx=8, pady=4)

        ttk.Label(dob, text="Contract expires").grid(row=6, column=0, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Auto (+3 years)", variable=self.single_contract_expires_mode, value="auto").grid(row=6, column=1, sticky="w", padx=8, pady=4)
        ttk.Radiobutton(dob, text="Fixed date", variable=self.single_contract_expires_mode, value="fixed").grid(row=6, column=2, sticky="w", padx=8, pady=4)
        self._make_date_input(dob, self.single_contract_expires_date).grid(row=6, column=3, sticky="w", padx=8, pady=4)

        # Height + feet (shared builder)
        self._add_height_feet_section(
            frm,
            row=7,
            height_mode_var=self.single_height_mode,
            height_min_var=self.single_height_min,
            height_max_var=self.single_height_max,
            height_fixed_var=self.single_height_fixed,
            feet_mode_var=self.single_feet_mode,
            feet_override_var=self.single_feet_override,
            left_foot_var=self.single_left_foot,
            right_foot_var=self.single_right_foot,
            show_height=False,
        )

        # Wage + Reputation + Transfer Value
        money = ttk.LabelFrame(frm, text="Wage + Reputation + Transfer Value")
        money.grid(row=8, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(10):
            money.columnconfigure(c, weight=1)

        ttk.Label(money, text="Wage").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Random range", variable=self.single_wage_mode, value="range").grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Fixed", variable=self.single_wage_mode, value="fixed").grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Min").grid(row=0, column=3, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_wage_min, width=6).grid(row=0, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Max").grid(row=0, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_wage_max, width=6).grid(row=0, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Fixed").grid(row=0, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_wage_fixed, width=8).grid(row=0, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="(min wage 30)", foreground="#444").grid(row=0, column=9, sticky="w", padx=8, pady=6)

        ttk.Label(money, text="Reputation (0–200)").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Random ordered", variable=self.single_rep_mode, value="range").grid(row=1, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(money, text="Fixed", variable=self.single_rep_mode, value="fixed").grid(row=1, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Range").grid(row=1, column=3, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_rep_min, width=6).grid(row=1, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="to").grid(row=1, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_rep_max, width=6).grid(row=1, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Current").grid(row=1, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_rep_current, width=6).grid(row=1, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Home").grid(row=2, column=7, sticky="w", padx=8, pady=4)
        ttk.Entry(money, textvariable=self.single_rep_home, width=6).grid(row=2, column=8, sticky="w", padx=8, pady=4)
        ttk.Label(money, text="World").grid(row=3, column=7, sticky="w", padx=8, pady=4)
        ttk.Entry(money, textvariable=self.single_rep_world, width=6).grid(row=3, column=8, sticky="w", padx=8, pady=4)
        ttk.Label(money, text="(enforced: current > home > world)", foreground="#444").grid(row=2, column=0, columnspan=7, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(money, text="Transfer value").grid(row=4, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Mode").grid(row=4, column=1, sticky="w", padx=8, pady=6)
        ttk.Combobox(money, textvariable=self.single_tv_mode, values=["auto", "fixed", "range"], state="readonly", width=10).grid(row=4, column=2, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Fixed").grid(row=4, column=3, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_tv_fixed, width=12).grid(row=4, column=4, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="Range").grid(row=4, column=5, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_tv_min, width=12).grid(row=4, column=6, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="to").grid(row=4, column=7, sticky="w", padx=8, pady=6)
        ttk.Entry(money, textvariable=self.single_tv_max, width=12).grid(row=4, column=8, sticky="w", padx=8, pady=6)
        ttk.Label(money, text="(auto uses PA, max 150,000,000)", foreground="#444").grid(row=4, column=9, sticky="w", padx=8, pady=6)

        # Club / City / Nation selection
        sel = ttk.LabelFrame(frm, text="Club / City / Nation")
        sel.grid(row=9, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        sel.columnconfigure(3, weight=1)

        self.single_club_mode = tk.StringVar(value="random")
        self.single_city_mode = tk.StringVar(value="random")
        self.single_nation_mode = tk.StringVar(value="random")

        self.single_club_sel = tk.StringVar(value="")
        self.single_city_sel = tk.StringVar(value="")
        self.single_nation_sel = tk.StringVar(value="")

        ttk.Label(sel, text="Club").grid(row=0, column=0, sticky="w", padx=8, pady=6)
        club_combo = ttk.Combobox(sel, textvariable=self.single_club_sel, values=[], state="disabled", width=55)
        club_combo.grid(row=0, column=3, sticky="ew", padx=8, pady=6)
        self.single_club_combo = club_combo
        ttk.Radiobutton(sel, text="Random", variable=self.single_club_mode, value="random", command=lambda mv=self.single_club_mode, cb=club_combo: self._combo_state_for_mode(mv, cb)).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(sel, text="Fixed", variable=self.single_club_mode, value="fixed", command=lambda mv=self.single_club_mode, cb=club_combo: self._combo_state_for_mode(mv, cb)).grid(row=0, column=2, sticky="w", padx=8, pady=6)

        ttk.Label(sel, text="City of birth").grid(row=1, column=0, sticky="w", padx=8, pady=6)
        city_combo = ttk.Combobox(sel, textvariable=self.single_city_sel, values=[], state="disabled", width=55)
        city_combo.grid(row=1, column=3, sticky="ew", padx=8, pady=6)
        self.single_city_combo = city_combo
        ttk.Radiobutton(sel, text="Random", variable=self.single_city_mode, value="random", command=lambda mv=self.single_city_mode, cb=city_combo: self._combo_state_for_mode(mv, cb)).grid(row=1, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(sel, text="Fixed", variable=self.single_city_mode, value="fixed", command=lambda mv=self.single_city_mode, cb=city_combo: self._combo_state_for_mode(mv, cb)).grid(row=1, column=2, sticky="w", padx=8, pady=6)

        ttk.Label(sel, text="Nation").grid(row=2, column=0, sticky="w", padx=8, pady=6)
        nation_combo = ttk.Combobox(sel, textvariable=self.single_nation_sel, values=[], state="disabled", width=55)
        nation_combo.grid(row=2, column=3, sticky="ew", padx=8, pady=6)
        self.single_nation_combo = nation_combo
        ttk.Radiobutton(sel, text="Random", variable=self.single_nation_mode, value="random", command=lambda mv=self.single_nation_mode, cb=nation_combo: self._combo_state_for_mode(mv, cb)).grid(row=2, column=1, sticky="w", padx=8, pady=6)
        ttk.Radiobutton(sel, text="Fixed", variable=self.single_nation_mode, value="fixed", command=lambda mv=self.single_nation_mode, cb=nation_combo: self._combo_state_for_mode(mv, cb)).grid(row=2, column=2, sticky="w", padx=8, pady=6)

        ttk.Button(sel, text="Reload from master_library.csv", command=self._reload_master_library).grid(row=3, column=0, columnspan=4, sticky="w", padx=8, pady=(4, 8))

        # Positions
        pos = ttk.LabelFrame(frm, text="Positions")
        pos.grid(row=10, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        ttk.Checkbutton(pos, text="Random positions (ignore selections)", variable=self.single_positions_random).grid(row=0, column=0, sticky="w", padx=8, pady=6)

        grid = ttk.Frame(pos)
        grid.grid(row=1, column=0, sticky="w", padx=8, pady=(0, 8))
        cols = 7
        for i, code in enumerate(ALL_POS):
            r = i // cols
            c = i % cols
            ttk.Checkbutton(grid, text=code, variable=self.single_pos_vars[code]).grid(row=r, column=c, sticky="w", padx=6, pady=2)

        # --- Extra position controls (keeps existing behaviour, just adds options) ---

        def _single_select_all_outfield():
            for k, v in self.single_pos_vars.items():
                v.set(k != "GK")

        def _single_clear_positions():
            for v in self.single_pos_vars.values():
                v.set(False)

        pos.columnconfigure(0, weight=1)

        tools = ttk.Frame(pos)
        tools.grid(row=2, column=0, sticky="e", padx=8, pady=(0, 6))
        ttk.Button(tools, text="Select all outfield", command=_single_select_all_outfield).pack(side="left", padx=(0, 6))
        ttk.Button(tools, text="Clear", command=_single_clear_positions).pack(side="left")
        wf = ttk.LabelFrame(frm, text="Random position distribution (fixed)")
        wf.grid(row=11, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(10):
            wf.columnconfigure(c, weight=1)

        ttk.Label(
            wf,
            text="Primary role split (%): GK 15 | DEF 35 | MID 35 | ST 15",
            foreground="#444"
        ).grid(row=0, column=0, columnspan=10, sticky="w", padx=8, pady=(6, 2))

        ttk.Label(wf, text="Outfield positions rated 20: chance (%)").grid(row=1, column=0, columnspan=10, sticky="w", padx=8, pady=(0, 4))

        headers = ["1","2","3","4","5","6","7","8–12","13"]
        values  = ["39","18","13","11","8","5.5","3.6","1.4","0.5"]

        for i, h in enumerate(headers):
            ttk.Label(wf, text=h).grid(row=2, column=i, sticky="w", padx=8, pady=2)
        for i, v in enumerate(values):
            ttk.Label(wf, text=v).grid(row=3, column=i, sticky="w", padx=8, pady=(0, 6))

        ttk.Label(
            wf,
            text="Note: Distribution is built into fm26_bulk_youth_generator4.py (not editable here).",
            foreground="#444"
        ).grid(row=4, column=0, columnspan=10, sticky="w", padx=8, pady=(0, 6))
        # Development positions (2..19) - auto-selected by generator for multi-position profiles
        dev = ttk.LabelFrame(frm, text="Development positions (2–19)")
        dev.grid(row=12, column=0, columnspan=3, sticky="ew", padx=8, pady=(0, 8))
        for c in range(8):
            dev.columnconfigure(c, weight=1)

        ttk.Checkbutton(
            dev,
            text="Enable dev positions (auto-picked; applies only to multi-position players)",
            variable=self.single_dev_enable
        ).grid(row=0, column=0, columnspan=5, sticky="w", padx=8, pady=(6, 4))

        ttk.Label(dev, text="Chance (%)").grid(row=0, column=5, sticky="w", padx=8, pady=(6, 4))
        ttk.Entry(dev, textvariable=self.single_auto_dev_chance, width=5).grid(row=0, column=6, sticky="w", padx=8, pady=(6, 4))

        ttk.Label(dev, text="Mode").grid(row=1, column=0, sticky="w", padx=8, pady=2)
        ttk.Combobox(
            dev, textvariable=self.single_dev_mode, values=["random", "fixed", "range"], width=8, state="readonly"
        ).grid(row=1, column=1, sticky="w", padx=8, pady=2)

        ttk.Label(dev, text="Fixed").grid(row=1, column=2, sticky="w", padx=8, pady=2)
        ttk.Entry(dev, textvariable=self.single_dev_fixed, width=5).grid(row=1, column=3, sticky="w", padx=8, pady=2)
        ttk.Label(dev, text="Min").grid(row=1, column=4, sticky="w", padx=8, pady=2)
        ttk.Entry(dev, textvariable=self.single_dev_min, width=5).grid(row=1, column=5, sticky="w", padx=8, pady=2)
        ttk.Label(dev, text="Max").grid(row=1, column=6, sticky="w", padx=8, pady=2)
        ttk.Entry(dev, textvariable=self.single_dev_max, width=5).grid(row=1, column=7, sticky="w", padx=8, pady=2)

        ttk.Label(
            dev,
            text="Note: If GK is primary, all other positions are forced to 1 (dev ignored). If outfield: GK stays 1.",
            foreground="#444"
        ).grid(row=2, column=0, columnspan=8, sticky="w", padx=8, pady=(0, 6))




    def _resolve_fmdata_path(self, name: str) -> str:
        try:
            d = getattr(self, "fmdata_dir", self.base_dir / "fmdata")
            d.mkdir(parents=True, exist_ok=True)
            return str(d / name)
        except Exception:
            return str((getattr(self, "base_dir", Path.cwd())) / name)

    # ---------------- File pickers ----------------

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

    def _run_batch_generator_safe(self) -> None:
        try:
            self._run_batch_generator()
        except Exception as e:
            try:
                self._ensure_output_visible()
                self._log(f"[ERROR] Run Batch Generator callback crashed: {e}")
            except Exception:
                pass
            try:
                messagebox.showerror("Run Batch Generator error", str(e))
            except Exception:
                pass

    def _run_single_generator_safe(self) -> None:
        try:
            self._run_single_generator()
        except Exception as e:
            try:
                self._ensure_output_visible()
                self._log(f"[ERROR] Generate 1 Player callback crashed: {e}")
            except Exception:
                pass
            try:
                messagebox.showerror("Generate 1 Player error", str(e))
            except Exception:
                pass

    def _run_batch_generator(self) -> None:
        extra: list[str] = []
        # Player tab: force person type = 2 (player) in generator builds that support it
        extra.extend(["--person_type_value", "2"])

        # DOB (supports legacy batch modes + Details-tab shared mode values)
        mode = (self.batch_dob_mode.get() or "age").strip()
        if mode == "fixed":
            d = self.batch_dob_fixed.get().strip()
            if not d:
                messagebox.showerror("Fixed DOB missing", "Fixed DOB is selected, but the date is blank.")
                return
            extra.extend(["--dob", d])
        elif mode in ("range", "dob"):  # "dob" kept for compatibility with earlier shared Details patch
            ds = self.batch_dob_start.get().strip()
            de = self.batch_dob_end.get().strip()
            if not ds or not de:
                messagebox.showerror("DOB range missing", "Please set both DOB Start and DOB End (YYYY-MM-DD).")
                return
            extra.extend(["--dob_start", ds, "--dob_end", de])

        # XML date overrides (optional)
        if self.batch_moved_to_nation_mode.get() == "fixed":
            d = self.batch_moved_to_nation_date.get().strip()
            if not d:
                messagebox.showerror("Date moved to nation missing", "Fixed Date moved to nation is selected, but the date is blank.")
                return
            extra.extend(["--moved_to_nation_date", d])

        if self.batch_joined_club_mode.get() == "fixed":
            d = self.batch_joined_club_date.get().strip()
            if not d:
                messagebox.showerror("Date joined club missing", "Fixed Date joined club is selected, but the date is blank.")
                return
            extra.extend(["--joined_club_date", d])

        if self.batch_contract_expires_mode.get() == "fixed":
            d = self.batch_contract_expires_date.get().strip()
            if not d:
                messagebox.showerror("Contract expires missing", "Fixed Contract expires is selected, but the date is blank.")
                return
            extra.extend(["--contract_expires_date", d])

        # Height
        if self.batch_height_mode.get() == "fixed":
            h = self.batch_height_fixed.get().strip()
            if not h:
                messagebox.showerror("Height missing", "Fixed height selected, but Height is blank.")
                return
            extra.extend(["--height", h])
        else:
            extra.extend(["--height_min", self.batch_height_min.get().strip(), "--height_max", self.batch_height_max.get().strip()])

        # Feet
        extra.extend(["--feet", (self.batch_feet_mode.get().strip() or "random")])
        if self.batch_feet_override.get():
            lf = self.batch_left_foot.get().strip()
            rf = self.batch_right_foot.get().strip()
            if not lf or not rf:
                messagebox.showerror("Feet missing", "Override feet is ticked, but Left/Right values are blank.")
                return
            extra.extend(["--left_foot", lf, "--right_foot", rf])

        # Club/City/Nation fixed selections
        if self.batch_club_mode.get() == "fixed":
            sel = self.batch_club_sel.get().strip()
            ids = self._get_fixed_ids("club", sel)
            if not ids:
                messagebox.showerror("Club missing", "Fixed Club is selected, but no club is chosen.")
                return
            extra.extend(["--club_dbid", ids[0], "--club_large", ids[1]])

        if self.batch_city_mode.get() == "fixed":
            sel = self.batch_city_sel.get().strip()
            ids = self._get_fixed_ids("city", sel)
            if not ids:
                messagebox.showerror("City missing", "Fixed City is selected, but no city is chosen.")
                return
            extra.extend(["--city_dbid", ids[0], "--city_large", ids[1]])

        if self.batch_nation_mode.get() == "fixed":
            sel = self.batch_nation_sel.get().strip()
            ids = self._get_fixed_ids("nation", sel)
            if not ids:
                messagebox.showerror("Nation missing", "Fixed Nation is selected, but no nation is chosen.")
                return
            extra.extend(["--nation_dbid", ids[0], "--nation_large", ids[1]])

        # Positions
        if self.batch_positions_random.get():
            # RANDOM positions: validate + pass editable distributions
            def _f(name: str, s: str) -> float:
                try:
                    return float(s)
                except Exception:
                    raise ValueError(f"{name} must be a number")

            try:
                gk = _f("GK %", self.batch_dist_gk.get().strip())
                de = _f("DEF %", self.batch_dist_def.get().strip())
                mi = _f("MID %", self.batch_dist_mid.get().strip())
                st = _f("ST %", self.batch_dist_st.get().strip())
                total = gk + de + mi + st
                if abs(total - 100.0) > 0.001:
                    diff = 100.0 - total
                    messagebox.showerror(
                        "Primary role split must total 100%",
                        f"Your GK/DEF/MID/ST totals {total:.3f}%. Difference: {diff:+.3f}%."
                    )
                    return

                n20_vals = [
                    _f("N20(1)", self.batch_n20_1.get().strip()),
                    _f("N20(2)", self.batch_n20_2.get().strip()),
                    _f("N20(3)", self.batch_n20_3.get().strip()),
                    _f("N20(4)", self.batch_n20_4.get().strip()),
                    _f("N20(5)", self.batch_n20_5.get().strip()),
                    _f("N20(6)", self.batch_n20_6.get().strip()),
                    _f("N20(7)", self.batch_n20_7.get().strip()),
                    _f("N20(8–12)", self.batch_n20_8_12.get().strip()),
                    _f("N20(13)", self.batch_n20_13.get().strip()),
                ]
                total2 = sum(n20_vals)
                if abs(total2 - 100.0) > 0.001:
                    diff2 = 100.0 - total2
                    messagebox.showerror(
                        "N20 distribution must total 100%",
                        f"Your 1..7, 8–12, 13 totals {total2:.3f}%. Difference: {diff2:+.3f}%."
                    )
                    return
            except ValueError as e:
                messagebox.showerror("Invalid distribution value", str(e))
                return

            extra.extend(["--positions", "RANDOM"])
            extra.extend(["--pos_primary_dist", f"{gk},{de},{mi},{st}"])
            extra.extend(["--pos_n20_dist", ",".join([str(x) for x in n20_vals])])

            # Dev positions chance (auto-picked by generator)
            if self.batch_dev_enable.get():
                extra.extend(["--auto_dev_chance", (self.batch_auto_dev_chance.get().strip() or "0")])
            else:
                extra.extend(["--auto_dev_chance", "0"])
        else:
            sel = [code for code, v in self.batch_pos_vars.items() if v.get()]
            if not sel:
                messagebox.showerror("Positions missing", "Please select at least one position, or tick Random positions.")
                return
            if "GK" in sel and len(sel) > 1:
                messagebox.showerror("Invalid selection", "GK cannot be combined with outfield positions.")
                return

            primary = sel[0]
            extras = sel[1:]
            extra.extend(["--pos_primary", primary])
            if extras:
                extra.extend(["--pos_20", ",".join(extras)])

            # Manual profiles currently do not use auto dev chance; keep at 0
            extra.extend(["--auto_dev_chance", "0"])
        # Development positions (auto-picked by generator v4)
        mode = (self.batch_dev_mode.get() or "random").strip().lower()
        if mode not in ("random", "fixed", "range"):
            mode = "random"
        extra.extend(["--pos_dev_mode", mode])

        if mode == "fixed":
            try:
                v = int((self.batch_dev_fixed.get() or "10").strip())
            except Exception:
                messagebox.showerror("Dev value", "Dev fixed value must be an integer (2..19).")
                return
            extra.extend(["--pos_dev_value", str(v)])
        elif mode == "range":
            try:
                mn = int((self.batch_dev_min.get() or "2").strip())
                mx = int((self.batch_dev_max.get() or "19").strip())
            except Exception:
                messagebox.showerror("Dev range", "Dev min/max must be integers (2..19).")
                return
            extra.extend(["--pos_dev_min", str(mn), "--pos_dev_max", str(mx)])

        # Wage
        if self.batch_wage_mode.get() == "fixed":
            w = self.batch_wage_fixed.get().strip()
            if not w:
                messagebox.showerror("Wage missing", "Fixed wage selected, but Wage is blank.")
                return
            extra.extend(["--wage", w])
        else:
            extra.extend(["--wage_min", self.batch_wage_min.get().strip(), "--wage_max", self.batch_wage_max.get().strip()])

        # Reputation
        if self.batch_rep_mode.get() == "fixed":
            rc = self.batch_rep_current.get().strip()
            rh = self.batch_rep_home.get().strip()
            rw = self.batch_rep_world.get().strip()
            if not rc or not rh or not rw:
                messagebox.showerror("Reputation missing", "Fixed reputation selected, but Current/Home/World are not all set.")
                return
            extra.extend(["--rep_current", rc, "--rep_home", rh, "--rep_world", rw])
        else:
            extra.extend(["--rep_min", self.batch_rep_min.get().strip(), "--rep_max", self.batch_rep_max.get().strip()])

        # Transfer value
        tv_mode = self.batch_tv_mode.get().strip() or "auto"
        extra.extend(["--transfer_mode", tv_mode])
        if tv_mode == "fixed":
            tv = self.batch_tv_fixed.get().strip()
            if not tv:
                messagebox.showerror("Transfer value missing", "Transfer mode is Fixed, but value is blank.")
                return
            extra.extend(["--transfer_value", tv])
        elif tv_mode == "range":
            tmin = self.batch_tv_min.get().strip()
            tmax = self.batch_tv_max.get().strip()
            if not tmin or not tmax:
                messagebox.showerror("Transfer value missing", "Transfer mode is Range, but min/max are blank.")
                return
            extra.extend(["--transfer_min", tmin, "--transfer_max", tmax])

        # Details section (supported exports + UI-ready placeholders)
        try:
            if self.batch_details_first_name_mode.get() == "custom" and self.batch_details_first_name_value.get().strip():
                extra.extend(["--first_name_text", self.batch_details_first_name_value.get().strip()])
            if self.batch_details_second_name_mode.get() == "custom" and self.batch_details_second_name_value.get().strip():
                extra.extend(["--second_name_text", self.batch_details_second_name_value.get().strip()])
            if self.batch_details_common_name_mode.get() == "custom" and self.batch_details_common_name_value.get().strip():
                extra.extend(["--common_name_text", self.batch_details_common_name_value.get().strip()])
            if self.batch_details_full_name_mode.get() == "custom" and self.batch_details_full_name_value.get().strip():
                extra.extend(["--full_name_text", self.batch_details_full_name_value.get().strip()])

            if self.batch_details_gender_mode.get() == "custom":
                gval = self.batch_details_gender_value.get().strip()
                if gval:
                    try:
                        gv = _details_gender_to_int(gval)
                    except Exception as e:
                        messagebox.showerror("Gender", str(e))
                        return
                    if gv is not None:
                        extra.extend(["--gender_value", str(gv)])

            if self.batch_details_ethnicity_mode.get() == "custom":
                eval_ = self.batch_details_ethnicity_value.get().strip()
                if eval_:
                    try:
                        ev = _details_ethnicity_to_int(eval_)
                    except Exception as e:
                        messagebox.showerror("Ethnicity", str(e))
                        return
                    if ev is not None:
                        extra.extend(["--ethnicity_value", str(ev)])

            # Primary nationality info (Details tab)
            _nat_info_added = False
            try:
                if self.batch_details_nationality_info_mode.get() == "custom":
                    ni_label = self.batch_details_nationality_info_value.get().strip()
                    if ni_label:
                        extra.extend(["--nationality_info", ni_label])
                        _nat_info_added = True
            except Exception:
                pass

            # Second Nations metadata export (editor values first, then first row as fallback)
            # NOTE: do NOT override the primary Details Nationality Info unless it is blank.
            try:
                _sn_editor_ni = (getattr(self, "batch_second_nations_nationality_info").get() or "").strip() if hasattr(self, "batch_second_nations_nationality_info") else ""
                _sn_editor_int_ret = bool(getattr(self, "batch_second_nations_international_retirement").get()) if hasattr(self, "batch_second_nations_international_retirement") else False
                _sn_editor_date = (getattr(self, "batch_second_nations_international_retirement_date").get() or "").strip() if hasattr(self, "batch_second_nations_international_retirement_date") else ""
                _sn_editor_retire_spell = bool(getattr(self, "batch_second_nations_retiring_after_spell_current_club").get()) if hasattr(self, "batch_second_nations_retiring_after_spell_current_club") else False

                _sn_items = list(getattr(self, "batch_second_nations_items", []) or [])
                _sn0 = dict(_sn_items[0] or {}) if _sn_items else {}

                # Export repeatable second nation list entries (nation + optional per-entry nationality info)
                for _sn in _sn_items:
                    try:
                        _sn_nation = (dict(_sn or {}).get("nation") or "").strip()
                        if not _sn_nation:
                            continue
                        _sn_ni_item = (dict(_sn or {}).get("nationality_info") or "").strip()
                        _sn_spec = _sn_nation
                        if _sn_ni_item:
                            # Pass label through; generator resolves labels/numbers to FM ntin values
                            _sn_spec = f"{_sn_spec}|{_sn_ni_item}"
                        extra.extend(["--second_nation", _sn_spec])
                    except Exception:
                        pass


                _sn_ni = _sn_editor_ni or (_sn0.get("nationality_info") or "").strip()
                if _sn_ni and not _nat_info_added and _sn_ni.lower() != "no info":
                    extra.extend(["--nationality_info", _sn_ni])

                if _sn_editor_int_ret or bool(_sn0.get("international_retirement", False)):
                    extra.append("--international_retirement")

                _sn_date = _sn_editor_date or (_sn0.get("international_retirement_date") or "").strip()
                if _sn_date:
                    extra.extend(["--international_retirement_date", _sn_date])

                if _sn_editor_retire_spell or bool(_sn0.get("retiring_after_spell_current_club", False)):
                    extra.append("--retiring_after_spell_current_club")
                try:
                    _dy_mode = (getattr(self, "batch_details_declared_for_youth_nation_mode").get() or "random").strip().lower() if hasattr(self, "batch_details_declared_for_youth_nation_mode") else "random"
                    _dy_sel = (getattr(self, "batch_details_declared_for_youth_nation_value").get() or "").strip() if hasattr(self, "batch_details_declared_for_youth_nation_value") else ""
                    if _dy_mode == "custom" and _dy_sel:
                        extra.extend(["--declared_for_youth_nation", _dy_sel])
                except Exception:
                    pass
            except Exception:
                pass

            if self.batch_details_date_of_birth_mode.get() == "custom":
                d = self.batch_details_date_of_birth_value.get().strip()
                if d:
                    extra.extend(["--dob", d])

            # Prefer new Details > Height block (range/fixed), fallback to legacy custom single-value height field
            details_height_handled = False
            try:
                h_mode2 = (self.batch_details_height_mode2.get() if hasattr(self, "batch_details_height_mode2") else "").strip()
                if h_mode2 == "fixed":
                    h = self.batch_details_height_fixed.get().strip()
                    if h:
                        extra.extend(["--height", h])
                        details_height_handled = True
                elif h_mode2 == "range":
                    hmin = self.batch_details_height_min.get().strip()
                    hmax = self.batch_details_height_max.get().strip()
                    if hmin and hmax:
                        extra.extend(["--height_min", hmin, "--height_max", hmax])
                        details_height_handled = True
            except Exception:
                pass

            if (not details_height_handled) and self.batch_details_height_mode.get() == "custom":
                h = self.batch_details_height_value.get().strip()
                if h:
                    extra.extend(["--height", h])

            if self.batch_details_city_of_birth_mode.get() == "custom":
                sel = self.batch_details_city_of_birth_value.get().strip()
                if sel:
                    ids = self._get_fixed_ids("city", sel)
                    if ids:
                        extra.extend(["--city_dbid", ids[0], "--city_large", ids[1]])
                    else:
                        messagebox.showerror("City Of Birth", "Custom City Of Birth must be selected from the master_library city list.")
                        return

            if self.batch_details_region_of_birth_mode.get() == "custom":
                sel = self.batch_details_region_of_birth_value.get().strip()
                if sel:
                    ids = self._get_fixed_ids("nation", sel)
                    if ids:
                        extra.extend(["--nation_dbid", ids[0], "--nation_large", ids[1]])
                    else:
                        messagebox.showerror("Region Of Birth", "Custom Region Of Birth currently maps to Nation and must be selected from the master_library nation list.")
                        return
        except Exception:
            pass

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

    # ---------------- Run: Single ----------------

    def _run_single_generator(self) -> None:
        ca = self.single_ca.get().strip()
        pa = self.single_pa.get().strip()
        # Optional single-player range override (leave blank to use fixed CA/PA as min=max)
        ca_min = self.single_ca_min.get().strip()
        ca_max = self.single_ca_max.get().strip()
        pa_min = self.single_pa_min.get().strip()
        pa_max = self.single_pa_max.get().strip()
        if any([ca_min, ca_max, pa_min, pa_max]):
            if not all([ca_min, ca_max, pa_min, pa_max]):
                messagebox.showerror("CA/PA range missing", "If using Single-player CA/PA range, fill CA min/max and PA min/max (or leave all four blank).")
                return
        else:
            ca_min = ca_max = ca
            pa_min = pa_max = pa

        base_year = self.single_base_year.get().strip()

        extra: list[str] = []
        # Player tab: force person type = 2 (player) in generator builds that support it
        extra.extend(["--person_type_value", "2"])

        # Age / DOB (supports legacy Single tab + shared Details DOB block)
        age = self.single_age.get().strip()
        age_min = (getattr(self, "single_age_min", tk.StringVar(value=age or "14")).get() or "").strip()
        age_max = (getattr(self, "single_age_max", tk.StringVar(value=age or "14")).get() or "").strip()
        if not age_min:
            age_min = age or "14"
        if not age_max:
            age_max = age or age_min or "14"

        s_dob_mode = (self.single_dob_mode.get() or "age").strip()

        # Legacy single uses mode "dob" for fixed DOB.
        # Shared Details block now uses "range" for DOB range, but we also accept "fixed" for compatibility.
        if s_dob_mode in ("dob", "fixed"):
            dob = (getattr(self, "single_dob_fixed", self.single_dob).get() if hasattr(self, "single_dob_fixed") else self.single_dob.get()).strip()
            if not dob:
                messagebox.showerror("DOB missing", "Use DOB / Fixed DOB is selected, but DOB is blank.")
                return
            extra.extend(["--dob", dob])
            try:
                by = int(base_year or "2026")
                a = max(0, by - int(dob[:4]))
                age = str(a)
                age_min = age_max = age
            except Exception:
                pass
        elif s_dob_mode == "range":
            ds = getattr(self, "single_dob_start", tk.StringVar(value="")).get().strip()
            de = getattr(self, "single_dob_end", tk.StringVar(value="")).get().strip()
            if not ds or not de:
                messagebox.showerror("DOB range missing", "Please set both DOB Start and DOB End (YYYY-MM-DD).")
                return
            extra.extend(["--dob_start", ds, "--dob_end", de])

        # XML date overrides (optional)
        if self.single_moved_to_nation_mode.get() == "fixed":
            d = self.single_moved_to_nation_date.get().strip()
            if not d:
                messagebox.showerror("Date moved to nation missing", "Fixed Date moved to nation is selected, but the date is blank.")
                return
            extra.extend(["--moved_to_nation_date", d])

        if self.single_joined_club_mode.get() == "fixed":
            d = self.single_joined_club_date.get().strip()
            if not d:
                messagebox.showerror("Date joined club missing", "Fixed Date joined club is selected, but the date is blank.")
                return
            extra.extend(["--joined_club_date", d])

        if self.single_contract_expires_mode.get() == "fixed":
            d = self.single_contract_expires_date.get().strip()
            if not d:
                messagebox.showerror("Contract expires missing", "Fixed Contract expires is selected, but the date is blank.")
                return
            extra.extend(["--contract_expires_date", d])

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
        extra.extend(["--feet", (self.single_feet_mode.get().strip() or "random")])
        if self.single_feet_override.get():
            lf = self.single_left_foot.get().strip()
            rf = self.single_right_foot.get().strip()
            if not lf or not rf:
                messagebox.showerror("Feet missing", "Override feet is ticked, but Left/Right values are blank.")
                return
            extra.extend(["--left_foot", lf, "--right_foot", rf])

        # Club/City/Nation fixed selections
        if self.single_club_mode.get() == "fixed":
            sel = self.single_club_sel.get().strip()
            ids = self._get_fixed_ids("club", sel)
            if not ids:
                messagebox.showerror("Club missing", "Fixed Club is selected, but no club is chosen.")
                return
            extra.extend(["--club_dbid", ids[0], "--club_large", ids[1]])

        if self.single_city_mode.get() == "fixed":
            sel = self.single_city_sel.get().strip()
            ids = self._get_fixed_ids("city", sel)
            if not ids:
                messagebox.showerror("City missing", "Fixed City is selected, but no city is chosen.")
                return
            extra.extend(["--city_dbid", ids[0], "--city_large", ids[1]])

        if self.single_nation_mode.get() == "fixed":
            sel = self.single_nation_sel.get().strip()
            ids = self._get_fixed_ids("nation", sel)
            if not ids:
                messagebox.showerror("Nation missing", "Fixed Nation is selected, but no nation is chosen.")
                return
            extra.extend(["--nation_dbid", ids[0], "--nation_large", ids[1]])

        # Positions
        if self.single_positions_random.get():
            extra.extend(["--positions", "RANDOM"])
            if self.single_dev_enable.get():
                extra.extend(["--auto_dev_chance", (self.single_auto_dev_chance.get().strip() or "0")])
            else:
                extra.extend(["--auto_dev_chance", "0"])
        else:
            sel = [code for code, v in self.single_pos_vars.items() if v.get()]
            if not sel:
                messagebox.showerror("Positions missing", "Please select at least one position, or tick Random positions.")
                return
            if "GK" in sel and len(sel) > 1:
                messagebox.showerror("Invalid selection", "GK cannot be combined with outfield positions.")
                return

            primary = sel[0]
            extras = sel[1:]
            extra.extend(["--pos_primary", primary])
            if extras:
                extra.extend(["--pos_20", ",".join(extras)])
            extra.extend(["--auto_dev_chance", "0"])
        # Development positions (auto-picked by generator v4)
        mode = (self.single_dev_mode.get() or "random").strip().lower()
        if mode not in ("random", "fixed", "range"):
            mode = "random"
        extra.extend(["--pos_dev_mode", mode])

        if mode == "fixed":
            try:
                v = int((self.single_dev_fixed.get() or "10").strip())
            except Exception:
                messagebox.showerror("Dev value", "Dev fixed value must be an integer (2..19).")
                return
            extra.extend(["--pos_dev_value", str(v)])
        elif mode == "range":
            try:
                mn = int((self.single_dev_min.get() or "2").strip())
                mx = int((self.single_dev_max.get() or "19").strip())
            except Exception:
                messagebox.showerror("Dev range", "Dev min/max must be integers (2..19).")
                return
            extra.extend(["--pos_dev_min", str(mn), "--pos_dev_max", str(mx)])

        # Wage
        if self.single_wage_mode.get() == "fixed":
            w = self.single_wage_fixed.get().strip()
            if not w:
                messagebox.showerror("Wage missing", "Fixed wage selected, but Wage is blank.")
                return
            extra.extend(["--wage", w])
        else:
            extra.extend(["--wage_min", self.single_wage_min.get().strip(), "--wage_max", self.single_wage_max.get().strip()])

        # Reputation
        if self.single_rep_mode.get() == "fixed":
            rc = self.single_rep_current.get().strip()
            rh = self.single_rep_home.get().strip()
            rw = self.single_rep_world.get().strip()
            if not rc or not rh or not rw:
                messagebox.showerror("Reputation missing", "Fixed reputation selected, but Current/Home/World are not all set.")
                return
            extra.extend(["--rep_current", rc, "--rep_home", rh, "--rep_world", rw])
        else:
            extra.extend(["--rep_min", self.single_rep_min.get().strip(), "--rep_max", self.single_rep_max.get().strip()])

        # Transfer value
        tv_mode = self.single_tv_mode.get().strip() or "auto"
        extra.extend(["--transfer_mode", tv_mode])
        if tv_mode == "fixed":
            tv = self.single_tv_fixed.get().strip()
            if not tv:
                messagebox.showerror("Transfer value missing", "Transfer mode is Fixed, but value is blank.")
                return
            extra.extend(["--transfer_value", tv])
        elif tv_mode == "range":
            tmin = self.single_tv_min.get().strip()
            tmax = self.single_tv_max.get().strip()
            if not tmin or not tmax:
                messagebox.showerror("Transfer value missing", "Transfer mode is Range, but min/max are blank.")
                return
            extra.extend(["--transfer_min", tmin, "--transfer_max", tmax])

        # Details section (supported exports + UI-ready placeholders)
        try:
            if self.single_details_first_name_mode.get() == "custom" and self.single_details_first_name_value.get().strip():
                extra.extend(["--first_name_text", self.single_details_first_name_value.get().strip()])
            if self.single_details_second_name_mode.get() == "custom" and self.single_details_second_name_value.get().strip():
                extra.extend(["--second_name_text", self.single_details_second_name_value.get().strip()])
            if self.single_details_common_name_mode.get() == "custom" and self.single_details_common_name_value.get().strip():
                extra.extend(["--common_name_text", self.single_details_common_name_value.get().strip()])
            if self.single_details_full_name_mode.get() == "custom" and self.single_details_full_name_value.get().strip():
                extra.extend(["--full_name_text", self.single_details_full_name_value.get().strip()])

            if self.single_details_gender_mode.get() == "custom":
                gval = self.single_details_gender_value.get().strip()
                if gval:
                    try:
                        gv = _details_gender_to_int(gval)
                    except Exception as e:
                        messagebox.showerror("Gender", str(e))
                        return
                    if gv is not None:
                        extra.extend(["--gender_value", str(gv)])

            if self.single_details_ethnicity_mode.get() == "custom":
                eval_ = self.single_details_ethnicity_value.get().strip()
                if eval_:
                    try:
                        ev = _details_ethnicity_to_int(eval_)
                    except Exception as e:
                        messagebox.showerror("Ethnicity", str(e))
                        return
                    if ev is not None:
                        extra.extend(["--ethnicity_value", str(ev)])

            # Primary nationality info (Details tab)
            _nat_info_added = False
            try:
                if self.single_details_nationality_info_mode.get() == "custom":
                    ni_label = self.single_details_nationality_info_value.get().strip()
                    if ni_label:
                        extra.extend(["--nationality_info", ni_label])
                        _nat_info_added = True
            except Exception:
                pass

            # Second Nations metadata export (editor values first, then first row as fallback)
            # NOTE: do NOT override the primary Details Nationality Info unless it is blank.
            try:
                _sn_editor_ni = (getattr(self, "single_second_nations_nationality_info").get() or "").strip() if hasattr(self, "single_second_nations_nationality_info") else ""
                _sn_editor_int_ret = bool(getattr(self, "single_second_nations_international_retirement").get()) if hasattr(self, "single_second_nations_international_retirement") else False
                _sn_editor_date = (getattr(self, "single_second_nations_international_retirement_date").get() or "").strip() if hasattr(self, "single_second_nations_international_retirement_date") else ""
                _sn_editor_retire_spell = bool(getattr(self, "single_second_nations_retiring_after_spell_current_club").get()) if hasattr(self, "single_second_nations_retiring_after_spell_current_club") else False

                _sn_items = list(getattr(self, "single_second_nations_items", []) or [])
                _sn0 = dict(_sn_items[0] or {}) if _sn_items else {}

                # Export repeatable second nation list entries (nation + optional per-entry nationality info)
                for _sn in _sn_items:
                    try:
                        _sn_nation = (dict(_sn or {}).get("nation") or "").strip()
                        if not _sn_nation:
                            continue
                        _sn_ni_item = (dict(_sn or {}).get("nationality_info") or "").strip()
                        _sn_spec = _sn_nation
                        if _sn_ni_item:
                            # Pass label through; generator resolves labels/numbers to FM ntin values
                            _sn_spec = f"{_sn_spec}|{_sn_ni_item}"
                        extra.extend(["--second_nation", _sn_spec])
                    except Exception:
                        pass


                _sn_ni = _sn_editor_ni or (_sn0.get("nationality_info") or "").strip()
                if _sn_ni and not _nat_info_added and _sn_ni.lower() != "no info":
                    extra.extend(["--nationality_info", _sn_ni])

                if _sn_editor_int_ret or bool(_sn0.get("international_retirement", False)):
                    extra.append("--international_retirement")

                _sn_date = _sn_editor_date or (_sn0.get("international_retirement_date") or "").strip()
                if _sn_date:
                    extra.extend(["--international_retirement_date", _sn_date])

                if _sn_editor_retire_spell or bool(_sn0.get("retiring_after_spell_current_club", False)):
                    extra.append("--retiring_after_spell_current_club")

                try:
                    _dy_mode = (getattr(self, "single_details_declared_for_youth_nation_mode").get() or "random").strip().lower() if hasattr(self, "single_details_declared_for_youth_nation_mode") else "random"
                    _dy_sel = (getattr(self, "single_details_declared_for_youth_nation_value").get() or "").strip() if hasattr(self, "single_details_declared_for_youth_nation_value") else ""
                    if _dy_mode == "custom" and _dy_sel:
                        extra.extend(["--declared_for_youth_nation", _dy_sel])
                except Exception:
                    pass
            except Exception:
                pass

            if self.single_details_date_of_birth_mode.get() == "custom":
                d = self.single_details_date_of_birth_value.get().strip()
                if d:
                    extra.extend(["--dob", d])

            # Prefer new Details > Height block (range/fixed), fallback to legacy custom single-value height field
            details_height_handled = False
            try:
                h_mode2 = (self.single_details_height_mode2.get() if hasattr(self, "single_details_height_mode2") else "").strip()
                if h_mode2 == "fixed":
                    h = self.single_details_height_fixed.get().strip()
                    if h:
                        extra.extend(["--height", h])
                        details_height_handled = True
                elif h_mode2 == "range":
                    hmin = self.single_details_height_min.get().strip()
                    hmax = self.single_details_height_max.get().strip()
                    if hmin and hmax:
                        extra.extend(["--height_min", hmin, "--height_max", hmax])
                        details_height_handled = True
            except Exception:
                pass

            if (not details_height_handled) and self.single_details_height_mode.get() == "custom":
                h = self.single_details_height_value.get().strip()
                if h:
                    extra.extend(["--height", h])

            if self.single_details_city_of_birth_mode.get() == "custom":
                sel = self.single_details_city_of_birth_value.get().strip()
                if sel:
                    ids = self._get_fixed_ids("city", sel)
                    if ids:
                        extra.extend(["--city_dbid", ids[0], "--city_large", ids[1]])
                    else:
                        messagebox.showerror("City Of Birth", "Custom City Of Birth must be selected from the master_library city list.")
                        return

            if self.single_details_region_of_birth_mode.get() == "custom":
                sel = self.single_details_region_of_birth_value.get().strip()
                if sel:
                    ids = self._get_fixed_ids("nation", sel)
                    if ids:
                        extra.extend(["--nation_dbid", ids[0], "--nation_large", ids[1]])
                    else:
                        messagebox.showerror("Region Of Birth", "Custom Region Of Birth currently maps to Nation and must be selected from the master_library nation list.")
                        return
        except Exception:
            pass

        self._run_generator_common(
            script_path=self.single_script.get().strip(),
            clubs=self.single_clubs.get().strip(),
            first=self.single_first.get().strip(),
            surn=self.single_surn.get().strip(),
            out_path=self.single_out.get().strip(),
            count="1",
            age_min=age_min,
            age_max=age_max,
            ca_min=ca_min,
            ca_max=ca_max,
            pa_min=pa_min,
            pa_max=pa_max,
            base_year=base_year,
            seed=self.single_seed.get().strip(),
            title="Single Generator",
            extra_args=extra,
        )

    # ---------------- Shared generator runner ----------------

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

        extra_joined = " ".join([str(x) for x in (extra_args or [])])
        has_manual_first = "--first_name_text" in extra_joined
        has_manual_second = "--second_name_text" in extra_joined

        if (not has_manual_first) and (not must_exist(first, "first names")):
            return
        if (not has_manual_second) and (not must_exist(surn, "surnames")):
            return
        if not out_path:
            messagebox.showerror("Missing output", "Please choose an output XML path.")
            return

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


    def _ensure_output_visible(self) -> None:
        """Show output pane if hidden so runs do not look like 'nothing happened'."""
        try:
            if not getattr(self, "_output_visible", False):
                self._toggle_output()
        except Exception:
            pass


    # ---------------- Async runner (live stream) ----------------

    def _run_async_stream(self, title: str, cmd: list[str], must_create: str | None = None) -> None:
        self._ensure_output_visible()
        self._log("\n" + "=" * 100)
        self._log(f"{title} command:\n  " + " ".join([_quote(x) for x in cmd]))
        self._log(f"Working directory:\n  {self.base_dir}\n")

        def worker():
            try:
                p = subprocess.Popen(
                    cmd,
                    cwd=str(self.base_dir),
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



    # ---------------- XML Appender (merge/append db_changes XML files) ----------------

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

    def _appender_refresh_source_list(self) -> None:
        lb = getattr(self, "appender_sources_listbox", None)
        if lb is None:
            return
        try:
            lb.delete(0, "end")
            for p in getattr(self, "appender_sources", []):
                lb.insert("end", p)
            self.appender_sources_count.set(f"{len(getattr(self, 'appender_sources', []))} source file(s) selected")
        except Exception:
            pass

    def _appender_add_sources(self) -> None:
        picks = filedialog.askopenfilenames(
            title="Select source XML file(s) to append",
            initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)),
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
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
        d = filedialog.askdirectory(title="Select folder containing XML files", initialdir=str(getattr(self, "fmdata_dir", self.fm_dir)))
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
        self._log(f"[OK] XML Appender: added {added} XML file(s) from folder:\n  {folder}\n")

    def _appender_remove_selected(self) -> None:
        lb = getattr(self, "appender_sources_listbox", None)
        if lb is None:
            return
        sel = list(lb.curselection())
        if not sel:
            return
        keep = []
        selset = set(int(i) for i in sel)
        for idx, p in enumerate(getattr(self, "appender_sources", [])):
            if idx not in selset:
                keep.append(p)
        self.appender_sources = keep
        self._appender_refresh_source_list()

    def _appender_clear_sources(self) -> None:
        self.appender_sources = []
        self._appender_refresh_source_list()

    def _build_appender_tab(self) -> None:
        frm = self.appender_body
        frm.columnconfigure(0, weight=1)

        # State
        self.appender_script = tk.StringVar(value=str(self.fmdata_dir / DEFAULT_XML_APPENDER_SCRIPT))
        self.appender_target_xml = tk.StringVar(value=str(self.fmdata_dir / "fm26_players.xml"))
        self.appender_output_xml = tk.StringVar(value=str(self.fmdata_dir / "fm26_merged.xml"))
        self.appender_sources = []  # list[str]
        self.appender_sources_count = tk.StringVar(value="0 source file(s) selected")

        self.appender_create_target = tk.BooleanVar(value=False)
        self.appender_backup = tk.BooleanVar(value=True)
        self.appender_skip_self = tk.BooleanVar(value=True)
        self.appender_dry_run = tk.BooleanVar(value=False)
        self.appender_verbose = tk.BooleanVar(value=True)
        self.appender_dedupe = tk.StringVar(value="create")

        # File inputs (hidden by default)
        paths = ttk.LabelFrame(frm, text="File inputs")
        paths.grid(row=0, column=0, sticky="ew", padx=8, pady=(0, 8))
        paths.columnconfigure(1, weight=1)
        self.appender_paths_frame = paths
        paths.grid_remove()

        def row_file(r: int, label: str, var: tk.StringVar, picker):
            ttk.Label(paths, text=label).grid(row=r, column=0, sticky="w", padx=(8, 6), pady=6)
            ttk.Entry(paths, textvariable=var).grid(row=r, column=1, sticky="ew", padx=(0, 6), pady=6)
            ttk.Button(paths, text="Browse…", command=lambda: picker(var)).grid(row=r, column=2, sticky="ew", padx=(0, 8), pady=6)

        row_file(0, "Appender script:", self.appender_script, self._pick_py_script_var)
        row_file(1, "Target XML:", self.appender_target_xml, self._pick_xml_target_open)
        row_file(2, "Output XML (optional):", self.appender_output_xml, self._pick_xml_output_save)

        # Source files selector (always visible)
        srcf = ttk.LabelFrame(frm, text="Source XML files to append (multi-select)")
        srcf.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        srcf.columnconfigure(0, weight=1)
        srcf.rowconfigure(1, weight=1)

        ttk.Label(srcf, text="Select multiple XML files and append them into the target (or output file).").grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(6, 4)
        )

        list_wrap = ttk.Frame(srcf)
        list_wrap.grid(row=1, column=0, sticky="nsew", padx=(8, 6), pady=(0, 8))
        list_wrap.columnconfigure(0, weight=1)
        list_wrap.rowconfigure(0, weight=1)

        self.appender_sources_listbox = tk.Listbox(list_wrap, height=10, selectmode="extended")
        self.appender_sources_listbox.grid(row=0, column=0, sticky="nsew")
        lb_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.appender_sources_listbox.yview)
        lb_scroll.grid(row=0, column=1, sticky="ns")
        self.appender_sources_listbox.configure(yscrollcommand=lb_scroll.set)

        btns = ttk.Frame(srcf)
        btns.grid(row=1, column=1, sticky="ns", padx=(0, 8), pady=(0, 8))
        ttk.Button(btns, text="Add XML file(s)…", command=self._appender_add_sources).pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="Add Folder (*.xml)…", command=self._appender_add_folder_xml).pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="Remove Selected", command=self._appender_remove_selected).pack(fill="x", pady=(0, 6))
        ttk.Button(btns, text="Clear List", command=self._appender_clear_sources).pack(fill="x", pady=(0, 6))

        ttk.Label(srcf, textvariable=self.appender_sources_count, foreground="#444").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8)
        )

        # Options
        opt = ttk.LabelFrame(frm, text="Appender options")
        opt.grid(row=2, column=0, sticky="ew", padx=8, pady=(0, 8))
        for c in range(4):
            opt.columnconfigure(c, weight=1)

        ttk.Checkbutton(opt, text="Create target if missing", variable=self.appender_create_target).grid(row=0, column=0, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(opt, text="Backup output/target (.bak)", variable=self.appender_backup).grid(row=0, column=1, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(opt, text="Skip source if same as target", variable=self.appender_skip_self).grid(row=0, column=2, sticky="w", padx=8, pady=6)
        ttk.Checkbutton(opt, text="Verbose per-file output", variable=self.appender_verbose).grid(row=0, column=3, sticky="w", padx=8, pady=6)

        ttk.Checkbutton(opt, text="Dry run (no write)", variable=self.appender_dry_run).grid(row=1, column=0, sticky="w", padx=8, pady=6)
        ttk.Label(opt, text="Dedupe mode:").grid(row=1, column=1, sticky="e", padx=(8, 6), pady=6)
        ded_cb = ttk.Combobox(opt, textvariable=self.appender_dedupe, values=["none", "exact", "create"], state="readonly", width=12)
        ded_cb.grid(row=1, column=2, sticky="w", padx=(0, 8), pady=6)
        ttk.Label(opt, text="create = skip duplicate player create-record IDs").grid(row=1, column=3, sticky="w", padx=8, pady=6)

        hint = (
            "Tip: Use this to merge multiple generated XML files (single-player and batch outputs) into one db_changes XML.\n"
            "You can select multiple files at once, or add a whole folder of XML files."
        )
        ttk.Label(frm, text=hint, foreground="#444").grid(row=3, column=0, sticky="w", padx=8, pady=(0, 8))

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
