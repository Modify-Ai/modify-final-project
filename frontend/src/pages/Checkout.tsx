import React, { useState, useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import axios from "axios";
import {
  ArrowLeft,
  CreditCard,
  Truck,
  User,
  CheckCircle,
  ShieldCheck,
  Package,
  AlertCircle,
  Search,
  Home,
  Clock,
  Plus,
  Smartphone,
  Building2,
} from "lucide-react";

// --- Icons (Brand Logos) ---
const KakaoSymbol = () => (
  <svg viewBox="0 0 24 24" className="w-full h-full" fill="currentColor">
    <path d="M12 3C5.925 3 1 6.925 1 11.775c0 2.9 1.75 5.5 4.625 7.125-.2 2.375-1.6 5.375-1.625 5.425 0 .05.025.1.075.125.025.025.075.025.1 0 .025 0 2.375-1.6 4.975-3.4 1 .15 1.85.225 2.85.225 6.075 0 11-3.925 11-8.775C23 6.925 18.075 3 12 3z" />
  </svg>
);

const NaverSymbol = () => (
  <svg viewBox="0 0 24 24" className="w-full h-full" fill="currentColor">
    <path d="M16.9 3v9.6L7.1 3H3v18h4.1v-9.6L16.9 21H21V3h-4.1z" />
  </svg>
);

const TossSymbol = () => (
  <svg viewBox="0 0 24 24" className="w-full h-full" fill="currentColor">
    <path d="M19.7 7.7c-.5-.3-1.1-.1-1.4.4L13 17.6c-.3.5-.1 1.1.4 1.4.5.3 1.1.1 1.4-.4l5.3-9.5c.3-.5.1-1.1-.4-1.4zM4.3 7.7c.5-.3 1.1-.1 1.4.4l5.3 9.5c.3.5.1 1.1-.4 1.4-.5.3-1.1.1-1.4-.4L3.9 9.1c-.3-.5-.1-1.1.4-1.4z" />
    <path d="M12 4c.6 0 1 .4 1 1v2.5c0 .6-.4 1-1 1s-1-.4-1-1V5c0-.6.4-1 1-1z" />
  </svg>
);

// --- Payment Method Definitions ---
const PAYMENT_METHODS = [
  {
    id: "card",
    label: "신용/체크",
    color: "text-purple-600",
    bg: "bg-purple-50",
    border: "border-purple-200",
    icon: <CreditCard className="w-8 h-8" />,
  },
  {
    id: "kakao",
    label: "카카오페이",
    color: "text-[#391B1B]",
    bg: "bg-[#FAE100]/10",
    border: "border-[#FAE100]",
    icon: (
      <div className="w-8 h-8 text-[#391B1B]">
        <KakaoSymbol />
      </div>
    ),
  },
  {
    id: "naver",
    label: "네이버페이",
    color: "text-[#03C75A]",
    bg: "bg-[#03C75A]/10",
    border: "border-[#03C75A]",
    icon: (
      <div className="w-8 h-8 text-[#03C75A]">
        <NaverSymbol />
      </div>
    ),
  },
  {
    id: "toss",
    label: "토스페이",
    color: "text-[#0064FF]",
    bg: "bg-[#0064FF]/10",
    border: "border-[#0064FF]",
    icon: (
      <div className="w-8 h-8 text-[#0064FF]">
        <TossSymbol />
      </div>
    ),
  },
  {
    id: "bank",
    label: "무통장입금",
    color: "text-gray-700",
    bg: "bg-gray-100",
    border: "border-gray-300",
    icon: <Building2 className="w-8 h-8" />,
  },
  {
    id: "phone",
    label: "휴대폰결제",
    color: "text-gray-700",
    bg: "bg-gray-100",
    border: "border-gray-300",
    icon: <Smartphone className="w-8 h-8" />,
  },
];

interface CartItem {
  id: number;
  name: string;
  price: number;
  image_url?: string; // [수정] 옵셔널로 변경
  image?: string;     // [수정] image 속성 추가 (장바구니 호환)
  quantity: number;
  size?: string;
}

interface OrdererInfo {
  name: string;
  phone: string;
  email: string;
}

interface ShippingInfo {
  name: string;
  phone: string;
  zipCode: string;
  address: string;
  addressDetail: string;
  memo: string;
  addressType: "home" | "recent" | "new";
}

const SIZE_OPTIONS = ["XS", "S", "M", "L", "XL", "XXL", "FREE"];

export default function Checkout() {
  const navigate = useNavigate();
  const location = useLocation();

  const [cartItems, setCartItems] = useState<CartItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [orderComplete, setOrderComplete] = useState(false);
  const [orderId, setOrderId] = useState<string>("");

  const [ordererInfo, setOrdererInfo] = useState<OrdererInfo>({
    name: "",
    phone: "",
    email: "",
  });
  const [shippingInfo, setShippingInfo] = useState<ShippingInfo>({
    name: "",
    phone: "",
    zipCode: "",
    address: "",
    addressDetail: "",
    memo: "문 앞에 놓아주세요",
    addressType: "new",
  });
  const [sameAsOrderer, setSameAsOrderer] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<string>("card");
  const [usePoints, setUsePoints] = useState(0);
  const [availablePoints] = useState(1050);

  useEffect(() => {
    const loadItems = () => {
      try {
        if (location.state?.directBuy && location.state?.product) {
          setCartItems([location.state.product]);
        } else {
          const saved = localStorage.getItem("cart");
          if (saved) {
            const items = JSON.parse(saved);
            if (items.length === 0) {
              navigate("/cart");
              return;
            }
            setCartItems(items);
          } else {
            navigate("/cart");
          }
        }
      } catch (error) {
        console.error("Failed to load items:", error);
        navigate("/cart");
      } finally {
        setIsLoading(false);
      }
    };
    loadItems();
  }, [location, navigate]);

  useEffect(() => {
    if (sameAsOrderer) {
      setShippingInfo((prev) => ({
        ...prev,
        name: ordererInfo.name,
        phone: ordererInfo.phone,
      }));
    }
  }, [sameAsOrderer, ordererInfo]);

  const handleOrdererChange = (field: keyof OrdererInfo, value: string) => {
    setOrdererInfo((prev) => ({ ...prev, [field]: value }));
  };
  const handleShippingChange = (field: keyof ShippingInfo, value: string) => {
    setShippingInfo((prev) => ({ ...prev, [field]: value }));
  };
  const handleSizeChange = (itemId: number, size: string) => {
    setCartItems((prev) =>
      prev.map((item) => (item.id === itemId ? { ...item, size } : item))
    );
  };
  const handleSearchAddress = () => {
    alert("우편번호 찾기 기능은 다음 주소 API 연동이 필요합니다.");
    setShippingInfo((prev) => ({
      ...prev,
      zipCode: "06234",
      address: "서울특별시 강남구 테헤란로 123",
    }));
  };

  const isFormValid = () => {
    return (
      ordererInfo.name.trim() !== "" &&
      ordererInfo.phone.trim() !== "" &&
      ordererInfo.email.trim() !== "" &&
      shippingInfo.name.trim() !== "" &&
      shippingInfo.phone.trim() !== "" &&
      shippingInfo.address.trim() !== "" &&
      cartItems.every((item) => item.size)
    );
  };
  const itemsWithoutSize = cartItems.filter((item) => !item.size);

  // [Helper] 이미지 URL 추출 함수 (강력해짐!)
  const getImageUrl = (item: CartItem) => {
    // 1. image_url 또는 image 속성에서 값 가져오기
    const rawUrl = item.image_url || item.image || "";
    
    if (!rawUrl) return "/placeholder.png";
    
    // 2. 이미 http로 시작하면 그대로 반환 (S3 풀 주소인 경우)
    if (rawUrl.startsWith("http")) return rawUrl;
    
    // 3. 상대 경로인 경우 S3 도메인 붙여서 반환
    return `https://modify-frontend-final-ai4.s3.ap-northeast-2.amazonaws.com${rawUrl.startsWith("/") ? "" : "/"}${rawUrl}`;
  };

  const handlePayment = async () => {
    if (!isFormValid()) {
      if (itemsWithoutSize.length > 0)
        alert("모든 상품의 사이즈를 선택해주세요.");
      else alert("필수 정보를 모두 입력해주세요.");
      return;
    }
    setIsProcessing(true);
    try {
      const authStorage = localStorage.getItem("auth-storage");
      const token = authStorage ? JSON.parse(authStorage).state.token : null;

      if (!token) {
        alert("로그인이 필요합니다. 다시 로그인해주세요.");
        navigate("/login");
        return;
      }

      const API_URL = import.meta.env.VITE_API_URL || "http://localhost";

      const orderData = {
        recipient_name: shippingInfo.name,
        recipient_phone: shippingInfo.phone,
        zip_code: shippingInfo.zipCode,
        address: shippingInfo.address,
        detail_address: shippingInfo.addressDetail,
        delivery_memo: shippingInfo.memo,
        payment_method: paymentMethod,
        order_items: cartItems.map((item) => ({
          product_id: item.id,
          product_name: item.name,
          product_price: item.price,
          // [수정] 여기서도 image_url이 없으면 image를 보내도록 처리
          product_image_url: item.image_url || item.image || "", 
          quantity: item.quantity,
        })),
      };

      const response = await axios.post(
        `${API_URL}/api/v1/orders/`,
        orderData,
        {
          headers: { Authorization: `Bearer ${token}` },
        }
      );

      setOrderId(response.data.order_number);
      if (!location.state?.directBuy) localStorage.removeItem("cart");
      setOrderComplete(true);
    } catch (error: any) {
      console.error("Order creation failed:", error);
      alert(
        error.response?.data?.detail ||
          "결제 처리 중 오류가 발생했습니다."
      );
    } finally {
      setIsProcessing(false);
    }
  };

  const totalPrice = cartItems.reduce(
    (sum, item) => sum + item.price * item.quantity,
    0
  );
  const shippingFee = totalPrice >= 50000 ? 0 : 3000;
  const pointDiscount = Math.min(usePoints, totalPrice);
  const finalPrice = totalPrice + shippingFee - pointDiscount;

  if (isLoading)
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
      </div>
    );

  if (orderComplete) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <div className="w-20 h-20 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-6">
            <CheckCircle className="w-10 h-10 text-green-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            주문이 완료되었습니다!
          </h1>
          <p className="text-gray-500 mb-6">주문번호: {orderId}</p>
          <div className="bg-gray-50 rounded-2xl p-6 mb-8 text-left">
            <h3 className="font-bold text-gray-900 mb-3 flex items-center gap-2">
              <Package className="w-5 h-5 text-purple-600" /> 배송 정보
            </h3>
            <p className="text-gray-600 text-sm">
              {shippingInfo.name} / {shippingInfo.phone}
              <br />[{shippingInfo.zipCode}] {shippingInfo.address}{" "}
              {shippingInfo.addressDetail}
            </p>
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="flex justify-between text-lg font-bold">
                <span>결제 금액</span>
                <span className="text-purple-600">
                  {finalPrice.toLocaleString()}원
                </span>
              </div>
            </div>
          </div>
          <div className="space-y-3">
            <button
              onClick={() => navigate("/")}
              className="w-full py-4 bg-purple-600 text-white font-bold rounded-xl hover:bg-purple-700 transition-colors"
            >
              쇼핑 계속하기
            </button>
            <button
              onClick={() => navigate("/orders")}
              className="w-full py-4 bg-gray-100 text-gray-700 font-bold rounded-xl hover:bg-gray-200 transition-colors"
            >
              주문 내역 보기
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8 py-8 pb-24">
      <div className="mb-8">
        <button
          onClick={() => navigate(-1)}
          className="inline-flex items-center text-gray-500 hover:text-gray-900 transition-colors text-sm font-medium mb-4"
        >
          <ArrowLeft className="w-4 h-4 mr-1" /> 뒤로 가기
        </button>
        <h1 className="text-3xl font-bold text-gray-900 flex items-center gap-3">
          <CreditCard className="w-8 h-8 text-purple-600" />
          결제하기
        </h1>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        <div className="lg:col-span-4 space-y-4">
          <div className="bg-white rounded-2xl border border-gray-200 p-5">
            <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <Package className="w-5 h-5 text-purple-600" /> 주문상품
            </h2>
            <div className="space-y-4">
              {cartItems.map((item) => (
                <div
                  key={item.id}
                  className="flex gap-4 pb-4 border-b border-gray-100 last:border-0 last:pb-0"
                >
                  <div className="w-20 h-24 bg-gray-100 rounded-lg overflow-hidden shrink-0">
                    {/* ✅ [수정완료] 강력해진 이미지 로더 적용 */}
                    <img
                      src={getImageUrl(item)}
                      alt={item.name}
                      className="w-full h-full object-cover"
                      onError={(e) =>
                        (e.currentTarget.src = "/placeholder.png")
                      }
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900 text-sm line-clamp-2 mb-1">
                      {item.name}
                    </p>
                    <div className="mb-2">
                      <select
                        value={item.size || ""}
                        onChange={(e) =>
                          handleSizeChange(item.id, e.target.value)
                        }
                        className={`w-full px-3 py-2 text-sm border rounded-lg bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none ${
                          !item.size
                            ? "border-red-300 bg-red-50"
                            : "border-gray-300"
                        }`}
                      >
                        <option value="">사이즈 선택</option>
                        {SIZE_OPTIONS.map((size) => (
                          <option key={size} value={size}>
                            {size}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-500">
                        {item.quantity}개
                      </span>
                      <span className="font-bold text-gray-900">
                        {(item.price * item.quantity).toLocaleString()}원
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
            {itemsWithoutSize.length > 0 && (
              <div className="mt-4 p-3 bg-red-50 rounded-lg text-red-600 text-sm flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                {itemsWithoutSize.length}개 상품의 사이즈를 선택해주세요
              </div>
            )}
            <div className="mt-4 pt-4 border-t border-gray-200">
              <div className="flex justify-between items-center mb-2">
                <span className="text-sm text-gray-600">적립금</span>
                <span className="text-sm text-gray-400">
                  사용가능: {availablePoints.toLocaleString()}원
                </span>
              </div>
              <div className="flex gap-2">
                <input
                  type="number"
                  value={usePoints}
                  onChange={(e) =>
                    setUsePoints(
                      Math.min(Number(e.target.value), availablePoints)
                    )
                  }
                  placeholder="0"
                  className="flex-1 px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
                />
                <button
                  onClick={() => setUsePoints(availablePoints)}
                  className="px-3 py-2 bg-gray-100 text-gray-600 text-sm rounded-lg hover:bg-gray-200 transition-colors"
                >
                  전액사용
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 p-5">
            <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <User className="w-5 h-5 text-purple-600" /> 주문자 정보
            </h2>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  주문자명 *
                </label>
                <input
                  type="text"
                  value={ordererInfo.name}
                  onChange={(e) => handleOrdererChange("name", e.target.value)}
                  placeholder="이름"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  연락처 *
                </label>
                <div className="flex gap-2">
                  <select className="px-3 py-3 border border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none">
                    <option>010</option>
                    <option>011</option>
                    <option>016</option>
                  </select>
                  <input
                    type="tel"
                    value={ordererInfo.phone}
                    onChange={(e) =>
                      handleOrdererChange("phone", e.target.value)
                    }
                    placeholder="0000-0000"
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  이메일 *
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={ordererInfo.email.split("@")[0] || ""}
                    onChange={(e) =>
                      handleOrdererChange(
                        "email",
                        e.target.value +
                          "@" +
                          (ordererInfo.email.split("@")[1] || "gmail.com")
                      )
                    }
                    placeholder="이메일"
                    className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all"
                  />
                  <span className="flex items-center text-gray-500">@</span>
                  <select
                    value={ordererInfo.email.split("@")[1] || "gmail.com"}
                    onChange={(e) =>
                      handleOrdererChange(
                        "email",
                        (ordererInfo.email.split("@")[0] || "") +
                          "@" +
                          e.target.value
                      )
                    }
                    className="px-3 py-3 border border-gray-300 rounded-xl bg-white focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
                  >
                    <option value="gmail.com">gmail.com</option>
                    <option value="naver.com">naver.com</option>
                    <option value="kakao.com">kakao.com</option>
                    <option value="daum.net">daum.net</option>
                  </select>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-bold text-gray-900 flex items-center gap-2">
                <Truck className="w-5 h-5 text-purple-600" /> 배송지 정보
              </h2>
              <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
                <input
                  type="checkbox"
                  checked={sameAsOrderer}
                  onChange={(e) => setSameAsOrderer(e.target.checked)}
                  className="w-4 h-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                />{" "}
                주문자 정보 자동 입력
              </label>
            </div>
            <div className="flex gap-2 mb-4">
              {[
                { id: "home", label: "자택", icon: Home },
                { id: "recent", label: "최근 배송지", icon: Clock },
                { id: "new", label: "신규 배송지", icon: Plus },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => handleShippingChange("addressType", id)}
                  className={`flex-1 flex items-center justify-center gap-1 py-2 text-sm rounded-lg border transition-all ${
                    shippingInfo.addressType === id
                      ? "border-purple-600 bg-purple-50 text-purple-700"
                      : "border-gray-200 hover:border-gray-300 text-gray-600"
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  {label}
                </button>
              ))}
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  수신자명 *
                </label>
                <input
                  type="text"
                  value={shippingInfo.name}
                  onChange={(e) => handleShippingChange("name", e.target.value)}
                  placeholder="이름"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  연락처 *
                </label>
                <input
                  type="tel"
                  value={shippingInfo.phone}
                  onChange={(e) =>
                    handleShippingChange("phone", e.target.value)
                  }
                  placeholder="010-0000-0000"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  배송지 주소 *
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={shippingInfo.zipCode}
                    onChange={(e) =>
                      handleShippingChange("zipCode", e.target.value)
                    }
                    placeholder="우편번호"
                    readOnly
                    className="w-32 px-4 py-3 border border-gray-300 rounded-xl bg-gray-50 outline-none"
                  />
                  <button
                    onClick={handleSearchAddress}
                    className="px-4 py-3 bg-gray-900 text-white font-medium rounded-xl hover:bg-black transition-colors flex items-center gap-2"
                  >
                    <Search className="w-4 h-4" /> 우편번호 찾기
                  </button>
                </div>
                <input
                  type="text"
                  value={shippingInfo.address}
                  onChange={(e) =>
                    handleShippingChange("address", e.target.value)
                  }
                  placeholder="기본 주소"
                  readOnly
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl bg-gray-50 mb-2 outline-none"
                />
                <input
                  type="text"
                  value={shippingInfo.addressDetail}
                  onChange={(e) =>
                    handleShippingChange("addressDetail", e.target.value)
                  }
                  placeholder="상세 주소 입력"
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  배송 메모
                </label>
                <select
                  value={shippingInfo.memo}
                  onChange={(e) => handleShippingChange("memo", e.target.value)}
                  className="w-full px-4 py-3 border border-gray-300 rounded-xl focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all bg-white"
                >
                  <option>문 앞에 놓아주세요</option>
                  <option>경비실에 맡겨주세요</option>
                  <option>배송 전 연락 부탁드립니다</option>
                  <option>직접 수령하겠습니다</option>
                  <option>택배함에 넣어주세요</option>
                </select>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3 space-y-6">
          <div className="bg-white rounded-2xl border border-gray-200 p-5">
            <h2 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
              <CreditCard className="w-5 h-5 text-purple-600" /> 결제 수단
            </h2>

            <div className="grid grid-cols-3 gap-3">
              {PAYMENT_METHODS.map((method) => (
                <button
                  key={method.id}
                  onClick={() => setPaymentMethod(method.id)}
                  className={`
                                            flex flex-col items-center justify-center p-3 rounded-xl border-2 transition-all duration-200 aspect-[4/3]
                                            ${
                                              paymentMethod === method.id
                                                ? `${method.border} ${
                                                    method.bg
                                                  } ring-1 ${method.color.replace(
                                                    "text",
                                                    "ring"
                                                  )}`
                                                : "border-gray-100 hover:border-gray-200 hover:shadow-sm bg-white"
                                            }
                                        `}
                >
                  <div className="mb-2">{method.icon}</div>
                  <span
                    className={`text-[11px] font-bold ${
                      paymentMethod === method.id
                        ? method.color
                        : "text-gray-500"
                    }`}
                  >
                    {method.label}
                  </span>
                </button>
              ))}
            </div>
          </div>

          <div className="bg-gray-50 rounded-2xl p-5 border border-gray-200 sticky top-24">
            <h2 className="text-lg font-bold text-gray-900 mb-4">결제 금액</h2>
            <div className="space-y-3 mb-6">
              <div className="flex justify-between text-gray-600 text-sm">
                <span>상품 금액</span>
                <span>{totalPrice.toLocaleString()}원</span>
              </div>
              <div className="flex justify-between text-gray-600 text-sm">
                <span>배송비</span>
                <span className={shippingFee === 0 ? "text-green-600" : ""}>
                  {shippingFee === 0
                    ? "무료"
                    : `+${shippingFee.toLocaleString()}원`}
                </span>
              </div>
              {pointDiscount > 0 && (
                <div className="flex justify-between text-gray-600 text-sm">
                  <span>적립금 할인</span>
                  <span className="text-red-500">
                    -{pointDiscount.toLocaleString()}원
                  </span>
                </div>
              )}
              <div className="border-t border-gray-200 pt-3">
                <div className="flex justify-between text-xl font-bold text-gray-900">
                  <span>총 결제금액</span>
                  <span className="text-purple-600">
                    {finalPrice.toLocaleString()}원
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={handlePayment}
              disabled={isProcessing || !isFormValid()}
              className="w-full py-4 bg-purple-600 text-white font-bold rounded-xl flex items-center justify-center gap-2 hover:bg-purple-700 transition-colors shadow-lg active:scale-95 disabled:bg-gray-300 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <>
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  결제 처리 중...
                </>
              ) : (
                <>
                  <CreditCard className="w-5 h-5" />{" "}
                  {finalPrice.toLocaleString()}원 결제하기
                </>
              )}
            </button>
            <div className="mt-4 flex items-center justify-center gap-2 text-xs text-gray-400">
              <ShieldCheck className="w-4 h-4" />
              <span>안심결제</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}