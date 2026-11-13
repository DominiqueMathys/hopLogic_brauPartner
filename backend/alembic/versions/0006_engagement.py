"""Campaigns, care rules, automations and notifications.

Revision ID: 0006_engagement
Revises: 0005_service
Create Date: 2026-11-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_engagement"
down_revision: Union[str, Sequence[str], None] = "0005_service"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "kampagnen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("campaign_type", sa.String(length=40), nullable=False),
        sa.Column("account_owner", sa.String(length=120), nullable=True),
        sa.Column("starts_on", sa.Date(), nullable=True),
        sa.Column("ends_on", sa.Date(), nullable=True),
        sa.Column("objective", sa.Text(), nullable=True),
        sa.Column("audience_kind", sa.String(length=20), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=True),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("budget", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("internal_note", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "campaign_type IN ('produkteinfuehrung', 'saisonal', 'partnerinformation', 'rueckgewinnung', 'event', 'individuell')",
            name="ck_kampagnen_type",
        ),
        sa.CheckConstraint(
            "status IN ('entwurf', 'geplant', 'aktiv', 'pausiert', 'abgeschlossen', 'archiviert')",
            name="ck_kampagnen_status",
        ),
        sa.CheckConstraint("audience_kind IN ('segment', 'partners', 'contacts')", name="ck_kampagnen_audience"),
        sa.CheckConstraint("channel IN ('email', 'telefon', 'besuch', 'brief', 'sonstige')", name="ck_kampagnen_channel"),
        sa.CheckConstraint("ends_on IS NULL OR starts_on IS NULL OR ends_on >= starts_on", name="ck_kampagnen_dates"),
        sa.ForeignKeyConstraint(["segment_id"], ["kundensegmente.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_kampagnen_demo_key"),
    )
    op.create_index("ix_kampagnen_status", "kampagnen", ["status"])
    op.create_index("ix_kampagnen_owner", "kampagnen", ["account_owner"])
    op.create_index("ix_kampagnen_type", "kampagnen", ["campaign_type"])

    op.create_table(
        "kampagnen_zielgruppe",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("contact_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "(partner_id IS NOT NULL AND contact_id IS NULL) OR (partner_id IS NULL AND contact_id IS NOT NULL)",
            name="ck_kampagnen_zielgruppe_target",
        ),
        sa.ForeignKeyConstraint(["campaign_id"], ["kampagnen.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["partner_id"], ["vertriebspartner.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["contact_id"], ["kontakte.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_kampagnen_zielgruppe_campaign", "kampagnen_zielgruppe", ["campaign_id"])
    op.create_index(
        "uq_kampagnen_zielgruppe_partner",
        "kampagnen_zielgruppe",
        ["campaign_id", "partner_id"],
        unique=True,
        postgresql_where=sa.text("partner_id IS NOT NULL"),
    )
    op.create_index(
        "uq_kampagnen_zielgruppe_contact",
        "kampagnen_zielgruppe",
        ["campaign_id", "contact_id"],
        unique=True,
        postgresql_where=sa.text("contact_id IS NOT NULL"),
    )

    op.create_table(
        "kampagnen_empfaenger",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("company_name", sa.String(length=160), server_default="", nullable=False),
        sa.Column("job_title", sa.String(length=120), server_default="", nullable=False),
        sa.Column("included", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("exclusion_reason", sa.String(length=200), nullable=True),
        sa.Column("frozen_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["kampagnen.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["contact_id"], ["kontakte.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["partner_id"], ["vertriebspartner.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("campaign_id", "contact_id", name="uq_kampagnen_empfaenger"),
    )
    op.create_index("ix_kampagnen_empfaenger_campaign", "kampagnen_empfaenger", ["campaign_id"])

    op.create_table(
        "nachrichtenvorlagen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("subject", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("channel", sa.String(length=20), nullable=False),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("channel IN ('email', 'telefon', 'besuch', 'brief', 'sonstige')", name="ck_vorlagen_channel"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_vorlagen_demo_key"),
    )
    op.create_index("ix_vorlagen_name", "nachrichtenvorlagen", ["name"])

    op.create_table(
        "kommunikationspraeferenzen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("contact_id", sa.Uuid(), nullable=False),
        sa.Column("preferred_channel", sa.String(length=20), nullable=False),
        sa.Column("email_marketing_allowed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("marketing_rejected", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("consent_on", sa.Date(), nullable=True),
        sa.Column("consent_source", sa.String(length=200), nullable=True),
        sa.Column("consent_evidence", sa.Text(), nullable=True),
        sa.Column("revoked_on", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("preferred_channel IN ('email', 'telefon', 'besuch', 'brief', 'sonstige')", name="ck_praeferenz_channel"),
        sa.CheckConstraint("NOT (email_marketing_allowed AND marketing_rejected)", name="ck_praeferenz_consent"),
        sa.ForeignKeyConstraint(["contact_id"], ["kontakte.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("contact_id", name="uq_praeferenz_contact"),
    )

    op.create_table(
        "betreuungsregeln",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("rule_kind", sa.String(length=40), nullable=False),
        sa.Column("threshold_days", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("create_tasks", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("task_title", sa.String(length=200), nullable=False),
        sa.Column("account_owner", sa.String(length=120), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "rule_kind IN ('no_contact', 'no_order', 'stale_deal', 'stale_ticket')",
            name="ck_betreuung_kind",
        ),
        sa.CheckConstraint("threshold_days >= 1 AND threshold_days <= 3650", name="ck_betreuung_days"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_betreuung_demo_key"),
    )
    op.create_index("ix_betreuung_active", "betreuungsregeln", ["is_active"])

    op.create_table(
        "automatisierungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("trigger_type", sa.String(length=40), nullable=False),
        sa.Column("trigger_config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("action_type", sa.String(length=40), nullable=False),
        sa.Column("action_config", postgresql.JSONB(), server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("account_owner", sa.String(length=120), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "trigger_type IN ('deal_created', 'deal_stage_changed', 'partner_created', 'ticket_created', 'ticket_priority_changed', 'order_created', 'task_due_soon', 'task_overdue', 'no_contact', 'no_order', 'ticket_stale')",
            name="ck_automatisierung_trigger",
        ),
        sa.CheckConstraint(
            "action_type IN ('create_task', 'notify_owner', 'create_reminder', 'log_activity')",
            name="ck_automatisierung_action",
        ),
        sa.CheckConstraint(
            "status IN ('entwurf', 'aktiv', 'pausiert', 'deaktiviert')",
            name="ck_automatisierung_status",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_automatisierung_demo_key"),
    )
    op.create_index("ix_automatisierung_status", "automatisierungen", ["status"])
    op.create_index("ix_automatisierung_trigger", "automatisierungen", ["trigger_type"])

    op.create_table(
        "benachrichtigungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("notification_type", sa.String(length=40), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("recipient_label", sa.String(length=120), nullable=False),
        sa.Column("href", sa.String(length=200), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("partner_id", sa.Uuid(), nullable=True),
        sa.Column("deal_id", sa.Uuid(), nullable=True),
        sa.Column("ticket_id", sa.Uuid(), nullable=True),
        sa.Column("automation_id", sa.Uuid(), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("demo_key", sa.String(length=80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint(
            "notification_type IN ('task_assigned', 'task_due_soon', 'task_overdue', 'critical_ticket', 'deal_assigned', 'automation_failed', 'general')",
            name="ck_benachrichtigung_type",
        ),
        sa.ForeignKeyConstraint(["task_id"], ["aufgaben.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["partner_id"], ["vertriebspartner.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("demo_key", name="uq_benachrichtigung_demo_key"),
    )
    op.create_index("ix_benachrichtigung_recipient", "benachrichtigungen", ["recipient_label"])
    op.create_index("ix_benachrichtigung_read", "benachrichtigungen", ["read_at"])
    op.create_index("ix_benachrichtigung_type", "benachrichtigungen", ["notification_type"])

    op.create_table(
        "benachrichtigungseinstellungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("recipient_label", sa.String(length=120), nullable=False),
        sa.Column("task_reminders", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("service_alerts", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("deal_alerts", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("automation_errors", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("recipient_label", name="uq_benachrichtigung_empfaenger"),
    )

    op.create_table(
        "betreuungs_ausfuehrungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.CheckConstraint("status IN ('erfolg', 'fehler', 'uebersprungen')", name="ck_betreuung_ausfuehrung_status"),
        sa.ForeignKeyConstraint(["rule_id"], ["betreuungsregeln.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["aufgaben.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_betreuung_ausfuehrung_erfolg",
        "betreuungs_ausfuehrungen",
        ["rule_id", "dedupe_key"],
        unique=True,
        postgresql_where=sa.text("status = 'erfolg'"),
    )

    op.create_table(
        "automatisierung_ausfuehrungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("rule_id", sa.Uuid(), nullable=False),
        sa.Column("dedupe_key", sa.String(length=200), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("task_id", sa.Uuid(), nullable=True),
        sa.Column("notification_id", sa.Uuid(), nullable=True),
        sa.Column("activity_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("status IN ('erfolg', 'fehler', 'uebersprungen')", name="ck_ausfuehrung_status"),
        sa.ForeignKeyConstraint(["rule_id"], ["automatisierungen.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["task_id"], ["aufgaben.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["activity_id"], ["aktivitaeten.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ausfuehrung_rule", "automatisierung_ausfuehrungen", ["rule_id"])
    op.create_index(
        "uq_ausfuehrung_erfolg",
        "automatisierung_ausfuehrungen",
        ["rule_id", "dedupe_key"],
        unique=True,
        postgresql_where=sa.text("status = 'erfolg'"),
    )

    op.add_column("aufgaben", sa.Column("origin", sa.String(length=20), nullable=True))
    op.create_index("ix_aufgaben_origin", "aufgaben", ["origin"])


def downgrade() -> None:
    op.drop_index("ix_aufgaben_origin", table_name="aufgaben")
    op.drop_column("aufgaben", "origin")
    op.drop_table("automatisierung_ausfuehrungen")
    op.drop_table("betreuungs_ausfuehrungen")
    op.drop_table("benachrichtigungseinstellungen")
    op.drop_table("benachrichtigungen")
    op.drop_table("automatisierungen")
    op.drop_table("betreuungsregeln")
    op.drop_table("kommunikationspraeferenzen")
    op.drop_table("nachrichtenvorlagen")
    op.drop_table("kampagnen_empfaenger")
    op.drop_table("kampagnen_zielgruppe")
    op.drop_table("kampagnen")
