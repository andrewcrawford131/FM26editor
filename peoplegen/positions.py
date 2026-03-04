
# -*- coding: utf-8 -*-
from __future__ import annotations

import random
from typing import Dict, List, Optional, Sequence, Tuple

# --- Position property IDs (FM) ---
POS_PROPS: Dict[str, int] = {
    "GK": 1348956001,
    "DL": 1348758643,
    "DC": 1348756325,
    "DR": 1348760179,
    "WBL": 1350001260,
    "WBR": 1350001266,
    "DM": 1348758883,
    "ML": 1349348467,
    "MC": 1349346149,
    "MR": 1349350003,
    "AML": 1348562284,
    "AMC": 1348562275,
    "AMR": 1348562290,
    "ST": 1348559717,
}

ALL_POS = list(POS_PROPS.keys())
OUTFIELD_POS = [p for p in ALL_POS if p != "GK"]

# --- Position distribution defaults (editable via CLI for RANDOM positions) ---
PRIMARY_DIST_DEFAULT = [15.0, 35.0, 35.0, 15.0]  # GK, DEF, MID, ST
N20_DIST_DEFAULT = [39.0, 18.0, 13.0, 11.0, 8.0, 5.5, 3.6, 1.4, 0.5]  # 1..7, 8-12, 13

# Runtime override (the generator can set these)
PRIMARY_DIST = PRIMARY_DIST_DEFAULT[:]  # type: List[float]
N20_DIST = N20_DIST_DEFAULT[:]          # type: List[float]

# ---- position profile logic (auto distribution) ----
DEF_POS = ["DL", "DC", "DR", "WBL", "WBR"]
MID_POS = ["DM", "ML", "MC", "MR", "AML", "AMC", "AMR"]
ATT_POS = ["ST"]

_POS_GROUP_OF = {p: "DEF" for p in DEF_POS}
_POS_GROUP_OF.update({p: "MID" for p in MID_POS})
_POS_GROUP_OF.update({p: "ATT" for p in ATT_POS})

_POS_ADJ = {
    "DL": ["WBL", "DC", "ML", "DM"],
    "WBL": ["DL", "ML", "AML", "DM"],
    "DC": ["DL", "DR", "DM", "MC"],
    "DR": ["WBR", "DC", "MR", "DM"],
    "WBR": ["DR", "MR", "AMR", "DM"],
    "DM": ["DC", "MC", "ML", "MR"],
    "ML": ["WBL", "MC", "AML", "DM"],
    "MC": ["DM", "ML", "MR", "AMC", "ST"],
    "MR": ["WBR", "MC", "AMR", "DM"],
    "AML": ["ML", "AMC", "ST", "WBL"],
    "AMC": ["MC", "AML", "AMR", "ST", "DM"],
    "AMR": ["MR", "AMC", "ST", "WBR"],
    "ST": ["AMC", "AML", "AMR", "MC"],
}


def _to_pos_float(val: object, default: float = 1.0) -> float:
    try:
        x = float(str(val).strip())
        if x > 0:
            return x
    except Exception:
        pass
    return float(default)


def _pick_weighted(rng: random.Random, items: Sequence[Tuple[str, float]]) -> str:
    tot = sum(w for _, w in items)
    x = rng.random() * tot
    acc = 0.0
    for v, w in items:
        acc += w
        if x <= acc:
            return v
    return items[-1][0]


def _random_primary_position(rng: random.Random) -> str:
    gk, de, mi, st = (PRIMARY_DIST + PRIMARY_DIST_DEFAULT)[:4]
    tot = max(0.000001, (gk + de + mi + st))
    grp = _pick_weighted(rng, [("GK", gk / tot), ("DEF", de / tot), ("MID", mi / tot), ("ATT", st / tot)])
    if grp == "GK":
        return "GK"
    pools = {"DEF": DEF_POS, "MID": MID_POS, "ATT": ATT_POS}
    return rng.choice(pools[grp])


def _sample_outfield_n20(rng: random.Random) -> int:
    vals = (N20_DIST + N20_DIST_DEFAULT)[:9]
    tot = sum(max(0.0, v) for v in vals) or 1.0
    probs = [max(0.0, v) / tot for v in vals]
    r = rng.random()
    cum = 0.0
    for n in range(1, 8):
        cum += probs[n - 1]
        if r < cum:
            return n
    cum += probs[7]
    if r < cum:
        return rng.randint(8, 12)
    return 13


def _extra_pos_weight(primary: str, chosen20: set, cand: str) -> float:
    if cand == "GK":
        return 0.0
    w = 1.0
    if _POS_GROUP_OF.get(cand) == _POS_GROUP_OF.get(primary):
        w += 1.5
    for p in chosen20:
        if cand in _POS_ADJ.get(p, []):
            w += 1.25
    if cand in chosen20:
        w = 0.0
    return w


