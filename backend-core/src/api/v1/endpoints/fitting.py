import os
import base64
import io
import httpx
from PIL import Image
from typing import List, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

import replicate
from pydantic import BaseModel
from datetime import datetime

from src.db.session import get_db
from src.models.user import User
from src.models.fitting import FittingResult
from src.api import deps    # 로그인 유저 확인용

router = APIRouter()

# 응답 스키마 (Schemas)
class FittingResponse(BaseModel):
    image_url: str
    id: int # 저장된 ID도 반환

class FittingHistoryResponse(BaseModel):
    id: int
    result_image_url: str
    category: str | None
    created_at: datetime
    
    class Config:
        from_attributes = True


# Helper Function 1 : 바이트 -> PIL 이미지 변환 및 리사이징 (YOLO용)
def preprocess_image(image_bytes: bytes) -> Image.Image:
    """
    이미지 바이트를 받아서 3:4 비율로 리사이징 및 패딩 처리된 PIL 객체를 반환합니다.
    (YOLO와 Replicate가 공통으로 사용)
    """
    img = Image.open(io.BytesIO(image_bytes))

    # 투명 배경(PNG) 등 처리
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    # 3:4 비율(768x1024) 설정
    target_ratio = 3 / 4
    target_width = 768
    target_height = 1024
    
    current_width, current_height = img.size
    current_ratio = current_width / current_height

    # 비율에 맞춰 리사이징 계산
    if current_ratio > target_ratio:
        new_width = target_width
        new_height = int(target_width / current_ratio)
    else:
        new_height = target_height
        new_width = int(target_height * current_ratio)
        
    img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
    
    # 흰색 배경 캔버스 생성
    new_img = Image.new("RGB", (target_width, target_height), (255, 255, 255))
    
    # 중앙 정렬 붙여넣기
    paste_x = (target_width - new_width) // 2
    paste_y = (target_height - new_height) // 2
    new_img.paste(img, (paste_x, paste_y))
    
    return new_img

# Helper Function 2 : PIL 이미지 -> Base64 문자열 변환 (API 전송용)
def image_to_base64(img: Image.Image) -> str:
    buffer = io.BytesIO()
    # JPEG 포맷, 퀄리티 85
    img.save(buffer, format="JPEG", quality=85)
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"

