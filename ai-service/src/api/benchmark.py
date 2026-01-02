"""
벤치마크 API 엔드포인트
다른 모델들과의 성능 비교 테스트용
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, Any
import time

from src.core.benchmark_models import get_benchmark_engine
from src.core.model_engine import model_engine

router = APIRouter(prefix="/benchmark", tags=["benchmark"])


class BenchmarkRequest(BaseModel):
    query: str
    image_path: Optional[str] = None


class BenchmarkResponse(BaseModel):
    results: Dict[str, Any]


@router.post("/compare-all", response_model=BenchmarkResponse)
async def compare_all_models(request: BenchmarkRequest):
    """
    모든 모델 성능 비교
    - BERT + CLIP (현재 사용)
    - Grounding DINO
    - LLaVA-Next
    - YOLO 단일
    """
    results = {}

    # 1. 현재 사용 모델 (BERT + CLIP)
    try:

        # BERT 테스트
        start = time.time()
        bert_result = model_engine.generate_embeddings(request.query)
        bert_elapsed = (time.time() - start) * 1000

        results["BERT (현재)"] = {
            "elapsed_ms": bert_elapsed,
            "vector_dim": len(bert_result["vectors"]["bert"]),
            "model_type": "text_embedding"
        }

        # CLIP 테스트 (determine_path 사용)
        start = time.time()
        clip_result = model_engine.determine_search_path(request.query)
        clip_elapsed = (time.time() - start) * 1000

        results["CLIP (현재)"] = {
            "elapsed_ms": clip_elapsed,
            "search_path": clip_result["search_path"],
            "model_type": "image_search"
        }

    except Exception as e:
        results["현재 모델"] = {"error": str(e)}

    # 2. 벤치마크 모델들
    try:
        benchmark_engine = get_benchmark_engine()

        # Ground Dino
        grounding_result = benchmark_engine.test_groundingdino(
            request.query,
            request.image_path
        )
        results["Grounding DINO"] = grounding_result

        # LLaVA-Next
        llava_result = benchmark_engine.test_llavanext(
            request.query,
            request.image_path
        )
        results["LLaVA-Next"] = llava_result

        # YOLO 단일
        yolo_result = benchmark_engine.test_yolo_only(
            request.query,
            request.image_path
        )
        results["YOLO 단일"] = yolo_result

    except Exception as e:
        results["벤치마크 모델"] = {"error": str(e)}

    return BenchmarkResponse(results=results)


@router.post("/groundingdino", response_model=Dict[str, Any])
async def test_groundingdino(request: BenchmarkRequest):
    """Grounding DINO 단독 테스트"""
    benchmark_engine = get_benchmark_engine()
    return benchmark_engine.test_groundingdino(request.query, request.image_path)


@router.post("/llavanext", response_model=Dict[str, Any])
async def test_llavanext(request: BenchmarkRequest):
    """LLaVA-Next 단독 테스트"""
    benchmark_engine = get_benchmark_engine()
    return benchmark_engine.test_llavanext(request.query, request.image_path)


@router.post("/yolo-only", response_model=Dict[str, Any])
async def test_yolo_only(request: BenchmarkRequest):
    """YOLO 단일 모델 테스트"""
    benchmark_engine = get_benchmark_engine()
    return benchmark_engine.test_yolo_only(request.query, request.image_path)
