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
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.engagement_catalog import (
    AUDIENCE_KINDS,
    AUTOMATION_ACTIONS,
    AUTOMATION_STATUSES,
    AUTOMATION_TRIGGERS,
    CAMPAIGN_STATUSES,
    CAMPAIGN_TYPES,
    CARE_RULE_KINDS,
    EXECUTION_STATUSES,
    MESSAGE_CHANNELS,
    NOTIFICATION_TYPES,
)
from app.models.partner import utcnow, _in_clause


class MarketingCampaign(Base):
    __tablename__ = "kampagnen"
    __table_args__ = (
        CheckConstraint(_in_clause("campaign_type", CAMPAIGN_TYPES), name="ck_kampagnen_type"),
        CheckConstraint(_in_clause("status", CAMPAIGN_STATUSES), name="ck_kampagnen_status"),
        CheckConstraint(_in_clause("audience_kind", AUDIENCE_KINDS), name="ck_kampagnen_audience"),
        CheckConstraint(_in_clause("channel", MESSAGE_CHANNELS), name="ck_kampagnen_channel"),
        CheckConstraint("ends_on IS NULL OR starts_on IS NULL OR ends_on >= starts_on", name="ck_kampagnen_dates"),
        UniqueConstraint("demo_key", name="uq_kampagnen_demo_key"),
        Index("ix_kampagnen_status", "status"),
        Index("ix_kampagnen_owner", "account_owner"),
        Index("ix_kampagnen_type", "campaign_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    campaign_type: Mapped[str] = mapped_column(String(40), nullable=False)
    account_owner: Mapped[str | None] = mapped_column(String(120))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))
    starts_on: Mapped[date | None] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    objective: Mapped[str | None] = mapped_column(Text)
    audience_kind: Mapped[str] = mapped_column(String(20), nullable=False)
    segment_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("kundensegmente.id", ondelete="RESTRICT"))
    channel: Mapped[str] = mapped_column(String(20), nullable=False)
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    internal_note: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="entwurf")
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class CampaignAudienceMember(Base):
    __tablename__ = "kampagnen_zielgruppe"
    __table_args__ = (
        CheckConstraint(
            "(partner_id IS NOT NULL AND contact_id IS NULL) OR (partner_id IS NULL AND contact_id IS NOT NULL)",
            name="ck_kampagnen_zielgruppe_target",
        ),
        Index("ix_kampagnen_zielgruppe_campaign", "campaign_id"),
        Index("uq_kampagnen_zielgruppe_partner", "campaign_id", "partner_id", unique=True, postgresql_where=text("partner_id IS NOT NULL")),
        Index("uq_kampagnen_zielgruppe_contact", "campaign_id", "contact_id", unique=True, postgresql_where=text("contact_id IS NOT NULL")),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kampagnen.id", ondelete="CASCADE"), nullable=False)
    partner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="RESTRICT"))
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("kontakte.id", ondelete="RESTRICT"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())


class CampaignRecipient(Base):
    __tablename__ = "kampagnen_empfaenger"
    __table_args__ = (
        UniqueConstraint("campaign_id", "contact_id", name="uq_kampagnen_empfaenger"),
        Index("ix_kampagnen_empfaenger_campaign", "campaign_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    campaign_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kampagnen.id", ondelete="CASCADE"), nullable=False)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kontakte.id", ondelete="RESTRICT"), nullable=False)
    partner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="RESTRICT"))
    first_name: Mapped[str] = mapped_column(String(80), nullable=False)
    last_name: Mapped[str] = mapped_column(String(80), nullable=False)
    company_name: Mapped[str] = mapped_column(String(160), nullable=False, default="", server_default="")
    job_title: Mapped[str] = mapped_column(String(120), nullable=False, default="", server_default="")
    included: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    exclusion_reason: Mapped[str | None] = mapped_column(String(200))
    frozen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())


