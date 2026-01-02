# MODIFY 프로젝트 성능 테스트

종합 성능 테스트 도구 - AI 모델, API, 데이터베이스, 처리량, 코사인 유사도 측정

## 📋 테스트 항목

### 1. AI 모델 성능 테스트
- **BERT 임베딩**: 텍스트 임베딩 생성 속도
- **CLIP 이미지 검색**: 이미지 검색 경로 결정 속도
- **LLM 텍스트 생성**: Watsonx를 통한 텍스트 생성 속도

### 2. API 엔드포인트 성능 테스트
- 상품 목록 조회
- 상품 검색 (텍스트)
- 사용자 정보 조회
- 주문 목록 조회

### 3. 데이터베이스 쿼리 성능 테스트
- 벡터 검색 (BERT 임베딩)
- 일반 필터링 쿼리
- 복합 쿼리 (검색 + 필터)

### 4. 시스템 처리량 테스트
- 동시 요청 1, 5, 10, 20, 50개 처리
- 초당 요청 수(RPS) 측정
- 평균 응답 시간 측정

### 5. 코사인 유사도 정확도 테스트
- 유사한 쿼리 쌍의 코사인 유사도 측정
- 비유사한 쿼리 쌍의 코사인 유사도 측정
- 분리도(Separation) 계산

## 🚀 사용 방법

### 1. 필수 패키지 설치
```bash
pip install aiohttp numpy matplotlib
```

### 2. 서비스 실행 확인
테스트 실행 전 다음 서비스가 실행 중이어야 합니다:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- AI Service: http://localhost:8005
- PostgreSQL: localhost:5432

```bash
# Docker Compose로 모든 서비스 실행
docker-compose -f docker-compose.dev.yml up -d
```

### 3. 테스트 실행
```bash
cd performance_tests
python run_performance_test.py
```

## 📊 결과 출력

테스트 완료 후 다음 파일들이 생성됩니다:

1. **results_YYYYMMDD_HHMMSS.png**: 성능 테스트 결과 그래프 (6개 차트)
2. **results_YYYYMMDD_HHMMSS.json**: 상세 수치 데이터 (JSON 형식)

### 그래프 구성
- **AI 모델 응답 시간**: 각 모델별 평균 응답 시간 (ms)
- **API 엔드포인트 응답 시간**: 엔드포인트별 평균 응답 시간 (ms)
- **데이터베이스 쿼리 성능**: 쿼리 유형별 평균 응답 시간 (ms)
- **시스템 처리량**: 동시 요청 수에 따른 초당 처리 요청 수 (req/s)
- **코사인 유사도 정확도**: 유사/비유사 쿼리 쌍의 유사도 분포
- **카테고리별 평균 성능**: 전체 성능 비교 차트

## ⚙️ 설정 변경

`run_performance_test.py` 파일 상단에서 다음 설정을 변경할 수 있습니다:

```python
# 테스트 설정
BASE_URL = "http://localhost"  # 백엔드 URL
AI_SERVICE_URL = "http://localhost:8005"  # AI 서비스 URL
TEST_ITERATIONS = 10  # 각 테스트당 반복 횟수
CONCURRENT_REQUESTS = [1, 5, 10, 20, 50]  # 동시 요청 수 목록
```

## 📈 성능 기준

### 권장 성능 지표
- **AI 모델 응답**: < 2000ms
- **API 엔드포인트**: < 500ms
- **데이터베이스 쿼리**: < 1000ms
- **처리량 (10개 동시)**: > 10 req/s
- **코사인 유사도 분리도**: > 0.2

## 🔍 문제 해결

### 로그인 실패
```
❌ 로그인 실패
```
→ `.env.dev` 파일의 `SUPERUSER_EMAIL`과 `SUPERUSER_PASSWORD` 확인

### 타임아웃 에러
```
⚠️ 테스트 실패: Timeout
```
→ 서비스가 실행 중인지 확인하거나 `TEST_ITERATIONS` 줄이기

### 한글 폰트 에러
```
UserWarning: Glyph missing from current font
```
→ `matplotlib.rcParams['font.family']`를 시스템에 맞게 변경
- Windows: `'Malgun Gothic'`
- Mac: `'AppleGothic'`
- Linux: `'NanumGothic'`

## 📝 참고사항

- 테스트는 실제 운영 환경의 성능과 다를 수 있습니다
- 네트워크 상태, 시스템 리소스에 따라 결과가 달라질 수 있습니다
- 정확한 측정을 위해 다른 프로세스를 최소화하고 실행하세요
