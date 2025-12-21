from fastapi import APIRouter

# 각 엔드포인트 모듈 임포트
from src.api.v1.endpoints import (
    auth,
    admin,
    users,
    products,
    search,
    wishlist,
    fitting,
    upload,
    orders
)

api_router = APIRouter()

# 1. 인증 (로그인, 회원가입)
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

# 2. 관리자 기능
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])

# 3. 사용자 관리
api_router.include_router(users.router, prefix="/users", tags=["users"])

# 4. 상품 관련 (조회, 업로드, AI 분석)
api_router.include_router(products.router, prefix="/products", tags=["products"])

# 5. 검색 기능 (AI 검색, 텍스트 검색)
api_router.include_router(search.router, prefix="/search", tags=["search"])

# 6. [NEW] 위시리스트 (찜하기)
api_router.include_router(wishlist.router, prefix="/wishlist", tags=["wishlist"])

api_router.include_router(upload.router, prefix="/utils", tags=["utils"])

# 7. [NEW] 가상 피팅 기능
api_router.include_router(fitting.router, prefix="/fitting", tags=["fitting"])

# 8. [NEW] 주문 관리
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])