#!/usr/bin/env python3
from __future__ import annotations
"""FM26 Players Generator (db changes XML) - stable SHA256 IDs (randomized names across runs, v6.1 foot modes).

Batch:
  python fm26_bulk_youth_generator2.py --master_library master_library.csv --count 10000 --output fm26_players.xml --seed 123

Single:
  python fm26_bulk_youth_generator2.py --master_library master_library.csv --count 1 --output fm26_players.xml --append \
    --dob 2012-12-31 --height 180 --club_dbid 1570 --club_large 6648609375756 --city_dbid 102580 --city_large 440573450358963 \
    --nation_dbid 793 --nation_large 3405909066521 --positions DL,DC --ca_min 120 --ca_max 120 --pa_min 180 --pa_max 180 --seed 123

Positions (new):
  - Primary position is forced to 20.
  - All other positions default to 1.
  - Optional extra 20-rated positions (outfield only) via --pos_20 or --pos_all_outfield_20.
  - Optional development positions (2..19) via --pos_dev (+ mode: random|fixed|range).
  GUI can apply development positions even when random primary is enabled (use --positions RANDOM + --pos_dev ...).
"""

import argparse
import csv
import datetime as dt
import hashlib
import json
import os
import random
import re
import sys
from typing import Dict, List, Optional, Sequence, Tuple
from xml.sax.saxutils import escape as xesc

# ---- FM property numbers (keep stable) ----
CITY_PROPERTY = 1348690537
CLUB_PROPERTY = 1348695145
NATION_PROPERTY = 1349416041
CREATE_PROPERTY = 1094992978

# player/person table attribute records
TBL_PLAYER = 1
# creation record table type
TBL_CREATE = 55

PROP_FIRST_NAME = 1348890209
PROP_SECOND_NAME = 1349742177
PROP_COMMON_NAME = 1348693601
PROP_HEIGHT = 1349018995
PROP_DOB = 1348759394
PROP_NATIONALITY_INFO = 1349415497
PROP_WAGE = 1348695911
PROP_DATE_MOVED_TO_NATION = 1346588266
PROP_DATE_JOINED_CLUB = 1348692580
PROP_DATE_LAST_SIGNED = 1348694884
PROP_CONTRACT_EXPIRES = 1348691320
PROP_SQUAD_STATUS = 1347253105
PROP_CA = 1346584898
PROP_PA = 1347436866
PROP_CURRENT_REP = 1346589264
PROP_HOME_REP = 1346916944
PROP_WORLD_REP = 1347899984
PROP_LEFT_FOOT = 1346661478
PROP_RIGHT_FOOT = 1346663017
PROP_TRANSFER_VALUE = 1348630085

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
PRIMARY_DIST = PRIMARY_DIST_DEFAULT[:]  # runtime override
N20_DIST = N20_DIST_DEFAULT[:]          # runtime override

DEFAULT_VERSION = 3727
DEFAULT_RULE_GROUP_VERSION = 1630
DEFAULT_EDVB = 1
DEFAULT_ORVS = "2600"
DEFAULT_SVVS = "2600"
DEFAULT_NNAT_ODVL = 3285649982205  # safe default seen in samples

INT32_MOD = 2147483646
INT64_MOD = 9223372036854775806

# Per-run namespace salt for generated IDs. Prevents ID reuse across runs when the
# same --seed is reused (attribute RNG remains seeded as before).
ID_NAMESPACE_SALT = ""

def _default_id_registry_path() -> str:
    try:
        base = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base = os.getcwd()
    return os.path.join(base, "fm26_player_generator_id_registry.json")

def _load_id_registry(path: str) -> Dict[str, object]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}
    if not isinstance(data.get("next_run_serial"), int) or int(data.get("next_run_serial", 0)) < 1:
        data["next_run_serial"] = 1
    data.setdefault("version", 1)
    return data

def _save_id_registry(path: str, data: Dict[str, object]) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)

def _reserve_id_namespace(seed: Optional[int], count: int, out_xml: str, registry_path: Optional[str] = None) -> Tuple[str, str]:
    path = registry_path or _default_id_registry_path()
    reg = _load_id_registry(path)
    serial = int(reg.get("next_run_serial", 1))
    reg["next_run_serial"] = serial + 1
    reg["last_run"] = {
        "serial": serial,
        "seed": seed,
        "count": int(count),
        "output": os.path.abspath(out_xml),
    }
    _save_id_registry(path, reg)
    return (f"run{serial}", path)

# ---- stable ids ----
def _sha(seed: int, i: int, label: str) -> int:
    h = hashlib.sha256(f"{seed}|{ID_NAMESPACE_SALT}|{i}|{label}".encode("utf-8")).digest()
    return int.from_bytes(h, "big")


def _id32(seed: int, i: int, label: str) -> int:
    return 1 + (_sha(seed, i, label) % INT32_MOD)


def _id64(seed: int, i: int, label: str) -> int:
    return 1 + (_sha(seed, i, label) % INT64_MOD)


def _uniq(make_id, seed: int, i: int, label: str, used: set, extra_ok=None) -> int:
    bump = 0
    while True:
        lbl = label if bump == 0 else f"{label}|{bump}"
        v = make_id(seed, i, lbl)
        if v in used:
            bump += 1
            continue
        if extra_ok and not extra_ok(v):
            bump += 1
            continue
        used.add(v)
        return v


# ---- csv helpers ----
def _detect_delim(sample: str) -> str:
    return "\t" if sample.count("\t") > sample.count(",") else ","


def _strip_excel(s: str) -> str:
    s = (s or "").strip()
    return s[2:-1] if s.startswith('="') and s.endswith('"') else s


def _to_int(s: str) -> Optional[int]:
    s = _strip_excel(s)
    if not s:
        return None
    if re.fullmatch(r"[0-9]+", s):
        try:
            return int(s)
        except ValueError:
            return None
    return None


