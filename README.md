# 🛍️ MODIFY - AI Fashion Search Platform

**MODIFY**는 BERT와 CLIP 모델을 결합한 **하이브리드 AI 엔진**을 탑재하여, 텍스트의 맥락과 이미지의 스타일을 동시에 분석하는 차세대 패션 검색 플랫폼입니다.

---

## 🛠️ 기술 스택 (Tech Stack)

*   **Backend & AI**: FastAPI, Python 3.11, PostgreSQL (pgvector), SQLAlchemy, Redis, Celery
*   **AI Engine**:
    *   **Text Model**: `BERT` (Sentence-Transformers `multi-qa-mpnet-base-dot-v1`) - 768차원 텍스트 임베딩
    *   **Vision Model**: `CLIP` (OpenAI `ViT-B/32`) - 512차원 이미지/텍스트 멀티모달 임베딩
    *   **LLM**: IBM Watsonx.ai (RAG 기반 트렌드 분석)
    *   **Object Detection**: YOLOv8 (패션 아이템 탐지 및 크롭)
*   **Frontend**: React, Vite, TypeScript, Zustand, TanStack Query, TailwindCSS, Framer Motion
*   **DevOps**: Docker, Docker Compose, Nginx

---

## 📖 설치 및 실행 가이드 (Setup and Run Guide)

이 프로젝트는 Docker Compose를 사용하여 모든 서비스를 한번에 실행합니다.

### ✅ 사전 요구사항 (Prerequisites)

