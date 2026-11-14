from collections.abc import Iterator
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from support import AuthClient, authenticated_client, login_session
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, get_db
from app.main import app
from app.models.partner import Partner
from app.seed_partners import DEMO_NOTE, DEMO_PARTNERS, seed_demo_partners

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
    with AuthClient(app) as client:
        login_session(client, db_session)
        yield client
    app.dependency_overrides.pop(get_db, None)


def partner_body(suffix: str, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "company_name": f"QA Partner {suffix}",
        "erp_customer_number": f"QA-{suffix}",
        "partner_type": "restaurant",
        "industry": f"QA-Branche {suffix}",
        "street": "Testweg 1",
        "postal_code": "9490",
        "city": f"Testort {suffix}",
        "region": "Liechtenstein",
        "country": "Liechtenstein",
        "phone": "+423 000 00 00",
        "email": f"qa-{suffix}@example.com",
        "website": "https://example.com/qa",
        "status": "lead",
        "account_owner": f"QA Betreuung {suffix}",
        "acquisition_source": "Messe",
        "priority": "normal",
        "first_contact_on": "2024-05-01",
        "notes": "Automatisierter Test",
    }
    body.update(overrides)
    return body


def test_create_get_and_update_partner(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    created = api.post("/api/partners", json=partner_body(suffix))

    assert created.status_code == 201
    body = created.json()
    partner_id = body["id"]
    assert body["company_name"] == f"QA Partner {suffix}"
    assert body["is_demo"] is False
    assert body["archived_at"] is None
    assert body["last_contact_at"] is None
    assert body["next_activity_on"] is None

    fetched = api.get(f"/api/partners/{partner_id}")
    assert fetched.status_code == 200
    assert fetched.json()["erp_customer_number"] == f"QA-{suffix}"

    changed = partner_body(
        suffix,
        company_name=f"QA Partner {suffix} Aktualisiert",
        status="aktiv",
        account_owner="QA Betreuung Neu",
        city=f"Testort {suffix}",
    )
    updated = api.put(f"/api/partners/{partner_id}", json=changed)

    assert updated.status_code == 200
    updated_body = updated.json()
    assert updated_body["company_name"] == f"QA Partner {suffix} Aktualisiert"
    assert updated_body["status"] == "aktiv"
    assert updated_body["account_owner"] == "QA Betreuung Neu"
    assert updated_body["updated_at"] >= body["updated_at"]


def test_search_filters_sort_and_pagination(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    first = partner_body(
        suffix,
        company_name=f"QA Alpha {suffix}",
        city="Filterstadt",
        region="Filterregion",
        status="aktiv",
    )
    second = partner_body(
        f"{suffix}b",
        company_name=f"QA Zulu {suffix}",
        city="Filterstadt",
        status="lead",
        industry=first["industry"],
        region="Filterregion",
        account_owner=first["account_owner"],
        erp_customer_number=f"QA-{suffix}B",
    )
    third = partner_body(
        f"{suffix}c",
        company_name=f"QA Mitte {suffix}",
        city="Andere Stadt",
        industry=first["industry"],
        account_owner=first["account_owner"],
        region="Filterregion",
        erp_customer_number=f"QA-{suffix}C",
        notes="EinzigartigerHinweisXYZ",
    )
    assert api.post("/api/partners", json=first).status_code == 201
    assert api.post("/api/partners", json=second).status_code == 201
    assert api.post("/api/partners", json=third).status_code == 201

    by_name = api.get("/api/partners", params={"q": f"alpha {suffix}"})
    assert by_name.status_code == 200
    assert by_name.json()["total"] == 1
    assert by_name.json()["items"][0]["city"] == "Filterstadt"

    by_city = api.get("/api/partners", params={"q": "filterstadt"})
    assert by_city.json()["total"] == 2

    by_erp = api.get("/api/partners", params={"q": f"qa-{suffix}b"})
    assert by_erp.json()["total"] == 1
    assert by_erp.json()["items"][0]["company_name"] == f"QA Zulu {suffix}"

    by_note = api.get("/api/partners", params={"q": "EinzigartigerHinweisXYZ"})
    assert by_note.json()["total"] == 0

    filtered = api.get(
        "/api/partners",
        params={
            "status": "aktiv",
            "industry": first["industry"],
            "region": "filterregion",
            "account_owner": first["account_owner"],
        },
    )
    assert filtered.json()["total"] == 1
    assert filtered.json()["items"][0]["company_name"] == f"QA Alpha {suffix}"

    ordered = api.get(
        "/api/partners",
        params={"q": suffix, "sort": "name", "direction": "desc", "page": 1, "page_size": 2},
    )
    assert ordered.status_code == 200
    ordered_body = ordered.json()
    assert ordered_body["total"] == 3
    assert ordered_body["page_size"] == 2
    assert [item["company_name"] for item in ordered_body["items"]] == [
        f"QA Zulu {suffix}",
        f"QA Mitte {suffix}",
    ]
    page_two = api.get(
        "/api/partners",
        params={"q": suffix, "sort": "name", "direction": "desc", "page": 2, "page_size": 2},
    )
    assert [item["company_name"] for item in page_two.json()["items"]] == [f"QA Alpha {suffix}"]

    options = api.get("/api/partners/filters")
    assert options.status_code == 200
    assert first["industry"] in options.json()["industries"]
    assert "Filterregion" in options.json()["regions"]
    assert first["account_owner"] in options.json()["account_owners"]


def test_validation_and_duplicates(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    missing = api.post("/api/partners", json=partner_body(suffix, company_name="   "))
    assert missing.status_code == 422
    assert "Unternehmensname ist erforderlich." in missing.text

    invalid_email = api.post("/api/partners", json=partner_body(suffix, email="keine-adresse"))
    assert invalid_email.status_code == 422
    assert "E-Mail ist ungültig." in invalid_email.text

    invalid_type = api.post("/api/partners", json=partner_body(suffix, partner_type="Brauerei"))
    assert invalid_type.status_code == 422
    assert "Partnertyp ist ungültig." in invalid_type.text

    future = (date.today() + timedelta(days=1)).isoformat()
    invalid_date = api.post("/api/partners", json=partner_body(suffix, first_contact_on=future))
    assert invalid_date.status_code == 422
    assert "nicht in der Zukunft" in invalid_date.text

    invalid_site = api.post("/api/partners", json=partner_body(suffix, website="example.com"))
    assert invalid_site.status_code == 422
    assert "https://" in invalid_site.text

    created = api.post("/api/partners", json=partner_body(suffix, erp_customer_number=f"QA-{suffix}"))
    assert created.status_code == 201
    partner_id = created.json()["id"]

    duplicate_erp = api.post(
        "/api/partners",
        json=partner_body(f"{suffix}x", erp_customer_number=f"qa-{suffix}", city="Andere Stadt"),
    )
    assert duplicate_erp.status_code == 409
    assert "ERP-Kundennummer" in duplicate_erp.text

    duplicate_place = api.post(
        "/api/partners",
        json=partner_body(
            f"{suffix}y",
            company_name=f"qa partner {suffix}",
            city=f"testort {suffix}",
            erp_customer_number=f"QA-{suffix}Y",
        ),
    )
    assert duplicate_place.status_code == 409
    assert "Unternehmensnamen und Ort" in duplicate_place.text

    other_city = api.post(
        "/api/partners",
        json=partner_body(
            f"{suffix}z",
            company_name=f"QA Partner {suffix}",
            city="Zweite Stadt",
            erp_customer_number=f"QA-{suffix}Z",
        ),
    )
    assert other_city.status_code == 201

    without_erp = api.post(
        "/api/partners",
        json=partner_body(f"{suffix}n", company_name=f"QA Ohne Nummer {suffix}", erp_customer_number=None),
    )
    assert without_erp.status_code == 201

    conflict = api.put(
        f"/api/partners/{partner_id}",
        json=partner_body(suffix, erp_customer_number=f"qa-{suffix}z"),
    )
    assert conflict.status_code == 409
    assert api.get(f"/api/partners/{partner_id}").json()["erp_customer_number"] == f"QA-{suffix}"

    invalid_sort = api.get("/api/partners", params={"sort": "umsatz"})
    assert invalid_sort.status_code == 422
    unknown = api.get(f"/api/partners/{uuid4()}")
    assert unknown.status_code == 404


def test_archive_and_restore(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    created = api.post("/api/partners", json=partner_body(suffix, status="aktiv"))
    partner_id = created.json()["id"]

    archived = api.post(f"/api/partners/{partner_id}/archive")
    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None

    hidden = api.get("/api/partners", params={"q": suffix})
    assert hidden.json()["total"] == 0
    visible = api.get("/api/partners", params={"q": suffix, "include_archived": True})
    assert visible.json()["total"] == 1

    blocked = api.put(f"/api/partners/{partner_id}", json=partner_body(suffix, status="inaktiv"))
    assert blocked.status_code == 409
    assert "Wiederherstellung" in blocked.text

    again = api.post(f"/api/partners/{partner_id}/archive")
    assert again.status_code == 409

    restored = api.post(f"/api/partners/{partner_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    assert api.get("/api/partners", params={"q": suffix}).json()["total"] == 1

    active = api.post(f"/api/partners/{partner_id}/restore")
    assert active.status_code == 409


def test_summary_counts_only_active_database_rows(api: TestClient) -> None:
    before = api.get("/api/partners/summary")
    assert before.status_code == 200
    suffix = uuid4().hex[:8]
    assert api.post("/api/partners", json=partner_body(suffix, status="aktiv")).status_code == 201
    assert api.post(
        "/api/partners",
        json=partner_body(f"{suffix}l", status="lead", erp_customer_number=f"QA-{suffix}L"),
    ).status_code == 201
    after = api.get("/api/partners/summary").json()
    assert after["active"] == before.json()["active"] + 1


def test_seed_is_repeatable_and_marked_as_test_data(db_session: Session) -> None:
    assert seed_demo_partners(db_session) == len(DEMO_PARTNERS)
    assert seed_demo_partners(db_session) == len(DEMO_PARTNERS)
    keys = [str(item["demo_key"]) for item in DEMO_PARTNERS]
    stored = db_session.scalars(select(Partner).where(Partner.demo_key.in_(keys))).all()
    assert len(stored) == len(keys)
    lago = next(row for row in stored if row.demo_key == "demo-ristorante-lago")
    assert lago.city == "Locarno"
    assert lago.is_demo is True
    assert lago.notes is not None and lago.notes.startswith(DEMO_NOTE)
    assert all(row.is_demo for row in stored)
    lago.archived_at = lago.updated_at
    seed_demo_partners(db_session)
    db_session.refresh(lago)
    assert lago.archived_at is not None


def test_partner_persists_in_postgresql() -> None:
    suffix = uuid4().hex[:8]
    partner_id: str | None = None
    try:
        with authenticated_client() as client:
            response = client.post("/api/partners", json=partner_body(suffix, company_name=f"QA Persistenz {suffix}"))
            assert response.status_code == 201
            partner_id = response.json()["id"]
            assert response.json()["last_contact_at"] is None
        with SessionLocal() as session:
            stored = session.get(Partner, UUID(partner_id))
            assert stored is not None
            assert stored.company_name == f"QA Persistenz {suffix}"
            assert stored.archived_at is None
            remaining = session.scalar(
                select(func.count()).select_from(Partner).where(Partner.company_name == f"QA Persistenz {suffix}")
            )
            assert remaining == 1
    finally:
        if partner_id is not None:
            with SessionLocal() as session:
                stored = session.get(Partner, UUID(partner_id))
                if stored is not None:
                    session.delete(stored)
                    session.commit()


def test_openapi_lists_partner_routes(api: TestClient) -> None:
    paths = api.get("/openapi.json").json()["paths"]
    assert "/api/partners" in paths
    assert "/api/partners/{partner_id}" in paths
    assert "/api/partners/{partner_id}/archive" in paths
    assert "/api/partners/{partner_id}/restore" in paths
    assert "/api/health" in paths
