#!/usr/bin/env python3
from __future__ import annotations
"""FM26 Players Generator (db changes XML) - stable SHA256 IDs (randomized names across runs, v6.1 foot modes + weighted/frequency names).

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
PROP_FULL_NAME = 1348889710
PROP_PERSON_TYPE = 1349810544
PROP_GENDER = 1349084773
PROP_ETHNICITY = 1348826216
PROP_HAIR_COLOUR = 1349018476
PROP_HAIR_LENGTH = 1349020782
PROP_SKIN_TONE = 1349741428
PROP_BODY_TYPE = 1348625524
PROP_HEIGHT = 1349018995
PROP_DOB = 1348759394
PROP_NATIONALITY_INFO = 1349415497
PROP_DECLARED_FOR_YOUTH_NATION = 1349411961
PROP_INTERNATIONAL_RETIREMENT = 1349675364
PROP_INTERNATIONAL_RETIREMENT_DATE = 1349087844
PROP_INTERNATIONAL_APPS = 1349083504
PROP_INTERNATIONAL_GOALS = 1349085036
PROP_U21_INTERNATIONAL_APPS = 1349871969
PROP_U21_INTERNATIONAL_GOALS = 1349871975
PROP_INTERNATIONAL_DEBUT_DATE = 1349084260
PROP_INTERNATIONAL_DEBUT_AGAINST = 1346978927
PROP_U21_INTERNATIONAL_DEBUT_DATE = 1349085028
PROP_U21_INTERNATIONAL_DEBUT_AGAINST = 1346979695
PROP_RETIRING_AFTER_SPELL_CURRENT_CLUB = 1349741682
PROP_WAGE = 1348695911
PROP_DATE_MOVED_TO_NATION = 1346588266
PROP_SECOND_NATIONS = 1347310195

# Nationality Info (FM enum) mappings (ordered to match FM editor dropdown)
NATIONALITY_INFO_ORDER_VALUES = [0, 85, 84, 83, 80, 86, 81, 87, 88, 82, 89, 90]
NATIONALITY_INFO_VALUE_TO_NAME: Dict[int, str] = {
    0: "No info",
    85: "Born In Nation",
    84: "Relative Born In Nation",
    83: "Declared For Nation",
    80: "Eligible For Nation",
    86: "Not Eligible For Nation",
    81: "Has Played For Nation",
    87: "Gained Citizenship Through Relative",
    88: "Gained Citizenship But Not Eligible For Nation Yet",
    82: "Gained Citizenship But Treated As Foreign",
    89: "Gained Citizenship And Declared For Nation",
    90: "Gained Citizenship Through Relative But Not Eligible For Nation Yet",
}

def _norm_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").strip().lower())

NATIONALITY_INFO_NAME_TO_VALUE: Dict[str, int] = {}
for _v, _name in NATIONALITY_INFO_VALUE_TO_NAME.items():
    NATIONALITY_INFO_NAME_TO_VALUE[_norm_key(_name)] = _v
# Helpful aliases
NATIONALITY_INFO_NAME_TO_VALUE.update({
    _norm_key("none"): 0,
    _norm_key("noinfo"): 0,
    _norm_key("born"): 85,
    _norm_key("relativeborn"): 84,
    _norm_key("declared"): 83,
    _norm_key("eligible"): 80,
    _norm_key("noteligible"): 86,
    _norm_key("played"): 81,
    _norm_key("gainedcitizenshipthroughrelative"): 87,
    _norm_key("gainedcitizenshipnoteligible"): 88,
    _norm_key("treatedasforeign"): 82,
    _norm_key("gainedcitizenshipdeclared"): 89,
    _norm_key("relativecitizenshipnoteligible"): 90,
    _norm_key("born in nation"): 85,
    _norm_key("borninnation"): 85,
    _norm_key("relative born in nation"): 84,
    _norm_key("declared for nation"): 83,
    _norm_key("not eligible"): 86,
    _norm_key("treated as foreign"): 82,
    _norm_key("gained citizenship through relative"): 87,
    _norm_key("gained citizenship not eligible"): 88,
    _norm_key("gained citizenship declared"): 89,
    _norm_key("relative citizenship not eligible"): 90,
})

def resolve_nationality_info(value: Optional[int] = None, name: Optional[str] = None) -> int:
    if name is not None and str(name).strip() != "":
        raw = str(name).strip()
        if re.fullmatch(r"-?\d+", raw):
            return int(raw)
        k = _norm_key(raw)
        if k in NATIONALITY_INFO_NAME_TO_VALUE:
            return int(NATIONALITY_INFO_NAME_TO_VALUE[k])
        allowed = ", ".join([f"{v}={NATIONALITY_INFO_VALUE_TO_NAME[v]}" for v in NATIONALITY_INFO_ORDER_VALUES])
        raise ValueError(f"Unknown nationality info name: {raw!r}. Allowed: {allowed}")
    if value is None:
        return 85
    return int(value)

def nationality_info_mapping_lines() -> List[str]:
    return [f"{v} = {NATIONALITY_INFO_VALUE_TO_NAME[v]}" for v in NATIONALITY_INFO_ORDER_VALUES]


def _norm_name_key(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (s or "").strip().lower())


_SECOND_NATION_NAME_ALIASES: Dict[str, str] = {
    _norm_name_key("argentia"): _norm_name_key("argentina"),  # common typo
}


def _build_nation_lookup(nations: List[Tuple[int, int, str]]) -> Dict[str, Tuple[int, int]]:
    out: Dict[str, Tuple[int, int]] = {}
    for dbid, large, name in (nations or []):
        k = _norm_name_key(name)
        if k:
            out[k] = (int(dbid), int(large))
    return out


def _fmdata_candidate_paths(path_value: Optional[str]) -> List[str]:
    p = (path_value or "").strip() if path_value is not None else ""
    if not p:
        return []
    cands: List[str] = []
    def _add(v: str) -> None:
        if v and v not in cands:
            cands.append(v)
    _add(p)
    if not os.path.isabs(p):
        _add(os.path.abspath(p))
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isabs(p):
            _add(os.path.join(script_dir, p))
            _add(os.path.join(script_dir, "fmdata", p))
        else:
            bn = os.path.basename(p)
            _add(os.path.join(script_dir, bn))
            _add(os.path.join(script_dir, "fmdata", bn))
    except Exception:
        pass
    return cands

def _resolve_existing_data_path(path_value: str, *, kind: str = "file") -> str:
    for cand in _fmdata_candidate_paths(path_value):
        if os.path.exists(cand):
            return cand
    return path_value

def _resolve_output_xml_path(path_value: str) -> str:
    p = (path_value or "").strip()
    if not p:
        return p
    if os.path.isabs(p):
        outp = p
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        fmdata_dir = os.path.join(script_dir, "fmdata")
        try:
            os.makedirs(fmdata_dir, exist_ok=True)
        except Exception:
            pass
        outp = os.path.join(fmdata_dir, p)
    try:
        parent = os.path.dirname(outp)
        if parent:
            os.makedirs(parent, exist_ok=True)
    except Exception:
        pass
    return outp


def _resolve_nation_from_lookup(name: str, nation_lookup: Dict[str, Tuple[int, int]]) -> Tuple[int, int]:
    key = _norm_name_key(name)
    key = _SECOND_NATION_NAME_ALIASES.get(key, key)
    hit = nation_lookup.get(key)
    if not hit:
        raise ValueError(f"Second nation not found in master library: {name}")
    return hit



_AUTO_INTL = object()

def _norm_omit_fields(values: Optional[Sequence[str]]) -> set[str]:
    out: set[str] = set()
    if not values:
        return out
    for v in values:
        if v is None:
            continue
        s = str(v).strip().lower().replace(" ", "_").replace("-", "_")
        if s:
            out.add(s)
    return out

def _intl_strength_factor(nation_name: Optional[str]) -> float:
    n = (nation_name or "").strip().lower()
    if not n:
        return 0.50
    strong = {"argentina","brazil","england","france","germany","spain","italy","portugal","netherlands","belgium","croatia","uruguay","colombia","denmark"}
    mid = {"scotland","wales","ireland","northern ireland","norway","sweden","switzerland","austria","poland","serbia","turkiye","turkey","czech republic","czechia","ukraine","morocco","senegal","japan","south korea","mexico","usa","united states"}
    low = {"andorra","san marino","gibraltar","faroe islands","malta","liechtenstein","luxembourg"}
    if n in strong: return 0.95
    if n in mid: return 0.65
    if n in low: return 0.25
    return 0.50

def _weighted_randint(rng: random.Random, lo: int, hi: int, bias: float = 0.5) -> int:
    lo = int(lo); hi = int(hi)
    if hi <= lo:
        return lo
    bias = max(0.05, min(0.95, float(bias)))
    x = rng.random() ** (1.75 - (bias * 1.5))
    return lo + int(round(x * (hi - lo)))

def _estimate_international_stats(rng: random.Random, *, age: int, pa: int, nation_name: Optional[str], max_caps: int, max_goals: int, youth: bool = False) -> Tuple[int, int]:
    age = max(14, min(50, int(age))); pa = max(1, min(200, int(pa)))
    strength = _intl_strength_factor(nation_name)
    pa_factor = max(0.0, min(1.0, (pa - 70) / 120.0))
    if youth:
        if age < 16: return (0, 0)
        years = max(0.0, min(7.0, age - 15))
        games_per_year = 3.0 + (6.0 * strength) + (4.0 * pa_factor)
        cap_ceiling = int(min(max_caps, max(0, round(years * games_per_year))))
        play_prob = max(0.0, min(0.98, 0.10 + (0.60 * pa_factor) + (0.20 * strength) + (0.03 * min(years, 6))))
    else:
        if age < 16: return (0, 0)
        years = max(0.0, age - 17)
        games_per_year = 2.0 + (7.0 * strength) + (4.5 * pa_factor)
        cap_ceiling = int(min(max_caps, max(0, round(years * games_per_year))))
        age_maturity = max(0.0, min(1.0, (age - 18) / 12.0))
        play_prob = max(0.0, min(0.995, 0.03 + (0.55 * pa_factor) + (0.22 * strength) + (0.20 * age_maturity)))
    if cap_ceiling <= 0 or rng.random() > play_prob:
        return (0, 0)
    caps = _weighted_randint(rng, 1, cap_ceiling, bias=(0.25 + 0.60 * pa_factor))
    goal_rate = (0.01 + 0.10 * pa_factor + 0.03 * strength)
    goal_rate *= rng.uniform(0.1, 0.6) if rng.random() < 0.55 else rng.uniform(0.6, 1.4)
    goals_ceiling = min(max_goals, caps, int(round(caps * min(0.85, goal_rate + 0.25))))
    goals = 0 if goals_ceiling <= 0 else _weighted_randint(rng, 0, goals_ceiling, bias=(0.20 + 0.40 * pa_factor))
    return (min(caps, max_caps), min(goals, caps, max_goals))

def _maybe_pick_random_opponent_nation(rng: random.Random, nation_lookup: Dict[str, Tuple[int, int]], exclude_names: Sequence[str] = ()) -> Optional[Tuple[int, int]]:
    if not nation_lookup:
        return None
    excludes = {str(x).strip().lower() for x in (exclude_names or ()) if str(x).strip()}
    keys = [k for k in nation_lookup.keys() if k not in excludes]
    if not keys:
        return None
    return nation_lookup[rng.choice(keys)]

def _random_date_between(rng: random.Random, start: dt.date, end: dt.date) -> dt.date:
    if end < start:
        start, end = end, start
    days = (end - start).days
    if days <= 0:
        return start
    return start + dt.timedelta(days=rng.randint(0, days))
def _parse_second_nation_specs(specs: Optional[List[str]], nation_lookup: Dict[str, Tuple[int, int]]) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for raw in (specs or []):
        s = (raw or "").strip()
        if not s:
            continue
        if "|" in s:
            nation_name, info_name = s.split("|", 1)
        else:
            nation_name, info_name = s, ""
        nation_name = (nation_name or "").strip()
        if not nation_name:
            continue
        dbid, large = _resolve_nation_from_lookup(nation_name, nation_lookup)
        ntin_val = resolve_nationality_info(name=(info_name or "").strip()) if (info_name or "").strip() else 0
        rows.append({"name": nation_name, "dbid": int(dbid), "large": int(large), "ntin": int(ntin_val)})
    return rows


def _pick_primary_nationality_info_default(rng: random.Random) -> int:
    """Default primary nationality info bias when user has not explicitly overridden it.

    Target behaviour:
      - ~95% Born In Nation (85)
      - ~5% spread across other plausible values
    """
    r = rng.random()
    if r < 0.95:
        return 85  # Born In Nation
    # small tail for variety; weighted towards common/credible outcomes
    r2 = rng.random()
    if r2 < 0.45:
        return 84  # Relative Born In Nation
    if r2 < 0.75:
        return 80  # Eligible For Nation
    if r2 < 0.90:
        return 83  # Declared For Nation
    return 0       # No info


def _pick_random_extra_nation_count(rng: random.Random) -> int:
    """Return number of randomly generated extra nationalities (beyond primary).

    Approximate overall probabilities (cumulative):
      - 10% have at least a 2nd nation (1 extra)
      - 3% have at least a 3rd nation (2 extras total)
      - 1% have at least a 4th nation (3 extras total)
      - 0.1% have 5+ nations total (4+ extras)
    """
    extras = 0
    if rng.random() < 0.10:
        extras = 1
        if rng.random() < 0.30:   # 10% * 30% = ~3% total => 3rd nation
            extras = 2
            if rng.random() < (1.0 / 3.0):  # ~1% total => 4th nation
                extras = 3
                if rng.random() < 0.10:     # ~0.1% total => 5+ nations
                    extras = 4
                    # allow rare 6th/7th/etc total nations (kept very small)
                    while extras < 8 and rng.random() < 0.20:
                        extras += 1
    return extras


def _pick_random_second_nation_nationality_info(rng: random.Random) -> int:
    """Weighted nationality info for randomly generated second/third/etc nations."""
    r = rng.random()
    if r < 0.70:
        return 80  # Eligible For Nation
    if r < 0.88:
        return 84  # Relative Born In Nation
    if r < 0.94:
        return 83  # Declared For Nation
    if r < 0.98:
        return 85  # Born In Nation
    return 0       # No info


def _build_random_extra_second_nations(
    rng: random.Random,
    nations: List[Tuple[int, int, str]],
    primary_nation: Tuple[int, int],
    existing_rows: Optional[List[Dict[str, object]]] = None,
) -> List[Dict[str, object]]:
    """Generate random extra nation rows using FM second-nation row model inputs.

    Returns parsed row dicts compatible with the existing second nation writer:
      {"name", "dbid", "large", "ntin"}

    Important: excludes the player's primary nation and any already-specified nations.
    """
    existing_rows = list(existing_rows or [])
    # Only auto-generate when user has not manually provided second nations.
    if existing_rows:
        return []

    extras_needed = _pick_random_extra_nation_count(rng)
    if extras_needed <= 0:
        return []

    p_dbid, p_large = (int(primary_nation[0]), int(primary_nation[1]))
    excluded = {(p_dbid, p_large)}
    for row in existing_rows:
        try:
            excluded.add((int(row.get("dbid", -1)), int(row.get("large", -1))))
        except Exception:
            pass

    pool = []
    for n in (nations or []):
        if len(n) < 2:
            continue
        dbid = int(n[0])
        large = int(n[1])
        if (dbid, large) in excluded:
            continue
        name = (n[2] if len(n) > 2 else "") or ""
        pool.append((dbid, large, str(name)))

    if not pool:
        return []

    rng.shuffle(pool)
    picked = pool[:min(extras_needed, len(pool))]
    out: List[Dict[str, object]] = []
    for dbid, large, name in picked:
        out.append({
            "name": name,
            "dbid": int(dbid),
            "large": int(large),
            "ntin": int(_pick_random_second_nation_nationality_info(rng)),
        })
    return out

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
                club_gender = (d.get("club_gender", "") or d.get("gender", "")).strip().lower()
                if dbid is None or large is None:
                    continue
                clubs[(dbid, large)] = (dbid, large, name, club_gender)

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

        global CLUB_GENDER_MAP
        CLUB_GENDER_MAP = {(c[0], c[1]): (c[3] if len(c) > 3 else "") for c in clubs.values()}
        return list(clubs.values()), list(cities.values()), list(nations.values())


# ---- names ----
def _to_pos_float(val: object, default: float = 1.0) -> float:
    try:
        x = float(str(val).strip())
        if x > 0:
            return x
    except Exception:
        pass
    return float(default)

def _load_name_rows(path: str) -> List[Dict[str, object]]:
    """
    Loads CSV rows for names.
    Supported columns (case-insensitive):
      - Name
      - Nationality / Nation
      - Weight      (optional; defaults to 1)
      - Frequency   (optional; defaults to 1)
    Backwards compatible with old 1- or 2-column CSVs.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    rows: List[Dict[str, object]] = []
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)
        s = sample.lower()
        has_header = ("name" in s and ("nationality" in s or ",nation" in s or ",weight" in s or ",frequency" in s))
        if has_header:
            dr = csv.DictReader(f)
            for d in dr:
                if not d:
                    continue
                name = (d.get("Name") or d.get("name") or "").strip()
                nat = (d.get("Nationality") or d.get("nationality") or d.get("Nation") or d.get("nation") or "").strip()
                weight = _to_pos_float(d.get("Weight") or d.get("weight") or 1, 1.0)
                freq = _to_pos_float(
                    d.get("Frequency") or d.get("frequency") or d.get("Freq") or d.get("freq") or 1,
                    1.0
                )
                if name:
                    rows.append({"name": name, "nationality": nat, "weight": weight, "frequency": freq})
        else:
            for row in csv.reader(f):
                if not row:
                    continue
                name = (row[0] or "").strip()
                if not name or name.lower() == "name":
                    continue
                nat = (row[1] or "").strip() if len(row) > 1 else ""
                if nat.lower() in ("nationality", "nation"):
                    nat = ""
                weight = _to_pos_float(row[2], 1.0) if len(row) > 2 else 1.0
                freq = _to_pos_float(row[3], 1.0) if len(row) > 3 else 1.0
                rows.append({"name": name, "nationality": nat, "weight": weight, "frequency": freq})
    if not rows:
        raise ValueError(f"No names loaded from {path}")
    return rows

