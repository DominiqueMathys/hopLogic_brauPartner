from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.crm_support import check_page, clean_query, run_write
from app.config import settings
from app.database import get_db
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
    TicketList,
    TicketSummary,
    TicketTaskCreate,
    TicketUpdate,
    TicketWrite,
)
from app.schemas.task import TaskRead
from app.service_catalog import (
    RESOLUTION_CODES,
    SEGMENT_FIELDS,
    TICKET_CATEGORIES,
    TICKET_PRIORITIES,
    TICKET_SORTS,
    TICKET_STATUSES,
)
from app.services.crm import CrmServiceError, read_tasks
from app.services.service_desk import (
    add_note,
    add_task,
    assign_ticket,
    attachment_file,
    change_priority,
    change_status,
    close_ticket,
    delete_attachment,
    delete_segment,
    insert_segment,
    insert_ticket,
    list_segments,
    partner_analysis,
    query_tickets,
    read_ticket,
    reopen_ticket,
    require_segment,
    resolve_ticket,
    save_attachment,
    segment_partners,
    ticket_summary,
    update_segment,
    update_ticket,
    upload_directory,
)

tickets_router = APIRouter(prefix="/tickets", tags=["kundenservice"])
segments_router = APIRouter(prefix="/segments", tags=["segmente"])
analysis_router = APIRouter(tags=["analyse"])

UPLOAD_NOTICE = (
    "Dateien liegen unter data/ticket-attachments und sind nicht öffentlich ausgeliefert. "
    "Es gibt noch keine Anmeldung. Der Upload ist deshalb nicht für einen öffentlichen Produktivbetrieb geeignet."
)


def _choice(value: str | None, allowed: tuple[str, ...], label: str) -> str | None:
    cleaned = clean_query(value, 40)
    if cleaned is None:
        return None
    if cleaned not in allowed:
        raise HTTPException(status_code=422, detail=f"{label} ist ungültig.")
    return cleaned


@tickets_router.get("/summary", response_model=TicketSummary)
def read_summary(db: Session = Depends(get_db)) -> TicketSummary:
    return ticket_summary(db)


@tickets_router.get("/meta")
def read_meta() -> dict[str, object]:
    return {
        "categories": TICKET_CATEGORIES,
        "priorities": TICKET_PRIORITIES,
        "statuses": TICKET_STATUSES,
        "resolutions": RESOLUTION_CODES,
        "segment_fields": SEGMENT_FIELDS,
        "max_bytes": settings.ticket_max_bytes,
        "storage": upload_directory(),
        "notice": UPLOAD_NOTICE,
    }


