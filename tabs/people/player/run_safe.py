# -*- coding: utf-8 -*-
from __future__ import annotations

from tkinter import messagebox

class RunSafeMixin:
    def _run_batch_generator_safe(self) -> None:
        try:
            self._run_batch_generator()
        except Exception as e:
            try:
                self._ensure_output_visible()
                self._log(f"[ERROR] Run Batch Generator callback crashed: {e}")
            except Exception:
                pass
            try:
                messagebox.showerror("Run Batch Generator error", str(e))
            except Exception:
                pass
    def _run_single_generator_safe(self) -> None:
        try:
            self._run_single_generator()
        except Exception as e:
            try:
                self._ensure_output_visible()
                self._log(f"[ERROR] Generate 1 Player callback crashed: {e}")
            except Exception:
                pass
            try:
                messagebox.showerror("Generate 1 Player error", str(e))
            except Exception:
                pass

        def _autoclear_dontset(self, src_var, dont_set_var) -> None:
            """When src_var changes, clear dont_set_var.
            Prevents accidental --omit-field when user selected Random/Range."""
            try:
                src_var.trace_add("write", lambda *_: dont_set_var.set(False))
            except Exception:
                pass

def main() -> int:
    try:
        app = App()
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
    raise SystemExit(main())
