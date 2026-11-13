"""Vertriebspartner table.

Revision ID: 0002_vertriebspartner
Revises: 0001_initial
Create Date: 2026-11-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_vertriebspartner"
down_revision: Union[str, Sequence[str], None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "vertriebspartner",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=False),
        sa.Column("erp_customer_number", sa.String(length=40), nullable=True),
        sa.Column("partner_type", sa.String(length=40), nullable=False),
        sa.Column("industry", sa.String(length=120), nullable=True),
        sa.Column("street", sa.String(length=200), nullable=True),
        sa.Column("postal_code", sa.String(length=12), nullable=True),
        sa.Column("city", sa.String(length=120), nullable=True),
        sa.Column("region", sa.String(length=120), nullable=True),
        sa.Column("country", sa.String(length=80), nullable=False),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("website", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("account_owner", sa.String(length=120), nullable=True),
        sa.Column("acquisition_source", sa.String(length=120), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("first_contact_on", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.CheckConstraint(
            "partner_type IN ('restaurant', 'hotel', 'bar', 'getraenkehaendler', 'detailhandel', 'veranstalter', 'sonstige')",
            name="ck_vertriebspartner_partner_type",
        ),
        sa.CheckConstraint(
            "status IN ('lead', 'potenziell', 'aktiv', 'inaktiv')",
            name="ck_vertriebspartner_status",
        ),
        sa.CheckConstraint(
            "priority IN ('niedrig', 'normal', 'hoch')",
            name="ck_vertriebspartner_priority",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_vertriebspartner_demo_key"),
    )
    op.create_index("ix_vertriebspartner_company_name", "vertriebspartner", ["company_name"])
    op.create_index("ix_vertriebspartner_city", "vertriebspartner", ["city"])
    op.create_index("ix_vertriebspartner_status", "vertriebspartner", ["status"])
    op.create_index("ix_vertriebspartner_created_at", "vertriebspartner", ["created_at"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_vertriebspartner_erp_customer_number
        ON vertriebspartner (lower(erp_customer_number))
        WHERE erp_customer_number IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_vertriebspartner_erp_customer_number")
    op.drop_index("ix_vertriebspartner_created_at", table_name="vertriebspartner")
    op.drop_index("ix_vertriebspartner_status", table_name="vertriebspartner")
    op.drop_index("ix_vertriebspartner_city", table_name="vertriebspartner")
    op.drop_index("ix_vertriebspartner_company_name", table_name="vertriebspartner")
    op.drop_table("vertriebspartner")
