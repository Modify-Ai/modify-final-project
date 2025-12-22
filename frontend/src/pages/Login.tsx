import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import client from "@/api/client"; // API 요청을 위한 axios 클라이언트
import { useAuthStore } from "@/store/authStore"; // 로그인 상태(토큰, 유저정보) 관리
import { Eye, EyeOff, Check, ChevronDown, Search } from "lucide-react"; // 아이콘
import DaumPostcodeEmbed from 'react-daum-postcode';

// ✅ 이미지 경로 (경로가 정확한지 꼭 확인!)
import loginVisual from "@/assets/images/login-visual.jpg";
import logoModifyColor from "@/assets/images/logo-modify-color.png";

/**
 * 🔐 Login 컴포넌트
 * ------------------------------------------------------------------
 * 1. 로그인 모드: 좌측 폼 + 우측 이미지 (기존 반반 레이아웃 유지)
 * 2. 회원가입 모드: 화면 중앙에 위치한 '카드 형태' (2열 그리드로 컴팩트하게!)
 */

// [추가] 🏠 주소 검색 모달 스타일
const modalStyle = {
  position: 'fixed' as 'fixed',
  top: '50%',
  left: '50%',
  transform: 'translate(-50%, -50%)',
  zIndex: 1000,
  border: '1px solid #ccc',
  background: '#fff',
  width: '400px',
  height: '500px',
  boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
  borderRadius: '8px',
};

const overlayStyle = {
  position: 'fixed' as 'fixed',
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: 'rgba(0,0,0,0.5)',
  zIndex: 999,
};

