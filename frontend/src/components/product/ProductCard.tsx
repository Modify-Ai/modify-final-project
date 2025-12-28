import React, { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
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
  // ✅ [FIX] S3 경로 자동 보정 ("static/" 강제 주입)
  // =================================================================
  const getImageUrl = (url: string) => {
    // 1. URL이 없으면 플레이스홀더
    if (!url) return "/placeholder.png";

    // 2. 이미 http로 시작하는 완벽한 주소면 그대로 사용
    if (url.startsWith("http")) return url;

    // 3. S3 버킷 주소 (서울 리전)
    const S3_BUCKET_URL = "https://modify-frontend-final-ai4.s3.ap-northeast-2.amazonaws.com";

    // 4. 앞쪽 슬래시(/) 제거 (경로 정규화)
    let cleanPath = url.startsWith("/") ? url.slice(1) : url;

    // 5. [핵심] 만약 경로가 'static/'으로 시작하지 않는다면 강제로 붙여준다.
    // 이유: 아까 S3에 'static' 폴더를 통째로 올렸기 때문에, 파일은 무조건 static 폴더 안에 있습니다.
    if (!cleanPath.startsWith("static/")) {
       cleanPath = `static/${cleanPath}`;
    }

    // 최종 주소: 버킷주소 + / + static/images/파일명.jpg
    return `${S3_BUCKET_URL}/${cleanPath}`;
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
      {/* 🎨 [Image Wrapper] */}
      <div className="relative aspect-[3/4] w-full overflow-hidden rounded-[1.5rem] bg-gray-100 dark:bg-gray-800 shadow-[0_2px_10px_rgba(0,0,0,0.03)] transition-all duration-500 ease-out group-hover:shadow-[0_20px_40px_-15px_rgba(0,0,0,0.12)] group-hover:-translate-y-1">
        {/* 이미지 */}
        <img
          src={displayImage}
          alt={product.name}
          className="h-full w-full object-cover object-center transition-transform duration-700 ease-out group-hover:scale-105"
          onError={(e) => {
            const imgElement = e.currentTarget;
            // 무한 루프 방지: 플레이스홀더도 없으면 멈춤
            if (!imgElement.src.includes("placeholder.png")) {
               console.error(`이미지 로드 실패: ${displayImage}`); // 디버깅용 로그
               imgElement.src = "/placeholder.png";
            }
          }}
        />

        {/* Overlay Gradient */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/20 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>

        {/* 💖 하트 버튼 */}
        <button
          onClick={handleToggleWishlist}
          className="absolute top-3 right-3 p-2.5 bg-white/70 dark:bg-black/40 backdrop-blur-md rounded-full text-gray-400 hover:bg-white hover:text-red-500 transition-all duration-300 shadow-sm opacity-0 translate-y-[-10px] group-hover:opacity-100 group-hover:translate-y-0"
        >
          <Heart
            className={`w-5 h-5 ${isWished ? "fill-red-500 text-red-500" : ""}`}
          />
        </button>

        {/* 🛒 장바구니 버튼 */}
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

      {/* 🎨 [Product Info] */}
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