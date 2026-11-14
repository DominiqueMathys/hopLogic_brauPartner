"""Synchronisation between the CRM and a configured ERP connector.

Field ownership:
- ERP leads for the ERP customer number, the ERP customer status, the article
  number and the current catalogue price, unit, category and active flag.
- CRM leads for notes, activities, tasks, segments, the account owner, the
  partner type and the CRM partner status.
- Shared address and contact fields keep the CRM value when it is already
  filled and differs. Empty CRM fields take the ERP value. A difference becomes
  a conflict and is not overwritten.
- Order line prices stay as stored. A later catalogue price does not rewrite them.
- The CRM order status and the technical transfer status are separate.
  A successful transfer is not a delivery and not an invoice.
"""

from __future__ import annotations

import csv
import io
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, inspect, select
from sqlalchemy.orm import Session

from app.config import settings
from app.integrations.connector import SOURCE_EXTERN, SOURCE_LABELS, SOURCE_MOCK, build_connector, connector_registered
from app.integrations.types import ErpAmbiguousError, ErpCustomer, ErpProduct, ErpTechnicalError
from app.models.integration import (
    TRANSFER_STATUSES,
    ErpConflict,
    ErpConnection,
    ErpExternalReference,
    ErpOrderTransfer,
    ErpSyncJob,
    ErpSyncRecord,
)
from app.models.partner import Partner
from app.models.sales import Order, OrderItem, Product
from app.partner_catalog import PARTNER_TYPES
from app.sales_catalog import CONTAINER_TYPES, PRODUCT_CATEGORIES

import app.integrations.mock_erp  # noqa: F401  (registers the mock connector)

NUMBER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9\-/]{0,39}$")
SHARED_FIELDS = ("company_name", "street", "postal_code", "city", "country", "phone", "email")
CATALOGUE_FIELDS = ("name", "description", "category", "sales_unit", "container_type", "container_size", "list_price", "vat_rate", "is_active")


class IntegrationError(Exception):
    def __init__(self, message: str, status_code: int = 422) -> None:
        self.message = message
        self.status_code = status_code


@dataclass
class PlanItem:
    action: str
    external_key: str
    label: str
    detail: str
    crm_id: UUID | None = None
    field_name: str = ""
    crm_value: str = ""
    external_value: str = ""
    remote: object | None = None
    fills: dict[str, str] = field(default_factory=dict)


def tables_ready(db: Session) -> bool:
    bind = db.get_bind()
    return inspect(bind).has_table("erp_verbindungen")


def ensure_connection(db: Session) -> ErpConnection:
    row = db.scalar(select(ErpConnection).limit(1))
    if row is None:
        row = ErpConnection()
        db.add(row)
        db.flush()
    return row


def _connector(connection: ErpConnection):
    if connection.mode != SOURCE_MOCK:
        raise IntegrationError("Es ist kein Connector aktiv. Zuerst den Modus Mock-ERP wählen.", 422)
    if not connector_registered(SOURCE_MOCK):
        raise IntegrationError("Der Mock-Connector ist nicht registriert.", 500)
    return build_connector(SOURCE_MOCK)


def external_ready() -> bool:
    url = settings.erp_base_url.strip()
    return bool(
        connector_registered(SOURCE_EXTERN)
        and url.startswith("https://")
        and settings.erp_client_id.strip()
        and settings.erp_client_secret.strip()
    )


def set_mode(db: Session, mode: str) -> ErpConnection:
    if mode not in {"nicht_konfiguriert", "mock", "extern"}:
        raise IntegrationError("Der Integrationsmodus ist unbekannt.")
    if mode == "extern":
        raise IntegrationError(
            "Der Modus Externes ERP bleibt gesperrt. Es ist kein Connector registriert und keine gültige HTTPS-Konfiguration vorhanden. Das Mock-ERP ist keine echte Anbindung.",
            422,
        )
    row = ensure_connection(db)
    row.mode = mode
    row.connection_ok = None
    row.updated_at = _now()
    db.flush()
    return row


def set_intervals(db: Session, customers: int, products: int, statuses: int) -> ErpConnection:
    if any(value < 0 or value > 1440 for value in (customers, products, statuses)):
        raise IntegrationError("Intervalle liegen zwischen 0 und 1440 Minuten. 0 schaltet den Lauf aus.")
    row = ensure_connection(db)
    row.customers_interval_minutes = customers
    row.products_interval_minutes = products
    row.status_interval_minutes = statuses
    row.auto_order_transfer = False
    row.updated_at = _now()
    db.flush()
    return row


