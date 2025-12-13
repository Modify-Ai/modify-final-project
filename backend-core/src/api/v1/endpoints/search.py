"""
search.py - 수정된 버전 v2
경로: backend-core/src/api/v1/endpoints/search.py

수정 사항:
1. 텍스트만 있어도 determine-path 호출
2. EXTERNAL 경로일 때 CLIP 이미지 벡터로 검색 (핵심 수정!)
3. 키워드 추출 시 연예인 검색 고려
"""

import logging
import base64
import asyncio
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from pydantic import BaseModel, ValidationError 

from src.api import deps
from src.crud.crud_product import crud_product
from src.schemas.product import ProductResponse
from src.config.settings import settings
from src.models.product import Product  # ✅ Product 모델 import 추가

logger = logging.getLogger(__name__)
router = APIRouter()

# DTO
class ImageAnalysisRequest(BaseModel):
    image_b64: str
    query: str


def detect_gender_intent(query: str) -> Optional[str]:
    """검색어에서 성별 키워드 추출"""
    q = query.lower()
    if any(x in q for x in ["남자", "남성", "맨", "men", "male", "boy"]):
        return "Male"
    elif any(x in q for x in ["여자", "여성", "우먼", "women", "female", "girl"]):
        return "Female"
    return None


def extract_core_keyword(query: str) -> str:
    """검색어에서 핵심 상품 키워드 추출 (성별/수식어 제거)"""
    import re
    
    # 제거할 단어들
    remove_words = [
        "남자", "여자", "남성", "여성", "남성용", "여성용",
        "추천", "해줘", "보여줘", "찾아줘", "알려줘",
        "스타일", "패션", "옷", "의류", "용"
    ]
    
    result = query
    for word in remove_words:
        result = result.replace(word, "")
    
    # 조사 제거
    result = re.sub(r'(은|는|이|가|을|를|의|에|로)$', '', result.strip())
    
    return result.strip() if result.strip() else query


def is_celebrity_search(query: str) -> bool:
    """연예인/인물 검색인지 판단"""
    import re

    # 패션 관련 키워드와 함께 사용된 경우
    fashion_keywords = ["패션", "스타일", "코디", "룩", "공항", "착장", "의상", "옷"]

    # 한글 이름 패턴 (2-4글자)
    korean_name = re.search(r'[가-힣]{2,4}', query)

    if korean_name and any(k in query for k in fashion_keywords):
        return True

    return False


def extract_negative_keywords(negative_prompt: Optional[str]) -> List[str]:
    """
    네거티브 프롬프트에서 제외할 키워드 리스트 추출
    예: "청바지, 스니커즈, 캐주얼" -> ["청바지", "스니커즈", "캐주얼"]
    """
    if not negative_prompt:
        return []

    # 쉼표, 슬래시, 공백으로 구분
    import re
    keywords = re.split(r'[,/\s]+', negative_prompt.strip())

    # 빈 문자열 제거 및 소문자 변환
    return [k.strip().lower() for k in keywords if k.strip()]


def filter_products_by_negative(products: List[Product], negative_keywords: List[str]) -> List[Product]:
    """
    네거티브 키워드를 포함하는 상품 제외
    """
    if not negative_keywords:
        return products

    filtered = []
    for product in products:
        # 상품명, 설명, 카테고리에서 네거티브 키워드 검색
        text_to_check = f"{product.name} {product.description or ''} {product.category or ''}".lower()

        # 네거티브 키워드가 하나라도 포함되면 제외
        contains_negative = any(keyword in text_to_check for keyword in negative_keywords)

        if not contains_negative:
            filtered.append(product)

    logger.info(f"🚫 Filtered {len(products) - len(filtered)} products by negative keywords: {negative_keywords}")
    return filtered


async def fetch_image_as_base64(url: str) -> Optional[str]:
    """외부 이미지 프록시 다운로드"""
    if not url:
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.google.com/"
        }
        async with httpx.AsyncClient(timeout=5.0, verify=False) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                b64_data = base64.b64encode(response.content).decode('utf-8')
                content_type = response.headers.get("content-type", "image/jpeg")
                return f"data:{content_type};base64,{b64_data}"
    except Exception as e:
        logger.warning(f"⚠️ Failed to proxy image ({url}): {e}")
    return None


