from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from src.db.session import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, index=True)
    
    # [계정 상태]
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    
    # [✅ Perfect 버전 필수 정보 - DB와 일치시킴]
    phone_number = Column(String, nullable=True)
    address = Column(String, nullable=True)
    zip_code = Column(String, nullable=True)   # 👈 추가됨
    detail_address = Column(String, nullable=True)  # 👈 추가됨
    birthdate = Column(String, nullable=True)
    gender = Column(String, nullable=True)     # 👈 추가됨
    is_marketing_agreed = Column(Boolean(), default=False)
    is_phone_verified = Column(Boolean(), default=False)    # 👈 추가됨

    # [✅ 소셜 로그인/프로필 - 에러 원인 해결]
    profile_image = Column(String, nullable=True)
    provider = Column(String, default="local") # 👈 🚨 핵심! 이게 있어야 에러 해결됨

    # [타임스탬프]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    fitting_results = relationship("FittingResult", back_populates="user", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="user", cascade="all, delete-orphan")