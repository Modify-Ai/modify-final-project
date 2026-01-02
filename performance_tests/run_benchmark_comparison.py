"""
AI 모델 벤치마크 비교 테스트
- BERT + CLIP (현재 사용)
- Grounding DINO
- LLaVA-Next
- YOLO 단일
"""
import asyncio
import aiohttp
import statistics
import time
import json
from datetime import datetime

# 설정
AI_SERVICE_URL = "http://localhost:8005"
TEST_ITERATIONS = 10

# 테스트 쿼리
TEST_QUERIES = [
    "검은색 가디건",
    "겨울 패딩",
    "화이트 티셔츠",
    "청바지",
    "운동화"
]


class ModelBenchmark:
    def __init__(self):
        self.results = {
            "BERT (현재)": [],
            "CLIP (현재)": [],
            "Grounding DINO": [],
            "LLaVA-Next": [],
            "YOLO 단일": []
        }

    async def test_all_models(self):
        """모든 모델 테스트"""
        print(f"[START] 모델 벤치마크 테스트 시작")
        print(f"테스트 쿼리 수: {len(TEST_QUERIES)}")
        print(f"각 쿼리당 반복: {TEST_ITERATIONS}회\n")

        async with aiohttp.ClientSession() as session:
            for query in TEST_QUERIES:
                print(f"\n[TEST] 쿼리: '{query}'")

                for i in range(TEST_ITERATIONS):
                    try:
                        async with session.post(
                            f"{AI_SERVICE_URL}/api/v1/benchmark/compare-all",
                            json={"query": query},
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            if response.status == 200:
                                data = await response.json()
                                results = data.get("results", {})

                                # BERT
                                if "BERT (현재)" in results:
                                    self.results["BERT (현재)"].append(
                                        results["BERT (현재)"]["elapsed_ms"]
                                    )

                                # CLIP
                                if "CLIP (현재)" in results:
                                    self.results["CLIP (현재)"].append(
                                        results["CLIP (현재)"]["elapsed_ms"]
                                    )

                                # Grounding DINO
                                if "Grounding DINO" in results:
                                    self.results["Grounding DINO"].append(
                                        results["Grounding DINO"]["elapsed_ms"]
                                    )

                                # LLaVA-Next
                                if "LLaVA-Next" in results:
                                    self.results["LLaVA-Next"].append(
                                        results["LLaVA-Next"]["elapsed_ms"]
                                    )

                                # YOLO 단일
                                if "YOLO 단일" in results:
                                    self.results["YOLO 단일"].append(
                                        results["YOLO 단일"]["elapsed_ms"]
                                    )

                                print(f"  [OK] 반복 {i+1}/{TEST_ITERATIONS}")

                    except Exception as e:
                        print(f"  [ERROR] 반복 {i+1} 실패: {e}")

                    # 과부하 방지
                    await asyncio.sleep(0.1)

        self.calculate_statistics()

    def calculate_statistics(self):
        """통계 계산"""
        print("\n\n" + "="*80)
        print("모델별 성능 통계")
        print("="*80)

        summary = {}

        for model_name, times in self.results.items():
            if times:
                summary[model_name] = {
                    "avg": statistics.mean(times),
                    "min": min(times),
                    "max": max(times),
                    "median": statistics.median(times),
                    "count": len(times)
                }

                print(f"\n{model_name}:")
                print(f"  평균: {summary[model_name]['avg']:.2f}ms")
                print(f"  최소: {summary[model_name]['min']:.2f}ms")
                print(f"  최대: {summary[model_name]['max']:.2f}ms")
                print(f"  중간값: {summary[model_name]['median']:.2f}ms")
                print(f"  테스트 수: {summary[model_name]['count']}")
            else:
                print(f"\n{model_name}: 데이터 없음")

        # JSON 저장
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"benchmark_comparison_{timestamp}.json"

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 결과 저장: {filename}")

        # 비교 출력
        print("\n\n" + "="*80)
        print("성능 비교 (평균 응답 시간)")
        print("="*80)

        sorted_models = sorted(summary.items(), key=lambda x: x[1]['avg'])

        for i, (model_name, stats) in enumerate(sorted_models, 1):
            print(f"{i}. {model_name}: {stats['avg']:.2f}ms")


async def main():
    benchmark = ModelBenchmark()
    await benchmark.test_all_models()


if __name__ == "__main__":
    asyncio.run(main())
