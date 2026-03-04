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

from ui.name_paths import _preferred_name_csv_path
from ui.app_shell import AppShellMixin
from ui.state import StateVarsMixin

import os
import sys
import csv
import re
import threading
import subprocess
import calendar as _cal
import datetime as _dt
from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from ui.date_picker import DatePickerPopup, DateInput
from ui.tooltips import _bind_help, _ToolTip, _attach_tooltip, _hoverhelp_autobind
from ui.runner import RunnerMixin
from ui.scroll import ScrollMixin
from ui.pickers import PickerWidgetsMixin
from ui.output_pane import OutputPaneMixin
from ui.file_dialogs import FileDialogsMixin
from ui.library_parsing_helpers import LibraryParsingHelpersMixin

from data.library_loader import LibraryLoaderMixin
# [SCROLL_MIXIN_V2]

from tabs.people.player.subtabs.international import InternationalSubtabMixin
from tabs.people.player.subtabs.contract import ContractSubtabMixin
from tabs.people.player.subtabs.contract_overrides import ContractOverridesMixin
from tabs.people.player.subtabs.details import DetailsSubtabMixin
from tabs.people.player.subtabs.person_data import PersonDataSubtabMixin

from tabs.people.player.subtabs.player_data import PlayerDataSubtabMixin

from tabs.people.player.ui_batch_tab import BatchTabUIMixin
from tabs.people.player.ui_single_tab import SingleTabUIMixin
from tabs.people.player.ui_common import PlayerUiCommonMixin
from tabs.people.player.subtabs.intl_cli_export import InternationalCliExportMixin
from tabs.people.player.generator_run import GeneratorRunMixin
from tabs.people.player.generator_runner_common import GeneratorRunnerCommonMixin
from tabs.people.player.details_height_bridge import DetailsHeightBridgeMixin
# [INTL_CLI_EXPORT_MIXIN_V1]

from tabs.xml_appender.tab import XmlAppenderMixin
from tabs.xml_appender.actions import XmlAppenderActionsMixin

from tabs.extractor.tab import ExtractorTabMixin
# [EXTRACTOR_MOD_V1]

# [XML_APPENDER_MOD_V1]

from tabs.settings.tab import SettingsTabMixin
from ui.cli_utils import _quote

from ui.path_utils import ensure_parent_dir

from tabs.people.player.subtabs.contract_overrides_engine import ContractOverridesEngineMixin

from tabs.people.player.details_dontset import DetailsDontSetMixin

from tabs.people.player.ui_cleanup import AppCleanupMixin

from tabs.people.player.nonplayer_job_pickers import NonPlayerJobPickersMixin

from ui.job_roles import JobRolesMixin

from tabs.people.player.subtabs.details_utils import DetailsUtilsMixin

from ui.mode_binders import ModeBindersMixin

from ui.path_resolve import PathResolveMixin

from ui.id_resolver import IdResolverMixin

from tabs.people.player.run_safe import RunSafeMixin

from ui.date_helpers import DateHelpersMixin

# [SETTINGS_MOD_V1]

# [DETAILS_MOD_V1]

# [CONTRACT_MOD_V3]

# [INTL_MIXIN_WIRING_V4]
from ui.constants import APP_TITLE, GUI_BUILD, DEFAULT_EXTRACT_SCRIPT, DEFAULT_GENERATE_SCRIPT, DEFAULT_XML_APPENDER_SCRIPT, ALL_POS

