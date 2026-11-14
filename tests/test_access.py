"""Reporting, authentication and permission tests."""

from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.main import app
from app.models.identity import AuditLog, PasswordReset
from app.services.identity import confirm_reset, start_reset
from support import PASSWORD, AuthClient, login_session

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def migrated_database() -> None:
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    command.upgrade(config, "head")


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
    def override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override
    with AuthClient(app) as client:
        login_session(client, db_session)
        yield client
    app.dependency_overrides.pop(get_db, None)


def partner_body(suffix: str, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "company_name": f"QA Bericht {suffix}",
        "erp_customer_number": f"QB-{suffix}",
        "partner_type": "restaurant",
        "industry": "Gastronomie",
        "street": "Testweg 1",
        "postal_code": "9490",
        "city": "Vaduz",
        "region": "Liechtenstein",
        "country": "Liechtenstein",
        "status": "aktiv",
        "account_owner": f"QA Person {suffix}",
        "priority": "normal",
    }
    body.update(overrides)
    return body


def test_report_uses_stored_lines_and_excludes_cancelled(api: TestClient, db_session: Session) -> None:
    day = date.today().isoformat()
    previous = (date.today() - timedelta(days=1)).isoformat()
    suffix = uuid4().hex[:8]
    partner = api.post("/api/partners", json=partner_body(suffix))
    assert partner.status_code == 201, partner.text
    partner_id = partner.json()["id"]
    product = api.post(
        "/api/products",
        json={
            "sku": f"QB-{suffix}",
            "name": f"Testbier {suffix}",
            "category": "bier",
            "container_type": "flasche",
            "list_price": "10.00",
            "vat_rate": "0.00",
            "is_active": True,
        },
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    counted = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "ordered_on": day,
            "items": [{"product_id": product_id, "quantity": "2"}],
            "submit": True,
        },
    )
    assert counted.status_code == 201, counted.text
    assert counted.json()["gross_total"] == "20.00"
    cancelled = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "ordered_on": day,
            "items": [{"product_id": product_id, "quantity": "4"}],
            "submit": True,
        },
    )
    assert cancelled.status_code == 201, cancelled.text
    stopped = api.post(f"/api/orders/{cancelled.json()['id']}/status", json={"status": "storniert"})
    assert stopped.status_code == 200, stopped.text
    draft = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "ordered_on": day,
            "items": [{"product_id": product_id, "quantity": "9"}],
        },
    )
    assert draft.status_code == 201, draft.text
    assert draft.json()["status"] == "entwurf"
    won = api.post(
        "/api/deals",
        json={
            "title": f"Gewinn {suffix}",
            "partner_id": partner_id,
            "account_owner": f"QA Person {suffix}",
            "estimated_value": "100.00",
            "stage": "neuer_lead",
            "priority": "normal",
        },
    )
    lost = api.post(
        "/api/deals",
        json={
            "title": f"Verlust {suffix}",
            "partner_id": partner_id,
            "account_owner": f"QA Person {suffix}",
            "estimated_value": "80.00",
            "stage": "neuer_lead",
            "priority": "normal",
        },
    )
    assert api.post(f"/api/deals/{won.json()['id']}/win", json={"closed_on": day}).status_code == 200
    assert api.post(
        f"/api/deals/{lost.json()['id']}/lose",
        json={"loss_reason": "Kein Bedarf", "closed_on": day},
    ).status_code == 200
    report = api.get("/api/reports", params={"partner_id": partner_id, "date_from": day, "date_to": day})
    assert report.status_code == 200, report.text
    body = report.json()
    figures = {item["key"]: item["value"] for item in body["kpis"] if item["section"] == "overview"}
    assert figures["order_volume"] == "20.00"
    assert figures["order_count"] == "1"
    assert figures["average_order"] == "20.00"
    assert figures["won_deals"] == "1"
    assert figures["close_rate"] == "50.0"
    sales = {item["key"]: item["value"] for item in body["kpis"] if item["section"] == "sales"}
    assert sales["lost_deals"] == "1"
    assert sales["won_deals"] == "1"
    orders = {item["key"]: item["value"] for item in body["kpis"] if item["section"] == "orders"}
    assert orders["cancelled"] == "1"
    assert "ERP" in body["source"] or "kein fakturierter" in body["source"]
    assert any("Öffnungs" in note or "Tracking" in note for note in body["notices"])
    earlier = api.get("/api/reports", params={"partner_id": partner_id, "date_from": previous, "date_to": previous})
    earlier_figures = {item["key"]: item["value"] for item in earlier.json()["kpis"] if item["section"] == "overview"}
    assert earlier_figures["order_volume"] == "0.00"
    assert earlier_figures["order_count"] == "0"
    assert earlier_figures["won_deals"] == "0"
    assert earlier_figures["close_rate"] is None


