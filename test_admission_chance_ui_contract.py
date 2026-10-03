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
        self.assertIn('id="dh-admission-exam-source" name="source" required', self.ui)
        self.assertIn('<option value="capacity">ظرفیت دفترچه</option>', self.ui)
        self.assertIn('<option value="program">مقایسه با آخرین رتبه</option>', self.ui)
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

    def test_exam_modes_keep_capacity_contract_and_add_rank_compare(self):
        self.assertIn('name="group"', self.ui)
        self.assertIn('name="major_id"', self.ui)
        self.assertIn('name="school_province_3y"', self.ui)
        self.assertIn('name="period"', self.ui)
        self.assertIn('name="rank_in_quota"', self.ui)
        self.assertIn('name="region_zone"', self.ui)
        self.assertIn('form.rank_in_quota.disabled = !isProgram', self.ui)
        self.assertIn('form.region_zone.disabled = !isProgram', self.ui)
        self.assertIn('form.group.disabled = isProgram', self.ui)
        self.assertIn('form.period.disabled = isProgram', self.ui)

    def test_exam_capacity_and_rank_compare_payloads(self):
        capacity_start = self.ui.index(
            "    return {\\n      admission_path: 'exam',\\n      source: 'capacity'"
        )
        capacity_end = self.ui.index(
            "    };",
            capacity_start,
        ) + len("    };")
        payload = self.ui[capacity_start:capacity_end]
        self.assertIn("source: 'capacity'", payload)
        self.assertIn("group:", payload)
        self.assertIn("major_ids:", payload)
        self.assertIn("province:", payload)
        self.assertIn("periods:", payload)
        self.assertIn("include_unknown: false", payload)
        self.assertNotIn("rank_in_quota", payload)
        self.assertNotIn("region_zone", payload)

        program_start = self.ui.index(
            "    if (values.source === 'program')"
        )
        program_end = self.ui.index(
            "\\n    }\\n\\n    return {",
            program_start,
        )
        program_payload = self.ui[program_start:program_end]
        self.assertIn("source: 'program'", program_payload)
        self.assertIn("major_ids:", program_payload)
        self.assertIn("rank_in_quota:", program_payload)
        self.assertIn("region_zone:", program_payload)
        self.assertIn("province:", program_payload)
        self.assertNotIn("periods:", program_payload)
        self.assertNotIn("group:", program_payload)

    def test_rank_comparison_render_contract(self):
        for token in (
            "renderRankComparisonItems",
            "status_label",
            "cutoff_reference",
            "above",
            "near",
            "below",
            "unknown",
        ):
            self.assertIn(token, self.ui)
        self.assertIn("این مقایسه فقط با دادهٔ cutoff تاریخی موجود انجام شده", self.ui)

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
