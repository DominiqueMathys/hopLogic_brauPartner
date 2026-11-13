"""Fictional winter campaign, care rule and automation for Ristorante Lago.

Nothing in this seed sends an email or creates an ERP transaction.
"""

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.engagement import (
    AutomationRule,
    CommunicationPreference,
    CustomerCareRule,
    MarketingCampaign,
    MessageTemplate,
    Notification,
)
from app.models.partner import Partner
from app.models.service import CustomerSegment
from app.models.task import Task
from app.schemas.engagement import (
    ActionConfig,
    AutomationWrite,
    CampaignWrite,
    CareRuleWrite,
    PreferenceWrite,
    TemplateWrite,
    TriggerConfig,
)
from app.schemas.task import TaskWrite
from app.seed_crm import CONTACT_KEY, PARTNER_KEY
from app.services.automation import paused_automations
from app.services.crm import CrmServiceError, insert_task
from app.services.engagement import insert_automation, insert_campaign, insert_care_rule, insert_template, save_preference

CAMPAIGN_KEY = "demo-kampagne-winter"
TEMPLATE_KEY = "demo-vorlage-winter"
CARE_KEY = "demo-regel-kontakt"
QUIET_KEY = "demo-auto-kontakt"
DEAL_KEY = "demo-auto-erstkontakt"
NOTICE_KEY = "demo-hinweis-lago"
TASK_KEY = "demo-lago-betreuung"
CAMPAIGN_NAME = "Winter-Sortiment 2026"
OBJECTIVE = "Bestehende Gastronomiepartner über ein saisonales Produktsortiment informieren."
NOTICE_TITLE = "Neue Betreuungsaufgabe für Ristorante Lago"


def seed_demo_engagement(db: Session) -> int:
    with paused_automations():
        return _seed(db)


def _seed(db: Session) -> int:
    partner = db.scalar(select(Partner).where(Partner.demo_key == PARTNER_KEY))
    contact = db.scalar(select(Contact).where(Contact.demo_key == CONTACT_KEY))
    segment = db.scalar(select(CustomerSegment).where(CustomerSegment.demo_key == "demo-segment-gastro"))
    if partner is None or contact is None or segment is None:
        raise CrmServiceError("Die Demo-Daten von Ristorante Lago oder das Gastrosegment fehlen.", 409)

    campaign = _campaign(db, segment.id)
    _template(db)
    save_preference(
        db,
        contact.id,
        PreferenceWrite(
            preferred_channel="telefon",
            email_marketing_allowed=False,
            marketing_rejected=False,
        ),
    )
    _care_rule(db)
    _automation(
        db,
        QUIET_KEY,
        AutomationWrite(
            name="Partnerkontakt nach 30 Tagen",
            description="Fiktive Regel: ohne dokumentierten Kontakt seit 30 Tagen entsteht eine interne Aufgabe. Es wird keine E-Mail versendet.",
            trigger_type="no_contact",
            trigger_config=TriggerConfig(days=30),
            action_type="create_task",
            action_config=ActionConfig(title="Partnerkontakt planen", due_days=3, priority="normal"),
            account_owner="Sandra Lutz",
        ),
        status="aktiv",
    )
    _automation(
        db,
        DEAL_KEY,
        AutomationWrite(
            name="Erstkontakt vorbereiten",
            description="Entwurf: eine neue Verkaufschance erzeugt die Aufgabe Erstkontakt vorbereiten.",
            trigger_type="deal_created",
            trigger_config=TriggerConfig(),
            action_type="create_task",
            action_config=ActionConfig(title="Erstkontakt vorbereiten", due_days=2, priority="hoch"),
            account_owner="Sandra Lutz",
        ),
        status="entwurf",
    )
    task = _task(db, partner.id, contact.id)
    _notice(db, partner.id, task.id)
    db.flush()
    return 8


def _campaign(db: Session, segment_id) -> MarketingCampaign:
    existing = db.scalar(select(MarketingCampaign).where(MarketingCampaign.demo_key == CAMPAIGN_KEY))
    payload = CampaignWrite(
        name=CAMPAIGN_NAME,
        description="Fiktive saisonale Information. Versand nicht konfiguriert.",
        campaign_type="saisonal",
        account_owner="Sandra Lutz",
        starts_on=date(2026, 12, 1),
        ends_on=date(2027, 2, 28),
        objective=OBJECTIVE,
        audience_kind="segment",
        segment_id=segment_id,
        channel="email",
        internal_note="Testdaten. Es wird keine Marketing-E-Mail zugestellt.",
    )
    if existing is None:
        created = insert_campaign(db, payload, is_demo=True, demo_key=CAMPAIGN_KEY)
        created.is_demo = True
        return created
    if existing.activated_at is None:
        existing.name = payload.name
        existing.description = payload.description
        existing.campaign_type = payload.campaign_type
        existing.objective = payload.objective
        existing.audience_kind = "segment"
        existing.segment_id = segment_id
        existing.channel = "email"
        existing.starts_on = payload.starts_on
        existing.ends_on = payload.ends_on
        existing.account_owner = "Sandra Lutz"
        existing.internal_note = payload.internal_note
    existing.is_demo = True
    existing.demo_key = CAMPAIGN_KEY
    return existing


