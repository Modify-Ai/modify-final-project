import React, { useState, useCallback, useEffect, useRef } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Loader2,
  Zap,
  Heart,
  MessageSquare,
  Send,
  Maximize2,
  ArrowLeft,
  ShoppingBag,
  CreditCard,
  CheckCircle,
  Ruler,
  Sparkles,
  Star,
  ChevronRight,
  X,
} from "lucide-react";

import client from "../api/client";
import ProductCard from "../components/product/ProductCard";
import Modal from "../components/ui/Modal";

// 🖼️ [Image Import]
import sizeIcon from "../assets/images/size.png";

// --- Types ---
interface ProductResponse {
  id: number;
  name: string;
  description: string;
  price: number;
  stock_quantity: number;
  category: string;
  image_url: string;
  in_stock: boolean;
  gender?: string;
}

interface CoordinationResponse {
  answer: string;
  products: ProductResponse[];
}

interface LLMQueryResponse {
  answer: string;
}

interface BodyMeasurements {
  height: string;
  weight: string;
  chest: string;
  waist: string;
  hip: string;
  footSize: string;
  preferFit: "tight" | "regular" | "loose";
}

// 🎨 [Custom Icons]
const MannequinIcon = ({ className }: { className?: string }) => (
  <svg
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className={className}
  >
    <path
      d="M12 2C13.1046 2 14 2.89543 14 4V5H10V4C10 2.89543 10.8954 2 12 2Z"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M14 5H18.5C19.3284 5 20 5.67157 20 6.5V9.5C20 10.0523 19.5523 10.5 19 10.5H18V20C18 21.1046 17.1046 22 16 22H8C6.89543 22 6 21.1046 6 20V10.5H5C4.44772 10.5 4 10.0523 4 9.5V6.5C4 5.67157 4.67157 5 5.5 5H10"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M14 5L14 12L18 10.5"
      stroke="currentColor"
      strokeWidth="1.5"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
  </svg>
);

// LLM 질문 훅
const useLLMQuery = (productId: number) => {
  return useMutation<LLMQueryResponse, Error, string>({
    mutationFn: async (question: string) => {
      const res = await client.post(`/products/${productId}/llm-query`, {
        question,
      });
      return res.data;
    },
  });
};

