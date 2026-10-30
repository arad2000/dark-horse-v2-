"""Deterministic scientific and membership reference fingerprints.

This module is deliberately independent of CI policy and production baselines.
It only builds explicit projections and hashes them; callers own expected values.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from collections.abc import Mapping, Sequence
from typing import Any

STAGING_CANDIDATE_IDS = frozenset({
    177, 178, 180, 181, 182,
    183, 184, 185, 186, 187, 189,
    199, 201, 202, 203, 204,
    205, 209, 210, 211, 212, 213, 214,
    208, 219, 220,
})
DEFERRED_STAGING_VERSION = "deferred_catalog_only_v1"


def _assert_finite_tree(value: Any, path: str = "$") -> None:
    """Reject NaN, infinities and parsed exponent overflow before projection."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return
    if isinstance(value, (int, float)):
        if not math.isfinite(float(value)):
            raise ValueError(f"Non-finite reference number at {path}")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _assert_finite_tree(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            _assert_finite_tree(item, f"{path}.{key}")
        return
    raise ValueError(f"Unsupported reference value at {path}: {type(value).__name__}")


def _canonical(value: Any) -> str:
    """Canonical, type-aware representation shared by all fingerprint projections.

    Numeric values are encoded as their exact IEEE-754 binary64 bytes. This avoids
    platform-specific JSON float formatting while preserving every finite value.
    """
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Non-finite reference number cannot be fingerprinted")
        return "#f64:" + struct.pack(">d", number).hex()
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, list):
        return "[" + ",".join(_canonical(item) for item in value) + "]"
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("Fingerprint object keys must be strings")
        return "{" + ",".join(
            json.dumps(key, ensure_ascii=False, separators=(",", ":"))
            + ":" + _canonical(value[key])
            for key in sorted(value)
        ) + "}"
    raise ValueError(f"Unsupported fingerprint value: {type(value).__name__}")


def _sha256_projection(projection: Mapping[str, Any]) -> str:
    _assert_finite_tree(projection)
    return hashlib.sha256(_canonical(projection).encode("utf-8")).hexdigest()


