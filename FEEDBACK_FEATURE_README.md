# AI 검색 결과 피드백 시스템 구현 완료

## 개요
사용자가 AI 검색 결과에 대해 피드백(좋아요/싫어요)을 제공할 수 있는 시스템이 구현되었습니다.

## 주요 기능

### 1. **실시간 피드백 수집**
- ✅ 좋아요 / 싫어요 버튼으로 간단한 피드백
- ✅ 로그인 / 비로그인 사용자 모두 사용 가능
- ✅ 검색 쿼리 저장 (어떤 검색어로 해당 상품을 찾았는지 기록)
- ✅ 토글 기능 (재클릭 시 취소, 다른 타입 클릭 시 변경)

### 2. **권한별 데이터 표시**
- **일반 고객**: 좋아요 수만 표시
- **관리자**: 좋아요 + 싫어요 모두 표시 및 만족도 비율 확인 가능

### 3. **관리자 대시보드**
- ✅ 최근 피드백 목록 (최근 20개)
- ✅ 상품 ID, 피드백 타입, 검색어, 사용자 정보, 일시 표시
- ✅ 상품 페이지로 바로 이동 가능한 링크

## 구현된 파일

### Backend
1. **[backend-core/src/models/search_feedback.py](backend-core/src/models/search_feedback.py)** - 피드백 데이터베이스 모델
2. **[backend-core/src/schemas/feedback.py](backend-core/src/schemas/feedback.py)** - Pydantic 스키마
3. **[backend-core/src/api/v1/endpoints/feedback.py](backend-core/src/api/v1/endpoints/feedback.py)** - API 엔드포인트
4. **[backend-core/alembic/versions/f1a2b3c4d5e6_add_search_feedbacks_table.py](backend-core/alembic/versions/f1a2b3c4d5e6_add_search_feedbacks_table.py)** - 마이그레이션 파일

### Frontend
1. **[frontend/src/utils/session.ts](frontend/src/utils/session.ts)** - 세션 ID 관리
2. **[frontend/src/api/feedback.ts](frontend/src/api/feedback.ts)** - 피드백 API 클라이언트
3. **[frontend/src/components/product/FeedbackButtons.tsx](frontend/src/components/product/FeedbackButtons.tsx)** - 피드백 버튼 컴포넌트
4. **[frontend/src/pages/ProductDetail.tsx](frontend/src/pages/ProductDetail.tsx)** - 상품 상세 페이지 (피드백 버튼 통합)
5. **[frontend/src/pages/admin/Dashboard.tsx](frontend/src/pages/admin/Dashboard.tsx)** - 관리자 대시보드 (피드백 통계 추가)

## 설치 및 실행

### 1. DB 마이그레이션 실행
Docker 환경이 실행 중인 상태에서:

```bash
# Docker 컨테이너 시작
docker-compose -f docker-compose.dev.yml up -d

# 백엔드 컨테이너에서 마이그레이션 실행
docker-compose -f docker-compose.dev.yml exec backend-core alembic upgrade head
```

### 2. 서비스 재시작
```bash
docker-compose -f docker-compose.dev.yml restart backend-core frontend
```

### 3. 확인
- 프론트엔드: http://localhost:5173
- API Docs: http://localhost:8000/docs
- 관리자 대시보드: http://localhost:5173/admin

## API 엔드포인트

### 1. 피드백 제출
```http
POST /api/v1/feedback/
Content-Type: application/json
X-Session-Id: {session_id}  # 비로그인 사용자
Authorization: Bearer {token}  # 로그인 사용자

{
  "product_id": 123,
  "feedback_type": "like",
  "search_query": "빨간색 니트"
}
```

**응답:**
```json
{
  "success": true,
  "message": "피드백이 등록되었습니다.",
  "current_feedback_type": "like"
}
```

### 2. 통계 조회
```http
GET /api/v1/feedback/stats/123
```

**응답 (일반 사용자):**
```json
{
  "like_count": 125,
  "dislike_count": 0,
  "like_ratio": 1.0
}
```

**응답 (관리자):**
```json
{
  "like_count": 125,
  "dislike_count": 8,
  "like_ratio": 0.94
}
```

### 3. 내 피드백 조회
```http
GET /api/v1/feedback/my-feedback/123
```