def load_master_library(path: str) -> Tuple[List[Tuple[int, int, str]], List[Tuple[int, int, str]], List[Tuple[int, int, str]]]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        head = f.readline()
        if not head:
            raise ValueError("CSV empty")
        delim = _detect_delim(head)
        f.seek(0)

        r = csv.DictReader(f, delimiter=delim)
        clubs, cities, nations = {}, {}, {}

        for row in r:
            d = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}

            kind = (d.get("type") or d.get("kind") or "").strip().lower()
            if kind not in ("club", "city", "nation"):
                if d.get("club_dbid") or d.get("club_large") or d.get("ttea_large") or d.get("ttea_large_text"):
                    kind = "club"
                elif d.get("city_dbid") or d.get("city_large") or d.get("city_large_text"):
                    kind = "city"
                elif (
                    d.get("nation_dbid")
                    or d.get("nation_large")
                    or d.get("nnat")
                    or d.get("nnat_large")
                    or d.get("nnat_large_text")
                ):
                    kind = "nation"
                else:
                    continue

            if kind == "club":
                dbid = _to_int(d.get("club_dbid", ""))
                large = (
                    _to_int(d.get("club_large", ""))
                    or _to_int(d.get("ttea_large", ""))
                    or _to_int(d.get("ttea_large_text", ""))
                    or _to_int(d.get("ttea", ""))
                )
                name = d.get("club_name", "")
                if dbid is None or large is None:
                    continue
                clubs[(dbid, large)] = (dbid, large, name)

            elif kind == "city":
                dbid = _to_int(d.get("city_dbid", ""))
                large = _to_int(d.get("city_large", "")) or _to_int(d.get("city_large_text", ""))
                name = d.get("city_name", "")
                if dbid is None or large is None:
                    continue
                cities[(dbid, large)] = (dbid, large, name)

            else:  # nation
                dbid = _to_int(d.get("nation_dbid", "")) or _to_int(d.get("dbid", ""))
                large = (
                    _to_int(d.get("nation_large", ""))
                    or _to_int(d.get("nnat_large", ""))
                    or _to_int(d.get("nnat_large_text", ""))
                    or _to_int(d.get("nnat", ""))
                )
                name = d.get("nation_name", "")
                if dbid is None or large is None:
                    continue
                nations[(dbid, large)] = (dbid, large, name)

        return list(clubs.values()), list(cities.values()), list(nations.values())


