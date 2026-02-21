
#!/usr/bin/env python3
"""
FM26 XML Appender v2.1 (auto remap, create-ID detection fix)
- Appends records from one/more FM db_changes XML files into a target XML.
- Handles wrapped FM XML (finds <list id="db_changes">, ignores <list id="verf">).
- Auto-remaps colliding player IDs/create-record IDs so multiple single-player files
  generated with the same seed can coexist in the merged file.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import random
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import xml.etree.ElementTree as ET

CREATE_PROPERTY = "1094992978"  # required create-record property

_rng = random.SystemRandom()


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _find_dbchanges_list(root: ET.Element) -> ET.Element:
    # Prefer explicit list id=db_changes anywhere in tree
    for elem in root.iter():
        if _local_name(elem.tag) == "list" and elem.attrib.get("id") == "db_changes":
            return elem
    raise ValueError("No <list id='db_changes'> found")


def _top_level_records(list_elem: ET.Element) -> List[ET.Element]:
    return [c for c in list_elem if _local_name(c.tag) == "record"]


def _record_hash(record: ET.Element) -> str:
    return hashlib.sha256(ET.tostring(record, encoding="utf-8")).hexdigest()


def _direct_child(record: ET.Element, tag_local: str, attr_id: Optional[str] = None) -> Optional[ET.Element]:
    for c in record:
        if _local_name(c.tag) != tag_local:
            continue
        if attr_id is not None and c.attrib.get("id") != attr_id:
            continue
        return c
    return None


def _record_property(record: ET.Element) -> Optional[str]:
    # IMPORTANT: do not use `a or b` with ElementTree Elements here.
    # ET Elements are falsy when they have no children, which makes a real match
    # incorrectly fall through to the second lookup.
    el = _direct_child(record, "unsigned", "property")
    if el is None:
        el = _direct_child(record, "integer", "property")
    return None if el is None else el.attrib.get("value")


def _record_table_type(record: ET.Element) -> Optional[str]:
    el = _direct_child(record, "integer", "database_table_type")
    return None if el is None else el.attrib.get("value")


def _record_direct_large_dbid(record: ET.Element) -> Optional[str]:
    el = _direct_child(record, "large", "db_unique_id")
    return None if el is None else el.attrib.get("value")


def _find_create_ids(record: ET.Element) -> Tuple[Optional[str], Optional[str]]:
    """
    Returns (create_record_db_unique_id, created_person_db_unique_id) if record is CREATE_PROPERTY else (None, None)
    """
    if _record_property(record) != CREATE_PROPERTY:
        return (None, None)
    create_rec_id = _record_direct_large_dbid(record)
    newv = _direct_child(record, "record", "new_value")
    if newv is None:
        return (create_rec_id, None)
    person_id_el = None
    for e in newv.iter():
        if _local_name(e.tag) == "large" and e.attrib.get("id") == "db_unique_id":
            person_id_el = e
            break
    return (create_rec_id, None if person_id_el is None else person_id_el.attrib.get("value"))


def _expand_sources(paths: List[str], globs: List[str], list_file: Optional[Path]) -> List[Path]:
    seen = set()
    out: List[Path] = []

    def add(pp: Path):
        rp = str(pp.resolve())
        if rp not in seen:
            seen.add(rp)
            out.append(pp)

    for p in paths:
        pp = Path(p)
        if pp.is_file():
            add(pp)
        elif pp.exists():
            eprint(f"[WARN] Skipping non-file path: {pp}")
        else:
            eprint(f"[WARN] Source path not found: {pp}")

    for pat in globs:
        matched = False
        for pp in Path().glob(pat):
            if pp.is_file():
                add(pp)
                matched = True
        if not matched:
            eprint(f"[WARN] Glob matched no files: {pat}")

    if list_file:
        if not list_file.exists():
            raise FileNotFoundError(f"Source list file not found: {list_file}")
        for line in list_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            pp = Path(line)
            if pp.is_file():
                add(pp)
            else:
                eprint(f"[WARN] Listed source not found or not file: {pp}")

    return out


def _parse_xml(path: Path) -> Tuple[ET.ElementTree, ET.Element]:
    tree = ET.parse(path)
    root = tree.getroot()
    db_list = _find_dbchanges_list(root)
    return tree, db_list


def _find_wrapper_root_record(root: ET.Element) -> Optional[ET.Element]:
    # Many FM exports have outer <record> wrapper with verf/db_changes/EDvb/version...
    if _local_name(root.tag) == "record":
        return root
    for ch in root:
        if _local_name(ch.tag) == "record":
            # pick first direct child record as wrapper candidate
            return ch
    return None


def _make_empty_minimal_tree() -> Tuple[ET.ElementTree, ET.Element]:
    root = ET.Element("record")
    ET.SubElement(root, "list", {"id": "verf"})
    db = ET.SubElement(root, "list", {"id": "db_changes"})
    ET.SubElement(root, "integer", {"id": "EDvb", "value": "1"})
    ET.SubElement(root, "string", {"id": "EDfb", "value": ""})
    ET.SubElement(root, "integer", {"id": "version", "value": "3727"})
    ET.SubElement(root, "integer", {"id": "rule_group_version", "value": "1630"})
    ET.SubElement(root, "boolean", {"id": "beta", "value": "false"})
    ET.SubElement(root, "string", {"id": "orvs", "value": "2600"})
    ET.SubElement(root, "string", {"id": "svvs", "value": "2600"})
    return ET.ElementTree(root), db


def _clone_wrapper_from_source(source_path: Path) -> Tuple[ET.ElementTree, ET.Element]:
    stree = ET.parse(source_path)
    sroot = stree.getroot()
    wrapper = _find_wrapper_root_record(sroot)
    if wrapper is None:
        # fallback minimal
        return _make_empty_minimal_tree()
    new_root = copy.deepcopy(wrapper)
    db = _find_dbchanges_list(new_root)
    # clear db_changes payload
    for c in list(db):
        db.remove(c)
    return ET.ElementTree(new_root), db


def _indent(tree: ET.ElementTree):
    if hasattr(ET, "indent"):
        ET.indent(tree, space="  ")  # type: ignore[attr-defined]


def _write(tree: ET.ElementTree, path: Path):
    _indent(tree)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(path, encoding="utf-8", xml_declaration=True)


def _new_unique_large(existing: set[str]) -> str:
    while True:
        v = str(_rng.randrange(1, 2**63 - 1))
        if v not in existing:
            existing.add(v)
            return v


def _new_unique_int(existing: set[str]) -> str:
    while True:
        v = str(_rng.randrange(1, 2_147_483_647))
        if v not in existing:
            existing.add(v)
            return v


def _collect_existing_ids(records: List[ET.Element]):
    top_large_ids: set[str] = set()
    player_ids: set[str] = set()
    db_random_ids: set[str] = set()

    for r in records:
        lid = _record_direct_large_dbid(r)
        if lid:
            top_large_ids.add(lid)
        dr = _direct_child(r, "integer", "db_random_id")
        if dr is not None and dr.attrib.get("value"):
            db_random_ids.add(dr.attrib["value"])
        c_rec_id, c_player_id = _find_create_ids(r)
        if c_rec_id:
            top_large_ids.add(c_rec_id)
        if c_player_id:
            player_ids.add(c_player_id)

    return top_large_ids, player_ids, db_random_ids


def _build_collision_maps_for_source(
    src_records: List[ET.Element],
    target_top_large_ids: set[str],
    target_player_ids: set[str],
    auto_remap: bool,
):
    createid_map: Dict[str, str] = {}
    playerid_map: Dict[str, str] = {}
    remap_pairs = 0

    # First pass over create records only
    for r in src_records:
        c_rec_id, c_player_id = _find_create_ids(r)
        if not c_rec_id and not c_player_id:
            continue

        # Track create-record row id collisions
        if c_rec_id:
            if c_rec_id in target_top_large_ids:
                if auto_remap:
                    createid_map[c_rec_id] = _new_unique_large(target_top_large_ids)
                    remap_pairs += 1
                # else keep collision
            else:
                target_top_large_ids.add(c_rec_id)

        # Track created player/person id collisions
        if c_player_id:
            if c_player_id in target_player_ids:
                if auto_remap:
                    playerid_map[c_player_id] = _new_unique_large(target_player_ids)
                    remap_pairs += 1
                # else keep collision
            else:
                target_player_ids.add(c_player_id)

    return createid_map, playerid_map, remap_pairs


def _apply_maps_to_record(record: ET.Element, createid_map: Dict[str, str], playerid_map: Dict[str, str], db_random_existing: set[str], remap_db_random: bool):
    r = copy.deepcopy(record)

    # Optional: make db_random_id unique (safe for repeated single-file merges)
    if remap_db_random:
        dr = _direct_child(r, "integer", "db_random_id")
        if dr is not None and dr.attrib.get("value"):
            old = dr.attrib["value"]
            if old in db_random_existing:
                dr.attrib["value"] = _new_unique_int(db_random_existing)
            else:
                db_random_existing.add(old)

    # Remap create-record IDs
    if _record_property(r) == CREATE_PROPERTY:
        direct_large = _direct_child(r, "large", "db_unique_id")
        if direct_large is not None:
            old = direct_large.attrib.get("value")
            if old in createid_map:
                direct_large.attrib["value"] = createid_map[old]
        newv = _direct_child(r, "record", "new_value")
        if newv is not None:
            for e in newv.iter():
                if _local_name(e.tag) == "large" and e.attrib.get("id") == "db_unique_id":
                    old = e.attrib.get("value")
                    if old in playerid_map:
                        e.attrib["value"] = playerid_map[old]
                    break

    # Remap player/person ID on all table_type=1 property rows
    if _record_table_type(r) == "1":
        direct_large = _direct_child(r, "large", "db_unique_id")
        if direct_large is not None:
            old = direct_large.attrib.get("value")
            if old in playerid_map:
                direct_large.attrib["value"] = playerid_map[old]

    return r


def main() -> int:
    ap = argparse.ArgumentParser(description="Append FM db_changes XML records from one/more sources into a target XML.")
    ap.add_argument("--target", required=True, help="Target FM db_changes XML (existing or new with --create-target)")
    ap.add_argument("--source", action="append", default=[], help="Source XML file (repeatable)")
    ap.add_argument("--glob", action="append", default=[], help='Glob for source XMLs, e.g. "out/*.xml"')
    ap.add_argument("--source-list", help="Text file with source XML paths (one per line)")
    ap.add_argument("--output", help="Write merged XML to different path (default: overwrite target)")
    ap.add_argument("--create-target", action="store_true", help="Create target XML if missing (clones wrapper from first source)")
    ap.add_argument("--backup", action="store_true", help="Write .bak before overwrite")
    ap.add_argument("--dry-run", action="store_true", help="Report only; do not write file")
    ap.add_argument("--skip-self", action="store_true", help="Skip sources that match target path")
    ap.add_argument("--dedupe", choices=["none", "exact", "create"], default="none",
                    help="none/exact/create (create skips duplicate create-record player IDs)")
    ap.add_argument("--auto-remap-collisions", choices=["on", "off"], default="on",
                    help="Auto remap colliding create/player IDs so appended players remain unique")
    ap.add_argument("--remap-db-random-id", choices=["on", "off"], default="on",
                    help="Also remap colliding db_random_id values")
    ap.add_argument("--verbose", action="store_true", help="Per-file stats")
    args = ap.parse_args()

    target = Path(args.target)
    output = Path(args.output) if args.output else target
    list_file = Path(args.source_list) if args.source_list else None
    auto_remap = (args.auto_remap_collisions == "on")
    remap_db_random = (args.remap_db_random_id == "on")

    sources = _expand_sources(args.source, args.glob, list_file)
    if not sources:
        eprint("[FAIL] No source XML files provided/found.")
        return 1

    if args.skip_self and target.exists():
        t = str(target.resolve())
        before = len(sources)
        sources = [s for s in sources if str(s.resolve()) != t]
        if before != len(sources):
            print(f"[INFO] Skipped {before-len(sources)} source(s) matching target path")
        if not sources:
            eprint("[FAIL] No sources left after --skip-self filtering.")
            return 1

    if target.exists():
        target_tree = ET.parse(target)
        target_root = target_tree.getroot()
        target_db = _find_dbchanges_list(target_root)
    else:
        if not args.create_target:
            eprint(f"[FAIL] Target XML not found: {target}")
            eprint("       Use --create-target to create a new target from the first source wrapper.")
            return 1
        target_tree, target_db = _clone_wrapper_from_source(sources[0])

    existing_exact = set()
    existing_create_player_ids = set()

    target_records = _top_level_records(target_db)
    top_large_ids, player_ids, db_random_ids = _collect_existing_ids(target_records)

    if args.dedupe == "exact":
        for r in target_records:
            existing_exact.add(_record_hash(r))
    elif args.dedupe == "create":
        for r in target_records:
            _, pid = _find_create_ids(r)
            if pid:
                existing_create_player_ids.add(pid)

    total_read = total_added = total_skipped = 0
    total_id_remaps = 0
    total_dbrandom_remaps = 0
    files_ok = 0

    for src in sources:
        try:
            s_tree = ET.parse(src)
            s_root = s_tree.getroot()
            s_db = _find_dbchanges_list(s_root)
            src_records = _top_level_records(s_db)
        except Exception as ex:
            eprint(f"[WARN] Failed to parse {src}: {ex}")
            continue

        createid_map, playerid_map, remap_pairs = _build_collision_maps_for_source(
            src_records, top_large_ids, player_ids, auto_remap
        )
        total_id_remaps += remap_pairs

        file_read = file_add = file_skip = 0
        before_db_random_size = len(db_random_ids)

        for rec in src_records:
            file_read += 1
            total_read += 1

            # Apply remaps first (important: dedupe=create checks create-player-id after remap)
            rec2 = _apply_maps_to_record(rec, createid_map, playerid_map, db_random_ids, remap_db_random)

            if args.dedupe == "exact":
                h = _record_hash(rec2)
                if h in existing_exact:
                    file_skip += 1
                    total_skipped += 1
                    continue
                existing_exact.add(h)

            elif args.dedupe == "create":
                _, pid = _find_create_ids(rec2)
                if pid and pid in existing_create_player_ids:
                    file_skip += 1
                    total_skipped += 1
                    continue
                if pid:
                    existing_create_player_ids.add(pid)

            # Reserve top-level direct db_unique_id to avoid future collisions in same run
            dlarge = _record_direct_large_dbid(rec2)
            if dlarge:
                top_large_ids.add(dlarge)

            target_db.append(rec2)
            file_add += 1
            total_added += 1

        total_dbrandom_remaps += max(0, len(db_random_ids) - before_db_random_size - file_add)  # rough info only
        files_ok += 1
        if args.verbose:
            print(f"[OK] {src} -> read {file_read}, appended {file_add}, skipped {file_skip}, id_remaps={remap_pairs}")

    # Update db_changes size if attribute exists
    if "size" in target_db.attrib:
        target_db.attrib["size"] = str(len(_top_level_records(target_db)))

    print("=" * 100)
    print("FM26 XML Appender v2.1 summary")
    print(f"Target: {target}")
    print(f"Output: {output}")
    print(f"Sources processed: {files_ok}")
    print(f"Top-level records read: {total_read}")
    print(f"Top-level records appended: {total_added}")
    print(f"Top-level records skipped: {total_skipped} (dedupe={args.dedupe})")
    print(f"ID remaps applied (create/player collisions): {total_id_remaps}")
    print(f"Auto remap collisions: {args.auto_remap_collisions}")
    print("=" * 100)

    if args.dry_run:
        print("[DRY-RUN] No file written.")
        return 0

    if args.backup and output.exists():
        bak = output.with_suffix(output.suffix + ".bak")
        bak.write_bytes(output.read_bytes())
        print(f"[OK] Backup written: {bak}")

    _write(target_tree, output)
    print(f"[OK] Wrote merged XML: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
