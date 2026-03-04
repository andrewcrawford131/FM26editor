# -*- coding: utf-8 -*-
from __future__ import annotations

import datetime as dt
from typing import Optional
from xml.sax.saxutils import escape as xesc

# Toggle via set_xml_comments() from generator CLI.
_XML_COMMENTS: bool = False

# Configured at runtime by generator (so no circular imports).
_TBL_PLAYER: Optional[int] = None
_TBL_CREATE: Optional[int] = None
_CREATE_PROPERTY: Optional[int] = None

DEFAULT_EDVB = 1
DEFAULT_RULE_GROUP_VERSION = 1630
DEFAULT_ORVS = "2600"
DEFAULT_SVVS = "2600"


def set_xml_comments(flag: bool) -> None:
    global _XML_COMMENTS
    _XML_COMMENTS = bool(flag)


def configure_tables(*, tbl_player: int, tbl_create: int, create_property: int) -> None:
    """Configure FM table/property constants used by writer."""
    global _TBL_PLAYER, _TBL_CREATE, _CREATE_PROPERTY
    _TBL_PLAYER = int(tbl_player)
    _TBL_CREATE = int(tbl_create)
    _CREATE_PROPERTY = int(create_property)


def _require_cfg() -> tuple[int, int, int]:
    if _TBL_PLAYER is None or _TBL_CREATE is None or _CREATE_PROPERTY is None:
        raise RuntimeError("xml_writer not configured: call configure_tables(tbl_player=..., tbl_create=..., create_property=...)")
    return int(_TBL_PLAYER), int(_TBL_CREATE), int(_CREATE_PROPERTY)


def _int(i: str, v: int) -> str:
    return f'<integer id="{i}" value="{int(v)}"/>'


def _large(i: str, v: int) -> str:
    return f'<large id="{i}" value="{int(v)}"/>'


def _uns(i: str, v: int) -> str:
    return f'<unsigned id="{i}" value="{int(v)}"/>'


def _str(i: str, s: str) -> str:
    return f'<string id="{i}" value="{xesc(str(s))}"/>'


def _bool(i: str, v: bool) -> str:
    return f'<boolean id="{i}" value="{"true" if bool(v) else "false"}"/>'


def _null(i: str) -> str:
    return f'<null id="{i}"/>'


def _date(i: str, d: dt.date) -> str:
    return f'<date id="{i}" day="{d.day}" month="{d.month}" year="{d.year}" time="0"/>'


def _rec(inner: str, comment: str = "") -> str:
    """Wrap a <record> for db_changes list."""
    c = f'<!-- {comment} -->' if (_XML_COMMENTS and comment) else ""
    return f"\t\t<record>{c}\n{inner}\t\t</record>\n"


def _attr(person_uid: int, prop: int, newv: str, rid: int, ver: int, extra: str = "", odvl: str = "") -> str:
    """Build a property record body (not wrapped). Caller usually does _rec(_attr(...))."""
    tbl_player, _, _ = _require_cfg()
    s = f"\t\t\t{_int('database_table_type', tbl_player)}\n"
    s += f"\t\t\t{_large('db_unique_id', int(person_uid))}\n"
    s += f"\t\t\t{_uns('property', int(prop))}\n"
    s += f"\t\t\t{newv}\n"
    s += f"\t\t\t{_int('version', int(ver))}\n"
    s += f"\t\t\t{_int('db_random_id', int(rid))}\n"
    if extra:
        s += extra
    if odvl:
        s += f"\t\t\t{odvl}\n"
    return s


def _create(create_uid: int, person_uid: int, rid: int, ver: int) -> str:
    """Create-record used to create a new player/person row."""
    tbl_player, tbl_create, create_prop = _require_cfg()

    inner = f"\t\t\t{_int('database_table_type', tbl_create)}\n"
    inner += f"\t\t\t{_large('db_unique_id', int(create_uid))}\n"
    inner += f"\t\t\t{_uns('property', int(create_prop))}\n"
    inner += "\t\t\t<record id=\"new_value\">\n"
    inner += f"\t\t\t\t{_int('database_table_type', tbl_player)}\n"
    inner += f"\t\t\t\t{_uns('dcty', 2)}\n"
    inner += f"\t\t\t\t{_large('db_unique_id', int(person_uid))}\n"
    inner += "\t\t\t</record>\n"
    inner += f"\t\t\t{_int('version', int(ver))}\n"
    inner += f"\t\t\t{_int('db_random_id', int(rid))}\n"
    inner += f"\t\t\t{_bool('is_client_field', True)}\n"
    return _rec(inner)


def _count_existing(xml_path: str) -> int:
    """Count existing create records in an existing db_changes XML."""
    _, _, create_prop = _require_cfg()
    with open(xml_path, "rb") as f:
        data = f.read()
    needle = f'<unsigned id="property" value="{int(create_prop)}"/>'.encode("utf-8")
    return data.count(needle)


def _append(existing_xml: str, frag: str, out_xml: str) -> None:
    """Append frag into the db_changes list of an existing FM db_changes XML."""
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


def write_new_db_changes(out_xml: str, frag: str, *, version: int,
                         edvb: int = DEFAULT_EDVB,
                         rule_group_version: int = DEFAULT_RULE_GROUP_VERSION,
                         orvs: str = DEFAULT_ORVS,
                         svvs: str = DEFAULT_SVVS) -> None:
    """Write a fresh db_changes XML containing frag."""
    with open(out_xml, "w", encoding="utf-8", newline="\n") as f:
        f.write("<record>\n\t<list id=\"verf\"/>\n\t<list id=\"db_changes\">\n")
        f.write(frag)
        f.write("\t</list>\n")
        f.write(f'\t<integer id="EDvb" value="{int(edvb)}"/>\n\t<string id="EDfb" value=""/>\n')
        f.write(f'\t<integer id="version" value="{int(version)}"/>\n\t<integer id="rule_group_version" value="{int(rule_group_version)}"/>\n')
        f.write('\t<boolean id="beta" value="false"/>\n')
        f.write(f'\t<string id="orvs" value="{xesc(str(orvs))}"/>\n\t<string id="svvs" value="{xesc(str(svvs))}"/>\n</record>\n')
