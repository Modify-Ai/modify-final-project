from typing import Any, List, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from src.api import deps
from src.crud import crud_user
from src.schemas.user import User, UserUpdate
from src.models.user import User as UserModel

router = APIRouter()

def check_superuser(current_user: UserModel = Depends(deps.get_current_user)) -> UserModel:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user

# 1. 내 정보 조회 (GET)
@router.get("/me", response_model=User)
async def read_user_me(
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    return current_user

# 2. 내 정보 수정 (PATCH)
@router.patch("/me", response_model=User)
async def update_user_me(
    *,
    db: AsyncSession = Depends(deps.get_db),
    user_in: UserUpdate,
    current_user: UserModel = Depends(deps.get_current_user),
) -> Any:
    # 이메일 중복 체크 로직
    if user_in.email and user_in.email != current_user.email:
        existing_user = await crud_user.get_user_by_email(db, email=user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="이미 사용 중인 이메일입니다.",
            )

    updated_user = await crud_user.update_user(db, db_obj=current_user, obj_in=user_in)

    return updated_user

# 3. 관리자 - 사용자 목록 조회
@router.get("/admin/list", response_model=dict)
async def get_users_list(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None, description="이메일 또는 이름 검색"),
    is_active: Optional[bool] = Query(None, description="활성화 상태 필터"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: UserModel = Depends(check_superuser),
) -> Any:
    """관리자용 사용자 목록 조회"""
    offset = (page - 1) * limit

    # 전체 사용자 수 조회
    count_query = select(func.count(UserModel.id))
    if search:
        count_query = count_query.where(
            (UserModel.email.ilike(f"%{search}%")) |
            (UserModel.full_name.ilike(f"%{search}%"))
        )
    if is_active is not None:
        count_query = count_query.where(UserModel.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 사용자 목록 조회
    query = select(UserModel)
    if search:
        query = query.where(
            (UserModel.email.ilike(f"%{search}%")) |
            (UserModel.full_name.ilike(f"%{search}%"))
        )
    if is_active is not None:
        query = query.where(UserModel.is_active == is_active)

    query = query.order_by(desc(UserModel.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    users = result.scalars().all()

    # 통계 계산
    from sqlalchemy import case as sql_case
    stats_query = select(
        func.count(UserModel.id).label('total'),
        func.sum(sql_case((UserModel.is_active == True, 1), else_=0)).label('active'),
        func.sum(sql_case((UserModel.is_marketing_agreed == True, 1), else_=0)).label('marketing'),
        func.sum(sql_case((UserModel.is_superuser == True, 1), else_=0)).label('admin')
    )
    stats_result = await db.execute(stats_query)
    stats_row = stats_result.one()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "users": [User.model_validate(user) for user in users],
        "stats": {
            "total": stats_row.total or 0,
            "active": stats_row.active or 0,
            "marketing": stats_row.marketing or 0,
            "admin": stats_row.admin or 0
        }
    }

# 4. 관리자 - 사용자 상태 변경
@router.patch("/admin/{user_id}/status", response_model=User)
async def update_user_status(
    user_id: int,
    status_data: dict,
    db: AsyncSession = Depends(deps.get_db),
    current_user: UserModel = Depends(check_superuser),
) -> Any:
    """관리자용 사용자 상태 업데이트 (활성화/비활성화, 관리자 권한)"""
    # 사용자 조회
    query = select(UserModel).where(UserModel.id == user_id)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

    # 본인은 수정 불가
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="본인의 상태는 변경할 수 없습니다.")

    # 상태 업데이트
    if "is_active" in status_data:
        user.is_active = status_data["is_active"]
    if "is_superuser" in status_data:
        user.is_superuser = status_data["is_superuser"]

    await db.commit()
    await db.refresh(user)

    return user