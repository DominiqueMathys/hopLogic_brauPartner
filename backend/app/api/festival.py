from datetime import datetime, timedelta, timezone
from uuid import UUID
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.access_context import set_actor, reset_actor
from app.database import get_db
from app.models.festival import FestivalAssignment, FestivalDelivery, FestivalMaterial, FestivalQuote, MaterialCategory, MaterialMovement, MaterialReservation
from app.schemas.festival import (
    AssetWrite,
    AssignmentWrite,
    DeliveryWrite,
    FestivalUpdate,
    FestivalWrite,
    IssueWrite,
    MaterialWrite,
    NoteWrite,
    QuoteItemsWrite,
    QuoteStatusWrite,
    QuoteWrite,
    ReasonWrite,
    ReplaceLineWrite,
    ReservationLineWrite,
    ReservationWrite,
    ReturnWrite,
    StockWrite,
    TicketLinkWrite,
)
from app.services.festival import (
    accept_quote,
    add_note,
    archive_festival,
    assignment_public,
    close_festival,
    convert_festival,
    create_assignment,
    create_delivery,
    create_festival,
    create_quote,
    dashboard,
    delivery_pdf,
    delivery_public,
    duplicate_festival,
    duplicate_quote,
    festival_detail,
    festival_public,
    link_ticket,
    new_quote_version,
    query_festivals,
    quote_pdf,
    quote_public,
    replace_quote_items,
    restore_festival,
    set_quote_status,
    update_assignment,
    update_delivery,
    update_festival,
)
from app.services.festival_stock import (
    FestivalError,
    add_asset,
    add_line,
    availability,
    cancel_reservation,
    check_reservation,
    confirm_reservation,
    create_category,
    create_material,
    create_reservation,
    issue_reservation,
    material_snapshot,
    post_stock,
    remove_line,
    replace_line,
    require_material,
    require_reservation,
    reservation_lines,
    return_reservation,
    update_material,
)
from sqlalchemy import select

def _bind_actor(request: Request):
    token = set_actor(getattr(request.state, "actor", None))
    try:
        yield
    finally:
        reset_actor(token)


router = APIRouter(prefix="/festivals", tags=["festmanagement"], dependencies=[Depends(_bind_actor)])
ZURICH = ZoneInfo("Europe/Zurich")


def _run(request: Request, db: Session, action):
    token = set_actor(getattr(request.state, "actor", None))
    try:
        try:
            value = action()
            db.commit()
            return value
        except FestivalError as error:
            if error.persist:
                db.commit()
            else:
                db.rollback()
            raise HTTPException(status_code=error.status_code, detail=error.message) from None
    finally:
        reset_actor(token)


def _dump(model) -> dict:
    return model.model_dump(exclude_unset=True)


def _aware_bound(value: datetime | None, end: bool = False) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZURICH)
    return value.astimezone(timezone.utc)


