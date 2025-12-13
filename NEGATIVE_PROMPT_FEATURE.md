# 네거티브 프롬프트 기능 구현 완료

## 개요
사용자가 검색 시 원하지 않는 스타일이나 특징을 명시하여 더 정확한 검색 결과를 얻을 수 있는 **네거티브 프롬프트** 기능이 구현되었습니다.

## 주요 기능

### ✅ 네거티브 필터링
- 사용자가 제외하고 싶은 키워드를 입력하면 해당 키워드가 포함된 상품을 자동으로 필터링
- 상품명, 설명, 카테고리에서 네거티브 키워드 검색
- 여러 키워드를 쉼표(,), 슬래시(/), 공백으로 구분하여 입력 가능

### 📍 적용 범위
- ✅ AI 검색 (`/api/v1/search/ai-search`)
- ✅ CLIP 이미지 검색 (`/api/v1/search/search-by-clip`)

## 사용 예시

### 1. 검색 UI
검색창 아래에 네거티브 프롬프트 입력 필드가 추가되었습니다:

```
┌─────────────────────────────────────────────┐
│ 🔍 장원영 공항 패션              🎤 검색  │
├─────────────────────────────────────────────┤
│ ✖ 청바지, 스니커즈, 캐주얼      초기화    │
└─────────────────────────────────────────────┘
```

### 2. 사용 시나리오

**시나리오 1: 포멀한 스타일만 검색**
- 검색어: "여성 코트"
- 네거티브: "청바지, 스니커즈, 캐주얼"
- 결과: 청바지, 스니커즈, 캐주얼이 포함되지 않은 포멀한 코트만 표시

**시나리오 2: 특정 색상 제외**
- 검색어: "원피스"
- 네거티브: "검은색, 블랙, black"
- 결과: 검은색 원피스 제외

**시나리오 3: 특정 브랜드/스타일 제외**
- 검색어: "남성 재킷"
- 네거티브: "데님, 후드, 스포츠"
- 결과: 데님/후드/스포츠 재킷 제외

## 기술 구현

### Backend (FastAPI)

#### 1. 네거티브 키워드 추출 함수
```python
def extract_negative_keywords(negative_prompt: Optional[str]) -> List[str]:
    """
    네거티브 프롬프트에서 제외할 키워드 리스트 추출
    예: "청바지, 스니커즈, 캐주얼" -> ["청바지", "스니커즈", "캐주얼"]
    """
    if not negative_prompt:
        return []

    keywords = re.split(r'[,/\s]+', negative_prompt.strip())
    return [k.strip().lower() for k in keywords if k.strip()]
```

#### 2. 상품 필터링 함수
```python
def filter_products_by_negative(products: List[Product], negative_keywords: List[str]) -> List[Product]:
    """네거티브 키워드를 포함하는 상품 제외"""
    if not negative_keywords:
        return products

    filtered = []
    for product in products:
        text_to_check = f"{product.name} {product.description or ''} {product.category or ''}".lower()
        contains_negative = any(keyword in text_to_check for keyword in negative_keywords)

        if not contains_negative:
            filtered.append(product)

    return filtered
```

#### 3. API 엔드포인트 수정

**AI 검색 엔드포인트:**
```python
@router.post("/ai-search")
async def ai_search(
    query: str = Form(...),
    image_file: Optional[UploadFile] = File(None),
    limit: int = Form(12),
    negative_prompt: Optional[str] = Form(None),  # ✅ 추가
    db: AsyncSession = Depends(deps.get_db),
):
    # ... 검색 로직 ...

    # ✅ 네거티브 프롬프트 필터링
    if negative_prompt:
        negative_keywords = extract_negative_keywords(negative_prompt)
        results = filter_products_by_negative(results, negative_keywords)
```

**CLIP 이미지 검색:**
```python
class ClipSearchRequest(BaseModel):
    image_b64: str
    limit: int = 12
    query: Optional[str] = None
    target: str = "full"
    negative_prompt: Optional[str] = None  # ✅ 추가

@router.post("/search-by-clip")
async def search_by_clip_image(request: ClipSearchRequest, ...):
    # ... CLIP 검색 ...

    # ✅ 네거티브 필터링 (더 많이 가져온 후 필터링)
    if request.negative_prompt:
        negative_keywords = extract_negative_keywords(request.negative_prompt)
        results = filter_products_by_negative(results, negative_keywords)
        results = results[:request.limit]
```

### Frontend (React + TypeScript)

#### 1. State 추가
```typescript
const [negativePrompt, setNegativePrompt] = useState<string>("");
```

