"""final_init

Revision ID: 00bfa93c2353
Revises: 
Create Date: 2025-12-17 10:34:21.445808

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from pgvector.sqlalchemy import Vector  # pgvector 타입 사용

# revision identifiers, used by Alembic.
revision: str = '00bfa93c2353'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. [필수] pgvector 확장 기능 활성화 (임베딩 저장을 위해 필요)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # ==========================================================
    # 2. Users 테이블 생성
    # ==========================================================
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('full_name', sa.String(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('is_superuser', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_marketing_agreed', sa.Boolean(), server_default='false', nullable=False),
        
        sa.Column('phone_number', sa.String(), nullable=True),
        sa.Column('address', sa.String(), nullable=True),
        sa.Column('zip_code', sa.String(), nullable=True),
        
        # [수정 1] DatatypeMismatch 해결: Date -> String으로 변경
        sa.Column('birthdate', sa.String(), nullable=True),
        
        sa.Column('gender', sa.String(), nullable=True),
        sa.Column('location', sa.String(), nullable=True),
        sa.Column('profile_image', sa.String(), nullable=True),
        sa.Column('provider', sa.String(), server_default='local', nullable=True),
        
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        
        # [수정 2] ResponseValidationError 해결: server_default 추가 (자동 시간 입력)
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # ==========================================================
    # 3. Products 테이블 생성
    # ==========================================================
    op.create_table(
        'products',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Integer(), nullable=False),
        sa.Column('stock_quantity', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('image_url', sa.String(length=500), nullable=True),
        sa.Column('gender', sa.String(length=20), nullable=True, server_default='Unisex'),
        
        # 벡터 컬럼들 (pgvector)
        sa.Column('embedding', Vector(768), nullable=True),
        sa.Column('embedding_clip', Vector(512), nullable=True),
        sa.Column('embedding_clip_upper', Vector(512), nullable=True),
        sa.Column('embedding_clip_lower', Vector(512), nullable=True),
        
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        # [수정 3] Products 테이블도 안전하게 default 추가
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        
        # 제약 조건
        sa.CheckConstraint('price >= 0', name='check_price_positive'),
        sa.CheckConstraint('stock_quantity >= 0', name='check_stock_positive'),
        sa.CheckConstraint("gender IN ('Male', 'Female', 'Unisex', NULL)", name='check_gender_valid')
    )
    op.create_index(op.f('ix_products_id'), 'products', ['id'], unique=False)
    op.create_index(op.f('ix_products_category'), 'products', ['category'], unique=False)
    op.create_index(op.f('ix_products_gender'), 'products', ['gender'], unique=False)

    # HNSW 벡터 인덱스
    op.create_index(
        'ix_product_embedding_hnsw', 'products', ['embedding'], unique=False,
        postgresql_using='hnsw', postgresql_with={'m': 32, 'ef_construction': 128},
        postgresql_ops={'embedding': 'vector_cosine_ops'}, postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.create_index(
        'ix_product_embedding_clip_hnsw', 'products', ['embedding_clip'], unique=False,
        postgresql_using='hnsw', postgresql_with={'m': 32, 'ef_construction': 128},
        postgresql_ops={'embedding_clip': 'vector_cosine_ops'}, postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.create_index(
        'ix_product_embedding_clip_upper_hnsw', 'products', ['embedding_clip_upper'], unique=False,
        postgresql_using='hnsw', postgresql_with={'m': 32, 'ef_construction': 128},
        postgresql_ops={'embedding_clip_upper': 'vector_cosine_ops'}, postgresql_where=sa.text("deleted_at IS NULL")
    )
    op.create_index(
        'ix_product_embedding_clip_lower_hnsw', 'products', ['embedding_clip_lower'], unique=False,
        postgresql_using='hnsw', postgresql_with={'m': 32, 'ef_construction': 128},
        postgresql_ops={'embedding_clip_lower': 'vector_cosine_ops'}, postgresql_where=sa.text("deleted_at IS NULL")
    )

    # ==========================================================
    # 4. Wishlists 테이블 생성
    # ==========================================================
    op.create_table(
        'wishlists',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'product_id', name='uq_wishlist_user_product')
    )
    op.create_index(op.f('ix_wishlists_id'), 'wishlists', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_wishlists_id'), table_name='wishlists')
    op.drop_table('wishlists')
    
    op.drop_index('ix_product_embedding_clip_lower_hnsw', table_name='products', postgresql_using='hnsw')
    op.drop_index('ix_product_embedding_clip_upper_hnsw', table_name='products', postgresql_using='hnsw')
    op.drop_index('ix_product_embedding_clip_hnsw', table_name='products', postgresql_using='hnsw')
    op.drop_index('ix_product_embedding_hnsw', table_name='products', postgresql_using='hnsw')
    op.drop_index(op.f('ix_products_gender'), table_name='products')
    op.drop_index(op.f('ix_products_category'), table_name='products')
    op.drop_index(op.f('ix_products_id'), table_name='products')
    op.drop_table('products')
    
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')