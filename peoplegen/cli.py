# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
import inspect

import fm26_people_generator_core as gen


def main(argv: list[str] | None = None) -> int:
    # If the core main() accepts argv, pass it through. Otherwise emulate via sys.argv.
    try:
        sig = inspect.signature(gen.main)
        if len(sig.parameters) >= 1:
            if argv is None:
                return int(gen.main() or 0)
            return int(gen.main(argv) or 0)
    except Exception:
        pass

    if argv is None:
        return int(gen.main() or 0)

    old = sys.argv[:]
    try:
        sys.argv = [old[0]] + list(argv)
        return int(gen.main() or 0)
    finally:
        sys.argv = old


if __name__ == "__main__":
    raise SystemExit(main())
