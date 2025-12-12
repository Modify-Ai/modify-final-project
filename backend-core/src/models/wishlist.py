from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
# 🚨 [FIX] 경로 수정: base_class -> session (사용자 프로젝트 구조에 맞춤)
from src.db.session import Base

class Wishlist(Base):
    __tablename__ = "wishlists"

    id = Column(Integer, primary_key=True, index=True)
    
    # 누가 찜했는지 (유저 삭제시 자동 삭제)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # 무엇을 찜했는지 (상품 삭제시 자동 삭제)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    
    # 언제 찜했는지
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 중복 찜 방지 제약조건
    __table_args__ = (
        UniqueConstraint('user_id', 'product_id', name='uq_wishlist_user_product'),
    )