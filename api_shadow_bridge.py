"""Safe, non-invasive bridge for future FastAPI shadow persistence integration.

This module intentionally does not modify main_v2.py. It provides the exact
post-response hook contract that can later be called by an endpoint after the
JSON-backed engine has finished scoring. The response object is treated as
immutable from the bridge's perspective.

Safety invariants:
- scoring and ranking remain owned by the JSON-backed engine;
- PostgreSQL is used only for operational persistence;
- shadow persistence is opt-in and disabled by default;
- persistence failures are non-fatal unless strict=True;
- production cutover cannot be enabled through this bridge.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from api_persistence_adapter import OperationalPersistenceAdapter
from shadow_persistence import ShadowPersistenceReport, persist_shadow


def persist_api_shadow(
    request_payload: dict[str, Any],
    response_payload: dict[str, Any],
    adapter: OperationalPersistenceAdapter,
    *,
    request_meta: dict[str, Any] | None = None,
    strict: bool = False,
) -> tuple[dict[str, Any], ShadowPersistenceReport]:
    """Return an untouched copy of the API response plus a shadow report.

    The input response is never mutated. The returned payload is a deep copy so
    callers can assert response identity/content independently of persistence.
    """
    response_copy = deepcopy(response_payload)
    discovery = response_payload.get("discovery_result") or {}
    branch = response_payload.get("branch_discovery_result")

    report = persist_shadow(
        adapter,
        request_payload,
        discovery,
        branch_response=branch,
        request_meta=request_meta,
        strict=strict,
    )
    return response_copy, report
