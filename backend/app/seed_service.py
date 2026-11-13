"""Fictional complaint for Ristorante Lago.

The ticket documents a damaged delivery. It does not create a replacement
delivery, a credit note, or any other ERP transaction.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.partner import Partner
from app.models.sales import Order, OrderItem
from app.models.service import ServiceTicket
from app.models.task import Task
from app.schemas.service import ConditionWrite, SegmentWrite, TicketTaskCreate, TicketWrite
from app.seed_crm import CONTACT_KEY, PARTNER_KEY
from app.seed_sales import ORDER_KEY
from app.services.crm import CrmServiceError
from app.services.service_desk import add_task, insert_segment, insert_ticket, update_segment

TICKET_KEY = "demo-lago-reklamation"
TICKET_NUMBER = "DEMO-SRV-1001"
TASK_KEY = "demo-lago-reklamation-task"
SEGMENT_GASTRO = "demo-segment-gastro"
SEGMENT_COMPLAINTS = "demo-segment-reklamationen"
SUBJECT = "Beschädigte Bierlieferung"
DESCRIPTION = "Bei der letzten Lieferung wurden mehrere beschädigte Flaschen festgestellt."
TASK_TITLE = "Beschädigte Lieferung prüfen und Ersatzlieferung mit Logistik abklären."


def _ticket_payload(partner_id, contact_id, order_id, product_ids: list) -> TicketWrite:
    return TicketWrite(
        subject=SUBJECT,
        category="beschaedigte_lieferung",
        description=DESCRIPTION,
        partner_id=partner_id,
        contact_id=contact_id,
        order_id=order_id,
        product_ids=product_ids,
        priority="hoch",
        account_owner="Sandra Lutz",
        due_on=(datetime.now(timezone.utc) + timedelta(days=5)).date(),
        internal_remark=(
            "Fiktive Reklamation. Eine dokumentierte Lösung erzeugt keine Ersatzlieferung "
            "und keine Gutschrift im ERP."
        ),
    )


def _segments() -> tuple[tuple[str, SegmentWrite], ...]:
    gastro = SegmentWrite(
        name="Aktive Gastronomiepartner",
        description="Partner vom Typ Restaurant mit Status aktiv. Die Zugehörigkeit wird bei der Abfrage berechnet.",
        match_mode="all",
        conditions=[
            ConditionWrite(field_name="partner_type", operator="eq", value="restaurant"),
            ConditionWrite(field_name="status", operator="eq", value="aktiv"),
        ],
    )
    complaints = SegmentWrite(
        name="Partner mit offenen Reklamationen",
        description="Partner mit mindestens einem offenen Service-Ticket. Keine gespeicherte Partnerliste.",
        match_mode="all",
        conditions=[ConditionWrite(field_name="open_tickets", operator="gte", value="1")],
    )
    return ((SEGMENT_GASTRO, gastro), (SEGMENT_COMPLAINTS, complaints))


def seed_demo_service(db: Session) -> int:
    partner = db.scalar(select(Partner).where(Partner.demo_key == PARTNER_KEY))
    contact = db.scalar(select(Contact).where(Contact.demo_key == CONTACT_KEY))
    order = db.scalar(select(Order).where(Order.demo_key == ORDER_KEY))
    if partner is None or contact is None or order is None:
        raise CrmServiceError("Die Demo-Bestellung von Ristorante Lago fehlt. Zuerst die Verkaufsdaten laden.", 409)
    product_ids = list(db.scalars(select(OrderItem.product_id).where(OrderItem.order_id == order.id)).all())
    payload = _ticket_payload(partner.id, contact.id, order.id, product_ids)
    ticket = db.scalar(select(ServiceTicket).where(ServiceTicket.demo_key == TICKET_KEY))
    if ticket is None:
        ticket = insert_ticket(
            db,
            payload,
            is_demo=True,
            demo_key=TICKET_KEY,
            number=TICKET_NUMBER,
            status="in_bearbeitung",
        )
    else:
        ticket.subject = payload.subject
        ticket.category = payload.category
        ticket.description = payload.description
        ticket.partner_id = partner.id
        ticket.contact_id = contact.id
        ticket.order_id = order.id
        ticket.priority = "hoch"
        ticket.account_owner = "Sandra Lutz"
        ticket.due_on = payload.due_on
        ticket.internal_remark = payload.internal_remark
        ticket.status = "in_bearbeitung"
        ticket.resolved_at = None
        ticket.closed_at = None
        ticket.is_demo = True
        ticket.ticket_number = TICKET_NUMBER
        from app.services.service_desk import _replace_products

        _replace_products(db, ticket.id, product_ids)
        db.flush()
    task = db.scalar(select(Task).where(Task.demo_key == TASK_KEY))
    if task is None:
        task = add_task(
            db,
            ticket.id,
            TicketTaskCreate(
                title=TASK_TITLE,
                due_at=datetime.now(timezone.utc) + timedelta(days=3),
                priority="hoch",
                description="Fiktive Folgeaufgabe. Es wird keine Ersatzlieferung im ERP ausgelöst.",
                account_owner="Sandra Lutz",
                changed_by="Sandra Lutz",
            ),
        )
        task.is_demo = True
        task.demo_key = TASK_KEY
    else:
        task.title = TASK_TITLE
        task.status = "offen"
        task.completed_at = None
        task.ticket_id = ticket.id
        task.partner_id = partner.id
        task.contact_id = contact.id
        task.account_owner = "Sandra Lutz"
        task.priority = "hoch"
        task.is_demo = True
    db.flush()
    for key, data in _segments():
        from app.models.service import CustomerSegment

        existing = db.scalar(select(CustomerSegment).where(CustomerSegment.demo_key == key))
        if existing is None:
            created = insert_segment(db, data, is_demo=True, demo_key=key)
            created.is_demo = True
            created.demo_key = key
        else:
            update_segment(db, existing.id, data)
            existing.is_demo = True
            existing.demo_key = key
    db.flush()
    return 4
