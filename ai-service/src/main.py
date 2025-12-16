import logging
import json
import re
import base64
import os
import uuid
import traceback
import io
from PIL import Image  # ✅ 이미지 처리를 위해 최상단으로 이동

from fastapi import FastAPI, HTTPException, APIRouter, UploadFile, File
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

# Core Modules
from src.core.model_engine import model_engine
from src.core.prompts import VISION_ANALYSIS_PROMPT
from src.core.yolo_detector import yolo_detector  # ✅ 여기서 미리 import
from src.services.rag_orchestrator import rag_orchestrator

# Logging Setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai-service")

# --- Lifespan Manager ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 AI Service Starting...")
    try:
        # 모델 엔진 초기화
        model_engine.initialize()
        
        # ✅ YOLO 모델도 서버 시작 시 미리 로드 (첫 요청 딜레이 방지)
        if not yolo_detector.initialized:
            logger.info("loading YOLO detector...")
            yolo_detector.initialize()
            
    except Exception as e:
        logger.error(f"⚠️ Model init warning: {e}")
        logger.error(traceback.format_exc())
    
    yield
    logger.info("💤 AI Service Shutting down...")

app = FastAPI(title="Modify AI Service", version="1.0.0", lifespan=lifespan)
api_router = APIRouter(prefix="/api/v1")

# --- DTO Definitions ---
class EmbedRequest(BaseModel):
    text: str

class AnalyzeRequest(BaseModel):
    image_b64: str
    query: str   

class EmbedResponse(BaseModel):
    vector: List[float]

class ImageAnalysisResponse(BaseModel):
    name: str
    category: str
    gender: str
    description: str
    price: int
    vector: List[float]           # BERT (768)
    vector_clip: List[float]      # CLIP Full (512)
    vector_clip_upper: List[float] # CLIP Upper (512)
    vector_clip_lower: List[float] # CLIP Lower (512)

class PathRequest(BaseModel):
    query: str

class InternalSearchRequest(BaseModel):
    query: str
    image_b64: Optional[str] = None

class ClipVectorRequest(BaseModel):
    image_b64: str

class ClipVectorResponse(BaseModel):
    vector: List[float]
    dimension: int

class ImageSearchRequest(BaseModel):
    image_b64: str
    limit: int = 12

class FashionClipRequest(BaseModel):
    image_b64: str
    target: str = "full"  # "full", "upper", "lower"

# --- Helper Methods ---

def _fix_encoding(text: str) -> str:
    """깨진 한글(Mojibake) 및 유니코드 이스케이프 복구"""
    if not text: return ""
    try:
        return text.encode('latin1').decode('utf-8')
    except:
        pass
    try:
        return text.encode('utf-8').decode('unicode_escape')
    except:
        pass
    return text

def _decode_image(image_b64: str) -> Image.Image:
    """✅ Base64 문자열을 PIL Image로 변환하는 공통 함수"""
    try:
        if "base64," in image_b64:
            image_b64 = image_b64.split("base64,")[1]
        
        image_data = base64.b64decode(image_b64)
        return Image.open(io.BytesIO(image_data)).convert("RGB")
    except Exception as e:
        logger.error(f"❌ Image decoding failed: {e}")
        raise HTTPException(status_code=400, detail="Invalid image data")

CATEGORY_MAP = {
    "상의": "Tops", "티셔츠": "Tops", "니트": "Tops", "셔츠": "Tops",
    "하의": "Bottoms", "바지": "Bottoms", "치마": "Bottoms", "스커트": "Bottoms", "팬츠": "Bottoms", "진": "Bottoms",
    "아우터": "Outerwear", "자켓": "Outerwear", "코트": "Outerwear", "패딩": "Outerwear",
    "원피스": "Dresses", "드레스": "Dresses",
    "신발": "Shoes", "슈즈": "Shoes",
    "액세서리": "Accessories", "모자": "Accessories", "가방": "Accessories"
}

