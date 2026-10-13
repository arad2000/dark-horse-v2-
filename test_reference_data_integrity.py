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
BASELINE_MAJOR_1_194_FINGERPRINT = "17c9b97787919b0a"


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
    assert len(majors) == 204
    ids = sorted(int(item["id"]) for item in majors)
    assert ids == list(range(1, 205))


def test_wave_a_deferred_catalog_contract():
    majors = load_json("majors_database_v2.json")
    wave_a = [m for m in majors if int(m["id"]) in range(177, 190)]
    assert len(wave_a) == 13
    assert [int(m["id"]) for m in wave_a] == list(range(177, 190))
    assert all(m.get("motive_driven") is False for m in wave_a)
    assert all(m.get("micro_motive_codes") == [] for m in wave_a)
    assert all(m.get("strategy_weights") == [] for m in wave_a)
    assert all(m.get("value_weights") == {} for m in wave_a)
    assert all(m.get("weights_version") == "deferred_catalog_only_v1" for m in wave_a)


def test_phase2_wave1_behavioral_contract():
    majors = load_json("majors_database_v2.json")
    phase2 = [m for m in majors if int(m["id"]) in PHASE2_WAVE1_IDS]
    assert len(phase2) == 16
    assert all(m.get("motive_driven") is True for m in phase2)
    assert all(m.get("handcrafted") is True for m in phase2)
    assert all(len(m.get("micro_motive_codes", [])) == 7 for m in phase2)
    assert all(m.get("weights_version", "").endswith("phase2_behavioral_cal_v1") for m in phase2)




def test_wave_b_deferred_catalog_contract():
    majors = load_json("majors_database_v2.json")
    wave_b = [m for m in majors if int(m["id"]) in range(190, 195)]
    assert len(wave_b) == 5
    assert [int(m["id"]) for m in wave_b] == list(range(190, 195))
    assert [m["name"] for m in wave_b] == [
        "ساخت پروتزهای دندانی",
        "بیولوژی و کنترل ناقلین بیماری‌ها",
        "بهداشت مواد غذایی",
        "بهداشت و بازرسی گوشت",
        "دکتری پیوسته بیوتکنولوژی",
    ]
    assert all(m.get("motive_driven") is False for m in wave_b)
    assert all(m.get("micro_motive_codes") == [] for m in wave_b)
    assert all(m.get("strategy_weights") == [] for m in wave_b)
    assert all(m.get("value_weights") == {} for m in wave_b)
    assert all(m.get("weights_version") == "deferred_catalog_only_v1" for m in wave_b)




def _canonical_value(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return f"#{int(float(value) * 1_000_000 + 0.5)}"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(_canonical_value(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(
            f"{json.dumps(str(key), ensure_ascii=False)}:{_canonical_value(value[key])}"
            for key in sorted(value)
        ) + "}"
    return str(value)


def _catalog_fingerprint(majors, max_id=194):
    rows = sorted(
        (
            item for item in majors
            if 1 <= int(item.get("id") or item.get("major_id") or 0) <= max_id
        ),
        key=lambda item: int(item.get("id") or item.get("major_id") or 0),
    )
    payload = "\\n".join(_canonical_value(item) for item in rows)
    value = 0xCBF29CE484222325
    prime = 0x100000001B3
    mask = 0xFFFFFFFFFFFFFFFF
    for char in payload:
        value ^= ord(char)
        value = (value * prime) & mask
    return f"{value:016x}"


def test_wave_c_preserves_entire_existing_catalog_1_to_194():
    majors = load_json("majors_database_v2.json")
    assert len([item for item in majors if 1 <= int(item["id"]) <= 194]) == 194
    assert _catalog_fingerprint(majors, max_id=194) == BASELINE_MAJOR_1_194_FINGERPRINT


def test_wave_c_deferred_catalog_contract():
    majors = load_json("majors_database_v2.json")
    wave_c = [m for m in majors if int(m["id"]) in range(195, 205)]
    assert len(wave_c) == 10
    assert [int(m["id"]) for m in wave_c] == list(range(195, 205))
    assert [m["name"] for m in wave_c] == [
        "مهندسی حرفه‌ای کامپیوتر",
        "علم اطلاعات و دانش‌شناسی",
        "مهندسی حرفه‌ای معماری",
        "مهندسی ساخت و تولید",
        "مهندسی هوانوردی و مراقبت پرواز",
        "فناوری اطلاعات و ارتباطات",
        "خلبانی بالگرد",
        "خلبانی پهپاد",
        "هوانوردی خلبانی",
        "مهندسی نگهداری و تعمیر بالگرد",
    ]
    assert all(m.get("motive_driven") is False for m in wave_c)
    assert all(m.get("micro_motive_codes") == [] for m in wave_c)
    assert all(m.get("strategy_weights") == [] for m in wave_c)
    assert all(m.get("value_weights") == {} for m in wave_c)
    assert all(m.get("weights_version") == "deferred_catalog_only_v1" for m in wave_c)

def test_major_names_are_unique_for_uq_major_name():
    majors = load_json("majors_database_v2.json")
    names = [str(item.get("name") or "").strip() for item in majors]
    assert all(names), "Every catalog major must have a name"
    assert len(names) == len(set(names)), "Duplicate major names conflict with uq_major_name"

def test_biotechnology_references_are_canonical():
    majors = load_json("majors_database_v2.json")
    biotech = next(m for m in majors if m.get("id") == 34)
    assert biotech["micro_motive_codes"] == [f"BIOT-{i:03d}" for i in range(1, 8)]

if __name__ == "__main__":
    test_micro_motive_references()
    test_phase2_wave1_catalog_contract()
    test_wave_a_deferred_catalog_contract()
    test_wave_b_deferred_catalog_contract()
    test_wave_c_preserves_entire_existing_catalog_1_to_194()
    test_wave_c_deferred_catalog_contract()
    test_major_names_are_unique_for_uq_major_name()
    test_biotechnology_references_are_canonical()
    print("REFERENCE_DATA_INTEGRITY=PASS")
