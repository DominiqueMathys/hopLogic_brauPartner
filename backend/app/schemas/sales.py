from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.sales_catalog import (
    CONTAINER_TYPES,
    DEAL_PRIORITIES,
    DEAL_STAGES,
    OPEN_DEAL_STAGES,
    ORDER_STATUSES,
    PRODUCT_CATEGORIES,
)
from app.schemas.fields import choice, optional_text, required_text
from app.services.money import as_decimal, money, percent, quantity

SKU_PATTERN_MESSAGE = "Die Artikelnummer darf nur Buchstaben, Ziffern, Bindestriche und Schrägstriche enthalten."


def _money_field(value: object, label: str, *, allow_negative: bool = False) -> Decimal:
    if isinstance(value, float):
        raise ValueError(f"{label} muss als Dezimalzahl übergeben werden.")
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise ValueError(f"{label} ist ungültig.")
    if isinstance(value, str):
        cleaned = value.strip().replace("'", "").replace(" ", "").replace(",", ".")
        if not cleaned:
            raise ValueError(f"{label} ist erforderlich.")
        value = cleaned
    try:
        amount = money(as_decimal(value))
    except Exception:
        raise ValueError(f"{label} ist ungültig.") from None
    if not allow_negative and amount < 0:
        raise ValueError(f"{label} darf nicht negativ sein.")
    if amount > Decimal("99999999.99"):
        raise ValueError(f"{label} ist zu gross.")
    return amount


def _percent_field(value: object, label: str) -> Decimal:
    amount = _money_field(value, label)
    if amount > Decimal("100"):
        raise ValueError(f"{label} darf höchstens 100 sein.")
    return percent(amount)


def _quantity_field(value: object) -> Decimal:
    if isinstance(value, float):
        raise ValueError("Die Menge muss als Dezimalzahl übergeben werden.")
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, str)):
        raise ValueError("Die Menge ist ungültig.")
    if isinstance(value, str):
        cleaned = value.strip().replace(",", ".")
        if not cleaned:
            raise ValueError("Die Menge ist erforderlich.")
        value = cleaned
    try:
        amount = quantity(as_decimal(value))
    except Exception:
        raise ValueError("Die Menge ist ungültig.") from None
    if amount <= 0:
        raise ValueError("Die Menge muss grösser als 0 sein.")
    if amount > Decimal("999999.999"):
        raise ValueError("Die Menge ist zu gross.")
    return amount


def _date_field(value: object, label: str, *, required: bool) -> date | None:
    if value is None or value == "":
        if required:
            raise ValueError(f"{label} ist erforderlich.")
        return None
    if isinstance(value, datetime):
        raise ValueError(f"{label} ist ungültig.")
    if isinstance(value, date):
        parsed = value
    elif isinstance(value, str):
        try:
            parsed = date.fromisoformat(value)
        except ValueError:
            raise ValueError(f"{label} ist ungültig.") from None
    else:
        raise ValueError(f"{label} ist ungültig.")
    if parsed.year < 1900 or parsed.year > 2100:
        raise ValueError(f"{label} ist unplausibel.")
    return parsed


class DealWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    title: str = ""
    partner_id: UUID
    contact_id: UUID | None = None
    account_owner: str | None = None
    estimated_value: Decimal = Decimal("0")
    expected_close_on: date | None = None
    stage: str = "neuer_lead"
    probability: Decimal | None = None
    priority: str = "normal"
    description: str | None = None

    @field_validator("title", mode="before")
    @classmethod
    def clean_title(cls, value: object) -> str:
        return required_text(value, "Deal-Titel", 200)

    @field_validator("account_owner", mode="before")
    @classmethod
    def clean_owner(cls, value: object) -> str | None:
        return optional_text(value, "Zuständige Person", 120)

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, value: object) -> str | None:
        return optional_text(value, "Beschreibung", 4000)

    @field_validator("estimated_value", mode="before")
    @classmethod
    def clean_value(cls, value: object) -> Decimal:
        return _money_field(value, "Geschätzter Verkaufswert")

    @field_validator("probability", mode="before")
    @classmethod
    def clean_probability(cls, value: object) -> Decimal | None:
        if value is None or value == "":
            return None
        return _percent_field(value, "Abschlusswahrscheinlichkeit")

    @field_validator("stage", mode="before")
    @classmethod
    def clean_stage(cls, value: object) -> str:
        return choice(value, "Verkaufsphase", DEAL_STAGES, default="neuer_lead")

    @field_validator("priority", mode="before")
    @classmethod
    def clean_priority(cls, value: object) -> str:
        return choice(value, "Priorität", DEAL_PRIORITIES, default="normal")

    @field_validator("expected_close_on", mode="before")
    @classmethod
    def clean_expected(cls, value: object) -> date | None:
        return _date_field(value, "Erwartetes Abschlussdatum", required=False)


