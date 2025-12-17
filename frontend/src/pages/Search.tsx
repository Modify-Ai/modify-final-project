import React, { useState, useCallback, useRef, useEffect } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import {
  Search as SearchIcon,
  Mic,
  X,
  Sparkles,
  TrendingUp,
  Image as ImageIcon,
  ShoppingBag,
  AlertCircle,
  RefreshCw,
  ArrowUp,
  ArrowLeft,
  Check, // ✅ Check 아이콘 사용됨
} from "lucide-react";
import client from "../api/client";
import ProductCard from "../components/product/ProductCard";
import { useSearchStore } from "../store/searchStore";

// 🟢 [헤더 로고 추가] 경로 확인 필요
import logo from "../assets/images/logo-modify-color.png";

// --- Types ---
interface ProductResponse {
  id: number;
  name: string;
  description: string;
  price: number;
  category: string;
  image_url: string;
  stock_quantity: number;
  in_stock?: boolean;
  gender?: string;
  is_active?: boolean;
}

interface CandidateImage {
  image_base64: string;
  score: number;
}

interface SearchResult {
  status: string;
  ai_analysis?: {
    summary: string;
    reference_image?: string;
    candidates?: CandidateImage[];
  };
  products: ProductResponse[];
}

const API_ENDPOINT = "/search/ai-search";

const useSearchQuery = () => {
  const [searchParams] = useSearchParams();
  return searchParams.get("q") || "";
};

const useTTS = () => {
  const speak = useCallback((text: string) => {
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = "ko-KR";
      utterance.rate = 1.0;
      window.speechSynthesis.speak(utterance);
    }
  }, []);
  return { speak };
};

const LOADING_STEPS = [
  { text: "글로벌 트렌드를 검색하고 있습니다..." },
  { text: "가장 적절한 제품 이미지를 선별 중입니다..." },
  { text: "패션 스타일과 핏을 정밀 분석 중입니다..." },
  { text: "적합한 스타일 칼럼을 작성하고 있습니다..." },
];

