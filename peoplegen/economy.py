
# -*- coding: utf-8 -*-
from __future__ import annotations

import random
from typing import Tuple

try:
    # Prefer the shared helper if you already extracted it.
    from peoplegen.xml_helpers import _rep_triplet as _rep_triplet
except Exception:
    def _rep_triplet(rng: random.Random, rep_min: int, rep_max: int) -> Tuple[int, int, int]:
        # Fallback (should match your generator's semantics closely)
        a = rng.randint(rep_min, rep_max)
        b = rng.randint(rep_min, max(rep_min, a - 1))
        c = rng.randint(rep_min, max(rep_min, b - 1))
        a = max(0, min(200, a))
        b = max(0, min(200, b))
        c = max(0, min(200, c))
        if b >= a:
            b = max(0, a - 1)
        if c >= b:
            c = max(0, b - 1)
        return a, b, c


def _tv_from_pa(pa: int, *, lo: int = 100_000, hi: int = 150_000_000) -> int:
    """Derive transfer value from PA.

    Default range: 100,000 .. 150,000,000 (the generator can clamp differently).
    """
    x = max(0, min(200, int(pa)))
    return int(lo + ((x / 200.0) ** 3) * (hi - lo))


def decide_economy(
    *,
    rng: random.Random,
    wage: int,
    wage_min: int,
    wage_max: int,
    rep_current: int,
    rep_home: int,
    rep_world: int,
    rep_min: int,
    rep_max: int,
    transfer_mode: str,
    transfer_value: int,
    transfer_min: int,
    transfer_max: int,
    pa: int,
    tv_lo: int,
    tv_hi: int,
) -> Tuple[int, int, int, int, int]:
    """Return (wage_val, rep_cur, rep_home_v, rep_world_v, transfer_value_tv).

    Mirrors the in-generator logic.
    """
    # wage (minimum 30)
    wage_val = max(30, wage) if wage > 0 else rng.randint(int(wage_min), int(wage_max))

    # reputation (strict current > home > world)
    if (rep_current >= 0) or (rep_home >= 0) or (rep_world >= 0):
        cur = rep_current if rep_current >= 0 else rep_max
        home = rep_home if rep_home >= 0 else max(rep_min, cur - 1)
        world = rep_world if rep_world >= 0 else max(rep_min, home - 1)
        cur = max(0, min(200, int(cur)))
        home = max(0, min(200, int(home)))
        world = max(0, min(200, int(world)))
        if home >= cur:
            home = max(0, cur - 1)
        if world >= home:
            world = max(0, home - 1)
        rep_cur, rep_home_v, rep_world_v = cur, home, world
    else:
        rep_cur, rep_home_v, rep_world_v = _rep_triplet(rng, int(rep_min), int(rep_max))

    # transfer value
    mode = str(transfer_mode or "").strip().lower()
    if mode == "auto":
        tv = _tv_from_pa(int(pa))
    elif mode == "fixed":
        tv = int(transfer_value)
    else:
        lo = int(transfer_min) if int(transfer_min) > 0 else int(tv_lo)
        hi = int(transfer_max) if int(transfer_max) > 0 else int(tv_hi)
        if hi < lo:
            lo, hi = hi, lo
        tv = rng.randint(lo, hi)

    tv = max(int(tv_lo), min(int(tv_hi), int(tv)))
    return int(wage_val), int(rep_cur), int(rep_home_v), int(rep_world_v), int(tv)


__all__ = [k for k in globals().keys() if not k.startswith("__")]
