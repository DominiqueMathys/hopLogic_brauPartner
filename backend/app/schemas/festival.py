from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.festival_catalog import (
    ASSIGNMENT_KINDS,
    ASSIGNMENT_STATUSES,
    DELIVERY_STATUSES,
    EVENT_TYPES,
    MATERIAL_TRACKING,
    MOVEMENT_TYPES,
    QUOTE_ITEM_KINDS,
    REQUEST_STATUSES,
)
from app.schemas.fields import choice, optional_text, parse_timestamp, required_text


class FestivalWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    organizer_name: str
    starts_at: datetime
    ends_at: datetime
    description: str | None = None
    event_type: str = "fest"
    organizer_partner_id: UUID | None = None
    distributor_partner_id: UUID | None = None
    contact_id: UUID | None = None
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    venue_name: str | None = None
    street: str | None = None
    postal_code: str | None = None
    city: str | None = None
    region: str | None = None
    country: str = "Schweiz"
    expected_visitors: int | None = Field(default=None, ge=0, le=1_000_000)
    notes: str | None = None
    requirements: str | None = None
    drinks: str | None = None
    material_wish: str | None = None
    delivery_wish_at: datetime | None = None
    pickup_wish_at: datetime | None = None
    account_owner: str | None = None
    order_id: UUID | None = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> str:
        return required_text(value, "Festname", 200)

    @field_validator("organizer_name", mode="before")
    @classmethod
    def clean_organizer(cls, value: object) -> str:
        return required_text(value, "Veranstalter", 200)

    @field_validator("event_type", mode="before")
    @classmethod
    def clean_type(cls, value: object) -> str:
        return choice(value, "Veranstaltungsart", EVENT_TYPES, default="fest")

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def clean_period(cls, value: object) -> datetime:
        return parse_timestamp(value, "Zeitraum")

    @field_validator("delivery_wish_at", "pickup_wish_at", mode="before")
    @classmethod
    def clean_optional_time(cls, value: object) -> datetime | None:
        if value is None or value == "":
            return None
        return parse_timestamp(value, "Wunschtermin")

    @field_validator(
        "description",
        "contact_name",
        "phone",
        "email",
        "venue_name",
        "street",
        "postal_code",
        "city",
        "region",
        "country",
        "notes",
        "requirements",
        "drinks",
        "material_wish",
        "account_owner",
        mode="before",
    )
    @classmethod
    def clean_text(cls, value: object) -> str | None:
        limit = 4000 if value is not None and isinstance(value, str) and len(value) > 300 else 300
        return optional_text(value, "Text", limit)


class FestivalUpdate(FestivalWrite):
    name: str | None = None
    organizer_name: str | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    request_status: str | None = None
    change_reason: str | None = None
    change_note: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> str | None:
        if value is None:
            return None
        return required_text(value, "Festname", 200)

    @field_validator("organizer_name", mode="before")
    @classmethod
    def clean_organizer(cls, value: object) -> str | None:
        if value is None:
            return None
        return required_text(value, "Veranstalter", 200)

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def clean_period(cls, value: object) -> datetime | None:
        if value is None or value == "":
            return None
        return parse_timestamp(value, "Zeitraum")

    @field_validator("request_status", mode="before")
    @classmethod
    def clean_request(cls, value: object) -> str | None:
        if value is None or value == "":
            return None
        return choice(value, "Anfragestatus", REQUEST_STATUSES)


class MaterialWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    category_id: UUID | None = None
    description: str | None = None
    tracking: str = "menge"
    location: str | None = None
    unit: str = "Stück"
    rental_price: Decimal | None = None
    deposit_amount: Decimal | None = None
    prep_hours: int = Field(default=0, ge=0, le=240)
    return_hours: int = Field(default=0, ge=0, le=240)
    cleaning_hours: int = Field(default=0, ge=0, le=240)
    notes: str | None = None

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> str:
        return required_text(value, "Materialname", 200)

    @field_validator("tracking", mode="before")
    @classmethod
    def clean_tracking(cls, value: object) -> str:
        return choice(value, "Materialtyp", MATERIAL_TRACKING, default="menge")


class StockWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    movement_type: str
    quantity: int = 0
    note: str | None = None
    location: str | None = None
    bucket: str | None = None

    @field_validator("movement_type", mode="before")
    @classmethod
    def clean_type(cls, value: object) -> str:
        return choice(value, "Bewegung", MOVEMENT_TYPES)


class AssetWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inventory_number: str
    location: str | None = None

    @field_validator("inventory_number", mode="before")
    @classmethod
    def clean_number(cls, value: object) -> str:
        return required_text(value, "Inventarnummer", 40)


class ReservationLineWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    material_id: UUID
    quantity: int = Field(ge=1, le=100000)
    asset_id: UUID | None = None


class ReservationWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    festival_id: UUID
    starts_at: datetime
    ends_at: datetime
    prep_hours: int = Field(default=0, ge=0, le=240)
    return_hours: int = Field(default=0, ge=0, le=240)
    cleaning_hours: int = Field(default=0, ge=0, le=240)
    location: str | None = None
    notes: str | None = None
    lines: list[ReservationLineWrite] = Field(default_factory=list)

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def clean_period(cls, value: object) -> datetime:
        return parse_timestamp(value, "Reservationszeitraum")


class ReplaceLineWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: UUID
    material_id: UUID
    quantity: int = Field(ge=1, le=100000)


class IssueLineWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: UUID
    quantity: int = Field(ge=1, le=100000)


class IssueWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lines: list[IssueLineWrite] = Field(default_factory=list)
    condition_note: str | None = None
    issued_at: datetime | None = None

    @field_validator("issued_at", mode="before")
    @classmethod
    def clean_time(cls, value: object) -> datetime | None:
        if value is None or value == "":
            return None
        return parse_timestamp(value, "Ausgabedatum")


class ReturnLineWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    line_id: UUID
    returned_qty: int = Field(default=0, ge=0, le=100000)
    damaged_qty: int = Field(default=0, ge=0, le=100000)
    missing_qty: int = Field(default=0, ge=0, le=100000)


class ReturnWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lines: list[ReturnLineWrite]
    notes: str | None = None
    returned_at: datetime | None = None
    idempotency_key: str | None = None

    @field_validator("returned_at", mode="before")
    @classmethod
    def clean_time(cls, value: object) -> datetime | None:
        if value is None or value == "":
            return None
        return parse_timestamp(value, "Rücknahmedatum")


class QuoteItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str
    quantity: Decimal = Field(gt=0)
    unit_price: Decimal = Field(ge=0)
    kind: str = "material"
    unit: str = "Stück"
    discount_percent: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    vat_rate: Decimal | None = Field(default=None, ge=0, le=100)
    material_id: UUID | None = None
    product_id: UUID | None = None

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, value: object) -> str:
        return required_text(value, "Position", 200)

    @field_validator("kind", mode="before")
    @classmethod
    def clean_kind(cls, value: object) -> str:
        return choice(value, "Positionsart", QUOTE_ITEM_KINDS, default="material")


class QuoteWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    festival_id: UUID
    contact_name: str | None = None
    quote_on: datetime | None = None
    valid_until: datetime | None = None
    vat_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    notes: str | None = None
    items: list[QuoteItemWrite] = Field(default_factory=list)

    @field_validator("quote_on", "valid_until", mode="before")
    @classmethod
    def clean_time(cls, value: object) -> datetime | None:
        if value is None or value == "":
            return None
        return parse_timestamp(value, "Offertendatum")


class QuoteItemsWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[QuoteItemWrite]


class QuoteStatusWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str


class DeliveryWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    festival_id: UUID
    address: str
    deliver_at: datetime | None = None
    deliver_window: str | None = None
    pickup_at: datetime | None = None
    pickup_window: str | None = None
    status: str = "geplant"
    account_owner: str | None = None
    notes: str | None = None

    @field_validator("address", mode="before")
    @classmethod
    def clean_address(cls, value: object) -> str:
        return required_text(value, "Lieferadresse", 300)

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, value: object) -> str:
        allowed = tuple(status for status in DELIVERY_STATUSES if status != "keine")
        return choice(value, "Transportstatus", allowed, default="geplant")

    @field_validator("deliver_at", "pickup_at", mode="before")
    @classmethod
    def clean_time(cls, value: object) -> datetime | None:
        if value is None or value == "":
            return None
        return parse_timestamp(value, "Transporttermin")


class AssignmentWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    festival_id: UUID
    person_name: str
    kind: str
    task: str
    starts_at: datetime
    ends_at: datetime
    user_id: UUID | None = None
    status: str = "geplant"
    notes: str | None = None

    @field_validator("person_name", "task", mode="before")
    @classmethod
    def clean_required(cls, value: object) -> str:
        return required_text(value, "Einsatz", 200)

    @field_validator("kind", mode="before")
    @classmethod
    def clean_kind(cls, value: object) -> str:
        return choice(value, "Einsatzart", ASSIGNMENT_KINDS)

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, value: object) -> str:
        return choice(value, "Einsatzstatus", ASSIGNMENT_STATUSES, default="geplant")

    @field_validator("starts_at", "ends_at", mode="before")
    @classmethod
    def clean_period(cls, value: object) -> datetime:
        return parse_timestamp(value, "Einsatzzeit")


class ReasonWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str

    @field_validator("reason", mode="before")
    @classmethod
    def clean_reason(cls, value: object) -> str:
        return required_text(value, "Grund", 400)


class NoteWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str | None = None
    activity_type: str = "gespraechsnotiz"

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: object) -> str:
        return required_text(value, "Titel", 200)


class TicketLinkWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: UUID
