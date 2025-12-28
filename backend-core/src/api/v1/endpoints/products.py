import logging
import csv
import io
import shutil
import os
import uuid
import boto3  # ✅ AWS S3 연동
from botocore.exceptions import NoCredentialsError # ✅ AWS 에러 처리
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

# 의존성 및 모듈 임포트
from src.api import deps
from src.crud.crud_product import crud_product
from src.config.settings import settings
from src.schemas.user import UserResponse as User
from src.schemas.product import (
    ProductResponse, 
    ProductCreate, 
    CoordinationResponse, 
    LLMQueryBody
)

from sqlalchemy import select as sql_select, func as sql_func, desc as sql_desc, case as sql_case
from src.models.product import Product

logger = logging.getLogger(__name__)
router = APIRouter()

# 🚨 [CRITICAL FIX] ECS 환경에서 DNS 이슈 방지를 위한 강제 로컬호스트 주소
SAFE_AI_URL = "http://127.0.0.1:8001/api/v1"

# ✅ [AWS S3 설정]
AWS_S3_BUCKET_NAME = "modify-frontend-final-ai4"
AWS_REGION = "ap-northeast-2"

# ------------------------------------------------------------------
# [Helper] 문자열 정리
# ------------------------------------------------------------------
def sanitize_string(value: Any) -> Any:
    if isinstance(value, str):
        return value.replace("\x00", "").strip()
    return value

# ------------------------------------------------------------------
# [Helper] Self-Healing
# ------------------------------------------------------------------
async def _heal_product_embedding(db: AsyncSession, product: Any) -> Any:
    """상품 데이터(임베딩, 설명) 누락 시 AI 서비스로 복구"""
    
    is_broken = (
        product.embedding is None or 
        (isinstance(product.embedding, list) and len(product.embedding) == 0) or
        product.description == "AI 분석 실패" or 
        not product.description
    )
    
    if not is_broken:
        return product 

    logger.warning(f"🚑 [Self-Healing] Product ID {product.id} data missing. Attempting recovery...")

    new_description = product.description
    # 1. 텍스트 생성 복구
    if not product.description or product.description == "AI 분석 실패":
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                prompt = f"상품명: {product.name}, 카테고리: {product.category}. 매력적인 쇼핑몰 상세 설명을 5문장 작성해줘."
                res = await client.post(f"{SAFE_AI_URL}/llm-generate-response", json={"prompt": prompt})
                if res.status_code == 200:
                    new_description = res.json().get("answer", product.name)
        except Exception as e:
            logger.error(f"Heal Description Failed: {e}")

    # 2. 임베딩 복구
    new_vector = product.embedding
    try:
        text_to_embed = f"{product.name} {product.category} {new_description}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post(f"{SAFE_AI_URL}/embed-text", json={"text": text_to_embed})
            if res.status_code == 200:
                new_vector = res.json().get("vector", [])
    except Exception as e:
        logger.error(f"Heal Embedding Failed: {e}")

    # 3. DB 업데이트
    if new_vector and len(new_vector) > 0:
        update_data = {"embedding": new_vector}
        if new_description != product.description:
            update_data["description"] = new_description
            
        product = await crud_product.update(db, db_obj=product, obj_in=update_data)
        logger.info(f"✅ Product {product.id} healed.")
    
    return product


