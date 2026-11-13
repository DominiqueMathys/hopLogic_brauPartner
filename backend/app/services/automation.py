"""Server-side automation runner.

Event hooks and the worker share one execution path. A successful action for the
same rule and dedupe key is not repeated. Failures are stored and not retried
for that same key, so a broken rule cannot loop. Nested events are ignored.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.engagement_catalog import TIME_TRIGGERS
from app.models.engagement import AutomationExecution, AutomationRule, Notification, NotificationPreference
from app.models.partner import Partner
from app.models.task import Task
from app.schemas.activity import ActivityWrite
from app.schemas.task import TaskWrite
from app.services.care_queries import (
    ZURICH,
    as_utc,
    deals_without_recent_activity,
    open_tasks_due_soon,
    open_tasks_overdue,
    partners_quiet_since,
    partners_without_orders_since,
    stale_open_tickets,
    zurich_today,
)
from app.services.crm import insert_activity, insert_task

_skip = ContextVar("automation_skip", default=False)
_depth = ContextVar("automation_depth", default=0)

PREFERENCE_FIELD = {
    "task_assigned": "task_reminders",
    "task_due_soon": "task_reminders",
    "task_overdue": "task_reminders",
    "critical_ticket": "service_alerts",
    "deal_assigned": "deal_alerts",
    "automation_failed": "automation_errors",
}


@contextmanager
def paused_automations():
    token = _skip.set(True)
    try:
        yield
    finally:
        _skip.reset(token)


def publish_event(db: Session, trigger: str, *, dedupe_key: str, context: dict) -> None:
    if _skip.get() or _depth.get() > 0:
        return
    token = _depth.set(_depth.get() + 1)
    try:
        rules = db.scalars(
            select(AutomationRule).where(
                AutomationRule.status == "aktiv",
                AutomationRule.trigger_type == trigger,
            )
        ).all()
        for rule in rules:
            if _matches(rule, context):
                attempt_rule(db, rule, dedupe_key, context)
    finally:
        _depth.reset(token)


def run_due_automations(db: Session, now: datetime | None = None) -> int:
    current = as_utc(now or datetime.now(timezone.utc))
    today = zurich_today(current)
    attempts = 0
    rules = db.scalars(
        select(AutomationRule).where(
            AutomationRule.status == "aktiv",
            AutomationRule.trigger_type.in_(TIME_TRIGGERS),
        )
    ).all()
    for rule in rules:
        days = int((rule.trigger_config or {}).get("days") or 1)
        subjects = _time_subjects(db, rule.trigger_type, days, current, today)
        for dedupe_key, context in subjects:
            if attempt_rule(db, rule, dedupe_key, context):
                attempts += 1
    from app.services.engagement import run_care_tasks

    attempts += run_care_tasks(db, current, today)
    return attempts


def attempt_rule(db: Session, rule: AutomationRule, dedupe_key: str, context: dict) -> bool:
    if _already_recorded(db, rule.id, dedupe_key):
        return False
    started = datetime.now(timezone.utc)
    nested = db.begin_nested()
    try:
        result = perform_action(db, rule, context)
        nested.commit()
    except Exception as exc:
        nested.rollback()
        message = str(exc).strip() or exc.__class__.__name__
        _store_execution(
            db,
            rule,
            dedupe_key,
            "fehler",
            started,
            error=message[:500],
            message="Die Aktion wurde zurückgerollt.",
        )
        rule.last_error = message[:500]
        rule.last_run_at = started
        _notify_failure(db, rule, message[:500])
        return True
    _store_execution(
        db,
        rule,
        dedupe_key,
        "erfolg",
        started,
        message="Aktion ausgeführt.",
        task_id=result.get("task_id"),
        notification_id=result.get("notification_id"),
        activity_id=result.get("activity_id"),
    )
    rule.last_error = None
    rule.last_run_at = started
    rule.run_count += 1
    return True


def perform_action(db: Session, rule: AutomationRule, context: dict) -> dict:
    config = rule.action_config or {}
    title = str(config.get("title") or rule.name)
    owner = context.get("owner") or rule.account_owner
    partner_id = context.get("partner_id")
    contact_id = context.get("contact_id")
    if rule.action_type == "create_task":
        due_days = int(config.get("due_days") or 3)
        task = insert_task(
            db,
            TaskWrite(
                title=title,
                description=config.get("description") or f"Erstellt durch die Automatisierung «{rule.name}».",
                account_owner=owner,
                due_at=datetime.now(timezone.utc) + timedelta(days=due_days),
                priority=config.get("priority") or "normal",
                status="offen",
                task_type="intern",
                partner_id=partner_id,
                contact_id=contact_id,
            ),
        )
        task.origin = "automation"
        db.flush()
        notice = _notify(
            db,
            kind="task_assigned",
            recipient=owner,
            title=title,
            body=f"Neue Aufgabe aus «{rule.name}».",
            href=f"/aufgaben/{task.id}/bearbeiten",
            task_id=task.id,
            partner_id=partner_id,
            automation_id=rule.id,
        )
        return {"task_id": task.id, "notification_id": notice.id if notice else None}
    if rule.action_type in {"notify_owner", "create_reminder"}:
        kind = str(config.get("notification_type") or _default_notice(rule.trigger_type))
        notice = _notify(
            db,
            kind=kind,
            recipient=owner,
            title=title,
            body=config.get("description") or rule.description,
            href=context.get("href"),
            partner_id=partner_id,
            task_id=context.get("task_id"),
            automation_id=rule.id,
            deal_id=context.get("deal_id"),
            ticket_id=context.get("ticket_id"),
        )
        if notice is None:
            raise RuntimeError("Die Benachrichtigung hat keine zuständige Person.")
        return {"notification_id": notice.id}
    if rule.action_type == "log_activity":
        if partner_id is None and contact_id is None:
            raise RuntimeError("Die Aktivität braucht einen Partner oder einen Kontakt.")
        activity = insert_activity(
            db,
            ActivityWrite(
                activity_type="gespraechsnotiz",
                title=title,
                description=config.get("description") or f"Protokoll aus der Automatisierung «{rule.name}».",
                occurred_at=datetime.now(timezone.utc),
                account_owner=owner,
                partner_id=partner_id,
                contact_id=contact_id,
            ),
        )
        return {"activity_id": activity.id}
    raise RuntimeError("Die Aktion ist nicht bekannt.")


def _matches(rule: AutomationRule, context: dict) -> bool:
    priority = (rule.trigger_config or {}).get("priority")
    if priority and context.get("priority") != priority:
        return False
    return True


def _time_subjects(db: Session, trigger: str, days: int, now: datetime, today) -> list[tuple[str, dict]]:
    subjects: list[tuple[str, dict]] = []
    if trigger == "no_contact":
        for partner, marker in partners_quiet_since(db, days, today):
            subjects.append(_partner_subject(partner, f"no-contact:{partner.id}:{marker}", "Partnerkontakt planen"))
    elif trigger == "no_order":
        for partner, marker in partners_without_orders_since(db, days, today):
            subjects.append(_partner_subject(partner, f"no-order:{partner.id}:{marker}", "Bestellung nachfassen"))
    elif trigger == "ticket_stale":
        for ticket in stale_open_tickets(db, days, now):
            subjects.append(
                (
                    f"ticket-stale:{ticket.id}:{as_utc(ticket.updated_at).isoformat()}",
                    {
                        "owner": ticket.account_owner,
                        "partner_id": ticket.partner_id,
                        "contact_id": ticket.contact_id,
                        "ticket_id": ticket.id,
                        "href": f"/kundenservice/{ticket.id}",
                        "priority": ticket.priority,
                        "subject_title": ticket.subject,
                    },
                )
            )
    elif trigger == "task_overdue":
        for task in open_tasks_overdue(db, now):
            subjects.append(_task_subject(task, "task_overdue"))
    elif trigger == "task_due_soon":
        for task in open_tasks_due_soon(db, now, days):
            subjects.append(_task_subject(task, "task_due_soon"))
    return subjects


def _partner_subject(partner: Partner, dedupe_key: str, fallback_title: str) -> tuple[str, dict]:
    return dedupe_key, {
        "owner": partner.account_owner,
        "partner_id": partner.id,
        "company_name": partner.company_name,
        "href": f"/vertriebspartner/{partner.id}",
        "subject_title": fallback_title,
    }


def _task_subject(task: Task, kind: str) -> tuple[str, dict]:
    return f"{kind}:{task.id}", {
        "owner": task.account_owner,
        "partner_id": task.partner_id,
        "contact_id": task.contact_id,
        "task_id": task.id,
        "href": f"/aufgaben/{task.id}/bearbeiten",
        "subject_title": task.title,
    }


def _default_notice(trigger: str) -> str:
    if trigger in {"ticket_created", "ticket_priority_changed", "ticket_stale"}:
        return "critical_ticket"
    if trigger in {"deal_created", "deal_stage_changed"}:
        return "deal_assigned"
    if trigger == "task_overdue":
        return "task_overdue"
    if trigger == "task_due_soon":
        return "task_due_soon"
    return "general"


def _already_recorded(db: Session, rule_id: UUID, dedupe_key: str) -> bool:
    existing = db.scalar(
        select(AutomationExecution.id).where(
            AutomationExecution.rule_id == rule_id,
            AutomationExecution.dedupe_key == dedupe_key,
            AutomationExecution.status.in_(("erfolg", "fehler")),
        )
    )
    return existing is not None


def _store_execution(
    db: Session,
    rule: AutomationRule,
    dedupe_key: str,
    status: str,
    started: datetime,
    *,
    message: str | None = None,
    error: str | None = None,
    task_id: UUID | None = None,
    notification_id: UUID | None = None,
    activity_id: UUID | None = None,
) -> None:
    db.add(
        AutomationExecution(
            rule_id=rule.id,
            dedupe_key=dedupe_key,
            status=status,
            message=message,
            error=error,
            started_at=started,
            finished_at=datetime.now(timezone.utc),
            task_id=task_id,
            notification_id=notification_id,
            activity_id=activity_id,
        )
    )
    db.flush()


def allows_notification(db: Session, recipient: str, kind: str) -> bool:
    field = PREFERENCE_FIELD.get(kind)
    if field is None:
        return True
    row = db.scalar(select(NotificationPreference).where(NotificationPreference.recipient_label == recipient))
    if row is None:
        return True
    return bool(getattr(row, field))


def _notify(
    db: Session,
    *,
    kind: str,
    recipient: str | None,
    title: str,
    body: str | None,
    href: str | None,
    task_id: UUID | None = None,
    partner_id: UUID | None = None,
    deal_id: UUID | None = None,
    ticket_id: UUID | None = None,
    automation_id: UUID | None = None,
) -> Notification | None:
    if not recipient:
        return None
    if not allows_notification(db, recipient, kind):
        return None
    row = Notification(
        notification_type=kind,
        title=title[:200],
        body=body,
        recipient_label=recipient,
        href=href,
        task_id=task_id,
        partner_id=partner_id,
        deal_id=deal_id,
        ticket_id=ticket_id,
        automation_id=automation_id,
    )
    db.add(row)
    db.flush()
    return row


def _notify_failure(db: Session, rule: AutomationRule, error: str) -> None:
    if not rule.account_owner:
        return
    try:
        _notify(
            db,
            kind="automation_failed",
            recipient=rule.account_owner,
            title=f"Automatisierung fehlgeschlagen: {rule.name}",
            body=error,
            href=f"/automatisierungen/{rule.id}/protokoll",
            automation_id=rule.id,
        )
    except Exception:
        return


def company_name(db: Session, partner_id: UUID | None) -> str | None:
    if partner_id is None:
        return None
    return db.scalar(select(Partner.company_name).where(Partner.id == partner_id))
