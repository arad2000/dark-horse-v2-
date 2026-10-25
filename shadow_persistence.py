"""Shadow-only API persistence integration for Dark Horse V2.

The live response remains owned by the existing JSON-backed engine. This module
can persist an already-produced API request/response pair to the operational DB
for staging observation, but it cannot alter scoring, ranking, or the response.

Safety rules:
- production PostgreSQL cutover gate must remain OFF;
- shadow persistence is disabled by default;
- failures are non-fatal unless strict=True is explicitly requested in staging;
- the module never reads PostgreSQL reference tables for scoring.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from api_persistence_adapter import OperationalPersistenceAdapter
from migration_control import is_postgres_runtime_enabled


@dataclass(frozen=True)
class ShadowPersistenceReport:
    attempted: bool
    persisted: bool
    session_id: int | None = None
    error: str | None = None


def shadow_enabled() -> bool:
    """Return True only for an explicit, non-production staging opt-in."""
    raw = os.getenv("DARK_HORSE_SHADOW_PERSISTENCE", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def assert_shadow_safe() -> None:
    """Fail closed if the production cutover gate is active."""
    if is_postgres_runtime_enabled():
        raise RuntimeError("Shadow persistence is disabled when PostgreSQL runtime cutover is ON")


def persist_shadow(
    adapter: OperationalPersistenceAdapter,
    request_payload: dict[str, Any],
    discovery_response: dict[str, Any],
    *,
    branch_response: dict[str, Any] | None = None,
    request_meta: dict[str, Any] | None = None,
    strict: bool = False,
) -> ShadowPersistenceReport:
    """Persist operational telemetry after scoring has already completed.

    The function deliberately returns a report rather than the persisted objects,
    and it never modifies the API response supplied by the caller.
    """
    assert_shadow_safe()

    if not shadow_enabled():
        return ShadowPersistenceReport(attempted=False, persisted=False)

    try:
        session = adapter.create_session(request_payload, request_meta=request_meta)
        session_id = int(session.id)
        adapter.persist_discovery(session_id, discovery_response)

        if branch_response is not None:
            adapter.persist_branch_discovery(session_id, branch_response)

        adapter.complete(session_id)
        return ShadowPersistenceReport(attempted=True, persisted=True, session_id=session_id)
    except Exception as exc:
        if strict:
            raise
        return ShadowPersistenceReport(
            attempted=True,
            persisted=False,
            error=f"{type(exc).__name__}: {exc}",
        )
