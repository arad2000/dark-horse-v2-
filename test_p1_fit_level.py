"""Unit tests for the calibrated compatibility labels (P1.1)."""
import unittest

from dark_horse_engine_v2 import DarkHorseEngineV2


class FitLevelCalibrationTests(unittest.TestCase):
    def test_exact_band_boundaries(self):
        get_level = DarkHorseEngineV2._get_fit_level
        cases = [
            (100.0, "همخوانی بسیار بالا"),
            (90.0, "همخوانی بسیار بالا"),
            (89.9, "همخوانی بالا"),
            (80.0, "همخوانی بالا"),
            (79.9, "همخوانی متوسط"),
            (50.0, "همخوانی متوسط"),
            (49.9, "همخوانی پایین"),
            (0.0, "همخوانی پایین"),
        ]
        for score, expected in cases:
            with self.subTest(score=score):
                self.assertEqual(get_level(score), expected)

    def test_labels_are_monotonic_with_score(self):
        get_level = DarkHorseEngineV2._get_fit_level
        ordered = [
            get_level(0.0),
            get_level(50.0),
            get_level(80.0),
            get_level(90.0),
        ]
        self.assertEqual(
            ordered,
            [
                "همخوانی پایین",
                "همخوانی متوسط",
                "همخوانی بالا",
                "همخوانی بسیار بالا",
            ],
        )


if __name__ == "__main__":
    unittest.main()