def test_connection(db: Session, actor_id: UUID | None) -> ErpSyncJob:
    row = ensure_connection(db)
    connector = _connector(row)
    job = _start_job(db, "verbindungstest", actor_id)
    try:
        message = connector.test_connection()
        row.connection_ok = True
        row.last_tested_at = _now()
        row.last_success_at = row.last_tested_at
        _finish(job, "erfolgreich", 1, 1, 0, message)
    except Exception as exc:
        row.connection_ok = False
        row.last_tested_at = _now()
        row.last_failure_at = row.last_tested_at
        _finish(job, "fehlgeschlagen", 1, 0, 1, _safe(exc))
    db.flush()
    return job


def preview(db: Session, kind: str) -> dict[str, object]:
    _require_kind(kind)
    connection = ensure_connection(db)
    connector = _connector(connection)
    items = _plan(db, connector, kind)
    return _preview_payload(kind, items)


def run_sync(db: Session, kind: str, actor_id: UUID | None) -> ErpSyncJob:
    _require_kind(kind)
    connection = _acquire(db, kind)
    job = _start_job(db, kind, actor_id)
    try:
        with db.begin_nested():
            connector = _connector(connection)
            items = _plan(db, connector, kind)
            _apply(db, connection, items, kind)
            failed = sum(1 for item in items if item.action in {"konflikt", "ungueltig"})
            success = len(items) - failed
            status = "erfolgreich" if failed == 0 else ("fehlgeschlagen" if success == 0 and failed else "teilweise")
            stamp = _now()
            if kind == "kunden":
                connection.last_customers_at = stamp
            elif kind == "produkte":
                connection.last_products_at = stamp
            else:
                connection.last_status_at = stamp
            if failed == 0:
                connection.last_success_at = stamp
            else:
                connection.last_failure_at = stamp
            message = f"{success} erfolgreich, {failed} mit Konflikt oder Fehler. Quelle: {SOURCE_LABELS[SOURCE_MOCK]}."
            _finish(job, status, len(items), success, failed, message)
            for item in items:
                db.add(
                    ErpSyncRecord(
                        job_id=job.id,
                        entity_type=kind,
                        external_key=item.external_key[:80],
                        action=item.action if item.action in {"neu", "aktualisiert", "unveraendert", "konflikt", "ungueltig", "uebertragen"} else "ungueltig",
                        message=item.detail[:500],
                        crm_id=item.crm_id,
                    )
                )
    except Exception as exc:
        db.expire(connection)
        db.refresh(connection)
        connection.last_failure_at = _now()
        text = exc.message if isinstance(exc, IntegrationError) else _safe(exc)
        _finish(job, "fehlgeschlagen", job.processed_count, job.success_count, max(job.failed_count, 1), text)
    finally:
        _release(connection)
        db.flush()
    return job


def prepare_transfer(db: Session, order_id: UUID) -> ErpOrderTransfer:
    order, partner, items = _order_bundle(db, order_id)
    reasons = _transfer_blockers(order, partner, items)
    if reasons:
        raise IntegrationError(" ".join(reasons))
    transfer = _transfer_row(db, order)
    if transfer.status == "erfolgreich":
        raise IntegrationError("Die Bestellung wurde bereits übertragen.", 409)
    if transfer.status == "manuelle_pruefung":
        raise IntegrationError("Die Übertragung wartet auf eine manuelle Prüfung.", 409)
    transfer.status = "bereit"
    order.transfer_status = "bereit"
    transfer.updated_at = _now()
    db.flush()
    return transfer


