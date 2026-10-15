"""Reference-data integrity checks.

This test validates references only; it does not alter scoring weights or ranking logic.
"""
from __future__ import annotations

import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def load_json(name: str):
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


PHASE2_WAVE1_IDS = frozenset(range(161, 177))
BASELINE_MAJOR_1_194_FINGERPRINT = "5189181b82aab0e6"
BASELINE_MAJOR_1_204_FINGERPRINT = "749c599468ce116b"
BASELINE_MAJOR_1_215_FINGERPRINT = "4a75d6d48c2b07ce"
F1_OWNER_APPROVED_STAGING_IDS = frozenset({183, 184, 185, 186, 187, 189})
F1B_CANDIDATE_STAGING_IDS = frozenset({177, 178, 180, 181, 182})
F1B_CANDIDATE_WEIGHTS_VERSION = "dh013_f1b_review_candidate_v1"
F1_ART_WEIGHTS_VERSION = "hybrid_swRESHARP_art_lang_v1|art_value_v1|swFIX72_v2"
F1_DEFERRED_STUB_FIELDS = {
    "handcrafted": False,
    "motive_driven": False,
    "weights_version": "deferred_catalog_only_v1",
    "micro_motive_codes": [],
    "strategy_weights": [],
    "value_weights": {},
    "archetype": "deferred_catalog_only",
    "fulfillment_source": "این مدخل فعلاً فقط برای کاتالوگ و تطبیق ظرفیت سنجش است؛ داده‌های فردیت و وزن‌های امتیازدهی تدوین و اعتبارسنجی نشده‌اند.",
}


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


def test_major_catalog_ids_are_contiguous_1_to_230():
    majors = load_json("majors_database_v2.json")
    assert len(majors) == 230
    ids = sorted(int(item["id"]) for item in majors)
    assert ids == list(range(1, 231))


def test_wave_a_deferred_catalog_contract():
    majors = load_json("majors_database_v2.json")
    wave_a = [m for m in majors if int(m["id"]) in range(177, 190)]
    assert len(wave_a) == 13
    assert [int(m["id"]) for m in wave_a] == list(range(177, 190))
    f1_active = [m for m in wave_a if int(m["id"]) in F1_OWNER_APPROVED_STAGING_IDS]
    f1b_candidates = [m for m in wave_a if int(m["id"]) in F1B_CANDIDATE_STAGING_IDS]
    wave_a_deferred = [
        m for m in wave_a
        if int(m["id"]) not in (F1_OWNER_APPROVED_STAGING_IDS | F1B_CANDIDATE_STAGING_IDS)
    ]
    assert [int(m["id"]) for m in f1_active] == [183, 184, 185, 186, 187, 189]
    assert [int(m["id"]) for m in f1b_candidates] == [177, 178, 180, 181, 182]
    assert [int(m["id"]) for m in wave_a_deferred] == [179, 188]
    assert len(wave_a_deferred) == 2
    assert all(m.get("motive_driven") is False for m in wave_a_deferred)
    assert all(m.get("handcrafted") is False for m in wave_a_deferred)
    assert all(m.get("micro_motive_codes") == [] for m in wave_a_deferred)
    assert all(m.get("strategy_weights") == [] for m in wave_a_deferred)
    assert all(m.get("value_weights") == {} for m in wave_a_deferred)
    assert all(m.get("weights_version") == "deferred_catalog_only_v1" for m in wave_a_deferred)

    expected_poles = {f"Q{q}{side}" for q in range(1, 16) for side in ("A", "B")}
    for major in f1_active:
        strategy = major.get("strategy_weights")
        values = major.get("value_weights")
        assert major.get("motive_driven") is True
        assert major.get("handcrafted") is True
        assert len(major.get("micro_motive_codes", [])) == 7
        assert major.get("weights_version") == F1_ART_WEIGHTS_VERSION
        assert isinstance(strategy, list) and len(strategy) == 25
        assert all(isinstance(row, list) and len(row) == 5 for row in strategy)
        assert all(
            all(isinstance(w, (int, float)) and math.isfinite(w) and 0 <= w <= 1 for w in row)
            and abs(sum(row) - 1.0) <= 0.002
            for row in strategy
        )
        assert isinstance(values, dict) and set(values) == expected_poles
        assert all(isinstance(w, (int, float)) and math.isfinite(w) and 0 <= w <= 1 for w in values.values())
        assert major.get("archetype") and major.get("archetype") != "deferred_catalog_only"
        assert major.get("fulfillment_source") and major.get("fulfillment_source") != F1_DEFERRED_STUB_FIELDS["fulfillment_source"]

    expected_candidate_codes = {
        177: [f"DIRECT-{i:03d}" for i in range(1, 8)],
        178: [f"DIRECT-{i:03d}" for i in range(8, 15)],
        180: [f"MUSIC-{i:03d}" for i in range(1, 8)],
        181: [f"MUSIC-{i:03d}" for i in range(8, 15)],
        182: [f"MUSIC-{i:03d}" for i in range(15, 22)],
    }
    for major in f1b_candidates:
        major_id = int(major["id"])
        strategy = major.get("strategy_weights")
        values = major.get("value_weights")
        assert major.get("motive_driven") is False
        assert major.get("handcrafted") is False
        assert major.get("weights_version") == F1B_CANDIDATE_WEIGHTS_VERSION
        assert major.get("micro_motive_codes") == expected_candidate_codes[major_id]
        assert isinstance(strategy, list) and len(strategy) == 25
        assert all(isinstance(row, list) and len(row) == 5 for row in strategy)
        assert all(
            all(isinstance(w, (int, float)) and math.isfinite(w) and 0 <= w <= 1 for w in row)
            and abs(sum(row) - 1.0) <= 0.002
            for row in strategy
        )
        assert isinstance(values, dict) and set(values) == expected_poles
        assert all(isinstance(w, (int, float)) and math.isfinite(w) and 0 <= w <= 1 for w in values.values())
        assert major.get("archetype") and major.get("archetype") != "deferred_catalog_only"
        assert major.get("fulfillment_source") and major.get("fulfillment_source") != F1_DEFERRED_STUB_FIELDS["fulfillment_source"]

    id188 = next(m for m in wave_a if int(m["id"]) == 188)
    assert id188.get("motive_driven") is False
    assert id188.get("micro_motive_codes") == []
    assert id188.get("strategy_weights") == []
    assert id188.get("value_weights") == {}

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


