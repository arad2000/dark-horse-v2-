"""Every user can own a referral code and share it.

Previously a marketer row was created only by an admin, so an ordinary user had
no way to hand out a code. This revision adds the two things needed for
self-service without weakening the admin path:

* ``referral_marketers.self_service`` separates "user minted their own code"
  from "admin onboarded this marketer", so the admin report can show which is
  which and the admin still controls commission rates for real partners.
* ``referral_codes.created_by_user_id`` records who minted the code.

No commission rate is granted implicitly: a self-service owner starts at 0 bps,
so minting a code can never create a payout obligation by itself.

Revision: 0015_self_service_codes
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_self_service_codes"
down_revision = "0014_signup_attribution"
branch_labels = None
depends_on = None


def _columns(table):
    try:
        return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    except Exception:
        return set()


def upgrade() -> None:
    if "self_service" not in _columns("referral_marketers"):
        op.add_column(
            "referral_marketers",
            sa.Column("self_service", sa.Boolean(), nullable=False, server_default=sa.false()),
        )
    if "created_by_user_id" not in _columns("referral_codes"):
        op.add_column("referral_codes", sa.Column("created_by_user_id", sa.BigInteger(), nullable=True))

    # One personal code per account: makes "generate my code" idempotent and
    # stops a user from minting a stable of codes to farm their own signups.
    op.execute(
        sa.text(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_referral_marketer_self_service_user
            ON referral_marketers (user_id)
            WHERE self_service = true
            """
        )
    )


def downgrade() -> None:
    op.execute(sa.text("DROP INDEX IF EXISTS uq_referral_marketer_self_service_user"))
    if "created_by_user_id" in _columns("referral_codes"):
        op.drop_column("referral_codes", "created_by_user_id")
    if "self_service" in _columns("referral_marketers"):
        op.drop_column("referral_marketers", "self_service")