def transfer_order(db: Session, order_id: UUID, actor_id: UUID | None) -> ErpOrderTransfer:
    connection = ensure_connection(db)
    connector = _connector(connection)
    order, partner, items = _order_bundle(db, order_id)
    transfer = _transfer_row(db, order)
    if transfer.status == "erfolgreich":
        return transfer
    if transfer.status == "manuelle_pruefung":
        raise IntegrationError("Unklare Antwort. Zuerst über den Übertragungsschlüssel prüfen, nicht erneut senden.", 409)
    if transfer.status != "bereit" and transfer.status != "fehlgeschlagen":
        raise IntegrationError("Die Bestellung ist nicht zur Übertragung freigegeben.")
    reasons = _transfer_blockers(order, partner, items)
    if reasons:
        raise IntegrationError(" ".join(reasons))
    from app.integrations.types import ErpOrderLine, ErpOrderRequest

    request = ErpOrderRequest(
        idempotency_key=transfer.idempotency_key,
        order_number=order.order_number,
        customer_number=partner.erp_customer_number or "",
        lines=tuple(
            ErpOrderLine(item.sku, item.product_name, item.quantity, item.unit_price, item.vat_rate) for item in items
        ),
    )
    found = connector.find_order(transfer.idempotency_key)
    if found is not None:
        _mark_transferred(db, order, transfer, found.reference, found.status, SOURCE_MOCK)
        _transfer_job(db, actor_id, order, "Bereits vorhandene Mock-Referenz übernommen. Keine zweite Bestellung.")
        return transfer
    transfer.status = "in_uebertragung"
    order.transfer_status = "in_uebertragung"
    db.flush()
    last_error = ""
    for attempt in range(1, settings.erp_max_attempts + 1):
        transfer.attempts = attempt
        try:
            result = connector.submit_order(request)
        except ErpAmbiguousError as exc:
            found = connector.find_order(transfer.idempotency_key)
            if found is not None:
                _mark_transferred(db, order, transfer, found.reference, found.status, SOURCE_MOCK)
                _transfer_job(db, actor_id, order, "Nach unklarer Antwort über den Schlüssel gefunden.")
                return transfer
            transfer.status = "manuelle_pruefung"
            order.transfer_status = "manuelle_pruefung"
            transfer.last_error = exc.args[0]
            transfer.updated_at = _now()
            connection.last_failure_at = transfer.updated_at
            _transfer_job(db, actor_id, order, transfer.last_error, failed=True)
            db.flush()
            return transfer
        except ErpTechnicalError as exc:
            last_error = exc.args[0]
            continue
        else:
            _mark_transferred(db, order, transfer, result.reference, result.status, result.source)
            connection.last_success_at = _now()
            _transfer_job(db, actor_id, order, f"Mock-Referenz {result.reference}. Das ist keine Lieferung und keine Rechnung.")
            return transfer
    transfer.status = "fehlgeschlagen"
    order.transfer_status = "fehlgeschlagen"
    transfer.last_error = last_error or "Die Übertragung ist nach den erlaubten Versuchen fehlgeschlagen."
    transfer.updated_at = _now()
    connection.last_failure_at = transfer.updated_at
    _transfer_job(db, actor_id, order, transfer.last_error, failed=True)
    db.flush()
    return transfer


def recheck_transfer(db: Session, order_id: UUID, actor_id: UUID | None) -> ErpOrderTransfer:
    connection = ensure_connection(db)
    connector = _connector(connection)
    order = db.get(Order, order_id)
    if order is None:
        raise IntegrationError("Die Bestellung wurde nicht gefunden.", 404)
    transfer = db.scalar(select(ErpOrderTransfer).where(ErpOrderTransfer.order_id == order.id))
    if transfer is None:
        raise IntegrationError("Für diese Bestellung gibt es keine Übertragung.")
    found = connector.find_order(transfer.idempotency_key)
    if found is None:
        transfer.last_error = "Über den Übertragungsschlüssel liegt im Mock-ERP keine Bestellung. Es wurde nichts erneut gesendet."
        transfer.updated_at = _now()
        db.flush()
        return transfer
    _mark_transferred(db, order, transfer, found.reference, found.status, SOURCE_MOCK)
    _transfer_job(db, actor_id, order, "Prüfung hat die vorhandene Referenz bestätigt.")
    return transfer


def pull_order_status(db: Session, order_id: UUID, actor_id: UUID | None) -> Order:
    connection = ensure_connection(db)
    connector = _connector(connection)
    order = db.get(Order, order_id)
    if order is None or not order.erp_reference:
        raise IntegrationError("Die Bestellung hat keine ERP-Referenz.", 404)
    snapshot = connector.order_status(order.erp_reference)
    if snapshot is None:
        raise IntegrationError("Der Connector kennt diese Referenz nicht.", 404)
    _apply_snapshot(order, snapshot)
    transfer = db.scalar(select(ErpOrderTransfer).where(ErpOrderTransfer.order_id == order.id))
    if transfer is not None:
        transfer.external_status = snapshot.status
        transfer.external_status_at = _now()
        transfer.delivery_on = snapshot.delivery_on
        transfer.delivery_note = snapshot.delivery_note
        transfer.delivery_status = snapshot.delivery_status
        transfer.invoice_number = snapshot.invoice_number
        transfer.invoice_on = snapshot.invoice_on
        transfer.invoice_status = snapshot.invoice_status
        transfer.updated_at = _now()
    connection.last_status_at = _now()
    connection.last_success_at = connection.last_status_at
    job = _start_job(db, "bestellstatus", actor_id)
    db.add(ErpSyncRecord(job_id=job.id, entity_type="bestellung", external_key=order.erp_reference, action="aktualisiert", message=f"Externer Status {snapshot.status}. Der CRM-Status bleibt unverändert.", crm_id=order.id))
    _finish(job, "erfolgreich", 1, 1, 0, "Externer Status aktualisiert. Keine Faktura und keine Änderung des CRM-Status.")
    db.flush()
    return order


