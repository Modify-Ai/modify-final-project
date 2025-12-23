import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";

interface OrderItem {
  id: number;
  product_id: number;
  product_name: string;
  product_price: number;
  product_image_url: string | null;
  quantity: number;
  created_at: string;
}

interface Order {
  id: number;
  order_number: string;
  total_amount: number;
  status: string;
  payment_status: string;
  created_at: string;
  order_items: OrderItem[];
}

const API_URL = import.meta.env.VITE_API_URL || "http://localhost";

const fetchOrders = async (): Promise<Order[]> => {
  // zustand persist에서 토큰 가져오기
  const authStorage = localStorage.getItem("auth-storage");
  const token = authStorage ? JSON.parse(authStorage).state.token : null;

  const response = await axios.get(`${API_URL}/api/v1/orders/`, {
    headers: { Authorization: `Bearer ${token}` },
  });

  return response.data;
};

const cancelOrder = async (orderId: number): Promise<Order> => {
  // zustand persist에서 토큰 가져오기
  const authStorage = localStorage.getItem("auth-storage");
  const token = authStorage ? JSON.parse(authStorage).state.token : null;

  const response = await axios.patch(
    `${API_URL}/api/v1/orders/${orderId}/cancel`,
    {},
    { headers: { Authorization: `Bearer ${token}` } }
  );

  return response.data;
};

const getStatusBadge = (status: string) => {
  const statusMap: Record<string, { label: string; className: string }> = {
    pending: { label: "결제 대기", className: "bg-yellow-100 text-yellow-800" },
    confirmed: { label: "주문 확인", className: "bg-blue-100 text-blue-800" },
    shipping: { label: "배송 중", className: "bg-purple-100 text-purple-800" },
    delivered: { label: "배송 완료", className: "bg-green-100 text-green-800" },
    cancelled: { label: "취소됨", className: "bg-red-100 text-red-800" },
  };

  const statusInfo = statusMap[status] || { label: status, className: "bg-gray-200 text-gray-800" };
  return (
    <span className={`px-3 py-1 rounded-full text-sm font-medium ${statusInfo.className}`}>
      {statusInfo.label}
    </span>
  );
};

export default function OrderHistory() {
  const queryClient = useQueryClient();

  const { data: orders, isLoading } = useQuery({
    queryKey: ["orders"],
    queryFn: () => fetchOrders(),
  });

  const cancelMutation = useMutation({
    mutationFn: cancelOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
      alert("주문이 취소되었습니다.");
    },
    onError: (error: any) => {
      alert(error.response?.data?.detail || "주문 취소에 실패했습니다.");
    },
  });

  const handleCancelOrder = (orderId: number) => {
    if (window.confirm("정말 주문을 취소하시겠습니까?")) {
      cancelMutation.mutate(orderId);
    }
  };

  return (
    <div className="container mx-auto py-8 px-4 max-w-6xl">
      <h1 className="text-3xl font-bold mb-8">주문 내역</h1>

      <div>
          {isLoading ? (
            <div className="text-center py-12">로딩 중...</div>
          ) : orders && orders.length > 0 ? (
            <div className="space-y-4">
              {orders.map((order) => (
                <div key={order.id} className="bg-white border rounded-lg shadow-sm overflow-hidden">
                  {/* Card Header */}
                  <div className="p-6 border-b bg-gray-50">
                    <div className="flex justify-between items-center">
                      <div>
                        <h3 className="text-lg font-semibold">
                          주문번호: {order.order_number}
                        </h3>
                        <p className="text-sm text-gray-500 mt-1">
                          {new Date(order.created_at).toLocaleDateString("ko-KR", {
                            year: "numeric",
                            month: "long",
                            day: "numeric",
                            hour: "2-digit",
                            minute: "2-digit",
                          })}
                        </p>
                      </div>
                      <div className="flex items-center gap-2">
                        {getStatusBadge(order.status)}
                        {order.status === "pending" && (
                          <button
                            onClick={() => handleCancelOrder(order.id)}
                            className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
                          >
                            취소
                          </button>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Card Content */}
                  <div className="p-6">
                    <div className="space-y-4">
                      {order.order_items.map((item, idx) => (
                        <div key={item.id}>
                          {idx > 0 && <div className="border-t my-4" />}
                          <div className="flex gap-4">
                            {item.product_image_url && (
                              <img
                                src={`${API_URL}${item.product_image_url}`}
                                alt={item.product_name}
                                className="w-20 h-20 object-cover rounded"
                              />
                            )}
                            <div className="flex-1">
                              <h4 className="font-medium">{item.product_name}</h4>
                              <p className="text-sm text-gray-500 mt-1">
                                수량: {item.quantity}개
                              </p>
                              <p className="text-sm font-semibold mt-1">
                                {item.product_price.toLocaleString()}원
                              </p>
                            </div>
                          </div>
                        </div>
                      ))}
                      <div className="border-t my-4 pt-4">
                        <div className="flex justify-between items-center">
                          <span className="font-semibold">총 결제금액</span>
                          <span className="text-xl font-bold text-blue-600">
                            {order.total_amount.toLocaleString()}원
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-gray-500">
              주문 내역이 없습니다.
            </div>
          )}
      </div>
    </div>
  );
}
