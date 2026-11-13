"""Contacts, company links, activities and tasks.

Revision ID: 0003_crm
Revises: 0002_vertriebspartner
Create Date: 2026-11-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_crm"
down_revision: Union[str, Sequence[str], None] = "0002_vertriebspartner"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kontakte",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("job_title", sa.String(length=120), nullable=True),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("mobile", sa.String(length=40), nullable=True),
        sa.Column("account_owner", sa.String(length=120), nullable=True),
        sa.Column("preferred_language", sa.String(length=8), nullable=False),
        sa.Column("preferred_channel", sa.String(length=20), nullable=False),
        sa.Column("lifecycle_phase", sa.String(length=20), nullable=False),
        sa.Column("lead_status", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("processing_basis", sa.String(length=40), nullable=False),
        sa.Column("processing_basis_note", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('aktiv', 'inaktiv')", name="ck_kontakte_status"),
        sa.CheckConstraint("lead_status IN ('keiner', 'offen', 'abgeschlossen')", name="ck_kontakte_lead_status"),
        sa.CheckConstraint(
            "lifecycle_phase IN ('lead', 'interessent', 'qualifiziert', 'kunde', 'ehemalig')",
            name="ck_kontakte_lifecycle",
        ),
        sa.CheckConstraint("preferred_language IN ('de', 'fr', 'it')", name="ck_kontakte_language"),
        sa.CheckConstraint(
            "preferred_channel IN ('telefon', 'email', 'mobil', 'persoenlich')",
            name="ck_kontakte_channel",
        ),
        sa.CheckConstraint(
            "processing_basis IN ('nicht_dokumentiert', 'vertrag', 'berechtigte_interessen', 'einwilligung', 'gesetzliche_pflicht')",
            name="ck_kontakte_processing_basis",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_kontakte_demo_key"),
    )
    op.create_index("ix_kontakte_last_name", "kontakte", ["last_name"])
    op.create_index("ix_kontakte_email", "kontakte", ["email"])
    op.create_index("ix_kontakte_account_owner", "kontakte", ["account_owner"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_kontakte_email_active
        ON kontakte (lower(email))
        WHERE email IS NOT NULL
        """
    )

    op.create_table(
        "unternehmen_kontakte",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["contact_id"], ["kontakte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["vertriebspartner.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("partner_id", "contact_id", name="uq_unternehmen_kontakte_pair"),
    )
    op.create_index("ix_unternehmen_kontakte_contact", "unternehmen_kontakte", ["contact_id"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_unternehmen_kontakte_primary
        ON unternehmen_kontakte (partner_id)
        WHERE is_primary
        """
    )

    op.create_table(
        "aktivitaeten",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("activity_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("account_owner", sa.String(length=120), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "activity_type IN ('telefonat', 'email', 'besuch', 'meeting', 'gespraechsnotiz', 'sonstige')",
            name="ck_aktivitaeten_type",
        ),
        sa.CheckConstraint("contact_id IS NOT NULL OR partner_id IS NOT NULL", name="ck_aktivitaeten_link"),
        sa.ForeignKeyConstraint(["contact_id"], ["kontakte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["vertriebspartner.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_aktivitaeten_demo_key"),
    )
    op.create_index("ix_aktivitaeten_occurred_at", "aktivitaeten", ["occurred_at"])
    op.create_index("ix_aktivitaeten_partner", "aktivitaeten", ["partner_id"])
    op.create_index("ix_aktivitaeten_contact", "aktivitaeten", ["contact_id"])

    op.create_table(
        "aufgaben",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("account_owner", sa.String(length=120), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("task_type", sa.String(length=20), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "status IN ('offen', 'in_bearbeitung', 'erledigt', 'abgebrochen')",
            name="ck_aufgaben_status",
        ),
        sa.CheckConstraint("priority IN ('niedrig', 'normal', 'hoch', 'dringend')", name="ck_aufgaben_priority"),
        sa.CheckConstraint(
            "task_type IN ('anruf', 'email', 'besuch', 'intern', 'sonstige')",
            name="ck_aufgaben_type",
        ),
        sa.ForeignKeyConstraint(["activity_id"], ["aktivitaeten.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["kontakte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["vertriebspartner.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_aufgaben_demo_key"),
    )
    op.create_index("ix_aufgaben_due_at", "aufgaben", ["due_at"])
    op.create_index("ix_aufgaben_status", "aufgaben", ["status"])
    op.create_index("ix_aufgaben_owner", "aufgaben", ["account_owner"])
    op.create_index("ix_aufgaben_partner", "aufgaben", ["partner_id"])
    op.create_index("ix_aufgaben_contact", "aufgaben", ["contact_id"])


def downgrade() -> None:
    op.drop_index("ix_aufgaben_contact", table_name="aufgaben")
    op.drop_index("ix_aufgaben_partner", table_name="aufgaben")
    op.drop_index("ix_aufgaben_owner", table_name="aufgaben")
    op.drop_index("ix_aufgaben_status", table_name="aufgaben")
    op.drop_index("ix_aufgaben_due_at", table_name="aufgaben")
    op.drop_table("aufgaben")
    op.drop_index("ix_aktivitaeten_contact", table_name="aktivitaeten")
    op.drop_index("ix_aktivitaeten_partner", table_name="aktivitaeten")
    op.drop_index("ix_aktivitaeten_occurred_at", table_name="aktivitaeten")
    op.drop_table("aktivitaeten")
    op.execute("DROP INDEX IF EXISTS uq_unternehmen_kontakte_primary")
    op.drop_index("ix_unternehmen_kontakte_contact", table_name="unternehmen_kontakte")
    op.drop_table("unternehmen_kontakte")
    op.execute("DROP INDEX IF EXISTS uq_kontakte_email_active")
    op.drop_index("ix_kontakte_account_owner", table_name="kontakte")
    op.drop_index("ix_kontakte_email", table_name="kontakte")
    op.drop_index("ix_kontakte_last_name", table_name="kontakte")
    op.drop_table("kontakte")
