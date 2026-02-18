#!/usr/bin/env python3
"""
fm_dbchanges_extract_fixed_v4.py

Extract *club* and *city* IDs from Football Manager db_changes XML and write ONE combined CSV.

What it detects (from <record id="new_value">):
- Clubs: <large id="Ttea" value="..."> and <integer id="DBID" value="...">
- Cities: <large id="city" value="..."> and <integer id="DBID" value="...">

Output CSV contains BOTH:
- club rows (club_* columns filled)
- city rows (city_* columns filled)

Also includes Excel-safe *_text columns like ="22341148568674088"
so long integers won’t be mangled by Excel.

Usage:
  python fm_dbchanges_extract_fixed_v4.py --xml playerdata2.xml --out clubs_cities.csv
"""
from __future__ import annotations

import argparse
import csv
import xml.etree.ElementTree as ET
from typing import Dict, Tuple, Optional


def excel_text(n: int) -> str:
    # Keep it as a formula so Excel preserves the exact digits.
    return f'="{n}"'


def _child_value(elem: ET.Element, tag: str, id_value: str) -> Optional[str]:
    for ch in list(elem):
        if ch.tag == tag and ch.attrib.get("id") == id_value:
            return ch.attrib.get("value")
    return None


def _find_new_value_record(record_elem: ET.Element) -> Optional[ET.Element]:
    for ch in list(record_elem):
        if ch.tag == "record" and ch.attrib.get("id") == "new_value":
            return ch
    return None


def extract(xml_path: str) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    Returns:
      clubs: {club_dbid: ttea_large}
      cities: {city_dbid: city_large}
    """
    clubs: Dict[int, int] = {}
    cities: Dict[int, int] = {}

    # Use iterparse for very large files
    for event, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag != "record":
            continue

        # Only process "outer" change records. Inner records (e.g. id="new_value"/"odvl")
        # must remain attached until the outer record ends.
        if elem.attrib.get("id") is not None:
            continue

        nv = _find_new_value_record(elem)
        if nv is None:
            elem.clear()
            continue

        dbid_s = _child_value(nv, "integer", "DBID") or _child_value(nv, "integer", "dbid")
        if dbid_s is None:
            elem.clear()
            continue

        try:
            dbid = int(dbid_s)
        except ValueError:
            elem.clear()
            continue

        # club?
        ttea_s = _child_value(nv, "large", "Ttea") or _child_value(nv, "large", "ttea")
        if ttea_s:
            try:
                clubs[dbid] = int(ttea_s)
            except ValueError:
                pass

        # city?
        city_s = _child_value(nv, "large", "city")
        if city_s:
            try:
                cities[dbid] = int(city_s)
            except ValueError:
                pass

        elem.clear()

    return clubs, cities


def write_combined_csv(out_path: str, clubs: Dict[int, int], cities: Dict[int, int]) -> None:
    # Column names match the requested canonical format.
    # (Older builds used kind/ttea_large; the generator accepts both, but we now
    # write the canonical names: type/club_large.)
    fieldnames = [
        "type",
        "club_dbid", "club_dbid_text",
        "club_large", "club_large_text",
        "club_name",
        "city_dbid", "city_dbid_text",
        "city_large", "city_large_text",
        "city_name",
    ]

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()

        # Clubs first
        for club_dbid in sorted(clubs.keys()):
            club_large = clubs[club_dbid]
            w.writerow({
                "type": "club",
                "club_dbid": club_dbid,
                "club_dbid_text": excel_text(club_dbid),
                "club_large": club_large,
                "club_large_text": excel_text(club_large),
                "club_name": "",
                "city_dbid": "",
                "city_dbid_text": "",
                "city_large": "",
                "city_large_text": "",
                "city_name": "",
            })

        # Cities next
        for city_dbid in sorted(cities.keys()):
            city_large = cities[city_dbid]
            w.writerow({
                "type": "city",
                "club_dbid": "",
                "club_dbid_text": "",
                "club_large": "",
                "club_large_text": "",
                "club_name": "",
                "city_dbid": city_dbid,
                "city_dbid_text": excel_text(city_dbid),
                "city_large": city_large,
                "city_large_text": excel_text(city_large),
                "city_name": "",
            })


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True, help="Path to db_changes XML")
    ap.add_argument("--out", required=True, help="Output combined CSV path (e.g. clubs_cities.csv)")
    return ap.parse_args()


def main() -> None:
    args = parse_args()
    clubs, cities = extract(args.xml)

    if not clubs:
        print("Warning: No clubs detected (no <record id='new_value'> containing Ttea + DBID).")
    if not cities:
        print("Warning: No cities detected (no <record id='new_value'> containing city + DBID).")

    write_combined_csv(args.out, clubs, cities)
    print(f"Wrote {args.out} (clubs={len(clubs)}, cities={len(cities)})")


if __name__ == "__main__":
    main()