export default function Search() {
  const queryTextFromUrl = useSearchQuery();
  const navigate = useNavigate();
  const { addRecentSearch } = useSearchStore();

  const [query, setQuery] = useState(queryTextFromUrl);
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [results, setResults] = useState<ProductResponse[]>([]);

  // AI 분석 상태
  const [aiAnalysis, setAiAnalysis] = useState<
    SearchResult["ai_analysis"] | null
  >(null);
  const [selectedImage, setSelectedImage] = useState<string | null>(null);
  const [currentText, setCurrentText] = useState<string>("");

  // 원본 검색어 저장 (CLIP 검색 시 성별 필터용)
  const [originalQuery, setOriginalQuery] = useState<string>("");

  // UI 상태
  const [isAnalyzingImage, setIsAnalyzingImage] = useState(false);
  const [isSearchingProducts, setIsSearchingProducts] = useState(false);
  const [showProducts, setShowProducts] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStepIndex, setLoadingStepIndex] = useState(0);
  const [timestamp, setTimestamp] = useState<number>(Date.now());

  // 🎨 [Design State] 검색창 포커스 효과를 위한 상태 추가
  const [isFocused, setIsFocused] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const productSectionRef = useRef<HTMLDivElement>(null);
  const { speak } = useTTS();

  // ✅ 백엔드 API URL (이미지 로딩용)
  const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

  useEffect(() => {
    if (isLoading) {
      const interval = setInterval(() => {
        setLoadingStepIndex((prev) => (prev + 1) % LOADING_STEPS.length);
      }, 800);
      return () => clearInterval(interval);
    } else {
      setLoadingStepIndex(0);
    }
  }, [isLoading]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file && file.type.startsWith("image/")) setImageFile(file);
  };

  // ✅ 이미지 URL 변환 + 캐시 버스팅
  const getBustedImage = (url: string) => {
    if (!url) return "https://placehold.co/400x500/e2e8f0/64748b?text=No+Image";
    if (url.startsWith("data:")) return url;
    if (url.startsWith("http://") || url.startsWith("https://")) {
      const separator = url.includes("?") ? "&" : "?";
      return `${url}${separator}t=${timestamp}`;
    }
    // /static/images/... 형식 → 백엔드 URL 붙이기
    if (url.startsWith("/static/")) {
      return `${API_BASE_URL}${url}?t=${timestamp}`;
    }
    return `${API_BASE_URL}/${url}?t=${timestamp}`;
  };

  // ✅ 이미지 기반 상품 검색 (쿼리 직접 전달 방식)
  const searchProductsByImage = useCallback(
    async (
      imageBase64: string,
      targetQuery: string,
      target: string = "full"
    ) => {
      setIsSearchingProducts(true);
      try {
        const clipResponse = await client.post("/search/search-by-clip", {
          image_b64: imageBase64,
          limit: 12,
          query: targetQuery, // ✅ 상태값이 아닌 인자값 사용
          target: target,
        });

        if (clipResponse.data && clipResponse.data.products) {
          setResults(clipResponse.data.products);
          setTimestamp(Date.now());
        }
      } catch (error) {
        console.error("Image-based search failed:", error);
      } finally {
        setIsSearchingProducts(false);
      }
    },
    []
  );

  // [핵심] 검색 로직
  const handleSearch = useCallback(
    async (
      currentQuery: string,
      currentImage: File | null,
      isVoice: boolean = false
    ) => {
      if (!currentQuery && !currentImage) return;

      // 초기화
      if (currentQuery) addRecentSearch(currentQuery);
      setIsLoading(true);
      setResults([]);
      setAiAnalysis(null);
      setSelectedImage(null);
      setCurrentText("");
      setShowProducts(false);
      setTimestamp(Date.now());

      // ✅ 원본 검색어 상태 업데이트 (UI용)
      setOriginalQuery(currentQuery);

      const formData = new FormData();
      formData.append("query", currentQuery);
      if (currentImage) formData.append("image_file", currentImage);
      formData.append("limit", "12");

      try {
        const response = await client.post<SearchResult>(
          API_ENDPOINT,
          formData,
          {
            headers: { "Content-Type": "multipart/form-data" },
          }
        );

        const data = response.data;
        setResults(data.products || []);

        if (data.ai_analysis && data.ai_analysis.reference_image) {
          setAiAnalysis(data.ai_analysis);
          setSelectedImage(data.ai_analysis.reference_image);
          setCurrentText(data.ai_analysis.summary);

          if (isVoice) speak(data.ai_analysis.summary);
        } else {
          setShowProducts(true);
        }
      } catch (error: any) {
        console.error("Search failed:", error);
        setShowProducts(true); // 에러 나도 빈 결과창 보여줌
      } finally {
        setIsLoading(false);
      }
    },
    [speak, addRecentSearch]
  );

  // 후보 이미지 선택 시 상품 재검색
  const handleSelectCandidateImage = async (imageBase64: string) => {
    setSelectedImage(imageBase64);

    if (showProducts) {
      // ✅ originalQuery 상태값 사용
      await searchProductsByImage(imageBase64, originalQuery, "full");
    }
  };

  const handleAnalyzeSelectedImage = async () => {
    if (!selectedImage || !query) return;
    setIsAnalyzingImage(true);
    try {
      const response = await client.post("/search/analyze-image", {
        image_b64: selectedImage,
        query: query,
      });
      setCurrentText(response.data.analysis);
    } catch (e) {
      console.error(e);
      setCurrentText("상세 분석에 실패했습니다. 잠시 후 다시 시도해주세요.");
    } finally {
      setIsAnalyzingImage(false);
    }
  };

  // ✅ 상품 보기 핸들러들
  const handleShowProducts = async () => {
    setShowProducts(true);
    if (selectedImage) {
      await searchProductsByImage(selectedImage, originalQuery, "full");
    }
    setTimeout(
      () => productSectionRef.current?.scrollIntoView({ behavior: "smooth" }),
      100
    );
  };

  const handleShowUpperOnly = async () => {
    setShowProducts(true);
    if (selectedImage) {
      await searchProductsByImage(selectedImage, originalQuery, "upper");
    }
    setTimeout(
      () => productSectionRef.current?.scrollIntoView({ behavior: "smooth" }),
      100
    );
  };

  const handleShowLowerOnly = async () => {
    setShowProducts(true);
    if (selectedImage) {
      await searchProductsByImage(selectedImage, originalQuery, "lower");
    }
    setTimeout(
      () => productSectionRef.current?.scrollIntoView({ behavior: "smooth" }),
      100
    );
  };

  const handleScrollTop = () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleVoiceSearch = () => {
    if (!("webkitSpeechRecognition" in window)) {
      alert("Chrome 브라우저를 사용해주세요.");
      return;
    }
    const recognition = new (window as any).webkitSpeechRecognition();
    recognition.lang = "ko-KR";
    recognition.onstart = () => speak("듣고 있습니다.");
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setQuery(transcript);
      handleSearch(transcript, imageFile, true);
    };
    recognition.start();
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSearch(query, imageFile, false);
  };

  const previewUrl = imageFile ? URL.createObjectURL(imageFile) : null;

  useEffect(() => {
    if (queryTextFromUrl) {
      setQuery(queryTextFromUrl);
      handleSearch(queryTextFromUrl, null, false);
    }
  }, [queryTextFromUrl, handleSearch]);

  return (
    // 🎨 [Design Update] 전체 배경: 눈이 편한 부드러운 그레이 톤
    <div className="min-h-screen bg-gray-50/50 dark:bg-black p-6 pb-40 transition-colors duration-300">
      {/* 🟢 [Header] 뒤로가기 + 로고 */}
      <header className="max-w-7xl mx-auto mb-8 pt-4">
        <div className="flex items-center gap-4 mb-8">
          <button
            onClick={() => navigate("/")}
            className="p-2 rounded-full hover:bg-white hover:shadow-sm dark:hover:bg-gray-800 transition-all duration-200"
          >
            <ArrowLeft className="w-6 h-6 text-gray-500 dark:text-gray-400" />
          </button>

          <div className="flex items-center gap-3">
            <img
              src={logo}
              alt="MODIFY"
              className="h-8 w-auto object-contain"
            />
            <h1 className="text-3xl font-light text-gray-900 dark:text-white">
              <span className="font-bold">통합 검색</span>
            </h1>
          </div>
        </div>

        {/* 🎨 [Design Update] 검색창 UI: Glow 효과 + 부드러운 트랜지션 */}
        <form
          onSubmit={handleSubmit}
          className={`
            relative flex items-center w-full bg-white dark:bg-gray-900 rounded-2xl p-2
            transition-all duration-300 ease-out
            ${
              isFocused
                ? "shadow-[0_0_20px_rgba(147,51,234,0.15)] ring-2 ring-purple-100 dark:ring-purple-900 border-purple-200 dark:border-purple-800"
                : "shadow-sm border border-gray-200 dark:border-gray-800 hover:shadow-md"
            }
          `}
        >
          <SearchIcon
            className={`w-6 h-6 ml-4 transition-colors duration-200 ${
              isFocused ? "text-purple-500" : "text-gray-400"
            }`}
          />

          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder="MODIFY가 고객님의 취향을 분석하여 상품을 찾고 있어요..."
            className="flex-1 text-lg p-4 bg-transparent border-none outline-none focus:ring-0 placeholder:text-gray-400 dark:placeholder:text-gray-600 text-gray-900 dark:text-white font-medium"
          />

          <div className="flex items-center gap-2 mr-2">
            {/* 음성 검색 버튼 */}
            <button
              type="button"
              onClick={handleVoiceSearch}
              className="p-3 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors group"
            >
              <Mic className="w-5 h-5 text-gray-400 group-hover:text-purple-500 transition-colors" />
            </button>

            {/* 이미지 업로드 */}
            {!isLoading && (
              <div
                {...(imageFile
                  ? {}
                  : { onClick: () => fileInputRef.current?.click() })}
                className="cursor-pointer"
              >
                <input
                  type="file"
                  accept="image/*"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  className="hidden"
                />

                {imageFile ? (
                  <div className="flex items-center gap-2 bg-purple-50 dark:bg-purple-900/30 px-3 py-1.5 rounded-lg animate-in fade-in">
                    <img
                      src={previewUrl || ""}
                      className="w-8 h-8 rounded object-cover border border-purple-100"
                      alt="preview"
                    />
                    <X
                      className="w-4 h-4 cursor-pointer hover:text-red-500 text-gray-500"
                      onClick={(e) => {
                        e.stopPropagation();
                        setImageFile(null);
                      }}
                    />
                  </div>
                ) : (
                  <p className="hidden sm:block text-xs text-gray-400 px-3 py-2 hover:bg-gray-50 rounded-lg transition-colors">
                    이미지로 검색
                  </p>
                )}
              </div>
            )}
          </div>
        </form>
      </header>

      {/* 🟠 [Loading] 스테퍼 디자인 변경 (Orange -> Violet) */}
      {isLoading && (
        <div className="flex flex-col items-center justify-center py-20 animate-in fade-in duration-500 max-w-7xl mx-auto">
          <h3 className="text-2xl font-bold text-gray-800 dark:text-white mb-10">
            스타일을 분석하고 있습니다...
          </h3>

          <div className="w-full max-w-2xl relative">
            {/* 배경 선 */}
            <div className="absolute top-1/2 left-0 w-full h-1 bg-gray-100 dark:bg-gray-800 -translate-y-1/2 rounded-full z-0"></div>

            {/* 🎨 [Design Update] 진행 선: 보라색 그라데이션 */}
            <div
              className="absolute top-1/2 left-0 h-1 bg-gradient-to-r from-purple-400 to-indigo-600 -translate-y-1/2 rounded-full z-0 transition-all duration-700 ease-in-out"
              style={{
                width: `${
                  (loadingStepIndex / (LOADING_STEPS.length - 1)) * 100
                }%`,
              }}
            ></div>

            {/* 단계별 원 */}
            <div className="relative z-10 flex justify-between w-full">
              {LOADING_STEPS.map((step, index) => {
                const isCompleted = index < loadingStepIndex;
                const isActive = index === loadingStepIndex;

                return (
                  <div key={index} className="flex flex-col items-center group">
                    <div
                      className={`w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all duration-500 shadow-sm
                        ${
                          isCompleted
                            ? "bg-indigo-600 border-indigo-600 text-white"
                            : isActive
                            ? "bg-white dark:bg-gray-800 border-indigo-500 text-indigo-600 scale-110 shadow-[0_0_15px_rgba(99,102,241,0.3)]"
                            : "bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-300"
                        }
                      `}
                    >
                      {isCompleted ? (
                        <Check className="w-5 h-5" />
                      ) : (
                        <span className="text-sm font-bold">{index + 1}</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          <p className="mt-8 text-gray-500 dark:text-gray-400 font-medium text-center animate-pulse min-h-[24px]">
            {LOADING_STEPS[loadingStepIndex].text}
          </p>
        </div>
      )}

      {/* [1단계] Visual RAG 리포트 - 🎨 디자인 리모델링 */}
      {!isLoading && aiAnalysis && (
        <main className="max-w-7xl mx-auto mb-12">
          <div className="bg-white dark:bg-gray-900 rounded-3xl p-8 border border-white/20 shadow-[0_8px_30px_rgb(0,0,0,0.04)] animate-in zoom-in-95 duration-500 overflow-hidden">
            <div className="flex flex-col md:flex-row gap-10 items-start">
              {/* 이미지 & 후보군 */}
              <div className="w-full md:w-1/3 flex-shrink-0 flex flex-col gap-5">
                <div className="relative rounded-2xl overflow-hidden bg-gray-100 dark:bg-gray-800 shadow-md group aspect-[3/4]">
                  <img
                    src={getBustedImage(
                      selectedImage || aiAnalysis.reference_image || ""
                    )}
                    alt="Trend Ref"
                    referrerPolicy="no-referrer"
                    className="object-cover w-full h-full group-hover:scale-105 transition-transform duration-700 ease-out"
                  />
                  <div className="absolute top-4 left-4 bg-white/80 backdrop-blur-md text-gray-800 text-xs font-bold px-3 py-1.5 rounded-full flex gap-1.5 items-center shadow-sm">
                    <TrendingUp className="w-3 h-3 text-purple-600" /> Trend
                    Reference
                  </div>
                </div>

                {/* 후보군 이미지 (가로 스크롤) */}
                {aiAnalysis.candidates && aiAnalysis.candidates.length > 0 && (
                  <div className="animate-in slide-in-from-bottom-2 fade-in">
                    <p className="text-xs text-gray-500 dark:text-gray-400 mb-3 font-medium flex items-center gap-1 ml-1">
                      <ImageIcon className="w-3 h-3" /> 연관 스타일 (클릭하여
                      변경)
                    </p>
                    <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-hide snap-x">
                      {aiAnalysis.candidates.map((cand, idx) => (
                        <button
                          key={idx}
                          onClick={() =>
                            handleSelectCandidateImage(cand.image_base64)
                          }
                          className={`relative w-20 h-24 rounded-xl overflow-hidden flex-shrink-0 border-2 transition-all snap-start ${
                            selectedImage === cand.image_base64
                              ? "border-purple-500 ring-2 ring-purple-100 dark:ring-purple-900/30 scale-105 shadow-md"
                              : "border-transparent hover:border-gray-200 dark:hover:border-gray-700 opacity-70 hover:opacity-100"
                          }`}
                        >
                          <img
                            src={getBustedImage(cand.image_base64)}
                            referrerPolicy="no-referrer"
                            className="w-full h-full object-cover"
                            alt={`candidate ${idx}`}
                          />
                          <div className="absolute bottom-0 w-full bg-black/60 text-[10px] text-white text-center py-1 backdrop-blur-sm">
                            {cand.score}%
                          </div>
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 텍스트 & 액션 버튼 */}
              <div className="flex-1 space-y-8 min-w-0">
                {/* 텍스트 박스 */}
                <div className="bg-gray-50/80 dark:bg-gray-800/50 rounded-3xl p-8 relative min-h-[300px]">
                  <div className="flex items-center justify-between mb-6 flex-wrap gap-4">
                    <div className="flex items-center gap-2">
                      <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
                        <Sparkles className="w-5 h-5 text-purple-600 dark:text-purple-400" />
                      </div>
                      <h2 className="text-xl font-bold text-gray-800 dark:text-gray-100">
                        MODIFY 스타일 분석 리포트
                      </h2>
                    </div>

                    {selectedImage &&
                      selectedImage !== aiAnalysis.reference_image && (
                        <button
                          onClick={handleAnalyzeSelectedImage}
                          disabled={isAnalyzingImage}
                          className="text-xs bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 text-gray-600 dark:text-gray-300 px-4 py-2 rounded-full hover:bg-purple-50 dark:hover:bg-purple-900/20 hover:text-purple-600 hover:border-purple-200 transition-all flex items-center gap-1.5 shadow-sm"
                        >
                          {isAnalyzingImage ? (
                            <RefreshCw className="w-3 h-3 animate-spin" />
                          ) : (
                            <Sparkles className="w-3 h-3" />
                          )}
                          {isAnalyzingImage
                            ? "분석 중..."
                            : "이 스타일 상세 분석"}
                        </button>
                      )}
                  </div>

                  {isAnalyzingImage ? (
                    <div className="flex flex-col items-center justify-center h-48 space-y-4 opacity-60">
                      <RefreshCw className="w-8 h-8 text-purple-500 animate-spin" />
                      <p className="text-sm text-purple-700 dark:text-purple-400 font-medium">
                        새로운 스타일을 분석하고 있습니다...
                      </p>
                    </div>
                  ) : (
                    <div className="prose prose-purple dark:prose-invert max-w-none animate-in fade-in duration-500">
                      <p className="text-gray-700 dark:text-gray-300 leading-8 text-lg whitespace-pre-wrap break-words font-light">
                        {currentText}
                      </p>
                    </div>
                  )}
                </div>

                {/* 액션 버튼 영역 */}
                <div className="space-y-4 animate-in slide-in-from-bottom-4 fade-in">
                  <div className="bg-white dark:bg-gray-800 border border-purple-100 dark:border-gray-700 rounded-2xl px-5 py-3 shadow-sm inline-block relative">
                    <p className="text-gray-800 dark:text-gray-200 font-medium flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></span>
                      분석된 스타일과 유사한 상품을 매칭해드릴까요?
                    </p>
                  </div>

                  <div className="flex flex-wrap gap-4">
                    <button
                      onClick={handleShowProducts}
                      disabled={isSearchingProducts}
                      className="px-8 py-4 bg-gradient-to-r from-purple-600 to-indigo-600 text-white rounded-2xl font-bold hover:shadow-[0_10px_20px_rgba(79,70,229,0.3)] transition-all flex items-center gap-2 active:scale-95 disabled:opacity-50 disabled:shadow-none"
                    >
                      {isSearchingProducts ? (
                        <>
                          <RefreshCw className="w-5 h-5 animate-spin" /> 검색
                          중...
                        </>
                      ) : (
                        <>
                          <Check className="w-5 h-5" /> 추천 코디 전체 보기
                        </>
                      )}
                    </button>

                    <button
                      onClick={handleShowUpperOnly}
                      disabled={isSearchingProducts}
                      className="px-6 py-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 rounded-2xl font-medium hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-purple-300 transition-all disabled:opacity-50"
                    >
                      👕 상의만
                    </button>
                    <button
                      onClick={handleShowLowerOnly}
                      disabled={isSearchingProducts}
                      className="px-6 py-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-700 dark:text-gray-200 rounded-2xl font-medium hover:bg-gray-50 dark:hover:bg-gray-700 hover:border-purple-300 transition-all disabled:opacity-50"
                    >
                      👖 하의만
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </main>
      )}

      {/* [2단계] 상품 리스트 */}
      {!isLoading && showProducts && results.length > 0 && (
        <div
          ref={productSectionRef}
          className="max-w-7xl mx-auto animate-in slide-in-from-bottom-10 duration-700 fade-in space-y-8 pt-8 border-t border-gray-200 dark:border-gray-800"
        >
          <div className="flex items-end justify-between mb-4">
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                추천 상품
              </h2>
              <span className="text-sm font-bold text-purple-600 bg-purple-100 dark:bg-purple-900/50 px-2.5 py-0.5 rounded-full">
                {results.length}
              </span>
              {isSearchingProducts && (
                <RefreshCw className="w-5 h-5 text-gray-400 animate-spin ml-2" />
              )}
            </div>
            <button
              onClick={handleScrollTop}
              className="text-gray-500 dark:text-gray-400 hover:text-purple-600 flex items-center gap-1 text-sm font-medium transition-colors"
            >
              <ArrowUp className="w-4 h-4" /> 분석 다시 보기
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-6">
            {results.map((product) => (
              <ProductCard
                key={`${product.id}-${timestamp}`}
                product={{
                  ...product,
                  image_url: getBustedImage(product.image_url),
                }}
              />
            ))}
          </div>
        </div>
      )}

      {/* 결과 없음 */}
      {!isLoading && showProducts && results.length === 0 && (
        <div className="max-w-md mx-auto text-center py-32 text-gray-500 dark:text-gray-400 animate-in fade-in flex flex-col items-center">
          <div className="w-20 h-20 bg-gray-100 dark:bg-gray-800 rounded-full flex items-center justify-center mb-6">
            <AlertCircle className="w-10 h-10 text-gray-400" />
          </div>
          <p className="text-xl mb-6 font-medium text-gray-800 dark:text-gray-200">
            {aiAnalysis
              ? "분석한 스타일과 일치하는 재고를 찾지 못했어요."
              : "검색 결과가 없습니다."}
          </p>
          <button
            onClick={() => {
              setQuery("");
              window.scrollTo({ top: 0, behavior: "smooth" });
            }}
            className="text-white font-medium bg-gray-900 dark:bg-gray-700 px-8 py-3 rounded-full hover:bg-black transition-all shadow-lg hover:shadow-xl"
          >
            다른 키워드로 검색하기
          </button>
        </div>
      )}

      {/* 스크롤바 숨김 유틸리티 스타일 */}
      <style>{`
        .scrollbar-hide::-webkit-scrollbar {
            display: none;
        }
        .scrollbar-hide {
            -ms-overflow-style: none;
            scrollbar-width: none;
        }
      `}</style>
    </div>
  );
}
