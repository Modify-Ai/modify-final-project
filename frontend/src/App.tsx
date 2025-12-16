import React, { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useUIStore } from "@/store/uiStore";

import Layout from "@/components/layout/Layout";
import Home from "@/pages/Home";
import Search from "@/pages/Search";
import Login from "@/pages/Login";
import Signup from "@/pages/Signup";
import ProductDetail from "@/pages/ProductDetail";
import Profile from "@/pages/Profile";
import Settings from "@/pages/Settings";
import Account from "@/pages/Account"; // ✅ [추가됨] 계정 정보 수정 페이지

// ✅ 장바구니 & 결제 페이지
import Cart from "@/pages/Cart";
import Checkout from "@/pages/Checkout";

// ✅ [Admin] 관리자 페이지 그룹 Import
import Dashboard from "@/pages/admin/Dashboard";
import ProductUpload from "@/pages/admin/ProductUpload";
import ProductManagement from "@/pages/admin/ProductManagement"; // 📦 상품 관리 (목록/수정/삭제)
import CustomerManagement from "@/pages/admin/CustomerManagement"; // 👥 고객 관리
import SalesManagement from "@/pages/admin/SalesManagement"; // 💰 판매(매출) 관리
import AdminRoute from "@/components/routes/AdminRoute";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export default function App() {
  const { isDarkMode } = useUIStore();

  // 다크모드 전역 설정 적용
  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [isDarkMode]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen w-full bg-white dark:bg-gray-900 text-gray-900 dark:text-white transition-colors duration-300">
          <Routes>
            {/* 1. 메인 레이아웃이 적용되는 페이지들 */}
            <Route element={<Layout />}>
              <Route path="/" element={<Home />} />
              <Route path="/search" element={<Search />} />
              <Route path="/products/:id" element={<ProductDetail />} />

              {/* 장바구니 & 결제 */}
              <Route path="/cart" element={<Cart />} />
              <Route path="/checkout" element={<Checkout />} />

              {/* ✨ [Admin] 관리자 전용 라우트 (보호됨) */}
              <Route element={<AdminRoute />}>
                <Route path="/admin" element={<Dashboard />} /> {/* 대시보드 */}
                <Route path="/admin/upload" element={<ProductUpload />} />{" "}
                {/* 상품 등록 (AI/CSV) */}
                <Route
                  path="/admin/products"
                  element={<ProductManagement />}
                />{" "}
                {/* 상품 관리 */}
                <Route
                  path="/admin/customers"
                  element={<CustomerManagement />}
                />{" "}
                {/* 고객 관리 */}
                <Route path="/admin/sales" element={<SalesManagement />} />{" "}
                {/* 판매 관리 */}
              </Route>
            </Route>
            {/* 2. 레이아웃 없는 단독 페이지들 (인증, 설정 등) */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} />
            <Route path="/profile" element={<Profile />} />
            <Route path="/settings" element={<Settings />} />
            <Route path="/account" element={<Account />} />{" "}
            {/* ✅ [추가됨] 계정 페이지 라우트 */}
            {/* 3. 잘못된 경로는 홈으로 리다이렉트 */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
