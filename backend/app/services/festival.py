"""Festivals, quotes, transports, assignments and festival metrics.

A request does not confirm material. Binding reservations happen only after the
festival order is confirmed and the stock check passes inside a locked transaction.
Ending a festival does not count material as physically returned.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.festival_catalog import HOLDING_STATUSES
from app.models.activity import Activity
from app.models.contact import Contact
from app.models.festival import (
    Festival,
    FestivalAssignment,
    FestivalChange,
    FestivalDelivery,
    FestivalMaterial,
    FestivalQuote,
    FestivalQuoteItem,
    MaterialReservation,
    MaterialReservationLine,
)
from app.models.partner import Partner, utcnow
from app.models.sales import Order
from app.models.service import ServiceTicket
from app.models.task import Task
from app.services.festival_stock import FestivalError, actor_label, next_number
from app.services.money import as_decimal, line_amounts, money

ZURICH = ZoneInfo("Europe/Zurich")
OPEN_REQUESTS = ("neue_anfrage", "in_pruefung", "offerte_vorbereitung", "offerte_versendet")
QUOTE_RANK = ("angenommen", "versendet", "in_pruefung", "entwurf", "abgelehnt", "abgelaufen")


def refresh_festival(db: Session, festival_id: UUID) -> Festival:
    event = db.get(Festival, festival_id)
    if event is None:
        raise FestivalError("Das Fest wurde nicht gefunden.", 404)
    reservations = list(db.scalars(select(MaterialReservation).where(MaterialReservation.festival_id == event.id)).all())
    active = [row for row in reservations if row.status != "storniert"]
    lines: list[MaterialReservationLine] = []
    if active:
        lines = list(
            db.scalars(
                select(MaterialReservationLine).where(
                    MaterialReservationLine.reservation_id.in_([row.id for row in active])
                )
            ).all()
        )
    by_reservation: dict[UUID, list[MaterialReservationLine]] = {}
    for line in lines:
        by_reservation.setdefault(line.reservation_id, []).append(line)

    def still_out(row: MaterialReservation) -> bool:
        return any(
            item.issued_qty - item.returned_qty - item.damaged_qty - item.missing_qty > 0
            for item in by_reservation.get(row.id, [])
        )

    if not active and not (event.material_wish or "").strip():
        event.material_status = "kein_bedarf"
    elif any(row.status in {"ausgegeben", "teilweise_zurueckgegeben"} and still_out(row) for row in active):
        event.material_status = "ruecknahme_offen"
    elif active and all(row.status == "zurueckgegeben" for row in active):
        event.material_status = "abgeschlossen"
    elif any(row.status == "ausgegeben" for row in active):
        event.material_status = "ausgegeben"
    elif any(row.status == "bestaetigt" for row in active):
        event.material_status = "reserviert"
    elif any(row.status == "teilweise_verfuegbar" for row in active):
        event.material_status = "konflikt"
    elif active:
        event.material_status = "ungeprueft"
    else:
        event.material_status = "kein_bedarf"

    quotes = list(db.scalars(select(FestivalQuote.status).where(FestivalQuote.festival_id == event.id)).all())
    event.quote_status = next((status for status in QUOTE_RANK if status in quotes), "keine")
    deliveries = list(
        db.scalars(
            select(FestivalDelivery)
            .where(FestivalDelivery.festival_id == event.id)
            .order_by(FestivalDelivery.updated_at.desc())
        ).all()
    )
    event.delivery_status = deliveries[0].status if deliveries else "keine"
    event.updated_at = utcnow()
    db.flush()
    return event


def _log(db: Session, event: Festival, field: str, old: object, new: object, reason: str | None, note: str | None = None) -> None:
    db.add(
        FestivalChange(
            festival_id=event.id,
            changed_at=utcnow(),
            actor_label=actor_label(),
            field_name=field,
            old_value=None if old is None else str(old)[:2000],
            new_value=None if new is None else str(new)[:2000],
            reason=reason,
            note=note,
        )
    )


def _require_festival(db: Session, festival_id: UUID) -> Festival:
    event = db.get(Festival, festival_id)
    if event is None:
        raise FestivalError("Das Fest wurde nicht gefunden.", 404)
    return event


def _ensure_partner(db: Session, partner_id: UUID | None) -> None:
    if partner_id is not None and db.get(Partner, partner_id) is None:
        raise FestivalError("Der Vertriebspartner wurde nicht gefunden.", 422)


def _ensure_contact(db: Session, contact_id: UUID | None) -> None:
    if contact_id is not None and db.get(Contact, contact_id) is None:
        raise FestivalError("Der Kontakt wurde nicht gefunden.", 422)


def _ensure_order(db: Session, order_id: UUID | None) -> None:
    if order_id is not None and db.get(Order, order_id) is None:
        raise FestivalError("Die Bestellung wurde nicht gefunden.", 422)


def create_festival(db: Session, data: dict, *, is_demo: bool = False, demo_key: str | None = None, publish: bool = True) -> Festival:
    if demo_key:
        existing = db.scalar(select(Festival).where(Festival.demo_key == demo_key))
        if existing is not None:
            return existing
    _ensure_partner(db, data.get("organizer_partner_id"))
    _ensure_partner(db, data.get("distributor_partner_id"))
    _ensure_contact(db, data.get("contact_id"))
    _ensure_order(db, data.get("order_id"))
    if data["ends_at"] <= data["starts_at"]:
        raise FestivalError("Das Ende muss nach dem Beginn liegen.", 422)
    event = Festival(
        event_number=next_number(db, "fest", "FEST"),
        name=data["name"],
        description=data.get("description"),
        event_type=data.get("event_type") or "fest",
        organizer_name=data["organizer_name"],
        organizer_partner_id=data.get("organizer_partner_id"),
        distributor_partner_id=data.get("distributor_partner_id"),
        contact_id=data.get("contact_id"),
        contact_name=data.get("contact_name"),
        phone=data.get("phone"),
        email=data.get("email"),
        venue_name=data.get("venue_name"),
        street=data.get("street"),
        postal_code=data.get("postal_code"),
        city=data.get("city"),
        region=data.get("region"),
        country=data.get("country") or "Schweiz",
        starts_at=data["starts_at"],
        ends_at=data["ends_at"],
        expected_visitors=data.get("expected_visitors"),
        notes=data.get("notes"),
        requirements=data.get("requirements"),
        drinks=data.get("drinks"),
        material_wish=data.get("material_wish"),
        delivery_wish_at=data.get("delivery_wish_at"),
        pickup_wish_at=data.get("pickup_wish_at"),
        account_owner=data.get("account_owner"),
        request_status="neue_anfrage",
        event_status="anfrage",
        is_binding=False,
        order_id=data.get("order_id"),
        is_demo=is_demo,
        demo_key=demo_key,
    )
    db.add(event)
    db.flush()
    _log(db, event, "request_status", None, "neue_anfrage", "Neue Festanfrage", data.get("notes"))
    db.flush()
    if publish:
        from app.services.automation import publish_event

        publish_event(
            db,
            "festival_request_created",
            dedupe_key=f"festival-request:{event.id}",
            context={
                "owner": event.account_owner,
                "partner_id": event.distributor_partner_id or event.organizer_partner_id,
                "contact_id": event.contact_id,
                "event_id": event.id,
                "href": f"/festmanagement/{event.id}",
                "subject_title": event.name,
            },
        )
    return event


WRITABLE = (
    "name",
    "description",
    "event_type",
    "organizer_name",
    "organizer_partner_id",
    "distributor_partner_id",
    "contact_id",
    "contact_name",
    "phone",
    "email",
    "venue_name",
    "street",
    "postal_code",
    "city",
    "region",
    "country",
    "starts_at",
    "ends_at",
    "expected_visitors",
    "notes",
    "requirements",
    "drinks",
    "material_wish",
    "delivery_wish_at",
    "pickup_wish_at",
    "account_owner",
    "request_status",
    "order_id",
)


def update_festival(db: Session, festival_id: UUID, data: dict, reason: str | None) -> Festival:
    from app.access_context import current_actor

    event = _require_festival(db, festival_id)
    if event.archived_at is not None:
        raise FestivalError("Das Fest ist archiviert.", 409)
    _ensure_partner(db, data.get("organizer_partner_id", event.organizer_partner_id))
    _ensure_partner(db, data.get("distributor_partner_id", event.distributor_partner_id))
    _ensure_contact(db, data.get("contact_id", event.contact_id))
    _ensure_order(db, data.get("order_id", event.order_id))
    changed: list[tuple[str, object, object]] = []
    for field in WRITABLE:
        if field not in data:
            continue
        new = data[field]
        old = getattr(event, field)
        if new != old:
            changed.append((field, old, new))
    if not changed:
        return event
    if not (reason or "").strip():
        raise FestivalError("Eine Änderung braucht einen Grund.", 422)
    if event.is_binding and any(field in {"starts_at", "ends_at"} for field, _, _ in changed):
        actor = current_actor.get()
        if actor is None or "festivals.confirm" not in actor.permissions:
            raise FestivalError("Verbindliche Termine dürfen nur mit Freigabe geändert werden.", 403)
    for field, _, new in changed:
        setattr(event, field, new)
    if event.ends_at <= event.starts_at:
        raise FestivalError("Das Ende muss nach dem Beginn liegen.", 422)
    if any(field in {"starts_at", "ends_at"} for field, _, _ in changed):
        _move_reservations(db, event)
    if event.request_status == "storniert":
        _cancel_open_reservations(db, event, reason or "Fest storniert")
        event.event_status = "storniert"
    for field, old, new in changed:
        _log(db, event, field, old, new, reason, data.get("change_note"))
    db.flush()
    return refresh_festival(db, event.id)


def _move_reservations(db: Session, event: Festival) -> None:
    from app.services.festival_stock import availability, lock_materials, require_material, reservation_lines

    rows = list(
        db.scalars(
            select(MaterialReservation).where(
                MaterialReservation.festival_id == event.id,
                MaterialReservation.status.notin_(("storniert", "zurueckgegeben")),
            )
        ).all()
    )
    for row in rows:
        row.starts_at = event.starts_at
        row.ends_at = event.ends_at
    holding = [row for row in rows if row.status in HOLDING_STATUSES]
    material_ids: list[UUID] = []
    cached: list[tuple[MaterialReservation, list]] = []
    for row in holding:
        lines = reservation_lines(db, row.id)
        cached.append((row, lines))
        material_ids.extend(line.material_id for line in lines)
    lock_materials(db, material_ids)
    shortages: list[str] = []
    for row, lines in cached:
        for line in lines:
            material = require_material(db, line.material_id)
            info = availability(
                db,
                material,
                row.starts_at,
                row.ends_at,
                quantity=line.quantity if row.status == "bestaetigt" else max(line.issued_qty, 1),
                location=row.location,
                ignore_reservation_id=row.id,
                prep_hours=row.prep_hours,
                return_hours=row.return_hours,
                cleaning_hours=row.cleaning_hours,
            )
            if not info["enough"]:
                shortages.append(f"{material.name}: verfügbar {info['available']}")
    if shortages:
        raise FestivalError("Der neue Zeitraum erzeugt einen Materialkonflikt. " + " ".join(shortages), 409)


def _cancel_open_reservations(db: Session, event: Festival, reason: str) -> None:
    from app.services.festival_stock import cancel_reservation

    rows = list(db.scalars(select(MaterialReservation).where(MaterialReservation.festival_id == event.id)).all())
    for row in rows:
        if row.status in HOLDING_STATUSES:
            raise FestivalError("Zuerst die verbindliche Materialreservation stornieren oder abschliessen.", 409)
        if row.status not in {"storniert", "zurueckgegeben"}:
            cancel_reservation(db, row.id, reason)


def duplicate_festival(db: Session, festival_id: UUID) -> Festival:
    source = _require_festival(db, festival_id)
    payload = {field: getattr(source, field) for field in WRITABLE if field != "request_status"}
    payload["name"] = f"{source.name} (Kopie)"
    payload["request_status"] = "neue_anfrage"
    copy = create_festival(db, payload, publish=True)
    from app.services.festival_stock import create_reservation

    for reservation in db.scalars(select(MaterialReservation).where(MaterialReservation.festival_id == source.id)).all():
        if reservation.status == "storniert":
            continue
        lines = db.scalars(select(MaterialReservationLine).where(MaterialReservationLine.reservation_id == reservation.id)).all()
        create_reservation(
            db,
            {
                "festival_id": copy.id,
                "status": "angefragt",
                "starts_at": copy.starts_at,
                "ends_at": copy.ends_at,
                "prep_hours": reservation.prep_hours,
                "return_hours": reservation.return_hours,
                "cleaning_hours": reservation.cleaning_hours,
                "location": reservation.location,
                "notes": "Kopie ohne verbindliche Reservation.",
                "lines": [
                    {"material_id": line.material_id, "asset_id": line.asset_id, "quantity": line.quantity}
                    for line in lines
                    if line.asset_id is None
                ],
            },
        )
    return copy


def archive_festival(db: Session, festival_id: UUID) -> Festival:
    event = _require_festival(db, festival_id)
    holding = db.scalar(
        select(MaterialReservation.id).where(
            MaterialReservation.festival_id == event.id,
            MaterialReservation.status.in_(HOLDING_STATUSES),
        )
    )
    if holding is not None:
        raise FestivalError("Zuerst offene Materialreservationen stornieren oder abschliessen.", 409)
    event.archived_at = utcnow()
    event.event_status = "archiviert"
    _log(db, event, "event_status", "archiviert", "archiviert", "Archiviert", None)
    db.flush()
    return event


def restore_festival(db: Session, festival_id: UUID) -> Festival:
    event = _require_festival(db, festival_id)
    event.archived_at = None
    if event.event_status == "archiviert":
        event.event_status = "geplant" if event.is_binding else "anfrage"
    _log(db, event, "archived_at", "archiviert", None, "Wiederhergestellt", None)
    db.flush()
    return event


def convert_festival(db: Session, festival_id: UUID) -> dict[str, object]:
    event = _require_festival(db, festival_id)
    if event.is_binding:
        raise FestivalError("Der Festauftrag ist bereits bestätigt.", 409)
    accepted = db.scalar(
        select(FestivalQuote.id).where(FestivalQuote.festival_id == event.id, FestivalQuote.status == "angenommen")
    )
    if accepted is None:
        raise FestivalError("Zuerst muss eine Offerte angenommen werden.", 409)
    event.is_binding = True
    event.event_status = "bestaetigt"
    event.request_status = "bestaetigt"
    _log(db, event, "event_status", "anfrage", "bestaetigt", "Festauftrag bestätigt", None)
    from app.services.festival_stock import availability, require_material, reservation_lines

    checks = []
    for reservation in db.scalars(
        select(MaterialReservation).where(
            MaterialReservation.festival_id == event.id,
            MaterialReservation.status.notin_(("storniert", "zurueckgegeben")),
        )
    ).all():
        for line in reservation_lines(db, reservation.id):
            material = require_material(db, line.material_id)
            info = availability(
                db,
                material,
                reservation.starts_at,
                reservation.ends_at,
                quantity=line.quantity,
                location=reservation.location,
                ignore_reservation_id=reservation.id,
                prep_hours=reservation.prep_hours,
                return_hours=reservation.return_hours,
                cleaning_hours=reservation.cleaning_hours,
            )
            checks.append(info)
    db.flush()
    refresh_festival(db, event.id)
    return {"festival_id": event.id, "is_binding": True, "availability": checks}


def close_festival(db: Session, festival_id: UUID) -> Festival:
    event = _require_festival(db, festival_id)
    open_hold = db.scalar(
        select(MaterialReservation.id).where(
            MaterialReservation.festival_id == event.id,
            MaterialReservation.status.in_(HOLDING_STATUSES),
        )
    )
    if open_hold is not None:
        raise FestivalError("Offene Ausgaben oder Reservationen müssen zuerst abgeschlossen werden.", 409)
    previous = event.event_status
    event.event_status = "abgeschlossen"
    _log(db, event, "event_status", previous, "abgeschlossen", "Fest abgeschlossen", None)
    db.flush()
    return event


def query_festivals(db: Session, filters: dict) -> tuple[list[Festival], int]:
    query = select(Festival)
    if not filters.get("include_archived"):
        query = query.where(Festival.archived_at.is_(None))
    if filters.get("q"):
        like = f"%{filters['q']}%"
        query = query.where(
            or_(
                Festival.name.ilike(like),
                Festival.event_number.ilike(like),
                Festival.organizer_name.ilike(like),
                Festival.city.ilike(like),
                Festival.venue_name.ilike(like),
            )
        )
    if filters.get("status"):
        query = query.where(Festival.event_status == filters["status"])
    if filters.get("request_status"):
        query = query.where(Festival.request_status == filters["request_status"])
    if filters.get("region"):
        query = query.where(Festival.region == filters["region"])
    if filters.get("organizer"):
        query = query.where(Festival.organizer_name.ilike(f"%{filters['organizer']}%"))
    if filters.get("owner"):
        query = query.where(Festival.account_owner == filters["owner"])
    if filters.get("partner_id"):
        partner_id = filters["partner_id"]
        query = query.where(or_(Festival.organizer_partner_id == partner_id, Festival.distributor_partner_id == partner_id))
    if filters.get("date_from"):
        query = query.where(Festival.ends_at >= filters["date_from"])
    if filters.get("date_to"):
        query = query.where(Festival.starts_at <= filters["date_to"])
    if filters.get("shortage"):
        query = query.where(Festival.material_status.in_(("teilweise", "konflikt", "ruecknahme_offen")))
    total = len(db.scalars(query).all())
    page = int(filters.get("page") or 1)
    page_size = int(filters.get("page_size") or 20)
    rows = list(
        db.scalars(query.order_by(Festival.starts_at.asc()).offset((page - 1) * page_size).limit(page_size)).all()
    )
    return rows, total


def festival_public(event: Festival) -> dict[str, object]:
    return {
        "id": event.id,
        "event_number": event.event_number,
        "name": event.name,
        "description": event.description,
        "event_type": event.event_type,
        "organizer_name": event.organizer_name,
        "organizer_partner_id": event.organizer_partner_id,
        "distributor_partner_id": event.distributor_partner_id,
        "contact_id": event.contact_id,
        "contact_name": event.contact_name,
        "phone": event.phone,
        "email": event.email,
        "venue_name": event.venue_name,
        "street": event.street,
        "postal_code": event.postal_code,
        "city": event.city,
        "region": event.region,
        "country": event.country,
        "starts_at": event.starts_at,
        "ends_at": event.ends_at,
        "expected_visitors": event.expected_visitors,
        "notes": event.notes,
        "requirements": event.requirements,
        "drinks": event.drinks,
        "material_wish": event.material_wish,
        "delivery_wish_at": event.delivery_wish_at,
        "pickup_wish_at": event.pickup_wish_at,
        "account_owner": event.account_owner,
        "request_status": event.request_status,
        "event_status": event.event_status,
        "material_status": event.material_status,
        "quote_status": event.quote_status,
        "delivery_status": event.delivery_status,
        "is_binding": event.is_binding,
        "order_id": event.order_id,
        "is_demo": event.is_demo,
        "archived_at": event.archived_at,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


def festival_detail(db: Session, festival_id: UUID) -> dict[str, object]:
    event = _require_festival(db, festival_id)
    payload = festival_public(event)
    payload["changes"] = [
        {
            "id": row.id,
            "changed_at": row.changed_at,
            "actor_label": row.actor_label,
            "field_name": row.field_name,
            "old_value": row.old_value,
            "new_value": row.new_value,
            "reason": row.reason,
            "note": row.note,
        }
        for row in db.scalars(
            select(FestivalChange).where(FestivalChange.festival_id == event.id).order_by(FestivalChange.changed_at.desc())
        ).all()
    ]
    payload["quotes"] = [quote_public(db, row) for row in db.scalars(select(FestivalQuote).where(FestivalQuote.festival_id == event.id)).all()]
    payload["reservations"] = [
        reservation_public(db, row)
        for row in db.scalars(select(MaterialReservation).where(MaterialReservation.festival_id == event.id)).all()
    ]
    payload["deliveries"] = [
        delivery_public(row)
        for row in db.scalars(select(FestivalDelivery).where(FestivalDelivery.festival_id == event.id)).all()
    ]
    payload["assignments"] = [
        assignment_public(row)
        for row in db.scalars(select(FestivalAssignment).where(FestivalAssignment.festival_id == event.id)).all()
    ]
    payload["tickets"] = [
        {"id": row.id, "ticket_number": row.ticket_number, "subject": row.subject, "status": row.status}
        for row in db.scalars(select(ServiceTicket).where(ServiceTicket.event_id == event.id)).all()
    ]
    payload["activities"] = [
        {"id": row.id, "title": row.title, "occurred_at": row.occurred_at, "activity_type": row.activity_type}
        for row in db.scalars(select(Activity).where(Activity.event_id == event.id)).all()
    ]
    payload["tasks"] = [
        {"id": row.id, "title": row.title, "status": row.status, "due_at": row.due_at}
        for row in db.scalars(select(Task).where(Task.event_id == event.id)).all()
    ]
    return payload


def reservation_public(db: Session, row: MaterialReservation) -> dict[str, object]:
    lines = []
    for line in db.scalars(select(MaterialReservationLine).where(MaterialReservationLine.reservation_id == row.id)).all():
        material = db.get(FestivalMaterial, line.material_id)
        lines.append(
            {
                "id": line.id,
                "material_id": line.material_id,
                "material_name": material.name if material else "",
                "asset_id": line.asset_id,
                "quantity": line.quantity,
                "issued_qty": line.issued_qty,
                "returned_qty": line.returned_qty,
                "damaged_qty": line.damaged_qty,
                "missing_qty": line.missing_qty,
            }
        )
    return {
        "id": row.id,
        "reservation_number": row.reservation_number,
        "festival_id": row.festival_id,
        "status": row.status,
        "starts_at": row.starts_at,
        "ends_at": row.ends_at,
        "prep_hours": row.prep_hours,
        "return_hours": row.return_hours,
        "cleaning_hours": row.cleaning_hours,
        "location": row.location,
        "notes": row.notes,
        "lines": lines,
    }


def _recalculate(db: Session, quote: FestivalQuote) -> None:
    items = list(db.scalars(select(FestivalQuoteItem).where(FestivalQuoteItem.quote_id == quote.id)).all())
    net = Decimal("0.00")
    vat = Decimal("0.00")
    gross = Decimal("0.00")
    for item in items:
        discount, line_net, line_vat, line_gross = line_amounts(
            as_decimal(item.quantity),
            as_decimal(item.unit_price),
            as_decimal(item.discount_percent),
            as_decimal(item.vat_rate),
        )
        item.line_discount = discount
        item.line_net = line_net
        item.line_vat = line_vat
        item.line_gross = line_gross
        net += line_net
        vat += line_vat
        gross += line_gross
    quote.net_total = money(net)
    quote.vat_total = money(vat)
    quote.gross_total = money(gross)


def _add_items(db: Session, quote: FestivalQuote, items: list[dict]) -> None:
    for index, item in enumerate(items, start=1):
        db.add(
            FestivalQuoteItem(
                quote_id=quote.id,
                position=index,
                kind=item.get("kind") or "material",
                description=item["description"],
                quantity=item["quantity"],
                unit=item.get("unit") or "Stück",
                unit_price=item["unit_price"],
                discount_percent=item.get("discount_percent") or Decimal("0"),
                vat_rate=item.get("vat_rate") if item.get("vat_rate") is not None else quote.vat_rate,
                line_discount=Decimal("0"),
                line_net=Decimal("0"),
                line_vat=Decimal("0"),
                line_gross=Decimal("0"),
                material_id=item.get("material_id"),
                product_id=item.get("product_id"),
            )
        )
    db.flush()
    _recalculate(db, quote)


def create_quote(db: Session, data: dict, *, is_demo: bool = False, demo_key: str | None = None) -> FestivalQuote:
    if demo_key:
        existing = db.scalar(select(FestivalQuote).where(FestivalQuote.demo_key == demo_key))
        if existing is not None:
            return existing
    event = _require_festival(db, data["festival_id"])
    quote = FestivalQuote(
        quote_number=next_number(db, "offerte", "OFF"),
        version=1,
        festival_id=event.id,
        contact_name=data.get("contact_name") or event.contact_name,
        quote_on=data.get("quote_on") or utcnow(),
        valid_until=data.get("valid_until"),
        status="entwurf",
        currency="CHF",
        vat_rate=data.get("vat_rate") if data.get("vat_rate") is not None else Decimal("0.00"),
        notes=data.get("notes"),
        is_demo=is_demo,
        demo_key=demo_key,
    )
    db.add(quote)
    db.flush()
    _add_items(db, quote, data.get("items") or [])
    if event.request_status == "neue_anfrage":
        event.request_status = "offerte_vorbereitung"
    refresh_festival(db, event.id)
    return quote


def replace_quote_items(db: Session, quote_id: UUID, items: list[dict]) -> FestivalQuote:
    quote = db.get(FestivalQuote, quote_id)
    if quote is None:
        raise FestivalError("Die Offerte wurde nicht gefunden.", 404)
    if quote.status not in {"entwurf", "in_pruefung"}:
        raise FestivalError("Eine versendete Offerte wird als neue Version geändert.", 409)
    for row in db.scalars(select(FestivalQuoteItem).where(FestivalQuoteItem.quote_id == quote.id)).all():
        db.delete(row)
    db.flush()
    _add_items(db, quote, items)
    quote.updated_at = utcnow()
    refresh_festival(db, quote.festival_id)
    return quote


def set_quote_status(db: Session, quote_id: UUID, status: str) -> FestivalQuote:
    quote = db.get(FestivalQuote, quote_id)
    if quote is None:
        raise FestivalError("Die Offerte wurde nicht gefunden.", 404)
    if status == "angenommen":
        raise FestivalError("Eine Offerte wird über die Annahme bestätigt.", 422)
    if status not in {"entwurf", "in_pruefung", "versendet", "abgelehnt", "abgelaufen"}:
        raise FestivalError("Der Offertenstatus ist ungültig.", 422)
    quote.status = status
    if status == "versendet":
        quote.sent_at = utcnow()
        event = _require_festival(db, quote.festival_id)
        if event.request_status in {"neue_anfrage", "in_pruefung", "offerte_vorbereitung"}:
            event.request_status = "offerte_versendet"
    quote.updated_at = utcnow()
    refresh_festival(db, quote.festival_id)
    return quote


def duplicate_quote(db: Session, quote_id: UUID) -> FestivalQuote:
    source = db.get(FestivalQuote, quote_id)
    if source is None:
        raise FestivalError("Die Offerte wurde nicht gefunden.", 404)
    items = list(db.scalars(select(FestivalQuoteItem).where(FestivalQuoteItem.quote_id == source.id)).all())
    return create_quote(
        db,
        {
            "festival_id": source.festival_id,
            "contact_name": source.contact_name,
            "valid_until": source.valid_until,
            "vat_rate": source.vat_rate,
            "notes": source.notes,
            "items": [_item_payload(item) for item in items],
        },
    )


def new_quote_version(db: Session, quote_id: UUID) -> FestivalQuote:
    source = db.get(FestivalQuote, quote_id)
    if source is None:
        raise FestivalError("Die Offerte wurde nicht gefunden.", 404)
    items = list(db.scalars(select(FestivalQuoteItem).where(FestivalQuoteItem.quote_id == source.id)).all())
    versions = db.scalars(select(FestivalQuote.version).where(FestivalQuote.quote_number == source.quote_number)).all()
    version = max([*versions, source.version])
    quote = FestivalQuote(
        quote_number=source.quote_number,
        version=version + 1,
        festival_id=source.festival_id,
        previous_id=source.id,
        contact_name=source.contact_name,
        quote_on=utcnow(),
        valid_until=source.valid_until,
        status="entwurf",
        currency="CHF",
        vat_rate=source.vat_rate,
        notes=source.notes,
        is_demo=source.is_demo,
    )
    db.add(quote)
    db.flush()
    _add_items(db, quote, [_item_payload(item) for item in items])
    refresh_festival(db, quote.festival_id)
    return quote


def accept_quote(db: Session, quote_id: UUID) -> FestivalQuote:
    quote = db.get(FestivalQuote, quote_id)
    if quote is None:
        raise FestivalError("Die Offerte wurde nicht gefunden.", 404)
    if quote.status not in {"entwurf", "in_pruefung", "versendet"}:
        raise FestivalError("Diese Offerte kann nicht angenommen werden.", 409)
    if not db.scalar(select(FestivalQuoteItem.id).where(FestivalQuoteItem.quote_id == quote.id)):
        raise FestivalError("Die Offerte hat keine Positionen.", 422)
    quote.status = "angenommen"
    quote.accepted_at = utcnow()
    for other in db.scalars(
        select(FestivalQuote).where(
            FestivalQuote.festival_id == quote.festival_id,
            FestivalQuote.id != quote.id,
            FestivalQuote.status.in_(("entwurf", "in_pruefung", "versendet")),
        )
    ).all():
        other.status = "abgelaufen"
    event = _require_festival(db, quote.festival_id)
    event.quote_status = "angenommen"
    if event.request_status != "storniert":
        event.request_status = "bestaetigt"
    _log(db, event, "quote_status", "angenommen", quote.quote_number, "Offerte angenommen", None)
    db.flush()
    from app.services.automation import publish_event

    publish_event(
        db,
        "festival_quote_accepted",
        dedupe_key=f"quote-accepted:{quote.id}",
        context={
            "owner": event.account_owner,
            "partner_id": event.distributor_partner_id or event.organizer_partner_id,
            "contact_id": event.contact_id,
            "event_id": event.id,
            "href": f"/festmanagement/{event.id}",
            "subject_title": quote.quote_number,
        },
    )
    refresh_festival(db, event.id)
    return quote


def _item_payload(item: FestivalQuoteItem) -> dict:
    return {
        "kind": item.kind,
        "description": item.description,
        "quantity": item.quantity,
        "unit": item.unit,
        "unit_price": item.unit_price,
        "discount_percent": item.discount_percent,
        "vat_rate": item.vat_rate,
        "material_id": item.material_id,
        "product_id": item.product_id,
    }


def quote_public(db: Session, quote: FestivalQuote) -> dict[str, object]:
    items = []
    for item in db.scalars(
        select(FestivalQuoteItem).where(FestivalQuoteItem.quote_id == quote.id).order_by(FestivalQuoteItem.position)
    ).all():
        items.append(
            {
                "id": item.id,
                "position": item.position,
                "kind": item.kind,
                "description": item.description,
                "quantity": item.quantity,
                "unit": item.unit,
                "unit_price": item.unit_price,
                "discount_percent": item.discount_percent,
                "vat_rate": item.vat_rate,
                "line_net": item.line_net,
                "line_vat": item.line_vat,
                "line_gross": item.line_gross,
                "material_id": item.material_id,
                "product_id": item.product_id,
            }
        )
    return {
        "id": quote.id,
        "quote_number": quote.quote_number,
        "version": quote.version,
        "festival_id": quote.festival_id,
        "previous_id": quote.previous_id,
        "contact_name": quote.contact_name,
        "quote_on": quote.quote_on,
        "valid_until": quote.valid_until,
        "sent_at": quote.sent_at,
        "status": quote.status,
        "currency": quote.currency,
        "vat_rate": quote.vat_rate,
        "notes": quote.notes,
        "net_total": quote.net_total,
        "vat_total": quote.vat_total,
        "gross_total": quote.gross_total,
        "accepted_at": quote.accepted_at,
        "is_demo": quote.is_demo,
        "items": items,
    }


def create_delivery(db: Session, data: dict, *, is_demo: bool = False, demo_key: str | None = None) -> FestivalDelivery:
    if demo_key:
        existing = db.scalar(select(FestivalDelivery).where(FestivalDelivery.demo_key == demo_key))
        if existing is not None:
            return existing
    _require_festival(db, data["festival_id"])
    row = FestivalDelivery(
        festival_id=data["festival_id"],
        address=data["address"],
        deliver_at=data.get("deliver_at"),
        deliver_window=data.get("deliver_window"),
        pickup_at=data.get("pickup_at"),
        pickup_window=data.get("pickup_window"),
        status=data.get("status") or "geplant",
        account_owner=data.get("account_owner"),
        notes=data.get("notes"),
        is_demo=is_demo,
        demo_key=demo_key,
    )
    db.add(row)
    db.flush()
    refresh_festival(db, row.festival_id)
    return row


def update_delivery(db: Session, delivery_id: UUID, data: dict) -> FestivalDelivery:
    row = db.get(FestivalDelivery, delivery_id)
    if row is None:
        raise FestivalError("Der Transport wurde nicht gefunden.", 404)
    for field in ("address", "deliver_at", "deliver_window", "pickup_at", "pickup_window", "status", "account_owner", "notes"):
        if field in data and data[field] is not None:
            setattr(row, field, data[field])
    row.updated_at = utcnow()
    db.flush()
    refresh_festival(db, row.festival_id)
    return row


def delivery_public(row: FestivalDelivery) -> dict[str, object]:
    return {
        "id": row.id,
        "festival_id": row.festival_id,
        "address": row.address,
        "deliver_at": row.deliver_at,
        "deliver_window": row.deliver_window,
        "pickup_at": row.pickup_at,
        "pickup_window": row.pickup_window,
        "status": row.status,
        "account_owner": row.account_owner,
        "notes": row.notes,
    }


def create_assignment(db: Session, data: dict, *, is_demo: bool = False, demo_key: str | None = None) -> FestivalAssignment:
    if demo_key:
        existing = db.scalar(select(FestivalAssignment).where(FestivalAssignment.demo_key == demo_key))
        if existing is not None:
            return existing
    _require_festival(db, data["festival_id"])
    if data["ends_at"] <= data["starts_at"]:
        raise FestivalError("Das Ende muss nach dem Beginn liegen.", 422)
    _assert_assignment_free(db, data["person_name"], data["starts_at"], data["ends_at"], None)
    row = FestivalAssignment(
        festival_id=data["festival_id"],
        person_name=data["person_name"].strip(),
        user_id=data.get("user_id"),
        kind=data["kind"],
        task=data["task"],
        starts_at=data["starts_at"],
        ends_at=data["ends_at"],
        status=data.get("status") or "geplant",
        notes=data.get("notes"),
        is_demo=is_demo,
        demo_key=demo_key,
    )
    db.add(row)
    db.flush()
    return row


def update_assignment(db: Session, assignment_id: UUID, data: dict) -> FestivalAssignment:
    row = db.get(FestivalAssignment, assignment_id)
    if row is None:
        raise FestivalError("Der Einsatz wurde nicht gefunden.", 404)
    person = data.get("person_name", row.person_name)
    start = data.get("starts_at", row.starts_at)
    end = data.get("ends_at", row.ends_at)
    status = data.get("status", row.status)
    if end <= start:
        raise FestivalError("Das Ende muss nach dem Beginn liegen.", 422)
    if status not in {"abgebrochen", "erledigt"}:
        _assert_assignment_free(db, person, start, end, row.id)
    for field in ("person_name", "user_id", "kind", "task", "starts_at", "ends_at", "status", "notes"):
        if field in data and data[field] is not None:
            setattr(row, field, data[field].strip() if field == "person_name" and isinstance(data[field], str) else data[field])
    row.updated_at = utcnow()
    db.flush()
    return row


def _assert_assignment_free(db: Session, person: str, start: datetime, end: datetime, ignore_id: UUID | None) -> None:
    rows = db.scalars(
        select(FestivalAssignment).where(
            FestivalAssignment.person_name.ilike(person.strip()),
            FestivalAssignment.status.notin_(("abgebrochen", "erledigt")),
        )
    ).all()
    for row in rows:
        if ignore_id is not None and row.id == ignore_id:
            continue
        if row.starts_at < end and start < row.ends_at:
            raise FestivalError(f"{person.strip()} ist in diesem Zeitraum bereits eingeteilt.", 409)


def assignment_public(row: FestivalAssignment) -> dict[str, object]:
    return {
        "id": row.id,
        "festival_id": row.festival_id,
        "person_name": row.person_name,
        "user_id": row.user_id,
        "kind": row.kind,
        "task": row.task,
        "starts_at": row.starts_at,
        "ends_at": row.ends_at,
        "status": row.status,
        "notes": row.notes,
    }


def link_ticket(db: Session, festival_id: UUID, ticket_id: UUID) -> ServiceTicket:
    _require_festival(db, festival_id)
    ticket = db.get(ServiceTicket, ticket_id)
    if ticket is None:
        raise FestivalError("Das Ticket wurde nicht gefunden.", 404)
    ticket.event_id = festival_id
    db.flush()
    return ticket


def add_note(db: Session, festival_id: UUID, title: str, description: str, activity_type: str = "gespraechsnotiz") -> Activity:
    from app.schemas.activity import ActivityWrite
    from app.services.crm import insert_activity

    event = _require_festival(db, festival_id)
    partner_id = event.distributor_partner_id or event.organizer_partner_id
    if partner_id is None and event.contact_id is None:
        raise FestivalError("Die Notiz braucht einen zugeordneten Partner oder Kontakt.", 422)
    activity = insert_activity(
        db,
        ActivityWrite(
            activity_type=activity_type,
            title=title,
            description=description,
            occurred_at=utcnow(),
            account_owner=event.account_owner,
            partner_id=partner_id,
            contact_id=event.contact_id,
        ),
    )
    activity.event_id = event.id
    db.flush()
    return activity


def dashboard(db: Session, *, start: datetime | None = None, end: datetime | None = None) -> dict[str, object]:
    now = utcnow()
    events = list(db.scalars(select(Festival).where(Festival.archived_at.is_(None))).all())
    if start is not None:
        events = [row for row in events if row.ends_at >= start]
    if end is not None:
        events = [row for row in events if row.starts_at <= end]
    reservations = list(db.scalars(select(MaterialReservation)).all())
    materials = list(db.scalars(select(FestivalMaterial).where(FestivalMaterial.is_active.is_(True))).all())
    deliveries = list(db.scalars(select(FestivalDelivery)).all())
    assignments = list(db.scalars(select(FestivalAssignment)).all())
    quotes = list(db.scalars(select(FestivalQuote)).all())
    months: dict[str, int] = {}
    for row in events:
        label = row.starts_at.astimezone(ZURICH).strftime("%m.%Y")
        months[label] = months.get(label, 0) + 1
    utilization = []
    horizon_end = now + timedelta(days=30)
    from app.services.festival_stock import availability, usable_quantity

    for material in materials:
        info = availability(db, material, now, horizon_end, quantity=1)
        usable = usable_quantity(material) if material.tracking == "menge" else int(info["usable"])
        held = int(info["held"])
        ratio = 0 if usable <= 0 else round(held / usable * 100)
        utilization.append({"material": material.name, "usable": usable, "held": held, "percent": ratio})
    overdue = [
        row
        for row in reservations
        if row.status in {"ausgegeben", "teilweise_zurueckgegeben"} and row.ends_at < now
    ]
    return {
        "planned": sum(1 for row in events if row.event_status in {"anfrage", "geplant", "bestaetigt", "laufend"}),
        "confirmed": sum(1 for row in events if row.event_status == "bestaetigt"),
        "by_month": [{"label": key, "count": months[key]} for key in sorted(months)],
        "open_requests": sum(1 for row in events if row.request_status in OPEN_REQUESTS),
        "open_quotes": sum(1 for row in quotes if row.status in {"entwurf", "in_pruefung", "versendet"}),
        "reservations": sum(1 for row in reservations if row.status != "storniert"),
        "utilization": utilization,
        "shortages": sum(1 for row in events if row.material_status in {"konflikt", "teilweise"}),
        "overdue_returns": len(overdue),
        "damaged": sum(row.quantity_defective for row in materials),
        "missing": sum(row.quantity_missing for row in materials),
        "open_transports": sum(1 for row in deliveries if row.status != "abgeschlossen"),
        "open_assignments": sum(1 for row in assignments if row.status in {"geplant", "bestaetigt"}),
        "erp_notice": "Keine externe Lageranbindung. Bestände sind lokale CRM-Daten und keine Live-Daten eines ERP.",
    }


def render_pdf(title: str, lines: list[str]) -> bytes:
    escaped = [line.encode("latin-1", errors="replace").decode("latin-1") for line in [title, *lines]]

    def esc(value: str) -> str:
        return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

    commands = ["BT", "/F1 11 Tf", "48 800 Td", "14 TL"]
    for index, line in enumerate(escaped):
        if index == 34:
            break
        commands.append(f"({esc(line[:100])}) Tj")
        commands.append("T*")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Count 1 /Kids [3 0 R] >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii")
    )
    return bytes(output)


def quote_pdf(db: Session, quote_id: UUID) -> tuple[str, bytes]:
    quote = db.get(FestivalQuote, quote_id)
    if quote is None:
        raise FestivalError("Die Offerte wurde nicht gefunden.", 404)
    event = _require_festival(db, quote.festival_id)
    public = quote_public(db, quote)
    lines = [
        "Fiktive CRM-Offerte. Keine Preisliste des Liechtensteiner Brauhauses.",
        f"{event.event_number} {event.name}",
        f"Veranstalter: {event.organizer_name}",
        f"Kontakt: {quote.contact_name or '-'}",
        f"Status: {quote.status}  Version {quote.version}",
        f"Netto {public['net_total']} {quote.currency}",
        f"MWST {public['vat_total']} {quote.currency}",
        f"Total {public['gross_total']} {quote.currency}",
    ]
    for item in public["items"]:
        lines.append(f"{item['position']}. {item['description']}  {item['quantity']} {item['unit']}  {item['line_gross']} {quote.currency}")
    return f"{quote.quote_number}-v{quote.version}.pdf", render_pdf(f"Offerte {quote.quote_number}", lines)


def delivery_pdf(db: Session, delivery_id: UUID) -> tuple[str, bytes]:
    row = db.get(FestivalDelivery, delivery_id)
    if row is None:
        raise FestivalError("Der Transport wurde nicht gefunden.", 404)
    event = _require_festival(db, row.festival_id)
    lines = [
        "Lieferschein aus dem CRM. Ein erreichtes Datum gilt nicht als Zustellung.",
        f"{event.event_number} {event.name}",
        f"Adresse: {row.address}",
        f"Status: {row.status}",
        f"Lieferung: {row.deliver_at or '-'} {row.deliver_window or ''}",
        f"Abholung: {row.pickup_at or '-'} {row.pickup_window or ''}",
        "Positionen:",
    ]
    issued = False
    for reservation in db.scalars(select(MaterialReservation).where(MaterialReservation.festival_id == event.id)).all():
        for line in db.scalars(select(MaterialReservationLine).where(MaterialReservationLine.reservation_id == reservation.id)).all():
            material = db.get(FestivalMaterial, line.material_id)
            name = material.name if material else "Material"
            if line.issued_qty:
                issued = True
                lines.append(f"Ausgegeben: {line.issued_qty} {name}")
            else:
                lines.append(f"Geplant, nicht ausgegeben: {line.quantity} {name}")
    if not issued:
        lines.append("Es wurde noch kein Material als ausgegeben bestätigt.")
    return f"lieferschein-{event.event_number}.pdf", render_pdf(f"Lieferschein {event.event_number}", lines)


def _context(event: Festival, dedupe: str, title: str) -> tuple[str, dict]:
    return dedupe, {
        "owner": event.account_owner,
        "partner_id": event.distributor_partner_id or event.organizer_partner_id,
        "contact_id": event.contact_id,
        "event_id": event.id,
        "href": f"/festmanagement/{event.id}",
        "subject_title": title,
    }


def festival_time_subjects(db: Session, trigger: str, days: int, now: datetime) -> list[tuple[str, dict]]:
    subjects: list[tuple[str, dict]] = []
    if trigger == "festival_quote_waiting":
        limit = now - timedelta(days=days)
        for quote in db.scalars(select(FestivalQuote).where(FestivalQuote.status == "versendet", FestivalQuote.sent_at.is_not(None))).all():
            if quote.sent_at is not None and quote.sent_at <= limit:
                event = db.get(Festival, quote.festival_id)
                if event is not None and event.archived_at is None:
                    subjects.append(_context(event, f"quote-wait:{quote.id}", quote.quote_number))
    elif trigger == "festival_starts_soon":
        horizon = now + timedelta(days=days)
        for event in db.scalars(
            select(Festival).where(
                Festival.archived_at.is_(None),
                Festival.event_status.in_(("geplant", "bestaetigt", "anfrage")),
                Festival.starts_at > now,
                Festival.starts_at <= horizon,
            )
        ).all():
            subjects.append(_context(event, f"festival-soon:{event.id}:{event.starts_at.date().isoformat()}", event.name))
    elif trigger == "festival_delivery_due":
        horizon = now + timedelta(days=days)
        for row in db.scalars(
            select(FestivalDelivery).where(
                FestivalDelivery.status.in_(("geplant", "bereit")),
                FestivalDelivery.deliver_at.is_not(None),
                FestivalDelivery.deliver_at > now,
                FestivalDelivery.deliver_at <= horizon,
            )
        ).all():
            event = db.get(Festival, row.festival_id)
            if event is not None:
                subjects.append(_context(event, f"delivery-due:{row.id}", event.name))
    elif trigger == "festival_ended":
        limit = now - timedelta(days=days)
        for event in db.scalars(
            select(Festival).where(
                Festival.archived_at.is_(None),
                Festival.event_status.notin_(("abgeschlossen", "archiviert", "storniert")),
                Festival.ends_at <= limit,
            )
        ).all():
            open_material = db.scalar(
                select(MaterialReservation.id).where(
                    MaterialReservation.festival_id == event.id,
                    MaterialReservation.status.in_(("bestaetigt", "ausgegeben", "teilweise_zurueckgegeben")),
                )
            )
            if open_material is not None:
                subjects.append(_context(event, f"festival-ended:{event.id}", f"Rücknahme {event.name}"))
    elif trigger == "festival_return_overdue":
        limit = now - timedelta(days=days)
        for event in db.scalars(select(Festival).where(Festival.ends_at <= limit, Festival.archived_at.is_(None))).all():
            open_return = db.scalar(
                select(MaterialReservation.id).where(
                    MaterialReservation.festival_id == event.id,
                    MaterialReservation.status.in_(("ausgegeben", "teilweise_zurueckgegeben")),
                )
            )
            if open_return is not None:
                subjects.append(_context(event, f"return-overdue:{event.id}", f"Rücknahme überfällig {event.name}"))
    return subjects
