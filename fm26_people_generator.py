# FM26 PEOPLE GENERATOR - STABLE V3 - DO NOT EDIT BY HAND
#!/usr/bin/env python3
# [PATCH DISTRIBUTIONS PACK v3a]

"""FM26 Players Generator (db changes XML) - stable SHA256 IDs (randomized names across runs, v6.1 foot modes + weighted/frequency names).

Batch:
  python fm26_bulk_youth_generator2.py --master_library master_library.csv --count 10000 --output fm26_players.xml --seed 123

Single:
  python fm26_bulk_youth_generator2.py --master_library master_library.csv --count 1 --output fm26_players.xml --append \
    --dob 2012-12-31 --height 180 --club_dbid 1570 --club_large 6648609375756 --city_dbid 102580 --city_large 440573450358963 \
    --nation_dbid 793 --nation_large 3405909066521 --positions DL,DC --ca_min 120 --ca_max 120 --pa_min 180 --pa_max 180 --seed 123

Positions (new):
  # Primary position is forced to 20.
  # All other positions default to 1.
  # Optional extra 20-rated positions (outfield only) via --pos_20 or --pos_all_outfield_20.
  # Optional development positions (2..19) via --pos_dev (+ mode: random|fixed|range).
  GUI can apply development positions even when random primary is enabled (use --positions RANDOM + --pos_dev ...).
"""

from __future__ import annotations
import datetime as dt
import os
import random
import sys
from typing import Dict, List, Optional, Sequence, Tuple
from peoplegen import fm_props as _fm
# (FM constants extracted to peoplegen/fm_props.py)
CITY_PROPERTY = _fm.CITY_PROPERTY
CLUB_PROPERTY = _fm.CLUB_PROPERTY
NATION_PROPERTY = _fm.NATION_PROPERTY
CREATE_PROPERTY = _fm.CREATE_PROPERTY
TBL_PLAYER = _fm.TBL_PLAYER
TBL_CREATE = _fm.TBL_CREATE
PROP_FIRST_NAME = _fm.PROP_FIRST_NAME
PROP_SECOND_NAME = _fm.PROP_SECOND_NAME
PROP_COMMON_NAME = _fm.PROP_COMMON_NAME
PROP_FULL_NAME = _fm.PROP_FULL_NAME
PROP_PERSON_TYPE = _fm.PROP_PERSON_TYPE
PROP_GENDER = _fm.PROP_GENDER
PROP_ETHNICITY = _fm.PROP_ETHNICITY
PROP_HAIR_COLOUR = _fm.PROP_HAIR_COLOUR
PROP_HAIR_LENGTH = _fm.PROP_HAIR_LENGTH
PROP_SKIN_TONE = _fm.PROP_SKIN_TONE
PROP_BODY_TYPE = _fm.PROP_BODY_TYPE
PROP_HEIGHT = _fm.PROP_HEIGHT
PROP_DOB = _fm.PROP_DOB
PROP_NATIONALITY_INFO = _fm.PROP_NATIONALITY_INFO
PROP_RETIRING_AFTER_SPELL_CURRENT_CLUB = _fm.PROP_RETIRING_AFTER_SPELL_CURRENT_CLUB
PROP_WAGE = _fm.PROP_WAGE
PROP_DATE_MOVED_TO_NATION = _fm.PROP_DATE_MOVED_TO_NATION
PROP_DATE_JOINED_CLUB = _fm.PROP_DATE_JOINED_CLUB
PROP_DATE_LAST_SIGNED = _fm.PROP_DATE_LAST_SIGNED
PROP_CONTRACT_EXPIRES = _fm.PROP_CONTRACT_EXPIRES
PROP_SQUAD_STATUS = _fm.PROP_SQUAD_STATUS
PROP_CA = _fm.PROP_CA
PROP_PA = _fm.PROP_PA
PROP_CURRENT_REP = _fm.PROP_CURRENT_REP
PROP_HOME_REP = _fm.PROP_HOME_REP
PROP_WORLD_REP = _fm.PROP_WORLD_REP
PROP_LEFT_FOOT = _fm.PROP_LEFT_FOOT
PROP_RIGHT_FOOT = _fm.PROP_RIGHT_FOOT
PROP_TRANSFER_VALUE = _fm.PROP_TRANSFER_VALUE
DEFAULT_VERSION = _fm.DEFAULT_VERSION
DEFAULT_RULE_GROUP_VERSION = _fm.DEFAULT_RULE_GROUP_VERSION
DEFAULT_EDVB = _fm.DEFAULT_EDVB
DEFAULT_ORVS = _fm.DEFAULT_ORVS
DEFAULT_SVVS = _fm.DEFAULT_SVVS
DEFAULT_NNAT_ODVL = _fm.DEFAULT_NNAT_ODVL
INT32_MOD = _fm.INT32_MOD
INT64_MOD = _fm.INT64_MOD
PROP_DECLARED_FOR_YOUTH_NATION = _fm.PROP_DECLARED_FOR_YOUTH_NATION
PROP_SECOND_NATIONS = _fm.PROP_SECOND_NATIONS
PROP_INTERNATIONAL_RETIREMENT = _fm.PROP_INTERNATIONAL_RETIREMENT
PROP_INTERNATIONAL_RETIREMENT_DATE = _fm.PROP_INTERNATIONAL_RETIREMENT_DATE
PROP_INTERNATIONAL_APPS = _fm.PROP_INTERNATIONAL_APPS
PROP_INTERNATIONAL_GOALS = _fm.PROP_INTERNATIONAL_GOALS
PROP_U21_INTERNATIONAL_APPS = _fm.PROP_U21_INTERNATIONAL_APPS
PROP_U21_INTERNATIONAL_GOALS = _fm.PROP_U21_INTERNATIONAL_GOALS
PROP_INTERNATIONAL_DEBUT_DATE = _fm.PROP_INTERNATIONAL_DEBUT_DATE
PROP_INTERNATIONAL_DEBUT_AGAINST = _fm.PROP_INTERNATIONAL_DEBUT_AGAINST
PROP_U21_INTERNATIONAL_DEBUT_DATE = _fm.PROP_U21_INTERNATIONAL_DEBUT_DATE
PROP_U21_INTERNATIONAL_DEBUT_AGAINST = _fm.PROP_U21_INTERNATIONAL_DEBUT_AGAINST

