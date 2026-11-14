"""Campaigns, templates, consent, care overview and notification inbox."""

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from app.crm_catalog import OPEN_TASK_STATUSES
from app.engagement_catalog import (
    AUTOMATION_TRANSITIONS,
    CAMPAIGN_TRANSITIONS,
    CONSENT_NOTICE,
    DELIVERY_NOTICE,
    FROZEN_AUDIENCE_NOTICE,
    PLACEHOLDERS,
)
from app.models.contact import CompanyContact, Contact
from app.models.engagement import (
    AutomationExecution,
    AutomationRule,
    CampaignAudienceMember,
    CampaignRecipient,
    CareExecution,
    CommunicationPreference,
    CustomerCareRule,
    MarketingCampaign,
    MessageTemplate,
    Notification,
    NotificationPreference,
)
from app.models.partner import Partner
from app.models.service import CustomerSegment
from app.models.task import Task
from app.schemas.engagement import (
    AudienceAdd,
    AudienceMemberRead,
    AudiencePreview,
    AutomationRead,
    AutomationWrite,
    CampaignList,
    CampaignRead,
    CampaignWrite,
    CareList,
    CareRow,
    CareRuleRead,
    CareRuleWrite,
    CareTaskCreate,
    EngagementSummary,
    ExecutionRead,
    NotificationList,
    NotificationRead,
    NotificationSummary,
    PreferenceRead,
    PreferenceSettingsRead,
    PreferenceSettingsWrite,
    PreferenceWrite,
    RecipientRead,
    TemplatePreview,
    TemplatePreviewRead,
    TemplateRead,
    TemplateWrite,
)
from app.schemas.task import TaskWrite
from app.services.care_queries import (
    active_partners,
    as_utc,
    deals_without_recent_activity,
    gap_from,
    last_contact_at,
    last_counted_order_on,
    next_open_task_at,
    open_complaint_count,
    open_deal_count,
    open_task_count,
    open_ticket_count,
    partners_quiet_since,
    partners_without_orders_since,
    stale_open_tickets,
    zurich_today,
)
from app.services.crm import CrmServiceError, insert_task

IDENTITY_NOTICE = (
    "Die Ansicht ist auf einen Namen eingeschränkt. Meldungen anderer Personen werden dabei nicht gemischt."
)
ACCOUNT_NOTICE = "Hinweise für das angemeldete Konto. Meldungen anderer Personen werden nicht angezeigt."
PREVIEW_NOTICE = "Vorschau der aktuellen Zielgruppe. Die Liste wird erst bei der Aktivierung festgehalten."


def render_template(text: str, values: dict[str, str | None]) -> str:
    mapping = {
        "{{vorname}}": values.get("first_name"),
        "{{nachname}}": values.get("last_name"),
        "{{unternehmen}}": values.get("company_name"),
        "{{funktion}}": values.get("job_title"),
    }
    rendered = text
    for token, raw in mapping.items():
        rendered = rendered.replace(token, raw if isinstance(raw, str) else "")
    return rendered


def require_campaign(db: Session, campaign_id: UUID) -> MarketingCampaign:
    campaign = db.get(MarketingCampaign, campaign_id)
    if campaign is None:
        raise CrmServiceError("Die Kampagne wurde nicht gefunden.", 404)
    return campaign


def require_template(db: Session, template_id: UUID) -> MessageTemplate:
    template = db.get(MessageTemplate, template_id)
    if template is None:
        raise CrmServiceError("Die Vorlage wurde nicht gefunden.", 404)
    return template


def require_rule(db: Session, rule_id: UUID) -> AutomationRule:
    rule = db.get(AutomationRule, rule_id)
    if rule is None:
        raise CrmServiceError("Die Automatisierung wurde nicht gefunden.", 404)
    return rule


def require_care_rule(db: Session, rule_id: UUID) -> CustomerCareRule:
    rule = db.get(CustomerCareRule, rule_id)
    if rule is None:
        raise CrmServiceError("Die Betreuungsregel wurde nicht gefunden.", 404)
    return rule


def insert_campaign(db: Session, data: CampaignWrite, *, is_demo: bool = False, demo_key: str | None = None) -> MarketingCampaign:
    _ensure_segment(db, data.segment_id)
    campaign = MarketingCampaign(status="entwurf", is_demo=is_demo, demo_key=demo_key, **data.model_dump())
    db.add(campaign)
    db.flush()
    return campaign


def update_campaign(db: Session, campaign_id: UUID, data: CampaignWrite) -> MarketingCampaign:
    campaign = require_campaign(db, campaign_id)
    if campaign.status == "archiviert":
        raise CrmServiceError("Archivierte Kampagnen können nicht bearbeitet werden.", 409)
    if campaign.activated_at is not None and (
        data.audience_kind != campaign.audience_kind
        or data.segment_id != campaign.segment_id
        or data.channel != campaign.channel
    ):
        raise CrmServiceError("Zielgruppe und Kanal einer aktivierten Kampagne bleiben beim Stand der Aktivierung.", 409)
    _ensure_segment(db, data.segment_id)
    if data.audience_kind != campaign.audience_kind:
        db.execute(delete(CampaignAudienceMember).where(CampaignAudienceMember.campaign_id == campaign.id))
    for field, value in data.model_dump().items():
        setattr(campaign, field, value)
    campaign.updated_at = _now()
    db.flush()
    return campaign


