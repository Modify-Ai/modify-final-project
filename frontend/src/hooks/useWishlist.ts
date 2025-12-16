// src/hooks/useWishlist.ts
import { useState, useEffect, useCallback } from "react";
import { useAuthStore } from "@/store/authStore"; // 경로 확인 필요

const API_BASE_URL = "http://localhost:8000/api/v1";

export interface Product {
  id: number;
  name: string;
  price: number;
  image_url?: string;
  category?: string;
}

export const useWishlist = (isOpen: boolean) => {
  const { token } = useAuthStore();
  const [wishlistItems, setWishlistItems] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);

  // 목록 불러오기
  const fetchWishlist = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/wishlist/`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setWishlistItems(data);
      }
    } catch (error) {
      console.error("에러 발생:", error);
    } finally {
      setLoading(false);
    }
  }, [token]);

  // 삭제 기능 (토글)
  const removeFromWishlist = async (productId: number) => {
    if (!token) return;

    // 1. 화면에서 먼저 지우기 (빠른 반응)
    setWishlistItems((prev) => prev.filter((item) => item.id !== productId));

    // 2. 서버에 요청 보내기
    try {
      await fetch(`${API_BASE_URL}/wishlist/toggle/${productId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
          "Content-Type": "application/json",
        },
      });
    } catch (error) {
      console.error("삭제 실패:", error);
      fetchWishlist(); // 실패하면 다시 목록 불러오기
    }
  };

  // 모달 열릴 때 자동 실행
  useEffect(() => {
    if (isOpen) fetchWishlist();
  }, [isOpen, fetchWishlist]);

  return { wishlistItems, loading, removeFromWishlist };
};
