from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload
from datetime import datetime
import uuid

from src.api.deps import get_db, get_current_user
from src.models.user import User
from src.models.order import Order, OrderItem
from src.schemas.order import OrderCreate, OrderResponse, OrderListResponse

router = APIRouter()


def generate_order_number() -> str:
    """주문 번호 생성 (예: ORD-20231215-A1B2C3D4)"""
    timestamp = datetime.now().strftime("%Y%m%d")
    unique_id = str(uuid.uuid4())[:8].upper()
    return f"ORD-{timestamp}-{unique_id}"


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
async def create_order(
    order_data: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """주문 생성"""

    # 총 금액 계산
    total_amount = sum(item.product_price * item.quantity for item in order_data.order_items)

    # 주문 번호 생성
    order_number = generate_order_number()

    # Order 객체 생성
    db_order = Order(
        user_id=current_user.id,
        order_number=order_number,
        total_amount=total_amount,
        status="pending",
        payment_status="pending",
        recipient_name=order_data.recipient_name,
        recipient_phone=order_data.recipient_phone,
        zip_code=order_data.zip_code,
        address=order_data.address,
        detail_address=order_data.detail_address,
        delivery_memo=order_data.delivery_memo,
        payment_method=order_data.payment_method,
    )

    db.add(db_order)
    await db.flush()  # ID 생성을 위해 flush

    # OrderItem 객체들 생성
    for item in order_data.order_items:
        db_order_item = OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            product_name=item.product_name,
            product_price=item.product_price,
            product_image_url=item.product_image_url,
            quantity=item.quantity,
        )
        db.add(db_order_item)

    await db.commit()
    await db.refresh(db_order, ["order_items"])

    return db_order


@router.get("/", response_model=List[OrderListResponse])
async def get_my_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    status_filter: Optional[str] = Query(None, description="주문 상태 필터"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
):
    """내 주문 목록 조회"""

    query = select(Order).options(selectinload(Order.order_items)).where(Order.user_id == current_user.id)

    # 상태 필터링
    if status_filter:
        query = query.where(Order.status == status_filter)

    # 최신순 정렬
    query = query.order_by(desc(Order.created_at)).offset(skip).limit(limit)

    result = await db.execute(query)
    orders = result.scalars().all()

    return orders


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order_detail(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """주문 상세 조회"""

    result = await db.execute(
        select(Order).options(selectinload(Order.order_items)).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="주문을 찾을 수 없습니다."
        )

    return order


@router.patch("/{order_id}/cancel", response_model=OrderResponse)
async def cancel_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """주문 취소"""

    result = await db.execute(
        select(Order).options(selectinload(Order.order_items)).where(Order.id == order_id, Order.user_id == current_user.id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="주문을 찾을 수 없습니다."
        )

    # 취소 가능한 상태인지 확인
    if order.status in ["cancelled", "delivered"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="취소할 수 없는 주문입니다."
        )

    order.status = "cancelled"
    order.payment_status = "cancelled"

    await db.commit()

    # 업데이트된 주문 정보 다시 조회
    result = await db.execute(
        select(Order).options(selectinload(Order.order_items)).where(Order.id == order_id)
    )
    updated_order = result.scalar_one()

    return updated_order
