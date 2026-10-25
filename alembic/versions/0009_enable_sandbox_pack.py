"""Enable the 3-test plan for the controlled payment sandbox.

The production free-only guard still prevents live ZarinPal unless its explicit
production approval is configured. This migration only makes the canonical
pack available to the mock/sandbox provider so the sandbox payment page remains
usable before merchant activation.
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_enable_sandbox_pack"
down_revision = "0008_billing_launch_plans"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE premium_plans SET is_active = TRUE WHERE code = 'pack_3_tests'"
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            "UPDATE premium_plans SET is_active = FALSE WHERE code = 'pack_3_tests'"
        )
    )
