import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.festival_catalog import (
    ASSIGNMENT_KINDS,
    ASSIGNMENT_STATUSES,
    DELIVERY_STATUSES,
    EVENT_STATUSES,
    EVENT_TYPES,
    MATERIAL_CONDITIONS,
    MATERIAL_STATUSES,
    MATERIAL_TRACKING,
    MOVEMENT_TYPES,
    QUOTE_ITEM_KINDS,
    QUOTE_STATUSES,
    REQUEST_STATUSES,
    RESERVATION_STATUSES,
)
from app.models.partner import _in_clause, utcnow


class NumberRange(Base):
    __tablename__ = "nummernkreise"

    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    last_value: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class Festival(Base):
    __tablename__ = "feste"
    __table_args__ = (
        CheckConstraint(_in_clause("event_type", EVENT_TYPES), name="ck_feste_event_type"),
        CheckConstraint(_in_clause("request_status", REQUEST_STATUSES), name="ck_feste_request_status"),
        CheckConstraint(_in_clause("event_status", EVENT_STATUSES), name="ck_feste_event_status"),
        CheckConstraint(_in_clause("material_status", MATERIAL_STATUSES), name="ck_feste_material_status"),
        CheckConstraint(_in_clause("quote_status", QUOTE_STATUSES), name="ck_feste_quote_status"),
        CheckConstraint(_in_clause("delivery_status", DELIVERY_STATUSES), name="ck_feste_delivery_status"),
        CheckConstraint("ends_at > starts_at", name="ck_feste_zeitraum"),
        UniqueConstraint("event_number", name="uq_feste_nummer"),
        UniqueConstraint("demo_key", name="uq_feste_demo_key"),
        Index("ix_feste_starts_at", "starts_at"),
        Index("ix_feste_status", "event_status"),
        Index("ix_feste_region", "region"),
        Index("ix_feste_owner", "account_owner"),
        Index("ix_feste_organizer_partner", "organizer_partner_id"),
        Index("ix_feste_distributor_partner", "distributor_partner_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    event_number: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False, default="fest")
    organizer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    organizer_partner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="RESTRICT"))
    distributor_partner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="RESTRICT"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("kontakte.id", ondelete="RESTRICT"))
    contact_name: Mapped[str | None] = mapped_column(String(200))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254))
    venue_name: Mapped[str | None] = mapped_column(String(200))
    street: Mapped[str | None] = mapped_column(String(200))
    postal_code: Mapped[str | None] = mapped_column(String(12))
    city: Mapped[str | None] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="Schweiz")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_visitors: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    requirements: Mapped[str | None] = mapped_column(Text)
    drinks: Mapped[str | None] = mapped_column(Text)
    material_wish: Mapped[str | None] = mapped_column(Text)
    delivery_wish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pickup_wish_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    account_owner: Mapped[str | None] = mapped_column(String(120))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))
    request_status: Mapped[str] = mapped_column(String(40), nullable=False, default="neue_anfrage")
    event_status: Mapped[str] = mapped_column(String(40), nullable=False, default="anfrage")
    material_status: Mapped[str] = mapped_column(String(40), nullable=False, default="kein_bedarf")
    quote_status: Mapped[str] = mapped_column(String(40), nullable=False, default="keine")
    delivery_status: Mapped[str] = mapped_column(String(40), nullable=False, default="keine")
    is_binding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    order_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("bestellungen.id", ondelete="SET NULL"))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)

    changes: Mapped[list["FestivalChange"]] = relationship(back_populates="festival")
    quotes: Mapped[list["FestivalQuote"]] = relationship(back_populates="festival")
    reservations: Mapped[list["MaterialReservation"]] = relationship(back_populates="festival")
    deliveries: Mapped[list["FestivalDelivery"]] = relationship(back_populates="festival")
    assignments: Mapped[list["FestivalAssignment"]] = relationship(back_populates="festival")


