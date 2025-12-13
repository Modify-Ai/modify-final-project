"""add_search_feedbacks_table

Revision ID: f1a2b3c4d5e6
Revises: a1b2c3d4e5f6
Create Date: 2025-12-11 17:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = 'f1a2b3c4d5e6'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create search_feedbacks table
    op.create_table(
        'search_feedbacks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('feedback_type', sa.String(length=20), nullable=False),
        sa.Column('search_query', sa.Text(), nullable=True),
        sa.Column('search_context', JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index('ix_search_feedbacks_id', 'search_feedbacks', ['id'], unique=False)
    op.create_index('ix_search_feedbacks_user_id', 'search_feedbacks', ['user_id'], unique=False)
    op.create_index('ix_search_feedbacks_session_id', 'search_feedbacks', ['session_id'], unique=False)
    op.create_index('ix_search_feedbacks_product_id', 'search_feedbacks', ['product_id'], unique=False)
    op.create_index('ix_feedback_user_product', 'search_feedbacks', ['user_id', 'product_id'], unique=False)
    op.create_index('ix_feedback_session_product', 'search_feedbacks', ['session_id', 'product_id'], unique=False)
    op.create_index('ix_feedback_product_type', 'search_feedbacks', ['product_id', 'feedback_type'], unique=False)


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_feedback_product_type', table_name='search_feedbacks')
    op.drop_index('ix_feedback_session_product', table_name='search_feedbacks')
    op.drop_index('ix_feedback_user_product', table_name='search_feedbacks')
    op.drop_index('ix_search_feedbacks_product_id', table_name='search_feedbacks')
    op.drop_index('ix_search_feedbacks_session_id', table_name='search_feedbacks')
    op.drop_index('ix_search_feedbacks_user_id', table_name='search_feedbacks')
    op.drop_index('ix_search_feedbacks_id', table_name='search_feedbacks')

    # Drop table
    op.drop_table('search_feedbacks')
