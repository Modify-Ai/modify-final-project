from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db.session import Base


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    order_number = Column(String(50), unique=True, nullable=False, index=True)
    total_amount = Column(Integer, nullable=False)
    status = Column(String(50), default="pending", nullable=False)
    payment_status = Column(String(50), default="pending", nullable=False)

    # 배송 정보
    recipient_name = Column(String(100), nullable=False)
    recipient_phone = Column(String(20), nullable=False)
    zip_code = Column(String(10), nullable=False)
    address = Column(String(200), nullable=False)
    detail_address = Column(String(200), nullable=True)
    delivery_memo = Column(Text, nullable=True)

    # 결제 정보
    payment_method = Column(String(50), nullable=True)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="orders")
    order_items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)

    # 주문 시점의 상품 정보 저장
    product_name = Column(String(200), nullable=False)
    product_price = Column(Integer, nullable=False)
    product_image_url = Column(String(500), nullable=True)
    quantity = Column(Integer, default=1, nullable=False)

    # 타임스탬프
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product")
