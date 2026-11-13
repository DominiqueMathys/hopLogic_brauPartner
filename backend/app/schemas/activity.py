from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.crm_catalog import ACTIVITY_TYPES, TASK_PRIORITIES, TASK_TYPES
from app.schemas.fields import choice, optional_text, parse_timestamp, required_text
from app.schemas.task import TaskRead


class ActivityWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    activity_type: str = ""
    title: str = ""
    description: str | None = None
    occurred_at: datetime | None = None
    account_owner: str | None = None
    contact_id: UUID | None = None
    partner_id: UUID | None = None

    @field_validator("activity_type", mode="before")
    @classmethod
    def clean_type(cls, value: object) -> str:
        return choice(value, "Aktivitätstyp", ACTIVITY_TYPES)

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

    @field_validator("occurred_at", mode="before")
    @classmethod
    def clean_occurred(cls, value: object) -> datetime:
        if value is None or value == "":
            raise ValueError("Datum und Uhrzeit sind erforderlich.")
        return parse_timestamp(value, "Datum und Uhrzeit")

    @model_validator(mode="after")
    def needs_a_link(self) -> "ActivityWrite":
        if self.contact_id is None and self.partner_id is None:
            raise ValueError("Die Aktivität braucht einen Kontakt oder ein Unternehmen.")
        return self


class FollowUpWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    title: str = ""
    description: str | None = None
    account_owner: str | None = None
    due_at: datetime | None = None
    priority: str = "normal"
    task_type: str = "anruf"

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: object) -> str:
        return required_text(value, "Aufgabentitel", 200)

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, value: object) -> str | None:
        return optional_text(value, "Aufgabenbeschreibung", 4000)

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

    @field_validator("task_type", mode="before")
    @classmethod
    def clean_type(cls, value: object) -> str:
        return choice(value, "Aufgabentyp", TASK_TYPES, default="anruf")


class NoteWithTaskWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    activity: ActivityWrite
    create_task: bool = False
    task: FollowUpWrite | None = None

    @model_validator(mode="after")
    def task_matches_checkbox(self) -> "NoteWithTaskWrite":
        if self.create_task and self.task is None:
            raise ValueError("Die Folgeaufgabe ist unvollständig.")
        if not self.create_task:
            self.task = None
        return self


class ActivityRead(BaseModel):
    id: UUID
    activity_type: str
    title: str
    description: str | None
    occurred_at: datetime
    account_owner: str | None
    contact_id: UUID | None
    partner_id: UUID | None
    contact_name: str | None
    company_name: str | None
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ActivityList(BaseModel):
    items: list[ActivityRead]
    total: int
    page: int
    page_size: int


class NoteWithTaskRead(BaseModel):
    activity: ActivityRead
    task: TaskRead | None
