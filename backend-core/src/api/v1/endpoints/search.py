import logging
import base64
import asyncio
import re
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
import httpx
from pydantic import BaseModel, ValidationError 

from src.api import deps
from src.crud.crud_product import crud_product
from src.schemas.product import ProductResponse
from src.config.settings import settings
from src.constants import ProductCategory

logger = logging.getLogger(__name__)
router = APIRouter()

# ------------------------------------------------------------------
# DTO Definitions
# ------------------------------------------------------------------

class ImageAnalysisRequest(BaseModel):
    image_b64: str
    query: str

class ClipSearchRequest(BaseModel):
    image_b64: str
    limit: int = 12
    query: Optional[str] = None  # 원본 검색어 (성별 추출용)
    target: str = "full"  # "full", "upper", "lower"

# ------------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------------

def detect_gender_intent(query: str) -> Optional[str]:
    """검색어에서 성별 키워드 추출"""
    if not query:
        return None
    q = query.lower()
    if any(x in q for x in ["남자", "남성", "맨", "men", "male", "boy"]):
        return "Male"
    elif any(x in q for x in ["여자", "여성", "우먼", "women", "female", "girl"]):
        return "Female"
    return None

def extract_core_keyword(query: str) -> str:
    """검색어에서 핵심 상품 키워드 추출 (성별/수식어 제거)"""
    if not query:
        return ""
        
    # 제거할 단어들
    remove_words = [
        "남자", "여자", "남성", "여성", "남성용", "여성용",
        "추천", "해줘", "보여줘", "찾아줘", "알려줘",
        "스타일", "패션", "의류", "용"
    ]
    # "옷"은 제거하지 않음 - 검색어로 유의미함
    
    result = query
    for word in remove_words:
        result = result.replace(word, "")
    
    # 조사 제거 (은/는/이/가 등)
    result = re.sub(r'(은|는|이|가|을|를|의|에|로)$', '', result.strip())
    
    return result.strip() if result.strip() else query

def is_celebrity_search(query: str) -> bool:
    """연예인/인물 검색인지 판단"""
    if not query:
        return False
        
    # 패션 관련 키워드와 함께 사용된 경우
    fashion_keywords = ["패션", "스타일", "코디", "룩", "공항", "착장", "의상", "옷"]
    
    # 한글 이름 패턴 (2-4글자)
    korean_name = re.search(r'[가-힣]{2,4}', query)
    
    if korean_name and any(k in query for k in fashion_keywords):
        return True
    
    return False

# ✅ [FIX] S3 URL 등 외부 이미지 다운로드 강화
async def fetch_image_as_base64(url: str) -> Optional[str]:
    """외부 이미지(S3 포함) 프록시 다운로드 -> Base64 변환"""
    if not url:
        return None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            # S3 접근 시 Referer가 필요 없는 경우가 많지만 안전하게 Google로 설정
            "Referer": "https://www.google.com/"
        }
        async with httpx.AsyncClient(timeout=10.0, verify=False) as client:
            response = await client.get(url, headers=headers)
            if response.status_code == 200:
                b64_data = base64.b64encode(response.content).decode('utf-8')
                content_type = response.headers.get("content-type", "image/jpeg")
                return f"data:{content_type};base64,{b64_data}"
            else:
                logger.warning(f"⚠️ Image Download Failed ({response.status_code}): {url}")
    except Exception as e:
        logger.warning(f"⚠️ Failed to proxy image ({url}): {e}")
    return None

def filter_by_negative_prompt(products: List[Any], negative_prompt: Optional[str]) -> List[Any]:
    """네거티브 프롬프트로 상품 필터링"""
    if not negative_prompt or not negative_prompt.strip():
        return products

    # 네거티브 키워드 파싱 (쉼표로 구분, 공백 제거, 소문자 변환)
    negative_keywords = [
        kw.strip().lower()
        for kw in negative_prompt.split(',')
        if kw.strip()
    ]

    if not negative_keywords:
        return products

    logger.info(f"🚫 Negative keywords: {negative_keywords}")

    # 필터링 로직
    filtered_products = []
    for product in products:
        # 상품 텍스트 결합 (이름, 설명, 카테고리)
        searchable_text = " ".join([
            (product.name or "").lower(),
            (product.description or "").lower(),
            (product.category or "").lower()
        ])

        # 네거티브 키워드가 하나라도 포함되면 제외
        if any(keyword in searchable_text for keyword in negative_keywords):
            logger.debug(f"🚫 Filtered out: {product.name} (matched negative keyword)")
            continue

        filtered_products.append(product)

    logger.info(f"✅ Negative filtering: {len(products)} → {len(filtered_products)} products")
    return filtered_products


