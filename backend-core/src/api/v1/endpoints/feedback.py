from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Header, status, Request
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from src.api.deps import get_db, get_current_superuser
from src.core.security import settings
from src.models.user import User
from src.models.search_feedback import SearchFeedback
from src.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackStats,
    FeedbackDetail,
    FeedbackListItem
)

router = APIRouter()


async def get_user_or_session(
    request: Request,
    db: AsyncSession,
    x_session_id: Optional[str] = Header(None)
) -> tuple[Optional[int], Optional[str]]:
    """
    사용자 식별: Authorization 헤더에서 user_id 추출, 없으면 session_id 사용
    """
    # Authorization 헤더에서 토큰 추출 시도
    auth_header = request.headers.get("Authorization")

    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.replace("Bearer ", "")
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                return int(user_id), None
        except JWTError:
            pass

    # 토큰이 없거나 유효하지 않으면 session_id 사용
    return None, x_session_id


@router.post("/", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_session_id: Optional[str] = Header(None)
):
    """
    피드백 제출 (토글 기능)
    - 피드백 없음 → 생성
    - 같은 타입 재클릭 → 삭제
    - 다른 타입 클릭 → 업데이트
    """
    user_id, session_id = await get_user_or_session(request, db, x_session_id)

    if not user_id and not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User identification required (login or session)"
        )

    try:
        # 기존 피드백 조회
        if user_id:
            stmt = select(SearchFeedback).where(
                SearchFeedback.user_id == user_id,
                SearchFeedback.product_id == feedback.product_id
            )
        else:
            stmt = select(SearchFeedback).where(
                SearchFeedback.session_id == session_id,
                SearchFeedback.product_id == feedback.product_id
            )

        result = await db.execute(stmt)
        existing_feedback = result.scalar_one_or_none()

        # 토글 로직
        if existing_feedback:
            if existing_feedback.feedback_type == feedback.feedback_type:
                # 같은 타입 → 삭제
                await db.delete(existing_feedback)
                await db.commit()
                return FeedbackResponse(
                    success=True,
                    message="피드백이 취소되었습니다.",
                    current_feedback_type=None
                )
            else:
                # 다른 타입 → 업데이트
                existing_feedback.feedback_type = feedback.feedback_type
                existing_feedback.search_query = feedback.search_query
                existing_feedback.search_context = feedback.search_context
                await db.commit()
                return FeedbackResponse(
                    success=True,
                    message="피드백이 변경되었습니다.",
                    current_feedback_type=feedback.feedback_type
                )
        else:
            # 새로 생성
            new_feedback = SearchFeedback(
                user_id=user_id,
                session_id=session_id,
                product_id=feedback.product_id,
                feedback_type=feedback.feedback_type,
                search_query=feedback.search_query,
                search_context=feedback.search_context
            )
            db.add(new_feedback)
            await db.commit()
            return FeedbackResponse(
                success=True,
                message="피드백이 등록되었습니다.",
                current_feedback_type=feedback.feedback_type
            )

    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit feedback: {str(e)}"
        )


@router.get("/stats/{product_id}", response_model=FeedbackStats)
async def get_feedback_stats(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_session_id: Optional[str] = Header(None)
):
    """
    피드백 통계 조회
    - 일반 사용자: 좋아요 수만 표시
    - 관리자: 좋아요 + 싫어요 모두 표시
    """
    # 좋아요 수 조회
    like_stmt = select(func.count()).select_from(SearchFeedback).where(
        SearchFeedback.product_id == product_id,
        SearchFeedback.feedback_type == "like"
    )
    like_result = await db.execute(like_stmt)
    like_count = like_result.scalar() or 0

    # 관리자 여부 확인
    user_id, _ = await get_user_or_session(request, db, x_session_id)
    is_admin = False

    if user_id:
        user = await db.get(User, user_id)
        is_admin = user.is_superuser if user else False

    dislike_count = 0
    if is_admin:
        # 싫어요 수 조회 (관리자만)
        dislike_stmt = select(func.count()).select_from(SearchFeedback).where(
            SearchFeedback.product_id == product_id,
            SearchFeedback.feedback_type == "dislike"
        )
        dislike_result = await db.execute(dislike_stmt)
        dislike_count = dislike_result.scalar() or 0

    # 좋아요 비율 계산
    total = like_count + dislike_count
    like_ratio = like_count / total if total > 0 else 0.0

    return FeedbackStats(
        like_count=like_count,
        dislike_count=dislike_count if is_admin else 0,
        like_ratio=like_ratio
    )


@router.get("/my-feedback/{product_id}", response_model=Optional[FeedbackDetail])
async def get_my_feedback(
    product_id: int,
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_session_id: Optional[str] = Header(None)
):
    """내 피드백 조회"""
    user_id, session_id = await get_user_or_session(request, db, x_session_id)

    if not user_id and not session_id:
        return None

    if user_id:
        stmt = select(SearchFeedback).where(
            SearchFeedback.user_id == user_id,
            SearchFeedback.product_id == product_id
        )
    else:
        stmt = select(SearchFeedback).where(
            SearchFeedback.session_id == session_id,
            SearchFeedback.product_id == product_id
        )

    result = await db.execute(stmt)
    feedback = result.scalar_one_or_none()

    if not feedback:
        return None

    return FeedbackDetail(
        id=feedback.id,
        product_id=feedback.product_id,
        feedback_type=feedback.feedback_type,
        search_query=feedback.search_query,
        created_at=feedback.created_at
    )


@router.get("/admin/recent", response_model=list[FeedbackListItem])
async def get_recent_feedbacks(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """관리자 전용: 최근 피드백 목록"""
    stmt = select(SearchFeedback).order_by(
        SearchFeedback.created_at.desc()
    ).limit(limit)

    result = await db.execute(stmt)
    feedbacks = result.scalars().all()

    return [
        FeedbackListItem(
            id=f.id,
            user_id=f.user_id,
            session_id=f.session_id,
            product_id=f.product_id,
            feedback_type=f.feedback_type,
            search_query=f.search_query,
            created_at=f.created_at
        )
        for f in feedbacks
    ]


@router.delete("/{feedback_id}")
async def delete_feedback(
    feedback_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_superuser)
):
    """관리자 전용: 피드백 삭제"""
    stmt = delete(SearchFeedback).where(SearchFeedback.id == feedback_id)
    await db.execute(stmt)
    await db.commit()

    return {"success": True, "message": "피드백이 삭제되었습니다."}
