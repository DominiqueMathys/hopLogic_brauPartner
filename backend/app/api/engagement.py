from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.crm_support import check_page, clean_query, run_write
from app.database import get_db
from app.engagement_catalog import (
    AUTOMATION_ACTIONS,
    AUTOMATION_STATUSES,
    AUTOMATION_TRIGGERS,
    CAMPAIGN_STATUSES,
    CAMPAIGN_TYPES,
    CARE_RULE_KINDS,
    CONSENT_NOTICE,
    DELIVERY_NOTICE,
    MESSAGE_CHANNELS,
    NOTIFICATION_TYPES,
)
from app.schemas.engagement import (
    AudienceAdd,
    AudiencePreview,
    AutomationRead,
    AutomationStatusChange,
    AutomationWrite,
    CampaignList,
    CampaignRead,
    CampaignWrite,
    CareList,
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
    RunDueResult,
    StatusChange,
    TemplatePreview,
    TemplatePreviewRead,
    TemplateRead,
    TemplateWrite,
)
from app.schemas.task import TaskRead
from app.services.automation import run_due_automations
from app.services.care_queries import ZURICH
from app.services.crm import read_tasks
from app.services.engagement import (
    add_audience_member,
    archive_template,
    audience_preview,
    care_overview,
    change_automation_status,
    change_campaign_status,
    create_care_task,
    delete_care_rule,
    duplicate_campaign,
    duplicate_template,
    engagement_summary,
    insert_automation,
    insert_campaign,
    insert_care_rule,
    insert_template,
    list_automations,
    list_care_rules,
    list_executions,
    list_notifications,
    list_templates,
    mark_all_read,
    mark_notification_read,
    notification_summary,
    placeholder_tokens,
    preview_template,
    query_campaigns,
    read_automation,
    read_campaign,
    read_care_rule,
    read_preference,
    read_settings,
    read_template,
    require_campaign,
    require_rule,
    require_template,
    save_preference,
    save_settings,
    suppressed_contacts,
    update_automation,
    update_campaign,
    update_care_rule,
    update_template,
)

campaigns_router = APIRouter(prefix="/campaigns", tags=["kampagnen"])
templates_router = APIRouter(prefix="/templates", tags=["vorlagen"])
care_router = APIRouter(prefix="/care", tags=["partnerbetreuung"])
automations_router = APIRouter(prefix="/automations", tags=["automatisierungen"])
notifications_router = APIRouter(prefix="/notifications", tags=["benachrichtigungen"])
preferences_router = APIRouter(tags=["kommunikation"])
summary_router = APIRouter(prefix="/engagement", tags=["engagement"])


@campaigns_router.get("/meta")
def campaign_meta() -> dict:
    return {
        "types": CAMPAIGN_TYPES,
        "statuses": CAMPAIGN_STATUSES,
        "channels": MESSAGE_CHANNELS,
        "placeholders": placeholder_tokens(),
        "delivery_notice": DELIVERY_NOTICE,
        "consent_notice": CONSENT_NOTICE,
        "timezone": str(ZURICH),
    }


