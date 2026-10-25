from __future__ import annotations

import unittest

from dark_horse_engine_v2 import DarkHorseEngineV2


class MotiveDrivenDiscoveryGuardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DarkHorseEngineV2(
            motives_path="docs/data/micro_motives.json",
            majors_path="majors_database_v2.json",
            trait_map_path="trait_map_v3.json",
            value_poles_path="value_poles_v2.json",
            school_branches_path="school_branches_v2.json",
        )

    def test_phase2_stub_majors_are_never_discovered(self):
        user_motives = ["P2-161-EDU-001"]
        sjt_answers = {f"sjt_{i}": "A" for i in range(1, 26)}
        conjoint_choices = {f"conj_{i}": "Q1A" for i in range(1, 16)}

        result = self.engine.discover_individuality(
            user_motives=user_motives,
            sjt_answers=sjt_answers,
            conjoint_choices=conjoint_choices,
        )

        discovered_ids = {
            item["major_id"]
            for item in result["discovered_majors"]
        }

        self.assertNotIn(161, discovered_ids)
        for major_id in range(161, 177):
            self.assertNotIn(major_id, discovered_ids)


if __name__ == "__main__":
    unittest.main(verbosity=2)
