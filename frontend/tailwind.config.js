/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class", // 수동 제어
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#6366f1", // Indigo 500
          dark: "#4338ca",
        },
        dark: {
          bg: "#111827", // Gray 900
          card: "#1f2937", // Gray 800
        },
      },
      // 👇 [수정됨] 폰트 설정: Pretendard를 1순위로, 뒤에 시스템 폰트들을 안전장치로 배치
      fontFamily: {
        sans: ["Pretendard", "ui-sans-serif", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