def _dev_pos_weight(chosen20: set, cand: str) -> float:
    if cand == "GK":
        return 0.0
    near = set()
    for p in chosen20:
        near.update(_POS_ADJ.get(p, []))
    return 5.0 if cand in near else 1.0


def _apply_dev_value(rng: random.Random, mode: str, fixed: int, mn: int, mx: int) -> int:
    mode = (mode or "random").strip().lower()
    if mode == "fixed":
        v = int(fixed)
        return max(2, min(19, v))
    if mode == "range":
        lo = max(2, min(19, int(mn)))
        hi = max(2, min(19, int(mx)))
        if hi < lo:
            lo, hi = hi, lo
        return rng.randint(lo, hi)
    return rng.randint(2, 19)


def _pos_map_auto_random(
    rng: random.Random,
    dev_mode: str,
    dev_value: int,
    dev_min: int,
    dev_max: int,
    auto_dev_chance: float = 0.15,
) -> Dict[str, int]:
    pm: Dict[str, int] = {p: 1 for p in ALL_POS}
    primary = _random_primary_position(rng)
    if primary == "GK":
        pm["GK"] = 20
        return pm
    pm[primary] = 20
    chosen20 = {primary}

    n20 = _sample_outfield_n20(rng)
    for _ in range(max(0, n20 - 1)):
        cands = [p for p in OUTFIELD_POS if p not in chosen20]
        if not cands:
            break
        weights = [_extra_pos_weight(primary, chosen20, c) for c in cands]
        tot = sum(weights) or 1.0
        probs = [w / tot for w in weights]
        r = rng.random()
        acc = 0.0
        pick = cands[-1]
        for c, pr in zip(cands, probs):
            acc += pr
            if r <= acc:
                pick = c
                break
        pm[pick] = 20
        chosen20.add(pick)

    if rng.random() < float(auto_dev_chance):
        devv = _apply_dev_value(rng, dev_mode, dev_value, dev_min, dev_max)
        k = rng.randint(1, 3)
        for _ in range(k):
            cands = [p for p in OUTFIELD_POS if p not in chosen20 and pm.get(p, 1) == 1]
            if not cands:
                break
            weights = [_dev_pos_weight(chosen20, c) for c in cands]
            tot = sum(weights) or 1.0
            probs = [w / tot for w in weights]
            r = rng.random()
            acc = 0.0
            pick = cands[-1]
            for c, pr in zip(cands, probs):
                acc += pr
                if r <= acc:
                    pick = c
                    break
            pm[pick] = devv

    return pm


def _pos_map_advanced(
    rng: random.Random,
    primary: Optional[str],
    extra_20: Optional[List[str]],
    all_outfield_20: bool,
    dev_positions: Optional[List[str]],
    dev_mode: str,
    dev_value: int,
    dev_min: int,
    dev_max: int,
    allow_random_primary: bool,
    auto_dev_chance: float = 0.15,
) -> Dict[str, int]:
    if allow_random_primary and (not primary or str(primary).strip().upper() == "RANDOM"):
        primary = _random_primary_position(rng)

    pm: Dict[str, int] = {p: 1 for p in ALL_POS}

    if not primary:
        return _pos_map_auto_random(rng, dev_mode, dev_value, dev_min, dev_max, auto_dev_chance=auto_dev_chance)

    primary = str(primary).strip().upper()
    if primary not in ALL_POS:
        return _pos_map_auto_random(rng, dev_mode, dev_value, dev_min, dev_max, auto_dev_chance=auto_dev_chance)

    if primary == "GK":
        pm["GK"] = 20
        return pm

    pm[primary] = 20
    chosen20 = {primary}

    if all_outfield_20:
        for p in OUTFIELD_POS:
            pm[p] = 20
            chosen20.add(p)
    else:
        for p in (extra_20 or []):
            pp = str(p).strip().upper()
            if pp in OUTFIELD_POS:
                pm[pp] = 20
                chosen20.add(pp)

    if dev_positions:
        devv = _apply_dev_value(rng, dev_mode, dev_value, dev_min, dev_max)
        for p in dev_positions:
            pp = str(p).strip().upper()
            if pp in OUTFIELD_POS and pm.get(pp, 1) < 20:
                pm[pp] = devv
    else:
        if rng.random() < float(auto_dev_chance):
            pm = _pos_map_auto_random(rng, dev_mode, dev_value, dev_min, dev_max, auto_dev_chance=auto_dev_chance)

    return pm