from peoplegen import config as _cfg

from peoplegen import xml_helpers as _xmlh

from peoplegen import club_assign as _club

from peoplegen import economy as _eco

from peoplegen import emitter as _emit

from peoplegen import emit_blocks as _emitblk

from peoplegen import nationality_info as _natinfo

from peoplegen import validate as _val
# (validation extracted to peoplegen/validate.py)

# (nationality info mapping extracted to peoplegen/nationality_info.py)
resolve_nationality_info = _natinfo.resolve_nationality_info
nationality_info_mapping_lines = _natinfo.nationality_info_mapping_lines

# (emit blocks extracted to peoplegen/emit_blocks.py)

# (record emission extracted to peoplegen/emitter.py)

_tv_from_pa = _eco._tv_from_pa

# (economy logic extracted to peoplegen/economy.py)

# (club selection extracted to peoplegen/club_assign.py)

# (xml helpers extracted to peoplegen/xml_helpers.py)
_foot = _xmlh._foot
_rep_triplet = _xmlh._rep_triplet

# (config defaults extracted to peoplegen/config.py)
try:
    _cfg.configure_from_globals(globals())
except Exception:
    pass
_NAME_LOCAL_BIAS = _cfg._NAME_LOCAL_BIAS
_FEMALE_PCT = _cfg._FEMALE_PCT
_APPEARANCE_MODE = _cfg._APPEARANCE_MODE
_GLOBAL_ETH_RANGE = _cfg._GLOBAL_ETH_RANGE
_GLOBAL_SKIN_RANGE = _cfg._GLOBAL_SKIN_RANGE
_GLOBAL_HAIR_RANGE = _cfg._GLOBAL_HAIR_RANGE
_HAIR_LEN_WEIGHTS_MALE = _cfg._HAIR_LEN_WEIGHTS_MALE
_HAIR_LEN_WEIGHTS_FEMALE = _cfg._HAIR_LEN_WEIGHTS_FEMALE
_BODY_TYPE_W123 = _cfg._BODY_TYPE_W123
_BODY_TYPE_W4 = _cfg._BODY_TYPE_W4
_BODY_TYPE_W5 = _cfg._BODY_TYPE_W5

