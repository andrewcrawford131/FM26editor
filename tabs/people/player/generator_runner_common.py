# -*- coding: utf-8 -*-
from __future__ import annotations

import re

import sys
from pathlib import Path
import tkinter as tk
from tkinter import messagebox

def ensure_parent_dir(file_path: str) -> None:
    """Create parent directory for a file path (or dir itself if no suffix)."""
    p = Path(str(file_path).strip())
    if not str(p):
        return
    parent = p.parent if p.suffix else p
    if not str(parent) or str(parent) in (".", ""):
        return
    parent.mkdir(parents=True, exist_ok=True)

class GeneratorRunnerCommonMixin:
    def _generator_script_supports_flag(self, script_path: str, flag: str) -> bool:
        try:
            txt = Path(script_path).read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return True  # don't block if unreadable
        return (flag in txt)
    def _strip_unsupported_cli_flags(self, cmd, script_path=None):

        """Remove unsupported --flags from the generator CLI command list.

        Keeps positional args. Drops flag + optional value when flag isn't found in the generator script."""

        try:

            cmd_list = list(cmd)

        except Exception:

            return cmd


        # Infer script_path if not provided

        if not script_path:

            sp = ""

            for tok in cmd_list:

                if isinstance(tok, str) and tok.lower().endswith('.py'):

                    sp = tok

                    break

            if not sp and len(cmd_list) >= 2 and isinstance(cmd_list[1], str):

                sp = cmd_list[1]

            script_path = sp


        out = []

        i = 0

        while i < len(cmd_list):

            tok = cmd_list[i]

            if isinstance(tok, str) and tok.startswith('--'):

                supported = True

                try:

                    supported = self._generator_script_supports_flag(script_path, tok)

                except Exception:

                    supported = True


                if supported:

                    out.append(tok)

                    # Keep next token as value if it isn't another --flag

                    if i + 1 < len(cmd_list):

                        nxt = cmd_list[i + 1]

                        if not (isinstance(nxt, str) and nxt.startswith('--')):

                            out.append(nxt)

                            i += 2

                            continue

                    i += 1

                    continue

                else:

                    # Skip flag and its value (if any)

                    if i + 1 < len(cmd_list):

                        nxt = cmd_list[i + 1]

                        if not (isinstance(nxt, str) and nxt.startswith('--')):

                            i += 2

                            continue

                    i += 1

                    continue

            else:

                out.append(tok)

                i += 1

        return out
    def _run_generator_common(
        self,
        script_path: str,
        clubs: str,
        first: str,
        female_first: str,
        common_names: str,
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
        if female_first and (not must_exist(female_first, "female first names")):
            return
        if common_names and (not must_exist(common_names, "common names")):
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


        # Base year validation (prevents 5-digit years like 20265)
        by = (base_year or "").strip()
        if not re.fullmatch(r"\d{1,4}", by):
            messagebox.showerror("Base year", "Base year must be 1–4 digits (e.g. 2026).")
            return
        by_i = int(by)
        if by_i < 1 or by_i > 9999:
            messagebox.showerror("Base year", "Base year must be in the range 1..9999.")
            return
        base_year = str(by_i)
        if by_i < 1900 or by_i > 2100:
            try:
                self._log(f"[WARN] Base year {by_i} is unusual (expected ~1900–2100). Continuing.\n")
            except Exception:
                pass

        cmd = [
            sys.executable,
            script_path,
            "--master_library", clubs,
            "--first_names", first,
            "--surnames", surn,
            "--count", count,
            "--output", out_path,
        ]
        if str(age_min or "").strip() != "":
            cmd.extend(["--age_min", str(age_min).strip()])
        if str(age_max or "").strip() != "":
            cmd.extend(["--age_max", str(age_max).strip()])

        _extra_scan = [str(x).strip().lower() for x in (extra_args or [])]
        _omit_fields = set()
        for i in range(len(_extra_scan) - 1):
            if _extra_scan[i] == "--omit-field":
                _omit_fields.add(_extra_scan[i + 1])

        if "ca" not in _omit_fields:
            cmd.extend(["--ca_min", ca_min, "--ca_max", ca_max])
        if "pa" not in _omit_fields:
            cmd.extend(["--pa_min", pa_min, "--pa_max", pa_max])
        cmd.extend(["--base_year", base_year])
        if female_first:
            cmd.extend(["--female_first_names", female_first])
        if common_names:
            cmd.extend(["--common_names", common_names])
        if seed:
            cmd.extend(["--seed", seed])
        if extra_args:
            extra_args = self._strip_unsupported_cli_flags(script_path, list(extra_args))
            cmd.extend([x for x in extra_args if x is not None and str(x) != ""])

        self._run_async_stream(title, cmd, must_create=out_path)

