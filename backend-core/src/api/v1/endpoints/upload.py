from typing import Any
from fastapi import APIRouter, UploadFile, File, HTTPException
import shutil
import os
from uuid import uuid4
import logging

# 로거 설정
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/upload/image")
async def upload_image(file: UploadFile = File(...)) -> Any:
    try:
        # 1. 저장 경로 설정 (Docker Volume 경로)
        UPLOAD_DIR = "/app/src/static/images"
        
        # 2. 폴더가 없으면 생성 (권한 문제 방지)
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
            logger.info(f"📁 Created directory: {UPLOAD_DIR}")

        # 3. 파일명 안전하게 변경 (UUID 사용)
        # 확장자가 없는 경우를 대비한 안전장치 추가
        filename = file.filename or "unknown.jpg"
        file_extension = filename.split(".")[-1].lower()
        
        # 허용된 확장자 체크 (선택 사항)
        if file_extension not in ["jpg", "jpeg", "png", "webp"]:
            file_extension = "jpg" # 기본값 설정

        new_filename = f"{uuid4()}.{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, new_filename)

        # 4. 파일 저장
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"✅ [Upload] Saved to: {file_path}")

        # 5. URL 반환
        # 프론트엔드에서 이 URL을 받아서 'Create Product' 할 때 사용합니다.
        return {"url": f"/static/images/{new_filename}"}

    except Exception as e:
        logger.error(f"❌ Upload Failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Image upload failed: {str(e)}")