"""Deterministic major_id -> major name mapping for the record admission path.

This module is reference-data only. It does not alter individual-fit scoring,
ranking, weights, Hybrid behavior, or PostgreSQL cutover.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
MAJORS_PATH = ROOT / "majors_database_v2.json"


class MajorMapDataError(RuntimeError):
    """Reference major mapping is missing or invalid."""


@lru_cache(maxsize=1)
def load_major_id_name_map() -> dict[str, str]:
    payload = json.loads(MAJORS_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise MajorMapDataError("majors_database_v2.json must contain a list")

    mapping: dict[str, str] = {}
    for item in payload:
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        name = str(item.get("name") or "").strip()
        if raw_id is None or not name:
            continue
        key = str(raw_id)
        if key in mapping:
            raise MajorMapDataError(f"duplicate major id: {key}")
        mapping[key] = name

    if not mapping:
        raise MajorMapDataError("majors_database_v2.json contains no major mappings")
    return mapping


def major_name_for_id(major_id: Any) -> str | None:
    """Return the canonical major name, or None when the id is unresolved."""
    if major_id is None:
        return None
    try:
        key = str(int(major_id))
    except (TypeError, ValueError):
        key = str(major_id).strip()
    return load_major_id_name_map().get(key)
