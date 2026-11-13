from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator

from app.crm_catalog import OPEN_TASK_STATUSES, TASK_PRIORITIES, TASK_STATUSES, TASK_TYPES
from app.schemas.fields import choice, optional_text, parse_timestamp, required_text


class TaskWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    title: str = ""
    description: str | None = None
    account_owner: str | None = None
    due_at: datetime | None = None
    priority: str = "normal"
    status: str = "offen"
    task_type: str = "intern"
    partner_id: UUID | None = None
    contact_id: UUID | None = None
    activity_id: UUID | None = None

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: object) -> str:
        return required_text(value, "Titel", 200)

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, value: object) -> str | None:
        return optional_text(value, "Beschreibung", 4000)

    @field_validator("account_owner", mode="before")
    @classmethod
    def clean_owner(cls, value: object) -> str | None:
        return optional_text(value, "Zuständige Person", 120)

    @field_validator("due_at", mode="before")
    @classmethod
    def clean_due(cls, value: object) -> datetime:
        if value is None or value == "":
            raise ValueError("Fälligkeit ist erforderlich.")
        return parse_timestamp(value, "Fälligkeit")

    @field_validator("priority", mode="before")
    @classmethod
    def clean_priority(cls, value: object) -> str:
        return choice(value, "Priorität", TASK_PRIORITIES, default="normal")

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, value: object) -> str:
        return choice(value, "Aufgabenstatus", TASK_STATUSES, default="offen")

    @field_validator("task_type", mode="before")
    @classmethod
    def clean_type(cls, value: object) -> str:
        return choice(value, "Aufgabentyp", TASK_TYPES, default="intern")


class TaskRead(BaseModel):
    id: UUID
    title: str
    description: str | None
    account_owner: str | None
    due_at: datetime
    priority: str
    status: str
    task_type: str
    partner_id: UUID | None
    contact_id: UUID | None
    activity_id: UUID | None
    company_name: str | None
    contact_name: str | None
    completed_at: datetime | None
    is_demo: bool
    is_overdue: bool
    is_due_soon: bool
    is_urgent: bool
    created_at: datetime
    updated_at: datetime


class TaskList(BaseModel):
    items: list[TaskRead]
    total: int
    page: int
    page_size: int


class TaskSummary(BaseModel):
    open: int
    overdue: int
    due_soon: int
    urgent: int
    open_demo: int


class TaskFilterOptions(BaseModel):
    account_owners: list[str]


def open_status(status: str) -> bool:
    return status in OPEN_TASK_STATUSES
