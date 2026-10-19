"""Regression checks for the report-only S/V rank harness."""
import unittest

from p1_3_sv_rank_harness import analyze_target


class SVRankHarnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = analyze_target(42)

    def test_target_profile_components(self):
        components = self.report["target_components_pct"]
        self.assertEqual(components["M"], 100.0)
        self.assertEqual(components["S"], 100.0)
        self.assertAlmostEqual(components["V"], 75.6, places=1)
        self.assertAlmostEqual(components["Total"], 92.7, places=1)

    def test_s_v_and_current_total_ranks_are_reproducible(self):
        rank = self.report["rank"]
        self.assertEqual((rank["S_only"]["rank"], rank["S_only"]["universe_size"]), (1, 202))
        self.assertEqual((rank["V_only"]["rank"], rank["V_only"]["universe_size"]), (8, 202))
        self.assertEqual((rank["current_Total"]["rank"], rank["current_Total"]["universe_size"]), (1, 2))

    def test_total_formula_and_catalog_pair_remain_report_only(self):
        self.assertEqual(self.report["protocol"]["total_formula"], "0.55*M + 0.30*V + 0.15*S")
        results = self.report["eligible_total_results"]
        self.assertEqual([item["major_id"] for item in results], [42, 44])
        self.assertAlmostEqual(results[0]["Total"], 92.7, places=1)
        self.assertAlmostEqual(results[1]["Total"], 85.0, places=1)


if __name__ == "__main__":
    unittest.main()
