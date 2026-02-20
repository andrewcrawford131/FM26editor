#!/usr/bin/env python3
"""
fm_dbchanges_extract_fixed_v4.py

Extract clubs + cities + nations from FM "db_changes" XML and merge into ONE CSV master_library.csv.

Extracts:
- City of birth property: 1348690537 -> city + DBID
- Club property:         1348695145 -> Ttea + DBID
- Nation property:       1349416041 -> Nnat + DBID

Merge mode:
- Loads existing CSV first
- Preserves manual name columns (club_name/city_name/nation_name)

IMPORTANT FIX:
- With iterparse(end), inner <record id="new_value"> ends before the parent <record>.
  If you clear() inner records, you erase DBID/Ttea/city before the parent is processed.
  So we NEVER clear records that have an "id=" attribute (new_value/odvl/etc).
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
import xml.etree.ElementTree as ET

CITY_PROP = 1348690537
CLUB_PROP = 1348695145
NATION_PROP = 1349416041

FIELDS = [
    "kind",
    "club_dbid", "club_dbid_text", "ttea_large", "ttea_large_text", "club_name",
    "city_dbid", "city_dbid_text", "city_large", "city_large_text", "city_name",
    "nation_dbid", "nation_dbid_text", "nnat_large", "nnat_large_text", "nation_name",
]


def excel_text_int(v: int | None) -> str:
    if v is None:
        return ""
    return f'="{v}"'


def _safe_int(s: str | None) -> int | None:
    if s is None:
        return None
    t = str(s).strip()
    if not t:
        return None
    # Excel-safe forms: ="123"
    if t.startswith('="') and t.endswith('"'):
        t = t[2:-1].strip()
    t = t.strip().strip('"').strip()
    if not t:
        return None
    try:
        return int(t)
    except Exception:
        return None


def load_existing_library(csv_path: Path):
    clubs, cities, nations = {}, {}, {}

    if not csv_path.exists():
        return clubs, cities, nations

    def g(row: dict, key: str) -> str:
        return (row.get(key) or "").strip()

    with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        for row in r:
            kind = (g(row, "kind") or g(row, "type")).lower()

            if kind == "club":
                dbid = _safe_int(g(row, "club_dbid"))
                large = _safe_int(g(row, "ttea_large") or g(row, "club_large") or g(row, "ttea_large_text"))
                name = g(row, "club_name")
                if dbid is not None and large is not None:
                    clubs[(dbid, large)] = {"dbid": dbid, "large": large, "name": name}

            elif kind == "city":
                dbid = _safe_int(g(row, "city_dbid"))
                large = _safe_int(g(row, "city_large") or g(row, "city_large_text"))
                name = g(row, "city_name")
                if dbid is not None and large is not None:
                    cities[(dbid, large)] = {"dbid": dbid, "large": large, "name": name}

            elif kind == "nation":
                dbid = _safe_int(g(row, "nation_dbid") or g(row, "dbid"))
                large = _safe_int(g(row, "nnat_large") or g(row, "nation_large") or g(row, "nnat_large_text"))
                name = g(row, "nation_name")
                if dbid is not None and large is not None:
                    nations[(dbid, large)] = {"dbid": dbid, "large": large, "name": name}

    return clubs, cities, nations


def _find_record(elem: ET.Element, rec_id: str) -> ET.Element | None:
    r = elem.find(f"./record[@id='{rec_id}']")
    if r is not None:
        return r
    return elem.find(f".//record[@id='{rec_id}']")


def _iter_values(root: ET.Element):
    """Yield (tag, id_lower, value_str) for any element with id/value."""
    for e in root.iter():
        _id = (e.get("id") or "").strip()
        if not _id:
            continue
        v = e.get("value")
        if v is None:
            continue
        yield (e.tag, _id.lower(), v)


def _find_value_anywhere(sources: list[ET.Element], id_names: list[str]) -> int | None:
    want = {x.lower() for x in id_names}
    for src in sources:
        for _tag, _id, v in _iter_values(src):
            if _id in want:
                iv = _safe_int(v)
                if iv is not None:
                    return iv
    return None


def extract_from_xml(xml_path: Path, debug: bool = False, scan_props: bool = False):
    clubs, cities, nations = {}, {}, {}

    stats = {
        "records_seen": 0,
        "club_hits": 0,
        "city_hits": 0,
        "nation_hits": 0,
        "nation_prop_seen": 0,
        "nation_missing_parts": 0,
        "prop_counts": {},
        "debug_dumps": 0,
    }

    for _event, elem in ET.iterparse(str(xml_path), events=("end",)):
        # IMPORTANT: don't clear inner records like <record id="new_value"> or <record id="odvl">
        # because the parent record hasn't been processed yet.
        if elem.tag == "record" and elem.get("id") is not None:
            continue

        if elem.tag != "record":
            continue

        prop_elem = elem.find("./unsigned[@id='property']")
        if prop_elem is None:
            prop_elem = elem.find("./integer[@id='property']")
        if prop_elem is None:
            elem.clear()
            continue

        prop = _safe_int(prop_elem.get("value"))
        if prop is None:
            elem.clear()
            continue

        stats["records_seen"] += 1
        if scan_props or debug:
            stats["prop_counts"][prop] = stats["prop_counts"].get(prop, 0) + 1

        if prop not in (CITY_PROP, CLUB_PROP, NATION_PROP):
            elem.clear()
            continue

        if prop == NATION_PROP:
            stats["nation_prop_seen"] += 1

        nv = _find_record(elem, "new_value")
        if nv is None:
            # sometimes FM uses null new_value, fall back to old_value
            if elem.find("./null[@id='new_value']") is not None:
                nv = _find_record(elem, "old_value")

        odvl = _find_record(elem, "odvl")

        sources: list[ET.Element] = []
        if nv is not None:
            sources.append(nv)
        if odvl is not None:
            sources.append(odvl)
        sources.append(elem)  # fallback

        dbid = _find_value_anywhere(sources, ["DBID", "dbid"])
        if dbid is None:
            if prop == NATION_PROP:
                stats["nation_missing_parts"] += 1
            if debug and stats["debug_dumps"] < 2:
                stats["debug_dumps"] += 1
                print("\n[DEBUG] Missing DBID in this record:")
                print(ET.tostring(elem, encoding="unicode")[:2000])
            elem.clear()
            continue

        if prop == CLUB_PROP:
            large = _find_value_anywhere(sources, ["Ttea", "ttea"])
            if large is None:
                if debug and stats["debug_dumps"] < 2:
                    stats["debug_dumps"] += 1
                    print("\n[DEBUG] Club record missing Ttea:")
                    print(ET.tostring(elem, encoding="unicode")[:2000])
                elem.clear()
                continue
            stats["club_hits"] += 1
            clubs[(dbid, large)] = {"dbid": dbid, "large": large, "name": ""}

        elif prop == CITY_PROP:
            large = _find_value_anywhere(sources, ["city"])
            if large is None:
                if debug and stats["debug_dumps"] < 2:
                    stats["debug_dumps"] += 1
                    print("\n[DEBUG] City record missing city large:")
                    print(ET.tostring(elem, encoding="unicode")[:2000])
                elem.clear()
                continue
            stats["city_hits"] += 1
            cities[(dbid, large)] = {"dbid": dbid, "large": large, "name": ""}

        elif prop == NATION_PROP:
            large = _find_value_anywhere(sources, ["Nnat", "nnat"])
            if large is None:
                stats["nation_missing_parts"] += 1
                if debug and stats["debug_dumps"] < 2:
                    stats["debug_dumps"] += 1
                    print("\n[DEBUG] Nation record missing Nnat:")
                    print(ET.tostring(elem, encoding="unicode")[:2000])
                elem.clear()
                continue
            stats["nation_hits"] += 1
            nations[(dbid, large)] = {"dbid": dbid, "large": large, "name": ""}

        elem.clear()

    return clubs, cities, nations, stats


def merge_preserving_names(existing: dict, new: dict) -> dict:
    for k, v in new.items():
        if k not in existing:
            existing[k] = v
        else:
            ex_name = (existing[k].get("name") or "").strip()
            new_name = (v.get("name") or "").strip()
            if not ex_name and new_name:
                existing[k]["name"] = new_name
    return existing


def write_master_csv(out_path: Path, clubs: dict, cities: dict, nations: dict) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    def club_rows():
        for (dbid, large) in sorted(clubs.keys()):
            name = (clubs[(dbid, large)].get("name") or "").strip()
            yield {
                "kind": "club",
                "club_dbid": str(dbid),
                "club_dbid_text": excel_text_int(dbid),
                "ttea_large": str(large),
                "ttea_large_text": excel_text_int(large),
                "club_name": name,
                "city_dbid": "", "city_dbid_text": "", "city_large": "", "city_large_text": "", "city_name": "",
                "nation_dbid": "", "nation_dbid_text": "", "nnat_large": "", "nnat_large_text": "", "nation_name": "",
            }

    def city_rows():
        for (dbid, large) in sorted(cities.keys()):
            name = (cities[(dbid, large)].get("name") or "").strip()
            yield {
                "kind": "city",
                "club_dbid": "", "club_dbid_text": "", "ttea_large": "", "ttea_large_text": "", "club_name": "",
                "city_dbid": str(dbid),
                "city_dbid_text": excel_text_int(dbid),
                "city_large": str(large),
                "city_large_text": excel_text_int(large),
                "city_name": name,
                "nation_dbid": "", "nation_dbid_text": "", "nnat_large": "", "nnat_large_text": "", "nation_name": "",
            }

    def nation_rows():
        for (dbid, large) in sorted(nations.keys()):
            name = (nations[(dbid, large)].get("name") or "").strip()
            yield {
                "kind": "nation",
                "club_dbid": "", "club_dbid_text": "", "ttea_large": "", "ttea_large_text": "", "club_name": "",
                "city_dbid": "", "city_dbid_text": "", "city_large": "", "city_large_text": "", "city_name": "",
                "nation_dbid": str(dbid),
                "nation_dbid_text": excel_text_int(dbid),
                "nnat_large": str(large),
                "nnat_large_text": excel_text_int(large),
                "nation_name": name,
            }

    with out_path.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        for row in nation_rows():
            w.writerow(row)
        for row in city_rows():
            w.writerow(row)
        for row in club_rows():
            w.writerow(row)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--xml", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--debug", action="store_true")
    ap.add_argument("--scan_props", action="store_true")
    args = ap.parse_args()

    xml_path = Path(args.xml).expanduser()
    out_path = Path(args.out).expanduser()

    if not xml_path.exists():
        print(f"[ERROR] XML not found: {xml_path}")
        return 2

    print("==== LOAD EXISTING LIBRARY ====")
    print(f"Existing file: {out_path}")
    existing_clubs, existing_cities, existing_nations = load_existing_library(out_path)

    print(f"Loaded clubs={len(existing_clubs)} cities={len(existing_cities)} nations={len(existing_nations)}")
    club_names = sum(1 for v in existing_clubs.values() if (v.get("name") or "").strip())
    city_names = sum(1 for v in existing_cities.values() if (v.get("name") or "").strip())
    nation_names = sum(1 for v in existing_nations.values() if (v.get("name") or "").strip())
    print(f"Loaded club names={club_names} city names={city_names} nation names={nation_names}\n")

    new_clubs, new_cities, new_nations, stats = extract_from_xml(
        xml_path, debug=args.debug, scan_props=args.scan_props
    )

    # "new IDs" (not already in CSV)
    new_only_clubs = len(set(new_clubs.keys()) - set(existing_clubs.keys()))
    new_only_cities = len(set(new_cities.keys()) - set(existing_cities.keys()))
    new_only_nations = len(set(new_nations.keys()) - set(existing_nations.keys()))

    print("==== EXTRACTED THIS RUN ====")
    print(f"Records with property field seen: {stats['records_seen']}")
    print(f"Extracted clubs:   {len(new_clubs)} (hits {stats['club_hits']}) | NEW vs CSV: {new_only_clubs}")
    print(f"Extracted cities:  {len(new_cities)} (hits {stats['city_hits']}) | NEW vs CSV: {new_only_cities}")
    print(f"Extracted nations: {len(new_nations)} (hits {stats['nation_hits']}) | NEW vs CSV: {new_only_nations}")

    if args.scan_props:
        print("\n==== TOP PROPERTY IDS IN THIS XML ====")
        top = sorted(stats["prop_counts"].items(), key=lambda kv: kv[1], reverse=True)[:25]
        for pid, cnt in top:
            print(f"{pid}: {cnt}")

    if args.debug:
        print("\n==== DEBUG ====")
        print(f"Nation prop seen: {stats['nation_prop_seen']}")
        print(f"Nation missing parts: {stats['nation_missing_parts']}")

    merged_clubs = merge_preserving_names(existing_clubs, new_clubs)
    merged_cities = merge_preserving_names(existing_cities, new_cities)
    merged_nations = merge_preserving_names(existing_nations, new_nations)

    print("\n==== FINAL LIBRARY COUNTS (after merge) ====")
    print(f"TOTAL clubs={len(merged_clubs)} cities={len(merged_cities)} nations={len(merged_nations)}")

    write_master_csv(out_path, merged_clubs, merged_cities, merged_nations)
    print(f"Wrote: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