def _template(db: Session) -> MessageTemplate:
    payload = TemplateWrite(
        name="Winter-Sortiment Hinweis",
        subject="Saisonales Sortiment für {{unternehmen}}",
        body=(
            "Guten Tag {{vorname}} {{nachname}}\n\n"
            "dieser Entwurf informiert {{funktion}} von {{unternehmen}} über ein fiktives Wintersortiment. "
            "Die Nachricht wird nicht versendet."
        ),
        channel="email",
    )
    existing = db.scalar(select(MessageTemplate).where(MessageTemplate.demo_key == TEMPLATE_KEY))
    if existing is None:
        created = insert_template(db, payload, is_demo=True, demo_key=TEMPLATE_KEY)
        created.is_demo = True
        return created
    existing.name = payload.name
    existing.subject = payload.subject
    existing.body = payload.body
    existing.channel = "email"
    existing.is_demo = True
    existing.demo_key = TEMPLATE_KEY
    return existing


def _care_rule(db: Session) -> CustomerCareRule:
    payload = CareRuleWrite(
        name="Kein dokumentierter Kontakt seit 30 Tagen",
        description="Vorschlagswert. Die Übersicht verwendet diese Schwelle. Aufgaben erzeugt die zugehörige Automatisierung.",
        rule_kind="no_contact",
        threshold_days=30,
        is_active=True,
        create_tasks=False,
        task_title="Partnerkontakt planen",
        account_owner="Sandra Lutz",
    )
    existing = db.scalar(select(CustomerCareRule).where(CustomerCareRule.demo_key == CARE_KEY))
    if existing is None:
        created = insert_care_rule(db, payload, is_demo=True, demo_key=CARE_KEY)
        created.is_demo = True
        return created
    existing.name = payload.name
    existing.description = payload.description
    existing.rule_kind = "no_contact"
    existing.threshold_days = 30
    existing.is_active = True
    existing.create_tasks = False
    existing.task_title = payload.task_title
    existing.account_owner = "Sandra Lutz"
    existing.is_demo = True
    return existing


def _automation(db: Session, demo_key: str, payload: AutomationWrite, *, status: str) -> AutomationRule:
    existing = db.scalar(select(AutomationRule).where(AutomationRule.demo_key == demo_key))
    if existing is None:
        created = insert_automation(db, payload, is_demo=True, demo_key=demo_key, status=status)
        created.is_demo = True
        return created
    existing.name = payload.name
    existing.description = payload.description
    existing.trigger_type = payload.trigger_type
    existing.trigger_config = payload.trigger_config.model_dump(exclude_none=True)
    existing.action_type = payload.action_type
    existing.action_config = payload.action_config.model_dump(exclude_none=True)
    existing.account_owner = payload.account_owner
    existing.is_demo = True
    existing.demo_key = demo_key
    return existing


def _task(db: Session, partner_id, contact_id) -> Task:
    existing = db.scalar(select(Task).where(Task.demo_key == TASK_KEY))
    due = datetime.now(timezone.utc) + timedelta(days=3)
    if existing is None:
        created = insert_task(
            db,
            TaskWrite(
                title="Partnerkontakt planen",
                description="Fiktive Betreuungsaufgabe für Ristorante Lago. Es wird keine E-Mail versendet.",
                account_owner="Sandra Lutz",
                due_at=due,
                priority="normal",
                status="offen",
                task_type="intern",
                partner_id=partner_id,
                contact_id=contact_id,
            ),
            is_demo=True,
            demo_key=TASK_KEY,
        )
        created.origin = "betreuung"
        created.is_demo = True
        return created
    existing.title = "Partnerkontakt planen"
    existing.status = "offen"
    existing.completed_at = None
    existing.partner_id = partner_id
    existing.contact_id = contact_id
    existing.account_owner = "Sandra Lutz"
    existing.due_at = due
    existing.origin = "betreuung"
    existing.is_demo = True
    return existing


def _notice(db: Session, partner_id, task_id) -> Notification:
    existing = db.scalar(select(Notification).where(Notification.demo_key == NOTICE_KEY))
    if existing is None:
        row = Notification(
            notification_type="task_assigned",
            title=NOTICE_TITLE,
            body="Fiktive interne Meldung. Es wurde keine E-Mail versendet.",
            recipient_label="Sandra Lutz",
            href=f"/aufgaben/{task_id}/bearbeiten",
            task_id=task_id,
            partner_id=partner_id,
            is_demo=True,
            demo_key=NOTICE_KEY,
        )
        db.add(row)
        db.flush()
        return row
    existing.title = NOTICE_TITLE
    existing.recipient_label = "Sandra Lutz"
    existing.href = f"/aufgaben/{task_id}/bearbeiten"
    existing.task_id = task_id
    existing.partner_id = partner_id
    existing.is_demo = True
    return existing
