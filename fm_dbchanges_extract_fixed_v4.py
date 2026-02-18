#!/usr/bin/env python3
"""
fm_dbchanges_extract_fixed_v4.py
MASTER LIBRARY extractor (clubs + cities + nations) with true merge (append behavior).

Fixes:
- Extracts Nations from property 1349416041 and/or presence of <large id="Nnat" ...>
- Only reads records INSIDE <list id="db_changes"> (matches your XML structure)
- Loads existing CSV and PRESERVES manual *_name fields
- Works whether your existing file is older clubs_cities.csv or newer master_library.csv
- Prints DEBUG so you can confirm what it's doing
"""

from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, Optional, Tuple

# Properties (as per your data)
CITY_PROPERTY = 1348690537
CLUB_PROPERTY = 1348695145
NATION_PROPERTY = 1349416041


def excel_text(n: int) -> str:
    return f'="{n}"'


def parse_excel_text_id(s: object) -> Optional[int]:
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None
    if s.startswith('="') and s.endswith('"') and len(s) >= 4:
        s = s[2:-1].strip()
    s = s.lstrip("=").strip().strip('"').strip()
    if not s or not all(ch.isdigit() for ch in s):
        return None
    try:
        return int(s)
    except ValueError:
        return None


def open_csv_smart(path: Path):
    """
    Try multiple encodings + delimiter sniff.
    Returns (file_handle, DictReader)
    """
    encodings = ["utf-8-sig", "utf-8", "utf-16", "utf-16-le", "utf-16-be", "latin-1"]
    last_err = None

    for enc in encodings:
        try:
            f = path.open("r", newline="", encoding=enc)
            sample = f.read(4096)
            f.seek(0)

            # Delimiter sniff (comma/semicolon/tab)
            dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
            r = csv.DictReader(f, dialect=dialect)
            return f, r
        except Exception as e:
            last_err = e
            try:
                f.close()
            except Exception:
                pass

    raise RuntimeError(f"Could not open CSV '{path}' with common encodings/delimiters. Last error: {last_err}")


def _child_value(elem: ET.Element, tag_options: tuple[str, ...], child_id: str) -> Optional[str]:
    for ch in list(elem):
        if ch.tag in tag_options and ch.attrib.get("id") == child_id:
            return ch.attrib.get("value")
    return None


def _find_property(record_elem: ET.Element) -> Optional[int]:
    v = _child_value(record_elem, ("unsigned", "integer"), "property")
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _find_new_value_record(record_elem: ET.Element) -> Optional[ET.Element]:
    for ch in list(record_elem):
        if ch.tag == "record" and ch.attrib.get("id") == "new_value":
            return ch
    return None


def _find_dbid(nv: ET.Element) -> Optional[int]:
    v = _child_value(nv, ("integer", "unsigned"), "DBID") or _child_value(nv, ("integer", "unsigned"), "dbid")
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def _find_large_case_insensitive(nv: ET.Element, wanted_lower: str) -> Optional[int]:
    wanted_lower = wanted_lower.lower()
    for ch in list(nv):
        if ch.tag != "large":
            continue
        cid = (ch.attrib.get("id") or "").strip().lower()
        if cid == wanted_lower:
            v = ch.attrib.get("value")
            if not v:
                return None
            try:
                return int(v)
            except ValueError:
                return None
    return None


def _has_large_case_insensitive(nv: ET.Element, wanted_lower: str) -> bool:
    wanted_lower = wanted_lower.lower()
    for ch in list(nv):
        if ch.tag == "large":
            cid = (ch.attrib.get("id") or "").strip().lower()
            if cid == wanted_lower:
                return True
    return False


