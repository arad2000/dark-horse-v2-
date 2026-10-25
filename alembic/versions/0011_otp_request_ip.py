"""Add request IP tracking for outbound OTP rate limiting."""
from alembic import op
import sqlalchemy as sa

revision = "0011_otp_request_ip"
down_revision = "0010_journey_credit_consumptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "phone_verifications",
        sa.Column("request_ip", sa.String(length=45), nullable=True),
    )
    op.create_index(
        "idx_phone_verification_ip_created",
        "phone_verifications",
        ["request_ip", "created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "idx_phone_verification_ip_created",
        table_name="phone_verifications",
    )
    op.drop_column("phone_verifications", "request_ip")
