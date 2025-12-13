from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    """피드백 생성 요청"""
    product_id: int = Field(..., description="상품 ID")
    feedback_type: Literal["like", "dislike"] = Field(..., description="피드백 타입")
    search_query: Optional[str] = Field(None, description="검색어")
    search_context: Optional[dict] = Field(None, description="검색 컨텍스트")


class FeedbackResponse(BaseModel):
    """피드백 응답"""
    success: bool
    message: str
    current_feedback_type: Optional[str] = None

    class Config:
        from_attributes = True


class FeedbackDetail(BaseModel):
    """피드백 상세 정보"""
    id: int
    product_id: int
    feedback_type: str
    search_query: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackStats(BaseModel):
    """피드백 통계"""
    like_count: int = 0
    dislike_count: int = 0
    like_ratio: float = 0.0


class FeedbackListItem(BaseModel):
    """관리자용 피드백 목록 아이템"""
    id: int
    user_id: Optional[int]
    session_id: Optional[str]
    product_id: int
    feedback_type: str
    search_query: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
