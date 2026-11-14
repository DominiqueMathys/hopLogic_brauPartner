import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.partner import utcnow, _in_clause
from app.sales_catalog import (
    CONTAINER_TYPES,
    DEAL_PRIORITIES,
    DEAL_STAGES,
    ORDER_STATUSES,
    PRODUCT_CATEGORIES,
)


class Deal(Base):
    __tablename__ = "verkaufschancen"
    __table_args__ = (
        CheckConstraint(_in_clause("stage", DEAL_STAGES), name="ck_verkaufschancen_stage"),
        CheckConstraint(_in_clause("priority", DEAL_PRIORITIES), name="ck_verkaufschancen_priority"),
        CheckConstraint("estimated_value >= 0", name="ck_verkaufschancen_value"),
        CheckConstraint("probability >= 0 AND probability <= 100", name="ck_verkaufschancen_probability"),
        UniqueConstraint("demo_key", name="uq_verkaufschancen_demo_key"),
        Index("ix_verkaufschancen_partner", "partner_id"),
        Index("ix_verkaufschancen_stage", "stage"),
        Index("ix_verkaufschancen_expected_close", "expected_close_on"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    partner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="RESTRICT"), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("kontakte.id", ondelete="RESTRICT"))
    account_owner: Mapped[str | None] = mapped_column(String(120))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))
    estimated_value: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    expected_close_on: Mapped[date | None] = mapped_column(Date)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    probability: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    description: Mapped[str | None] = mapped_column(Text)
    closed_on: Mapped[date | None] = mapped_column(Date)
    loss_reason: Mapped[str | None] = mapped_column(String(500))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class DealStageHistory(Base):
    __tablename__ = "verkaufschancen_phasen"
    __table_args__ = (
        CheckConstraint(_in_clause("to_stage", DEAL_STAGES), name="ck_verkaufschancen_phasen_to"),
        Index("ix_verkaufschancen_phasen_deal", "deal_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    deal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("verkaufschancen.id", ondelete="RESTRICT"), nullable=False)
    from_stage: Mapped[str | None] = mapped_column(String(30))
    to_stage: Mapped[str] = mapped_column(String(30), nullable=False)
    changed_by: Mapped[str | None] = mapped_column(String(120))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())


class Product(Base):
    __tablename__ = "produkte"
    __table_args__ = (
        CheckConstraint(_in_clause("category", PRODUCT_CATEGORIES), name="ck_produkte_category"),
        CheckConstraint(_in_clause("container_type", CONTAINER_TYPES), name="ck_produkte_container"),
        CheckConstraint("list_price >= 0", name="ck_produkte_price"),
        CheckConstraint("vat_rate >= 0 AND vat_rate <= 100", name="ck_produkte_vat"),
        UniqueConstraint("demo_key", name="uq_produkte_demo_key"),
        Index("ix_produkte_name", "name"),
        Index("ix_produkte_category", "category"),
        Index(
            "uq_produkte_sku",
            text("lower(sku)"),
            unique=True,
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    sku: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    container_type: Mapped[str] = mapped_column(String(20), nullable=False, default="flasche")
    container_size: Mapped[str | None] = mapped_column(String(40))
    sales_unit: Mapped[str | None] = mapped_column(String(80))
    list_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class Order(Base):
    __tablename__ = "bestellungen"
    __table_args__ = (
        CheckConstraint(_in_clause("status", ORDER_STATUSES), name="ck_bestellungen_status"),
        CheckConstraint("subtotal >= 0 AND net_total >= 0 AND gross_total >= 0", name="ck_bestellungen_totals"),
        UniqueConstraint("order_number", name="uq_bestellungen_order_number"),
        UniqueConstraint("demo_key", name="uq_bestellungen_demo_key"),
        Index("ix_bestellungen_partner", "partner_id"),
        Index("ix_bestellungen_status", "status"),
        Index("ix_bestellungen_ordered_on", "ordered_on"),
        Index(
            "uq_bestellungen_erp_reference",
            text("lower(erp_reference)"),
            unique=True,
            postgresql_where=text("erp_reference IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_number: Mapped[str] = mapped_column(String(40), nullable=False)
    partner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="RESTRICT"), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("kontakte.id", ondelete="RESTRICT"))
    deal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("verkaufschancen.id", ondelete="RESTRICT"))
    ordered_on: Mapped[date] = mapped_column(Date, nullable=False)
    requested_delivery_on: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="entwurf")
    notes: Mapped[str | None] = mapped_column(Text)
    erp_reference: Mapped[str | None] = mapped_column(String(80))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    net_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vat_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    gross_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class OrderItem(Base):
    __tablename__ = "bestellpositionen"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_bestellpositionen_quantity"),
        CheckConstraint("unit_price >= 0", name="ck_bestellpositionen_price"),
        CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="ck_bestellpositionen_discount"),
        CheckConstraint("vat_rate >= 0 AND vat_rate <= 100", name="ck_bestellpositionen_vat"),
        UniqueConstraint("order_id", "position", name="uq_bestellpositionen_position"),
        Index("ix_bestellpositionen_product", "product_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bestellungen.id", ondelete="RESTRICT"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("produkte.id", ondelete="RESTRICT"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    product_name: Mapped[str] = mapped_column(String(200), nullable=False)
    sku: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    line_net: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_gross: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
