"""ERP integration records.

These tables describe the CRM side of a sync. The mock ERP lives in a separate
SQLite file and is not stored here.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.partner import utcnow

MODES = ("nicht_konfiguriert", "mock", "extern")
JOB_KINDS = ("kunden", "produkte", "bestellstatus", "uebertragung", "verbindungstest")
JOB_STATUSES = ("erfolgreich", "fehlgeschlagen", "teilweise")
RECORD_ACTIONS = ("neu", "aktualisiert", "unveraendert", "konflikt", "ungueltig", "uebertragen")
CONFLICT_STATUSES = ("offen", "geprueft")
TRANSFER_STATUSES = (
    "nicht_uebertragen",
    "bereit",
    "in_uebertragung",
    "erfolgreich",
    "fehlgeschlagen",
    "manuelle_pruefung",
)


def _in(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class ErpConnection(Base):
    __tablename__ = "erp_verbindungen"
    __table_args__ = (
        CheckConstraint(_in("mode", MODES), name="ck_erp_verbindungen_mode"),
        CheckConstraint("auto_order_transfer IS FALSE", name="ck_erp_verbindungen_keine_auto_uebertragung"),
        CheckConstraint("customers_interval_minutes >= 0 AND products_interval_minutes >= 0 AND status_interval_minutes >= 0", name="ck_erp_verbindungen_intervalle"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    mode: Mapped[str] = mapped_column(String(30), nullable=False, default="nicht_konfiguriert", server_default="nicht_konfiguriert")
    customers_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    products_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    status_interval_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    auto_order_transfer: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    connection_ok: Mapped[bool | None] = mapped_column(Boolean)
    last_tested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_customers_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_products_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    running_kind: Mapped[str | None] = mapped_column(String(40))
    running_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class ErpSyncJob(Base):
    __tablename__ = "erp_sync_laeufe"
    __table_args__ = (
        CheckConstraint(_in("kind", JOB_KINDS), name="ck_erp_sync_laeufe_kind"),
        CheckConstraint(_in("status", JOB_STATUSES), name="ck_erp_sync_laeufe_status"),
        Index("ix_erp_sync_laeufe_started", "started_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    dry_run: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    processed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    success_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actor_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))


class ErpSyncRecord(Base):
    __tablename__ = "erp_sync_eintraege"
    __table_args__ = (
        CheckConstraint(_in("action", RECORD_ACTIONS), name="ck_erp_sync_eintraege_action"),
        Index("ix_erp_sync_eintraege_job", "job_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("erp_sync_laeufe.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    external_key: Mapped[str] = mapped_column(String(80), nullable=False)
    action: Mapped[str] = mapped_column(String(30), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    crm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)


class ErpExternalReference(Base):
    __tablename__ = "erp_referenzen"
    __table_args__ = (
        UniqueConstraint("source", "entity_type", "external_key", name="uq_erp_referenzen_extern"),
        Index("ix_erp_referenzen_crm", "entity_type", "crm_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    external_key: Mapped[str] = mapped_column(String(80), nullable=False)
    crm_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())


class ErpConflict(Base):
    __tablename__ = "erp_konflikte"
    __table_args__ = (
        CheckConstraint(_in("status", CONFLICT_STATUSES), name="ck_erp_konflikte_status"),
        Index("ix_erp_konflikte_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    kind: Mapped[str] = mapped_column(String(60), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(40), nullable=False)
    external_key: Mapped[str] = mapped_column(String(80), nullable=False)
    crm_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    crm_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    external_value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offen", server_default="offen")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))


class ErpOrderTransfer(Base):
    __tablename__ = "erp_uebertragungen"
    __table_args__ = (
        CheckConstraint(_in("status", TRANSFER_STATUSES), name="ck_erp_uebertragungen_status"),
        UniqueConstraint("order_id", name="uq_erp_uebertragungen_order"),
        UniqueConstraint("idempotency_key", name="uq_erp_uebertragungen_key"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    order_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("bestellungen.id", ondelete="RESTRICT"), nullable=False)
    idempotency_key: Mapped[str] = mapped_column(String(80), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="nicht_uebertragen")
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    external_reference: Mapped[str | None] = mapped_column(String(80))
    external_status: Mapped[str | None] = mapped_column(String(40))
    external_status_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    source: Mapped[str | None] = mapped_column(String(20))
    last_error: Mapped[str] = mapped_column(Text, nullable=False, default="")
    delivery_on: Mapped[date | None] = mapped_column(Date)
    delivery_note: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    delivery_status: Mapped[str] = mapped_column(String(40), nullable=False, default="")
    invoice_number: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    invoice_on: Mapped[date | None] = mapped_column(Date)
    invoice_status: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)
