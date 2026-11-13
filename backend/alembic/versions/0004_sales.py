"""Deals, products and orders.

Revision ID: 0004_sales
Revises: 0003_crm
Create Date: 2026-11-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_sales"
down_revision: Union[str, Sequence[str], None] = "0003_crm"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "verkaufschancen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("account_owner", sa.String(length=120), nullable=True),
        sa.Column("estimated_value", sa.Numeric(12, 2), nullable=False),
        sa.Column("expected_close_on", sa.Date(), nullable=True),
        sa.Column("stage", sa.String(length=30), nullable=False),
        sa.Column("probability", sa.Numeric(5, 2), nullable=False),
        sa.Column("priority", sa.String(length=20), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("closed_on", sa.Date(), nullable=True),
        sa.Column("loss_reason", sa.String(length=500), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "stage IN ('neuer_lead', 'erstkontakt', 'bedarf', 'angebot', 'verhandlung', 'gewonnen', 'verloren')",
            name="ck_verkaufschancen_stage",
        ),
        sa.CheckConstraint("priority IN ('niedrig', 'normal', 'hoch', 'dringend')", name="ck_verkaufschancen_priority"),
        sa.CheckConstraint("estimated_value >= 0", name="ck_verkaufschancen_value"),
        sa.CheckConstraint("probability >= 0 AND probability <= 100", name="ck_verkaufschancen_probability"),
        sa.ForeignKeyConstraint(["contact_id"], ["kontakte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["vertriebspartner.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_verkaufschancen_demo_key"),
    )
    op.create_index("ix_verkaufschancen_partner", "verkaufschancen", ["partner_id"])
    op.create_index("ix_verkaufschancen_stage", "verkaufschancen", ["stage"])
    op.create_index("ix_verkaufschancen_expected_close", "verkaufschancen", ["expected_close_on"])

    op.create_table(
        "verkaufschancen_phasen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("deal_id", sa.Uuid(), nullable=False),
        sa.Column("from_stage", sa.String(length=30), nullable=True),
        sa.Column("to_stage", sa.String(length=30), nullable=False),
        sa.Column("changed_by", sa.String(length=120), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "to_stage IN ('neuer_lead', 'erstkontakt', 'bedarf', 'angebot', 'verhandlung', 'gewonnen', 'verloren')",
            name="ck_verkaufschancen_phasen_to",
        ),
        sa.ForeignKeyConstraint(["deal_id"], ["verkaufschancen.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_verkaufschancen_phasen_deal", "verkaufschancen_phasen", ["deal_id"])

    op.create_table(
        "produkte",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("sku", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("container_type", sa.String(length=20), nullable=False),
        sa.Column("container_size", sa.String(length=40), nullable=True),
        sa.Column("sales_unit", sa.String(length=80), nullable=True),
        sa.Column("list_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "category IN ('bier', 'alkoholfrei', 'mischgetraenke', 'merchandising', 'festmaterial', 'sonstiges')",
            name="ck_produkte_category",
        ),
        sa.CheckConstraint(
            "container_type IN ('flasche', 'dose', 'fass', 'gebinde', 'sonstiges')",
            name="ck_produkte_container",
        ),
        sa.CheckConstraint("list_price >= 0", name="ck_produkte_price"),
        sa.CheckConstraint("vat_rate >= 0 AND vat_rate <= 100", name="ck_produkte_vat"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_produkte_demo_key"),
    )
    op.create_index("ix_produkte_name", "produkte", ["name"])
    op.create_index("ix_produkte_category", "produkte", ["category"])
    op.execute("CREATE UNIQUE INDEX uq_produkte_sku ON produkte (lower(sku))")

    op.create_table(
        "bestellungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_number", sa.String(length=40), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("deal_id", sa.Uuid(), nullable=True),
        sa.Column("ordered_on", sa.Date(), nullable=False),
        sa.Column("requested_delivery_on", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("erp_reference", sa.String(length=80), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("net_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("vat_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("gross_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "status IN ('entwurf', 'eingereicht', 'bestaetigt', 'in_bearbeitung', 'versandt', 'geliefert', 'storniert')",
            name="ck_bestellungen_status",
        ),
        sa.CheckConstraint("subtotal >= 0 AND net_total >= 0 AND gross_total >= 0", name="ck_bestellungen_totals"),
        sa.ForeignKeyConstraint(["contact_id"], ["kontakte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deal_id"], ["verkaufschancen.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["vertriebspartner.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_number", name="uq_bestellungen_order_number"),
        sa.UniqueConstraint("demo_key", name="uq_bestellungen_demo_key"),
    )
    op.create_index("ix_bestellungen_partner", "bestellungen", ["partner_id"])
    op.create_index("ix_bestellungen_status", "bestellungen", ["status"])
    op.create_index("ix_bestellungen_ordered_on", "bestellungen", ["ordered_on"])
    op.execute(
        """
        CREATE UNIQUE INDEX uq_bestellungen_erp_reference
        ON bestellungen (lower(erp_reference))
        WHERE erp_reference IS NOT NULL
        """
    )

    op.create_table(
        "bestellpositionen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=200), nullable=False),
        sa.Column("sku", sa.String(length=40), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("vat_rate", sa.Numeric(5, 2), nullable=False),
        sa.Column("line_net", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_vat", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_gross", sa.Numeric(12, 2), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_bestellpositionen_quantity"),
        sa.CheckConstraint("unit_price >= 0", name="ck_bestellpositionen_price"),
        sa.CheckConstraint("discount_percent >= 0 AND discount_percent <= 100", name="ck_bestellpositionen_discount"),
        sa.CheckConstraint("vat_rate >= 0 AND vat_rate <= 100", name="ck_bestellpositionen_vat"),
        sa.ForeignKeyConstraint(["order_id"], ["bestellungen.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["product_id"], ["produkte.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "position", name="uq_bestellpositionen_position"),
    )
    op.create_index("ix_bestellpositionen_product", "bestellpositionen", ["product_id"])


def downgrade() -> None:
    op.drop_index("ix_bestellpositionen_product", table_name="bestellpositionen")
    op.drop_table("bestellpositionen")
    op.execute("DROP INDEX IF EXISTS uq_bestellungen_erp_reference")
    op.drop_index("ix_bestellungen_ordered_on", table_name="bestellungen")
    op.drop_index("ix_bestellungen_status", table_name="bestellungen")
    op.drop_index("ix_bestellungen_partner", table_name="bestellungen")
    op.drop_table("bestellungen")
    op.execute("DROP INDEX IF EXISTS uq_produkte_sku")
    op.drop_index("ix_produkte_category", table_name="produkte")
    op.drop_index("ix_produkte_name", table_name="produkte")
    op.drop_table("produkte")
    op.drop_index("ix_verkaufschancen_phasen_deal", table_name="verkaufschancen_phasen")
    op.drop_table("verkaufschancen_phasen")
    op.drop_index("ix_verkaufschancen_expected_close", table_name="verkaufschancen")
    op.drop_index("ix_verkaufschancen_stage", table_name="verkaufschancen")
    op.drop_index("ix_verkaufschancen_partner", table_name="verkaufschancen")
    op.drop_table("verkaufschancen")
