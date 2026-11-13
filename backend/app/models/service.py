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
from app.models.partner import _in_clause, utcnow
from app.service_catalog import (
    RESOLUTION_CODES,
    SEGMENT_FIELDS,
    SEGMENT_MATCH_MODES,
    SEGMENT_OPERATORS,
    TICKET_CATEGORIES,
    TICKET_EVENT_TYPES,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
)


class ServiceTicket(Base):
    __tablename__ = "service_tickets"
    __table_args__ = (
        CheckConstraint(_in_clause("category", TICKET_CATEGORIES), name="ck_service_tickets_category"),
        CheckConstraint(_in_clause("priority", TICKET_PRIORITIES), name="ck_service_tickets_priority"),
        CheckConstraint(_in_clause("status", TICKET_STATUSES), name="ck_service_tickets_status"),
        UniqueConstraint("ticket_number", name="uq_service_tickets_number"),
        UniqueConstraint("demo_key", name="uq_service_tickets_demo_key"),
        Index("ix_service_tickets_partner", "partner_id"),
        Index("ix_service_tickets_status", "status"),
        Index("ix_service_tickets_priority", "priority"),
        Index("ix_service_tickets_owner", "account_owner"),
        Index("ix_service_tickets_updated", "updated_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ticket_number: Mapped[str] = mapped_column(String(40), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    category: Mapped[str] = mapped_column(String(40), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    partner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="RESTRICT"), nullable=False)
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("kontakte.id", ondelete="RESTRICT"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bestellungen.id", ondelete="RESTRICT"))
    account_owner: Mapped[str | None] = mapped_column(String(120))
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="neu")
    due_on: Mapped[date | None] = mapped_column(Date)
    internal_remark: Mapped[str | None] = mapped_column(Text)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class TicketProduct(Base):
    __tablename__ = "ticket_produkte"
    __table_args__ = (Index("ix_ticket_produkte_product", "product_id"),)

    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_tickets.id", ondelete="RESTRICT"), primary_key=True)
    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("produkte.id", ondelete="RESTRICT"), primary_key=True)


class TicketEvent(Base):
    __tablename__ = "ticket_ereignisse"
    __table_args__ = (
        CheckConstraint(_in_clause("event_type", TICKET_EVENT_TYPES), name="ck_ticket_ereignisse_type"),
        Index("ix_ticket_ereignisse_ticket", "ticket_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_tickets.id", ondelete="RESTRICT"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    from_value: Mapped[str | None] = mapped_column(String(200))
    to_value: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)
    changed_by: Mapped[str | None] = mapped_column(String(120))
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aufgaben.id", ondelete="RESTRICT"))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())


class TicketAttachment(Base):
    __tablename__ = "ticket_anhaenge"
    __table_args__ = (Index("ix_ticket_anhaenge_ticket", "ticket_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_tickets.id", ondelete="RESTRICT"), nullable=False)
    original_name: Mapped[str] = mapped_column(String(200), nullable=False)
    stored_name: Mapped[str] = mapped_column(String(80), nullable=False)
    content_type: Mapped[str] = mapped_column(String(80), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())


class TicketResolution(Base):
    __tablename__ = "ticket_loesungen"
    __table_args__ = (
        CheckConstraint(_in_clause("code", RESOLUTION_CODES), name="ck_ticket_loesungen_code"),
        Index("ix_ticket_loesungen_ticket", "ticket_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("service_tickets.id", ondelete="RESTRICT"), nullable=False)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    recorded_by: Mapped[str | None] = mapped_column(String(120))
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())


class CustomerSegment(Base):
    __tablename__ = "kundensegmente"
    __table_args__ = (
        CheckConstraint(_in_clause("match_mode", SEGMENT_MATCH_MODES), name="ck_kundensegmente_mode"),
        UniqueConstraint("name", name="uq_kundensegmente_name"),
        UniqueConstraint("demo_key", name="uq_kundensegmente_demo_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    match_mode: Mapped[str] = mapped_column(String(10), nullable=False, default="all")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class SegmentCondition(Base):
    __tablename__ = "segmentbedingungen"
    __table_args__ = (
        CheckConstraint(_in_clause("field_name", SEGMENT_FIELDS), name="ck_segmentbedingungen_field"),
        CheckConstraint(_in_clause("operator", SEGMENT_OPERATORS), name="ck_segmentbedingungen_operator"),
        Index("ix_segmentbedingungen_segment", "segment_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    segment_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kundensegmente.id", ondelete="RESTRICT"), nullable=False)
    field_name: Mapped[str] = mapped_column(String(40), nullable=False)
    operator: Mapped[str] = mapped_column(String(20), nullable=False)
    value: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    position: Mapped[int] = mapped_column(Integer, nullable=False, default=1)


class PartnerMetric:
    """Computed view used while evaluating segments. Not a table."""

    def __init__(
        self,
        partner_id: uuid.UUID,
        company_name: str,
        partner_type: str,
        industry: str | None,
        region: str | None,
        status: str,
        order_count: int,
        order_volume: Decimal,
        last_order_on: date | None,
        open_deals: int,
        open_tickets: int,
        last_activity_on: date | None,
    ) -> None:
        self.partner_id = partner_id
        self.company_name = company_name
        self.partner_type = partner_type
        self.industry = industry
        self.region = region
        self.status = status
        self.order_count = order_count
        self.order_volume = order_volume
        self.last_order_on = last_order_on
        self.open_deals = open_deals
        self.open_tickets = open_tickets
        self.last_activity_on = last_activity_on
