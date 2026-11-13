"""Shared CRM lookups for care rules and time-based automations.

Dates are compared in Europe/Zurich. Stored timestamps stay timezone-aware.
"""

from datetime import date, datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crm_catalog import OPEN_TASK_STATUSES
from app.models.activity import Activity
from app.models.partner import Partner
from app.models.sales import Deal, Order
from app.models.service import ServiceTicket
from app.models.task import Task
from app.sales_catalog import CLOSED_DEAL_STAGES, COUNTED_ORDER_STATUSES
from app.service_catalog import COMPLAINT_CATEGORIES, OPEN_TICKET_STATUSES

ZURICH = ZoneInfo("Europe/Zurich")
OPEN_ENDED_GAP = 100000


def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def zurich_day(value: datetime) -> date:
    return as_utc(value).astimezone(ZURICH).date()


def zurich_today(now: datetime | None = None) -> date:
    return zurich_day(now or datetime.now(timezone.utc))


def gap_from(today: date, moment: datetime | date | None) -> int:
    if moment is None:
        return OPEN_ENDED_GAP
    if isinstance(moment, datetime):
        moment = zurich_day(moment)
    return (today - moment).days


def active_partners(db: Session) -> list[Partner]:
    return list(db.scalars(select(Partner).where(Partner.archived_at.is_(None)).order_by(Partner.company_name)).all())


def last_contact_at(db: Session, partner_id: UUID) -> datetime | None:
    return db.scalar(
        select(func.max(Activity.occurred_at)).where(
            Activity.partner_id == partner_id,
            Activity.archived_at.is_(None),
        )
    )


def last_counted_order_on(db: Session, partner_id: UUID) -> date | None:
    return db.scalar(
        select(func.max(Order.ordered_on)).where(
            Order.partner_id == partner_id,
            Order.status.in_(COUNTED_ORDER_STATUSES),
        )
    )


def open_task_count(db: Session, partner_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(Task).where(
                Task.partner_id == partner_id,
                Task.status.in_(OPEN_TASK_STATUSES),
            )
        )
        or 0
    )


def open_ticket_count(db: Session, partner_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(ServiceTicket).where(
                ServiceTicket.partner_id == partner_id,
                ServiceTicket.status.in_(OPEN_TICKET_STATUSES),
            )
        )
        or 0
    )


def open_complaint_count(db: Session, partner_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(ServiceTicket).where(
                ServiceTicket.partner_id == partner_id,
                ServiceTicket.status.in_(OPEN_TICKET_STATUSES),
                ServiceTicket.category.in_(COMPLAINT_CATEGORIES),
            )
        )
        or 0
    )


def open_deal_count(db: Session, partner_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count()).select_from(Deal).where(
                Deal.partner_id == partner_id,
                Deal.archived_at.is_(None),
                Deal.stage.not_in(CLOSED_DEAL_STAGES),
            )
        )
        or 0
    )


def next_open_task_at(db: Session, partner_id: UUID) -> datetime | None:
    return db.scalar(
        select(func.min(Task.due_at)).where(
            Task.partner_id == partner_id,
            Task.status.in_(OPEN_TASK_STATUSES),
        )
    )


def contact_marker(moment: datetime | None) -> str:
    if moment is None:
        return "none"
    return as_utc(moment).isoformat()


def partners_quiet_since(db: Session, days: int, today: date) -> list[tuple[Partner, str]]:
    found = []
    for partner in active_partners(db):
        moment = last_contact_at(db, partner.id)
        if gap_from(today, moment) >= days:
            found.append((partner, contact_marker(moment)))
    return found


def partners_without_orders_since(db: Session, days: int, today: date) -> list[tuple[Partner, str]]:
    found = []
    for partner in active_partners(db):
        moment = last_counted_order_on(db, partner.id)
        if gap_from(today, moment) >= days:
            found.append((partner, moment.isoformat() if moment else "none"))
    return found


def stale_open_tickets(db: Session, days: int, now: datetime) -> list[ServiceTicket]:
    cutoff = as_utc(now) - timedelta(days=days)
    return list(
        db.scalars(
            select(ServiceTicket).where(
                ServiceTicket.status.in_(OPEN_TICKET_STATUSES),
                ServiceTicket.updated_at <= cutoff,
            )
        ).all()
    )


def deals_without_recent_activity(db: Session, days: int, today: date) -> list[Deal]:
    found = []
    deals = db.scalars(
        select(Deal).where(Deal.archived_at.is_(None), Deal.stage.not_in(CLOSED_DEAL_STAGES))
    ).all()
    for deal in deals:
        activity = last_contact_at(db, deal.partner_id)
        activity_gap = gap_from(today, activity)
        deal_gap = gap_from(today, deal.updated_at)
        if activity_gap >= days and deal_gap >= days:
            found.append(deal)
    return found


def open_tasks_overdue(db: Session, now: datetime) -> list[Task]:
    return list(
        db.scalars(
            select(Task).where(Task.status.in_(OPEN_TASK_STATUSES), Task.due_at < as_utc(now))
        ).all()
    )


def open_tasks_due_soon(db: Session, now: datetime, days: int) -> list[Task]:
    current = as_utc(now)
    horizon = current + timedelta(days=days)
    return list(
        db.scalars(
            select(Task).where(
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.due_at >= current,
                Task.due_at <= horizon,
            )
        ).all()
    )
