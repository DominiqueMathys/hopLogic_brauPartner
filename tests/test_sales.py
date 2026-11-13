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

from app.database import SessionLocal, engine, get_db
from app.main import app
from app.models.contact import CompanyContact, Contact
from app.models.partner import Partner
from app.models.sales import Deal, DealStageHistory, Order, OrderItem, Product
from app.services.money import line_amounts

ROOT = Path(__file__).resolve().parents[1]


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


def partner_body(suffix: str) -> dict[str, object]:
    return {
        "company_name": f"QA Verkauf {suffix}",
        "erp_customer_number": f"VK-{suffix}",
        "partner_type": "restaurant",
        "city": f"Orts{suffix}",
        "country": "Liechtenstein",
        "status": "aktiv",
        "priority": "normal",
        "account_owner": "QA Betreuung",
    }


def contact_body(suffix: str, partner_id: str) -> dict[str, object]:
    return {
        "first_name": "Giulia",
        "last_name": f"Verkauf {suffix}",
        "account_owner": "Sandra Lutz",
        "preferred_language": "de",
        "preferred_channel": "telefon",
        "lifecycle_phase": "kunde",
        "lead_status": "keiner",
        "status": "aktiv",
        "processing_basis": "nicht_dokumentiert",
        "companies": [{"partner_id": partner_id, "is_primary": True}],
    }


def product_body(suffix: str, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "sku": f"QA-{suffix}",
        "name": f"Lagerbier Test {suffix}",
        "category": "bier",
        "description": "Testartikel, kein offizielles Sortiment.",
        "container_type": "flasche",
        "container_size": "33 cl",
        "sales_unit": "Flasche",
        "list_price": "2.40",
        "vat_rate": "8.10",
        "is_active": True,
    }
    body.update(overrides)
    return body


def deal_body(partner_id: str, contact_id: str | None = None, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "title": "Erweiterung des Biersortiments",
        "partner_id": partner_id,
        "contact_id": contact_id,
        "account_owner": "Sandra Lutz",
        "estimated_value": "4800.00",
        "expected_close_on": "2026-12-15",
        "stage": "neuer_lead",
        "priority": "hoch",
        "description": "Automatisierter Test",
    }
    body.update(overrides)
    return body


def create_partner(api: TestClient, suffix: str) -> str:
    response = api.post("/api/partners", json=partner_body(suffix))
    assert response.status_code == 201
    return response.json()["id"]


def create_contact(api: TestClient, suffix: str, partner_id: str) -> str:
    response = api.post("/api/contacts", json=contact_body(suffix, partner_id))
    assert response.status_code == 201
    return response.json()["id"]


