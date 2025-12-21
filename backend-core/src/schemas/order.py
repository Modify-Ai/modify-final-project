from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class OrderItemCreate(BaseModel):
    product_id: int
    product_name: str
    product_price: int
    product_image_url: Optional[str] = None
    quantity: int = 1


class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    product_name: str
    product_price: int
    product_image_url: Optional[str] = None
    quantity: int
    created_at: datetime

    class Config:
        from_attributes = True


class OrderCreate(BaseModel):
    recipient_name: str = Field(..., min_length=1, max_length=100)
    recipient_phone: str = Field(..., min_length=1, max_length=20)
    zip_code: str = Field(..., min_length=1, max_length=10)
    address: str = Field(..., min_length=1, max_length=200)
    detail_address: Optional[str] = Field(None, max_length=200)
    delivery_memo: Optional[str] = None
    payment_method: Optional[str] = None
    order_items: List[OrderItemCreate]


class OrderResponse(BaseModel):
    id: int
    user_id: int
    order_number: str
    total_amount: int
    status: str
    payment_status: str
    recipient_name: str
    recipient_phone: str
    zip_code: str
    address: str
    detail_address: Optional[str] = None
    delivery_memo: Optional[str] = None
    payment_method: Optional[str] = None
    order_items: List[OrderItemResponse]
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    id: int
    order_number: str
    total_amount: int
    status: str
    payment_status: str
    created_at: datetime
    order_items: List[OrderItemResponse]

    class Config:
        from_attributes = True