def advance_mock_status(db: Session, order_id: UUID) -> Order:
    connection = ensure_connection(db)
    if connection.mode != SOURCE_MOCK:
        raise IntegrationError("Eine simulierte Statusänderung gibt es nur im Mock-ERP.")
    order = db.get(Order, order_id)
    if order is None or not order.erp_reference:
        raise IntegrationError("Die Bestellung hat keine Mock-Referenz.", 404)
    connector = _connector(connection)
    snapshot = connector.advance_status(order.erp_reference)
    _apply_snapshot(order, snapshot)
    transfer = db.scalar(select(ErpOrderTransfer).where(ErpOrderTransfer.order_id == order.id))
    if transfer is not None:
        transfer.external_status = snapshot.status
        transfer.external_status_at = _now()
        transfer.delivery_status = snapshot.delivery_status
        transfer.delivery_on = snapshot.delivery_on
        transfer.delivery_note = snapshot.delivery_note
        transfer.invoice_number = snapshot.invoice_number
        transfer.invoice_on = snapshot.invoice_on
        transfer.invoice_status = snapshot.invoice_status
    db.flush()
    return order


def review_conflict(db: Session, conflict_id: UUID, actor_id: UUID | None) -> ErpConflict:
    row = db.get(ErpConflict, conflict_id)
    if row is None:
        raise IntegrationError("Der Konflikt wurde nicht gefunden.", 404)
    row.status = "geprueft"
    row.reviewed_at = _now()
    row.reviewed_by = actor_id
    db.flush()
    return row


def run_due_integrations(db: Session) -> int:
    if not tables_ready(db):
        return 0
    connection = ensure_connection(db)
    if connection.mode != SOURCE_MOCK:
        return 0
    if connection.auto_order_transfer:
        connection.auto_order_transfer = False
    ran = 0
    now = _now()
    plan = (
        ("kunden", connection.customers_interval_minutes, connection.last_customers_at),
        ("produkte", connection.products_interval_minutes, connection.last_products_at),
        ("bestellstatus", connection.status_interval_minutes, connection.last_status_at),
    )
    for kind, minutes, last in plan:
        if minutes <= 0:
            continue
        if last is not None and now - last < timedelta(minutes=minutes):
            continue
        if connection.running_kind:
            break
        try:
            run_sync(db, kind, None)
        except IntegrationError:
            pass
        ran += 1
    return ran


def status_payload(db: Session) -> dict[str, object]:
    connection = ensure_connection(db)
    open_conflicts = int(db.scalar(select(func.count()).select_from(ErpConflict).where(ErpConflict.status == "offen")) or 0)
    synced = int(db.scalar(select(func.count()).select_from(ErpExternalReference)) or 0)
    last_success = db.scalar(select(ErpSyncJob).where(ErpSyncJob.status == "erfolgreich").order_by(ErpSyncJob.finished_at.desc()).limit(1))
    last_failure = db.scalar(select(ErpSyncJob).where(ErpSyncJob.status == "fehlgeschlagen").order_by(ErpSyncJob.finished_at.desc()).limit(1))
    return {
        "mode": connection.mode,
        "mode_label": _mode_label(connection.mode),
        "external_available": external_ready(),
        "connection_ok": connection.connection_ok,
        "last_tested_at": connection.last_tested_at,
        "last_success_at": connection.last_success_at,
        "last_failure_at": connection.last_failure_at,
        "synced_records": synced,
        "open_conflicts": open_conflicts,
        "customers_interval_minutes": connection.customers_interval_minutes,
        "products_interval_minutes": connection.products_interval_minutes,
        "status_interval_minutes": connection.status_interval_minutes,
        "auto_order_transfer": False,
        "source_label": SOURCE_LABELS.get(connection.mode, "Nicht konfiguriert"),
        "leadership": [
            "ERP ist führend für ERP-Kundennummer, ERP-Kundenstatus, Artikelnummer und den aktuellen Katalogpreis.",
            "CRM ist führend für Notizen, Aktivitäten, Aufgaben, Segmente, Betreuung und den CRM-Partnerstatus.",
            "Abweichende, bereits gefüllte Stammdaten werden nicht überschrieben. Sie erscheinen als Konflikt.",
            "Gespeicherte Bestellpositionen behalten ihren Preis.",
            "Eine erfolgreiche Übertragung ist keine Lieferung und keine Rechnung.",
            "Das Mock-ERP ist eine Testumgebung und keine Anbindung an das ERP des Liechtensteiner Brauhauses.",
        ],
        "last_success_job_id": None if last_success is None else last_success.id,
        "last_failure_job_id": None if last_failure is None else last_failure.id,
    }


