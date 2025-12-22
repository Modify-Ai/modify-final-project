from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from jose import jwt, JWTError

from src.api.deps import get_db, get_current_user
from src.core import security
from src.crud import crud_user
from src.schemas.user import UserCreate, UserResponse, Token
from src.models.user import User
from src.config.settings import settings
import random
import re
import redis

router = APIRouter()

# --------------------------------------------------------------------------
# 회원가입 API
# POST /api/v1/auth/signup
# --------------------------------------------------------------------------
@router.post("/signup", response_model=UserResponse, status_code=201)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    일반 사용자 회원가입
    """
    # 이메일 중복 체크
    user = await crud_user.get_user_by_email(db, email=user_in.email)
    if user:
        raise HTTPException(
            status_code=400,
            detail="The user with this email already exists in the system.",
        )
    
    # 유저 생성
    user = await crud_user.create_user(db, user=user_in)
    return user

# --------------------------------------------------------------------------
# 로그인 API
# POST /api/v1/auth/login
# --------------------------------------------------------------------------
@router.post("/login", response_model=Token)
async def login_access_token(
    db: AsyncSession = Depends(get_db), 
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 호환 토큰 로그인 (username=이메일)
    """
    user = await crud_user.authenticate_user(
        db, email=form_data.username, password=form_data.password
    )
    if not user:
        raise HTTPException(status_code=400, detail="회원정보가 일치하지 않습니다.")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    # Access Token (짧은 만료)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    # Refresh Token (긴 만료: 7일)
    refresh_token_expires = timedelta(days=7)
    refresh_token = security.create_refresh_token(
        user.id, expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }

# --------------------------------------------------------------------------
# 토큰 갱신 API
# POST /api/v1/auth/refresh
# --------------------------------------------------------------------------
@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Refresh Token을 검증하여 새로운 Access Token을 발급합니다.
    """
    try:
        # 토큰 디코딩 및 검증
        payload = jwt.decode(
            refresh_token, settings.JWT_SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        token_type = payload.get("type")
        user_id = payload.get("sub")
        
        if token_type != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token subject")
            
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")
        
        # 사용자 조회
    user = await crud_user.get(db, user_id=int(user_id))
    
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    elif not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")

    # 새 Access Token 발급
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    new_access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )
    
    # Refresh Token Rotation (보안 강화: Refresh Token도 새로 발급)
    new_refresh_token = security.create_refresh_token(
        user.id, expires_delta=timedelta(days=7)
    )
    
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

# --------------------------------------------------------------------------
# 내 정보 조회 API
# GET /api/v1/auth/me
# --------------------------------------------------------------------------
@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """
    현재 로그인한 내 정보 조회
    """
    return current_user

# --------------------------------------------------------------------------
# 인증번호 발송 API
# GET /api/v1/auth/send-code
# --------------------------------------------------------------------------

# --- Redis 연결 설정 ---
# Docker Compose의 redis 서비스와 연결
try:
    # from_url을 사용하면 host, port, db 등을 한 번에 설정 가능
    # decode_responses=True: 데이터를 받을 때 bytes가 아닌 str로 자동 변환
    redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
except Exception as e:
    redis_client = None
    print(f"❌ Redis 연결 실패: {e}")
    # 실제 운영 시에는 여기서 에러를 발생시키거나 예외 처리를 해야 합니다.

# --- 요청/응답 스키마 정의 ---
class PhoneAuthRequest(BaseModel):
    phone_number: str

class PhoneVerifyRequest(BaseModel):
    phone_number: str
    code: str

@router.post("/send-code", status_code=200)
def send_verification_code(request: PhoneAuthRequest):
    """
    [인증번호 발송 API]
    1. 전화번호 형식을 검증합니다.
    2. 6자리 랜덤 숫자를 생성합니다.
    3. (Mock) 콘솔에 출력하거나 실제 SMS를 발송합니다.
    4. 저장소에 {전화번호: 인증번호}를 저장합니다.
    """
    # 1. 전화번호 정제 (하이픈 제거)
    phone = request.phone_number.replace("-", "").strip()
    
    # 2. 형식 검사 (010xxxxxxxx)
    if not re.match(r"^01[0-9]\d{7,8}$", phone):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="유효하지 않은 전화번호 형식입니다."
        )

    # 3. 인증번호 생성 (6자리)
    code = str(random.randint(100000, 999999))
    
    # 4. Redis 저장 (Key: 전화번호, Value: 인증번호, TTL: 180초)
    # setex(name, time, value) -> time 초 후에 데이터가 자동 삭제됨
    try:
        redis_client.setex(name=phone, time=180, value=code)
    except redis.RedisError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="인증 서버(Redis) 연결에 실패했습니다."
        )
    
    # 5. [Mock] SMS 발송 대신 콘솔 출력 (개발용)
    print(f"=========================================")
    print(f"📩 [SMS 발송] 수신자: {phone}, 인증번호: [{code}]")
    print(f"=========================================")
    
    # 실제 SMS API 연동 시 여기에 CoolSMS 등의 코드가 들어갑니다.
    return {"message": "인증번호가 발송되었습니다.", "debug_code": code} # 디버깅용으로 코드 반환 (배포 시 제거)

# --------------------------------------------------------------------------
# 인증번호 확인 API
# GET /api/v1/auth/verify-code
# --------------------------------------------------------------------------

@router.post("/verify-code", status_code=200)
def verify_phone_code(request: PhoneVerifyRequest):
    """
    [인증번호 확인 API]
    1. 저장소에서 해당 전화번호의 인증번호를 찾습니다.
    2. 사용자가 입력한 코드와 일치하는지 확인합니다.
    3. 일치하면 성공, 아니면 에러를 반환합니다.
    """
    phone = request.phone_number.replace("-", "").strip()
    input_code = request.code
    
    try:
        # 1. Redis에서 조회
        saved_code = redis_client.get(phone)
    except redis.RedisError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="인증 서버 오류입니다."
        )
    
    # 2. 검증 로직
    if saved_code is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="인증번호가 만료되었거나 요청 기록이 없습니다."
        )
    
    if saved_code == input_code:
        # 인증 성공 시, 재사용 방지를 위해 Redis에서 즉시 삭제
        redis_client.delete(phone)
        return {"message": "인증에 성공했습니다."}
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="인증번호가 일치하지 않습니다."
        )