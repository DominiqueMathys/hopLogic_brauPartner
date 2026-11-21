"""Festival requests, stock, reservations and returns.

Most cases roll back with the outer transaction. The concurrency and persistence
cases commit on purpose and delete only the rows they created.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, get_db
from app.main import app
from app.models.engagement import AutomationRule
from app.models.festival import (
    Festival,
    FestivalMaterial,
    FestivalQuote,
    MaterialMovement,
    MaterialReservation,
)
from app.models.task import Task
from app.services.automation import run_due_automations
from support import PASSWORD, AuthClient, login_session

ROOT = Path(__file__).resolve().parents[1]
START = datetime(2028, 7, 17, 8, 0, tzinfo=timezone.utc)
END = datetime(2028, 7, 18, 0, 0, tzinfo=timezone.utc)


@pytest.fixture(scope="module", autouse=True)
def migrated_database() -> None:
    command.upgrade(Config(str(ROOT / "backend" / "alembic.ini")), "head")


@pytest.fixture()
def db_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint", autoflush=False, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def api(db_session: Session) -> Iterator[TestClient]:
    for row in db_session.scalars(select(AutomationRule).where(AutomationRule.trigger_type.like("festival_%"), AutomationRule.status == "aktiv")).all():
        row.status = "pausiert"
    db_session.flush()

    def override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override
    with AuthClient(app) as client:
        login_session(client, db_session)
        yield client
    app.dependency_overrides.pop(get_db, None)


def _event(api: TestClient, name: str = "QA Fest") -> dict:
    response = api.post(
        "/api/festivals",
        json={
            "name": name,
            "organizer_name": "Eventorganisation Seeblick",
            "event_type": "fest",
            "city": "Locarno",
            "region": "Tessin",
            "country": "Schweiz",
            "starts_at": START.isoformat(),
            "ends_at": END.isoformat(),
            "expected_visitors": 400,
            "account_owner": "Pytest Admin",
            "drinks": "Fiktives Sortiment",
            "material_wish": "Zapfanlagen und Gläser",
            "notes": "Fiktive Festanfrage für den automatisierten Test.",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def _material(api: TestClient, name: str, quantity: int, **extra: object) -> dict:
    created = api.post(
        "/api/festivals/materials",
        json={"name": name, "tracking": "menge", "unit": "Stück", "location": "Lager Vaduz", "prep_hours": 0, **extra},
    )
    assert created.status_code == 201, created.text
    material = created.json()
    stock = api.post(
        f"/api/festivals/materials/{material['id']}/stock",
        json={"movement_type": "wareneingang", "quantity": quantity, "note": "Testbestand"},
    )
    assert stock.status_code == 200, stock.text
    return stock.json()


def _bind(api: TestClient, festival_id: str) -> None:
    quote = api.post(
        "/api/festivals/quotes",
        json={
            "festival_id": festival_id,
            "vat_rate": "8.10",
            "notes": "Fiktive Richtpreise, keine Brauhaus-Preisliste.",
            "items": [
                {
                    "kind": "material",
                    "description": "Fiktive Materialmiete",
                    "quantity": "2",
                    "unit_price": "10.00",
                    "vat_rate": "8.10",
                }
            ],
        },
    )
    assert quote.status_code == 201, quote.text
    body = quote.json()
    assert Decimal(str(body["gross_total"])) == Decimal("21.62")
    accepted = api.post(f"/api/festivals/quotes/{body['id']}/accept")
    assert accepted.status_code == 200, accepted.text
    converted = api.post(f"/api/festivals/{festival_id}/convert")
    assert converted.status_code == 200, converted.text


def _reserve(api: TestClient, festival_id: str, material_id: str, quantity: int, **extra: object) -> dict:
    response = api.post(
        "/api/festivals/reservations",
        json={
            "festival_id": festival_id,
            "starts_at": START.isoformat(),
            "ends_at": END.isoformat(),
            "lines": [{"material_id": material_id, "quantity": quantity}],
            **extra,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_request_edit_duplicate_and_calendar(api: TestClient) -> None:
    event = _event(api, "QA Fest erstellen")
    assert event["event_number"].startswith("FEST-")
    assert event["request_status"] == "neue_anfrage"
    assert event["is_binding"] is False
    renamed = api.patch(
        f"/api/festivals/{event['id']}",
        json={"name": "QA Fest bearbeitet", "change_reason": "Telefonische Korrektur"},
    )
    assert renamed.status_code == 200, renamed.text
    assert renamed.json()["name"] == "QA Fest bearbeitet"
    detail = api.get(f"/api/festivals/{event['id']}")
    assert detail.status_code == 200
    assert any(row["field_name"] == "name" for row in detail.json()["changes"])
    copy = api.post(f"/api/festivals/{event['id']}/duplicate")
    assert copy.status_code == 201, copy.text
    assert copy.json()["id"] != event["id"]
    calendar = api.get("/api/festivals/calendar", params={"start": "2028-07-01T00:00:00+02:00", "end": "2028-07-31T00:00:00+02:00", "region": "Tessin"})
    assert calendar.status_code == 200, calendar.text
    assert any(item["id"] == event["id"] for item in calendar.json()["items"])
    archived = api.post(f"/api/festivals/{copy.json()['id']}/archive")
    assert archived.status_code == 200, archived.text
    restored = api.post(f"/api/festivals/{copy.json()['id']}/restore")
    assert restored.status_code == 200, restored.text


def test_quote_version_and_amounts(api: TestClient) -> None:
    event = _event(api, "QA Offerte")
    quote = api.post(
        "/api/festivals/quotes",
        json={
            "festival_id": event["id"],
            "vat_rate": "8.10",
            "items": [{"description": "Miete", "quantity": "1", "unit_price": "100.00", "discount_percent": "10", "vat_rate": "8.10"}],
        },
    )
    assert quote.status_code == 201, quote.text
    original = quote.json()
    assert Decimal(str(original["net_total"])) == Decimal("90.00")
    version = api.post(f"/api/festivals/quotes/{original['id']}/version")
    assert version.status_code == 201, version.text
    assert version.json()["version"] == 2
    assert version.json()["quote_number"] == original["quote_number"]
    sent = api.post(f"/api/festivals/quotes/{version.json()['id']}/status", json={"status": "versendet"})
    assert sent.status_code == 200, sent.text
    pdf = api.get(f"/api/festivals/quotes/{version.json()['id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")


def test_availability_overlap_and_buffer(api: TestClient) -> None:
    event = _event(api, "QA Verfügbarkeit")
    material = _material(api, "QA Zapfanlage", 5, prep_hours=4, return_hours=4, cleaning_hours=4)
    _bind(api, event["id"])
    first = _reserve(api, event["id"], material["id"], 3, prep_hours=4, return_hours=4, cleaning_hours=4)
    confirmed = api.post(f"/api/festivals/reservations/{first['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "bestaetigt"
    second = _reserve(api, event["id"], material["id"], 3)
    conflict = api.post(f"/api/festivals/reservations/{second['id']}/confirm")
    assert conflict.status_code == 409, conflict.text
    assert "Materialkonflikt" in conflict.json()["detail"]
    probe = api.get(
        "/api/festivals/materials/availability",
        params={
            "material_id": material["id"],
            "start": START.isoformat(),
            "end": END.isoformat(),
            "quantity": 3,
            "prep_hours": 4,
        },
    )
    assert probe.status_code == 200, probe.text
    assert probe.json()["available"] == 2
    assert probe.json()["enough"] is False


def test_serialized_asset_and_stock_correction(api: TestClient, db_session: Session) -> None:
    created = api.post("/api/festivals/materials", json={"name": "QA Einzelzapf", "tracking": "einzel", "unit": "Stück"})
    assert created.status_code == 201, created.text
    material_id = created.json()["id"]
    asset = api.post(f"/api/festivals/materials/{material_id}/assets", json={"inventory_number": f"QA-{uuid4().hex[:6]}"})
    assert asset.status_code == 201, asset.text
    denied = api.post(
        "/api/festivals/materials/{0}/stock".format(material_id),
        json={"movement_type": "bestandskorrektur", "quantity": 1, "bucket": "total", "note": ""},
    )
    assert denied.status_code == 422
    corrected = api.post(
        f"/api/festivals/materials/{material_id}/stock",
        json={"movement_type": "bestandskorrektur", "quantity": 0, "bucket": "total", "note": "Inventur ohne Mengenänderung"},
    )
    assert corrected.status_code == 200, corrected.text
    assert db_session.get(FestivalMaterial, UUID(material_id)).quantity_total == 1


def test_issue_return_and_no_double_booking(api: TestClient) -> None:
    event = _event(api, "QA Rücknahme")
    material = _material(api, "QA Gläser", 100)
    _bind(api, event["id"])
    reservation = _reserve(api, event["id"], material["id"], 100)
    early = api.post(f"/api/festivals/reservations/{reservation['id']}/issue", json={"lines": [{"line_id": reservation["lines"][0]["id"], "quantity": 100}]})
    assert early.status_code == 409
    confirmed = api.post(f"/api/festivals/reservations/{reservation['id']}/confirm")
    assert confirmed.status_code == 200, confirmed.text
    line_id = confirmed.json()["lines"][0]["id"]
    issued = api.post(
        f"/api/festivals/reservations/{reservation['id']}/issue",
        json={"lines": [{"line_id": line_id, "quantity": 100}], "condition_note": "Vollständig und sauber"},
    )
    assert issued.status_code == 200, issued.text
    again = api.post(
        f"/api/festivals/reservations/{reservation['id']}/issue",
        json={"lines": [{"line_id": line_id, "quantity": 100}]},
    )
    assert again.status_code == 409
    returned = api.post(
        f"/api/festivals/reservations/{reservation['id']}/return",
        json={"lines": [{"line_id": line_id, "returned_qty": 92, "damaged_qty": 3, "missing_qty": 5}], "notes": "Kontrolle nach dem Fest"},
    )
    assert returned.status_code == 200, returned.text
    assert returned.json()["status"] == "zurueckgegeben"
    repeat = api.post(
        f"/api/festivals/reservations/{reservation['id']}/return",
        json={"lines": [{"line_id": line_id, "returned_qty": 92, "damaged_qty": 3, "missing_qty": 5}]},
    )
    assert repeat.status_code == 409
    stock = api.get(f"/api/festivals/materials")
    row = next(item for item in stock.json()["items"] if item["id"] == material["id"])
    assert row["quantity_total"] == 100
    assert row["quantity_defective"] == 3
    assert row["quantity_missing"] == 5
    assert row["available_now"] == 92
    closed = api.post(f"/api/festivals/{event['id']}/close")
    assert closed.status_code == 200, closed.text
    assert closed.json()["event_status"] == "abgeschlossen"


def test_transport_assignment_and_dashboard(api: TestClient) -> None:
    event = _event(api, "QA Transport")
    delivery = api.post(
        "/api/festivals/deliveries",
        json={"festival_id": event["id"], "address": "Seeufer, 6600 Locarno", "deliver_at": START.isoformat(), "status": "geplant"},
    )
    assert delivery.status_code == 201, delivery.text
    pdf = api.get(f"/api/festivals/deliveries/{delivery.json()['id']}/pdf")
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    reached = api.get(f"/api/festivals/{event['id']}")
    assert reached.json()["delivery_status"] == "geplant"
    first = api.post(
        "/api/festivals/assignments",
        json={
            "festival_id": event["id"],
            "person_name": "Lea Test",
            "kind": "lieferung",
            "task": "Material anliefern",
            "starts_at": START.isoformat(),
            "ends_at": END.isoformat(),
        },
    )
    assert first.status_code == 201, first.text
    overlap = api.post(
        "/api/festivals/assignments",
        json={
            "festival_id": event["id"],
            "person_name": "Lea Test",
            "kind": "aufbau",
            "task": "Zweiter Einsatz",
            "starts_at": START.isoformat(),
            "ends_at": END.isoformat(),
        },
    )
    assert overlap.status_code == 409
    metrics = api.get("/api/festivals/dashboard")
    assert metrics.status_code == 200, metrics.text
    assert metrics.json()["planned"] >= 1
    assert "ERP" in metrics.json()["erp_notice"]
    report = api.get("/api/reports")
    assert report.status_code == 200, report.text
    assert any(item["key"] == "planned" and item["section"] == "festivals" for item in report.json()["kpis"])


def test_return_task_is_created_once(api: TestClient, db_session: Session) -> None:
    event = _event(api, "QA Automatisierung")
    past_end = datetime.now(timezone.utc) - timedelta(days=3)
    past_start = past_end - timedelta(hours=6)
    edited = api.patch(
        f"/api/festivals/{event['id']}",
        json={"starts_at": past_start.isoformat(), "ends_at": past_end.isoformat(), "change_reason": "Testzeitraum"},
    )
    assert edited.status_code == 200, edited.text
    material = _material(api, "QA Rücklauf", 2)
    reservation = MaterialReservation(
        reservation_number=f"RES-TEST-{uuid4().hex[:6]}",
        festival_id=event["id"],
        status="ausgegeben",
        starts_at=past_start,
        ends_at=past_end,
    )
    db_session.add(reservation)
    db_session.flush()
    rule = AutomationRule(
        name="QA Rücknahme",
        trigger_type="festival_ended",
        trigger_config={"days": 1},
        action_type="create_task",
        action_config={"title": "Rücknahme prüfen", "due_days": 1},
        status="aktiv",
        account_owner="Pytest Admin",
    )
    db_session.add(rule)
    db_session.flush()
    assert run_due_automations(db_session) >= 1
    task = db_session.scalar(select(Task).where(Task.event_id == event["id"], Task.title == "Rücknahme prüfen"))
    assert task is not None
    assert run_due_automations(db_session) >= 0
    assert len(db_session.scalars(select(Task).where(Task.event_id == event["id"], Task.title == "Rücknahme prüfen")).all()) == 1


def test_roles_cannot_cross_festival_actions(db_session: Session) -> None:
    def override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override
    try:
        with AuthClient(app) as client:
            login_session(client, db_session, role="vertrieb", email="pytest-vertrieb-fest@example.invalid", first="Vera", last="Vertrieb")
            created = client.post(
                "/api/festivals",
                json={
                    "name": "QA Rolle",
                    "organizer_name": "Veranstalter Rolle",
                    "starts_at": START.isoformat(),
                    "ends_at": END.isoformat(),
                },
            )
            assert created.status_code == 201, created.text
            material = client.post("/api/festivals/materials", json={"name": "QA Rollenmaterial", "tracking": "menge"})
            assert material.status_code == 403
        with AuthClient(app) as client:
            login_session(client, db_session, role="logistik", email="pytest-logistik-fest@example.invalid", first="Lars", last="Logistik")
            denied = client.post(
                "/api/festivals",
                json={
                    "name": "QA Logistik",
                    "organizer_name": "Veranstalter",
                    "starts_at": START.isoformat(),
                    "ends_at": END.isoformat(),
                },
            )
            assert denied.status_code == 403
            assert client.get("/api/festivals").status_code == 200
        with AuthClient(app) as client:
            login_session(client, db_session, role="marketing", email="pytest-marketing-fest@example.invalid", first="Mia", last="Marketing")
            assert client.get("/api/festivals/dashboard").status_code == 200
            assert client.post("/api/festivals/materials", json={"name": "Nein", "tracking": "menge"}).status_code == 403
        with AuthClient(app) as client:
            login_session(client, db_session, role="kundenservice", email="pytest-service-fest@example.invalid", first="Kim", last="Service")
            assert client.get("/api/festivals").status_code == 200
            assert client.post(
                "/api/festivals",
                json={"name": "QA Service", "organizer_name": "Veranstalter", "starts_at": START.isoformat(), "ends_at": END.isoformat()},
            ).status_code == 403
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_parallel_confirm_cannot_overbook() -> None:
    token = uuid4().hex[:8]
    created: dict[str, str] = {}
    try:
        with SessionLocal() as db:
            from app.services.identity import ensure_catalog

            ensure_catalog(db)
            db.commit()
        with AuthClient(app) as client:
            with SessionLocal() as db:
                login_session(client, db, email="pytest-admin@example.invalid")
                db.commit()
            material = client.post("/api/festivals/materials", json={"name": f"QA Rennen {token}", "tracking": "menge", "unit": "Stück"})
            assert material.status_code == 201, material.text
            created["material"] = material.json()["id"]
            stock = client.post(
                f"/api/festivals/materials/{created['material']}/stock",
                json={"movement_type": "wareneingang", "quantity": 1, "note": "ein Stück"},
            )
            assert stock.status_code == 200, stock.text
            event = client.post(
                "/api/festivals",
                json={
                    "name": f"QA Rennen {token}",
                    "organizer_name": "Fiktiver Veranstalter",
                    "starts_at": START.isoformat(),
                    "ends_at": END.isoformat(),
                    "notes": "Wird nach dem Test gelöscht.",
                },
            )
            assert event.status_code == 201, event.text
            created["festival"] = event.json()["id"]
            quote = client.post(
                "/api/festivals/quotes",
                json={"festival_id": created["festival"], "items": [{"description": "Test", "quantity": "1", "unit_price": "1.00"}]},
            )
            assert quote.status_code == 201, quote.text
            assert client.post(f"/api/festivals/quotes/{quote.json()['id']}/accept").status_code == 200
            assert client.post(f"/api/festivals/{created['festival']}/convert").status_code == 200
            reservations = []
            for _ in range(2):
                row = client.post(
                    "/api/festivals/reservations",
                    json={
                        "festival_id": created["festival"],
                        "starts_at": START.isoformat(),
                        "ends_at": END.isoformat(),
                        "lines": [{"material_id": created["material"], "quantity": 1}],
                    },
                )
                assert row.status_code == 201, row.text
                reservations.append(row.json()["id"])
            import threading

            from app.services.festival_stock import FestivalError, confirm_reservation

            results: list[int] = []

            def confirm(reservation_id: str) -> None:
                session = SessionLocal()
                try:
                    confirm_reservation(session, UUID(reservation_id))
                    session.commit()
                    results.append(200)
                except FestivalError as error:
                    if error.persist:
                        session.commit()
                    else:
                        session.rollback()
                    results.append(error.status_code)
                finally:
                    session.close()

            threads = [threading.Thread(target=confirm, args=(reservation_id,)) for reservation_id in reservations]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(10)
        assert sorted(results) == [200, 409]
        with SessionLocal() as db:
            confirmed = db.scalars(
                select(MaterialReservation).where(
                    MaterialReservation.festival_id == created["festival"],
                    MaterialReservation.status == "bestaetigt",
                )
            ).all()
            assert len(confirmed) == 1
    finally:
        with SessionLocal() as db:
            if created.get("festival"):
                from app.models.festival import FestivalChange, FestivalQuoteItem, MaterialIssue, MaterialReservationLine, MaterialReturn

                festival_id = created["festival"]
                reservation_ids = list(db.scalars(select(MaterialReservation.id).where(MaterialReservation.festival_id == festival_id)).all())
                if reservation_ids:
                    db.query(MaterialReservationLine).filter(MaterialReservationLine.reservation_id.in_(reservation_ids)).delete(synchronize_session=False)
                    db.query(MaterialIssue).filter(MaterialIssue.festival_id == festival_id).delete(synchronize_session=False)
                    db.query(MaterialReturn).filter(MaterialReturn.festival_id == festival_id).delete(synchronize_session=False)
                    db.query(MaterialReservation).filter(MaterialReservation.festival_id == festival_id).delete(synchronize_session=False)
                quote_ids = list(db.scalars(select(FestivalQuote.id).where(FestivalQuote.festival_id == festival_id)).all())
                if quote_ids:
                    db.query(FestivalQuoteItem).filter(FestivalQuoteItem.quote_id.in_(quote_ids)).delete(synchronize_session=False)
                    db.query(FestivalQuote).filter(FestivalQuote.festival_id == festival_id).delete(synchronize_session=False)
                db.query(FestivalChange).filter(FestivalChange.festival_id == festival_id).delete(synchronize_session=False)
                db.query(MaterialMovement).filter(MaterialMovement.festival_id == festival_id).delete(synchronize_session=False)
                db.query(Festival).filter(Festival.id == festival_id).delete(synchronize_session=False)
            if created.get("material"):
                db.query(MaterialMovement).filter(MaterialMovement.material_id == created["material"]).delete(synchronize_session=False)
                db.query(FestivalMaterial).filter(FestivalMaterial.id == created["material"]).delete(synchronize_session=False)
            db.commit()


def test_festival_persists_until_cleanup() -> None:
    token = uuid4().hex[:8]
    festival_id = None
    try:
        with AuthClient(app) as client:
            with SessionLocal() as db:
                login_session(client, db)
                db.commit()
            response = client.post(
                "/api/festivals",
                json={
                    "name": f"QA Persistenz {token}",
                    "organizer_name": "Fiktiver Veranstalter",
                    "starts_at": START.isoformat(),
                    "ends_at": END.isoformat(),
                    "notes": "Wird nach dem Persistenztest gelöscht.",
                },
            )
            assert response.status_code == 201, response.text
            festival_id = response.json()["id"]
        with SessionLocal() as db:
            stored = db.get(Festival, festival_id)
            assert stored is not None
            assert stored.name == f"QA Persistenz {token}"
    finally:
        if festival_id:
            with SessionLocal() as db:
                from app.models.festival import FestivalChange

                db.query(FestivalChange).filter(FestivalChange.festival_id == festival_id).delete(synchronize_session=False)
                db.query(Festival).filter(Festival.id == festival_id).delete(synchronize_session=False)
                db.commit()
