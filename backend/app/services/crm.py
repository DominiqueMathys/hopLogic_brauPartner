from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.crm_catalog import OPEN_TASK_STATUSES
from app.models.activity import Activity
from app.models.contact import CompanyContact, Contact
from app.models.partner import Partner
from app.models.task import Task
from app.schemas.activity import ActivityRead, ActivityWrite, FollowUpWrite, NoteWithTaskWrite
from app.schemas.contact import (
    CompanyLinkRead,
    CompanyOption,
    ContactRead,
    ContactWrite,
)
from app.schemas.task import TaskRead, TaskWrite
from app.services.partners import contains_pattern, distinct_text, require_partner
from app.services.timeline import contact_last_expression, contact_last_map

SOON = timedelta(days=7)

CONTACT_FIELDS = (
    "first_name",
    "last_name",
    "job_title",
    "email",
    "phone",
    "mobile",
    "account_owner",
    "preferred_language",
    "preferred_channel",
    "lifecycle_phase",
    "lead_status",
    "status",
    "notes",
    "processing_basis",
    "processing_basis_note",
)

ACTIVITY_FIELDS = (
    "activity_type",
    "title",
    "description",
    "occurred_at",
    "account_owner",
    "contact_id",
    "partner_id",
)

TASK_FIELDS = (
    "title",
    "description",
    "account_owner",
    "due_at",
    "priority",
    "status",
    "task_type",
    "partner_id",
    "contact_id",
    "activity_id",
)


class CrmServiceError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def require_contact(db: Session, contact_id: UUID) -> Contact:
    contact = db.get(Contact, contact_id)
    if contact is None:
        raise CrmServiceError("Der Kontakt wurde nicht gefunden.", 404)
    return contact


def require_activity(db: Session, activity_id: UUID) -> Activity:
    activity = db.get(Activity, activity_id)
    if activity is None:
        raise CrmServiceError("Die Aktivität wurde nicht gefunden.", 404)
    return activity


def require_task(db: Session, task_id: UUID) -> Task:
    task = db.get(Task, task_id)
    if task is None:
        raise CrmServiceError("Die Aufgabe wurde nicht gefunden.", 404)
    return task


def _ensure_partner(db: Session, partner_id: UUID | None, *, allow_archived: bool) -> None:
    if partner_id is None:
        return
    partner = require_partner(db, partner_id)
    if partner.archived_at is not None and not allow_archived:
        raise CrmServiceError("Archivierte Partner können nicht neu zugeordnet werden.", 409)


def _ensure_contact_exists(db: Session, contact_id: UUID | None) -> None:
    if contact_id is None:
        return
    require_contact(db, contact_id)


def _ensure_activity_exists(db: Session, activity_id: UUID | None) -> None:
    if activity_id is None:
        return
    require_activity(db, activity_id)


def ensure_contact_email(db: Session, email: str | None, exclude_id: UUID | None = None) -> None:
    if not email:
        return
    statement = select(Contact.id).where(func.lower(Contact.email) == email.casefold())
    if exclude_id is not None:
        statement = statement.where(Contact.id != exclude_id)
    if db.scalar(statement) is not None:
        raise CrmServiceError("Diese E-Mail-Adresse ist bereits einem Kontakt zugeordnet.", 409)


def _clear_primary(db: Session, partner_id: UUID) -> None:
    rows = db.scalars(
        select(CompanyContact).where(
            CompanyContact.partner_id == partner_id,
            CompanyContact.is_primary.is_(True),
        )
    ).all()
    for row in rows:
        row.is_primary = False
        row.updated_at = _now()
    if rows:
        db.flush()


def _add_links(db: Session, contact_id: UUID, links: list) -> None:
    for link in links:
        _ensure_partner(db, link.partner_id, allow_archived=False)
        if link.is_primary:
            _clear_primary(db, link.partner_id)
        db.add(
            CompanyContact(
                partner_id=link.partner_id,
                contact_id=contact_id,
                is_primary=link.is_primary,
            )
        )
    if links:
        db.flush()


def apply_contact(contact: Contact, data: ContactWrite) -> None:
    for field in CONTACT_FIELDS:
        setattr(contact, field, getattr(data, field))
    contact.updated_at = _now()


def insert_contact(db: Session, data: ContactWrite, *, is_demo: bool = False, demo_key: str | None = None) -> Contact:
    ensure_contact_email(db, data.email)
    contact = Contact(is_demo=is_demo, demo_key=demo_key)
    apply_contact(contact, data)
    db.add(contact)
    db.flush()
    _add_links(db, contact.id, data.companies)
    return contact


