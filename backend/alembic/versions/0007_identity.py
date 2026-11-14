"""Users, roles, sessions, audit log and optional owner links.

Revision ID: 0007_identity
Revises: 0006_engagement
Create Date: 2026-11-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_identity"
down_revision: Union[str, Sequence[str], None] = "0006_engagement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rollen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=40), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_rollen_code"),
    )
    op.create_table(
        "berechtigungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=60), nullable=False),
        sa.Column("resource", sa.String(length=40), nullable=False),
        sa.Column("action", sa.String(length=20), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code", name="uq_berechtigungen_code"),
    )
    op.create_table(
        "rollen_berechtigungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("permission_id", sa.Uuid(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["berechtigungen.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["rollen.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_rollen_berechtigungen"),
    )
    op.create_table(
        "benutzer",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("email", sa.String(length=200), nullable=False),
        sa.Column("password_hash", sa.String(length=200), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'aktiv'"), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("password_changed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_demo", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('aktiv', 'deaktiviert')", name="ck_benutzer_status"),
        sa.ForeignKeyConstraint(["role_id"], ["rollen.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_benutzer_email"),
    )
    op.create_index("ix_benutzer_role", "benutzer", ["role_id"])
    op.create_index("ix_benutzer_status", "benutzer", ["status"])
    op.create_table(
        "sitzungen",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("csrf_token", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["benutzer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_sitzungen_token"),
    )
    op.create_index("ix_sitzungen_user", "sitzungen", ["user_id"])
    op.create_table(
        "passwort_resets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["benutzer.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash", name="uq_passwort_resets_token"),
    )
    op.create_index("ix_passwort_resets_user", "passwort_resets", ["user_id"])
    op.create_table(
        "audit_protokoll",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=40), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_label", sa.String(length=200), nullable=True),
        sa.Column("resource_type", sa.String(length=40), nullable=True),
        sa.Column("resource_id", sa.String(length=80), nullable=True),
        sa.Column("result", sa.String(length=20), nullable=False),
        sa.Column("detail", sa.String(length=300), nullable=True),
        sa.CheckConstraint("result IN ('erfolg', 'abgelehnt')", name="ck_audit_result"),
        sa.ForeignKeyConstraint(["actor_id"], ["benutzer.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_occurred", "audit_protokoll", ["occurred_at"])
    op.create_index("ix_audit_event", "audit_protokoll", ["event_type"])
    for table in (
        "vertriebspartner",
        "kontakte",
        "aktivitaeten",
        "aufgaben",
        "verkaufschancen",
        "service_tickets",
        "kampagnen",
        "automatisierungen",
    ):
        op.add_column(table, sa.Column("owner_user_id", sa.Uuid(), nullable=True))
        op.create_foreign_key(f"fk_{table}_owner_user", table, "benutzer", ["owner_user_id"], ["id"], ondelete="SET NULL")
        op.create_index(f"ix_{table}_owner_user", table, ["owner_user_id"])
    op.add_column("benachrichtigungen", sa.Column("user_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_benachrichtigungen_user", "benachrichtigungen", "benutzer", ["user_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_benachrichtigungen_user", "benachrichtigungen", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_benachrichtigungen_user", table_name="benachrichtigungen")
    op.drop_constraint("fk_benachrichtigungen_user", "benachrichtigungen", type_="foreignkey")
    op.drop_column("benachrichtigungen", "user_id")
    for table in (
        "automatisierungen",
        "kampagnen",
        "service_tickets",
        "verkaufschancen",
        "aufgaben",
        "aktivitaeten",
        "kontakte",
        "vertriebspartner",
    ):
        op.drop_index(f"ix_{table}_owner_user", table_name=table)
        op.drop_constraint(f"fk_{table}_owner_user", table, type_="foreignkey")
        op.drop_column(table, "owner_user_id")
    op.drop_index("ix_audit_event", table_name="audit_protokoll")
    op.drop_index("ix_audit_occurred", table_name="audit_protokoll")
    op.drop_table("audit_protokoll")
    op.drop_index("ix_passwort_resets_user", table_name="passwort_resets")
    op.drop_table("passwort_resets")
    op.drop_index("ix_sitzungen_user", table_name="sitzungen")
    op.drop_table("sitzungen")
    op.drop_index("ix_benutzer_status", table_name="benutzer")
    op.drop_index("ix_benutzer_role", table_name="benutzer")
    op.drop_table("benutzer")
    op.drop_table("rollen_berechtigungen")
    op.drop_table("berechtigungen")
    op.drop_table("rollen")
