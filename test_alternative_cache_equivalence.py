from __future__ import annotations

import unittest

from dark_horse_engine_v2 import DarkHorseEngineV2


class AlternativeCacheEquivalenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = DarkHorseEngineV2(
            motives_path="docs/data/micro_motives.json",
            majors_path="majors_database_v2.json",
            trait_map_path="trait_map_v3.json",
            value_poles_path="value_poles_v2.json",
            school_branches_path="school_branches_v2.json",
        )

    def test_major_cache_matches_fresh_computation_for_all_majors(self):
        self.assertEqual(len(self.engine.majors_db), 230)
        self.assertEqual(set(self.engine._alt_paths_cache), set(self.engine.majors_db))

        active_count = 0
        stub_count = 0
        for major_id, major_data in self.engine.majors_db.items():
            cached = self.engine._find_alternative_paths(major_id, top_n=3)
            fresh = self.engine._compute_alternative_paths(major_id, top_n=3)
            self.assertEqual(cached, fresh, major_id)
            if major_data.get("motive_driven") is False:
                stub_count += 1
                self.assertEqual(cached, [], f"Stub major {major_id} must not expose alternative paths")
            else:
                active_count += 1
                self.assertEqual(len(cached), 3, f"Active major {major_id} must have 3 alternative paths")

            for top_n in (1, 2, 3):
                self.assertEqual(
                    self.engine._find_alternative_paths(major_id, top_n=top_n),
                    fresh[:top_n],
                    f"{major_id}:top_n={top_n}",
                )

        self.assertEqual(active_count, 202)
        self.assertEqual(stub_count, 28)

    def test_branch_cache_matches_fresh_computation_for_all_branches(self):
        self.assertEqual(len(self.engine.school_branches), 4)
        self.assertEqual(
            set(self.engine._branch_alt_paths_cache),
            set(self.engine.school_branches),
        )

        for branch_name in self.engine.school_branches:
            cached = self.engine._find_branch_alternative_paths(branch_name, top_n=3)
            fresh = self.engine._compute_branch_alternative_paths(branch_name, top_n=3)
            self.assertEqual(cached, fresh, branch_name)

            for top_n in (1, 2, 3):
                self.assertEqual(
                    self.engine._find_branch_alternative_paths(branch_name, top_n=top_n),
                    fresh[:top_n],
                    f"{branch_name}:top_n={top_n}",
                )


if __name__ == "__main__":
    unittest.main(verbosity=2)
