import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";

// 1. 백엔드 데이터 타입 정의 (휴대폰 번호 등 필드 추가)
export interface User {
  id: number;
  email: string;
  full_name?: string;
  is_active: boolean;
  is_superuser: boolean;
  phone_number?: string; // ✨ 추가됨: 프로필 페이지에서 사용
  is_marketing_agreed?: boolean; // ✨ 추가됨: 마케팅 동의 여부
  provider?: string;

  // 🟢 [FE 수정] 프로필 이미지 필드 추가
  // 사유: 백엔드 User 스키마에는 존재하지만 프론트 타입 정의에 누락되어 있어,
  // 프로필 조회 및 수정 시 타입 에러가 발생함. 이를 해결하기 위해 추가.
  profile_image?: string;
}

interface AuthState {
  token: string | null;
  refreshToken: string | null;
  user: User | null;
  isAdmin: boolean;

  // 로그인 함수
  login: (token: string, refreshToken: string, user: User) => void;

  // Access Token만 교체하는 함수
  setAccessToken: (token: string) => void;

  // 로그아웃
  logout: () => void;

  // ✨ 프로필 업데이트용 함수 (이름을 setUser로 변경하여 Profile.tsx와 맞춤)
  setUser: (user: User) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      refreshToken: null,
      user: null,
      isAdmin: false,

      // 로그인 시 실행
      login: (token, refreshToken, user) => {
        set({
          token: token,
          refreshToken: refreshToken,
          user: user,
          isAdmin: user.is_superuser,
        });
        console.log("✅ Logged In:", user.email);
      },

      // 토큰 갱신 시 실행
      setAccessToken: (token) => {
        set({ token: token });
      },

      // 로그아웃 시 실행
      logout: () => {
        set({ token: null, refreshToken: null, user: null, isAdmin: false });
        localStorage.removeItem("auth-storage");
      },

      // 프로필 정보 업데이트
      setUser: (updatedUser) => {
        set((state) => ({
          // 🟢 [FE 수정] 상태 병합 로직 개선
          // 사유: 기존에는 updatedUser로 덮어쓰기만 하여, 일부 필드만 업데이트 될 때
          // 기존 데이터가 유실될 위험이 있었음. Spread 연산자로 기존 state.user와 병합하도록 수정.
          user: state.user ? { ...state.user, ...updatedUser } : updatedUser,
          isAdmin: updatedUser.is_superuser,
        }));
      },
    }),
    {
      name: "auth-storage",
      storage: createJSONStorage(() => localStorage),
    }
  )
);