def job_csv(db: Session, job_id: UUID) -> str:
    job = db.get(ErpSyncJob, job_id)
    if job is None:
        raise IntegrationError("Der Synchronisationslauf wurde nicht gefunden.", 404)
    records = db.scalars(select(ErpSyncRecord).where(ErpSyncRecord.job_id == job.id).order_by(ErpSyncRecord.external_key)).all()
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(["Lauf", "Art", "Status", "Start", "Ende", "Verarbeitet", "Erfolgreich", "Fehlerhaft", "Hinweis"])
    writer.writerow([str(job.id), job.kind, job.status, job.started_at.isoformat(), "" if job.finished_at is None else job.finished_at.isoformat(), job.processed_count, job.success_count, job.failed_count, job.message])
    writer.writerow([])
    writer.writerow(["Schlüssel", "Aktion", "Hinweis"])
    for record in records:
        writer.writerow([record.external_key, record.action, record.message])
    return buffer.getvalue()


def _plan(db: Session, connector, kind: str) -> list[PlanItem]:
    if kind == "kunden":
        return [_customer_item(db, remote) for remote in connector.customers()]
    if kind == "produkte":
        return [_product_item(db, remote) for remote in connector.products()]
    return _status_plan(db, connector)


def _apply(db: Session, connection: ErpConnection, items: list[PlanItem], kind: str) -> None:
    now = _now()
    for item in items:
        if kind == "kunden" and isinstance(item.remote, ErpCustomer):
            _apply_customer(db, item, connection.mode, now)
        elif kind == "produkte" and isinstance(item.remote, ErpProduct):
            _apply_product(db, item, connection.mode, now)
        elif kind == "bestellstatus" and item.action == "aktualisiert" and item.crm_id is not None:
            order = db.get(Order, item.crm_id)
            snapshot = item.remote
            if order is not None and snapshot is not None and not isinstance(snapshot, (ErpCustomer, ErpProduct)):
                _apply_snapshot(order, snapshot)


def _customer_item(db: Session, remote: ErpCustomer) -> PlanItem:
    if not remote.company_name.strip() or not NUMBER.fullmatch(remote.number) or (remote.email and "@" not in remote.email):
        return PlanItem("ungueltig", remote.number or "ohne-nummer", remote.company_name or "Ohne Name", "Ungültige Kundendaten wurden abgelehnt.", remote=remote)
    partner = db.scalar(select(Partner).where(func.lower(Partner.erp_customer_number) == remote.number.lower()))
    if partner is None:
        named = db.scalars(select(Partner).where(func.lower(Partner.company_name) == remote.company_name.strip().lower(), Partner.archived_at.is_(None))).all()
        if len(named) > 1:
            return PlanItem("konflikt", remote.number, remote.company_name, "Mehrere Partner tragen denselben Namen.", field_name="company_name", external_value=remote.company_name, remote=remote)
        if len(named) == 1 and named[0].erp_customer_number and named[0].erp_customer_number.lower() != remote.number.lower():
            return PlanItem(
                "konflikt",
                remote.number,
                remote.company_name,
                "Der Name ist einem Partner mit einer anderen ERP-Kundennummer zugeordnet.",
                crm_id=named[0].id,
                field_name="erp_customer_number",
                crm_value=named[0].erp_customer_number,
                external_value=remote.number,
                remote=remote,
            )
        if len(named) == 1:
            partner = named[0]
    if partner is None:
        return PlanItem("neu", remote.number, remote.company_name, "Neuer Partner aus dem Connector. CRM-Status bleibt potenziell.", remote=remote)
    fills, conflicts = _shared_diff(partner, remote)
    if conflicts:
        first = conflicts[0]
        return PlanItem("konflikt", remote.number, partner.company_name, first[3], crm_id=partner.id, field_name=first[0], crm_value=first[1], external_value=first[2], remote=remote, fills=fills)
    if fills or (partner.erp_customer_status or "") != remote.status or not partner.erp_customer_number:
        return PlanItem("aktualisiert", remote.number, partner.company_name, "Leere Felder und der ERP-Status werden ergänzt.", crm_id=partner.id, remote=remote, fills=fills)
    return PlanItem("unveraendert", remote.number, partner.company_name, "Keine abweichenden Stammdaten.", crm_id=partner.id, remote=remote)


def _shared_diff(partner: Partner, remote: ErpCustomer) -> tuple[dict[str, str], list[tuple[str, str, str, str]]]:
    incoming = {
        "company_name": remote.company_name.strip(),
        "street": remote.street.strip(),
        "postal_code": remote.postal_code.strip(),
        "city": remote.city.strip(),
        "country": remote.country.strip() or "Schweiz",
        "phone": remote.phone.strip(),
        "email": remote.email.strip(),
    }
    fills: dict[str, str] = {}
    conflicts: list[tuple[str, str, str, str]] = []
    for name in SHARED_FIELDS:
        current = (getattr(partner, name) or "").strip()
        new = incoming[name]
        if not new or current == new:
            continue
        if not current:
            fills[name] = new
        else:
            conflicts.append((name, current, new, f"Feld {name} weicht ab und bleibt im CRM unverändert."))
    return fills, conflicts