def generate_players_xml(
    library_csv: str,
    out_xml: str,
    count: int,
    seed: Optional[int] = None,
    append: bool = False,
    start_index: int = 0,
    age_min: int = 14,
    age_max: int = 30,
    ca_min: int = 70,
    ca_max: int = 160,
    pa_min: int = 110,
    pa_max: int = 200,
    base_year: int = 2025,
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
    date_last_signed: Optional[dt.date] = None,
    squad_status: Optional[int] = None,
    fixed_height: Optional[int] = None,
    height_min: int = 150,
    height_max: int = 210,
    fixed_club: Optional[Tuple[int, int]] = None,
    club_assign_pct: int = 100,
    fixed_city: Optional[Tuple[int, int]] = None,
    fixed_nation: Optional[Tuple[int, int]] = None,# new positions
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
    # Sync extracted config defaults from generator globals (CLI overrides, etc.)
    try:
        _cfg.configure_from_globals(globals())
    except Exception:
        pass

    # Sync second-nations module config from generator globals (CLI overrides, etc.)
    try:
        _sn.configure_from_globals(globals())
    except Exception:
        pass

    # Sync randomness module config from generator globals (body type weights, etc.)
    try:
        _rand.configure_from_globals(globals())
    except Exception:
        pass

    # Sync international module config from generator globals
    try:
        _intl.configure_from_globals(globals())
    except Exception:
        pass

    # Sync names module config from generator globals (appearance ranges, weights, etc.)
    try:
        _names.configure_from_globals(globals())
    except Exception:
        pass

    # Configure XML writer constants (extracted module)
    try:
        _xmlw.configure_tables(tbl_player=TBL_PLAYER, tbl_create=TBL_CREATE, create_property=CREATE_PROPERTY)
    except Exception:
        pass

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

    # Base-year sanity (prevents invalid dt.date() years if GUI input is wrong)
    try:
        by = int(base_year)
    except Exception:
        raise ValueError('base_year must be an integer')
    if by < 1 or by > 9999:
        raise ValueError('base_year must be in 1..9999')
    base_year = by

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

    # Validation extracted
    (wage_min, wage_max, wage,
     rep_min, rep_max, rep_current, rep_home, rep_world,
     transfer_mode, transfer_value, transfer_min, transfer_max,
     TV_LO, TV_HI,
     _omit_fields, _is_omitted) = _val.validate_and_prepare(
        wage_min=wage_min, wage_max=wage_max, wage=wage,
        rep_min=rep_min, rep_max=rep_max, rep_current=rep_current, rep_home=rep_home, rep_world=rep_world,
        transfer_mode=transfer_mode, transfer_value=transfer_value, transfer_min=transfer_min, transfer_max=transfer_max,
        fixed_height=fixed_height, height_min=height_min, height_max=height_max,
        dob_start=dob_start, dob_end=dob_end,
        moved_to_nation_date=moved_to_nation_date, joined_club_date=joined_club_date,
        international_retirement_date=international_retirement_date,
        international_debut_date=international_debut_date,
        u21_international_debut_date=u21_international_debut_date,
        international_apps=international_apps, international_goals=international_goals,
        u21_international_apps=u21_international_apps, u21_international_goals=u21_international_goals,
        omit_fields=omit_fields,
    )
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
    # ID_NAMESPACE_SALT lives in peoplegen.ids now
    if id_namespace_salt is not None and str(id_namespace_salt).strip():
        _ids.ID_NAMESPACE_SALT = str(id_namespace_salt).strip()
    elif id_registry_mode == "auto":
        _ids.ID_NAMESPACE_SALT, _id_reg_path = _ids.reserve_id_namespace(seed, count, out_xml, id_registry_path)
        print(f"[INFO] ID namespace: {_ids.ID_NAMESPACE_SALT} (registry: {_id_reg_path})", file=sys.stderr)
    else:
        _ids.ID_NAMESPACE_SALT = ""

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
    for idx in range(count):
        i = start_index + existing + idx

        create_uid = _ids.uniq(_id64, seed, i, "create_uid", used_create)
        person_uid = _ids.uniq(_id64, seed, i, "person_uid", used64, extra_ok=person_ok)

        rid_create = _ids.uniq(_id32, seed, i, "rid|create", used32)
        frags.append(_create(create_uid, person_uid, rid_create, version))

        # Determine gender + nation before names so name pools can be nationality-aware.
        # gender (settings)
        if gender_value is not None:
            eff_gender_value = int(gender_value)
        else:
            _fp = float(_FEMALE_PCT)
            if _fp < 0.0: _fp = 0.0
            if _fp > 100.0: _fp = 100.0
            eff_gender_value = 1 if (rng.random() < (_fp / 100.0)) else 0

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
            fn = _pick_name_weighted(name_rng, first_pool, primary_nation_name, local_bias=_NAME_LOCAL_BIAS)
        sn = fixed_second_name if fixed_second_name is not None else _pick_name_weighted(name_rng, surname_rows, primary_nation_name, local_bias=_NAME_LOCAL_BIAS)
        if fixed_common_name or fixed_full_name:
            cn = (fixed_common_name or fixed_full_name or f"{fn} {sn}").strip()
        else:
            if common_name_rows and (name_rng.random() < float(common_name_chance)):
                cn = (_pick_name_weighted(name_rng, common_name_rows, primary_nation_name, local_bias=_NAME_LOCAL_BIAS) or "").strip()
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

        # [PATCH AGE VAR v1]


        age = max(1, min(100, int(base_year) - int(dob.year)))


        

        ca = rng.randint(ca_min, ca_max)
        pa = rng.randint(pa_min, pa_max)
        if pa < ca:
            pa = ca

        # Club selection + record emit gating (extracted)
        club_dbid, club_large = _club.pick_club_dbids(rng=rng, clubs=clubs, fixed_club=fixed_club, eff_gender_value=eff_gender_value)
        club_record_emit = _club.should_emit_club_record(rng=rng, club_dbid=club_dbid, club_large=club_large, club_assign_pct=club_assign_pct, is_omitted=_is_omitted)

        city_dbid, city_large = fixed_city if fixed_city else (lambda x: (x[0], x[1]))(rng.choice(cities))

        # positions (advanced only; legacy removed)
        primary = pos_primary
        extra_20 = pos_20 or []
        dev = pos_dev or []
        has_explicit = bool(primary and str(primary).strip()) or bool(extra_20) or bool(pos_all_outfield_20) or bool(dev)
        if has_explicit:
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
                allow_random_primary=True,
                auto_dev_chance=auto_dev_chance,
            )
        else:
            # distribution-driven random positions (PRIMARY_DIST/N20_DIST)
            pos_map = _pos_map_auto_random(
                rng,
                dev_mode=pos_dev_mode,
                dev_value=pos_dev_value,
                dev_min=pos_dev_min,
                dev_max=pos_dev_max,
                auto_dev_chance=auto_dev_chance,
            )
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

        # economy (wage + reputation + transfer value) extracted
        wage_val, rep_cur, rep_home_v, rep_world_v, tv = _eco.decide_economy(
            rng=rng,
            wage=wage, wage_min=wage_min, wage_max=wage_max,
            rep_current=rep_current, rep_home=rep_home, rep_world=rep_world,
            rep_min=rep_min, rep_max=rep_max,
            transfer_mode=transfer_mode, transfer_value=transfer_value, transfer_min=transfer_min, transfer_max=transfer_max,
            pa=pa, tv_lo=TV_LO, tv_hi=TV_HI,
        )


        joined = joined_club_date if joined_club_date is not None else dt.date(base_year, 7, 1)
        moved_to_nation = moved_to_nation_date if moved_to_nation_date is not None else dob
        last_signed = date_last_signed if date_last_signed is not None else joined
        expires = contract_expires_date if contract_expires_date is not None else dt.date(base_year + 3, 6, 30)
        squad_status_val = int(squad_status) if squad_status is not None else 9

        # Record emission (rid/push) extracted
        emit = _emit.Emitter(
            frags=frags,
            is_omitted=_is_omitted,
            rid_func=lambda lbl: _ids.uniq(_id32, seed, i, lbl, used32),
        )
        rid = emit.rid
        push = emit.push
        # Details randomization: when GUI/CLI chooses "Random" it omits the value args.
        # In that case generate a valid random FM value instead of omitting the record.
        eff_gender_value = int(eff_gender_value)  # set earlier so name pool + club filtering stay in sync
        _app = _default_appearance_values(rng, primary_nation_name, eff_gender_value)
        eff_ethnicity_value = int(ethnicity_value) if ethnicity_value is not None else int(_app["ethnicity_value"])
        eff_hair_colour_value = int(hair_colour_value) if hair_colour_value is not None else int(_app["hair_colour_value"])
        eff_hair_length_value = int(hair_length_value) if hair_length_value is not None else int(_app["hair_length_value"])
        eff_skin_tone_value = int(skin_tone_value) if skin_tone_value is not None else int(_app["skin_tone_value"])
        eff_body_type_value = int(body_type_value) if body_type_value is not None else _random_body_type_weighted(rng)

        # identity/appearance/positions emit block extracted
        _emitblk.emit_identity_appearance_positions(
            push=push,
            rid=rid,
            _is_omitted=_is_omitted,
            person_uid=person_uid,
            version=version,
            fn=fn,
            sn=sn,
            cn=cn,
            fixed_full_name=fixed_full_name,
            person_type_value=person_type_value,
            eff_gender_value=eff_gender_value,
            eff_ethnicity_value=eff_ethnicity_value,
            eff_hair_colour_value=eff_hair_colour_value,
            eff_hair_length_value=eff_hair_length_value,
            eff_skin_tone_value=eff_skin_tone_value,
            eff_body_type_value=eff_body_type_value,
            lang_extra=lang_extra,
            odvl0=odvl0,
            pos_map=pos_map,
        )
        # city/nation/secondnations/international/club emit block extracted
        _emitblk.emit_city_nation_club(ctx={**globals(), **locals()})
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
    """CLI wrapper. Real CLI logic lives in peoplegen/cli_entry.py."""
    from peoplegen import cli_entry as _cli
    import sys as _sys
    return _cli.main(argv=argv, gen_mod=_sys.modules[__name__])

if __name__ == "__main__":
    raise SystemExit(main())