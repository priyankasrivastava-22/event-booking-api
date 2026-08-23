"""add quantity to booking items

Revision ID: 8e9e52159d58
Revises: 324802802f87
Create Date: 2026-08-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8e9e52159d58"
down_revision: Union[str, Sequence[str], None] = "324802802f87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add quantity to booking items."""
    # server_default handles existing rows automatically (Postgres 11+ constant
    # default optimization), so this is safe even though it's NOT NULL from the start.
    op.add_column(
        "booking_items",
        sa.Column(
            "quantity",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    """Remove quantity from booking items."""
    op.drop_column("booking_items", "quantity")