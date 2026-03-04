# -*- coding: utf-8 -*-
from __future__ import annotations

import hashlib
import json
import os
from typing import Dict, Optional, Tuple

# Keep the same constants as generator used
INT32_MOD = 2147483646
INT64_MOD = 9223372036854775806

# Per-run namespace salt for generated IDs.
ID_NAMESPACE_SALT = ""


def default_id_registry_path() -> str:
    try:
        base = os.path.dirname(os.path.abspath(__file__))
    except NameError:
        base = os.getcwd()
    # keep filename stable for existing users
    return os.path.join(base, "..", "fm26_player_generator_id_registry.json")


def load_id_registry(path: str) -> Dict[str, object]:
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


def save_id_registry(path: str, data: Dict[str, object]) -> None:
    d = os.path.dirname(os.path.abspath(path))
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    os.replace(tmp, path)


def reserve_id_namespace(seed: Optional[int], count: int, out_xml: str, registry_path: Optional[str] = None) -> Tuple[str, str]:
    path = registry_path or default_id_registry_path()
    reg = load_id_registry(path)
    serial = int(reg.get("next_run_serial", 1))
    reg["next_run_serial"] = serial + 1
    reg["last_run"] = {
        "serial": serial,
        "seed": seed,
        "count": int(count),
        "output": os.path.abspath(out_xml),
    }
    save_id_registry(path, reg)
    return (f"run{serial}", path)


def sha(seed: int, i: int, label: str) -> int:
    h = hashlib.sha256(f"{seed}|{ID_NAMESPACE_SALT}|{i}|{label}".encode("utf-8")).digest()
    return int.from_bytes(h, "big")


def id32(seed: int, i: int, label: str) -> int:
    return 1 + (sha(seed, i, label) % INT32_MOD)


def id64(seed: int, i: int, label: str) -> int:
    return 1 + (sha(seed, i, label) % INT64_MOD)


def uniq(make_id, seed: int, i: int, label: str, used: set, extra_ok=None) -> int:
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
