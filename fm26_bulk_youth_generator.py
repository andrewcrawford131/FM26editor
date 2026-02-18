#!/usr/bin/env python3
from __future__ import annotations
"""
FM26 Players Generator (db changes XML) - stable SHA256 IDs.

Batch:
  python fm26_bulk_youth_generator.py --master_library master_library.csv --count 10000 --output fm26_players.xml --seed 123

Single:
  python fm26_bulk_youth_generator.py --master_library master_library.csv --count 1 --output fm26_players.xml --append \
    --dob 2012-12-31 --height 180 --club_dbid 1570 --club_large 6648609375756 --city_dbid 102580 --city_large 440573450358963 \
    --nation_dbid 793 --nation_large 3405909066521 --positions DL,DC --ca_min 120 --ca_max 120 --pa_min 180 --pa_max 180 --seed 123
"""
import argparse, csv, datetime as dt, hashlib, os, random, re, sys
from xml.sax.saxutils import escape as xesc
from typing import Dict, List, Optional, Sequence, Tuple

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

DEFAULT_VERSION = 3727
DEFAULT_RULE_GROUP_VERSION = 1630
DEFAULT_EDVB = 1
DEFAULT_ORVS = "2600"
DEFAULT_SVVS = "2600"
DEFAULT_NNAT_ODVL = 3285649982205  # safe default seen in samples

INT32_MOD = 2147483646
INT64_MOD = 9223372036854775806

# ---- stable ids ----
def _sha(seed: int, i: int, label: str) -> int:
    h = hashlib.sha256(f"{seed}|{i}|{label}".encode("utf-8")).digest()
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

def load_master_library(path: str) -> Tuple[List[Tuple[int,int,str]], List[Tuple[int,int,str]], List[Tuple[int,int,str]]]:
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
                    _to_int(d.get("club_large", "")) or
                    _to_int(d.get("ttea_large", "")) or
                    _to_int(d.get("ttea_large_text", "")) or
                    _to_int(d.get("ttea", ""))
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
                    _to_int(d.get("nation_large", "")) or
                    _to_int(d.get("nnat_large", "")) or
                    _to_int(d.get("nnat_large_text", "")) or
                    _to_int(d.get("nnat", ""))
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

def _pick_weighted(rng: random.Random, items: Sequence[Tuple[str, float]]) -> str:
    tot = sum(w for _, w in items)
    x = rng.random() * tot
    acc = 0.0
    for v, w in items:
        acc += w
        if x <= acc:
            return v
    return items[-1][0]

def _random_positions(rng: random.Random) -> List[str]:
    grp = _pick_weighted(rng, [("GK", 0.10), ("DEF", 0.35), ("MID", 0.40), ("ATT", 0.15)])
    if grp == "GK":
        return ["GK"]
    pool = {
        "DEF": ["DL", "DC", "DR", "WBL", "WBR", "DM"],
        "MID": ["DM", "ML", "MC", "MR", "AML", "AMC", "AMR"],
        "ATT": ["AML", "AMC", "AMR", "ST"],
    }[grp]
    n = 1
    r = rng.random()
    if r < 0.25:
        n = 2
    elif r < 0.30:
        n = 3
    rng.shuffle(pool)
    return pool[:n]

def _pos_map(rng: random.Random, selected: List[str]) -> Dict[str, int]:
    sel = [p for p in (selected or []) if p in POS_PROPS]
    if not sel:
        sel = _random_positions(rng)
    if "GK" in sel:
        return {"GK": rng.randint(15, 20)}
    return {p: rng.randint(15, 20) for p in sel}

def _foot(rng: random.Random) -> Tuple[int, int]:
    k = _pick_weighted(rng, [("R", 0.72), ("L", 0.20), ("B", 0.08)])
    if k == "R":
        return rng.randint(1, 10), rng.randint(15, 20)
    if k == "L":
        return rng.randint(15, 20), rng.randint(1, 10)
    return rng.randint(15, 20), rng.randint(15, 20)

def _tv_from_pa(pa: int) -> int:
    x = max(0, min(200, pa))
    return max(100_000, min(1_000_000_000, int(200_000 + ((x / 200.0) ** 3) * 999_800_000)))

# ---- xml helpers ----
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
    c = f'<!-- {comment} -->' if comment else ''
    return f'\t\t<record>{c}\n{inner}\t\t</record>\n'

def _attr(person_uid: int, prop: int, newv: str, rid: int, ver: int, extra: str = "", odvl: str = "") -> str:
    s = f'\t\t\t{_int("database_table_type", TBL_PLAYER)}\n'
    s += f'\t\t\t{_large("db_unique_id", person_uid)}\n'
    s += f'\t\t\t{_uns("property", prop)}\n'
    s += f'\t\t\t{newv}\n'
    s += f'\t\t\t{_int("version", ver)}\n'
    s += f'\t\t\t{_int("db_random_id", rid)}\n'
    if extra:
        s += extra
    if odvl:
        s += f'\t\t\t{odvl}\n'
    return s

