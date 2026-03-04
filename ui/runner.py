# -*- coding: utf-8 -*-

from __future__ import annotations

import subprocess
import threading
from pathlib import Path


def quote_arg(s: str) -> str:
    """Shell-ish quoting for log output only (not for execution)."""
    s = "" if s is None else str(s)
    if s == "":
        return '""'
    if any(ch in s for ch in " \t\n\""):
        return '"' + s.replace('"', '\\"') + '"'
    return s


class RunnerMixin:
    """
    Mixin providing the shared async runner used by Generator / Extractor / XML Appender.

    Requires host class to provide:
      - self.base_dir : Path (or str)
      - self._toggle_output()
      - self._log(str)
      - self._log_threadsafe(str)
      - self._ui_error(title, message)
    """

    def _ensure_output_visible(self) -> None:
        """Show output pane if hidden so runs do not look like 'nothing happened'."""
        try:
            if not getattr(self, "_output_visible", False):
                self._toggle_output()
        except Exception:
            pass

    def _run_async_stream(self, title: str, cmd: list[str], must_create: str | None = None) -> None:
        self._ensure_output_visible()
        try:
            wd = str(getattr(self, "base_dir", "."))
        except Exception:
            wd = "."
        try:
            self._log("\n" + "=" * 100)
            self._log(f"{title} command:\n  " + " ".join([quote_arg(x) for x in cmd]))
            self._log(f"Working directory:\n  {wd}\n")
        except Exception:
            pass

        def worker():
            try:
                p = subprocess.Popen(
                    cmd,
                    cwd=wd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                assert p.stdout is not None
                for line in p.stdout:
                    try:
                        self._log_threadsafe(line.rstrip("\n"))
                    except Exception:
                        pass
                rc = p.wait()
            except Exception as e:
                try:
                    self._ui_error(f"{title} failed", str(e))
                except Exception:
                    pass
                return

            if rc == 0 and must_create:
                try:
                    outp = Path(must_create).expanduser()
                    if not outp.exists():
                        try:
                            self._ui_error("Output missing", f"{title} said OK, but output file was not found:\n{outp}")
                        except Exception:
                            pass
                        return
                    if outp.is_file() and outp.stat().st_size == 0:
                        try:
                            self._ui_error("Empty output", f"Output file was created but is empty:\n{outp}")
                        except Exception:
                            pass
                        return
                    try:
                        self._log_threadsafe(f"\n[OK] Output written:\n  {outp}\n  Size: {outp.stat().st_size:,} bytes\n")
                    except Exception:
                        pass
                except Exception as e:
                    try:
                        self._log_threadsafe(f"[WARN] Could not verify output file: {e}\n")
                    except Exception:
                        pass

            if rc == 0:
                try:
                    self._log_threadsafe(f"\n[OK] {title} finished successfully.\n")
                except Exception:
                    pass
            else:
                try:
                    self._log_threadsafe(f"\n[FAIL] {title} exited with code {rc}.\n")
                except Exception:
                    pass
                try:
                    self._ui_error(f"{title} failed", f"{title} failed (exit code {rc}).\nCheck Output/Errors box for details.")
                except Exception:
                    pass

        threading.Thread(target=worker, daemon=True).start()
