"""add locked_count to ticket_types

Revision ID: 837d0ec026e5
Revises: 8e9e52159d58
Create Date: 2026-08-23

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "837d0ec026e5"
down_revision: Union[str, Sequence[str], None] = "8e9e52159d58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add locked_count to ticket_types, mirroring event_zones.locked_count.

    Needed so hold_passes()/release_passes() can track "currently held but
    not yet paid" passes without a race  -  without this column there was no
    safe way to prevent overselling a pooled pass type under concurrent load.
    """
    op.add_column(
        "ticket_types",
        sa.Column(
            "locked_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.create_check_constraint(
        "ck_ticket_locked_non_negative",
        "ticket_types",
        "locked_count >= 0",
    )


def downgrade() -> None:
    """Remove locked_count from ticket_types."""
    op.drop_constraint("ck_ticket_locked_non_negative", "ticket_types", type_="check")
    op.drop_column("ticket_types", "locked_count")