class StageMove(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stage: str

    @field_validator("stage", mode="before")
    @classmethod
    def clean_stage(cls, value: object) -> str:
        cleaned = choice(value, "Verkaufsphase", OPEN_DEAL_STAGES)
        return cleaned


class DealClose(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closed_on: date | None = None
    loss_reason: str | None = None

    @field_validator("closed_on", mode="before")
    @classmethod
    def clean_closed(cls, value: object) -> date | None:
        parsed = _date_field(value, "Abschlussdatum", required=False)
        if parsed is not None and parsed > date.today():
            raise ValueError("Das Abschlussdatum darf nicht in der Zukunft liegen.")
        return parsed

    @field_validator("loss_reason", mode="before")
    @classmethod
    def clean_reason(cls, value: object) -> str | None:
        return optional_text(value, "Verlustgrund", 500)


class DealRead(BaseModel):
    id: UUID
    title: str
    partner_id: UUID
    contact_id: UUID | None
    company_name: str
    contact_name: str | None
    account_owner: str | None
    estimated_value: Decimal
    expected_close_on: date | None
    stage: str
    probability: Decimal
    priority: str
    description: str | None
    closed_on: date | None
    loss_reason: str | None
    is_overdue: bool
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime


class StageHistoryRead(BaseModel):
    id: UUID
    from_stage: str | None
    to_stage: str
    changed_by: str | None
    changed_at: datetime


class DealDetail(DealRead):
    history: list[StageHistoryRead]


class DealList(BaseModel):
    items: list[DealRead]
    total: int
    page: int
    page_size: int


class PipelineCard(BaseModel):
    id: UUID
    title: str
    partner_id: UUID
    company_name: str
    estimated_value: Decimal
    account_owner: str | None
    expected_close_on: date | None
    is_overdue: bool
    is_demo: bool


class PipelineColumn(BaseModel):
    stage: str
    count: int
    total_value: Decimal
    deals: list[PipelineCard]


class PipelineBoard(BaseModel):
    columns: list[PipelineColumn]


class DealSummary(BaseModel):
    open_count: int
    open_demo: int
    pipeline_value: Decimal
    won_count: int
    won_value: Decimal
    overdue_count: int


class ProductWrite(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_default=True)

    sku: str = ""
    name: str = ""
    category: str = ""
    description: str | None = None
    container_type: str = "flasche"
    container_size: str | None = None
    sales_unit: str | None = None
    list_price: Decimal = Decimal("0")
    vat_rate: Decimal = Decimal("8.10")
    is_active: bool = True

    @field_validator("sku", mode="before")
    @classmethod
    def clean_sku(cls, value: object) -> str:
        cleaned = required_text(value, "Artikelnummer", 40)
        allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-/")
        if any(character not in allowed for character in cleaned):
            raise ValueError(SKU_PATTERN_MESSAGE)
        return cleaned

    @field_validator("name", mode="before")
    @classmethod
    def clean_name(cls, value: object) -> str:
        return required_text(value, "Produktname", 200)

    @field_validator("category", mode="before")
    @classmethod
    def clean_category(cls, value: object) -> str:
        return choice(value, "Produktkategorie", PRODUCT_CATEGORIES)

    @field_validator("container_type", mode="before")
    @classmethod
    def clean_container(cls, value: object) -> str:
        return choice(value, "Gebindeart", CONTAINER_TYPES, default="flasche")

    @field_validator("description", mode="before")
    @classmethod
    def clean_description(cls, value: object) -> str | None:
        return optional_text(value, "Beschreibung", 4000)

    @field_validator("container_size", mode="before")
    @classmethod
    def clean_size(cls, value: object) -> str | None:
        return optional_text(value, "Gebindegrösse", 40)

    @field_validator("sales_unit", mode="before")
    @classmethod
    def clean_unit(cls, value: object) -> str | None:
        return optional_text(value, "Verkaufseinheit", 80)

    @field_validator("list_price", mode="before")
    @classmethod
    def clean_price(cls, value: object) -> Decimal:
        return _money_field(value, "Richtpreis")

    @field_validator("vat_rate", mode="before")
    @classmethod
    def clean_vat(cls, value: object) -> Decimal:
        return _percent_field(value, "Mehrwertsteuersatz")


class ProductRead(BaseModel):
    id: UUID
    sku: str
    name: str
    category: str
    description: str | None
    container_type: str
    container_size: str | None
    sales_unit: str | None
    list_price: Decimal
    vat_rate: Decimal
    currency: str = "CHF"
    erp_source: str | None = None
    erp_synced_at: datetime | None = None
    is_active: bool
    is_demo: bool
    created_at: datetime
    updated_at: datetime


class ProductList(BaseModel):
    items: list[ProductRead]
    total: int
    page: int
    page_size: int


class OrderItemWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: UUID
    quantity: Decimal
    unit_price: Decimal | None = None
    discount_percent: Decimal = Decimal("0")

    @field_validator("quantity", mode="before")
    @classmethod
    def clean_quantity(cls, value: object) -> Decimal:
        return _quantity_field(value)

    @field_validator("unit_price", mode="before")
    @classmethod
    def clean_price(cls, value: object) -> Decimal | None:
        if value is None or value == "":
            return None
        return _money_field(value, "Einzelpreis")

    @field_validator("discount_percent", mode="before")
    @classmethod
    def clean_discount(cls, value: object) -> Decimal:
        if value is None or value == "":
            return Decimal("0.00")
        return _percent_field(value, "Rabatt")


class OrderWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")

    partner_id: UUID
    contact_id: UUID | None = None
    deal_id: UUID | None = None
    ordered_on: date
    requested_delivery_on: date | None = None
    notes: str | None = None
    erp_reference: str | None = None
    items: list[OrderItemWrite]
    submit: bool = False

    @field_validator("ordered_on", mode="before")
    @classmethod
    def clean_ordered(cls, value: object) -> date:
        parsed = _date_field(value, "Bestelldatum", required=True)
        assert parsed is not None
        return parsed

    @field_validator("requested_delivery_on", mode="before")
    @classmethod
    def clean_delivery(cls, value: object) -> date | None:
        return _date_field(value, "Gewünschtes Lieferdatum", required=False)

    @field_validator("notes", mode="before")
    @classmethod
    def clean_notes(cls, value: object) -> str | None:
        return optional_text(value, "Interne Bemerkungen", 4000)

    @field_validator("erp_reference", mode="before")
    @classmethod
    def clean_erp(cls, value: object) -> str | None:
        return optional_text(value, "ERP-Referenz", 80)

    @model_validator(mode="after")
    def needs_items(self) -> "OrderWrite":
        if len(self.items) == 0:
            raise ValueError("Die Bestellung braucht mindestens eine Position.")
        if len(self.items) > 100:
            raise ValueError("Eine Bestellung darf höchstens 100 Positionen haben.")
        return self


class OrderItemRead(BaseModel):
    id: UUID
    product_id: UUID
    position: int
    product_name: str
    sku: str
    quantity: Decimal
    unit_price: Decimal
    discount_percent: Decimal
    discount_amount: Decimal
    vat_rate: Decimal
    line_net: Decimal
    line_vat: Decimal
    line_gross: Decimal


class OrderRead(BaseModel):
    id: UUID
    order_number: str
    partner_id: UUID
    contact_id: UUID | None
    deal_id: UUID | None
    company_name: str
    contact_name: str | None
    ordered_on: date
    requested_delivery_on: date | None
    status: str
    notes: str | None
    erp_reference: str | None
    transfer_status: str = "nicht_uebertragen"
    erp_status: str | None = None
    erp_status_at: datetime | None = None
    erp_status_source: str | None = None
    delivery_on: date | None = None
    delivery_note: str = ""
    delivery_status: str = ""
    invoice_number: str = ""
    invoice_on: date | None = None
    invoice_status: str = ""
    subtotal: Decimal
    discount_total: Decimal
    net_total: Decimal
    vat_total: Decimal
    gross_total: Decimal
    is_demo: bool
    archived_at: datetime | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemRead]
    allowed_transitions: list[str]


class OrderListItem(BaseModel):
    id: UUID
    order_number: str
    partner_id: UUID
    company_name: str
    ordered_on: date
    status: str
    gross_total: Decimal
    is_demo: bool


class OrderList(BaseModel):
    items: list[OrderListItem]
    total: int
    page: int
    page_size: int


class OrderStatusChange(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str

    @field_validator("status", mode="before")
    @classmethod
    def clean_status(cls, value: object) -> str:
        return choice(value, "Bestellstatus", ORDER_STATUSES)


class OrderSummary(BaseModel):
    volume: Decimal
    volume_demo: Decimal
    new_count: int
    order_count: int
    last_ordered_on: date | None
