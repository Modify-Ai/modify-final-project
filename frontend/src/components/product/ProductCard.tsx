import React, { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Heart, ShoppingBag } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import client from "../../api/client";

interface Product {
  id: number;
  name: string;
  category: string;
  price: number;
  image_url: string;
}

interface ProductCardProps {
  product: Product;
}

export default function ProductCard({ product }: ProductCardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [isWished, setIsWished] = useState(false);

  // =================================================================
  // 🕵️‍♀️ [DEBUG] 이미지 주소 정규화 및 로그 출력
  // =================================================================
  const getImageUrl = (url: string) => {
    if (!url) {
      // DB에 이미지 주소가 아예 없는 경우
      return "/placeholder.png";
    }

    // 1. 이미 완전한 URL인 경우 (http로 시작) -> 그대로 사용
    if (url.startsWith("http")) {
      return url;
    }

    // 2. 상대 경로인 경우 (/static으로 시작) -> 백엔드 주소(localhost:8000) 붙이기
    // TODO: 배포 환경에서는 이 부분을 환경변수(import.meta.env.VITE_API_URL)로 교체해야 합니다.
    const BACKEND_URL = "http://localhost:8000";

    const cleanUrl = url.startsWith("/") ? url : `/${url}`;
    const fullUrl = `${BACKEND_URL}${cleanUrl}`;

    return fullUrl;
  };

  const displayImage = getImageUrl(product.image_url);
  // =================================================================

  // 1. 초기 찜 상태 확인
  const { data: wishStatus } = useQuery({
    queryKey: ["wishlist-status", product.id],
    queryFn: async () => {
      try {
        const res = await client.get(`/wishlist/check/${product.id}`);
        return res.data;
      } catch {
        return { is_wished: false };
      }
    },
  });

  useEffect(() => {
    if (wishStatus) setIsWished(wishStatus.is_wished);
  }, [wishStatus]);

  // 2. 찜 토글 Mutation
  const toggleWishlistMutation = useMutation({
    mutationFn: async () => {
      const res = await client.post(`/wishlist/toggle/${product.id}`);
      return res.data;
    },
    onSuccess: (data) => {
      setIsWished(data.is_wished);
      queryClient.invalidateQueries({ queryKey: ["my-wishlist"] });
      queryClient.invalidateQueries({
        queryKey: ["wishlist-status", product.id],
      });
    },
    onError: () => {
      alert("로그인이 필요합니다.");
    },
  });

  const handleToggleWishlist = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    toggleWishlistMutation.mutate();
  };

  return (
    <div
      className="group relative flex flex-col gap-3 cursor-pointer"
      onClick={() => navigate(`/products/${product.id}`)}
    >
      {/* 🎨 [Image Wrapper] 둥근 모서리, 부드러운 그림자, 호버 시 떠오름 */}
      <div className="relative aspect-[3/4] w-full overflow-hidden rounded-[1.5rem] bg-gray-100 dark:bg-gray-800 shadow-[0_2px_10px_rgba(0,0,0,0.03)] transition-all duration-500 ease-out group-hover:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.12)] group-hover:-translate-y-1">
        {/* 이미지: 시네마틱 줌 효과 */}
        <img
          src={displayImage}
          alt={product.name}
          className="h-full w-full object-cover object-center transition-transform duration-700 ease-out group-hover:scale-105"
          // 🕵️‍♀️ [DEBUG] 에러 발생 시 상세 로그 출력
          onError={(e) => {
            const imgElement = e.currentTarget;

            // 무한 루프 방지: 이미 placeholder인데 또 에러나면 중단
            if (imgElement.src.includes("placeholder.png")) {
              console.error(
                `[ProductCard] ${product.name}: placeholder 이미지조차 로드 실패! (경로 확인 필요: /placeholder.png)`
              );
              return;
            }

            console.error(`[ProductCard] 이미지 로드 실패!`, {
              상품명: product.name,
              시도한URL: imgElement.src,
              DB원본URL: product.image_url,
              조치: "placeholder 이미지로 교체합니다.",
            });

            // placeholder 이미지로 교체
            imgElement.src = "/placeholder.png";
          }}
        />

        {/* Overlay Gradient (Hover 시 텍스트 가독성 및 분위기 연출) */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>

        {/* 💖 [Rollback] 하트 버튼: 이미지 오른쪽 상단에 위치 (Glassmorphism) */}
        <button
          onClick={handleToggleWishlist}
          className="absolute top-3 right-3 p-2.5 bg-white/70 dark:bg-black/40 backdrop-blur-md rounded-full text-gray-400 hover:bg-white hover:text-red-500 transition-all duration-300 shadow-sm opacity-0 translate-y-[-10px] group-hover:opacity-100 group-hover:translate-y-0"
        >
          <Heart
            className={`w-5 h-5 ${isWished ? "fill-red-500 text-red-500" : ""}`}
          />
        </button>

        {/* 🛒 [Rollback] 장바구니 버튼: 이미지 오른쪽 하단에 위치 (Hover시 등장) */}
        <div className="absolute bottom-3 right-3 opacity-0 translate-y-4 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-300 delay-75">
          <button
            onClick={(e) => {
              e.stopPropagation();
              alert("상세 페이지에서 옵션을 선택해주세요.");
              navigate(`/products/${product.id}`);
            }}
            className="p-3 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-full shadow-lg hover:scale-110 hover:bg-black transition-transform flex items-center justify-center"
          >
            <ShoppingBag className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* 🎨 [Product Info] 깔끔하고 모던한 타이포그래피 */}
      <div className="px-1 space-y-1.5">
        {/* 카테고리 태그 */}
        <div className="flex items-center">
          <span className="text-[10px] font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider bg-gray-100 dark:bg-gray-800 px-2 py-0.5 rounded-md">
            {product.category || "Basic"}
          </span>
        </div>

        {/* 상품명 */}
        <h3 className="text-[15px] font-medium text-gray-900 dark:text-white line-clamp-1 group-hover:text-purple-600 transition-colors">
          {product.name}
        </h3>

        {/* 가격 */}
        <div className="flex items-center justify-between">
          <p className="text-base font-bold text-gray-900 dark:text-gray-100">
            {product.price?.toLocaleString()}
            <span className="text-xs font-normal text-gray-400 ml-0.5">원</span>
          </p>
        </div>
      </div>
    </div>
  );
}
