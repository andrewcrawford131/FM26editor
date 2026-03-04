# -*- coding: utf-8 -*-
from __future__ import annotations

class DetailsUtilsMixin:
    def _details_gender_to_int(self, label: str):
        lab = (label or "").strip().lower()
        if not lab:
            return None
        if lab in ("male", "m"):
            return 0
        if lab in ("female", "f"):
            return 1
        raise ValueError("Gender must be Male or Female.")
    def _details_ethnicity_to_int(self, label: str):
        lab = (label or "").strip()
        if not lab:
            return None
        mapping = {
            "Unknown": -1,
            "Northern European": 0,
            "Mediterranean/Hispanic": 1,
            "North African/Middle Eastern": 2,
            "African/Caribbean": 3,
            "Asian": 4,
            "South East Asian": 5,
            "Pacific Islander": 6,
            "Native American": 7,
            "Native Australian": 8,
            "Mixed Race": 9,
            "East Asian": 10,
        }
        if lab not in mapping:
            raise ValueError("Ethnicity option is not recognised.")
        return mapping[lab]
