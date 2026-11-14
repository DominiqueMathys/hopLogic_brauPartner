"""ERP integration tables and external status fields.

Revision ID: 0008_integration
Revises: 0007_identity
Create Date: 2026-11-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0008_integration"
down_revision: Union[str, Sequence[str], None] = "0007_identity"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("vertriebspartner", sa.Column("erp_customer_status", sa.String(length=40), nullable=True))
    op.add_column("vertriebspartner", sa.Column("erp_source", sa.String(length=20), nullable=True))
    op.add_column("vertriebspartner", sa.Column("erp_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("produkte", sa.Column("currency", sa.String(length=3), nullable=False, server_default="CHF"))
    op.add_column("produkte", sa.Column("erp_source", sa.String(length=20), nullable=True))
    op.add_column("produkte", sa.Column("erp_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bestellungen", sa.Column("transfer_status", sa.String(length=30), nullable=False, server_default="nicht_uebertragen"))
    op.add_column("bestellungen", sa.Column("erp_status", sa.String(length=40), nullable=True))
    op.add_column("bestellungen", sa.Column("erp_status_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("bestellungen", sa.Column("erp_status_source", sa.String(length=20), nullable=True))
    op.add_column("bestellungen", sa.Column("delivery_on", sa.Date(), nullable=True))
    op.add_column("bestellungen", sa.Column("delivery_note", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("bestellungen", sa.Column("delivery_status", sa.String(length=40), nullable=False, server_default=""))
    op.add_column("bestellungen", sa.Column("invoice_number", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("bestellungen", sa.Column("invoice_on", sa.Date(), nullable=True))
    op.add_column("bestellungen", sa.Column("invoice_status", sa.String(length=120), nullable=False, server_default=""))
    op.create_check_constraint(
        "ck_bestellungen_transfer_status",
        "bestellungen",
        "transfer_status IN ('nicht_uebertragen', 'bereit', 'in_uebertragung', 'erfolgreich', 'fehlgeschlagen', 'manuelle_pruefung')",
    )
    op.create_table(
        "erp_verbindungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("mode", sa.String(length=30), nullable=False, server_default="nicht_konfiguriert"),
        sa.Column("customers_interval_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("products_interval_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status_interval_minutes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("auto_order_transfer", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("connection_ok", sa.Boolean(), nullable=True),
        sa.Column("last_tested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_failure_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_customers_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_products_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_status_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("running_kind", sa.String(length=40), nullable=True),
        sa.Column("running_since", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("mode IN ('nicht_konfiguriert', 'mock', 'extern')", name="ck_erp_verbindungen_mode"),
        sa.CheckConstraint("auto_order_transfer IS FALSE", name="ck_erp_verbindungen_keine_auto_uebertragung"),
        sa.CheckConstraint("customers_interval_minutes >= 0 AND products_interval_minutes >= 0 AND status_interval_minutes >= 0", name="ck_erp_verbindungen_intervalle"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "erp_sync_laeufe",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("dry_run", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("kind IN ('kunden', 'produkte', 'bestellstatus', 'uebertragung', 'verbindungstest')", name="ck_erp_sync_laeufe_kind"),
        sa.CheckConstraint("status IN ('erfolgreich', 'fehlgeschlagen', 'teilweise')", name="ck_erp_sync_laeufe_status"),
        sa.ForeignKeyConstraint(["actor_id"], ["benutzer.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_erp_sync_laeufe_started", "erp_sync_laeufe", ["started_at"])
    op.create_table(
        "erp_sync_eintraege",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("job_id", sa.Uuid(), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("external_key", sa.String(length=80), nullable=False),
        sa.Column("action", sa.String(length=30), nullable=False),
        sa.Column("message", sa.Text(), nullable=False, server_default=""),
        sa.Column("crm_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("action IN ('neu', 'aktualisiert', 'unveraendert', 'konflikt', 'ungueltig', 'uebertragen')", name="ck_erp_sync_eintraege_action"),
        sa.ForeignKeyConstraint(["job_id"], ["erp_sync_laeufe.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_erp_sync_eintraege_job", "erp_sync_eintraege", ["job_id"])
    op.create_table(
        "erp_referenzen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("external_key", sa.String(length=80), nullable=False),
        sa.Column("crm_id", sa.Uuid(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "entity_type", "external_key", name="uq_erp_referenzen_extern"),
    )
    op.create_index("ix_erp_referenzen_crm", "erp_referenzen", ["entity_type", "crm_id"])
    op.create_table(
        "erp_konflikte",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("kind", sa.String(length=60), nullable=False),
        sa.Column("entity_type", sa.String(length=40), nullable=False),
        sa.Column("external_key", sa.String(length=80), nullable=False),
        sa.Column("crm_id", sa.Uuid(), nullable=True),
        sa.Column("field_name", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("crm_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("external_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="offen"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reviewed_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint("status IN ('offen', 'geprueft')", name="ck_erp_konflikte_status"),
        sa.ForeignKeyConstraint(["reviewed_by"], ["benutzer.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_erp_konflikte_status", "erp_konflikte", ["status"])
    op.create_table(
        "erp_uebertragungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("order_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("external_reference", sa.String(length=80), nullable=True),
        sa.Column("external_status", sa.String(length=40), nullable=True),
        sa.Column("external_status_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=False, server_default=""),
        sa.Column("delivery_on", sa.Date(), nullable=True),
        sa.Column("delivery_note", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("delivery_status", sa.String(length=40), nullable=False, server_default=""),
        sa.Column("invoice_number", sa.String(length=80), nullable=False, server_default=""),
        sa.Column("invoice_on", sa.Date(), nullable=True),
        sa.Column("invoice_status", sa.String(length=120), nullable=False, server_default=""),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('nicht_uebertragen', 'bereit', 'in_uebertragung', 'erfolgreich', 'fehlgeschlagen', 'manuelle_pruefung')",
            name="ck_erp_uebertragungen_status",
        ),
        sa.ForeignKeyConstraint(["order_id"], ["bestellungen.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_erp_uebertragungen_order"),
        sa.UniqueConstraint("idempotency_key", name="uq_erp_uebertragungen_key"),
    )


def downgrade() -> None:
    op.drop_table("erp_uebertragungen")
    op.drop_index("ix_erp_konflikte_status", table_name="erp_konflikte")
    op.drop_table("erp_konflikte")
    op.drop_index("ix_erp_referenzen_crm", table_name="erp_referenzen")
    op.drop_table("erp_referenzen")
    op.drop_index("ix_erp_sync_eintraege_job", table_name="erp_sync_eintraege")
    op.drop_table("erp_sync_eintraege")
    op.drop_index("ix_erp_sync_laeufe_started", table_name="erp_sync_laeufe")
    op.drop_table("erp_sync_laeufe")
    op.drop_table("erp_verbindungen")
    op.drop_constraint("ck_bestellungen_transfer_status", "bestellungen", type_="check")
    for column in (
        "invoice_status",
        "invoice_on",
        "invoice_number",
        "delivery_status",
        "delivery_note",
        "delivery_on",
        "erp_status_source",
        "erp_status_at",
        "erp_status",
        "transfer_status",
    ):
        op.drop_column("bestellungen", column)
    for column in ("erp_synced_at", "erp_source", "currency"):
        op.drop_column("produkte", column)
    for column in ("erp_synced_at", "erp_source", "erp_customer_status"):
        op.drop_column("vertriebspartner", column)
