from datetime import date, datetime
from uuid import UUID
from weakref import WeakKeyDictionary

from sqlalchemy import func, nulls_last, select
from sqlalchemy.orm import Session

from app.crm_catalog import OPEN_TASK_STATUSES
from app.models.activity import Activity
from app.models.partner import Partner
from app.models.task import Task

_partner_last: WeakKeyDictionary[Partner, datetime | None] = WeakKeyDictionary()
_partner_next: WeakKeyDictionary[Partner, date | None] = WeakKeyDictionary()


def partner_last_contact(partner: Partner) -> datetime | None:
    return _partner_last.get(partner)


def partner_next_activity(partner: Partner) -> date | None:
    return _partner_next.get(partner)


def attach_partner_timeline(db: Session, partners: list[Partner]) -> None:
    if not partners:
        return
    ids = [partner.id for partner in partners]
    last_rows = db.execute(
        select(Activity.partner_id, func.max(Activity.occurred_at))
        .where(Activity.partner_id.in_(ids), Activity.archived_at.is_(None))
        .group_by(Activity.partner_id)
    ).all()
    next_rows = db.execute(
        select(Task.partner_id, func.min(Task.due_at))
        .where(Task.partner_id.in_(ids), Task.status.in_(OPEN_TASK_STATUSES))
        .group_by(Task.partner_id)
    ).all()
    last_map = {row[0]: row[1] for row in last_rows}
    next_map = {row[0]: row[1] for row in next_rows}
    for partner in partners:
        _partner_last[partner] = last_map.get(partner.id)
        due = next_map.get(partner.id)
        _partner_next[partner] = due.date() if isinstance(due, datetime) else None


def last_activity_expression(direction: str):
    expression = (
        select(func.max(Activity.occurred_at))
        .where(Activity.partner_id == Partner.id, Activity.archived_at.is_(None))
        .correlate(Partner)
        .scalar_subquery()
    )
    ordered = expression.desc() if direction == "desc" else expression.asc()
    return nulls_last(ordered)


def contact_last_map(db: Session, contact_ids: list[UUID]) -> dict[UUID, datetime]:
    if not contact_ids:
        return {}
    rows = db.execute(
        select(Activity.contact_id, func.max(Activity.occurred_at))
        .where(Activity.contact_id.in_(contact_ids), Activity.archived_at.is_(None))
        .group_by(Activity.contact_id)
    ).all()
    return {row[0]: row[1] for row in rows if row[0] is not None}


def contact_last_expression(direction: str):
    from app.models.contact import Contact

    expression = (
        select(func.max(Activity.occurred_at))
        .where(Activity.contact_id == Contact.id, Activity.archived_at.is_(None))
        .correlate(Contact)
        .scalar_subquery()
    )
    ordered = expression.desc() if direction == "desc" else expression.asc()
    return nulls_last(ordered)
