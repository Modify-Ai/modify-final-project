"""add_clip_embedding

Revision ID: a1b2c3d4e5f6
Revises: eb7ce1bf9db5
Create Date: 2024-05-20 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '6548ddd476c8'  # add_orders_tables 이후 실행
branch_labels = None
depends_on = None

def upgrade() -> None:
    # 1. CLIP Embedding 컬럼 추가 (512차원)
    op.add_column('products', sa.Column('embedding_clip', Vector(512), nullable=True))
    op.add_column('products', sa.Column('embedding_clip_upper', Vector(512), nullable=True))
    op.add_column('products', sa.Column('embedding_clip_lower', Vector(512), nullable=True))

    # 2. HNSW 인덱스 생성 (속도 최적화)
    # vector_cosine_ops 사용 (Cosine Distance 기반)
    # 전체 이미지 CLIP 인덱스
    op.create_index(
        'ix_product_embedding_clip_hnsw',
        'products',
        ['embedding_clip'],
        postgresql_using='hnsw',
        postgresql_with={'m': 32, 'ef_construction': 128},
        postgresql_ops={'embedding_clip': 'vector_cosine_ops'},
        postgresql_where=sa.text("deleted_at IS NULL")
    )

    # 상의 영역 CLIP 인덱스
    op.create_index(
        'ix_product_embedding_clip_upper_hnsw',
        'products',
        ['embedding_clip_upper'],
        postgresql_using='hnsw',
        postgresql_with={'m': 32, 'ef_construction': 128},
        postgresql_ops={'embedding_clip_upper': 'vector_cosine_ops'},
        postgresql_where=sa.text("deleted_at IS NULL")
    )

    # 하의 영역 CLIP 인덱스
    op.create_index(
        'ix_product_embedding_clip_lower_hnsw',
        'products',
        ['embedding_clip_lower'],
        postgresql_using='hnsw',
        postgresql_with={'m': 32, 'ef_construction': 128},
        postgresql_ops={'embedding_clip_lower': 'vector_cosine_ops'},
        postgresql_where=sa.text("deleted_at IS NULL")
    )

def downgrade() -> None:
    # 인덱스 삭제 (역순)
    op.drop_index('ix_product_embedding_clip_lower_hnsw', table_name='products')
    op.drop_index('ix_product_embedding_clip_upper_hnsw', table_name='products')
    op.drop_index('ix_product_embedding_clip_hnsw', table_name='products')

    # 컬럼 삭제
    op.drop_column('products', 'embedding_clip_lower')
    op.drop_column('products', 'embedding_clip_upper')
    op.drop_column('products', 'embedding_clip')