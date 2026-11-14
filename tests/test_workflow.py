"""One CRM workflow through the HTTP API.

The database transaction rolls back at the end. The mock ERP file is temporary.
"""

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import engine, get_db
from app.main import app
from app.models.engagement import AutomationRule
from support import PASSWORD, AuthClient, login_session

ROOT = Path(__file__).resolve().parents[1]


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
def api(db_session: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    monkeypatch.setattr(settings, "mock_erp_path", str(tmp_path / "workflow-mock.sqlite"))

    def override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override
    with AuthClient(app) as client:
        login_session(client, db_session)
        yield client
    app.dependency_overrides.pop(get_db, None)


def test_demo_workflow_from_partner_to_mock_erp(api: TestClient, db_session: Session) -> None:
    for row in db_session.scalars(select(AutomationRule).where(AutomationRule.trigger_type == "deal_created", AutomationRule.status == "aktiv")).all():
        row.status = "pausiert"
    db_session.flush()
    suffix = uuid4().hex[:8]

    partner = api.post(
        "/api/partners",
        json={
            "company_name": f"QA Ablauf {suffix}",
            "erp_customer_number": f"AB-{suffix[:6]}",
            "partner_type": "restaurant",
            "city": "Vaduz",
            "country": "Liechtenstein",
            "status": "aktiv",
            "priority": "normal",
            "account_owner": "Sandra Lutz",
            "notes": "Automatisierter Ablauf, keine echte Kundenbeziehung.",
        },
    )
    assert partner.status_code == 201, partner.text
    partner_id = partner.json()["id"]
    found = api.get("/api/partners", params={"q": f"QA Ablauf {suffix}"})
    assert found.status_code == 200 and found.json()["total"] == 1

    contact = api.post(
        "/api/contacts",
        json={
            "first_name": "Giulia",
            "last_name": f"Ablauf {suffix}",
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
    assert contact.status_code == 201, contact.text
    contact_id = contact.json()["id"]

    activity = api.post(
        "/api/activities",
        json={
            "activity_type": "telefonat",
            "title": f"Kundengespräch {suffix}",
            "description": "Fiktives Gespräch im automatisierten Ablauf.",
            "occurred_at": "2026-11-12T09:00:00+01:00",
            "account_owner": "Sandra Lutz",
            "contact_id": contact_id,
            "partner_id": partner_id,
        },
    )
    assert activity.status_code == 201, activity.text

    task = api.post(
        "/api/tasks",
        json={
            "title": f"Reklamation abklären {suffix}",
            "description": "Mit der Logistik sprechen.",
            "due_at": "2026-11-20T09:00:00+01:00",
            "priority": "hoch",
            "status": "offen",
            "task_type": "intern",
            "account_owner": "Sandra Lutz",
            "partner_id": partner_id,
            "contact_id": contact_id,
        },
    )
    assert task.status_code == 201, task.text
    task_id = task.json()["id"]
    moved = api.put(
        f"/api/tasks/{task_id}",
        json={
            "title": f"Reklamation abklären {suffix}",
            "account_owner": "Marco Keller",
            "due_at": "2026-11-21T09:00:00+01:00",
            "priority": "hoch",
            "status": "offen",
            "task_type": "intern",
            "partner_id": partner_id,
            "contact_id": contact_id,
        },
    )
    assert moved.status_code == 200, moved.text
    done = api.post(f"/api/tasks/{task_id}/complete")
    assert done.status_code == 200, done.text

    rule = api.post(
        "/api/automations",
        json={
            "name": f"Ablauf Erstkontakt {suffix}",
            "trigger_type": "deal_created",
            "action_type": "create_task",
            "action_config": {"title": f"Folgeaufgabe {suffix}", "due_days": 2, "priority": "normal"},
            "account_owner": "Sandra Lutz",
        },
    )
    assert rule.status_code == 201, rule.text
    assert api.post(f"/api/automations/{rule.json()['id']}/status", json={"status": "aktiv"}).status_code == 200

    deal = api.post(
        "/api/deals",
        json={
            "title": f"Erweiterung {suffix}",
            "partner_id": partner_id,
            "contact_id": contact_id,
            "account_owner": "Sandra Lutz",
            "estimated_value": "120.00",
            "expected_close_on": "2026-12-15",
            "stage": "neuer_lead",
            "priority": "hoch",
            "description": "Automatisierter Ablauf.",
        },
    )
    assert deal.status_code == 201, deal.text
    deal_id = deal.json()["id"]
    stage = api.post(f"/api/deals/{deal_id}/stage", json={"stage": "angebot"})
    assert stage.status_code == 200, stage.text
    assert stage.json()["stage"] == "angebot"
    assert any(row["to_stage"] == "angebot" for row in stage.json()["history"])
    follow_up = api.get("/api/tasks", params={"partner_id": partner_id, "q": f"Folgeaufgabe {suffix}"})
    assert follow_up.json()["total"] == 1
    notices = api.get("/api/notifications", params={"empfaenger": "Sandra Lutz"})
    assert notices.status_code == 200, notices.text

    product = api.post(
        "/api/products",
        json={
            "sku": f"QA-AB-{suffix}",
            "name": "Ablaufbier",
            "category": "bier",
            "container_type": "flasche",
            "sales_unit": "Flasche",
            "list_price": "2.40",
            "vat_rate": "8.10",
            "is_active": True,
        },
    )
    assert product.status_code == 201, product.text
    order = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "contact_id": contact_id,
            "deal_id": deal_id,
            "ordered_on": "2026-11-12",
            "items": [{"product_id": product.json()["id"], "quantity": "2"}],
            "submit": True,
            "notes": "Automatisierter Ablauf, keine echte Bestellung.",
        },
    )
    assert order.status_code == 201, order.text
    order_body = order.json()
    assert Decimal(order_body["net_total"]) == Decimal("4.80")
    assert Decimal(order_body["gross_total"]) > Decimal(order_body["net_total"])
    assert order_body["items"][0]["unit_price"] == "2.40"
    order_id = order_body["id"]

    ticket = api.post(
        "/api/tickets",
        json={
            "subject": f"Beschädigte Lieferung {suffix}",
            "category": "beschaedigte_lieferung",
            "description": "Fiktive Reklamation im Ablauf.",
            "partner_id": partner_id,
            "contact_id": contact_id,
            "order_id": order_id,
            "priority": "hoch",
        },
    )
    assert ticket.status_code == 201, ticket.text
    ticket_id = ticket.json()["id"]
    assert api.post(f"/api/tickets/{ticket_id}/status", json={"status": "in_bearbeitung", "changed_by": "Marco Keller"}).status_code == 200
    assert api.post(f"/api/tickets/{ticket_id}/notes", json={"note": "Mit der Logistik besprochen.", "changed_by": "Marco Keller"}).status_code == 200
    assert api.post(f"/api/tickets/{ticket_id}/resolve", json={"code": "logistik", "note": "Ersatz im Ablauf vermerkt.", "changed_by": "Sandra Lutz"}).status_code == 200
    closed = api.post(f"/api/tickets/{ticket_id}/close", json={"changed_by": "Sandra Lutz"})
    assert closed.status_code == 200, closed.text
    assert closed.json()["status"] == "geschlossen"
    assert len(api.get(f"/api/tickets/{ticket_id}").json()["events"]) >= 2

    campaign = api.post(
        "/api/campaigns",
        json={
            "name": f"Winterprobe {suffix}",
            "description": "Entwurf im Ablauf",
            "campaign_type": "saisonal",
            "account_owner": "Sandra Lutz",
            "starts_on": "2026-12-01",
            "ends_on": "2027-02-28",
            "objective": "Saison vorstellen",
            "audience_kind": "contacts",
            "channel": "telefon",
            "budget": "100.00",
        },
    )
    assert campaign.status_code == 201, campaign.text
    campaign_id = campaign.json()["id"]
    assert api.post(f"/api/campaigns/{campaign_id}/audience", json={"contact_id": contact_id}).status_code == 201

    report = api.get("/api/reports", params={"date_from": "2026-11-01", "date_to": "2026-11-30", "section": "orders"})
    assert report.status_code == 200, report.text
    exported = api.post("/api/reports/export", params={"date_from": "2026-11-01", "date_to": "2026-11-30", "section": "orders", "export_format": "csv"})
    assert exported.status_code == 200, exported.text
    assert "text/csv" in exported.headers["content-type"] or exported.content.startswith(b"\xef\xbb\xbf") or b"," in exported.content or b";" in exported.content

    assert api.post("/api/integration/mode", json={"mode": "mock"}).status_code == 200
    assert api.post(f"/api/integration/orders/{order_id}/prepare").status_code == 200
    sent = api.post(f"/api/integration/orders/{order_id}/transfer")
    assert sent.status_code == 200, sent.text
    assert sent.json()["external_reference"].startswith("MOCK-AUF-")
    refreshed = api.post(f"/api/integration/orders/{order_id}/status")
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["status"] == "eingereicht"
    assert refreshed.json()["erp_status"] == "empfangen"
    assert refreshed.json()["erp_status_source"] == "mock"

    assert api.post("/api/auth/logout").status_code == 204
    assert api.get(f"/api/partners/{partner_id}").status_code == 401
    again = api.post("/api/auth/login", json={"email": "pytest-admin@example.invalid", "password": PASSWORD})
    assert again.status_code == 200, again.text
    stored = api.get(f"/api/partners/{partner_id}")
    assert stored.status_code == 200
    assert stored.json()["company_name"] == f"QA Ablauf {suffix}"
    assert api.get(f"/api/orders/{order_id}").json()["erp_reference"].startswith("MOCK-AUF-")


def test_roles_are_enforced_on_the_api(api: TestClient, db_session: Session) -> None:
    assert api.get("/api/users").status_code == 200
    checks = (
        ("geschaeftsleitung", "Gesa", "Leitung", "/api/integration/status", "GET", 200),
        ("vertrieb", "Vera", "Trieb", "/api/users", "GET", 403),
        ("marketing", "Mia", "Markt", "/api/orders", "POST", 403),
        ("kundenservice", "Marco", "Service", "/api/deals", "POST", 403),
    )
    for role, first, last, path, method, expected in checks:
        email = f"pytest-{role}-ablauf@example.invalid"
        login_session(api, db_session, role=role, email=email, first=first, last=last)
        response = api.request(method, path, json={})
        assert response.status_code == expected, (role, response.status_code, response.text)
