"""Reference-data integrity checks.

This test validates references only; it does not alter scoring weights or ranking logic.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_json(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


PHASE2_WAVE1_IDS = frozenset(range(161, 177))


def _is_phase2_stub_reference(major: dict, code: str) -> bool:
    try:
        major_id = int(major.get("id") or major.get("major_id"))
    except (TypeError, ValueError):
        return False
    return major_id in PHASE2_WAVE1_IDS and code.startswith(f"P2-{major_id}-")


def test_micro_motive_references():
    motives = load_json("micro_motives.json")
    codes = {
        str(item.get("code", "")).strip().lower()
        for item in motives
        if isinstance(item, dict) and item.get("code")
    }
    majors = load_json("majors_database_v2.json")
    missing = []
    deferred = []
    for major in majors:
        for raw_code in major.get("micro_motive_codes", []) or []:
            code = str(raw_code).strip()
            if code.lower() in codes:
                continue
            if _is_phase2_stub_reference(major, code):
                deferred.append((major.get("id"), major.get("name"), code))
                continue
            missing.append((major.get("id"), major.get("name"), code))
    assert len(deferred) == 0, f"Phase2 references must be fully resolved: {deferred}"
    assert not missing, f"Missing micro-motive references: {missing}"


def test_phase2_wave1_catalog_contract():
    majors = load_json("majors_database_v2.json")
    assert len(majors) == 176
    ids = sorted(int(item["id"]) for item in majors)
    assert ids == list(range(1, 177))


def test_phase2_wave1_behavioral_contract():
    majors = load_json("majors_database_v2.json")
    phase2 = [m for m in majors if int(m["id"]) in PHASE2_WAVE1_IDS]
    assert len(phase2) == 16
    assert all(m.get("motive_driven") is True for m in phase2)
    assert all(m.get("handcrafted") is True for m in phase2)
    assert all(len(m.get("micro_motive_codes", [])) == 7 for m in phase2)
    assert all(m.get("weights_version", "").endswith("phase2_behavioral_cal_v1") for m in phase2)

    majors = load_json("majors_database_v2.json")
    biotech = next(m for m in majors if m.get("id") == 34)
    assert biotech["micro_motive_codes"] == [f"BIOT-{i:03d}" for i in range(1, 8)]


if __name__ == "__main__":
    test_micro_motive_references()
    test_phase2_wave1_catalog_contract()
    test_biotechnology_references_are_canonical()
    print("REFERENCE_DATA_INTEGRITY=PASS")
