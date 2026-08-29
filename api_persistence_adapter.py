"""Non-cutover API persistence adapter for Dark Horse V2.

This adapter is intentionally opt-in and operational-only. It persists session,
result, branch recommendation, feedback and audit data without changing the
JSON-backed scoring/reference source. Runtime cutover is guarded elsewhere.
"""
from __future__ import annotations

from typing import Any

from migration_control import is_postgres_runtime_enabled
from operational_store import OperationalStore


class OperationalPersistenceAdapter:
    """Thin API-facing wrapper around OperationalStore.

    This adapter never reads reference data from PostgreSQL and never changes
    scoring/ranking behavior. It is safe to instantiate during the staging phase.
    """

    def __init__(self, store: OperationalStore):
        self.store = store

    def create_session(self, payload: dict[str, Any], *, request_meta: dict[str, Any] | None = None):
        request_meta = request_meta or {}
        return self.store.create_session(
            payload.get("micro_motives") or [],
            payload.get("sjt_answers") or {},
            payload.get("conjoint_choices") or {},
            session_uuid=payload.get("session_uuid"),
            user_ip=request_meta.get("user_ip"),
            user_agent=request_meta.get("user_agent"),
            language_preference=payload.get("language_preference") or "fa",
        )

    def persist_discovery(self, session_id: int, discovery: dict[str, Any]):
        recommendations = discovery.get("discovered_majors") or discovery.get("recommendations") or []
        return self.store.store_discovery_results(session_id, recommendations)

    def persist_branch_discovery(self, session_id: int, result: dict[str, Any]):
        branches = result.get("recommended_branches") or result.get("branches") or []
        return self.store.store_branch_recommendations(session_id, branches)

    def complete(self, session_id: int) -> None:
        self.store.complete_session(session_id)

    def feedback(self, session_id: int, payload: dict[str, Any]):
        return self.store.save_feedback(
            session_id,
            satisfaction_score=payload.get("satisfaction_score"),
            accuracy_rating=payload.get("accuracy_rating"),
            comments=payload.get("comments"),
            recommended_major_id=payload.get("recommended_major_id"),
            would_recommend=payload.get("would_recommend"),
            contact_for_research=bool(payload.get("contact_for_research", False)),
            email=payload.get("email"),
        )

    def archive(self, session_id: int, changed_by: str = "api") -> None:
        self.store.archive_session(session_id, changed_by=changed_by)


def assert_safe_mode() -> None:
    """Fail closed if someone accidentally tries to use the adapter after cutover."""
    if is_postgres_runtime_enabled():
        raise RuntimeError(
            "OperationalPersistenceAdapter is staging-only; production cutover must use the approved runtime path."
        )