def _apply_customer(db: Session, item: PlanItem, source: str, now: datetime) -> None:
    remote = item.remote
    if not isinstance(remote, ErpCustomer) or item.action == "ungueltig":
        return
    if item.action == "konflikt":
        _remember_conflict(db, item)
        if item.field_name not in {"erp_customer_number", "company_name"} and item.crm_id is not None:
            partner = db.get(Partner, item.crm_id)
            if partner is not None and (partner.erp_customer_number or "").lower() in {"", remote.number.lower()}:
                _fill_partner(partner, item.fills, remote, source, now)
        return
    if item.action == "neu":
        partner = Partner(
            company_name=remote.company_name.strip(),
            erp_customer_number=remote.number,
            partner_type="sonstige" if "sonstige" in PARTNER_TYPES else PARTNER_TYPES[0],
            street=remote.street or None,
            postal_code=remote.postal_code or None,
            city=remote.city or None,
            country=remote.country or "Schweiz",
            phone=remote.phone or None,
            email=remote.email or None,
            status="potenziell",
            priority="normal",
            notes="Fiktiver Datensatz aus dem Mock-ERP. Keine echte Kundenbeziehung und keine Verbindung zum ERP des Liechtensteiner Brauhauses." if remote.is_demo else None,
            is_demo=remote.is_demo,
            erp_customer_status=remote.status,
            erp_source=source,
            erp_synced_at=now,
        )
        db.add(partner)
        db.flush()
        item.crm_id = partner.id
        _remember_reference(db, source, "partner", remote.number, partner.id, now)
        return
    partner = db.get(Partner, item.crm_id) if item.crm_id else None
    if partner is None:
        return
    if not partner.erp_customer_number:
        partner.erp_customer_number = remote.number
    _fill_partner(partner, item.fills, remote, source, now)
    _remember_reference(db, source, "partner", remote.number, partner.id, now)


def _fill_partner(partner: Partner, fills: dict[str, str], remote: ErpCustomer, source: str, now: datetime) -> None:
    for name, value in fills.items():
        setattr(partner, name, value)
    partner.erp_customer_status = remote.status
    partner.erp_source = source
    partner.erp_synced_at = now


def _product_item(db: Session, remote: ErpProduct) -> PlanItem:
    if (
        not remote.name.strip()
        or not NUMBER.fullmatch(remote.sku)
        or remote.price < 0
        or remote.currency != "CHF"
        or remote.vat_rate < 0
        or remote.vat_rate > 100
        or remote.category not in PRODUCT_CATEGORIES
        or remote.container_type not in CONTAINER_TYPES
    ):
        return PlanItem("ungueltig", remote.sku or "ohne-artikel", remote.name or "Ohne Name", "Ungültige Produktdaten wurden abgelehnt.", remote=remote)
    product = db.scalar(select(Product).where(func.lower(Product.sku) == remote.sku.lower()))
    if product is None:
        return PlanItem("neu", remote.sku, remote.name, "Neues Katalogprodukt. Bestehende Bestellpositionen bleiben unberührt.", remote=remote)
    changed = _catalogue_changed(product, remote)
    if not changed:
        return PlanItem("unveraendert", remote.sku, product.name, "Katalogdaten stimmen überein.", crm_id=product.id, remote=remote)
    if product.erp_synced_at is not None and product.updated_at > product.erp_synced_at + timedelta(seconds=2):
        return PlanItem(
            "konflikt",
            remote.sku,
            product.name,
            "Das Produkt wurde im CRM nach der letzten Synchronisation geändert und wird nicht überschrieben.",
            crm_id=product.id,
            field_name="katalog",
            crm_value=str(product.list_price),
            external_value=str(remote.price),
            remote=remote,
        )
    return PlanItem("aktualisiert", remote.sku, product.name, "Katalogdaten werden vom Connector übernommen. Bestellpositionen bleiben gespeichert.", crm_id=product.id, remote=remote)


def _catalogue_changed(product: Product, remote: ErpProduct) -> bool:
    return any(
        (
            product.name != remote.name,
            (product.description or "") != remote.description,
            product.category != remote.category,
            (product.sales_unit or "") != remote.sales_unit,
            product.container_type != remote.container_type,
            (product.container_size or "") != remote.container_size,
            product.list_price != remote.price,
            product.vat_rate != remote.vat_rate,
            product.is_active != remote.is_active,
        )
    )


