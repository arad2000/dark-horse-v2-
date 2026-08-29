"""Operational persistence contract for Dark Horse V2 Hybrid mode.

This module is intentionally independent from the scoring engine. It defines
validation helpers for persisted session/result payloads while the live source
of scoring/reference data remains JSON until explicit cutover approval.
"""
from __future__ import annotations

import math
from typing import Any


_SCORE_KEYS = (
    "m_score",
    "s_score",
    "v_score",
    "total_score",
    "fit_score",
    "average_score",
    "score",
)


def validate_scores(item: dict[str, Any], required: tuple[str, ...] = _SCORE_KEYS) -> None:
    """Reject non-numeric, non-finite, or out-of-range percentage scores.

    The API has historically used multiple aliases (e.g. ``score``,
    ``fit_score`` and ``average_score``), so all supported persisted score
    fields are guarded.
    """
    for key in required:
        if key not in item or item[key] is None:
            continue
        try:
            value = float(item[key])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{key} must be numeric; got {item[key]!r}") from exc
        if not math.isfinite(value) or not 0.0 <= value <= 100.0:
            raise ValueError(f"{key} must be a finite value between 0 and 100; got {value}")


def validate_ranked_items(items: list[dict[str, Any]], *, rank_key: str = "rank") -> None:
    """Require a stable, contiguous 1-based ranking when a rank is supplied."""
    ranks = [int(item[rank_key]) for item in items if rank_key in item and item[rank_key] is not None]
    if not ranks:
        return
    if sorted(ranks) != list(range(1, len(ranks) + 1)):
        raise ValueError(f"Ranks must be contiguous 1..N; got {ranks}")


def validate_session_payload(micro_motives: list[str], sjt_answers: dict[str, Any], conjoint_choices: dict[str, Any]) -> None:
    if not isinstance(micro_motives, list) or any(not isinstance(x, str) or not x.strip() for x in micro_motives):
        raise ValueError("micro_motives must be a list of non-empty strings")
    if not isinstance(sjt_answers, dict) or not isinstance(conjoint_choices, dict):
        raise ValueError("sjt_answers and conjoint_choices must be objects")


def validate_discovery_payload(recommendations: list[dict[str, Any]]) -> None:
    if not isinstance(recommendations, list):
        raise ValueError("recommendations must be a list")
    for item in recommendations:
        if "major_id" not in item:
            raise ValueError("each discovery recommendation requires major_id")
        validate_scores(item)
        nested_fit = item.get("individuality_fit")
        if nested_fit is not None:
            if not isinstance(nested_fit, dict):
                raise ValueError("individuality_fit must be an object when supplied")
            validate_scores(nested_fit)
    validate_ranked_items(recommendations)


def validate_branch_payload(branches: list[dict[str, Any]]) -> None:
    if not isinstance(branches, list):
        raise ValueError("branches must be a list")
    for item in branches:
        if not (item.get("branch_name") or item.get("branch_name_fa")):
            raise ValueError("each branch recommendation requires a branch name")
        validate_scores(item)
    validate_ranked_items(branches)
