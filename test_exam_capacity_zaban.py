from __future__ import annotations

import unittest

from admission_exam_capacity import CAPACITY_PATHS, build_exam_capacity_results


class ZabanExamCapacityLoaderTests(unittest.TestCase):
    def test_zaban_uses_1405_source_and_honar_stays_1404(self):
        self.assertIn("sanjesh_zaban_1405_programs.json", str(CAPACITY_PATHS["zaban"]))
        self.assertIn("sanjesh_honar_1404_programs.json", str(CAPACITY_PATHS["honar"]))

    def test_zaban_english_tehran_daily_returns_1405_capacity(self):
        items = build_exam_capacity_results(
            group="zaban",
            major_ids=[147],  # آموزش زبان انگلیسی
            province="تهران",
            periods=["روزانه"],
            limit=5,
        )
        self.assertGreater(len(items), 0)
        self.assertTrue(all(item["sanjesh_code"] for item in items))
        self.assertTrue(all(item["province"] == "تهران" for item in items))
        self.assertTrue(all(item["period"] == "روزانه" for item in items))


if __name__ == "__main__":
    unittest.main(verbosity=2)