def _restore_f1_approved_rows_for_historical_fingerprint(major_json_text):
    majors = json.loads(major_json_text)
    for major in majors:
        if int(major.get("id") or 0) in (F1_OWNER_APPROVED_STAGING_IDS | F1B_CANDIDATE_STAGING_IDS):
            major.update(json.loads(json.dumps(F1_DEFERRED_STUB_FIELDS, ensure_ascii=False)))
    return json.dumps(majors, ensure_ascii=False, indent=2) + "\n"


def _catalog_fingerprint(major_json_text, marker_id=195):
    normalized_text = _restore_f1_approved_rows_for_historical_fingerprint(major_json_text)
    marker = f'\n  {{\n    "id": {marker_id},'
    prefix, found, _ = normalized_text.partition(marker)
    assert found, f"Baseline marker for major {marker_id} is missing"
    prefix = prefix.rstrip()
    assert prefix.endswith(","), "Baseline catalog prefix is malformed"
    baseline_text = prefix[:-1] + "\n]\n"
    value = 0xCBF29CE484222325
    prime = 0x100000001B3
    mask = 0xFFFFFFFFFFFFFFFF
    for char in baseline_text:
        value ^= ord(char)
        value = (value * prime) & mask
    return f"{value:016x}"

def test_wave_c_preserves_entire_existing_catalog_1_to_194():
    majors = load_json("majors_database_v2.json")
    assert len([item for item in majors if 1 <= int(item["id"]) <= 194]) == 194
    catalog_text = (ROOT / "majors_database_v2.json").read_text(encoding="utf-8")
    assert _catalog_fingerprint(catalog_text) == BASELINE_MAJOR_1_194_FINGERPRINT


