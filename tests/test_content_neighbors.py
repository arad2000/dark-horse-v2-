"""Offline source-neighborhood regressions; no API/DB/credentials required.
Run: python -m unittest discover -s tests -p test_content_neighbors.py
"""
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dark_horse_engine_v2 import DarkHorseEngineV2, MAJOR_CONTENT_NEIGHBORS


class ContentNeighborsTest(unittest.TestCase):
    def setUp(self):
        self.engine = DarkHorseEngineV2.__new__(DarkHorseEngineV2)
        self.engine.majors_db = {
            m['id']: m for m in json.loads((ROOT / 'majors_database_v2.json').read_text())
        }
        self.engine.school_branches = {}
        self.engine._alt_paths_cache = {}
        self.engine._branch_alt_paths_cache = {}

    def test_explicit_subject_neighbors(self):
        expected = {101: [208, 215, 105], 208: [101, 215, 105], 133: [173, 164]}
        for source, ids in expected.items():
            result = self.engine._find_alternative_paths(source)
            self.assertEqual([x['major_id'] for x in result], ids)
            for row in result:
                self.assertEqual(row['matching_method'], 'explicit_content_neighbors_v1')
                self.assertNotIn('distance', row)
                self.assertNotIn('value_distance', row)
                self.assertNotIn('strategy_distance', row)
                self.assertNotEqual(row['major_id'], source)
                self.assertEqual(row['major_name'], self.engine.majors_db[row['major_id']]['name'])

    def test_weights_and_catalog_order_cannot_change_neighbors(self):
        before = {k: self.engine._find_alternative_paths(k) for k in MAJOR_CONTENT_NEIGHBORS}
        self.engine.majors_db = dict(reversed(list(self.engine.majors_db.items())))
        for major in self.engine.majors_db.values():
            major['strategy_weights'] = [[999] * 5] * 25
            major['value_weights'] = {'Q1A': -999}
        for k, expected in before.items():
            self.assertEqual(self.engine._find_alternative_paths(k), expected)

    def test_no_numeric_fallback_for_unreviewed_or_missing_ids(self):
        self.engine._hybrid_profile_distance = lambda *a, **kw: self.fail('numeric fallback called')
        self.engine._strategy_profile_vector = lambda *a, **kw: self.fail('strategy fallback called')
        for k in self.engine.majors_db:
            if k not in MAJOR_CONTENT_NEIGHBORS:
                self.assertEqual(self.engine._find_alternative_paths(k), [])
        self.assertEqual(self.engine._find_alternative_paths(-1), [])

    def test_cache_and_limits(self):
        direct = self.engine._find_alternative_paths(101)
        self.engine._precompute_alternative_paths()
        self.assertEqual(self.engine._find_alternative_paths(101), direct)
        self.assertEqual(self.engine._find_alternative_paths(101, 1), direct[:1])
        self.assertEqual(self.engine._compute_alternative_paths(133, 10), self.engine._find_alternative_paths(133))
        self.assertEqual(self.engine._compute_alternative_paths(101, 0), [])
        returned = self.engine._find_alternative_paths(101)
        returned.pop()
        self.assertEqual(self.engine._find_alternative_paths(101), direct)

    def test_catalog_id_drift_fails_closed(self):
        self.engine.majors_db[133]['name'] = 'unexpected subject'
        self.assertEqual(self.engine._find_alternative_paths(133), [])
        self.engine.majors_db[208]['name'] = 'unexpected subject'
        self.assertNotIn(208, [x['major_id'] for x in self.engine._find_alternative_paths(101)])
        del self.engine.majors_db[215]
        self.assertEqual([x['major_id'] for x in self.engine._find_alternative_paths(101)], [105])

    def test_all_other_engine_bytes_unchanged(self):
        # Fingerprint of main 3d99539b excluding ONLY the replaced major-neighbor
        # method and the new explicit table. Locks Total, M/S/V, gates, Hybrid,
        # branch alternatives, discovery, sorting and all other engine code.
        source = (ROOT / 'dark_horse_engine_v2.py').read_text()
        start = source.index('# Explicit subject/work neighbors,')
        end = source.index('class DarkHorseEngineV2:', start)
        source = source[:start] + source[end:]
        start = source.index('    def _compute_alternative_paths(')
        end = source.index('    # ── مسیرهای جایگزین برای شاخه‌های دبیرستانی', start)
        source = source[:start] + '    # CONTENT_NEIGHBOR_METHOD\n' + source[end:]
        self.assertEqual(hashlib.sha256(source.encode()).hexdigest(),
                         '8ffa62e861e4782bf5524b827f1ad959f5f7c58bc3d4ea997792db2e474a922c')


if __name__ == '__main__':
    unittest.main()
