import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/authStore";
import { MousePointer2, CheckCircle2, ArrowLeft } from "lucide-react";
import Modal from "@/components/ui/Modal";

// API URL
const API_BASE_URL = "http://localhost:8000/api/v1";

// 🎨 [Design Component] 민트색 화살표 아이콘
const CyanArrow = () => (
  <svg
    width="8"
    height="10"
    viewBox="0 0 12 14"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    className="ml-1.5 mt-[1px]"
  >
    <path d="M12 7L0 13.9282L0 0.0717969L12 7Z" fill="#64FFDA" />
  </svg>
);

export default function Account() {
  const navigate = useNavigate();
  const { user, token, setUser } = useAuthStore();

  // ✅ "email" 모달 타입 추가됨
  const [activeModal, setActiveModal] = useState<
    "name" | "password" | "phone" | "reset" | "email" | null
  >(null);
  const [isLoading, setIsLoading] = useState(false);

  // 폼 상태
  const [newName, setNewName] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [newPhone, setNewPhone] = useState("");
  const [newEmail, setNewEmail] = useState(""); // ✅ 이메일 상태 추가됨

  const handleGoBack = () => navigate(-1);

  const closeModal = () => {
    setActiveModal(null);
    setNewName("");
    setNewPassword("");
    setConfirmPassword("");
    setNewPhone("");
    setNewEmail("");
  };

  // ----------------------------------------------------------------------
  // ✨ 마스킹 헬퍼 함수들
  // ----------------------------------------------------------------------
  const maskEmail = (email: string) => {
    if (!email) return "";
    const [name, domain] = email.split("@");
    const maskedName =
      name.length > 3 ? name.slice(0, 3) + "*".repeat(name.length - 3) : name;
    return `${maskedName}@${domain}`;
  };

  const formatPhoneNumber = (phone: string | undefined) => {
    if (!phone) return "010-****-**** (미등록)";
    const clean = phone.replace(/[^0-9]/g, "");
    if (clean.length === 11) {
      return `${clean.slice(0, 3)}-****-${clean.slice(7)}`;
    } else if (clean.length === 10) {
      return `${clean.slice(0, 3)}-***-${clean.slice(6)}`;
    }
    return phone;
  };

  // ----------------------------------------------------------------------
  // API 통신
  // ----------------------------------------------------------------------
  const updateProfile = async (data: object, successMessage: string) => {
    if (!token) return;
    setIsLoading(true);

    try {
      const response = await fetch(`${API_BASE_URL}/users/me`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify(data),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => null);
        throw new Error(errorData?.detail || `서버 오류 (${response.status})`);
      }

      const updatedUser = await response.json();
      setUser(updatedUser);
      alert(successMessage);
      closeModal();
    } catch (error: any) {
      console.error(error);
      alert(`업데이트 실패: ${error.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  // ✅ 이메일 변경 핸들러
  const handleSubmitEmail = () => {
    if (!newEmail.trim() || !newEmail.includes("@")) {
      return alert("올바른 이메일 형식을 입력해주세요.");
    }
    updateProfile({ email: newEmail }, "이메일(ID)이 변경되었습니다.");
  };

  const handleSubmitName = () => {
    if (!newName.trim()) return alert("이름을 입력해주세요.");
    updateProfile({ full_name: newName }, "이름이 변경되었습니다.");
  };

  const handleSubmitPassword = () => {
    if (newPassword.length < 6)
      return alert("비밀번호는 6자 이상이어야 합니다.");
    if (newPassword !== confirmPassword)
      return alert("비밀번호가 일치하지 않습니다.");
    updateProfile({ password: newPassword }, "비밀번호가 변경되었습니다.");
  };

  const handleSubmitPhone = () => {
    const cleanPhone = newPhone.replace(/-/g, "");
    if (cleanPhone.length < 10)
      return alert("올바른 휴대폰 번호를 입력해주세요.");

    updateProfile(
      { phone_number: cleanPhone },
      "휴대폰 번호가 변경되었습니다."
    );
  };

  const handleSubmitReset = () => {
    alert("본인인증 정보가 초기화되었습니다.");
    closeModal();
  };

  if (!user)
    return (
      <div className="p-10 text-center">로그인 정보를 불러오는 중입니다...</div>
    );

  return (
    <div className="min-h-screen bg-[#F7F8FA] py-12 px-4 sm:px-6 flex justify-center">
      <div className="w-full max-w-[1000px] bg-white rounded-[2rem] shadow-sm p-12 sm:p-16 relative">
        {/* 뒤로가기 버튼 */}
        <button
          onClick={handleGoBack}
          className="absolute top-8 left-8 p-2 text-gray-400 hover:text-gray-800 transition-colors"
        >
          <ArrowLeft className="w-6 h-6" />
        </button>

        {/* 1. 타이틀 영역 */}
        <div className="flex items-center gap-3 mb-10 mt-2">
          <MousePointer2 className="w-8 h-8 text-black fill-black -rotate-12" />
          <h1 className="text-4xl font-extrabold text-gray-900 tracking-tight">
            계정정보
          </h1>
        </div>

        {/* 2. 프로필 섹션 (회색 박스) */}
        <div className="bg-[#F9FAFB] rounded-xl p-10 mb-12">
          <h2 className="text-xl font-bold text-gray-800 mb-8 border-b border-gray-200 pb-4">
            프로필
          </h2>

          <div className="space-y-8">
            {/* Grid Layout: 라벨(고정폭) | 값(유동폭) | 버튼(우측) */}

            {/* Row 1: Modify ID (변경 가능!) */}
            <div className="grid grid-cols-[100px_1fr_auto] items-center gap-4">
              <span className="text-gray-500 font-medium">MoDify ID</span>
              <span className="text-gray-900 font-bold text-lg">
                {maskEmail(user.email)}
              </span>
              {/* ✅ 버튼 활성화됨 */}
              <button
                onClick={() => {
                  setNewEmail("");
                  setActiveModal("email");
                }}
                className="flex items-center text-gray-900 font-bold hover:opacity-70 transition-opacity"
              >
                변경 <CyanArrow />
              </button>
            </div>

            {/* Row 2: 비밀번호 */}
            <div className="grid grid-cols-[100px_1fr_auto] items-center gap-4">
              <span className="text-gray-500 font-medium">비밀번호</span>
              <span className="text-gray-900 font-bold text-lg tracking-widest">
                ********
              </span>
              <button
                onClick={() => setActiveModal("password")}
                className="flex items-center text-gray-900 font-bold hover:opacity-70 transition-opacity"
              >
                변경 <CyanArrow />
              </button>
            </div>

            {/* Row 3: 이름 */}
            <div className="grid grid-cols-[100px_1fr_auto] items-center gap-4">
              <span className="text-gray-500 font-medium">이름</span>
              <span className="text-gray-900 font-bold text-lg">
                {user.full_name || "이름 없음"}
              </span>
              <button
                onClick={() => {
                  setNewName(user.full_name || "");
                  setActiveModal("name");
                }}
                className="flex items-center text-gray-900 font-bold hover:opacity-70 transition-opacity"
              >
                변경 <CyanArrow />
              </button>
            </div>

            {/* Row 4: 휴대폰 */}
            <div className="grid grid-cols-[100px_1fr_auto] items-center gap-4">
              <span className="text-gray-500 font-medium">휴대폰</span>
              <span className="text-gray-900 font-bold text-lg">
                {formatPhoneNumber(user.phone_number)}
              </span>
              <button
                onClick={() => {
                  setNewPhone(user.phone_number || "");
                  setActiveModal("phone");
                }}
                className="flex items-center text-gray-900 font-bold hover:opacity-70 transition-opacity"
              >
                변경 <span className="text-gray-300 mx-1 font-light">|</span>{" "}
                삭제 <CyanArrow />
              </button>
            </div>
          </div>
        </div>

        {/* 3. 구분선 */}
        <div className="h-px bg-gray-100 w-full mb-12"></div>

        {/* 4. 본인확인 섹션 */}
        <div className="bg-[#F9FAFB] rounded-xl p-10 flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-gray-800 mb-4">본인확인</h2>
            <div className="flex items-center gap-2">
              <span className="text-gray-900 font-bold text-lg">
                본인확인 완료
              </span>
              <CheckCircle2 className="w-5 h-5 text-[#FF5A5A] fill-current" />
            </div>
          </div>

          <button
            onClick={() => setActiveModal("reset")}
            className="bg-white border border-gray-200 px-6 py-3 rounded-lg shadow-sm text-gray-600 font-bold hover:bg-gray-50 transition-colors"
          >
            본인인증 초기화
          </button>
        </div>
      </div>

      {/* --- Modals --- */}

      {/* ✅ [추가됨] 이메일 변경 모달 */}
      <Modal
        isOpen={activeModal === "email"}
        onClose={closeModal}
        title="아이디(이메일) 변경"
      >
        <div className="space-y-4">
          <p className="text-sm text-gray-500 bg-gray-50 p-3 rounded-xl border border-gray-100">
            ⚠️ 아이디를 변경하면 <strong>재 로그인이</strong> 필요합니다.
          </p>
          <input
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-black outline-none bg-gray-50"
            placeholder="새로운 이메일 입력"
          />
          <button
            onClick={handleSubmitEmail}
            disabled={isLoading}
            className="w-full py-3.5 bg-black text-white rounded-xl font-bold hover:opacity-90 transition-opacity"
          >
            {isLoading ? "처리 중..." : "변경하기"}
          </button>
        </div>
      </Modal>

      <Modal
        isOpen={activeModal === "name"}
        onClose={closeModal}
        title="이름 변경"
      >
        <div className="space-y-4">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-black outline-none bg-gray-50"
            placeholder="새 이름"
          />
          <button
            onClick={handleSubmitName}
            disabled={isLoading}
            className="w-full py-3.5 bg-black text-white rounded-xl font-bold hover:opacity-90 transition-opacity"
          >
            {isLoading ? "처리 중..." : "저장하기"}
          </button>
        </div>
      </Modal>

      <Modal
        isOpen={activeModal === "password"}
        onClose={closeModal}
        title="비밀번호 변경"
      >
        <div className="space-y-4">
          <input
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-black outline-none bg-gray-50"
            placeholder="새 비밀번호"
          />
          <input
            type="password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-black outline-none bg-gray-50"
            placeholder="비밀번호 확인"
          />
          <button
            onClick={handleSubmitPassword}
            disabled={isLoading}
            className="w-full py-3.5 bg-black text-white rounded-xl font-bold hover:opacity-90 transition-opacity"
          >
            {isLoading ? "처리 중..." : "변경하기"}
          </button>
        </div>
      </Modal>

      <Modal
        isOpen={activeModal === "phone"}
        onClose={closeModal}
        title="휴대폰 번호 변경"
      >
        <div className="space-y-4">
          <input
            type="text"
            value={newPhone}
            onChange={(e) => setNewPhone(e.target.value)}
            className="w-full px-4 py-3 border rounded-xl focus:ring-2 focus:ring-black outline-none bg-gray-50"
            placeholder="010******** (-없이 입력해주세요)"
          />
          <button
            onClick={handleSubmitPhone}
            disabled={isLoading}
            className="w-full py-3.5 bg-black text-white rounded-xl font-bold hover:opacity-90 transition-opacity"
          >
            {isLoading ? "처리 중..." : "저장하기"}
          </button>
        </div>
      </Modal>

      <Modal
        isOpen={activeModal === "reset"}
        onClose={closeModal}
        title="본인인증 초기화"
      >
        <div className="text-center space-y-6">
          <p className="text-gray-600 font-medium">정말 초기화 하시겠습니까?</p>
          <div className="flex gap-3">
            <button
              onClick={closeModal}
              className="flex-1 py-3 bg-gray-100 rounded-xl font-bold text-gray-600 hover:bg-gray-200"
            >
              취소
            </button>
            <button
              onClick={handleSubmitReset}
              className="flex-1 py-3 bg-[#FF5A5A] text-white rounded-xl font-bold hover:bg-red-600"
            >
              초기화
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
