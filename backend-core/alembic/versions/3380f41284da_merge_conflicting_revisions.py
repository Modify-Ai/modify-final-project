"""Merge conflicting revisions

Revision ID: 3380f41284da
Revises: 181bf85da2ce, a1b2c3d4e5f6
Create Date: 2025-12-14 20:26:47.591384

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3380f41284da'
down_revision: Union[str, None] = ('181bf85da2ce', 'a1b2c3d4e5f6')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
