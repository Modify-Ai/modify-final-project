import React, { useState } from "react";
import { Menu, Camera, ShoppingBag, ChevronRight } from "lucide-react"; // 아이콘 (설정, 로그아웃 아이콘은 제거하여 심플하게)
import { Link, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore"; // 유저 상태 관리

// ✅ 로고 이미지 불러오기
import logoModifyColor from "@/assets/images/logo-modify-color.png";

// ✅ 프로필 모달 컴포넌트 불러오기
import ProfileModal from "@/components/ui/ProfileModal";

interface HeaderProps {
  onMenuClick: () => void; // 사이드바 열기 함수
}

/**
 * 🧢 Header 컴포넌트
 * - 상단 고정, 투명 배경
 * - 로그인 시 프로필 드롭다운 제공 -> 클릭 시 모달 오픈
 * - 프로필 이름 표시 로직 (뒤에서 2글자) 포함
 */
export default function Header({ onMenuClick }: HeaderProps) {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore(); // 로그인 정보 & 로그아웃 함수

  // -- 🟢 상태 관리 --
  const [isDropdownOpen, setIsDropdownOpen] = useState(false); // 드롭다운 메뉴 열림/닫힘
  const [isProfileModalOpen, setIsProfileModalOpen] = useState(false); // 프로필 수정 모달 열림/닫힘

  // -- 🔵 핸들러 --

  // 로그아웃 처리
  const handleLogout = () => {
    logout();
    setIsDropdownOpen(false); // 메뉴 닫기
    navigate("/"); // 홈으로 이동
  };

  // ✨ [추가됨] 이름을 예쁘게 잘라주는 함수 (권혁준 -> 혁준)
  const getDisplayName = () => {
    if (!user) return "";
    const name = user.full_name || "";

    // 이름이 2글자 이상이면 뒤에서 2글자만 추출
    if (name.length >= 2) {
      return name.slice(-2);
    }
    // 이름이 없거나 1글자면 이름 그대로 혹은 이메일 앞자리 사용
    return name || user.email?.split("@")[0] || "ME";
  };

  return (
    <>
      {/* 헤더 바 (투명 배경) */}
      <header className="fixed top-0 left-0 right-0 h-16 z-30 px-4 flex items-center justify-between transition-colors duration-300 bg-transparent">
        {/* 1. 왼쪽 영역: 햄버거 버튼 + 로고 */}
        <div className="flex items-center gap-4">
          <button
            onClick={onMenuClick}
            className="p-2 -ml-2 text-gray-600 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/10 rounded-full transition-colors"
          >
            <Menu size={24} />
          </button>

          {/* 로고 클릭 시 홈으로 */}
          <Link to="/" className="flex items-center">
            <img
              src={logoModifyColor}
              alt="MODIFY"
              className="h-5 w-auto hover:opacity-80 transition-opacity mb-0.5"
            />
          </Link>
        </div>

        {/* 2. 오른쪽 영역: 가상 피팅 + 장바구니 + 프로필 */}
        <div className="flex items-center gap-3">

          {/* 가상 피팅 아이콘 (항상 보임) */}
          <Link 
            to="/virtual-fitting" 
            className="p-2 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-full transition-colors relative"
          >
            <Camera size={24} />
          </Link>

          {/* 장바구니 아이콘 (항상 보임) */}
          <Link
            to="/cart"
            className="p-2 text-gray-600 dark:text-gray-300 hover:bg-black/5 dark:hover:bg-white/10 rounded-full transition-colors relative"
          >
            <ShoppingBag size={24} />
            {/* 알림 뱃지 (빨간 점) */}
            <span className="absolute top-1 right-1 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white dark:border-gray-900"></span>
          </Link>

          {/* 👇 프로필 영역 (로그인 여부에 따라 다르게 보임) */}
          {user ? (
            <div className="relative">
              {/* 👤 프로필 아이콘 버튼 (클릭 시 드롭다운 토글) */}
              <button
                onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                className="w-9 h-9 rounded-full bg-white border border-gray-200 flex items-center justify-center overflow-hidden hover:ring-2 hover:ring-[#7A51A1] transition-all shadow-sm"
              >
                {/* 프사가 있으면 이미지, 없으면 이름 뒤 2글자 */}
                {user.profile_image ? (
                  <img
                    src={user.profile_image}
                    alt="Profile"
                    className="w-full h-full object-cover"
                  />
                ) : (
                  // ✨ 수정된 함수 적용!
                  <span className="text-xs font-bold text-gray-600">
                    {getDisplayName()}
                  </span>
                )}
              </button>

              {/* ✨ [피그마 스타일 적용] 드롭다운 메뉴 ✨ */}
              {isDropdownOpen && (
                <>
                  {/* 배경 투명막 (화면 아무 데나 누르면 닫히게) */}
                  <div
                    className="fixed inset-0 z-10"
                    onClick={() => setIsDropdownOpen(false)}
                  ></div>

                  {/* 메뉴 박스 (둥글고 그림자 있는 카드) */}
                  {/* p-3 패딩을 줘서 내부 회색 박스를 띄움 */}
                  <div className="absolute right-0 mt-3 w-80 bg-white rounded-[32px] shadow-2xl border border-gray-100 z-20 overflow-hidden animate-fade-in-up p-3">
                    {/* [상단] 프로필 정보 (회색 박스로 독립됨) */}
                    <div className="p-6 flex flex-col items-center justify-center bg-[#F2F4F6] rounded-3xl">
                      {/* 큰 프로필 이미지 + 그라데이션 테두리 */}
                      {/* border-white를 제거하고 패딩만 줘서 그라데이션과 밀착시킴 */}
                      <div className="w-24 h-24 rounded-full bg-gradient-to-tr from-[#7A51A1] to-[#5D93D0] p-[4px] mb-3 shadow-md">
                        <div className="w-full h-full rounded-full bg-[#1A1A1A] flex items-center justify-center overflow-hidden">
                          {user.profile_image ? (
                            <img
                              src={user.profile_image}
                              className="w-full h-full object-cover"
                            />
                          ) : (
                            // ✨ 여기도 수정된 함수 적용! (글씨 크게)
                            <span className="text-3xl font-bold text-white">
                              {getDisplayName()}
                            </span>
                          )}
                        </div>
                      </div>

                      {/* 닉네임 & 이메일 */}
                      <p className="text-xl font-bold text-gray-900">
                        {user.full_name || "사용자"}
                      </p>
                      <p className="text-sm text-gray-500 font-medium mb-1">
                        {user.email}
                      </p>
                    </div>

                    {/* [하단] 메뉴 리스트 */}
                    <div className="p-1 mt-1">
                      {/* 내 프로필 관리 버튼 -> 모달 열기! */}
                      <button
                        onClick={() => {
                          setIsProfileModalOpen(true);
                          setIsDropdownOpen(false);
                        }}
                        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 rounded-2xl transition-colors group text-left mb-1"
                      >
                        <span className="text-[15px] font-semibold text-gray-800">
                          내 프로필 관리
                        </span>
                        <ChevronRight
                          size={18}
                          className="text-gray-400 group-hover:text-gray-600 transition-colors"
                        />
                      </button>

                      {/* 로그아웃 버튼 */}
                      <button
                        onClick={handleLogout}
                        className="w-full flex items-center justify-between p-4 hover:bg-red-50 rounded-2xl transition-colors group text-left"
                      >
                        <span className="text-[15px] font-semibold text-red-500">
                          로그아웃
                        </span>
                        <ChevronRight
                          size={18}
                          className="text-red-300 group-hover:text-red-500 transition-colors"
                        />
                      </button>
                    </div>
                  </div>
                </>
              )}
            </div>
          ) : (
            /* 로그인 안 했을 땐 '로그인' 버튼 노출 */
            <Link
              to="/login"
              className="px-4 py-2 bg-black text-white text-sm font-bold rounded-full hover:bg-gray-800 transition-colors shadow-md ml-1"
            >
              로그인
            </Link>
          )}
        </div>
      </header>

      {/* ✅ 프로필 수정 모달 (isOpen 상태에 따라 렌더링) */}
      <ProfileModal
        isOpen={isProfileModalOpen}
        onClose={() => setIsProfileModalOpen(false)}
      />
    </>
  );
}
