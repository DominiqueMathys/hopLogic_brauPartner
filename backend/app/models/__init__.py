"""ORM models.

Import new model modules here so Alembic can discover them on Base.metadata.
"""

from app.database import Base
from app.models.activity import Activity
from app.models.contact import CompanyContact, Contact
from app.models.partner import Partner
from app.models.task import Task

__all__ = ["Activity", "Base", "CompanyContact", "Contact", "Partner", "Task"]
