"""Production membership fingerprint baseline for the deploy snapshot."""

from __future__ import annotations

import json
from pathlib import Path

from reference_fingerprints import (
    EXPECTED_MEMBERSHIP_FINGERPRINTS,
    membership_fingerprint,
)

ROOT = Path(__file__).resolve().parent
# Expected digests are centralized with the projection schema in reference_fingerprints.py.


def load(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_membership_fingerprints_match_deploy_head():
    majors = load("majors_database_v2.json")
    branches = load("school_branches_v2.json")
    results = {}
    for end, expected in EXPECTED_MEMBERSHIP_FINGERPRINTS.items():
        actual = membership_fingerprint(
            majors, branches, max_major_id=end
        )
        results[end] = actual
        assert actual == expected, (
            f"membership fingerprint mismatch for 1..{end}: "
            f"expected={expected} actual={actual}"
        )
    print("REFERENCE_MEMBERSHIP_FINGERPRINTS=" + json.dumps(
        results, sort_keys=True
    ))


if __name__ == "__main__":
    test_membership_fingerprints_match_deploy_head()
    print("REFERENCE_MEMBERSHIP_INTEGRITY=PASS")
