"""Reference-data integrity checks.

This test validates references only; it does not alter scoring weights or ranking logic.
"""
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_json(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def test_micro_motive_references():
    motives = load_json("micro_motives.json")
    codes = {
        str(item.get("code", "")).strip().lower()
        for item in motives
        if isinstance(item, dict) and item.get("code")
    }
    majors = load_json("majors_database_v2.json")
    missing = []
    for major in majors:
        for code in major.get("micro_motive_codes", []) or []:
            if str(code).strip().lower() not in codes:
                missing.append((major.get("id"), major.get("name"), code))
    assert not missing, f"Missing micro-motive references: {missing}"


def test_biotechnology_references_are_canonical():
    majors = load_json("majors_database_v2.json")
    biotech = next(m for m in majors if m.get("id") == 34)
    assert biotech["micro_motive_codes"] == [f"BIOT-{i:03d}" for i in range(1, 8)]


if __name__ == "__main__":
    test_micro_motive_references()
    test_biotechnology_references_are_canonical()
    print("REFERENCE_DATA_INTEGRITY=PASS")
