# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

class OutputPaneMixin:
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
            getattr(self, "batch_international_paths_frame", None),
            getattr(self, "batch_contract_paths_frame", None),
            getattr(self, "single_paths_frame", None),
            getattr(self, "single_details_paths_frame", None),
            getattr(self, "single_international_paths_frame", None),
            getattr(self, "single_contract_paths_frame", None),
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

    # ---------- Date input (no pip) ----------------
    def _copy_output(self) -> None:
        """Copy the Output/Errors log to clipboard."""
        try:
            data = self.log.get('1.0', 'end-1c')
            self.clipboard_clear()
            self.clipboard_append(data)
            try:
                self._log('[OK] Output copied to clipboard.\n')
            except Exception:
                pass
        except Exception as e:
            try:
                messagebox.showerror('Copy failed', str(e))
            except Exception:
                pass

