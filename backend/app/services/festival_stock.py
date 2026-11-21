"""Material stock, availability and reservations.

Owned quantity changes only through receipts, damage, loss, repair and corrections.
A reservation does not reduce the owned quantity. Availability for a period is calculated
from usable stock minus overlapping confirmed holds, including preparation, return and cleaning time.
Issued material stays unavailable until a confirmed return books the good quantity back.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.access_context import current_actor
from app.festival_catalog import HOLDING_STATUSES
from app.models.festival import (
    Festival,
    FestivalMaterial,
    MaterialAsset,
    MaterialCategory,
    MaterialIssue,
    MaterialMovement,
    MaterialReservation,
    MaterialReservationLine,
    MaterialReturn,
    NumberRange,
)
from app.models.partner import utcnow

FAR_FUTURE = datetime(2099, 1, 1, tzinfo=timezone.utc)


class FestivalError(Exception):
    def __init__(self, message: str, status_code: int = 422, *, persist: bool = False) -> None:
        self.message = message
        self.status_code = status_code
        self.persist = persist


def actor_label() -> str | None:
    actor = current_actor.get()
    return actor.display_name if actor else None


def require_permission(*codes: str) -> None:
    actor = current_actor.get()
    if actor is None or not any(code in actor.permissions for code in codes):
        raise FestivalError("Keine Berechtigung für diese Aktion.", 403)


def next_number(db: Session, key: str, prefix: str) -> str:
    from zoneinfo import ZoneInfo

    year = datetime.now(ZoneInfo("Europe/Zurich")).year
    name = f"{key}-{year}"
    row = db.scalar(select(NumberRange).where(NumberRange.name == name).with_for_update())
    if row is None:
        nested = db.begin_nested()
        try:
            row = NumberRange(name=name, last_value=0)
            db.add(row)
            db.flush()
            nested.commit()
        except IntegrityError:
            nested.rollback()
            row = db.scalar(select(NumberRange).where(NumberRange.name == name).with_for_update())
    if row is None:
        raise FestivalError("Die Nummer konnte nicht vergeben werden.", 409)
    row.last_value += 1
    db.flush()
    return f"{prefix}-{year}-{row.last_value:04d}"


def record_movement(
    db: Session,
    material: FestivalMaterial,
    movement_type: str,
    quantity: int,
    *,
    festival_id: UUID | None = None,
    reservation_id: UUID | None = None,
    asset_id: UUID | None = None,
    note: str | None = None,
    when: datetime | None = None,
) -> MaterialMovement:
    row = MaterialMovement(
        material_id=material.id,
        asset_id=asset_id,
        festival_id=festival_id,
        reservation_id=reservation_id,
        movement_type=movement_type,
        quantity=quantity,
        occurred_at=when or utcnow(),
        actor_label=actor_label(),
        note=note,
    )
    db.add(row)
    db.flush()
    return row


def require_material(db: Session, material_id: UUID) -> FestivalMaterial:
    material = db.get(FestivalMaterial, material_id)
    if material is None:
        raise FestivalError("Das Material wurde nicht gefunden.", 404)
    return material


def require_reservation(db: Session, reservation_id: UUID) -> MaterialReservation:
    row = db.get(MaterialReservation, reservation_id)
    if row is None:
        raise FestivalError("Die Reservation wurde nicht gefunden.", 404)
    return row


def lock_reservation(db: Session, reservation_id: UUID) -> MaterialReservation:
    row = db.scalar(select(MaterialReservation).where(MaterialReservation.id == reservation_id).with_for_update())
    if row is None:
        raise FestivalError("Die Reservation wurde nicht gefunden.", 404)
    return row


def lock_materials(db: Session, material_ids: list[UUID]) -> None:
    if not material_ids:
        return
    db.execute(
        select(FestivalMaterial)
        .where(FestivalMaterial.id.in_(sorted(set(material_ids))))
        .order_by(FestivalMaterial.id)
        .with_for_update()
    )
    db.execute(
        select(MaterialAsset)
        .where(MaterialAsset.material_id.in_(sorted(set(material_ids))))
        .order_by(MaterialAsset.id)
        .with_for_update()
    )


def reservation_lines(db: Session, reservation_id: UUID) -> list[MaterialReservationLine]:
    return list(
        db.scalars(
            select(MaterialReservationLine).where(MaterialReservationLine.reservation_id == reservation_id)
        ).all()
    )


def usable_quantity(material: FestivalMaterial) -> int:
    return material.quantity_total - material.quantity_defective - material.quantity_locked - material.quantity_missing


def _still_out(lines: list[MaterialReservationLine]) -> bool:
    return any(line.issued_qty - line.returned_qty - line.damaged_qty - line.missing_qty > 0 for line in lines)


def blocked_window(reservation: MaterialReservation, lines: list[MaterialReservationLine]) -> tuple[datetime, datetime]:
    start = reservation.starts_at - timedelta(hours=reservation.prep_hours)
    if reservation.status in {"ausgegeben", "teilweise_zurueckgegeben"} and _still_out(lines):
        end = FAR_FUTURE
    else:
        end = reservation.ends_at + timedelta(hours=reservation.return_hours + reservation.cleaning_hours)
    return start, end


def held_quantity(line: MaterialReservationLine, reservation: MaterialReservation) -> int:
    if reservation.status == "bestaetigt":
        return line.quantity
    if reservation.status in {"ausgegeben", "teilweise_zurueckgegeben"}:
        outstanding = line.issued_qty - line.returned_qty - line.damaged_qty - line.missing_qty
        return max(outstanding, 0)
    return 0


def _overlaps(left: tuple[datetime, datetime], right: tuple[datetime, datetime]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def availability(
    db: Session,
    material: FestivalMaterial,
    start: datetime,
    end: datetime,
    *,
    quantity: int = 1,
    location: str | None = None,
    ignore_reservation_id: UUID | None = None,
    prep_hours: int = 0,
    return_hours: int = 0,
    cleaning_hours: int = 0,
) -> dict[str, object]:
    if end <= start:
        raise FestivalError("Das Ende muss nach dem Beginn liegen.", 422)
    window = (start - timedelta(hours=prep_hours), end + timedelta(hours=return_hours + cleaning_hours))
    location_mismatch = bool(location and material.location and location.casefold() != material.location.casefold())
    conflicts: list[str] = []
    held = 0
    held_assets: set[UUID] = set()
    rows = db.execute(
        select(MaterialReservationLine, MaterialReservation)
        .join(MaterialReservation, MaterialReservation.id == MaterialReservationLine.reservation_id)
        .where(
            MaterialReservationLine.material_id == material.id,
            MaterialReservation.status.in_(HOLDING_STATUSES),
        )
    ).all()
    grouped: dict[UUID, list[MaterialReservationLine]] = {}
    reservations: dict[UUID, MaterialReservation] = {}
    for line, reservation in rows:
        grouped.setdefault(reservation.id, []).append(line)
        reservations[reservation.id] = reservation
    for reservation_id, lines in grouped.items():
        reservation = reservations[reservation_id]
        if ignore_reservation_id is not None and reservation_id == ignore_reservation_id:
            continue
        if not _overlaps(window, blocked_window(reservation, lines)):
            continue
        amount = sum(held_quantity(line, reservation) for line in lines)
        held += amount
        for line in lines:
            if line.asset_id is not None and held_quantity(line, reservation) > 0:
                held_assets.add(line.asset_id)
        if amount:
            conflicts.append(f"{reservation.reservation_number}: {amount} belegt")
    if material.tracking == "einzel":
        assets = list(
            db.scalars(
                select(MaterialAsset).where(
                    MaterialAsset.material_id == material.id,
                    MaterialAsset.is_active.is_(True),
                    MaterialAsset.condition == "einsatzbereit",
                )
            ).all()
        )
        if location:
            assets = [asset for asset in assets if (asset.location or material.location or "").casefold() == location.casefold()]
        free = [asset for asset in assets if asset.id not in held_assets]
        usable = len(assets)
        available = 0 if location_mismatch else len(free)
    else:
        usable = max(usable_quantity(material), 0)
        available = 0 if location_mismatch else max(usable - held, 0)
    if location_mismatch:
        conflicts.append(f"Der Bestand liegt in {material.location}, nicht in {location}.")
    return {
        "material_id": material.id,
        "material_name": material.name,
        "usable": usable,
        "held": held,
        "available": available,
        "requested": quantity,
        "enough": available >= quantity and not location_mismatch,
        "conflicts": conflicts,
    }


def create_category(db: Session, code: str, name: str, *, example: bool = True, sort_order: int = 0) -> MaterialCategory:
    existing = db.scalar(select(MaterialCategory).where(MaterialCategory.code == code))
    if existing is not None:
        existing.name = name
        return existing
    row = MaterialCategory(code=code, name=name, sort_order=sort_order, is_example=example)
    db.add(row)
    db.flush()
    return row


def create_material(db: Session, data: dict, *, is_demo: bool = False, demo_key: str | None = None) -> FestivalMaterial:
    if demo_key:
        existing = db.scalar(select(FestivalMaterial).where(FestivalMaterial.demo_key == demo_key))
        if existing is not None:
            return existing
    material = FestivalMaterial(
        material_number=next_number(db, "material", "MAT"),
        name=data["name"],
        category_id=data.get("category_id"),
        description=data.get("description"),
        tracking=data.get("tracking") or "menge",
        quantity_total=0,
        location=data.get("location"),
        condition="einsatzbereit",
        unit=data.get("unit") or "Stück",
        rental_price=data.get("rental_price"),
        deposit_amount=data.get("deposit_amount"),
        prep_hours=int(data.get("prep_hours") or 0),
        return_hours=int(data.get("return_hours") or 0),
        cleaning_hours=int(data.get("cleaning_hours") or 0),
        notes=data.get("notes"),
        is_demo=is_demo,
        demo_key=demo_key,
    )
    db.add(material)
    db.flush()
    return material


def update_material(db: Session, material_id: UUID, data: dict) -> FestivalMaterial:
    material = require_material(db, material_id)
    for field in ("name", "category_id", "description", "location", "unit", "rental_price", "deposit_amount", "notes", "is_active"):
        if field in data:
            setattr(material, field, data[field])
    for field in ("prep_hours", "return_hours", "cleaning_hours"):
        if field in data and data[field] is not None:
            setattr(material, field, int(data[field]))
    material.updated_at = utcnow()
    db.flush()
    return material


def post_stock(db: Session, material_id: UUID, data: dict) -> FestivalMaterial:
    material = require_material(db, material_id)
    kind = data["movement_type"]
    quantity = int(data.get("quantity") or 0)
    note = (data.get("note") or "").strip()
    if material.tracking == "einzel" and kind == "wareneingang":
        raise FestivalError("Einzelstücke werden über eine Inventarnummer eingebucht.", 422)
    if kind == "bestandskorrektur":
        require_permission("materials.correct")
        if not note:
            raise FestivalError("Eine Bestandskorrektur braucht einen Grund.", 422)
        bucket = data.get("bucket") or "total"
        if bucket not in {"total", "locked", "defective", "missing"}:
            raise FestivalError("Der Bestandstopf ist ungültig.", 422)
        _adjust_bucket(material, bucket, quantity)
    elif kind == "wareneingang":
        require_permission("materials.write", "materials.correct")
        if quantity < 1:
            raise FestivalError("Der Wareneingang braucht eine Menge.", 422)
        material.quantity_total += quantity
    elif kind == "reparatur":
        require_permission("materials.write", "materials.correct")
        if quantity < 1:
            raise FestivalError("Die Reparatur braucht eine Menge.", 422)
        if quantity > material.quantity_defective:
            raise FestivalError("Es ist nicht so viel defektes Material vorhanden.", 409)
        material.quantity_defective -= quantity
        if material.quantity_defective == 0 and material.condition == "defekt":
            material.condition = "einsatzbereit"
    elif kind == "standortwechsel":
        require_permission("materials.write", "materials.correct")
        location = (data.get("location") or "").strip()
        if not location:
            raise FestivalError("Der neue Standort ist erforderlich.", 422)
        material.location = location
        quantity = 0
    else:
        raise FestivalError("Diese Bewegung läuft über Reservation, Ausgabe oder Rücknahme.", 422)
    _guard_quantities(material)
    record_movement(db, material, kind, quantity, note=note or None)
    material.updated_at = utcnow()
    db.flush()
    return material


def _adjust_bucket(material: FestivalMaterial, bucket: str, quantity: int) -> None:
    if bucket == "total":
        material.quantity_total += quantity
    elif bucket == "locked":
        material.quantity_locked += quantity
        material.condition = "gesperrt" if material.quantity_locked else material.condition
    elif bucket == "defective":
        material.quantity_defective += quantity
        material.condition = "defekt" if material.quantity_defective else "einsatzbereit"
    else:
        material.quantity_missing += quantity
    if material.quantity_locked < 0 or material.quantity_defective < 0 or material.quantity_missing < 0 or material.quantity_total < 0:
        raise FestivalError("Der Bestand darf nicht negativ werden.", 409)


def _guard_quantities(material: FestivalMaterial) -> None:
    if material.quantity_defective + material.quantity_locked + material.quantity_missing > material.quantity_total:
        raise FestivalError("Defekte, gesperrte und fehlende Mengen übersteigen den Gesamtbestand.", 409)


def add_asset(db: Session, material_id: UUID, inventory_number: str, *, location: str | None = None, demo_key: str | None = None) -> MaterialAsset:
    material = require_material(db, material_id)
    if material.tracking != "einzel":
        raise FestivalError("Nur einzeln geführtes Material erhält eine Inventarnummer.", 422)
    if demo_key:
        existing = db.scalar(select(MaterialAsset).where(MaterialAsset.demo_key == demo_key))
        if existing is not None:
            return existing
    asset = MaterialAsset(
        material_id=material.id,
        inventory_number=inventory_number.strip(),
        condition="einsatzbereit",
        location=location or material.location,
        demo_key=demo_key,
    )
    db.add(asset)
    try:
        db.flush()
    except IntegrityError:
        raise FestivalError("Diese Inventarnummer ist bereits vergeben.", 409) from None
    material.quantity_total += 1
    record_movement(db, material, "wareneingang", 1, asset_id=asset.id, note=inventory_number)
    db.flush()
    return asset


def create_reservation(db: Session, data: dict, *, is_demo: bool = False, demo_key: str | None = None) -> MaterialReservation:
    if demo_key:
        existing = db.scalar(select(MaterialReservation).where(MaterialReservation.demo_key == demo_key))
        if existing is not None:
            return existing
    festival = db.get(Festival, data["festival_id"])
    if festival is None:
        raise FestivalError("Das Fest wurde nicht gefunden.", 404)
    if festival.archived_at is not None:
        raise FestivalError("Für ein archiviertes Fest kann kein Material reserviert werden.", 409)
    status = data.get("status") or "angefragt"
    if status in HOLDING_STATUSES or status == "ausgegeben":
        raise FestivalError("Eine neue Reservation startet ungeprüft und reserviert noch nichts verbindlich.", 422)
    row = MaterialReservation(
        reservation_number=next_number(db, "reservation", "RES"),
        festival_id=festival.id,
        status=status,
        starts_at=data["starts_at"],
        ends_at=data["ends_at"],
        prep_hours=int(data.get("prep_hours") or 0),
        return_hours=int(data.get("return_hours") or 0),
        cleaning_hours=int(data.get("cleaning_hours") or 0),
        location=data.get("location"),
        notes=data.get("notes"),
        is_demo=is_demo,
        demo_key=demo_key,
    )
    if row.ends_at <= row.starts_at:
        raise FestivalError("Das Ende muss nach dem Beginn liegen.", 422)
    db.add(row)
    db.flush()
    for line in data.get("lines") or []:
        add_line(db, row.id, line)
    from app.services.festival import refresh_festival

    refresh_festival(db, festival.id)
    return row


def add_line(db: Session, reservation_id: UUID, data: dict) -> MaterialReservationLine:
    reservation = lock_reservation(db, reservation_id)
    if reservation.status in {"ausgegeben", "teilweise_zurueckgegeben", "zurueckgegeben", "storniert", "bestaetigt"}:
        raise FestivalError("Bestätigte oder abgeschlossene Positionen werden über eine Änderung mit Verfügbarkeitsprüfung angepasst.", 409)
    material = require_material(db, data["material_id"])
    asset_id = data.get("asset_id")
    quantity = int(data["quantity"])
    if quantity < 1:
        raise FestivalError("Die Menge muss mindestens 1 sein.", 422)
    if material.tracking == "einzel":
        if asset_id is None:
            raise FestivalError("Ein Einzelstück braucht eine Inventarnummer.", 422)
        quantity = 1
        asset = db.get(MaterialAsset, asset_id)
        if asset is None or asset.material_id != material.id:
            raise FestivalError("Die Inventarnummer gehört nicht zu diesem Material.", 422)
    elif asset_id is not None:
        raise FestivalError("Mengenmaterial hat keine Inventarnummer.", 422)
    line = MaterialReservationLine(
        reservation_id=reservation.id,
        material_id=material.id,
        asset_id=asset_id,
        quantity=quantity,
    )
    db.add(line)
    db.flush()
    return line


def remove_line(db: Session, reservation_id: UUID, line_id: UUID) -> None:
    reservation = lock_reservation(db, reservation_id)
    if reservation.status in HOLDING_STATUSES or reservation.status in {"zurueckgegeben", "storniert"}:
        raise FestivalError("Diese Position kann nicht mehr entfernt werden.", 409)
    line = db.get(MaterialReservationLine, line_id)
    if line is None or line.reservation_id != reservation.id:
        raise FestivalError("Die Position wurde nicht gefunden.", 404)
    db.delete(line)
    db.flush()


def check_reservation(db: Session, reservation_id: UUID) -> dict[str, object]:
    reservation = require_reservation(db, reservation_id)
    lines = reservation_lines(db, reservation.id)
    results = []
    enough = True
    for line in lines:
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
        results.append(info)
        enough = enough and bool(info["enough"])
    if reservation.status in {"entwurf", "angefragt", "in_pruefung", "teilweise_verfuegbar"}:
        reservation.status = "teilweise_verfuegbar" if not enough else "in_pruefung"
        db.flush()
        from app.services.festival import refresh_festival

        refresh_festival(db, reservation.festival_id)
    return {"enough": enough, "lines": results, "status": reservation.status}


def confirm_reservation(db: Session, reservation_id: UUID) -> MaterialReservation:
    reservation = lock_reservation(db, reservation_id)
    if reservation.status not in {"entwurf", "angefragt", "in_pruefung", "teilweise_verfuegbar"}:
        raise FestivalError("Diese Reservation ist bereits verbindlich oder abgeschlossen.", 409)
    lines = reservation_lines(db, reservation.id)
    if not lines:
        raise FestivalError("Die Reservation enthält kein Material.", 422)
    festival = db.get(Festival, reservation.festival_id)
    if festival is None or not festival.is_binding:
        raise FestivalError("Verbindlich reservieren geht erst nach dem bestätigten Festauftrag.", 409)
    lock_materials(db, [line.material_id for line in lines])
    shortages: list[str] = []
    for line in lines:
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
        if not info["enough"]:
            shortages.append(f"{material.name}: verfügbar {info['available']}, benötigt {line.quantity}")
    if shortages:
        reservation.status = "teilweise_verfuegbar"
        db.flush()
        from app.services.festival import refresh_festival

        refresh_festival(db, reservation.festival_id)
        _publish_short(db, reservation, shortages)
        raise FestivalError("Materialkonflikt. " + " ".join(shortages), 409, persist=True)
    reservation.status = "bestaetigt"
    reservation.confirmed_at = utcnow()
    for line in lines:
        material = require_material(db, line.material_id)
        record_movement(
            db,
            material,
            "reservation",
            line.quantity,
            festival_id=reservation.festival_id,
            reservation_id=reservation.id,
            asset_id=line.asset_id,
            note=reservation.reservation_number,
        )
    db.flush()
    from app.services.festival import refresh_festival

    refresh_festival(db, reservation.festival_id)
    return reservation


def cancel_reservation(db: Session, reservation_id: UUID, reason: str) -> MaterialReservation:
    reservation = lock_reservation(db, reservation_id)
    if reservation.status in {"ausgegeben", "teilweise_zurueckgegeben", "zurueckgegeben"}:
        raise FestivalError("Ausgegebenes Material kann nicht storniert werden. Zuerst die Rücknahme erfassen.", 409)
    if reservation.status == "storniert":
        return reservation
    lines = reservation_lines(db, reservation.id)
    if reservation.status == "bestaetigt":
        lock_materials(db, [line.material_id for line in lines])
        for line in lines:
            material = require_material(db, line.material_id)
            record_movement(
                db,
                material,
                "reservationsfreigabe",
                line.quantity,
                festival_id=reservation.festival_id,
                reservation_id=reservation.id,
                asset_id=line.asset_id,
                note=reason,
            )
    reservation.status = "storniert"
    reservation.notes = reason
    db.flush()
    from app.services.festival import refresh_festival

    refresh_festival(db, reservation.festival_id)
    return reservation


def replace_line(db: Session, reservation_id: UUID, line_id: UUID, material_id: UUID, quantity: int) -> MaterialReservationLine:
    reservation = lock_reservation(db, reservation_id)
    if reservation.status in {"ausgegeben", "teilweise_zurueckgegeben", "zurueckgegeben", "storniert"}:
        raise FestivalError("Ausgegebenes Material wird nicht mehr ersetzt.", 409)
    line = db.get(MaterialReservationLine, line_id)
    if line is None or line.reservation_id != reservation.id:
        raise FestivalError("Die Position wurde nicht gefunden.", 404)
    material = require_material(db, material_id)
    if material.tracking == "einzel":
        raise FestivalError("Einzelstücke werden als eigene Position ersetzt.", 422)
    if quantity < 1:
        raise FestivalError("Die Menge muss mindestens 1 sein.", 422)
    lock_materials(db, [line.material_id, material.id])
    if reservation.status == "bestaetigt":
        info = availability(
            db,
            material,
            reservation.starts_at,
            reservation.ends_at,
            quantity=quantity,
            location=reservation.location,
            ignore_reservation_id=reservation.id,
            prep_hours=reservation.prep_hours,
            return_hours=reservation.return_hours,
            cleaning_hours=reservation.cleaning_hours,
        )
        if not info["enough"]:
            raise FestivalError(
                f"Materialkonflikt. {material.name}: verfügbar {info['available']}, benötigt {quantity}.",
                409,
            )
        previous = require_material(db, line.material_id)
        record_movement(db, previous, "reservationsfreigabe", line.quantity, festival_id=reservation.festival_id, reservation_id=reservation.id, note="Ersatz")
        record_movement(db, material, "reservation", quantity, festival_id=reservation.festival_id, reservation_id=reservation.id, note="Ersatz")
    line.material_id = material.id
    line.quantity = quantity
    line.asset_id = None
    db.flush()
    return line


def issue_reservation(db: Session, reservation_id: UUID, data: dict) -> MaterialIssue:
    reservation = lock_reservation(db, reservation_id)
    if reservation.status != "bestaetigt":
        raise FestivalError("Nur eine bestätigte Reservation kann ausgegeben werden.", 409)
    if db.scalar(select(MaterialIssue.id).where(MaterialIssue.reservation_id == reservation.id)) is not None:
        raise FestivalError("Diese Reservation wurde bereits ausgegeben.", 409)
    lines = reservation_lines(db, reservation.id)
    if any(line.issued_qty > 0 for line in lines):
        raise FestivalError("Diese Reservation wurde bereits ausgegeben.", 409)
    requested = {UUID(str(item["line_id"])): int(item["quantity"]) for item in data.get("lines") or []}
    lock_materials(db, [line.material_id for line in lines])
    when = data.get("issued_at") or utcnow()
    for line in lines:
        quantity = requested.get(line.id, line.quantity)
        if quantity < 1 or quantity > line.quantity:
            raise FestivalError("Die ausgegebene Menge muss zwischen 1 und der reservierten Menge liegen.", 422)
        if quantity < line.quantity:
            record_movement(
                db,
                require_material(db, line.material_id),
                "reservationsfreigabe",
                line.quantity - quantity,
                festival_id=reservation.festival_id,
                reservation_id=reservation.id,
                asset_id=line.asset_id,
                note="Nicht ausgegebene Reserve",
            )
            line.quantity = quantity
        line.issued_qty = quantity
        record_movement(
            db,
            require_material(db, line.material_id),
            "ausgabe",
            quantity,
            festival_id=reservation.festival_id,
            reservation_id=reservation.id,
            asset_id=line.asset_id,
            note=data.get("condition_note"),
            when=when,
        )
    reservation.status = "ausgegeben"
    reservation.issued_at = when
    issue = MaterialIssue(
        reservation_id=reservation.id,
        festival_id=reservation.festival_id,
        issued_at=when,
        actor_label=actor_label(),
        condition_note=data.get("condition_note"),
        confirmed=True,
    )
    db.add(issue)
    try:
        db.flush()
    except IntegrityError:
        raise FestivalError("Diese Reservation wurde bereits ausgegeben.", 409) from None
    from app.services.festival import refresh_festival

    refresh_festival(db, reservation.festival_id)
    return issue


def return_reservation(db: Session, reservation_id: UUID, data: dict) -> MaterialReturn:
    key = (data.get("idempotency_key") or "").strip() or None
    if key:
        existing = db.scalar(select(MaterialReturn).where(MaterialReturn.idempotency_key == key))
        if existing is not None:
            return existing
    reservation = lock_reservation(db, reservation_id)
    if reservation.status not in {"ausgegeben", "teilweise_zurueckgegeben"}:
        raise FestivalError("Eine Rücknahme setzt eine vorherige Ausgabe voraus.", 409)
    lines = {line.id: line for line in reservation_lines(db, reservation.id)}
    payloads = data.get("lines") or []
    if not payloads:
        raise FestivalError("Die Rücknahme braucht mindestens eine Position.", 422)
    lock_materials(db, [line.material_id for line in lines.values()])
    when = data.get("returned_at") or utcnow()
    damaged_any = False
    for item in payloads:
        line = lines.get(UUID(str(item["line_id"])))
        if line is None:
            raise FestivalError("Eine Rücknahmeposition gehört nicht zu dieser Reservation.", 422)
        good = int(item.get("returned_qty") or 0)
        damaged = int(item.get("damaged_qty") or 0)
        missing = int(item.get("missing_qty") or 0)
        if min(good, damaged, missing) < 0:
            raise FestivalError("Mengen dürfen nicht negativ sein.", 422)
        incoming = good + damaged + missing
        if incoming < 1:
            raise FestivalError("Die Rücknahme braucht eine Menge.", 422)
        accounted = line.returned_qty + line.damaged_qty + line.missing_qty
        if accounted + incoming > line.issued_qty:
            raise FestivalError("Die Rücknahme übersteigt die ausgegebene Menge. Eine doppelte Rückbuchung wird abgelehnt.", 409)
        material = require_material(db, line.material_id)
        line.returned_qty += good
        line.damaged_qty += damaged
        line.missing_qty += missing
        if good:
            record_movement(db, material, "ruecknahme", good, festival_id=reservation.festival_id, reservation_id=reservation.id, asset_id=line.asset_id, note=data.get("notes"), when=when)
        if damaged:
            material.quantity_defective += damaged
            material.condition = "defekt"
            damaged_any = True
            if line.asset_id is not None:
                asset = db.get(MaterialAsset, line.asset_id)
                if asset is not None:
                    asset.condition = "defekt"
            record_movement(db, material, "beschaedigung", damaged, festival_id=reservation.festival_id, reservation_id=reservation.id, asset_id=line.asset_id, note=data.get("notes"), when=when)
        if missing:
            material.quantity_missing += missing
            record_movement(db, material, "verlust", missing, festival_id=reservation.festival_id, reservation_id=reservation.id, asset_id=line.asset_id, note=data.get("notes"), when=when)
        _guard_quantities(material)
    settled = all(
        line.returned_qty + line.damaged_qty + line.missing_qty == line.issued_qty for line in lines.values() if line.issued_qty
    )
    reservation.status = "zurueckgegeben" if settled else "teilweise_zurueckgegeben"
    if settled:
        reservation.returned_at = when
    row = MaterialReturn(
        reservation_id=reservation.id,
        festival_id=reservation.festival_id,
        returned_at=when,
        actor_label=actor_label(),
        notes=data.get("notes"),
        idempotency_key=key,
        stock_posted=True,
    )
    db.add(row)
    try:
        db.flush()
    except IntegrityError:
        raise FestivalError("Diese Rücknahme wurde bereits verbucht.", 409) from None
    from app.services.festival import refresh_festival

    refresh_festival(db, reservation.festival_id)
    if damaged_any:
        _publish_damaged(db, reservation, row)
    return row


def _publish_short(db: Session, reservation: MaterialReservation, shortages: list[str]) -> None:
    from app.services.automation import publish_event

    festival = db.get(Festival, reservation.festival_id)
    publish_event(
        db,
        "festival_material_short",
        dedupe_key=f"material-short:{reservation.id}",
        context={
            "owner": festival.account_owner if festival else None,
            "partner_id": festival.distributor_partner_id if festival else None,
            "event_id": reservation.festival_id,
            "href": f"/festmanagement/{reservation.festival_id}",
            "subject_title": " ".join(shortages)[:180],
        },
    )


def _publish_damaged(db: Session, reservation: MaterialReservation, row: MaterialReturn) -> None:
    from app.services.automation import publish_event

    festival = db.get(Festival, reservation.festival_id)
    publish_event(
        db,
        "festival_material_damaged",
        dedupe_key=f"material-damaged:{row.id}",
        context={
            "owner": festival.account_owner if festival else None,
            "partner_id": festival.distributor_partner_id if festival else None,
            "event_id": reservation.festival_id,
            "href": f"/festmanagement/{reservation.festival_id}",
            "subject_title": "Beschädigtes Festmaterial prüfen",
        },
    )


def material_snapshot(db: Session, material: FestivalMaterial, start: datetime, end: datetime) -> dict[str, object]:
    info = availability(db, material, start, end, quantity=1)
    category = db.get(MaterialCategory, material.category_id) if material.category_id else None
    assets = list(db.scalars(select(MaterialAsset).where(MaterialAsset.material_id == material.id)).all())
    return {
        "id": material.id,
        "material_number": material.material_number,
        "name": material.name,
        "category_name": category.name if category else None,
        "description": material.description,
        "tracking": material.tracking,
        "quantity_total": material.quantity_total,
        "quantity_defective": material.quantity_defective,
        "quantity_locked": material.quantity_locked,
        "quantity_missing": material.quantity_missing,
        "usable": usable_quantity(material) if material.tracking == "menge" else info["usable"],
        "available_now": info["available"],
        "location": material.location,
        "condition": material.condition,
        "unit": material.unit,
        "rental_price": material.rental_price,
        "deposit_amount": material.deposit_amount,
        "prep_hours": material.prep_hours,
        "return_hours": material.return_hours,
        "cleaning_hours": material.cleaning_hours,
        "notes": material.notes,
        "is_active": material.is_active,
        "erp_article_number": material.erp_article_number,
        "erp_source": material.erp_source,
        "is_demo": material.is_demo,
        "assets": [
            {"id": asset.id, "inventory_number": asset.inventory_number, "condition": asset.condition, "location": asset.location}
            for asset in assets
        ],
    }
