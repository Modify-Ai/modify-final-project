import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "0.0.0.0", // [유지] 도커 밖에서 접속하려면 필수

    // 👇 [추가됨] 윈도우+도커 환경에서 저장 시 자동반영(HMR) 되게 하는 설정
    watch: {
      usePolling: true,
    },

    proxy: {
      // [유지] 백엔드랑 통신하려면 필수
      "/api": {
        target: process.env.VITE_API_URL || "http://backend-core:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
