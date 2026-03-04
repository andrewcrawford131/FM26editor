# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

class NonPlayerJobPickersMixin:
    def _build_nonplayer_job_pickers(self) -> None:
        """Ensure Job/Role pickers exist in Non-player + Player/Non-Player Contract tabs."""
        try:
            if getattr(self, "_job_pickers_built", False):
                return

            # If tabs already have children, don't duplicate (job picker is usually the only content)
            try:
                if hasattr(self, "nonplayer_batch_contract_tab") and self.nonplayer_batch_contract_tab.winfo_children():
                    self._job_pickers_built = True
                    return
            except Exception:
                pass

            self._job_pickers_built = True

            try:
                nonplayer_roles, hybrid_roles = self._build_job_role_options()
            except Exception:
                nonplayer_roles, hybrid_roles = [], ["Player"]

            if not hasattr(self, "nonplayer_batch_job_role"):
                self.nonplayer_batch_job_role = tk.StringVar(value=(nonplayer_roles[0] if nonplayer_roles else "Coach First Team"))
            if not hasattr(self, "nonplayer_single_job_role"):
                self.nonplayer_single_job_role = tk.StringVar(value=(nonplayer_roles[0] if nonplayer_roles else "Coach First Team"))
            if not hasattr(self, "player_nonplayer_batch_job_role"):
                self.player_nonplayer_batch_job_role = tk.StringVar(value="Player")
            if not hasattr(self, "player_nonplayer_single_job_role"):
                self.player_nonplayer_single_job_role = tk.StringVar(value="Player")

            def _add_picker(tab, title, var, options, note):
                lf = ttk.LabelFrame(tab, text=title)
                lf.pack(fill="x", padx=12, pady=12)
                ttk.Label(lf, text="Job / Role").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 4))
                w = self._make_searchable_picker(lf, var, list(options or []), width=64)
                w.grid(row=1, column=0, sticky="ew", padx=8, pady=(0, 8))
                lf.columnconfigure(0, weight=1)
                ttk.Label(lf, text=note, foreground="#444", wraplength=900, justify="left").grid(row=2, column=0, sticky="w", padx=8, pady=(0, 8))

            if hasattr(self, "nonplayer_batch_contract_tab"):
                _add_picker(self.nonplayer_batch_contract_tab, "Non-Player (staff-only)", self.nonplayer_batch_job_role, nonplayer_roles,
                            "Non-Player cannot select Player-only or Player/… roles.")
            if hasattr(self, "nonplayer_single_contract_tab"):
                _add_picker(self.nonplayer_single_contract_tab, "Non-Player (staff-only)", self.nonplayer_single_job_role, nonplayer_roles,
                            "Non-Player cannot select Player-only or Player/… roles.")
            if hasattr(self, "player_nonplayer_batch_contract_tab"):
                _add_picker(self.player_nonplayer_batch_contract_tab, "Player/Non-Player (hybrid)", self.player_nonplayer_batch_job_role, hybrid_roles,
                            "Hybrid can be 'Player' or 'Player/…' roles only.")
            if hasattr(self, "player_nonplayer_single_contract_tab"):
                _add_picker(self.player_nonplayer_single_contract_tab, "Player/Non-Player (hybrid)", self.player_nonplayer_single_job_role, hybrid_roles,
                            "Hybrid can be 'Player' or 'Player/…' roles only.")
        except Exception:
            pass

    # Attach Settings/Jobs helpers
    try:
        App._build_nonplayer_job_pickers = _build_nonplayer_job_pickers
    except Exception:
        pass



