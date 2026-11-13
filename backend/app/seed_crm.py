"""Fictional contact, activity and task for the Ristorante Lago case.

Every record is marked as test data. Giulia Bernasconi is not a real person
and Ristorante Lago is not a customer of Liechtensteiner Brauhaus.
No email address, phone number or consent is stored for this contact.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.activity import Activity
from app.models.contact import CompanyContact, Contact
from app.models.partner import Partner
from app.models.task import Task
from app.schemas.activity import ActivityWrite
from app.schemas.contact import CompanyLinkWrite, ContactWrite
from app.schemas.task import TaskWrite
from app.services.crm import (
    CrmServiceError,
    apply_contact,
    ensure_contact_email,
    insert_activity,
    insert_contact,
    insert_task,
    link_company,
    set_primary_company,
)
from app.services.crm import ACTIVITY_FIELDS, TASK_FIELDS

CONTACT_KEY = "demo-giulia-bernasconi"
ACTIVITY_KEY = "demo-giulia-telefonat"
TASK_KEY = "demo-giulia-sortiment"
PARTNER_KEY = "demo-ristorante-lago"
DEMO_CONTACT_NOTE = "Testdatensatz. Keine echte Person und keine Kundenbeziehung des Liechtensteiner Brauhauses."
ACTIVITY_TEXT = (
    "Telefonischer Austausch mit Giulia Bernasconi über eine mögliche Erweiterung des Biersortiments."
)
TASK_TITLE = "Getränkehändler kontaktieren und Sortimentsanpassung für Ristorante Lago prüfen."


def _contact_data() -> ContactWrite:
    return ContactWrite(
        first_name="Giulia",
        last_name="Bernasconi",
        job_title="Inhaberin",
        account_owner="Sandra Lutz",
        preferred_language="de",
        preferred_channel="telefon",
        lifecycle_phase="kunde",
        lead_status="keiner",
        status="aktiv",
        notes=DEMO_CONTACT_NOTE,
        processing_basis="nicht_dokumentiert",
        processing_basis_note="Keine Einwilligung erfasst. Fiktiver Testdatensatz, keine echte Person.",
    )


def _upsert_contact(db: Session, partner_id) -> Contact:
    data = _contact_data()
    existing = db.scalar(select(Contact).where(Contact.demo_key == CONTACT_KEY))
    if existing is None:
        data.companies = [CompanyLinkWrite(partner_id=partner_id, is_primary=True)]
        return insert_contact(db, data, is_demo=True, demo_key=CONTACT_KEY)
    archived_at = existing.archived_at
    ensure_contact_email(db, data.email, exclude_id=existing.id)
    apply_contact(existing, data)
    existing.is_demo = True
    existing.demo_key = CONTACT_KEY
    existing.archived_at = archived_at
    link = db.scalar(
        select(CompanyContact).where(
            CompanyContact.contact_id == existing.id,
            CompanyContact.partner_id == partner_id,
        )
    )
    if link is None and archived_at is None:
        link_company(db, existing.id, partner_id, True)
    elif link is not None and not link.is_primary:
        set_primary_company(db, existing.id, partner_id)
    db.flush()
    return existing


def _upsert_activity(db: Session, contact_id, partner_id) -> Activity:
    data = ActivityWrite(
        activity_type="telefonat",
        title="Telefonat zum Biersortiment",
        description=ACTIVITY_TEXT,
        occurred_at=datetime(2026, 11, 10, 9, 0, tzinfo=timezone.utc),
        account_owner="Sandra Lutz",
        contact_id=contact_id,
        partner_id=partner_id,
    )
    existing = db.scalar(select(Activity).where(Activity.demo_key == ACTIVITY_KEY))
    if existing is None:
        return insert_activity(db, data, is_demo=True, demo_key=ACTIVITY_KEY)
    archived_at = existing.archived_at
    for field in ACTIVITY_FIELDS:
        setattr(existing, field, getattr(data, field))
    existing.is_demo = True
    existing.demo_key = ACTIVITY_KEY
    existing.archived_at = archived_at
    existing.updated_at = datetime.now(timezone.utc)
    db.flush()
    return existing


def _demo_due() -> datetime:
    moment = datetime.now(timezone.utc) + timedelta(days=3)
    return moment.replace(hour=9, minute=0, second=0, microsecond=0)


def _upsert_task(db: Session, contact_id, partner_id, activity_id) -> Task:
    data = TaskWrite(
        title=TASK_TITLE,
        description="Folgeaufgabe zum fiktiven Telefonat. Testdatensatz, keine echte Betreuung.",
        account_owner="Sandra Lutz",
        due_at=_demo_due(),
        priority="hoch",
        status="offen",
        task_type="anruf",
        partner_id=partner_id,
        contact_id=contact_id,
        activity_id=activity_id,
    )
    existing = db.scalar(select(Task).where(Task.demo_key == TASK_KEY))
    if existing is None:
        return insert_task(db, data, is_demo=True, demo_key=TASK_KEY)
    for field in TASK_FIELDS:
        setattr(existing, field, getattr(data, field))
    existing.completed_at = None
    existing.is_demo = True
    existing.demo_key = TASK_KEY
    existing.updated_at = datetime.now(timezone.utc)
    db.flush()
    return existing


def seed_demo_crm(db: Session) -> int:
    partner = db.scalar(select(Partner).where(Partner.demo_key == PARTNER_KEY))
    if partner is None:
        raise CrmServiceError(
            "Ristorante Lago fehlt. Zuerst die Partner-Testdaten laden.",
            409,
        )
    contact = _upsert_contact(db, partner.id)
    activity = _upsert_activity(db, contact.id, partner.id)
    _upsert_task(db, contact.id, partner.id, activity.id)
    return 3
