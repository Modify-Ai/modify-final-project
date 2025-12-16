"""Add missing columns to users

Revision ID: 0d7a3f4b9c1e
Revises: a1b2c3d4e5f6
Create Date: 2025-12-16 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d7a3f4b9c1e'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))
    op.add_column('users', sa.Column('address', sa.String(), nullable=True))
    op.add_column('users', sa.Column('zip_code', sa.String(), nullable=True))
    op.add_column('users', sa.Column('birthdate', sa.String(), nullable=True))
    op.add_column('users', sa.Column('gender', sa.String(), nullable=True))
    op.add_column('users', sa.Column('location', sa.String(), nullable=True))
    op.add_column('users', sa.Column('profile_image', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'profile_image')
    op.drop_column('users', 'location')
    op.drop_column('users', 'gender')
    op.drop_column('users', 'birthdate')
    op.drop_column('users', 'zip_code')
    op.drop_column('users', 'address')
    op.drop_column('users', 'phone_number')
