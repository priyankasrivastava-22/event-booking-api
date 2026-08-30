"""add booking item quantity

Revision ID: 324802802f87
Revises: 1ca7934d9c63
Create Date: 2026-08-23 17:27:08.206052

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '324802802f87'
down_revision: Union[str, Sequence[str], None] = '1ca7934d9c63'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
