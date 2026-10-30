"""Production membership fingerprint baseline for the deploy snapshot."""

from __future__ import annotations

import json
from pathlib import Path

from reference_fingerprints import membership_fingerprint

ROOT = Path(__file__).resolve().parent
# Expected digests are recorded from deploy HEAD 02f40f16e044219141a1d354d9d1aa30df416d87.
# They are intentionally separate from the legacy mixed fingerprint constants.
EXPECTED_MEMBERSHIP_FINGERPRINTS = {
    194: "1b1be8f6e40bf498512827346593b7010cc04feea5357c470579a03a6f77d4e9",
    204: "cf9e0adcfb72b2b65ad60eadef633db50b88b07228ea1824d3b8ccd1bc1d0c49",
    215: "26457ea856fa9b975dd0cc23fd2cd690104257ff68a5566571a7772986e7af7c",
}


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
