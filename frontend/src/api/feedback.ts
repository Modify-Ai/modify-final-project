import client from './client';

export interface FeedbackCreate {
  product_id: number;
  feedback_type: 'like' | 'dislike';
  search_query?: string;
  search_context?: Record<string, any>;
}

export interface FeedbackResponse {
  success: boolean;
  message: string;
  current_feedback_type: string | null;
}

export interface FeedbackStats {
  like_count: number;
  dislike_count: number;
  like_ratio: number;
}

export interface FeedbackDetail {
  id: number;
  product_id: number;
  feedback_type: string;
  search_query: string | null;
  created_at: string;
}

export interface FeedbackListItem {
  id: number;
  user_id: number | null;
  session_id: string | null;
  product_id: number;
  feedback_type: string;
  search_query: string | null;
  created_at: string;
}

export const feedbackAPI = {
  /**
   * 피드백 제출 (토글 기능)
   */
  async submit(data: FeedbackCreate): Promise<FeedbackResponse> {
    const response = await client.post('/feedback/', data);
    return response.data;
  },

  /**
   * 피드백 통계 조회
   */
  async getStats(productId: number): Promise<FeedbackStats> {
    const response = await client.get(`/feedback/stats/${productId}`);
    return response.data;
  },

  /**
   * 내 피드백 조회
   */
  async getMyFeedback(productId: number): Promise<FeedbackDetail | null> {
    try {
      const response = await client.get(`/feedback/my-feedback/${productId}`);
      return response.data;
    } catch (error) {
      return null;
    }
  },

  /**
   * 관리자 전용: 최근 피드백 목록
   */
  async getRecentFeedbacks(limit: number = 100): Promise<FeedbackListItem[]> {
    const response = await client.get('/feedback/admin/recent', {
      params: { limit }
    });
    return response.data;
  },

  /**
   * 관리자 전용: 피드백 삭제
   */
  async deleteFeedback(feedbackId: number): Promise<{ success: boolean; message: string }> {
    const response = await client.delete(`/feedback/${feedbackId}`);
    return response.data;
  },
};
