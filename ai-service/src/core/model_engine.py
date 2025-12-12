import os
import logging
import base64
import io
import threading
import json
import re
import random
import ast
from typing import List, Optional, Dict, Union
from PIL import Image

import torch
from sentence_transformers import SentenceTransformer, util 
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ibm import ChatWatsonx
from langchain_core.messages import HumanMessage

from src.core.prompts import VISION_ANALYSIS_PROMPT

logger = logging.getLogger(__name__)

# [상수 정의]
BERT_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
CLIP_MODEL_NAME = "sentence-transformers/clip-ViT-B-32-multilingual-v1"
CLIP_VISION_MODEL_NAME = "sentence-transformers/clip-ViT-B-32"
VISION_MODEL_ID = "meta-llama/llama-3-2-11b-vision-instruct" 

class ModelEngine:
    _instance: Optional['ModelEngine'] = None
    _lock = threading.Lock() 
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ModelEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, 'is_initialized') and self.is_initialized:
            return
            
        self.vision_model: Optional[ChatWatsonx] = None
        self.text_model: Optional[ChatWatsonx] = None # [복구] 텍스트 전용 모델 추가
        self.bert_model: Optional[HuggingFaceEmbeddings] = None
        self.clip_text_model: Optional[SentenceTransformer] = None
        self.clip_vision_model: Optional[SentenceTransformer] = None
        
        self.project_id = os.getenv("WATSONX_PROJECT_ID")
        self.device = os.getenv("EMBEDDING_DEVICE", "cpu")
        self.is_initialized = False

    def initialize(self):
        if self.is_initialized: return
        
        with self._lock:
            if self.is_initialized: return
            logger.info(f"🚀 Initializing Hybrid Model Engine on [{self.device}]...")
            self._init_watsonx()
            
            try:
                self.bert_model = HuggingFaceEmbeddings(
                    model_name=BERT_MODEL_NAME,
                    model_kwargs={'device': self.device},
                    encode_kwargs={'normalize_embeddings': True}
                )
            except Exception: pass

            try:
                self.clip_text_model = SentenceTransformer(CLIP_MODEL_NAME, device=self.device)
            except Exception: pass

            try:
                self.clip_vision_model = SentenceTransformer(CLIP_VISION_MODEL_NAME, device=self.device)
            except Exception: pass

            self.is_initialized = True
            logger.info("✅ All Models Initialized.")

    def _init_watsonx(self):
        """
        [수정됨] 이전에 성공했던 '정확도 중심' 설정으로 복구
        """
        try:
            api_key = os.getenv("WATSONX_API_KEY")
            url = os.getenv("WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
            
            if api_key and self.project_id:
                # 1. [Vision Model] 이미지 분석용 (정확도 최우선)
                self.vision_model = ChatWatsonx(
                    model_id=VISION_MODEL_ID, 
                    url=url, 
                    apikey=api_key, 
                    project_id=self.project_id,
                    params={
                        "decoding_method": "greedy", # [중요] sample -> greedy (일관된 분석 결과)
                        "temperature": 0.0,          # [중요] 창의성 제거 (사실 기반 묘사)
                        "max_new_tokens": 500,       # 너무 길지 않게
                        "min_new_tokens": 10,
                        "repetition_penalty": 1.2
                    }
                )
                
                # 2. [Text Model] 단순 작문용 (약간의 창의성 허용)
                self.text_model = ChatWatsonx(
                    model_id=VISION_MODEL_ID, 
                    url=url, 
                    apikey=api_key, 
                    project_id=self.project_id,
                    params={
                        "decoding_method": "sample",
                        "temperature": 0.3,
                        "max_new_tokens": 600,
                    }
                )
                
                logger.info(f"✅ Watsonx Connected (Vision & Text Configured).")
            else:
                logger.warning("⚠️ Watsonx credentials missing.")
        except Exception as e: logger.error(f"❌ Watsonx Init Failed: {e}")

    # -----------------------------------------------------------
    # [Robust Parsing] 인코딩 -> 정규식 추출 -> AST -> JSON
    # -----------------------------------------------------------
    def _fix_encoding(self, text: str) -> str:
        if not text: return ""
        if "\\u" in text:
            try: return text.encode('utf-8').decode('unicode_escape')
            except: pass
        try: return text.encode('cp1252').decode('utf-8')
        except: pass
        try: return text.encode('latin1').decode('utf-8')
        except: pass
        return text

    def _extract_fields_with_regex(self, text: str) -> Optional[Dict]:
        try:
            data = {}
            patterns = {
                "name": r'["\']name["\']\s*:\s*["\']([^"\']+)["\']',
                "category": r'["\']category["\']\s*:\s*["\']([^"\']+)["\']',
                "gender": r'["\']gender["\']\s*:\s*["\']([^"\']+)["\']',
                "description": r'["\']description["\']\s*:\s*["\']([^"\']+)["\']',
                "luxury_tier": r'["\']luxury_tier["\']\s*:\s*(\d+)',
                "price": r'["\']price["\']\s*:\s*(\d+)'
            }
            
            for key, pattern in patterns.items():
                match = re.search(pattern, text)
                if match:
                    val = match.group(1)
                    if key in ["luxury_tier", "price"]:
                        try: data[key] = int(val)
                        except: data[key] = 0
                    else:
                        data[key] = val
            
            if "name" in data:
                return data
            return None
        except:
            return None

    def _clean_and_parse_json(self, raw_text: str) -> Dict:
        text = raw_text
        try:
            text = re.sub(r'```json\s*', '', text)
            text = re.sub(r'```', '', text)
            text = text.strip()
            text = text.replace('\\"', '"')

            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            json_candidate = text
            if start_idx != -1 and end_idx != -1:
                json_candidate = text[start_idx : end_idx + 1]

            try: return json.loads(json_candidate)
            except: pass

            try:
                py_text = json_candidate.replace("true", "True").replace("false", "False").replace("null", "None")
                return ast.literal_eval(py_text)
            except: pass

            recovered_data = self._extract_fields_with_regex(text)
            if recovered_data:
                return recovered_data

            return None

        except Exception: 
            return None

    def _create_fallback_json(self, raw_text: str) -> Dict:
        logger.warning("⚠️ Triggering Fallback JSON Generator...")
        
        clean_text = self._fix_encoding(raw_text)
        clean_text = re.sub(r'[{}"]', '', clean_text)
        
        name = "트렌디 시즌 아이템"
        lower = raw_text.lower()
        if "leggings" in lower or "레깅스" in clean_text:
            name = f"퍼포먼스 핏 레깅스 {random.randint(10,99)}"
        elif "jacket" in lower or "자켓" in clean_text:
            name = f"데일리 무드 자켓 {random.randint(10,99)}"
            
        gender = "Unisex"
        if "man" in lower or "male" in lower: gender = "남성"
        elif "woman" in lower or "female" in lower: gender = "여성"

        description = clean_text[:100] + "..." if len(clean_text) > 10 else "AI가 이미지를 분석하여 추천하는 상품입니다."

        return {
            "name": name,
            "category": "패션",
            "gender": gender,
            "description": description,
            "price": random.randint(3, 15) * 10000 + 9000
        }

    def _calculate_dynamic_price(self, tier: Union[int, str], category_text: str = "") -> int:
        try: tier = int(tier)
        except: tier = 3
        
        cat_lower = str(category_text).lower()
        base_price = 65000 

        if any(x in cat_lower for x in ['coat', 'jacket', 'padding', 'outer', '코트', '자켓', '패딩', '아우터', '점퍼']):
            base_price = 128000
        elif any(x in cat_lower for x in ['dress', 'onepiece', 'suit', 'set', '원피스', '수트', '세트']):
            base_price = 89000
        elif any(x in cat_lower for x in ['pants', 'jeans', 'skirt', 'bottom', 'leggings', '바지', '팬츠', '스커트', '하의', '레깅스']):
            base_price = 52000
        elif any(x in cat_lower for x in ['shirt', 't-shirt', 'top', 'knit', 'sweater', 'hoodie', '티셔츠', '셔츠', '니트', '상의', '후드']):
            base_price = 39000
        elif any(x in cat_lower for x in ['shoes', 'sneakers', 'boots', 'bag', '신발', '운동화', '부츠', '가방']):
            base_price = 95000
        
        tier_multiplier = {1: 0.6, 2: 0.8, 3: 1.0, 4: 1.8, 5: 3.5}.get(tier, 1.0)

        final_price = base_price * tier_multiplier
        final_price = int(final_price / 100) * 100 + random.choice([0, 800, 900])
        
        return max(final_price, 15000)

    # -----------------------------------------------------------
    # [Core] AI Generation
    # -----------------------------------------------------------
    def generate_with_image(self, text_prompt: str, image_b64: str) -> str:
        if not self.vision_model: self.initialize()
        
        if self.vision_model is None:
            return json.dumps({
                "name": "연결 실패", "category": "Error", "gender": "Unisex",
                "description": "AI 모델 연결 실패", "price": 0
            }, ensure_ascii=False)

        try:
            final_prompt = text_prompt
            if "Analyze" in text_prompt or "JSON" in text_prompt:
                final_prompt = VISION_ANALYSIS_PROMPT

            message = HumanMessage(content=[
                {"type": "text", "text": final_prompt},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ])
            
            response = self.vision_model.invoke([message])
            raw_content = self._fix_encoding(response.content)
            
            if "JSON" in final_prompt:
                parsed_data = self._clean_and_parse_json(raw_content)
                if parsed_data:
                    tier = parsed_data.get("luxury_tier", 3)
                    category = parsed_data.get("category", "")
                    parsed_data["price"] = self._calculate_dynamic_price(tier, category)
                    
                    if "luxury_tier" in parsed_data: del parsed_data["luxury_tier"]
                    return json.dumps(parsed_data, ensure_ascii=False)
                else:
                    logger.error(f"❌ JSON Parse Failed. Raw: {raw_content[:100]}...")
                    return json.dumps(self._create_fallback_json(raw_content), ensure_ascii=False)
            
            return raw_content

        except Exception as e:
            logger.error(f"Vision Error: {e}")
            return json.dumps(self._create_fallback_json(""), ensure_ascii=False)
        
    def generate_text(self, prompt: str) -> str:
        if not self.vision_model: self.initialize()
        
        try:
            # 텍스트 전용 모델이 있으면 우선 사용, 없으면 비전 모델 사용
            model_to_use = self.text_model if self.text_model else self.vision_model
            
            if not model_to_use:
                return "AI 모델이 초기화되지 않았습니다."

            messages = [HumanMessage(content=prompt)]
            response = model_to_use.invoke(messages)
            return response.content
            
        except Exception as e:
            logger.error(f"❌ Text Generation Error: {e}")
            return "죄송합니다. 답변을 생성할 수 없습니다." 

    # -----------------------------------------------------------
    # [Essential] Embedding Functions (YOLO 포함 완전 복구)
    # -----------------------------------------------------------
    def generate_embedding(self, text: str) -> List[float]:
        if not self.bert_model: self.initialize()
        try: return self.bert_model.embed_query(text)
        except: return [0.0] * 768

    def generate_dual_embedding(self, text: str) -> Dict[str, List[float]]:
        if not self.bert_model or not self.clip_text_model: self.initialize()
        result = {"bert": [0.0] * 768, "clip": [0.0] * 512}
        try:
            if self.bert_model: result["bert"] = self.bert_model.embed_query(text)
            if self.clip_text_model:
                clip_vec = self.clip_text_model.encode(text)
                result["clip"] = clip_vec.tolist() if hasattr(clip_vec, "tolist") else list(clip_vec)
        except: pass
        return result

    def calculate_similarity(self, text: str, image: Image.Image) -> float:
        if not self.clip_text_model or not self.clip_vision_model: self.initialize()
        try:
            text_emb = self.clip_text_model.encode(text, convert_to_tensor=True)
            img_emb = self.clip_vision_model.encode(image, convert_to_tensor=True)
            return util.cos_sim(text_emb, img_emb).item()
        except: return 0.0

    def generate_image_embedding(self, image_data: Union[str, Image.Image], use_yolo: bool = True) -> Dict[str, List[float]]:
        if not self.clip_vision_model: self.initialize()
        default_vector = [0.0] * 512
        try:
            pil_image = image_data
            if isinstance(image_data, str):
                if "base64," in image_data: image_data = image_data.split("base64,")[1]
                pil_image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            
            if use_yolo:
                try:
                    from src.core.yolo_detector import yolo_detector
                    cropped = yolo_detector.crop_fashion_regions(pil_image, target="full")
                    if cropped: pil_image = cropped
                except: pass

            if self.clip_vision_model:
                vector = self.clip_vision_model.encode(pil_image)
                return {"clip": vector.tolist() if hasattr(vector, "tolist") else list(vector)}
            return {"clip": default_vector}
        except: return {"clip": default_vector}

    def generate_fashion_embeddings(self, image_data: Union[str, Image.Image]) -> Dict[str, List[float]]:
        if not self.clip_vision_model: self.initialize()
        zero_vector = [0.0] * 512
        result = {"full": zero_vector.copy(), "upper": zero_vector.copy(), "lower": zero_vector.copy()}
        try:
            pil_image = image_data
            if isinstance(image_data, str):
                if "base64," in image_data: image_data = image_data.split("base64,")[1]
                pil_image = Image.open(io.BytesIO(base64.b64decode(image_data)))
            
            try:
                from src.core.yolo_detector import yolo_detector
                features = yolo_detector.extract_fashion_features(pil_image)
                for k, img_crop in features.items():
                    if img_crop and self.clip_vision_model:
                        vec = self.clip_vision_model.encode(img_crop)
                        result[k] = vec.tolist() if hasattr(vec, "tolist") else list(vec)
            except Exception as e:
                logger.error(f"Fashion Feature Extraction Failed: {e}")
                if self.clip_vision_model:
                    vec = self.clip_vision_model.encode(pil_image)
                    result["full"] = vec.tolist() if hasattr(vec, "tolist") else list(vec)

        except Exception as e: 
            logger.error(f"Embedding Gen Error: {e}")
            
        return result

model_engine = ModelEngine()