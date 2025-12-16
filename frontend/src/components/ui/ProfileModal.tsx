import React, { useState, useRef, useEffect } from "react";
import { useAuthStore } from "@/store/authStore";
import client from "@/api/client";
import {
  Camera,
  X,
  Save,
  Settings,
  LogOut,
  ArrowLeft,
  Trash2,
} from "lucide-react";
import { useNavigate } from "react-router-dom";

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function ProfileModal({ isOpen, onClose }: ProfileModalProps) {
  const navigate = useNavigate();
  const { user, setUser, logout } = useAuthStore();

  // -- 🟢 상태 관리 --
  const [nickname, setNickname] = useState("");
  const [previewImage, setPreviewImage] = useState<string | null>(null);

  // 실제 업로드할 파일 객체 (이게 있어야 서버로 전송 가능!)
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  // 🗑️ [이미지 삭제 상태]
  // true면 "사용자가 이미지를 지웠음"을 의미 -> 나중에 저장 시 null을 보내서 DB 비움
  const [isImageDeleted, setIsImageDeleted] = useState(false);

  const [isLoading, setIsLoading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // 모달 열릴 때마다 초기 데이터 세팅 (기존 정보 불러오기)
  useEffect(() => {
    if (isOpen && user) {
      setNickname(user.full_name || "");
      setPreviewImage(user.profile_image || null);
      setSelectedFile(null);
      setIsImageDeleted(false); // 삭제 상태 초기화
    }
  }, [isOpen, user]);

  if (!isOpen) return null;

  // -- 🔵 핸들러 함수들 --

  // 📸 [변경] 이미지 선택 핸들러
  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const imageUrl = URL.createObjectURL(file);
      setPreviewImage(imageUrl); // 화면에 미리보기 보여주기
      setSelectedFile(file); // 업로드할 파일 저장
      setIsImageDeleted(false); // "삭제됨" 상태 취소 (새거 올렸으니까!)
    }
  };

  // 🗑️ [삭제] 이미지 삭제 핸들러
  const handleDeleteImage = () => {
    setPreviewImage(null); // 미리보기 제거 (이니셜 나오게 함)
    setSelectedFile(null); // 선택된 파일 제거
    setIsImageDeleted(true); // "나 사진 지웠어!" 표시 (나중에 null 전송용)
    if (fileInputRef.current) fileInputRef.current.value = ""; // 인풋값 초기화
  };

  // ✨ [이름 표시 함수] 모달에서도 "혁준"처럼 나오게!
  const getDisplayName = () => {
    const name = nickname || user?.full_name || ""; // 입력 중인 닉네임이 있으면 그거 우선 표시
    if (name.length >= 2) return name.slice(-2); // 2글자 이상이면 뒤에서 자름
    return name || user?.email?.[0].toUpperCase() || "ME"; // 없으면 이메일 앞글자
  };

  // 💾 [저장] 버튼 핸들러 (여기가 핵심 로직!)
  const handleSave = async () => {
    if (!nickname.trim()) return alert("닉네임을 입력해주세요.");
    setIsLoading(true);

    try {
      // 기본값은 undefined (변경 없음)
      // undefined를 보내면 백엔드가 "아, 사진은 안 바꾸는구나" 하고 무시함
      let finalImageUrl: string | null | undefined = undefined;

      // 경우의 수 1: 새 파일을 선택했다면? -> 업로드 후 URL 사용
      if (selectedFile) {
        const formData = new FormData();
        formData.append("file", selectedFile);
        const uploadRes = await client.post("/utils/upload/image", formData, {
          headers: { "Content-Type": "multipart/form-data" },
        });
        finalImageUrl = uploadRes.data.url;
      }
      // 경우의 수 2: 파일은 없는데 삭제 버튼을 눌렀다면? -> DB를 비워야 함 (null 전송)
      else if (isImageDeleted) {
        finalImageUrl = null;
      }

      // (아무것도 안 건드렸으면 finalImageUrl은 undefined -> 기존 사진 유지됨)

      // 3. 프로필 정보 업데이트 (PATCH)
      const updateData: any = { full_name: nickname };

      // 이미지가 변경된 경우에만 필드 추가 (undefined면 안 보냄)
      if (finalImageUrl !== undefined) {
        updateData.profile_image = finalImageUrl;
      }

      const response = await client.patch("/users/me", updateData);

      setUser(response.data);
      alert("프로필이 수정되었습니다! ✨");
      onClose(); // 저장 후 닫기
    } catch (error) {
      console.error(error);
      alert("수정에 실패했습니다.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <>
      {/* 1. 투명 배경 오버레이 (화면 다른 곳 클릭 시 닫기용) */}
      <div
        className="fixed inset-0 z-40 bg-transparent cursor-default"
        onClick={onClose}
      />

      {/* 2. 팝업 컨텐츠 (위치 변경됨!) */}
      {/* fixed top-20 right-4: 헤더(h-16) 바로 아래 오른쪽 끝에 배치 */}
      <div className="fixed top-20 right-4 z-50 w-full max-w-[400px] bg-white rounded-[32px] shadow-2xl border border-gray-100 overflow-hidden animate-fade-in-up m-4">
        {/* ✨ [핵심] 좌->우 게이지 애니메이션 Bar (차올랐다가 투명해짐!) */}
        {/* h-1.5: 게이지 높이 */}
        <div className="h-1.5 w-full bg-gray-100">
          <div className="h-full bg-gradient-to-r from-[#7A51A1] to-[#5D93D0] animate-gauge-fill-fade" />
        </div>

        {/* 컨텐츠 영역 (스크롤 가능) */}
        <div className="p-8 relative max-h-[80vh] overflow-y-auto scrollbar-hide">
          {/* 닫기 버튼 */}
          <button
            onClick={onClose}
            className="absolute top-4 right-4 text-gray-400 hover:text-gray-600 transition-colors"
          >
            <X size={24} />
          </button>

          <div className="flex flex-col items-center mt-2">
            <h2 className="text-2xl font-bold text-gray-800 mb-8">
              프로필 편집
            </h2>

            {/* 🖼️ 프사 영역 (피그마 스타일) */}
            <div className="relative group mb-8">
              {/* 그라데이션 테두리 박스 */}
              <div className="w-32 h-32 rounded-full bg-gradient-to-tr from-[#7A51A1] to-[#5D93D0] p-[4px] shadow-lg">
                <div className="w-full h-full rounded-full bg-[#1A1A1A] flex items-center justify-center overflow-hidden border-2 border-white relative">
                  {previewImage ? (
                    <img
                      src={previewImage}
                      alt="Profile"
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <span className="text-4xl font-bold text-white">
                      {getDisplayName()}
                    </span>
                  )}
                </div>
              </div>

              {/* 📸 변경 버튼 (우측 하단) */}
              <button
                onClick={() => fileInputRef.current?.click()}
                className="absolute bottom-1 right-1 w-10 h-10 bg-[#7A51A1] text-white rounded-full flex items-center justify-center shadow-md hover:bg-[#6941C6] transition-all border-2 border-white z-10"
              >
                <Camera size={18} />
              </button>

              {/* 🗑️ 삭제 버튼 (좌측 하단) - 이미지가 있을 때만 보임 */}
              {previewImage && (
                <button
                  onClick={handleDeleteImage}
                  className="absolute bottom-1 left-1 w-10 h-10 bg-gray-200 text-gray-600 rounded-full flex items-center justify-center shadow-md hover:bg-red-100 hover:text-red-500 transition-all border-2 border-white z-10"
                >
                  <Trash2 size={18} />
                </button>
              )}

              <input
                type="file"
                ref={fileInputRef}
                className="hidden"
                accept="image/*"
                onChange={handleImageChange}
              />
            </div>

            {/* 📝 닉네임 입력 */}
            <div className="w-full space-y-2 mb-8">
              <label className="text-sm font-bold text-gray-600 ml-1">
                닉네임
              </label>
              <input
                type="text"
                value={nickname}
                onChange={(e) => setNickname(e.target.value)}
                className="w-full h-[54px] px-5 bg-[#F2F4F7] border-none rounded-2xl focus:bg-white focus:ring-2 focus:ring-[#7A51A1] outline-none transition-all text-center text-lg font-medium text-gray-800"
                placeholder="닉네임을 입력하세요"
              />
            </div>

            {/* 저장 버튼 */}
            <button
              onClick={handleSave}
              disabled={isLoading}
              className="w-full h-[54px] bg-gradient-to-r from-[#7A51A1] to-[#5D93D0] hover:opacity-90 text-white font-bold rounded-2xl transition-all shadow-lg flex items-center justify-center gap-2 disabled:opacity-70"
            >
              {isLoading ? (
                "저장 중..."
              ) : (
                <>
                  <Save size={20} /> 저장하기
                </>
              )}
            </button>

            {/* 하단 링크들 */}
            <div className="w-full mt-8 pt-8 border-t border-gray-100 space-y-3">
              <p className="text-xs text-gray-400 font-medium ml-2 mb-2">
                계정 관리
              </p>

              {/* 계정 설정으로 이동 (주소 수정됨!) */}
              <button
                onClick={() => {
                  onClose();
                  navigate("/account"); // 👈 여기가 진짜 계정 설정 페이지 주소!
                }}
                className="w-full flex items-center justify-between p-4 bg-gray-50 hover:bg-gray-100 rounded-2xl transition-colors group"
              >
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-gray-500 shadow-sm group-hover:text-[#7A51A1]">
                    <Settings size={20} />
                  </div>
                  <div className="text-left">
                    <p className="text-sm font-bold text-gray-700">
                      계정 및 보안 설정
                    </p>
                    <p className="text-xs text-gray-400">
                      비밀번호 변경, 전화번호 관리
                    </p>
                  </div>
                </div>
                <ArrowLeft size={18} className="text-gray-300 rotate-180" />
              </button>

              {/* 로그아웃 버튼 */}
              <button
                onClick={() => {
                  onClose();
                  logout();
                  navigate("/login");
                }}
                className="w-full flex items-center justify-center p-3 text-red-500 text-sm font-medium hover:bg-red-50 rounded-xl transition-colors"
              >
                <LogOut size={16} className="mr-2" /> 로그아웃
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ✨ 애니메이션: 0.8초 동안 차오르고(0~70%), 마지막에 투명해짐(70~100%) */}
      {/* 이 스타일이 있어야 게이지가 예쁘게 사라짐! */}
      <style>{`
        @keyframes gaugeFillAndFade {
          0% { width: 0%; opacity: 1; }
          70% { width: 100%; opacity: 1; } 
          100% { width: 100%; opacity: 0; }
        }
        .animate-gauge-fill-fade {
          animation: gaugeFillAndFade 0.8s ease-in-out forwards;
        }
      `}</style>
    </>
  );
}
