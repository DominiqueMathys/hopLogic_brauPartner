import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
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

from app.crm_catalog import (
    CHANNELS,
    CONTACT_STATUSES,
    LANGUAGES,
    LEAD_STATUSES,
    LIFECYCLE_PHASES,
    PROCESSING_BASES,
)
from app.database import Base
from app.models.partner import utcnow, _in_clause


class Contact(Base):
    __tablename__ = "kontakte"
    __table_args__ = (
        CheckConstraint(_in_clause("status", CONTACT_STATUSES), name="ck_kontakte_status"),
        CheckConstraint(_in_clause("lead_status", LEAD_STATUSES), name="ck_kontakte_lead_status"),
        CheckConstraint(_in_clause("lifecycle_phase", LIFECYCLE_PHASES), name="ck_kontakte_lifecycle"),
        CheckConstraint(_in_clause("preferred_language", LANGUAGES), name="ck_kontakte_language"),
        CheckConstraint(_in_clause("preferred_channel", CHANNELS), name="ck_kontakte_channel"),
        CheckConstraint(_in_clause("processing_basis", PROCESSING_BASES), name="ck_kontakte_processing_basis"),
        UniqueConstraint("demo_key", name="uq_kontakte_demo_key"),
        Index("ix_kontakte_last_name", "last_name"),
        Index("ix_kontakte_email", "email"),
        Index("ix_kontakte_account_owner", "account_owner"),
        Index(
            "uq_kontakte_email_active",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("email IS NOT NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    job_title: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str | None] = mapped_column(String(40))
    mobile: Mapped[str | None] = mapped_column(String(40))
    account_owner: Mapped[str | None] = mapped_column(String(120))
    preferred_language: Mapped[str] = mapped_column(String(8), nullable=False, default="de")
    preferred_channel: Mapped[str] = mapped_column(String(20), nullable=False, default="telefon")
    lifecycle_phase: Mapped[str] = mapped_column(String(20), nullable=False)
    lead_status: Mapped[str] = mapped_column(String(20), nullable=False, default="keiner")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="aktiv")
    notes: Mapped[str | None] = mapped_column(Text)
    processing_basis: Mapped[str] = mapped_column(String(40), nullable=False, default="nicht_dokumentiert")
    processing_basis_note: Mapped[str | None] = mapped_column(Text)
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


class CompanyContact(Base):
    __tablename__ = "unternehmen_kontakte"
    __table_args__ = (
        UniqueConstraint("partner_id", "contact_id", name="uq_unternehmen_kontakte_pair"),
        Index("ix_unternehmen_kontakte_contact", "contact_id"),
        Index(
            "uq_unternehmen_kontakte_primary",
            "partner_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    partner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vertriebspartner.id", ondelete="RESTRICT"),
        nullable=False,
    )
    contact_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("kontakte.id", ondelete="RESTRICT"),
        nullable=False,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
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
