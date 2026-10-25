from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from dark_horse_engine_v2 import DarkHorseEngineV2

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    161:{"prefix":"SPORT-","realm":"builder","subRealm":"builder-motion","pathId":"motion-design"},
    162:{"prefix":"ARCH-","realm":"builder","subRealm":"builder-structure","pathId":"structure-builders"},
    163:{"prefix":"TOURISM-","realm":"thinker","subRealm":"thinker-wealth","pathId":"wealth-business"},
    164:{"prefix":"QURAN-","realm":"thinker","subRealm":"thinker-history","pathId":"history-meaning-text"},
    165:{"prefix":"WATER-","realm":"builder","subRealm":"builder-earth","pathId":"earth-ecosystem"},
    166:{"prefix":"ARCHY-","realm":"thinker","subRealm":"thinker-history","pathId":"history-explorer"},
    167:{"prefix":"CARPET-","realm":"artist","subRealm":"artist-visual","pathId":"visual-graphic"},
    168:{"prefix":"CRAFT-","realm":"artist","subRealm":"artist-hand","pathId":"hand-craft"},
    169:{"prefix":"BIOTECH-","realm":"explorer","subRealm":"explorer-life","pathId":"life-engineer"},
    170:{"prefix":"ISLART-","realm":"artist","subRealm":"artist-hand","pathId":"hand-paint"},
    171:{"prefix":"HOTEL-","realm":"thinker","subRealm":"thinker-wealth","pathId":"wealth-business"},
    172:{"prefix":"INTARCH-","realm":"artist","subRealm":"artist-space","pathId":"space-architect"},
    173:{"prefix":"RELIG-","realm":"thinker","subRealm":"thinker-history","pathId":"history-meaning-text"},
    174:{"prefix":"FAMILY-","realm":"thinker","subRealm":"thinker-psych","pathId":"psych-education"},
    175:{"prefix":"FRENCH-","realm":"speaker","subRealm":"speaker-word","pathId":"word-literature"},
    176:{"prefix":"ARBTR-","realm":"speaker","subRealm":"speaker-word","pathId":"word-literature"}
}


def path_codes(data_js: str, path_id: str) -> list[str]:
    match = re.search(rf"id:'{re.escape(path_id)}'[\\s\\S]*?majorCodes:\\s*\\[([^\\]]*)\\]", data_js)
    if not match:
        raise AssertionError(f"path missing: {path_id}")
    return re.findall(r"'([^']+)'", match.group(1))


class Phase3CityPathTests(unittest.TestCase):
    def test_prefix_decks_and_city_mapping(self):
        root = json.loads((ROOT / "micro_motives.json").read_text(encoding="utf-8"))
        docs = json.loads((ROOT / "docs/data/micro_motives.json").read_text(encoding="utf-8"))
        majors = json.loads((ROOT / "majors_database_v2.json").read_text(encoding="utf-8"))
        data_js = (ROOT / "docs/data.js").read_text(encoding="utf-8")
        self.assertEqual(root, docs)
        for major_id, meta in EXPECTED.items():
            major = next(m for m in majors if m["id"] == major_id)
            expected_codes = [f"{meta['prefix']}{i:03d}" for i in range(1, 8)]
            self.assertEqual(major["micro_motive_codes"], expected_codes)
            self.assertTrue(major["motive_driven"])
            self.assertIn(meta["prefix"], path_codes(data_js, meta["pathId"]))
            self.assertEqual(
                [m["code"] for m in root if m["code"].startswith(meta["prefix"])],
                expected_codes,
            )
        self.assertEqual(path_codes(data_js, "rescue-crisis"), ["MED-", "EMER-"])
        self.assertEqual(path_codes(data_js, "justice-law"), ["LAW-"])

    def test_discover_includes_all_phase3_majors(self):
        engine = DarkHorseEngineV2(
            motives_path="docs/data/micro_motives.json",
            majors_path="majors_database_v2.json",
            trait_map_path="trait_map_v3.json",
            value_poles_path="value_poles_v2.json",
            school_branches_path="school_branches_v2.json",
        )
        user_motives = [
            f"{meta['prefix']}{i:03d}"
            for meta in EXPECTED.values()
            for i in range(1, 8)
        ]
        result = engine.discover_individuality(
            user_motives=user_motives,
            sjt_answers={f"sjt_{i}": "A" for i in range(1, 26)},
            conjoint_choices={f"conj_{i}": "Q1A" for i in range(1, 16)},
        )
        discovered = {item["major_id"] for item in result["discovered_majors"]}
        self.assertTrue({int(k) for k in EXPECTED}.issubset(discovered))


if __name__ == "__main__":
    unittest.main(verbosity=2)
