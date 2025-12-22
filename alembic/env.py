from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
import os
import sys

# -----------------------------------------------------------------
# [1] 경로 설정: backend-core 폴더 인식
# -----------------------------------------------------------------
current_dir = os.getcwd()
sys.path.insert(0, os.path.join(current_dir, 'backend-core'))

# -----------------------------------------------------------------
# [2] 모델 강제 등록 (이게 핵심입니다!)
# -----------------------------------------------------------------
try:
    # 1. Base 가져오기
    from src.models.base import Base
    
    # 2. 모든 모델을 여기서 import 해야 Metadata에 등록됩니다.
    # (파일 구조상 존재하는 모델들을 다 불러옵니다)
    from src.models.user import User
    from src.models.product import Product
    from src.models.wishlist import Wishlist
    # 필요한 경우 여기에 다른 모델도 추가하세요 (예: Order 등)

except ImportError as e:
    print("❌ 모델 import 실패! 경로를 확인하세요.")
    raise e
# -----------------------------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 등록된 모델들의 정보를 담은 메타데이터 연결
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()