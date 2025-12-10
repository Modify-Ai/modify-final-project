from sqlalchemy import Boolean, Column, Integer, String, DateTime, Date, Text
from sqlalchemy.sql import func
from src.db.session import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, index=True)
    
    # 계정 상태
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    
    # 로그인 방식 (local, google, kakao 등)
    provider = Column(String, nullable=False, default="local", server_default="local")
    
    # 프로필 정보
    phone_number = Column(String, nullable=True)
    address = Column(Text, nullable=True)
    profile_image = Column(String, nullable=True)
    birthdate = Column(Date, nullable=True)
    location = Column(String, nullable=True)
    is_marketing_agreed = Column(Boolean(), default=False)
    
    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)