class FestivalChange(Base):
    __tablename__ = "fest_aenderungen"
    __table_args__ = (Index("ix_fest_aenderungen_fest", "festival_id", "changed_at"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    festival_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feste.id", ondelete="RESTRICT"), nullable=False)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    actor_label: Mapped[str | None] = mapped_column(String(200))
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    reason: Mapped[str | None] = mapped_column(String(400))
    note: Mapped[str | None] = mapped_column(Text)
    festival: Mapped[Festival] = relationship(back_populates="changes")


class MaterialCategory(Base):
    __tablename__ = "material_kategorien"
    __table_args__ = (UniqueConstraint("code", name="uq_material_kategorien_code"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_example: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class FestivalMaterial(Base):
    __tablename__ = "festmaterial"
    __table_args__ = (
        CheckConstraint(_in_clause("tracking", MATERIAL_TRACKING), name="ck_festmaterial_tracking"),
        CheckConstraint(_in_clause("condition", MATERIAL_CONDITIONS), name="ck_festmaterial_condition"),
        CheckConstraint("quantity_total >= 0 AND quantity_defective >= 0 AND quantity_locked >= 0 AND quantity_missing >= 0", name="ck_festmaterial_mengen"),
        CheckConstraint("quantity_defective + quantity_locked + quantity_missing <= quantity_total", name="ck_festmaterial_teilmengen"),
        CheckConstraint("prep_hours >= 0 AND return_hours >= 0 AND cleaning_hours >= 0", name="ck_festmaterial_puffer"),
        UniqueConstraint("material_number", name="uq_festmaterial_nummer"),
        UniqueConstraint("demo_key", name="uq_festmaterial_demo_key"),
        Index("ix_festmaterial_kategorie", "category_id"),
        Index("ix_festmaterial_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    material_number: Mapped[str] = mapped_column(String(40), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("material_kategorien.id", ondelete="SET NULL"))
    description: Mapped[str | None] = mapped_column(Text)
    tracking: Mapped[str] = mapped_column(String(20), nullable=False, default="menge")
    quantity_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_defective: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_locked: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity_missing: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location: Mapped[str | None] = mapped_column(String(120))
    condition: Mapped[str] = mapped_column(String(30), nullable=False, default="einsatzbereit")
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="Stück")
    rental_price: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    prep_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    return_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleaning_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    erp_article_number: Mapped[str | None] = mapped_column(String(40))
    erp_source: Mapped[str | None] = mapped_column(String(20))
    erp_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)

    assets: Mapped[list["MaterialAsset"]] = relationship(back_populates="material")


class MaterialAsset(Base):
    __tablename__ = "material_inventar"
    __table_args__ = (
        CheckConstraint(_in_clause("condition", MATERIAL_CONDITIONS), name="ck_material_inventar_condition"),
        UniqueConstraint("inventory_number", name="uq_material_inventar_nummer"),
        UniqueConstraint("demo_key", name="uq_material_inventar_demo_key"),
        Index("ix_material_inventar_material", "material_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("festmaterial.id", ondelete="RESTRICT"), nullable=False)
    inventory_number: Mapped[str] = mapped_column(String(40), nullable=False)
    condition: Mapped[str] = mapped_column(String(30), nullable=False, default="einsatzbereit")
    location: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    material: Mapped[FestivalMaterial] = relationship(back_populates="assets")


class MaterialReservation(Base):
    __tablename__ = "material_reservationen"
    __table_args__ = (
        CheckConstraint(_in_clause("status", RESERVATION_STATUSES), name="ck_material_reservationen_status"),
        CheckConstraint("ends_at > starts_at", name="ck_material_reservationen_zeitraum"),
        CheckConstraint("prep_hours >= 0 AND return_hours >= 0 AND cleaning_hours >= 0", name="ck_material_reservationen_puffer"),
        UniqueConstraint("reservation_number", name="uq_material_reservationen_nummer"),
        UniqueConstraint("demo_key", name="uq_material_reservationen_demo_key"),
        Index("ix_material_reservationen_fest", "festival_id"),
        Index("ix_material_reservationen_status", "status"),
        Index("ix_material_reservationen_zeit", "starts_at", "ends_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reservation_number: Mapped[str] = mapped_column(String(40), nullable=False)
    festival_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feste.id", ondelete="RESTRICT"), nullable=False)
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="entwurf")
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    prep_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    return_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cleaning_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    location: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    returned_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)
    festival: Mapped[Festival] = relationship(back_populates="reservations")
    lines: Mapped[list["MaterialReservationLine"]] = relationship(back_populates="reservation")


class MaterialReservationLine(Base):
    __tablename__ = "material_reservationspositionen"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_reservationspositionen_menge"),
        CheckConstraint("issued_qty >= 0 AND returned_qty >= 0 AND damaged_qty >= 0 AND missing_qty >= 0", name="ck_reservationspositionen_ist"),
        CheckConstraint("returned_qty + damaged_qty + missing_qty <= issued_qty", name="ck_reservationspositionen_ruecknahme"),
        Index("ix_reservationspositionen_material", "material_id"),
        Index("ix_reservationspositionen_reservation", "reservation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("material_reservationen.id", ondelete="RESTRICT"), nullable=False)
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("festmaterial.id", ondelete="RESTRICT"), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("material_inventar.id", ondelete="RESTRICT"))
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    issued_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    returned_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    damaged_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    missing_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reservation: Mapped[MaterialReservation] = relationship(back_populates="lines")


class MaterialMovement(Base):
    __tablename__ = "material_bewegungen"
    __table_args__ = (
        CheckConstraint(_in_clause("movement_type", MOVEMENT_TYPES), name="ck_material_bewegungen_typ"),
        Index("ix_material_bewegungen_material", "material_id", "occurred_at"),
        Index("ix_material_bewegungen_fest", "festival_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    material_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("festmaterial.id", ondelete="RESTRICT"), nullable=False)
    asset_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("material_inventar.id", ondelete="SET NULL"))
    festival_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("feste.id", ondelete="SET NULL"))
    reservation_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("material_reservationen.id", ondelete="SET NULL"))
    movement_type: Mapped[str] = mapped_column(String(40), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    actor_label: Mapped[str | None] = mapped_column(String(200))
    note: Mapped[str | None] = mapped_column(Text)


class MaterialIssue(Base):
    __tablename__ = "material_ausgaben"
    __table_args__ = (
        UniqueConstraint("reservation_id", name="uq_material_ausgaben_reservation"),
        Index("ix_material_ausgaben_fest", "festival_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("material_reservationen.id", ondelete="RESTRICT"), nullable=False)
    festival_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feste.id", ondelete="RESTRICT"), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_label: Mapped[str | None] = mapped_column(String(200))
    condition_note: Mapped[str | None] = mapped_column(Text)
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class MaterialReturn(Base):
    __tablename__ = "material_ruecknahmen"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_material_ruecknahmen_schluessel"),
        Index("ix_material_ruecknahmen_reservation", "reservation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    reservation_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("material_reservationen.id", ondelete="RESTRICT"), nullable=False)
    festival_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feste.id", ondelete="RESTRICT"), nullable=False)
    returned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actor_label: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    idempotency_key: Mapped[str | None] = mapped_column(String(80))
    stock_posted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))


class FestivalQuote(Base):
    __tablename__ = "fest_offerten"
    __table_args__ = (
        CheckConstraint(_in_clause("status", ("entwurf", "in_pruefung", "versendet", "angenommen", "abgelehnt", "abgelaufen")), name="ck_fest_offerten_status"),
        CheckConstraint("version >= 1", name="ck_fest_offerten_version"),
        UniqueConstraint("quote_number", "version", name="uq_fest_offerten_version"),
        UniqueConstraint("demo_key", name="uq_fest_offerten_demo_key"),
        Index("ix_fest_offerten_fest", "festival_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    quote_number: Mapped[str] = mapped_column(String(40), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    festival_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feste.id", ondelete="RESTRICT"), nullable=False)
    previous_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("fest_offerten.id", ondelete="SET NULL"))
    contact_name: Mapped[str | None] = mapped_column(String(200))
    quote_on: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="entwurf")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="CHF")
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    notes: Mapped[str | None] = mapped_column(Text)
    net_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    vat_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    gross_total: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)
    festival: Mapped[Festival] = relationship(back_populates="quotes")
    items: Mapped[list["FestivalQuoteItem"]] = relationship(back_populates="quote")


class FestivalQuoteItem(Base):
    __tablename__ = "fest_offerten_positionen"
    __table_args__ = (
        CheckConstraint(_in_clause("kind", QUOTE_ITEM_KINDS), name="ck_fest_offerten_positionen_art"),
        CheckConstraint("quantity > 0", name="ck_fest_offerten_positionen_menge"),
        Index("ix_fest_offerten_positionen_offerte", "quote_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    quote_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("fest_offerten.id", ondelete="RESTRICT"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 3), nullable=False)
    unit: Mapped[str] = mapped_column(String(40), nullable=False, default="Stück")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    discount_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=Decimal("0.00"))
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    line_discount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_net: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    line_gross: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    material_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("festmaterial.id", ondelete="SET NULL"))
    product_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("produkte.id", ondelete="SET NULL"))
    quote: Mapped[FestivalQuote] = relationship(back_populates="items")


class FestivalDelivery(Base):
    __tablename__ = "fest_transporte"
    __table_args__ = (
        CheckConstraint(_in_clause("status", ("geplant", "bereit", "unterwegs", "geliefert", "abholung_geplant", "abgeholt", "abgeschlossen")), name="ck_fest_transporte_status"),
        UniqueConstraint("demo_key", name="uq_fest_transporte_demo_key"),
        Index("ix_fest_transporte_fest", "festival_id"),
        Index("ix_fest_transporte_lieferung", "deliver_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    festival_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feste.id", ondelete="RESTRICT"), nullable=False)
    address: Mapped[str] = mapped_column(String(300), nullable=False)
    deliver_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deliver_window: Mapped[str | None] = mapped_column(String(80))
    pickup_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    pickup_window: Mapped[str | None] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(40), nullable=False, default="geplant")
    account_owner: Mapped[str | None] = mapped_column(String(120))
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)
    festival: Mapped[Festival] = relationship(back_populates="deliveries")


class FestivalAssignment(Base):
    __tablename__ = "fest_einsaetze"
    __table_args__ = (
        CheckConstraint(_in_clause("kind", ASSIGNMENT_KINDS), name="ck_fest_einsaetze_art"),
        CheckConstraint(_in_clause("status", ASSIGNMENT_STATUSES), name="ck_fest_einsaetze_status"),
        CheckConstraint("ends_at > starts_at", name="ck_fest_einsaetze_zeitraum"),
        UniqueConstraint("demo_key", name="uq_fest_einsaetze_demo_key"),
        Index("ix_fest_einsaetze_fest", "festival_id"),
        Index("ix_fest_einsaetze_person", "person_name", "starts_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    festival_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("feste.id", ondelete="RESTRICT"), nullable=False)
    person_name: Mapped[str] = mapped_column(String(120), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    task: Mapped[str] = mapped_column(String(200), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="geplant")
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)
    festival: Mapped[Festival] = relationship(back_populates="assignments")
