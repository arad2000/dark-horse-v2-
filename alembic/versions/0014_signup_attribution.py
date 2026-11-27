"""Signup attribution for referral codes.

Why this table exists
---------------------
``orders.referral_code_snapshot`` answers "who bought with this code". It cannot
answer "how many people did this marketer bring", because most signups never
buy. This table records the attribution at the moment an account is created, so
the count is complete and independent of purchases.

Rules
  * ``user_id`` is unique: an account is attributed exactly once, so re-applying
    a different code can never inflate a marketer's head-count.
  * A code that is unknown or inactive at signup is simply not recorded. Signup
    is never blocked. The rejection reason is kept so an operator can explain a
    marketer's "missing" person.
  * Redeemed is self-reported by the marketer; confirmed means the person has a
    paid order carrying that marketer's snapshot.

Revision: 0014_signup_attribution
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_signup_attribution"
down_revision = "0013_referral_ownership"
branch_labels = None
depends_on = None


def _tables():
    try:
        return set(sa.inspect(op.get_bind()).get_table_names())
    except Exception:
        return set()


def upgrade() -> None:
    if "referral_signups" in _tables():
        return
    op.create_table(
        "referral_signups",
        sa.Column("id", sa.Integer(), primary_key=True),
        # One attribution per account, ever.
        sa.Column("user_id", sa.BigInteger(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        # Immutable copy of the code as it was at signup.
        sa.Column("code", sa.String(length=64), nullable=False),
        # Owner snapshot: survives the code later moving to another marketer.
        sa.Column("marketer_id", sa.Integer(), sa.ForeignKey("referral_marketers.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="register"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_referral_signups_marketer", "referral_signups", ["marketer_id"])
    op.create_index("idx_referral_signups_code", "referral_signups", ["code"])
    op.create_index("idx_referral_signups_created", "referral_signups", ["created_at"])

    # Why a signup carried no attribution (unknown/disabled code, typo, ...).
    # Kept outside the attribution table so a rejected attempt can never be
    # mistaken for a successful referral.
    with op.batch_alter_table("phone_verifications") as batch:
        batch.add_column(sa.Column("referral_code_input", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("referral_rejected_reason", sa.String(length=64), nullable=True))


def downgrade() -> None:
    if "referral_signups" in _tables():
        op.drop_index("idx_referral_signups_created", table_name="referral_signups")
        op.drop_index("idx_referral_signups_code", table_name="referral_signups")
        op.drop_index("idx_referral_signups_marketer", table_name="referral_signups")
        op.drop_table("referral_signups")
    with op.batch_alter_table("phone_verifications") as batch:
        for column in ("referral_rejected_reason", "referral_code_input"):
            try:
                batch.drop_column(column)
            except Exception:
                pass
