"""Mock-ERP integration tests.

The SQLite file is a separate test database. It is not a connection to a real ERP.
"""

from collections.abc import Iterator
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal, engine, get_db
from app.integrations.mock_erp import MockErpConnector
from app.main import app
from app.models.integration import ErpConflict, ErpSyncJob
from app.models.partner import Partner
from app.models.sales import Order, OrderItem, Product
from app.services.integration import run_due_integrations
from support import AuthClient, authenticated_client, login_session

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
def mock_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "mock.sqlite"
    monkeypatch.setattr(settings, "mock_erp_path", str(path))
    return path


@pytest.fixture()
def api(db_session: Session, mock_file: Path) -> Iterator[TestClient]:
    def override() -> Iterator[Session]:
        yield db_session

    app.dependency_overrides[get_db] = override
    with AuthClient(app) as client:
        login_session(client, db_session)
        yield client
    app.dependency_overrides.pop(get_db, None)


def _enable(api: TestClient) -> None:
    mode = api.post("/api/integration/mode", json={"mode": "mock"})
    assert mode.status_code == 200, mode.text


def test_mock_connection_and_external_mode_stays_locked(api: TestClient) -> None:
    _enable(api)
    tested = api.post("/api/integration/test")
    assert tested.status_code == 200, tested.text
    assert "Mock-ERP" in tested.json()["message"]
    assert "Keine echte ERP-Verbindung" in tested.json()["message"]
    blocked = api.post("/api/integration/mode", json={"mode": "extern"})
    assert blocked.status_code == 422
    status = api.get("/api/integration/status")
    assert status.json()["external_available"] is False
    assert status.json()["auto_order_transfer"] is False


def test_product_preview_does_not_change_prices(api: TestClient, db_session: Session) -> None:
    _enable(api)
    before = db_session.scalar(select(Product.list_price).where(Product.sku == "DEMO-SPEZ-50"))
    before_count = db_session.scalar(select(func.count()).select_from(Product).where(Product.sku == "MOCK-WEIZEN-50"))
    preview = api.post("/api/integration/preview", json={"kind": "produkte"})
    assert preview.status_code == 200, preview.text
    body = preview.json()
    assert body["dry_run"] is True
    listed = [*body["new"], *body["update"], *body["unchanged"]]
    assert any(row["external_key"] == "MOCK-WEIZEN-50" for row in listed)
    assert any(row["external_key"] == "MOCK-PREIS-NEG" for row in body["invalid"])
    after = db_session.scalar(select(Product.list_price).where(Product.sku == "DEMO-SPEZ-50"))
    assert before == after
    assert db_session.scalar(select(func.count()).select_from(Product).where(Product.sku == "MOCK-WEIZEN-50")) == before_count


def test_product_import_updates_catalogue_and_keeps_order_lines(api: TestClient, db_session: Session) -> None:
    _enable(api)
    line = db_session.scalar(select(OrderItem.unit_price).join(Order, Order.id == OrderItem.order_id).where(Order.order_number == "DEMO-BP-1001", OrderItem.sku == "DEMO-SPEZ-50"))
    assert line == Decimal("3.80")
    run = api.post("/api/integration/run", json={"kind": "produkte"})
    assert run.status_code == 200, run.text
    assert run.json()["failed_count"] >= 1
    db_session.expire_all()
    assert db_session.scalar(select(Product.list_price).where(Product.sku == "DEMO-SPEZ-50")) == Decimal("3.90")
    created = db_session.scalar(select(Product).where(Product.sku == "MOCK-WEIZEN-50"))
    assert created is not None and created.is_demo is True and created.erp_source == "mock"
    assert db_session.scalar(select(Product).where(Product.sku == "MOCK-PREIS-NEG")) is None
    assert db_session.scalar(select(OrderItem.unit_price).join(Order, Order.id == OrderItem.order_id).where(Order.order_number == "DEMO-BP-1001", OrderItem.sku == "DEMO-SPEZ-50")) == Decimal("3.80")
    second = api.post("/api/integration/run", json={"kind": "produkte"})
    assert second.status_code == 200
    db_session.expire_all()
    assert db_session.scalar(select(func_count(Product)).where(Product.sku == "MOCK-WEIZEN-50")) == 1


def func_count(model: type) -> object:
    from sqlalchemy import func

    return func.count(model.id)


