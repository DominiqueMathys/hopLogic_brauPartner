"""ORM models.

Import new model modules here so Alembic can discover them on Base.metadata.
"""

from app.database import Base

__all__ = ["Base"]