# ---- names ----
def _load_names(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    out = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if not row:
                continue
            v = (row[0] or "").strip()
            if v and v.lower() != "name":
                out.append(v)
    if not out:
        raise ValueError(f"No names loaded from {path}")
    return out


# ---- randomness ----
def _days_in_month(y: int, m: int) -> int:
    if m == 12:
        return (dt.date(y + 1, 1, 1) - dt.date(y, m, 1)).days
    return (dt.date(y, m + 1, 1) - dt.date(y, m, 1)).days


def _random_dob(rng: random.Random, age: int, base_year: int) -> dt.date:
    y = base_year - age
    m = rng.randint(1, 12)
    d = rng.randint(1, _days_in_month(y, m))
    return dt.date(y, m, d)


def _parse_ymd(s: str) -> dt.date:
    m = re.fullmatch(r"(\d{4})-(\d{2})-(\d{2})", (s or "").strip())
    if not m:
        raise ValueError("DOB must be YYYY-MM-DD")
    y, mo, d = map(int, m.groups())
    return dt.date(y, mo, d)


def _random_dob_between(rng: random.Random, start: dt.date, end: dt.date) -> dt.date:
    """Random date between start and end (inclusive)."""
    if end < start:
        raise ValueError("DOB range end must be >= start")
    a = start.toordinal()
    b = end.toordinal()
    return dt.date.fromordinal(rng.randint(a, b))


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
    # Primary role distribution (must be stable):
    #   GK 15% | DEF 35% | MID 35% | ST 15%
    gk, de, mi, st = (PRIMARY_DIST + PRIMARY_DIST_DEFAULT)[:4]
    tot = max(0.000001, (gk+de+mi+st))
    grp = _pick_weighted(rng, [("GK", gk/tot), ("DEF", de/tot), ("MID", mi/tot), ("ATT", st/tot)])
    if grp == "GK":
        return "GK"

    pools = {
        # defenders
        "DEF": ["DL", "DC", "DR", "WBL", "WBR"],
        # midfielders (includes AM lines)
        "MID": ["DM", "ML", "MC", "MR", "AML", "AMC", "AMR"],
        # strikers
        "ATT": ["ST"],
    }
    return rng.choice(pools[grp])


# ---- position profile logic (auto distribution) ----
DEF_POS = ["DL", "DC", "DR", "WBL", "WBR"]
MID_POS = ["DM", "ML", "MC", "MR", "AML", "AMC", "AMR"]
ATT_POS = ["ST"]

_POS_GROUP_OF = {p: "DEF" for p in DEF_POS}
_POS_GROUP_OF.update({p: "MID" for p in MID_POS})
_POS_GROUP_OF.update({p: "ATT" for p in ATT_POS})

# Adjacency bias for "nearby" positions (used when picking multi-position profiles)
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


def _sample_outfield_n20(rng: random.Random) -> int:
    """How many outfield positions should be rated 20.

    Uses N20_DIST (1..7, 8-12 bucket, 13) which defaults to:
      39, 18, 13, 11, 8, 5.5, 3.6, 1.4 (for 8..12), then 0.5 for 13.
    """
    vals = (N20_DIST + N20_DIST_DEFAULT)[:9]
    # Normalize to 1.0
    tot = sum(max(0.0, v) for v in vals) or 1.0
    probs = [max(0.0, v)/tot for v in vals]
    r = rng.random()
    cum = 0.0
    # 1..7
    for n in range(1, 8):
        cum += probs[n-1]
        if r < cum:
            return n
    # 8-12 bucket
    cum += probs[7]
    if r < cum:
        return rng.randint(8, 12)
    # 13 (all outfield)
    return 13

def _extra_pos_weight(primary: str, chosen20: set, cand: str) -> float:
    """Weight for choosing additional 20-rated positions."""
    if cand == "GK":
        return 0.0
    w = 1.0
    # Prefer same broad group as primary
    if _POS_GROUP_OF.get(cand) == _POS_GROUP_OF.get(primary):
        w += 1.5
    # Prefer adjacent positions to anything already 20
    for p in chosen20:
        if cand in _POS_ADJ.get(p, []):
            w += 3.0
            break
    return w


def _dev_pos_weight(chosen20: set, cand: str) -> float:
    """Weight for choosing development (2..19) positions."""
    if cand == "GK":
        return 0.0
    near = set()
    for p in chosen20:
        near.update(_POS_ADJ.get(p, []))
    return 5.0 if cand in near else 1.0


def _pos_map_auto_random(
    rng: random.Random,
    dev_mode: str,
    dev_value: int,
    dev_min: int,
    dev_max: int,
    auto_dev_chance: float = 0.15,
) -> Dict[str, int]:
    """Generate a full position map using the requested global distributions.

    - Primary role: GK 15% | DEF 35% | MID 35% | ST 15%
    - If GK: GK=20 and everything else = 1
    - If outfield:
        * Choose N outfield positions at 20 (N=1..13) using the requested distribution.
        * Optional dev positions (2..19) for 2..12 position players (default 15% chance).
    """
    pm: Dict[str, int] = {p: 1 for p in ALL_POS}

    primary = _random_primary_position(rng)

    if primary == "GK":
        pm["GK"] = 20
        for k in OUTFIELD_POS:
            pm[k] = 1
        return pm

    # outfield primary
    pm["GK"] = 1
    pm[primary] = 20

    n20 = _sample_outfield_n20(rng)

    # 13 outfield positions at 20 (everything except GK)
    if n20 >= len(OUTFIELD_POS):
        for k in OUTFIELD_POS:
            pm[k] = 20
        pm["GK"] = 1
        return pm

    chosen20 = {primary}
    # add extra 20s
    while len(chosen20) < n20:
        candidates = [p for p in OUTFIELD_POS if p not in chosen20]
        pick = _pick_weighted(rng, [(c, _extra_pos_weight(primary, chosen20, c)) for c in candidates])
        chosen20.add(pick)
        pm[pick] = 20

    # Auto dev positions only for multi-position (2..12) profiles
    if 2 <= n20 <= 12 and auto_dev_chance > 0 and rng.random() < auto_dev_chance:
        dev_candidates = [p for p in OUTFIELD_POS if pm.get(p, 1) != 20]
        if dev_candidates:
            # Mostly 1 dev position, sometimes 2, rarely 3
            rr = rng.random()
            if rr < 0.75:
                dev_count = 1
            elif rr < 0.95:
                dev_count = 2
            else:
                dev_count = 3
            dev_count = min(dev_count, len(dev_candidates))

            dev_picks: set = set()
            while len(dev_picks) < dev_count:
                cand = [p for p in dev_candidates if p not in dev_picks]
                pick = _pick_weighted(rng, [(c, _dev_pos_weight(chosen20, c)) for c in cand])
                dev_picks.add(pick)
                pm[pick] = _apply_dev_value(rng, dev_mode, dev_value, dev_min, dev_max)

    return pm


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
    # random
    return rng.randint(2, 19)


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
    """Advanced position assignment.

    Rules:
      - primary is 20
      - everything else starts at 1
      - if primary == GK: everything else forced to 1
      - if outfield primary: GK always 1
      - optional extra 20-rated outfield positions
      - optional dev positions (2..19), but never override a 20

    Also: if *no* manual primary/extra positions are provided, we auto-generate a
    full position profile using the requested global distributions.
    """

    # AUTO profile mode: if no manual primary and no manual extra 20s and not "all outfield 20"
    if not (primary or "").strip() and not all_outfield_20 and not (extra_20 or []):
        auto_dev = 0.0 if (dev_positions or []) else auto_dev_chance
        pm = _pos_map_auto_random(
            rng,
            dev_mode=dev_mode,
            dev_value=dev_value,
            dev_min=dev_min,
            dev_max=dev_max,
            auto_dev_chance=auto_dev,
        )

        # If GK was picked, lock outfield positions to 1 and ignore dev selections.
        if pm.get("GK", 1) == 20:
            return pm

        # Apply any *manual* dev positions on top (never overriding 20s)
        if dev_positions:
            for k in dev_positions:
                kk = (k or "").strip().upper()
                if kk not in OUTFIELD_POS:
                    continue
                if pm.get(kk, 1) == 20:
                    continue
                pm[kk] = _apply_dev_value(rng, dev_mode, dev_value, dev_min, dev_max)

        return pm

    pm: Dict[str, int] = {p: 1 for p in ALL_POS}

    p = (primary or "").strip().upper()
    if not p and allow_random_primary:
        p = _random_primary_position(rng)

    if p and p not in POS_PROPS:
        # invalid primary -> treat as random
        p = _random_primary_position(rng)

    if not p:
        # final fallback
        p = _random_primary_position(rng)

    # GK primary: lock it
    if p == "GK":
        pm["GK"] = 20
        for k in OUTFIELD_POS:
            pm[k] = 1
        return pm

    # outfield primary
    pm["GK"] = 1
    pm[p] = 20

    # optional: all outfield at 20
    if all_outfield_20:
        for k in OUTFIELD_POS:
            pm[k] = 20
    else:
        # optional: extra 20s
        if extra_20:
            for k in extra_20:
                kk = (k or "").strip().upper()
                if kk in OUTFIELD_POS:
                    pm[kk] = 20

    # optional: dev positions (2..19), never override 20s
    if dev_positions:
        for k in dev_positions:
            kk = (k or "").strip().upper()
            if kk not in OUTFIELD_POS:
                continue
            if pm.get(kk, 1) == 20:
                continue
            pm[kk] = _apply_dev_value(rng, dev_mode, dev_value, dev_min, dev_max)

    return pm


def _tv_from_pa(pa: int) -> int:
    """Derive transfer value from PA.

    Range: 100,000 .. 150,000,000 (cap as requested).
    """
    x = max(0, min(200, int(pa)))
    lo = 100_000
    hi = 150_000_000
    return int(lo + ((x / 200.0) ** 3) * (hi - lo))


# ---- xml helpers ----

def _foot(rng: random.Random, feet_mode: str) -> Tuple[int, int]:
    """Return (left_foot, right_foot) 1..20.

    Supported modes:
      - left_only  -> left=20, right=1..5
      - left       -> left=20, right=6..14
      - right_only -> right=20, left=1..5
      - right      -> right=20, left=6..14
      - both       -> left=20, right=20
      - random     -> weighted mix of the above (keeps a realistic spread)

    Notes:
      - Any unknown mode falls back to 'random'
      - Exactly one foot is forced to 20 for left/right variants
    """
    mode = (feet_mode or "random").strip().lower()

    if mode == "random":
        # Weighted spread (sums to 100):
        # left_only 10%, left 30%, right_only 10%, right 30%, both 20%
        r = rng.random()
        if r < 0.10:
            mode = "left_only"
        elif r < 0.40:
            mode = "left"
        elif r < 0.50:
            mode = "right_only"
        elif r < 0.80:
            mode = "right"
        else:
            mode = "both"

    if mode == "both":
        return 20, 20

    if mode == "left_only":
        return 20, rng.randint(1, 5)

    if mode == "right_only":
        return rng.randint(1, 5), 20

    if mode == "right":
        return rng.randint(6, 14), 20

    # default 'left'
    return 20, rng.randint(6, 14)


def _rep_triplet(rng: random.Random, rep_min: int, rep_max: int) -> Tuple[int, int, int]:
    """Return (current, home, world) with current >= home >= world."""
    lo = int(rep_min)
    hi = int(rep_max)
    if hi < lo:
        lo, hi = hi, lo
    lo = max(0, lo)
    hi = min(200, hi)
    current = rng.randint(lo, hi)
    home = rng.randint(lo, current)
    world = rng.randint(lo, home)
    return current, home, world


def _int(i: str, v: int) -> str:
    return f'<integer id="{i}" value="{v}"/>'


def _large(i: str, v: int) -> str:
    return f'<large id="{i}" value="{v}"/>'


def _uns(i: str, v: int) -> str:
    return f'<unsigned id="{i}" value="{v}"/>'


def _str(i: str, s: str) -> str:
    return f'<string id="{i}" value="{xesc(s)}"/>'


def _bool(i: str, v: bool) -> str:
    return f'<boolean id="{i}" value="{"true" if v else "false"}"/>'


def _null(i: str) -> str:
    return f'<null id="{i}"/>'


def _date(i: str, d: dt.date) -> str:
    return f'<date id="{i}" day="{d.day}" month="{d.month}" year="{d.year}" time="0"/>'


def _rec(inner: str, comment: str = "") -> str:
    c = f'<!-- {comment} -->' if comment else ""
    return f"\t\t<record>{c}\n{inner}\t\t</record>\n"


def _attr(person_uid: int, prop: int, newv: str, rid: int, ver: int, extra: str = "", odvl: str = "") -> str:
    s = f"\t\t\t{_int('database_table_type', TBL_PLAYER)}\n"
    s += f"\t\t\t{_large('db_unique_id', person_uid)}\n"
    s += f"\t\t\t{_uns('property', prop)}\n"
    s += f"\t\t\t{newv}\n"
    s += f"\t\t\t{_int('version', ver)}\n"
    s += f"\t\t\t{_int('db_random_id', rid)}\n"
    if extra:
        s += extra
    if odvl:
        s += f"\t\t\t{odvl}\n"
    return s


def _create(create_uid: int, person_uid: int, rid: int, ver: int) -> str:
    inner = f"\t\t\t{_int('database_table_type', TBL_CREATE)}\n"
    inner += f"\t\t\t{_large('db_unique_id', create_uid)}\n"
    inner += f"\t\t\t{_uns('property', CREATE_PROPERTY)}\n"
    inner += "\t\t\t<record id=\"new_value\">\n"
    inner += f"\t\t\t\t{_int('database_table_type', TBL_PLAYER)}\n"
    inner += f"\t\t\t\t{_uns('dcty', 2)}\n"
    inner += f"\t\t\t\t{_large('db_unique_id', person_uid)}\n"
    inner += "\t\t\t</record>\n"
    inner += f"\t\t\t{_int('version', ver)}\n"
    inner += f"\t\t\t{_int('db_random_id', rid)}\n"
    inner += f"\t\t\t{_bool('is_client_field', True)}\n"
    return _rec(inner, "Required per player record")


def _count_existing(xml_path: str) -> int:
    with open(xml_path, "rb") as f:
        data = f.read()
    return data.count(b'<unsigned id="property" value="1094992978"/>')


def _append(existing_xml: str, frag: str, out_xml: str) -> None:
    with open(existing_xml, "rb") as f:
        data = f.read()
    marker = b'<integer id="EDvb"'
    mpos = data.find(marker)
    if mpos == -1:
        raise ValueError("EDvb marker not found (not an FM db changes XML?)")
    insert = data.rfind(b"</list>", 0, mpos)
    if insert == -1:
        raise ValueError("Cannot find db_changes closing </list> before EDvb")
    with open(out_xml, "wb") as f:
        f.write(data[:insert])
        f.write(frag.encode("utf-8"))
        f.write(data[insert:])


def generate_players_xml(
    library_csv: str,
    out_xml: str,
    count: int,
    seed: Optional[int] = None,
    append: bool = False,
    start_index: int = 0,
    age_min: int = 14,
    age_max: int = 16,
    ca_min: int = 20,
    ca_max: int = 160,
    pa_min: int = 80,
    pa_max: int = 200,
    base_year: int = 2026,
    version: int = DEFAULT_VERSION,
    first_names_csv: str = "scottish_male_first_names_2500.csv",
    surnames_csv: str = "scottish_surnames_2500.csv",
    fixed_dob: Optional[dt.date] = None,
    dob_start: Optional[dt.date] = None,
    dob_end: Optional[dt.date] = None,
    fixed_height: Optional[int] = None,
    height_min: int = 150,
    height_max: int = 210,
    fixed_club: Optional[Tuple[int, int]] = None,
    fixed_city: Optional[Tuple[int, int]] = None,
    fixed_nation: Optional[Tuple[int, int]] = None,
    # legacy positions (kept for backwards compatibility)
    fixed_positions: Optional[List[str]] = None,
    # new positions
    pos_primary: Optional[str] = None,
    pos_20: Optional[List[str]] = None,
    pos_all_outfield_20: bool = False,
    pos_dev: Optional[List[str]] = None,
    pos_dev_mode: str = "random",
    pos_dev_value: int = 0,
    pos_dev_min: int = 2,
    pos_dev_max: int = 19,
    feet_mode: str = "random",
    fixed_left_foot: Optional[int] = None,
    fixed_right_foot: Optional[int] = None,
    wage: int = 0,
    wage_min: int = 30,
    wage_max: int = 80,
    rep_current: int = -1,
    rep_home: int = -1,
    rep_world: int = -1,
    rep_min: int = 0,
    rep_max: int = 200,
    transfer_mode: str = "auto",  # auto|fixed|range
    transfer_value: int = 0,
    transfer_min: int = 0,
    transfer_max: int = 0,
    auto_dev_chance: float = 0.15,
    nationality_info_value: int = 85,
    id_registry_path: Optional[str] = None,
    id_registry_mode: str = "auto",  # auto|off
    id_namespace_salt: Optional[str] = None,
) -> None:
    if seed is None:
        seed = int(dt.datetime.utcnow().timestamp())
    if count < 1:
        raise ValueError("count must be >=1")
    if not (0 <= ca_min <= ca_max <= 200):
        raise ValueError("CA must be 0..200")
    if not (0 <= pa_min <= pa_max <= 200):
        raise ValueError("PA must be 0..200")
    if age_max < age_min or age_min < 1:
        raise ValueError("invalid age range")

    # Wage (minimum 30)
    wage_min = max(30, int(wage_min))
    wage_max = max(wage_min, int(wage_max))
    wage = int(wage)

    # Reputation (0..200)
    rep_min = int(rep_min)
    rep_max = int(rep_max)
    rep_current = int(rep_current)
    rep_home = int(rep_home)
    rep_world = int(rep_world)

    # Transfer value
    transfer_mode = (transfer_mode or "auto").lower().strip()
    if transfer_mode not in ("auto", "fixed", "range"):
        raise ValueError("transfer_mode must be auto|fixed|range")
    transfer_value = int(transfer_value)
    transfer_min = int(transfer_min)
    transfer_max = int(transfer_max)
    TV_LO = 100_000
    TV_HI = 2_000_000_000  # allow fixed values above 150m

    if fixed_height is not None:
        if not (150 <= fixed_height <= 210):
            raise ValueError("height must be 150..210")
    else:
        if not (150 <= height_min <= 210 and 150 <= height_max <= 210 and height_min <= height_max):
            raise ValueError("height range must be within 150..210 and min<=max")

    if (dob_start is None) ^ (dob_end is None):
        raise ValueError("DOB range requires both dob_start and dob_end")
    if dob_start is not None and dob_end is not None and dob_end < dob_start:
        raise ValueError("DOB range end must be >= start")

    fm = (feet_mode or "random").strip().lower()
    if fm not in ("random", "left_only", "left", "right_only", "right", "both"):
        raise ValueError("feet_mode must be one of: random, left_only, left, right_only, right, both")
    if (fixed_left_foot is None) ^ (fixed_right_foot is None):
        raise ValueError("If fixing feet, set BOTH fixed_left_foot and fixed_right_foot")
    if fixed_left_foot is not None and not (1 <= fixed_left_foot <= 20 and 1 <= fixed_right_foot <= 20):
        raise ValueError("Fixed feet values must be 1..20")

    # new positions validation
    if pos_primary is not None and pos_primary.strip():
        pp = pos_primary.strip().upper()
        if pp not in POS_PROPS:
            raise ValueError(f"Unknown pos_primary: {pp}. Allowed: {', '.join(ALL_POS)}")

    if pos_20:
        for p in pos_20:
            if p.strip().upper() not in POS_PROPS:
                raise ValueError(f"Unknown pos_20 position: {p}")

    if pos_dev:
        for p in pos_dev:
            if p.strip().upper() not in POS_PROPS:
                raise ValueError(f"Unknown pos_dev position: {p}")

    if pos_dev_mode not in ("random", "fixed", "range"):
        raise ValueError("pos_dev_mode must be random|fixed|range")

    clubs, cities, nations = load_master_library(library_csv)
    if not clubs:
        raise ValueError("No clubs loaded from master library")
    if not cities:
        raise ValueError("No cities loaded from master library")
    if not nations and fixed_nation is None:
        raise ValueError("No nations loaded (add at least Scotland)")

    first = _load_names(first_names_csv)
    sur = _load_names(surnames_csv)

    if id_registry_mode not in ("auto", "off"):
        raise ValueError("id_registry_mode must be auto|off")
    global ID_NAMESPACE_SALT
    if id_namespace_salt is not None and str(id_namespace_salt).strip():
        ID_NAMESPACE_SALT = str(id_namespace_salt).strip()
    elif id_registry_mode == "auto":
        ID_NAMESPACE_SALT, _id_reg_path = _reserve_id_namespace(seed, count, out_xml, id_registry_path)
        print(f"[INFO] ID namespace: {ID_NAMESPACE_SALT} (registry: {_id_reg_path})", file=sys.stderr)
    else:
        ID_NAMESPACE_SALT = ""

    rng = random.Random(seed)
    # Name RNG is intentionally non-deterministic so repeated runs with the same --seed
    # (used for stable IDs/output reproducibility) do not always produce the same player name.
    # This keeps IDs deterministic while making names vary across runs.
    name_rng = random.SystemRandom()

    existing = _count_existing(out_xml) if append and os.path.exists(out_xml) else 0

    used32 = set()
    used64 = set()
    used_create = set()
    used_low32 = set()

    def person_ok(v: int) -> bool:
        low = v & 0xFFFFFFFF
        if low >= 2147483648:
            return False
        if low in used_low32:
            return False
        used_low32.add(low)
        return True

    frags: List[str] = []
    lang_extra = '\t\t\t<string id="odvl" value=""/>\n\t\t\t<boolean id="is_language_field" value="true"/>\n'
    odvl0 = _int("odvl", 0)
    odvl_date = _date("odvl", dt.date(1900, 1, 1))

    # decide whether to use advanced position logic
    use_advanced_pos = any(
        [
            (pos_primary is not None and pos_primary.strip()),
            bool(pos_20),
            bool(pos_all_outfield_20),
            bool(pos_dev),
        ]
    )

    for idx in range(count):
        i = start_index + existing + idx

        create_uid = _uniq(_id64, seed, i, "create_uid", used_create)
        person_uid = _uniq(_id64, seed, i, "person_uid", used64, extra_ok=person_ok)

        rid_create = _uniq(_id32, seed, i, "rid|create", used32)
        frags.append(_create(create_uid, person_uid, rid_create, version))

        fn = name_rng.choice(first)
        sn = name_rng.choice(sur)
        cn = f"{fn} {sn}"
        height = fixed_height if fixed_height is not None else rng.randint(height_min, height_max)
        if fixed_dob is not None:
            dob = fixed_dob
        elif (dob_start is not None and dob_end is not None):
            dob = _random_dob_between(rng, dob_start, dob_end)
        else:
            dob = _random_dob(rng, rng.randint(age_min, age_max), base_year)

        ca = rng.randint(ca_min, ca_max)
        pa = rng.randint(pa_min, pa_max)
        if pa < ca:
            pa = ca

        club_dbid, club_large = fixed_club if fixed_club else (lambda x: (x[0], x[1]))(rng.choice(clubs))
        city_dbid, city_large = fixed_city if fixed_city else (lambda x: (x[0], x[1]))(rng.choice(cities))

        if fixed_nation:
            nation_dbid, nation_large = fixed_nation
        else:
            n = rng.choice(nations)
            nation_dbid, nation_large = n[0], n[1]

        # positions
        if use_advanced_pos:
            # if legacy --positions was provided as RANDOM, we still want a random primary.
            allow_random_primary = True
            primary = pos_primary
            extra_20 = pos_20 or []
            dev = pos_dev or []
            pos_map = _pos_map_advanced(
                rng,
                primary=primary,
                extra_20=extra_20,
                all_outfield_20=bool(pos_all_outfield_20),
                dev_positions=dev,
                dev_mode=pos_dev_mode,
                dev_value=pos_dev_value,
                dev_min=pos_dev_min,
                dev_max=pos_dev_max,
                allow_random_primary=allow_random_primary,
                auto_dev_chance=auto_dev_chance,
            )
        else:
            # legacy behaviour
            sel = [p for p in (fixed_positions or []) if p in POS_PROPS]

            if not sel:
                # New: auto-distribution position profiles (primary role + multi-position + optional dev)
                pos_map = _pos_map_auto_random(
                    rng,
                    dev_mode=pos_dev_mode,
                    dev_value=pos_dev_value,
                    dev_min=pos_dev_min,
                    dev_max=pos_dev_max,
                    auto_dev_chance=auto_dev_chance,
                )
            else:
                # Kept for backwards compatibility with explicit legacy --positions lists
                if "GK" in sel:
                    pos_map = {p: 1 for p in ALL_POS}
                    pos_map["GK"] = 20
                else:
                    pos_map = {p: 1 for p in ALL_POS}
                    pos_map["GK"] = 1
                    for pp in sel:
                        if pp in POS_PROPS and pp != "GK":
                            pos_map[pp] = 20
        if fixed_left_foot is not None or fixed_right_foot is not None:
            # If only one override is supplied, mirror it to the other.
            if fixed_left_foot is None:
                fixed_left_foot = fixed_right_foot
            if fixed_right_foot is None:
                fixed_right_foot = fixed_left_foot
            left = int(max(1, min(20, fixed_left_foot)))
            right = int(max(1, min(20, fixed_right_foot)))
        else:
            left, right = _foot(rng, feet_mode)

        # wage (minimum 30)
        wage_val = max(30, wage) if wage > 0 else rng.randint(wage_min, wage_max)

        # reputation (strict current > home > world)
        if (rep_current >= 0) or (rep_home >= 0) or (rep_world >= 0):
            cur = rep_current if rep_current >= 0 else rep_max
            home = rep_home if rep_home >= 0 else max(rep_min, cur - 1)
            world = rep_world if rep_world >= 0 else max(rep_min, home - 1)
            cur = max(0, min(200, cur))
            home = max(0, min(200, home))
            world = max(0, min(200, world))
            if home >= cur:
                home = max(0, cur - 1)
            if world >= home:
                world = max(0, home - 1)
            rep_cur, rep_home_v, rep_world_v = cur, home, world
        else:
            rep_cur, rep_home_v, rep_world_v = _rep_triplet(rng, rep_min, rep_max)

        # transfer value
        if transfer_mode == "auto":
            tv = _tv_from_pa(pa)
        elif transfer_mode == "fixed":
            tv = transfer_value
        else:
            lo = transfer_min if transfer_min > 0 else TV_LO
            hi = transfer_max if transfer_max > 0 else TV_HI
            if hi < lo:
                lo, hi = hi, lo
            tv = rng.randint(lo, hi)
        tv = max(TV_LO, min(TV_HI, int(tv)))

        joined = dt.date(base_year, 7, 1)
        expires = dt.date(base_year + 3, 6, 30)

        def rid(lbl: str) -> int:
            return _uniq(_id32, seed, i, lbl, used32)

        # string fields (with language flag)
        frags.append(_rec(_attr(person_uid, PROP_FIRST_NAME, _str("new_value", fn), rid("rid|fn"), version, extra=lang_extra), "First Name"))
        frags.append(_rec(_attr(person_uid, PROP_SECOND_NAME, _str("new_value", sn), rid("rid|sn"), version, extra=lang_extra), "Second Name"))
        frags.append(_rec(_attr(person_uid, PROP_COMMON_NAME, _str("new_value", cn), rid("rid|cn"), version, extra=lang_extra), "Common Name"))

        # scalar ints/dates
        frags.append(_rec(_attr(person_uid, PROP_HEIGHT, _int("new_value", int(height)), rid("rid|h"), version, odvl=odvl0), "Height"))
        frags.append(_rec(_attr(person_uid, PROP_DOB, _date("new_value", dob), rid("rid|dob"), version, odvl=odvl_date), "DOB"))

        # city record
        newv = (
            '<record id="new_value">\n'
            + f'\t\t\t\t{_large("city", city_large)}\n'
            + f'\t\t\t\t{_int("DBID", city_dbid)}\n'
            + "\t\t\t</record>"
        )
        frags.append(_rec(_attr(person_uid, CITY_PROPERTY, newv, rid("rid|city"), version, odvl=_null("odvl")), "City of birth"))

        # nation record (+ odvl record)
        newv = (
            '<record id="new_value">\n'
            + f'\t\t\t\t{_large("Nnat", nation_large)}\n'
            + f'\t\t\t\t{_int("DBID", nation_dbid)}\n'
            + "\t\t\t</record>"
        )
        odvl = '<record id="odvl">\n' + f'\t\t\t\t{_large("Nnat", DEFAULT_NNAT_ODVL)}\n' + "\t\t\t</record>"
        frags.append(_rec(_attr(person_uid, NATION_PROPERTY, newv, rid("rid|nation"), version, odvl=odvl), "Nation"))

        # nationality info
        frags.append(_rec(_attr(person_uid, PROP_NATIONALITY_INFO, _int("new_value", int(nationality_info_value)), rid("rid|ninfo"), version, odvl=odvl0), "Nationality Info"))

        # club record
        newv = (
            '<record id="new_value">\n'
            + f'\t\t\t\t{_large("Ttea", club_large)}\n'
            + f'\t\t\t\t{_int("DBID", club_dbid)}\n'
            + "\t\t\t</record>"
        )
        frags.append(_rec(_attr(person_uid, CLUB_PROPERTY, newv, rid("rid|club"), version, odvl=_null("odvl")), "Club"))

        # other ints/dates
        frags.append(_rec(_attr(person_uid, PROP_WAGE, _int("new_value", wage_val), rid("rid|wage"), version, odvl=odvl0), "Wage"))
        frags.append(_rec(_attr(person_uid, PROP_DATE_MOVED_TO_NATION, _date("new_value", dob), rid("rid|moved"), version, odvl=odvl_date), "Moved to nation"))
        frags.append(_rec(_attr(person_uid, PROP_DATE_JOINED_CLUB, _date("new_value", joined), rid("rid|joined"), version, odvl=odvl_date), "Joined club"))
        frags.append(_rec(_attr(person_uid, PROP_DATE_LAST_SIGNED, _date("new_value", joined), rid("rid|signed"), version, odvl=odvl_date), "Last signed"))
        frags.append(_rec(_attr(person_uid, PROP_CONTRACT_EXPIRES, _date("new_value", expires), rid("rid|expires"), version, odvl=odvl_date), "Contract expires"))
        frags.append(_rec(_attr(person_uid, PROP_SQUAD_STATUS, _int("new_value", 9), rid("rid|squad"), version, odvl=_null("odvl")), "Squad status"))
        frags.append(_rec(_attr(person_uid, PROP_CA, _int("new_value", ca), rid("rid|ca"), version, odvl=odvl0), "CA"))
        frags.append(_rec(_attr(person_uid, PROP_PA, _int("new_value", pa), rid("rid|pa"), version, odvl=odvl0), "PA"))
        frags.append(_rec(_attr(person_uid, PROP_CURRENT_REP, _int("new_value", rep_cur), rid("rid|rep"), version, odvl=odvl0), "Current rep"))
        frags.append(_rec(_attr(person_uid, PROP_HOME_REP, _int("new_value", rep_home_v), rid("rid|rep_home"), version, odvl=odvl0), "Home rep"))
        frags.append(_rec(_attr(person_uid, PROP_WORLD_REP, _int("new_value", rep_world_v), rid("rid|rep_world"), version, odvl=odvl0), "World rep"))
        frags.append(_rec(_attr(person_uid, PROP_LEFT_FOOT, _str("new_value", str(left)), rid("rid|lf"), version, odvl=odvl0), "Left foot"))
        frags.append(_rec(_attr(person_uid, PROP_RIGHT_FOOT, _str("new_value", str(right)), rid("rid|rf"), version, odvl=odvl0), "Right foot"))
        frags.append(_rec(_attr(person_uid, PROP_TRANSFER_VALUE, _int("new_value", tv), rid("rid|tv"), version, odvl=odvl0), "Transfer value"))

        # positions output
        for code in ALL_POS:
            v = pos_map.get(code, 1)
            frags.append(_rec(_attr(person_uid, POS_PROPS[code], _int("new_value", v), rid(f"rid|pos|{code}"), version), code))

    frag = "".join(frags)

    if append and os.path.exists(out_xml):
        tmp = out_xml + ".tmp"
        _append(out_xml, frag, tmp)
        os.replace(tmp, out_xml)
    else:
        with open(out_xml, "w", encoding="utf-8", newline="\n") as f:
            f.write("<record>\n\t<list id=\"verf\"/>\n\t<list id=\"db_changes\">\n")
            f.write(frag)
            f.write("\t</list>\n")
            f.write(f'\t<integer id="EDvb" value="{DEFAULT_EDVB}"/>\n\t<string id="EDfb" value=""/>\n')
            f.write(f'\t<integer id="version" value="{version}"/>\n\t<integer id="rule_group_version" value="{DEFAULT_RULE_GROUP_VERSION}"/>\n')
            f.write('\t<boolean id="beta" value="false"/>\n')
            f.write(f'\t<string id="orvs" value="{DEFAULT_ORVS}"/>\n\t<string id="svvs" value="{DEFAULT_SVVS}"/>\n</record>\n')


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--master_library", "--library", dest="library_csv", required=True)
    ap.add_argument("--count", type=int, required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--append", action="store_true")
    ap.add_argument("--start_index", type=int, default=0)
    ap.add_argument("--age_min", type=int, default=14)
    ap.add_argument("--age_max", type=int, default=16)
    ap.add_argument("--ca_min", type=int, default=20)
    ap.add_argument("--ca_max", type=int, default=160)
    ap.add_argument("--pa_min", type=int, default=80)
    ap.add_argument("--pa_max", type=int, default=200)
    ap.add_argument("--base_year", type=int, default=2026)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--id_registry_mode", choices=["auto", "off"], default="auto")
    ap.add_argument("--id_registry_path", default=None)
    ap.add_argument("--id_namespace_salt", default=None)
    ap.add_argument("--version", type=int, default=DEFAULT_VERSION)

    ap.add_argument("--dob", default="")
    ap.add_argument("--dob_start", default="")
    ap.add_argument("--dob_end", default="")

    ap.add_argument("--height", type=int, default=0)
    ap.add_argument("--height_min", type=int, default=150)
    ap.add_argument("--height_max", type=int, default=210)

    ap.add_argument("--feet", default="random", choices=["random", "left_only", "left", "right_only", "right", "both"])

    # Wage / Reputation / Transfer value
    ap.add_argument("--wage", type=int, default=0)
    ap.add_argument("--wage_min", type=int, default=30)
    ap.add_argument("--wage_max", type=int, default=80)

    ap.add_argument("--rep_current", type=int, default=-1)
    ap.add_argument("--rep_home", type=int, default=-1)
    ap.add_argument("--rep_world", type=int, default=-1)
    ap.add_argument("--rep_min", type=int, default=0)
    ap.add_argument("--rep_max", type=int, default=200)

    ap.add_argument("--transfer_mode", default="auto", choices=["auto", "fixed", "range"])
    ap.add_argument("--transfer_value", type=int, default=0)
    ap.add_argument("--transfer_min", type=int, default=0)
    ap.add_argument("--transfer_max", type=int, default=0)

    ap.add_argument("--left_foot", type=int, default=0)
    ap.add_argument("--right_foot", type=int, default=0)

    # fixed club/city/nation
    ap.add_argument("--club_dbid", type=int, default=0)
    ap.add_argument("--club_large", type=int, default=0)
    ap.add_argument("--city_dbid", type=int, default=0)
    ap.add_argument("--city_large", type=int, default=0)
    ap.add_argument("--nation_dbid", type=int, default=0)
    ap.add_argument("--nation_large", type=int, default=0)

    # legacy positions (still supported)
    ap.add_argument("--positions", default="")

    # new positions
    ap.add_argument("--pos_primary", default="")
    ap.add_argument("--pos_20", default="")
    ap.add_argument("--pos_all_outfield_20", action="store_true")
    ap.add_argument("--pos_dev", default="")
    ap.add_argument("--pos_dev_mode", default="random", choices=["random", "fixed", "range"])
    ap.add_argument("--pos_dev_value", type=int, default=0)
    ap.add_argument("--pos_dev_min", type=int, default=2)
    ap.add_argument("--pos_dev_max", type=int, default=19)

    ap.add_argument("--auto_dev_chance", type=float, default=0.15)
    ap.add_argument("--pos_primary_dist", default="15,35,35,15")
    ap.add_argument("--pos_n20_dist", default="39,18,13,11,8,5.5,3.6,1.4,0.5")

    ap.add_argument("--nationality_info_value", type=int, default=85)
    ap.add_argument("--first_names", default="scottish_male_first_names_2500.csv")
    ap.add_argument("--surnames", default="scottish_surnames_2500.csv")

    args = ap.parse_args(argv)
# --- parse editable position distributions (used only for RANDOM position profiles) ---
    def _parse_dist_list(s: str, expected: int) -> List[float]:
        parts = [p.strip() for p in (s or "").split(",") if p.strip() != ""]
        if len(parts) != expected:
            raise ValueError(f"Expected {expected} comma-separated values, got {len(parts)} in: {s!r}")
        out: List[float] = []
        for p in parts:
            out.append(float(p))
        return out

    try:
        pd = _parse_dist_list(args.pos_primary_dist, 4)
        nd = _parse_dist_list(args.pos_n20_dist, 9)
        # only accept if they roughly total 100; we'll normalize anyway
        if abs(sum(pd) - 100.0) > 0.001:
            print(f"[WARN] --pos_primary_dist totals {sum(pd):.3f} (expected 100). Normalizing.", file=sys.stderr)
        if abs(sum(nd) - 100.0) > 0.001:
            print(f"[WARN] --pos_n20_dist totals {sum(nd):.3f} (expected 100). Normalizing.", file=sys.stderr)
        global PRIMARY_DIST, N20_DIST
        PRIMARY_DIST = pd
        N20_DIST = nd
    except Exception as e:
        print(f"[FAIL] Invalid distribution arguments: {e}", file=sys.stderr)
        return 2

    # --- auto dev chance: accept 0-1 or 0-100 ---
    auto_dev_chance = float(args.auto_dev_chance)
    if auto_dev_chance > 1.0:
        auto_dev_chance = auto_dev_chance / 100.0
    auto_dev_chance = max(0.0, min(1.0, auto_dev_chance))


    if args.pa_min > 200 or args.pa_max > 200:
        print("[FAIL] PA must be within 0..200 (you passed >200).", file=sys.stderr)
        return 2
    if args.ca_min > 200 or args.ca_max > 200:
        print("[FAIL] CA must be within 0..200.", file=sys.stderr)
        return 2

    fixed_dob = _parse_ymd(args.dob) if args.dob else None
    dob_start = _parse_ymd(args.dob_start) if args.dob_start else None
    dob_end = _parse_ymd(args.dob_end) if args.dob_end else None

    fixed_height = args.height if args.height else None
    height_min = int(args.height_min)
    height_max = int(args.height_max)

    fixed_club = (args.club_dbid, args.club_large) if (args.club_dbid and args.club_large) else None
    fixed_city = (args.city_dbid, args.city_large) if (args.city_dbid and args.city_large) else None
    fixed_nation = (args.nation_dbid, args.nation_large) if (args.nation_dbid and args.nation_large) else None

    fixed_left_foot = args.left_foot if args.left_foot else None
    fixed_right_foot = args.right_foot if args.right_foot else None
    feet_mode = args.feet

    # legacy positions
    fixed_positions = None
    if args.positions:
        pos = [p.strip().upper() for p in args.positions.split(",") if p.strip()]
        if len(pos) == 1 and pos[0] == "RANDOM":
            fixed_positions = []
        else:
            for p in pos:
                if p not in POS_PROPS:
                    print(f"[FAIL] Unknown position: {p}. Allowed: {', '.join(ALL_POS)} or RANDOM", file=sys.stderr)
                    return 2
            fixed_positions = pos

    # new positions
    pos_primary = args.pos_primary.strip().upper() if args.pos_primary.strip() else None

    pos_20 = [p.strip().upper() for p in args.pos_20.split(",") if p.strip()] if args.pos_20.strip() else None
    pos_dev = [p.strip().upper() for p in args.pos_dev.split(",") if p.strip()] if args.pos_dev.strip() else None

    try:
        generate_players_xml(
            library_csv=args.library_csv,
            out_xml=args.output,
            count=args.count,
            seed=args.seed,
            append=args.append,
            start_index=args.start_index,
            age_min=args.age_min,
            age_max=args.age_max,
            ca_min=args.ca_min,
            ca_max=args.ca_max,
            pa_min=args.pa_min,
            pa_max=args.pa_max,
            base_year=args.base_year,
            version=args.version,
            first_names_csv=args.first_names,
            surnames_csv=args.surnames,
            fixed_dob=fixed_dob,
            dob_start=dob_start,
            dob_end=dob_end,
            fixed_height=fixed_height,
            height_min=height_min,
            height_max=height_max,
            fixed_club=fixed_club,
            fixed_city=fixed_city,
            fixed_nation=fixed_nation,
            fixed_positions=fixed_positions,
            pos_primary=pos_primary,
            pos_20=pos_20,
            pos_all_outfield_20=bool(args.pos_all_outfield_20),
            pos_dev=pos_dev,
            pos_dev_mode=args.pos_dev_mode,
            pos_dev_value=args.pos_dev_value,
            pos_dev_min=args.pos_dev_min,
            pos_dev_max=args.pos_dev_max,
            feet_mode=feet_mode,
            fixed_left_foot=fixed_left_foot,
            fixed_right_foot=fixed_right_foot,
            wage=args.wage,
            wage_min=args.wage_min,
            wage_max=args.wage_max,
            rep_current=args.rep_current,
            rep_home=args.rep_home,
            rep_world=args.rep_world,
            rep_min=args.rep_min,
            rep_max=args.rep_max,
            transfer_mode=args.transfer_mode,
            transfer_value=args.transfer_value,
            transfer_min=args.transfer_min,
            transfer_max=args.transfer_max,
            nationality_info_value=args.nationality_info_value,
            id_registry_path=args.id_registry_path,
            id_registry_mode=args.id_registry_mode,
            id_namespace_salt=args.id_namespace_salt,
        )
    except Exception as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        return 1

    print(f"[OK] Wrote: {args.output} (count={args.count}, append={args.append})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
