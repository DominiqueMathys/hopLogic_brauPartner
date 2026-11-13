from collections.abc import Iterator
from datetime import date
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, engine, get_db
from app.main import app
from app.models.contact import CompanyContact, Contact
from app.models.partner import Partner
from app.models.sales import Deal, DealStageHistory, Order, OrderItem, Product
from app.models.service import (
    CustomerSegment,
    SegmentCondition,
    ServiceTicket,
    TicketAttachment,
    TicketEvent,
    TicketProduct,
    TicketResolution,
)
from app.models.task import Task

ROOT = Path(__file__).resolve().parents[1]
PNG = bytes.fromhex("89504e470d0a1a0a") + b"qa"


@pytest.fixture(scope="module", autouse=True)
def migrated_database() -> None:
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    command.upgrade(config, "head")


@pytest.fixture()
def db_session() -> Iterator[Session]:
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection,
        join_transaction_mode="create_savepoint",
        autoflush=False,
        expire_on_commit=False,
    )
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture()
def api(db_session: Session) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.pop(get_db, None)


def create_partner(api: TestClient, suffix: str, partner_type: str = "restaurant") -> str:
    response = api.post(
        "/api/partners",
        json={
            "company_name": f"QA Service {suffix}",
            "erp_customer_number": f"SV-{suffix}",
            "partner_type": partner_type,
            "city": f"Orts{suffix}",
            "country": "Liechtenstein",
            "status": "aktiv",
            "priority": "normal",
            "account_owner": "QA Betreuung",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_contact(api: TestClient, suffix: str, partner_id: str) -> str:
    response = api.post(
        "/api/contacts",
        json={
            "first_name": "Giulia",
            "last_name": f"Service {suffix}",
            "account_owner": "Sandra Lutz",
            "preferred_language": "de",
            "preferred_channel": "telefon",
            "lifecycle_phase": "kunde",
            "lead_status": "keiner",
            "status": "aktiv",
            "processing_basis": "nicht_dokumentiert",
            "companies": [{"partner_id": partner_id, "is_primary": True}],
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_product(api: TestClient, suffix: str) -> str:
    response = api.post(
        "/api/products",
        json={
            "sku": f"QA-SV-{suffix}",
            "name": f"Servicebier {suffix}",
            "category": "bier",
            "container_type": "flasche",
            "container_size": "33 cl",
            "sales_unit": "Flasche",
            "list_price": "2.40",
            "vat_rate": "8.10",
            "is_active": True,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_order(api: TestClient, partner_id: str, product_id: str, *, submit: bool) -> dict:
    response = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "ordered_on": "2026-11-12",
            "items": [{"product_id": product_id, "quantity": "3", "discount_percent": "0"}],
            "submit": submit,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def ticket_body(partner_id: str, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "subject": "Beschädigte Bierlieferung",
        "category": "beschaedigte_lieferung",
        "description": "Bei der letzten Lieferung wurden mehrere beschädigte Flaschen festgestellt.",
        "partner_id": partner_id,
        "priority": "hoch",
    }
    body.update(overrides)
    return body


def test_create_edit_assign_and_history(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    contact_id = create_contact(api, suffix, partner_id)
    product_id = create_product(api, suffix)
    order = create_order(api, partner_id, product_id, submit=True)

    created = api.post(
        "/api/tickets",
        json=ticket_body(
            partner_id,
            contact_id=contact_id,
            order_id=order["id"],
            product_ids=[product_id],
            account_owner="Sandra Lutz",
        ),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["ticket_number"].startswith("SRV-")
    assert body["status"] == "neu"
    assert body["order_number"] == order["order_number"]
    assert body["products"][0]["id"] == product_id
    assert body["events"][0]["event_type"] == "created"
    ticket_id = body["id"]

    edited = api.put(
        f"/api/tickets/{ticket_id}",
        json=ticket_body(
            partner_id,
            contact_id=contact_id,
            order_id=order["id"],
            product_ids=[product_id],
            subject="Beschädigte Lieferung nachgefasst",
            account_owner="Sandra Lutz",
        ),
    )
    assert edited.status_code == 200
    assert edited.json()["subject"] == "Beschädigte Lieferung nachgefasst"
    assert edited.json()["events"][0]["event_type"] == "created"

    assigned = api.post(
        f"/api/tickets/{ticket_id}/assign",
        json={"account_owner": "Marco Keller", "changed_by": "Sandra Lutz"},
    )
    assert assigned.status_code == 200
    assert assigned.json()["account_owner"] == "Marco Keller"
    assert any(event["event_type"] == "owner_changed" for event in assigned.json()["events"])

    status = api.post(f"/api/tickets/{ticket_id}/status", json={"status": "in_bearbeitung", "changed_by": "Marco Keller"})
    assert status.status_code == 200
    assert status.json()["status"] == "in_bearbeitung"

    rejected = api.post(f"/api/tickets/{ticket_id}/status", json={"status": "geschlossen"})
    assert rejected.status_code == 409

    noted = api.post(f"/api/tickets/{ticket_id}/notes", json={"note": "Interne Sichtprüfung, keine Kundennachricht.", "changed_by": "Marco Keller"})
    assert noted.status_code == 200
    note = next(event for event in noted.json()["events"] if event["event_type"] == "note_added")
    assert note["note"].startswith("Interne Sichtprüfung")
    assert noted.json()["events"][0]["event_type"] == "created"

    task = api.post(
        f"/api/tickets/{ticket_id}/tasks",
        json={"title": "Beschädigte Lieferung prüfen und Ersatzlieferung mit Logistik abklären.", "due_at": "2026-12-01T09:00:00+00:00", "priority": "hoch"},
    )
    assert task.status_code == 201, task.text
    assert task.json()["ticket_id"] == ticket_id
    listed = api.get("/api/tickets", params={"partner_id": partner_id, "sort": "priority", "direction": "desc"})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1
    detail = api.get(f"/api/tickets/{ticket_id}")
    assert any(event["event_type"] == "task_created" for event in detail.json()["events"])
    assert detail.json()["tasks"][0]["title"].startswith("Beschädigte Lieferung prüfen")


def test_invalid_transition_close_and_reopen(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    ticket_id = api.post("/api/tickets", json=ticket_body(partner_id)).json()["id"]
    blocked = api.post(f"/api/tickets/{ticket_id}/status", json={"status": "warten_kunde"})
    assert blocked.status_code == 409

    resolved = api.post(f"/api/tickets/{ticket_id}/resolve", json={"code": "logistik", "note": "Mit Logistik besprochen. Kein ERP-Vorgang.", "changed_by": "Sandra Lutz"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "geloest"
    assert resolved.json()["resolutions"][0]["code"] == "logistik"

    closed = api.post(f"/api/tickets/{ticket_id}/close", json={"changed_by": "Sandra Lutz"})
    assert closed.status_code == 200
    assert closed.json()["status"] == "geschlossen"
    still_there = [event["event_type"] for event in closed.json()["events"]]
    assert still_there[0] == "created"
    assert "resolved" in still_there
    assert "closed" in still_there

    reopened = api.post(f"/api/tickets/{ticket_id}/reopen", json={"changed_by": "Sandra Lutz"})
    assert reopened.status_code == 200
    assert reopened.json()["status"] == "offen"
    assert any(event["event_type"] == "reopened" for event in reopened.json()["events"])


def test_upload_accepts_png_and_rejects_invalid(api: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ticket_upload_dir", str(tmp_path))
    monkeypatch.setattr(settings, "ticket_max_bytes", 32)
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    ticket_id = api.post("/api/tickets", json=ticket_body(partner_id)).json()["id"]

    rejected_type = api.post(f"/api/tickets/{ticket_id}/attachments", files={"file": ("notiz.txt", b"hello", "text/plain")})
    assert rejected_type.status_code == 422
    rejected_magic = api.post(f"/api/tickets/{ticket_id}/attachments", files={"file": ("foto.png", b"not-a-png", "image/png")})
    assert rejected_magic.status_code == 422
    too_large = api.post(f"/api/tickets/{ticket_id}/attachments", files={"file": ("foto.png", PNG + b"x" * 40, "image/png")})
    assert too_large.status_code == 413

    stored = api.post(f"/api/tickets/{ticket_id}/attachments", files={"file": ("schaden.png", PNG, "image/png")})
    assert stored.status_code == 201, stored.text
    attachment_id = stored.json()["id"]
    downloaded = api.get(f"/api/tickets/{ticket_id}/attachments/{attachment_id}")
    assert downloaded.status_code == 200
    assert downloaded.content.startswith(bytes.fromhex("89504e47"))
    removed = api.delete(f"/api/tickets/{ticket_id}/attachments/{attachment_id}")
    assert removed.status_code == 204
    missing = api.get(f"/api/tickets/{ticket_id}/attachments/{attachment_id}")
    assert missing.status_code == 404


def test_segments_and_cancelled_orders(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    restaurant_id = create_partner(api, suffix, "restaurant")
    hotel_id = create_partner(api, f"h{suffix[:7]}", "hotel")
    product_id = create_product(api, suffix)
    counted = create_order(api, restaurant_id, product_id, submit=True)
    cancelled = create_order(api, restaurant_id, product_id, submit=True)
    cancelled_status = api.post(f"/api/orders/{cancelled['id']}/status", json={"status": "storniert"})
    assert cancelled_status.status_code == 200

    analysis = api.get(f"/api/partners/{restaurant_id}/analysis")
    assert analysis.status_code == 200, analysis.text
    body = analysis.json()
    assert body["order_count"] == 1
    assert Decimal(body["order_volume"]) == Decimal(counted["gross_total"])
    assert Decimal(body["average_order_value"]) == Decimal(counted["gross_total"])
    assert "ERP" in body["volume_basis"]
    assert body["open_tickets"] == 0

    ticket = api.post("/api/tickets", json=ticket_body(restaurant_id, priority="kritisch"))
    assert ticket.status_code == 201
    again = api.get(f"/api/partners/{restaurant_id}/analysis")
    assert again.json()["open_tickets"] == 1
    assert again.json()["order_count"] == 1

    created = api.post(
        "/api/segments",
        json={
            "name": f"QA Segment {suffix}",
            "description": "Aktive Restaurants mit offenem Ticket.",
            "match_mode": "all",
            "conditions": [
                {"field_name": "partner_type", "operator": "eq", "value": "restaurant"},
                {"field_name": "status", "operator": "eq", "value": "aktiv"},
                {"field_name": "open_tickets", "operator": "gte", "value": "1"},
            ],
        },
    )
    assert created.status_code == 201, created.text
    segment_id = created.json()["id"]
    assert created.json()["partner_count"] >= 1
    partners = api.get(f"/api/segments/{segment_id}/partners")
    ids = {row["id"] for row in partners.json()}
    assert restaurant_id in ids
    assert hotel_id not in ids

    summary = api.get("/api/tickets/summary")
    assert summary.status_code == 200
    assert summary.json()["open_count"] >= 1
    assert summary.json()["critical_count"] >= 1
    assert summary.json()["duration_sample"] == 0 or summary.json()["average_hours"] is not None


def test_service_persists_in_postgresql(tmp_path: Path) -> None:
    suffix = uuid4().hex[:8]
    previous = settings.ticket_upload_dir
    settings.ticket_upload_dir = str(tmp_path)
    partner_id: str | None = None
    segment_id: str | None = None
    try:
        with TestClient(app) as client:
            partner_id = create_partner(client, suffix)
            created = client.post("/api/tickets", json=ticket_body(partner_id, subject="Persistenzprüfung"))
            assert created.status_code == 201
            ticket_id = created.json()["id"]
            uploaded = client.post(
                f"/api/tickets/{ticket_id}/attachments",
                files={"file": ("schaden.png", PNG, "image/png")},
            )
            assert uploaded.status_code == 201
            segment = client.post(
                "/api/segments",
                json={
                    "name": f"QA Persistenz {suffix}",
                    "match_mode": "all",
                    "conditions": [{"field_name": "partner_type", "operator": "eq", "value": "restaurant"}],
                },
            )
            assert segment.status_code == 201
            segment_id = segment.json()["id"]
        with SessionLocal() as session:
            stored = session.scalar(select(ServiceTicket).where(ServiceTicket.id == UUID(ticket_id)))
            assert stored is not None
            assert stored.subject == "Persistenzprüfung"
            event = session.scalar(select(TicketEvent).where(TicketEvent.ticket_id == stored.id))
            attachment = session.scalar(select(TicketAttachment).where(TicketAttachment.ticket_id == stored.id))
            assert event is not None and event.event_type == "created"
            assert attachment is not None
            assert (tmp_path / str(stored.id) / attachment.stored_name).is_file()
            saved_segment = session.get(CustomerSegment, UUID(segment_id))
            assert saved_segment is not None
    finally:
        settings.ticket_upload_dir = previous
        if partner_id is not None:
            with SessionLocal() as session:
                partner = session.get(Partner, UUID(partner_id))
                if partner is not None:
                    ticket_ids = select(ServiceTicket.id).where(ServiceTicket.partner_id == partner.id)
                    order_ids = select(Order.id).where(Order.partner_id == partner.id)
                    contact_ids = select(CompanyContact.contact_id).where(CompanyContact.partner_id == partner.id)
                    session.execute(delete(TicketEvent).where(TicketEvent.ticket_id.in_(ticket_ids)))
                    session.execute(delete(Task).where(Task.partner_id == partner.id))
                    session.execute(delete(TicketAttachment).where(TicketAttachment.ticket_id.in_(ticket_ids)))
                    session.execute(delete(TicketResolution).where(TicketResolution.ticket_id.in_(ticket_ids)))
                    session.execute(delete(TicketProduct).where(TicketProduct.ticket_id.in_(ticket_ids)))
                    session.execute(delete(ServiceTicket).where(ServiceTicket.partner_id == partner.id))
                    session.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
                    session.execute(delete(Order).where(Order.partner_id == partner.id))
                    session.execute(delete(DealStageHistory).where(DealStageHistory.deal_id.in_(select(Deal.id).where(Deal.partner_id == partner.id))))
                    session.execute(delete(Deal).where(Deal.partner_id == partner.id))
                    session.execute(delete(Product).where(Product.sku == f"QA-SV-{suffix}"))
                    session.execute(delete(CompanyContact).where(CompanyContact.partner_id == partner.id))
                    session.execute(delete(Contact).where(Contact.id.in_(contact_ids)))
                    session.execute(delete(Partner).where(Partner.id == partner.id))
                    session.commit()
        if segment_id is not None:
            with SessionLocal() as session:
                session.execute(delete(SegmentCondition).where(SegmentCondition.segment_id == UUID(segment_id)))
                session.execute(delete(CustomerSegment).where(CustomerSegment.id == UUID(segment_id)))
                session.commit()
