from collections.abc import Iterator
from datetime import datetime, timedelta, timezone
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
from app.models.activity import Activity
from app.models.contact import CompanyContact, Contact
from app.models.partner import Partner
from app.models.task import Task
from app.seed_crm import ACTIVITY_TEXT, CONTACT_KEY, TASK_TITLE, seed_demo_crm
from app.seed_partners import seed_demo_partners
from app.services.crm import CrmServiceError

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


def partner_body(suffix: str) -> dict[str, object]:
    return {
        "company_name": f"QA CRM {suffix}",
        "erp_customer_number": f"CRM-{suffix}",
        "partner_type": "restaurant",
        "city": f"Orts{suffix}",
        "country": "Liechtenstein",
        "status": "aktiv",
        "priority": "normal",
        "account_owner": "QA Betreuung",
    }


def contact_body(suffix: str, partner_id: str | None = None, **overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "first_name": "Giulia",
        "last_name": f"Test {suffix}",
        "job_title": "Inhaberin",
        "email": f"qa-crm-{suffix}@example.com",
        "phone": "+423 000 11 22",
        "mobile": "+423 000 33 44",
        "account_owner": "Sandra Lutz",
        "preferred_language": "de",
        "preferred_channel": "telefon",
        "lifecycle_phase": "kunde",
        "lead_status": "keiner",
        "status": "aktiv",
        "notes": "Automatisierter Test",
        "processing_basis": "nicht_dokumentiert",
        "processing_basis_note": "Keine Einwilligung im Test erfasst.",
        "companies": [{"partner_id": partner_id, "is_primary": True}] if partner_id else [],
    }
    body.update(overrides)
    return body


def create_partner(api: TestClient, suffix: str) -> str:
    response = api.post("/api/partners", json=partner_body(suffix))
    assert response.status_code == 201
    return response.json()["id"]