def test_customers_import_once_and_keep_conflicting_number(api: TestClient, db_session: Session) -> None:
    _enable(api)
    first = api.post("/api/integration/run", json={"kind": "kunden"})
    assert first.status_code == 200, first.text
    second = api.post("/api/integration/run", json={"kind": "kunden"})
    assert second.status_code == 200, second.text
    db_session.expire_all()
    created = db_session.scalars(select(Partner).where(Partner.company_name == "Gasthaus Mockstein")).all()
    assert len(created) == 1
    assert created[0].is_demo is True
    assert created[0].status == "potenziell"
    assert "Mock-ERP" in (created[0].notes or "")
    hotel = db_session.scalar(select(Partner).where(Partner.company_name == "Hotel Alpenblick", Partner.archived_at.is_(None)))
    assert hotel is not None
    assert hotel.erp_customer_number == "DEMO-1002"
    conflict = db_session.scalar(select(ErpConflict).where(ErpConflict.external_key == "MOCK-ALPEN", ErpConflict.status == "offen"))
    assert conflict is not None
    lago = db_session.scalar(select(Partner).where(Partner.demo_key == "demo-ristorante-lago"))
    assert lago is not None and lago.erp_customer_number == "10457"
    assert "Testdatensatz" in (lago.notes or "")


def test_order_transfer_is_idempotent_and_status_stays_separate(api: TestClient, db_session: Session, mock_file: Path) -> None:
    _enable(api)
    suffix = uuid4().hex[:8]
    partner = api.post(
        "/api/partners",
        json={
            "company_name": f"QA ERP {suffix}",
            "erp_customer_number": f"QA-{suffix[:6]}",
            "partner_type": "restaurant",
            "country": "Liechtenstein",
            "status": "aktiv",
            "priority": "normal",
        },
    )
    assert partner.status_code == 201, partner.text
    product = api.post(
        "/api/products",
        json={
            "sku": f"QA-ERP-{suffix}",
            "name": "QA Bier",
            "category": "bier",
            "container_type": "flasche",
            "sales_unit": "Flasche",
            "list_price": "2.00",
            "vat_rate": "8.10",
            "is_active": True,
        },
    )
    assert product.status_code == 201, product.text
    order = api.post(
        "/api/orders",
        json={
            "partner_id": partner.json()["id"],
            "ordered_on": "2026-11-12",
            "items": [{"product_id": product.json()["id"], "quantity": "2"}],
            "submit": True,
        },
    )
    assert order.status_code == 201, order.text
    order_id = order.json()["id"]
    crm_status = order.json()["status"]
    prepared = api.post(f"/api/integration/orders/{order_id}/prepare")
    assert prepared.status_code == 200, prepared.text
    sent = api.post(f"/api/integration/orders/{order_id}/transfer")
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "erfolgreich"
    reference = sent.json()["external_reference"]
    assert reference.startswith("MOCK-AUF-")
    again = api.post(f"/api/integration/orders/{order_id}/transfer")
    assert again.status_code == 200
    assert again.json()["external_reference"] == reference
    assert MockErpConnector(str(mock_file)).order_count() == 1
    stored = db_session.get(Order, UUID(order_id))
    assert stored is not None and stored.status == crm_status
    advanced = api.post(f"/api/integration/orders/{order_id}/advance")
    assert advanced.status_code == 200, advanced.text
    assert advanced.json()["erp_status"] == "bestaetigt"
    assert advanced.json()["status"] == crm_status
    assert advanced.json()["erp_status_source"] == "mock"
    refreshed = api.post(f"/api/integration/orders/{order_id}/status")
    assert refreshed.status_code == 200
    assert refreshed.json()["erp_status"] == "bestaetigt"


def test_ambiguous_response_is_not_sent_again(api: TestClient, mock_file: Path) -> None:
    _enable(api)
    suffix = uuid4().hex[:8]
    partner = api.post("/api/partners", json={"company_name": f"QA Unklar {suffix}", "erp_customer_number": f"QU-{suffix[:6]}", "partner_type": "bar", "country": "Schweiz", "status": "aktiv", "priority": "normal"})
    product = api.post("/api/products", json={"sku": f"QA-UNKLAR-{suffix}", "name": "QA", "category": "bier", "container_type": "flasche", "sales_unit": "Flasche", "list_price": "2.00", "vat_rate": "8.10", "is_active": True})
    order = api.post("/api/orders", json={"partner_id": partner.json()["id"], "ordered_on": "2026-11-12", "items": [{"product_id": product.json()["id"], "quantity": "1"}], "submit": True})
    order_id = order.json()["id"]
    assert api.post(f"/api/integration/orders/{order_id}/prepare").status_code == 200
    MockErpConnector(str(mock_file)).arm("ambiguous", 1)
    sent = api.post(f"/api/integration/orders/{order_id}/transfer")
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "manuelle_pruefung"
    assert MockErpConnector(str(mock_file)).order_count() == 0
    blocked = api.post(f"/api/integration/orders/{order_id}/transfer")
    assert blocked.status_code == 409
    checked = api.post(f"/api/integration/orders/{order_id}/recheck")
    assert checked.status_code == 200
    assert checked.json()["status"] == "manuelle_pruefung"
    assert MockErpConnector(str(mock_file)).order_count() == 0