def create_product(api: TestClient, suffix: str, **overrides: object) -> str:
    response = api.post("/api/products", json=product_body(suffix, **overrides))
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_create_and_edit_deal(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    contact_id = create_contact(api, suffix, partner_id)
    created = api.post("/api/deals", json=deal_body(partner_id, contact_id))
    assert created.status_code == 201
    body = created.json()
    assert body["stage"] == "neuer_lead"
    assert body["probability"] == "10.00"
    assert body["company_name"].startswith("QA Verkauf")
    assert body["contact_name"].startswith("Giulia")
    assert body["is_overdue"] is False
    assert len(body["id"]) == 36

    updated = api.put(
        f"/api/deals/{body['id']}",
        json=deal_body(partner_id, contact_id, title="Sortiment angepasst", estimated_value="5100.50", priority="normal"),
    )
    assert updated.status_code == 200
    detail = updated.json()
    assert detail["title"] == "Sortiment angepasst"
    assert detail["estimated_value"] == "5100.50"
    assert detail["history"][0]["to_stage"] == "neuer_lead"
    assert detail["history"][0]["from_stage"] is None


def test_assign_and_move_stage(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    created = api.post("/api/deals", json=deal_body(partner_id, stage="erstkontakt"))
    assert created.status_code == 201
    deal_id = created.json()["id"]
    assert created.json()["probability"] == "20.00"

    moved = api.post(f"/api/deals/{deal_id}/stage", json={"stage": "angebot"})
    assert moved.status_code == 200
    body = moved.json()
    assert body["stage"] == "angebot"
    assert body["probability"] == "60.00"
    assert [row["to_stage"] for row in body["history"]] == ["erstkontakt", "angebot"]

    listed = api.get("/api/deals", params={"partner_id": partner_id})
    assert listed.status_code == 200
    assert listed.json()["total"] == 1

    closed_only = api.get("/api/deals", params={"stage": "gewonnen", "include_closed": True, "partner_id": partner_id})
    assert closed_only.json()["total"] == 0

    rejected = api.post(f"/api/deals/{deal_id}/stage", json={"stage": "gewonnen"})
    assert rejected.status_code == 422


def test_win_and_lose_deal(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    won_id = api.post("/api/deals", json=deal_body(partner_id, title="Gewinnen")).json()["id"]
    lost_id = api.post("/api/deals", json=deal_body(partner_id, title="Verlieren")).json()["id"]

    missing_reason = api.post(f"/api/deals/{lost_id}/lose", json={})
    assert missing_reason.status_code == 422

    lost = api.post(f"/api/deals/{lost_id}/lose", json={"loss_reason": "Kein Bedarf mehr"})
    assert lost.status_code == 200
    assert lost.json()["stage"] == "verloren"
    assert lost.json()["probability"] == "0.00"
    assert lost.json()["loss_reason"] == "Kein Bedarf mehr"
    assert lost.json()["closed_on"] == date.today().isoformat()

    won = api.post(f"/api/deals/{won_id}/win", json={"closed_on": "2026-11-01"})
    assert won.status_code == 200
    assert won.json()["stage"] == "gewonnen"
    assert won.json()["probability"] == "100.00"
    assert won.json()["loss_reason"] is None

    open_list = api.get("/api/deals", params={"partner_id": partner_id})
    assert open_list.json()["total"] == 0
    closed_list = api.get("/api/deals", params={"partner_id": partner_id, "include_closed": True})
    assert closed_list.json()["total"] == 2

    stuck = api.post(f"/api/deals/{won_id}/stage", json={"stage": "verhandlung"})
    assert stuck.status_code == 409

    archived = api.post(f"/api/deals/{won_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    restored = api.post(f"/api/deals/{won_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None


def test_create_edit_and_deactivate_product(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    created = api.post("/api/products", json=product_body(suffix))
    assert created.status_code == 201
    body = created.json()
    assert body["list_price"] == "2.40"
    assert body["vat_rate"] == "8.10"
    assert body["is_active"] is True

    updated = api.put(
        f"/api/products/{body['id']}",
        json=product_body(suffix, name="Spezialbier Test", list_price="3.80", category="bier"),
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Spezialbier Test"
    assert updated.json()["list_price"] == "3.80"

    inactive = api.post(f"/api/products/{body['id']}/deactivate")
    assert inactive.status_code == 200
    assert inactive.json()["is_active"] is False
    hidden = api.get("/api/products", params={"q": f"QA-{suffix}"})
    assert hidden.json()["total"] == 0
    visible = api.get("/api/products", params={"q": f"QA-{suffix}", "include_inactive": True})
    assert visible.json()["total"] == 1

    again = api.post(f"/api/products/{body['id']}/deactivate")
    assert again.status_code == 409
    duplicate = api.post("/api/products", json=product_body(suffix))
    assert duplicate.status_code == 409


def test_order_amounts_and_vat(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    contact_id = create_contact(api, suffix, partner_id)
    standard_id = create_product(api, f"{suffix}a", sku=f"QA-A-{suffix}", vat_rate="8.10", list_price="10.00")
    reduced_id = create_product(api, f"{suffix}b", sku=f"QA-B-{suffix}", vat_rate="2.60", list_price="2.20", name="Alkoholfrei Test")

    discount, net, vat, gross = line_amounts(Decimal("2"), Decimal("10.00"), Decimal("10"), Decimal("8.10"))
    assert (discount, net, vat, gross) == (Decimal("2.00"), Decimal("18.00"), Decimal("1.46"), Decimal("19.46"))

    created = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "contact_id": contact_id,
            "ordered_on": "2026-11-12",
            "requested_delivery_on": "2026-11-20",
            "notes": "Testbestellung, nicht ans ERP gesendet.",
            "items": [
                {"product_id": standard_id, "quantity": "2", "unit_price": "10.00", "discount_percent": "10"},
                {"product_id": reduced_id, "quantity": "12", "discount_percent": "0"},
            ],
            "submit": False,
        },
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["status"] == "entwurf"
    assert body["order_number"].startswith("BP-")
    first, second = body["items"]
    assert first["product_name"].startswith("Lagerbier")
    assert first["discount_amount"] == "2.00"
    assert first["line_net"] == "18.00"
    assert first["line_vat"] == "1.46"
    assert first["line_gross"] == "19.46"
    assert second["vat_rate"] == "2.60"
    assert second["unit_price"] == "2.20"
    assert second["line_net"] == "26.40"
    assert second["line_vat"] == "0.69"
    assert second["line_gross"] == "27.09"
    assert body["discount_total"] == "2.00"
    assert body["net_total"] == "44.40"
    assert body["vat_total"] == "2.15"
    assert body["gross_total"] == "46.55"
    assert "eingereicht" in body["allowed_transitions"]

    renamed = api.put(
        f"/api/products/{standard_id}",
        json=product_body(f"{suffix}a", sku=f"QA-A-{suffix}", name="Umbenannt", list_price="99.00", vat_rate="8.10"),
    )
    assert renamed.status_code == 200
    stored = api.get(f"/api/orders/{body['id']}")
    assert stored.json()["items"][0]["product_name"].startswith("Lagerbier")
    assert stored.json()["items"][0]["unit_price"] == "10.00"


def test_order_status_transitions(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    product_id = create_product(api, suffix)
    created = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "ordered_on": "2026-11-12",
            "items": [{"product_id": product_id, "quantity": "1"}],
            "submit": True,
        },
    )
    assert created.status_code == 201
    order_id = created.json()["id"]
    assert created.json()["status"] == "eingereicht"

    edited = api.put(
        f"/api/orders/{order_id}",
        json={
            "partner_id": partner_id,
            "ordered_on": "2026-11-12",
            "items": [{"product_id": product_id, "quantity": "2"}],
        },
    )
    assert edited.status_code == 409

    skipped = api.post(f"/api/orders/{order_id}/status", json={"status": "versandt"})
    assert skipped.status_code == 409
    assert api.get(f"/api/orders/{order_id}").json()["status"] == "eingereicht"

    confirmed = api.post(f"/api/orders/{order_id}/status", json={"status": "bestaetigt"})
    assert confirmed.status_code == 200
    working = api.post(f"/api/orders/{order_id}/status", json={"status": "in_bearbeitung"})
    shipped = api.post(f"/api/orders/{working.json()['id']}/status", json={"status": "versandt"})
    delivered = api.post(f"/api/orders/{order_id}/status", json={"status": "geliefert"})
    assert delivered.status_code == 200
    assert delivered.json()["status"] == "geliefert"
    assert shipped.status_code == 200
    terminal = api.post(f"/api/orders/{order_id}/status", json={"status": "storniert"})
    assert terminal.status_code == 409


def test_partner_and_contact_links(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    other_id = create_partner(api, f"{suffix}x")
    contact_id = create_contact(api, suffix, partner_id)
    product_id = create_product(api, suffix)

    foreign = api.post("/api/deals", json=deal_body(partner_id, contact_id))
    assert foreign.status_code == 201
    deal_id = foreign.json()["id"]
    unlinked = api.post("/api/deals", json=deal_body(other_id, contact_id))
    assert unlinked.status_code == 409

    missing_product = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "ordered_on": "2026-11-12",
            "items": [{"product_id": str(uuid4()), "quantity": "1"}],
        },
    )
    assert missing_product.status_code == 404

    wrong_deal = api.post(
        "/api/orders",
        json={
            "partner_id": other_id,
            "deal_id": deal_id,
            "ordered_on": "2026-11-12",
            "items": [{"product_id": product_id, "quantity": "1"}],
        },
    )
    assert wrong_deal.status_code == 409

    inactive = api.post(f"/api/products/{product_id}/deactivate")
    assert inactive.status_code == 200
    blocked = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "contact_id": contact_id,
            "ordered_on": "2026-11-12",
            "items": [{"product_id": product_id, "quantity": "1"}],
        },
    )
    assert blocked.status_code == 409

    missing = api.get(f"/api/deals/{uuid4()}")
    assert missing.status_code == 404
    float_money = api.post("/api/products", json=product_body(f"{suffix}f", sku=f"QA-F-{suffix}", list_price=2.4))
    assert float_money.status_code == 422


def test_pipeline_and_summaries(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    deal = api.post("/api/deals", json=deal_body(partner_id, stage="angebot", estimated_value="100.00"))
    assert deal.status_code == 201
    board = api.get("/api/deals/pipeline", params={"partner_id": partner_id})
    assert board.status_code == 200
    columns = {column["stage"]: column for column in board.json()["columns"]}
    assert list(columns) == ["neuer_lead", "erstkontakt", "bedarf", "angebot", "verhandlung"]
    assert columns["angebot"]["count"] == 1
    assert columns["angebot"]["total_value"] == "100.00"
    assert columns["angebot"]["deals"][0]["company_name"].startswith("QA Verkauf")

    summary = api.get("/api/deals/summary", params={"partner_id": partner_id})
    assert summary.status_code == 200
    assert summary.json()["open_count"] == 1
    assert summary.json()["pipeline_value"] == "60.00"

    product_id = create_product(api, suffix, list_price="10.00", vat_rate="0")
    order = api.post(
        "/api/orders",
        json={
            "partner_id": partner_id,
            "ordered_on": date.today().isoformat(),
            "items": [{"product_id": product_id, "quantity": "1"}],
            "submit": True,
        },
    )
    assert order.status_code == 201
    orders = api.get("/api/orders/summary", params={"partner_id": partner_id})
    assert orders.json()["order_count"] == 1
    assert orders.json()["new_count"] == 1
    assert orders.json()["volume"] == "10.00"

    partners = api.get("/api/partners", params={"q": f"QA Verkauf {suffix}"})
    assert partners.status_code == 200
    assert partners.json()["total"] == 1


def test_sales_persists_in_postgresql() -> None:
    suffix = uuid4().hex[:8]
    partner_id: str | None = None
    try:
        with TestClient(app) as client:
            partner_id = create_partner(client, suffix)
            contact_id = create_contact(client, suffix, partner_id)
            product_id = create_product(client, suffix)
            deal = client.post("/api/deals", json=deal_body(partner_id, contact_id, stage="angebot"))
            assert deal.status_code == 201
            order = client.post(
                "/api/orders",
                json={
                    "partner_id": partner_id,
                    "contact_id": contact_id,
                    "deal_id": deal.json()["id"],
                    "ordered_on": "2026-11-12",
                    "items": [{"product_id": product_id, "quantity": "3", "discount_percent": "0"}],
                    "submit": True,
                },
            )
            assert order.status_code == 201
            deal_id = deal.json()["id"]
            order_id = order.json()["id"]
        with SessionLocal() as session:
            stored_deal = session.get(Deal, UUID(deal_id))
            stored_order = session.get(Order, UUID(order_id))
            assert stored_deal is not None and stored_deal.stage == "angebot"
            assert stored_order is not None and stored_order.gross_total == Decimal("7.78")
            history = session.scalars(select(DealStageHistory).where(DealStageHistory.deal_id == stored_deal.id)).all()
            items = session.scalars(select(OrderItem).where(OrderItem.order_id == stored_order.id)).all()
            assert len(history) == 1
            assert len(items) == 1
            assert items[0].sku == f"QA-{suffix}"
    finally:
        if partner_id is not None:
            with SessionLocal() as session:
                partner = session.get(Partner, UUID(partner_id))
                if partner is not None:
                    order_ids = select(Order.id).where(Order.partner_id == partner.id)
                    deal_ids = select(Deal.id).where(Deal.partner_id == partner.id)
                    contact_ids = select(CompanyContact.contact_id).where(CompanyContact.partner_id == partner.id)
                    session.execute(delete(OrderItem).where(OrderItem.order_id.in_(order_ids)))
                    session.execute(delete(Order).where(Order.partner_id == partner.id))
                    session.execute(delete(DealStageHistory).where(DealStageHistory.deal_id.in_(deal_ids)))
                    session.execute(delete(Deal).where(Deal.partner_id == partner.id))
                    session.execute(delete(Product).where(Product.sku == f"QA-{suffix}"))
                    session.execute(delete(CompanyContact).where(CompanyContact.partner_id == partner.id))
                    session.execute(delete(Contact).where(Contact.id.in_(contact_ids)))
                    session.execute(delete(Partner).where(Partner.id == partner.id))
                    session.commit()
