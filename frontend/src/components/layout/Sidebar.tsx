import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import {
  X,
  ChevronRight,
  Star,
  Trash2,
  Settings,
  User,
  Sun,
  Moon,
  LogOut,
  Heart, // ✅ [추가] 하트 아이콘
} from "lucide-react";
import { useAuthStore } from "@/store/authStore";
import { useSearchStore } from "@/store/searchStore";
import { useUIStore } from "@/store/uiStore";

// ✅ [추가] 위시리스트 모달 불러오기
import WishlistModal from "@/components/product/WishlistModal";

// ✅ [1] 로고 이미지 불러오기 (경로가 정확한지 꼭 확인!)
import logoModifyColor from "@/assets/images/logo-modify-color.png";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function Sidebar({ isOpen, onClose }: SidebarProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { isDarkMode, toggleDarkMode } = useUIStore();

  // ✅ [추가] 위시리스트 모달 상태 관리
  const [isWishlistOpen, setIsWishlistOpen] = useState(false);

  // 검색 기록과 즐겨찾기 데이터를 가져옵니다.
  const {
    recentSearches,
    favorites,
    removeRecentSearch,
    clearRecentSearches,
    toggleFavorite,
  } = useSearchStore();

  // 검색어 클릭 시 이동 핸들러
  const handleItemClick = (keyword: string) => {
    navigate(`/search?q=${encodeURIComponent(keyword)}`);
    onClose();
  };

  // ✨ [이름 표시 함수] 프로필 사진 없을 때 이름(뒤 2글자) 보여주기
  const getDisplayName = () => {
    if (!user) return "";
    const name = user.full_name || "";
    // 이름이 2글자 이상이면 뒤에서 2글자만 추출 (권혁준 -> 혁준)
    if (name.length >= 2) return name.slice(-2);
    // 없으면 이름 그대로 혹은 이메일 앞글자
    return name || user.email?.split("@")[0]?.[0].toUpperCase() || "ME";
  };

  return (
    <>
      {/* 배경 오버레이 (클릭 시 닫힘) */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black/20 dark:bg-black/60 z-40 transition-opacity backdrop-blur-sm"
          onClick={onClose}
        />
      )}

      {/* ✅ [디자인 포인트] 
        1. rounded-r-[20px]: 오른쪽 모서리를 둥글게 처리
        2. bg-[#F7F8FA]: 피그마와 동일한 연한 회색 배경
      */}
      <div
        className={`fixed top-0 left-0 h-full w-80 bg-[#F7F8FA] dark:bg-[#1a1a1a] text-gray-900 dark:text-gray-300 z-50 transform transition-transform duration-300 ease-in-out shadow-2xl flex flex-col rounded-r-[20px] overflow-hidden ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* 1. 상단: 헤더 (로고 & 닫기) */}
        <div className="p-6 border-b border-gray-200 dark:border-gray-800">
          <div className="flex justify-between items-center mb-6">
            {/* ✅ [2] 텍스트 로고 삭제 -> 이미지 로고 교체 */}
            <img
              src={logoModifyColor}
              alt="MODIFY"
              className="h-6 w-auto cursor-pointer"
              onClick={() => {
                navigate("/"); // 로고 누르면 홈으로
                onClose(); // 사이드바 닫기
              }}
            />
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-900 dark:text-gray-400 dark:hover:text-white transition-colors"
            >
              <X size={24} />
            </button>
          </div>

          {/* 👇 유저 프로필 영역 (로그인 여부에 따라 다름) */}
          {user ? (
            // 🚨 [수정됨] 클릭 이벤트(onClick) 제거!
            // 이제 여기를 눌러도 페이지 이동 안 함 (단순 정보 표시용)
            <div className="flex items-center gap-3 p-3 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
              {/* 🖼️ 프로필 이미지 영역 */}
              <div className="w-10 h-10 rounded-full bg-purple-100 dark:bg-purple-900 flex items-center justify-center text-purple-600 dark:text-purple-300 font-bold text-sm overflow-hidden">
                {user.profile_image ? (
                  <img
                    src={user.profile_image}
                    alt="Profile"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  // 이미지가 없으면 이름(혁준) 표시
                  getDisplayName()
                )}
              </div>

              <div className="overflow-hidden">
                {/* 📝 이메일 아이디 */}
                <p className="text-sm font-bold text-gray-900 dark:text-white truncate">
                  {user.email.split("@")[0]}
                </p>
                {/* 📝 이름 (작게 표시) */}
                <p className="text-xs text-gray-400 truncate">
                  {user.full_name || "Member"}
                </p>
              </div>

              {/* 🚨 이동 화살표 아이콘 삭제함 (클릭 안 된다는 의미) */}
            </div>
          ) : (
            // 로그인 안 했을 땐 [로그인하기] 버튼 (이건 클릭 돼야 함!)
            <Link
              to="/login"
              onClick={onClose}
              className="flex items-center justify-between w-full p-3 bg-white dark:bg-purple-900/20 text-purple-700 dark:text-purple-300 rounded-xl font-bold hover:bg-purple-50 dark:hover:bg-purple-900/40 transition-colors shadow-sm border border-purple-100 dark:border-purple-800"
            >
              <div className="flex items-center gap-2">
                <User size={20} />
                <span>로그인하기</span>
              </div>
              <ChevronRight size={18} />
            </Link>
          )}
        </div>

        {/* 2. 메인 컨텐츠 (My Menu, 즐겨찾기, 최근 검색) */}
        <div className="flex-1 overflow-y-auto p-6 space-y-8 scrollbar-hide">
          {/* ✨ [NEW] My Menu 섹션 (위시리스트 버튼) */}
          <section>
            <h3 className="text-xs font-bold text-gray-400 mb-3 uppercase tracking-wider ml-1">
              My Menu
            </h3>
            <div className="space-y-2">
              {/* 💖 위시리스트 버튼 */}
              <button
                onClick={() => setIsWishlistOpen(true)} // 모달 열기!
                className="w-full flex items-center justify-between p-3 bg-white dark:bg-gray-800 border border-gray-100 dark:border-gray-700 rounded-xl hover:shadow-md transition-all group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-full bg-red-50 dark:bg-red-900/20 text-red-500 flex items-center justify-center group-hover:bg-red-100 dark:group-hover:bg-red-900/40">
                    <Heart size={16} fill="currentColor" />
                  </div>
                  <span className="font-bold text-gray-700 dark:text-gray-200">
                    위시리스트
                  </span>
                </div>
                <ChevronRight
                  size={16}
                  className="text-gray-300 group-hover:text-gray-500"
                />
              </button>
            </div>
          </section>

          {/* ⭐ 즐겨찾기 섹션 (검색어) */}
          <div>
            <h3 className="flex items-center gap-2 text-sm font-bold text-gray-800 dark:text-gray-200 mb-3">
              <Star size={16} className="text-orange-500 fill-orange-500" />
              즐겨찾는 검색어
            </h3>
            {favorites.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-600 py-2">
                즐겨찾는 스타일이 없습니다.
              </p>
            ) : (
              <ul className="space-y-2">
                {favorites.map((item, idx) => (
                  <li
                    key={idx}
                    className="group flex justify-between items-center p-2 rounded-lg hover:bg-white dark:hover:bg-gray-800 transition-colors cursor-pointer hover:shadow-sm"
                    onClick={() => handleItemClick(item)}
                  >
                    <span className="text-sm font-medium truncate w-full text-gray-600 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">
                      {item}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleFavorite(item);
                      }}
                      className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all"
                    >
                      <X size={14} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* 🕒 최근 검색 섹션 */}
          <div>
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-sm font-bold text-gray-800 dark:text-gray-200">
                최근 검색
              </h3>

              {/* 기록 삭제 버튼 (기록 있을 때만 보임) */}
              {recentSearches.length > 0 && (
                <button
                  onClick={clearRecentSearches}
                  className="text-xs text-gray-400 hover:text-red-500 flex items-center gap-1 transition-colors px-2 py-1 rounded-md hover:bg-white dark:hover:bg-red-900/20 hover:shadow-sm"
                >
                  <Trash2 size={12} />
                  <span>기록 삭제</span>
                </button>
              )}
            </div>

            {recentSearches.length === 0 ? (
              <p className="text-xs text-gray-400 dark:text-gray-600 py-2">
                최근 검색 기록이 없습니다.
              </p>
            ) : (
              <ul className="space-y-2">
                {recentSearches.map((item, idx) => (
                  <li
                    key={idx}
                    className="group flex justify-between items-center p-2 rounded-lg hover:bg-white dark:hover:bg-gray-800 transition-colors cursor-pointer hover:shadow-sm"
                    onClick={() => handleItemClick(item)}
                  >
                    <span className="text-sm text-gray-600 dark:text-gray-400 group-hover:text-gray-900 dark:group-hover:text-gray-200 truncate w-full">
                      {item}
                    </span>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        removeRecentSearch(item);
                      }}
                      className="p-1.5 opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 transition-all"
                    >
                      <X size={14} />
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

        {/* 3. 하단: 설정 및 테마 토글 */}
        <div className="p-6 border-t border-gray-200 dark:border-gray-800 bg-white/50 dark:bg-[#1a1a1a] space-y-3 backdrop-blur-sm">
          {/* 다크모드 버튼 */}
          <button
            onClick={toggleDarkMode}
            className="w-full flex items-center justify-between px-4 py-3 rounded-xl bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 shadow-sm hover:shadow-md transition-shadow"
          >
            <span className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-gray-300">
              {isDarkMode ? (
                <Moon size={16} className="text-purple-400" />
              ) : (
                <Sun size={16} className="text-orange-500" />
              )}
              {isDarkMode ? "다크 모드" : "라이트 모드"}
            </span>
            <div
              className={`w-9 h-5 rounded-full p-0.5 transition-colors duration-300 ${
                isDarkMode ? "bg-purple-600" : "bg-gray-300"
              }`}
            >
              <div
                className={`w-4 h-4 bg-white rounded-full shadow-sm transform transition-transform duration-300 ${
                  isDarkMode ? "translate-x-4" : "translate-x-0"
                }`}
              />
            </div>
          </button>

          {/* 설정 및 로그아웃 버튼 */}
          <div className="flex items-center justify-between px-2 pt-2">
            <button
              onClick={() => {
                navigate("/settings");
                onClose();
              }}
              className="flex items-center gap-2 text-xs font-medium text-gray-500 hover:text-gray-900 dark:hover:text-gray-300"
            >
              <Settings size={14} /> 설정
            </button>
            {user && (
              <button
                onClick={() => {
                  logout();
                  onClose();
                }}
                className="flex items-center gap-2 text-xs font-medium text-red-500 hover:text-red-600"
              >
                <LogOut size={14} /> 로그아웃
              </button>
            )}
          </div>
        </div>
      </div>

      {/* ✅ [추가] 사이드바 밖에 위시리스트 모달 배치 */}
      <WishlistModal
        isOpen={isWishlistOpen}
        onClose={() => setIsWishlistOpen(false)}
      />
    </>
  );
}
