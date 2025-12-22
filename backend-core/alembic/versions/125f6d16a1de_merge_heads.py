"""merge heads

Revision ID: 125f6d16a1de
Revises: 6bb99ad9237c, 181bf85da2ce
Create Date: 2025-12-21 20:42:17.615229

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '125f6d16a1de'
down_revision: Union[str, None] = ('6bb99ad9237c', '181bf85da2ce')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