class App(InternationalSubtabMixin, ContractSubtabMixin, ContractOverridesMixin, DetailsSubtabMixin, PersonDataSubtabMixin, PlayerDataSubtabMixin, SettingsTabMixin, XmlAppenderMixin, XmlAppenderActionsMixin, ExtractorTabMixin, RunnerMixin, GeneratorRunMixin, ScrollMixin, InternationalCliExportMixin, BatchTabUIMixin, SingleTabUIMixin, PickerWidgetsMixin, LibraryLoaderMixin, PlayerUiCommonMixin, LibraryParsingHelpersMixin, StateVarsMixin, AppShellMixin, DetailsHeightBridgeMixin, GeneratorRunnerCommonMixin, OutputPaneMixin, FileDialogsMixin, ContractOverridesEngineMixin, DetailsDontSetMixin, AppCleanupMixin, NonPlayerJobPickersMixin, JobRolesMixin, DetailsUtilsMixin, ModeBindersMixin, PathResolveMixin, RunSafeMixin, DateHelpersMixin, tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        # Keep title/build info available across extracted modules
        try:
            self._app_title = APP_TITLE
            self._gui_build = GUI_BUILD
        except Exception:
            pass
        # Install global combobox patches if present (safe no-op if missing)
        try:
            self._install_global_combobox_patches()
        except Exception:
            pass
        self._init_state_vars()
        self._build_shell()
        self._wire_tabs()

    # ---------------- Players (Batch) UI ----------------

# ---------------- Crash-safe entrypoint (auto-patched) ----------------

CRASH_LOG_NAME = "fm26_gui_crash.log"

def _append_crash_log(text: str) -> None:
    try:
        log_path = Path(__file__).resolve().with_name(CRASH_LOG_NAME)
    except Exception:
        return
    try:
        with log_path.open("a", encoding="utf-8", errors="ignore") as f:
            f.write(text)
    except Exception:
        pass

def _install_tk_callback_logger(app) -> None:
    # Capture uncaught Tk callback exceptions into fm26_gui_crash.log and show a popup.

    def _cb(exc, val, tb):
        try:
            import traceback
            stamp = _dt.datetime.now().isoformat(sep=" ", timespec="seconds")
            tbtxt = "".join(traceback.format_exception(exc, val, tb))
            _append_crash_log(f'''\n[{stamp}] Tk callback exception\n{tbtxt}\n''')
        except Exception:
            _append_crash_log("\nTk callback exception (failed to format traceback)\n")
        try:
            lp = Path(__file__).resolve().with_name(CRASH_LOG_NAME)
            messagebox.showerror("FM26 Generator error", f"A GUI callback crashed.\n\nLog: {lp}")
        except Exception:
            pass

    try:
        app.report_callback_exception = _cb
    except Exception:
        pass

def _crash_safe_main() -> int:
    # Run main() and write a crash log + popup on any unhandled exception.
    try:
        return int(main() or 0)
    except Exception:
        try:
            import traceback
            stamp = _dt.datetime.now().isoformat(sep=" ", timespec="seconds")
            tbtxt = traceback.format_exc()
            _append_crash_log(f'''\n[{stamp}] Unhandled exception in GUI\n{tbtxt}\n''')
        except Exception:
            _append_crash_log("\nUnhandled exception in GUI (failed to format traceback)\n")
        try:
            lp = Path(__file__).resolve().with_name(CRASH_LOG_NAME)
        except Exception:
            lp = CRASH_LOG_NAME
        try:
            # Ensure a Tk root exists when running via pythonw.
            try:
                r = tk.Tk()
                r.withdraw()
                messagebox.showerror("FM26 Generator crashed", f"The app crashed.\n\nLog: {lp}")
                r.destroy()
            except Exception:
                messagebox.showerror("FM26 Generator crashed", f"The app crashed.\n\nLog: {lp}")
        except Exception:
            pass
        return 1

def main() -> int:
    try:
        app = App()
        try:
            _install_tk_callback_logger(app)
        except Exception:
            pass
        try:
            _hoverhelp_autobind(app)
        except Exception:
            pass
    except tk.TclError as e:
        print("Tkinter UI could not start. On Linux you may need Tk support, e.g.:")
        print("  sudo apt-get install python3-tk")
        print(f"Error: {e}")
        return 2

    app.mainloop()
    return 0
if __name__ == "__main__":
    raise SystemExit(_crash_safe_main())
