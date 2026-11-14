import uuid
from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.partner_catalog import PARTNER_STATUSES, PARTNER_TYPES, PRIORITIES


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _in_clause(column: str, values: tuple[str, ...]) -> str:
    quoted = ", ".join(f"'{value}'" for value in values)
    return f"{column} IN ({quoted})"


class Partner(Base):
    __tablename__ = "vertriebspartner"
    __table_args__ = (
        CheckConstraint(_in_clause("partner_type", PARTNER_TYPES), name="ck_vertriebspartner_partner_type"),
        CheckConstraint(_in_clause("status", PARTNER_STATUSES), name="ck_vertriebspartner_status"),
        CheckConstraint(_in_clause("priority", PRIORITIES), name="ck_vertriebspartner_priority"),
        UniqueConstraint("demo_key", name="uq_vertriebspartner_demo_key"),
        Index("ix_vertriebspartner_company_name", "company_name"),
        Index("ix_vertriebspartner_city", "city"),
        Index("ix_vertriebspartner_status", "status"),
        Index("ix_vertriebspartner_created_at", "created_at"),
        Index(
            "uq_vertriebspartner_erp_customer_number",
            text("lower(erp_customer_number)"),
            unique=True,
            postgresql_where=text("erp_customer_number IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    company_name: Mapped[str] = mapped_column(String(200), nullable=False)
    erp_customer_number: Mapped[str | None] = mapped_column(String(40))
    partner_type: Mapped[str] = mapped_column(String(40), nullable=False)
    industry: Mapped[str | None] = mapped_column(String(120))
    street: Mapped[str | None] = mapped_column(String(200))
    postal_code: Mapped[str | None] = mapped_column(String(12))
    city: Mapped[str | None] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(120))
    country: Mapped[str] = mapped_column(String(80), nullable=False, default="Schweiz")
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(254))
    website: Mapped[str | None] = mapped_column(String(300))
    status: Mapped[str] = mapped_column(String(40), nullable=False)
    account_owner: Mapped[str | None] = mapped_column(String(120))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))
    acquisition_source: Mapped[str | None] = mapped_column(String(120))
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    first_contact_on: Mapped[date | None] = mapped_column(Date)
    notes: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=utcnow,
        server_default=func.now(),
        onupdate=utcnow,
    )

    @property
    def last_contact_at(self) -> datetime | None:
        from app.services.timeline import partner_last_contact

        return partner_last_contact(self)

    @property
    def next_activity_on(self) -> date | None:
        from app.services.timeline import partner_next_activity

        return partner_next_activity(self)
