"""Referral code ownership and commission accounting.

Revision ID: 0013_referral_ownership
Revises: 0012_referral_attribution

Additive only. Does not alter scoring, pricing, plans, entitlements, or the
credit ledger. Commission is a *reported accrual*, never a payment: there is no
wallet, no balance mutation, and no automatic settlement.

Design notes
  * A code is owned by a marketer row, not by a free-text label. The marketer
    may be an existing user of this site (``user_id`` set) or an outside person
    with no account (``phone``/name only). This is why ownership lives in its
    own table instead of overloading ``admin_audit_logs``.
  * ``orders.marketer_id_snapshot`` copies the owner onto the order at payment
    time. Changing a code's owner later therefore cannot move past commission.
  * ``referral_commissions`` is a one-to-one ledger keyed by order, so
    recomputation is idempotent and an order can never accrue twice.
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_referral_ownership"
down_revision = "0012_referral_attribution"
branch_labels = None
depends_on = None


def _inspector():
    return sa.inspect(op.get_bind())


def _tables():
    try:
        return set(_inspector().get_table_names())
    except Exception:
        return set()


def _columns(table: str) -> set[str]:
    try:
        return {c["name"] for c in _inspector().get_columns(table)}
    except Exception:
        return set()


def _add_if_missing(table: str, column: sa.Column) -> None:
    if column.name not in _columns(table):
        op.add_column(table, column)


def upgrade() -> None:
    existing = _tables()

    if "referral_marketers" not in existing:
        op.create_table(
            "referral_marketers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("public_id", sa.String(length=40), nullable=False),
            # Optional link to a real account; NULL means an outside marketer.
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("name", sa.String(length=200), nullable=False),
            sa.Column("phone", sa.String(length=32), nullable=True),
            # Commission rate in basis points: 1500 = 15.00%. Integer math only,
            # so no floating-point rounding ever reaches a money value.
            sa.Column("commission_bps", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint("public_id", name="uq_referral_marketer_public_id"),
            sa.CheckConstraint("commission_bps >= 0 AND commission_bps <= 10000", name="ck_commission_bps_range"),
        )
        op.create_index("idx_referral_marketer_user", "referral_marketers", ["user_id"])
        op.create_index("idx_referral_marketer_active", "referral_marketers", ["is_active"])

    if "referral_codes" not in existing:
        op.create_table(
            "referral_codes",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("code", sa.String(length=64), nullable=False),
            sa.Column("marketer_id", sa.Integer(), sa.ForeignKey("referral_marketers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("code", name="uq_referral_codes_code"),
        )
        op.create_index("idx_referral_codes_marketer", "referral_codes", ["marketer_id"])

    # Owner snapshot on the order, frozen at the same moment the code is frozen.
    _add_if_missing("orders", sa.Column("marketer_id_snapshot", sa.Integer(), nullable=True))
    _add_if_missing("orders", sa.Column("commission_bps_snapshot", sa.Integer(), nullable=True))

    if "referral_commissions" not in existing:
        op.create_table(
            "referral_commissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            # One commission per order: the unique constraint is the idempotency guard.
            sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
            sa.Column("marketer_id", sa.Integer(), sa.ForeignKey("referral_marketers.id", ondelete="RESTRICT"), nullable=False),
            sa.Column("referral_code", sa.String(length=64), nullable=False),
            sa.Column("gross_amount_minor", sa.BigInteger(), nullable=False),
            sa.Column("commission_bps", sa.Integer(), nullable=False),
            # Integer arithmetic only: gross * bps / 10000, truncated down.
            sa.Column("commission_amount_minor", sa.BigInteger(), nullable=False),
            sa.Column("currency", sa.String(length=8), nullable=False),
            sa.Column("status", sa.String(length=16), nullable=False, server_default="accrued"),
            sa.Column("settled_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("note", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("order_id", name="uq_referral_commission_order"),
        )
        op.create_index("idx_referral_commission_marketer", "referral_commissions", ["marketer_id"])
        op.create_index("idx_referral_commission_status", "referral_commissions", ["status"])


def downgrade() -> None:
    tables = _tables()
    if "referral_commissions" in tables:
        op.drop_index("idx_referral_commission_status", table_name="referral_commissions")
        op.drop_index("idx_referral_commission_marketer", table_name="referral_commissions")
        op.drop_table("referral_commissions")
    for column in ("commission_bps_snapshot", "marketer_id_snapshot"):
        if column in _columns("orders"):
            op.drop_column("orders", column)
    if "referral_codes" in tables:
        op.drop_index("idx_referral_codes_marketer", table_name="referral_codes")
        op.drop_table("referral_codes")
    if "referral_marketers" in tables:
        op.drop_index("idx_referral_marketer_active", table_name="referral_marketers")
        op.drop_index("idx_referral_marketer_user", table_name="referral_marketers")
        op.drop_table("referral_marketers")
