import React, { useState } from "react";
import { useNavigate } from "react-router-dom"; // ⚙️ 페이지 이동을 위한 훅
import { Mic, Heart, Send } from "lucide-react"; // 🎨 아이콘 라이브러리
import { useVoiceControl } from "@/hooks/useVoiceControl"; // ⚙️ 음성 인식 로직
import { useSearchStore } from "@/store/searchStore"; // ⚙️ 검색 기록 저장소 상태 관리
import WishlistModal from "@/components/product/WishlistModal"; // ⚙️ [팀장님 추가] 위시리스트 팝업 컴포넌트

export default function Home() {
  // ⚙️ [Logic] 라우팅 및 상태 관리
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState(""); // 검색어 입력 상태

  // ⚙️ [Logic] 위시리스트 모달 열기/닫기 상태 (팀장님 코드)
  // - false면 닫힘, true면 열림
  const [isWishlistOpen, setIsWishlistOpen] = useState(false);

  // ⚙️ [Logic] 최근 검색어 저장소 연결
  const { addRecentSearch } = useSearchStore();

  // ⚙️ [Logic] 음성 인식 훅 사용
  // - isListening: 듣고 있는지 여부
  // - startListening: 마이크 켜는 함수
  const { isListening, startListening } = useVoiceControl((text) => {
    setPrompt((prev) => (prev ? `${prev} ${text}` : text)); // 기존 텍스트 뒤에 이어 붙이기
  });

  // ⚙️ [Logic] 검색 실행 함수
  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!prompt.trim()) return; // 빈 값이면 실행 안 함

    addRecentSearch(prompt.trim()); // 스토어에 기록 저장
    navigate(`/search?q=${encodeURIComponent(prompt)}`); // 검색 결과 페이지로 이동
  };

  // ⚙️ [Logic] 추천 키워드 클릭 시 검색 실행
  const handleKeywordClick = (keyword: string) => {
    navigate(`/search?q=${encodeURIComponent(keyword)}`);
  };

  // 🎨 [UI Data] 화면에 뿌려줄 텍스트 데이터들
  const topKeywords = ["봄 데이트룩", "미니멀", "오피스룩", "빈티지"];
  const promptCards = [
    {
      text: "다가오는 벚꽃 축제, 화사하게 입고 싶은데 남자친구랑 시밀러 룩 추천해줘",
    },
    { text: "바리스타로서의 매력이 좋아보이는 편안한 룩을 검색해줘" },
    {
      text: "어른들과 함께하는 격식있는 식사자리에서 입을 만한 마무리 검색해줘",
    },
    { text: "해외여행을 앞두고 캐주얼한 복장과 간편한 착장을 추천해줘" },
  ];

  return (
    // 🎨 [Layout] 전체 컨테이너
    // - min-h-[calc...]: 헤더 높이(4rem)를 뺀 만큼 꽉 채우기
    // - dark:bg-black: 다크모드 대응
    <div className="flex flex-col items-center justify-center p-6 transition-colors duration-300 relative min-h-[calc(100vh-4rem)]">
      {/* 🎨 [UI] 메인 타이틀 */}
      {/* - bg-clip-text: 글자 안에 그라데이션 넣기 */}
      <h1 className="text-3xl md:text-5xl font-bold mb-16 text-center tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-purple-600 via-violet-600 to-blue-500 pb-2 mt-12 md:mt-0">
        원하시는 스타일이 무엇인가요?
      </h1>

      {/* 🎨 [UI] 상단 추천 키워드 버튼 영역 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 w-full max-w-7xl mb-8 px-4">
        {topKeywords.map((keyword, idx) => (
          <button
            key={idx}
            onClick={() => handleKeywordClick(keyword)} // ⚙️ 클릭 시 검색 이동
            // 🎨 버튼 스타일: 둥근 모서리, 그림자, 호버 시 살짝 위로 뜸(-translate-y-0.5)
            className="w-full py-3.5 bg-white dark:bg-slate-800 rounded-2xl shadow-[0_2px_8px_rgba(0,0,0,0.04)] border border-slate-100 dark:border-slate-700 text-slate-700 dark:text-slate-200 font-semibold text-lg hover:shadow-lg hover:-translate-y-0.5 hover:text-indigo-600 dark:hover:text-indigo-400 hover:border-indigo-50 dark:hover:border-indigo-900 transition-all duration-300"
          >
            {keyword}
          </button>
        ))}
      </div>

      {/* 🎨 [UI] 추천 질문 카드 영역 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5 w-full max-w-7xl mb-14 px-4">
        {promptCards.map((card, idx) => (
          <div
            key={idx}
            onClick={() => setPrompt(card.text)} // ⚙️ 클릭 시 입력창에 텍스트 채움
            // 🎨 카드 스타일: hover 시 테두리 색상 변경 및 그림자 강화
            className="group bg-white dark:bg-slate-800 p-6 rounded-2xl shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] border border-white dark:border-slate-700 hover:border-purple-50 dark:hover:border-slate-600 cursor-pointer hover:shadow-[0_8px_30px_-4px_rgba(0,0,0,0.1)] hover:-translate-y-1 transition-all duration-300 flex items-center h-full min-h-[100px]"
          >
            <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed group-hover:text-slate-800 dark:group-hover:text-slate-200 font-medium">
              {card.text}
            </p>
          </div>
        ))}
      </div>

      {/* 🎨 [UI] 메인 입력창 영역 (가장 큰 박스) */}
      <div className="w-full max-w-7xl px-4 relative">
        <div className="relative bg-white dark:bg-slate-800 rounded-[2.5rem] p-6 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.1)] border border-slate-50 dark:border-slate-700 flex gap-6 transition-all hover:shadow-[0_30px_70px_-15px_rgba(0,0,0,0.12)] mb-4">
          {/* 🎨 [UI] 마이크 버튼 */}
          <button
            onClick={startListening} // ⚙️ 음성 인식 시작
            // ⚙️ 상태에 따른 스타일 분기: 듣고 있으면 빨간색(bg-red-500), 아니면 그라데이션
            className={`w-16 h-16 shrink-0 rounded-2xl flex items-center justify-center text-white shadow-xl transition-all duration-300
              ${
                isListening
                  ? "bg-red-500 animate-pulse ring-4 ring-red-100 dark:ring-red-900"
                  : "bg-gradient-to-br from-indigo-500 to-purple-600 hover:scale-105 hover:shadow-indigo-200 dark:hover:shadow-none"
              }
            `}
            title="음성으로 입력하기"
          >
            <Mic size={28} className="stroke-[2.5]" />
          </button>

          {/* 🎨 [UI] 텍스트 입력 필드 Wrapper */}
          <div className="flex-1 flex flex-col min-h-[160px]">
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)} // ⚙️ 입력값 상태 업데이트
              onKeyDown={(e) => {
                // ⚙️ 엔터키 입력 시 검색 실행 (Shift+Enter는 줄바꿈)
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSearch();
                }
              }}
              placeholder={
                isListening
                  ? "말씀해주세요..."
                  : "원하는 스타일을 입력하거나 위의 예시를 클릭 해주세요"
              }
              // 🎨 텍스트영역 스타일: 테두리 없음, 투명 배경, 리사이즈 금지
              className="w-full h-full bg-transparent border-none outline-none text-xl resize-none placeholder-slate-300 dark:placeholder-slate-600 text-slate-800 dark:text-slate-100 leading-relaxed pt-2"
            />

            {/* 🎨 [UI] 하단 컨트롤 바 (글자수 + 전송 버튼) */}
            <div className="flex justify-end items-end pb-1">
              <div className="flex items-center gap-4">
                {/* 🎨 글자수 표시 */}
                <span className="text-xs text-slate-400 dark:text-slate-500 font-medium">
                  {prompt.length} / 1000
                </span>

                {/* 🎨 전송 버튼 */}
                <button
                  onClick={() => handleSearch()} // ⚙️ 검색 실행
                  disabled={!prompt.trim()} // ⚙️ 내용 없으면 비활성화
                  className="p-3 text-slate-300 dark:text-slate-600 hover:text-indigo-600 dark:hover:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-slate-700 rounded-full transition-all disabled:opacity-30"
                >
                  <Send size={24} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* 🔗 [Integration] 팀장님 기능(Modal) + 내 디자인(Button) 융합 */}
        <div className="flex justify-start">
          <button
            onClick={() => setIsWishlistOpen(true)} // ⚙️ 모달 열기 상태 true로 변경
            // 🎨 검정색 배경, 둥근 모서리, 하트 아이콘 배치
            className="flex items-center gap-2 px-4 py-2 bg-slate-900 dark:bg-slate-700 text-white rounded-xl text-xs font-bold tracking-wide hover:bg-slate-800 dark:hover:bg-slate-600 transition-all shadow-md hover:shadow-lg"
          >
            <Heart size={14} className="fill-current text-red-500" />
            Wishlist
          </button>
        </div>

        {/* 🎨 [UI] 음성 인식 중일 때 나타나는 애니메이션 배지 */}
        {isListening && (
          <div className="absolute -top-14 left-1/2 -translate-x-1/2 bg-slate-900/90 backdrop-blur text-white px-6 py-3 rounded-full text-sm font-medium animate-bounce shadow-2xl flex items-center gap-3">
            <span className="w-2.5 h-2.5 bg-red-500 rounded-full animate-pulse" />
            듣고 있어요...
          </div>
        )}
      </div>

      {/* ⚙️ [Logic] 위시리스트 모달 (화면에는 안 보이다가 isOpen이 true일 때만 뜸) */}
      <WishlistModal
        isOpen={isWishlistOpen}
        onClose={() => setIsWishlistOpen(false)} // 닫기 버튼 누르면 false로 변경
      />
    </div>
  );
}