# --- Endpoints ---

@api_router.post("/embed-text", response_model=EmbedResponse)
async def embed_text(request: EmbedRequest):
    try:
        vector = model_engine.generate_embedding(request.text)
        return {"vector": vector}
    except:
        return {"vector": [0.0] * 768} 

@api_router.post("/analyze-image", response_model=ImageAnalysisResponse)
async def analyze_image(file: UploadFile = File(...)):
    filename = file.filename
    try:
        contents = await file.read()
        image_b64 = base64.b64encode(contents).decode("utf-8")
        
        logger.info(f"👁️ Analyzing image: {filename}...")
        
        # 1. Text Generation (Llama)
        generated_text = model_engine.generate_with_image(VISION_ANALYSIS_PROMPT, image_b64)
        
        # JSON Parsing
        try:
            product_data = json.loads(generated_text)
        except:
            product_data = {
                "name": f"상품 {filename}", "category": "Fashion", 
                "price": 0, "gender": "Unisex", 
                "description": generated_text[:200]
            }

        # 카테고리 매핑 로직
        raw_category = product_data.get("category", "Etc")
        standard_category = CATEGORY_MAP.get(raw_category)
        
        if not standard_category:
            for kr_key, en_val in CATEGORY_MAP.items():
                if kr_key in raw_category:
                    standard_category = en_val
                    break
        
        final_category = standard_category if standard_category else "Etc"
        product_data["category"] = final_category
        
        logger.info(f"🔄 Category Mapped: '{raw_category}' -> '{final_category}'")

        # 2. Vector Generation
        meta_text = f"[{product_data.get('gender')}] {product_data.get('name')} {product_data.get('category')}"
        vector_bert = model_engine.generate_embedding(meta_text)
        
        # CLIP (512 x 3)
        fashion_vectors = model_engine.generate_fashion_embeddings(image_b64)
        
        logger.info(f"✅ Analysis Success: {product_data.get('name')}")
        
        return {
            "name": product_data.get("name", "Unknown"),
            "category": product_data.get("category", "Etc"),
            "gender": product_data.get("gender", "Unisex"),
            "description": product_data.get("description", ""),
            "price": product_data.get("price", 0),
            "vector": vector_bert,
            "vector_clip": fashion_vectors["full"],
            "vector_clip_upper": fashion_vectors["upper"],
            "vector_clip_lower": fashion_vectors["lower"]
        }

    except Exception as e:
        logger.error(f"❌ Analysis Critical Error: {e}")
        zero_512 = [0.0] * 512
        return {
            "name": f"ErrorItem ({filename})", "category": "Error", "gender": "Unisex",
            "description": "분석 실패", "price": 0, "vector": [0.0] * 768,
            "vector_clip": zero_512, "vector_clip_upper": zero_512, "vector_clip_lower": zero_512
        }

@api_router.post("/llm-generate-response")
async def llm_generate(body: Dict[str, str]):
    prompt = body.get("prompt", "")
    logger.info(f"📝 LLM Prompt received: {prompt[:100]}...")
    try:
        korean_prompt = f"질문: {prompt}\n답변 (한국어):"
        answer = model_engine.generate_text(korean_prompt)
        return {"answer": answer}
    except Exception as e:
        logger.error(f"❌ LLM Generation Failed: {e}")
        return {"answer": "죄송합니다. AI 응답을 생성할 수 없습니다."}
    
@api_router.post("/analyze-image-detail")
async def analyze_image_detail(req: AnalyzeRequest):
    result = await rag_orchestrator.analyze_specific_image(req.image_b64, req.query)
    return {"analysis": result}    

