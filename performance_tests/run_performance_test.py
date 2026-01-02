"""
MODIFY 프로젝트 종합 성능 테스트
- AI 모델 응답 시간
- API 엔드포인트 응답 시간
- 데이터베이스 쿼리 성능
- 시스템 처리량 (동시 요청)
- 코사인 유사도 정확도
"""

import asyncio
import aiohttp
import time
import numpy as np
import matplotlib.pyplot as plt
import matplotlib
from typing import List, Dict, Any
from datetime import datetime
import json
import statistics

# 한글 폰트 설정
matplotlib.rcParams['font.family'] = 'Malgun Gothic'  # Windows
matplotlib.rcParams['axes.unicode_minus'] = False

# 테스트 설정
BASE_URL = "http://localhost"
AI_SERVICE_URL = "http://localhost:8005"
TEST_ITERATIONS = 10  # 각 테스트당 반복 횟수
CONCURRENT_REQUESTS = [1, 5, 10, 20, 50]  # 동시 요청 수


class PerformanceTester:
    def __init__(self):
        self.results = {
            "ai_models": {},
            "api_endpoints": {},
            "database_queries": {},
            "throughput": {},
            "cosine_similarity": {}
        }
        self.token = None

    async def login(self, session: aiohttp.ClientSession):
        """로그인하여 JWT 토큰 획득"""
        try:
            async with session.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={"email": "admin@modify.com", "password": "super_secure_password1"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    self.token = data.get("access_token")
                    print("[OK] 로그인 성공")
                    return True
        except Exception as e:
            print(f"[ERROR] 로그인 실패: {e}")
        return False

    async def test_ai_model_performance(self, session: aiohttp.ClientSession):
        """AI 모델별 응답 시간 측정 (7개 모델)"""
        print("\n[TEST] AI 모델 성능 테스트 중...")

        # 테스트용 샘플 이미지 (1x1 픽셀 흰색 이미지 base64)
        sample_image_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="

        tests = {
            "BERT 임베딩": {
                "url": f"{AI_SERVICE_URL}/api/v1/process-internal",
                "payload": {"query": "검은색 가디건"}
            },
            "CLIP 텍스트": {
                "url": f"{AI_SERVICE_URL}/api/v1/determine-path",
                "payload": {"query": "겨울 패딩"}
            },
            "CLIP 이미지": {
                "url": f"{AI_SERVICE_URL}/api/v1/generate-clip-vector",
                "payload": {"image_b64": sample_image_b64}
            },
            "LLM 텍스트 생성": {
                "url": f"{AI_SERVICE_URL}/api/v1/llm-generate-response",
                "payload": {
                    "prompt": "사용자 질문: 이 상품 소재가 뭐야?\n상품명: 울 코트\n카테고리: Outerwear"
                }
            },
            "YOLO 객체 탐지": {
                "url": f"{AI_SERVICE_URL}/api/v1/generate-fashion-clip-vector",
                "payload": {"image_b64": sample_image_b64, "target": "full"}
            },
            "YOLO 포즈 추정": {
                "url": f"{AI_SERVICE_URL}/api/v1/generate-fashion-clip-vector",
                "payload": {"image_b64": sample_image_b64, "target": "upper"}
            },
            "YOLO 세그멘테이션": {
                "url": f"{AI_SERVICE_URL}/api/v1/generate-mask",
                "payload": {"image_b64": sample_image_b64, "target": "upper"}
            }
        }

        for model_name, test_config in tests.items():
            times = []
            for i in range(TEST_ITERATIONS):
                start = time.time()
                try:
                    async with session.post(
                        test_config["url"],
                        json=test_config["payload"],
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        await response.text()
                        elapsed = time.time() - start
                        times.append(elapsed * 1000)  # ms로 변환
                except Exception as e:
                    print(f"  [WARN] {model_name} 테스트 {i+1} 실패: {e}")
                    times.append(None)

            valid_times = [t for t in times if t is not None]
            if valid_times:
                self.results["ai_models"][model_name] = {
                    "avg": statistics.mean(valid_times),
                    "min": min(valid_times),
                    "max": max(valid_times),
                    "median": statistics.median(valid_times)
                }
                print(f"  [OK] {model_name}: 평균 {self.results['ai_models'][model_name]['avg']:.2f}ms")

    async def test_api_endpoints(self, session: aiohttp.ClientSession):
        """API 엔드포인트 응답 시간 측정"""
        print("\n[TEST] API 엔드포인트 성능 테스트 중...")

        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}

        tests = {
            "상품 목록 조회": {
                "method": "GET",
                "url": f"{BASE_URL}/api/v1/products?page=1&limit=12"
            },
            "상품 검색 (텍스트)": {
                "method": "POST",
                "url": f"{BASE_URL}/api/v1/products/search",
                "payload": {"query": "겨울 코트", "page": 1, "limit": 12}
            },
            "사용자 정보 조회": {
                "method": "GET",
                "url": f"{BASE_URL}/api/v1/users/me",
                "headers": headers
            },
            "주문 목록 조회": {
                "method": "GET",
                "url": f"{BASE_URL}/api/v1/orders/my-orders?page=1&limit=10",
                "headers": headers
            }
        }

        for endpoint_name, test_config in tests.items():
            times = []
            for i in range(TEST_ITERATIONS):
                start = time.time()
                try:
                    request_headers = test_config.get("headers", {})
                    if test_config["method"] == "GET":
                        async with session.get(
                            test_config["url"],
                            headers=request_headers,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            await response.text()
                            elapsed = time.time() - start
                            times.append(elapsed * 1000)
                    else:
                        async with session.post(
                            test_config["url"],
                            json=test_config.get("payload", {}),
                            headers=request_headers,
                            timeout=aiohttp.ClientTimeout(total=10)
                        ) as response:
                            await response.text()
                            elapsed = time.time() - start
                            times.append(elapsed * 1000)
                except Exception as e:
                    print(f"  [WARN] {endpoint_name} 테스트 {i+1} 실패: {e}")
                    times.append(None)

            valid_times = [t for t in times if t is not None]
            if valid_times:
                self.results["api_endpoints"][endpoint_name] = {
                    "avg": statistics.mean(valid_times),
                    "min": min(valid_times),
                    "max": max(valid_times),
                    "median": statistics.median(valid_times)
                }
                print(f"  [OK] {endpoint_name}: 평균 {self.results['api_endpoints'][endpoint_name]['avg']:.2f}ms")

    async def test_database_performance(self, session: aiohttp.ClientSession):
        """데이터베이스 쿼리 성능 측정"""
        print("\n[TEST] 데이터베이스 성능 테스트 중...")

        tests = {
            "벡터 검색 (BERT)": {
                "url": f"{BASE_URL}/api/v1/products/search",
                "payload": {"query": "검은색 가디건", "page": 1, "limit": 12}
            },
            "일반 필터링 쿼리": {
                "method": "GET",
                "url": f"{BASE_URL}/api/v1/products?category=Outerwear&page=1&limit=12"
            },
            "복합 쿼리 (검색+필터)": {
                "url": f"{BASE_URL}/api/v1/products/search",
                "payload": {"query": "코트", "category": "Outerwear"}
            }
        }

        for query_name, test_config in tests.items():
            times = []
            for i in range(TEST_ITERATIONS):
                start = time.time()
                try:
                    if test_config.get("method") == "GET":
                        async with session.get(
                            test_config["url"],
                            timeout=aiohttp.ClientTimeout(total=15)
                        ) as response:
                            await response.text()
                            elapsed = time.time() - start
                            times.append(elapsed * 1000)
                    else:
                        async with session.post(
                            test_config["url"],
                            json=test_config.get("payload", {}),
                            timeout=aiohttp.ClientTimeout(total=15)
                        ) as response:
                            await response.text()
                            elapsed = time.time() - start
                            times.append(elapsed * 1000)
                except Exception as e:
                    print(f"  [WARN] {query_name} 테스트 {i+1} 실패: {e}")
                    times.append(None)

            valid_times = [t for t in times if t is not None]
            if valid_times:
                self.results["database_queries"][query_name] = {
                    "avg": statistics.mean(valid_times),
                    "min": min(valid_times),
                    "max": max(valid_times),
                    "median": statistics.median(valid_times)
                }
                print(f"  [OK] {query_name}: 평균 {self.results['database_queries'][query_name]['avg']:.2f}ms")

    async def test_throughput(self, session: aiohttp.ClientSession):
        """시스템 처리량 테스트 (동시 요청 처리)"""
        print("\n[TEST] 시스템 처리량 테스트 중...")

        async def make_request():
            start = time.time()
            try:
                async with session.get(
                    f"{BASE_URL}/api/v1/products?page=1&limit=12",
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    await response.text()
                    return time.time() - start
            except:
                return None

        for concurrent in CONCURRENT_REQUESTS:
            print(f"  [RUN] 동시 요청 {concurrent}개 테스트 중...")
            total_start = time.time()

            tasks = [make_request() for _ in range(concurrent)]
            results = await asyncio.gather(*tasks)

            total_elapsed = time.time() - total_start
            valid_results = [r for r in results if r is not None]

            if valid_results:
                self.results["throughput"][f"{concurrent}개"] = {
                    "total_time": total_elapsed * 1000,
                    "avg_response_time": statistics.mean([r * 1000 for r in valid_results]),
                    "requests_per_second": len(valid_results) / total_elapsed,
                    "success_rate": len(valid_results) / concurrent * 100
                }
                print(f"    [OK] 처리율: {self.results['throughput'][f'{concurrent}개']['requests_per_second']:.2f} req/s")

    async def test_cosine_similarity(self, session: aiohttp.ClientSession):
        """코사인 유사도 정확도 측정"""
        print("\n[TEST] 코사인 유사도 정확도 테스트 중...")

        # 테스트 쿼리 쌍 (유사한 쿼리)
        similar_queries = [
            ("겨울 코트", "따뜻한 외투"),
            ("검은색 청바지", "블랙 데님 팬츠"),
            ("여름 원피스", "시원한 드레스"),
            ("운동화", "스니커즈"),
            ("정장 셔츠", "포멀 와이셔츠")
        ]

        # 테스트 쿼리 쌍 (다른 쿼리)
        dissimilar_queries = [
            ("겨울 코트", "여름 반바지"),
            ("구두", "모자"),
            ("스커트", "장갑"),
            ("니트", "선글라스"),
            ("가방", "양말")
        ]

        similar_scores = []
        dissimilar_scores = []

        # 유사한 쿼리 테스트
        for query1, query2 in similar_queries:
            try:
                # 첫 번째 쿼리 임베딩
                async with session.post(
                    f"{AI_SERVICE_URL}/api/v1/process-internal",
                    json={"query": query1},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data1 = await response.json()
                    vec1 = np.array(data1["vectors"]["bert"])

                # 두 번째 쿼리 임베딩
                async with session.post(
                    f"{AI_SERVICE_URL}/api/v1/process-internal",
                    json={"query": query2},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data2 = await response.json()
                    vec2 = np.array(data2["vectors"]["bert"])

                # 코사인 유사도 계산
                similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                similar_scores.append(similarity)
                print(f"  [OK] '{query1}' vs '{query2}': {similarity:.4f}")
            except Exception as e:
                print(f"  [WARN] 유사 쿼리 테스트 실패: {e}")

        # 다른 쿼리 테스트
        for query1, query2 in dissimilar_queries:
            try:
                async with session.post(
                    f"{AI_SERVICE_URL}/api/v1/process-internal",
                    json={"query": query1},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data1 = await response.json()
                    vec1 = np.array(data1["vectors"]["bert"])

                async with session.post(
                    f"{AI_SERVICE_URL}/api/v1/process-internal",
                    json={"query": query2},
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    data2 = await response.json()
                    vec2 = np.array(data2["vectors"]["bert"])

                similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
                dissimilar_scores.append(similarity)
                print(f"  [OK] '{query1}' vs '{query2}': {similarity:.4f}")
            except Exception as e:
                print(f"  [WARN] 비유사 쿼리 테스트 실패: {e}")

        if similar_scores and dissimilar_scores:
            self.results["cosine_similarity"] = {
                "similar_avg": statistics.mean(similar_scores),
                "similar_min": min(similar_scores),
                "similar_max": max(similar_scores),
                "dissimilar_avg": statistics.mean(dissimilar_scores),
                "dissimilar_min": min(dissimilar_scores),
                "dissimilar_max": max(dissimilar_scores),
                "separation": statistics.mean(similar_scores) - statistics.mean(dissimilar_scores)
            }
            print(f"\n  [RESULT] 유사 쿼리 평균 유사도: {self.results['cosine_similarity']['similar_avg']:.4f}")
            print(f"  [RESULT] 비유사 쿼리 평균 유사도: {self.results['cosine_similarity']['dissimilar_avg']:.4f}")
            print(f"  [RESULT] 분리도: {self.results['cosine_similarity']['separation']:.4f}")

    def plot_results(self):
        """결과를 선 그래프로 시각화"""
        print("\n[PLOT] 결과 그래프 생성 중...")

        fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        fig.suptitle('MODIFY 프로젝트 종합 성능 테스트 결과', fontsize=16, fontweight='bold')

        # 1. AI 모델 성능
        if self.results["ai_models"]:
            ax = axes[0, 0]
            models = list(self.results["ai_models"].keys())
            avg_times = [self.results["ai_models"][m]["avg"] for m in models]

            ax.plot(range(len(models)), avg_times, marker='o', linewidth=2, markersize=8, color='#2E86DE')
            ax.set_xticks(range(len(models)))
            ax.set_xticklabels(models, rotation=45, ha='right')
            ax.set_ylabel('응답 시간 (ms)', fontweight='bold')
            ax.set_title('AI 모델 응답 시간', fontweight='bold')
            ax.grid(True, alpha=0.3)

            for i, v in enumerate(avg_times):
                ax.text(i, v, f'{v:.1f}ms', ha='center', va='bottom')

        # 2. API 엔드포인트 성능
        if self.results["api_endpoints"]:
            ax = axes[0, 1]
            endpoints = list(self.results["api_endpoints"].keys())
            avg_times = [self.results["api_endpoints"][e]["avg"] for e in endpoints]

            ax.plot(range(len(endpoints)), avg_times, marker='s', linewidth=2, markersize=8, color='#10AC84')
            ax.set_xticks(range(len(endpoints)))
            ax.set_xticklabels(endpoints, rotation=45, ha='right')
            ax.set_ylabel('응답 시간 (ms)', fontweight='bold')
            ax.set_title('API 엔드포인트 응답 시간', fontweight='bold')
            ax.grid(True, alpha=0.3)

            for i, v in enumerate(avg_times):
                ax.text(i, v, f'{v:.1f}ms', ha='center', va='bottom')

        # 3. 데이터베이스 쿼리 성능
        if self.results["database_queries"]:
            ax = axes[0, 2]
            queries = list(self.results["database_queries"].keys())
            avg_times = [self.results["database_queries"][q]["avg"] for q in queries]

            ax.plot(range(len(queries)), avg_times, marker='^', linewidth=2, markersize=8, color='#EE5A6F')
            ax.set_xticks(range(len(queries)))
            ax.set_xticklabels(queries, rotation=45, ha='right')
            ax.set_ylabel('응답 시간 (ms)', fontweight='bold')
            ax.set_title('데이터베이스 쿼리 성능', fontweight='bold')
            ax.grid(True, alpha=0.3)

            for i, v in enumerate(avg_times):
                ax.text(i, v, f'{v:.1f}ms', ha='center', va='bottom')

        # 4. 시스템 처리량
        if self.results["throughput"]:
            ax = axes[1, 0]
            concurrents = list(self.results["throughput"].keys())
            rps = [self.results["throughput"][c]["requests_per_second"] for c in concurrents]

            ax.plot(range(len(concurrents)), rps, marker='D', linewidth=2, markersize=8, color='#F368E0')
            ax.set_xticks(range(len(concurrents)))
            ax.set_xticklabels(concurrents, rotation=0)
            ax.set_ylabel('초당 요청 수 (req/s)', fontweight='bold')
            ax.set_title('시스템 처리량 (동시 요청)', fontweight='bold')
            ax.grid(True, alpha=0.3)

            for i, v in enumerate(rps):
                ax.text(i, v, f'{v:.1f}', ha='center', va='bottom')

        # 5. 코사인 유사도
        if self.results["cosine_similarity"]:
            ax = axes[1, 1]
            categories = ['유사\n(평균)', '유사\n(최소)', '유사\n(최대)',
                         '비유사\n(평균)', '비유사\n(최소)', '비유사\n(최대)']
            values = [
                self.results["cosine_similarity"]["similar_avg"],
                self.results["cosine_similarity"]["similar_min"],
                self.results["cosine_similarity"]["similar_max"],
                self.results["cosine_similarity"]["dissimilar_avg"],
                self.results["cosine_similarity"]["dissimilar_min"],
                self.results["cosine_similarity"]["dissimilar_max"]
            ]

            ax.plot(range(len(categories)), values, marker='o', linewidth=2, markersize=8, color='#FFA502')
            ax.set_xticks(range(len(categories)))
            ax.set_xticklabels(categories, rotation=0)
            ax.set_ylabel('코사인 유사도', fontweight='bold')
            ax.set_title('코사인 유사도 정확도', fontweight='bold')
            ax.set_ylim([0, 1])
            ax.grid(True, alpha=0.3)
            ax.axhline(y=0.5, color='gray', linestyle='--', alpha=0.5)

            for i, v in enumerate(values):
                ax.text(i, v, f'{v:.3f}', ha='center', va='bottom')

        # 6. 종합 비교
        ax = axes[1, 2]
        categories = []
        avg_values = []

        if self.results["ai_models"]:
            categories.append('AI 모델')
            avg_values.append(statistics.mean([self.results["ai_models"][m]["avg"] for m in self.results["ai_models"]]))

        if self.results["api_endpoints"]:
            categories.append('API')
            avg_values.append(statistics.mean([self.results["api_endpoints"][e]["avg"] for e in self.results["api_endpoints"]]))

        if self.results["database_queries"]:
            categories.append('DB 쿼리')
            avg_values.append(statistics.mean([self.results["database_queries"][q]["avg"] for q in self.results["database_queries"]]))

        if avg_values:
            ax.plot(range(len(categories)), avg_values, marker='*', linewidth=3, markersize=15, color='#FF6348')
            ax.set_xticks(range(len(categories)))
            ax.set_xticklabels(categories)
            ax.set_ylabel('평균 응답 시간 (ms)', fontweight='bold')
            ax.set_title('카테고리별 평균 성능', fontweight='bold')
            ax.grid(True, alpha=0.3)

            for i, v in enumerate(avg_values):
                ax.text(i, v, f'{v:.1f}ms', ha='center', va='bottom', fontsize=10, fontweight='bold')

        plt.tight_layout()

        # 결과 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"results/performance_test_{timestamp}.png"
        plt.savefig(filename, dpi=300, bbox_inches='tight')
        print(f"[OK] 그래프 저장: {filename}")

        # JSON 결과도 저장
        json_filename = f"results/performance_test_{timestamp}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"[OK] JSON 결과 저장: {json_filename}")

        plt.show()

    async def warmup_ai_service(self, session: aiohttp.ClientSession):
        """AI 서비스 워밍업 (모델 로딩 대기)"""
        print("\n[WARMUP] AI 서비스 워밍업 중...")
        try:
            async with session.post(
                f"{AI_SERVICE_URL}/api/v1/process-internal",
                json={"query": "test"},
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                if response.status == 200:
                    print("  [OK] AI 서비스 준비 완료")
                    return True
        except Exception as e:
            print(f"  [WARN] AI 서비스 워밍업 실패: {e}")
        return False

    async def run_all_tests(self):
        """모든 테스트 실행"""
        print("[START] MODIFY 프로젝트 종합 성능 테스트 시작\n")
        print(f"테스트 시작: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"반복 횟수: {TEST_ITERATIONS}회\n")

        # 연결 풀 크기 증가
        connector = aiohttp.TCPConnector(limit=100, limit_per_host=30)
        timeout = aiohttp.ClientTimeout(total=300)

        async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
            await self.login(session)
            await self.warmup_ai_service(session)
            await self.test_ai_model_performance(session)
            await self.test_api_endpoints(session)
            await self.test_database_performance(session)
            await self.test_throughput(session)
            await self.test_cosine_similarity(session)

        self.plot_results()

        print(f"\n[DONE] 모든 테스트 완료!")
        print(f"테스트 종료: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    tester = PerformanceTester()
    asyncio.run(tester.run_all_tests())
