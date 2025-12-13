import React, { useState, useEffect } from 'react';
import { ThumbsUp, ThumbsDown } from 'lucide-react';
import { feedbackAPI, FeedbackStats, FeedbackDetail } from '../../api/feedback';
import { useAuthStore } from '../../store/authStore';

interface FeedbackButtonsProps {
  productId: number;
  searchQuery?: string;
  searchContext?: Record<string, any>;
  className?: string;
}

export const FeedbackButtons: React.FC<FeedbackButtonsProps> = ({
  productId,
  searchQuery,
  searchContext,
  className = ''
}) => {
  const { isAdmin } = useAuthStore();
  const [stats, setStats] = useState<FeedbackStats>({ like_count: 0, dislike_count: 0, like_ratio: 0 });
  const [myFeedback, setMyFeedback] = useState<FeedbackDetail | null>(null);
  const [loading, setLoading] = useState(false);

  // 통계 및 내 피드백 불러오기
  const loadData = async () => {
    try {
      const [statsData, myFeedbackData] = await Promise.all([
        feedbackAPI.getStats(productId),
        feedbackAPI.getMyFeedback(productId)
      ]);
      setStats(statsData);
      setMyFeedback(myFeedbackData);
    } catch (error) {
      console.error('Failed to load feedback data:', error);
    }
  };

  useEffect(() => {
    loadData();
  }, [productId]);

  // 피드백 제출 핸들러
  const handleFeedback = async (type: 'like' | 'dislike') => {
    if (loading) return;

    setLoading(true);
    try {
      const response = await feedbackAPI.submit({
        product_id: productId,
        feedback_type: type,
        search_query: searchQuery,
        search_context: searchContext
      });

      // 즉시 UI 업데이트
      await loadData();

      // 토스트 메시지 표시 (선택사항)
      console.log(response.message);
    } catch (error) {
      console.error('Failed to submit feedback:', error);
      alert('피드백 제출에 실패했습니다. 다시 시도해주세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={`flex items-center gap-3 ${className}`}>
      {/* 좋아요 버튼 */}
      <button
        onClick={() => handleFeedback('like')}
        disabled={loading}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
          myFeedback?.feedback_type === 'like'
            ? 'bg-green-500 text-white border-green-500'
            : 'bg-white text-gray-700 border-gray-300 hover:border-green-500 hover:text-green-500'
        } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
      >
        <ThumbsUp className="w-5 h-5" />
        <span className="font-medium">{stats.like_count}</span>
      </button>

      {/* 싫어요 버튼 (관리자만 표시) */}
      {isAdmin && (
        <button
          onClick={() => handleFeedback('dislike')}
          disabled={loading}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
            myFeedback?.feedback_type === 'dislike'
              ? 'bg-red-500 text-white border-red-500'
              : 'bg-white text-gray-700 border-gray-300 hover:border-red-500 hover:text-red-500'
          } ${loading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
        >
          <ThumbsDown className="w-5 h-5" />
          <span className="font-medium">{stats.dislike_count}</span>
        </button>
      )}

      {/* 관리자용 통계 */}
      {isAdmin && stats.like_count + stats.dislike_count > 0 && (
        <div className="text-sm text-gray-600">
          <span className="font-medium">
            만족도: {(stats.like_ratio * 100).toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  );
};
