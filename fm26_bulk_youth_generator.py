#!/usr/bin/env python3
"""FM26 Bulk Youth Generator (DB Changes XML)

Generates Football Manager 26 Editor "db changes" XML with randomly generated youth players.

Key feature: deterministic, collision-safe ID generation using SHA-256 as specified:
  digest = SHA256(f"{seed}|{i}|{label}")
  n = int.from_bytes(digest, "big")
  int32  = 1 + (n % 2147483646)
  int64  = 1 + (n % 9223372036854775806)

If collisions happen in one file, we re-hash with label+"|1", "|2", ...

Usage:
  python fm26_bulk_youth_generator.py --clubs_cities clubs_cities.csv --count 10 --output fm26_youth.xml \
      --age_min 14 --age_max 16 --ca_min 20 --ca_max 160 --pa_min 80 --pa_max 200 --seed 123

Inputs:
  - clubs_cities.csv (from fm_dbchanges_extract_fixed_v4.py)
  - scottish_male_first_names_2500.csv (header: name)
  - scottish_surnames_2500.csv (header: name)

Notes:
  - CSV rows may have blanks (clubs have no city fields and vice versa). We skip blanks safely.
  - Nationality is always included (Scotland constants from your sample XML).
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# DO NOT CHANGE (per user requirement)
CITY_PROPERTY = 1348690537
CLUB_PROPERTY = 1348695145

# From your sample XML (keep nationality included)
SCOTLAND_DBID = 793
SCOTLAND_NNAT = 3405909066521
SCOTLAND_ODVL_NNAT = 3285649982205
NATIONALITY_INFO_VALUE = 85

# Core property IDs from your sample (used in output)
PROP_FIRST_NAME = 1348890209
PROP_SECOND_NAME = 1349742177
PROP_COMMON_NAME = 1348693601
PROP_HEIGHT = 1349018995
PROP_DOB = 1348759394
PROP_CITY_OF_BIRTH = CITY_PROPERTY
PROP_NATION = 1349416041
PROP_NATIONALITY_INFO = 1349415497
PROP_CLUB = CLUB_PROPERTY
PROP_WAGE = 1348695911
PROP_DATE_MOVED_TO_NATION = 1346588266
PROP_CONTRACT_EXPIRES = 1348691320
PROP_SQUAD_STATUS = 1347253105
PROP_CA = 1346584898
PROP_PA = 1347436866
PROP_REP_CURRENT = 1346589264
PROP_REP_HOME = 1346916944
PROP_REP_WORLD = 1347899984
PROP_LEFT_FOOT = 1346661478
PROP_RIGHT_FOOT = 1346663017

# Optional-but-useful contract fields from your sample
PROP_DATE_JOINED_CLUB = 1348692580
PROP_DATE_LAST_SIGNED = 1348694884
PROP_TRANSFER_VALUE = 1348630085

# Position properties (from your sample)
PROP_POS_GK = 1348956001
PROP_POS_DL = 1348758643
PROP_POS_DC = 1348756325
PROP_POS_DR = 1348760179
PROP_POS_DM = 1348758883
PROP_POS_WBL = 1350001260
PROP_POS_WBR = 1350001266
PROP_POS_ML = 1349348467
PROP_POS_MC = 1349346149
PROP_POS_MR = 1349350003
PROP_POS_AML = 1348562284
PROP_POS_AMC = 1348562275
PROP_POS_AMR = 1348562290
PROP_POS_ST = 1348559717

ALL_POS_PROPS = [
    PROP_POS_GK,
    PROP_POS_DL, PROP_POS_DC, PROP_POS_DR,
    PROP_POS_DM,
    PROP_POS_WBL, PROP_POS_WBR,
    PROP_POS_ML, PROP_POS_MC, PROP_POS_MR,
    PROP_POS_AML, PROP_POS_AMC, PROP_POS_AMR,
    PROP_POS_ST,
]

# XML constants
XML_VERSION = 3727
RULE_GROUP_VERSION = 1630
ORVS = "2600"
SVVS = "2600"


def excel_safe_text(n_str: str) -> str:
    return f'="{n_str}"'


def _read_name_csv(path: Path) -> List[str]:
    with path.open("r", encoding="utf-8", newline="") as f:
        r = csv.DictReader(f)
        if not r.fieldnames or "name" not in r.fieldnames:
            raise ValueError(f"Expected a 'name' column in {path}")
        out: List[str] = []
        for row in r:
            val = (row.get("name") or "").strip()
            if val:
                out.append(val)
        if not out:
            raise ValueError(f"No names found in {path}")
        return out


@dataclass(frozen=True)
class Club:
    dbid: int
    large: int
    name: str = ""


@dataclass(frozen=True)
class City:
    dbid: int
    large: int
    name: str = ""


def _to_int(s: Optional[str]) -> Optional[int]:
    """Parse integers from CSV cells robustly.

    Supports:
      - plain ints: 123
      - Excel-safe text/formulas: ="123"
      - quoted: "123"
      - scientific notation strings: 6.743E+12 (best-effort via Decimal)
    """
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None

    # Excel-safe formula like ="123456"
    m = re.search(r"(\d+)", s)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            pass

    # scientific notation (best-effort; may already have lost precision if Excel rewrote it)
    if re.fullmatch(r"[0-9]+(\.[0-9]+)?[eE][+-]?[0-9]+", s):
        try:
            from decimal import Decimal
            return int(Decimal(s))
        except Exception:
            return None

    try:
        return int(s)
    except Exception:
        return None


def load_clubs_cities(path: Path) -> Tuple[List[Club], List[City]]:
    """Load clubs/cities from a combined CSV.

    Expected columns (case-insensitive; extra columns ignored):
      type, club_dbid, club_large, club_name, city_dbid, city_large, city_name

    Backwards-compatible column aliases:
      - kind (alias of type)
      - ttea_large / ttea_large_text (alias of club_large / club_large_text)

    Also supports Excel-safe columns produced by the extractor:
      club_dbid_text, club_large_text, city_dbid_text, city_large_text

    Handles common gotchas:
      - CSV saved by Excel with ';' separator (auto-detected)
      - numbers rewritten in scientific notation (prefers *_text columns)
      - whitespace / case differences in headers
    """
    clubs: Dict[Tuple[int, int], Club] = {}
    cities: Dict[Tuple[int, int], City] = {}

    with path.open("r", encoding="utf-8-sig", newline="") as f:
        sample = f.read(4096)
        f.seek(0)

        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=[",", ";", "\t", "|"])
        except Exception:
            dialect = csv.excel  # comma by default

        r = csv.DictReader(f, dialect=dialect)
        if not r.fieldnames:
            raise ValueError("clubs_cities.csv has no header")

        first_data_row_preview: Optional[Dict[str, Any]] = None

        for row in r:
            # normalize keys to be resilient to Excel/header edits
            rown = {(k or "").strip().lower(): v for k, v in row.items()}

            if first_data_row_preview is None and any((v or "").strip() for v in rown.values()):
                first_data_row_preview = dict(list(rown.items())[:12])

            t = (rown.get("type") or rown.get("kind") or rown.get("row_type") or "").strip().lower()

            club_dbid = _to_int(rown.get("club_dbid")) or _to_int(rown.get("club_dbid_text"))

            # club_large may appear as club_large, ttea_large, or (rarely) ttea
            club_large = (
                _to_int(rown.get("club_large") or rown.get("ttea_large") or rown.get("ttea"))
                or _to_int(rown.get("club_large_text") or rown.get("ttea_large_text"))
            )
            club_name = (rown.get("club_name") or "").strip()

            city_dbid = _to_int(rown.get("city_dbid")) or _to_int(rown.get("city_dbid_text"))
            city_large = _to_int(rown.get("city_large")) or _to_int(rown.get("city_large_text"))
            city_name = (rown.get("city_name") or "").strip()

            if t == "club":
                if club_dbid is None or club_large is None:
                    continue
                key = (club_dbid, club_large)
                if key not in clubs:
                    clubs[key] = Club(dbid=club_dbid, large=club_large, name=club_name)

            elif t == "city":
                if city_dbid is None or city_large is None:
                    continue
                key = (city_dbid, city_large)
                if key not in cities:
                    cities[key] = City(dbid=city_dbid, large=city_large, name=city_name)

    if not clubs:
        raise ValueError(
            "No clubs loaded from clubs_cities.csv. "
            "Check that the file contains rows where type=club (or kind=club) and club_dbid/club_large (or ttea_large) are present. "
            f"Detected headers: {list((r.fieldnames or []))}. "
            f"First row preview: {first_data_row_preview}"
        )
    if not cities:
        raise ValueError(
            "No cities loaded from clubs_cities.csv. "
            "Check that the file contains rows where type=city and city_dbid/city_large are present. "
            f"Detected headers: {list((r.fieldnames or []))}. "
            f"First row preview: {first_data_row_preview}"
        )
    return list(clubs.values()), list(cities.values())



class StableIdGenerator:
    def __init__(self, seed: int):
        self.seed = seed
        self.used_int32: Set[int] = set()
        self.used_int64_person: Set[int] = set()
        self.used_int64_change: Set[int] = set()
        # FM appears to key some identifiers by low 32 bits; keep those unique too.
        self.used_person_low32: Set[int] = set()
        self.used_change_low32: Set[int] = set()

    @staticmethod
    def _sha_to_int(seed: int, i: int, label: str) -> int:
        digest = hashlib.sha256(f"{seed}|{i}|{label}".encode("utf-8")).digest()
        return int.from_bytes(digest, "big")

    def _unique(self, used: Set[int], seed: int, i: int, label: str, modulus: int) -> int:
        # collision-safe with deterministic suffix
        k = 0
        while True:
            lbl = label if k == 0 else f"{label}|{k}"
            n = self._sha_to_int(seed, i, lbl)
            val = 1 + (n % modulus)
            if val not in used:
                used.add(val)
                return val
            k += 1

    def int32(self, i: int, label: str) -> int:
        return self._unique(self.used_int32, self.seed, i, label, 2147483646)

    def int64_person(self, i: int, label: str) -> int:
        """Signed-safe int64 for person db_unique_id.

        FM26 appears to silently reject person records when the low 32 bits of the
        db_unique_id are >= 2^31 (2147483648). We enforce:
            (val & 0xFFFFFFFF) < 2147483648

        This stays deterministic by re-hashing with a suffix label|k until valid,
        and also remains collision-safe within one file.
        """
        modulus = 9223372036854775806
        k = 0
        while True:
            lbl = label if k == 0 else f"{label}|{k}"
            n = self._sha_to_int(self.seed, i, lbl)
            val = 1 + (n % modulus)
            # signed-safe low 32-bit requirement
            if (val & 0xFFFFFFFF) >= 2147483648:
                k += 1
                continue
            low32 = val & 0xFFFFFFFF
            if val not in self.used_int64_person and low32 not in self.used_person_low32:
                self.used_int64_person.add(val)
                self.used_person_low32.add(low32)
                return val
            k += 1

    def int64_change(self, i: int, label: str) -> int:
        """Signed-safe int64 for change record db_unique_id.

        In practice FM seems happiest when the low 32 bits are < 2^31 and
        also unique within the file, similar to person ids.
        """
        modulus = 9223372036854775806
        k = 0
        while True:
            lbl = label if k == 0 else f"{label}|{k}"
            n = self._sha_to_int(self.seed, i, lbl)
            val = 1 + (n % modulus)
            low32 = val & 0xFFFFFFFF
            if low32 >= 2147483648:
                k += 1
                continue
            if val not in self.used_int64_change and low32 not in self.used_change_low32:
                self.used_int64_change.add(val)
                self.used_change_low32.add(low32)
                return val
            k += 1


def _date_dict_to_xml(tag_id: str, day: int, month: int, year: int, time: int = 0) -> str:
    return f'<date id="{tag_id}" day="{day}" month="{month}" year="{year}" time="{time}"/>'


def _record_header(db_unique_id: int, prop: int, new_value_xml: str, *, db_random_id: int, extra: str = "") -> str:
    # extra can include odvl / language flags etc.
    return (
        "\t\t<record>\n"
        "\t\t\t<integer id=\"database_table_type\" value=\"1\"/>\n"
        f"\t\t\t<large id=\"db_unique_id\" value=\"{db_unique_id}\"/>\n"
        f"\t\t\t<unsigned id=\"property\" value=\"{prop}\"/>\n"
        f"\t\t\t{new_value_xml}\n"
        f"\t\t\t<integer id=\"version\" value=\"{XML_VERSION}\"/>\n"
        f"\t\t\t<integer id=\"db_random_id\" value=\"{db_random_id}\"/>\n"
        f"{extra}"
        "\t\t</record>\n"
    )


def _string_new_value(val: str) -> str:
    # Escape minimally for XML attributes
    val = val.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<string id="new_value" value="{val}"/>'


def _integer_new_value(val: int) -> str:
    return f'<integer id="new_value" value="{val}"/>'


def _null_odvl() -> str:
    return "\t\t\t<null id=\"odvl\"/>\n"


def _int_odvl(v: int = 0) -> str:
    return f"\t\t\t<integer id=\"odvl\" value=\"{v}\"/>\n"


def _string_odvl_empty() -> str:
    return "\t\t\t<string id=\"odvl\" value=\"\"/>\n"


def _lang_flag() -> str:
    return "\t\t\t<boolean id=\"is_language_field\" value=\"true\"/>\n"


def _nation_new_value() -> str:
    return (
        "<record id=\"new_value\">"
        f"<large id=\"Nnat\" value=\"{SCOTLAND_NNAT}\"/>"
        f"<integer id=\"DBID\" value=\"{SCOTLAND_DBID}\"/>"
        "</record>"
    )


def _nation_odvl() -> str:
    return (
        "\t\t\t<record id=\"odvl\">\n"
        f"\t\t\t\t<large id=\"Nnat\" value=\"{SCOTLAND_ODVL_NNAT}\"/>\n"
        "\t\t\t</record>\n"
    )


def _club_new_value(club: Club) -> str:
    return (
        "<record id=\"new_value\">"
        f"<large id=\"Ttea\" value=\"{club.large}\"/>"
        f"<integer id=\"DBID\" value=\"{club.dbid}\"/>"
        "</record>"
    )


def _city_new_value(city: City) -> str:
    return (
        "<record id=\"new_value\">"
        f"<large id=\"city\" value=\"{city.large}\"/>"
        f"<integer id=\"DBID\" value=\"{city.dbid}\"/>"
        "</record>"
    )


def _random_date_for_age(rng: random.Random, base_year: int, age: int) -> Tuple[int, int, int]:
    year = base_year - age
    month = rng.randint(1, 12)
    day = rng.randint(1, 28)
    return day, month, year


def _transfer_value_from_pa(pa: int) -> int:
    # Simple scale: PA 80..200 -> 100k..50m
    lo_pa, hi_pa = 80, 200
    lo_val, hi_val = 100_000, 50_000_000
    pa_clamped = max(lo_pa, min(hi_pa, pa))
    t = (pa_clamped - lo_pa) / (hi_pa - lo_pa)
    return int(lo_val + t * (hi_val - lo_val))


def _pick_foot(rng: random.Random) -> Tuple[int, int]:
    # returns (left, right) on 1..20
    r = rng.random()
    if r < 0.75:
        # right footed
        right = rng.randint(17, 20)
        left = rng.randint(1, 12)
    elif r < 0.93:
        # left footed
        left = rng.randint(17, 20)
        right = rng.randint(1, 12)
    else:
        # both
        left = rng.randint(15, 20)
        right = rng.randint(15, 20)
    return left, right


def _pick_position_profile(rng: random.Random) -> Dict[int, int]:
    # Return mapping of position property -> value (1..20)
    out = {p: 1 for p in ALL_POS_PROPS}

    r = rng.random()
    if r < 0.10:
        primary = PROP_POS_GK
    elif r < 0.45:
        primary = rng.choice([PROP_POS_DL, PROP_POS_DC, PROP_POS_DR, PROP_POS_WBL, PROP_POS_WBR])
    elif r < 0.85:
        primary = rng.choice([PROP_POS_DM, PROP_POS_ML, PROP_POS_MC, PROP_POS_MR, PROP_POS_AML, PROP_POS_AMC, PROP_POS_AMR])
    else:
        primary = PROP_POS_ST

    if primary == PROP_POS_GK:
        out[PROP_POS_GK] = rng.randint(15, 20)
        return out

    out[primary] = rng.randint(15, 20)

    # Add a light secondary chance for adjacent roles
    if primary in (PROP_POS_DL, PROP_POS_WBL):
        out[PROP_POS_DL] = max(out[PROP_POS_DL], rng.randint(10, 16))
        out[PROP_POS_WBL] = max(out[PROP_POS_WBL], rng.randint(10, 16))
        out[PROP_POS_ML] = max(out[PROP_POS_ML], rng.randint(6, 12))
    elif primary in (PROP_POS_DR, PROP_POS_WBR):
        out[PROP_POS_DR] = max(out[PROP_POS_DR], rng.randint(10, 16))
        out[PROP_POS_WBR] = max(out[PROP_POS_WBR], rng.randint(10, 16))
        out[PROP_POS_MR] = max(out[PROP_POS_MR], rng.randint(6, 12))
    elif primary == PROP_POS_DC:
        out[PROP_POS_DC] = max(out[PROP_POS_DC], rng.randint(15, 20))
        out[PROP_POS_DM] = max(out[PROP_POS_DM], rng.randint(6, 12))
    elif primary == PROP_POS_DM:
        out[PROP_POS_DM] = max(out[PROP_POS_DM], rng.randint(15, 20))
        out[PROP_POS_MC] = max(out[PROP_POS_MC], rng.randint(6, 12))
    elif primary in (PROP_POS_MC, PROP_POS_AMC):
        out[PROP_POS_MC] = max(out[PROP_POS_MC], rng.randint(12, 18))
        out[PROP_POS_AMC] = max(out[PROP_POS_AMC], rng.randint(8, 16))
        out[PROP_POS_DM] = max(out[PROP_POS_DM], rng.randint(4, 10))
    elif primary == PROP_POS_ST:
        out[PROP_POS_ST] = max(out[PROP_POS_ST], rng.randint(15, 20))
        out[PROP_POS_AMC] = max(out[PROP_POS_AMC], rng.randint(4, 10))

    out[PROP_POS_GK] = 1
    return out


def build_player_records(
    *,
    i: int,
    idgen: StableIdGenerator,
    rng: random.Random,
    first_name: str,
    surname: str,
    club: Club,
    city: City,
    age: int,
    ca: int,
    pa: int,
    base_year: int,
    manifest_sink=None,
) -> str:
    # IDs
    person_id = idgen.int64_person(i, "person_id")
    change_uid = idgen.int64_change(i, "change_uid")

    # Random properties
    common_name = first_name
    height = rng.randint(150, 210)

    dob_day, dob_month, dob_year = _random_date_for_age(rng, base_year, age)

    left_foot, right_foot = _pick_foot(rng)
    pos = _pick_position_profile(rng)


    # Optional manifest row (helps debug missing imports)
    if manifest_sink is not None:
        primary_pos_prop = max(pos.items(), key=lambda kv: kv[1])[0] if pos else ""
        manifest_sink.writerow([
            i,
            change_uid,
            person_id,
            first_name,
            surname,
            f"{dob_year:04d}-{dob_month:02d}-{dob_day:02d}",
            age,
            ca,
            pa,
            club.dbid,
            club.large,
            club.name,
            city.dbid,
            city.large,
            city.name,
            left_foot,
            right_foot,
            primary_pos_prop,
        ])

    wage = rng.randint(0, 200)
    rep_current = rng.randint(0, 50)
    rep_home = rng.randint(0, 60)
    rep_world = rng.randint(0, 60)

    transfer_value = _transfer_value_from_pa(pa)

    # Constant-ish dates (match your examples)
    joined_day, joined_month, joined_year = 1, 2, 2025
    exp_day, exp_month, exp_year = 28, 2, 2029

    # 1) Player "create" record (database_table_type=55)
    recs = []
    recs.append(
        "\t\t<record><!-- This is require per player record -->\n"
        "\t\t\t<integer id=\"database_table_type\" value=\"55\"/>\n"
        f"\t\t\t<large id=\"db_unique_id\" value=\"{change_uid}\"/>\n"
        "\t\t\t<unsigned id=\"property\" value=\"1094992978\"/>\n"
        "\t\t\t<record id=\"new_value\">\n"
        "\t\t\t\t<integer id=\"database_table_type\" value=\"1\"/>\n"
        "\t\t\t\t<unsigned id=\"dcty\" value=\"2\"/>\n"
        f"\t\t\t\t<large id=\"db_unique_id\" value=\"{person_id}\"/>\n"
        "\t\t\t</record>\n"
        f"\t\t\t<integer id=\"version\" value=\"{XML_VERSION}\"/>\n"
        f"\t\t\t<integer id=\"db_random_id\" value=\"{idgen.int32(i, 'create_random')}\"/>\n"
        "\t\t\t<boolean id=\"is_client_field\" value=\"true\"/>\n"
        "\t\t</record>\n"
    )

    # Helpers for IDs per record
    def rid(lbl: str) -> int:
        return idgen.int32(i, lbl)

    # 2) Names
    recs.append(
        _record_header(
            person_id,
            PROP_FIRST_NAME,
            _string_new_value(first_name),
            db_random_id=rid("first_name"),
            extra=_string_odvl_empty() + _lang_flag(),
        )
    )
    recs.append(
        _record_header(
            person_id,
            PROP_SECOND_NAME,
            _string_new_value(surname),
            db_random_id=rid("second_name"),
            extra=_string_odvl_empty() + _lang_flag(),
        )
    )
    recs.append(
        _record_header(
            person_id,
            PROP_COMMON_NAME,
            _string_new_value(common_name),
            db_random_id=rid("common_name"),
            extra=_string_odvl_empty() + _lang_flag(),
        )
    )

    # 3) Bio-ish basics
    recs.append(_record_header(person_id, PROP_HEIGHT, _integer_new_value(height), db_random_id=rid("height"), extra=_int_odvl(0)))
    recs.append(
        _record_header(
            person_id,
            PROP_DOB,
            _date_dict_to_xml("new_value", dob_day, dob_month, dob_year),
            db_random_id=rid("dob"),
            extra=f"\t\t\t{_date_dict_to_xml('odvl', 1, 1, 1900)}\n",
        )
    )

    # 4) City of birth
    recs.append(
        _record_header(
            person_id,
            PROP_CITY_OF_BIRTH,
            _city_new_value(city),
            db_random_id=rid("city"),
            extra=_null_odvl(),
        )
    )

    # 5) Nation + nationality info
    recs.append(
        _record_header(
            person_id,
            PROP_NATION,
            _nation_new_value(),
            db_random_id=rid("nation"),
            extra=_nation_odvl(),
        )
    )
    recs.append(
        _record_header(
            person_id,
            PROP_NATIONALITY_INFO,
            _integer_new_value(NATIONALITY_INFO_VALUE),
            db_random_id=rid("nat_info"),
            extra=_int_odvl(0),
        )
    )

    # 6) Club
    recs.append(
        _record_header(
            person_id,
            PROP_CLUB,
            _club_new_value(club),
            db_random_id=rid("club"),
            extra=_null_odvl(),
        )
    )

    # 7) Contract fields
    recs.append(_record_header(person_id, PROP_WAGE, _integer_new_value(wage), db_random_id=rid("wage"), extra=_int_odvl(0)))

    # date joined club
    recs.append(
        _record_header(
            person_id,
            PROP_DATE_JOINED_CLUB,
            _date_dict_to_xml("new_value", joined_day, joined_month, joined_year),
            db_random_id=rid("date_joined"),
            extra=f"\t\t\t{_date_dict_to_xml('odvl', 1, 7, joined_year)}\n",
        )
    )

    # date moved to nation (set to DOB)
    recs.append(
        _record_header(
            person_id,
            PROP_DATE_MOVED_TO_NATION,
            _date_dict_to_xml("new_value", dob_day, dob_month, dob_year),
            db_random_id=rid("date_moved"),
            extra=f"\t\t\t{_date_dict_to_xml('odvl', 1, 1, 1900)}\n",
        )
    )

    # date last signed
    recs.append(
        _record_header(
            person_id,
            PROP_DATE_LAST_SIGNED,
            _date_dict_to_xml("new_value", joined_day, joined_month, joined_year),
            db_random_id=rid("date_signed"),
            extra=f"\t\t\t{_date_dict_to_xml('odvl', 1, 7, joined_year)}\n",
        )
    )

    # contract expires
    recs.append(
        _record_header(
            person_id,
            PROP_CONTRACT_EXPIRES,
            _date_dict_to_xml("new_value", exp_day, exp_month, exp_year),
            db_random_id=rid("contract_expires"),
            extra=f"\t\t\t{_date_dict_to_xml('odvl', 1, 1, 1900)}\n",
        )
    )

    # squad status
    recs.append(_record_header(person_id, PROP_SQUAD_STATUS, _integer_new_value(9), db_random_id=rid("squad_status"), extra=_null_odvl()))

    # 8) Abilities
    recs.append(_record_header(person_id, PROP_CA, _integer_new_value(ca), db_random_id=rid("ca"), extra=_int_odvl(0)))
    recs.append(_record_header(person_id, PROP_PA, _integer_new_value(pa), db_random_id=rid("pa"), extra=_int_odvl(0)))

    # 9) Reputation
    recs.append(_record_header(person_id, PROP_REP_CURRENT, _integer_new_value(rep_current), db_random_id=rid("rep_current"), extra=_int_odvl(0)))
    recs.append(_record_header(person_id, PROP_REP_HOME, _integer_new_value(rep_home), db_random_id=rid("rep_home"), extra=_int_odvl(0)))
    recs.append(_record_header(person_id, PROP_REP_WORLD, _integer_new_value(rep_world), db_random_id=rid("rep_world"), extra=_int_odvl(0)))

    # 10) Feet (strings)
    recs.append(_record_header(person_id, PROP_LEFT_FOOT, _string_new_value(str(left_foot)), db_random_id=rid("left_foot"), extra=_int_odvl(0)))
    recs.append(_record_header(person_id, PROP_RIGHT_FOOT, _string_new_value(str(right_foot)), db_random_id=rid("right_foot"), extra=_int_odvl(0)))

    # 11) Transfer value
    recs.append(_record_header(person_id, PROP_TRANSFER_VALUE, _integer_new_value(transfer_value), db_random_id=rid("transfer_value"), extra=_int_odvl(0)))

    # 12) Positions
    for prop_id, val in pos.items():
        recs.append(_record_header(person_id, prop_id, _integer_new_value(val), db_random_id=rid(f"pos_{prop_id}"), extra=_int_odvl(0)))

    return "".join(recs)


def build_xml(players_xml: str) -> str:
    return (
        "<record>\n"
        "\t<list id=\"verf\"/>\n"
        "\t<list id=\"db_changes\">\n"
        f"{players_xml}"
        "\t</list>\n"
        "\t<integer id=\"EDvb\" value=\"1\"/>\n"
        "\t<string id=\"EDfb\" value=\"\"/>\n"
        f"\t<integer id=\"version\" value=\"{XML_VERSION}\"/>\n"
        f"\t<integer id=\"rule_group_version\" value=\"{RULE_GROUP_VERSION}\"/>\n"
        "\t<boolean id=\"beta\" value=\"false\"/>\n"
        f"\t<string id=\"orvs\" value=\"{ORVS}\"/>\n"
        f"\t<string id=\"svvs\" value=\"{SVVS}\"/>\n"
        "</record>\n"
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate FM26 DB Changes XML of youth players with stable IDs.")
    p.add_argument("--clubs_cities", required=True, help="Input clubs_cities.csv")
    p.add_argument("--count", type=int, required=True, help="Number of players to generate")
    p.add_argument("--output", required=True, help="Output XML path")

    p.add_argument("--age_min", type=int, default=14)
    p.add_argument("--age_max", type=int, default=16)
    p.add_argument("--ca_min", type=int, default=20)
    p.add_argument("--ca_max", type=int, default=160)
    p.add_argument("--pa_min", type=int, default=80)
    p.add_argument("--pa_max", type=int, default=200)

    p.add_argument("--seed", type=int, default=None, help="Seed for deterministic output")
    p.add_argument("--start_index", type=int, default=0, help="Start index offset for deterministic IDs (useful when generating multiple files)")
    p.add_argument("--base_year", type=int, default=2025, help="Base year used to compute DOB from age")

    p.add_argument(
        "--first_names",
        default=str(Path(__file__).with_name("scottish_male_first_names_2500.csv")),
        help="CSV of first names (header: name)",
    )
    p.add_argument(
        "--surnames",
        default=str(Path(__file__).with_name("scottish_surnames_2500.csv")),
        help="CSV of surnames (header: name)",
    )
    p.add_argument(
        "--chunk_size",
        type=int,
        default=0,
        help="If >0, split output into multiple XML files of this many players each (recommended for very large imports)",
    )
    p.add_argument(
        "--manifest",
        default="",
        help="Optional path to write a manifest CSV of generated players (IDs/names/club/city/CA/PA)",
    )

    return p.parse_args()




def main() -> int:
    args = parse_args()

    clubs_cities_path = Path(args.clubs_cities)
    out_path = Path(args.output)

    if args.count <= 0:
        raise SystemExit("--count must be > 0")

    # Basic sanity checks (avoids confusing FM import behavior).
    if args.age_min > args.age_max:
        raise SystemExit(f"--age_min ({args.age_min}) cannot be greater than --age_max ({args.age_max})")
    if args.ca_min > args.ca_max:
        raise SystemExit(f"--ca_min ({args.ca_min}) cannot be greater than --ca_max ({args.ca_max})")
    if args.pa_min > args.pa_max:
        raise SystemExit(f"--pa_min ({args.pa_min}) cannot be greater than --pa_max ({args.pa_max})")

    for k in ("ca_min", "ca_max", "pa_min", "pa_max"):
        v = int(getattr(args, k))
        if not (0 <= v <= 200):
            raise SystemExit(f"--{k} must be between 0 and 200 (FM ability scale). Got {v}.")

    # If no seed supplied, generate one but print it so the user can reproduce.
    seed = args.seed
    if seed is None:
        seed = random.SystemRandom().randint(1, 2147483646)
        print(f"[info] --seed not provided; using seed={seed}")

    rng = random.Random(seed)
    idgen = StableIdGenerator(seed)

    clubs, cities = load_clubs_cities(clubs_cities_path)

    first_names = _read_name_csv(Path(args.first_names))
    surnames = _read_name_csv(Path(args.surnames))


    # Split into multiple files if requested (helps avoid rare import drops on very large single files)
    chunk_size = int(args.chunk_size or 0)
    if chunk_size <= 0:
        chunk_size = args.count

    # Output paths
    outputs: List[Path] = []
    if chunk_size >= args.count:
        outputs = [out_path]
    else:
        stem = out_path.with_suffix("")
        suffix = out_path.suffix if out_path.suffix else ".xml"
        total_files = (args.count + chunk_size - 1) // chunk_size
        outputs = [Path(f"{stem}_{k:04d}{suffix}") for k in range(1, total_files + 1)]

    # Optional manifest CSV
    manifest_fp = None
    manifest_writer = None
    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_fp = manifest_path.open("w", newline="", encoding="utf-8")
        manifest_writer = csv.writer(manifest_fp)
        manifest_writer.writerow([
            "index",
            "change_uid",
            "person_id",
            "first_name",
            "surname",
            "dob",
            "age",
            "ca",
            "pa",
            "club_dbid",
            "club_large",
            "club_name",
            "city_dbid",
            "city_large",
            "city_name",
            "left_foot",
            "right_foot",
            "primary_pos_prop",
        ])

    XML_PREFIX = "<record>\n\t<list id=\"verf\"/>\n\t<list id=\"db_changes\">\n"
    XML_SUFFIX = (
        "\t</list>\n"
        "\t<integer id=\"EDvb\" value=\"1\"/>\n"
        "\t<string id=\"EDfb\" value=\"\"/>\n"
        f"\t<integer id=\"version\" value=\"{XML_VERSION}\"/>\n"
        f"\t<integer id=\"rule_group_version\" value=\"{RULE_GROUP_VERSION}\"/>\n"
        "\t<boolean id=\"beta\" value=\"false\"/>\n"
        "\t<string id=\"orvs\" value=\"2600\"/>\n"
        "\t<string id=\"svvs\" value=\"2600\"/>\n"
        "</record>\n"
    )

    # Stream-write XML (avoids huge RAM use and makes chunking easy)
    current_chunk = 0
    out_f = outputs[0].open("w", encoding="utf-8", newline="\n")
    out_f.write(XML_PREFIX)

    for local_i in range(args.count):
        chunk = local_i // chunk_size
        if chunk != current_chunk:
            out_f.write(XML_SUFFIX)
            out_f.close()
            current_chunk = chunk
            out_f = outputs[current_chunk].open("w", encoding="utf-8", newline="\n")
            out_f.write(XML_PREFIX)

        i = args.start_index + local_i
        first = rng.choice(first_names)
        last = rng.choice(surnames)

        club = rng.choice(clubs)
        city = rng.choice(cities)

        age = rng.randint(args.age_min, args.age_max)
        ca = rng.randint(args.ca_min, args.ca_max)
        pa = rng.randint(args.pa_min, args.pa_max)
        # FM tends to be happier when PA >= CA; clamp deterministically.
        if pa < ca:
            pa = min(args.pa_max, ca)
            if pa < ca:
                ca = pa

        out_f.write(
            build_player_records(
                i=i,
                idgen=idgen,
                rng=rng,
                first_name=first,
                surname=last,
                club=club,
                city=city,
                age=age,
                ca=ca,
                pa=pa,
                base_year=args.base_year,
                manifest_sink=manifest_writer,
            )
        )

    out_f.write(XML_SUFFIX)
    out_f.close()

    if manifest_fp is not None:
        manifest_fp.close()

    if len(outputs) == 1:
        print(f"Wrote {args.count} players to {outputs[0]}")
    else:
        print(f"Wrote {args.count} players split across {len(outputs)} files:")
        for p in outputs:
            print(f"  - {p}")

    return 0



if __name__ == "__main__":
    raise SystemExit(main())
