from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.crm_catalog import TASK_PRIORITIES
from app.engagement_catalog import (
    AUDIENCE_KINDS,
    AUTOMATION_ACTIONS,
    AUTOMATION_STATUSES,
    AUTOMATION_TRIGGERS,
    CAMPAIGN_STATUSES,
    CAMPAIGN_TYPES,
    CARE_RULE_KINDS,
    EVENT_TRIGGERS,
    MESSAGE_CHANNELS,
    NOTIFICATION_TYPES,
    TIME_TRIGGERS,
)
from app.schemas.fields import choice, optional_text, parse_timestamp, required_text
from app.services.money import as_decimal, money


class CampaignWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    campaign_type: str
    account_owner: str | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    objective: str | None = None
    audience_kind: str
    segment_id: UUID | None = None
    channel: str
    budget: Decimal | None = None
    internal_note: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> str:
        return required_text(value, "Kampagnenname", 160)

    @field_validator("description", "objective", "internal_note", mode="before")
    @classmethod
    def clean_long(cls, value: object) -> str | None:
        return optional_text(value, "Text", 4000)

    @field_validator("campaign_type", mode="before")
    @classmethod
    def clean_type(cls, value: object) -> str:
        return choice(value, "Kampagnentyp", CAMPAIGN_TYPES)

    @field_validator("account_owner", mode="before")
    @classmethod
    def clean_owner(cls, value: object) -> str | None:
        return optional_text(value, "Verantwortliche Person", 120)

    @field_validator("audience_kind", mode="before")
    @classmethod
    def clean_audience(cls, value: object) -> str:
        return choice(value, "Zielgruppe", AUDIENCE_KINDS)

    @field_validator("channel", mode="before")
    @classmethod
    def clean_channel(cls, value: object) -> str:
        return choice(value, "Kommunikationskanal", MESSAGE_CHANNELS)

    @field_validator("budget", mode="before")
    @classmethod
    def clean_budget(cls, value: object) -> Decimal | None:
        if value is None or value == "":
            return None
        if isinstance(value, float):
            raise ValueError("Budget muss als Text übergeben werden.")
        if not isinstance(value, (Decimal, int, str)):
            raise ValueError("Budget ist ungültig.")
        amount = money(as_decimal(value))
        if amount < 0 or amount > Decimal("9999999999.99"):
            raise ValueError("Budget ist unplausibel.")
        return amount

    @model_validator(mode="after")
    def dates_and_segment(self) -> "CampaignWrite":
        if self.starts_on and self.ends_on and self.ends_on < self.starts_on:
            raise ValueError("Das Enddatum liegt vor dem Startdatum.")
        if self.audience_kind == "segment" and self.segment_id is None:
            raise ValueError("Für ein Kundensegment muss ein Segment gewählt werden.")
        if self.audience_kind != "segment":
            self.segment_id = None
        return self


class StatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, value: object) -> str:
        return choice(value, "Status", CAMPAIGN_STATUSES)


class AudienceAdd(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partner_id: UUID | None = None
    contact_id: UUID | None = None

    @model_validator(mode="after")
    def one_target(self) -> "AudienceAdd":
        if (self.partner_id is None) == (self.contact_id is None):
            raise ValueError("Es braucht genau einen Vertriebspartner oder eine Kontaktperson.")
        return self


class TemplateWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    subject: str
    body: str
    channel: str = "email"

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> str:
        return required_text(value, "Vorlagenname", 160)

    @field_validator("subject", mode="before")
    @classmethod
    def clean_subject(cls, value: object) -> str:
        return required_text(value, "Betreff", 200)

    @field_validator("body", mode="before")
    @classmethod
    def clean_body(cls, value: object) -> str:
        return required_text(value, "Nachrichtentext", 8000)

    @field_validator("channel", mode="before")
    @classmethod
    def clean_channel(cls, value: object) -> str:
        return choice(value, "Kommunikationskanal", MESSAGE_CHANNELS, default="email")


class TemplatePreview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    contact_id: UUID | None = None
    first_name: str | None = None
    last_name: str | None = None
    company_name: str | None = None
    job_title: str | None = None


class PreferenceWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preferred_channel: str = "telefon"
    email_marketing_allowed: bool = False
    marketing_rejected: bool = False
    consent_on: date | None = None
    consent_source: str | None = None
    consent_evidence: str | None = None
    revoked_on: date | None = None

    @field_validator("preferred_channel", mode="before")
    @classmethod
    def clean_channel(cls, value: object) -> str:
        return choice(value, "Bevorzugter Kanal", MESSAGE_CHANNELS, default="telefon")

    @field_validator("consent_source", mode="before")
    @classmethod
    def clean_source(cls, value: object) -> str | None:
        return optional_text(value, "Quelle der Einwilligung", 200)

    @field_validator("consent_evidence", mode="before")
    @classmethod
    def clean_evidence(cls, value: object) -> str | None:
        return optional_text(value, "Nachweis", 4000)

    @model_validator(mode="after")
    def consent_rules(self) -> "PreferenceWrite":
        if self.marketing_rejected and self.email_marketing_allowed:
            raise ValueError("Eine abgelehnte Marketingkommunikation kann nicht gleichzeitig erlaubt sein.")
        if self.email_marketing_allowed and (self.consent_on is None or not self.consent_source):
            raise ValueError("Eine E-Mail-Einwilligung braucht ein Datum und eine Quelle. Die Adresse allein genügt nicht.")
        if self.marketing_rejected and self.revoked_on is None:
            raise ValueError("Ein Widerruf braucht ein Datum.")
        return self


class CareRuleWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    rule_kind: str
    threshold_days: int
    is_active: bool = True
    create_tasks: bool = False
    task_title: str = "Partnerkontakt planen"
    account_owner: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> str:
        return required_text(value, "Regelname", 160)

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, value: object) -> str | None:
        return optional_text(value, "Beschreibung", 4000)

    @field_validator("rule_kind", mode="before")
    @classmethod
    def clean_kind(cls, value: object) -> str:
        return choice(value, "Betreuungsregel", CARE_RULE_KINDS)

    @field_validator("threshold_days", mode="before")
    @classmethod
    def clean_days(cls, value: object) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Die Anzahl Tage muss eine ganze Zahl sein.")
        if value < 1 or value > 3650:
            raise ValueError("Die Anzahl Tage muss zwischen 1 und 3650 liegen.")
        return value

    @field_validator("task_title", mode="before")
    @classmethod
    def clean_title(cls, value: object) -> str:
        return required_text(value, "Aufgabentitel", 200)

    @field_validator("account_owner", mode="before")
    @classmethod
    def clean_owner(cls, value: object) -> str | None:
        return optional_text(value, "Zuständige Person", 120)


class CareTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partner_id: UUID
    title: str
    due_at: datetime
    account_owner: str | None = None
    contact_id: UUID | None = None

    @field_validator("due_at", mode="before")
    @classmethod
    def clean_due(cls, value: object) -> datetime:
        return parse_timestamp(value, "Fälligkeit")

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: object) -> str:
        return required_text(value, "Aufgabentitel", 200)

    @field_validator("account_owner", mode="before")
    @classmethod
    def clean_owner(cls, value: object) -> str | None:
        return optional_text(value, "Zuständige Person", 120)


class ActionConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = None
    description: str | None = None
    priority: str | None = None
    due_days: int | None = None
    notification_type: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: object) -> str | None:
        return optional_text(value, "Titel", 200)

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, value: object) -> str | None:
        return optional_text(value, "Beschreibung", 4000)

    @field_validator("priority", mode="before")
    @classmethod
    def clean_priority(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        return choice(value, "Priorität", TASK_PRIORITIES)

    @field_validator("notification_type", mode="before")
    @classmethod
    def clean_notice(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        return choice(value, "Benachrichtigungstyp", NOTIFICATION_TYPES)

    @field_validator("due_days", mode="before")
    @classmethod
    def clean_due(cls, value: object) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Die Fälligkeit in Tagen muss eine ganze Zahl sein.")
        if value < 0 or value > 365:
            raise ValueError("Die Fälligkeit in Tagen ist unplausibel.")
        return value


class TriggerConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    days: int | None = None
    priority: str | None = None

    @field_validator("priority", mode="before")
    @classmethod
    def clean_priority(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        return choice(value, "Priorität", ("niedrig", "normal", "hoch", "kritisch"))

    @field_validator("days", mode="before")
    @classmethod
    def clean_days(cls, value: object) -> int | None:
        if value is None or value == "":
            return None
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Die Anzahl Tage muss eine ganze Zahl sein.")
        if value < 1 or value > 3650:
            raise ValueError("Die Anzahl Tage muss zwischen 1 und 3650 liegen.")
        return value


class AutomationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    trigger_type: str
    trigger_config: TriggerConfig = TriggerConfig()
    action_type: str
    action_config: ActionConfig = ActionConfig()
    account_owner: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> str:
        return required_text(value, "Name", 160)

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, value: object) -> str | None:
        return optional_text(value, "Beschreibung", 4000)

    @field_validator("trigger_type", mode="before")
    @classmethod
    def clean_trigger(cls, value: object) -> str:
        return choice(value, "Auslöser", AUTOMATION_TRIGGERS)

    @field_validator("action_type", mode="before")
    @classmethod
    def clean_action(cls, value: object) -> str:
        return choice(value, "Aktion", AUTOMATION_ACTIONS)

    @field_validator("account_owner", mode="before")
    @classmethod
    def clean_owner(cls, value: object) -> str | None:
        return optional_text(value, "Zuständige Person", 120)

    @model_validator(mode="after")
    def config_matches_trigger(self) -> "AutomationWrite":
        if self.trigger_type in TIME_TRIGGERS and self.trigger_config.days is None:
            raise ValueError("Ein zeitbasierter Auslöser braucht eine Anzahl Tage.")
        if self.trigger_type in EVENT_TRIGGERS:
            self.trigger_config.days = None
        if self.action_type == "create_task" and not self.action_config.title:
            raise ValueError("Die Aufgabe braucht einen Titel.")
        if self.action_type in {"notify_owner", "create_reminder"} and not self.action_config.title:
            raise ValueError("Die Benachrichtigung braucht einen Titel.")
        if self.action_type == "log_activity" and not self.action_config.title:
            raise ValueError("Die Aktivität braucht einen Titel.")
        return self


class AutomationStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, value: object) -> str:
        return choice(value, "Status", AUTOMATION_STATUSES)


class PreferenceSettingsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recipient_label: str
    task_reminders: bool = True
    service_alerts: bool = True
    deal_alerts: bool = True
    automation_errors: bool = True

    @field_validator("recipient_label", mode="before")
    @classmethod
    def clean_label(cls, value: object) -> str:
        return required_text(value, "Anzeigename", 120)


class CampaignRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    campaign_type: str
    account_owner: str | None
    starts_on: date | None
    ends_on: date | None
    objective: str | None
    audience_kind: str
    segment_id: UUID | None
    segment_name: str | None
    channel: str
    budget: str | None
    internal_note: str | None
    status: str
    allowed_statuses: list[str]
    activated_at: datetime | None
    audience_frozen: bool
    recipient_count: int
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class CampaignList(BaseModel):
    items: list[CampaignRead]
    total: int
    page: int
    page_size: int


class RecipientRead(BaseModel):
    contact_id: UUID
    partner_id: UUID | None
    name: str
    company_name: str
    job_title: str
    included: bool
    exclusion_reason: str | None


class AudienceMemberRead(BaseModel):
    id: UUID
    partner_id: UUID | None
    contact_id: UUID | None
    label: str


class AudiencePreview(BaseModel):
    frozen: bool
    notice: str
    delivery_notice: str
    consent_notice: str
    included_count: int
    excluded_count: int
    included: list[RecipientRead]
    excluded: list[RecipientRead]
    members: list[AudienceMemberRead]


class TemplateRead(BaseModel):
    id: UUID
    name: str
    subject: str
    body: str
    channel: str
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class TemplatePreviewRead(BaseModel):
    subject: str
    body: str
    delivery_notice: str


class PreferenceRead(BaseModel):
    contact_id: UUID
    preferred_channel: str
    email_marketing_allowed: bool
    marketing_rejected: bool
    consent_on: date | None
    consent_source: str | None
    consent_evidence: str | None
    revoked_on: date | None
    notice: str
    stored: bool


class CareRuleRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    rule_kind: str
    threshold_days: int
    is_active: bool
    create_tasks: bool
    task_title: str
    account_owner: str | None
    is_demo: bool
    match_count: int


class CareRow(BaseModel):
    partner_id: UUID
    company_name: str
    account_owner: str | None
    last_contact_at: datetime | None
    last_order_on: date | None
    open_tasks: int
    open_tickets: int
    open_deals: int
    next_activity_at: datetime | None
    contact_gap: bool
    order_gap: bool
    has_open_deals: bool
    has_open_complaints: bool


class CareList(BaseModel):
    items: list[CareRow]
    total: int
    page: int
    page_size: int
    contact_days: int
    order_days: int


class AutomationRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    trigger_type: str
    trigger_config: dict
    action_type: str
    action_config: dict
    status: str
    allowed_statuses: list[str]
    account_owner: str | None
    last_run_at: datetime | None
    run_count: int
    last_error: str | None
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class ExecutionRead(BaseModel):
    id: UUID
    rule_id: UUID
    dedupe_key: str
    status: str
    message: str | None
    error: str | None
    started_at: datetime
    finished_at: datetime
    task_id: UUID | None
    notification_id: UUID | None
    activity_id: UUID | None


class NotificationRead(BaseModel):
    id: UUID
    notification_type: str
    title: str
    body: str | None
    recipient_label: str
    href: str | None
    read_at: datetime | None
    is_demo: bool
    created_at: datetime


class NotificationList(BaseModel):
    items: list[NotificationRead]
    total: int
    unread: int
    page: int
    page_size: int
    identity_limited: bool
    notice: str


class NotificationSummary(BaseModel):
    unread: int
    identity_limited: bool
    notice: str


class PreferenceSettingsRead(BaseModel):
    recipient_label: str
    task_reminders: bool
    service_alerts: bool
    deal_alerts: bool
    automation_errors: bool
    notice: str


class EngagementSummary(BaseModel):
    active_campaigns: int
    care_tasks: int
    partners_without_contact: int
    contact_days: int
    overdue_tasks: int
    active_automations: int


class RunDueResult(BaseModel):
    attempts: int
    timezone: str
