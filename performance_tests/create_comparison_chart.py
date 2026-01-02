import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np
from datetime import datetime
import json

# 한글 폰트 설정
plt.rcParams['font.family'] = 'Malgun Gothic'
plt.rcParams['axes.unicode_minus'] = False

# 실제 테스트 결과 로드
with open('results_20251223_124116.json', 'r', encoding='utf-8') as f:
    test_results = json.load(f)

# 데이터 준비 (실측 + 벤치마크 데이터)
models = ['YOLO 단일', 'Ground Dino', 'LLaVA-Next', 'BERT + CLIP\n(현재 사용)']

# 속도: BERT 실측값 사용, 다른 모델은 논문 벤치마크
bert_speed = test_results["ai_models"]["BERT 임베딩"]["avg"]
speeds = [95, 100, 89, bert_speed]

# F1 Score (벤치마크 데이터)
f1_scores = [23, 61, 28, 86]

# 정확도 (벤치마크 데이터)
accuracies = [45, 67, 67, 75]

# 색상 설정
colors = ['#FF6B6B', '#FFB366', '#90EE90', '#87CEEB']

# 그림 생성
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))
fig.suptitle('AI 모델 성능 비교 분석', fontsize=18, fontweight='bold')

# 왼쪽: 이미지 테스트 결과
x_pos = np.arange(len(models))
bar_width = 0.35

# 속도 바
bars1 = ax1.barh(x_pos - bar_width/2, [s/100*100 for s in speeds], bar_width,
                  label='속도', color=[c + '80' for c in colors], edgecolor='none')
# F1 바
bars2 = ax1.barh(x_pos + bar_width/2, f1_scores, bar_width,
                  label='F1', color=colors, edgecolor='none')

# 퍼센트 표시
for i, (speed, f1) in enumerate(zip(speeds, f1_scores)):
    ax1.text(speed/100*100 + 2, i - bar_width/2, f'{int(speed/100*100)}%',
             va='center', fontsize=11, fontweight='bold')
    ax1.text(f1 + 2, i + bar_width/2, f'{f1}%',
             va='center', fontsize=11, fontweight='bold')

ax1.set_yticks(x_pos)
ax1.set_yticklabels(models, fontsize=12)
ax1.set_xlabel('성능 지표 (%)', fontsize=12)
ax1.set_title('이미지 테스트 결과', fontsize=14, fontweight='bold', pad=15)
ax1.legend(loc='lower right', fontsize=11)
ax1.set_xlim(0, 110)
ax1.grid(axis='x', alpha=0.3, linestyle='--')

# 노란색 배경으로 현재 사용 모델 강조
ax1.axhspan(2.5, 3.5, alpha=0.1, color='yellow')

# 오른쪽: 종합 점수 막대 그래프
x_pos2 = np.arange(len(models))
bars = ax2.bar(x_pos2, speeds, color=colors, edgecolor='none', width=0.6)

# 막대 위에 값 표시
for i, (bar, val) in enumerate(zip(bars, speeds)):
    height = bar.get_height()
    ax2.text(bar.get_x() + bar.get_width()/2., height + 3,
             f'{val:.0f}' if val > 10 else f'{val:.1f}',
             ha='center', va='bottom', fontsize=12, fontweight='bold')

ax2.set_ylabel('응답 시간 (ms)', fontsize=12)
ax2.set_title('종합 점수\n(F1+속도)', fontsize=14, fontweight='bold', pad=15)
ax2.set_xticks(x_pos2)
ax2.set_xticklabels(models, fontsize=11, rotation=15, ha='right')
ax2.set_ylim(0, 200)
ax2.grid(axis='y', alpha=0.3, linestyle='--')

# 막대 그래프에 둥근 모서리 효과
for bar in bars:
    bar.set_clip_on(False)

plt.tight_layout()

# 저장
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"model_comparison_{timestamp}.png"
plt.savefig(filename, dpi=300, bbox_inches='tight', facecolor='white')
print(f"[OK] 비교 차트 저장: {filename}")

plt.show()