def extract(xml_path: str) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, int], dict]:
    """
    Extracts clubs/cities/nations ONLY from within <list id="db_changes">.
    Returns dicts: clubs{dbid: ttea}, cities{dbid: city_large}, nations{dbid: nnat}
    """
    clubs: Dict[int, int] = {}
    cities: Dict[int, int] = {}
    nations: Dict[int, int] = {}

    stats = {
        "in_db_changes_records_seen": 0,
        "club_hits": 0,
        "city_hits": 0,
        "nation_hits": 0,
        "nation_prop_seen": 0,
        "nation_shape_seen": 0,
        "nation_missing_parts": 0,
        "first_nations": [],
    }

    in_db_changes = 0  # nesting-safe counter

    for ev, elem in ET.iterparse(xml_path, events=("start", "end")):
        if ev == "start" and elem.tag == "list" and elem.attrib.get("id") == "db_changes":
            in_db_changes += 1
            continue

        if ev == "end" and elem.tag == "list" and elem.attrib.get("id") == "db_changes":
            in_db_changes = max(0, in_db_changes - 1)
            elem.clear()
            continue

        if ev != "end":
            continue

        if in_db_changes <= 0:
            continue

        if elem.tag != "record":
            continue

        # Skip inner <record id="new_value"> and other id'd records (we need the outer record)
        if elem.attrib.get("id") is not None:
            continue

        stats["in_db_changes_records_seen"] += 1

        prop = _find_property(elem)
        nv = _find_new_value_record(elem)
        if nv is None:
            elem.clear()
            continue

        # CLUB
        if prop == CLUB_PROPERTY:
            dbid = _find_dbid(nv)
            ttea = _find_large_case_insensitive(nv, "ttea")
            if dbid is not None and ttea is not None:
                clubs[dbid] = ttea
                stats["club_hits"] += 1
            elem.clear()
            continue

        # CITY
        if prop == CITY_PROPERTY:
            dbid = _find_dbid(nv)
            city = _find_large_case_insensitive(nv, "city")
            if dbid is not None and city is not None:
                cities[dbid] = city
                stats["city_hits"] += 1
            elem.clear()
            continue

        # NATION (property OR "shape" presence of Nnat)
        is_nation_prop = (prop == NATION_PROPERTY)
        is_nation_shape = _has_large_case_insensitive(nv, "nnat")

        if is_nation_prop:
            stats["nation_prop_seen"] += 1
        if is_nation_shape:
            stats["nation_shape_seen"] += 1

        if is_nation_prop or is_nation_shape:
            dbid = _find_dbid(nv)
            nnat = _find_large_case_insensitive(nv, "nnat")
            if dbid is None or nnat is None:
                stats["nation_missing_parts"] += 1
            else:
                nations[dbid] = nnat
                stats["nation_hits"] += 1
                if len(stats["first_nations"]) < 10:
                    stats["first_nations"].append((dbid, nnat))

        elem.clear()

    return clubs, cities, nations, stats


def load_existing_library(path: str):
    """
    Loads existing CSV (old or new schema) and preserves manual names.
    """
    clubs: Dict[int, int] = {}
    cities: Dict[int, int] = {}
    nations: Dict[int, int] = {}

    club_names: Dict[int, str] = {}
    city_names: Dict[int, str] = {}
    nation_names: Dict[int, str] = {}

    p = Path(path)
    if not p.exists():
        return clubs, cities, nations, club_names, city_names, nation_names, {"loaded": False}

    fh, r = open_csv_smart(p)
    loaded_rows = 0
    headers = r.fieldnames or []

    try:
        for row in r:
            loaded_rows += 1
            kind = (row.get("kind") or row.get("type") or "").strip().lower()

            if kind == "club":
                dbid = parse_excel_text_id(row.get("club_dbid")) or parse_excel_text_id(row.get("club_dbid_text"))
                if dbid is None:
                    continue
                large = (
                    parse_excel_text_id(row.get("ttea_large"))
                    or parse_excel_text_id(row.get("club_large"))
                    or parse_excel_text_id(row.get("ttea_large_text"))
                )
                if large is not None:
                    clubs[dbid] = large
                name = (row.get("club_name") or "").strip()
                if name:
                    club_names[dbid] = name

            elif kind == "city":
                dbid = parse_excel_text_id(row.get("city_dbid")) or parse_excel_text_id(row.get("city_dbid_text"))
                if dbid is None:
                    continue
                large = (
                    parse_excel_text_id(row.get("city_large"))
                    or parse_excel_text_id(row.get("city"))
                    or parse_excel_text_id(row.get("city_large_text"))
                )
                if large is not None:
                    cities[dbid] = large
                name = (row.get("city_name") or "").strip()
                if name:
                    city_names[dbid] = name

            elif kind == "nation":
                dbid = parse_excel_text_id(row.get("nation_dbid")) or parse_excel_text_id(row.get("nation_dbid_text"))
                if dbid is None:
                    continue
                large = (
                    parse_excel_text_id(row.get("nnat_large"))
                    or parse_excel_text_id(row.get("Nnat"))
                    or parse_excel_text_id(row.get("nnat_large_text"))
                )
                if large is not None:
                    nations[dbid] = large
                name = (row.get("nation_name") or "").strip()
                if name:
                    nation_names[dbid] = name
    finally:
        fh.close()

    meta = {"loaded": True, "rows": loaded_rows, "headers": headers}
    return clubs, cities, nations, club_names, city_names, nation_names, meta