def _load_names(path: str) -> List[str]:
    return [str(r["name"]) for r in _load_name_rows(path)]

def _norm_nat(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("brzail", "brazil").replace("argentia", "argentina")
    return s

def _weighted_name_choice(name_rng: random.Random, rows: List[Dict[str, object]]) -> str:
    if not rows:
        return ""
    names: List[str] = []
    weights: List[float] = []
    for r in rows:
        nm = str(r.get("name", "") or "").strip()
        if not nm:
            continue
        w = _to_pos_float(r.get("weight", 1), 1.0)
        f = _to_pos_float(r.get("frequency", 1), 1.0)
        eff = max(1e-9, w * f)
        names.append(nm)
        weights.append(eff)
    if not names:
        return ""
    try:
        return name_rng.choices(names, weights=weights, k=1)[0]
    except Exception:
        # Safe fallback if weights ever fail
        return name_rng.choice(names)

def _pick_name_weighted(name_rng: random.Random, rows: List[Dict[str, object]], primary_nation_name: str, local_bias: float = 0.85) -> str:
    if not rows:
        return ""
    pn = _norm_nat(primary_nation_name)
    local = [r for r in rows if _norm_nat(str(r.get("nationality", ""))) == pn]
    foreign = [r for r in rows if _norm_nat(str(r.get("nationality", ""))) != pn]
    if local and foreign:
        pool = local if name_rng.random() < local_bias else foreign
        return _weighted_name_choice(name_rng, pool)
    if local:
        return _weighted_name_choice(name_rng, local)
    return _weighted_name_choice(name_rng, rows)

def _ethnicity_profile_for_nation(nation_name: str) -> Dict[str, Tuple[int, int]]:
    n = _norm_nat(nation_name)
    if n in ("scotland", "england", "france"):
        return {"ethnicity": (0, 2), "skin": (0, 5), "hair_colour": (0, 4)}
    if n in ("argentina",):
        return {"ethnicity": (0, 5), "skin": (2, 10), "hair_colour": (0, 5)}
    if n in ("brazil",):
        return {"ethnicity": (0, 10), "skin": (2, 18), "hair_colour": (0, 6)}
    return {"ethnicity": (0, 10), "skin": (0, 19), "hair_colour": (0, 6)}

def _rand_from_rng_range(rng: random.Random, lo: int, hi: int) -> int:
    lo2 = int(min(lo, hi)); hi2 = int(max(lo, hi))
    return rng.randint(lo2, hi2)

def _default_appearance_values(rng: random.Random, nation_name: str, gender_val: int) -> Dict[str, int]:
    prof = _ethnicity_profile_for_nation(nation_name)
    if gender_val == 1:
        hair_length = rng.choices([0, 1, 2, 3], weights=[8, 20, 34, 38], k=1)[0]
    else:
        hair_length = rng.choices([0, 1, 2, 3], weights=[36, 40, 18, 6], k=1)[0]
    return {
        "ethnicity_value": _rand_from_rng_range(rng, *prof["ethnicity"]),
        "skin_tone_value": _rand_from_rng_range(rng, *prof["skin"]),
        "hair_colour_value": _rand_from_rng_range(rng, *prof["hair_colour"]),
        "hair_length_value": int(hair_length),
    }

# ---- randomness ----


def _random_body_type_weighted(rng: random.Random) -> int:
    """Body type realism bias: 95% types 1-3, 4% type 4, 1% type 5."""
    roll = rng.random() * 100.0
    if roll < 95.0:
        return rng.choice((1, 2, 3))
    if roll < 99.0:
        return 4
    return 5

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




def _attr_second_nations_listop(person_uid: int, rid: int, ver: int, *, lsop: int, dbid: Optional[int] = None,
                                large: Optional[int] = None, ntin: Optional[int] = None,
                                element_id: int = 1851880553) -> str:
    # FM26 exported shape: the nation row and per-row nationality-info row are separate records.
    # This function writes only the nation row (id=1851880553). ntin is ignored here by design.
    if int(lsop) == 0:
        newv = '<record id="new_value">\n' + f'\t\t\t\t{_int("lsop", 0)}\n' + "\t\t\t</record>"
        return _attr(person_uid, PROP_SECOND_NATIONS, newv, rid, ver)

    if dbid is None or large is None:
        raise ValueError("second nation lsop=1 requires dbid and large")

    newv = (
        '<record id="new_value">\n'
        + f'\t\t\t\t{_uns("id", int(element_id))}\n'
        + '\t\t\t\t<record id="value">\n'
        + f'\t\t\t\t\t{_large("Nnat", int(large))}\n'
        + f'\t\t\t\t\t{_int("DBID", int(dbid))}\n'
        + '\t\t\t\t</record>\n'
        + f'\t\t\t\t{_int("lsop", 1)}\n'
        + '\t\t\t\t<record id="olvl">\n'
        + f'\t\t\t\t\t{_int("ntin", 80)}\n'
        + f'\t\t\t\t\t{_null("nation")}\n'
        + '\t\t\t\t</record>\n'
        + '\t\t\t</record>'
    )
    return _attr(person_uid, PROP_SECOND_NATIONS, newv, rid, ver)

def _attr_second_nation_nationality_info(person_uid: int, rid: int, ver: int, *, nation_large: int, ntin_value: int) -> str:
    # FM26 exported per-row nationality info (linked to a second nation by Nnat)
    newv = (
        '<record id="new_value">\n'
        + f'\t\t\t\t{_uns("id", 1853122926)}\n'
        + f'\t\t\t\t{_int("value", int(ntin_value))}\n'
        + f'\t\t\t\t{_int("lsop", 1)}\n'
        + '\t\t\t\t<record id="olvl">\n'
        + f'\t\t\t\t\t{_int("ntin", 80)}\n'
        + '\t\t\t\t\t<record id="nation">\n'
        + f'\t\t\t\t\t\t{_large("Nnat", int(nation_large))}\n'
        + '\t\t\t\t\t</record>\n'
        + '\t\t\t\t</record>\n'
        + '\t\t\t</record>'
    )
    return _attr(person_uid, PROP_SECOND_NATIONS, newv, rid, ver)

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
    first_names_csv: str = "male_first_names.csv",
    female_first_names_csv: Optional[str] = None,
    common_names_csv: Optional[str] = None,
    common_name_chance: float = 0.05,
    surnames_csv: str = "surnames.csv",
    fixed_first_name: Optional[str] = None,
    fixed_second_name: Optional[str] = None,
    fixed_common_name: Optional[str] = None,
    fixed_full_name: Optional[str] = None,
    person_type_value: Optional[int] = None,
    gender_value: Optional[int] = None,
    ethnicity_value: Optional[int] = None,
    hair_colour_value: Optional[int] = None,
    hair_length_value: Optional[int] = None,
    skin_tone_value: Optional[int] = None,
    body_type_value: Optional[int] = None,
    fixed_dob: Optional[dt.date] = None,
    dob_start: Optional[dt.date] = None,
    dob_end: Optional[dt.date] = None,
    moved_to_nation_date: Optional[dt.date] = None,
    joined_club_date: Optional[dt.date] = None,
    contract_expires_date: Optional[dt.date] = None,
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
    international_apps: Optional[int] = None,
    international_goals: Optional[int] = None,
    u21_international_apps: Optional[int] = None,
    u21_international_goals: Optional[int] = None,
    international_debut_date: Optional[dt.date] = None,
    international_debut_against_name: Optional[str] = None,
    u21_international_debut_date: Optional[dt.date] = None,
    u21_international_debut_against_name: Optional[str] = None,
    first_international_goal_date: Optional[dt.date] = None,
    first_international_goal_against_name: Optional[str] = None,
    nationality_info_value: Optional[int] = None,
    second_nation_specs: Optional[List[str]] = None,
    declared_for_youth_nation_name: Optional[str] = None,
    international_retirement: bool = False,
    international_retirement_date: Optional[dt.date] = None,
    retiring_after_spell_current_club: bool = False,
    id_registry_path: Optional[str] = None,
    id_registry_mode: str = "auto",  # auto|off
    id_namespace_salt: Optional[str] = None,
    omit_fields: Optional[Sequence[str]] = None,
) -> None:
    if seed is None:
        seed = int(dt.datetime.utcnow().timestamp())
    if count < 1:
        raise ValueError("count must be >=1")
    if not (0 <= ca_min <= ca_max <= 200):
        raise ValueError("CA must be 0..200")
    if not (0 <= pa_min <= pa_max <= 200):
        raise ValueError("PA must be 0..200")
    if age_max < age_min or age_min < 1 or age_max > 100:
        raise ValueError("invalid age range (allowed: 1..100)")

    library_csv = _resolve_existing_data_path(library_csv, kind='master_library.csv')
    first_names_csv = _resolve_existing_data_path(first_names_csv, kind='first names csv')
    surnames_csv = _resolve_existing_data_path(surnames_csv, kind='surnames csv')
    if female_first_names_csv:
        female_first_names_csv = _resolve_existing_data_path(female_first_names_csv, kind='female first names csv')
    if common_names_csv:
        common_names_csv = _resolve_existing_data_path(common_names_csv, kind='common names csv')
    out_xml = _resolve_output_xml_path(out_xml)

    if person_type_value is not None:
        person_type_value = int(person_type_value)
        if person_type_value not in (1, 2):
            raise ValueError("person_type_value must be 1 or 2")
    if gender_value is not None:
        gender_value = int(gender_value)
        if gender_value not in (0, 1):
            raise ValueError("gender_value must be 0 (Male) or 1 (Female)")
    if ethnicity_value is not None:
        ethnicity_value = int(ethnicity_value)
        if ethnicity_value < -1 or ethnicity_value > 10:
            raise ValueError("ethnicity_value must be between -1 and 10")
    if hair_colour_value is not None:
        hair_colour_value = int(hair_colour_value)
        if hair_colour_value < 0 or hair_colour_value > 6:
            raise ValueError("invalid hair colour value (allowed: 0..6)")
    if hair_length_value is not None:
        hair_length_value = int(hair_length_value)
        if hair_length_value < 0 or hair_length_value > 3:
            raise ValueError("invalid hair length value (allowed: 0..3)")
    if skin_tone_value is not None:
        skin_tone_value = int(skin_tone_value)
        if skin_tone_value < -1 or skin_tone_value > 19:
            raise ValueError("invalid skin tone value (allowed: -1..19)")
    if body_type_value is not None:
        body_type_value = int(body_type_value)
        if body_type_value < 1 or body_type_value > 5:
            raise ValueError("invalid body type value (allowed: 1..5)")

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
    if moved_to_nation_date is not None and not isinstance(moved_to_nation_date, dt.date):
        raise ValueError("moved_to_nation_date must be a valid date")
    if joined_club_date is not None and not isinstance(joined_club_date, dt.date):
        raise ValueError("joined_club_date must be a valid date")
    if international_retirement_date is not None and not isinstance(international_retirement_date, dt.date):
        raise ValueError("international_retirement_date must be a valid date")
    if international_debut_date is not None and not isinstance(international_debut_date, dt.date):
        raise ValueError("international_debut_date must be a valid date")
    if u21_international_debut_date is not None and not isinstance(u21_international_debut_date, dt.date):
        raise ValueError("u21_international_debut_date must be a valid date")
    for _n, _v in (("international_apps", international_apps), ("international_goals", international_goals), ("u21_international_apps", u21_international_apps), ("u21_international_goals", u21_international_goals)):
        if _v is not None:
            _iv = int(_v)
            if _iv < 0 and _iv not in (-1, -2):
                raise ValueError(f"{_n} must be >= 0 (or -1 omit / -2 auto)")

    _omit_fields = _norm_omit_fields(omit_fields)
    def _is_omitted(*names: str) -> bool:
        for _name in names:
            if str(_name).strip().lower().replace(" ", "_").replace("-", "_") in _omit_fields:
                return True
        return False

    def _norm_intl_count(_v):
        if _v is None:
            return None
        _iv = int(_v)
        if _iv == -1:
            return None
        if _iv == -2:
            return _AUTO_INTL
        return _iv
    international_apps = _norm_intl_count(international_apps)
    international_goals = _norm_intl_count(international_goals)
    u21_international_apps = _norm_intl_count(u21_international_apps)
    u21_international_goals = _norm_intl_count(u21_international_goals)

    if isinstance(international_debut_against_name, str) and international_debut_against_name.strip() == "__NONE__":
        international_debut_against_name = None
    if isinstance(first_international_goal_against_name, str) and first_international_goal_against_name.strip() == "__NONE__":
        first_international_goal_against_name = None
    if isinstance(u21_international_debut_against_name, str) and u21_international_debut_against_name.strip() == "__NONE__":
        u21_international_debut_against_name = None

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
    nation_lookup = _build_nation_lookup(nations)
    nation_name_by_key = {(n[0], n[1]): (n[2] if len(n) > 2 else "") for n in nations}
    parsed_second_nations = _parse_second_nation_specs(second_nation_specs, nation_lookup)

    international_debut_against = None
    if international_debut_against_name:
        _v = str(international_debut_against_name).strip()
        if _v:
            international_debut_against = _resolve_nation_from_lookup(_v, nation_lookup)
    u21_international_debut_against = None
    if u21_international_debut_against_name:
        _v = str(u21_international_debut_against_name).strip()
        if _v:
            u21_international_debut_against = _resolve_nation_from_lookup(_v, nation_lookup)
    first_international_goal_against = None
    if first_international_goal_against_name:
        _v = str(first_international_goal_against_name).strip()
        if _v:
            first_international_goal_against = _resolve_nation_from_lookup(_v, nation_lookup)
    _first_goal_date_eff = first_international_goal_date

    declared_for_youth_nation = None
    if declared_for_youth_nation_name:
        k = str(declared_for_youth_nation_name).strip().lower()
        if k:
            declared_for_youth_nation = nation_lookup.get(k)
            if declared_for_youth_nation is None:
                raise ValueError(f"Declared-for-youth nation not found in master_library: {declared_for_youth_nation_name!r}")

    fixed_first_name = (fixed_first_name or "").strip() or None
    fixed_second_name = (fixed_second_name or "").strip() or None
    fixed_common_name = (fixed_common_name or "").strip() or None
    fixed_full_name = (fixed_full_name or "").strip() or None

    male_first_rows: List[Dict[str, str]] = []
    female_first_rows: List[Dict[str, str]] = []
    surname_rows: List[Dict[str, str]] = []
    common_name_rows: List[Dict[str, str]] = []
    if fixed_first_name is None:
        male_first_rows = _load_name_rows(first_names_csv)
    if fixed_second_name is None:
        surname_rows = _load_name_rows(surnames_csv)
    if female_first_names_csv:
        try:
            female_first_rows = _load_name_rows(female_first_names_csv)
        except FileNotFoundError:
            female_first_rows = []
    if common_names_csv:
        try:
            common_name_rows = _load_name_rows(common_names_csv)
        except FileNotFoundError:
            common_name_rows = []

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

        # Determine gender + nation before names so name pools can be nationality-aware.
        eff_gender_value = int(gender_value if gender_value is not None else rng.choice([0, 1]))
        person_type = int(person_type_value) if person_type_value is not None else 2

        if fixed_nation:
            nation_dbid, nation_large = fixed_nation
        else:
            n = rng.choice(nations)
            nation_dbid, nation_large = n[0], n[1]
        primary_nation_name = nation_name_by_key.get((nation_dbid, nation_large), "")

        if fixed_first_name is not None:
            fn = fixed_first_name
        else:
            first_pool = female_first_rows if (eff_gender_value == 1 and female_first_rows) else male_first_rows
            fn = _pick_name_weighted(name_rng, first_pool, primary_nation_name, local_bias=0.85)
        sn = fixed_second_name if fixed_second_name is not None else _pick_name_weighted(name_rng, surname_rows, primary_nation_name, local_bias=0.85)
        if fixed_common_name or fixed_full_name:
            cn = (fixed_common_name or fixed_full_name or f"{fn} {sn}").strip()
        else:
            if common_name_rows and (name_rng.random() < float(common_name_chance)):
                cn = (_pick_name_weighted(name_rng, common_name_rows, primary_nation_name, local_bias=0.85) or "").strip()
                if not cn or cn.lower() in {fn.lower(), sn.lower()}:
                    cn = f"{fn} {sn}"
            else:
                cn = f"{fn} {sn}"

        height = fixed_height if fixed_height is not None else rng.randint(height_min, height_max)
        if fixed_dob is not None:
            dob = fixed_dob
        elif (dob_start is not None and dob_end is not None):
            dob = _random_dob_between(rng, dob_start, dob_end)
        else:
            dob = _random_dob(rng, rng.randint(age_min, age_max), base_year)

        # Always derive an age value from DOB so later logic (e.g. auto international stats)
        # never depends on a separately defined local `age` variable.
        # Use 30 June of base_year as a stable season reference point.
        _season_ref = dt.date(int(base_year), 6, 30)
        age = int(_season_ref.year - dob.year - ((dob.month, dob.day) > (_season_ref.month, _season_ref.day)))
        if age < 0:
            age = 0

        ca = rng.randint(ca_min, ca_max)
        pa = rng.randint(pa_min, pa_max)
        if pa < ca:
            pa = ca

        if fixed_club:
            club_dbid, club_large = fixed_club
        else:
            want_gender = "female" if eff_gender_value == 1 else "male"
            club_pool = [c for c in clubs if len(c) <= 3 or (str(c[3]).strip().lower() in ("", want_gender))]
            c = rng.choice(club_pool or clubs)
            club_dbid, club_large = c[0], c[1]
        city_dbid, city_large = fixed_city if fixed_city else (lambda x: (x[0], x[1]))(rng.choice(cities))

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

        joined = joined_club_date if joined_club_date is not None else dt.date(base_year, 7, 1)
        moved_to_nation = moved_to_nation_date if moved_to_nation_date is not None else dob
        expires = contract_expires_date if contract_expires_date is not None else dt.date(base_year + 3, 6, 30)

        def rid(lbl: str) -> int:
            return _uniq(_id32, seed, i, lbl, used32)

        # Details randomization: when GUI/CLI chooses "Random" it omits the value args.
        # In that case generate a valid random FM value instead of omitting the record.
        eff_gender_value = int(eff_gender_value)  # set earlier so name pool + club filtering stay in sync
        _app = _default_appearance_values(rng, primary_nation_name, eff_gender_value)
        eff_ethnicity_value = int(ethnicity_value) if ethnicity_value is not None else int(_app["ethnicity_value"])
        eff_hair_colour_value = int(hair_colour_value) if hair_colour_value is not None else int(_app["hair_colour_value"])
        eff_hair_length_value = int(hair_length_value) if hair_length_value is not None else int(_app["hair_length_value"])
        eff_skin_tone_value = int(skin_tone_value) if skin_tone_value is not None else int(_app["skin_tone_value"])
        eff_body_type_value = int(body_type_value) if body_type_value is not None else _random_body_type_weighted(rng)

        # string fields (with language flag)
        if not _is_omitted("first_name"):
            frags.append(_rec(_attr(person_uid, PROP_FIRST_NAME, _str("new_value", fn), rid("rid|fn"), version, extra=lang_extra), "First Name"))
        if not _is_omitted("second_name"):
            frags.append(_rec(_attr(person_uid, PROP_SECOND_NAME, _str("new_value", sn), rid("rid|sn"), version, extra=lang_extra), "Second Name"))
        if not _is_omitted("common_name"):
            frags.append(_rec(_attr(person_uid, PROP_COMMON_NAME, _str("new_value", cn), rid("rid|cn"), version, extra=lang_extra), "Common Name"))

        full_name = (fixed_full_name.strip() if isinstance(fixed_full_name, str) and fixed_full_name.strip() else f"{fn} {sn}".strip())
        if not _is_omitted("full_name"):
            frags.append(_rec(_attr(person_uid, PROP_FULL_NAME, _str("new_value", full_name), rid("rid|full_name"), version, odvl=_str("odvl", f"{fn} {sn}".strip())), "Full Name"))
        if person_type_value is not None:
            _pt = int(person_type_value)
            _pt_odvl = 1 if _pt == 2 else 2
            frags.append(_rec(_attr(person_uid, PROP_PERSON_TYPE, _int("new_value", _pt), rid("rid|ptype"), version, odvl=_int("odvl", _pt_odvl)), "Person Type"))
        if not _is_omitted("gender"):
            frags.append(_rec(_attr(person_uid, PROP_GENDER, _int("new_value", eff_gender_value), rid("rid|gender"), version, odvl=_bool("odvl", False)), "Gender"))
        if not _is_omitted("ethnicity"):
            frags.append(_rec(_attr(person_uid, PROP_ETHNICITY, _int("new_value", eff_ethnicity_value), rid("rid|ethnicity"), version, odvl=_int("odvl", -1)), "Ethnicity"))
        if not _is_omitted("hair_colour", "hair_color"):
            frags.append(_rec(_attr(person_uid, PROP_HAIR_COLOUR, _int("new_value", eff_hair_colour_value), rid("rid|hair_colour"), version, odvl=_uns("odvl", 3)), "Hair Colour"))
        if not _is_omitted("hair_length"):
            frags.append(_rec(_attr(person_uid, PROP_HAIR_LENGTH, _int("new_value", eff_hair_length_value), rid("rid|hair_length"), version, odvl=_uns("odvl", 1)), "Hair Length"))
        if not _is_omitted("skin_tone"):
            frags.append(_rec(_attr(person_uid, PROP_SKIN_TONE, _int("new_value", eff_skin_tone_value), rid("rid|skin_tone"), version, odvl=_int("odvl", -1)), "Skin Tone"))
        if not _is_omitted("body_type"):
            frags.append(_rec(_attr(person_uid, PROP_BODY_TYPE, _int("new_value", eff_body_type_value), rid("rid|body_type"), version, odvl=_uns("odvl", 3)), "Body Type"))

        # scalar ints/dates
        if not _is_omitted("height"):
            frags.append(_rec(_attr(person_uid, PROP_HEIGHT, _int("new_value", int(height)), rid("rid|h"), version, odvl=odvl0), "Height"))
        if not _is_omitted("dob", "date_of_birth"):
            frags.append(_rec(_attr(person_uid, PROP_DOB, _date("new_value", dob), rid("rid|dob"), version, odvl=odvl_date), "DOB"))

        # city record
        newv = (
            '<record id="new_value">\n'
            + f'\t\t\t\t{_large("city", city_large)}\n'
            + f'\t\t\t\t{_int("DBID", city_dbid)}\n'
            + "\t\t\t</record>"
        )
        if not _is_omitted("city_of_birth", "city"):
            frags.append(_rec(_attr(person_uid, CITY_PROPERTY, newv, rid("rid|city"), version, odvl=_null("odvl")), "City of birth"))

        # nation record (+ odvl record)
        newv = (
            '<record id="new_value">\n'
            + f'\t\t\t\t{_large("Nnat", nation_large)}\n'
            + f'\t\t\t\t{_int("DBID", nation_dbid)}\n'
            + "\t\t\t</record>"
        )
        odvl = '<record id="odvl">\n' + f'\t\t\t\t{_large("Nnat", DEFAULT_NNAT_ODVL)}\n' + "\t\t\t</record>"
        if not _is_omitted("nation", "nationality"):
            frags.append(_rec(_attr(person_uid, NATION_PROPERTY, newv, rid("rid|nation"), version, odvl=odvl), "Nation"))

        # second nations list entries (FM property 1347310195)
        _effective_second_nations = list(parsed_second_nations or [])
        if not _effective_second_nations:
            _effective_second_nations.extend(_build_random_extra_second_nations(
                rng,
                nations,
                (int(nation_dbid), int(nation_large)),
                existing_rows=parsed_second_nations,
            ))

        if _effective_second_nations:
            for _sn in _effective_second_nations:
                frags.append(_rec(_attr_second_nations_listop(person_uid, rid("rid|second_nation|prep"), version, lsop=0), "Second nation list prep"))
            for _sn_idx, _sn in enumerate(_effective_second_nations, start=2):
                _comment = "Second nation" if _sn_idx == 2 else f"{_sn_idx}th nation"
                if _sn_idx == 3:
                    _comment = "Third nation"
                _sn_large = int(_sn["large"])
                _sn_ntin = int(_sn.get("ntin", 80))
                frags.append(_rec(_attr_second_nations_listop(
                    person_uid,
                    rid(f"rid|second_nation|{_sn_idx}"),
                    version,
                    lsop=1,
                    dbid=int(_sn["dbid"]),
                    large=_sn_large,
                    ntin=_sn_ntin,
                ), _comment))
                frags.append(_rec(_attr_second_nation_nationality_info(
                    person_uid,
                    rid(f"rid|second_nation_natinf|{_sn_idx}"),
                    version,
                    nation_large=_sn_large,
                    ntin_value=_sn_ntin,
                ), f"{_comment} nationality info"))

        # nationality info (default bias = ~95% Born In Nation unless explicitly overridden)
        _effective_primary_natinf = int(nationality_info_value) if nationality_info_value is not None else _pick_primary_nationality_info_default(rng)
        if not _is_omitted("nationality_info", "natinf", "nationalityinfo"):
            frags.append(_rec(_attr(person_uid, PROP_NATIONALITY_INFO, _int("new_value", int(_effective_primary_natinf)), rid("rid|ninfo"), version, odvl=odvl0), "Nationality Info"))

        if (declared_for_youth_nation is not None) and (not _is_omitted("declared_for_youth_nation")):
            _dy_dbid, _dy_large = declared_for_youth_nation
            _dy_newv = (
                '<record id="new_value">\n'
                + f'\t\t\t\t{_large("Nnat", int(_dy_large))}\n'
                + f'\t\t\t\t{_int("DBID", int(_dy_dbid))}\n'
                + "\t\t\t</record>"
            )
            frags.append(_rec(_attr(person_uid, PROP_DECLARED_FOR_YOUTH_NATION, _dy_newv, rid("rid|declared_for_youth_nation"), version, odvl=_null("odvl")), "Declared For Nation At Youth Level"))

        _intl_apps_eff = international_apps
        _intl_goals_eff = international_goals
        _u21_apps_eff = u21_international_apps
        _u21_goals_eff = u21_international_goals
        _intl_debut_date_eff = international_debut_date
        _intl_debut_against_eff = international_debut_against
        _first_goal_date_eff_player = _first_goal_date_eff
        _first_goal_against_eff_player = first_international_goal_against

        _need_auto_intl = any(v is _AUTO_INTL for v in (_intl_apps_eff, _intl_goals_eff, _u21_apps_eff, _u21_goals_eff))
        if _need_auto_intl:
            _sen_caps_auto, _sen_goals_auto = _estimate_international_stats(rng, age=age, pa=pa, nation_name=primary_nation_name, max_caps=250, max_goals=250, youth=False)
            _u21_caps_auto, _u21_goals_auto = _estimate_international_stats(rng, age=age, pa=pa, nation_name=primary_nation_name, max_caps=100, max_goals=100, youth=True)
            if _intl_apps_eff is _AUTO_INTL: _intl_apps_eff = _sen_caps_auto
            if _intl_goals_eff is _AUTO_INTL: _intl_goals_eff = min(_sen_goals_auto, int(_intl_apps_eff or 0))
            if _u21_apps_eff is _AUTO_INTL: _u21_apps_eff = _u21_caps_auto
            if _u21_goals_eff is _AUTO_INTL: _u21_goals_eff = min(_u21_goals_auto, int(_u21_apps_eff or 0))
            _today_est = dt.date(base_year, 6, 30)
            if _intl_apps_eff and _intl_apps_eff > 0 and _intl_debut_date_eff is None:
                _start = max(dob + dt.timedelta(days=16*365), dt.date(max(base_year-35, dob.year+16), 1, 1))
                _end = min(_today_est, dt.date(base_year, 12, 31))
                if _end >= _start:
                    _intl_debut_date_eff = _random_date_between(rng, _start, _end)
            if _intl_apps_eff and _intl_apps_eff > 0 and _intl_debut_against_eff is None:
                _intl_debut_against_eff = _maybe_pick_random_opponent_nation(rng, nation_lookup, exclude_names=[primary_nation_name])
            if _intl_goals_eff and _intl_goals_eff > 0 and _first_goal_date_eff_player is None:
                _fg_start = _intl_debut_date_eff or max(dob + dt.timedelta(days=16*365), dt.date(max(base_year-35, dob.year+16), 1, 1))
                _fg_end = _today_est
                if _fg_end >= _fg_start:
                    _first_goal_date_eff_player = _random_date_between(rng, _fg_start, _fg_end)
            if _intl_goals_eff and _intl_goals_eff > 0 and _first_goal_against_eff_player is None:
                _first_goal_against_eff_player = _maybe_pick_random_opponent_nation(rng, nation_lookup, exclude_names=[primary_nation_name])

        # international data (optional test fields from International Data tab)
        if (not _is_omitted('international_apps')) and _intl_apps_eff is not None:
            frags.append(_rec(_attr(person_uid, PROP_INTERNATIONAL_APPS, _int("new_value", int(_intl_apps_eff)), rid("rid|international_apps"), version, odvl=odvl0), "International appearances"))
        if (not _is_omitted('international_goals')) and _intl_goals_eff is not None:
            frags.append(_rec(_attr(person_uid, PROP_INTERNATIONAL_GOALS, _int("new_value", int(_intl_goals_eff)), rid("rid|international_goals"), version, odvl=odvl0), "International goals"))
        if (not _is_omitted('u21_international_apps','under_21_international_apps')) and _u21_apps_eff is not None:
            frags.append(_rec(_attr(person_uid, PROP_U21_INTERNATIONAL_APPS, _int("new_value", int(_u21_apps_eff)), rid("rid|u21_international_apps"), version, odvl=odvl0), "U21 International appearances"))
        if (not _is_omitted('u21_international_goals','under_21_international_goals')) and _u21_goals_eff is not None:
            frags.append(_rec(_attr(person_uid, PROP_U21_INTERNATIONAL_GOALS, _int("new_value", int(_u21_goals_eff)), rid("rid|u21_international_goals"), version, odvl=odvl0), "U21 International goals"))
        if (not _is_omitted('international_debut_date')) and _intl_debut_date_eff is not None:
            frags.append(_rec(_attr(person_uid, PROP_INTERNATIONAL_DEBUT_DATE, _date("new_value", _intl_debut_date_eff), rid("rid|international_debut_date"), version, odvl=odvl_date), "International debut date"))
        if (not _is_omitted('international_debut_against')) and _intl_debut_against_eff is not None:
            _ida_dbid, _ida_large = _intl_debut_against_eff
            _ida_newv = (
                "<record id=\"new_value\">\n"
                + f'\t\t\t\t{_large("Nnat", int(_ida_large))}\n'
                + f'\t\t\t\t{_int("DBID", int(_ida_dbid))}\n'
                + "\t\t\t</record>"
            )
            frags.append(_rec(_attr(person_uid, PROP_INTERNATIONAL_DEBUT_AGAINST, _ida_newv, rid("rid|international_debut_against"), version, odvl=_null("odvl")), "International debut against"))
        if u21_international_debut_date is not None:
            frags.append(_rec(_attr(person_uid, PROP_U21_INTERNATIONAL_DEBUT_DATE, _date("new_value", u21_international_debut_date), rid("rid|u21_international_debut_date"), version, odvl=odvl_date), "U21 International debut date"))
        if u21_international_debut_against is not None:
            _u21da_dbid, _u21da_large = u21_international_debut_against
            _u21da_newv = (
                "<record id=\"new_value\">\n"
                + f'\t\t\t\t{_large("Nnat", int(_u21da_large))}\n'
                + f'\t\t\t\t{_int("DBID", int(_u21da_dbid))}\n'
                + "\t\t\t</record>"
            )
            frags.append(_rec(_attr(person_uid, PROP_U21_INTERNATIONAL_DEBUT_AGAINST, _u21da_newv, rid("rid|u21_international_debut_against"), version, odvl=_null("odvl")), "U21 International debut against"))

        # optional international retirement / nationality metadata
        if bool(international_retirement):
            frags.append(_rec(_attr(person_uid, PROP_INTERNATIONAL_RETIREMENT, _bool("new_value", True), rid("rid|intl_ret"), version, odvl=_bool("odvl", False)), "International Retirement"))
        if international_retirement_date is not None:
            frags.append(_rec(_attr(person_uid, PROP_INTERNATIONAL_RETIREMENT_DATE, _date("new_value", international_retirement_date), rid("rid|intl_ret_date"), version, odvl=odvl_date), "International Retirement Date"))
        if bool(retiring_after_spell_current_club):
            frags.append(_rec(_attr(person_uid, PROP_RETIRING_AFTER_SPELL_CURRENT_CLUB, _bool("new_value", True), rid("rid|intl_ret_end_season"), version, odvl=_bool("odvl", False)), "International Retirement end of club season"))

        # club record
        if not _is_omitted("club", "club_team"):
            newv = (
                '<record id="new_value">\n'
                + f'\t\t\t\t{_large("Ttea", club_large)}\n'
                + f'\t\t\t\t{_int("DBID", club_dbid)}\n'
                + "\t\t\t</record>"
            )
            frags.append(_rec(_attr(person_uid, CLUB_PROPERTY, newv, rid("rid|club"), version, odvl=_null("odvl")), "Club"))

        # other ints/dates
        if not _is_omitted("wage"):
            frags.append(_rec(_attr(person_uid, PROP_WAGE, _int("new_value", wage_val), rid("rid|wage"), version, odvl=odvl0), "Wage"))
        frags.append(_rec(_attr(person_uid, PROP_DATE_MOVED_TO_NATION, _date("new_value", moved_to_nation), rid("rid|moved"), version, odvl=odvl_date), "Moved to nation"))
        frags.append(_rec(_attr(person_uid, PROP_DATE_JOINED_CLUB, _date("new_value", joined), rid("rid|joined"), version, odvl=odvl_date), "Joined club"))
        frags.append(_rec(_attr(person_uid, PROP_DATE_LAST_SIGNED, _date("new_value", joined), rid("rid|signed"), version, odvl=odvl_date), "Last signed"))
        frags.append(_rec(_attr(person_uid, PROP_CONTRACT_EXPIRES, _date("new_value", expires), rid("rid|expires"), version, odvl=odvl_date), "Contract expires"))
        frags.append(_rec(_attr(person_uid, PROP_SQUAD_STATUS, _int("new_value", 9), rid("rid|squad"), version, odvl=_null("odvl")), "Squad status"))
        if not _is_omitted("ca"):
            frags.append(_rec(_attr(person_uid, PROP_CA, _int("new_value", ca), rid("rid|ca"), version, odvl=odvl0), "CA"))
        if not _is_omitted("pa"):
            frags.append(_rec(_attr(person_uid, PROP_PA, _int("new_value", pa), rid("rid|pa"), version, odvl=odvl0), "PA"))
        if not _is_omitted("reputation", "rep"):
            frags.append(_rec(_attr(person_uid, PROP_CURRENT_REP, _int("new_value", rep_cur), rid("rid|rep"), version, odvl=odvl0), "Current rep"))
            frags.append(_rec(_attr(person_uid, PROP_HOME_REP, _int("new_value", rep_home_v), rid("rid|rep_home"), version, odvl=odvl0), "Home rep"))
            frags.append(_rec(_attr(person_uid, PROP_WORLD_REP, _int("new_value", rep_world_v), rid("rid|rep_world"), version, odvl=odvl0), "World rep"))
        if not _is_omitted("feet", "foot"):
            frags.append(_rec(_attr(person_uid, PROP_LEFT_FOOT, _str("new_value", str(left)), rid("rid|lf"), version, odvl=odvl0), "Left foot"))
            frags.append(_rec(_attr(person_uid, PROP_RIGHT_FOOT, _str("new_value", str(right)), rid("rid|rf"), version, odvl=odvl0), "Right foot"))
        if not _is_omitted("transfer_value", "value", "transfer"):
            frags.append(_rec(_attr(person_uid, PROP_TRANSFER_VALUE, _int("new_value", tv), rid("rid|tv"), version, odvl=odvl0), "Transfer value"))

        # positions output
        if not _is_omitted("positions", "position", "pos"):
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
    if argv is None:
        argv = sys.argv[1:]
    if any(a in ('--list_nationality_info', '--list-nationality-info') for a in argv):
        for line in nationality_info_mapping_lines():
            print(line)
        return 0

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
    ap.add_argument("--omit-field", action="append", default=[], help="Field key to omit entirely (repeatable). Used by GUI Don\'t set modes.")
    ap.add_argument("--version", type=int, default=DEFAULT_VERSION)

    ap.add_argument("--dob", default="")
    ap.add_argument("--dob_start", default="")
    ap.add_argument("--dob_end", default="")
    ap.add_argument("--moved_to_nation_date", default="", help="Override date moved to nation (YYYY-MM-DD). Default: DOB")
    ap.add_argument("--joined_club_date", default="", help="Override joined club date (YYYY-MM-DD). Default: base_year-07-01")
    ap.add_argument("--contract_expires_date", default="", help="Override contract expiry date (YYYY-MM-DD). Default: base_year+3-06-30")

    ap.add_argument("--person_type_value", type=int, default=None, help="1 = Non-Player, 2 = Player")
    ap.add_argument("--gender_value", type=int, default=None, help="0 = Male, 1 = Female")
    ap.add_argument("--ethnicity_value", type=int, default=None, help="FM ethnicity mapping (-1..10)")
    ap.add_argument("--hair_colour_value", type=int, default=None, help="FM hair colour mapping (0..6)")
    ap.add_argument("--hair_length_value", type=int, default=None, help="FM hair length mapping (0..3)")
    ap.add_argument("--skin_tone_value", type=int, default=None, help="FM skin tone mapping (-1..19; Unknown=-1, Skin Tone 1=0 ... Skin Tone 20=19)")
    ap.add_argument("--body_type_value", type=int, default=None, help="FM body type mapping (1..5) [1=Ectomorph, 2=Ecto-Mesomorph, 3=Mesomorph, 4=Meso-Endomorph, 5=Endomorph]")

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
    ap.add_argument("--nationality_info", default="", help="Nationality info by name or numeric value (e.g. 'Born In Nation' or 85). Overrides --nationality_info_value if set")
    ap.add_argument("--second_nation", action="append", default=[], help="Repeatable second nation entry. Format: Nation or Nation|Nationality Info label/value")
    ap.add_argument("--declared_for_youth_nation", default="", help="Nation name for separate Declared For Nation At Youth Level field (property 1349411961)")
    ap.add_argument("--list_nationality_info", action="store_true", help="Print nationality info mapping (value -> name) and exit")
    ap.add_argument("--international_retirement", action="store_true", help="Set International Retirement = true")
    ap.add_argument("--international_retirement_date", default="", help="Set International Retirement Date (YYYY-MM-DD)")
    ap.add_argument("--retiring_after_spell_current_club", action="store_true", help="Set Retiring After Spell At Current Club = true")
    ap.add_argument("--international_apps", type=int, default=None, help="International appearances (property 1349083504)")
    ap.add_argument("--international_goals", type=int, default=None, help="International goals (property 1349085036)")
    ap.add_argument("--u21_international_apps", type=int, default=None, help="U21 International appearances (property 1349871969)")
    ap.add_argument("--u21_international_goals", type=int, default=None, help="U21 International goals (property 1349871975)")
    ap.add_argument("--international_debut_date", default="", help="International debut date (YYYY-MM-DD)")
    ap.add_argument("--international_debut_against", default="", help="International debut against nation name")
    ap.add_argument("--u21_international_debut_date", default="", help="U21 International debut date (YYYY-MM-DD)")
    ap.add_argument("--u21_international_debut_against", default="", help="U21 International debut against nation name")
    ap.add_argument("--first_international_goal_date", default="", help="First international goal date (YYYY-MM-DD) [GUI compatibility]")
    ap.add_argument("--first_international_goal_against", default="", help="First international goal against nation name [GUI compatibility]")
    ap.add_argument("--other_nation_caps_json", default="", help="Reserved GUI payload (not yet written to XML; accepted for compatibility)")
    ap.add_argument("--other_nation_youth_caps_json", default="", help="Reserved GUI payload (not yet written to XML; accepted for compatibility)")
    ap.add_argument("--first_names", default="male_first_names.csv")
    ap.add_argument("--female_first_names", default="female_first_names.csv")
    ap.add_argument("--common_names", default="common_names.csv")
    ap.add_argument("--common_name_chance", type=float, default=5.0, help="Chance of using common name CSV (0-1 or 0-100); default 5")
    ap.add_argument("--surnames", default="surnames.csv")
    ap.add_argument("--first_name_text", default="", help="Fixed first name (optional; skips first names CSV if set)")
    ap.add_argument("--second_name_text", default="", help="Fixed second/surname (optional; skips surnames CSV if set)")
    ap.add_argument("--last_name_text", default="", help="Alias for second/surname (optional; compatibility)")
    ap.add_argument("--common_name_text", default="", help="Fixed common name (optional)")
    ap.add_argument("--full_name_text", default="", help="Alias for common name (optional)")

    _argv_for_parse = list(sys.argv[1:] if argv is None else argv)
    _nat_info_explicit = any(
        (a == "--nationality_info")
        or str(a).startswith("--nationality_info=")
        or (a == "--nationality_info_value")
        or str(a).startswith("--nationality_info_value=")
        for a in _argv_for_parse
    )
    args = ap.parse_args(_argv_for_parse)
    # Compatibility aliases for GUI variants:
    # - some versions pass --second_name_text
    # - others pass --last_name_text
    # Prefer explicit --second_name_text if both are provided.
    resolved_last_name_text = (getattr(args, 'second_name_text', '') or '').strip() or (getattr(args, 'last_name_text', '') or '').strip()
    resolved_full_name_text = (getattr(args, 'full_name_text', '') or '').strip()
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
    common_name_chance = float(getattr(args, "common_name_chance", 5.0) or 0.0)
    if common_name_chance > 1.0:
        common_name_chance = common_name_chance / 100.0
    common_name_chance = max(0.0, min(1.0, common_name_chance))

    if args.pa_min > 200 or args.pa_max > 200:
        print("[FAIL] PA must be within 0..200 (you passed >200).", file=sys.stderr)
        return 2
    if args.ca_min > 200 or args.ca_max > 200:
        print("[FAIL] CA must be within 0..200.", file=sys.stderr)
        return 2

    fixed_dob = _parse_ymd(args.dob) if args.dob else None
    dob_start = _parse_ymd(args.dob_start) if args.dob_start else None
    dob_end = _parse_ymd(args.dob_end) if args.dob_end else None
    moved_to_nation_date = _parse_ymd(args.moved_to_nation_date) if args.moved_to_nation_date else None
    joined_club_date = _parse_ymd(args.joined_club_date) if args.joined_club_date else None
    contract_expires_date = _parse_ymd(args.contract_expires_date) if args.contract_expires_date else None
    international_retirement_date = _parse_ymd(args.international_retirement_date) if args.international_retirement_date else None
    international_debut_date = None if (str(args.international_debut_date).strip() in ('', '__NONE__')) else _parse_ymd(args.international_debut_date)
    u21_international_debut_date = None if (str(args.u21_international_debut_date).strip() in ('', '__NONE__')) else _parse_ymd(args.u21_international_debut_date)
    first_international_goal_date = None if (str(getattr(args, 'first_international_goal_date', '')).strip() in ('', '__NONE__')) else _parse_ymd(getattr(args, 'first_international_goal_date'))
    if str(getattr(args, 'other_nation_caps_json', '') or '').strip():
        print("[WARN] --other_nation_caps_json accepted for GUI compatibility but not yet written to XML in this build.", file=sys.stderr)
    if str(getattr(args, 'other_nation_youth_caps_json', '') or '').strip():
        print("[WARN] --other_nation_youth_caps_json accepted for GUI compatibility but not yet written to XML in this build.", file=sys.stderr)

    fixed_height = args.height if args.height else None
    height_min = int(args.height_min)
    height_max = int(args.height_max)

    fixed_club = (args.club_dbid, args.club_large) if (args.club_dbid and args.club_large) else None
    fixed_city = (args.city_dbid, args.city_large) if (args.city_dbid and args.city_large) else None
    fixed_nation = (args.nation_dbid, args.nation_large) if (args.nation_dbid and args.nation_large) else None

    fixed_left_foot = args.left_foot if args.left_foot else None
    fixed_right_foot = args.right_foot if args.right_foot else None
    feet_mode = args.feet

    nationality_info_value_resolved = None
    if _nat_info_explicit:
        try:
            nationality_info_value_resolved = resolve_nationality_info(args.nationality_info_value, getattr(args, 'nationality_info', ''))
        except Exception as e:
            print(f"[FAIL] {e}", file=sys.stderr)
            return 2

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

    args.output = _resolve_output_xml_path(args.output)

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
            female_first_names_csv=(args.female_first_names or None),
            common_names_csv=(args.common_names or None),
            common_name_chance=common_name_chance,
            surnames_csv=args.surnames,
            fixed_first_name=(args.first_name_text or None),
            fixed_second_name=(resolved_last_name_text or None),
            fixed_common_name=(args.common_name_text or None),
            fixed_full_name=(resolved_full_name_text or None),
            person_type_value=args.person_type_value,
            gender_value=args.gender_value,
            ethnicity_value=args.ethnicity_value,
            hair_colour_value=args.hair_colour_value,
            hair_length_value=args.hair_length_value,
            skin_tone_value=args.skin_tone_value,
            body_type_value=args.body_type_value,
            fixed_dob=fixed_dob,
            dob_start=dob_start,
            dob_end=dob_end,
            moved_to_nation_date=moved_to_nation_date,
            joined_club_date=joined_club_date,
            contract_expires_date=contract_expires_date,
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
            international_apps=args.international_apps,
            international_goals=args.international_goals,
            u21_international_apps=args.u21_international_apps,
            u21_international_goals=args.u21_international_goals,
            international_debut_date=international_debut_date,
            international_debut_against_name=(args.international_debut_against or None),
            u21_international_debut_date=u21_international_debut_date,
            u21_international_debut_against_name=(args.u21_international_debut_against or None),
            first_international_goal_date=first_international_goal_date,
            first_international_goal_against_name=(getattr(args, "first_international_goal_against", "") or None),
            nationality_info_value=nationality_info_value_resolved,
            second_nation_specs=list(getattr(args, "second_nation", []) or []),
            international_retirement=bool(args.international_retirement),
            international_retirement_date=international_retirement_date,
            retiring_after_spell_current_club=bool(args.retiring_after_spell_current_club),
            id_registry_path=args.id_registry_path,
            id_registry_mode=args.id_registry_mode,
            id_namespace_salt=args.id_namespace_salt,
            omit_fields=args.omit_field,
        )
    except Exception as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        return 1

    print(f"[OK] Wrote: {args.output} (count={args.count}, append={args.append})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
