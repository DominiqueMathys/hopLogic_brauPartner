import re
from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.partner_catalog import PARTNER_STATUSES, PARTNER_TYPES, PRIORITIES

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
WEBSITE_PATTERN = re.compile(r"^https?://[^\s]+$", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"^[0-9+()\s./-]{6,40}$")
POSTAL_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-]{2,11}$")
ERP_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-/]{0,39}$")


def _collapse(value: str) -> str:
    return " ".join(value.split())


class PartnerWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    company_name: str = ""
    erp_customer_number: str | None = None
    partner_type: str = ""
    industry: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    region: str | None = None
    country: str = "Schweiz"
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    status: str = ""
    account_owner: str | None = None
    acquisition_source: str | None = None
    priority: str = "normal"
    first_contact_on: date | None = None
    notes: str | None = None

    @field_validator("company_name", mode="before")
    @classmethod
    def clean_company_name(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Unternehmensname ist erforderlich.")
        cleaned = _collapse(value)
        if not cleaned:
            raise ValueError("Unternehmensname ist erforderlich.")
        if len(cleaned) > 200:
            raise ValueError("Unternehmensname darf höchstens 200 Zeichen haben.")
        return cleaned

    @field_validator("partner_type", mode="before")
    @classmethod
    def clean_partner_type(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Partnertyp ist erforderlich.")
        cleaned = value.strip()
        if cleaned not in PARTNER_TYPES:
            raise ValueError("Partnertyp ist ungültig.")
        return cleaned

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, value: object) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Partnerstatus ist erforderlich.")
        cleaned = value.strip()
        if cleaned not in PARTNER_STATUSES:
            raise ValueError("Partnerstatus ist ungültig.")
        return cleaned

    @field_validator("priority", mode="before")
    @classmethod
    def clean_priority(cls, value: object) -> str:
        if value is None or value == "":
            return "normal"
        if not isinstance(value, str) or value.strip() not in PRIORITIES:
            raise ValueError("Priorität ist ungültig.")
        return value.strip()

    @field_validator("country", mode="before")
    @classmethod
    def clean_country(cls, value: object) -> str:
        if not isinstance(value, str):
            raise ValueError("Land ist erforderlich.")
        cleaned = _collapse(value)
        if not cleaned:
            raise ValueError("Land ist erforderlich.")
        if len(cleaned) > 80:
            raise ValueError("Land darf höchstens 80 Zeichen haben.")
        return cleaned

    @field_validator("industry", "street", "city", "region", "account_owner", "acquisition_source", mode="before")
    @classmethod
    def clean_optional_text(cls, value: object, info) -> str | None:
        labels = {
            "industry": "Branche",
            "street": "Strasse und Hausnummer",
            "city": "Ort",
            "region": "Kanton/Region",
            "account_owner": "Betreuungsperson",
            "acquisition_source": "Akquisitionsquelle",
        }
        limits = {
            "industry": 120,
            "street": 200,
            "city": 120,
            "region": 120,
            "account_owner": 120,
            "acquisition_source": 120,
        }
        label = labels[info.field_name]
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{label} ist ungültig.")
        cleaned = _collapse(value)
        if not cleaned:
            return None
        if len(cleaned) > limits[info.field_name]:
            raise ValueError(f"{label} darf höchstens {limits[info.field_name]} Zeichen haben.")
        return cleaned

    @field_validator("erp_customer_number", mode="before")
    @classmethod
    def clean_erp(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Die ERP-Kundennummer ist ungültig.")
        cleaned = value.strip()
        if not cleaned:
            return None
        if not ERP_PATTERN.fullmatch(cleaned):
            raise ValueError(
                "Die ERP-Kundennummer darf nur Buchstaben, Ziffern, Bindestriche und Schrägstriche enthalten."
            )
        return cleaned

    @field_validator("postal_code", mode="before")
    @classmethod
    def clean_postal_code(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Postleitzahl ist ungültig.")
        cleaned = _collapse(value)
        if not cleaned:
            return None
        if not POSTAL_PATTERN.fullmatch(cleaned):
            raise ValueError("Postleitzahl ist ungültig.")
        return cleaned

    @field_validator("phone", mode="before")
    @classmethod
    def clean_phone(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Telefonnummer ist ungültig.")
        cleaned = _collapse(value)
        if not cleaned:
            return None
        if not PHONE_PATTERN.fullmatch(cleaned):
            raise ValueError("Telefonnummer ist ungültig.")
        return cleaned

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

    @field_validator("website", mode="before")
    @classmethod
    def clean_website(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Website ist ungültig.")
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) > 300 or not WEBSITE_PATTERN.fullmatch(cleaned):
            raise ValueError("Website muss mit http:// oder https:// beginnen.")
        return cleaned

    @field_validator("notes", mode="before")
    @classmethod
    def clean_notes(cls, value: object) -> str | None:
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError("Interne Bemerkungen sind ungültig.")
        cleaned = value.strip()
        if not cleaned:
            return None
        if len(cleaned) > 4000:
            raise ValueError("Interne Bemerkungen dürfen höchstens 4000 Zeichen haben.")
        return cleaned

    @field_validator("first_contact_on", mode="before")
    @classmethod
    def clean_first_contact(cls, value: object) -> date | None:
        if value is None or value == "":
            return None
        if isinstance(value, datetime):
            raise ValueError("Das Datum der ersten Kontaktaufnahme ist ungültig.")
        if isinstance(value, date):
            parsed = value
        elif isinstance(value, str):
            try:
                parsed = date.fromisoformat(value)
            except ValueError:
                raise ValueError("Das Datum der ersten Kontaktaufnahme ist ungültig.") from None
        else:
            raise ValueError("Das Datum der ersten Kontaktaufnahme ist ungültig.")
        if parsed > date.today():
            raise ValueError("Das Datum der ersten Kontaktaufnahme darf nicht in der Zukunft liegen.")
        if parsed.year < 1900:
            raise ValueError("Das Datum der ersten Kontaktaufnahme ist unplausibel.")
        return parsed


class PartnerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    company_name: str
    erp_customer_number: str | None
    erp_customer_status: str | None = None
    erp_source: str | None = None
    erp_synced_at: datetime | None = None
    partner_type: str
    industry: str | None
    street: str | None
    postal_code: str | None
    city: str | None
    region: str | None
    country: str
    phone: str | None
    email: str | None
    website: str | None
    status: str
    account_owner: str | None
    acquisition_source: str | None
    priority: str
    first_contact_on: date | None
    notes: str | None
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    last_contact_at: datetime | None = Field(
        default=None,
        description="Jüngste nicht archivierte Aktivität dieses Partners.",
    )
    next_activity_on: date | None = Field(
        default=None,
        description="Frühestes Fälligkeitsdatum einer offenen Aufgabe dieses Partners.",
    )


class PartnerList(BaseModel):
    items: list[PartnerRead]
    total: int
    page: int
    page_size: int


class PartnerFilterOptions(BaseModel):
    industries: list[str]
    regions: list[str]
    account_owners: list[str]


class PartnerSummary(BaseModel):
    active: int
    active_demo: int
