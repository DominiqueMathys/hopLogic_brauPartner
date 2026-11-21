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

from app.crm_catalog import ACTIVITY_TYPES
from app.database import Base
from app.models.partner import utcnow, _in_clause


class Activity(Base):
    __tablename__ = "aktivitaeten"
    __table_args__ = (
        CheckConstraint(_in_clause("activity_type", ACTIVITY_TYPES), name="ck_aktivitaeten_type"),
        CheckConstraint(
            "contact_id IS NOT NULL OR partner_id IS NOT NULL",
            name="ck_aktivitaeten_link",
        ),
        UniqueConstraint("demo_key", name="uq_aktivitaeten_demo_key"),
        Index("ix_aktivitaeten_occurred_at", "occurred_at"),
        Index("ix_aktivitaeten_partner", "partner_id"),
        Index("ix_aktivitaeten_contact", "contact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    activity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    account_owner: Mapped[str | None] = mapped_column(String(120))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("kontakte.id", ondelete="RESTRICT"))
    partner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="RESTRICT"))
    event_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("feste.id", ondelete="RESTRICT"))
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
