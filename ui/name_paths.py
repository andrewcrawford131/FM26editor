# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

def _preferred_name_csv_path(fmdata_dir: Path, stem: str) -> str:
    """Return best-guess CSV path for a given stem in fmdata_dir.

    Preference order (when files exist):
      1) <stem>_5n_v3_weightfreq.csv
      2) <stem>_v3_weightfreq.csv
      3) <stem>.csv
    """
    base = Path(fmdata_dir)
    candidates = [
        base / f"{stem}_5n_v3_weightfreq.csv",
        base / f"{stem}_v3_weightfreq.csv",
        base / f"{stem}.csv",
    ]
    for p in candidates:
        try:
            if p.exists():
                return str(p)
        except Exception:
            pass
    return str(candidates[-1])
