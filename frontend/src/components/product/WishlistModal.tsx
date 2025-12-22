import React from "react";
import { useQuery } from "@tanstack/react-query";
import client from "../../api/client";
import Modal from "../ui/Modal";
import ProductCard from "./ProductCard";
import { Loader2, ShoppingBag } from "lucide-react"; // Heart는 제목에서 뺐으니 여기서도 지워도 돼

interface WishlistModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function WishlistModal({ isOpen, onClose }: WishlistModalProps) {
  // 위시리스트 데이터 가져오기
  const { data: products, isLoading } = useQuery({
    queryKey: ["my-wishlist"],
    queryFn: async () => {
      const res = await client.get("/wishlist/");
      return res.data;
    },
    enabled: isOpen,
  });

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      // 👇 [수정함] 이제 빨간 줄 안 뜰 거야! 그냥 글자만 딱 넣자.
      title="My Wishlist"
      maxWidth="max-w-5xl"
    >
      <div className="min-h-[300px]">
        {isLoading ? (
          <div className="flex justify-center items-center h-64">
            <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
          </div>
        ) : !products || products.length === 0 ? (
          <div className="flex flex-col justify-center items-center h-64 text-gray-400 gap-4">
            <ShoppingBag className="w-16 h-16 opacity-20" />
            <p>아직 찜한 상품이 없습니다.</p>
            <button
              onClick={onClose}
              className="text-sm text-indigo-600 font-bold hover:underline"
            >
              쇼핑하러 가기
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4 pb-4">
            {products.map((product: any) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}
