# -*- coding: utf-8 -*-
# Auto-generated from fm26_generator_gui_2.py
# XML Appender tab extracted into a mixin to reduce main GUI file size.


from __future__ import annotations

import os
import re
from pathlib import Path
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Helper bridge (if main GUI defines these)
try:
    from __main__ import _attach_tooltip, _bind_help  # type: ignore
except Exception:
    def _attach_tooltip(*_a, **_k):
        return
    def _bind_help(*_a, **_k):
        return


DEFAULT_XML_APPENDER_SCRIPT = "fm26_xml_appender.py"

def _guess_default_appender_script(fmdata_dir: Path) -> Path:
    """Prefer repo-root fm26_xml_appender.py; fallback to fmdata_dir."""
    repo_root = Path(__file__).resolve().parents[2]
    p_repo = repo_root / DEFAULT_XML_APPENDER_SCRIPT
    if p_repo.exists():
        return p_repo
    return fmdata_dir / DEFAULT_XML_APPENDER_SCRIPT


class XmlAppenderMixin:
    def _build_appender_tab(self) -> None:
        frm = self.appender_body
        frm.columnconfigure(0, weight=1)

        # State
        default_script = _guess_default_appender_script(getattr(self, 'fmdata_dir', Path.cwd()))
        self.appender_script = tk.StringVar(value=str(default_script))
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
        ded_cb = ttk.Combobox(opt, textvariable=self.appender_dedupe, values=["none", "exact", "create"], state="normal", width=12)
        ded_cb.grid(row=1, column=2, sticky="w", padx=(0, 8), pady=6)
        ttk.Label(opt, text="create = skip duplicate player create-record IDs").grid(row=1, column=3, sticky="w", padx=8, pady=6)

        hint = (
            "Tip: Use this to merge multiple generated XML files (single-player and batch outputs) into one db_changes XML.\n"
            "You can select multiple files at once, or add a whole folder of XML files."
        )
        ttk.Label(frm, text=hint, foreground="#444").grid(row=3, column=0, sticky="w", padx=8, pady=(0, 8))

