"""Regression checks for the P1.4 alternative-path audit."""
import unittest

from p1_4_intercluster_audit import build_audit


class InterclusterAlternativesAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.audit = build_audit()
        cls.by_target = {row["target_id"]: row for row in cls.audit["targets"]}

    def test_known_cluster_path_counts_are_reproducible(self):
        summary = self.audit["summary"]
        self.assertEqual(summary["major_count"], 230)
        self.assertEqual(summary["active_target_count"], 202)
        self.assertEqual(summary["known_cluster_target_count"], 187)
        self.assertEqual(summary["target_cluster_missing_count"], 15)
        self.assertEqual(summary["slots_for_known_cluster_targets"], 561)
        self.assertEqual(summary["same_cluster_slots"], 332)
        self.assertEqual(summary["cross_cluster_slots"], 224)
        self.assertEqual(summary["unknown_cluster_slots"], 50)
        self.assertEqual(summary["cross_pct_of_known_source_slots"], 39.93)
        self.assertEqual(summary["cross_pct_of_classifiable_slots"], 40.29)
        self.assertEqual(summary["targets_with_at_least_one_cross_cluster_path"], 123)
        self.assertEqual(summary["pct_known_cluster_targets_with_cross_cluster_path"], 65.78)

    def test_top3_are_distance_sorted_and_have_auditable_examples(self):
        for target in self.audit["targets"]:
            paths = target["alternatives"]
            self.assertEqual(len(paths), 3)
            self.assertEqual(
                [p["distance"] for p in paths],
                sorted(p["distance"] for p in paths),
            )

        expected = [
            (24, 113, 0.053),
            (35, 93, 0.067),
            (57, 97, 0.078),
            (18, 105, 0.147),
            (1, 104, 0.143),
        ]
        samples = {
            (row["target_id"], row["major_id"]): row["distance"]
            for row in self.audit["sample_cross_cluster_paths"]
        }
        for source, alternative, distance in expected:
            with self.subTest(source=source, alternative=alternative):
                self.assertEqual(samples[(source, alternative)], distance)

    def test_no_inactive_major_is_currently_returned_in_top3(self):
        self.assertEqual(self.audit["summary"]["inactive_candidates_in_top3"], 0)

    def test_cluster_mismatch_is_not_itself_a_filter(self):
        # Cross-cluster links remain in the top three when they are the smallest
        # S/V profile distances; this test prevents an arbitrary cluster-only drop.
        path = next(
            p for p in self.by_target[24]["alternatives"]
            if p["major_id"] == 113
        )
        self.assertEqual(path["relation"], "cross_cluster")
        self.assertEqual(path["rank"], 1)


if __name__ == "__main__":
    unittest.main()
