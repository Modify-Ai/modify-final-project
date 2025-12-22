from typing import Optional, Dict, Any, Union # 👈 Dict, Any, Union 추가됨
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from src.models.user import User
from src.schemas.user import UserCreate, UserUpdate # 👈 UserUpdate 추가됨 (필수!)
from src.core.security import get_password_hash, verify_password

# --------------------------------------------------------------------------
# ID로 유저 조회
# --------------------------------------------------------------------------
async def get(db: AsyncSession, user_id: int) -> Optional[User]:
    """ID 기반 유저 조회"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().first()

# --------------------------------------------------------------------------
# 이메일로 유저 조회
# --------------------------------------------------------------------------
async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """이메일 기반 유저 조회"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalars().first()

# --------------------------------------------------------------------------
# 핸드폰 번호로 유저 조회
# --------------------------------------------------------------------------
async def get_user_by_phone(db: AsyncSession, phone: str) -> Optional[User]:
    query = select(User).where(User.phone_number == phone)
    result = await db.execute(query)
    return result.scalars().first()

# --------------------------------------------------------------------------
# 유저 생성
# --------------------------------------------------------------------------
async def create_user(db: AsyncSession, user: UserCreate) -> User:
    """새로운 유저 생성 (비밀번호 해싱 적용)"""
    hashed_password = get_password_hash(user.password)
    db_obj = User(
        email=user.email,
        hashed_password=hashed_password,
        full_name=user.full_name,
        phone_number=user.phone_number,
        birthdate=user.birthdate,
        zip_code=user.zip_code,
        address=user.address,
        detail_address=user.detail_address,

        # 전화번호가 있으면 인증된 것으로 간주 (API에서 체크했으므로)
        is_phone_verified=True if user.phone_number else False,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        provider="local"
    )
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

# --------------------------------------------------------------------------
# 🔥 [NEW] 유저 정보 수정 (이게 없어서 업데이트 실패가 떴던 거야!)
# --------------------------------------------------------------------------
async def update_user(
    db: AsyncSession, 
    db_obj: User, 
    obj_in: Union[UserUpdate, Dict[str, Any]]
) -> User:
    """
    유저 정보를 업데이트합니다.
    (주석 유지: 비밀번호 변경 및 프로필 정보 자동 반영)
    """
    # 1. 변경할 데이터 정리 (딕셔너리 변환)
    if isinstance(obj_in, dict):
        update_data = obj_in
    else:
        update_data = obj_in.model_dump(exclude_unset=True)

    # 2. 비밀번호가 변경 목록에 있다면 암호화해서 처리
    if "password" in update_data and update_data["password"]:
        hashed_password = get_password_hash(update_data["password"])
        del update_data["password"]
        db_obj.hashed_password = hashed_password

    # 3. 나머지 정보들(이메일, 이름, 주소 등) 업데이트
    for field in update_data:
        if hasattr(db_obj, field):
            setattr(db_obj, field, update_data[field])

    # 4. DB 저장
    db.add(db_obj)
    await db.commit()
    await db.refresh(db_obj)
    return db_obj

# --------------------------------------------------------------------------
# 인증 확인 (로그인 용)
# --------------------------------------------------------------------------
async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[User]:
    """이메일과 비밀번호로 유저 검증"""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user