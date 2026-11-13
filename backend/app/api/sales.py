from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.crm_support import check_page, clean_query, run_write
from app.database import get_db
from app.sales_catalog import DEAL_STAGES, ORDER_STATUSES, PRODUCT_CATEGORIES
from app.schemas.sales import (
    DealClose,
    DealDetail,
    DealList,
    DealRead,
    DealSummary,
    DealWrite,
    OrderList,
    OrderRead,
    OrderStatusChange,
    OrderSummary,
    OrderWrite,
    PipelineBoard,
    ProductList,
    ProductRead,
    ProductWrite,
    StageMove,
)
from app.services.crm import CrmServiceError
from app.services.sales import (
    archive_deal,
    change_order_status,
    close_deal,
    deactivate_product,
    deal_summary,
    insert_deal,
    insert_order,
    insert_product,
    move_deal,
    order_summary,
    pipeline,
    query_deals,
    query_orders,
    query_products,
    read_deal_detail,
    read_deals,
    read_order,
    require_deal,
    require_order,
    require_product,
    restore_deal,
    update_deal,
    update_order,
    update_product,
    _product_read,
)

deals_router = APIRouter(prefix="/deals", tags=["verkaufschancen"])
products_router = APIRouter(prefix="/products", tags=["produkte"])
orders_router = APIRouter(prefix="/orders", tags=["bestellungen"])


def _parse_date(value: str | None, label: str) -> date | None:
    cleaned = clean_query(value, 10)
    if cleaned is None:
        return None
    try:
        return date.fromisoformat(cleaned)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"{label} ist ungültig.") from None


@deals_router.get("/summary", response_model=DealSummary)
def read_deal_summary(partner_id: UUID | None = None, db: Session = Depends(get_db)) -> DealSummary:
    return deal_summary(db, partner_id)


@deals_router.get("/pipeline", response_model=PipelineBoard)
def read_pipeline(
    q: str | None = None,
    account_owner: str | None = None,
    partner_id: UUID | None = None,
    contact_id: UUID | None = None,
    close_from: str | None = None,
    close_to: str | None = None,
    db: Session = Depends(get_db),
) -> PipelineBoard:
    return pipeline(
        db,
        q=clean_query(q),
        account_owner=clean_query(account_owner, 120),
        partner_id=partner_id,
        contact_id=contact_id,
        close_from=_parse_date(close_from, "Abschlussdatum von"),
        close_to=_parse_date(close_to, "Abschlussdatum bis"),
    )


