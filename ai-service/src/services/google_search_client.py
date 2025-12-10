import os
import httpx
import logging
import re
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class GoogleSearchClient:
    def __init__(self):
        # 1. 환경변수 로드 (호환성 강화: 가능한 모든 변수명 확인)
        self.api_key = os.getenv("GOOGLE_SEARCH_API_KEY") or os.getenv("GOOGLE_API_KEY")
        
        # [FIX] GOOGLE_SEARCH_ENGINE_ID 추가
        self.cx = (
            os.getenv("GOOGLE_SEARCH_CX") or 
            os.getenv("GOOGLE_CSE_ID") or 
            os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        )
        
        # 공백 제거 (안전장치)
        if self.api_key: self.api_key = self.api_key.strip()
        if self.cx: self.cx = self.cx.strip()
        
        # 키 가리기 (보안 로그)
        masked_key = f"{self.api_key[:5]}..." if self.api_key else "None"
        masked_cx = f"{self.cx[:5]}..." if self.cx else "None"
        
        logger.info(f"🔑 Google Client Init - Key: {masked_key}, CX: {masked_cx}")
        self.is_ready = bool(self.api_key and self.cx)
        self.search_url = "https://www.googleapis.com/customsearch/v1"

    # [기능 유지] 유연한 필터링 로직 (조사 제거 및 안전망)
    def _filter_irrelevant_results(self, items: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        if not items or not query: return items

        # 1. 키워드 정제 (조사 제거: 이효리가 -> 이효리)
        clean_query = re.sub(r'[^\w\s]', '', query) # 특수문자 제거
        words = clean_query.split()
        
        # 의미 있는 키워드만 추출 (2글자 이상)
        keywords = []
        for w in words:
            # 끝 글자가 조사일 수 있으므로 제거 시도 (간단한 휴리스틱)
            root_w = re.sub(r'(은|는|이|가|을|를)$', '', w)
            if len(root_w) >= 2:
                keywords.append(root_w)
        
        # 키워드가 없으면 필터링 스킵
        if not keywords: return items

        filtered_items = []
        for item in items:
            title = item.get("title", "").lower()
            snippet = item.get("snippet", "").lower()
            combined_text = title + " " + snippet
            
            # [조건] 키워드 중 하나라도 포함되면 통과
            is_relevant = False
            for k in keywords:
                if k.lower() in combined_text:
                    is_relevant = True
                    break
            
            # [제외] 광고성 단어
            if "buy" in combined_text or "discount" in combined_text:
                is_relevant = False

            if is_relevant:
                filtered_items.append(item)

        # [안전망] 필터링 결과가 0개면, 원본 상위 3개 반환 (아무것도 안 나오는 것보단 낫다)
        if not filtered_items:
            logger.warning("⚠️ All items filtered out. Returning top 3 original items as fallback.")
            return items[:3]

        logger.info(f"🧹 Filtering: {len(items)} -> {len(filtered_items)} items")
        return filtered_items

    async def _execute_search(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        if not self.is_ready: 
            logger.error("❌ Google Search Credentials missing in .env")
            return []

        # API 키 주입
        params['key'] = self.api_key
        params['cx'] = self.cx

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # 로그용 파라미터 (키 숨김)
                safe_params = params.copy()
                safe_params['key'] = 'HIDDEN'
                safe_params['cx'] = 'HIDDEN'
                logger.info(f"📤 Google Request: {safe_params}")

                response = await client.get(self.search_url, params=params)
                
                # [상세 에러 로깅]
                if response.status_code != 200:
                    error_text = response.text
                    if response.status_code == 403:
                        logger.error(f"❌ Google API 403 Forbidden: 키가 틀렸거나 CX ID가 잘못되었습니다. 응답: {error_text}")
                    elif response.status_code == 429:
                        logger.error(f"❌ Google API 429 Quota Exceeded: 하루 무료 사용량(100회)을 초과했습니다.")
                    else:
                        logger.error(f"❌ Google API Error ({response.status_code}): {error_text}")
                    return []

                data = response.json()
                items = data.get("items", [])
                
                # [적용] 필터링 수행
                query = params.get("q", "")
                valid_items = self._filter_irrelevant_results(items, query)
                
                results = []
                for item in valid_items:
                    results.append({
                        "title": item.get("title", ""),
                        "link": item.get("link", ""),
                        "snippet": item.get("snippet", ""),
                        "thumbnail": item.get("image", {}).get("thumbnailLink", item.get("link", ""))
                    })
                return results

            except Exception as e:
                logger.error(f"❌ Google Search Connection Failed: {e}")
                return []

    async def search(self, query: str, num_results: int = 5) -> List[Dict[str, Any]]:
        params = {
            "q": query, 
            "num": num_results
        }
        return await self._execute_search(params)

    async def search_images(self, query: str, num_results: int = 4, start_index: int = 1) -> List[Dict[str, Any]]:
        # 필터링을 위해 원본 쿼리의 의미를 유지하되, 검색 엔진을 위해 불필요한 수식어 제거
        clean_query = query.replace("독사진 전신 고화질 패션", "").strip()
        final_query = clean_query if len(clean_query) > 2 else query

        # 넉넉하게 가져와서 필터링
        request_num = min(num_results * 3, 10) 

        params = {
            "q": final_query,
            "searchType": "image",
            "num": request_num, 
            "start": start_index,            
            "imgType": "photo",
            "imgSize": "large",
            "safe": "off",
            "gl": "kr",
            "hl": "ko"
        }
        
        results = await self._execute_search(params)
        return results[:num_results]