@router.get("")
def list_festivals(
    q: str | None = None,
    status: str | None = None,
    request_status: str | None = None,
    region: str | None = None,
    organizer: str | None = None,
    owner: str | None = None,
    partner_id: UUID | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    shortage: bool = False,
    include_archived: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> dict:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="Die Seitengrösse ist ungültig.")
    rows, total = query_festivals(
        db,
        {
            "q": q,
            "status": status,
            "request_status": request_status,
            "region": region,
            "organizer": organizer,
            "owner": owner,
            "partner_id": partner_id,
            "date_from": _aware_bound(date_from),
            "date_to": _aware_bound(date_to, end=True),
            "shortage": shortage,
            "include_archived": include_archived,
            "page": page,
            "page_size": page_size,
        },
    )
    return {"items": [festival_public(row) for row in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/dashboard")
def read_dashboard(db: Session = Depends(get_db)) -> dict:
    return dashboard(db)


@router.get("/calendar")
def read_calendar(
    start: datetime,
    end: datetime,
    region: str | None = None,
    owner: str | None = None,
    shortage: bool = False,
    db: Session = Depends(get_db),
) -> dict:
    rows, total = query_festivals(
        db,
        {
            "date_from": _aware_bound(start),
            "date_to": _aware_bound(end),
            "region": region,
            "owner": owner,
            "shortage": shortage,
            "page": 1,
            "page_size": 100,
        },
    )
    return {"items": [festival_public(row) for row in rows], "total": total}


@router.post("", status_code=201)
def post_festival(payload: FestivalWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    event = _run(request, db, lambda: create_festival(db, payload.model_dump()))
    return festival_public(event)


@router.get("/materials")
def list_materials(db: Session = Depends(get_db)) -> dict:
    rows = list(db.scalars(select(FestivalMaterial).order_by(FestivalMaterial.name)).all())
    now = datetime.now(timezone.utc)
    later = now + timedelta(hours=1)
    return {
        "items": [material_snapshot(db, row, now, later) for row in rows],
        "erp_notice": "Keine externe Lageranbindung. Bestände sind lokale CRM-Daten und keine Live-Daten eines ERP.",
    }


@router.post("/materials", status_code=201)
def post_material(payload: MaterialWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: create_material(db, payload.model_dump()))
    now = datetime.now(timezone.utc)
    return material_snapshot(db, row, now, now + timedelta(hours=1))


@router.post("/materials/categories", status_code=201)
def post_category(code: str, name: str, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: create_category(db, code, name, example=True))
    return {"id": row.id, "code": row.code, "name": row.name, "is_example": row.is_example}


@router.get("/materials/categories")
def list_categories(db: Session = Depends(get_db)) -> dict:
    rows = list(db.scalars(select(MaterialCategory).order_by(MaterialCategory.sort_order, MaterialCategory.name)).all())
    return {"items": [{"id": row.id, "code": row.code, "name": row.name, "is_example": row.is_example} for row in rows]}


@router.get("/materials/availability")
def read_availability(
    material_id: UUID,
    start: datetime,
    end: datetime,
    quantity: int = 1,
    location: str | None = None,
    prep_hours: int = 0,
    return_hours: int = 0,
    cleaning_hours: int = 0,
    db: Session = Depends(get_db),
) -> dict:
    try:
        material = require_material(db, material_id)
        return availability(
            db,
            material,
            _aware_bound(start) or start,
            _aware_bound(end) or end,
            quantity=quantity,
            location=location,
            prep_hours=prep_hours,
            return_hours=return_hours,
            cleaning_hours=cleaning_hours,
        )
    except FestivalError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None


@router.patch("/materials/{material_id}")
def patch_material(material_id: UUID, payload: MaterialWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: update_material(db, material_id, _dump(payload)))
    now = datetime.now(timezone.utc)
    return material_snapshot(db, row, now, now + timedelta(hours=1))


@router.post("/materials/{material_id}/stock")
def post_material_stock(material_id: UUID, payload: StockWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: post_stock(db, material_id, payload.model_dump()))
    now = datetime.now(timezone.utc)
    return material_snapshot(db, row, now, now + timedelta(hours=1))


@router.post("/materials/{material_id}/assets", status_code=201)
def post_asset(material_id: UUID, payload: AssetWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    asset = _run(request, db, lambda: add_asset(db, material_id, payload.inventory_number, location=payload.location))
    return {"id": asset.id, "inventory_number": asset.inventory_number, "condition": asset.condition}


@router.get("/reservations")
def list_reservations(festival_id: UUID | None = None, db: Session = Depends(get_db)) -> dict:
    from app.services.festival import reservation_public

    query = select(MaterialReservation)
    if festival_id is not None:
        query = query.where(MaterialReservation.festival_id == festival_id)
    rows = list(db.scalars(query.order_by(MaterialReservation.starts_at)).all())
    return {"items": [reservation_public(db, row) for row in rows]}


@router.post("/reservations", status_code=201)
def post_reservation(payload: ReservationWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    from app.services.festival import reservation_public

    row = _run(request, db, lambda: create_reservation(db, payload.model_dump()))
    return reservation_public(db, row)


@router.post("/reservations/{reservation_id}/lines", status_code=201)
def post_line(reservation_id: UUID, payload: ReservationLineWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    line = _run(request, db, lambda: add_line(db, reservation_id, payload.model_dump()))
    return {"id": line.id, "quantity": line.quantity}


@router.delete("/reservations/{reservation_id}/lines/{line_id}", status_code=204)
def delete_line(reservation_id: UUID, line_id: UUID, request: Request, db: Session = Depends(get_db)) -> None:
    _run(request, db, lambda: remove_line(db, reservation_id, line_id))


@router.post("/reservations/{reservation_id}/check")
def post_check(reservation_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    return _run(request, db, lambda: check_reservation(db, reservation_id))


@router.post("/reservations/{reservation_id}/confirm")
def post_confirm(reservation_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    from app.services.festival import reservation_public

    row = _run(request, db, lambda: confirm_reservation(db, reservation_id))
    return reservation_public(db, row)


@router.post("/reservations/{reservation_id}/cancel")
def post_cancel(reservation_id: UUID, payload: ReasonWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    from app.services.festival import reservation_public

    row = _run(request, db, lambda: cancel_reservation(db, reservation_id, payload.reason))
    return reservation_public(db, row)


@router.post("/reservations/{reservation_id}/replace")
def post_replace(reservation_id: UUID, payload: ReplaceLineWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    line = _run(request, db, lambda: replace_line(db, reservation_id, payload.line_id, payload.material_id, payload.quantity))
    return {"id": line.id, "material_id": line.material_id, "quantity": line.quantity}


@router.post("/reservations/{reservation_id}/issue")
def post_issue(reservation_id: UUID, payload: IssueWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: issue_reservation(db, reservation_id, payload.model_dump()))
    return {"id": row.id, "reservation_id": row.reservation_id, "issued_at": row.issued_at}


@router.post("/reservations/{reservation_id}/return")
def post_return(reservation_id: UUID, payload: ReturnWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: return_reservation(db, reservation_id, payload.model_dump()))
    reservation = require_reservation(db, reservation_id)
    lines = reservation_lines(db, reservation.id)
    return {
        "id": row.id,
        "status": reservation.status,
        "lines": [
            {
                "id": line.id,
                "returned_qty": line.returned_qty,
                "damaged_qty": line.damaged_qty,
                "missing_qty": line.missing_qty,
            }
            for line in lines
        ],
    }


@router.get("/quotes")
def list_quotes(festival_id: UUID | None = None, db: Session = Depends(get_db)) -> dict:
    query = select(FestivalQuote)
    if festival_id is not None:
        query = query.where(FestivalQuote.festival_id == festival_id)
    rows = list(db.scalars(query.order_by(FestivalQuote.created_at.desc())).all())
    return {"items": [quote_public(db, row) for row in rows]}


@router.post("/quotes", status_code=201)
def post_quote(payload: QuoteWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: create_quote(db, payload.model_dump()))
    return quote_public(db, row)


@router.put("/quotes/{quote_id}/items")
def put_quote_items(quote_id: UUID, payload: QuoteItemsWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: replace_quote_items(db, quote_id, [item.model_dump() for item in payload.items]))
    return quote_public(db, row)


@router.post("/quotes/{quote_id}/status")
def post_quote_status(quote_id: UUID, payload: QuoteStatusWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: set_quote_status(db, quote_id, payload.status))
    return quote_public(db, row)


@router.post("/quotes/{quote_id}/duplicate", status_code=201)
def post_duplicate_quote(quote_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: duplicate_quote(db, quote_id))
    return quote_public(db, row)


@router.post("/quotes/{quote_id}/version", status_code=201)
def post_quote_version(quote_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: new_quote_version(db, quote_id))
    return quote_public(db, row)


@router.post("/quotes/{quote_id}/accept")
def post_accept_quote(quote_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: accept_quote(db, quote_id))
    return quote_public(db, row)


@router.get("/quotes/{quote_id}/pdf")
def get_quote_pdf(quote_id: UUID, db: Session = Depends(get_db)) -> Response:
    try:
        filename, content = quote_pdf(db, quote_id)
    except FestivalError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/deliveries")
def list_deliveries(festival_id: UUID | None = None, db: Session = Depends(get_db)) -> dict:
    query = select(FestivalDelivery)
    if festival_id is not None:
        query = query.where(FestivalDelivery.festival_id == festival_id)
    rows = list(db.scalars(query.order_by(FestivalDelivery.deliver_at)).all())
    return {"items": [delivery_public(row) for row in rows]}


@router.post("/deliveries", status_code=201)
def post_delivery(payload: DeliveryWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: create_delivery(db, payload.model_dump()))
    return delivery_public(row)


@router.patch("/deliveries/{delivery_id}")
def patch_delivery(delivery_id: UUID, payload: DeliveryWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: update_delivery(db, delivery_id, _dump(payload)))
    return delivery_public(row)


@router.get("/deliveries/{delivery_id}/pdf")
def get_delivery_pdf(delivery_id: UUID, db: Session = Depends(get_db)) -> Response:
    try:
        filename, content = delivery_pdf(db, delivery_id)
    except FestivalError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return Response(content=content, media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/assignments")
def list_assignments(festival_id: UUID | None = None, db: Session = Depends(get_db)) -> dict:
    query = select(FestivalAssignment)
    if festival_id is not None:
        query = query.where(FestivalAssignment.festival_id == festival_id)
    rows = list(db.scalars(query.order_by(FestivalAssignment.starts_at)).all())
    return {"items": [assignment_public(row) for row in rows]}


@router.post("/assignments", status_code=201)
def post_assignment(payload: AssignmentWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: create_assignment(db, payload.model_dump()))
    return assignment_public(row)


@router.patch("/assignments/{assignment_id}")
def patch_assignment(assignment_id: UUID, payload: AssignmentWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: update_assignment(db, assignment_id, _dump(payload)))
    return assignment_public(row)


@router.get("/movements")
def list_movements(material_id: UUID | None = None, festival_id: UUID | None = None, db: Session = Depends(get_db)) -> dict:
    query = select(MaterialMovement).order_by(MaterialMovement.occurred_at.desc()).limit(200)
    if material_id is not None:
        query = query.where(MaterialMovement.material_id == material_id)
    if festival_id is not None:
        query = query.where(MaterialMovement.festival_id == festival_id)
    rows = list(db.scalars(query).all())
    return {
        "items": [
            {
                "id": row.id,
                "material_id": row.material_id,
                "festival_id": row.festival_id,
                "reservation_id": row.reservation_id,
                "movement_type": row.movement_type,
                "quantity": row.quantity,
                "occurred_at": row.occurred_at,
                "actor_label": row.actor_label,
                "note": row.note,
            }
            for row in rows
        ]
    }


@router.get("/{festival_id}")
def read_festival(festival_id: UUID, db: Session = Depends(get_db)) -> dict:
    try:
        return festival_detail(db, festival_id)
    except FestivalError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None


@router.patch("/{festival_id}")
def patch_festival(festival_id: UUID, payload: FestivalUpdate, request: Request, db: Session = Depends(get_db)) -> dict:
    data = _dump(payload)
    reason = data.pop("change_reason", None)
    data.pop("change_note", None)
    note = payload.change_note
    if note:
        data["change_note"] = note
    event = _run(request, db, lambda: update_festival(db, festival_id, data, reason))
    return festival_public(event)


@router.post("/{festival_id}/duplicate", status_code=201)
def post_duplicate(festival_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    event = _run(request, db, lambda: duplicate_festival(db, festival_id))
    return festival_public(event)


@router.post("/{festival_id}/archive")
def post_archive(festival_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    event = _run(request, db, lambda: archive_festival(db, festival_id))
    return festival_public(event)


@router.post("/{festival_id}/restore")
def post_restore(festival_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    event = _run(request, db, lambda: restore_festival(db, festival_id))
    return festival_public(event)


@router.post("/{festival_id}/convert")
def post_convert(festival_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    return _run(request, db, lambda: convert_festival(db, festival_id))


@router.post("/{festival_id}/close")
def post_close(festival_id: UUID, request: Request, db: Session = Depends(get_db)) -> dict:
    event = _run(request, db, lambda: close_festival(db, festival_id))
    return festival_public(event)


@router.post("/{festival_id}/notes", status_code=201)
def post_note(festival_id: UUID, payload: NoteWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: add_note(db, festival_id, payload.title, payload.description or "", payload.activity_type))
    return {"id": row.id, "title": row.title}


@router.post("/{festival_id}/tickets")
def post_ticket_link(festival_id: UUID, payload: TicketLinkWrite, request: Request, db: Session = Depends(get_db)) -> dict:
    row = _run(request, db, lambda: link_ticket(db, festival_id, payload.ticket_id))
    return {"id": row.id, "event_id": row.event_id}
