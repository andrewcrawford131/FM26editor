# -*- coding: utf-8 -*-
from __future__ import annotations

class JobRolesMixin:
    def _build_job_role_options(self):
        """Build job/role labels for Non-Player and Player/Non-Player tabs.

        These labels mirror the FM editor dropdown style (e.g. 'Manager First Team', 'Manager (U21 Team)', 'Player/Coach First Team').
        Mapping to numeric 'job' values (property 1346587215) is wired separately once the mapping table is finalised.
        """
        # Board / executive roles (non-playing)
        board = [
            "Chairperson",
            "Owner",
            "Managing Director",
            "Director",
        ]

        # Club-wide staff roles (non-playing)
        clubwide = [
            "Director of Football",
            "Technical Director",
            "Head of Youth Development",
            "Chief Scout",
            "Scout",
            "Recruitment Analyst",
            "Loan Manager",
        ]

        # First team staff roles (non-playing)
        first_team = [
            "Manager First Team",
            "Assistant Manager First Team",
            "Coach First Team",
            "GK Coach First Team",
            "Fitness Coach First Team",
            "Set Piece Coach",
            "Head Performance Analyst",
            "Performance Analyst First Team",
            "Head Physio",
            "Physio First Team",
            "Head of Sports Science",
            "Sports Scientist First Team",
            "Chief Doctor",
            "Doctor First Team",
        ]

        # Reserve team staff roles (non-playing)
        reserve_team = [
            "Manager Reserve Team",
            "Assistant Manager Reserve Team",
            "Coach Reserve Team",
            "GK Coach Reserve Team",
            "Fitness Coach Reserve Team",
            "Performance Analyst Reserve Team",
            "Physio Reserve Team",
            "Sports Scientist Reserve Team",
            "Doctor Reserve Team",
        ]

        # Third team (seen in editor list)
        third_team = [
            "Manager Third Team",
        ]

        # Youth/Uxx team staff roles (non-playing)
        u_roles = ["Manager", "Assistant Manager", "Coach", "GK Coach", "Fitness Coach", "Performance Analyst", "Physio", "Sports Scientist", "Doctor"]
        u_levels = [23, 22, 21, 20, 19, 18]
        youth = [f"{r} (U{u} Team)" for u in u_levels for r in u_roles]

        # Youth teams aggregate (seen in editor list)
        youth_agg = ["Coach (Youth Teams)"]

        nonplayer = board + clubwide + first_team + reserve_team + third_team + youth + youth_agg

        # De-duplicate while preserving order
        seen = set()
        nonplayer_unique = []
        for x in nonplayer:
            if x and x not in seen:
                seen.add(x)
                nonplayer_unique.append(x)

        player_nonplayer = ["Player"] + [f"Player/{x}" for x in nonplayer_unique if x != "Player"]
        return nonplayer_unique, player_nonplayer
    # ---------------- Master library cache (clubs/cities/nations) ----------------