export default function Login() {
  const navigate = useNavigate();
  const { login } = useAuthStore();

  // -- 🟢 상태 관리 (State) --
  const [isLoginMode, setIsLoginMode] = useState(true); // true: 로그인, false: 회원가입
  const [isLoading, setIsLoading] = useState(false); // API 로딩 상태
  const [showPassword, setShowPassword] = useState(false); // 비밀번호 보이기/숨기기

  // 📝 폼 데이터 (로그인과 회원가입에서 공통으로 사용)
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    fullName: "",
    confirmPassword: "",
    // 👇 회원가입용 추가 정보들
    year: "",
    month: "",
    day: "", // 생년월일
    phone: "",
    authCode: "",
    zipCode: '',        // 우편번호
    address: '',        // 기본주소
    detailAddress: '',  // 상세주소
    agree: false,
  });

  const [error, setError] = useState<string | null>(null);

  // 🔐 기능 상태 (전화번호 인증, 주소 검색)
  const [isPhoneSent, setIsPhoneSent] = useState(false);
  const [isPhoneVerified, setIsPhoneVerified] = useState(false);
  const [isAddressModalOpen, setIsAddressModalOpen] = useState(false);

  // -- 🔵 핸들러 함수 --

  // 입력값 변경 핸들러
  const handleChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value, type } = e.target;
    // 체크박스는 value 대신 checked 값을 사용
    if (type === "checkbox") {
      const target = e.target as HTMLInputElement;
      setFormData({ ...formData, [name]: target.checked });
    } else {
      setFormData({ ...formData, [name]: value });
    }
  };

  // 📮 주소 검색 완료 핸들러
  const handleAddressComplete = (data: any) => {
    let fullAddress = data.address;
    let extraAddress = '';

    if (data.addressType === 'R') {
      if (data.bname !== '') extraAddress += data.bname;
      if (data.buildingName !== '') extraAddress += (extraAddress !== '' ? `, ${data.buildingName}` : data.buildingName);
      fullAddress += (extraAddress !== '' ? ` (${extraAddress})` : '');
    }

    setFormData(prev => ({
      ...prev,
      zipCode: data.zonecode,
      address: fullAddress
    }));
    setIsAddressModalOpen(false);
  };

  // 📱 전화번호 인증 요청 (API 연동)
  const handleSendPhoneAuth = async () => {
    if (!formData.phone) {
      alert("전화번호를 입력해주세요.");
      return;
    }
    try {
      // POST /auth/send-code 요청
      await client.post('/auth/send-code', { 
        phone_number: formData.phone
      });
      
      setIsPhoneSent(true);
      alert("인증번호가 발송되었습니다.\n(서버 콘솔을 확인하세요!)");
      
    } catch (err: any) {
      console.error(err);
      const msg = err.response?.data?.detail || "발송 실패";
      alert(msg);
    }
  };

  // 📱 전화번호 인증 확인 (API 연동)
  const handleVerifyPhoneCode = async () => {
    if (!formData.authCode) {
      alert("인증번호를 입력해주세요.");
      return;
    }

    try {
      // POST /auth/verify-code 요청
      await client.post('/auth/verify-code', { 
        phone_number: formData.phone,
        code: formData.authCode
      });
      
      setIsPhoneVerified(true);
      alert("✅ 인증이 완료되었습니다.");
      
    } catch (err: any) {
      console.error(err);
      const msg = err.response?.data?.detail || "인증 실패";
      alert(msg);
    }
  };

  // 폼 제출 핸들러 (로그인/회원가입 분기 처리)
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true); // 로딩 시작

    try {
      if (isLoginMode) {
        // ============================================================
        // 🔵 [로그인 로직]
        // ============================================================
        const formBody = new URLSearchParams();
        formBody.append("username", formData.email);
        formBody.append("password", formData.password);

        // 1. 로그인 요청
        const response = await client.post("/auth/login", formBody.toString(), {
          headers: { "Content-Type": "application/x-www-form-urlencoded" },
        });

        const { access_token, refresh_token } = response.data;

        // 2. 유저 정보 요청
        const userRes = await client.get("/auth/me", {
          headers: { Authorization: `Bearer ${access_token}` },
        });

        // 3. 스토어 저장 및 이동
        login(access_token, refresh_token, userRes.data);

        if (userRes.data.is_superuser) navigate("/admin", { replace: true });
        else navigate("/", { replace: true });
      } else {
        // ============================================================
        // 🟣 [회원가입 로직]
        // ============================================================

        // 유효성 검사
        if (formData.password !== formData.confirmPassword) {
          setError("비밀번호가 일치하지 않습니다.");
          setIsLoading(false);
          return;
        }
        if (!formData.agree) {
          setError("약관에 동의해주세요.");
          setIsLoading(false);
          return;
        }

        // 생년월일 합치기 (YYYY-MM-DD)
        const birthDatePayload =
          formData.year && formData.month && formData.day
            ? `${formData.year}-${formData.month.padStart(
                2,
                "0"
              )}-${formData.day.padStart(2, "0")}`
            : null;

        // 백엔드 전송
        await client.post("/auth/signup", {
          email: formData.email,
          password: formData.password,
          full_name: formData.fullName,
          phone_number: formData.phone,
          birth_date: birthDatePayload,
          address: formData.address,
          zip_code: formData.zipCode,
          detail_address: formData.detailAddress,
          is_marketing_agreed: formData.agree,
        });

        alert("회원가입이 완료되었습니다! 로그인해주세요.");
        setIsLoginMode(true); // 로그인 화면으로 이동
        setFormData((prev) => ({ ...prev, password: "", confirmPassword: "" }));
      }
    } catch (err: any) {
      console.error(err);
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setError(detail[0].msg);
      } else {
        setError(detail || "요청 처리에 실패했습니다.");
      }
    } finally {
      setIsLoading(false);
    }
  };

  const handleSocialLogin = (provider: string) => {
    alert(`${provider} 로그인은 준비 중입니다.`);
  };

  // ==================================================================================
  // 🟣 [화면 A] 회원가입 모드 (컴팩트한 2열 그리드 디자인)
  // - 세로로 길어지지 않게 가로 공간을 활용합니다.
  // ==================================================================================
  if (!isLoginMode) {
    return (
      <div className="min-h-screen bg-[#F9FAFB] flex flex-col items-center justify-center p-4">
        {/* 🏠 주소 검색 모달 */}
        {isAddressModalOpen && (
          <>
            <div style={overlayStyle} onClick={() => setIsAddressModalOpen(false)} />
            <div style={modalStyle}>
              <DaumPostcodeEmbed onComplete={handleAddressComplete} style={{ height: '100%' }} />
            </div>
          </>
        )}
        {/* 카드 컨테이너 (너비를 800px로 넓혀서 2열 배치가 넉넉하게 함) */}
        <div className="w-full max-w-[800px] bg-white rounded-[32px] shadow-xl p-8 sm:p-10 border border-gray-100">
          {/* 상단 로고 */}
          <div className="text-center mb-8">
            <img
              src={logoModifyColor}
              alt="MODIFY"
              className="h-7 mx-auto cursor-pointer mb-2"
              onClick={() => navigate("/")}
            />
          </div>

          <form onSubmit={handleSubmit} className="space-y-5">
            {/* 1행: 아이디 (중요하니까 한 줄 차지) */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-gray-700 ml-1">
                아이디
              </label>
              <input
                name="email"
                value={formData.email}
                onChange={handleChange}
                placeholder="아이디 입력"
                className="input-field"
                required
              />
            </div>

            {/* 2행: 비밀번호 + 확인 (반반 배치: grid-cols-2) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-gray-700 ml-1">
                  비밀번호
                </label>
                <div className="relative">
                  <input
                    name="password"
                    type={showPassword ? "text" : "password"}
                    value={formData.password}
                    onChange={handleChange}
                    placeholder="비밀번호 입력"
                    className="input-field pr-10"
                    required
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400"
                  >
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-gray-700 ml-1">
                  비밀번호 재확인
                </label>
                <input
                  name="confirmPassword"
                  type="password"
                  value={formData.confirmPassword}
                  onChange={handleChange}
                  placeholder="비밀번호 재확인"
                  className="input-field"
                  required
                />
              </div>
            </div>

            {/* 약관 동의 (체크박스) */}
            <div className="flex items-center gap-2 px-1">
              <input
                type="checkbox"
                name="agree"
                id="agree"
                checked={formData.agree}
                onChange={handleChange}
                className="w-4 h-4 accent-[#7A51A1]"
              />
              <label
                htmlFor="agree"
                className="text-xs text-gray-500 cursor-pointer"
              >
                뉴스 및 이벤트 소식을 수신하는 것에 동의합니다.
              </label>
            </div>

            {/* 3행: 이름 + 생년월일 (반반 배치) */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-gray-700 ml-1">
                  이름
                </label>
                <input
                  name="fullName"
                  value={formData.fullName}
                  onChange={handleChange}
                  placeholder="이름"
                  className="input-field"
                  required
                />
              </div>
              <div className="space-y-1">
                <label className="text-xs font-bold text-gray-700 ml-1">
                  생년월일
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <input
                    name="year"
                    value={formData.year}
                    onChange={handleChange}
                    placeholder="YYYY"
                    className="input-field text-center px-1"
                  />
                  <input
                    name="month"
                    value={formData.month}
                    onChange={handleChange}
                    placeholder="MM"
                    className="input-field text-center px-1"
                  />
                  <input
                    name="day"
                    value={formData.day}
                    onChange={handleChange}
                    placeholder="DD"
                    className="input-field text-center px-1"
                  />
                </div>
              </div>
            </div>

            {/* 📱 전화번호 인증 (핵심 기능) */}
            <div className="space-y-1">
              <label className="text-xs font-bold text-gray-500 ml-1">휴대폰 번호</label>
              <div className="flex gap-2">
                <input
                  name="phone"
                  placeholder="01012345678"
                  value={formData.phone}
                  onChange={handleChange}
                  disabled={isPhoneVerified}
                  className="flex-1 h-12 px-4 bg-gray-100 dark:bg-gray-700/50 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none disabled:opacity-50 dark:text-white"
                />
                <button
                  type="button"
                  onClick={handleSendPhoneAuth}
                  disabled={isPhoneVerified}
                  className="px-4 bg-black text-white rounded-xl text-sm font-bold hover:bg-gray-800 disabled:bg-gray-300 transition-colors whitespace-nowrap"
                >
                  {isPhoneSent ? '재전송' : '인증요청'}
                </button>
              </div>
            </div>

            {/* 인증번호 입력 (조건부 렌더링) */}
            {isPhoneSent && !isPhoneVerified && (
              <div className="flex gap-2 animate-fade-in-down">
                <input
                  name="authCode"
                  placeholder="인증번호 6자리"
                  value={formData.authCode}
                  onChange={handleChange}
                  className="flex-1 h-12 px-4 bg-gray-100 dark:bg-gray-700/50 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none dark:text-white"
                />
                <button
                  type="button"
                  onClick={handleVerifyPhoneCode}
                  className="px-4 bg-purple-100 text-purple-700 rounded-xl text-sm font-bold hover:bg-purple-200 transition-colors whitespace-nowrap"
                >
                  확인
                </button>
              </div>
            )}

            {isPhoneVerified && <p className="text-xs text-green-500 font-bold ml-1">✅ 인증 성공</p>}

            {/* 🏠 주소 검색 (핵심 기능) */}
            <div className="space-y-2 pt-2">
              <label className="text-xs font-bold text-gray-500 ml-1">주소</label>
              <div className="flex gap-2">
                <input
                  name="zipCode"
                  placeholder="우편번호"
                  value={formData.zipCode}
                  readOnly
                  className="w-24 h-12 px-4 bg-gray-100 dark:bg-gray-700/50 rounded-xl outline-none cursor-default dark:text-white"
                />
                <button
                  type="button"
                  onClick={() => setIsAddressModalOpen(true)}
                  className="flex-1 h-12 bg-gray-200 dark:bg-gray-600 text-gray-700 dark:text-white rounded-xl text-sm font-bold flex items-center justify-center gap-2 hover:bg-gray-300 transition-colors"
                >
                  <Search size={16} /> 주소 검색
                </button>
              </div>
              <input
                name="address"
                placeholder="기본 주소"
                value={formData.address}
                readOnly
                className="w-full h-12 px-4 bg-gray-100 dark:bg-gray-700/50 rounded-xl outline-none dark:text-white"
              />
              <input
                name="detailAddress"
                placeholder="상세 주소 (예: 101동 101호)"
                value={formData.detailAddress}
                onChange={handleChange}
                className="w-full h-12 px-4 bg-gray-100 dark:bg-gray-700/50 rounded-xl focus:ring-2 focus:ring-purple-500 outline-none dark:text-white"
              />
            </div>

            {/* 에러 메시지 */}
            {error && (
              <div className="p-2 bg-red-50 text-red-500 text-xs rounded-lg text-center">
                {error}
              </div>
            )}

            {/* 가입 버튼 */}
            <button
              type="submit"
              disabled={isLoading}
              // 🔴 [수정됨] bg-[#6941C6]... 삭제하고 아래 그라데이션 코드로 교체!
              className="w-full h-[54px] mt-4 bg-gradient-to-r from-[#7A51A1] to-[#5D93D0] hover:opacity-90 text-white font-bold rounded-xl transition-all shadow-lg disabled:opacity-70"
            >
              {isLoading ? "처리 중..." : "회원가입"}
            </button>
          </form>

          <div className="mt-4 text-center text-xs text-gray-500">
            이미 계정이 있으신가요?{" "}
            <button
              onClick={() => setIsLoginMode(true)}
              className="font-bold text-[#6941C6] hover:underline"
            >
              로그인
            </button>
          </div>
        </div>

        {/* 스타일: 입력창 배경색(회색), 높이 줄임(46px), 폰트 작게(13px) */}
        <style>{`
          .input-field {
            width: 100%; height: 46px; padding: 0 16px;
            background-color: #E2E4E9; border-radius: 8px; font-size: 13px;
            color: #1F2937; outline: none; border: 1px solid transparent; transition: all 0.2s;
          }
          .input-field:focus { background-color: white; border-color: #7A51A1; box-shadow: 0 0 0 3px rgba(122, 81, 161, 0.1); }
        `}</style>
      </div>
    );
  }

  // ==================================================================================
  // 🔵 [화면 B] 로그인 모드 (기존 반반 화면 유지)
  // ==================================================================================
  return (
    <div className="flex min-h-screen w-full bg-white">
      {/* 1️⃣ 왼쪽: 로그인 폼 영역 */}
      <div className="w-full lg:w-1/2 flex flex-col justify-center items-center px-8 sm:px-12 lg:px-24 xl:px-32 bg-white z-10">
        <div className="w-full max-w-[440px]">
          {/* 로고 영역 */}
          <div className="mb-12 flex flex-col items-center text-center">
            <img
              src={logoModifyColor}
              alt="MODIFY Logo"
              className="h-9 w-auto cursor-pointer mb-2 hover:opacity-90 transition-opacity"
              onClick={() => navigate("/")}
            />
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700 ml-1">
                아이디(이메일)
              </label>
              <input
                name="email"
                type="email"
                placeholder="example@modify.com"
                value={formData.email}
                onChange={handleChange}
                required
                className="w-full h-[54px] px-5 bg-[#F2F4F7] border-none rounded-2xl focus:bg-white focus:ring-2 focus:ring-[#7A51A1] outline-none transition-all placeholder-gray-400 text-gray-900"
              />
            </div>

            <div className="space-y-1">
              <label className="text-sm font-medium text-gray-700 ml-1">
                비밀번호
              </label>
              <div className="relative">
                <input
                  name="password"
                  type={showPassword ? "text" : "password"}
                  placeholder="영문, 숫자 조합 6~20자 입력"
                  value={formData.password}
                  onChange={handleChange}
                  required
                  className="w-full h-[54px] px-5 bg-[#F2F4F7] border-none rounded-2xl focus:bg-white focus:ring-2 focus:ring-[#7A51A1] outline-none transition-all placeholder-gray-400 text-gray-900 pr-12"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                >
                  {showPassword ? <EyeOff size={22} /> : <Eye size={22} />}
                </button>
              </div>
            </div>

            {error && (
              <div className="p-3 bg-red-50 text-red-500 text-sm rounded-xl text-center font-medium">
                {error}
              </div>
            )}

            <div className="flex items-center gap-2 px-1">
              <div className="relative flex items-center">
                <input
                  type="checkbox"
                  id="saveId"
                  className="peer w-5 h-5 cursor-pointer appearance-none rounded-md border border-gray-300 checked:bg-[#7A51A1] checked:border-transparent transition-all"
                />
                <Check
                  size={14}
                  className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 text-white opacity-0 peer-checked:opacity-100 pointer-events-none"
                />
              </div>
              <label
                htmlFor="saveId"
                className="text-sm text-gray-500 cursor-pointer font-medium"
              >
                아이디 저장
              </label>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="w-full h-[54px] bg-gradient-to-r from-[#7A51A1] to-[#5D93D0] hover:opacity-90 text-white font-bold rounded-2xl transition-all text-lg shadow-lg shadow-purple-100 hover:shadow-xl transform active:scale-[0.98] disabled:opacity-70 disabled:cursor-not-allowed"
            >
              {isLoading ? "처리 중..." : "로그인"}
            </button>
          </form>

          {/* 하단 링크들 */}
          <div className="mt-10 text-center">
            <div className="text-sm text-gray-500 mb-8">
              <button className="hover:text-[#7A51A1] hover:underline transition-colors">
                로그인 정보를 잊으셨나요?
              </button>
            </div>

            <div className="relative flex justify-center mb-6">
              <div className="bg-[#7A51A1] text-white text-xs px-4 py-1.5 rounded-full flex items-center gap-1 shadow-md font-bold">
                간편로그인으로 3초만에 시작하기 🚀
                <div className="absolute top-full left-1/2 -translate-x-1/2 -mt-1 w-2.5 h-2.5 bg-[#7A51A1] rotate-45"></div>
              </div>
            </div>

            <div className="flex justify-center gap-5 mb-10">
              <button
                onClick={() => handleSocialLogin("Google")}
                className="w-12 h-12 rounded-full border border-gray-200 flex items-center justify-center hover:bg-gray-50 hover:scale-110 transition-all bg-white shadow-sm"
              >
                <svg className="w-6 h-6" viewBox="0 0 24 24">
                  <path
                    fill="#4285F4"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="#34A853"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="#FBBC05"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.26.81-.58z"
                  />
                  <path
                    fill="#EA4335"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
              </button>
              <button
                onClick={() => handleSocialLogin("Kakao")}
                className="w-12 h-12 rounded-full bg-[#FEE500] flex items-center justify-center hover:opacity-90 hover:scale-110 transition-all shadow-sm text-[#391B1B]"
              >
                <svg className="w-6 h-6 fill-current" viewBox="0 0 24 24">
                  <path d="M12 3c-4.97 0-9 3.185-9 7.115 0 2.557 1.707 4.8 4.27 6.054-.188.702-.682 2.545-.78 2.94-.122.49.178.483.376.351.279-.186 2.946-2.003 4.13-2.809.664.095 1.346.145 2.04.145 4.97 0 9-3.185 9-7.115S16.97 3 12 3z" />
                </svg>
              </button>
              <button
                onClick={() => handleSocialLogin("Naver")}
                className="w-12 h-12 rounded-full bg-[#03C75A] flex items-center justify-center hover:opacity-90 hover:scale-110 transition-all shadow-sm text-white"
              >
                <span className="font-bold text-lg font-sans">N</span>
              </button>
            </div>

            <div className="text-xs text-gray-500 font-medium">
              아직 계정이 없으신가요?{" "}
              <button
                onClick={() => setIsLoginMode(false)}
                className="font-bold text-[#7A51A1] hover:underline ml-1"
              >
                회원가입
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* 2️⃣ 오른쪽: 이미지 영역 (PC 화면에서만 표시) */}
      <div className="hidden lg:block w-1/2 relative bg-white">
        {/* 이미지 모서리 디자인 포인트 🔴
          - rounded-[50px]: 모든 모서리를 둥글게 처리
          - m-4: 상하좌우 여백을 주어 액자처럼 띄움
          - shadow-lg: 그림자를 주어 입체감 살림
        */}
        <div className="absolute inset-0 w-full h-full rounded-[50px] overflow-hidden m-4 shadow-lg">
          <img
            src={loginVisual}
            alt="Fashion Visual"
            className="absolute inset-0 w-full h-full object-cover"
          />
        </div>
      </div>
    </div>
  );
}
