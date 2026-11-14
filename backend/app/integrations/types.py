"""Typed payloads shared by every ERP connector.

The CRM never depends on a vendor schema. A later connector maps its own
responses into these models.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


class ErpError(Exception):
    """Base error for connector calls. Messages stay free of secrets."""


class ErpTechnicalError(ErpError):
    """Temporary failure. A bounded retry with the same idempotency key is allowed."""


class ErpAmbiguousError(ErpError):
    """The connector did not confirm whether the order was created."""


@dataclass(frozen=True)
class ErpCustomer:
    number: str
    company_name: str
    street: str
    postal_code: str
    city: str
    country: str
    phone: str
    email: str
    status: str
    is_demo: bool


@dataclass(frozen=True)
class ErpProduct:
    sku: str
    name: str
    description: str
    category: str
    sales_unit: str
    container_type: str
    container_size: str
    price: Decimal
    currency: str
    vat_rate: Decimal
    is_active: bool
    is_demo: bool


@dataclass(frozen=True)
class ErpOrderLine:
    sku: str
    name: str
    quantity: Decimal
    unit_price: Decimal
    vat_rate: Decimal


@dataclass(frozen=True)
class ErpOrderRequest:
    idempotency_key: str
    order_number: str
    customer_number: str
    lines: tuple[ErpOrderLine, ...]


@dataclass(frozen=True)
class ErpSubmitResult:
    idempotency_key: str
    reference: str
    status: str
    source: str


@dataclass(frozen=True)
class ErpStatusSnapshot:
    reference: str
    status: str
    source: str
    delivery_status: str
    delivery_on: date | None
    delivery_note: str
    invoice_number: str
    invoice_on: date | None
    invoice_status: str
