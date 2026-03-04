# -*- coding: utf-8 -*-
from __future__ import annotations

import csv
import os
import re
from typing import Dict, List, Optional, Tuple

# (dbid, large) -> 'male' / 'female' / '' (if unknown)
CLUB_GENDER_MAP: Dict[Tuple[int, int], str] = {}


def _detect_delim(sample: str) -> str:
    return "\t" if sample.count("\t") > sample.count(",") else ","


def _strip_excel(s: str) -> str:
    s = (s or "").strip()
    # handle Excel exported cells like ="123"
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
    """Load the master library CSV.

    Returns:
      clubs:  list of (club_dbid, club_large, club_name, club_gender?)  (we keep the same tuple shape where possible)
      cities: list of (city_dbid, city_large, city_name)
      nations:list of (nation_dbid, nation_large, nation_name)

    Also populates CLUB_GENDER_MAP for (club_dbid, club_large)->gender.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        head = f.readline()
        if not head:
            raise ValueError("CSV empty")
        delim = _detect_delim(head)
        f.seek(0)

        r = csv.DictReader(f, delimiter=delim)
        clubs: Dict[Tuple[int, int], Tuple[int, int, str, str]] = {}
        cities: Dict[Tuple[int, int], Tuple[int, int, str]] = {}
        nations: Dict[Tuple[int, int], Tuple[int, int, str]] = {}

        for row in r:
            d = {(k or "").strip().lower(): (v or "").strip() for k, v in (row or {}).items()}

            kind = (d.get("type") or d.get("kind") or "").strip().lower()
            if kind not in ("club", "city", "nation"):
                # Heuristics when 'type/kind' column is absent
                if d.get("club_dbid") or d.get("club_large") or d.get("ttea_large") or d.get("ttea_large_text"):
                    kind = "club"
                elif d.get("city_dbid") or d.get("city_large") or d.get("city_large_text"):
                    kind = "city"
                elif d.get("nation_dbid") or d.get("nation_large") or d.get("nnat") or d.get("nnat_large") or d.get("nnat_large_text"):
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

        # Preserve the original tuple shapes used by generator:
        # clubs were historically (dbid, large, name, gender)
        return list(clubs.values()), list(cities.values()), list(nations.values())

# ---------------- Nation lookup helpers (extracted) ----------------
import re as _re
import unicodedata as _ud
from typing import Dict as _Dict, Tuple as _Tuple, Optional as _Optional, List as _List


def _norm_name_key(s: str) -> str:
    '''Normalize a nation name into a forgiving key for lookups.'''
    if s is None:
        return ""
    s = str(s).strip().lower()
    if not s:
        return ""
    # drop accents
    s = "".join(ch for ch in _ud.normalize("NFKD", s) if not _ud.combining(ch))
    # common punctuation -> spaces
    s = _re.sub(r"[^a-z0-9]+", " ", s)
    s = _re.sub(r"\s+", " ", s).strip()
    return s


def _build_nation_lookup(nations: _List[tuple]) -> _Dict[str, _Tuple[int, int, str]]:
    '''Build a lookup dict from the nations tuples returned by load_master_library().

    Expected nation tuple shape: (dbid, large, name) or (dbid, large, name, ...)
    Returns: key -> (dbid, large, name)
    '''
    out: _Dict[str, _Tuple[int, int, str]] = {}
    for n in nations or []:
        try:
            dbid = int(n[0])
            large = int(n[1])
            name = str(n[2]) if len(n) > 2 else ""
        except Exception:
            continue
        k = _norm_name_key(name)
        if not k:
            continue
        # Prefer first seen to keep deterministic.
        out.setdefault(k, (dbid, large, name))
        # light aliases
        if " and " in k:
            out.setdefault(k.replace(" and ", " & "), (dbid, large, name))
            out.setdefault(k.replace(" and ", " "), (dbid, large, name))
    return out


def _resolve_nation_from_lookup(label: str, lookup: _Dict[str, _Tuple[int, int, str]]) -> _Optional[_Tuple[int, int, str]]:
    '''Resolve a label into (dbid, large, name) using lookup.

    Accepts:
      - "Scotland (DBID 11)" or "DBID 11"
      - plain "Scotland"
    '''
    if not label:
        return None
    s = str(label).strip()
    if not s:
        return None

    # 1) DBID hint match (best effort)
    m = _re.search(r"DBID\s*(\d+)", s, flags=_re.I)
    if m:
        want = m.group(1)
        for _, v in (lookup or {}).items():
            try:
                if str(v[0]) == want:
                    return v
            except Exception:
                continue

    # 2) Name key lookup (use left of parentheses)
    name = s.split("(")[0].strip()
    k = _norm_name_key(name)
    if not k:
        return None
    hit = (lookup or {}).get(k)
    if hit:
        return hit

    return None


def _parse_second_nation_specs(spec: str) -> _List[str]:
    '''Parse a second-nation spec string into tokens.

    Accepts formats like:
      - "Scotland|England|Wales"
      - "Scotland, England; Wales"
    Returns list of cleaned names (not DBIDs).
    '''
    if not spec:
        return []
    s = str(spec).strip()
    if not s:
        return []
    parts = _re.split(r"[|,;]+", s)
    out = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
    return out

# -------------------------------------------------------------------