def write_master_library_csv(out_path: str,
                            clubs: Dict[int, int],
                            cities: Dict[int, int],
                            nations: Dict[int, int],
                            club_names: Dict[int, str],
                            city_names: Dict[int, str],
                            nation_names: Dict[int, str]) -> None:
    fieldnames = [
        "kind",

        "club_dbid", "club_dbid_text",
        "ttea_large", "ttea_large_text",
        "club_name",

        "city_dbid", "city_dbid_text",
        "city_large", "city_large_text",
        "city_name",

        "nation_dbid", "nation_dbid_text",
        "nnat_large", "nnat_large_text",
        "nation_name",
    ]

    outp = Path(out_path)
    tmp = outp.with_suffix(outp.suffix + ".tmp")

    with tmp.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        for dbid in sorted(clubs.keys()):
            large = clubs.get(dbid)
            w.writerow({
                "kind": "club",
                "club_dbid": dbid,
                "club_dbid_text": excel_text(dbid),
                "ttea_large": large if large is not None else "",
                "ttea_large_text": excel_text(large) if large is not None else "",
                "club_name": club_names.get(dbid, ""),

                "city_dbid": "", "city_dbid_text": "", "city_large": "", "city_large_text": "", "city_name": "",
                "nation_dbid": "", "nation_dbid_text": "", "nnat_large": "", "nnat_large_text": "", "nation_name": "",
            })

        for dbid in sorted(cities.keys()):
            large = cities.get(dbid)
            w.writerow({
                "kind": "city",
                "club_dbid": "", "club_dbid_text": "", "ttea_large": "", "ttea_large_text": "", "club_name": "",

                "city_dbid": dbid,
                "city_dbid_text": excel_text(dbid),
                "city_large": large if large is not None else "",
                "city_large_text": excel_text(large) if large is not None else "",
                "city_name": city_names.get(dbid, ""),

                "nation_dbid": "", "nation_dbid_text": "", "nnat_large": "", "nnat_large_text": "", "nation_name": "",
            })

        for dbid in sorted(nations.keys()):
            large = nations.get(dbid)
            w.writerow({
                "kind": "nation",
                "club_dbid": "", "club_dbid_text": "", "ttea_large": "", "ttea_large_text": "", "club_name": "",
                "city_dbid": "", "city_dbid_text": "", "city_large": "", "city_large_text": "", "city_name": "",

                "nation_dbid": dbid,
                "nation_dbid_text": excel_text(dbid),
                "nnat_large": large if large is not None else "",
                "nnat_large_text": excel_text(large) if large is not None else "",
                "nation_name": nation_names.get(dbid, ""),
            })

    tmp.replace(outp)


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True, help="Path to db_changes XML")
    ap.add_argument("--out", required=True, help="Output CSV path (master_library.csv recommended)")
    return ap.parse_args()


def main() -> int:
    args = parse_args()

    clubs_new, cities_new, nations_new, stats = extract(args.xml)

    clubs_old, cities_old, nations_old, club_names, city_names, nation_names, meta = load_existing_library(args.out)

    print("==== LOAD EXISTING LIBRARY ====")
    if meta.get("loaded"):
        print(f"Existing file: {args.out}")
        print(f"Rows read: {meta.get('rows')}")
        print(f"Headers: {meta.get('headers')}")
        print(f"Loaded clubs={len(clubs_old)} cities={len(cities_old)} nations={len(nations_old)}")
        print(f"Loaded club names={len(club_names)} city names={len(city_names)} nation names={len(nation_names)}")
    else:
        print("No existing file found (will create new).")

    # Merge = append behavior (union)
    clubs = dict(clubs_old)
    for k, v in clubs_new.items():
        if k not in clubs:
            clubs[k] = v
        elif (clubs.get(k) in (None, 0, "")) and v:
            clubs[k] = v

    cities = dict(cities_old)
    for k, v in cities_new.items():
        if k not in cities:
            cities[k] = v
        elif (cities.get(k) in (None, 0, "")) and v:
            cities[k] = v

    nations = dict(nations_old)
    for k, v in nations_new.items():
        if k not in nations:
            nations[k] = v
        elif (nations.get(k) in (None, 0, "")) and v:
            nations[k] = v

    write_master_library_csv(args.out, clubs, cities, nations, club_names, city_names, nation_names)

    print("\n==== EXTRACT DEBUG (from XML) ====")
    print(f"Records seen inside db_changes: {stats['in_db_changes_records_seen']}")
    print(f"Club hits:   {stats['club_hits']} (unique clubs extracted this run: {len(clubs_new)})")
    print(f"City hits:   {stats['city_hits']} (unique cities extracted this run: {len(cities_new)})")
    print(f"Nation prop seen: {stats['nation_prop_seen']}, nation shape seen: {stats['nation_shape_seen']}")
    print(f"Nation hits: {stats['nation_hits']} (unique nations extracted this run: {len(nations_new)})")
    print(f"Nation missing parts: {stats['nation_missing_parts']}")
    print(f"First nations: {stats['first_nations']}")

    print("\n==== FINAL LIBRARY COUNTS (after merge) ====")
    print(f"TOTAL clubs={len(clubs)} cities={len(cities)} nations={len(nations)}")
    print(f"Wrote: {args.out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