*   **Docker Desktop**: [공식 홈페이지](https://www.docker.com/products/docker-desktop/)에서 설치하세요.

### 🚀 1단계: 프로젝트 클론 (Clone)

```bash
git clone https://github.com/Modify-Ai/modify-final-project.git
cd modify-final-project
```

### 🔑 2단계: 환경 변수 설정 (.env)

기본 환경 변수 파일을 복사하여 실제 사용할 설정 파일을 생성합니다.

```bash
cp .env.example .env.dev
```

이후, 생성된 `.env.dev` 파일을 열어 아래 **필수 값**들을 자신의 키로 채워주세요.

*   `WATSONX_API_KEY`: IBM Watsonx.ai API 키
*   `GOOGLE_API_KEY`: Google Custom Search API 키
*   `POSTGRES_PASSWORD`: 데이터베이스 비밀번호 (원하는 값으로 설정)
*   `REPLICATE_API_TOKEN`: Replicate API 키

### 🐳 3단계: Docker 컨테이너 실행

아래 명령어를 실행하면 모든 서비스(DB, 백엔드, AI, 프론트엔드)가 빌드되고 실행됩니다.

```bash
docker-compose -f docker-compose.dev.yml up -d --build
```
> 💡 최초 빌드 시 AI 모델 다운로드 등으로 인해 시간이 다소 소요될 수 있습니다.

### 💾 4단계: 데이터베이스 스키마 생성

컨테이너가 실행된 후, **별도의 터미널**에서 아래 명령어를 딱 한 번 실행하여 데이터베이스 테이블과 AI 검색에 필요한 설정을 적용합니다.

```bash
docker-compose -f docker-compose.dev.yml exec backend-core alembic upgrade head
```
이 명령어는 Alembic을 사용하여 최신 버전의 데이터베이스 스키마를 자동으로 생성해줍니다. (기존 README의 복잡한 SQL 수동 실행을 대체합니다.)

### 🎉 실행 완료!

모든 설정이 완료되었습니다. 이제 웹 브라우저에서 아래 주소로 접속하세요.

*   **메인 서비스**: [http://localhost](http://localhost)
*   **API 문서 (Swagger)**: [http://localhost/docs](http://localhost/docs)
*   **관리자용 대시보드**: [http://localhost/admin](http://localhost/admin)
    *   초기 관리자 계정은 `.env.dev` 파일에 설정된 `SUPERUSER_EMAIL`과 `SUPERUSER_PASSWORD`로 자동 생성됩니다.

---

## 셧다운 (Shutdown)

프로젝트를 종료하려면 아래 명령어를 사용하세요.

```bash
docker-compose -f docker-compose.dev.yml down
```
> `-v` 옵션을 추가하면 Docker 볼륨(DB 데이터 등)까지 모두 삭제되니 주의하세요.

---

## ✨ 주요 기능 (Key Features)

### 🛒 주문 및 결제 시스템
- **주문 내역 관리**: 사용자별 주문 내역 조회 및 관리
- **주문 상태 추적**: 결제 대기, 결제 완료, 배송 중, 배송 완료, 취소 상태 관리
- **주문 취소**: 결제 대기 상태의 주문 취소 기능
- **상세 배송 정보**: 수령인 정보, 배송 주소, 배송 메모 관리

### 🔍 AI 기반 스마트 검색
- **하이브리드 검색 엔진**: BERT(텍스트) + CLIP(이미지) 듀얼 모델 결합
- **네거티브 프롬프트**: 원하지 않는 스타일 제외 검색 지원
- **멀티모달 검색**: 텍스트와 이미지를 동시에 활용한 정교한 검색

### 👤 사용자 관리
- **회원가입/로그인**: JWT 기반 인증 시스템
- **위시리스트**: 관심 상품 저장 및 관리
- **프로필 관리**: 개인정보 및 배송지 관리

---

## DB 테이블 수정사항
```bash

-- 1. 트랜잭션 시작 및 기존 테이블 정리
BEGIN;
DROP TABLE IF EXISTS order_items CASCADE;
DROP TABLE IF EXISTS orders CASCADE;
DROP TABLE IF EXISTS wishlists CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS fitting_results CASCADE;

-- 2. 벡터 확장 기능 활성화 (AI 핵심)
CREATE EXTENSION IF NOT EXISTS vector;

-- 3. Users 테이블 생성
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    is_active BOOLEAN DEFAULT TRUE,
    is_superuser BOOLEAN DEFAULT FALSE,
    phone_number VARCHAR(50),
    address VARCHAR(255),
    zip_code VARCHAR(20),
    detail_address VARCHAR(255),
    birthdate VARCHAR(20),
    gender VARCHAR(10),
    is_marketing_agreed BOOLEAN DEFAULT FALSE,
    is_phone_verified BOOLEAN DEFAULT false,
    profile_image VARCHAR(500),
    provider VARCHAR(50) DEFAULT 'local',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 4. Products 테이블 생성 (BERT + CLIP 벡터 포함)
CREATE TABLE products (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price INTEGER NOT NULL,
    stock_quantity INTEGER NOT NULL DEFAULT 0,
    category VARCHAR(100),
    image_url VARCHAR(500),
    is_active BOOLEAN DEFAULT TRUE NOT NULL,
    gender VARCHAR(50) DEFAULT 'Unisex',
    embedding vector(768),
    embedding_clip vector(512),
    embedding_clip_upper vector(512),
    embedding_clip_lower vector(512),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE
);

-- 5. Wishlists 테이블 생성
CREATE TABLE wishlists (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_wishlist_user_product UNIQUE (user_id, product_id)
);

-- 6. Orders 테이블 생성 (주문 정보)
CREATE TABLE orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    order_number VARCHAR(50) UNIQUE NOT NULL,
    total_amount INTEGER NOT NULL,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    payment_status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    recipient_name VARCHAR(100) NOT NULL,
    recipient_phone VARCHAR(20) NOT NULL,
    zip_code VARCHAR(10) NOT NULL,
    address VARCHAR(200) NOT NULL,
    detail_address VARCHAR(200),
    delivery_memo TEXT,
    payment_method VARCHAR(50),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_orders_id ON orders (id);
CREATE INDEX ix_orders_order_number ON orders (order_number);

-- 7. Order Items 테이블 생성 (주문 상품 정보)
CREATE TABLE order_items (
    id SERIAL PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    product_id INTEGER NOT NULL REFERENCES products(id),
    product_name VARCHAR(200) NOT NULL,
    product_price INTEGER NOT NULL,
    product_image_url VARCHAR(500),
    quantity INTEGER DEFAULT 1 NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX ix_order_items_id ON order_items (id);

-- 8. fitting_results 테이블 생성
CREATE TABLE fitting_results (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    result_image_url VARCHAR NOT NULL,
    category VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now()
);
CREATE INDEX ix_fitting_results_id ON fitting_results (id);

-- 9. 변경사항 확정
COMMIT;