def test_technical_retries_are_limited(api: TestClient, mock_file: Path, db_session: Session) -> None:
    _enable(api)
    suffix = uuid4().hex[:8]
    partner = api.post("/api/partners", json={"company_name": f"QA Fehler {suffix}", "erp_customer_number": f"QF-{suffix[:6]}", "partner_type": "bar", "country": "Schweiz", "status": "aktiv", "priority": "normal"})
    product = api.post("/api/products", json={"sku": f"QA-FEHLER-{suffix}", "name": "QA", "category": "bier", "container_type": "flasche", "sales_unit": "Flasche", "list_price": "2.00", "vat_rate": "8.10", "is_active": True})
    order = api.post("/api/orders", json={"partner_id": partner.json()["id"], "ordered_on": "2026-11-12", "items": [{"product_id": product.json()["id"], "quantity": "1"}], "submit": True})
    order_id = order.json()["id"]
    assert api.post(f"/api/integration/orders/{order_id}/prepare").status_code == 200
    MockErpConnector(str(mock_file)).arm("error", 5)
    sent = api.post(f"/api/integration/orders/{order_id}/transfer")
    assert sent.status_code == 200, sent.text
    assert sent.json()["status"] == "fehlgeschlagen"
    assert sent.json()["attempts"] == 3
    assert MockErpConnector(str(mock_file)).order_count() == 0
    job = db_session.scalar(select(ErpSyncJob).where(ErpSyncJob.kind == "uebertragung", ErpSyncJob.status == "fehlgeschlagen"))
    assert job is not None
    assert "abgelehnt" in job.message


def test_permissions(api: TestClient, db_session: Session) -> None:
    login_session(api, db_session, role="vertrieb", email="pytest-vertrieb-erp@example.invalid", first="Vera", last="Trieb")
    assert api.get("/api/integration/status").status_code == 403
    assert api.post("/api/integration/run", json={"kind": "produkte"}).status_code == 403
    assert api.get("/api/partners").status_code == 200
    login_session(api, db_session, role="geschaeftsleitung", email="pytest-gl-erp@example.invalid", first="Gesa", last="Leitung")
    assert api.get("/api/integration/status").status_code == 200
    assert api.post("/api/integration/run", json={"kind": "produkte"}).status_code == 403


def test_background_interval_runs_without_a_browser(api: TestClient, db_session: Session) -> None:
    _enable(api)
    saved = api.put("/api/integration/intervals", json={"customers_interval_minutes": 0, "products_interval_minutes": 1, "status_interval_minutes": 0})
    assert saved.status_code == 200, saved.text
    from app.models.integration import ErpConnection

    connection = db_session.scalar(select(ErpConnection).limit(1))
    assert connection is not None
    connection.last_products_at = None
    db_session.flush()
    ran = run_due_integrations(db_session)
    assert ran == 1, (connection.mode, connection.products_interval_minutes, connection.last_products_at, connection.running_kind)
    job = db_session.scalar(select(ErpSyncJob).where(ErpSyncJob.kind == "produkte"))
    assert job is not None


def test_sync_persists_after_a_new_session(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(settings, "mock_erp_path", str(tmp_path / "persist.sqlite"))
    job_id: str | None = None
    with SessionLocal() as session:
        spezial = session.scalar(select(Product).where(Product.sku == "DEMO-SPEZ-50"))
        previous_price = None if spezial is None else spezial.list_price
        previous_source = None if spezial is None else spezial.erp_source
        previous_synced = None if spezial is None else spezial.erp_synced_at
        from app.models.integration import ErpConnection

        connection = session.scalar(select(ErpConnection).limit(1))
        previous_mode = None if connection is None else connection.mode
        previous_products_at = None if connection is None else connection.last_products_at
    try:
        with authenticated_client() as client:
            assert client.post("/api/integration/mode", json={"mode": "mock"}).status_code == 200
            run = client.post("/api/integration/run", json={"kind": "produkte"})
            assert run.status_code == 200, run.text
            job_id = run.json()["id"]
        with SessionLocal() as session:
            job = session.get(ErpSyncJob, UUID(job_id))
            assert job is not None and job.status in {"erfolgreich", "teilweise"}
            assert session.scalar(select(func.count()).select_from(ErpSyncJob).where(ErpSyncJob.id == UUID(job_id))) == 1
    finally:
        with SessionLocal() as session:
            if job_id is not None:
                from app.models.integration import ErpSyncRecord

                session.execute(ErpSyncRecord.__table__.delete().where(ErpSyncRecord.job_id == UUID(job_id)))
                job = session.get(ErpSyncJob, UUID(job_id))
                if job is not None:
                    session.delete(job)
            spezial = session.scalar(select(Product).where(Product.sku == "DEMO-SPEZ-50"))
            if spezial is not None and previous_price is not None:
                spezial.list_price = previous_price
                spezial.erp_source = previous_source
                spezial.erp_synced_at = previous_synced
            from app.models.integration import ErpConnection

            connection = session.scalar(select(ErpConnection).limit(1))
            if connection is not None and previous_mode is not None:
                connection.mode = previous_mode
                connection.last_products_at = previous_products_at
                connection.running_kind = None
                connection.running_since = None
            session.commit()