def test_exports_contain_filtered_rows_and_block_other_roles(api: TestClient, db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    partner = api.post("/api/partners", json=partner_body(suffix, company_name=f"Export Haus {suffix}"))
    partner_id = partner.json()["id"]
    created = api.post(
        "/api/users",
        json={
            "first_name": "Nina",
            "last_name": f"Berger{suffix[:4]}",
            "email": f"nina-{suffix}@example.invalid",
            "role_code": "vertrieb",
            "password": "Vertrieb-Passwort-12",
        },
    )
    assert created.status_code == 201, created.text
    params = {"partner_id": partner_id, "date_from": "2026-11-01", "date_to": "2026-11-30", "section": "partners"}
    csv_file = api.post("/api/reports/export", params={**params, "export_format": "csv"})
    assert csv_file.status_code == 200, csv_file.text
    assert f"Export Haus {suffix}".encode() in csv_file.content
    workbook = api.post("/api/reports/export", params={**params, "export_format": "xlsx"})
    assert workbook.status_code == 200
    assert workbook.content[:2] == b"PK"
    pdf = api.post("/api/reports/export", params={**params, "export_format": "pdf"})
    assert pdf.status_code == 200
    assert pdf.content.startswith(b"%PDF")
    assert b"Diagramme sind als Wertetabellen" in pdf.content
    sales = AuthClient(app)
    logged = sales.post("/api/auth/login", json={"email": f"nina-{suffix}@example.invalid", "password": "Vertrieb-Passwort-12"})
    assert logged.status_code == 200, logged.text
    denied = sales.post("/api/reports/export", params={**params, "export_format": "csv"})
    assert denied.status_code == 403
    denied_users = sales.get("/api/users")
    assert denied_users.status_code == 403
    assert sales.get("/api/partners").status_code == 200
    assert sales.get("/api/deals").status_code == 200
    audit_rows = api.get("/api/audit").json()["items"]
    assert any(row["event_type"] == "data_export" and row["result"] == "erfolg" for row in audit_rows)
    assert any(row["event_type"] == "data_export" and row["result"] == "abgelehnt" for row in audit_rows)
    assert all("Vertrieb-Passwort-12" not in (row["detail"] or "") for row in audit_rows)


def test_login_password_reset_and_session(api: TestClient, db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    email = f"konto-{suffix}@example.invalid"
    created = api.post(
        "/api/users",
        json={
            "first_name": "Omar",
            "last_name": "Test",
            "email": email,
            "role_code": "kundenservice",
            "password": "Service-Passwort-12",
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]
    anonymous = TestClient(app)
    assert anonymous.get("/api/partners").status_code == 401
    assert anonymous.get("/api/health").status_code == 200
    wrong = anonymous.post("/api/auth/login", json={"email": email, "password": "falsch-falsch-falsch"})
    assert wrong.status_code == 401
    assert wrong.json()["detail"] == "Anmeldung abgelehnt."
    unknown = anonymous.post("/api/auth/login", json={"email": f"niemand-{suffix}@example.invalid", "password": "falsch-falsch-falsch"})
    assert unknown.status_code == 401
    assert unknown.json()["detail"] == wrong.json()["detail"]
    client = AuthClient(app)
    logged = client.post("/api/auth/login", json={"email": email, "password": "Service-Passwort-12"})
    assert logged.status_code == 200
    assert logged.json()["user"]["role_code"] == "kundenservice"
    assert client.get("/api/auth/me").status_code == 200
    assert client.get("/api/tickets").status_code == 200
    assert client.get("/api/users").status_code == 403
    changed = client.post("/api/auth/password", json={"current_password": "Service-Passwort-12", "new_password": "Neues-Passwort-12"})
    assert changed.status_code == 204, changed.text
    assert client.get("/api/auth/me").status_code == 401
    old = client.post("/api/auth/login", json={"email": email, "password": "Service-Passwort-12"})
    assert old.status_code == 401
    again = client.post("/api/auth/login", json={"email": email, "password": "Neues-Passwort-12"})
    assert again.status_code == 200
    raw_cookie = client.cookies.get("bp_session")
    assert client.post("/api/auth/logout").status_code == 204
    assert client.get("/api/auth/me").status_code == 401
    client.cookies.set("bp_session", raw_cookie)
    assert client.get("/api/auth/me").status_code == 401
    blocked = api.post(f"/api/users/{user_id}/status", json={"status": "deaktiviert"})
    assert blocked.status_code == 200
    disabled = client.post("/api/auth/login", json={"email": email, "password": "Neues-Passwort-12"})
    assert disabled.status_code == 403
    assert disabled.json()["detail"] == "Dieses Konto ist deaktiviert."
    request = anonymous.post("/api/auth/password-reset/request", json={"email": email})
    assert request.status_code == 202
    assert "eyJ" not in request.text
    assert len(request.json()["detail"]) < 400
    assert db_session.scalar(select(PasswordReset).where(PasswordReset.user_id == user_id)) is None
    api.post(f"/api/users/{user_id}/status", json={"status": "aktiv"})
    raw = start_reset(db_session, email)
    assert raw
    stored = db_session.scalar(select(PasswordReset).where(PasswordReset.user_id == user_id))
    assert stored is not None
    assert stored.token_hash != raw
    confirm_reset(db_session, raw, "Reset-Passwort-12")
    try:
        confirm_reset(db_session, raw, "Nochmals-Passwort-12")
        raise AssertionError("Das Token war ein zweites Mal gültig.")
    except Exception as error:
        assert getattr(error, "status", None) == 400
    expired = start_reset(db_session, email)
    row = db_session.scalars(select(PasswordReset).where(PasswordReset.user_id == user_id).order_by(PasswordReset.created_at.desc())).first()
    assert row is not None and expired
    row.expires_at = row.created_at - timedelta(minutes=1)
    db_session.flush()
    try:
        confirm_reset(db_session, expired, "Spaeter-Passwort-12")
        raise AssertionError("Ein abgelaufenes Token wurde akzeptiert.")
    except Exception as error:
        assert getattr(error, "status", None) == 400
    fresh = start_reset(db_session, email)
    assert fresh
    confirmed = anonymous.post("/api/auth/password-reset/confirm", json={"token": fresh, "new_password": "Abschluss-Passwort-12"})
    assert confirmed.status_code == 204, confirmed.text
    assert "Abschluss-Passwort-12" not in confirmed.text
    audit_text = " ".join((row.detail or "") + row.event_type for row in db_session.scalars(select(AuditLog)).all())
    assert "Abschluss-Passwort-12" not in audit_text
    assert fresh not in audit_text
    for _ in range(5):
        assert anonymous.post("/api/auth/login", json={"email": email, "password": "immer-falsch-00"}).status_code == 401
    locked = anonymous.post("/api/auth/login", json={"email": email, "password": "Abschluss-Passwort-12"})
    assert locked.status_code == 401
    csrf = AuthClient(app)
    logged = csrf.post("/api/auth/login", json={"email": "pytest-admin@example.invalid", "password": PASSWORD})
    assert logged.status_code == 200
    plain = TestClient(app)
    plain.cookies.set("bp_session", csrf.cookies.get("bp_session"))
    plain.cookies.set("bp_csrf", csrf.cookies.get("bp_csrf"))
    assert plain.post("/api/partners", json=partner_body(uuid4().hex[:8])).status_code == 403


def test_role_assignment_and_existing_modules(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    created = api.post(
        "/api/users",
        json={
            "first_name": "Mia",
            "last_name": "Verkauf",
            "email": f"mia-{suffix}@example.invalid",
            "role_code": "marketing",
            "password": "Marketing-Passwort-12",
        },
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]
    updated = api.put(
        f"/api/users/{user_id}",
        json={
            "first_name": "Mia",
            "last_name": "Verkauf",
            "email": f"mia-{suffix}@example.invalid",
            "role_code": "vertrieb",
        },
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["role_code"] == "vertrieb"
    assert api.get("/api/partners").status_code == 200
    assert api.get("/api/deals").status_code == 200
    assert api.get("/api/orders").status_code == 200
    assert api.get("/api/campaigns").status_code == 200
    today = date.today().isoformat()
    report = api.get("/api/reports", params={"date_from": today, "date_to": today, "section": "overview"})
    assert report.status_code == 200, report.text
    assert report.json()["period_from"] == today
