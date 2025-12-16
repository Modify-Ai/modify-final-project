from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, ConfigDict, field_validator
import re

# 공통 속성
class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    is_active: Optional[bool] = True
    is_superuser: Optional[bool] = False
    phone_number: Optional[str] = None 

# 회원가입/생성 시 필요한 속성
class UserCreate(UserBase):
    password: str

    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6 or len(v) > 100:
            raise ValueError('비밀번호는 6자 이상 100자 이하이어야 합니다.')
        
        if not re.match(r"^(?=.*[A-Za-z])(?=.*\d).+$", v):
            raise ValueError('비밀번호는 영문과 숫자를 반드시 포함해야 합니다.')
            
        return v

# 업데이트 시 필요한 속성 (내 정보 수정)
class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    password: Optional[str] = None
    is_marketing_agreed: Optional[bool] = None
    phone_number: Optional[str] = None
    
    # ✅ [NEW] 프로필 정보 수정 필드 추가
    profile_image: Optional[str] = None
    address: Optional[str] = None
    birthdate: Optional[str] = None
    location: Optional[str] = None

# DB에서 조회해서 나갈 때 쓰는 속성 (로그인 응답 등)
class UserResponse(UserBase):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    provider: str = "email"
    created_at: datetime 
    updated_at: datetime 
    is_marketing_agreed: bool 
    
    # ✅ [NEW] 관리자 권한 확인을 위해 명시적 선언 (상속받지만 확실하게!)
    is_active: bool = True
    is_superuser: bool = False

    # ✅ [NEW] 프로필 정보 응답 필드 추가
    profile_image: Optional[str] = None
    address: Optional[str] = None
    birthdate: Optional[str] = None
    location: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

# 로그인 시 토큰 응답 스키마
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: Optional[int] = None

# 외부 파일 호환성
User = UserResponse