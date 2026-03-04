# -*- coding: utf-8 -*-
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

class AppCleanupMixin:
    def _app_cleanup_other_tabs_fields(self):
        """Best-effort UI cleanup hook for duplicate fields on 'Other' tabs.
        Safe no-op if widgets/attributes are not present in this build."""
        try:
            # Optional future cleanup logic can live here.
            return
        except Exception:
            return