def update_contact(db: Session, contact_id: UUID, data: ContactWrite) -> Contact:
    contact = require_contact(db, contact_id)
    if contact.archived_at is not None:
        raise CrmServiceError(
            "Archivierte Kontakte können erst nach der Wiederherstellung bearbeitet werden.",
            409,
        )
    ensure_contact_email(db, data.email, exclude_id=contact.id)
    apply_contact(contact, data)
    db.flush()
    return contact


def archive_contact(db: Session, contact_id: UUID) -> Contact:
    contact = require_contact(db, contact_id)
    if contact.archived_at is not None:
        raise CrmServiceError("Der Kontakt ist bereits archiviert.", 409)
    contact.archived_at = _now()
    contact.updated_at = contact.archived_at
    db.flush()
    return contact


def restore_contact(db: Session, contact_id: UUID) -> Contact:
    contact = require_contact(db, contact_id)
    if contact.archived_at is None:
        raise CrmServiceError("Der Kontakt ist nicht archiviert.", 409)
    ensure_contact_email(db, contact.email, exclude_id=contact.id)
    contact.archived_at = None
    contact.updated_at = _now()
    db.flush()
    return contact


def link_company(db: Session, contact_id: UUID, partner_id: UUID, is_primary: bool) -> Contact:
    contact = require_contact(db, contact_id)
    if contact.archived_at is not None:
        raise CrmServiceError(
            "Archivierte Kontakte können erst nach der Wiederherstellung zugeordnet werden.",
            409,
        )
    _ensure_partner(db, partner_id, allow_archived=False)
    existing = db.scalar(
        select(CompanyContact).where(
            CompanyContact.contact_id == contact_id,
            CompanyContact.partner_id == partner_id,
        )
    )
    if existing is not None:
        raise CrmServiceError("Dieser Kontakt ist diesem Unternehmen bereits zugeordnet.", 409)
    if is_primary:
        _clear_primary(db, partner_id)
    db.add(CompanyContact(partner_id=partner_id, contact_id=contact_id, is_primary=is_primary))
    db.flush()
    return contact


def unlink_company(db: Session, contact_id: UUID, partner_id: UUID) -> Contact:
    contact = require_contact(db, contact_id)
    link = db.scalar(
        select(CompanyContact).where(
            CompanyContact.contact_id == contact_id,
            CompanyContact.partner_id == partner_id,
        )
    )
    if link is None:
        raise CrmServiceError("Die Zuordnung wurde nicht gefunden.", 404)
    db.delete(link)
    db.flush()
    return contact


def set_primary_company(db: Session, contact_id: UUID, partner_id: UUID) -> Contact:
    contact = require_contact(db, contact_id)
    link = db.scalar(
        select(CompanyContact).where(
            CompanyContact.contact_id == contact_id,
            CompanyContact.partner_id == partner_id,
        )
    )
    if link is None:
        raise CrmServiceError("Die Zuordnung wurde nicht gefunden.", 404)
    _clear_primary(db, partner_id)
    link.is_primary = True
    link.updated_at = _now()
    db.flush()
    return contact


def company_links_for(db: Session, contact_ids: list[UUID]) -> dict[UUID, list[CompanyLinkRead]]:
    grouped: dict[UUID, list[CompanyLinkRead]] = {contact_id: [] for contact_id in contact_ids}
    if not contact_ids:
        return grouped
    rows = db.execute(
        select(CompanyContact, Partner)
        .join(Partner, Partner.id == CompanyContact.partner_id)
        .where(CompanyContact.contact_id.in_(contact_ids))
        .order_by(Partner.company_name.asc(), CompanyContact.id.asc())
    ).all()
    for link, partner in rows:
        grouped.setdefault(link.contact_id, []).append(
            CompanyLinkRead(
                partner_id=partner.id,
                company_name=partner.company_name,
                city=partner.city,
                is_primary=link.is_primary,
                partner_archived=partner.archived_at is not None,
            )
        )
    return grouped


def read_contacts(db: Session, contacts: list[Contact]) -> list[ContactRead]:
    ids = [contact.id for contact in contacts]
    links = company_links_for(db, ids)
    lasts = contact_last_map(db, ids)
    return [
        ContactRead(
            id=contact.id,
            first_name=contact.first_name,
            last_name=contact.last_name,
            job_title=contact.job_title,
            email=contact.email,
            phone=contact.phone,
            mobile=contact.mobile,
            account_owner=contact.account_owner,
            preferred_language=contact.preferred_language,
            preferred_channel=contact.preferred_channel,
            lifecycle_phase=contact.lifecycle_phase,
            lead_status=contact.lead_status,
            status=contact.status,
            notes=contact.notes,
            processing_basis=contact.processing_basis,
            processing_basis_note=contact.processing_basis_note,
            is_demo=contact.is_demo,
            archived_at=contact.archived_at,
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            last_contact_at=lasts.get(contact.id),
            companies=links.get(contact.id, []),
        )
        for contact in contacts
    ]