@tickets_router.get("", response_model=TicketList)
def list_tickets(
    q: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    category: str | None = None,
    account_owner: str | None = None,
    partner_id: UUID | None = None,
    contact_id: UUID | None = None,
    order_id: UUID | None = None,
    scope: str | None = None,
    sort: str = "updated_at",
    direction: str = "desc",
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> TicketList:
    check_page(page, page_size)
    if sort not in TICKET_SORTS:
        raise HTTPException(status_code=422, detail="Die Sortierung ist ungültig.")
    if direction not in {"asc", "desc"}:
        raise HTTPException(status_code=422, detail="Die Sortierrichtung ist ungültig.")
    cleaned_scope = _choice(scope, ("open", "closed", "overdue"), "Ansicht")
    return query_tickets(
        db,
        q=clean_query(q),
        status=_choice(status, TICKET_STATUSES, "Status"),
        priority=_choice(priority, TICKET_PRIORITIES, "Priorität"),
        category=_choice(category, TICKET_CATEGORIES, "Kategorie"),
        account_owner=clean_query(account_owner, 120),
        partner_id=partner_id,
        contact_id=contact_id,
        order_id=order_id,
        scope=cleaned_scope,
        sort=sort,
        direction=direction,
        page=page,
        page_size=page_size,
    )


@tickets_router.post("", response_model=TicketDetail, status_code=201)
def create_ticket(payload: TicketWrite, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = run_write(db, lambda: insert_ticket(db, payload))
    return read_ticket(db, ticket.id)


@tickets_router.get("/{ticket_id}", response_model=TicketDetail)
def get_ticket(ticket_id: UUID, db: Session = Depends(get_db)) -> TicketDetail:
    try:
        return read_ticket(db, ticket_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None


@tickets_router.put("/{ticket_id}", response_model=TicketDetail)
def edit_ticket(ticket_id: UUID, payload: TicketUpdate, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = run_write(db, lambda: update_ticket(db, ticket_id, payload))
    return read_ticket(db, ticket.id)


@tickets_router.post("/{ticket_id}/status", response_model=TicketDetail)
def set_status(ticket_id: UUID, payload: StatusChange, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = run_write(db, lambda: change_status(db, ticket_id, payload))
    return read_ticket(db, ticket.id)


@tickets_router.post("/{ticket_id}/priority", response_model=TicketDetail)
def set_priority(ticket_id: UUID, payload: PriorityChange, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = run_write(db, lambda: change_priority(db, ticket_id, payload))
    return read_ticket(db, ticket.id)


@tickets_router.post("/{ticket_id}/assign", response_model=TicketDetail)
def set_owner(ticket_id: UUID, payload: AssignChange, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = run_write(db, lambda: assign_ticket(db, ticket_id, payload))
    return read_ticket(db, ticket.id)


@tickets_router.post("/{ticket_id}/notes", response_model=TicketDetail)
def create_note(ticket_id: UUID, payload: NoteCreate, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = run_write(db, lambda: add_note(db, ticket_id, payload))
    return read_ticket(db, ticket.id)


@tickets_router.post("/{ticket_id}/resolve", response_model=TicketDetail)
def resolve(ticket_id: UUID, payload: ResolveCreate, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = run_write(db, lambda: resolve_ticket(db, ticket_id, payload))
    return read_ticket(db, ticket.id)


@tickets_router.post("/{ticket_id}/close", response_model=TicketDetail)
def close(ticket_id: UUID, payload: Actor, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = run_write(db, lambda: close_ticket(db, ticket_id, payload))
    return read_ticket(db, ticket.id)


@tickets_router.post("/{ticket_id}/reopen", response_model=TicketDetail)
def reopen(ticket_id: UUID, payload: Actor, db: Session = Depends(get_db)) -> TicketDetail:
    ticket = run_write(db, lambda: reopen_ticket(db, ticket_id, payload))
    return read_ticket(db, ticket.id)


@tickets_router.post("/{ticket_id}/tasks", response_model=TaskRead, status_code=201)
def create_task(ticket_id: UUID, payload: TicketTaskCreate, db: Session = Depends(get_db)) -> TaskRead:
    task = run_write(db, lambda: add_task(db, ticket_id, payload))
    return read_tasks(db, [task])[0]


@tickets_router.post("/{ticket_id}/attachments", response_model=TicketAttachmentRead, status_code=201)
def upload(ticket_id: UUID, file: UploadFile = File(...), db: Session = Depends(get_db)) -> TicketAttachmentRead:
    payload = file.file.read(settings.ticket_max_bytes + 1)
    row = run_write(db, lambda: save_attachment(db, ticket_id, file.filename or "", payload))
    return TicketAttachmentRead(
        id=row.id,
        original_name=row.original_name,
        content_type=row.content_type,
        size_bytes=row.size_bytes,
        created_at=row.created_at,
    )


@tickets_router.get("/{ticket_id}/attachments/{attachment_id}")
def download(ticket_id: UUID, attachment_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    try:
        row, path = attachment_file(db, ticket_id, attachment_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return FileResponse(path, media_type=row.content_type, filename=row.original_name)


@tickets_router.delete("/{ticket_id}/attachments/{attachment_id}", status_code=204)
def remove_attachment(ticket_id: UUID, attachment_id: UUID, db: Session = Depends(get_db)) -> None:
    run_write(db, lambda: delete_attachment(db, ticket_id, attachment_id))


@segments_router.get("", response_model=list[SegmentRead])
def get_segments(db: Session = Depends(get_db)) -> list[SegmentRead]:
    return list_segments(db)


@segments_router.post("", response_model=SegmentRead, status_code=201)
def create_segment(payload: SegmentWrite, db: Session = Depends(get_db)) -> SegmentRead:
    segment = run_write(db, lambda: insert_segment(db, payload))
    return next(item for item in list_segments(db) if item.id == segment.id)


@segments_router.get("/{segment_id}", response_model=SegmentRead)
def get_segment(segment_id: UUID, db: Session = Depends(get_db)) -> SegmentRead:
    try:
        require_segment(db, segment_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return next(item for item in list_segments(db) if item.id == segment_id)


@segments_router.put("/{segment_id}", response_model=SegmentRead)
def edit_segment(segment_id: UUID, payload: SegmentWrite, db: Session = Depends(get_db)) -> SegmentRead:
    segment = run_write(db, lambda: update_segment(db, segment_id, payload))
    return next(item for item in list_segments(db) if item.id == segment.id)


@segments_router.delete("/{segment_id}", status_code=204)
def remove_segment(segment_id: UUID, db: Session = Depends(get_db)) -> None:
    run_write(db, lambda: delete_segment(db, segment_id))


@segments_router.get("/{segment_id}/partners", response_model=list[SegmentPartner])
def get_segment_partners(segment_id: UUID, db: Session = Depends(get_db)) -> list[SegmentPartner]:
    try:
        return segment_partners(db, segment_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None


@analysis_router.get("/partners/{partner_id}/analysis", response_model=PartnerAnalysis)
def get_analysis(partner_id: UUID, db: Session = Depends(get_db)) -> PartnerAnalysis:
    try:
        return partner_analysis(db, partner_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
