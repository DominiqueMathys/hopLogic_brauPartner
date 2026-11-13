from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.crm_catalog import (
    CHANNELS,
    CONTACT_STATUSES,
    LANGUAGES,
    LEAD_STATUSES,
    LIFECYCLE_PHASES,
    PROCESSING_BASES,
)
from app.schemas.fields import choice, collapse, optional_text, required_text
from app.schemas.partner import EMAIL_PATTERN, PHONE_PATTERN

NAME_LIMIT = 80


class CompanyLinkWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partner_id: UUID
    is_primary: bool = False


class ContactWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    first_name: str = ""
    last_name: str = ""
    job_title: str | None = None
    email: str | None = None
    phone: str | None = None
    mobile: str | None = None
    account_owner: str | None = None
    preferred_language: str = "de"
    preferred_channel: str = "telefon"
    lifecycle_phase: str = ""
    lead_status: str = "keiner"
    status: str = "aktiv"
    notes: str | None = None
    processing_basis: str = "nicht_dokumentiert"
    processing_basis_note: str | None = None
    companies: list[CompanyLinkWrite] = []

    @field_validator("first_name", mode="before")
    @classmethod
    def clean_first_name(cls, value: object) -> str:
        return required_text(value, "Vorname", NAME_LIMIT)

    @field_validator("last_name", mode="before")
    @classmethod
    def clean_last_name(cls, value: object) -> str:
        return required_text(value, "Nachname", NAME_LIMIT)

    @field_validator("job_title", mode="before")
    @classmethod
    def clean_job_title(cls, value: object) -> str | None:
        return optional_text(value, "Funktion", 120)

    @field_validator("account_owner", mode="before")
    @classmethod
    def clean_owner(cls, value: object) -> str | None:
        return optional_text(value, "Betreuungsperson", 120)

    @field_validator("preferred_language", mode="before")
    @classmethod
    def clean_language(cls, value: object) -> str:
        return choice(value, "Bevorzugte Sprache", LANGUAGES, default="de")

    @field_validator("preferred_channel", mode="before")
    @classmethod
    def clean_channel(cls, value: object) -> str:
        return choice(value, "Bevorzugter Kommunikationskanal", CHANNELS, default="telefon")

    @field_validator("lifecycle_phase", mode="before")
    @classmethod
    def clean_lifecycle(cls, value: object) -> str:
        return choice(value, "Lifecycle-Phase", LIFECYCLE_PHASES)

    @field_validator("lead_status", mode="before")
    @classmethod
    def clean_lead_status(cls, value: object) -> str:
        return choice(value, "Leadstatus", LEAD_STATUSES, default="keiner")

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, value: object) -> str:
        return choice(value, "Kontaktstatus", CONTACT_STATUSES, default="aktiv")

    @field_validator("processing_basis", mode="before")
    @classmethod
    def clean_basis(cls, value: object) -> str:
        return choice(value, "Rechtsgrundlage", PROCESSING_BASES, default="nicht_dokumentiert")

    @field_validator("notes", "processing_basis_note", mode="before")
    @classmethod
    def clean_notes(cls, value: object, info) -> str | None:
        label = "Interne Bemerkungen" if info.field_name == "notes" else "Dokumentation der Rechtsgrundlage"
        return optional_text(value, label, 4000)

    @field_validator("email", mode="before")
    @classmethod
    def clean_email(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("E-Mail ist ungültig.")
        cleaned = value.strip().lower()
        if not cleaned:
            return None
        if len(cleaned) > 254 or not EMAIL_PATTERN.fullmatch(cleaned):
            raise ValueError("E-Mail ist ungültig.")
        return cleaned

    @field_validator("phone", "mobile", mode="before")
    @classmethod
    def clean_phone(cls, value: object, info) -> str | None:
        label = "Telefonnummer" if info.field_name == "phone" else "Mobilnummer"
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{label} ist ungültig.")
        cleaned = collapse(value)
        if not cleaned:
            return None
        if not PHONE_PATTERN.fullmatch(cleaned):
            raise ValueError(f"{label} ist ungültig.")
        return cleaned

    @model_validator(mode="after")
    def companies_are_unique(self) -> "ContactWrite":
        seen: set[UUID] = set()
        for link in self.companies:
            if link.partner_id in seen:
                raise ValueError("Dasselbe Unternehmen ist mehrfach angegeben.")
            seen.add(link.partner_id)
        return self


class ContactUpdate(ContactWrite):
    companies: list[CompanyLinkWrite] = []

    @model_validator(mode="after")
    def ignore_companies_on_update(self) -> "ContactUpdate":
        self.companies = []
        return self


class CompanyLinkRead(BaseModel):
    partner_id: UUID
    company_name: str
    city: str | None
    is_primary: bool
    partner_archived: bool


class ContactRead(BaseModel):
    id: UUID
    first_name: str
    last_name: str
    job_title: str | None
    email: str | None
    phone: str | None
    mobile: str | None
    account_owner: str | None
    preferred_language: str
    preferred_channel: str
    lifecycle_phase: str
    lead_status: str
    status: str
    notes: str | None
    processing_basis: str
    processing_basis_note: str | None
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    last_contact_at: datetime | None
    companies: list[CompanyLinkRead]


class ContactList(BaseModel):
    items: list[ContactRead]
    total: int
    page: int
    page_size: int


class CompanyOption(BaseModel):
    partner_id: UUID
    company_name: str
    city: str | None


class ContactFilterOptions(BaseModel):
    companies: list[CompanyOption]
    account_owners: list[str]
