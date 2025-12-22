from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import uuid

from src.api.deps import get_db, get_current_user
from src.models.user import User
from src.models.order import Order, OrderItem
from src.schemas.order import OrderCreate, OrderResponse, OrderListResponse

router = APIRouter()

def check_superuser(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="관리자 권한이 필요합니다."
        )
    return current_user


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


# =========================================================
# 관리자용 주문 관리 API
# =========================================================

@router.get("/admin", response_model=dict)
async def get_all_orders_admin(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status_filter: Optional[str] = Query(None, description="주문 상태 필터"),
    start_date: Optional[str] = Query(None, description="시작 날짜 (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="종료 날짜 (YYYY-MM-DD)"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_superuser),
):
    """관리자용 전체 주문 목록 조회"""
    offset = (page - 1) * limit

    # 전체 주문 수 조회
    count_query = select(func.count(Order.id))
    if status_filter:
        count_query = count_query.where(Order.status == status_filter)
    if start_date:
        start_datetime = datetime.fromisoformat(start_date)
        count_query = count_query.where(Order.created_at >= start_datetime)
    if end_date:
        # 종료 날짜는 해당 날짜의 23:59:59까지 포함
        end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
        count_query = count_query.where(Order.created_at < end_datetime)

    total_result = await db.execute(count_query)
    total = total_result.scalar_one()

    # 주문 목록 조회 (user도 함께 로드)
    query = select(Order).options(
        selectinload(Order.order_items),
        selectinload(Order.user)
    )
    if status_filter:
        query = query.where(Order.status == status_filter)
    if start_date:
        start_datetime = datetime.fromisoformat(start_date)
        query = query.where(Order.created_at >= start_datetime)
    if end_date:
        end_datetime = datetime.fromisoformat(end_date) + timedelta(days=1)
        query = query.where(Order.created_at < end_datetime)

    query = query.order_by(desc(Order.created_at)).offset(offset).limit(limit)

    result = await db.execute(query)
    orders = result.scalars().all()

    # OrderListResponse로 변환하면서 user_name과 first_item_name 추가
    order_list = []
    for order in orders:
        order_dict = OrderListResponse.model_validate(order).model_dump()
        order_dict["user_name"] = order.user.full_name if order.user else None
        order_dict["user_email"] = order.user.email if order.user else None
        order_dict["first_item_name"] = order.order_items[0].product_name if order.order_items else None
        order_dict["item_count"] = len(order.order_items)
        order_list.append(order_dict)

    # 통계 계산 (취소된 주문 제외)
    from sqlalchemy import case as sql_case
    stats_query = select(
        func.sum(sql_case((Order.status != 'cancelled', Order.total_amount), else_=0)).label('total_revenue'),
        func.count(Order.id).label('total_orders'),
        func.avg(sql_case((Order.status != 'cancelled', Order.total_amount), else_=None)).label('avg_order'),
        func.sum(sql_case((Order.status == 'pending', 1), else_=0)).label('pending')
    )
    stats_result = await db.execute(stats_query)
    stats_row = stats_result.one()

    return {
        "total": total,
        "page": page,
        "limit": limit,
        "orders": order_list,
        "stats": {
            "total_revenue": int(stats_row.total_revenue) if stats_row.total_revenue else 0,
            "total_orders": stats_row.total_orders or 0,
            "avg_order": int(stats_row.avg_order) if stats_row.avg_order else 0,
            "pending": stats_row.pending or 0
        }
    }


@router.patch("/admin/{order_id}/status", response_model=OrderResponse)
async def update_order_status_admin(
    order_id: int,
    status_data: dict,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_superuser),
):
    """관리자용 주문 상태 업데이트"""
    new_status = status_data.get("status")
    if not new_status:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status 필드가 필요합니다."
        )

    result = await db.execute(
        select(Order).options(selectinload(Order.order_items)).where(Order.id == order_id)
    )
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="주문을 찾을 수 없습니다."
        )

    order.status = new_status
    await db.commit()
    await db.refresh(order)

    return order


# =========================================================
# 일반 사용자용 주문 조회 및 관리
# =========================================================

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
