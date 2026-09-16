"""Hard safety gate for the Dark Horse Hybrid PostgreSQL rollout.

Production PostgreSQL use is deliberately locked OFF in this phase.
Changing this constant requires an explicit reviewed commit after all
migration, dual-run, and integrity audits have passed.
"""

POSTGRES_RUNTIME_CUTOVER_APPROVED = False


def is_postgres_runtime_enabled() -> bool:
    """Return the current production cutover state.

    This intentionally ignores environment variables so an accidental
    deployment configuration cannot silently switch the live engine.
    """
    return POSTGRES_RUNTIME_CUTOVER_APPROVED
