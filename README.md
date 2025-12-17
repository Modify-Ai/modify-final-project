# 🛍️ MODIFY - AI Fashion Search Platform

**MODIFY**는 BERT와 CLIP 모델을 결합한 **하이브리드 AI 엔진**을 탑재하여, 텍스트의 맥락과 이미지의 스타일을 동시에 분석하는 차세대 패션 검색 플랫폼입니다.

## 🛠️ 기술 스택 (Tech Stack)

### Backend & AI
* **Framework:** FastAPI, Python 3.11
* **Database:** PostgreSQL 16 (pgvector), SQLAlchemy (Async), Redis
* **AI Engine:** * **Text Model:** **BERT** (Sentence-Transformers `mpnet-base`) - 768차원 텍스트 임베딩
    * **Vision Model:** **CLIP** (OpenAI `ViT-B/32`) - 512차원 이미지/텍스트 멀티모달 임베딩
    * **LLM:** IBM Watsonx.ai (RAG 기반 트렌드 분석)
* **Object Detection:** YOLOv8 (패션 아이템 탐지 및 크롭)

### Frontend
* **Framework:** React, Vite, TypeScript
* **State Management:** Zustand, TanStack Query
* **Style:** TailwindCSS, Framer Motion
* **Visualization:** Recharts (관리자 대시보드)

### DevOps
* **Infrastructure:** Docker, Docker Compose
* **Server:** Nginx (Reverse Proxy)

---

## 🚀 AI 모델 아키텍처 (Core Features)

이 프로젝트는 두 가지 벡터 검색 기술을 결합하여 최적의 검색 결과를 제공합니다.

1.  **텍스트 의미 검색 (Semantic Text Search)**
    * **Model:** BERT (768-dim)
    * **Role:** 사용자가 입력한 문장의 의도와 뉘앙스를 파악하여 상품 이름/설명과 매칭합니다. (예: "가을에 입기 좋은 차분한 코트")
    
2.  **이미지 스타일 검색 (Visual Style Search)**
    * **Model:** CLIP (512-dim)
    * **Role:** 상품의 시각적 특징(색감, 핏, 기장)을 분석합니다. 상의(`Upper`)와 하의(`Lower`)를 YOLO로 분리하여 디테일한 부분 검색이 가능합니다.

---

## 🚀 설치 및 실행 가이드 (Setup Guide)

### 1. 프로젝트 클론 (Clone)
```bash
git clone <REPOSITORY_URL>
cd modify-final-project

2. 환경 변수 설정 (Environment Variables)
Bash

cp .env.example .env.dev
.env.dev 파일에 WATSONX_API_KEY, GOOGLE_API_KEY, DB_PASSWORD 등을 설정합니다.

3. 도커 컨테이너 실행 (Run)
Bash

docker-compose -f docker-compose.dev.yml up -d --build
💾 데이터베이스 초기화 (Database Initialization)
[필수] 처음 실행 시 DB 스키마와 벡터 컬럼을 생성하기 위해 아래 SQL을 실행해야 합니다.

실행 방법
Bash

# 실행 중인 DB 컨테이너에 접속하여 SQL 실행
docker-compose -f docker-compose.dev.yml exec postgres psql -U modify_user -d modify_db
(아래 SQL 전체를 복사해서 붙여넣고 Enter)

초기화 SQL (Schema Script)
SQL

-- 1. 트랜잭션 시작 및 기존 테이블 정리
BEGIN;
DROP TABLE IF EXISTS wishlists CASCADE;
DROP TABLE IF EXISTS products CASCADE;
DROP TABLE IF EXISTS users CASCADE;

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
    birthdate VARCHAR(20),
    location VARCHAR(100),
    gender VARCHAR(10),
    is_marketing_agreed BOOLEAN DEFAULT FALSE,
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
    
    -- [AI Vector Columns]
    embedding vector(768),             -- BERT (Text Context)
    embedding_clip vector(512),        -- CLIP (Full Image Context)
    embedding_clip_upper vector(512),  -- CLIP (Upper Crop)
    embedding_clip_lower vector(512),  -- CLIP (Lower Crop)
    
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

-- 6. 변경사항 확정
COMMIT;
✅ 주요 접속 경로 (URLs)
Main Service: http://localhost

Admin Dashboard: http://localhost/admin

API Swagger: http://localhost/docs


