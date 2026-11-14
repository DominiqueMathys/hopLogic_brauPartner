"""ORM models.

Import new model modules here so Alembic can discover them on Base.metadata.
"""

from app.database import Base
from app.models.activity import Activity
from app.models.identity import AuditLog, PasswordReset, Permission, Role, RolePermission, User, UserSession
from app.models.contact import CompanyContact, Contact
from app.models.integration import (
    ErpConflict,
    ErpConnection,
    ErpExternalReference,
    ErpOrderTransfer,
    ErpSyncJob,
    ErpSyncRecord,
)
from app.models.engagement import (
    AutomationExecution,
    AutomationRule,
    CampaignAudienceMember,
    CampaignRecipient,
    CareExecution,
    CommunicationPreference,
    CustomerCareRule,
    MarketingCampaign,
    MessageTemplate,
    Notification,
    NotificationPreference,
)
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
    "AuditLog",
    "PasswordReset",
    "Permission",
    "Role",
    "RolePermission",
    "User",
    "UserSession",
    "AutomationExecution",
    "AutomationRule",
    "Base",
    "CampaignAudienceMember",
    "CampaignRecipient",
    "CareExecution",
    "CommunicationPreference",
    "CustomerCareRule",
    "CompanyContact",
    "Contact",
    "CustomerSegment",
    "ErpConflict",
    "ErpConnection",
    "ErpExternalReference",
    "ErpOrderTransfer",
    "ErpSyncJob",
    "ErpSyncRecord",
    "Deal",
    "DealStageHistory",
    "MarketingCampaign",
    "MessageTemplate",
    "Notification",
    "NotificationPreference",
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