**응답:**
```json
{
  "id": 456,
  "product_id": 123,
  "feedback_type": "like",
  "search_query": "빨간색 니트",
  "created_at": "2025-12-11T10:30:00Z"
}
```

### 4. 관리자 전용: 최근 피드백 목록
```http
GET /api/v1/feedback/admin/recent?limit=100
Authorization: Bearer {admin_token}
```

**응답:**
```json
[
  {
    "id": 1,
    "user_id": 5,
    "session_id": null,
    "product_id": 123,
    "feedback_type": "like",
    "search_query": "빨간색 니트",
    "created_at": "2025-12-11T10:30:00Z"
  }
]
```

## 데이터베이스 스키마

```sql
CREATE TABLE search_feedbacks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    product_id INTEGER REFERENCES products(id) ON DELETE CASCADE NOT NULL,
    feedback_type VARCHAR(20) NOT NULL,
    search_query TEXT,
    search_context JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

-- 인덱스
CREATE INDEX ix_search_feedbacks_id ON search_feedbacks(id);
CREATE INDEX ix_search_feedbacks_user_id ON search_feedbacks(user_id);
CREATE INDEX ix_search_feedbacks_session_id ON search_feedbacks(session_id);
CREATE INDEX ix_search_feedbacks_product_id ON search_feedbacks(product_id);
CREATE INDEX ix_feedback_user_product ON search_feedbacks(user_id, product_id);
CREATE INDEX ix_feedback_session_product ON search_feedbacks(session_id, product_id);
CREATE INDEX ix_feedback_product_type ON search_feedbacks(product_id, feedback_type);
```

## 사용자 플로우

### 비로그인 사용자
1. 페이지 방문 시 자동으로 세션 ID 생성 (localStorage에 저장)
2. 피드백 버튼 클릭 → API 요청 시 `X-Session-Id` 헤더로 전송
3. 같은 브라우저에서는 세션 ID 유지 (새로고침 후에도 피드백 유지)

### 로그인 사용자
1. 로그인 → JWT 토큰 발급
2. 피드백 버튼 클릭 → API 요청 시 `Authorization` 헤더로 전송
3. DB에 user_id로 저장

### 관리자
1. 상품 상세 페이지에서 좋아요 + 싫어요 버튼 모두 표시
2. 관리자 대시보드에서 최근 피드백 목록 확인
3. 만족도 비율 확인 가능

## 주의사항

### 마이그레이션 실행
- **반드시 Docker 환경에서 실행해야 합니다**
- 마이그레이션 실패 시 롤백:
  ```bash
  docker-compose -f docker-compose.dev.yml exec backend-core alembic downgrade -1
  ```

### 세션 ID
- 브라우저 localStorage에 저장됨
- 개발자 도구에서 삭제 가능: `localStorage.removeItem('modify_session_id')`

## 트러블슈팅

### Q1. 피드백 버튼이 작동하지 않아요
**원인**: DB 마이그레이션이 실행되지 않았을 수 있습니다.
**해결**: 위의 "DB 마이그레이션 실행" 절차를 따라주세요.

### Q2. 관리자인데 싫어요 버튼이 안 보여요
**원인**: 프론트엔드에서 관리자 권한이 제대로 인식되지 않았을 수 있습니다.
**해결**:
1. 로그아웃 후 재로그인
2. 개발자 도구 → Application → Local Storage → `auth-storage` 확인
3. `isAdmin` 값이 `true`인지 확인

### Q3. 세션 ID가 계속 변경돼요
**원인**: localStorage가 제대로 작동하지 않거나 브라우저 설정 문제
**해결**:
1. 시크릿 모드가 아닌지 확인
2. 쿠키/저장소 차단 설정 확인

## 향후 개선 사항
- [ ] 검색 결과 페이지에서도 피드백 버튼 추가
- [ ] 피드백 통계 차트 시각화
- [ ] 상품별 피드백 상세 분석 페이지
- [ ] CSV 내보내기 기능

## 기술 스택
- **Backend**: FastAPI, PostgreSQL, SQLAlchemy, Alembic
- **Frontend**: React, TypeScript, Axios, Zustand
- **Auth**: JWT (로그인), Session ID (비로그인)
- **UI**: Tailwind CSS, Lucide Icons

---

구현 완료일: 2025-12-11
작성자: Claude Code Assistant
