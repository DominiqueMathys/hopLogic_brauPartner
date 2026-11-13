from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.contact import CompanyContact, Contact
from app.models.partner import Partner
from app.models.sales import Deal, DealStageHistory, Order, OrderItem, Product
from app.sales_catalog import (
    CLOSED_DEAL_STAGES,
    COUNTED_ORDER_STATUSES,
    OPEN_DEAL_STAGES,
    ORDER_TRANSITIONS,
    STAGE_PROBABILITY,
)
from app.schemas.sales import (
    DealClose,
    DealDetail,
    DealRead,
    DealSummary,
    DealWrite,
    OrderItemRead,
    OrderListItem,
    OrderRead,
    OrderSummary,
    OrderWrite,
    PipelineBoard,
    PipelineCard,
    PipelineColumn,
    ProductRead,
    ProductWrite,
    StageHistoryRead,
)
from app.services.crm import CrmServiceError, require_contact
from app.services.money import line_amounts, money
from app.services.partners import contains_pattern, require_partner

DEAL_FIELDS = (
    "title",
    "partner_id",
    "contact_id",
    "account_owner",
    "estimated_value",
    "expected_close_on",
    "priority",
    "description",
)
PRODUCT_FIELDS = (
    "sku",
    "name",
    "category",
    "description",
    "container_type",
    "container_size",
    "sales_unit",
    "list_price",
    "vat_rate",
    "is_active",
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def require_deal(db: Session, deal_id: UUID) -> Deal:
    deal = db.get(Deal, deal_id)
    if deal is None:
        raise CrmServiceError("Die Verkaufschance wurde nicht gefunden.", 404)
    return deal


def require_product(db: Session, product_id: UUID) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise CrmServiceError("Das Produkt wurde nicht gefunden.", 404)
    return product


def require_order(db: Session, order_id: UUID) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise CrmServiceError("Die Bestellung wurde nicht gefunden.", 404)
    return order


def _ensure_link(db: Session, partner_id: UUID, contact_id: UUID | None) -> None:
    require_partner(db, partner_id)
    if contact_id is None:
        return
    require_contact(db, contact_id)
    link = db.scalar(
        select(CompanyContact.id).where(
            CompanyContact.partner_id == partner_id,
            CompanyContact.contact_id == contact_id,
        )
    )
    if link is None:
        raise CrmServiceError("Die Kontaktperson ist diesem Unternehmen nicht zugeordnet.", 409)


def _ensure_deal_for_partner(db: Session, deal_id: UUID | None, partner_id: UUID) -> None:
    if deal_id is None:
        return
    deal = require_deal(db, deal_id)
    if deal.partner_id != partner_id:
        raise CrmServiceError("Die Verkaufschance gehört zu einem anderen Unternehmen.", 409)


def _record_stage(db: Session, deal: Deal, from_stage: str | None, to_stage: str, changed_by: str | None) -> None:
    row = DealStageHistory(
        deal_id=deal.id,
        from_stage=from_stage,
        to_stage=to_stage,
        changed_by=changed_by,
    )
    db.add(row)
    db.flush()
    if from_stage is not None:
        from app.services.automation import company_name, publish_event

        publish_event(
            db,
            "deal_stage_changed",
            dedupe_key=f"deal-stage:{row.id}",
            context={
                "owner": deal.account_owner,
                "partner_id": deal.partner_id,
                "contact_id": deal.contact_id,
                "company_name": company_name(db, deal.partner_id),
                "href": f"/verkaufschancen/{deal.id}",
                "deal_id": deal.id,
            },
        )


def _names(db: Session, partner_ids: list[UUID], contact_ids: list[UUID]) -> tuple[dict[UUID, str], dict[UUID, str]]:
    partners = {
        row.id: row.company_name
        for row in db.scalars(select(Partner).where(Partner.id.in_(partner_ids))).all()
    } if partner_ids else {}
    contacts = {
        row.id: f"{row.first_name} {row.last_name}"
        for row in db.scalars(select(Contact).where(Contact.id.in_(contact_ids))).all()
    } if contact_ids else {}
    return partners, contacts


def _deal_read(deal: Deal, company_name: str, contact_name: str | None) -> DealRead:
    overdue = (
        deal.archived_at is None
        and deal.stage in OPEN_DEAL_STAGES
        and deal.expected_close_on is not None
        and deal.expected_close_on < _today()
    )
    return DealRead(
        id=deal.id,
        title=deal.title,
        partner_id=deal.partner_id,
        contact_id=deal.contact_id,
        company_name=company_name,
        contact_name=contact_name,
        account_owner=deal.account_owner,
        estimated_value=deal.estimated_value,
        expected_close_on=deal.expected_close_on,
        stage=deal.stage,
        probability=deal.probability,
        priority=deal.priority,
        description=deal.description,
        closed_on=deal.closed_on,
        loss_reason=deal.loss_reason,
        is_overdue=overdue,
        is_demo=deal.is_demo,
        archived_at=deal.archived_at,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
    )


def read_deals(db: Session, rows: list[Deal]) -> list[DealRead]:
    partners, contacts = _names(
        db,
        [row.partner_id for row in rows],
        [row.contact_id for row in rows if row.contact_id is not None],
    )
    return [
        _deal_read(row, partners.get(row.partner_id, ""), contacts.get(row.contact_id) if row.contact_id else None)
        for row in rows
    ]


def read_deal_detail(db: Session, deal: Deal) -> DealDetail:
    base = read_deals(db, [deal])[0]
    history = db.scalars(
        select(DealStageHistory).where(DealStageHistory.deal_id == deal.id).order_by(DealStageHistory.changed_at.asc())
    ).all()
    return DealDetail(
        **base.model_dump(),
        history=[
            StageHistoryRead(
                id=row.id,
                from_stage=row.from_stage,
                to_stage=row.to_stage,
                changed_by=row.changed_by,
                changed_at=row.changed_at,
            )
            for row in history
        ],
    )


def _apply_stage(deal: Deal, stage: str, probability: Decimal | None) -> None:
    deal.stage = stage
    deal.probability = probability if probability is not None else STAGE_PROBABILITY[stage]
    if stage in OPEN_DEAL_STAGES:
        deal.closed_on = None
        deal.loss_reason = None


def insert_deal(db: Session, data: DealWrite, *, is_demo: bool = False, demo_key: str | None = None) -> Deal:
    if data.stage in CLOSED_DEAL_STAGES:
        raise CrmServiceError("Gewonnene oder verlorene Deals werden über die Abschlussaktion erfasst.", 422)
    _ensure_link(db, data.partner_id, data.contact_id)
    deal = Deal(is_demo=is_demo, demo_key=demo_key, stage=data.stage, probability=Decimal("0"))
    for field in DEAL_FIELDS:
        setattr(deal, field, getattr(data, field))
    _apply_stage(deal, data.stage, data.probability)
    deal.updated_at = _now()
    db.add(deal)
    db.flush()
    _record_stage(db, deal, None, deal.stage, data.account_owner)
    db.flush()
    from app.services.automation import company_name, publish_event

    publish_event(
        db,
        "deal_created",
        dedupe_key=f"deal:{deal.id}",
        context={
            "owner": deal.account_owner,
            "partner_id": deal.partner_id,
            "contact_id": deal.contact_id,
            "company_name": company_name(db, deal.partner_id),
            "href": f"/verkaufschancen/{deal.id}",
            "deal_id": deal.id,
        },
    )
    return deal


def update_deal(db: Session, deal_id: UUID, data: DealWrite) -> Deal:
    deal = require_deal(db, deal_id)
    if deal.archived_at is not None:
        raise CrmServiceError("Archivierte Verkaufschancen können erst nach der Wiederherstellung bearbeitet werden.", 409)
    if data.stage in CLOSED_DEAL_STAGES and data.stage != deal.stage:
        raise CrmServiceError("Abschluss bitte über Gewinnen oder Verlieren erfassen.", 422)
    if deal.stage in CLOSED_DEAL_STAGES and data.stage != deal.stage:
        raise CrmServiceError("Ein abgeschlossener Deal kann nicht in eine offene Phase zurückgesetzt werden.", 409)
    _ensure_link(db, data.partner_id, data.contact_id)
    previous = deal.stage
    for field in DEAL_FIELDS:
        setattr(deal, field, getattr(data, field))
    if data.stage != previous:
        _apply_stage(deal, data.stage, data.probability)
        _record_stage(db, deal, previous, data.stage, data.account_owner)
    elif data.probability is not None and deal.stage not in CLOSED_DEAL_STAGES:
        deal.probability = data.probability
    deal.updated_at = _now()
    db.flush()
    return deal


def move_deal(db: Session, deal_id: UUID, stage: str) -> Deal:
    deal = require_deal(db, deal_id)
    if deal.archived_at is not None:
        raise CrmServiceError("Archivierte Verkaufschancen können nicht verschoben werden.", 409)
    if deal.stage in CLOSED_DEAL_STAGES:
        raise CrmServiceError("Abgeschlossene Deals bleiben in der Abschlussphase.", 409)
    if stage not in OPEN_DEAL_STAGES:
        raise CrmServiceError("In der Pipeline sind nur offene Verkaufsphasen erlaubt.", 422)
    if stage == deal.stage:
        return deal
    previous = deal.stage
    _apply_stage(deal, stage, None)
    deal.updated_at = _now()
    _record_stage(db, deal, previous, stage, deal.account_owner)
    db.flush()
    return deal


def close_deal(db: Session, deal_id: UUID, data: DealClose, *, won: bool) -> Deal:
    deal = require_deal(db, deal_id)
    if deal.archived_at is not None:
        raise CrmServiceError("Archivierte Verkaufschancen können nicht abgeschlossen werden.", 409)
    if deal.stage in CLOSED_DEAL_STAGES:
        raise CrmServiceError("Die Verkaufschance ist bereits abgeschlossen.", 409)
    if not won and not data.loss_reason:
        raise CrmServiceError("Ein verlorener Deal braucht einen Verlustgrund.", 422)
    previous = deal.stage
    stage = "gewonnen" if won else "verloren"
    _apply_stage(deal, stage, None)
    deal.closed_on = data.closed_on or _today()
    deal.loss_reason = None if won else data.loss_reason
    deal.updated_at = _now()
    _record_stage(db, deal, previous, stage, deal.account_owner)
    db.flush()
    return deal


def archive_deal(db: Session, deal_id: UUID) -> Deal:
    deal = require_deal(db, deal_id)
    if deal.archived_at is not None:
        raise CrmServiceError("Die Verkaufschance ist bereits archiviert.", 409)
    deal.archived_at = _now()
    deal.updated_at = deal.archived_at
    db.flush()
    return deal


def restore_deal(db: Session, deal_id: UUID) -> Deal:
    deal = require_deal(db, deal_id)
    if deal.archived_at is None:
        raise CrmServiceError("Die Verkaufschance ist nicht archiviert.", 409)
    deal.archived_at = None
    deal.updated_at = _now()
    db.flush()
    return deal


def _deal_filters(
    *,
    q: str | None,
    stage: str | None,
    account_owner: str | None,
    partner_id: UUID | None,
    contact_id: UUID | None,
    close_from: date | None,
    close_to: date | None,
    include_closed: bool,
    include_archived: bool,
    overdue_only: bool,
) -> list:
    filters = []
    if not include_archived:
        filters.append(Deal.archived_at.is_(None))
    if stage:
        filters.append(Deal.stage == stage)
    elif not include_closed:
        filters.append(Deal.stage.in_(OPEN_DEAL_STAGES))
    if account_owner:
        filters.append(func.lower(Deal.account_owner) == account_owner.casefold())
    if partner_id is not None:
        filters.append(Deal.partner_id == partner_id)
    if contact_id is not None:
        filters.append(Deal.contact_id == contact_id)
    if close_from is not None:
        filters.append(Deal.expected_close_on >= close_from)
    if close_to is not None:
        filters.append(Deal.expected_close_on <= close_to)
    if overdue_only:
        filters.append(Deal.stage.in_(OPEN_DEAL_STAGES))
        filters.append(Deal.expected_close_on.is_not(None))
        filters.append(Deal.expected_close_on < _today())
    if q and q.strip():
        pattern = contains_pattern(q.strip())
        company_ids = select(Partner.id).where(Partner.company_name.ilike(pattern, escape="\\"))
        filters.append(or_(Deal.title.ilike(pattern, escape="\\"), Deal.partner_id.in_(company_ids)))
    return filters


def query_deals(db: Session, *, page: int, page_size: int, **kwargs) -> tuple[list[Deal], int]:
    filters = _deal_filters(**kwargs)
    count_statement = select(func.count()).select_from(Deal)
    statement = select(Deal)
    if filters:
        count_statement = count_statement.where(*filters)
        statement = statement.where(*filters)
    total = int(db.scalar(count_statement) or 0)
    rows = db.scalars(
        statement.order_by(Deal.expected_close_on.asc().nulls_last(), Deal.title.asc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def pipeline(db: Session, **kwargs) -> PipelineBoard:
    filters = _deal_filters(include_closed=False, include_archived=False, overdue_only=False, stage=None, **kwargs)
    rows = list(db.scalars(select(Deal).where(*filters).order_by(Deal.expected_close_on.asc().nulls_last(), Deal.title.asc())).all())
    partners, _contacts = _names(db, [row.partner_id for row in rows], [])
    grouped: dict[str, list[Deal]] = {stage: [] for stage in OPEN_DEAL_STAGES}
    for row in rows:
        if row.stage in grouped:
            grouped[row.stage].append(row)
    columns = []
    for stage in OPEN_DEAL_STAGES:
        deals = grouped[stage]
        cards = []
        total = Decimal("0.00")
        for deal in deals:
            total += deal.estimated_value
            cards.append(
                PipelineCard(
                    id=deal.id,
                    title=deal.title,
                    partner_id=deal.partner_id,
                    company_name=partners.get(deal.partner_id, ""),
                    estimated_value=deal.estimated_value,
                    account_owner=deal.account_owner,
                    expected_close_on=deal.expected_close_on,
                    is_overdue=deal.expected_close_on is not None and deal.expected_close_on < _today(),
                    is_demo=deal.is_demo,
                )
            )
        columns.append(PipelineColumn(stage=stage, count=len(cards), total_value=money(total), deals=cards))
    return PipelineBoard(columns=columns)


def deal_summary(db: Session, partner_id: UUID | None = None) -> DealSummary:
    base = [Deal.archived_at.is_(None)]
    if partner_id is not None:
        base.append(Deal.partner_id == partner_id)
    open_filter = [*base, Deal.stage.in_(OPEN_DEAL_STAGES)]
    open_count = int(db.scalar(select(func.count()).select_from(Deal).where(*open_filter)) or 0)
    open_demo = int(db.scalar(select(func.count()).select_from(Deal).where(*open_filter, Deal.is_demo.is_(True))) or 0)
    weighted = db.execute(
        select(Deal.estimated_value, Deal.probability).where(*open_filter)
    ).all()
    pipeline_value = money(sum((value * probability / Decimal("100") for value, probability in weighted), Decimal("0")))
    won_filter = [*base, Deal.stage == "gewonnen"]
    won_count = int(db.scalar(select(func.count()).select_from(Deal).where(*won_filter)) or 0)
    won_value = money(db.scalar(select(func.coalesce(func.sum(Deal.estimated_value), 0)).where(*won_filter)) or Decimal("0"))
    overdue = int(
        db.scalar(
            select(func.count()).select_from(Deal).where(
                *open_filter,
                Deal.expected_close_on.is_not(None),
                Deal.expected_close_on < _today(),
            )
        )
        or 0
    )
    return DealSummary(
        open_count=open_count,
        open_demo=open_demo,
        pipeline_value=pipeline_value,
        won_count=won_count,
        won_value=won_value,
        overdue_count=overdue,
    )


def _product_read(product: Product) -> ProductRead:
    return ProductRead(
        id=product.id,
        sku=product.sku,
        name=product.name,
        category=product.category,
        description=product.description,
        container_type=product.container_type,
        container_size=product.container_size,
        sales_unit=product.sales_unit,
        list_price=product.list_price,
        vat_rate=product.vat_rate,
        is_active=product.is_active,
        is_demo=product.is_demo,
        created_at=product.created_at,
        updated_at=product.updated_at,
    )


def ensure_sku(db: Session, sku: str, exclude_id: UUID | None = None) -> None:
    statement = select(Product.id).where(func.lower(Product.sku) == sku.casefold())
    if exclude_id is not None:
        statement = statement.where(Product.id != exclude_id)
    if db.scalar(statement) is not None:
        raise CrmServiceError("Diese Artikelnummer ist bereits vergeben.", 409)


def insert_product(db: Session, data: ProductWrite, *, is_demo: bool = False, demo_key: str | None = None) -> Product:
    ensure_sku(db, data.sku)
    product = Product(is_demo=is_demo, demo_key=demo_key)
    for field in PRODUCT_FIELDS:
        setattr(product, field, getattr(data, field))
    product.updated_at = _now()
    db.add(product)
    db.flush()
    return product


def update_product(db: Session, product_id: UUID, data: ProductWrite) -> Product:
    product = require_product(db, product_id)
    ensure_sku(db, data.sku, exclude_id=product.id)
    for field in PRODUCT_FIELDS:
        setattr(product, field, getattr(data, field))
    product.updated_at = _now()
    db.flush()
    return product


def deactivate_product(db: Session, product_id: UUID) -> Product:
    product = require_product(db, product_id)
    if not product.is_active:
        raise CrmServiceError("Das Produkt ist bereits inaktiv.", 409)
    product.is_active = False
    product.updated_at = _now()
    db.flush()
    return product


def query_products(
    db: Session,
    *,
    q: str | None,
    category: str | None,
    include_inactive: bool,
    page: int,
    page_size: int,
) -> tuple[list[Product], int]:
    filters = []
    if not include_inactive:
        filters.append(Product.is_active.is_(True))
    if category:
        filters.append(Product.category == category)
    if q and q.strip():
        pattern = contains_pattern(q.strip())
        filters.append(or_(Product.name.ilike(pattern, escape="\\"), Product.sku.ilike(pattern, escape="\\")))
    count_statement = select(func.count()).select_from(Product)
    statement = select(Product)
    if filters:
        count_statement = count_statement.where(*filters)
        statement = statement.where(*filters)
    total = int(db.scalar(count_statement) or 0)
    rows = db.scalars(statement.order_by(Product.name.asc()).offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total


def _next_order_number(db: Session) -> str:
    year = _today().year
    prefix = f"BP-{year}-"
    latest = db.scalars(
        select(Order.order_number).where(Order.order_number.like(f"{prefix}%")).order_by(Order.order_number.desc())
    ).first()
    number = 1
    if latest:
        try:
            number = int(latest.removeprefix(prefix)) + 1
        except ValueError:
            number = 1
    return f"{prefix}{number:04d}"


def _build_items(db: Session, order: Order, payload: OrderWrite) -> None:
    subtotal = Decimal("0.00")
    discount_total = Decimal("0.00")
    net_total = Decimal("0.00")
    vat_total = Decimal("0.00")
    gross_total = Decimal("0.00")
    for index, item in enumerate(payload.items, start=1):
        product = require_product(db, item.product_id)
        if not product.is_active:
            raise CrmServiceError(f"Das Produkt «{product.name}» ist inaktiv und kann nicht bestellt werden.", 409)
        unit_price = product.list_price if item.unit_price is None else item.unit_price
        discount, net, vat, gross = line_amounts(item.quantity, unit_price, item.discount_percent, product.vat_rate)
        subtotal += money(item.quantity * unit_price)
        discount_total += discount
        net_total += net
        vat_total += vat
        gross_total += gross
        db.add(
            OrderItem(
                order_id=order.id,
                product_id=product.id,
                position=index,
                product_name=product.name,
                sku=product.sku,
                quantity=item.quantity,
                unit_price=unit_price,
                discount_percent=item.discount_percent,
                discount_amount=discount,
                vat_rate=product.vat_rate,
                line_net=net,
                line_vat=vat,
                line_gross=gross,
            )
        )
    order.subtotal = money(subtotal)
    order.discount_total = money(discount_total)
    order.net_total = money(net_total)
    order.vat_total = money(vat_total)
    order.gross_total = money(gross_total)


def _order_items(db: Session, order_id: UUID) -> list[OrderItem]:
    return list(
        db.scalars(select(OrderItem).where(OrderItem.order_id == order_id).order_by(OrderItem.position.asc())).all()
    )


def read_order(db: Session, order: Order) -> OrderRead:
    partners, contacts = _names(db, [order.partner_id], [order.contact_id] if order.contact_id else [])
    items = [
        OrderItemRead(
            id=item.id,
            product_id=item.product_id,
            position=item.position,
            product_name=item.product_name,
            sku=item.sku,
            quantity=item.quantity,
            unit_price=item.unit_price,
            discount_percent=item.discount_percent,
            discount_amount=item.discount_amount,
            vat_rate=item.vat_rate,
            line_net=item.line_net,
            line_vat=item.line_vat,
            line_gross=item.line_gross,
        )
        for item in _order_items(db, order.id)
    ]
    return OrderRead(
        id=order.id,
        order_number=order.order_number,
        partner_id=order.partner_id,
        contact_id=order.contact_id,
        deal_id=order.deal_id,
        company_name=partners.get(order.partner_id, ""),
        contact_name=contacts.get(order.contact_id) if order.contact_id else None,
        ordered_on=order.ordered_on,
        requested_delivery_on=order.requested_delivery_on,
        status=order.status,
        notes=order.notes,
        erp_reference=order.erp_reference,
        subtotal=order.subtotal,
        discount_total=order.discount_total,
        net_total=order.net_total,
        vat_total=order.vat_total,
        gross_total=order.gross_total,
        is_demo=order.is_demo,
        archived_at=order.archived_at,
        created_at=order.created_at,
        updated_at=order.updated_at,
        items=items,
        allowed_transitions=sorted(ORDER_TRANSITIONS[order.status]),
    )


def _ensure_erp(db: Session, reference: str | None, exclude_id: UUID | None = None) -> None:
    if not reference:
        return
    statement = select(Order.id).where(func.lower(Order.erp_reference) == reference.casefold())
    if exclude_id is not None:
        statement = statement.where(Order.id != exclude_id)
    if db.scalar(statement) is not None:
        raise CrmServiceError("Diese ERP-Referenz ist bereits einer Bestellung zugeordnet.", 409)


def insert_order(
    db: Session,
    data: OrderWrite,
    *,
    is_demo: bool = False,
    demo_key: str | None = None,
    order_number: str | None = None,
) -> Order:
    _ensure_link(db, data.partner_id, data.contact_id)
    _ensure_deal_for_partner(db, data.deal_id, data.partner_id)
    _ensure_erp(db, data.erp_reference)
    order = Order(
        order_number=order_number or _next_order_number(db),
        partner_id=data.partner_id,
        contact_id=data.contact_id,
        deal_id=data.deal_id,
        ordered_on=data.ordered_on,
        requested_delivery_on=data.requested_delivery_on,
        status="eingereicht" if data.submit else "entwurf",
        notes=data.notes,
        erp_reference=data.erp_reference,
        subtotal=Decimal("0.00"),
        discount_total=Decimal("0.00"),
        net_total=Decimal("0.00"),
        vat_total=Decimal("0.00"),
        gross_total=Decimal("0.00"),
        is_demo=is_demo,
        demo_key=demo_key,
    )
    db.add(order)
    db.flush()
    _build_items(db, order, data)
    order.updated_at = _now()
    db.flush()
    from app.services.automation import company_name, publish_event

    publish_event(
        db,
        "order_created",
        dedupe_key=f"order:{order.id}",
        context={
            "owner": None,
            "partner_id": order.partner_id,
            "contact_id": order.contact_id,
            "company_name": company_name(db, order.partner_id),
            "href": f"/bestellungen/{order.id}",
        },
    )
    return order


def update_order(db: Session, order_id: UUID, data: OrderWrite) -> Order:
    order = require_order(db, order_id)
    if order.status != "entwurf":
        raise CrmServiceError("Nur Entwürfe können bearbeitet werden.", 409)
    _ensure_link(db, data.partner_id, data.contact_id)
    _ensure_deal_for_partner(db, data.deal_id, data.partner_id)
    _ensure_erp(db, data.erp_reference, exclude_id=order.id)
    for item in _order_items(db, order.id):
        db.delete(item)
    db.flush()
    order.partner_id = data.partner_id
    order.contact_id = data.contact_id
    order.deal_id = data.deal_id
    order.ordered_on = data.ordered_on
    order.requested_delivery_on = data.requested_delivery_on
    order.notes = data.notes
    order.erp_reference = data.erp_reference
    if data.submit:
        order.status = "eingereicht"
    _build_items(db, order, data)
    order.updated_at = _now()
    db.flush()
    return order


def change_order_status(db: Session, order_id: UUID, status: str) -> Order:
    order = require_order(db, order_id)
    if order.archived_at is not None:
        raise CrmServiceError("Archivierte Bestellungen können nicht geändert werden.", 409)
    allowed = ORDER_TRANSITIONS[order.status]
    if status not in allowed:
        raise CrmServiceError("Dieser Statuswechsel ist nicht erlaubt.", 409)
    order.status = status
    order.updated_at = _now()
    db.flush()
    return order


def query_orders(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    partner_id: UUID | None,
    contact_id: UUID | None,
    deal_id: UUID | None,
    page: int,
    page_size: int,
) -> tuple[list[OrderListItem], int]:
    filters = [Order.archived_at.is_(None)]
    if status:
        filters.append(Order.status == status)
    if partner_id is not None:
        filters.append(Order.partner_id == partner_id)
    if contact_id is not None:
        filters.append(Order.contact_id == contact_id)
    if deal_id is not None:
        filters.append(Order.deal_id == deal_id)
    if q and q.strip():
        pattern = contains_pattern(q.strip())
        company_ids = select(Partner.id).where(Partner.company_name.ilike(pattern, escape="\\"))
        filters.append(or_(Order.order_number.ilike(pattern, escape="\\"), Order.partner_id.in_(company_ids)))
    total = int(db.scalar(select(func.count()).select_from(Order).where(*filters)) or 0)
    rows = db.scalars(
        select(Order).where(*filters).order_by(Order.ordered_on.desc(), Order.order_number.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    partners, _contacts = _names(db, [row.partner_id for row in rows], [])
    items = [
        OrderListItem(
            id=row.id,
            order_number=row.order_number,
            partner_id=row.partner_id,
            company_name=partners.get(row.partner_id, ""),
            ordered_on=row.ordered_on,
            status=row.status,
            gross_total=row.gross_total,
            is_demo=row.is_demo,
        )
        for row in rows
    ]
    return items, total


def order_summary(db: Session, partner_id: UUID | None = None) -> OrderSummary:
    filters = [Order.archived_at.is_(None), Order.status.in_(COUNTED_ORDER_STATUSES)]
    if partner_id is not None:
        filters.append(Order.partner_id == partner_id)
    volume = money(db.scalar(select(func.coalesce(func.sum(Order.gross_total), 0)).where(*filters)) or Decimal("0"))
    volume_demo = money(
        db.scalar(select(func.coalesce(func.sum(Order.gross_total), 0)).where(*filters, Order.is_demo.is_(True))) or Decimal("0")
    )
    since = _today() - timedelta(days=30)
    new_count = int(
        db.scalar(select(func.count()).select_from(Order).where(*filters, Order.ordered_on >= since)) or 0
    )
    order_count = int(db.scalar(select(func.count()).select_from(Order).where(*filters)) or 0)
    last_ordered = db.scalar(select(func.max(Order.ordered_on)).where(*filters))
    return OrderSummary(
        volume=volume,
        volume_demo=volume_demo,
        new_count=new_count,
        order_count=order_count,
        last_ordered_on=last_ordered,
    )
