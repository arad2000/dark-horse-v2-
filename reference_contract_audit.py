"""Strict offline contract audit for Dark Horse Hybrid migration.

Read-only. This script never connects to PostgreSQL and never changes runtime state.
It validates the exact reference-data invariants required before a staging seed.

BIOTM-* references are intentionally deferred until the dedicated BIOTM reference
correction phase. They are reported as deferred findings, while every other
unresolved motive reference remains a hard failure.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DEFERRED_MOTIVE_PREFIXES = ("BIOTM-",)

FILES = {
    "micro_motives": ROOT / "docs" / "data" / "micro_motives.json",
    "majors": ROOT / "majors_database_v2.json",
    "school_branches": ROOT / "school_branches_v2.json",
    "value_poles": ROOT / "value_poles_v2.json",
    "trait_map": ROOT / "docs" / "data" / "trait_map_v3.json",
    "questions": ROOT / "docs" / "data" / "questions_v2.json",
}


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def rows(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in keys:
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    raise ValueError("Unsupported JSON collection shape")


def strategy_question_rows(payload: Any) -> list[dict[str, Any]]:
    """Read the canonical nested questions_v2.json shape without reordering it."""
    if isinstance(payload, dict):
        layers = payload.get("layers")
        if isinstance(layers, dict):
            strategies = layers.get("strategies")
            if isinstance(strategies, dict):
                questions = strategies.get("questions")
                if isinstance(questions, list):
                    return [x for x in questions if isinstance(x, dict)]
    return rows(payload, ("questions", "data", "items"))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dup(values: list[Any]) -> list[Any]:
    seen: set[Any] = set()
    result: list[Any] = []
    for value in values:
        if value in seen and value not in result:
            result.append(value)
        seen.add(value)
    return result


def validate_trait_map(payload: Any) -> tuple[bool, dict[str, Any], list[str]]:
    errors: list[str] = []
    if not isinstance(payload, dict):
        return False, {"count": 0, "exact_S01_S25": False}, ["trait_map_not_object"]

    expected_questions = [f"S{i:02d}" for i in range(1, 26)]
    actual_questions = list(payload.keys())
    actual_question_strings = [str(k) for k in actual_questions]
    exact_questions = actual_question_strings == expected_questions
    if not exact_questions:
        errors.append("strategy_question_ids_not_exact_S01_S25_or_order_changed")

    option_counts: dict[str, int] = {}
    option_shape_ok = True
    empty_trait_options: list[str] = []
    for qcode in expected_questions:
        row = payload.get(qcode)
        if not isinstance(row, dict):
            option_shape_ok = False
            errors.append(f"{qcode}_not_object")
            continue
        numeric_keys: list[int] = []
        for raw_key, traits in row.items():
            key = str(raw_key)
            if not key.isdigit():
                option_shape_ok = False
                errors.append(f"{qcode}_non_numeric_option:{key}")
            else:
                numeric_keys.append(int(key))
            if isinstance(traits, list):
                if not traits or not all(isinstance(t, str) and t.strip() for t in traits):
                    empty_trait_options.append(f"{qcode}:{key}")
            else:
                option_shape_ok = False
                errors.append(f"{qcode}[{key}]_traits_not_list")
        option_counts[qcode] = len(numeric_keys)
        if sorted(numeric_keys) != [0, 1, 2, 3, 4]:
            option_shape_ok = False
            errors.append(f"{qcode}_options_not_exact_0_to_4")

    if empty_trait_options:
        option_shape_ok = False
        errors.append(f"empty_or_invalid_traits:{len(empty_trait_options)}")

    return (
        exact_questions and option_shape_ok,
        {
            "count": len(actual_question_strings),
            "exact_S01_S25": exact_questions,
            "order_preserved": exact_questions,
            "every_question_has_5_options": option_shape_ok and len(option_counts) == 25,
            "option_counts": option_counts,
            "invalid_trait_option_count": len(empty_trait_options),
        },
        errors,
    )


def validate_strategy_questions(payload: Any) -> tuple[bool, dict[str, Any], list[str]]:
    """Require the canonical S01..S25 question list and exact 1..25 order/options."""
    errors: list[str] = []
    questions = strategy_question_rows(payload)
    expected_ids = [f"S{i:02d}" for i in range(1, 26)]
    ids = [str(q.get("id", "")) for q in questions]
    numbers = [q.get("number") for q in questions]
    order_ok = ids == expected_ids and numbers == list(range(1, 26))
    unique_ids = len(ids) == len(set(ids))
    unique_numbers = len(numbers) == len(set(numbers))
    option_shape_ok = True
    text_values: list[str] = []

    if not order_ok:
        errors.append("strategy_questions_not_exactly_S01_to_S25_in_order")
    if not unique_ids:
        errors.append("duplicate_strategy_question_ids")
    if not unique_numbers:
        errors.append("duplicate_strategy_question_numbers")

    for q in questions:
        qid = str(q.get("id", "?"))
        opts = q.get("options")
        if not isinstance(opts, list):
            option_shape_ok = False
            errors.append(f"{qid}_options_not_list")
            continue
        indices = [o.get("index") for o in opts if isinstance(o, dict)]
        texts = [str(o.get("text", "")).strip() for o in opts if isinstance(o, dict)]
        text_values.extend(texts)
        if indices != [0, 1, 2, 3, 4]:
            option_shape_ok = False
            errors.append(f"{qid}_option_indices_not_exact_0_to_4_or_order_changed")
        if len(texts) != 5 or any(not t for t in texts):
            option_shape_ok = False
            errors.append(f"{qid}_must_have_5_nonempty_option_texts")

    duplicate_texts = dup(text_values)
    if duplicate_texts:
        errors.append(f"duplicate_strategy_option_texts:{duplicate_texts[:20]}")

    report = {
        "count": len(questions),
        "exact_S01_S25": order_ok,
        "order_preserved": order_ok,
        "unique_ids": unique_ids,
        "unique_numbers": unique_numbers,
        "every_question_has_5_options": option_shape_ok and len(questions) == 25,
        "duplicate_option_texts": len(duplicate_texts),
        "json_shape": "layers.strategies.questions" if isinstance(payload, dict) and isinstance(payload.get("layers"), dict) else "collection",
    }
    return order_ok and unique_ids and unique_numbers and option_shape_ok and len(questions) == 25 and not duplicate_texts, report, errors


def main() -> None:
    report: dict[str, Any] = {
        "status": "PASS",
        "runtime_cutover": "OFF",
        "errors": [],
        "deferred": [],
        "files": {},
    }

    payloads: dict[str, Any] = {}
    for name, path in FILES.items():
        if not path.exists():
            report["status"] = "FAIL"
            report["errors"].append(f"missing:{path}")
            continue
        try:
            payloads[name] = load(path)
            report["files"][name] = {"path": str(path.relative_to(ROOT)), "sha256": sha256(path)}
        except Exception as exc:
            report["status"] = "FAIL"
            report["errors"].append(f"invalid_json:{name}:{exc}")

    if report["status"] != "PASS":
        print(json.dumps(report, ensure_ascii=False, indent=2))
        raise SystemExit(1)

    motives = rows(payloads["micro_motives"], ("micro_motives", "motives", "data"))
    majors = rows(payloads["majors"], ("majors", "data"))
    branches = rows(payloads["school_branches"], ("school_branches", "branches", "data"))
    value_payload = payloads["value_poles"]
    if not isinstance(value_payload, dict):
        report["status"] = "FAIL"
        report["errors"].append("value_poles_not_object")
        values = []
    else:
        values = [{"code": str(k).strip().upper(), "description": str(v)} for k, v in value_payload.items()]

    motive_codes = [str(x.get("code") or "").strip() for x in motives]
    major_ids = [x.get("id") if x.get("id") is not None else x.get("major_id") for x in majors]
    branch_names = [str(x.get("name") or x.get("branch_name") or "").strip() for x in branches]
    value_codes = [str(x.get("code") or "").strip() for x in values]

    report["counts"] = {
        "micro_motives": len(motives),
        "majors": len(majors),
        "school_branches": len(branches),
        "value_poles": len(values),
    }

    expected_counts = {"micro_motives": 1099, "majors": 160, "value_poles": 30}
    for name, expected in expected_counts.items():
        actual = report["counts"][name]
        if actual != expected:
            report["status"] = "FAIL"
            report["errors"].append(f"count_mismatch:{name}:expected={expected}:actual={actual}")

    for label, values_ in (
        ("motive_codes", motive_codes),
        ("major_ids", [str(x) for x in major_ids]),
        ("branch_names", branch_names),
        ("value_codes", value_codes),
    ):
        duplicates = dup(values_)
        if duplicates:
            report["status"] = "FAIL"
            report["errors"].append(f"duplicate_{label}:{duplicates}")

    if sorted(int(x) for x in major_ids if x is not None) != list(range(1, 161)):
        report["status"] = "FAIL"
        report["errors"].append("major_ids_not_exact_1_to_160")

    trait_ok, trait_report, trait_errors = validate_trait_map(payloads["trait_map"])
    report["strategy_trait_map"] = trait_report
    report["errors"].extend(trait_errors)
    if not trait_ok:
        report["status"] = "FAIL"

    question_ok, question_report, question_errors = validate_strategy_questions(payloads["questions"])
    report["strategy_questions"] = question_report
    report["errors"].extend(question_errors)
    if not question_ok:
        report["status"] = "FAIL"

    missing_refs: list[dict[str, str]] = []
    deferred_refs: list[dict[str, str]] = []
    motive_set = set(motive_codes)
    for kind, items in (("major", majors), ("branch", branches)):
        for item in items:
            owner = str(item.get("id") or item.get("major_id") or item.get("branch_id") or item.get("name") or "?")
            for raw in item.get("micro_motive_codes") or []:
                code = str(raw).strip()
                if code in motive_set:
                    continue
                finding = {"kind": kind, "owner": owner, "code": code}
                if code.startswith(DEFERRED_MOTIVE_PREFIXES):
                    deferred_refs.append(finding)
                else:
                    missing_refs.append(finding)

    report["motive_reference_integrity"] = {
        "missing": len(missing_refs),
        "pass": not missing_refs,
        "deferred": len(deferred_refs),
        "deferred_prefixes": list(DEFERRED_MOTIVE_PREFIXES),
        "sample": (missing_refs + deferred_refs)[:20],
    }
    if deferred_refs:
        report["deferred"].append(
            f"unresolved_motive_references_deferred:{len(deferred_refs)}:prefixes={list(DEFERRED_MOTIVE_PREFIXES)}"
        )
    if missing_refs:
        report["status"] = "FAIL"
        report["errors"].append(f"unresolved_motive_references:{len(missing_refs)}")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