def test_wave_d_preserves_entire_existing_catalog_1_to_204():
    majors = load_json("majors_database_v2.json")
    assert len([item for item in majors if 1 <= int(item["id"]) <= 204]) == 204
    catalog_text = (ROOT / "majors_database_v2.json").read_text(encoding="utf-8")
    assert _catalog_fingerprint(catalog_text, marker_id=205) == BASELINE_MAJOR_1_204_FINGERPRINT


def test_wave_e_preserves_entire_existing_catalog_1_to_215():
    majors = load_json("majors_database_v2.json")
    assert len([item for item in majors if 1 <= int(item["id"]) <= 215]) == 215
    catalog_text = (ROOT / "majors_database_v2.json").read_text(encoding="utf-8")
    assert _catalog_fingerprint(catalog_text, marker_id=216) == BASELINE_MAJOR_1_215_FINGERPRINT


def test_wave_e_deferred_catalog_contract():
    majors = load_json("majors_database_v2.json")
    wave_e = [m for m in majors if int(m["id"]) in range(216, 231)]
    assert len(wave_e) == 15
    assert [int(m["id"]) for m in wave_e] == list(range(216, 231))
    assert [m["name"] for m in wave_e] == [
        "مهندسی تولید و ژنتیک گیاهی",
        "مهندسی طبیعت",
        "علوم و مهندسی جنگل",
        "مهندسی فضای سبز",
        "مهندسی مکانیزاسیون کشاورزی",
        "زیست‌شناسی دریا",
        "مهندسی گیاه‌پزشکی",
        "کاردانی معماری",
        "کاردانی امور بانکی",
        "کاردانی امور مالی و مالیاتی",
        "کاردانی برق — قدرت",
        "کاردانی بیمه",
        "کاردانی کارهای عمومی ساختمان",
        "کاردانی ارتباطات و فناوری اطلاعات",
        "کاردانی نقشه‌برداری — ژئودزی",
    ]
    assert all(m.get("motive_driven") is False for m in wave_e)
    assert all(m.get("handcrafted") is False for m in wave_e)
    assert all(m.get("micro_motive_codes") == [] for m in wave_e)
    assert all(m.get("strategy_weights") == [] for m in wave_e)
    assert all(m.get("value_weights") == {} for m in wave_e)
    assert all(m.get("weights_version") == "deferred_catalog_only_v1" for m in wave_e)


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

def test_wave_d_deferred_catalog_contract():
    majors = load_json("majors_database_v2.json")
    wave_d = [m for m in majors if int(m["id"]) in range(205, 216)]
    assert len(wave_d) == 11
    assert [int(m["id"]) for m in wave_d] == list(range(205, 216))
    assert [m["name"] for m in wave_d] == [
        "زبان روسی", "سیاستگذاری اجتماعی", "فقه شافعی", "علوم قضایی",
        "زبان و ادبیات آلمانی", "زبان و ادبیات اسپانیایی", "زبان و ادبیات ترکی استانبولی",
        "زبان و ادبیات ایتالیایی", "زبان و ادبیات ژاپنی", "زبان و ادبیات کردی",
        "کارشناسی ارشد پیوسته علوم قضایی",
    ]
    assert all(m.get("motive_driven") is False for m in wave_d)
    assert all(m.get("handcrafted") is False for m in wave_d)
    assert all(m.get("micro_motive_codes") == [] for m in wave_d)
    assert all(m.get("strategy_weights") == [] for m in wave_d)
    assert all(m.get("value_weights") == {} for m in wave_d)
    assert all(m.get("weights_version") == "deferred_catalog_only_v1" for m in wave_d)


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
    test_major_catalog_ids_are_contiguous_1_to_230()
    test_wave_a_deferred_catalog_contract()
    test_wave_b_deferred_catalog_contract()
    test_wave_c_preserves_entire_existing_catalog_1_to_194()
    test_wave_d_preserves_entire_existing_catalog_1_to_204()
    test_wave_e_preserves_entire_existing_catalog_1_to_215()
    test_wave_c_deferred_catalog_contract()
    test_wave_d_deferred_catalog_contract()
    test_wave_e_deferred_catalog_contract()
    test_major_names_are_unique_for_uq_major_name()
    test_biotechnology_references_are_canonical()
    print("REFERENCE_DATA_INTEGRITY=PASS")
