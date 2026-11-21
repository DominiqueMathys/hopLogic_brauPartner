"""Festival management, materials and links from tasks, activities and tickets.

Revision ID: 0009_festivals
Revises: 0008_integration
Create Date: 2026-11-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.database import Base
from app.models.festival import (
    Festival,
    FestivalAssignment,
    FestivalChange,
    FestivalDelivery,
    FestivalMaterial,
    FestivalQuote,
    FestivalQuoteItem,
    MaterialAsset,
    MaterialCategory,
    MaterialIssue,
    MaterialMovement,
    MaterialReservation,
    MaterialReservationLine,
    MaterialReturn,
    NumberRange,
)

revision: str = "0009_festivals"
down_revision: Union[str, Sequence[str], None] = "0008_integration"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FESTIVAL_TABLES = (
    NumberRange.__table__,
    MaterialCategory.__table__,
    Festival.__table__,
    FestivalChange.__table__,
    FestivalMaterial.__table__,
    MaterialAsset.__table__,
    MaterialReservation.__table__,
    MaterialReservationLine.__table__,
    MaterialMovement.__table__,
    MaterialIssue.__table__,
    MaterialReturn.__table__,
    FestivalQuote.__table__,
    FestivalQuoteItem.__table__,
    FestivalDelivery.__table__,
    FestivalAssignment.__table__,
)

PREVIOUS_TRIGGERS = (
    "trigger_type IN ('deal_created', 'deal_stage_changed', 'partner_created', "
    "'ticket_created', 'ticket_priority_changed', 'order_created', 'task_due_soon', "
    "'task_overdue', 'no_contact', 'no_order', 'ticket_stale')"
)

CURRENT_TRIGGERS = (
    "trigger_type IN ('deal_created', 'deal_stage_changed', 'partner_created', "
    "'ticket_created', 'ticket_priority_changed', 'order_created', "
    "'festival_request_created', 'festival_quote_accepted', 'festival_material_short', "
    "'festival_material_damaged', 'task_due_soon', 'task_overdue', 'no_contact', "
    "'no_order', 'ticket_stale', 'festival_quote_waiting', 'festival_starts_soon', "
    "'festival_delivery_due', 'festival_ended', 'festival_return_overdue')"
)


def upgrade() -> None:
    Base.metadata.create_all(op.get_bind(), tables=list(FESTIVAL_TABLES))
    op.add_column("aufgaben", sa.Column("event_id", sa.Uuid(), nullable=True))
    op.add_column("aktivitaeten", sa.Column("event_id", sa.Uuid(), nullable=True))
    op.add_column("service_tickets", sa.Column("event_id", sa.Uuid(), nullable=True))
    op.create_foreign_key("fk_aufgaben_fest", "aufgaben", "feste", ["event_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_aktivitaeten_fest", "aktivitaeten", "feste", ["event_id"], ["id"], ondelete="RESTRICT")
    op.create_foreign_key("fk_service_tickets_fest", "service_tickets", "feste", ["event_id"], ["id"], ondelete="RESTRICT")
    op.create_index("ix_aufgaben_fest", "aufgaben", ["event_id"])
    op.create_index("ix_aktivitaeten_fest", "aktivitaeten", ["event_id"])
    op.create_index("ix_service_tickets_fest", "service_tickets", ["event_id"])
    op.drop_constraint("ck_automatisierung_trigger", "automatisierungen", type_="check")
    op.create_check_constraint("ck_automatisierung_trigger", "automatisierungen", CURRENT_TRIGGERS)


def downgrade() -> None:
    op.drop_constraint("ck_automatisierung_trigger", "automatisierungen", type_="check")
    op.create_check_constraint("ck_automatisierung_trigger", "automatisierungen", PREVIOUS_TRIGGERS)
    op.drop_index("ix_service_tickets_fest", table_name="service_tickets")
    op.drop_index("ix_aktivitaeten_fest", table_name="aktivitaeten")
    op.drop_index("ix_aufgaben_fest", table_name="aufgaben")
    op.drop_constraint("fk_service_tickets_fest", "service_tickets", type_="foreignkey")
    op.drop_constraint("fk_aktivitaeten_fest", "aktivitaeten", type_="foreignkey")
    op.drop_constraint("fk_aufgaben_fest", "aufgaben", type_="foreignkey")
    op.drop_column("service_tickets", "event_id")
    op.drop_column("aktivitaeten", "event_id")
    op.drop_column("aufgaben", "event_id")
    for table in reversed(FESTIVAL_TABLES):
        op.drop_table(table.name)