def map_product_to_response(product) -> Optional[ProductResponse]:
    """Product 객체를 ProductResponse로 변환 (similarity 포함)"""
    try:
        p_dict = {
            "id": product.id,
            "name": product.name or "Unnamed Product",
            "description": product.description or "",
            "price": float(product.price) if product.price else 0,
            "stock_quantity": int(product.stock_quantity) if product.stock_quantity else 0,
            "category": product.category or "Etc",
            "image_url": product.image_url or "",
            "gender": product.gender or "Unisex",
            "is_active": product.is_active if product.is_active is not None else True,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "in_stock": (product.stock_quantity or 0) > 0,
            "similarity": getattr(product, 'similarity', None)
        }
        return ProductResponse.model_validate(p_dict)
    except ValidationError as e:
        logger.warning(f"⚠️ Product validation error: {e}")
        return None


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.post("/search-by-clip")
async def search_by_clip_image(
    request: ClipSearchRequest,
    db: AsyncSession = Depends(deps.get_db),
):
    """
    이미지 기반 상품 검색 (CLIP Vector)
    """
    logger.info(f"🖼️ CLIP Image Search Request (limit: {request.limit}, query: {request.query}, target: {request.target})")
    
    # 1. 원본 쿼리에서 성별 추출
    target_gender = None
    if request.query:
        target_gender = detect_gender_intent(request.query)
        logger.info(f"📌 Detected gender from query: {target_gender}")

    target_categories = None
    if request.target == "upper":
        target_categories = [
            ProductCategory.TOPS.value, 
            ProductCategory.OUTERWEAR.value, 
            ProductCategory.DRESSES.value
        ]
    elif request.target == "lower":
        target_categories = [ProductCategory.BOTTOMS.value] 
    
    # ✅ [FIX] URL 보정 로직 (SAFE_AI_URL 사용)
    # settings.py가 환경변수를 잘못 읽더라도, 코드는 무조건 127.0.0.1을 바라봅니다.
    AI_SERVICE_API_URL = "http://127.0.0.1:8001/api/v1"
    
    try:
        # 2. AI 서비스에서 CLIP 벡터 생성
        async with httpx.AsyncClient(timeout=30.0) as client:
            clip_res = await client.post(
                f"{AI_SERVICE_API_URL}/generate-fashion-clip-vector",
                json={
                    "image_b64": request.image_b64,
                    "target": request.target
                }
            )
            
            if clip_res.status_code != 200:
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
        
        # 3. CLIP 벡터로 상품 검색
        results = await crud_product.search_by_clip_vector(
            db,
            clip_vector=clip_vector,
            limit=request.limit,
            filter_gender=target_gender,
            target=request.target,
            include_category=target_categories
        )
        
        logger.info(f"✅ CLIP search found {len(results)} products (gender filter: {target_gender})")
        
        # 4. Response 구성
        product_responses = []
        for p in results:
            response = map_product_to_response(p)
            if response:
                product_responses.append(response)
        
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
    
    AI_SERVICE_API_URL = "http://127.0.0.1:8001/api/v1"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            target_url = f"{AI_SERVICE_API_URL}/analyze-image-detail"
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
    negative_prompt: Optional[str] = Form(None, description="제외할 키워드 (쉼표로 구분)"),
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    """
    [Upgraded v3] 스마트 하이브리드 검색
    """
    logger.info(f"🔍 AI Search Request: '{query}' (Image: {image_file is not None}, Negative: {negative_prompt})")

    # 1. 의도 및 정보 추출
    target_gender = detect_gender_intent(query)
    core_keyword = extract_core_keyword(query)
    is_celeb_search = is_celebrity_search(query)
    
    logger.info(f"📌 Gender: {target_gender}, Core Keyword: '{core_keyword}', Celebrity: {is_celeb_search}")

    # 2. 업로드 이미지 처리 (Base64 변환)
    image_b64: Optional[str] = None
    if image_file:
        try:
            content = await image_file.read()
            image_b64 = base64.b64encode(content).decode("utf-8")
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid image file")

    # 3. AI Service 호출 (경로 판단 및 벡터 생성)
    AI_SERVICE_API_URL = "http://127.0.0.1:8001/api/v1"
    
    search_strategy = "SMART_HYBRID"
    search_path = "INTERNAL"
    ai_summary = "검색 결과입니다."
    ref_image_url = None
    candidates = []
    
    bert_vec: Optional[List[float]] = None
    clip_vec: Optional[List[float]] = None
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                # 3-1. 경로 결정 API 호출
                path_res = await client.post(
                    f"{AI_SERVICE_API_URL}/determine-path",
                    json={"query": query}
                )
                
                search_path = "INTERNAL"
                if path_res.status_code == 200:
                    search_path = path_res.json().get("path", "INTERNAL")
                
                logger.info(f"🛤️ Search Path Decision: {search_path}")
                
                # 3-2. 경로에 따른 상세 처리 호출
                endpoint = "/process-external" if search_path == 'EXTERNAL' else "/process-internal"
                
                target_ai_url = f"{AI_SERVICE_API_URL}{endpoint}"
                
                payload = {"query": query, "image_b64": image_b64}
                ai_res = await client.post(target_ai_url, json=payload)
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
                
                # ✅ [FIX] S3/외부 이미지 URL이면 Base64로 미리 변환
                if ref_image_url and ref_image_url.startswith("http"):
                    logger.info(f"🔄 Proxying reference image: {ref_image_url}")
                    proxy_image = await fetch_image_as_base64(ref_image_url)
                    if proxy_image:
                        ref_image_url = proxy_image
                
                break # 성공 시 재시도 루프 탈출

        except Exception as e:
            logger.warning(f"⚠️ AI Service Retry ({attempt+1}/{max_retries}): {e}")
            if attempt == max_retries - 1:
                search_strategy = "KEYWORD_FALLBACK"
                logger.error(f"❌ AI Service failed after {max_retries} retries")
            await asyncio.sleep(1)

    # 4. 🌟 검색 실행 - DB 조회
    results = []
    gender_filtered = True # 성별 필터 적용 여부 추적

    # 네거티브 프롬프트가 있으면 더 많은 후보 검색
    search_limit = limit * 2 if negative_prompt else limit

    try:
        # Case A: EXTERNAL 경로이면서 CLIP 벡터가 있는 경우
        if search_path == "EXTERNAL" and clip_vec and len(clip_vec) == 512:
            logger.info(f"🖼️ Using CLIP image vector search (512-dim)")

            results = await crud_product.search_by_clip_vector(
                db,
                clip_vector=clip_vec,
                limit=search_limit,
                filter_gender=target_gender
            )
            
            if results:
                search_strategy = "CLIP_VISUAL_SEARCH"
                logger.info(f"✅ CLIP search found {len(results)} products")
            else:
                logger.info(f"⚠️ CLIP search empty, falling back to BERT")
                if bert_vec and len(bert_vec) == 768:
                    results = await crud_product.search_hybrid(
                        db,
                        bert_vector=bert_vec,
                        limit=search_limit,
                        filter_gender=target_gender
                    )
                    search_strategy = "BERT_FALLBACK"

        # Case B: INTERNAL 경로 또는 벡터 검색 실패 시 -> 스마트 하이브리드
        if not results:
            results = await crud_product.search_smart_hybrid(
                db,
                query=core_keyword,
                bert_vector=bert_vec,
                clip_vector=clip_vec,
                limit=search_limit,
                filter_gender=target_gender
            )
            
            # 결과 없으면 성별 필터를 완화
            if not results:
                logger.info(f"⚠️ No results with gender filter '{target_gender}', trying relaxed search")
                results = await crud_product.search_smart_hybrid(
                    db,
                    query=query,
                    bert_vector=bert_vec,
                    clip_vector=clip_vec,
                    limit=search_limit,
                    filter_gender=None
                )
                if results:
                    search_strategy = "RELAXED_SEARCH"
                    gender_filtered = False
                    logger.info(f"⚠️ Relaxed search found {len(results)} products (gender filter removed)")

        # Case C: 최후의 수단 (최신 상품)
        if not results:
            results = await crud_product.get_multi(db, limit=search_limit)
            search_strategy = "FALLBACK_LATEST"
            gender_filtered = False

    except Exception as e:
        logger.error(f"❌ DB Search Error: {e}")
        raise HTTPException(status_code=500, detail="Database Search Failed")

    # 5. 네거티브 프롬프트 필터링
    filtered_count = 0
    if negative_prompt and results:
        original_count = len(results)
        results = filter_by_negative_prompt(results, negative_prompt)
        filtered_count = original_count - len(results)
        logger.info(f"🚫 Negative filtering removed {filtered_count} products")

    # 6. 최종 결과 자르기
    results = results[:limit]

    # 7. Response 매핑
    product_responses = []
    for p in results:
        response = map_product_to_response(p)
        if response:
            product_responses.append(response)

    logger.info(f"✅ Search Complete: {len(product_responses)} products found (Strategy: {search_strategy})")

    return {
        "status": "SUCCESS",
        "search_path": search_strategy,
        "gender_filter_applied": gender_filtered,
        "detected_gender": target_gender,
        "negative_prompt_applied": negative_prompt is not None and negative_prompt.strip() != "",
        "filtered_count": filtered_count,
        "ai_analysis": {
            "summary": ai_summary,
            "reference_image": ref_image_url,
            "candidates": candidates
        },
        "products": product_responses
    }