# Helper Function 3 : 의류 이미지 파일명 분석 -> 영문 프롬프트 생성
def get_detailed_garment_prompt(filename: str, category: str) -> str:
    """
    파일명에 포함된 한글 키워드를 분석하여, AI에게 전달할 최적의 영문 프롬프트를 생성합니다.
    """
    filename = filename.replace(" ", "").lower() # 공백 제거 및 소문자화
    
    # 기본 수식어 (퀄리티 향상용)
    base_suffix = ", high quality, realistic texture, 8k, detailed features"
    desc = "clothing" # 기본값

    # --------------------------------------------------------
    # 1. 아우터 (Outerwear)
    # --------------------------------------------------------
    if "패딩" in filename:
        if "롱" in filename:
            desc = "long down jacket, winter puffy coat, warm texture"
        elif "숏" in filename:
            desc = "short down jacket, puffer jacket, cropped length"
        else:
            desc = "padded jacket, down coat, puffy texture"
            
    elif "코트" in filename:
        if "더블" in filename:
            desc = "double-breasted wool coat, long trench coat style"
        else:
            desc = "single-breasted long coat, wool blend texture, clean look"
            
    elif "무스탕" in filename:
        desc = "shearling jacket, leather jacket with fur lining, mustang style"
        
    elif "플리스" in filename or "후리스" in filename:
        desc = "fleece jacket, fuzzy texture, warm material"
        
    elif "카디건" in filename or "가디건" in filename:
        desc = "knitted cardigan, soft wool texture, button down"
        
    elif "재킷" in filename or "자켓" in filename:
        if "레더" in filename or "가죽" in filename:
            desc = "leather jacket, biker style, smooth texture"
        elif "데님" in filename or "청" in filename:
            desc = "denim jacket, jean jacket"
        else:
            desc = "tailored jacket, blazer, formal style"
            
    elif "후드" in filename:
        if "집업" in filename:
            desc = "zip-up hoodie, casual sweatshirt material"
        else:
            desc = "hooded sweatshirt, hoodie, cotton jersey texture"

    # --------------------------------------------------------
    # 2. 상의 (Tops)
    # --------------------------------------------------------
    elif "맨투맨" in filename:
        desc = "sweatshirt, crew neck, cotton texture, long sleeve"
        
    elif "스웨터" in filename or "니트" in filename:
        desc = "knitted sweater, wool texture, ribbed details"
        
    elif "셔츠" in filename or "남방" in filename:
        if "체크" in filename:
            desc = "plaid shirt, button up shirt, collar"
        else:
            desc = "dress shirt, button up, crisp cotton texture"
            
    elif "티셔츠" in filename:
        if "반소매" in filename or "반팔" in filename:
            desc = "short sleeve t-shirt, casual cotton top"
        elif "긴소매" in filename or "긴팔" in filename:
            desc = "long sleeve t-shirt, basic top"
        else:
            desc = "t-shirt, jersey fabric"

    # --------------------------------------------------------
    # 3. 드레스 / 원피스 (Dresses)
    # --------------------------------------------------------
    elif "원피스" in filename:
        if "맥시" in filename or "롱" in filename:
            desc = "maxi dress, long one-piece dress, elegant flow"
        elif "미니" in filename:
            desc = "mini dress, short one-piece"
        elif "미디" in filename:
            desc = "midi dress, knee length one-piece"
        else:
            desc = "one-piece dress, casual dress"

    # --------------------------------------------------------
    # 4. 하의 (Bottoms)
    # --------------------------------------------------------
    elif "슬랙스" in filename:
        desc = "slacks, formal trousers, suit pants, smooth fabric"
        
    elif "레깅스" in filename:
        desc = "tight leggings, yoga pants, athletic wear, stretchy fabric"
        
    elif "스커트" in filename or "치마" in filename:
        if "롱" in filename:
            desc = "long skirt, maxi skirt"
        elif "미니" in filename:
            desc = "mini skirt, short length"
        elif "데님" in filename:
            desc = "denim skirt, jean skirt"
        else:
            desc = "skirt, bottom wear"
            
    elif "팬츠" in filename or "바지" in filename:
        if "데님" in filename or "청" in filename:
            desc = "blue jeans, denim pants, texture details"
        elif "카고" in filename:
            desc = "cargo pants, utility pockets"
        else:
            desc = "trousers, pants"

    # --------------------------------------------------------
    # 5. 예외 처리 (파일명에서 정보를 못 찾은 경우)
    # --------------------------------------------------------
    else:
        # 카테고리 정보를 보조적으로 사용
        if category == "dresses":
            desc = "dress, one-piece"
        elif category == "lower_body":
            desc = "pants, trousers, skirt"
        else:
            desc = "top, shirt, outerwear"

    return desc + base_suffix