def _create(create_uid: int, person_uid: int, rid: int, ver: int) -> str:
    inner = f'\t\t\t{_int("database_table_type", TBL_CREATE)}\n'
    inner += f'\t\t\t{_large("db_unique_id", create_uid)}\n'
    inner += f'\t\t\t{_uns("property", CREATE_PROPERTY)}\n'
    inner += '\t\t\t<record id="new_value">\n'
    inner += f'\t\t\t\t{_int("database_table_type", TBL_PLAYER)}\n'
    inner += f'\t\t\t\t{_uns("dcty", 2)}\n'
    inner += f'\t\t\t\t{_large("db_unique_id", person_uid)}\n'
    inner += '\t\t\t</record>\n'
    inner += f'\t\t\t{_int("version", ver)}\n'
    inner += f'\t\t\t{_int("db_random_id", rid)}\n'
    inner += f'\t\t\t{_bool("is_client_field", True)}\n'
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
    fixed_height: Optional[int] = None,
    fixed_club: Optional[Tuple[int, int]] = None,
    fixed_city: Optional[Tuple[int, int]] = None,
    fixed_nation: Optional[Tuple[int, int]] = None,
    fixed_positions: Optional[List[str]] = None,
    nationality_info_value: int = 85,
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
    if fixed_height is not None and not (150 <= fixed_height <= 210):
        raise ValueError("height must be 150..210")

    clubs, cities, nations = load_master_library(library_csv)
    if not clubs:
        raise ValueError("No clubs loaded from master library")
    if not cities:
        raise ValueError("No cities loaded from master library")
    if not nations and fixed_nation is None:
        raise ValueError("No nations loaded (add at least Scotland)")

    first = _load_names(first_names_csv)
    sur = _load_names(surnames_csv)
    rng = random.Random(seed)

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

    frags = []
    lang_extra = '\t\t\t<string id="odvl" value=""/>\n\t\t\t<boolean id="is_language_field" value="true"/>\n'
    odvl0 = _int("odvl", 0)
    odvl_date = _date("odvl", dt.date(1900, 1, 1))

    for idx in range(count):
        i = start_index + existing + idx

        create_uid = _uniq(_id64, seed, i, "create_uid", used_create)
        person_uid = _uniq(_id64, seed, i, "person_uid", used64, extra_ok=person_ok)

        rid_create = _uniq(_id32, seed, i, "rid|create", used32)
        frags.append(_create(create_uid, person_uid, rid_create, version))

        fn = rng.choice(first)
        sn = rng.choice(sur)
        cn = f"{fn} {sn}"
        height = fixed_height if fixed_height is not None else rng.randint(150, 210)
        dob = fixed_dob if fixed_dob is not None else _random_dob(rng, rng.randint(age_min, age_max), base_year)

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

        pos_sel = [p.strip().upper() for p in (fixed_positions or []) if p.strip()]
        pos_map = _pos_map(rng, pos_sel)

        left, right = _foot(rng)
        wage = rng.randint(20, 80)
        rep = 30
        tv = _tv_from_pa(pa)

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
            + '\t\t\t</record>'
        )
        frags.append(_rec(_attr(person_uid, CITY_PROPERTY, newv, rid("rid|city"), version, odvl=_null("odvl")), "City of birth"))

        # nation record (+ odvl record)
        newv = (
            '<record id="new_value">\n'
            + f'\t\t\t\t{_large("Nnat", nation_large)}\n'
            + f'\t\t\t\t{_int("DBID", nation_dbid)}\n'
            + '\t\t\t</record>'
        )
        odvl = (
            '<record id="odvl">\n'
            + f'\t\t\t\t{_large("Nnat", DEFAULT_NNAT_ODVL)}\n'
            + '\t\t\t</record>'
        )
        frags.append(_rec(_attr(person_uid, NATION_PROPERTY, newv, rid("rid|nation"), version, odvl=odvl), "Nation"))

        # nationality info
        frags.append(_rec(_attr(person_uid, PROP_NATIONALITY_INFO, _int("new_value", int(nationality_info_value)), rid("rid|ninfo"), version, odvl=odvl0), "Nationality Info"))

        # club record
        newv = (
            '<record id="new_value">\n'
            + f'\t\t\t\t{_large("Ttea", club_large)}\n'
            + f'\t\t\t\t{_int("DBID", club_dbid)}\n'
            + '\t\t\t</record>'
        )
        frags.append(_rec(_attr(person_uid, CLUB_PROPERTY, newv, rid("rid|club"), version, odvl=_null("odvl")), "Club"))

        # other ints/dates
        frags.append(_rec(_attr(person_uid, PROP_WAGE, _int("new_value", wage), rid("rid|wage"), version, odvl=odvl0), "Wage"))
        frags.append(_rec(_attr(person_uid, PROP_DATE_MOVED_TO_NATION, _date("new_value", dob), rid("rid|moved"), version, odvl=odvl_date), "Moved to nation"))
        frags.append(_rec(_attr(person_uid, PROP_DATE_JOINED_CLUB, _date("new_value", joined), rid("rid|joined"), version, odvl=odvl_date), "Joined club"))
        frags.append(_rec(_attr(person_uid, PROP_DATE_LAST_SIGNED, _date("new_value", joined), rid("rid|signed"), version, odvl=odvl_date), "Last signed"))
        frags.append(_rec(_attr(person_uid, PROP_CONTRACT_EXPIRES, _date("new_value", expires), rid("rid|expires"), version, odvl=odvl_date), "Contract expires"))
        frags.append(_rec(_attr(person_uid, PROP_SQUAD_STATUS, _int("new_value", 9), rid("rid|squad"), version, odvl=_null("odvl")), "Squad status"))
        frags.append(_rec(_attr(person_uid, PROP_CA, _int("new_value", ca), rid("rid|ca"), version, odvl=odvl0), "CA"))
        frags.append(_rec(_attr(person_uid, PROP_PA, _int("new_value", pa), rid("rid|pa"), version, odvl=odvl0), "PA"))
        frags.append(_rec(_attr(person_uid, PROP_CURRENT_REP, _int("new_value", rep), rid("rid|rep"), version, odvl=odvl0), "Current rep"))
        frags.append(_rec(_attr(person_uid, PROP_HOME_REP, _int("new_value", rep), rid("rid|rep_home"), version, odvl=odvl0), "Home rep"))
        frags.append(_rec(_attr(person_uid, PROP_WORLD_REP, _int("new_value", rep), rid("rid|rep_world"), version, odvl=odvl0), "World rep"))
        frags.append(_rec(_attr(person_uid, PROP_LEFT_FOOT, _str("new_value", str(left)), rid("rid|lf"), version, odvl=odvl0), "Left foot"))
        frags.append(_rec(_attr(person_uid, PROP_RIGHT_FOOT, _str("new_value", str(right)), rid("rid|rf"), version, odvl=odvl0), "Right foot"))
        frags.append(_rec(_attr(person_uid, PROP_TRANSFER_VALUE, _int("new_value", tv), rid("rid|tv"), version, odvl=odvl0), "Transfer value"))

        # positions
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
    ap.add_argument("--version", type=int, default=DEFAULT_VERSION)
    ap.add_argument("--dob", default="")
    ap.add_argument("--height", type=int, default=0)
    ap.add_argument("--club_dbid", type=int, default=0)
    ap.add_argument("--club_large", type=int, default=0)
    ap.add_argument("--city_dbid", type=int, default=0)
    ap.add_argument("--city_large", type=int, default=0)
    ap.add_argument("--nation_dbid", type=int, default=0)
    ap.add_argument("--nation_large", type=int, default=0)
    ap.add_argument("--positions", default="")
    ap.add_argument("--nationality_info_value", type=int, default=85)
    ap.add_argument("--first_names", default="scottish_male_first_names_2500.csv")
    ap.add_argument("--surnames", default="scottish_surnames_2500.csv")
    args = ap.parse_args(argv)

    if args.pa_min > 200 or args.pa_max > 200:
        print("[FAIL] PA must be within 0..200 (you passed >200).", file=sys.stderr)
        return 2
    if args.ca_min > 200 or args.ca_max > 200:
        print("[FAIL] CA must be within 0..200.", file=sys.stderr)
        return 2

    fixed_dob = _parse_ymd(args.dob) if args.dob else None
    fixed_height = args.height if args.height else None
    fixed_club = (args.club_dbid, args.club_large) if (args.club_dbid and args.club_large) else None
    fixed_city = (args.city_dbid, args.city_large) if (args.city_dbid and args.city_large) else None
    fixed_nation = (args.nation_dbid, args.nation_large) if (args.nation_dbid and args.nation_large) else None

    fixed_positions = None
    if args.positions:
        pos = [p.strip().upper() for p in args.positions.split(",") if p.strip()]
        if len(pos) == 1 and pos[0] == "RANDOM":
            fixed_positions = []
        else:
            for p in pos:
                if p not in POS_PROPS:
                    print(f"[FAIL] Unknown position: {p}. Allowed: {', '.join(ALL_POS)} or random", file=sys.stderr)
                    return 2
            fixed_positions = pos

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
            fixed_height=fixed_height,
            fixed_club=fixed_club,
            fixed_city=fixed_city,
            fixed_nation=fixed_nation,
            fixed_positions=fixed_positions,
            nationality_info_value=args.nationality_info_value,
        )
    except Exception as e:
        print(f"[FAIL] {e}", file=sys.stderr)
        return 1

    print(f"[OK] Wrote: {args.output} (count={args.count}, append={args.append})")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
