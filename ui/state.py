# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk


class StateVarsMixin:
    def _init_state_vars(self) -> None:
        # Ensure Job/Role option lists exist before state vars reference them
        try:
            if (not hasattr(self, "_job_roles_nonplayer")) or (not hasattr(self, "_job_roles_player_nonplayer")):
                try:
                    self._job_roles_nonplayer, self._job_roles_player_nonplayer = self._build_job_role_options()
                except Exception:
                    self._job_roles_nonplayer, self._job_roles_player_nonplayer = [], ["Player"]
        except Exception:
            try:
                self._job_roles_nonplayer, self._job_roles_player_nonplayer = [], ["Player"]
            except Exception:
                pass

        self._paths_visible = False
        self._output_visible = False
        self.status_var = tk.StringVar(value="")
        self.nonplayer_batch_job_role = tk.StringVar(value=(self._job_roles_nonplayer[0] if self._job_roles_nonplayer else "Coach First Team"))
        self.nonplayer_single_job_role = tk.StringVar(value=(self._job_roles_nonplayer[0] if self._job_roles_nonplayer else "Coach First Team"))
        self.player_nonplayer_batch_job_role = tk.StringVar(value="Player")
        self.player_nonplayer_single_job_role = tk.StringVar(value="Player")

        # Back-compat: some overrides expect single_wage_value
        try:
            if hasattr(self, 'single_wage_fixed') and not hasattr(self, 'single_wage_value'):
                self.single_wage_value = self.single_wage_fixed
        except Exception:
            pass
