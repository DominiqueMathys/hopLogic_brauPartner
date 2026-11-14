"""Service tickets, append-only history, files and computed segments.

Handling time starts at created_at and ends at resolved_at, or at closed_at when
the ticket was closed without a documented resolution. Assigned-only roles see
tickets that match their account. File storage is not a public directory.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.orm import Session

from app.config import ROOT_DIR, settings
from app.crm_catalog import OPEN_TASK_STATUSES
from app.models.activity import Activity
from app.models.contact import CompanyContact, Contact
from app.models.partner import Partner
from app.models.sales import Deal, Order, Product
from app.models.service import (
    CustomerSegment,
    PartnerMetric,
    SegmentCondition,
    ServiceTicket,
    TicketAttachment,
    TicketEvent,
    TicketProduct,
    TicketResolution,
)
from app.models.task import Task
from app.sales_catalog import COUNTED_ORDER_STATUSES, OPEN_DEAL_STAGES
from app.schemas.service import (
    Actor,
    AssignChange,
    NoteCreate,
    PartnerAnalysis,
    PriorityChange,
    ResolveCreate,
    SegmentPartner,
    SegmentRead,
    SegmentWrite,
    StatusChange,
    TicketAttachmentRead,
    TicketDetail,
    TicketEventRead,
    TicketList,
    TicketProductRead,
    TicketRead,
    TicketResolutionRead,
    TicketSummary,
    TicketTaskCreate,
    TicketTaskRead,
    TicketUpdate,
    TicketWrite,
)
from app.schemas.task import TaskWrite
from app.service_catalog import (
    CLOSE_FROM,
    COMPLAINT_CATEGORIES,
    OPEN_TICKET_STATUSES,
    PRIORITY_RANK,
    REOPEN_FROM,
    RESOLVE_FROM,
    TICKET_STATUS_TRANSITIONS,
)
from app.services.crm import CrmServiceError, insert_task
from app.services.money import as_decimal, money

DURATION_DEFINITION = (
    "Start ist das Erfassen des Tickets. Ende ist die dokumentierte Lösung, "
    "oder die Schliessung, wenn keine Lösung erfasst wurde."
)
VOLUME_BASIS = "CRM-Bestellvolumen ohne Entwürfe und ohne stornierte Bestellungen. Kein fakturierter ERP-Umsatz."
FILE_KINDS = {
    ".pdf": ("application/pdf", b"%PDF"),
    ".jpg": ("image/jpeg", b"\xff\xd8\xff"),
    ".jpeg": ("image/jpeg", b"\xff\xd8\xff"),
    ".png": ("image/png", b"\x89PNG\r\n\x1a\n"),
}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _today() -> date:
    return _now().date()


def _actor(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split())
    return cleaned or None


def _limit_tickets(ticket: ServiceTicket) -> None:
    from fastapi import HTTPException

    from app.access_context import ticket_owner_limit

    limit = ticket_owner_limit()
    if limit is None:
        return
    name, user_id = limit
    if ticket.account_owner == name or ticket.owner_user_id == user_id:
        return
    raise HTTPException(status_code=403, detail="Keine Berechtigung für diesen Datensatz.")


def require_ticket(db: Session, ticket_id: uuid.UUID) -> ServiceTicket:
    ticket = db.get(ServiceTicket, ticket_id)
    if ticket is None:
        raise CrmServiceError("Das Service-Ticket wurde nicht gefunden.", 404)
    return ticket


def _partner(db: Session, partner_id: uuid.UUID) -> Partner:
    partner = db.get(Partner, partner_id)
    if partner is None or partner.archived_at is not None:
        raise CrmServiceError("Der Vertriebspartner wurde nicht gefunden.", 404)
    return partner


def _ensure_contact(db: Session, contact_id: uuid.UUID | None, partner_id: uuid.UUID) -> None:
    if contact_id is None:
        return
    link = db.scalar(
        select(CompanyContact.id).where(
            CompanyContact.contact_id == contact_id,
            CompanyContact.partner_id == partner_id,
        )
    )
    if link is None:
        raise CrmServiceError("Die Kontaktperson ist diesem Unternehmen nicht zugeordnet.", 409)


def _ensure_order(db: Session, order_id: uuid.UUID | None, partner_id: uuid.UUID) -> None:
    if order_id is None:
        return
    order = db.get(Order, order_id)
    if order is None or order.archived_at is not None or order.partner_id != partner_id:
        raise CrmServiceError("Die Bestellung gehört nicht zu diesem Vertriebspartner.", 409)


def _replace_products(db: Session, ticket_id: uuid.UUID, product_ids: list[uuid.UUID]) -> None:
    unique = list(dict.fromkeys(product_ids))
    if unique:
        found = set(db.scalars(select(Product.id).where(Product.id.in_(unique))).all())
        if found != set(unique):
            raise CrmServiceError("Mindestens ein Produkt wurde nicht gefunden.", 404)
    db.execute(delete(TicketProduct).where(TicketProduct.ticket_id == ticket_id))
    for product_id in unique:
        db.add(TicketProduct(ticket_id=ticket_id, product_id=product_id))


def _event(
    db: Session,
    ticket: ServiceTicket,
    event_type: str,
    *,
    from_value: str | None = None,
    to_value: str | None = None,
    note: str | None = None,
    changed_by: str | None = None,
    task_id: uuid.UUID | None = None,
) -> None:
    db.add(
        TicketEvent(
            ticket_id=ticket.id,
            event_type=event_type,
            from_value=from_value,
            to_value=to_value,
            note=note,
            changed_by=_actor(changed_by),
            task_id=task_id,
            changed_at=_now(),
        )
    )
    ticket.updated_at = _now()


def _next_number(db: Session) -> str:
    year = _today().year
    prefix = f"SRV-{year}-"
    numbers = db.scalars(select(ServiceTicket.ticket_number).where(ServiceTicket.ticket_number.like(f"{prefix}%"))).all()
    highest = 0
    for number in numbers:
        suffix = number.removeprefix(prefix)
        if suffix.isdigit():
            highest = max(highest, int(suffix))
    return f"{prefix}{highest + 1:04d}"


def insert_ticket(db: Session, data: TicketWrite, *, is_demo: bool = False, demo_key: str | None = None, number: str | None = None, status: str = "neu") -> ServiceTicket:
    _partner(db, data.partner_id)
    _ensure_contact(db, data.contact_id, data.partner_id)
    _ensure_order(db, data.order_id, data.partner_id)
    ticket = ServiceTicket(
        ticket_number=number or _next_number(db),
        subject=data.subject,
        category=data.category,
        description=data.description,
        partner_id=data.partner_id,
        contact_id=data.contact_id,
        order_id=data.order_id,
        account_owner=data.account_owner,
        priority=data.priority,
        status=status,
        due_on=data.due_on,
        internal_remark=data.internal_remark,
        is_demo=is_demo,
        demo_key=demo_key,
    )
    db.add(ticket)
    db.flush()
    _replace_products(db, ticket.id, data.product_ids)
    _event(db, ticket, "created", to_value=status, changed_by=data.account_owner)
    db.flush()
    from app.services.automation import publish_event

    publish_event(
        db,
        "ticket_created",
        dedupe_key=f"ticket:{ticket.id}",
        context={
            "owner": ticket.account_owner,
            "partner_id": ticket.partner_id,
            "contact_id": ticket.contact_id,
            "priority": ticket.priority,
            "ticket_id": ticket.id,
            "href": f"/kundenservice/{ticket.id}",
            "subject_title": ticket.subject,
        },
    )
    return ticket


def update_ticket(db: Session, ticket_id: uuid.UUID, data: TicketUpdate, *, changed_by: str | None = None) -> ServiceTicket:
    ticket = require_ticket(db, ticket_id)
    _partner(db, data.partner_id)
    _ensure_contact(db, data.contact_id, data.partner_id)
    _ensure_order(db, data.order_id, data.partner_id)
    previous_priority = ticket.priority
    previous_owner = ticket.account_owner
    ticket.subject = data.subject
    ticket.category = data.category
    ticket.description = data.description
    ticket.partner_id = data.partner_id
    ticket.contact_id = data.contact_id
    ticket.order_id = data.order_id
    ticket.due_on = data.due_on
    ticket.internal_remark = data.internal_remark
    ticket.priority = data.priority
    ticket.account_owner = data.account_owner
    ticket.updated_at = _now()
    _replace_products(db, ticket.id, data.product_ids)
    actor = changed_by or data.account_owner
    if previous_priority != data.priority:
        _event(db, ticket, "priority_changed", from_value=previous_priority, to_value=data.priority, changed_by=actor)
        from app.services.automation import publish_event

        publish_event(
            db,
            "ticket_priority_changed",
            dedupe_key=f"ticket-priority:{ticket.id}:{previous_priority}:{data.priority}",
            context={
                "owner": ticket.account_owner,
                "partner_id": ticket.partner_id,
                "contact_id": ticket.contact_id,
                "priority": data.priority,
                "ticket_id": ticket.id,
                "href": f"/kundenservice/{ticket.id}",
            },
        )
    if (previous_owner or "") != (data.account_owner or ""):
        _event(db, ticket, "owner_changed", from_value=previous_owner, to_value=data.account_owner, changed_by=actor)
    db.flush()
    return ticket


def change_status(db: Session, ticket_id: uuid.UUID, data: StatusChange) -> ServiceTicket:
    ticket = require_ticket(db, ticket_id)
    if data.status in {"geloest", "geschlossen"}:
        raise CrmServiceError("Lösung und Abschluss laufen über die eigenen Funktionen.", 409)
    allowed = TICKET_STATUS_TRANSITIONS[ticket.status]
    if data.status not in allowed:
        raise CrmServiceError("Dieser Statuswechsel ist nicht zulässig.", 409)
    previous = ticket.status
    ticket.status = data.status
    _event(db, ticket, "status_changed", from_value=previous, to_value=data.status, changed_by=data.changed_by)
    db.flush()
    return ticket


def change_priority(db: Session, ticket_id: uuid.UUID, data: PriorityChange) -> ServiceTicket:
    ticket = require_ticket(db, ticket_id)
    if ticket.priority == data.priority:
        return ticket
    previous = ticket.priority
    ticket.priority = data.priority
    _event(db, ticket, "priority_changed", from_value=previous, to_value=data.priority, changed_by=data.changed_by)
    db.flush()
    from app.services.automation import publish_event

    publish_event(
        db,
        "ticket_priority_changed",
        dedupe_key=f"ticket-priority:{ticket.id}:{previous}:{data.priority}",
        context={
            "owner": ticket.account_owner,
            "partner_id": ticket.partner_id,
            "contact_id": ticket.contact_id,
            "priority": data.priority,
            "ticket_id": ticket.id,
            "href": f"/kundenservice/{ticket.id}",
        },
    )
    return ticket


def assign_ticket(db: Session, ticket_id: uuid.UUID, data: AssignChange) -> ServiceTicket:
    ticket = require_ticket(db, ticket_id)
    if (ticket.account_owner or "") == (data.account_owner or ""):
        return ticket
    previous = ticket.account_owner
    ticket.account_owner = data.account_owner
    _event(db, ticket, "owner_changed", from_value=previous, to_value=data.account_owner, changed_by=data.changed_by)
    db.flush()
    return ticket


def add_note(db: Session, ticket_id: uuid.UUID, data: NoteCreate) -> ServiceTicket:
    ticket = require_ticket(db, ticket_id)
    _event(db, ticket, "note_added", note=data.note, changed_by=data.changed_by)
    db.flush()
    return ticket


def add_task(db: Session, ticket_id: uuid.UUID, data: TicketTaskCreate) -> Task:
    ticket = require_ticket(db, ticket_id)
    task = insert_task(
        db,
        TaskWrite(
            title=data.title,
            description=data.description,
            account_owner=data.account_owner or ticket.account_owner,
            due_at=data.due_at,
            priority=data.priority,
            status="offen",
            task_type="intern",
            partner_id=ticket.partner_id,
            contact_id=ticket.contact_id,
        ),
    )
    task.ticket_id = ticket.id
    _event(db, ticket, "task_created", to_value=data.title, task_id=task.id, changed_by=data.changed_by)
    db.flush()
    return task


def resolve_ticket(db: Session, ticket_id: uuid.UUID, data: ResolveCreate) -> ServiceTicket:
    ticket = require_ticket(db, ticket_id)
    if ticket.status not in RESOLVE_FROM:
        raise CrmServiceError("Das Ticket kann in diesem Status nicht gelöst werden.", 409)
    previous = ticket.status
    moment = _now()
    db.add(
        TicketResolution(
            ticket_id=ticket.id,
            code=data.code,
            note=data.note,
            recorded_by=_actor(data.changed_by),
            recorded_at=moment,
        )
    )
    ticket.status = "geloest"
    ticket.resolved_at = moment
    _event(
        db,
        ticket,
        "resolved",
        from_value=previous,
        to_value=data.code,
        note=data.note,
        changed_by=data.changed_by,
    )
    db.flush()
    return ticket


def close_ticket(db: Session, ticket_id: uuid.UUID, data: Actor) -> ServiceTicket:
    ticket = require_ticket(db, ticket_id)
    if ticket.status not in CLOSE_FROM:
        raise CrmServiceError("Das Ticket kann in diesem Status nicht geschlossen werden.", 409)
    previous = ticket.status
    ticket.status = "geschlossen"
    ticket.closed_at = _now()
    _event(db, ticket, "closed", from_value=previous, to_value="geschlossen", changed_by=data.changed_by)
    db.flush()
    return ticket


def reopen_ticket(db: Session, ticket_id: uuid.UUID, data: Actor) -> ServiceTicket:
    ticket = require_ticket(db, ticket_id)
    if ticket.status not in REOPEN_FROM:
        raise CrmServiceError("Nur ein gelöstes oder geschlossenes Ticket kann wieder geöffnet werden.", 409)
    previous = ticket.status
    ticket.status = "offen"
    ticket.resolved_at = None
    ticket.closed_at = None
    _event(db, ticket, "reopened", from_value=previous, to_value="offen", changed_by=data.changed_by)
    db.flush()
    return ticket


def _names(db: Session, tickets: list[ServiceTicket]) -> tuple[dict, dict, dict]:
    partner_ids = {row.partner_id for row in tickets}
    contact_ids = {row.contact_id for row in tickets if row.contact_id}
    order_ids = {row.order_id for row in tickets if row.order_id}
    partners = {row.id: row.company_name for row in db.scalars(select(Partner).where(Partner.id.in_(partner_ids or {uuid.uuid4()}))).all()} if partner_ids else {}
    contacts = {}
    if contact_ids:
        for row in db.scalars(select(Contact).where(Contact.id.in_(contact_ids))).all():
            contacts[row.id] = f"{row.first_name} {row.last_name}".strip()
    orders = {}
    if order_ids:
        orders = {row.id: row.order_number for row in db.scalars(select(Order).where(Order.id.in_(order_ids))).all()}
    return partners, contacts, orders


def _ticket_read(row: ServiceTicket, company: str, contact: str | None) -> TicketRead:
    overdue = row.due_on is not None and row.due_on < _today() and row.status in OPEN_TICKET_STATUSES
    return TicketRead(
        id=row.id,
        ticket_number=row.ticket_number,
        subject=row.subject,
        category=row.category,
        priority=row.priority,
        status=row.status,
        partner_id=row.partner_id,
        company_name=company,
        contact_id=row.contact_id,
        contact_name=contact,
        account_owner=row.account_owner,
        due_on=row.due_on,
        is_overdue=overdue,
        is_demo=row.is_demo,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def read_ticket(db: Session, ticket_id: uuid.UUID) -> TicketDetail:
    ticket = require_ticket(db, ticket_id)
    _limit_tickets(ticket)
    partners, contacts, orders = _names(db, [ticket])
    base = _ticket_read(ticket, partners.get(ticket.partner_id, ""), contacts.get(ticket.contact_id) if ticket.contact_id else None)
    product_rows = db.execute(
        select(Product.id, Product.name, Product.sku)
        .join(TicketProduct, TicketProduct.product_id == Product.id)
        .where(TicketProduct.ticket_id == ticket.id)
        .order_by(Product.name)
    ).all()
    events = db.scalars(select(TicketEvent).where(TicketEvent.ticket_id == ticket.id).order_by(TicketEvent.changed_at, TicketEvent.id)).all()
    files = db.scalars(select(TicketAttachment).where(TicketAttachment.ticket_id == ticket.id).order_by(TicketAttachment.created_at)).all()
    resolutions = db.scalars(select(TicketResolution).where(TicketResolution.ticket_id == ticket.id).order_by(TicketResolution.recorded_at)).all()
    tasks = db.scalars(select(Task).where(Task.ticket_id == ticket.id).order_by(Task.due_at)).all()
    return TicketDetail(
        **base.model_dump(),
        description=ticket.description,
        order_id=ticket.order_id,
        order_number=orders.get(ticket.order_id) if ticket.order_id else None,
        internal_remark=ticket.internal_remark,
        resolved_at=ticket.resolved_at,
        closed_at=ticket.closed_at,
        products=[TicketProductRead(id=row.id, name=row.name, sku=row.sku) for row in product_rows],
        events=[
            TicketEventRead(
                id=row.id,
                event_type=row.event_type,
                from_value=row.from_value,
                to_value=row.to_value,
                note=row.note,
                changed_by=row.changed_by,
                task_id=row.task_id,
                changed_at=row.changed_at,
            )
            for row in events
        ],
        attachments=[
            TicketAttachmentRead(
                id=row.id,
                original_name=row.original_name,
                content_type=row.content_type,
                size_bytes=row.size_bytes,
                created_at=row.created_at,
            )
            for row in files
        ],
        resolutions=[
            TicketResolutionRead(
                id=row.id,
                code=row.code,
                note=row.note,
                recorded_by=row.recorded_by,
                recorded_at=row.recorded_at,
            )
            for row in resolutions
        ],
        tasks=[
            TicketTaskRead(
                id=row.id,
                title=row.title,
                status=row.status,
                priority=row.priority,
                due_at=row.due_at,
                account_owner=row.account_owner,
            )
            for row in tasks
        ],
        allowed_statuses=sorted(TICKET_STATUS_TRANSITIONS[ticket.status]),
        can_resolve=ticket.status in RESOLVE_FROM,
        can_close=ticket.status in CLOSE_FROM,
        can_reopen=ticket.status in REOPEN_FROM,
    )


def query_tickets(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    priority: str | None,
    category: str | None,
    account_owner: str | None,
    partner_id: uuid.UUID | None,
    contact_id: uuid.UUID | None,
    order_id: uuid.UUID | None,
    scope: str | None,
    sort: str,
    direction: str,
    page: int,
    page_size: int,
) -> TicketList:
    filters = []
    if q:
        pattern = f"%{q.strip()}%"
        filters.append(or_(ServiceTicket.ticket_number.ilike(pattern), ServiceTicket.subject.ilike(pattern), Partner.company_name.ilike(pattern)))
    if status:
        filters.append(ServiceTicket.status == status)
    if priority:
        filters.append(ServiceTicket.priority == priority)
    if category:
        filters.append(ServiceTicket.category == category)
    if account_owner:
        filters.append(ServiceTicket.account_owner == account_owner)
    if partner_id:
        filters.append(ServiceTicket.partner_id == partner_id)
    if contact_id:
        filters.append(ServiceTicket.contact_id == contact_id)
    if order_id:
        filters.append(ServiceTicket.order_id == order_id)
    if scope == "open":
        filters.append(ServiceTicket.status.in_(OPEN_TICKET_STATUSES))
    elif scope == "closed":
        filters.append(ServiceTicket.status.in_(("geloest", "geschlossen")))
    elif scope == "overdue":
        filters.append(ServiceTicket.due_on < _today())
        filters.append(ServiceTicket.status.in_(OPEN_TICKET_STATUSES))
    from app.access_context import ticket_owner_limit

    limit = ticket_owner_limit()
    if limit is not None:
        name, user_id = limit
        filters.append(or_(ServiceTicket.account_owner == name, ServiceTicket.owner_user_id == user_id))
    base = select(ServiceTicket).join(Partner, Partner.id == ServiceTicket.partner_id)
    if filters:
        base = base.where(*filters)
    total = db.scalar(select(func.count()).select_from(base.subquery())) or 0
    descending = direction != "asc"
    if sort == "created_at":
        ordering = ServiceTicket.created_at.desc() if descending else ServiceTicket.created_at.asc()
    elif sort == "priority":
        rank = case(PRIORITY_RANK, value=ServiceTicket.priority, else_=9)
        ordering = rank.asc() if descending else rank.desc()
    else:
        ordering = ServiceTicket.updated_at.desc() if descending else ServiceTicket.updated_at.asc()
    rows = db.scalars(
        base.order_by(ordering, ServiceTicket.ticket_number.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    partners, contacts, _orders = _names(db, rows)
    items = [
        _ticket_read(row, partners.get(row.partner_id, ""), contacts.get(row.contact_id) if row.contact_id else None)
        for row in rows
    ]
    return TicketList(items=items, total=total, page=page, page_size=page_size)


def ticket_summary(db: Session) -> TicketSummary:
    from app.access_context import ticket_owner_limit

    rows = list(db.scalars(select(ServiceTicket)).all())
    limit = ticket_owner_limit()
    if limit is not None:
        name, user_id = limit
        rows = [row for row in rows if row.account_owner == name or row.owner_user_id == user_id]
    by_category = {key: 0 for key in ("beschaedigte_lieferung", "fehlende_lieferung", "falsche_lieferung", "produktqualitaet", "rechnung", "anfrage", "technisch", "sonstiges")}
    by_priority = {key: 0 for key in ("niedrig", "normal", "hoch", "kritisch")}
    by_status = {key: 0 for key in ("neu", "offen", "in_bearbeitung", "warten_kunde", "warten_intern", "geloest", "geschlossen")}
    durations: list[float] = []
    open_count = critical = resolved = overdue = complaints = 0
    complaint_partners: set[uuid.UUID] = set()
    for row in rows:
        by_category[row.category] = by_category.get(row.category, 0) + 1
        by_priority[row.priority] = by_priority.get(row.priority, 0) + 1
        by_status[row.status] = by_status.get(row.status, 0) + 1
        if row.status in OPEN_TICKET_STATUSES:
            open_count += 1
            if row.priority == "kritisch":
                critical += 1
            if row.due_on is not None and row.due_on < _today():
                overdue += 1
            if row.category in COMPLAINT_CATEGORIES:
                complaints += 1
                complaint_partners.add(row.partner_id)
        if row.status in {"geloest", "geschlossen"}:
            resolved += 1
            end = row.resolved_at or row.closed_at
            if end is not None:
                durations.append((end - row.created_at).total_seconds())
    task_count = db.scalar(
        select(func.count()).select_from(Task).where(
            Task.ticket_id.is_not(None),
            Task.status.in_(OPEN_TASK_STATUSES),
            Task.due_at < _now(),
        )
    ) or 0
    average = None
    if durations:
        average = money(as_decimal(str(sum(durations) / len(durations) / 3600)))
    return TicketSummary(
        open_count=open_count,
        critical_count=critical,
        resolved_count=resolved,
        overdue_count=overdue,
        open_complaints=complaints,
        partners_with_complaints=len(complaint_partners),
        overdue_service_tasks=task_count,
        average_hours=average,
        duration_sample=len(durations),
        duration_definition=DURATION_DEFINITION,
        by_category=by_category,
        by_priority=by_priority,
        by_status=by_status,
    )


def _upload_root() -> Path:
    root = Path(settings.ticket_upload_dir)
    if not root.is_absolute():
        root = ROOT_DIR / root
    return root.resolve()


def save_attachment(db: Session, ticket_id: uuid.UUID, original_name: str, payload: bytes) -> TicketAttachment:
    _limit_tickets(require_ticket(db, ticket_id))
    ticket = require_ticket(db, ticket_id)
    if len(payload) == 0:
        raise CrmServiceError("Die Datei ist leer.", 422)
    if len(payload) > settings.ticket_max_bytes:
        raise CrmServiceError("Die Datei überschreitet die zulässige Grösse.", 413)
    safe_name = Path(original_name or "").name
    extension = Path(safe_name).suffix.lower()
    kind = FILE_KINDS.get(extension)
    if kind is None or not payload.startswith(kind[1]):
        raise CrmServiceError("Zulässig sind nur PDF, JPG und PNG mit passendem Inhalt.", 422)
    if len(safe_name) > 200:
        safe_name = safe_name[:190] + extension
    stored = f"{uuid.uuid4().hex}{extension if extension != '.jpeg' else '.jpg'}"
    folder = _upload_root() / str(ticket.id)
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / stored
    target.write_bytes(payload)
    row = TicketAttachment(
        ticket_id=ticket.id,
        original_name=safe_name or stored,
        stored_name=stored,
        content_type=kind[0],
        size_bytes=len(payload),
    )
    db.add(row)
    ticket.updated_at = _now()
    db.flush()
    return row


def attachment_file(db: Session, ticket_id: uuid.UUID, attachment_id: uuid.UUID) -> tuple[TicketAttachment, Path]:
    _limit_tickets(require_ticket(db, ticket_id))
    row = db.get(TicketAttachment, attachment_id)
    if row is None or row.ticket_id != ticket_id:
        raise CrmServiceError("Die Datei wurde nicht gefunden.", 404)
    root = _upload_root()
    path = (root / str(row.ticket_id) / row.stored_name).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise CrmServiceError("Die Datei wurde nicht gefunden.", 404)
    return row, path


def delete_attachment(db: Session, ticket_id: uuid.UUID, attachment_id: uuid.UUID) -> None:
    _limit_tickets(require_ticket(db, ticket_id))
    row, path = attachment_file(db, ticket_id, attachment_id)
    path.unlink(missing_ok=True)
    db.delete(row)
    ticket = require_ticket(db, ticket_id)
    ticket.updated_at = _now()
    db.flush()


def _metrics(db: Session) -> list[PartnerMetric]:
    partners = db.scalars(select(Partner).where(Partner.archived_at.is_(None)).order_by(Partner.company_name)).all()
    order_rows = db.execute(
        select(Order.partner_id, func.count(), func.coalesce(func.sum(Order.gross_total), 0), func.max(Order.ordered_on))
        .where(Order.archived_at.is_(None), Order.status.in_(COUNTED_ORDER_STATUSES))
        .group_by(Order.partner_id)
    ).all()
    orders = {row[0]: row for row in order_rows}
    deal_rows = db.execute(
        select(Deal.partner_id, func.count(), func.coalesce(func.sum(Deal.estimated_value * Deal.probability / 100), 0))
        .where(Deal.archived_at.is_(None), Deal.stage.in_(OPEN_DEAL_STAGES))
        .group_by(Deal.partner_id)
    ).all()
    deals = {row[0]: row for row in deal_rows}
    ticket_rows = db.execute(
        select(ServiceTicket.partner_id, func.count())
        .where(ServiceTicket.status.in_(OPEN_TICKET_STATUSES))
        .group_by(ServiceTicket.partner_id)
    ).all()
    tickets = {row[0]: row[1] for row in ticket_rows}
    activity_rows = db.execute(
        select(Activity.partner_id, func.max(Activity.occurred_at))
        .where(Activity.archived_at.is_(None), Activity.partner_id.is_not(None))
        .group_by(Activity.partner_id)
    ).all()
    activities = {row[0]: row[1].date() for row in activity_rows if row[1] is not None}
    result = []
    for partner in partners:
        order = orders.get(partner.id)
        deal = deals.get(partner.id)
        result.append(
            PartnerMetric(
                partner_id=partner.id,
                company_name=partner.company_name,
                partner_type=partner.partner_type,
                industry=partner.industry,
                region=partner.region,
                status=partner.status,
                order_count=int(order[1]) if order else 0,
                order_volume=money(as_decimal(order[2] if order else 0)),
                last_order_on=order[3] if order else None,
                open_deals=int(deal[1]) if deal else 0,
                open_tickets=int(tickets.get(partner.id, 0)),
                last_activity_on=activities.get(partner.id),
            )
        )
    return result


def partner_analysis(db: Session, partner_id: uuid.UUID) -> PartnerAnalysis:
    partner = db.get(Partner, partner_id)
    if partner is None or partner.archived_at is not None:
        raise CrmServiceError("Der Vertriebspartner wurde nicht gefunden.", 404)
    metric = next(row for row in _metrics(db) if row.partner_id == partner_id)
    pipeline_row = db.scalar(
        select(func.coalesce(func.sum(Deal.estimated_value * Deal.probability / 100), 0)).where(
            Deal.partner_id == partner_id,
            Deal.archived_at.is_(None),
            Deal.stage.in_(OPEN_DEAL_STAGES),
        )
    )
    closed = db.scalar(
        select(func.count()).select_from(ServiceTicket).where(
            ServiceTicket.partner_id == partner_id,
            ServiceTicket.status.in_(("geloest", "geschlossen")),
        )
    ) or 0
    last_complaint = db.scalar(
        select(func.max(ServiceTicket.created_at)).where(
            ServiceTicket.partner_id == partner_id,
            ServiceTicket.category.in_(COMPLAINT_CATEGORIES),
        )
    )
    average = None
    if metric.order_count:
        average = money(metric.order_volume / metric.order_count)
    return PartnerAnalysis(
        partner_id=partner_id,
        order_count=metric.order_count,
        order_volume=metric.order_volume,
        average_order_value=average,
        last_order_on=metric.last_order_on,
        open_deals=metric.open_deals,
        pipeline_value=money(as_decimal(pipeline_row or 0)),
        open_tickets=metric.open_tickets,
        closed_tickets=int(closed),
        last_complaint_on=last_complaint.date() if last_complaint else None,
        last_activity_on=metric.last_activity_on,
        volume_basis=VOLUME_BASIS,
    )


def _compare(metric: PartnerMetric, condition: SegmentCondition) -> bool:
    field = condition.field_name
    operator = condition.operator
    raw = condition.value.strip()
    if field in {"partner_type", "industry", "region", "status"}:
        current = getattr(metric, field) or ""
        return current.casefold() == raw.casefold()
    if field in {"last_order_on", "last_activity_on"}:
        current = getattr(metric, field)
        if operator == "empty":
            return current is None
        try:
            limit = date.fromisoformat(raw)
        except ValueError:
            return False
        if current is None:
            return False
        if operator == "before":
            return current < limit
        return current > limit
    if field == "order_volume":
        try:
            limit = Decimal(raw)
        except Exception:
            return False
        current = metric.order_volume
    else:
        try:
            limit = Decimal(int(raw))
        except Exception:
            return False
        current = Decimal(getattr(metric, field))
    if operator == "eq":
        return current == limit
    if operator == "gte":
        return current >= limit
    return current <= limit


def _matches(metric: PartnerMetric, segment: CustomerSegment, conditions: list[SegmentCondition]) -> bool:
    if not conditions:
        return False
    results = [_compare(metric, condition) for condition in conditions]
    if segment.match_mode == "any":
        return any(results)
    return all(results)


def _segment_conditions(db: Session, segment_id: uuid.UUID) -> list[SegmentCondition]:
    return list(db.scalars(select(SegmentCondition).where(SegmentCondition.segment_id == segment_id).order_by(SegmentCondition.position)).all())


def _segment_read(db: Session, segment: CustomerSegment, metrics: list[PartnerMetric] | None = None) -> SegmentRead:
    conditions = _segment_conditions(db, segment.id)
    source = metrics if metrics is not None else _metrics(db)
    count = sum(1 for metric in source if _matches(metric, segment, conditions))
    return SegmentRead(
        id=segment.id,
        name=segment.name,
        description=segment.description,
        match_mode=segment.match_mode,
        partner_count=count,
        is_demo=segment.is_demo,
        conditions=[
            {
                "id": row.id,
                "field_name": row.field_name,
                "operator": row.operator,
                "value": row.value,
                "position": row.position,
            }
            for row in conditions
        ],
        created_at=segment.created_at,
        updated_at=segment.updated_at,
    )


def list_segments(db: Session) -> list[SegmentRead]:
    segments = db.scalars(select(CustomerSegment).order_by(CustomerSegment.name)).all()
    metrics = _metrics(db)
    return [_segment_read(db, segment, metrics) for segment in segments]


def require_segment(db: Session, segment_id: uuid.UUID) -> CustomerSegment:
    segment = db.get(CustomerSegment, segment_id)
    if segment is None:
        raise CrmServiceError("Das Segment wurde nicht gefunden.", 404)
    return segment


def _store_conditions(db: Session, segment_id: uuid.UUID, data: SegmentWrite) -> None:
    db.execute(delete(SegmentCondition).where(SegmentCondition.segment_id == segment_id))
    for index, condition in enumerate(data.conditions, start=1):
        if condition.operator != "empty" and not condition.value.strip():
            raise CrmServiceError("Jede Bedingung braucht einen Vergleichswert.", 422)
        db.add(
            SegmentCondition(
                segment_id=segment_id,
                field_name=condition.field_name,
                operator=condition.operator,
                value=condition.value.strip(),
                position=index,
            )
        )


def _name_taken(db: Session, name: str, current: uuid.UUID | None) -> None:
    existing = db.scalar(select(CustomerSegment).where(func.lower(CustomerSegment.name) == name.casefold()))
    if existing is not None and existing.id != current:
        raise CrmServiceError("Ein Segment mit diesem Namen besteht bereits.", 409)


def insert_segment(db: Session, data: SegmentWrite, *, is_demo: bool = False, demo_key: str | None = None) -> CustomerSegment:
    _name_taken(db, data.name, None)
    segment = CustomerSegment(
        name=data.name,
        description=data.description,
        match_mode=data.match_mode,
        is_demo=is_demo,
        demo_key=demo_key,
    )
    db.add(segment)
    db.flush()
    _store_conditions(db, segment.id, data)
    db.flush()
    return segment


def update_segment(db: Session, segment_id: uuid.UUID, data: SegmentWrite) -> CustomerSegment:
    segment = require_segment(db, segment_id)
    _name_taken(db, data.name, segment.id)
    segment.name = data.name
    segment.description = data.description
    segment.match_mode = data.match_mode
    segment.updated_at = _now()
    _store_conditions(db, segment.id, data)
    db.flush()
    return segment


def delete_segment(db: Session, segment_id: uuid.UUID) -> None:
    segment = require_segment(db, segment_id)
    db.execute(delete(SegmentCondition).where(SegmentCondition.segment_id == segment.id))
    db.delete(segment)
    db.flush()


def segment_partners(db: Session, segment_id: uuid.UUID) -> list[SegmentPartner]:
    segment = require_segment(db, segment_id)
    conditions = _segment_conditions(db, segment.id)
    cities = {row.id: row.city for row in db.scalars(select(Partner).where(Partner.archived_at.is_(None))).all()}
    result = []
    for metric in _metrics(db):
        if not _matches(metric, segment, conditions):
            continue
        result.append(
            SegmentPartner(
                id=metric.partner_id,
                company_name=metric.company_name,
                city=cities.get(metric.partner_id) or "",
                partner_type=metric.partner_type,
                status=metric.status,
                order_count=metric.order_count,
                order_volume=metric.order_volume,
                open_tickets=metric.open_tickets,
            )
        )
    return result


def upload_directory() -> str:
    return str(_upload_root())