def _require_records(payload: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise ValueError(f"{label} must be a JSON array of objects")
    return payload


def _major_rows(majors: Any, max_major_id: int) -> list[dict[str, Any]]:
    if isinstance(max_major_id, bool) or not isinstance(max_major_id, int) or max_major_id < 1:
        raise ValueError("max_major_id must be a positive integer")
    rows = _require_records(majors, "majors_database_v2")
    selected: list[dict[str, Any]] = []
    seen: set[int] = set()
    for row in rows:
        raw_id = row.get("id", row.get("major_id"))
        if isinstance(raw_id, bool):
            raise ValueError(f"Invalid major id: {raw_id!r}")
        try:
            major_id = int(raw_id)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid major id: {raw_id!r}") from exc
        if major_id in seen:
            raise ValueError(f"Duplicate major id: {major_id}")
        seen.add(major_id)
        if 1 <= major_id <= max_major_id:
            selected.append(row)
    selected.sort(key=lambda row: int(row.get("id", row.get("major_id"))))
    return selected


def _code_set(raw_codes: Any, path: str) -> list[str]:
    if raw_codes is None:
        return []
    if isinstance(raw_codes, dict):
        source = raw_codes.keys()
    elif isinstance(raw_codes, list):
        source = raw_codes
    else:
        raise ValueError(f"{path} must be an array or object of motive codes")
    normalized = {
        str(code).strip().lower()
        for code in source
        if code is not None and str(code).strip()
    }
    return sorted(normalized)


def _is_explicit_inactive_staging(row: Mapping[str, Any], major_id: int) -> bool:
    return (
        major_id in STAGING_CANDIDATE_IDS
        and row.get("motive_driven") is False
        and row.get("weights_version") == DEFERRED_STAGING_VERSION
    )


def _scoring_major_row(row: Mapping[str, Any]) -> dict[str, Any]:
    raw_id = row.get("id", row.get("major_id"))
    major_id = int(raw_id)
    active = row.get("motive_driven")
    if not isinstance(active, bool):
        raise ValueError(f"Major {major_id} must declare motive_driven as a boolean")

    codes = _code_set(row.get("micro_motive_codes"), f"major[{major_id}].micro_motive_codes")
    strategy = row.get("strategy_weights")
    values = row.get("value_weights")
    version = row.get("weights_version")

    if _is_explicit_inactive_staging(row, major_id):
        # Only a known staging candidate that is explicitly inactive and still
        # carries the canonical deferred version can be normalized. Do not mask
        # non-empty profile data: that is a contract violation and must fail.
        if codes or strategy not in (None, []) or values not in (None, {}):
            raise ValueError(
                f"Inactive staging major {major_id} contains scoring profile data"
            )
        codes = []
        strategy = []
        values = {}

    return {
        "id": major_id,
        "motive_driven": active,
        "weights_version": version,
        "micro_motive_codes": codes,
        "strategy_weights": strategy,
        "value_weights": values,
    }


def _strategy_questions(questions_payload: Any) -> list[dict[str, Any]]:
    if not isinstance(questions_payload, dict):
        raise ValueError("questions_v2 must be an object")
    layers = questions_payload.get("layers")
    strategies = layers.get("strategies") if isinstance(layers, dict) else None
    questions = strategies.get("questions") if isinstance(strategies, dict) else None
    if not isinstance(questions, list):
        raise ValueError("questions_v2.layers.strategies.questions must be an array")

    result: list[dict[str, Any]] = []
    for position, question in enumerate(questions):
        if not isinstance(question, dict):
            raise ValueError(f"Strategy question {position} must be an object")
        options = question.get("options")
        if not isinstance(options, list):
            raise ValueError(f"Strategy question {position} options must be an array")
        normalized_options = []
        for option_index, option in enumerate(options):
            if not isinstance(option, dict):
                raise ValueError(
                    f"Strategy question {position} option {option_index} must be an object"
                )
            normalized_options.append({
                "index": option.get("index"),
                "text": option.get("text"),
            })
        result.append({
            "id": question.get("id"),
            "number": question.get("number"),
            "question": question.get("question"),
            "options": normalized_options,
        })
    return result


def build_scoring_projection(
    majors: Any,
    school_branches: Any,
    micro_motives: Any,
    questions: Any,
    *,
    max_major_id: int,
) -> dict[str, Any]:
    """Build the versioned projection of data consumed by numeric/scoring logic."""
    for label, payload in (
        ("majors_database_v2", majors),
        ("school_branches_v2", school_branches),
        ("micro_motives", micro_motives),
        ("questions_v2", questions),
    ):
        _assert_finite_tree(payload, label)

    major_rows = _major_rows(majors, max_major_id)
    branch_rows = _require_records(school_branches, "school_branches_v2")
    motive_rows = _require_records(micro_motives, "micro_motives")

    branch_projection = []
    seen_branch_names: set[str] = set()
    for row in branch_rows:
        name = row.get("name") or row.get("branch_name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every school branch must have a non-empty name")
        if name in seen_branch_names:
            raise ValueError(f"Duplicate school branch name: {name}")
        seen_branch_names.add(name)
        branch_projection.append({
            "id": row.get("id", row.get("branch_id")),
            "name": name,
            "micro_motive_codes": _code_set(
                row.get("micro_motive_codes"), f"school_branch[{name}].micro_motive_codes"
            ),
            "m_score_denom_limit": row.get("m_score_denom_limit"),
            "strategy_weights": row.get("strategy_weights"),
            "value_weights": row.get("value_weights"),
            "weights_version": row.get("weights_version"),
        })
    branch_projection.sort(key=lambda row: str(row["id"] or row["name"]))

    motive_codes = set()
    for index, row in enumerate(motive_rows):
        code = row.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError(f"micro_motives[{index}].code must be a non-empty string")
        motive_codes.add(code.strip().lower())

    return {
        "schema": "dark-horse-scientific-fingerprint-v1",
        "range_end": max_major_id,
        "majors": [_scoring_major_row(row) for row in major_rows],
        "school_branches": branch_projection,
        "micro_motive_codes": sorted(motive_codes),
        "strategy_questions": _strategy_questions(questions),
    }


def build_membership_projection(
    majors: Any,
    school_branches: Any,
    *,
    max_major_id: int,
) -> dict[str, Any]:
    """Build the independent membership/catalog/educational-guidance projection."""
    _assert_finite_tree(majors, "majors_database_v2")
    _assert_finite_tree(school_branches, "school_branches_v2")
    major_rows = _major_rows(majors, max_major_id)
    branch_rows = _require_records(school_branches, "school_branches_v2")

    major_projection = []
    for row in major_rows:
        major_projection.append({
            "id": int(row.get("id", row.get("major_id"))),
            "name": row.get("name") or row.get("major_name_fa") or row.get("major_name"),
            "high_school_branch": row.get("high_school_branch"),
            "group": row.get("group"),
            "cluster": row.get("cluster"),
            "subgroup": row.get("subgroup"),
            "exam_group": row.get("exam_group"),
        })

    branch_projection = []
    seen_branch_ids: set[str] = set()
    for row in branch_rows:
        branch_id = row.get("id", row.get("branch_id"))
        name = row.get("name") or row.get("branch_name")
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Every school branch must have a non-empty name")
        stable_id = str(branch_id or name)
        if stable_id in seen_branch_ids:
            raise ValueError(f"Duplicate school branch id: {stable_id}")
        seen_branch_ids.add(stable_id)
        branch_projection.append({
            "id": branch_id,
            "name": name,
            "group": row.get("group"),
        })
    branch_projection.sort(key=lambda row: str(row["id"] or row["name"]))

    return {
        "schema": "dark-horse-membership-fingerprint-v1",
        "range_end": max_major_id,
        "majors": major_projection,
        "school_branches": branch_projection,
    }


def scientific_fingerprint(
    majors: Any,
    school_branches: Any,
    micro_motives: Any,
    questions: Any,
    *,
    max_major_id: int,
) -> str:
    return _sha256_projection(build_scoring_projection(
        majors, school_branches, micro_motives, questions,
        max_major_id=max_major_id,
    ))


def membership_fingerprint(
    majors: Any,
    school_branches: Any,
    *,
    max_major_id: int,
) -> str:
    return _sha256_projection(build_membership_projection(
        majors, school_branches, max_major_id=max_major_id,
    ))
