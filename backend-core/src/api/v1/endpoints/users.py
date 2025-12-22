from typing import Any
from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.api import deps
from src.crud import crud_user # 👈 우리가 만든 crud 파일 가져오기
from src.schemas.user import User, UserUpdate
from src.models.user import User as UserModel

router = APIRouter()

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
            
    # 🔥 [수정 포인트] 여기가 중요해! 
    # 아까 crud_user.py에 만든 함수 이름(update_user)을 정확하게 불러야 해.
    # (전: crud_user.user.update -> 후: crud_user.update_user)
    updated_user = await crud_user.update_user(db, db_obj=current_user, obj_in=user_in)
    
    return updated_user