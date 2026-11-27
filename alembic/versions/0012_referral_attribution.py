"""Add referral-code attribution and immutable paid-order snapshots.

Revision ID: 0012_referral_attribution
Revises: 0011_otp_request_ip

Attribution-only schema. Does not alter payment amounts, product plans,
commission economics, wallet, payout, settlement, or scoring data.

Upgrade-safety rules for this revision (attribution must never block a release):
  * every DDL step is guarded on current inspector state, so the revision is
    safe to run against a database that already carries part of its schema;
  * the duplicate-code reconciliation does not delete or rewrite ledger rows.
    It re-keys only the *older* duplicates so the partial unique index can be
    created; attribution lineage of the surviving code is unchanged;
  * if duplicates are still present after reconciliation the revision raises a
    readable error rather than silently discarding data.
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_referral_attribution"
down_revision = "0011_otp_request_ip"
branch_labels = None
depends_on = None

INDEX_NAME = "uq_admin_audit_referral_code"
TABLE = "admin_audit_logs"
PARTIAL_PREDICATE = "target_type = 'referral_code' AND action = 'create_referral_code'"


def _inspector():
    return sa.inspect(op.get_bind())


def _has_index(inspector, table: str, index: str) -> bool:
    try:
        return any(i.get("name") == index for i in inspector.get_indexes(table))
    except Exception:
        return False


def _column_names(inspector, table: str) -> set[str]:
    try:
        return {c["name"] for c in inspector.get_columns(table)}
    except Exception:
        return set()


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _column_names(_inspector(), table):
        op.add_column(table, column)


def _reconcile_duplicate_codes() -> None:
    """Re-key older duplicate codes so the partial unique index can be built.

    A referral code is identified by ``target_id``. If the live ledger already
    holds the same code more than once, creating the unique index fails and the
    whole release stops. Rather than deleting ledger rows (which would destroy
    audit history), the older duplicates are given a distinct, clearly marked
    ``target_id`` while keeping their ``action``/``target_type``/metadata. The
    surviving row keeps the original code, so existing attribution is unchanged.

    The re-keyed values are suffixed with their own row id, which is unique,
    so this is idempotent: a second run finds no duplicates and does nothing.
    """
    op.execute(
        sa.text(
            f"""
            WITH ranked AS (
                SELECT id,
                       row_number() OVER (PARTITION BY target_id ORDER BY id) AS position
                FROM {TABLE}
                WHERE target_type = 'referral_code'
                  AND action = 'create_referral_code'
            )
            UPDATE {TABLE} AS audit
            SET target_id = audit.target_id || '-ARCHIVED-' || audit.id::text
            FROM ranked
            WHERE audit.id = ranked.id
              AND ranked.position > 1
            """
        )
    )

    remaining = op.get_bind().execute(
        sa.text(
            f"""
            SELECT count(*) FROM (
                SELECT target_id FROM {TABLE}
                WHERE target_type = 'referral_code'
                  AND action = 'create_referral_code'
                GROUP BY target_id HAVING count(*) > 1
            ) AS duplicates
            """
        )
    ).scalar_one()
    if remaining:
        raise RuntimeError(
            "duplicate referral_code ledger rows could not be reconciled: "
            f"{remaining} code(s) still appear more than once. Resolve them manually."
        )


def upgrade() -> None:
    inspector = _inspector()

    # Reuse the existing admin audit ledger as the code registry. The partial
    # unique index keeps codes unique without introducing a new Hybrid table.
    if not _has_index(inspector, TABLE, INDEX_NAME):
        _reconcile_duplicate_codes()
        op.create_index(
            INDEX_NAME,
            TABLE,
            ["target_id"],
            unique=True,
            postgresql_where=sa.text(PARTIAL_PREDICATE),
            sqlite_where=sa.text(PARTIAL_PREDICATE),
        )

    _add_column_if_missing("users", sa.Column("referral_code", sa.String(length=64), nullable=True))
    _add_column_if_missing("users", sa.Column("referral_locked_at", sa.DateTime(timezone=True), nullable=True))

    _add_column_if_missing("orders", sa.Column("referral_code_snapshot", sa.String(length=64), nullable=True))
    _add_column_if_missing("orders", sa.Column("referral_label_snapshot", sa.String(length=200), nullable=True))
    _add_column_if_missing("orders", sa.Column("referral_snapshot_at", sa.DateTime(timezone=True), nullable=True))

    # Existing paid accounts are already past the edit window. Preserve that
    # invariant during rollout even though historical orders get no attribution.
    op.execute(
        sa.text(
            """
            UPDATE users
            SET referral_locked_at = (
                SELECT MIN(o.paid_at)
                FROM orders AS o
                WHERE o.user_id = users.id
                  AND o.status = 'paid'
                  AND o.paid_at IS NOT NULL
            )
            WHERE referral_locked_at IS NULL
              AND EXISTS (
                  SELECT 1
                  FROM orders AS o
                  WHERE o.user_id = users.id
                    AND o.status = 'paid'
                    AND o.paid_at IS NOT NULL
              )
            """
        )
    )


def downgrade() -> None:
    for table, column in (
        ("orders", "referral_snapshot_at"),
        ("orders", "referral_label_snapshot"),
        ("orders", "referral_code_snapshot"),
        ("users", "referral_locked_at"),
        ("users", "referral_code"),
    ):
        if column in _column_names(_inspector(), table):
            op.drop_column(table, column)

    if _has_index(_inspector(), TABLE, INDEX_NAME):
        op.drop_index(INDEX_NAME, table_name=TABLE)
