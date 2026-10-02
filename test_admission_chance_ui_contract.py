from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parent
UI = ROOT / "docs" / "admission_chance_ui.js"
INDEX = ROOT / "docs" / "index.html"


class AdmissionChanceUICapacityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ui = UI.read_text(encoding="utf-8")
        cls.index = INDEX.read_text(encoding="utf-8")

    def test_exam_tab_uses_capacity_contract(self):
        self.assertIn("data-source="capacity"", self.ui)
        self.assertIn("source: 'capacity'", self.ui)
        self.assertIn("admission_path: 'exam'", self.ui)
        self.assertIn("periods: values.period ? [values.period] : []", self.ui)

    def test_exam_capacity_active_fields_are_major_province_period(self):
        self.assertIn('name="major_id"', self.ui)
        self.assertIn('name="school_province_3y"', self.ui)
        self.assertIn('name="period"', self.ui)
        self.assertIn('id="dh-admission-exam-rank" type="text" value="در این فاز استفاده نمی‌شود" disabled', self.ui)
        self.assertIn('id="dh-admission-exam-region" disabled', self.ui)
        self.assertIn('id="dh-admission-exam-special-quota" disabled', self.ui)

    def test_capacity_card_contains_required_fields(self):
        for token in (
            "کد رشته‌محل:",
            "استان:",
            "دوره:",
            "ظرفیت کل:",
            "item.note",
        ):
            self.assertIn(token, self.ui)

    def test_empty_capacity_is_not_rejection_message(self):
        self.assertIn("این پیام به معنی رد شدن داوطلب نیست", self.ui)

    def test_cache_bust_loads_new_ui_and_css(self):
        self.assertIn('admission_chance_ui.js?v=2', self.index)
        self.assertIn('admission_chance_ui.css?v=1', self.index)

    def test_no_engine_or_shell_changes_are_required(self):
        self.assertNotIn("app.js", self.ui)
        self.assertNotIn("shell.js", self.ui)


if __name__ == "__main__":
    unittest.main(verbosity=2)