def query_contacts(
    db: Session,
    *,
    q: str | None,
    partner_id: UUID | None,
    status: str | None,
    account_owner: str | None,
    include_archived: bool,
    sort: str,
    direction: str,
    page: int,
    page_size: int,
) -> tuple[list[Contact], int]:
    filters = []
    if not include_archived:
        filters.append(Contact.archived_at.is_(None))
    if status:
        filters.append(Contact.status == status)
    if account_owner:
        filters.append(func.lower(Contact.account_owner) == account_owner.casefold())
    if partner_id is not None:
        filters.append(
            Contact.id.in_(select(CompanyContact.contact_id).where(CompanyContact.partner_id == partner_id))
        )
    if q and q.strip():
        pattern = contains_pattern(q.strip())
        company_match = select(CompanyContact.contact_id).join(Partner, Partner.id == CompanyContact.partner_id).where(
            Partner.company_name.ilike(pattern, escape="\\")
        )
        filters.append(
            or_(
                Contact.first_name.ilike(pattern, escape="\\"),
                Contact.last_name.ilike(pattern, escape="\\"),
                Contact.email.ilike(pattern, escape="\\"),
                Contact.id.in_(company_match),
            )
        )
    count_statement = select(func.count()).select_from(Contact)
    statement = select(Contact)
    if filters:
        count_statement = count_statement.where(*filters)
        statement = statement.where(*filters)
    total = int(db.scalar(count_statement) or 0)
    if sort == "last_contact":
        ordered = contact_last_expression(direction)
        statement = statement.order_by(ordered, Contact.last_name.asc(), Contact.first_name.asc(), Contact.id.asc())
    else:
        last = Contact.last_name.desc() if direction == "desc" else Contact.last_name.asc()
        first = Contact.first_name.desc() if direction == "desc" else Contact.first_name.asc()
        statement = statement.order_by(last, first, Contact.id.asc())
    rows = db.scalars(statement.offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total


def contact_filter_options(db: Session) -> tuple[list[CompanyOption], list[str]]:
    partners = db.scalars(
        select(Partner)
        .join(CompanyContact, CompanyContact.partner_id == Partner.id)
        .distinct()
        .order_by(Partner.company_name.asc())
    ).all()
    companies = [
        CompanyOption(partner_id=partner.id, company_name=partner.company_name, city=partner.city) for partner in partners
    ]
    return companies, distinct_text(db, Contact.account_owner)


def _names(db: Session, contact_ids: list[UUID], partner_ids: list[UUID]) -> tuple[dict[UUID, str], dict[UUID, str]]:
    contacts: dict[UUID, str] = {}
    partners: dict[UUID, str] = {}
    if contact_ids:
        for contact in db.scalars(select(Contact).where(Contact.id.in_(contact_ids))).all():
            contacts[contact.id] = f"{contact.first_name} {contact.last_name}"
    if partner_ids:
        for partner in db.scalars(select(Partner).where(Partner.id.in_(partner_ids))).all():
            partners[partner.id] = partner.company_name
    return contacts, partners


def read_activities(db: Session, rows: list[Activity]) -> list[ActivityRead]:
    contacts, partners = _names(
        db,
        [row.contact_id for row in rows if row.contact_id is not None],
        [row.partner_id for row in rows if row.partner_id is not None],
    )
    return [
        ActivityRead(
            id=row.id,
            activity_type=row.activity_type,
            title=row.title,
            description=row.description,
            occurred_at=row.occurred_at,
            account_owner=row.account_owner,
            contact_id=row.contact_id,
            partner_id=row.partner_id,
            contact_name=contacts.get(row.contact_id) if row.contact_id else None,
            company_name=partners.get(row.partner_id) if row.partner_id else None,
            is_demo=row.is_demo,
            archived_at=row.archived_at,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


def insert_activity(db: Session, data: ActivityWrite, *, is_demo: bool = False, demo_key: str | None = None) -> Activity:
    _ensure_contact_exists(db, data.contact_id)
    _ensure_partner(db, data.partner_id, allow_archived=True)
    activity = Activity(is_demo=is_demo, demo_key=demo_key)
    for field in ACTIVITY_FIELDS:
        setattr(activity, field, getattr(data, field))
    activity.updated_at = _now()
    db.add(activity)
    db.flush()
    return activity


def update_activity(db: Session, activity_id: UUID, data: ActivityWrite) -> Activity:
    activity = require_activity(db, activity_id)
    if activity.archived_at is not None:
        raise CrmServiceError(
            "Archivierte Aktivitäten können erst nach der Wiederherstellung bearbeitet werden.",
            409,
        )
    _ensure_contact_exists(db, data.contact_id)
    _ensure_partner(db, data.partner_id, allow_archived=True)
    for field in ACTIVITY_FIELDS:
        setattr(activity, field, getattr(data, field))
    activity.updated_at = _now()
    db.flush()
    return activity


def archive_activity(db: Session, activity_id: UUID) -> Activity:
    activity = require_activity(db, activity_id)
    if activity.archived_at is not None:
        raise CrmServiceError("Die Aktivität ist bereits archiviert.", 409)
    activity.archived_at = _now()
    activity.updated_at = activity.archived_at
    db.flush()
    return activity


def restore_activity(db: Session, activity_id: UUID) -> Activity:
    activity = require_activity(db, activity_id)
    if activity.archived_at is None:
        raise CrmServiceError("Die Aktivität ist nicht archiviert.", 409)
    activity.archived_at = None
    activity.updated_at = _now()
    db.flush()
    return activity


def query_activities(
    db: Session,
    *,
    q: str | None,
    activity_type: str | None,
    partner_id: UUID | None,
    contact_id: UUID | None,
    include_archived: bool,
    page: int,
    page_size: int,
) -> tuple[list[Activity], int]:
    filters = []
    if not include_archived:
        filters.append(Activity.archived_at.is_(None))
    if activity_type:
        filters.append(Activity.activity_type == activity_type)
    if partner_id is not None:
        filters.append(Activity.partner_id == partner_id)
    if contact_id is not None:
        filters.append(Activity.contact_id == contact_id)
    if q and q.strip():
        pattern = contains_pattern(q.strip())
        filters.append(
            or_(
                Activity.title.ilike(pattern, escape="\\"),
                Activity.description.ilike(pattern, escape="\\"),
            )
        )
    count_statement = select(func.count()).select_from(Activity)
    statement = select(Activity)
    if filters:
        count_statement = count_statement.where(*filters)
        statement = statement.where(*filters)
    total = int(db.scalar(count_statement) or 0)
    rows = db.scalars(
        statement.order_by(Activity.occurred_at.desc(), Activity.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return list(rows), total


def _task_flags(task: Task, now: datetime) -> tuple[bool, bool, bool]:
    open_task = task.status in OPEN_TASK_STATUSES
    overdue = bool(open_task and task.due_at < now)
    due_soon = bool(open_task and not overdue and task.due_at <= now + SOON)
    urgent = bool(open_task and task.priority == "dringend")
    return overdue, due_soon, urgent


def read_tasks(db: Session, rows: list[Task]) -> list[TaskRead]:
    now = _now()
    contacts, partners = _names(
        db,
        [row.contact_id for row in rows if row.contact_id is not None],
        [row.partner_id for row in rows if row.partner_id is not None],
    )
    result = []
    for row in rows:
        overdue, due_soon, urgent = _task_flags(row, now)
        result.append(
            TaskRead(
                id=row.id,
                title=row.title,
                description=row.description,
                account_owner=row.account_owner,
                due_at=row.due_at,
                priority=row.priority,
                status=row.status,
                task_type=row.task_type,
                partner_id=row.partner_id,
                contact_id=row.contact_id,
                activity_id=row.activity_id,
                ticket_id=row.ticket_id,
                company_name=partners.get(row.partner_id) if row.partner_id else None,
                contact_name=contacts.get(row.contact_id) if row.contact_id else None,
                completed_at=row.completed_at,
                is_demo=row.is_demo,
                is_overdue=overdue,
                is_due_soon=due_soon,
                is_urgent=urgent,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return result


def _apply_completion(task: Task) -> None:
    if task.status == "erledigt":
        if task.completed_at is None:
            task.completed_at = _now()
    else:
        task.completed_at = None


def insert_task(db: Session, data: TaskWrite, *, is_demo: bool = False, demo_key: str | None = None) -> Task:
    _ensure_contact_exists(db, data.contact_id)
    _ensure_partner(db, data.partner_id, allow_archived=True)
    _ensure_activity_exists(db, data.activity_id)
    task = Task(is_demo=is_demo, demo_key=demo_key)
    for field in TASK_FIELDS:
        setattr(task, field, getattr(data, field))
    _apply_completion(task)
    task.updated_at = _now()
    db.add(task)
    db.flush()
    return task


def update_task(db: Session, task_id: UUID, data: TaskWrite) -> Task:
    task = require_task(db, task_id)
    _ensure_contact_exists(db, data.contact_id)
    _ensure_partner(db, data.partner_id, allow_archived=True)
    _ensure_activity_exists(db, data.activity_id)
    for field in TASK_FIELDS:
        setattr(task, field, getattr(data, field))
    _apply_completion(task)
    task.updated_at = _now()
    db.flush()
    return task


def complete_task(db: Session, task_id: UUID) -> Task:
    task = require_task(db, task_id)
    if task.status == "erledigt":
        raise CrmServiceError("Die Aufgabe ist bereits erledigt.", 409)
    if task.status == "abgebrochen":
        raise CrmServiceError("Eine abgebrochene Aufgabe kann nicht als erledigt markiert werden.", 409)
    task.status = "erledigt"
    task.completed_at = _now()
    task.updated_at = task.completed_at
    db.flush()
    return task


def query_tasks(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    priority: str | None,
    account_owner: str | None,
    partner_id: UUID | None,
    contact_id: UUID | None,
    due: str | None,
    service_only: bool,
    page: int,
    page_size: int,
) -> tuple[list[Task], int]:
    now = _now()
    filters = []
    if status:
        filters.append(Task.status == status)
    if priority:
        filters.append(Task.priority == priority)
    if account_owner:
        filters.append(func.lower(Task.account_owner) == account_owner.casefold())
    if partner_id is not None:
        filters.append(Task.partner_id == partner_id)
    if contact_id is not None:
        filters.append(Task.contact_id == contact_id)
    if due == "open":
        filters.append(Task.status.in_(OPEN_TASK_STATUSES))
    elif due == "overdue":
        filters.append(Task.status.in_(OPEN_TASK_STATUSES))
        filters.append(Task.due_at < now)
    elif due == "soon":
        filters.append(Task.status.in_(OPEN_TASK_STATUSES))
        filters.append(Task.due_at >= now)
        filters.append(Task.due_at <= now + SOON)
    elif due == "urgent":
        filters.append(Task.status.in_(OPEN_TASK_STATUSES))
        filters.append(Task.priority == "dringend")
    if service_only:
        filters.append(Task.ticket_id.is_not(None))
    if q and q.strip():
        pattern = contains_pattern(q.strip())
        filters.append(or_(Task.title.ilike(pattern, escape="\\"), Task.description.ilike(pattern, escape="\\")))
    count_statement = select(func.count()).select_from(Task)
    statement = select(Task)
    if filters:
        count_statement = count_statement.where(*filters)
        statement = statement.where(*filters)
    total = int(db.scalar(count_statement) or 0)
    rows = db.scalars(
        statement.order_by(Task.due_at.asc(), Task.id.asc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def task_summary(db: Session) -> tuple[int, int, int, int, int]:
    now = _now()
    open_filter = Task.status.in_(OPEN_TASK_STATUSES)
    open_count = int(db.scalar(select(func.count()).select_from(Task).where(open_filter)) or 0)
    overdue = int(
        db.scalar(select(func.count()).select_from(Task).where(open_filter, Task.due_at < now)) or 0
    )
    soon = int(
        db.scalar(
            select(func.count()).select_from(Task).where(open_filter, Task.due_at >= now, Task.due_at <= now + SOON)
        )
        or 0
    )
    urgent = int(
        db.scalar(select(func.count()).select_from(Task).where(open_filter, Task.priority == "dringend")) or 0
    )
    demo = int(
        db.scalar(select(func.count()).select_from(Task).where(open_filter, Task.is_demo.is_(True))) or 0
    )
    return open_count, overdue, soon, urgent, demo


def create_note_with_task(db: Session, payload: NoteWithTaskWrite) -> tuple[Activity, Task | None]:
    activity = insert_activity(db, payload.activity)
    if payload.task is None:
        return activity, None
    follow_up: FollowUpWrite = payload.task
    task = insert_task(
        db,
        TaskWrite(
            title=follow_up.title,
            description=follow_up.description,
            account_owner=follow_up.account_owner,
            due_at=follow_up.due_at,
            priority=follow_up.priority,
            status="offen",
            task_type=follow_up.task_type,
            partner_id=activity.partner_id,
            contact_id=activity.contact_id,
            activity_id=activity.id,
        ),
    )
    return activity, task
