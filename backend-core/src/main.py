import logging
import os
from contextlib import asynccontextmanager
import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi_limiter import FastAPILimiter
from fastapi.staticfiles import StaticFiles

from src.config.settings import settings
from src.core.security import setup_superuser
from src.db.session import engine, async_session_maker
from src.middleware.exception_handler import global_exception_handler
from src.api.v1 import api_router

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# 1. Lifespan 이벤트 핸들러 (Startup/Shutdown 관리)
# --------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 시작 및 종료 시 이벤트를 처리합니다."""
    
    # [Startup 1] Redis 및 Rate Limiter 초기화
    redis_connection = None
    try:
        redis_connection = redis.from_url(settings.REDIS_URL, encoding="utf-8", decode_responses=True)
        await FastAPILimiter.init(redis_connection)
        logger.info("✅ Rate Limiter System Ready.")
    except Exception as e:
        logger.warning(f"⚠️ Redis Connection Failed. Rate Limiter will be inactive: {e}")
    
    # [Startup 2] 초기 관리자 계정 생성 및 DB 유효성 검사
    async with async_session_maker() as session:
        try:
            await setup_superuser(session)
            logger.info("✅ Superuser check completed.")
        except Exception as e:
            logger.error(f"❌ Failed to set up superuser (DB Error likely): {e}")

    # [Startup 3] AI 모델 프리로딩 (선택사항: 필요시 주석 해제)
    # try:
    #     from src.core.model_engine import ModelEngine
    #     ModelEngine.initialize() # 모델을 미리 메모리에 올림
    #     logger.info("✅ AI Models Pre-loaded.")
    # except Exception as e:
    #     logger.warning(f"⚠️ Model pre-loading skipped: {e}")

    yield # 애플리케이션 실행 구간

    # [Shutdown] 리소스 해제
    if redis_connection:
        await redis_connection.close()
    await engine.dispose()
    logger.info("🛑 Application shutdown complete.")

# --------------------------------------------------------------------------
# 2. FastAPI 애플리케이션 인스턴스 생성
# --------------------------------------------------------------------------
app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
   docs_url="/docs",  # ✅ 무조건 문서 열기
    openapi_url="/openapi.json"
)

# --------------------------------------------------------------------------
# 3. CORS 미들웨어 설정 (프론트엔드 통신 필수)
# --------------------------------------------------------------------------
# 개발 환경에서는 광범위하게 허용, 운영에서는 엄격하게 관리
origins = [
    "http://localhost",           # Nginx (포트 80)
    "http://localhost:80",
    "http://localhost:5173",      # Vite 로컬 개발
    "http://127.0.0.1",
    "http://127.0.0.1:5173",
    "http://modify-frontend:5173", # Docker 내부 통신용
    settings.FRONTEND_URL,        # .env에서 가져온 URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST, PUT, DELETE 등 모두 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# --------------------------------------------------------------------------
# 4. 예외 핸들러 및 라우터 포함
# --------------------------------------------------------------------------
app.add_exception_handler(Exception, global_exception_handler)
app.include_router(api_router, prefix=settings.API_V1_STR)

# --------------------------------------------------------------------------
# 5. 정적 파일(이미지) 서빙 설정
# --------------------------------------------------------------------------
try:
    # 현재 파일(main.py)의 위치: /app/src
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    
    # 정적 파일 경로: /app/src/static
    static_dir = os.path.join(BASE_DIR, "static")
    image_dir = os.path.join(static_dir, "images")
    
    # 🚨 중요: 폴더가 없으면 에러가 나므로 자동 생성
    os.makedirs(image_dir, exist_ok=True)
    
    # /static 경로로 들어오는 요청을 static_dir 폴더로 연결
    app.mount("/static", StaticFiles(directory=static_dir), name="static")
    
    logger.info(f"✅ Static file serving enabled: /static -> {static_dir}")
except Exception as e:
    logger.error(f"❌ Failed to setup static file serving: {e}")

# --------------------------------------------------------------------------
# 6. 기본 엔드포인트
# --------------------------------------------------------------------------
@app.get("/health")
async def health_check():
    return {"status": "ok", "env": settings.ENVIRONMENT}

@app.get("/")
def read_root():
    return {"message": f"Welcome to {settings.PROJECT_NAME} API Service"}

@app.get("/debug/images")
def debug_images():
    """이미지 업로드 디버깅용: 실제 폴더에 파일이 있는지 확인"""
    try:
        check_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", "images")
        
        if not os.path.exists(check_path):
            return {"status": "error", "message": f"폴더가 없습니다: {check_path}"}
            
        files = os.listdir(check_path)
        return {
            "status": "ok",
            "path": check_path,
            "file_count": len(files),
            "files": files
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}