# =========================================================
# 1️⃣ [API] 이미지 자동 분석 업로드 (S3 버전) - 수정 완료 ✅
# =========================================================
@router.post("/upload/image-auto", response_model=ProductResponse)
async def upload_product_image_auto(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    ai_analyzed_data = {}
    logger.info(f"Processing Image Upload (S3): {file.filename}")

    # 1. 파일 내용 읽기 (메모리에 로드)
    await file.seek(0)
    file_content = await file.read()
    
    # [Step A] AI 서비스로 이미지 전송 (분석용)
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            files = {"file": (file.filename, file_content, file.content_type)}
            response = await client.post(
                f"{SAFE_AI_URL}/analyze-image",
                files=files 
            )
            if response.status_code == 200:
                ai_analyzed_data = response.json()
            else:
                logger.error(f"AI Service Error ({response.status_code}): {response.text}")
        except Exception as e:
            logger.error(f"AI Connection Error: {e}")

    # ----------------------------------------------------------------
    # ✅ [Step B] AWS S3 업로드 (핵심 변경 사항)
    # ----------------------------------------------------------------
    final_image_url = ""
    try:
        # 1. S3 클라이언트 생성
        s3_client = boto3.client(
            's3',
            aws_access_key_id=getattr(settings, 'AWS_ACCESS_KEY_ID', None),
            aws_secret_access_key=getattr(settings, 'AWS_SECRET_ACCESS_KEY', None),
            region_name=AWS_REGION
        )

        # 2. 파일명 난수화
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # 3. S3 저장 경로 (static/images/파일명)
        s3_key = f"static/images/{unique_filename}"

        # 4. 업로드 실행 (메모리 -> S3)
        s3_client.upload_fileobj(
            io.BytesIO(file_content),
            AWS_S3_BUCKET_NAME,
            s3_key,
            ExtraArgs={
                "ContentType": file.content_type
            }
        )

        # 5. S3 URL 생성 (DB 저장용)
        final_image_url = f"https://{AWS_S3_BUCKET_NAME}.s3.{AWS_REGION}.amazonaws.com/{s3_key}"
        logger.info(f"✅ S3 Upload Success: {final_image_url}")

    except NoCredentialsError:
        logger.error("AWS 자격 증명이 없습니다.")
        raise HTTPException(status_code=500, detail="AWS S3 자격 증명 오류")
    except Exception as e:
        logger.error(f"S3 Upload Error: {str(e)}")
        # 실패 시에도 서버가 죽지 않도록 플레이스홀더 처리
        final_image_url = "https://placehold.co/600x400?text=Upload+Failed"

    # [Step C] 데이터 파싱
    raw_name = ai_analyzed_data.get("name")
    final_name = str(raw_name).strip() if (raw_name and len(str(raw_name).strip()) >= 2) else f"상품 {file.filename}"
    
    raw_desc = ai_analyzed_data.get("description")
    final_desc = str(raw_desc).strip() if raw_desc else "AI 분석 중... 상세 내용을 수정해주세요."
    final_gender = ai_analyzed_data.get("gender", "Unisex")

    try:
        final_price = int(ai_analyzed_data.get("price", 0))
    except:
        final_price = 0

    # 벡터 처리
    vector = ai_analyzed_data.get("vector", [])
    if not vector or len(vector) != 768:
        vector = None
    vector_clip = ai_analyzed_data.get("vector_clip", [])
    if not vector_clip or len(vector_clip) != 512:
        vector_clip = None

    # [Step D] DB 저장
    product_in_data = {
        "name": sanitize_string(final_name),
        "category": sanitize_string(ai_analyzed_data.get("category", "Uncategorized")),
        "description": sanitize_string(final_desc),
        "price": final_price,
        "stock_quantity": 100,
        "image_url": final_image_url, # ✅ S3 URL 저장
        "embedding": vector,
        "embedding_clip": vector_clip,
        "gender": final_gender,
        "is_active": True
    }

    try:
        new_product = await crud_product.create(db, obj_in=product_in_data)
        if vector is None:
            new_product = await _heal_product_embedding(db, new_product)
        return new_product
    except Exception as e:
        logger.error(f"DB Insert Error: {e}")
        raise HTTPException(status_code=500, detail=f"DB 저장 실패: {str(e)}")


# =========================================================
# 2️⃣ [Mode 2] CSV 대량 업로드
# =========================================================
@router.post("/upload/csv")
async def upload_products_csv(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    content = await file.read()
    try:
        decoded_content = content.decode("utf-8")
    except UnicodeDecodeError:
        try:
            decoded_content = content.decode("cp949")
        except UnicodeDecodeError:
            decoded_content = content.decode("euc-kr", errors="ignore")

    csv_reader = csv.DictReader(io.StringIO(decoded_content))
    results = {"success": 0, "failed": 0, "errors": []}
    AI_SERVICE_API_URL = SAFE_AI_URL

    for row in csv_reader:
        try:
            name = row.get("name") or row.get("상품명")
            if not name: continue 

            category = row.get("category") or row.get("카테고리") or "Uncategorized"
            description = row.get("description") or row.get("설명") or ""
            gender = row.get("gender") or row.get("성별") or "Unisex"
            
            price_raw = row.get("price") or row.get("가격") or "0"
            try:
                price = int(str(price_raw).replace(",", "").strip())
            except:
                price = 0

            stock_raw = row.get("stock_quantity") or row.get("재고") or "100"
            try:
                stock = int(str(stock_raw).replace(",", "").strip())
            except:
                stock = 100
            
            image_url = row.get("image_url") or row.get("이미지") or "https://placehold.co/400x500?text=No+Image"

            # BERT 벡터
            vector = None 
            text_for_vector = f"[{gender}] {name} {category} {description}"
            async with httpx.AsyncClient(timeout=3.0) as client:
                try:
                    res = await client.post(f"{AI_SERVICE_API_URL}/embed-text", json={"text": text_for_vector})
                    if res.status_code == 200:
                        v_data = res.json().get("vector", [])
                        if v_data and len(v_data) == 768:
                            vector = v_data
                except: pass 

            # CLIP 벡터
            vector_clip = None
            if image_url and not image_url.startswith("https://placehold"):
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        img_response = await client.get(image_url)
                        if img_response.status_code == 200:
                            import base64
                            image_b64 = base64.b64encode(img_response.content).decode("utf-8")
                            clip_res = await client.post(f"{AI_SERVICE_API_URL}/generate-clip-vector", json={"image_b64": image_b64})
                            if clip_res.status_code == 200:
                                v_clip_data = clip_res.json().get("vector", [])
                                if v_clip_data and len(v_clip_data) == 512:
                                    vector_clip = v_clip_data
                except Exception as e:
                    logger.warning(f"⚠️ CLIP vector generation failed for {name}: {e}")

            product_in = {
                "name": sanitize_string(name),
                "category": sanitize_string(category),
                "description": sanitize_string(description),
                "price": price,
                "stock_quantity": stock,
                "image_url": image_url,
                "embedding": vector,              
                "embedding_clip": vector_clip,    
                "gender": gender,
                "is_active": True
            }
            
            await crud_product.create(db, obj_in=product_in)
            results["success"] += 1

        except Exception as e:
            results["failed"] += 1
            results["errors"].append(f"{name}: {str(e)}")

    return results

# =========================================================
# 3️⃣ 일반 API (CRUD, Recommendation, LLM Query)
# =========================================================

@router.post("/", response_model=ProductResponse)
async def create_product(
    *,
    db: AsyncSession = Depends(deps.get_db),
    product_in: ProductCreate,
    current_user: User = Depends(deps.get_current_user),
) -> Any:
    """단일 상품 직접 생성"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    product_data = product_in.model_dump()
    for key, value in product_data.items():
        product_data[key] = sanitize_string(value)

    # BERT 임베딩 생성
    embedding_vector = None
    text_to_embed = f"상품명: {product_data['name']} | 카테고리: {product_data.get('category', '')} | 설명: {product_data.get('description', '')}"
    
    # SAFE_AI_URL 사용
    AI_SERVICE_API_URL = SAFE_AI_URL

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{AI_SERVICE_API_URL}/embed-text",
                json={"text": text_to_embed}
            )
            if response.status_code == 200:
                v_data = response.json().get("vector", [])
                if v_data and len(v_data) == 768:
                    embedding_vector = v_data
    except Exception as e:
        logger.error(f"❌ Failed to generate BERT embedding: {e}")

    product_data["embedding"] = embedding_vector

    product = await crud_product.create(db, obj_in=product_data)
    return product

# =========================================================
# 관리자용 상품 관리 API
# =========================================================

@router.get("/admin/list", response_model=dict)
async def get_products_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    is_active: Optional[bool] = Query(None, description="활성화 상태 필터"),
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """관리자용 상품 목록 조회"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    offset = (page - 1) * limit

    # 전체 상품 수 조회
    count_query = sql_select(sql_func.count(Product.id)).where(Product.deleted_at == None)
    if category:
        count_query = count_query.where(Product.category == category)
    if is_active is not None:
        count_query = count_query.where(Product.is_active == is_active)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 상품 목록 조회
    query = sql_select(Product).where(Product.deleted_at == None)
    if category:
        query = query.where(Product.category == category)
    if is_active is not None:
        query = query.where(Product.is_active == is_active)
    query = query.order_by(sql_desc(Product.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    products = result.scalars().all()

    # 통계 계산 (삭제되지 않은 상품 기준)
    stats_query = sql_select(
        sql_func.count(Product.id).label('total'),
        sql_func.sum(sql_case((Product.stock_quantity > 0, 1), else_=0)).label('selling'),
        sql_func.sum(sql_case((Product.stock_quantity == 0, 1), else_=0)).label('soldout'),
        sql_func.avg(Product.price).label('avg_price')
    ).where(Product.deleted_at == None)
    stats_result = await db.execute(stats_query)
    stats_row = stats_result.one()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "products": [ProductResponse.model_validate(p) for p in products],
        "stats": {
            "total": stats_row.total or 0,
            "selling": stats_row.selling or 0,
            "soldout": stats_row.soldout or 0,
            "avg_price": int(stats_row.avg_price) if stats_row.avg_price else 0
        }
    }


@router.patch("/admin/{product_id}", response_model=ProductResponse)
async def update_product_admin(
    product_id: int,
    product_data: ProductCreate,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """관리자용 상품 정보 업데이트"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    product = await crud_product.get(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    updated_product = await crud_product.update(db, db_obj=product, obj_in=product_data.model_dump(exclude_unset=True))
    return ProductResponse.model_validate(updated_product)


@router.delete("/admin/{product_id}")
async def delete_product_admin(
    product_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """관리자용 상품 삭제 (소프트 삭제)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    product = await crud_product.get(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    # 소프트 삭제
    from datetime import datetime
    product.deleted_at = datetime.now()
    await db.commit()

    return {"message": "상품이 삭제되었습니다.", "product_id": product_id}

# =========================================================
# 일반 상품 조회 및 AI 기능
# =========================================================

@router.get("/", response_model=dict)
async def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(12, ge=1, le=100),
    category: Optional[str] = Query(None, description="카테고리 필터"),
    search: Optional[str] = Query(None, description="상품명 검색"),
    db: AsyncSession = Depends(deps.get_db),
):
    """일반 사용자용 상품 목록 조회 (활성화된 상품만)"""
    offset = (page - 1) * limit

    # 전체 상품 수 조회 (활성화된 상품만)
    count_query = sql_select(sql_func.count(Product.id)).where(
        Product.deleted_at == None,
        Product.is_active == True
    )
    if category:
        count_query = count_query.where(Product.category == category)
    if search:
        count_query = count_query.where(Product.name.ilike(f"%{search}%"))

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 상품 목록 조회 (활성화된 상품만)
    query = sql_select(Product).where(
        Product.deleted_at == None,
        Product.is_active == True
    )
    if category:
        query = query.where(Product.category == category)
    if search:
        query = query.where(Product.name.ilike(f"%{search}%"))
    query = query.order_by(sql_desc(Product.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    products = result.scalars().all()

    # 통계 계산 (활성화된 상품 기준)
    stats_query = sql_select(
        sql_func.count(Product.id).label('total'),
        sql_func.sum(sql_case((Product.stock_quantity > 0, 1), else_=0)).label('selling'),
        sql_func.sum(sql_case((Product.stock_quantity == 0, 1), else_=0)).label('soldout'),
        sql_func.avg(Product.price).label('avg_price')
    ).where(
        Product.deleted_at == None,
        Product.is_active == True
    )
    stats_result = await db.execute(stats_query)
    stats_row = stats_result.one()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "products": [ProductResponse.model_validate(p) for p in products],
        "stats": {
            "total": stats_row.total or 0,
            "selling": stats_row.selling or 0,
            "soldout": stats_row.soldout or 0,
            "avg_price": int(stats_row.avg_price) if stats_row.avg_price else 0
        }
    }


@router.get("/{product_id}", response_model=ProductResponse)
async def read_product(
    product_id: int,
    db: AsyncSession = Depends(deps.get_db),
) -> Any:
    product = await crud_product.get(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product = await _heal_product_embedding(db, product)
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: int,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """상품 삭제 (관리자 전용 - 소프트 삭제)"""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")

    product = await crud_product.get(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")

    # 소프트 삭제
    product.deleted_at = datetime.now()
    await db.commit()

    return {"message": "상품이 삭제되었습니다.", "product_id": product_id}


@router.post("/{product_id}/llm-query", response_model=Dict[str, str])
async def llm_query_product(
    product_id: int,
    query_body: LLMQueryBody,
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> Dict[str, str]:
    product = await crud_product.get(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product = await _heal_product_embedding(db, product)

    context = (
        f"상품명: {product.name}, 카테고리: {product.category}, 가격: {product.price}원, "
        f"설명: {product.description}, 성별: {product.gender}"
    )
    prompt = (
        f"사용자 질문: {query_body.question}\n"
        f"다음 상품 정보를 바탕으로 쇼핑몰 전문가처럼 친절하게 답변하세요.\n정보: {context}"
    )
    
    # SAFE_AI_URL 사용
    AI_SERVICE_API_URL = SAFE_AI_URL

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            ai_response = await client.post(
                f"{AI_SERVICE_API_URL}/llm-generate-response", 
                json={"prompt": prompt}
            )
            ai_response.raise_for_status()
            ai_data = ai_response.json()
            return {"answer": ai_data.get("answer", "답변을 생성하지 못했습니다.")}
        except Exception as e:
            logger.error(f"LLM Query failed: {e}")
            raise HTTPException(status_code=503, detail="AI 서비스 통신 오류")

# --- AI Coordination ---
@router.get("/ai-coordination/{product_id}", response_model=CoordinationResponse)
async def get_ai_coordination_products(
    product_id: int, 
    db: AsyncSession = Depends(deps.get_db),
    current_user: Any = Depends(deps.get_current_user),
) -> CoordinationResponse:
    
    product = await crud_product.get(db, product_id=product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    product = await _heal_product_embedding(db, product)
    
    
    has_embedding = (
        product.embedding is not None and 
        hasattr(product.embedding, '__len__') and 
        len(product.embedding) > 0
    )
    
    if not has_embedding:
        raise HTTPException(status_code=503, detail="AI Service is currently unavailable to analyze this product.")
    
    coordination_prompt = (
        f"상품명 '{product.name}', 성별 '{product.gender}', 카테고리 '{product.category}'의 코디에 적합한 "
        f"다른 카테고리(예: 상의면 하의)의 검색 키워드 3개를 한국어로 쉼표로 구분해줘."
    )
    
    # SAFE_AI_URL 사용
    AI_SERVICE_API_URL = SAFE_AI_URL
    coordination_keywords = ["추천", "베이직", "데일리"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            llm_res = await client.post(
                f"{AI_SERVICE_API_URL}/llm-generate-response", 
                json={"prompt": coordination_prompt}
            )
            if llm_res.status_code == 200:
                data = llm_res.json()
                answer_text = data.get("answer", "")
                extracted = [k.strip() for k in answer_text.split(',') if k.strip()]
                if extracted:
                    coordination_keywords = extracted
        except Exception as e:
            logger.error(f"LLM Keyword Generation failed: {e}")

    embedding_text = f"{product.name} 코디 {' '.join(coordination_keywords)}"
    coordination_vector = list(product.embedding) if product.embedding is not None else []
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            vector_res = await client.post(
                f"{AI_SERVICE_API_URL}/embed-text", 
                json={"text": embedding_text}
            )
            if vector_res.status_code == 200:
                coordination_vector = vector_res.json().get("vector", coordination_vector)
        except Exception as e:
            logger.error(f"Embedding API failed: {e}")

    coordination_products = await crud_product.search_by_vector(
        db, 
        query_vector=coordination_vector, 
        limit=5, 
        exclude_category=[product.category]
    )

    coordination_reason = (
        f"'{product.name}'와(과) 완벽한 매치를 보여주는 아이템들입니다.\n"
        f"AI 추천 키워드: #{', #'.join(coordination_keywords[:3])}"
    )

    return CoordinationResponse(
        answer=coordination_reason,
        products=[ProductResponse.model_validate(p) for p in coordination_products]
    )

# --- Related Recommendations ---

@router.get("/related-price/{product_id}", response_model=CoordinationResponse)
async def get_related_by_price(
    product_id: int, 
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> CoordinationResponse:
    product = await crud_product.get(db, product_id=product_id)
    product = await _heal_product_embedding(db, product) 
    
    if not product or not product.embedding:
        raise HTTPException(status_code=404, detail="AI Analysis Required")
    
    price_range = product.price * 0.15
    min_p = max(0, int(product.price - price_range))
    max_p = int(product.price + price_range)

    related_products = await crud_product.search_by_vector(
        db, 
        query_vector=product.embedding,
        limit=5,
        min_price=min_p,
        max_price=max_p,
        exclude_id=[product.id]
    )

    reason = (
        f"가격대({min_p:,}원 ~ {max_p:,}원)가 비슷한 상품 중에서, "
        f"'{product.name}'와 스타일이 가장 유사한 상품들을 추천합니다."
    )

    return CoordinationResponse(
        answer=reason,
        products=[ProductResponse.model_validate(p) for p in related_products]
    )

@router.get("/related-color/{product_id}", response_model=CoordinationResponse)
async def get_related_by_color(
    product_id: int, 
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> CoordinationResponse:
    product = await crud_product.get(db, product_id=product_id)
    product = await _heal_product_embedding(db, product)
    
    if not product or not product.embedding:
        raise HTTPException(status_code=404, detail="AI Analysis Required")
    
    color_prompt = f"상품 '{product.name}'의 설명에서 가장 지배적인 색상 키워드 1개만 (예: 블랙, 네이비) 답변하시오."
    
    # SAFE_AI_URL 사용
    AI_SERVICE_API_URL = SAFE_AI_URL
    target_color = "유사색상"
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            llm_res = await client.post(
                f"{AI_SERVICE_API_URL}/llm-generate-response", 
                json={"prompt": color_prompt}
            )
            if llm_res.status_code == 200:
                target_color = llm_res.json().get("answer", "유사색상")
        except Exception:
            pass

    embedding_text = f"{product.name} 디자인 {target_color} 색상"
    color_vector = product.embedding 
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            vector_res = await client.post(
                f"{AI_SERVICE_API_URL}/embed-text", 
                json={"text": embedding_text}
            )
            if vector_res.status_code == 200:
                color_vector = vector_res.json().get("vector", [])
        except Exception:
            pass
    
    related_products = await crud_product.search_by_vector(
        db, 
        query_vector=color_vector,
        limit=5,
        exclude_id=[product.id]
    )
    
    return CoordinationResponse(
        answer=f"'{product.name}'의 디자인은 유지하면서, '{target_color}' 계열의 비슷한 스타일 상품을 추천합니다.",
        products=[ProductResponse.model_validate(p) for p in related_products]
    )

@router.get("/related-brand/{product_id}", response_model=CoordinationResponse)
async def get_related_by_brand(
    product_id: int, 
    db: AsyncSession = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
) -> CoordinationResponse:
    product = await crud_product.get(db, product_id=product_id)
    product = await _heal_product_embedding(db, product)
    
    if not product or not product.embedding:
        raise HTTPException(status_code=404, detail="AI Analysis Required")
    
    style_prompt = f"'{product.name}' 상품의 스타일(예: 미니멀리즘, 스트리트) 키워드 3개만 쉼표로 구분하여 답변하시오."
    
    # SAFE_AI_URL 사용
    AI_SERVICE_API_URL = SAFE_AI_URL
    style_keywords = ["유사 스타일"]
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            llm_res = await client.post(
                f"{AI_SERVICE_API_URL}/llm-generate-response", 
                json={"prompt": style_prompt}
            )
            if llm_res.status_code == 200:
                text = llm_res.json().get("answer", "")
                style_keywords = [k.strip() for k in text.split(',') if k.strip()]
        except Exception:
            pass

    embedding_text = f"다른 브랜드 {product.category} {', '.join(style_keywords)}"
    brand_vector = product.embedding 
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            vector_res = await client.post(
                f"{AI_SERVICE_API_URL}/embed-text", 
                json={"text": embedding_text}
            )
            if vector_res.status_code == 200:
                brand_vector = vector_res.json().get("vector", [])
        except Exception:
            pass
        
    related_products = await crud_product.search_by_vector(
        db, 
        query_vector=brand_vector,
        limit=5,
        exclude_id=[product.id] 
    )

    return CoordinationResponse(
        answer=f"'{product.name}'와 비슷한 스타일({', '.join(style_keywords)})이지만, 다른 브랜드의 유사 상품들을 엄선하여 추천합니다.",
        products=[ProductResponse.model_validate(p) for p in related_products]
    )