def _apply_product(db: Session, item: PlanItem, source: str, now: datetime) -> None:
    remote = item.remote
    if not isinstance(remote, ErpProduct) or item.action in {"ungueltig", "unveraendert"}:
        if isinstance(remote, ErpProduct) and item.action == "unveraendert" and item.crm_id is not None:
            product = db.get(Product, item.crm_id)
            if product is not None:
                product.erp_source = source
                product.erp_synced_at = now
                _remember_reference(db, source, "produkt", remote.sku, product.id, now)
        if item.action == "konflikt":
            _remember_conflict(db, item)
        return
    if item.action == "konflikt":
        _remember_conflict(db, item)
        return
    if item.action == "neu":
        product = Product(
            sku=remote.sku,
            name=remote.name,
            category=remote.category,
            description=remote.description,
            container_type=remote.container_type,
            container_size=remote.container_size,
            sales_unit=remote.sales_unit,
            list_price=remote.price,
            vat_rate=remote.vat_rate,
            is_active=remote.is_active,
            is_demo=remote.is_demo,
            currency="CHF",
            erp_source=source,
            erp_synced_at=now,
        )
        db.add(product)
        db.flush()
        item.crm_id = product.id
        _remember_reference(db, source, "produkt", remote.sku, product.id, now)
        return
    product = db.get(Product, item.crm_id) if item.crm_id else None
    if product is None:
        return
    product.name = remote.name
    product.description = remote.description
    product.category = remote.category
    product.sales_unit = remote.sales_unit
    product.container_type = remote.container_type
    product.container_size = remote.container_size
    product.list_price = remote.price
    product.vat_rate = remote.vat_rate
    product.is_active = remote.is_active
    product.currency = "CHF"
    product.erp_source = source
    product.erp_synced_at = now
    product.updated_at = now
    _remember_reference(db, source, "produkt", remote.sku, product.id, now)


def _status_plan(db: Session, connector) -> list[PlanItem]:
    orders = db.scalars(select(Order).where(Order.erp_reference.is_not(None), Order.archived_at.is_(None))).all()
    items: list[PlanItem] = []
    for order in orders:
        snapshot = connector.order_status(order.erp_reference or "")
        if snapshot is None:
            items.append(PlanItem("ungueltig", order.erp_reference or "", order.order_number, "Die Referenz ist im Connector nicht vorhanden.", crm_id=order.id))
            continue
        if order.erp_status == snapshot.status:
            items.append(PlanItem("unveraendert", snapshot.reference, order.order_number, "Der externe Status ist unverändert.", crm_id=order.id))
            continue
        items.append(PlanItem("aktualisiert", snapshot.reference, order.order_number, f"Externer Status {snapshot.status}.", crm_id=order.id, remote=snapshot))
    return items


def _remember_conflict(db: Session, item: PlanItem) -> None:
    existing = db.scalar(
        select(ErpConflict).where(
            ErpConflict.external_key == item.external_key,
            ErpConflict.field_name == item.field_name,
            ErpConflict.status == "offen",
        )
    )
    if existing is not None:
        return
    db.add(
        ErpConflict(
            kind=item.field_name or "abweichung",
            entity_type="partner" if isinstance(item.remote, ErpCustomer) else "produkt",
            external_key=item.external_key,
            crm_id=item.crm_id,
            field_name=item.field_name,
            crm_value=item.crm_value[:500],
            external_value=item.external_value[:500],
            message=item.detail,
        )
    )


def _remember_reference(db: Session, source: str, entity_type: str, external_key: str, crm_id: UUID, now: datetime) -> None:
    row = db.scalar(
        select(ErpExternalReference).where(
            ErpExternalReference.source == source,
            ErpExternalReference.entity_type == entity_type,
            ErpExternalReference.external_key == external_key,
        )
    )
    if row is None:
        db.add(ErpExternalReference(source=source, entity_type=entity_type, external_key=external_key, crm_id=crm_id, last_seen_at=now))
    else:
        row.crm_id = crm_id
        row.last_seen_at = now


def _order_bundle(db: Session, order_id: UUID) -> tuple[Order, Partner, list[OrderItem]]:
    order = db.get(Order, order_id)
    if order is None or order.archived_at is not None:
        raise IntegrationError("Die Bestellung wurde nicht gefunden.", 404)
    partner = db.get(Partner, order.partner_id)
    if partner is None:
        raise IntegrationError("Der Vertriebspartner wurde nicht gefunden.", 404)
    items = list(db.scalars(select(OrderItem).where(OrderItem.order_id == order.id).order_by(OrderItem.position)).all())
    return order, partner, items


