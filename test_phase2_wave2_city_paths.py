from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

from dark_horse_engine_v2 import DarkHorseEngineV2

ROOT = Path(__file__).resolve().parent
EXPECTED = {
    177: {"prefix": "PLANTGEN-", "realm": "builder", "subRealm": "builder-earth", "pathId": "earth-produce"},
    178: {"prefix": "PROARCH-", "realm": "builder", "subRealm": "builder-structure", "pathId": "structure-builders"},
    179: {"prefix": "SOIL-", "realm": "builder", "subRealm": "builder-earth", "pathId": "earth-ecosystem"},
    180: {"prefix": "NATURE-", "realm": "builder", "subRealm": "builder-earth", "pathId": "earth-ecosystem"},
    181: {"prefix": "FISHSCI-", "realm": "builder", "subRealm": "builder-earth", "pathId": "earth-produce"},
    182: {"prefix": "MATSCI-", "realm": "builder", "subRealm": "builder-transform", "pathId": "transform-material"},
    183: {"prefix": "LIS-", "realm": "thinker", "subRealm": "thinker-society", "pathId": "knowledge-organization"},
    184: {"prefix": "PROCOMP-", "realm": "builder", "subRealm": "builder-digital", "pathId": "digital-logic"},
    185: {"prefix": "FORESTRY-", "realm": "builder", "subRealm": "builder-earth", "pathId": "earth-ecosystem"},
    186: {"prefix": "LANDSCAPE-", "realm": "artist", "subRealm": "artist-space", "pathId": "space-architect"},
    187: {"prefix": "PRESCHOOL-", "realm": "thinker", "subRealm": "thinker-psych", "pathId": "psych-education"},
    188: {"prefix": "HEALTHIT-", "realm": "healer", "subRealm": "healer-system", "pathId": "system-it"},
    189: {"prefix": "MANUPROD-", "realm": "builder", "subRealm": "builder-transform", "pathId": "transform-process"},
    190: {"prefix": "RADTECH-", "realm": "healer", "subRealm": "healer-detect", "pathId": "detect-image"},
    191: {"prefix": "DRAMA-", "realm": "artist", "subRealm": "artist-space", "pathId": "space-stage"},
    192: {"prefix": "CINEMA-", "realm": "artist", "subRealm": "artist-space", "pathId": "screen-cinema"}
}
EXPECTED_MAJOR_COUNT = 192
LEGACY_1_176_FNV1A64 = "89829a83a5975ef5"

def canonical(value):
    if isinstance(value, list): return [canonical(v) for v in value]
    if isinstance(value, dict): return {k: canonical(value[k]) for k in sorted(value)}
    return value

def fnv1a64_utf8(value):
    h = 1469598103934665603
    prime = 1099511628211
    mask = (1 << 64) - 1
    for byte in value.encode('utf-8'):
        h ^= byte
        h = (h * prime) & mask
    return f'{h:016x}'

def path_codes(data_js: str, path_id: str) -> list[str]:
    marker = "id:'" + path_id + "'"
    start = data_js.find(marker)
    if start < 0: raise AssertionError(f'path missing: {path_id}')
    codes_at = data_js.find('majorCodes:', start)
    if codes_at < 0: raise AssertionError(f'majorCodes missing: {path_id}')
    end = data_js.find(']', codes_at)
    return re.findall(r"'([^']+)'", data_js[codes_at:end])

class Phase2Wave2CityPathTests(unittest.TestCase):
    def setUp(self):
        self.majors = json.loads((ROOT / 'majors_database_v2.json').read_text(encoding='utf-8'))
        self.root = json.loads((ROOT / 'micro_motives.json').read_text(encoding='utf-8'))
        self.docs = json.loads((ROOT / 'docs/data/micro_motives.json').read_text(encoding='utf-8'))
        self.data_js = (ROOT / 'docs/data.js').read_text(encoding='utf-8')

    def test_catalog_count_and_legacy_fingerprint(self):
        self.assertEqual(len(self.majors), EXPECTED_MAJOR_COUNT)
        self.assertEqual([m['id'] for m in self.majors], list(range(1, EXPECTED_MAJOR_COUNT + 1)))
        self.assertEqual(fnv1a64_utf8(json.dumps(canonical(self.majors[:176]), ensure_ascii=False, separators=(',', ':'))), LEGACY_1_176_FNV1A64)

    def test_new_majors_and_weights(self):
        codes = [x['code'] for x in self.root]
        self.assertEqual(self.root, self.docs)
        self.assertEqual(len(codes), len(set(codes)))
        for major_id, meta in EXPECTED.items():
            major = next(m for m in self.majors if m['id'] == major_id)
            exp = [f"{meta['prefix']}{i:03d}" for i in range(1, 8)]
            self.assertTrue(major['handcrafted'])
            self.assertTrue(major['motive_driven'])
            self.assertIn('phase2_wave2_behavioral_cal_v1', major['weights_version'])
            self.assertEqual(major['micro_motive_codes'], exp)
            self.assertEqual([x for x in codes if x.startswith(meta['prefix'])], exp)
            self.assertEqual(len(major['strategy_weights']), 25)
            self.assertTrue(all(len(row) == 5 for row in major['strategy_weights']))
            for row in major['strategy_weights']: self.assertAlmostEqual(sum(row), 1.0, places=9)
            self.assertEqual(set(major['value_weights']), {f'Q{i}{s}' for i in range(1,16) for s in ('A','B')})

    def test_swipe_paths_and_MED_LAW_regression(self):
        for major_id, meta in EXPECTED.items():
            prefix = meta['prefix']
            self.assertIn(prefix, path_codes(self.data_js, meta['pathId']))
            self.assertEqual([c for c in self.root if c['code'].startswith(prefix)], [f'{prefix}{i:03d}' for i in range(1,8)])
        self.assertEqual(path_codes(self.data_js, 'rescue-crisis'), ['MED-', 'EMER-'])
        self.assertEqual(path_codes(self.data_js, 'justice-law'), ['LAW-'])

    def test_discover_all_16_new_ids(self):
        engine = DarkHorseEngineV2(motives_path='docs/data/micro_motives.json', majors_path='majors_database_v2.json', trait_map_path='trait_map_v3.json', value_poles_path='value_poles_v2.json', school_branches_path='school_branches_v2.json')
        motives = sorted(f"{meta['prefix']}{i:03d}" for meta in EXPECTED.values() for i in range(1,8))
        result = engine.discover_individuality(user_motives=motives, sjt_answers={f'sjt_{i}':'A' for i in range(1,26)}, conjoint_choices={f'conj_{i}':'Q1A' for i in range(1,16)})
        discovered = {int(x['major_id']) for x in result['discovered_majors']}
        self.assertTrue(set(EXPECTED).issubset(discovered))
        self.assertEqual(len(set(EXPECTED) & discovered), 16)

if __name__ == '__main__':
    unittest.main(verbosity=2)
