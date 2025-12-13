import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useUIStore } from '@/store/uiStore';

import Layout from '@/components/layout/Layout';
import Home from '@/pages/Home';
import Search from '@/pages/Search';
import MoodSearch from '@/pages/MoodSearch'; // ✅ [NEW] 무드 검색 페이지
import Login from '@/pages/Login';
import Signup from '@/pages/Signup'; // 👈 [NEW] 회원가입 페이지 추가
import ProductDetail from '@/pages/ProductDetail';
import Profile from '@/pages/Profile';
import Settings from '@/pages/Settings';

// ✅ 장바구니 & 결제 페이지
import Cart from '@/pages/Cart';
import Checkout from '@/pages/Checkout';

import Dashboard from '@/pages/admin/Dashboard';
import ProductUpload from '@/pages/admin/ProductUpload';
import AdminRoute from '@/components/routes/AdminRoute'; 

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

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen w-full bg-white dark:bg-gray-900 text-gray-900 dark:text-white transition-colors duration-300">
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Home />} />
              <Route path="/search" element={<Search />} />
              <Route path="/products/:id" element={<ProductDetail />} />
              
              {/* ✅ 장바구니 & 결제 라우트 */}
              <Route path="/cart" element={<Cart />} />
              <Route path="/checkout" element={<Checkout />} />
              
              {/* 관리자 라우트 */}
              <Route element={<AdminRoute />}> 
                <Route path="/admin" element={<Dashboard />} />
                <Route path="/admin/upload" element={<ProductUpload />} />
              </Route>
            </Route>
            
            {/* 인증 및 사용자 페이지 */}
            <Route path="/login" element={<Login />} />
            <Route path="/signup" element={<Signup />} /> {/* 👈 [NEW] 라우트 연결 */}
            <Route path="/profile" element={<Profile />} />
            <Route path="/settings" element={<Settings />} />

            {/* 무드 검색 페이지 */}
            <Route path="/mood-search" element={<MoodSearch />} />
            
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}