def _transfer_blockers(order: Order, partner: Partner, items: list[OrderItem]) -> list[str]:
    reasons: list[str] = []
    if order.status in {"entwurf", "storniert"}:
        reasons.append("Entwürfe und stornierte Bestellungen werden nicht übertragen.")
    if not partner.erp_customer_number:
        reasons.append("Dem Partner fehlt eine ERP-Kundennummer.")
    if not items:
        reasons.append("Die Bestellung hat keine Positionen.")
    return reasons


def _transfer_row(db: Session, order: Order) -> ErpOrderTransfer:
    row = db.scalar(select(ErpOrderTransfer).where(ErpOrderTransfer.order_id == order.id))
    if row is None:
        row = ErpOrderTransfer(order_id=order.id, idempotency_key=f"crm-{order.id}", status=order.transfer_status or "nicht_uebertragen")
        db.add(row)
        db.flush()
    return row


def _mark_transferred(db: Session, order: Order, transfer: ErpOrderTransfer, reference: str, status: str, source: str) -> None:
    now = _now()
    transfer.status = "erfolgreich"
    transfer.external_reference = reference
    transfer.external_status = status
    transfer.external_status_at = now
    transfer.source = source
    transfer.last_error = ""
    transfer.updated_at = now
    order.transfer_status = "erfolgreich"
    order.erp_reference = reference
    order.erp_status = status
    order.erp_status_at = now
    order.erp_status_source = source
    _remember_reference(db, source, "bestellung", reference, order.id, now)


def _apply_snapshot(order: Order, snapshot) -> None:
    order.erp_status = snapshot.status
    order.erp_status_at = _now()
    order.erp_status_source = snapshot.source
    order.delivery_on = snapshot.delivery_on
    order.delivery_note = snapshot.delivery_note
    order.delivery_status = snapshot.delivery_status
    order.invoice_number = snapshot.invoice_number
    order.invoice_on = snapshot.invoice_on
    order.invoice_status = snapshot.invoice_status


def _transfer_job(db: Session, actor_id: UUID | None, order: Order, message: str, failed: bool = False) -> None:
    job = _start_job(db, "uebertragung", actor_id)
    db.add(ErpSyncRecord(job_id=job.id, entity_type="bestellung", external_key=order.order_number, action="uebertragen" if not failed else "ungueltig", message=message, crm_id=order.id))
    _finish(job, "fehlgeschlagen" if failed else "erfolgreich", 1, 0 if failed else 1, 1 if failed else 0, message)


def _acquire(db: Session, kind: str) -> ErpConnection:
    connection = ensure_connection(db)
    db.execute(select(ErpConnection).where(ErpConnection.id == connection.id).with_for_update())
    db.refresh(connection)
    if connection.running_kind and connection.running_since and _now() - connection.running_since < timedelta(minutes=15):
        raise IntegrationError("Eine Synchronisation läuft bereits.", 409)
    connection.running_kind = kind
    connection.running_since = _now()
    db.flush()
    return connection


def _release(connection: ErpConnection) -> None:
    connection.running_kind = None
    connection.running_since = None


def _start_job(db: Session, kind: str, actor_id: UUID | None) -> ErpSyncJob:
    job = ErpSyncJob(kind=kind, status="erfolgreich", started_at=_now(), actor_id=actor_id, message="")
    db.add(job)
    db.flush()
    return job


def _finish(job: ErpSyncJob, status: str, processed: int, success: int, failed: int, message: str) -> None:
    job.status = status
    job.finished_at = _now()
    job.processed_count = processed
    job.success_count = success
    job.failed_count = failed
    job.message = message[:1000]


def _preview_payload(kind: str, items: list[PlanItem]) -> dict[str, object]:
    def pack(action: str) -> list[dict[str, str]]:
        return [{"external_key": item.external_key, "label": item.label, "detail": item.detail} for item in items if item.action == action]

    return {
        "kind": kind,
        "dry_run": True,
        "source_label": SOURCE_LABELS[SOURCE_MOCK],
        "new": pack("neu"),
        "update": pack("aktualisiert"),
        "unchanged": pack("unveraendert"),
        "conflicts": pack("konflikt"),
        "invalid": pack("ungueltig"),
    }


def _require_kind(kind: str) -> None:
    if kind not in {"kunden", "produkte", "bestellstatus"}:
        raise IntegrationError("Die Synchronisationsart ist unbekannt.")


def _mode_label(mode: str) -> str:
    return {
        "nicht_konfiguriert": "Nicht konfiguriert",
        "mock": "Mock-ERP, nur Testdaten",
        "extern": "Externes ERP",
    }.get(mode, mode)


def _safe(exc: Exception) -> str:
    text = str(exc).strip() or exc.__class__.__name__
    return text[:300]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def known_transfer_statuses() -> tuple[str, ...]:
    return TRANSFER_STATUSES
