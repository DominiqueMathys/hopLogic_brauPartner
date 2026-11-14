import os
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from support import AuthClient, authenticated_client, login_session
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, get_db
from app.main import app
from app.models.contact import CompanyContact, Contact
from app.models.engagement import AutomationRule, CampaignAudienceMember, CampaignRecipient, MarketingCampaign
from app.models.partner import Partner
from app.services.automation import publish_event, run_due_automations

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module", autouse=True)
def migrated_database() -> None:
    config = Config(str(ROOT / "backend" / "alembic.ini"))
    command.upgrade(config, "head")


@pytest.fixture()
def db_session():
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
def api(db_session: Session):
    def override():
        yield db_session

    app.dependency_overrides[get_db] = override
    with AuthClient(app) as client:
        login_session(client, db_session)
        yield client
    app.dependency_overrides.pop(get_db, None)


def create_partner(api: TestClient, suffix: str) -> str:
    response = api.post(
        "/api/partners",
        json={
            "company_name": f"QA Engagement {suffix}",
            "erp_customer_number": f"EG-{suffix}",
            "partner_type": "restaurant",
            "city": "Vaduz",
            "country": "Liechtenstein",
            "status": "aktiv",
            "priority": "normal",
            "account_owner": "Sandra Lutz",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def create_contact(api: TestClient, suffix: str, partner_id: str, email: str | None = None) -> str:
    payload = {
        "first_name": "Giulia",
        "last_name": f"Engagement {suffix}",
        "account_owner": "Sandra Lutz",
        "preferred_language": "de",
        "preferred_channel": "telefon",
        "lifecycle_phase": "kunde",
        "lead_status": "keiner",
        "status": "aktiv",
        "processing_basis": "nicht_dokumentiert",
        "companies": [{"partner_id": partner_id, "is_primary": True}],
    }
    if email:
        payload["email"] = email
    response = api.post("/api/contacts", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["id"]


def campaign_body(**overrides: object) -> dict:
    body = {
        "name": "Winterprobe",
        "description": "Entwurf",
        "campaign_type": "saisonal",
        "account_owner": "Sandra Lutz",
        "starts_on": "2026-12-01",
        "ends_on": "2027-02-28",
        "objective": "Saison vorstellen",
        "audience_kind": "contacts",
        "channel": "telefon",
        "budget": "1500.00",
    }
    body.update(overrides)
    return body


def test_campaign_audience_consent_and_status(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    other_id = create_partner(api, f"{suffix}b")
    allowed_id = create_contact(api, f"{suffix}a", partner_id, email=f"{suffix}@example.com")
    rejected_id = create_contact(api, f"{suffix}r", partner_id, email=f"stop-{suffix}@example.com")
    plain_id = create_contact(api, f"{suffix}p", other_id)
    linked = api.post(f"/api/contacts/{plain_id}/companies", json={"partner_id": partner_id, "is_primary": False})
    assert linked.status_code == 200, linked.text

    allowed = api.put(
        f"/api/contacts/{allowed_id}/preferences",
        json={
            "preferred_channel": "email",
            "email_marketing_allowed": True,
            "marketing_rejected": False,
            "consent_on": "2026-11-01",
            "consent_source": "Schriftliche Rückmeldung im CRM-Test",
            "consent_evidence": "Testnachweis, keine echte Einwilligung.",
        },
    )
    assert allowed.status_code == 200, allowed.text
    assert "rechtlich" in allowed.json()["notice"]
    bare = api.put(
        f"/api/contacts/{plain_id}/preferences",
        json={"preferred_channel": "email", "email_marketing_allowed": True, "marketing_rejected": False},
    )
    assert bare.status_code == 422
    rejected = api.put(
        f"/api/contacts/{rejected_id}/preferences",
        json={
            "preferred_channel": "telefon",
            "email_marketing_allowed": False,
            "marketing_rejected": True,
            "revoked_on": "2026-11-02",
        },
    )
    assert rejected.status_code == 200, rejected.text
    suppressed = api.get("/api/preferences/suppressed")
    assert rejected_id in {row["contact_id"] for row in suppressed.json()}

    created = api.post("/api/campaigns", json=campaign_body())
    assert created.status_code == 201, created.text
    campaign_id = created.json()["id"]
    edited = api.put(f"/api/campaigns/{campaign_id}", json=campaign_body(name="Winterprobe angepasst", budget="1500.50"))
    assert edited.status_code == 200
    assert edited.json()["budget"] == "1500.50"
    assert api.post("/api/campaigns", json=campaign_body(budget=12.5)).status_code == 422

    assert api.post(f"/api/campaigns/{campaign_id}/audience", json={"contact_id": allowed_id}).status_code == 201
    assert api.post(f"/api/campaigns/{campaign_id}/audience", json={"contact_id": allowed_id}).status_code == 409
    assert api.post(f"/api/campaigns/{campaign_id}/audience", json={"contact_id": rejected_id}).status_code == 201
    assert api.post(f"/api/campaigns/{campaign_id}/audience", json={"contact_id": plain_id}).status_code == 201

    phone = api.get(f"/api/campaigns/{campaign_id}/audience").json()
    included = {row["contact_id"] for row in phone["included"]}
    assert allowed_id in included and plain_id in included and rejected_id not in included
    assert "Marketingkommunikation abgelehnt" in {row["exclusion_reason"] for row in phone["excluded"]}

    assert api.put(f"/api/campaigns/{campaign_id}", json=campaign_body(name="Winterprobe angepasst", channel="email")).status_code == 200
    mail = api.get(f"/api/campaigns/{campaign_id}/audience").json()
    assert {row["contact_id"] for row in mail["included"]} == {allowed_id}
    reasons = {row["contact_id"]: row["exclusion_reason"] for row in mail["excluded"]}
    assert reasons[plain_id] == "Keine dokumentierte E-Mail-Einwilligung"

    partner_campaign = api.post("/api/campaigns", json=campaign_body(name="Partnerwahl", audience_kind="partners"))
    partner_campaign_id = partner_campaign.json()["id"]
    assert api.post(f"/api/campaigns/{partner_campaign_id}/audience", json={"partner_id": partner_id}).status_code == 201
    assert api.post(f"/api/campaigns/{partner_campaign_id}/audience", json={"partner_id": other_id}).status_code == 201
    shared = [row for row in api.get(f"/api/campaigns/{partner_campaign_id}/audience").json()["included"] if row["contact_id"] == plain_id]
    assert len(shared) == 1

    assert api.post(f"/api/campaigns/{campaign_id}/status", json={"status": "aktiv"}).status_code == 409
    assert api.post(f"/api/campaigns/{campaign_id}/status", json={"status": "geplant"}).status_code == 200
    activated = api.post(f"/api/campaigns/{campaign_id}/status", json={"status": "aktiv"})
    assert activated.status_code == 200, activated.text
    assert activated.json()["recipient_count"] == 1
    api.put(
        f"/api/contacts/{allowed_id}/preferences",
        json={
            "preferred_channel": "email",
            "email_marketing_allowed": False,
            "marketing_rejected": True,
            "revoked_on": "2026-11-13",
        },
    )
    still = {row["contact_id"] for row in api.get(f"/api/campaigns/{campaign_id}/audience").json()["included"]}
    assert still == {allowed_id}
    assert api.post(f"/api/campaigns/{campaign_id}/send").status_code == 409

    segment = api.post(
        "/api/segments",
        json={
            "name": f"QA Segment {suffix}",
            "match_mode": "all",
            "conditions": [{"field_name": "partner_type", "operator": "eq", "value": "restaurant"}],
        },
    )
    assert segment.status_code == 201, segment.text
    segmented = api.post(
        "/api/campaigns",
        json=campaign_body(name="Segmentwahl", audience_kind="segment", segment_id=segment.json()["id"], channel="telefon"),
    )
    assert segmented.status_code == 201, segmented.text
    assert segmented.json()["segment_name"].startswith("QA Segment")


def test_template_preview_and_missing_values(api: TestClient) -> None:
    created = api.post(
        "/api/templates",
        json={
            "name": f"Vorlage {uuid4().hex[:6]}",
            "subject": "Hallo {{vorname}}",
            "body": "{{vorname}} {{nachname}} von {{unternehmen}}, {{funktion}} {{unbekannt}}",
            "channel": "email",
        },
    )
    assert created.status_code == 201, created.text
    template_id = created.json()["id"]
    preview = api.post(f"/api/templates/{template_id}/preview", json={"first_name": "Giulia"})
    assert preview.status_code == 200, preview.text
    assert preview.json()["subject"] == "Hallo Giulia"
    assert "{{unbekannt}}" in preview.json()["body"]
    assert preview.json()["body"].startswith("Giulia ")
    assert "Versand nicht konfiguriert" in preview.json()["delivery_notice"]
    assert api.post(f"/api/templates/{template_id}/duplicate").status_code == 201
    assert api.post(f"/api/templates/{template_id}/archive").json()["archived_at"] is not None


def test_care_rule_ignores_cancelled_orders(api: TestClient) -> None:
    suffix = uuid4().hex[:8]
    quiet = create_partner(api, f"{suffix}q")
    buyer = create_partner(api, f"{suffix}k")
    product = api.post(
        "/api/products",
        json={
            "sku": f"QA-EG-{suffix}",
            "name": "Regeltest",
            "category": "bier",
            "container_type": "flasche",
            "container_size": "33 cl",
            "sales_unit": "Flasche",
            "list_price": "2.40",
            "vat_rate": "8.10",
        },
    )
    assert product.status_code == 201, product.text
    product_id = product.json()["id"]
    cancelled = api.post(
        "/api/orders",
        json={"partner_id": quiet, "ordered_on": "2026-11-01", "items": [{"product_id": product_id, "quantity": "1"}]},
    )
    assert cancelled.status_code == 201, cancelled.text
    assert api.post(f"/api/orders/{cancelled.json()['id']}/status", json={"status": "storniert"}).status_code == 200
    kept = api.post(
        "/api/orders",
        json={
            "partner_id": buyer,
            "ordered_on": date.today().isoformat(),
            "submit": True,
            "items": [{"product_id": product_id, "quantity": "2"}],
        },
    )
    assert kept.status_code == 201, kept.text
    rule = api.post(
        "/api/care/rules",
        json={
            "name": f"Keine Bestellung {suffix}",
            "rule_kind": "no_order",
            "threshold_days": 30,
            "is_active": True,
            "create_tasks": False,
            "task_title": "Bestellung nachfassen",
        },
    )
    assert rule.status_code == 201, rule.text
    overview = api.get("/api/care/overview", params={"signal": "order", "page_size": 100})
    assert overview.status_code == 200, overview.text
    ids = {row["partner_id"] for row in overview.json()["items"]}
    assert quiet in ids
    assert buyer not in ids


def test_event_automation_dedupe_pause_and_failure(api: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    for row in db_session.scalars(select(AutomationRule).where(AutomationRule.trigger_type == "deal_created", AutomationRule.status == "aktiv")).all():
        row.status = "pausiert"
    db_session.flush()
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    created = api.post(
        "/api/automations",
        json={
            "name": f"Erstkontakt {suffix}",
            "trigger_type": "deal_created",
            "action_type": "create_task",
            "action_config": {"title": "Erstkontakt vorbereiten", "due_days": 2, "priority": "hoch"},
            "account_owner": "Sandra Lutz",
        },
    )
    assert created.status_code == 201, created.text
    rule_id = created.json()["id"]
    assert api.post(f"/api/automations/{rule_id}/status", json={"status": "aktiv"}).status_code == 200
    deal = api.post(
        "/api/deals",
        json={
            "title": f"Deal {suffix}",
            "partner_id": partner_id,
            "account_owner": "Sandra Lutz",
            "estimated_value": "100.00",
            "expected_close_on": "2026-12-20",
            "stage": "neuer_lead",
            "priority": "normal",
        },
    )
    assert deal.status_code == 201, deal.text
    assert api.get("/api/tasks", params={"partner_id": partner_id, "q": "Erstkontakt vorbereiten"}).json()["total"] == 1
    publish_event(
        db_session,
        "deal_created",
        dedupe_key=f"deal:{deal.json()['id']}",
        context={"owner": "Sandra Lutz", "partner_id": partner_id},
    )
    assert api.get("/api/tasks", params={"partner_id": partner_id, "q": "Erstkontakt vorbereiten"}).json()["total"] == 1
    assert api.get(f"/api/automations/{rule_id}/executions").json()[0]["status"] == "erfolg"
    assert api.post(f"/api/automations/{rule_id}/status", json={"status": "pausiert"}).status_code == 200
    paused_deal = api.post(
        "/api/deals",
        json={
            "title": f"Deal pausiert {suffix}",
            "partner_id": partner_id,
            "account_owner": "Sandra Lutz",
            "estimated_value": "50.00",
            "expected_close_on": "2026-12-21",
            "stage": "neuer_lead",
            "priority": "normal",
        },
    )
    assert paused_deal.status_code == 201
    assert api.get("/api/tasks", params={"partner_id": partner_id, "q": "Erstkontakt vorbereiten"}).json()["total"] == 1
    assert api.post(f"/api/automations/{rule_id}/status", json={"status": "aktiv"}).status_code == 200

    def explode(_db, _rule, _context):
        raise RuntimeError("Kaputt")

    monkeypatch.setattr("app.services.automation.perform_action", explode)
    failed = api.post(
        "/api/deals",
        json={
            "title": f"Deal Fehler {suffix}",
            "partner_id": partner_id,
            "account_owner": "Sandra Lutz",
            "estimated_value": "20.00",
            "expected_close_on": "2026-12-22",
            "stage": "neuer_lead",
            "priority": "normal",
        },
    )
    assert failed.status_code == 201, failed.text
    failures = [row for row in api.get(f"/api/automations/{rule_id}/executions").json() if row["status"] == "fehler"]
    assert failures and "Kaputt" in (failures[0]["error"] or "")


def test_time_trigger_notifications_and_preferences(api: TestClient, db_session: Session) -> None:
    suffix = uuid4().hex[:8]
    partner_id = create_partner(api, suffix)
    rule = api.post(
        "/api/automations",
        json={
            "name": f"Ruhe {suffix}",
            "trigger_type": "no_contact",
            "trigger_config": {"days": 1},
            "action_type": "create_task",
            "action_config": {"title": f"Partnerkontakt {suffix}", "due_days": 3},
            "account_owner": "QA Hinweis",
        },
    )
    assert rule.status_code == 201, rule.text
    assert api.post(f"/api/automations/{rule.json()['id']}/status", json={"status": "aktiv"}).status_code == 200
    overdue = api.post(
        "/api/tasks",
        json={
            "title": f"Ueberfaellig {suffix}",
            "account_owner": "QA Hinweis",
            "due_at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat(),
            "priority": "hoch",
            "status": "offen",
            "task_type": "intern",
            "partner_id": partner_id,
        },
    )
    assert overdue.status_code == 201, overdue.text
    reminder = api.post(
        "/api/automations",
        json={
            "name": f"Erinnerung {suffix}",
            "trigger_type": "task_overdue",
            "trigger_config": {"days": 1},
            "action_type": "create_reminder",
            "action_config": {"title": f"Nachfassen {suffix}", "notification_type": "task_overdue"},
            "account_owner": "QA Hinweis",
        },
    )
    assert reminder.status_code == 201, reminder.text
    assert api.post(f"/api/automations/{reminder.json()['id']}/status", json={"status": "aktiv"}).status_code == 200
    run_due_automations(db_session)
    run_due_automations(db_session)
    assert api.get("/api/tasks", params={"partner_id": partner_id, "q": f"Partnerkontakt {suffix}"}).json()["total"] == 1
    notices = api.get("/api/notifications", params={"empfaenger": "QA Hinweis"})
    assert notices.status_code == 200, notices.text
    assert notices.json()["unread"] >= 1
    titles = {row["title"] for row in notices.json()["items"]}
    assert f"Nachfassen {suffix}" in titles or f"Partnerkontakt {suffix}" in titles
    assert api.get("/api/notifications").json()["items"] == []
    target = notices.json()["items"][0]
    marked = api.post(f"/api/notifications/{target['id']}/read", params={"empfaenger": "QA Hinweis"})
    assert marked.status_code == 200, marked.text
    assert marked.json()["read_at"] is not None
    assert api.post(f"/api/notifications/{target['id']}/read", params={"empfaenger": "Jemand anders"}).status_code == 404
    muted = api.put(
        "/api/notifications/settings",
        json={
            "recipient_label": "QA Stumm",
            "task_reminders": False,
            "service_alerts": True,
            "deal_alerts": True,
            "automation_errors": True,
        },
    )
    assert muted.status_code == 200
    assert muted.json()["task_reminders"] is False


def test_worker_process_and_persistence() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "backend")
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, "-m", "app.worker", "--once"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        timeout=90,
        check=False,
    )
    stdout = completed.stdout.decode("utf-8", errors="replace")
    stderr = completed.stderr.decode("utf-8", errors="replace")
    assert completed.returncode == 0, stderr
    assert "Zeitbasierte Automatisierungen" in stdout
    assert "Ausführungen:" in stdout

    suffix = uuid4().hex[:8]
    with authenticated_client() as client:
        partner_id = create_partner(client, suffix)
        contact_id = create_contact(client, suffix, partner_id)
        created = client.post("/api/campaigns", json=campaign_body(name=f"Persistenz {suffix}"))
        assert created.status_code == 201, created.text
        campaign_id = created.json()["id"]
        assert client.post(f"/api/campaigns/{campaign_id}/audience", json={"contact_id": contact_id}).status_code == 201
    with SessionLocal() as session:
        stored = session.get(MarketingCampaign, UUID(campaign_id))
        assert stored is not None
        assert stored.name == f"Persistenz {suffix}"
        session.execute(delete(CampaignAudienceMember).where(CampaignAudienceMember.campaign_id == stored.id))
        session.execute(delete(CampaignRecipient).where(CampaignRecipient.campaign_id == stored.id))
        session.execute(delete(MarketingCampaign).where(MarketingCampaign.id == stored.id))
        session.execute(delete(CompanyContact).where(CompanyContact.contact_id == UUID(contact_id)))
        session.execute(delete(Contact).where(Contact.id == UUID(contact_id)))
        session.execute(delete(Partner).where(Partner.id == UUID(partner_id)))
        session.commit()
    with SessionLocal() as session:
        assert session.get(MarketingCampaign, UUID(campaign_id)) is None


def test_summary_uses_stored_counts(api: TestClient) -> None:
    summary = api.get("/api/engagement/summary")
    assert summary.status_code == 200, summary.text
    assert summary.json()["contact_days"] >= 1
    meta = api.get("/api/campaigns/meta")
    assert meta.json()["timezone"] == "Europe/Zurich"
    assert "Versand nicht konfiguriert" in meta.json()["delivery_notice"]