@deals_router.get("", response_model=DealList)
def list_deals(
    q: str | None = None,
    stage: str | None = None,
    account_owner: str | None = None,
    partner_id: UUID | None = None,
    contact_id: UUID | None = None,
    close_from: str | None = None,
    close_to: str | None = None,
    include_closed: bool = False,
    include_archived: bool = False,
    overdue_only: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> DealList:
    check_page(page, page_size)
    stage = clean_query(stage, 30)
    if stage is not None and stage not in DEAL_STAGES:
        raise HTTPException(status_code=422, detail="Die Verkaufsphase ist ungültig.")
    rows, total = query_deals(
        db,
        q=clean_query(q),
        stage=stage,
        account_owner=clean_query(account_owner, 120),
        partner_id=partner_id,
        contact_id=contact_id,
        close_from=_parse_date(close_from, "Abschlussdatum von"),
        close_to=_parse_date(close_to, "Abschlussdatum bis"),
        include_closed=include_closed,
        include_archived=include_archived,
        overdue_only=overdue_only,
        page=page,
        page_size=page_size,
    )
    return DealList(items=read_deals(db, rows), total=total, page=page, page_size=page_size)


@deals_router.post("", response_model=DealRead, status_code=201)
def create_deal(payload: DealWrite, db: Session = Depends(get_db)) -> DealRead:
    deal = run_write(db, lambda: insert_deal(db, payload))
    return read_deals(db, [deal])[0]


@deals_router.get("/{deal_id}", response_model=DealDetail)
def read_one_deal(deal_id: UUID, db: Session = Depends(get_db)) -> DealDetail:
    try:
        deal = require_deal(db, deal_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return read_deal_detail(db, deal)


@deals_router.put("/{deal_id}", response_model=DealDetail)
def edit_deal(deal_id: UUID, payload: DealWrite, db: Session = Depends(get_db)) -> DealDetail:
    deal = run_write(db, lambda: update_deal(db, deal_id, payload))
    return read_deal_detail(db, deal)


@deals_router.post("/{deal_id}/stage", response_model=DealDetail)
def move(deal_id: UUID, payload: StageMove, db: Session = Depends(get_db)) -> DealDetail:
    deal = run_write(db, lambda: move_deal(db, deal_id, payload.stage))
    return read_deal_detail(db, deal)


@deals_router.post("/{deal_id}/win", response_model=DealDetail)
def win(deal_id: UUID, payload: DealClose, db: Session = Depends(get_db)) -> DealDetail:
    deal = run_write(db, lambda: close_deal(db, deal_id, payload, won=True))
    return read_deal_detail(db, deal)


@deals_router.post("/{deal_id}/lose", response_model=DealDetail)
def lose(deal_id: UUID, payload: DealClose, db: Session = Depends(get_db)) -> DealDetail:
    deal = run_write(db, lambda: close_deal(db, deal_id, payload, won=False))
    return read_deal_detail(db, deal)


@deals_router.post("/{deal_id}/archive", response_model=DealDetail)
def archive(deal_id: UUID, db: Session = Depends(get_db)) -> DealDetail:
    deal = run_write(db, lambda: archive_deal(db, deal_id))
    return read_deal_detail(db, deal)


@deals_router.post("/{deal_id}/restore", response_model=DealDetail)
def restore(deal_id: UUID, db: Session = Depends(get_db)) -> DealDetail:
    deal = run_write(db, lambda: restore_deal(db, deal_id))
    return read_deal_detail(db, deal)


@products_router.get("", response_model=ProductList)
def list_products(
    q: str | None = None,
    category: str | None = None,
    include_inactive: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> ProductList:
    check_page(page, page_size)
    category = clean_query(category, 30)
    if category is not None and category not in PRODUCT_CATEGORIES:
        raise HTTPException(status_code=422, detail="Die Produktkategorie ist ungültig.")
    rows, total = query_products(
        db,
        q=clean_query(q),
        category=category,
        include_inactive=include_inactive,
        page=page,
        page_size=page_size,
    )
    return ProductList(items=[_product_read(row) for row in rows], total=total, page=page, page_size=page_size)


@products_router.post("", response_model=ProductRead, status_code=201)
def create_product(payload: ProductWrite, db: Session = Depends(get_db)) -> ProductRead:
    product = run_write(db, lambda: insert_product(db, payload))
    return _product_read(product)


@products_router.get("/{product_id}", response_model=ProductRead)
def read_one_product(product_id: UUID, db: Session = Depends(get_db)) -> ProductRead:
    try:
        product = require_product(db, product_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return _product_read(product)


@products_router.put("/{product_id}", response_model=ProductRead)
def edit_product(product_id: UUID, payload: ProductWrite, db: Session = Depends(get_db)) -> ProductRead:
    product = run_write(db, lambda: update_product(db, product_id, payload))
    return _product_read(product)


@products_router.post("/{product_id}/deactivate", response_model=ProductRead)
def deactivate(product_id: UUID, db: Session = Depends(get_db)) -> ProductRead:
    product = run_write(db, lambda: deactivate_product(db, product_id))
    return _product_read(product)


@orders_router.get("/summary", response_model=OrderSummary)
def read_order_summary(partner_id: UUID | None = None, db: Session = Depends(get_db)) -> OrderSummary:
    return order_summary(db, partner_id)


@orders_router.get("", response_model=OrderList)
def list_orders(
    q: str | None = None,
    status: str | None = None,
    partner_id: UUID | None = None,
    contact_id: UUID | None = None,
    deal_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> OrderList:
    check_page(page, page_size)
    status = clean_query(status, 30)
    if status is not None and status not in ORDER_STATUSES:
        raise HTTPException(status_code=422, detail="Der Bestellstatus ist ungültig.")
    items, total = query_orders(
        db,
        q=clean_query(q),
        status=status,
        partner_id=partner_id,
        contact_id=contact_id,
        deal_id=deal_id,
        page=page,
        page_size=page_size,
    )
    return OrderList(items=items, total=total, page=page, page_size=page_size)


@orders_router.post("", response_model=OrderRead, status_code=201)
def create_order(payload: OrderWrite, db: Session = Depends(get_db)) -> OrderRead:
    order = run_write(db, lambda: insert_order(db, payload))
    return read_order(db, order)


@orders_router.get("/{order_id}", response_model=OrderRead)
def read_one_order(order_id: UUID, db: Session = Depends(get_db)) -> OrderRead:
    try:
        order = require_order(db, order_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return read_order(db, order)


@orders_router.put("/{order_id}", response_model=OrderRead)
def edit_order(order_id: UUID, payload: OrderWrite, db: Session = Depends(get_db)) -> OrderRead:
    order = run_write(db, lambda: update_order(db, order_id, payload))
    return read_order(db, order)


@orders_router.post("/{order_id}/status", response_model=OrderRead)
def set_status(order_id: UUID, payload: OrderStatusChange, db: Session = Depends(get_db)) -> OrderRead:
    order = run_write(db, lambda: change_order_status(db, order_id, payload.status))
    return read_order(db, order)
