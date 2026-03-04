# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

# XML writer bindings (for push_attr)
from peoplegen import xml_writer as _xmlw
_rec = _xmlw._rec
_attr = _xmlw._attr



RidFunc = Callable[[str], int]
IsOmittedFunc = Callable[..., bool]


@dataclass
class Emitter:
    # A reference to the shared fragment list in the generator
    frags: List[str]
    # Omit checker (closure in generator). Signature is flexible: *names -> bool.
    is_omitted: Optional[IsOmittedFunc] = None
    # Record-id generator (closure in generator)
    rid_func: Optional[RidFunc] = None

    def rid(self, lbl: str) -> int:
        if not self.rid_func:
            raise RuntimeError("Emitter.rid() called but rid_func is None")
        return int(self.rid_func(str(lbl)))

    def omitted(self, *names: str) -> bool:
        if not self.is_omitted:
            return False
        try:
            return bool(self.is_omitted(*names))
        except Exception:
            return False

    def push(self, frag: str, *names: str) -> None:
        # Gate if any names are provided and they are omitted
        if names and self.omitted(*names):
            return
        self.frags.append(str(frag))



    def push_attr(self, person_uid, prop: int, newv: str, rid_lbl: str, version: int, comment: str = "",
                  *names: str, extra: str = "", odvl: str = "") -> None:
        """Emit a property record with omit gating.

        Builds the record via xml_writer:
          _rec(_attr(person_uid, prop, newv, rid(rid_lbl), version, extra=..., odvl=...), comment)
        and appends it to frags if not omitted.
        """
        try:
            ridv = self.rid(str(rid_lbl))
        except Exception:
            ridv = int(self.rid(str(rid_lbl)))
        inner = _attr(person_uid, int(prop), str(newv), int(ridv), int(version), extra=str(extra) if extra else "", odvl=str(odvl) if odvl else "")
        self.push(_rec(inner, str(comment) if comment else ""), *names)

__all__ = [k for k in globals().keys() if not k.startswith("__")]