#### 2. UI 컴포넌트
```tsx
{/* 네거티브 프롬프트 입력 필드 */}
<div className="flex items-center space-x-3 mt-3 pt-3 border-t">
    <X className="w-5 h-5 text-red-400" />
    <input
        type="text"
        value={negativePrompt}
        onChange={(e) => setNegativePrompt(e.target.value)}
        placeholder="제외할 스타일 (예: 청바지, 스니커즈, 캐주얼)"
        className="flex-1 text-sm ..."
    />
    {negativePrompt && (
        <button onClick={() => setNegativePrompt("")}>
            초기화
        </button>
    )}
</div>
```

#### 3. API 호출 수정
```typescript
const formData = new FormData();
formData.append('query', currentQuery);
if (currentImage) formData.append('image_file', currentImage);
if (negativePrompt) formData.append('negative_prompt', negativePrompt);  // ✅
formData.append('limit', '12');
```

## 동작 원리

### 1. 키워드 추출
```
입력: "청바지, 스니커즈 / 캐주얼"
↓
split by [, / 공백]
↓
["청바지", "스니커즈", "캐주얼"]
↓
소문자 변환
↓
["청바지", "스니커즈", "캐주얼"]
```

### 2. 상품 필터링
```
상품 A: "블루 청바지 (데님 팬츠)" → ❌ 제외 (청바지 포함)
상품 B: "화이트 셔츠 (포멀)" → ✅ 포함
상품 C: "블랙 스니커즈" → ❌ 제외 (스니커즈 포함)
상품 D: "레더 구두" → ✅ 포함
```

### 3. 검색 플로우
```
사용자 입력
  ↓
검색어: "여성 코트"
네거티브: "청바지, 캐주얼"
  ↓
AI/CLIP 검색 (limit * 2개 가져옴)
  ↓
네거티브 필터링
  ↓
결과: 12개 반환
```

## 파일 변경 내역

### Backend
1. **[backend-core/src/api/v1/endpoints/search.py](backend-core/src/api/v1/endpoints/search.py)**
   - `extract_negative_keywords()` 함수 추가
   - `filter_products_by_negative()` 함수 추가
   - `ClipSearchRequest`에 `negative_prompt` 필드 추가
   - `/ai-search` 엔드포인트에 `negative_prompt` 파라미터 추가
   - CLIP 검색 및 AI 검색에 네거티브 필터링 로직 적용

### Frontend
1. **[frontend/src/pages/Search.tsx](frontend/src/pages/Search.tsx)**
   - `negativePrompt` state 추가
   - 네거티브 프롬프트 입력 UI 추가
   - API 호출 시 `negative_prompt` 파라미터 전송

## 사용 방법

### 1. 백엔드 재시작
```bash
docker restart modify-backend
```

### 2. 프론트엔드 테스트
1. http://localhost:5173 접속
2. 검색 페이지로 이동
3. 검색어 입력 (예: "여성 코트")
4. 네거티브 프롬프트 입력 (예: "청바지, 캐주얼")
5. 검색 버튼 클릭
6. 결과 확인

### 3. API 테스트
```bash
# curl 테스트
curl -X POST "http://localhost:8000/api/v1/search/ai-search" \
  -F "query=여성 코트" \
  -F "negative_prompt=청바지, 캐주얼" \
  -F "limit=12"
```

## 주의사항

### 1. 네거티브 키워드 형식
- ✅ 올바른 예: "청바지, 스니커즈, 캐주얼"
- ✅ 올바른 예: "청바지 / 스니커즈 / 캐주얼"
- ✅ 올바른 예: "청바지 스니커즈 캐주얼"
- ❌ 잘못된 예: "" (빈 문자열은 무시됨)

### 2. 검색 결과 수
- 네거티브 필터링으로 인해 결과가 적어질 수 있음
- CLIP 검색 시 `limit * 2`개를 가져온 후 필터링하여 충분한 결과 보장

### 3. 성능
- 네거티브 키워드가 많을수록 필터링 시간이 약간 증가할 수 있음
- 하지만 키워드 매칭은 매우 빠르므로 성능 영향은 미미함

## 향후 개선 사항
- [ ] 네거티브 프롬프트 자동 완성 기능
- [ ] 자주 사용하는 네거티브 키워드 저장
- [ ] 네거티브 키워드 제안 (AI 기반)
- [ ] 네거티브 필터링 결과 통계 표시

## 기술 스택
- **Backend**: FastAPI, Python
- **Frontend**: React, TypeScript, Tailwind CSS
- **Filtering**: 정규표현식 기반 키워드 매칭

---

구현 완료일: 2025-12-11
작성자: Claude Code Assistant
