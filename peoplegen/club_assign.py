# -*- coding: utf-8 -*-
from __future__ import annotations

import random
from typing import Callable, Optional, Sequence, Tuple, Any

# clubs entries may be: (dbid, large, name) OR (dbid, large, name, gender)
ClubTuple = tuple[Any, Any, Any] | tuple[Any, Any, Any, Any]
IsOmittedFn = Callable[..., bool]


def pick_club_dbids(*, rng: random.Random, clubs: Sequence[ClubTuple], fixed_club: Optional[Tuple[int, int]], eff_gender_value: int) -> Tuple[int, int]:
    """Pick a club (dbid, large).

    - If fixed_club is provided, return it.
    - Else pick from clubs list.
    - If clubs include gender at index 3, prefer matching gender ('male'/'female'),
      but allow blank gender.
    """
    if fixed_club:
        try:
            return int(fixed_club[0]), int(fixed_club[1])
        except Exception:
            return fixed_club[0], fixed_club[1]  # type: ignore[return-value]

    want_gender = "female" if int(eff_gender_value) == 1 else "male"
    pool = []
    for c in (clubs or []):
        try:
            # if no gender field, accept
            if len(c) <= 3:
                pool.append(c)
                continue
            g = str(c[3]).strip().lower()
            if g in ("", want_gender):
                pool.append(c)
        except Exception:
            # if weird tuple, ignore
            continue

    pick_from = pool if pool else list(clubs or [])
    if not pick_from:
        return (0, 0)
    c = rng.choice(pick_from)
    try:
        return int(c[0]), int(c[1])
    except Exception:
        return c[0], c[1]  # type: ignore[return-value]


def should_emit_club_record(*, rng: random.Random, club_dbid: int, club_large: int, club_assign_pct: Any, is_omitted: IsOmittedFn) -> bool:
    """Decide once whether to emit a club record.

    Mirrors generator logic:
    - If club field omitted OR no club ids -> False
    - Otherwise emit with probability club_assign_pct% (clamped 0..100)
    """
    try:
        if is_omitted("club", "club_dbid", "club_large"):
            return False
    except Exception:
        # If omit checker fails, default to emitting (but still require ids).
        pass

    if not club_dbid or not club_large:
        return False

    pct = 100
    try:
        pct = int(club_assign_pct)
    except Exception:
        pct = 100

    if pct < 0:
        pct = 0
    if pct > 100:
        pct = 100

    if pct >= 100:
        return True
    if pct <= 0:
        return False

    return rng.random() < (float(pct) / 100.0)


__all__ = [k for k in globals().keys() if not k.startswith("__")]
