# -*- coding: utf-8 -*-
from __future__ import annotations




from ui.fm_paths import detect_fm26_editor_data_dir

import sys

from pathlib import Path

import tkinter as tk
from tkinter import ttk, filedialog, messagebox


class AppShellMixin:
    def _build_shell(self) -> None:
        # Local aliases for legacy references
        APP_TITLE = getattr(self, "_app_title", "FM26 Generator")
        GUI_BUILD = getattr(self, "_gui_build", "")

        self._install_global_combobox_patches()
        self.title(f"{APP_TITLE} [{GUI_BUILD}]")
        self.geometry("1060x720")
        self.minsize(980, 620)

        # Top bar toggles (friendlier UI)
        topbar = ttk.Frame(self)
        topbar.pack(fill="x", padx=10, pady=(10, 0))

        self.btn_toggle_paths = ttk.Button(topbar, text="Show File Inputs", command=self._toggle_paths)
        self.btn_toggle_paths.pack(side="left")

        self.btn_toggle_output = ttk.Button(topbar, text="Show Output", command=self._toggle_output)
        self.btn_toggle_output.pack(side="left", padx=(8, 0))
        self.btn_copy_output = ttk.Button(topbar, text="Copy Output", command=self._copy_output)
        self.btn_copy_output.pack(side="left", padx=(8, 0))

        ttk.Label(topbar, text="(Clean view by default — reveal only when needed)").pack(side="left", padx=(12, 0))


        self.base_dir = Path(__file__).resolve().parents[1]
        self.fm_dir = detect_fm26_editor_data_dir()
        self.fmdata_dir = (self.fm_dir / "fmdata") if self.fm_dir else (self.base_dir / "fmdata")
        try:
            self.fmdata_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

        # Vertical paned window: top (tabs) + bottom (log)
        self.paned = ttk.Panedwindow(self, orient="vertical")
        self.paned.pack(fill="both", expand=True, padx=10, pady=10)


        # [PATCH STATUS BAR HOVERHELP v1]
        # Status bar: hover help (reliable alternative to pop-up tooltips)
        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor="w")
        self.status_label.pack(side="bottom", fill="x", padx=10, pady=(0, 8))


        # Top area
        self._top = ttk.Frame(self.paned)
        # Compat: older shell code uses local 'top' variable
        try:
            _t = getattr(self, '_top', None)
        except Exception:
            _t = None
        if _t is None:
            try:
                self._top = ttk.Frame(self.paned)
            except Exception:
                self._top = ttk.Frame(self)
        top = self._top

        self.paned.add(top, weight=4)

    def _wire_tabs(self) -> None:
        # Local aliases for legacy references
        APP_TITLE = getattr(self, "_app_title", "FM26 Generator")
        GUI_BUILD = getattr(self, "_gui_build", "")

        self.notebook = ttk.Notebook(self._top)
        self.notebook.pack(fill="both", expand=True)

        # Tabs
        self.extract_tab = ttk.Frame(self.notebook)
        self.appender_tab = ttk.Frame(self.notebook)
        self.gen_tab = ttk.Frame(self.notebook)  # visible label renamed to People

        self.notebook.add(self.extract_tab, text="Extractor (Cities,Clubs,Nations and Regions)")
        self.notebook.add(self.appender_tab, text="XML Appender")
        self.settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.add(self.gen_tab, text="People")

        # People -> Player / Non-player
        self.people_kind_notebook = ttk.Notebook(self.gen_tab)
        self.people_kind_notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.player_people_tab = ttk.Frame(self.people_kind_notebook)
        self.nonplayer_people_tab = ttk.Frame(self.people_kind_notebook)
        self.player_nonplayer_people_tab = ttk.Frame(self.people_kind_notebook)

        self.people_kind_notebook.add(self.player_people_tab, text="Player")
        self.people_kind_notebook.add(self.nonplayer_people_tab, text="Non-player")
        self.people_kind_notebook.add(self.player_nonplayer_people_tab, text="Player/Non-Player")

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
        self.batch_international_tab = ttk.Frame(self.player_batch_notebook)  # International Data
        self.batch_contract_tab = ttk.Frame(self.player_batch_notebook)  # Contract
        self.player_batch_notebook.add(self.batch_tab, text="Other")
        self.player_batch_notebook.add(self.batch_details_tab, text="Details")
        self.player_batch_notebook.add(self.batch_international_tab, text="International Data")
        self.player_batch_notebook.add(self.batch_contract_tab, text="Contract")

        self.batch_person_data_tab = ttk.Frame(self.player_batch_notebook)
        self.player_batch_notebook.add(self.batch_person_data_tab, text="Person Data")

        self.batch_player_data_tab = ttk.Frame(self.player_batch_notebook)
        self.player_batch_notebook.add(self.batch_player_data_tab, text="Player Data")

        # Player > Single Person -> Other / Details / International Data
        self.player_single_notebook = ttk.Notebook(self.player_single_parent)
        self.player_single_notebook.pack(fill="both", expand=True)
        self.single_tab = ttk.Frame(self.player_single_notebook)         # Other
        self.single_details_tab = ttk.Frame(self.player_single_notebook) # Details
        self.single_international_tab = ttk.Frame(self.player_single_notebook) # International Data
        self.single_contract_tab = ttk.Frame(self.player_single_notebook)  # Contract
        self.player_single_notebook.add(self.single_tab, text="Other")
        self.player_single_notebook.add(self.single_details_tab, text="Details")
        self.player_single_notebook.add(self.single_international_tab, text="International Data")
        self.player_single_notebook.add(self.single_contract_tab, text="Contract")

        self.single_person_data_tab = ttk.Frame(self.player_single_notebook)
        self.player_single_notebook.add(self.single_person_data_tab, text="Person Data")

        self.single_player_data_tab = ttk.Frame(self.player_single_notebook)
        self.player_single_notebook.add(self.single_player_data_tab, text="Player Data")

        # Non-player scaffolding tabs (Batch/Single) — no "Other" tab
        self.nonplayer_modes_notebook = ttk.Notebook(self.nonplayer_people_tab)
        self.nonplayer_modes_notebook.pack(fill="both", expand=True)

        self.nonplayer_batch_parent = ttk.Frame(self.nonplayer_modes_notebook)
        self.nonplayer_single_parent = ttk.Frame(self.nonplayer_modes_notebook)
        self.nonplayer_modes_notebook.add(self.nonplayer_batch_parent, text="Batch")
        self.nonplayer_modes_notebook.add(self.nonplayer_single_parent, text="Single Person")

        self.nonplayer_batch_notebook = ttk.Notebook(self.nonplayer_batch_parent)
        self.nonplayer_batch_notebook.pack(fill="both", expand=True)
        self.nonplayer_batch_contract_tab = ttk.Frame(self.nonplayer_batch_notebook)
        self.nonplayer_batch_international_tab = ttk.Frame(self.nonplayer_batch_notebook)
        self.nonplayer_batch_notebook.add(self.nonplayer_batch_contract_tab, text="Contract")
        self.nonplayer_batch_notebook.add(self.nonplayer_batch_international_tab, text="International Data")

        self.nonplayer_single_notebook = ttk.Notebook(self.nonplayer_single_parent)
        self.nonplayer_single_notebook.pack(fill="both", expand=True)
        self.nonplayer_single_contract_tab = ttk.Frame(self.nonplayer_single_notebook)
        self.nonplayer_single_international_tab = ttk.Frame(self.nonplayer_single_notebook)
        self.nonplayer_single_notebook.add(self.nonplayer_single_contract_tab, text="Contract")
        self.nonplayer_single_notebook.add(self.nonplayer_single_international_tab, text="International Data")

        # Player/Non-Player scaffolding tabs (hybrid roles like Player/Coach, Player/Chairperson)
        self.player_nonplayer_modes_notebook = ttk.Notebook(self.player_nonplayer_people_tab)
        self.player_nonplayer_modes_notebook.pack(fill="both", expand=True)

        self.player_nonplayer_batch_parent = ttk.Frame(self.player_nonplayer_modes_notebook)
        self.player_nonplayer_single_parent = ttk.Frame(self.player_nonplayer_modes_notebook)
        self.player_nonplayer_modes_notebook.add(self.player_nonplayer_batch_parent, text="Batch")
        self.player_nonplayer_modes_notebook.add(self.player_nonplayer_single_parent, text="Single Person")

        self.player_nonplayer_batch_notebook = ttk.Notebook(self.player_nonplayer_batch_parent)
        self.player_nonplayer_batch_notebook.pack(fill="both", expand=True)
        self.player_nonplayer_batch_contract_tab = ttk.Frame(self.player_nonplayer_batch_notebook)
        self.player_nonplayer_batch_international_tab = ttk.Frame(self.player_nonplayer_batch_notebook)
        self.player_nonplayer_batch_notebook.add(self.player_nonplayer_batch_contract_tab, text="Contract")
        self.player_nonplayer_batch_notebook.add(self.player_nonplayer_batch_international_tab, text="International Data")

        self.player_nonplayer_single_notebook = ttk.Notebook(self.player_nonplayer_single_parent)
        self.player_nonplayer_single_notebook.pack(fill="both", expand=True)
        self.player_nonplayer_single_contract_tab = ttk.Frame(self.player_nonplayer_single_notebook)
        self.player_nonplayer_single_international_tab = ttk.Frame(self.player_nonplayer_single_notebook)
        self.player_nonplayer_single_notebook.add(self.player_nonplayer_single_contract_tab, text="Contract")
        self.player_nonplayer_single_notebook.add(self.player_nonplayer_single_international_tab, text="International Data")



        # Job / Role pickers (Non-player + Player/Non-Player)
        # - Player tab is always 'Player' (no staff roles)
        # - Non-player cannot use Player or Player/… roles
        # - Player/Non-Player can be 'Player' or 'Player/…' roles only
        try:
            self._job_roles_nonplayer, self._job_roles_player_nonplayer = self._build_job_role_options()
        except Exception:
            self._job_roles_nonplayer, self._job_roles_player_nonplayer = [], ["Player"]

        def _role_picker(parent, *, title: str, var: tk.StringVar, options: list[str], note: str):
            wrap = ttk.Frame(parent, padding=16)
            wrap.pack(fill="both", expand=True)
            ttk.Label(wrap, text=title, font=("Segoe UI", 10, "bold")).pack(anchor="w")
            ttk.Label(wrap, text="Job / Role").pack(anchor="w", pady=(10, 2))
            cb = self._make_searchable_picker(wrap, var, options, width=64)
            cb.pack(anchor="w", fill="x")
            ttk.Label(wrap, text=note, foreground="#444", wraplength=900, justify="left").pack(anchor="w", pady=(10, 0))

        # Non-Player role selectors (staff-only)
        _note_np = "Role options are filtered: Non-Player cannot select Player-only or Player/… roles.\n" \
                   "XML mapping for job property 1346587215 will be wired once the full mapping table is confirmed."
        _role_picker(self.nonplayer_batch_contract_tab, title="Non-Player (staff-only)", var=self.nonplayer_batch_job_role, options=self._job_roles_nonplayer, note=_note_np)
        _role_picker(self.nonplayer_single_contract_tab, title="Non-Player (staff-only)", var=self.nonplayer_single_job_role, options=self._job_roles_nonplayer, note=_note_np)

        # Player/Non-Player role selectors (hybrid)
        _note_pnp = "Role options are filtered: Player/Non-Player can be 'Player' or 'Player/…' roles only.\n" \
                    "Pure staff-only roles are not allowed in this tab.\n" \
                    "XML mapping for job property 1346587215 will be wired once the full mapping table is confirmed."
        _role_picker(self.player_nonplayer_batch_contract_tab, title="Player/Non-Player (hybrid)", var=self.player_nonplayer_batch_job_role, options=self._job_roles_player_nonplayer, note=_note_pnp)
        _role_picker(self.player_nonplayer_single_contract_tab, title="Player/Non-Player (hybrid)", var=self.player_nonplayer_single_job_role, options=self._job_roles_player_nonplayer, note=_note_pnp)

        # Placeholders for International Data (to be mirrored from Player tab later)
        _intl_note = "International Data UI for Non-player / Player/Non-Player will be mirrored from the Player tab.\n" \
                     "For now, configure International Data in Player > International Data."
        for _fr in (
            self.nonplayer_batch_international_tab,
            self.nonplayer_single_international_tab,
            self.player_nonplayer_batch_international_tab,
            self.player_nonplayer_single_international_tab,
        ):
            try:
                ttk.Label(_fr, text=_intl_note, padding=16, wraplength=900, justify="left").pack(anchor="w")
            except Exception:
                pass


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

        self.batch_international_actionbar = ttk.Frame(self.batch_international_tab)
        self.batch_international_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.batch_international_actionbar, text="Run Batch Generator", command=self._run_batch_generator_safe).pack(side="left")

        batch_international_holder = ttk.Frame(self.batch_international_tab)
        batch_international_holder.pack(side="top", fill="both", expand=True)
        self.batch_international_body = self._make_scrollable(batch_international_holder)

        self.single_international_actionbar = ttk.Frame(self.single_international_tab)
        self.single_international_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.single_international_actionbar, text="Generate 1 Player", command=self._run_single_generator_safe).pack(side="left")

        single_international_holder = ttk.Frame(self.single_international_tab)
        single_international_holder.pack(side="top", fill="both", expand=True)
        self.single_international_body = self._make_scrollable(single_international_holder)

        self.batch_contract_actionbar = ttk.Frame(self.batch_contract_tab)
        self.batch_contract_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.batch_contract_actionbar, text="Run Batch Generator", command=self._run_batch_generator_safe).pack(side="left")

        batch_contract_holder = ttk.Frame(self.batch_contract_tab)
        batch_contract_holder.pack(side="top", fill="both", expand=True)
        self.batch_contract_body = self._make_scrollable(batch_contract_holder)


        self.batch_person_actionbar = ttk.Frame(self.batch_person_data_tab)
        self.batch_person_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.batch_person_actionbar, text="Run Batch Generator", command=self._run_batch_generator_safe).pack(side="left")

        batch_person_holder = ttk.Frame(self.batch_person_data_tab)
        batch_person_holder.pack(side="top", fill="both", expand=True)
        self.batch_person_data_body = self._make_scrollable(batch_person_holder)


        self.batch_player_actionbar = ttk.Frame(self.batch_player_data_tab)
        self.batch_player_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.batch_player_actionbar, text="Run Batch Generator", command=self._run_batch_generator_safe).pack(side="left")

        batch_player_holder = ttk.Frame(self.batch_player_data_tab)
        batch_player_holder.pack(side="top", fill="both", expand=True)
        self.batch_player_data_body = self._make_scrollable(batch_player_holder)

        self.single_contract_actionbar = ttk.Frame(self.single_contract_tab)
        self.single_contract_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.single_contract_actionbar, text="Generate 1 Player", command=self._run_single_generator_safe).pack(side="left")

        single_contract_holder = ttk.Frame(self.single_contract_tab)
        single_contract_holder.pack(side="top", fill="both", expand=True)
        self.single_contract_body = self._make_scrollable(single_contract_holder)


        self.single_person_actionbar = ttk.Frame(self.single_person_data_tab)
        self.single_person_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.single_person_actionbar, text="Generate 1 Player", command=self._run_single_generator_safe).pack(side="left")

        single_person_holder = ttk.Frame(self.single_person_data_tab)
        single_person_holder.pack(side="top", fill="both", expand=True)
        self.single_person_data_body = self._make_scrollable(single_person_holder)


        self.single_player_actionbar = ttk.Frame(self.single_player_data_tab)
        self.single_player_actionbar.pack(side="bottom", fill="x", padx=10, pady=(0, 10))
        ttk.Button(self.single_player_actionbar, text="Generate 1 Player", command=self._run_single_generator_safe).pack(side="left")

        single_player_holder = ttk.Frame(self.single_player_data_tab)
        single_player_holder.pack(side="top", fill="both", expand=True)
        self.single_player_data_body = self._make_scrollable(single_player_holder)

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
        self._build_batch_international_tab()
        self._build_single_international_tab()
        self._build_batch_contract_tab()
        self._build_single_contract_tab()
        self._build_batch_person_data_tab()
        self._build_single_person_data_tab()

        self._build_batch_player_data_tab()
        self._build_single_player_data_tab()

        self._build_appender_tab()
        self._build_settings_tab()
        self._build_nonplayer_job_pickers()
        self._init_batch_single_file_sync()
        self.after(200, self._reload_master_library)
        self.after(350, self._cleanup_other_tabs_fields)
        self.after(900, self._cleanup_other_tabs_fields)
        self.after(1800, self._cleanup_other_tabs_fields)
        self.after(3200, self._cleanup_other_tabs_fields)
        self.after(1200, self._poll_master_library_changes)

    # ---------------- Logging helpers ----------------