def change_campaign_status(db: Session, campaign_id: UUID, status: str) -> MarketingCampaign:
    campaign = require_campaign(db, campaign_id)
    if status not in CAMPAIGN_TRANSITIONS[campaign.status]:
        raise CrmServiceError("Dieser Kampagnenstatus ist nicht zulässig.", 409)
    if status == "aktiv" and campaign.activated_at is None:
        _freeze_recipients(db, campaign)
        campaign.activated_at = _now()
    campaign.status = status
    if status == "archiviert":
        campaign.archived_at = _now()
    campaign.updated_at = _now()
    db.flush()
    return campaign


def duplicate_campaign(db: Session, campaign_id: UUID) -> MarketingCampaign:
    source = require_campaign(db, campaign_id)
    copy = MarketingCampaign(
        name=f"Kopie von {source.name}"[:160],
        description=source.description,
        campaign_type=source.campaign_type,
        account_owner=source.account_owner,
        starts_on=source.starts_on,
        ends_on=source.ends_on,
        objective=source.objective,
        audience_kind=source.audience_kind,
        segment_id=source.segment_id,
        channel=source.channel,
        budget=source.budget,
        internal_note=source.internal_note,
        status="entwurf",
    )
    db.add(copy)
    db.flush()
    for member in _members(db, source.id):
        db.add(
            CampaignAudienceMember(
                campaign_id=copy.id,
                partner_id=member.partner_id,
                contact_id=member.contact_id,
            )
        )
    db.flush()
    return copy


def add_audience_member(db: Session, campaign_id: UUID, data: AudienceAdd) -> CampaignAudienceMember:
    campaign = _editable_audience(db, campaign_id)
    if campaign.audience_kind == "segment":
        raise CrmServiceError("Ein Kundensegment wird nicht um einzelne Personen ergänzt.", 409)
    if campaign.audience_kind == "partners" and data.partner_id is None:
        raise CrmServiceError("Diese Kampagne verwendet Vertriebspartner.", 409)
    if campaign.audience_kind == "contacts" and data.contact_id is None:
        raise CrmServiceError("Diese Kampagne verwendet Kontaktpersonen.", 409)
    if data.partner_id is not None:
        _require_partner(db, data.partner_id)
    if data.contact_id is not None:
        _require_contact(db, data.contact_id)
    existing = db.scalar(
        select(CampaignAudienceMember).where(
            CampaignAudienceMember.campaign_id == campaign.id,
            CampaignAudienceMember.partner_id == data.partner_id,
            CampaignAudienceMember.contact_id == data.contact_id,
        )
    )
    if existing is not None:
        raise CrmServiceError("Dieser Empfänger ist bereits zugeordnet.", 409)
    member = CampaignAudienceMember(campaign_id=campaign.id, partner_id=data.partner_id, contact_id=data.contact_id)
    db.add(member)
    db.flush()
    return member


def remove_audience_member(db: Session, campaign_id: UUID, member_id: UUID) -> None:
    campaign = _editable_audience(db, campaign_id)
    member = db.get(CampaignAudienceMember, member_id)
    if member is None or member.campaign_id != campaign.id:
        raise CrmServiceError("Die Zuordnung wurde nicht gefunden.", 404)
    db.delete(member)
    db.flush()


def audience_preview(db: Session, campaign_id: UUID) -> AudiencePreview:
    campaign = require_campaign(db, campaign_id)
    members = [_member_read(db, member) for member in _members(db, campaign.id)]
    if campaign.activated_at is not None:
        stored = list(db.scalars(select(CampaignRecipient).where(CampaignRecipient.campaign_id == campaign.id)).all())
        included = [_stored_recipient(row) for row in stored if row.included]
        excluded = [_stored_recipient(row) for row in stored if not row.included]
        notice = FROZEN_AUDIENCE_NOTICE
    else:
        included, excluded = _classify(db, campaign)
        notice = PREVIEW_NOTICE
    return AudiencePreview(
        frozen=campaign.activated_at is not None,
        notice=notice,
        delivery_notice=DELIVERY_NOTICE,
        consent_notice=CONSENT_NOTICE,
        included_count=len(included),
        excluded_count=len(excluded),
        included=included,
        excluded=excluded,
        members=members,
    )


def refuse_delivery() -> None:
    raise CrmServiceError(DELIVERY_NOTICE, 409)