# ✅ NEW: CLIP 이미지 기반 검색 엔드포인트
class ClipSearchRequest(BaseModel):
    image_b64: str
    limit: int = 12
    query: Optional[str] = None  # ✅ 원본 검색어 (성별 추출용)
    target: str = "full"  # ✅ "full", "upper", "lower"
    negative_prompt: Optional[str] = None  # ✅ 네거티브 프롬프트 (제외할 특징)


@router.post("/search-by-clip")
async def search_by_clip_image(
    request: ClipSearchRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    이미지 기반 상품 검색
    - 후보 이미지 클릭 시 호출
    - 이미지 → CLIP 벡터 → 유사 상품 검색
    - ✅ 원본 쿼리에서 성별 추출하여 필터링
    - ✅ target: "full"(전체), "upper"(상의), "lower"(하의)
    """
    logger.info(f"🖼️ CLIP Image Search Request (limit: {request.limit}, query: {request.query}, target: {request.target})")
    
    # ✅ 원본 쿼리에서 성별 추출
    target_gender = None
    if request.query:
        target_gender = detect_gender_intent(request.query)
        logger.info(f"📌 Detected gender from query: {target_gender}")
    
    # ✅ target에 따른 카테고리 필터
    category_filter = None
    if request.target == "upper":
        category_filter = ["Tops", "Outerwear", "Shirts", "Sweaters", "상의", "아우터", "셔츠", "니트"]
    elif request.target == "lower":
        category_filter = ["Bottoms", "Pants", "Skirts", "하의", "바지", "치마"]
    
    AI_SERVICE_API_URL = settings.AI_SERVICE_API_URL
    
    try:
        # 1. AI 서비스에서 CLIP 벡터 생성 (YOLO + 영역 지정)
        async with httpx.AsyncClient(timeout=30.0) as client:
            clip_res = await client.post(
                f"{AI_SERVICE_API_URL}/generate-fashion-clip-vector",
                json={
                    "image_b64": request.image_b64,
                    "target": request.target  # ✅ 영역 지정
                }
            )
            
            if clip_res.status_code != 200:
                # Fallback: 기존 엔드포인트
                logger.warning("⚠️ Fashion CLIP endpoint failed, falling back to standard CLIP")
                clip_res = await client.post(
                    f"{AI_SERVICE_API_URL}/generate-clip-vector",
                    json={"image_b64": request.image_b64}
                )
            
            if clip_res.status_code != 200:
                raise HTTPException(status_code=500, detail="CLIP 벡터 생성 실패")
            
            clip_data = clip_res.json()
            clip_vector = clip_data.get("vector", [])
            
            if not clip_vector or len(clip_vector) != 512:
                raise HTTPException(status_code=500, detail="유효하지 않은 CLIP 벡터")
        
        logger.info(f"✅ CLIP vector generated: {len(clip_vector)} dims (target: {request.target})")
        
        # 2. CLIP 벡터로 상품 검색 (✅ 성별 필터 적용)
        results = await crud_product.search_by_clip_vector(
            db,
            clip_vector=clip_vector,
            limit=request.limit * 2 if request.negative_prompt else request.limit,  # ✅ 네거티브 필터링을 고려해 더 많이 가져옴
            filter_gender=target_gender  # ✅ 성별 필터 추가!
        )

        logger.info(f"✅ CLIP search found {len(results)} products (gender filter: {target_gender})")

        # ✅ 네거티브 프롬프트 필터링
        if request.negative_prompt:
            negative_keywords = extract_negative_keywords(request.negative_prompt)
            results = filter_products_by_negative(results, negative_keywords)
            results = results[:request.limit]  # 필터링 후 원래 limit으로 제한

        # 3. Response 구성
        product_responses = []
        for p in results:
            try:
                p_dict = {
                    "id": p.id,
                    "name": p.name or "Unnamed Product",
                    "description": p.description or "",
                    "price": float(p.price) if p.price else 0,
                    "stock_quantity": int(p.stock_quantity) if p.stock_quantity else 0,
                    "category": p.category or "Etc",
                    "image_url": p.image_url or "",
                    "gender": p.gender or "Unisex",
                    "is_active": p.is_active if p.is_active is not None else True,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "in_stock": (p.stock_quantity or 0) > 0
                }
                validated_product = ProductResponse.model_validate(p_dict)
                product_responses.append(validated_product)
            except ValidationError:
                continue
        
        return {
            "status": "SUCCESS",
            "search_type": "CLIP_IMAGE_SIMILARITY",
            "products": product_responses
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ CLIP search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-image")
async def analyze_image_proxy(request: ImageAnalysisRequest):
    """개별 이미지 분석 프록시 (후보 이미지 상세 분석)"""
    AI_SERVICE_API_URL = settings.AI_SERVICE_API_URL.rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # ✅ /analyze-image-detail 엔드포인트 호출 (JSON body 버전)
            target_url = f"{AI_SERVICE_API_URL}/analyze-image-detail"
            if "/api/v1" not in AI_SERVICE_API_URL:
                target_url = f"{AI_SERVICE_API_URL}/api/v1/analyze-image-detail"
            
            logger.info(f"📤 Calling AI Service: {target_url}")

            response = await client.post(
                target_url,
                json={"image_b64": request.image_b64, "query": request.query}
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ AI Service HTTP Error: {e.response.status_code} - {e.response.text}")
        raise HTTPException(status_code=502, detail=f"AI Service Error: {e.response.status_code}")
    except Exception as e:
        logger.error(f"❌ Analysis Proxy Failed: {e}")
        raise HTTPException(status_code=500, detail=f"AI Service Error: {str(e)}")


@router.post("/ai-search", response_model=Dict[str, Any])
async def ai_search(
    query: str = Form(..., description="사용자 검색 쿼리"),
    image_file: Optional[UploadFile] = File(None),
    limit: int = Form(12),
    negative_prompt: Optional[str] = Form(None, description="제외할 특징/스타일"),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    [Upgraded v2] 스마트 하이브리드 검색
    - 키워드 매칭 우선 (일반 검색)
    - ✅ EXTERNAL 경로: CLIP 이미지 벡터로 시각적 유사도 검색
    - 성별 필터 자동 적용
    """
    logger.info(f"🔍 AI Search Request: '{query}' (Image: {image_file is not None})")

    # 1. 의도 파악
    target_gender = detect_gender_intent(query)
    core_keyword = extract_core_keyword(query)
    is_celeb_search = is_celebrity_search(query)
    
    logger.info(f"📌 Gender: {target_gender}, Core Keyword: '{core_keyword}', Celebrity: {is_celeb_search}")

    # 2. 이미지 처리
    image_b64: Optional[str] = None
    if image_file:
        try:
            content = await image_file.read()
            image_b64 = base64.b64encode(content).decode("utf-8")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image file")

    # 3. AI Service 호출
    AI_SERVICE_API_URL = settings.AI_SERVICE_API_URL
    
    search_strategy = "SMART_HYBRID"
    search_path = "INTERNAL"
    ai_summary = "검색 결과입니다."
    ref_image_url = None
    candidates = []
    
    bert_vec: Optional[List[float]] = None
    clip_vec: Optional[List[float]] = None
    
    # ✅ 항상 determine-path 호출
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # 경로 결정 API 호출
                path_res = await client.post(
                    f"{AI_SERVICE_API_URL}/determine-path",
                    json={"query": query}
                )
                search_path = "INTERNAL"
                if path_res.status_code == 200:
                    search_path = path_res.json().get("path", "INTERNAL")
                
                logger.info(f"🛤️ Search Path Decision: {search_path}")
                
                # 경로에 따라 적절한 엔드포인트 호출
                endpoint = "/process-external" if search_path == 'EXTERNAL' else "/process-internal"
                payload = {"query": query, "image_b64": image_b64}
                
                ai_res = await client.post(f"{AI_SERVICE_API_URL}{endpoint}", json=payload)
                ai_res.raise_for_status()
                
                data = ai_res.json()
                
                # 벡터 추출
                if "vectors" in data:
                    bert_vec = data["vectors"].get("bert")
                    clip_vec = data["vectors"].get("clip")
                    logger.info(f"📊 Vectors received - BERT: {len(bert_vec) if bert_vec else 0}dim, CLIP: {len(clip_vec) if clip_vec else 0}dim")
                elif "vector" in data:
                    bert_vec = data["vector"]
                
                # AI 분석 결과 추출
                if "ai_analysis" in data and data["ai_analysis"]:
                    analysis = data["ai_analysis"]
                    ai_summary = analysis.get("summary") or ai_summary
                    ref_image_url = analysis.get("reference_image")
                    candidates = analysis.get("candidates", [])
                else:
                    ai_summary = data.get("description") or data.get("reason") or ai_summary
                    ref_image_url = data.get("ref_image")
                
                search_strategy = data.get("strategy", search_path).upper()
                
                # 외부 이미지 URL이면 프록시 처리
                if ref_image_url and ref_image_url.startswith("http"):
                    logger.info(f"🔄 Proxying reference image...")
                    proxy_image = await fetch_image_as_base64(ref_image_url)
                    if proxy_image:
                        ref_image_url = proxy_image
                
                break  # 성공 시 루프 탈출

        except Exception as e:
            logger.warning(f"⚠️ AI Service Retry ({attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                search_strategy = "KEYWORD_FALLBACK"
                logger.error(f"❌ AI Service failed after {max_retries} retries")
            await asyncio.sleep(1)

    # 4. 🌟 검색 실행 - 경로에 따라 다른 전략
    results = []
    
    try:
        # ✅ 핵심 수정: EXTERNAL 경로 (연예인 패션 등) → CLIP 이미지 벡터로 검색
        if search_path == "EXTERNAL" and clip_vec and len(clip_vec) == 512:
            logger.info(f"🖼️ Using CLIP image vector search (512-dim)")
            
            # CLIP 이미지 벡터로 시각적 유사도 검색
            results = await crud_product.search_by_clip_vector(
                db,
                clip_vector=clip_vec,
                limit=limit,
                filter_gender=target_gender
            )
            
            if results:
                search_strategy = "CLIP_VISUAL_SEARCH"
                logger.info(f"✅ CLIP search found {len(results)} products")
            else:
                # CLIP 검색 결과 없으면 BERT로 Fallback
                logger.info(f"⚠️ CLIP search empty, falling back to BERT")
                if bert_vec and len(bert_vec) == 768:
                    results = await crud_product.search_hybrid(
                        db,
                        bert_vector=bert_vec,
                        limit=limit,
                        filter_gender=target_gender
                    )
                    search_strategy = "BERT_FALLBACK"
        
        # INTERNAL 경로 또는 CLIP 벡터 없음 → 기존 스마트 하이브리드
        if not results:
            results = await crud_product.search_smart_hybrid(
                db,
                query=core_keyword,
                bert_vector=bert_vec,
                clip_vector=clip_vec,
                limit=limit,
                filter_gender=target_gender
            )
            
            # 결과 없으면 전체 쿼리로 재시도
            if not results:
                results = await crud_product.search_smart_hybrid(
                    db,
                    query=query,
                    bert_vector=bert_vec,
                    clip_vector=clip_vec,
                    limit=limit,
                    filter_gender=None
                )
                if results:
                    search_strategy = "RELAXED_SEARCH"
        
        # 그래도 없으면 최신 상품
        if not results:
            results = await crud_product.get_multi(db, limit=limit)
            search_strategy = "FALLBACK_LATEST"

    except Exception as e:
        logger.error(f"❌ DB Search Error: {e}")
        raise HTTPException(status_code=500, detail="Database Search Failed")

    # ✅ 네거티브 프롬프트 필터링
    if negative_prompt:
        negative_keywords = extract_negative_keywords(negative_prompt)
        logger.info(f"🚫 Applying negative filter: {negative_keywords}")
        results = filter_products_by_negative(results, negative_keywords)

    # 5. Response 구성
    product_responses = []
    for p in results:
        try:
            p_dict = {
                "id": p.id,
                "name": p.name or "Unnamed Product",
                "description": p.description or "",
                "price": float(p.price) if p.price else 0,
                "stock_quantity": int(p.stock_quantity) if p.stock_quantity else 0,
                "category": p.category or "Etc",
                "image_url": p.image_url or "",
                "gender": p.gender or "Unisex",
                "is_active": p.is_active if p.is_active is not None else True,
                "created_at": p.created_at,
                "updated_at": p.updated_at,
                "in_stock": (p.stock_quantity or 0) > 0
            }
            validated_product = ProductResponse.model_validate(p_dict)
            product_responses.append(validated_product)
        except ValidationError:
            continue

    logger.info(f"✅ Search Complete: {len(product_responses)} products found (Strategy: {search_strategy})")

    return {
        "status": "SUCCESS",
        "search_path": search_strategy,
        "ai_analysis": {
            "summary": ai_summary,
            "reference_image": ref_image_url,
            "candidates": candidates
        },
        "products": product_responses
    }


# ✅ [NEW] 무드 기반 검색 (향수/음악 → 패션)
@router.post("/mood-search", response_model=Dict[str, Any])
async def mood_search(
    query: str = Form(..., description="향수 노트 또는 음악 장르"),
    limit: int = Form(12),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    무드 기반 패션 검색
    - 향수 노트: "플로럴", "우디", "시트러스" 등
    - 음악 장르: "재즈", "힙합", "클래식" 등
    - 자동으로 어울리는 패션 스타일 추천
    """
    from src.utils.mood_mapper import extract_mood_keywords, build_mood_search_query

    logger.info(f"🎭 Mood Search Request: '{query}'")

    # 1. 무드 키워드 추출
    mood_data = extract_mood_keywords(query)

    if not mood_data.get("detected"):
        # 감지된 무드가 없으면 일반 검색으로 fallback
        logger.info(f"⚠️ No mood detected, falling back to regular search")
        return {
            "status": "NO_MOOD_DETECTED",
            "message": f"'{query}'에서 향수 노트나 음악 장르를 찾을 수 없습니다. 일반 검색을 시도하세요.",
            "products": []
        }

    logger.info(f"✅ Mood detected: {mood_data['detected']} ({mood_data['type']})")

    # 2. 무드 데이터로부터 검색 쿼리 생성
    search_query = build_mood_search_query(mood_data)
    negative_keywords_str = ", ".join(mood_data.get("negative", []))

    logger.info(f"🔍 Generated query: '{search_query}' (negative: '{negative_keywords_str}')")

    # 3. 데이터베이스 검색
    try:
        # 키워드 기반 하이브리드 검색
        results = await crud_product.search_smart_hybrid(
            db,
            query=search_query,
            limit=limit * 2 if negative_keywords_str else limit  # 네거티브 필터 고려
        )

        logger.info(f"✅ Found {len(results)} products")

        # 4. 네거티브 필터링
        if negative_keywords_str:
            negative_keywords = extract_negative_keywords(negative_keywords_str)
            results = filter_products_by_negative(results, negative_keywords)
            results = results[:limit]

        # 5. Response 구성
        product_responses = []
        for p in results:
            try:
                p_dict = {
                    "id": p.id,
                    "name": p.name or "Unnamed Product",
                    "description": p.description or "",
                    "price": float(p.price) if p.price else 0,
                    "stock_quantity": int(p.stock_quantity) if p.stock_quantity else 0,
                    "category": p.category or "Etc",
                    "image_url": p.image_url or "",
                    "gender": p.gender or "Unisex",
                    "is_active": p.is_active if p.is_active is not None else True,
                    "created_at": p.created_at,
                    "updated_at": p.updated_at,
                    "in_stock": (p.stock_quantity or 0) > 0
                }
                validated_product = ProductResponse.model_validate(p_dict)
                product_responses.append(validated_product)
            except ValidationError:
                continue

        # 6. 무드 설명 생성
        mood_description = f"{mood_data['detected']}의 {mood_data['mood']} 분위기에 어울리는 {mood_data['style']} 스타일입니다."

        return {
            "status": "SUCCESS",
            "mood_info": {
                "type": mood_data["type"],  # "perfume" or "music"
                "detected": mood_data["detected"],
                "style": mood_data["style"],
                "mood": mood_data["mood"],
                "colors": mood_data["colors"],
                "description": mood_description
            },
            "products": product_responses
        }

    except Exception as e:
        logger.error(f"❌ Mood search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))