export default function ProductDetail() {
  const { id } = useParams<{ id: string }>();
  const productId = Number(id);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const chatScrollRef = useRef<HTMLDivElement>(null);

  // 상품 데이터 상태
  const [product, setProduct] = useState<ProductResponse | null>(null);
  const [isProductLoading, setIsProductLoading] = useState(true);
  const [isProductError, setIsProductError] = useState(false);

  // ✅ [수정된 부분] 이미지 주소 정규화 헬퍼 함수 (S3 주소로 연결)
  const getImageUrl = (url: string) => {
    if (!url) return "/placeholder.png";
    // 이미 http로 시작하면(S3 풀 주소면) 그대로 사용
    if (url.startsWith("http")) return url;
    // 아니면 S3 버킷 주소를 붙여서 완성
    return `https://modify-frontend-final-ai4.s3.ap-northeast-2.amazonaws.com${url.startsWith("/") ? "" : "/"}${url}`;
  };

  // 상품 정보 가져오기
  useEffect(() => {
    const fetchProduct = async () => {
      if (!productId) return;
      setIsProductLoading(true);
      try {
        const response = await client.get(`/products/${productId}`);
        setProduct(response.data);
      } catch (err) {
        console.error("Failed to fetch product:", err);
        setIsProductError(true);
      } finally {
        setIsProductLoading(false);
      }
    };
    fetchProduct();
  }, [productId]);

  // AI 코디 관련 상태
  const [coordinationResult, setCoordinationResult] =
    useState<CoordinationResponse | null>(null);
  const [isCoordinationLoading, setIsCoordinationLoading] = useState(false);

  // LLM 질문 상태
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [qaHistory, setQaHistory] = useState<
    Array<{ type: "user" | "ai"; text: string }>
  >([]);
  const llmQueryMutation = useLLMQuery(productId || 0);

  // UI 상태
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalContent, setModalContent] = useState<React.ReactNode>(null);
  const [modalTitle, setModalTitle] = useState("");
  const [isImageZoomOpen, setIsImageZoomOpen] = useState(false);
  const [isChatOpen, setIsChatOpen] = useState(false);

  // 장바구니 상태
  const [isInCart, setIsInCart] = useState(false);
  const [justAdded, setJustAdded] = useState(false);

  // 사이즈 추천 상태
  const [isSizeModalOpen, setIsSizeModalOpen] = useState(false);
  const [isSizeLoading, setIsSizeLoading] = useState(false);
  const [sizeRecommendation, setSizeRecommendation] = useState<string | null>(
    null
  );
  const [bodyMeasurements, setBodyMeasurements] = useState<BodyMeasurements>({
    height: "",
    weight: "",
    chest: "",
    waist: "",
    hip: "",
    footSize: "",
    preferFit: "regular",
  });

  // 위시리스트 상태 관리
  const [isWished, setIsWished] = useState(false);

  const { data: wishStatus } = useQuery({
    queryKey: ["wishlist-status", productId],
    queryFn: async () => {
      try {
        const res = await client.get(`/wishlist/check/${productId}`);
        return res.data;
      } catch (e) {
        return { is_wished: false };
      }
    },
    enabled: !!productId,
  });

  useEffect(() => {
    if (wishStatus) setIsWished(wishStatus.is_wished);
  }, [wishStatus]);

  const toggleWishlistMutation = useMutation({
    mutationFn: async () => {
      const res = await client.post(`/wishlist/toggle/${productId}`);
      return res.data;
    },
    onSuccess: (data) => {
      setIsWished(data.is_wished);
      queryClient.invalidateQueries({ queryKey: ["my-wishlist"] });
      queryClient.invalidateQueries({
        queryKey: ["wishlist-status", productId],
      });
    },
    onError: () => {
      alert("로그인이 필요한 서비스입니다.");
    },
  });

  const handleToggleWishlist = () => {
    toggleWishlistMutation.mutate();
  };

  // 장바구니 상태 체크
  useEffect(() => {
    if (!product) return;
    const cart = JSON.parse(localStorage.getItem("cart") || "[]");
    const exists = cart.some((item: any) => item.id === product.id);
    setIsInCart(exists);
  }, [product]);

  // 채팅 스크롤 자동 이동
  useEffect(() => {
    if (chatScrollRef.current) {
      chatScrollRef.current.scrollTop = chatScrollRef.current.scrollHeight;
    }
  }, [qaHistory, llmQueryMutation.isPending, isChatOpen]);

  // --- 핸들러 ---
  const handleGoBack = () => {
    if (window.history.length > 1) navigate(-1);
    else navigate("/search");
  };

  const handleAddToCart = useCallback(async () => {
    if (!product) return;
    try {
      const cart = JSON.parse(localStorage.getItem("cart") || "[]");
      const existingIndex = cart.findIndex(
        (item: any) => item.id === product.id
      );

      if (existingIndex > -1) {
        cart[existingIndex].quantity += 1;
      } else {
        cart.push({
          id: product.id,
          name: product.name,
          price: product.price,
          image_url: product.image_url,
          quantity: 1,
        });
      }

      localStorage.setItem("cart", JSON.stringify(cart));
      setIsInCart(true);
      setJustAdded(true);
      setTimeout(() => setJustAdded(false), 3000);
    } catch (error) {
      alert("장바구니 담기에 실패했습니다.");
    }
  }, [product]);

  const handleGoToCart = () => navigate("/cart");

  const handleBuyNow = () => {
    if (!product) return;
    handleAddToCart();
    navigate("/checkout", {
      state: {
        directBuy: true,
        product: {
          id: product.id,
          name: product.name,
          price: product.price,
          image_url: product.image_url,
          quantity: 1,
        },
      },
    });
  };

  // AI 코디 추천
  const handleAICoordination = useCallback(async () => {
    if (!product) return;
    setIsCoordinationLoading(true);
    setCoordinationResult(null);

    try {
      const res = await client.get(`/products/ai-coordination/${product.id}`);
      const apiResponse = res.data;
      setCoordinationResult(apiResponse);

      setModalTitle("MODIFY 스타일리스트 추천 코디");
      setModalContent(
        <div className="space-y-8 p-1">
          <div className="bg-gradient-to-br from-purple-50 to-indigo-50 p-6 rounded-2xl border border-purple-100 shadow-sm relative overflow-hidden">
            <div className="absolute top-0 right-0 -mt-2 -mr-2 w-16 h-16 bg-purple-200 rounded-full opacity-20 blur-xl"></div>
            <div className="flex items-start gap-4 relative z-10">
              <div className="p-2.5 bg-white rounded-xl shadow-sm border border-purple-50">
                <MannequinIcon className="w-5 h-5 text-purple-600" />
              </div>
              <div className="space-y-1">
                <h5 className="font-bold text-gray-900 text-sm">
                  Styling Advice
                </h5>
                <p className="text-gray-700 leading-relaxed text-sm whitespace-pre-wrap">
                  {apiResponse.answer}
                </p>
              </div>
            </div>
          </div>

          <div>
            <div className="flex items-center justify-between mb-4">
              <h4 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                <ShoppingBag className="w-4 h-4 text-gray-500" /> 함께 입으면
                좋은 아이템
              </h4>
            </div>
            {apiResponse.products && apiResponse.products.length > 0 ? (
              <div className="grid grid-cols-2 gap-4">
                {apiResponse.products.map((p: ProductResponse) => (
                  <ProductCard key={p.id} product={p} />
                ))}
              </div>
            ) : (
              <div className="flex flex-col items-center justify-center py-12 bg-gray-50 rounded-2xl border border-dashed border-gray-200 text-gray-400 gap-2">
                <ShoppingBag className="w-8 h-8 opacity-50" />
                <span className="text-sm">추천 상품을 찾지 못했습니다.</span>
              </div>
            )}
          </div>
        </div>
      );
      setIsModalOpen(true);
    } catch (e) {
      alert("AI 코디 분석 중 오류가 발생했습니다.");
    } finally {
      setIsCoordinationLoading(false);
    }
  }, [product]);

  // 사이즈 추천 핸들러
  const handleSizeRecommendation = async () => {
    if (!product) return;

    if (!bodyMeasurements.height || !bodyMeasurements.weight) {
      alert("키와 몸무게는 필수 입력 항목입니다.");
      return;
    }

    setIsSizeLoading(true);
    setSizeRecommendation(null);

    try {
      const prompt = `상품: ${product.name}, 키: ${bodyMeasurements.height}cm, 몸무게: ${bodyMeasurements.weight}kg. 사이즈 추천해줘.`;
      const res = await client.post(`/products/${product.id}/llm-query`, {
        question: prompt,
      });
      setSizeRecommendation(res.data.answer);
    } catch (error) {
      setSizeRecommendation("AI 연결 상태가 원활하지 않습니다.");
    } finally {
      setIsSizeLoading(false);
    }
  };

  const handleBodyChange = (field: keyof BodyMeasurements, value: string) => {
    setBodyMeasurements((prev) => ({ ...prev, [field]: value }));
  };

  const handleLLMSubmit = () => {
    const trimmedQuestion = currentQuestion.trim();
    if (!trimmedQuestion || llmQueryMutation.isPending) return;

    setQaHistory((prev) => [...prev, { type: "user", text: trimmedQuestion }]);
    setCurrentQuestion("");

    llmQueryMutation.mutate(trimmedQuestion, {
      onSuccess: (data) => {
        setQaHistory((prev) => [...prev, { type: "ai", text: data.answer }]);
      },
      onError: () => {
        setQaHistory((prev) => [
          ...prev,
          {
            type: "ai",
            text: "죄송합니다. AI 서비스 연결이 원활하지 않습니다.",
          },
        ]);
      },
    });
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleLLMSubmit();
    }
  };

  if (isProductLoading)
    return (
      <div className="h-screen flex items-center justify-center bg-gray-50/50">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="w-10 h-10 animate-spin text-purple-600" />
          <p className="text-gray-500 font-medium animate-pulse">
            상품 정보를 불러오고 있습니다...
          </p>
        </div>
      </div>
    );

  if (isProductError || !product)
    return (
      <div className="h-screen flex flex-col items-center justify-center text-gray-500 bg-gray-50/50 gap-4">
        <ShoppingBag className="w-16 h-16 text-gray-300" />
        <p>상품 정보를 불러올 수 없습니다.</p>
        <button
          onClick={handleGoBack}
          className="text-purple-600 hover:underline"
        >
          돌아가기
        </button>
      </div>
    );

  const defaultAIBriefing =
    product.description ||
    "MODIFY가 상품 상세 정보를 분석하여 최적의 쇼핑 정보를 제공합니다.";

  return (
    // 🎨 전체 배경
    <div className="min-h-screen bg-[#F8F9FA] dark:bg-black transition-colors duration-300">
      {/* 상단 네비게이션 영역 */}
      <div className="sticky top-0 z-10 bg-white/80 dark:bg-black/80 backdrop-blur-md border-b border-gray-100 dark:border-gray-800">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <button
            onClick={handleGoBack}
            className="group flex items-center text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors font-medium"
          >
            <div className="p-2 rounded-full group-hover:bg-gray-100 dark:group-hover:bg-gray-800 transition-colors mr-1">
              <ArrowLeft className="w-5 h-5" />
            </div>
            <span className="text-sm">Back</span>
          </button>
          {/* 상단 간략 정보 */}
          <div
            className="hidden md:flex items-center gap-4 opacity-0 animate-fade-in"
            style={{ animationDelay: "0.5s", animationFillMode: "forwards" }}
          >
            <span className="text-sm font-medium text-gray-900 dark:text-white truncate max-w-[200px]">
              {product.name}
            </span>
            <div className="h-4 w-px bg-gray-300"></div>
            <span className="text-sm font-bold text-purple-600">
              {product.price.toLocaleString()}원
            </span>
          </div>
          <div className="w-10"></div>
        </div>
      </div>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 lg:py-12 pb-32 animate-fade-in">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-16 mb-20">
          {/* 🎨 [Left] Image Section */}
          <div className="lg:col-span-7 relative">
            <div className="sticky top-24">
              <div className="relative bg-white dark:bg-gray-900 rounded-[2.5rem] overflow-hidden aspect-[3/4] lg:aspect-[4/5] shadow-[0_20px_50px_-12px_rgba(0,0,0,0.1)] group border border-gray-100 dark:border-gray-800">
                {/* ✅ [수정] getImageUrl 헬퍼 함수 적용 */}
                <img
                  src={getImageUrl(product.image_url)}
                  alt={product.name}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-1000 ease-out"
                  onError={(e) =>
                    (e.currentTarget.src = "/placeholder.png")
                  }
                />
                {/* Image Overlay Gradient */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>

                {/* 🔍 이미지 확대 버튼 */}
                <button
                  onClick={() => setIsImageZoomOpen(true)}
                  className="absolute top-6 right-6 p-3 bg-white/90 backdrop-blur-md rounded-full text-gray-700 hover:text-purple-600 transition-all shadow-lg hover:scale-110 active:scale-95 z-10"
                >
                  <Maximize2 className="w-5 h-5" />
                </button>
              </div>
            </div>
          </div>

          {/* 🎨 [Right] Product Info */}
          <div className="lg:col-span-5 flex flex-col justify-center">
            <div className="mb-10">
              <div className="flex items-center gap-3 mb-6 flex-wrap">
                <span className="px-4 py-1.5 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300 text-xs font-bold rounded-full uppercase tracking-wider border border-gray-200 dark:border-gray-700">
                  {product.category}
                </span>
                {product.in_stock ? (
                  <span className="text-xs font-bold text-emerald-600 bg-emerald-50 dark:bg-emerald-900/30 px-3 py-1.5 rounded-full border border-emerald-100 dark:border-emerald-800 flex items-center gap-1.5">
                    <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></div>
                    IN STOCK
                  </span>
                ) : (
                  <span className="text-xs font-bold text-rose-500 bg-rose-50 px-3 py-1.5 rounded-full border border-rose-100">
                    SOLD OUT
                  </span>
                )}
              </div>

              <h1 className="text-3xl lg:text-5xl font-light text-gray-900 dark:text-white leading-[1.1] mb-6 tracking-tight">
                {product.name}
              </h1>

              <div className="flex items-baseline gap-2 mb-10">
                <span className="text-4xl font-bold text-gray-900 dark:text-white">
                  {product.price.toLocaleString()}
                </span>
                <span className="text-xl font-normal text-gray-500 dark:text-gray-400">
                  KRW
                </span>
              </div>

              <p className="text-gray-600 dark:text-gray-300 leading-relaxed mb-10 border-l-4 border-gray-200 dark:border-gray-700 pl-6 py-1">
                {product.description}
              </p>

              {/* 🟠 [Buttons Group] */}
              <div className="flex items-center gap-3 w-full">
                <button
                  onClick={handleToggleWishlist}
                  className="flex flex-col items-center justify-center min-w-[3.5rem] h-[3.5rem] rounded-xl hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors group"
                >
                  <Heart
                    className={`w-7 h-7 transition-colors ${
                      isWished
                        ? "fill-red-500 text-red-500"
                        : "text-gray-400 group-hover:text-red-500"
                    }`}
                    strokeWidth={1.5}
                  />
                </button>

                <button
                  onClick={isInCart ? handleGoToCart : handleAddToCart}
                  disabled={!product.in_stock}
                  className="flex-1 h-[3.5rem] bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-700 text-gray-900 dark:text-white text-base font-bold rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
                >
                  {isInCart ? "장바구니 이동" : "장바구니"}
                </button>

                <button
                  onClick={handleBuyNow}
                  disabled={!product.in_stock}
                  className="flex-1 h-[3.5rem] text-white text-base font-bold rounded-lg shadow-md transition-all hover:opacity-90 active:scale-[0.98] disabled:opacity-50"
                  style={{
                    background:
                      "linear-gradient(90deg, #7A51A1 0%, #5D93D0 100%)",
                  }}
                >
                  구매하기
                </button>
              </div>
            </div>

            {/* 🎨 [AI Features] */}
            <div className="space-y-4 mt-8">
              <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">
                AI Smart Assistant
              </h3>

              {/* ✨ 스타일링 추천 카드 */}
              <div
                onClick={handleAICoordination}
                className="group relative bg-white dark:bg-gray-800 p-1 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-lg transition-all cursor-pointer overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-purple-50 to-pink-50 dark:from-purple-900/10 dark:to-pink-900/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <div className="relative p-5 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-xl text-purple-600 dark:text-purple-300 group-hover:scale-110 transition-transform duration-300">
                      <MannequinIcon className="w-6 h-6" />
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900 dark:text-white group-hover:text-purple-700 transition-colors">
                        MODIFY 스타일링 추천
                      </h4>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        이 상품과 찰떡인 코디를 제안해드려요.
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-purple-500 group-hover:translate-x-1 transition-all" />
                </div>
              </div>

              {/* 📏 사이즈 분석 카드 */}
              <div
                onClick={() => setIsSizeModalOpen(true)}
                className="group relative bg-white dark:bg-gray-800 p-1 rounded-2xl border border-gray-100 dark:border-gray-700 shadow-sm hover:shadow-lg transition-all cursor-pointer overflow-hidden"
              >
                <div className="absolute inset-0 bg-gradient-to-r from-blue-50 to-cyan-50 dark:from-blue-900/10 dark:to-cyan-900/10 opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
                <div className="relative p-5 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="p-3 bg-blue-100 dark:bg-blue-900/30 rounded-xl flex items-center justify-center group-hover:scale-110 transition-transform duration-300">
                      <img
                        src={sizeIcon}
                        alt="Size Analysis"
                        className="w-6 h-6 object-contain opacity-80"
                      />
                    </div>
                    <div>
                      <h4 className="font-bold text-gray-900 dark:text-white group-hover:text-blue-700 transition-colors">
                        MODIFY에서 사이즈 분석
                      </h4>
                      <p className="text-sm text-gray-500 dark:text-gray-400">
                        내 신체 정보로 딱 맞는 사이즈 찾기.
                      </p>
                    </div>
                  </div>
                  <ChevronRight className="w-5 h-5 text-gray-300 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" />
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* 🚀 [Floating Chat Button] */}
      <button
        onClick={() => setIsChatOpen(!isChatOpen)}
        className={`fixed bottom-6 right-6 z-50 flex items-center justify-center shadow-2xl hover:scale-105 transition-all duration-300 group
          ${
            isChatOpen
              ? "w-14 h-14 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-full"
              : "px-6 py-4 bg-gray-900 dark:bg-white text-white dark:text-gray-900 rounded-full gap-2.5"
          }`}
      >
        {isChatOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <>
            <MessageSquare className="w-5 h-5" />
            <span className="font-bold text-sm whitespace-nowrap">
              AI 스타일리스트
            </span>
          </>
        )}
      </button>

      {/* 💬 [Chat Popup Widget] */}
      <div
        className={`fixed bottom-24 right-6 z-40 w-[90vw] max-w-[400px] h-[600px] bg-white dark:bg-gray-900 rounded-[2rem] shadow-2xl border border-gray-100 dark:border-gray-800 overflow-hidden transition-all duration-300 origin-bottom-right ${
          isChatOpen
            ? "scale-100 opacity-100"
            : "scale-0 opacity-0 pointer-events-none"
        }`}
      >
        <div className="bg-gradient-to-r from-gray-900 to-gray-800 p-6 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="relative">
              <div className="p-2.5 bg-white/10 backdrop-blur-md rounded-xl text-white border border-white/20">
                <MessageSquare className="w-6 h-6" />
              </div>
              <div className="absolute -bottom-1 -right-1 w-3.5 h-3.5 bg-green-500 border-2 border-gray-900 rounded-full animate-pulse"></div>
            </div>
            <div>
              <h2 className="text-lg font-bold text-white">
                AI Fashion Consultant
              </h2>
              <p className="text-xs text-gray-300">
                실시간으로 상품 궁금증 해결하기
              </p>
            </div>
          </div>
        </div>

        <div className="flex flex-col h-[calc(100%-88px)] bg-[#F3F4F6] dark:bg-[#111]">
          <div
            className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar scroll-smooth"
            ref={chatScrollRef}
          >
            <div className="flex justify-start animate-slide-up">
              <div className="max-w-[85%] space-y-2">
                <div className="flex items-center gap-2 mb-1 ml-1">
                  <Sparkles className="w-3 h-3 text-purple-600" />
                  <span className="text-xs font-bold text-gray-500">
                    AI Stylist
                  </span>
                </div>
                <div className="bg-white dark:bg-gray-800 p-5 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 dark:border-gray-700 text-sm leading-relaxed text-gray-700 dark:text-gray-200">
                  <strong className="block text-purple-600 dark:text-purple-400 mb-2 font-bold">
                    Product Insight
                  </strong>
                  {defaultAIBriefing}
                </div>
                <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                  {["세탁 방법은?", "소재가 뭐야?", "여름에 더울까?"].map(
                    (suggestion, idx) => (
                      <button
                        key={idx}
                        onClick={() => setCurrentQuestion(suggestion)}
                        className="whitespace-nowrap px-4 py-2 bg-white dark:bg-gray-800 border border-purple-100 dark:border-purple-900/30 rounded-full text-xs text-purple-600 dark:text-purple-400 hover:bg-purple-50 transition-colors"
                      >
                        {suggestion}
                      </button>
                    )
                  )}
                </div>
              </div>
            </div>

            {qaHistory.map((item, index) => (
              <div
                key={index}
                className={`flex ${
                  item.type === "user" ? "justify-end" : "justify-start"
                } animate-slide-up`}
              >
                <div
                  className={`max-w-[80%] px-5 py-3.5 rounded-2xl text-sm leading-relaxed shadow-sm
                                                                ${
                                                                  item.type ===
                                                                  "user"
                                                                    ? "bg-gray-900 text-white rounded-br-none"
                                                                    : "bg-white dark:bg-gray-800 text-gray-800 dark:text-gray-200 rounded-tl-none border border-gray-100 dark:border-gray-700"
                                                                }`}
                >
                  {item.text}
                </div>
              </div>
            ))}

            {llmQueryMutation.isPending && (
              <div className="flex justify-start animate-fade-in">
                <div className="bg-white dark:bg-gray-800 px-4 py-3 rounded-2xl rounded-tl-none shadow-sm border border-gray-100 dark:border-gray-700 flex items-center gap-2">
                  <div className="flex gap-1">
                    <span
                      className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce"
                      style={{ animationDelay: "0s" }}
                    ></span>
                    <span
                      className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></span>
                    <span
                      className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-bounce"
                      style={{ animationDelay: "0.4s" }}
                    ></span>
                  </div>
                  <span className="text-xs text-gray-400 ml-1">
                    답변 작성 중...
                  </span>
                </div>
              </div>
            )}
          </div>

          <div className="p-4 bg-white dark:bg-gray-900 border-t border-gray-100 dark:border-gray-800">
            <div className="flex gap-3 bg-gray-50 dark:bg-gray-800 p-2 rounded-[1.5rem] border border-gray-200 dark:border-gray-700 focus-within:ring-2 focus-within:ring-purple-100 dark:focus-within:ring-purple-900 transition-all">
              <input
                type="text"
                value={currentQuestion}
                onChange={(e) => setCurrentQuestion(e.target.value)}
                onKeyPress={handleKeyPress}
                disabled={llmQueryMutation.isPending}
                placeholder="이 상품에 대해 궁금한 점을 물어보세요..."
                className="flex-1 bg-transparent px-4 py-3 outline-none text-sm text-gray-800 dark:text-white placeholder:text-gray-400"
              />
              <button
                onClick={handleLLMSubmit}
                disabled={llmQueryMutation.isPending || !currentQuestion.trim()}
                className="p-3 bg-gray-900 dark:bg-purple-600 text-white rounded-full hover:bg-black dark:hover:bg-purple-700 disabled:bg-gray-300 dark:disabled:bg-gray-700 transition-colors shadow-md disabled:shadow-none"
              >
                <Send className="w-5 h-5 ml-0.5" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 모달 */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={modalTitle}
        maxWidth="max-w-2xl"
      >
        {modalContent}
      </Modal>

      <Modal
        isOpen={isSizeModalOpen}
        onClose={() => setIsSizeModalOpen(false)}
        title="사이즈 정밀 분석"
        maxWidth="max-w-md"
      >
        <div className="space-y-6 pt-2">
          {!sizeRecommendation ? (
            <>
              <div className="bg-blue-50 p-4 rounded-xl text-xs text-blue-700 mb-4 flex gap-2">
                <span className="text-lg">💡</span>
                <div>
                  신체 사이즈를 입력하면 MODIFY가 고객님의 체형 데이터와 상품
                  실측 사이즈를 비교 분석합니다.
                </div>
              </div>
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5 ml-1">
                    Height
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      value={bodyMeasurements.height}
                      onChange={(e) =>
                        handleBodyChange("height", e.target.value)
                      }
                      className="w-full p-4 bg-gray-50 rounded-xl border-none focus:ring-2 focus:ring-purple-100 transition-all font-medium text-gray-900"
                      placeholder="0"
                    />
                    <span className="absolute right-4 top-4 text-gray-400 font-medium">
                      cm
                    </span>
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-500 uppercase mb-1.5 ml-1">
                    Weight
                  </label>
                  <div className="relative">
                    <input
                      type="number"
                      value={bodyMeasurements.weight}
                      onChange={(e) =>
                        handleBodyChange("weight", e.target.value)
                      }
                      className="w-full p-4 bg-gray-50 rounded-xl border-none focus:ring-2 focus:ring-purple-100 transition-all font-medium text-gray-900"
                      placeholder="0"
                    />
                    <span className="absolute right-4 top-4 text-gray-400 font-medium">
                      kg
                    </span>
                  </div>
                </div>
              </div>
              <button
                onClick={handleSizeRecommendation}
                disabled={isSizeLoading}
                className="w-full py-4 mt-4 bg-gray-900 text-white rounded-xl hover:bg-black disabled:opacity-50 font-bold shadow-lg transition-all flex justify-center items-center gap-2"
              >
                {isSizeLoading ? (
                  <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                  <>
                    <Ruler className="w-4 h-4" /> 분석 시작하기
                  </>
                )}
              </button>
            </>
          ) : (
            <div className="space-y-6 animate-fade-in">
              <div className="bg-gradient-to-br from-purple-50 to-white p-6 rounded-2xl text-gray-800 whitespace-pre-wrap leading-relaxed border border-purple-100 shadow-sm text-sm">
                <strong className="block text-purple-600 mb-2 font-bold text-base">
                  분석 결과
                </strong>
                {sizeRecommendation}
              </div>
              <button
                onClick={() => setSizeRecommendation(null)}
                className="w-full py-3.5 bg-white border border-gray-200 text-gray-900 font-bold rounded-xl hover:bg-gray-50 transition-colors"
              >
                다시 입력하기
              </button>
            </div>
          )}
        </div>
      </Modal>

      {/* 🆕 [New Modal] 이미지 확대 줌 모달 */}
      {isImageZoomOpen && (
        <div
          className="fixed inset-0 z-[60] flex items-center justify-center bg-black/90 backdrop-blur-sm animate-fade-in cursor-zoom-out"
          onClick={() => setIsImageZoomOpen(false)}
        >
          {/* 닫기 버튼 */}
          <button className="absolute top-6 right-6 p-2 bg-black/50 text-white rounded-full hover:bg-white hover:text-black transition-colors">
            <X className="w-8 h-8" />
          </button>

          {/* 확대된 이미지 */}
          <img
            src={getImageUrl(product.image_url)}
            alt={product.name}
            className="max-w-[95vw] max-h-[95vh] object-contain rounded-lg shadow-2xl cursor-default"
            onClick={(e) => e.stopPropagation()}
          />
        </div>
      )}

      {/* Utility Styles */}
      <style>{`
        .animate-fade-in { animation: fadeIn 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(20px); }
        .animate-slide-up { animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1) forwards; opacity: 0; transform: translateY(10px); }
        @keyframes fadeIn { to { opacity: 1; transform: translateY(0); } }
        @keyframes slideUp { to { opacity: 1; transform: translateY(0); } }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background-color: #e5e7eb; border-radius: 20px; }
        .scrollbar-hide::-webkit-scrollbar { display: none; }
      `}</style>
    </div>
  );
}