def test_create_and_edit_contact(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    created = api.post("/api/contacts", json=contact_body(suffix, partner_id))
    assert created.status_code == 201
    body = created.json()
    assert body["lifecycle_phase"] == "kunde"
    assert body["lead_status"] == "keiner"
    assert body["companies"][0]["is_primary"] is True
    assert body["companies"][0]["company_name"].startswith("QA CRM")
    assert body["last_contact_at"] is None

    updated = api.put(
        f"/api/contacts/{body['id']}",
        json=contact_body(suffix, job_title="Geschäftsführerin", lifecycle_phase="interessent"),
    )
    assert updated.status_code == 200
    assert updated.json()["job_title"] == "Geschäftsführerin"
    assert updated.json()["lifecycle_phase"] == "interessent"
    assert updated.json()["companies"][0]["partner_id"] == partner_id

    fetched = api.get(f"/api/contacts/{body['id']}")
    assert fetched.status_code == 200
    assert fetched.json()["job_title"] == "Geschäftsführerin"


def test_company_links_multiple_contacts_and_primary(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    other_id = create_partner(api, f"{suffix}b")
    first = api.post("/api/contacts", json=contact_body(suffix, partner_id, email=f"a-{suffix}@example.com"))
    second = api.post(
        "/api/contacts",
        json=contact_body(
            f"{suffix}b",
            partner_id,
            first_name="Marco",
            email=f"b-{suffix}@example.com",
            companies=[{"partner_id": partner_id, "is_primary": False}],
        ),
    )
    assert first.status_code == 201
    assert second.status_code == 201
    listed = api.get("/api/contacts", params={"partner_id": partner_id})
    assert listed.status_code == 200
    assert listed.json()["total"] == 2
    assert first.json()["companies"][0]["is_primary"] is True

    moved = api.post(
        f"/api/contacts/{second.json()['id']}/companies/{partner_id}/primary",
    )
    assert moved.status_code == 200
    assert moved.json()["companies"][0]["is_primary"] is True
    refreshed = api.get(f"/api/contacts/{first.json()['id']}")
    assert refreshed.json()["companies"][0]["is_primary"] is False

    linked = api.post(
        f"/api/contacts/{first.json()['id']}/companies",
        json={"partner_id": other_id, "is_primary": True},
    )
    assert linked.status_code == 200
    assert len(linked.json()["companies"]) == 2

    duplicate = api.post(
        f"/api/contacts/{first.json()['id']}/companies",
        json={"partner_id": other_id, "is_primary": False},
    )
    assert duplicate.status_code == 409


def test_archive_restore_and_unlink_keeps_history(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    contact_id = api.post("/api/contacts", json=contact_body(suffix, partner_id)).json()["id"]
    activity = api.post(
        "/api/activities",
        json={
            "activity_type": "telefonat",
            "title": f"Anruf {suffix}",
            "description": "Testanruf",
            "occurred_at": "2026-11-01T09:00:00+00:00",
            "account_owner": "Sandra Lutz",
            "contact_id": contact_id,
            "partner_id": partner_id,
        },
    )
    assert activity.status_code == 201
    activity_id = activity.json()["id"]

    removed = api.delete(f"/api/contacts/{contact_id}/companies/{partner_id}")
    assert removed.status_code == 200
    assert removed.json()["companies"] == []
    assert api.get(f"/api/contacts/{contact_id}").status_code == 200
    assert api.get(f"/api/activities/{activity_id}").status_code == 200

    archived = api.post(f"/api/contacts/{contact_id}/archive")
    assert archived.status_code == 200
    assert api.get("/api/contacts", params={"q": suffix}).json()["total"] == 0
    blocked = api.put(f"/api/contacts/{contact_id}", json=contact_body(suffix, job_title="Archiv"))
    assert blocked.status_code == 409
    restored = api.post(f"/api/contacts/{contact_id}/restore")
    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None

    hidden = api.post(f"/api/activities/{activity_id}/archive")
    assert hidden.status_code == 200
    assert api.get("/api/activities", params={"contact_id": contact_id}).json()["total"] == 0
    assert api.get("/api/activities", params={"contact_id": contact_id, "include_archived": True}).json()["total"] == 1


def test_activity_is_visible_for_contact_and_partner(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    contact_id = api.post("/api/contacts", json=contact_body(suffix, partner_id)).json()["id"]
    created = api.post(
        "/api/activities",
        json={
            "activity_type": "meeting",
            "title": f"Meeting {suffix}",
            "occurred_at": "2026-11-02T15:30:00Z",
            "contact_id": contact_id,
            "partner_id": partner_id,
        },
    )
    assert created.status_code == 201
    assert created.json()["contact_name"].startswith("Giulia")
    assert created.json()["company_name"].startswith("QA CRM")
    by_contact = api.get("/api/activities", params={"contact_id": contact_id})
    by_partner = api.get("/api/activities", params={"partner_id": partner_id})
    assert by_contact.json()["total"] == 1
    assert by_partner.json()["total"] == 1
    assert by_contact.json()["items"][0]["id"] == by_partner.json()["items"][0]["id"]

    edited = api.put(
        f"/api/activities/{created.json()['id']}",
        json={
            "activity_type": "gespraechsnotiz",
            "title": f"Notiz {suffix}",
            "occurred_at": "2026-11-02T15:30:00Z",
            "contact_id": contact_id,
            "partner_id": partner_id,
        },
    )
    assert edited.status_code == 200
    assert edited.json()["activity_type"] == "gespraechsnotiz"

    partner = api.get(f"/api/partners/{partner_id}")
    assert partner.json()["last_contact_at"] is not None


def test_task_edit_status_and_overdue(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    contact_id = api.post("/api/contacts", json=contact_body(suffix, partner_id)).json()["id"]
    past = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    overdue = api.post(
        "/api/tasks",
        json={
            "title": f"Überfällig {suffix}",
            "account_owner": "Sandra Lutz",
            "due_at": past,
            "priority": "dringend",
            "status": "offen",
            "task_type": "anruf",
            "partner_id": partner_id,
            "contact_id": contact_id,
        },
    )
    upcoming = api.post(
        "/api/tasks",
        json={
            "title": f"Bald {suffix}",
            "account_owner": "Sandra Lutz",
            "due_at": future,
            "priority": "normal",
            "status": "offen",
            "task_type": "intern",
            "partner_id": partner_id,
        },
    )
    assert overdue.status_code == 201
    assert upcoming.status_code == 201
    assert overdue.json()["is_overdue"] is True
    assert overdue.json()["is_urgent"] is True
    assert upcoming.json()["is_due_soon"] is True
    assert upcoming.json()["is_overdue"] is False

    found = api.get("/api/tasks", params={"due": "overdue", "q": suffix})
    assert found.status_code == 200
    assert [item["id"] for item in found.json()["items"]] == [overdue.json()["id"]]

    edited = api.put(
        f"/api/tasks/{upcoming.json()['id']}",
        json={
            "title": f"Bald {suffix}",
            "account_owner": "Neue Betreuung",
            "due_at": future,
            "priority": "hoch",
            "status": "in_bearbeitung",
            "task_type": "email",
            "partner_id": partner_id,
            "contact_id": contact_id,
        },
    )
    assert edited.status_code == 200
    assert edited.json()["status"] == "in_bearbeitung"
    assert edited.json()["priority"] == "hoch"
    assert edited.json()["account_owner"] == "Neue Betreuung"

    done = api.post(f"/api/tasks/{overdue.json()['id']}/complete")
    assert done.status_code == 200
    assert done.json()["status"] == "erledigt"
    assert done.json()["is_overdue"] is False
    assert api.get("/api/tasks", params={"due": "overdue", "q": suffix}).json()["total"] == 0

    summary = api.get("/api/tasks/summary")
    assert summary.status_code == 200
    assert summary.json()["open"] >= 1


def test_note_with_follow_up_task_links_both_records(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    contact_id = api.post("/api/contacts", json=contact_body(suffix, partner_id)).json()["id"]
    due = (datetime.now(timezone.utc) + timedelta(days=4)).isoformat()
    created = api.post(
        "/api/activities/note-with-task",
        json={
            "activity": {
                "activity_type": "telefonat",
                "title": f"Gespräch {suffix}",
                "description": "Telefonischer Austausch",
                "occurred_at": "2026-11-10T09:00:00+00:00",
                "account_owner": "Sandra Lutz",
                "contact_id": contact_id,
                "partner_id": partner_id,
            },
            "create_task": True,
            "task": {
                "title": f"Nachfassen {suffix}",
                "account_owner": "Sandra Lutz",
                "due_at": due,
                "priority": "hoch",
                "task_type": "anruf",
            },
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["task"]["activity_id"] == body["activity"]["id"]
    assert body["task"]["contact_id"] == contact_id
    assert body["task"]["partner_id"] == partner_id
    assert api.get("/api/activities", params={"partner_id": partner_id}).json()["total"] == 1
    assert api.get("/api/tasks", params={"contact_id": contact_id}).json()["total"] == 1


def test_follow_up_failure_does_not_keep_the_activity(api: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    contact_id = api.post("/api/contacts", json=contact_body(suffix, partner_id)).json()["id"]

    def fail_task(*_args, **_kwargs):
        raise CrmServiceError("Die Folgeaufgabe ist ungültig.", 422)

    monkeypatch.setattr("app.services.crm.insert_task", fail_task)
    failed = api.post(
        "/api/activities/note-with-task",
        json={
            "activity": {
                "activity_type": "gespraechsnotiz",
                "title": f"Unvollständig {suffix}",
                "occurred_at": "2026-11-10T09:00:00+00:00",
                "contact_id": contact_id,
                "partner_id": partner_id,
            },
            "create_task": True,
            "task": {
                "title": f"Folge {suffix}",
                "due_at": "2026-11-20T09:00:00+00:00",
                "priority": "normal",
                "task_type": "intern",
            },
        },
    )
    assert failed.status_code == 422
    assert api.get("/api/activities", params={"q": suffix}).json()["total"] == 0
    assert api.get("/api/tasks", params={"q": suffix}).json()["total"] == 0


def test_validation_and_duplicate_email(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    missing = api.post("/api/contacts", json={"first_name": "Nur"})
    assert missing.status_code == 422
    partner_id = create_partner(api, suffix)
    first = api.post("/api/contacts", json=contact_body(suffix, partner_id))
    assert first.status_code == 201
    duplicate = api.post(
        "/api/contacts",
        json=contact_body(f"{suffix}x", partner_id, email=f"qa-crm-{suffix}@example.com"),
    )
    assert duplicate.status_code == 409
    assert "E-Mail" in duplicate.text
    unlinked = api.post(
        "/api/activities",
        json={"activity_type": "notiz", "title": "Ohne Bezug", "occurred_at": "2026-11-01T09:00:00Z"},
    )
    assert unlinked.status_code == 422


def test_seed_is_repeatable(db_session: Session) -> None:
    assert seed_demo_partners(db_session) >= 1
    assert seed_demo_crm(db_session) == 3
    assert seed_demo_crm(db_session) == 3
    contact = db_session.scalar(select(Contact).where(Contact.demo_key == CONTACT_KEY))
    assert contact is not None
    assert contact.is_demo is True
    assert contact.email is None
    assert contact.phone is None
    assert contact.lifecycle_phase == "kunde"
    assert contact.lead_status == "keiner"
    assert contact.processing_basis == "nicht_dokumentiert"
    activity = db_session.scalar(select(Activity).where(Activity.demo_key == "demo-giulia-telefonat"))
    assert activity is not None
    assert activity.description == ACTIVITY_TEXT
    assert activity.contact_id == contact.id
    task = db_session.scalar(select(Task).where(Task.demo_key == "demo-giulia-sortiment"))
    assert task is not None
    assert task.title == TASK_TITLE
    assert task.activity_id == activity.id
    assert db_session.scalar(select(func.count()).select_from(Contact).where(Contact.demo_key == CONTACT_KEY)) == 1


def test_contact_persists_in_postgresql() -> None:
    suffix = uuid4().hex[:8]
    contact_id: str | None = None
    partner_id: str | None = None
    try:
        with authenticated_client() as client:
            partner_id = create_partner(client, suffix)
            response = client.post("/api/contacts", json=contact_body(suffix, partner_id, email=None))
            assert response.status_code == 201
            contact_id = response.json()["id"]
        with SessionLocal() as session:
            stored = session.get(Contact, UUID(contact_id))
            assert stored is not None
            assert stored.last_name == f"Test {suffix}"
            link = session.scalar(select(CompanyContact).where(CompanyContact.contact_id == stored.id))
            assert link is not None
    finally:
        if contact_id is not None:
            with SessionLocal() as session:
                session.query(CompanyContact).filter(CompanyContact.contact_id == UUID(contact_id)).delete()
                session.query(Activity).filter(Activity.contact_id == UUID(contact_id)).delete()
                session.query(Task).filter(Task.contact_id == UUID(contact_id)).delete()
                stored = session.get(Contact, UUID(contact_id))
                if stored is not None:
                    session.delete(stored)
                if partner_id is not None:
                    partner = session.get(Partner, UUID(partner_id))
                    if partner is not None:
                        session.delete(partner)
                session.commit()