@campaigns_router.get("", response_model=CampaignList)
def get_campaigns(
    q: str | None = None,
    status: str | None = None,
    campaign_type: str | None = None,
    account_owner: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> CampaignList:
    check_page(page, page_size)
    if status and status not in CAMPAIGN_STATUSES:
        status = None
    if campaign_type and campaign_type not in CAMPAIGN_TYPES:
        campaign_type = None
    return query_campaigns(
        db,
        q=clean_query(q),
        status=status,
        campaign_type=campaign_type,
        account_owner=clean_query(account_owner, 120),
        page=page,
        page_size=page_size,
    )


@campaigns_router.post("", response_model=CampaignRead, status_code=201)
def post_campaign(payload: CampaignWrite, db: Session = Depends(get_db)) -> CampaignRead:
    campaign = run_write(db, lambda: insert_campaign(db, payload))
    return read_campaign(db, campaign)


@campaigns_router.get("/{campaign_id}", response_model=CampaignRead)
def get_campaign(campaign_id: UUID, db: Session = Depends(get_db)) -> CampaignRead:
    return read_campaign(db, require_campaign(db, campaign_id))


@campaigns_router.put("/{campaign_id}", response_model=CampaignRead)
def put_campaign(campaign_id: UUID, payload: CampaignWrite, db: Session = Depends(get_db)) -> CampaignRead:
    campaign = run_write(db, lambda: update_campaign(db, campaign_id, payload))
    return read_campaign(db, campaign)


@campaigns_router.post("/{campaign_id}/status", response_model=CampaignRead)
def post_campaign_status(campaign_id: UUID, payload: StatusChange, db: Session = Depends(get_db)) -> CampaignRead:
    campaign = run_write(db, lambda: change_campaign_status(db, campaign_id, payload.status))
    return read_campaign(db, campaign)


@campaigns_router.post("/{campaign_id}/duplicate", response_model=CampaignRead, status_code=201)
def post_duplicate_campaign(campaign_id: UUID, db: Session = Depends(get_db)) -> CampaignRead:
    campaign = run_write(db, lambda: duplicate_campaign(db, campaign_id))
    return read_campaign(db, campaign)


@campaigns_router.get("/{campaign_id}/audience", response_model=AudiencePreview)
def get_audience(campaign_id: UUID, db: Session = Depends(get_db)) -> AudiencePreview:
    return audience_preview(db, campaign_id)


@campaigns_router.post("/{campaign_id}/audience", status_code=201)
def post_audience(campaign_id: UUID, payload: AudienceAdd, db: Session = Depends(get_db)) -> dict[str, str]:
    member = run_write(db, lambda: add_audience_member(db, campaign_id, payload))
    return {"id": str(member.id)}


@campaigns_router.delete("/{campaign_id}/audience/{member_id}", status_code=204)
def delete_audience(campaign_id: UUID, member_id: UUID, db: Session = Depends(get_db)) -> None:
    run_write(db, lambda: remove_audience_member(db, campaign_id, member_id))


@campaigns_router.post("/{campaign_id}/send", status_code=409)
def post_send(campaign_id: UUID, db: Session = Depends(get_db)) -> None:
    require_campaign(db, campaign_id)
    raise HTTPException(status_code=409, detail=DELIVERY_NOTICE)


@templates_router.get("", response_model=list[TemplateRead])
def get_templates(include_archived: bool = False, db: Session = Depends(get_db)) -> list[TemplateRead]:
    return list_templates(db, include_archived=include_archived)


@templates_router.post("", response_model=TemplateRead, status_code=201)
def post_template(payload: TemplateWrite, db: Session = Depends(get_db)) -> TemplateRead:
    template = run_write(db, lambda: insert_template(db, payload))
    return read_template(template)


@templates_router.get("/{template_id}", response_model=TemplateRead)
def get_template(template_id: UUID, db: Session = Depends(get_db)) -> TemplateRead:
    return read_template(require_template(db, template_id))


@templates_router.put("/{template_id}", response_model=TemplateRead)
def put_template(template_id: UUID, payload: TemplateWrite, db: Session = Depends(get_db)) -> TemplateRead:
    template = run_write(db, lambda: update_template(db, template_id, payload))
    return read_template(template)


@templates_router.post("/{template_id}/archive", response_model=TemplateRead)
def post_archive_template(template_id: UUID, db: Session = Depends(get_db)) -> TemplateRead:
    template = run_write(db, lambda: archive_template(db, template_id))
    return read_template(template)


@templates_router.post("/{template_id}/duplicate", response_model=TemplateRead, status_code=201)
def post_duplicate_template(template_id: UUID, db: Session = Depends(get_db)) -> TemplateRead:
    template = run_write(db, lambda: duplicate_template(db, template_id))
    return read_template(template)


@templates_router.post("/{template_id}/preview", response_model=TemplatePreviewRead)
def post_preview(template_id: UUID, payload: TemplatePreview, db: Session = Depends(get_db)) -> TemplatePreviewRead:
    return preview_template(db, template_id, payload)


@care_router.get("/rules", response_model=list[CareRuleRead])
def get_care_rules(db: Session = Depends(get_db)) -> list[CareRuleRead]:
    return list_care_rules(db)


@care_router.post("/rules", response_model=CareRuleRead, status_code=201)
def post_care_rule(payload: CareRuleWrite, db: Session = Depends(get_db)) -> CareRuleRead:
    rule = run_write(db, lambda: insert_care_rule(db, payload))
    return read_care_rule(db, rule)


@care_router.put("/rules/{rule_id}", response_model=CareRuleRead)
def put_care_rule(rule_id: UUID, payload: CareRuleWrite, db: Session = Depends(get_db)) -> CareRuleRead:
    rule = run_write(db, lambda: update_care_rule(db, rule_id, payload))
    return read_care_rule(db, rule)


@care_router.delete("/rules/{rule_id}", status_code=204)
def remove_care_rule(rule_id: UUID, db: Session = Depends(get_db)) -> None:
    run_write(db, lambda: delete_care_rule(db, rule_id))


@care_router.get("/overview", response_model=CareList)
def get_care_overview(
    signal: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> CareList:
    check_page(page, page_size)
    if signal not in {None, "", "contact", "order", "deals", "complaints"}:
        signal = None
    return care_overview(db, signal=signal or None, page=page, page_size=page_size)


@care_router.post("/tasks", response_model=TaskRead, status_code=201)
def post_care_task(payload: CareTaskCreate, db: Session = Depends(get_db)) -> TaskRead:
    task = run_write(db, lambda: create_care_task(db, payload))
    return read_tasks(db, [task])[0]


@care_router.get("/meta")
def care_meta() -> dict:
    return {"kinds": CARE_RULE_KINDS, "timezone": str(ZURICH)}


@automations_router.get("/meta")
def automation_meta() -> dict:
    return {
        "triggers": AUTOMATION_TRIGGERS,
        "actions": AUTOMATION_ACTIONS,
        "statuses": AUTOMATION_STATUSES,
        "timezone": str(ZURICH),
    }


@automations_router.get("", response_model=list[AutomationRead])
def get_automations(db: Session = Depends(get_db)) -> list[AutomationRead]:
    return list_automations(db)


@automations_router.post("", response_model=AutomationRead, status_code=201)
def post_automation(payload: AutomationWrite, db: Session = Depends(get_db)) -> AutomationRead:
    rule = run_write(db, lambda: insert_automation(db, payload))
    return read_automation(rule)


@automations_router.post("/run-due", response_model=RunDueResult)
def post_run_due(db: Session = Depends(get_db)) -> RunDueResult:
    attempts = run_write(db, lambda: run_due_automations(db))
    return RunDueResult(attempts=attempts, timezone=str(ZURICH))


@automations_router.get("/{rule_id}", response_model=AutomationRead)
def get_automation(rule_id: UUID, db: Session = Depends(get_db)) -> AutomationRead:
    return read_automation(require_rule(db, rule_id))


@automations_router.put("/{rule_id}", response_model=AutomationRead)
def put_automation(rule_id: UUID, payload: AutomationWrite, db: Session = Depends(get_db)) -> AutomationRead:
    rule = run_write(db, lambda: update_automation(db, rule_id, payload))
    return read_automation(rule)


@automations_router.post("/{rule_id}/status", response_model=AutomationRead)
def post_automation_status(rule_id: UUID, payload: AutomationStatusChange, db: Session = Depends(get_db)) -> AutomationRead:
    rule = run_write(db, lambda: change_automation_status(db, rule_id, payload.status))
    return read_automation(rule)


@automations_router.get("/{rule_id}/executions", response_model=list[ExecutionRead])
def get_executions(rule_id: UUID, db: Session = Depends(get_db)) -> list[ExecutionRead]:
    return list_executions(db, rule_id)


@notifications_router.get("", response_model=NotificationList)
def get_notifications(
    empfaenger: str | None = None,
    notification_type: str | None = None,
    unread: bool = False,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> NotificationList:
    check_page(page, page_size)
    if notification_type and notification_type not in NOTIFICATION_TYPES:
        notification_type = None
    return list_notifications(
        db,
        recipient=clean_query(empfaenger, 120),
        notification_type=notification_type,
        unread_only=unread,
        page=page,
        page_size=page_size,
    )


@notifications_router.get("/summary", response_model=NotificationSummary)
def get_notification_summary(empfaenger: str | None = None, db: Session = Depends(get_db)) -> NotificationSummary:
    return notification_summary(db, clean_query(empfaenger, 120))


@notifications_router.get("/settings", response_model=PreferenceSettingsRead)
def get_notification_settings(empfaenger: str | None = None, db: Session = Depends(get_db)) -> PreferenceSettingsRead:
    label = clean_query(empfaenger, 120)
    if not label:
        raise HTTPException(status_code=422, detail="Bis Phase 08 braucht die Einstellung einen Anzeigenamen. Es gibt kein Benutzerkonto.")
    return read_settings(db, label)


@notifications_router.put("/settings", response_model=PreferenceSettingsRead)
def put_notification_settings(payload: PreferenceSettingsWrite, db: Session = Depends(get_db)) -> PreferenceSettingsRead:
    return run_write(db, lambda: save_settings(db, payload))


@notifications_router.post("/read-all")
def post_read_all(empfaenger: str = Query(min_length=1), db: Session = Depends(get_db)) -> dict[str, int]:
    count = run_write(db, lambda: mark_all_read(db, clean_query(empfaenger, 120) or ""))
    return {"updated": count}


@notifications_router.post("/{notification_id}/read", response_model=NotificationRead)
def post_read(notification_id: UUID, empfaenger: str = Query(min_length=1), db: Session = Depends(get_db)) -> NotificationRead:
    return run_write(db, lambda: mark_notification_read(db, notification_id, clean_query(empfaenger, 120) or ""))


@preferences_router.get("/contacts/{contact_id}/preferences", response_model=PreferenceRead)
def get_contact_preferences(contact_id: UUID, db: Session = Depends(get_db)) -> PreferenceRead:
    return read_preference(db, contact_id)


@preferences_router.put("/contacts/{contact_id}/preferences", response_model=PreferenceRead)
def put_contact_preferences(contact_id: UUID, payload: PreferenceWrite, db: Session = Depends(get_db)) -> PreferenceRead:
    return run_write(db, lambda: save_preference(db, contact_id, payload))


@preferences_router.get("/preferences/suppressed", response_model=list[PreferenceRead])
def get_suppressed(db: Session = Depends(get_db)) -> list[PreferenceRead]:
    return suppressed_contacts(db)


@summary_router.get("/summary", response_model=EngagementSummary)
def get_engagement_summary(db: Session = Depends(get_db)) -> EngagementSummary:
    return engagement_summary(db)