@api_router.post("/generate-clip-vector", response_model=ClipVectorResponse)
async def generate_clip_vector(request: ClipVectorRequest):
    """기본 CLIP 벡터 생성 (재검색용)"""
    try:
        # 공통 함수 사용
        pil_image = _decode_image(request.image_b64)
        
        result = model_engine.generate_image_embedding(pil_image, use_yolo=True)
        clip_vector = result.get("clip", [])
        
        if not clip_vector:
            raise HTTPException(status_code=500, detail="CLIP 벡터 생성 실패")
        
        return {"vector": clip_vector, "dimension": len(clip_vector)}
        
    except Exception as e:
        logger.error(f"❌ CLIP vector generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/generate-fashion-clip-vector")
async def generate_fashion_clip_vector(request: FashionClipRequest):
    """
    ✅ 패션 특화 CLIP 벡터 생성 (YOLO 크롭 적용)
    """
    try:
        # 1. 이미지 디코딩 (공통 함수)
        pil_image = _decode_image(request.image_b64)
        target = request.target
        
        # 2. YOLO로 영역 크롭
        try:
            cropped = yolo_detector.crop_fashion_regions(pil_image, target=target)
            
            if cropped is not None:
                logger.info(f"✂️ YOLO cropped '{target}' region: {cropped.size}")
                pil_image = cropped

                # [DEBUG] 디버그 이미지 저장 (경로 안전하게 처리)
                debug_dir = os.path.join(os.getcwd(), "static", "debug")
                os.makedirs(debug_dir, exist_ok=True)
                
                debug_filename = os.path.join(debug_dir, f"{uuid.uuid4()}_{target}.jpg")
                pil_image.save(debug_filename)
                logger.info(f"📸 Debug Image Saved: {debug_filename}")
            else:
                logger.warning(f"⚠️ YOLO crop failed for '{target}', using original")
                
        except Exception as e:
            logger.warning(f"⚠️ YOLO process failed: {e}")
        
        # 3. CLIP 벡터 생성 (YOLO 이미 적용했으므로 use_yolo=False)
        result = model_engine.generate_image_embedding(pil_image, use_yolo=False)
        clip_vector = result.get("clip", [])
        
        if not clip_vector:
            raise HTTPException(status_code=500, detail="CLIP 벡터 생성 실패")
        
        return {
            "vector": clip_vector,
            "dimension": len(clip_vector),
            "target": target
        }
        
    except Exception as e:
        logger.error(f"❌ Fashion CLIP vector generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/search-by-image")
async def search_by_image(request: ImageSearchRequest):
    """이미지 기반 검색 (CLIP)"""
    try:
        pil_image = _decode_image(request.image_b64)
        
        result = model_engine.generate_image_embedding(pil_image)
        clip_vector = result.get("clip", [])
        
        if not clip_vector:
            raise HTTPException(status_code=500, detail="CLIP 벡터 생성 실패")
        
        return {
            "vectors": {
                "clip": clip_vector,
                "bert": None
            },
            "search_type": "image_similarity"
        }
        
    except Exception as e:
        logger.error(f"❌ Image search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# --- RAG Orchestrator ---

@api_router.post("/determine-path")
async def determine_path(request: PathRequest):
    logger.info(f"🤔 Determining path for query: {request.query}")
    try:
        decision = await rag_orchestrator.determine_search_path(request.query)
        return {"path": decision}
    except Exception as e:
        logger.error(f"Determine path error: {e}")
        return {"path": "INTERNAL"}

@api_router.post("/process-internal")
async def process_internal(request: InternalSearchRequest):
    logger.info(f"🏢 Processing Internal: {request.query}")
    return await rag_orchestrator.process_internal_search(request.query)

@api_router.post("/process-external")
async def process_external(request: InternalSearchRequest):
    logger.info(f"🌍 Processing External: {request.query}")
    try:
        return await rag_orchestrator.process_external_rag(request.query)
    except Exception as e:
        logger.error(f"External processing failed: {e}")
        return await rag_orchestrator.process_internal_search(request.query)

app.include_router(api_router)

@app.get("/")
def read_root():
    return {"message": "Modify AI Service is Running 🚀"}