class MessageTemplate(Base):
    __tablename__ = "nachrichtenvorlagen"
    __table_args__ = (
        CheckConstraint(_in_clause("channel", MESSAGE_CHANNELS), name="ck_vorlagen_channel"),
        UniqueConstraint("demo_key", name="uq_vorlagen_demo_key"),
        Index("ix_vorlagen_name", "name"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    subject: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[str] = mapped_column(String(20), nullable=False, default="email")
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class CommunicationPreference(Base):
    __tablename__ = "kommunikationspraeferenzen"
    __table_args__ = (
        CheckConstraint(_in_clause("preferred_channel", MESSAGE_CHANNELS), name="ck_praeferenz_channel"),
        CheckConstraint(
            "NOT (email_marketing_allowed AND marketing_rejected)",
            name="ck_praeferenz_consent",
        ),
        UniqueConstraint("contact_id", name="uq_praeferenz_contact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("kontakte.id", ondelete="RESTRICT"), nullable=False)
    preferred_channel: Mapped[str] = mapped_column(String(20), nullable=False, default="telefon")
    email_marketing_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    marketing_rejected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    consent_on: Mapped[date | None] = mapped_column(Date)
    consent_source: Mapped[str | None] = mapped_column(String(200))
    consent_evidence: Mapped[str | None] = mapped_column(Text)
    revoked_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class CustomerCareRule(Base):
    __tablename__ = "betreuungsregeln"
    __table_args__ = (
        CheckConstraint(_in_clause("rule_kind", CARE_RULE_KINDS), name="ck_betreuung_kind"),
        CheckConstraint("threshold_days >= 1 AND threshold_days <= 3650", name="ck_betreuung_days"),
        UniqueConstraint("demo_key", name="uq_betreuung_demo_key"),
        Index("ix_betreuung_active", "is_active"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rule_kind: Mapped[str] = mapped_column(String(40), nullable=False)
    threshold_days: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    create_tasks: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    task_title: Mapped[str] = mapped_column(String(200), nullable=False, default="Partnerkontakt planen")
    account_owner: Mapped[str | None] = mapped_column(String(120))
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class CareExecution(Base):
    __tablename__ = "betreuungs_ausfuehrungen"
    __table_args__ = (
        CheckConstraint(_in_clause("status", EXECUTION_STATUSES), name="ck_betreuung_ausfuehrung_status"),
        Index(
            "uq_betreuung_ausfuehrung_erfolg",
            "rule_id",
            "dedupe_key",
            unique=True,
            postgresql_where=text("status = 'erfolg'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("betreuungsregeln.id", ondelete="CASCADE"), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aufgaben.id", ondelete="SET NULL"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())


class AutomationRule(Base):
    __tablename__ = "automatisierungen"
    __table_args__ = (
        CheckConstraint(_in_clause("trigger_type", AUTOMATION_TRIGGERS), name="ck_automatisierung_trigger"),
        CheckConstraint(_in_clause("action_type", AUTOMATION_ACTIONS), name="ck_automatisierung_action"),
        CheckConstraint(_in_clause("status", AUTOMATION_STATUSES), name="ck_automatisierung_status"),
        UniqueConstraint("demo_key", name="uq_automatisierung_demo_key"),
        Index("ix_automatisierung_status", "status"),
        Index("ix_automatisierung_trigger", "trigger_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    trigger_type: Mapped[str] = mapped_column(String(40), nullable=False)
    trigger_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    action_type: Mapped[str] = mapped_column(String(40), nullable=False)
    action_config: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="entwurf")
    account_owner: Mapped[str | None] = mapped_column(String(120))
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    run_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")
    last_error: Mapped[str | None] = mapped_column(Text)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)


class AutomationExecution(Base):
    __tablename__ = "automatisierung_ausfuehrungen"
    __table_args__ = (
        CheckConstraint(_in_clause("status", EXECUTION_STATUSES), name="ck_ausfuehrung_status"),
        Index("ix_ausfuehrung_rule", "rule_id"),
        Index(
            "uq_ausfuehrung_erfolg",
            "rule_id",
            "dedupe_key",
            unique=True,
            postgresql_where=text("status = 'erfolg'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rule_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("automatisierungen.id", ondelete="CASCADE"), nullable=False)
    dedupe_key: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    message: Mapped[str | None] = mapped_column(Text)
    error: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    finished_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aufgaben.id", ondelete="SET NULL"))
    notification_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    activity_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aktivitaeten.id", ondelete="SET NULL"))


class Notification(Base):
    __tablename__ = "benachrichtigungen"
    __table_args__ = (
        CheckConstraint(_in_clause("notification_type", NOTIFICATION_TYPES), name="ck_benachrichtigung_type"),
        UniqueConstraint("demo_key", name="uq_benachrichtigung_demo_key"),
        Index("ix_benachrichtigung_recipient", "recipient_label"),
        Index("ix_benachrichtigung_read", "read_at"),
        Index("ix_benachrichtigung_type", "notification_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    notification_type: Mapped[str] = mapped_column(String(40), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    recipient_label: Mapped[str] = mapped_column(String(120), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("benutzer.id", ondelete="SET NULL"))
    href: Mapped[str | None] = mapped_column(String(200))
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    task_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("aufgaben.id", ondelete="SET NULL"))
    partner_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("vertriebspartner.id", ondelete="SET NULL"))
    deal_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    ticket_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    automation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    is_demo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=text("false"))
    demo_key: Mapped[str | None] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now())


class NotificationPreference(Base):
    __tablename__ = "benachrichtigungseinstellungen"
    __table_args__ = (UniqueConstraint("recipient_label", name="uq_benachrichtigung_empfaenger"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    recipient_label: Mapped[str] = mapped_column(String(120), nullable=False)
    task_reminders: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    service_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    deal_alerts: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    automation_errors: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=text("true"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=utcnow, server_default=func.now(), onupdate=utcnow)
