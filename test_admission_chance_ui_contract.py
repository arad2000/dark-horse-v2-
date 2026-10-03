from pathlib import Path
import re
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
        self.assertIn('data-source="capacity"', self.ui)
        self.assertIn("source: 'capacity'", self.ui)
        self.assertIn("admission_path: 'exam'", self.ui)
        self.assertIn("periods: values.period ? [values.period] : []", self.ui)

    def test_exam_capacity_group_selector_is_required_and_mapped(self):
        self.assertIn('id="dh-admission-exam-group" name="group" required', self.ui)
        for token in (
            "{ value: 'riazi', label: 'ریاضی' }",
            "{ value: 'tajrobi', label: 'تجربی' }",
            "{ value: 'ensani', label: 'انسانی' }",
            "{ value: 'honar', label: 'هنر' }",
            "{ value: 'zaban', label: 'زبان' }",
        ):
            self.assertIn(token, self.ui)
        self.assertIn("group: EXAM_GROUP_LABELS[values.group] ? values.group : 'riazi'", self.ui)
        self.assertIn("String(form.group.value || 'riazi').trim() || 'riazi'", self.ui)

    def test_exam_capacity_active_fields_are_group_major_province_period(self):
        self.assertIn('name="group"', self.ui)
        self.assertIn('name="major_id"', self.ui)
        self.assertIn('name="school_province_3y"', self.ui)
        self.assertIn('name="period"', self.ui)
        self.assertIn('id="dh-admission-exam-rank" type="text" value="در این فاز استفاده نمی‌شود" disabled', self.ui)
        self.assertIn('id="dh-admission-exam-region" disabled', self.ui)
        self.assertIn('id="dh-admission-exam-special-quota" disabled', self.ui)

    def test_exam_capacity_payload_excludes_rank_region_quota(self):
        match = re.search(
            r"return \{\n      admission_path: 'exam',[\s\S]*?\n    \};",
            self.ui,
        )
        self.assertIsNotNone(match)
        payload_block = match.group(0)
        self.assertIn("admission_path: 'exam'", payload_block)
        self.assertIn("source: 'capacity'", payload_block)
        self.assertIn("group: EXAM_GROUP_LABELS[values.group] ? values.group : 'riazi'", payload_block)
        self.assertIn("major_ids:", payload_block)
        self.assertIn("province:", payload_block)
        self.assertIn("periods:", payload_block)
        self.assertIn("include_unknown: false", payload_block)
        self.assertNotIn("rank_in_quota", payload_block)
        self.assertNotIn("region_zone", payload_block)
        self.assertNotIn("special_quota", payload_block)

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
        self.assertIn('admission_chance_ui.js?v=9', self.index)
        self.assertIn('admission_chance_ui.css?v=3', self.index)

    def test_no_engine_or_shell_changes_are_required(self):
        self.assertNotIn("app.js", self.ui)
        self.assertNotIn("shell.js", self.ui)


if __name__ == "__main__":
    unittest.main(verbosity=2)
