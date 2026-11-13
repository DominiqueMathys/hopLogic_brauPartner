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

from app.crm_catalog import TASK_PRIORITIES, TASK_STATUSES, TASK_TYPES
from app.database import Base
from app.models.partner import utcnow, _in_clause


class Task(Base):
    __tablename__ = "aufgaben"
    __table_args__ = (
        CheckConstraint(_in_clause("status", TASK_STATUSES), name="ck_aufgaben_status"),
        CheckConstraint(_in_clause("priority", TASK_PRIORITIES), name="ck_aufgaben_priority"),
        CheckConstraint(_in_clause("task_type", TASK_TYPES), name="ck_aufgaben_type"),
        UniqueConstraint("demo_key", name="uq_aufgaben_demo_key"),
        Index("ix_aufgaben_due_at", "due_at"),
        Index("ix_aufgaben_status", "status"),
        Index("ix_aufgaben_owner", "account_owner"),
        Index("ix_aufgaben_partner", "partner_id"),
        Index("ix_aufgaben_contact", "contact_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    account_owner: Mapped[str | None] = mapped_column(String(120))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="normal")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="offen")
    task_type: Mapped[str] = mapped_column(String(20), nullable=False, default="intern")
    partner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="RESTRICT"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("kontakte.id", ondelete="RESTRICT"))
    activity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aktivitaeten.id", ondelete="RESTRICT"))
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("service_tickets.id", ondelete="RESTRICT"))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
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
