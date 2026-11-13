from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.service_catalog import (
    FIELD_OPERATORS,
    RESOLUTION_CODES,
    SEGMENT_MATCH_MODES,
    TICKET_CATEGORIES,
    TICKET_PRIORITIES,
    TICKET_STATUSES,
)


def _text(value: str, limit: int) -> str:
    cleaned = " ".join(value.split())
    if not cleaned:
        raise ValueError("Pflichtfeld.")
    if len(cleaned) > limit:
        raise ValueError(f"Höchstens {limit} Zeichen.")
    return cleaned


def _optional(value: str | None, limit: int) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    if not cleaned:
        return None
    if len(cleaned) > limit:
        raise ValueError(f"Höchstens {limit} Zeichen.")
    return cleaned


def _choice(value: str, allowed: tuple[str, ...]) -> str:
    if value not in allowed:
        raise ValueError("Unzulässiger Wert.")
    return value


class TicketWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    subject: str
    category: str
    description: str
    partner_id: UUID
    priority: str
    contact_id: UUID | None = None
    order_id: UUID | None = None
    product_ids: list[UUID] = Field(default_factory=list, max_length=20)
    account_owner: str | None = None
    due_on: date | None = None
    internal_remark: str | None = None

    @field_validator("subject")
    @classmethod
    def subject_ok(cls, value: str) -> str:
        return _text(value, 200)

    @field_validator("description")
    @classmethod
    def description_ok(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Pflichtfeld.")
        if len(cleaned) > 4000:
            raise ValueError("Höchstens 4000 Zeichen.")
        return cleaned

    @field_validator("category")
    @classmethod
    def category_ok(cls, value: str) -> str:
        return _choice(value, TICKET_CATEGORIES)

    @field_validator("priority")
    @classmethod
    def priority_ok(cls, value: str) -> str:
        return _choice(value, TICKET_PRIORITIES)

    @field_validator("account_owner", "internal_remark")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return _optional(value, 2000)


class TicketUpdate(TicketWrite):
    pass


class Actor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    changed_by: str | None = None

    @field_validator("changed_by")
    @classmethod
    def actor_ok(cls, value: str | None) -> str | None:
        return _optional(value, 120)


class StatusChange(Actor):
    status: str

    @field_validator("status")
    @classmethod
    def status_ok(cls, value: str) -> str:
        return _choice(value, TICKET_STATUSES)


class PriorityChange(Actor):
    priority: str

    @field_validator("priority")
    @classmethod
    def priority_ok(cls, value: str) -> str:
        return _choice(value, TICKET_PRIORITIES)


class AssignChange(Actor):
    account_owner: str | None = None

    @field_validator("account_owner")
    @classmethod
    def owner_ok(cls, value: str | None) -> str | None:
        return _optional(value, 120)


class NoteCreate(Actor):
    note: str

    @field_validator("note")
    @classmethod
    def note_ok(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Pflichtfeld.")
        if len(cleaned) > 4000:
            raise ValueError("Höchstens 4000 Zeichen.")
        return cleaned


class ResolveCreate(Actor):
    code: str
    note: str | None = None

    @field_validator("code")
    @classmethod
    def code_ok(cls, value: str) -> str:
        return _choice(value, RESOLUTION_CODES)

    @field_validator("note")
    @classmethod
    def note_ok(cls, value: str | None) -> str | None:
        return _optional(value, 2000)


class TicketTaskCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    due_at: datetime
    priority: str = "normal"
    description: str | None = None
    account_owner: str | None = None
    changed_by: str | None = None

    @field_validator("title")
    @classmethod
    def title_ok(cls, value: str) -> str:
        return _text(value, 200)

    @field_validator("priority")
    @classmethod
    def priority_ok(cls, value: str) -> str:
        return _choice(value, ("niedrig", "normal", "hoch", "dringend"))

    @field_validator("description", "account_owner", "changed_by")
    @classmethod
    def optional_text(cls, value: str | None) -> str | None:
        return _optional(value, 2000)


class TicketEventRead(BaseModel):
    id: UUID
    event_type: str
    from_value: str | None
    to_value: str | None
    note: str | None
    changed_by: str | None
    task_id: UUID | None
    changed_at: datetime


class TicketAttachmentRead(BaseModel):
    id: UUID
    original_name: str
    content_type: str
    size_bytes: int
    created_at: datetime


class TicketResolutionRead(BaseModel):
    id: UUID
    code: str
    note: str | None
    recorded_by: str | None
    recorded_at: datetime


class TicketProductRead(BaseModel):
    id: UUID
    name: str
    sku: str


class TicketTaskRead(BaseModel):
    id: UUID
    title: str
    status: str
    priority: str
    due_at: datetime
    account_owner: str | None


class TicketRead(BaseModel):
    id: UUID
    ticket_number: str
    subject: str
    category: str
    priority: str
    status: str
    partner_id: UUID
    company_name: str
    contact_id: UUID | None
    contact_name: str | None
    account_owner: str | None
    due_on: date | None
    is_overdue: bool
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class TicketDetail(TicketRead):
    description: str
    order_id: UUID | None
    order_number: str | None
    internal_remark: str | None
    resolved_at: datetime | None
    closed_at: datetime | None
    products: list[TicketProductRead]
    events: list[TicketEventRead]
    attachments: list[TicketAttachmentRead]
    resolutions: list[TicketResolutionRead]
    tasks: list[TicketTaskRead]
    allowed_statuses: list[str]
    can_resolve: bool
    can_close: bool
    can_reopen: bool


class TicketList(BaseModel):
    items: list[TicketRead]
    total: int
    page: int
    page_size: int


class TicketSummary(BaseModel):
    open_count: int
    critical_count: int
    resolved_count: int
    overdue_count: int
    open_complaints: int
    partners_with_complaints: int
    overdue_service_tasks: int
    average_hours: Decimal | None
    duration_sample: int
    duration_definition: str
    by_category: dict[str, int]
    by_priority: dict[str, int]
    by_status: dict[str, int]


class PartnerAnalysis(BaseModel):
    partner_id: UUID
    order_count: int
    order_volume: Decimal
    average_order_value: Decimal | None
    last_order_on: date | None
    open_deals: int
    pipeline_value: Decimal
    open_tickets: int
    closed_tickets: int
    last_complaint_on: date | None
    last_activity_on: date | None
    volume_basis: str


class ConditionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field_name: str
    operator: str
    value: str = ""

    @field_validator("field_name")
    @classmethod
    def field_ok(cls, value: str) -> str:
        if value not in FIELD_OPERATORS:
            raise ValueError("Unzulässiges Feld.")
        return value

    @field_validator("operator")
    @classmethod
    def operator_ok(cls, value: str, info: Any) -> str:
        field_name = info.data.get("field_name")
        allowed = FIELD_OPERATORS.get(field_name, ())
        if value not in allowed:
            raise ValueError("Unzulässiger Operator für dieses Feld.")
        return value

    @field_validator("value")
    @classmethod
    def value_ok(cls, value: str) -> str:
        cleaned = value.strip()
        if len(cleaned) > 120:
            raise ValueError("Höchstens 120 Zeichen.")
        return cleaned


class SegmentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    match_mode: str = "all"
    conditions: list[ConditionWrite] = Field(min_length=1, max_length=12)

    @field_validator("name")
    @classmethod
    def name_ok(cls, value: str) -> str:
        return _text(value, 120)

    @field_validator("description")
    @classmethod
    def description_ok(cls, value: str | None) -> str | None:
        return _optional(value, 2000)

    @field_validator("match_mode")
    @classmethod
    def mode_ok(cls, value: str) -> str:
        return _choice(value, SEGMENT_MATCH_MODES)


class ConditionRead(BaseModel):
    id: UUID
    field_name: str
    operator: str
    value: str
    position: int


class SegmentRead(BaseModel):
    id: UUID
    name: str
    description: str | None
    match_mode: str
    partner_count: int
    is_demo: bool
    conditions: list[ConditionRead]
    created_at: datetime
    updated_at: datetime


class SegmentPartner(BaseModel):
    id: UUID
    company_name: str
    city: str
    partner_type: str
    status: str
    order_count: int
    order_volume: Decimal
    open_tickets: int
