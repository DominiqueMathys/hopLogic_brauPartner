"""Service tickets, resolutions and customer segments.

Revision ID: 0005_service
Revises: 0004_sales
Create Date: 2026-11-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_service"
down_revision: Union[str, Sequence[str], None] = "0004_sales"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "service_tickets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_number", sa.String(length=40), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=40), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("order_id", sa.Uuid(), nullable=True),
        sa.Column("account_owner", sa.String(length=120), nullable=True),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("internal_remark", sa.Text(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "category IN ('beschaedigte_lieferung', 'fehlende_lieferung', 'falsche_lieferung', 'produktqualitaet', 'rechnung', 'anfrage', 'technisch', 'sonstiges')",
            name="ck_service_tickets_category",
        ),
        sa.CheckConstraint("priority IN ('niedrig', 'normal', 'hoch', 'kritisch')", name="ck_service_tickets_priority"),
        sa.CheckConstraint(
            "status IN ('neu', 'offen', 'in_bearbeitung', 'warten_kunde', 'warten_intern', 'geloest', 'geschlossen')",
            name="ck_service_tickets_status",
        ),
        sa.ForeignKeyConstraint(["partner_id"], ["vertriebspartner.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["kontakte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["order_id"], ["bestellungen.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ticket_number", name="uq_service_tickets_number"),
        sa.UniqueConstraint("demo_key", name="uq_service_tickets_demo_key"),
    )
    op.create_index("ix_service_tickets_partner", "service_tickets", ["partner_id"])
    op.create_index("ix_service_tickets_status", "service_tickets", ["status"])
    op.create_index("ix_service_tickets_priority", "service_tickets", ["priority"])
    op.create_index("ix_service_tickets_owner", "service_tickets", ["account_owner"])
    op.create_index("ix_service_tickets_updated", "service_tickets", ["updated_at"])

    op.create_table(
        "ticket_produkte",
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["service_tickets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["produkte.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("ticket_id", "product_id"),
    )
    op.create_index("ix_ticket_produkte_product", "ticket_produkte", ["product_id"])

    op.create_table(
        "ticket_anhaenge",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("original_name", sa.String(length=200), nullable=False),
        sa.Column("stored_name", sa.String(length=80), nullable=False),
        sa.Column("content_type", sa.String(length=80), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["ticket_id"], ["service_tickets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_anhaenge_ticket", "ticket_anhaenge", ["ticket_id"])

    op.create_table(
        "ticket_loesungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("recorded_by", sa.String(length=120), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "code IN ('ersatzlieferung', 'gutschrift', 'vertrieb', 'logistik', 'keine_massnahme', 'sonstige')",
            name="ck_ticket_loesungen_code",
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["service_tickets.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_loesungen_ticket", "ticket_loesungen", ["ticket_id"])

    op.add_column("aufgaben", sa.Column("ticket_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_aufgaben_ticket", "aufgaben", "service_tickets", ["ticket_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_aufgaben_ticket", "aufgaben", ["ticket_id"])

    op.create_table(
        "ticket_ereignisse",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ticket_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=30), nullable=False),
        sa.Column("from_value", sa.String(length=200), nullable=True),
        sa.Column("to_value", sa.String(length=200), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("changed_by", sa.String(length=120), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "event_type IN ('created', 'status_changed', 'priority_changed', 'owner_changed', 'note_added', 'task_created', 'resolved', 'closed', 'reopened')",
            name="ck_ticket_ereignisse_type",
        ),
        sa.ForeignKeyConstraint(["ticket_id"], ["service_tickets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["task_id"], ["aufgaben.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ticket_ereignisse_ticket", "ticket_ereignisse", ["ticket_id"])

    op.create_table(
        "kundensegmente",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("match_mode", sa.String(length=10), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("match_mode IN ('all', 'any')", name="ck_kundensegmente_mode"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_kundensegmente_name"),
        sa.UniqueConstraint("demo_key", name="uq_kundensegmente_demo_key"),
    )
    op.create_table(
        "segmentbedingungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sa.String(length=40), nullable=False),
        sa.Column("operator", sa.String(length=20), nullable=False),
        sa.Column("value", sa.String(length=120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "field_name IN ('partner_type', 'industry', 'region', 'status', 'order_count', 'order_volume', 'last_order_on', 'open_deals', 'open_tickets', 'last_activity_on')",
            name="ck_segmentbedingungen_field",
        ),
        sa.CheckConstraint(
            "operator IN ('eq', 'gte', 'lte', 'before', 'after', 'empty')",
            name="ck_segmentbedingungen_operator",
        ),
        sa.ForeignKeyConstraint(["segment_id"], ["kundensegmente.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_segmentbedingungen_segment", "segmentbedingungen", ["segment_id"])


def downgrade() -> None:
    op.drop_index("ix_segmentbedingungen_segment", table_name="segmentbedingungen")
    op.drop_table("segmentbedingungen")
    op.drop_table("kundensegmente")
    op.drop_index("ix_ticket_ereignisse_ticket", table_name="ticket_ereignisse")
    op.drop_table("ticket_ereignisse")
    op.drop_index("ix_aufgaben_ticket", table_name="aufgaben")
    op.drop_constraint("fk_aufgaben_ticket", "aufgaben", type_="foreignkey")
    op.drop_column("aufgaben", "ticket_id")
    op.drop_index("ix_ticket_loesungen_ticket", table_name="ticket_loesungen")
    op.drop_table("ticket_loesungen")
    op.drop_index("ix_ticket_anhaenge_ticket", table_name="ticket_anhaenge")
    op.drop_table("ticket_anhaenge")
    op.drop_index("ix_ticket_produkte_product", table_name="ticket_produkte")
    op.drop_table("ticket_produkte")
    op.drop_index("ix_service_tickets_updated", table_name="service_tickets")
    op.drop_index("ix_service_tickets_owner", table_name="service_tickets")
    op.drop_index("ix_service_tickets_priority", table_name="service_tickets")
    op.drop_index("ix_service_tickets_status", table_name="service_tickets")
    op.drop_index("ix_service_tickets_partner", table_name="service_tickets")
    op.drop_table("service_tickets")
