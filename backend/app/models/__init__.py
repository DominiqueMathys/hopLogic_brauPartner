"""ORM models.

Import new model modules here so Alembic can discover them on Base.metadata.
"""

from app.database import Base
from app.models.activity import Activity
from app.models.contact import CompanyContact, Contact
from app.models.partner import Partner
from app.models.sales import Deal, DealStageHistory, Order, OrderItem, Product
from app.models.service import (
    CustomerSegment,
    SegmentCondition,
    ServiceTicket,
    TicketAttachment,
    TicketEvent,
    TicketProduct,
    TicketResolution,
)
from app.models.task import Task

__all__ = [
    "Activity",
    "Base",
    "CompanyContact",
    "Contact",
    "CustomerSegment",
    "Deal",
    "DealStageHistory",
    "Order",
    "OrderItem",
    "Partner",
    "Product",
    "SegmentCondition",
    "ServiceTicket",
    "Task",
    "TicketAttachment",
    "TicketEvent",
    "TicketProduct",
    "TicketResolution",
]