# 1. 가상 피팅 생성 및 저장 엔드포인트
# .env 파일이나 settings.py에 REPLICATE_API_TOKEN이 있어야 합니다.
@router.post("/generate", response_model=FittingResponse)
async def generate_fitting(
    human_img: UploadFile = File(...),
    garm_img: UploadFile = File(...),
    category: str = Form("upper_body"),  # 프론트에서 보낸 값이 여기로 들어온다.
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)  # 로그인 유저 필수
):
    """
    [가상 피팅 생성 API (YOLO Segmentation 적용)]
    1. 이미지 전처리 (3:4 비율 맞춤)
    2. YOLO를 사용하여 사람 영역 마스크(Mask) 생성
    3. Replicate IDM-VTON 모델에 원본+마스크 전송
    """
    try:
        # 1. 파일 읽기 (바이트 변환)
        human_bytes = await human_img.read()
        garm_bytes = await garm_img.read()

        # 2. 이미지 전처리 (PIL 객체 생성)
        human_pil = preprocess_image(human_bytes)
        garm_pil = preprocess_image(garm_bytes)

        # Base64 변환 (AI Service에 보내기 위해 필요)
        human_uri = image_to_base64(human_pil)
        garm_uri = image_to_base64(garm_pil)

        if category == "lower_body":
            target_part = "lower"
        elif category == "dresses":     # 아우터/원피스
            target_part = "full"
        else:
            target_part = "upper"

        # 3. AI Service에 마스크 생성 요청 보내기
        print("📡 AI Service에 마스크 생성 요청 중...")
        
        mask_uri = None
        ai_service_url = "http://ai-service-api:8000/api/v1/generate-mask" # 도커 서비스명 사용

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    ai_service_url,
                    json={"image_b64": human_uri, "target": target_part},
                    timeout=10.0 # 10초 대기
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get("status") == "success":
                        mask_uri = result.get("mask_b64")
                        print("✅ AI Service로부터 마스크 수신 완료")
                    else:
                        print("⚠️ AI Service: 마스크 생성 실패")
                else:
                    print(f"⚠️ AI Service 통신 오류: {response.status_code}")
                    
        except Exception as e:
            print(f"❌ AI Service 연결 실패: {e}")
            # 마스크 없이 진행 (Fallback)
        
        garment_desc = get_detailed_garment_prompt(garm_img.filename, category)
        print(f"📝 생성된 프롬프트: {garment_desc}")

        # 4. Replicate 입력 데이터 구성
        input_data = {
            "human_img": human_uri,   
            "garm_img": garm_uri,
            "category": category,       
            "garment_des": garment_desc,  
            "crop": False,
            "seed": 42
        }
        
        # 마스크가 있으면 입력에 추가
        if mask_uri:
            input_data["mask_img"] = mask_uri

        # 5. Replicate 모델 실행
        model_id = "cuuupid/idm-vton:0513734a452173b8173e907e3a59d19a36266e55b48528559432bd21c7d7e985"

        output = replicate.run(
            model_id, 
            input=input_data
        )

        result_url = str(output)
        print(f"✅ 생성 완료: {result_url}")

        # 6. DB 저장 로직
        history = FittingResult(
            user_id=current_user.id,
            result_image_url=result_url,
            category=category,
            created_at=datetime.utcnow()
        )
        db.add(history)
        await db.commit()
        await db.refresh(history)

        print(f"✅ DB 저장 완료 (ID: {history.id})")

        return {"image_url": result_url, "id": history.id}
    
    except replicate.exceptions.ReplicateError as e:
        print(f"❌ Replicate API Error: {e}")
        raise HTTPException(status_code=500, detail=f"AI 모델 오류: {str(e)}")
    
    except Exception as e:
        print(f"❌ General Error: {e}")
        raise HTTPException(status_code=500, detail=f"서버 오류: {str(e)}")


# 2. 가상 피팅 히스토리 목록 조회 엔드포인트
@router.get("/history", response_model=List[FittingHistoryResponse])
async def get_fitting_history(
    skip: int = 0,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(deps.get_current_user)  # 로그인 유저 필수
):
    """
    [가상 피팅 히스토리 조회 API]
    1. 로그인한 유저의 가상 피팅 히스토리를 조회합니다.
    2. 최신 순으로 정렬하여 반환합니다.
    """
    query = select(FittingResult)\
        .where(FittingResult.user_id == current_user.id)\
        .order_by(desc(FittingResult.created_at))\
        .offset(skip)\
        .limit(limit)
        
    result = await db.execute(query) 
    histories = result.scalars().all() 
    
    return histories