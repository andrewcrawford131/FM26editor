# -*- coding: utf-8 -*-
from __future__ import annotations

def _quote(s: str) -> str:
    if not s:
        return '""'
    if any(ch in s for ch in " \t\n\""):
        return '"' + s.replace('"', '"') + '"'
    return s
