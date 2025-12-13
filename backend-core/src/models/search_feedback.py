from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, TIMESTAMP, Text, Index, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from src.db.session import Base


class SearchFeedback(Base):
    """AI 검색 결과에 대한 사용자 피드백"""
    __tablename__ = "search_feedbacks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    product_id: Mapped[int] = mapped_column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    feedback_type: Mapped[str] = mapped_column(String(20), nullable=False)
    search_query: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    search_context: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index('ix_feedback_user_product', 'user_id', 'product_id'),
        Index('ix_feedback_session_product', 'session_id', 'product_id'),
        Index('ix_feedback_product_type', 'product_id', 'feedback_type'),
    )