def read_campaign(db: Session, campaign: MarketingCampaign) -> CampaignRead:
    segment_name = None
    if campaign.segment_id is not None:
        segment_name = db.scalar(select(CustomerSegment.name).where(CustomerSegment.id == campaign.segment_id))
    return CampaignRead(
        id=campaign.id,
        name=campaign.name,
        description=campaign.description,
        campaign_type=campaign.campaign_type,
        account_owner=campaign.account_owner,
        starts_on=campaign.starts_on,
        ends_on=campaign.ends_on,
        objective=campaign.objective,
        audience_kind=campaign.audience_kind,
        segment_id=campaign.segment_id,
        segment_name=segment_name,
        channel=campaign.channel,
        budget=None if campaign.budget is None else f"{campaign.budget:.2f}",
        internal_note=campaign.internal_note,
        status=campaign.status,
        allowed_statuses=sorted(CAMPAIGN_TRANSITIONS[campaign.status]),
        activated_at=campaign.activated_at,
        audience_frozen=campaign.activated_at is not None,
        recipient_count=_recipient_count(db, campaign),
        is_demo=campaign.is_demo,
        created_at=campaign.created_at,
        updated_at=campaign.updated_at,
    )


def query_campaigns(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    campaign_type: str | None,
    account_owner: str | None,
    page: int,
    page_size: int,
) -> CampaignList:
    statement = select(MarketingCampaign)
    if q:
        like = f"%{q}%"
        statement = statement.where(or_(MarketingCampaign.name.ilike(like), MarketingCampaign.objective.ilike(like)))
    if status:
        statement = statement.where(MarketingCampaign.status == status)
    else:
        statement = statement.where(MarketingCampaign.status != "archiviert")
    if campaign_type:
        statement = statement.where(MarketingCampaign.campaign_type == campaign_type)
    if account_owner:
        statement = statement.where(MarketingCampaign.account_owner == account_owner)
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(
        statement.order_by(MarketingCampaign.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return CampaignList(
        items=[read_campaign(db, row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


def insert_template(db: Session, data: TemplateWrite, *, is_demo: bool = False, demo_key: str | None = None) -> MessageTemplate:
    template = MessageTemplate(is_demo=is_demo, demo_key=demo_key, **data.model_dump())
    db.add(template)
    db.flush()
    return template


def update_template(db: Session, template_id: UUID, data: TemplateWrite) -> MessageTemplate:
    template = require_template(db, template_id)
    if template.archived_at is not None:
        raise CrmServiceError("Archivierte Vorlagen können nicht bearbeitet werden.", 409)
    for field, value in data.model_dump().items():
        setattr(template, field, value)
    template.updated_at = _now()
    db.flush()
    return template


def archive_template(db: Session, template_id: UUID) -> MessageTemplate:
    template = require_template(db, template_id)
    if template.archived_at is None:
        template.archived_at = _now()
        template.updated_at = template.archived_at
    db.flush()
    return template


def duplicate_template(db: Session, template_id: UUID) -> MessageTemplate:
    source = require_template(db, template_id)
    copy = MessageTemplate(
        name=f"Kopie von {source.name}"[:160],
        subject=source.subject,
        body=source.body,
        channel=source.channel,
    )
    db.add(copy)
    db.flush()
    return copy


def preview_template(db: Session, template_id: UUID, data: TemplatePreview) -> TemplatePreviewRead:
    template = require_template(db, template_id)
    values = {
        "first_name": data.first_name,
        "last_name": data.last_name,
        "company_name": data.company_name,
        "job_title": data.job_title,
    }
    if data.contact_id is not None:
        contact = _require_contact(db, data.contact_id)
        company = _primary_company(db, contact.id)
        values = {
            "first_name": contact.first_name,
            "last_name": contact.last_name,
            "company_name": company,
            "job_title": contact.job_title,
        }
    return TemplatePreviewRead(
        subject=render_template(template.subject, values),
        body=render_template(template.body, values),
        delivery_notice=DELIVERY_NOTICE,
    )


def read_template(template: MessageTemplate) -> TemplateRead:
    return TemplateRead(
        id=template.id,
        name=template.name,
        subject=template.subject,
        body=template.body,
        channel=template.channel,
        is_demo=template.is_demo,
        archived_at=template.archived_at,
        created_at=template.created_at,
        updated_at=template.updated_at,
    )


def list_templates(db: Session, *, include_archived: bool) -> list[TemplateRead]:
    statement = select(MessageTemplate).order_by(MessageTemplate.updated_at.desc())
    if not include_archived:
        statement = statement.where(MessageTemplate.archived_at.is_(None))
    return [read_template(row) for row in db.scalars(statement).all()]


def read_preference(db: Session, contact_id: UUID) -> PreferenceRead:
    _require_contact(db, contact_id)
    row = db.scalar(select(CommunicationPreference).where(CommunicationPreference.contact_id == contact_id))
    if row is None:
        return PreferenceRead(
            contact_id=contact_id,
            preferred_channel="telefon",
            email_marketing_allowed=False,
            marketing_rejected=False,
            consent_on=None,
            consent_source=None,
            consent_evidence=None,
            revoked_on=None,
            notice=CONSENT_NOTICE,
            stored=False,
        )
    return _preference_read(row)


def save_preference(db: Session, contact_id: UUID, data: PreferenceWrite) -> PreferenceRead:
    _require_contact(db, contact_id)
    row = db.scalar(select(CommunicationPreference).where(CommunicationPreference.contact_id == contact_id))
    if row is None:
        row = CommunicationPreference(contact_id=contact_id)
        db.add(row)
    for field, value in data.model_dump().items():
        setattr(row, field, value)
    row.updated_at = _now()
    db.flush()
    return _preference_read(row)


def suppressed_contacts(db: Session) -> list[PreferenceRead]:
    rows = db.scalars(
        select(CommunicationPreference).where(CommunicationPreference.marketing_rejected.is_(True))
    ).all()
    return [_preference_read(row) for row in rows]


def insert_care_rule(db: Session, data: CareRuleWrite, *, is_demo: bool = False, demo_key: str | None = None) -> CustomerCareRule:
    rule = CustomerCareRule(is_demo=is_demo, demo_key=demo_key, **data.model_dump())
    db.add(rule)
    db.flush()
    return rule


def update_care_rule(db: Session, rule_id: UUID, data: CareRuleWrite) -> CustomerCareRule:
    rule = require_care_rule(db, rule_id)
    for field, value in data.model_dump().items():
        setattr(rule, field, value)
    rule.updated_at = _now()
    db.flush()
    return rule


def delete_care_rule(db: Session, rule_id: UUID) -> None:
    rule = require_care_rule(db, rule_id)
    db.execute(delete(CareExecution).where(CareExecution.rule_id == rule.id))
    db.delete(rule)
    db.flush()


def read_care_rule(db: Session, rule: CustomerCareRule) -> CareRuleRead:
    today = zurich_today()
    return CareRuleRead(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        rule_kind=rule.rule_kind,
        threshold_days=rule.threshold_days,
        is_active=rule.is_active,
        create_tasks=rule.create_tasks,
        task_title=rule.task_title,
        account_owner=rule.account_owner,
        is_demo=rule.is_demo,
        match_count=len(care_matches(db, rule, today, _now())),
    )


def list_care_rules(db: Session) -> list[CareRuleRead]:
    rows = db.scalars(select(CustomerCareRule).order_by(CustomerCareRule.name)).all()
    return [read_care_rule(db, row) for row in rows]


def care_overview(db: Session, *, signal: str | None, page: int, page_size: int) -> CareList:
    today = zurich_today()
    contact_days, order_days = _threshold_days(db)
    rows = [_care_row(db, partner, today, contact_days, order_days) for partner in active_partners(db)]
    if signal == "contact":
        rows = [row for row in rows if row.contact_gap]
    elif signal == "order":
        rows = [row for row in rows if row.order_gap]
    elif signal == "deals":
        rows = [row for row in rows if row.has_open_deals]
    elif signal == "complaints":
        rows = [row for row in rows if row.has_open_complaints]
    total = len(rows)
    start = (page - 1) * page_size
    return CareList(
        items=rows[start : start + page_size],
        total=total,
        page=page,
        page_size=page_size,
        contact_days=contact_days,
        order_days=order_days,
    )


def create_care_task(db: Session, data: CareTaskCreate) -> Task:
    _require_partner(db, data.partner_id)
    if data.contact_id is not None:
        _require_contact(db, data.contact_id)
    task = insert_task(
        db,
        TaskWrite(
            title=data.title,
            description="Betreuungsaufgabe aus der Partnerbetreuung.",
            account_owner=data.account_owner,
            due_at=data.due_at,
            priority="normal",
            status="offen",
            task_type="intern",
            partner_id=data.partner_id,
            contact_id=data.contact_id,
        ),
    )
    task.origin = "betreuung"
    db.flush()
    return task


def run_care_tasks(db: Session, now: datetime, today) -> int:
    attempts = 0
    rules = db.scalars(
        select(CustomerCareRule).where(
            CustomerCareRule.is_active.is_(True),
            CustomerCareRule.create_tasks.is_(True),
        )
    ).all()
    for rule in rules:
        for partner, marker, contact_id in care_matches(db, rule, today, now):
            dedupe_key = f"{rule.rule_kind}:{partner.id}:{marker}"
            if _care_recorded(db, rule.id, dedupe_key):
                continue
            started = _now()
            nested = db.begin_nested()
            try:
                task = insert_task(
                    db,
                    TaskWrite(
                        title=rule.task_title,
                        description=f"Erstellt durch die Betreuungsregel «{rule.name}».",
                        account_owner=rule.account_owner or partner.account_owner,
                        due_at=now + timedelta(days=3),
                        priority="normal",
                        status="offen",
                        task_type="intern",
                        partner_id=partner.id,
                        contact_id=contact_id,
                    ),
                )
                task.origin = "betreuung"
                db.flush()
                nested.commit()
            except Exception as exc:
                nested.rollback()
                db.add(
                    CareExecution(
                        rule_id=rule.id,
                        dedupe_key=dedupe_key,
                        status="fehler",
                        error=str(exc)[:500],
                        started_at=started,
                        finished_at=_now(),
                    )
                )
                db.flush()
                attempts += 1
                continue
            db.add(
                CareExecution(
                    rule_id=rule.id,
                    dedupe_key=dedupe_key,
                    status="erfolg",
                    message="Betreuungsaufgabe erstellt.",
                    task_id=task.id,
                    started_at=started,
                    finished_at=_now(),
                )
            )
            db.flush()
            attempts += 1
    return attempts


def care_matches(db: Session, rule: CustomerCareRule, today, now: datetime) -> list[tuple[Partner, str, UUID | None]]:
    if rule.rule_kind == "no_contact":
        return [(partner, marker, None) for partner, marker in partners_quiet_since(db, rule.threshold_days, today)]
    if rule.rule_kind == "no_order":
        return [(partner, marker, None) for partner, marker in partners_without_orders_since(db, rule.threshold_days, today)]
    if rule.rule_kind == "stale_deal":
        grouped: dict[UUID, tuple[Partner, str]] = {}
        for deal in deals_without_recent_activity(db, rule.threshold_days, today):
            partner = db.get(Partner, deal.partner_id)
            if partner is None or partner.archived_at is not None:
                continue
            marker = as_utc(deal.updated_at).isoformat()
            current = grouped.get(partner.id)
            if current is None or marker < current[1]:
                grouped[partner.id] = (partner, marker)
        return [(partner, marker, None) for partner, marker in grouped.values()]
    tickets = []
    for ticket in stale_open_tickets(db, rule.threshold_days, now):
        partner = db.get(Partner, ticket.partner_id)
        if partner is None or partner.archived_at is not None:
            continue
        tickets.append((partner, f"{ticket.id}:{as_utc(ticket.updated_at).isoformat()}", ticket.contact_id))
    return tickets


def insert_automation(db: Session, data: AutomationWrite, *, is_demo: bool = False, demo_key: str | None = None, status: str = "entwurf") -> AutomationRule:
    rule = AutomationRule(
        name=data.name,
        description=data.description,
        trigger_type=data.trigger_type,
        trigger_config=data.trigger_config.model_dump(exclude_none=True),
        action_type=data.action_type,
        action_config=data.action_config.model_dump(exclude_none=True),
        account_owner=data.account_owner,
        status=status,
        is_demo=is_demo,
        demo_key=demo_key,
    )
    db.add(rule)
    db.flush()
    return rule


def update_automation(db: Session, rule_id: UUID, data: AutomationWrite) -> AutomationRule:
    rule = require_rule(db, rule_id)
    if rule.status == "aktiv":
        raise CrmServiceError("Aktive Automatisierungen werden zuerst pausiert.", 409)
    rule.name = data.name
    rule.description = data.description
    rule.trigger_type = data.trigger_type
    rule.trigger_config = data.trigger_config.model_dump(exclude_none=True)
    rule.action_type = data.action_type
    rule.action_config = data.action_config.model_dump(exclude_none=True)
    rule.account_owner = data.account_owner
    rule.updated_at = _now()
    db.flush()
    return rule


def change_automation_status(db: Session, rule_id: UUID, status: str) -> AutomationRule:
    rule = require_rule(db, rule_id)
    if status not in AUTOMATION_TRANSITIONS[rule.status]:
        raise CrmServiceError("Dieser Automatisierungsstatus ist nicht zulässig.", 409)
    rule.status = status
    rule.updated_at = _now()
    db.flush()
    return rule


def read_automation(rule: AutomationRule) -> AutomationRead:
    return AutomationRead(
        id=rule.id,
        name=rule.name,
        description=rule.description,
        trigger_type=rule.trigger_type,
        trigger_config=rule.trigger_config or {},
        action_type=rule.action_type,
        action_config=rule.action_config or {},
        status=rule.status,
        allowed_statuses=sorted(AUTOMATION_TRANSITIONS[rule.status]),
        account_owner=rule.account_owner,
        last_run_at=rule.last_run_at,
        run_count=rule.run_count,
        last_error=rule.last_error,
        is_demo=rule.is_demo,
        created_at=rule.created_at,
        updated_at=rule.updated_at,
    )


def list_automations(db: Session) -> list[AutomationRead]:
    rows = db.scalars(select(AutomationRule).order_by(AutomationRule.updated_at.desc())).all()
    return [read_automation(row) for row in rows]


def list_executions(db: Session, rule_id: UUID) -> list[ExecutionRead]:
    require_rule(db, rule_id)
    rows = db.scalars(
        select(AutomationExecution)
        .where(AutomationExecution.rule_id == rule_id)
        .order_by(AutomationExecution.started_at.desc())
    ).all()
    return [
        ExecutionRead(
            id=row.id,
            rule_id=row.rule_id,
            dedupe_key=row.dedupe_key,
            status=row.status,
            message=row.message,
            error=row.error,
            started_at=row.started_at,
            finished_at=row.finished_at,
            task_id=row.task_id,
            notification_id=row.notification_id,
            activity_id=row.activity_id,
        )
        for row in rows
    ]


def list_notifications(
    db: Session,
    *,
    recipient: str | None,
    notification_type: str | None,
    unread_only: bool,
    page: int,
    page_size: int,
    bound: bool = False,
) -> NotificationList:
    if not recipient:
        return NotificationList(
            items=[],
            total=0,
            unread=0,
            page=page,
            page_size=page_size,
            identity_limited=True,
            notice=IDENTITY_NOTICE,
        )
    statement = select(Notification).where(Notification.recipient_label == recipient)
    if notification_type:
        statement = statement.where(Notification.notification_type == notification_type)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    unread = int(
        db.scalar(
            select(func.count()).select_from(Notification).where(
                Notification.recipient_label == recipient,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )
    rows = db.scalars(
        statement.order_by(Notification.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return NotificationList(
        items=[_notification_read(row) for row in rows],
        total=total,
        unread=unread,
        page=page,
        page_size=page_size,
        identity_limited=not bound,
        notice=ACCOUNT_NOTICE if bound else IDENTITY_NOTICE,
    )


def notification_summary(db: Session, recipient: str | None, *, bound: bool = False) -> NotificationSummary:
    if not recipient:
        return NotificationSummary(unread=0, identity_limited=True, notice=IDENTITY_NOTICE)
    unread = int(
        db.scalar(
            select(func.count()).select_from(Notification).where(
                Notification.recipient_label == recipient,
                Notification.read_at.is_(None),
            )
        )
        or 0
    )
    return NotificationSummary(unread=unread, identity_limited=not bound, notice=ACCOUNT_NOTICE if bound else IDENTITY_NOTICE)


def mark_notification_read(db: Session, notification_id: UUID, recipient: str) -> NotificationRead:
    row = _notification_for(db, notification_id, recipient)
    if row.read_at is None:
        row.read_at = _now()
        db.flush()
    return _notification_read(row)


def mark_all_read(db: Session, recipient: str) -> int:
    if not recipient:
        raise CrmServiceError(IDENTITY_NOTICE, 422)
    rows = db.scalars(
        select(Notification).where(Notification.recipient_label == recipient, Notification.read_at.is_(None))
    ).all()
    now = _now()
    for row in rows:
        row.read_at = now
    db.flush()
    return len(rows)


def read_settings(db: Session, recipient: str) -> PreferenceSettingsRead:
    if not recipient:
        raise CrmServiceError(IDENTITY_NOTICE, 422)
    row = db.scalar(select(NotificationPreference).where(NotificationPreference.recipient_label == recipient))
    if row is None:
        return PreferenceSettingsRead(
            recipient_label=recipient,
            task_reminders=True,
            service_alerts=True,
            deal_alerts=True,
            automation_errors=True,
            notice=IDENTITY_NOTICE,
        )
    return _settings_read(row)


def save_settings(db: Session, data: PreferenceSettingsWrite) -> PreferenceSettingsRead:
    row = db.scalar(select(NotificationPreference).where(NotificationPreference.recipient_label == data.recipient_label))
    if row is None:
        row = NotificationPreference(recipient_label=data.recipient_label)
        db.add(row)
    row.task_reminders = data.task_reminders
    row.service_alerts = data.service_alerts
    row.deal_alerts = data.deal_alerts
    row.automation_errors = data.automation_errors
    row.updated_at = _now()
    db.flush()
    return _settings_read(row)


def engagement_summary(db: Session) -> EngagementSummary:
    today = zurich_today()
    contact_days, _order_days = _threshold_days(db)
    now = _now()
    active_campaigns = int(
        db.scalar(select(func.count()).select_from(MarketingCampaign).where(MarketingCampaign.status == "aktiv")) or 0
    )
    care_tasks = int(
        db.scalar(
            select(func.count()).select_from(Task).where(
                Task.origin.in_(("betreuung", "automation")),
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.due_at >= now,
            )
        )
        or 0
    )
    overdue = int(
        db.scalar(
            select(func.count()).select_from(Task).where(
                Task.status.in_(OPEN_TASK_STATUSES),
                Task.due_at < now,
            )
        )
        or 0
    )
    active_automations = int(
        db.scalar(select(func.count()).select_from(AutomationRule).where(AutomationRule.status == "aktiv")) or 0
    )
    return EngagementSummary(
        active_campaigns=active_campaigns,
        care_tasks=care_tasks,
        partners_without_contact=len(partners_quiet_since(db, contact_days, today)),
        contact_days=contact_days,
        overdue_tasks=overdue,
        active_automations=active_automations,
    )


def placeholder_tokens() -> list[str]:
    return list(PLACEHOLDERS)


def _freeze_recipients(db: Session, campaign: MarketingCampaign) -> None:
    moment = _now()
    seen: set[UUID] = set()
    for contact, partner_id, company in _candidate_contacts(db, campaign):
        if contact.id in seen:
            continue
        seen.add(contact.id)
        reason = _exclusion_reason(db, campaign, contact)
        db.add(
            CampaignRecipient(
                campaign_id=campaign.id,
                contact_id=contact.id,
                partner_id=partner_id,
                first_name=contact.first_name,
                last_name=contact.last_name,
                company_name=company,
                job_title=contact.job_title or "",
                included=reason is None,
                exclusion_reason=reason,
                frozen_at=moment,
            )
        )
    db.flush()


def _classify(db: Session, campaign: MarketingCampaign) -> tuple[list[RecipientRead], list[RecipientRead]]:
    included: list[RecipientRead] = []
    excluded: list[RecipientRead] = []
    seen: set[UUID] = set()
    for contact, partner_id, company in _candidate_contacts(db, campaign):
        if contact.id in seen:
            continue
        seen.add(contact.id)
        reason = _exclusion_reason(db, campaign, contact)
        row = RecipientRead(
            contact_id=contact.id,
            partner_id=partner_id,
            name=f"{contact.first_name} {contact.last_name}",
            company_name=company,
            job_title=contact.job_title or "",
            included=reason is None,
            exclusion_reason=reason,
        )
        if reason is None:
            included.append(row)
        else:
            excluded.append(row)
    return included, excluded


def _candidate_contacts(db: Session, campaign: MarketingCampaign) -> list[tuple[Contact, UUID | None, str]]:
    found: list[tuple[Contact, UUID | None, str]] = []
    if campaign.audience_kind == "segment" and campaign.segment_id is not None:
        from app.services.service_desk import segment_partners

        for partner in segment_partners(db, campaign.segment_id):
            found.extend(_contacts_of_partner(db, partner.id))
        return found
    for member in _members(db, campaign.id):
        if member.partner_id is not None:
            found.extend(_contacts_of_partner(db, member.partner_id))
        elif member.contact_id is not None:
            contact = db.get(Contact, member.contact_id)
            if contact is not None and contact.archived_at is None:
                found.append((contact, _primary_partner_id(db, contact.id), _primary_company(db, contact.id)))
    return found


def _contacts_of_partner(db: Session, partner_id: UUID) -> list[tuple[Contact, UUID, str]]:
    company = db.scalar(select(Partner.company_name).where(Partner.id == partner_id)) or ""
    rows = db.execute(
        select(Contact)
        .join(CompanyContact, CompanyContact.contact_id == Contact.id)
        .where(
            CompanyContact.partner_id == partner_id,
            Contact.archived_at.is_(None),
            Contact.status == "aktiv",
        )
        .order_by(Contact.last_name, Contact.first_name)
    ).scalars()
    return [(contact, partner_id, company) for contact in rows]


def _exclusion_reason(db: Session, campaign: MarketingCampaign, contact: Contact) -> str | None:
    preference = db.scalar(select(CommunicationPreference).where(CommunicationPreference.contact_id == contact.id))
    if preference is not None and preference.marketing_rejected:
        return "Marketingkommunikation abgelehnt"
    if campaign.channel == "email":
        if preference is None or not preference.email_marketing_allowed:
            return "Keine dokumentierte E-Mail-Einwilligung"
        if not contact.email:
            return "Keine E-Mail-Adresse"
    return None


def _recipient_count(db: Session, campaign: MarketingCampaign) -> int:
    if campaign.activated_at is not None:
        return int(
            db.scalar(
                select(func.count()).select_from(CampaignRecipient).where(
                    CampaignRecipient.campaign_id == campaign.id,
                    CampaignRecipient.included.is_(True),
                )
            )
            or 0
        )
    included, _excluded = _classify(db, campaign)
    return len(included)


def _stored_recipient(row: CampaignRecipient) -> RecipientRead:
    return RecipientRead(
        contact_id=row.contact_id,
        partner_id=row.partner_id,
        name=f"{row.first_name} {row.last_name}".strip(),
        company_name=row.company_name,
        job_title=row.job_title,
        included=row.included,
        exclusion_reason=row.exclusion_reason,
    )


def _member_read(db: Session, member: CampaignAudienceMember) -> AudienceMemberRead:
    if member.partner_id is not None:
        label = db.scalar(select(Partner.company_name).where(Partner.id == member.partner_id)) or "Vertriebspartner"
    else:
        contact = db.get(Contact, member.contact_id)
        label = f"{contact.first_name} {contact.last_name}" if contact else "Kontakt"
    return AudienceMemberRead(id=member.id, partner_id=member.partner_id, contact_id=member.contact_id, label=label)


def _members(db: Session, campaign_id: UUID) -> list[CampaignAudienceMember]:
    return list(
        db.scalars(select(CampaignAudienceMember).where(CampaignAudienceMember.campaign_id == campaign_id)).all()
    )


def _editable_audience(db: Session, campaign_id: UUID) -> MarketingCampaign:
    campaign = require_campaign(db, campaign_id)
    if campaign.activated_at is not None:
        raise CrmServiceError("Die Empfängerliste einer aktivierten Kampagne ist festgehalten.", 409)
    if campaign.status == "archiviert":
        raise CrmServiceError("Archivierte Kampagnen können nicht verändert werden.", 409)
    return campaign


def _care_row(db: Session, partner: Partner, today, contact_days: int, order_days: int) -> CareRow:
    last_contact = last_contact_at(db, partner.id)
    last_order = last_counted_order_on(db, partner.id)
    complaints = open_complaint_count(db, partner.id)
    deals = open_deal_count(db, partner.id)
    return CareRow(
        partner_id=partner.id,
        company_name=partner.company_name,
        account_owner=partner.account_owner,
        last_contact_at=last_contact,
        last_order_on=last_order,
        open_tasks=open_task_count(db, partner.id),
        open_tickets=open_ticket_count(db, partner.id),
        open_deals=deals,
        next_activity_at=next_open_task_at(db, partner.id),
        contact_gap=gap_from(today, last_contact) >= contact_days,
        order_gap=gap_from(today, last_order) >= order_days,
        has_open_deals=deals > 0,
        has_open_complaints=complaints > 0,
    )


def _threshold_days(db: Session) -> tuple[int, int]:
    contact = db.scalar(
        select(func.min(CustomerCareRule.threshold_days)).where(
            CustomerCareRule.is_active.is_(True),
            CustomerCareRule.rule_kind == "no_contact",
        )
    )
    order = db.scalar(
        select(func.min(CustomerCareRule.threshold_days)).where(
            CustomerCareRule.is_active.is_(True),
            CustomerCareRule.rule_kind == "no_order",
        )
    )
    return int(contact or 30), int(order or 60)


def _care_recorded(db: Session, rule_id: UUID, dedupe_key: str) -> bool:
    existing = db.scalar(
        select(CareExecution.id).where(
            CareExecution.rule_id == rule_id,
            CareExecution.dedupe_key == dedupe_key,
            CareExecution.status.in_(("erfolg", "fehler")),
        )
    )
    return existing is not None


def _preference_read(row: CommunicationPreference) -> PreferenceRead:
    return PreferenceRead(
        contact_id=row.contact_id,
        preferred_channel=row.preferred_channel,
        email_marketing_allowed=row.email_marketing_allowed,
        marketing_rejected=row.marketing_rejected,
        consent_on=row.consent_on,
        consent_source=row.consent_source,
        consent_evidence=row.consent_evidence,
        revoked_on=row.revoked_on,
        notice=CONSENT_NOTICE,
        stored=True,
    )


def _notification_read(row: Notification) -> NotificationRead:
    return NotificationRead(
        id=row.id,
        notification_type=row.notification_type,
        title=row.title,
        body=row.body,
        recipient_label=row.recipient_label,
        href=row.href,
        read_at=row.read_at,
        is_demo=row.is_demo,
        created_at=row.created_at,
    )


def _notification_for(db: Session, notification_id: UUID, recipient: str) -> Notification:
    row = db.get(Notification, notification_id)
    if row is None or not recipient or row.recipient_label != recipient:
        raise CrmServiceError("Die Benachrichtigung wurde nicht gefunden.", 404)
    return row


def _settings_read(row: NotificationPreference) -> PreferenceSettingsRead:
    return PreferenceSettingsRead(
        recipient_label=row.recipient_label,
        task_reminders=row.task_reminders,
        service_alerts=row.service_alerts,
        deal_alerts=row.deal_alerts,
        automation_errors=row.automation_errors,
        notice=IDENTITY_NOTICE,
    )


def _ensure_segment(db: Session, segment_id: UUID | None) -> None:
    if segment_id is None:
        return
    if db.get(CustomerSegment, segment_id) is None:
        raise CrmServiceError("Das Kundensegment wurde nicht gefunden.", 404)


def _require_partner(db: Session, partner_id: UUID) -> Partner:
    partner = db.get(Partner, partner_id)
    if partner is None or partner.archived_at is not None:
        raise CrmServiceError("Der Vertriebspartner wurde nicht gefunden.", 404)
    return partner


def _require_contact(db: Session, contact_id: UUID) -> Contact:
    contact = db.get(Contact, contact_id)
    if contact is None or contact.archived_at is not None:
        raise CrmServiceError("Die Kontaktperson wurde nicht gefunden.", 404)
    return contact


def _primary_company(db: Session, contact_id: UUID) -> str:
    name = db.scalar(
        select(Partner.company_name)
        .join(CompanyContact, CompanyContact.partner_id == Partner.id)
        .where(CompanyContact.contact_id == contact_id)
        .order_by(CompanyContact.is_primary.desc())
    )
    return name or ""


def _primary_partner_id(db: Session, contact_id: UUID) -> UUID | None:
    return db.scalar(
        select(CompanyContact.partner_id)
        .where(CompanyContact.contact_id == contact_id)
        .order_by(CompanyContact.is_primary.desc())
    )


def _now() -> datetime:
    return datetime.now(timezone.utc)
