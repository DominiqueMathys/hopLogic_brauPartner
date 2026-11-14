"""Reporting figures calculated from stored CRM rows.

CRM order volume is the stored order value, not invoiced ERP revenue.
Lost deals are never counted as won deals. Marketing open, click and delivery
rates are omitted because no send or tracking data is stored.
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.access import REPORT_SECTIONS
from app.crm_catalog import OPEN_TASK_STATUSES
from app.models.activity import Activity
from app.models.engagement import CampaignRecipient, MarketingCampaign
from app.models.partner import Partner
from app.models.sales import Deal, Order, OrderItem, Product
from app.models.service import ServiceTicket
from app.models.task import Task
from app.sales_catalog import CLOSED_DEAL_STAGES, COUNTED_ORDER_STATUSES, OPEN_DEAL_STAGES, ORDER_STATUSES
from app.service_catalog import COMPLAINT_CATEGORIES, OPEN_TICKET_STATUSES

ZURICH = ZoneInfo("Europe/Zurich")
CENT = Decimal("0.01")
TENTH = Decimal("0.1")

DEFINITIONS = {
    "active_partners": "Aktive Vertriebspartner sind nicht archiviert und haben den Status aktiv. Der Zeitraum ändert diesen Bestand nicht.",
    "new_partners": "Neue Vertriebspartner sind im Zeitraum erstellt und nicht archiviert.",
    "open_deals": "Offene Verkaufschancen stehen nicht auf gewonnen oder verloren und sind nicht archiviert.",
    "pipeline_value": "Pipeline-Wert ist die Summe der gespeicherten geschätzten Werte offener Verkaufschancen in CHF.",
    "weighted_pipeline": "Gewichteter Pipeline-Wert ist die Summe aus geschätztem Wert mal gespeicherter Wahrscheinlichkeit.",
    "won_deals": "Gewonnene Deals haben die Phase gewonnen und ein Abschlussdatum im Zeitraum.",
    "lost_deals": "Verlorene Deals haben die Phase verloren und ein Abschlussdatum im Zeitraum. Sie zählen nicht als gewonnen.",
    "close_rate": "Abschlussquote = gewonnene Deals / (gewonnene + verlorene) im Zeitraum. Ohne abgeschlossene Deals bleibt die Quote leer.",
    "order_volume": (
        "CRM-Bestellwert ist die Summe der gespeicherten Positionsbruttobeträge "
        f"({', '.join(COUNTED_ORDER_STATUSES)}). Entwürfe und Stornierungen zählen nicht. Das ist kein fakturierter ERP-Umsatz."
    ),
    "order_count": "Gezählt werden Bestellungen in den Status, die in den Bestellwert einfliessen.",
    "average_order": "Durchschnittlicher Bestellwert = CRM-Bestellwert / Anzahl dieser Bestellungen.",
    "cancelled_orders": "Stornierte Bestellungen werden separat gezeigt und sind im Bestellwert nicht enthalten.",
    "open_tickets": "Offene Tickets haben einen offenen Status. Der Zeitraum ändert diesen Bestand nicht.",
    "ticket_duration": "Bearbeitungsdauer = Zeitpunkt gelöst, sonst geschlossen, minus Erstellungszeitpunkt. Nur Tickets, die im Zeitraum gelöst oder geschlossen wurden.",
    "overdue_tasks": "Überfällige Aufgaben sind offen oder in Bearbeitung und vor jetzt fällig.",
    "task_duration": "Erledigungsdauer = Zeitpunkt erledigt minus Erstellungszeitpunkt, für Aufgaben, die im Zeitraum erledigt wurden.",
    "pipeline_history": "Es gibt keine historische Pipeline-Momentaufnahme. Die Monatsreihe zeigt den heutigen geschätzten Wert der in diesem Monat erstellten Deals.",
    "product_category": "Der Positionswert ist gespeichert. Die Kategorie ist die aktuelle Produktkategorie, weil Positionen keine eigene Kategorie speichern.",
    "marketing_tracking": "Öffnungs-, Klick- und Zustellquoten fehlen, weil kein Versand- und kein Trackingdatum gespeichert ist.",
    "campaign_links": "Aktivitäten und Aufgaben haben keine gespeicherte Kampagnenverknüpfung. Folgeaufgaben werden deshalb nicht als Zahl erfunden.",
    "campaign_filters": "Kampagnen haben keinen Vertriebspartner. Filter für Partner, Region und Partnertyp gelten dort nicht. Der Zuständigkeitsfilter gilt.",
    "order_owner": "Bei Bestellungen gilt die zuständige Person des Vertriebspartners, weil die Bestellung selbst kein Zuständigkeitsfeld hat.",
}


def _today() -> date:
    return datetime.now(ZURICH).date()


def _money(value: Decimal) -> str:
    return str(value.quantize(CENT, rounding=ROUND_HALF_UP))


def _hours(delta: timedelta) -> Decimal:
    seconds = Decimal(delta.days * 86400) + Decimal(delta.seconds) + (Decimal(delta.microseconds) / Decimal(1000000))
    return (seconds / Decimal(3600)).quantize(TENTH, rounding=ROUND_HALF_UP)


def _local_date(value: datetime) -> date:
    if value.tzinfo is None:
        value = value.replace(tzinfo=ZURICH)
    return value.astimezone(ZURICH).date()


def _in_dates(value: date | None, start: date, end: date) -> bool:
    return value is not None and start <= value <= end


def _in_stamp(value: datetime | None, start: date, end: date) -> bool:
    return value is not None and _in_dates(_local_date(value), start, end)


def _month(value: date) -> str:
    return f"{value.year:04d}-{value.month:02d}"


def _months(start: date, end: date) -> list[str]:
    keys: list[str] = []
    year, month = start.year, start.month
    while (year, month) <= (end.year, end.month):
        keys.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            month = 1
            year += 1
    return keys


def resolve_period(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    end = date_to or _today()
    start = date_from or (end - timedelta(days=365))
    if start > end:
        raise ValueError("Der Zeitraum beginnt nach seinem Ende.")
    if (end - start).days > 366 * 5:
        raise ValueError("Der Zeitraum darf höchstens fünf Jahre umfassen.")
    return start, end


def build_report(
    db: Session,
    *,
    date_from: date | None,
    date_to: date | None,
    partner_id: UUID | None,
    region: str | None,
    partner_type: str | None,
    owner: str | None,
    allowed: set[str],
) -> dict[str, object]:
    start, end = resolve_period(date_from, date_to)
    sections = [section for section in REPORT_SECTIONS if section in allowed]
    partners = list(db.scalars(select(Partner)).all())
    deals = list(db.scalars(select(Deal)).all())
    orders = list(db.scalars(select(Order)).all())
    items = list(db.scalars(select(OrderItem)).all())
    products = {row.id: row for row in db.scalars(select(Product)).all()}
    tickets = list(db.scalars(select(ServiceTicket)).all())
    tasks = list(db.scalars(select(Task)).all())
    activities = list(db.scalars(select(Activity)).all())
    campaigns = list(db.scalars(select(MarketingCampaign)).all())
    recipients = list(db.scalars(select(CampaignRecipient)).all())

    partner_by_id = {row.id: row for row in partners}

    def base_partner(row: Partner) -> bool:
        if row.archived_at is not None:
            return False
        if partner_id is not None and row.id != partner_id:
            return False
        if region and row.region != region:
            return False
        if partner_type and row.partner_type != partner_type:
            return False
        return True

    def partner_selected(row: Partner) -> bool:
        return base_partner(row) and (not owner or (row.account_owner or "") == owner)

    selected_partners = [row for row in partners if partner_selected(row)]
    selected_ids = {row.id for row in selected_partners}
    base_ids = {row.id for row in partners if base_partner(row)}

    def deal_ok(row: Deal) -> bool:
        if row.archived_at is not None or row.partner_id not in base_ids:
            return False
        return not owner or (row.account_owner or "") == owner

    def order_ok(row: Order) -> bool:
        if row.archived_at is not None or row.partner_id not in base_ids:
            return False
        partner = partner_by_id.get(row.partner_id)
        return partner is not None and (not owner or (partner.account_owner or "") == owner)

    def ticket_ok(row: ServiceTicket) -> bool:
        if row.partner_id not in base_ids:
            return False
        return not owner or (row.account_owner or "") == owner

    def task_ok(row: Task) -> bool:
        if row.partner_id is not None and row.partner_id not in base_ids:
            return False
        if partner_id is not None and row.partner_id != partner_id:
            return False
        return not owner or (row.account_owner or "") == owner

    def activity_ok(row: Activity) -> bool:
        if row.archived_at is not None:
            return False
        if row.partner_id is not None and row.partner_id not in base_ids:
            return False
        if partner_id is not None and row.partner_id != partner_id:
            return False
        if (region or partner_type) and row.partner_id not in base_ids:
            return False
        return not owner or (row.account_owner or "") == owner

    chosen_deals = [row for row in deals if deal_ok(row)]
    chosen_orders = [row for row in orders if order_ok(row)]
    chosen_tickets = [row for row in tickets if ticket_ok(row)]
    chosen_tasks = [row for row in tasks if task_ok(row)]
    chosen_activities = [row for row in activities if activity_ok(row)]
    order_ids = {row.id for row in chosen_orders}
    items_by_order: dict[UUID, list[OrderItem]] = defaultdict(list)
    for item in items:
        if item.order_id in order_ids:
            items_by_order[item.order_id].append(item)

    open_deals = [row for row in chosen_deals if row.stage in OPEN_DEAL_STAGES]
    won = [row for row in chosen_deals if row.stage == "gewonnen" and _in_dates(row.closed_on, start, end)]
    lost = [row for row in chosen_deals if row.stage == "verloren" and _in_dates(row.closed_on, start, end)]
    counted = [row for row in chosen_orders if row.status in COUNTED_ORDER_STATUSES and _in_dates(row.ordered_on, start, end)]
    cancelled = [row for row in chosen_orders if row.status == "storniert" and _in_dates(row.ordered_on, start, end)]
    period_orders = [row for row in chosen_orders if _in_dates(row.ordered_on, start, end)]

    def line_gross(rows: list[Order]) -> Decimal:
        total = Decimal("0")
        for row in rows:
            total += sum((item.line_gross for item in items_by_order.get(row.id, [])), Decimal("0"))
        return total

    volume = line_gross(counted)
    pipeline = sum((row.estimated_value for row in open_deals), Decimal("0"))
    weighted = sum((row.estimated_value * row.probability / Decimal(100) for row in open_deals), Decimal("0"))
    close = None
    if won or lost:
        close = (Decimal(len(won)) / Decimal(len(won) + len(lost)) * Decimal(100)).quantize(TENTH, rounding=ROUND_HALF_UP)

    created_tickets = [row for row in chosen_tickets if _in_stamp(row.created_at, start, end)]
    resolved_tickets = []
    durations: list[Decimal] = []
    for row in chosen_tickets:
        finished = row.resolved_at or row.closed_at
        if row.status in {"geloest", "geschlossen"} and _in_stamp(finished, start, end) and finished is not None:
            resolved_tickets.append(row)
            if finished >= row.created_at:
                durations.append(_hours(finished - row.created_at))
    open_tickets = [row for row in chosen_tickets if row.status in OPEN_TICKET_STATUSES]
    critical = [row for row in open_tickets if row.priority == "kritisch"]
    overdue = [row for row in chosen_tasks if row.status in OPEN_TASK_STATUSES and row.due_at < datetime.now(ZURICH)]
    completed = [row for row in chosen_tasks if row.status == "erledigt" and _in_stamp(row.completed_at, start, end)]
    task_hours = [
        _hours(row.completed_at - row.created_at)
        for row in completed
        if row.completed_at is not None and row.completed_at >= row.created_at
    ]
    new_partners = [row for row in selected_partners if _in_stamp(row.created_at, start, end)]
    active_partners = [row for row in selected_partners if row.status == "aktiv"]

    month_keys = _months(start, end)
    kpis: list[dict[str, object]] = []
    charts: list[dict[str, object]] = []
    tables: list[dict[str, object]] = []
    notices = [
        DEFINITIONS["order_volume"],
        DEFINITIONS["close_rate"],
        DEFINITIONS["marketing_tracking"],
        DEFINITIONS["order_owner"],
    ]
    if partner_id or region or partner_type:
        notices.append(DEFINITIONS["campaign_filters"])

    def add_kpi(section: str, key: str, label: str, value: str | None, unit: str, note: str) -> None:
        if section in allowed:
            kpis.append({"section": section, "key": key, "label": label, "value": value, "unit": unit, "note": note})

    def add_chart(section: str, key: str, title: str, kind: str, unit: str, points: list[dict[str, object]], note: str) -> None:
        if section in allowed:
            charts.append(
                {"section": section, "key": key, "title": title, "kind": kind, "unit": unit, "points": points, "note": note}
            )

    def add_table(section: str, key: str, title: str, columns: list[dict[str, str]], rows: list[dict[str, str]], note: str) -> None:
        if section in allowed:
            tables.append({"section": section, "key": key, "title": title, "columns": columns, "rows": rows, "note": note})

    def count_points(pairs: list[tuple[str, int]]) -> list[dict[str, object]]:
        return [{"label": label, "count": count, "amount": None} for label, count in pairs]

    def amount_points(pairs: list[tuple[str, Decimal]]) -> list[dict[str, object]]:
        return [{"label": label, "count": None, "amount": _money(amount)} for label, amount in pairs]

    def month_counts(rows: list[date]) -> list[dict[str, object]]:
        bucket = {key: 0 for key in month_keys}
        for value in rows:
            key = _month(value)
            if key in bucket:
                bucket[key] += 1
        return count_points(list(bucket.items()))

    add_kpi("overview", "active_partners", "Aktive Vertriebspartner", str(len(active_partners)), "count", DEFINITIONS["active_partners"])
    add_kpi("overview", "new_partners", "Neue Vertriebspartner", str(len(new_partners)), "count", DEFINITIONS["new_partners"])
    add_kpi("overview", "open_deals", "Offene Verkaufschancen", str(len(open_deals)), "count", DEFINITIONS["open_deals"])
    add_kpi("overview", "pipeline", "Pipeline-Wert", _money(pipeline), "chf", DEFINITIONS["pipeline_value"])
    add_kpi("overview", "won_deals", "Gewonnene Verkaufschancen", str(len(won)), "count", DEFINITIONS["won_deals"])
    add_kpi("overview", "close_rate", "Abschlussquote", None if close is None else str(close), "percent", DEFINITIONS["close_rate"])
    add_kpi("overview", "order_volume", "CRM-Bestellwert", _money(volume), "chf", DEFINITIONS["order_volume"])
    add_kpi("overview", "order_count", "Anzahl Bestellungen", str(len(counted)), "count", DEFINITIONS["order_count"])
    add_kpi(
        "overview",
        "average_order",
        "Durchschnittlicher Bestellwert",
        None if not counted else _money(volume / Decimal(len(counted))),
        "chf",
        DEFINITIONS["average_order"],
    )
    add_kpi("overview", "open_tickets", "Offene Service-Tickets", str(len(open_tickets)), "count", DEFINITIONS["open_tickets"])
    add_kpi(
        "overview",
        "ticket_duration",
        "Durchschnittliche Ticketbearbeitungsdauer",
        None if not durations else str((sum(durations, Decimal("0")) / Decimal(len(durations))).quantize(TENTH, rounding=ROUND_HALF_UP)),
        "hours",
        DEFINITIONS["ticket_duration"],
    )
    add_kpi("overview", "overdue_tasks", "Überfällige Aufgaben", str(len(overdue)), "count", DEFINITIONS["overdue_tasks"])

    stage_counts: dict[str, int] = defaultdict(int)
    stage_values: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in chosen_deals:
        if row.stage in OPEN_DEAL_STAGES or (row.stage in CLOSED_DEAL_STAGES and _in_dates(row.closed_on, start, end)):
            stage_counts[row.stage] += 1
            stage_values[row.stage] += row.estimated_value
    stage_order = ["neuer_lead", "erstkontakt", "bedarf", "angebot", "verhandlung", "gewonnen", "verloren"]
    add_kpi("sales", "weighted_pipeline", "Gewichteter Pipeline-Wert", _money(weighted), "chf", DEFINITIONS["weighted_pipeline"])
    add_kpi("sales", "won_deals", "Gewonnene Deals", str(len(won)), "count", DEFINITIONS["won_deals"])
    add_kpi("sales", "lost_deals", "Verlorene Deals", str(len(lost)), "count", DEFINITIONS["lost_deals"])
    add_kpi("sales", "close_rate", "Abschlussquote", None if close is None else str(close), "percent", DEFINITIONS["close_rate"])
    created_deals = [row for row in chosen_deals if _in_stamp(row.created_at, start, end)]
    add_kpi(
        "sales",
        "average_deal",
        "Durchschnittlicher Deal-Wert",
        None if not created_deals else _money(sum((row.estimated_value for row in created_deals), Decimal("0")) / Decimal(len(created_deals))),
        "chf",
        "Durchschnitt der gespeicherten Schätzwerte von Deals, die im Zeitraum erstellt wurden.",
    )
    add_chart(
        "sales",
        "deals_by_stage",
        "Deals nach Verkaufsphase",
        "bar",
        "count",
        count_points([(stage, stage_counts[stage]) for stage in stage_order]),
        "Offene Phasen sind der aktuelle Bestand. Gewonnen und verloren sind auf den Zeitraum begrenzt.",
    )
    add_chart(
        "sales",
        "value_by_stage",
        "Deal-Wert nach Verkaufsphase",
        "bar",
        "chf",
        amount_points([(stage, stage_values[stage]) for stage in stage_order]),
        "Summe der gespeicherten Schätzwerte.",
    )
    add_chart(
        "sales",
        "new_deals_month",
        "Neue Deals pro Monat",
        "line",
        "count",
        month_counts([_local_date(row.created_at) for row in created_deals]),
        "Erstellungszeitpunkt in Europe/Zurich.",
    )
    add_chart(
        "sales",
        "won_deals_month",
        "Gewonnene Deals pro Monat",
        "line",
        "count",
        month_counts([row.closed_on for row in won if row.closed_on is not None]),
        DEFINITIONS["won_deals"],
    )
    created_value: dict[str, Decimal] = {key: Decimal("0") for key in month_keys}
    for row in created_deals:
        key = _month(_local_date(row.created_at))
        if key in created_value:
            created_value[key] += row.estimated_value
    add_chart(
        "sales",
        "pipeline_month",
        "Geschätzter Wert neu erstellter Deals",
        "line",
        "chf",
        amount_points(list(created_value.items())),
        DEFINITIONS["pipeline_history"],
    )
    owners: dict[str, list[Deal]] = defaultdict(list)
    for row in open_deals:
        owners[row.account_owner or "Ohne Zuordnung"].append(row)
    add_table(
        "sales",
        "deals_by_owner",
        "Offene Deals nach zuständiger Person",
        [{"key": "owner", "label": "Zuständig"}, {"key": "count", "label": "Anzahl"}, {"key": "amount", "label": "Geschätzter Wert CHF"}],
        [
            {
                "owner": name,
                "count": str(len(rows)),
                "amount": _money(sum((item.estimated_value for item in rows), Decimal("0"))),
            }
            for name, rows in sorted(owners.items(), key=lambda item: sum((row.estimated_value for row in item[1]), Decimal("0")), reverse=True)
        ],
        "Aktueller Bestand der offenen Verkaufschancen.",
    )

    def partner_groups(attribute: str) -> list[dict[str, object]]:
        bucket: dict[str, int] = defaultdict(int)
        for row in selected_partners:
            bucket[getattr(row, attribute) or "Ohne Angabe"] += 1
        return count_points(sorted(bucket.items()))

    add_chart("partners", "by_region", "Vertriebspartner nach Region", "bar", "count", partner_groups("region"), "Nicht archivierte Partner im Filter.")
    add_chart("partners", "by_industry", "Vertriebspartner nach Branche", "bar", "count", partner_groups("industry"), "Nicht archivierte Partner im Filter.")
    add_chart("partners", "by_status", "Vertriebspartner nach Status", "donut", "count", partner_groups("status"), "Nicht archivierte Partner im Filter.")
    add_chart(
        "partners",
        "new_month",
        "Neue Partner pro Monat",
        "line",
        "count",
        month_counts([_local_date(row.created_at) for row in new_partners]),
        DEFINITIONS["new_partners"],
    )
    volume_by_partner: dict[UUID, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in counted:
        volume_by_partner[row.partner_id] += sum((item.line_gross for item in items_by_order.get(row.id, [])), Decimal("0"))
    without_order = [row for row in active_partners if volume_by_partner.get(row.id, Decimal("0")) == 0]
    complaint_ids = {
        row.partner_id
        for row in open_tickets
        if row.category in COMPLAINT_CATEGORIES
    }
    with_complaints = [row for row in selected_partners if row.id in complaint_ids]
    ranking = sorted(selected_partners, key=lambda row: volume_by_partner.get(row.id, Decimal("0")), reverse=True)
    open_deals_by_partner: dict[UUID, int] = defaultdict(int)
    for row in open_deals:
        open_deals_by_partner[row.partner_id] += 1
    open_tickets_by_partner: dict[UUID, int] = defaultdict(int)
    for row in open_tickets:
        open_tickets_by_partner[row.partner_id] += 1
    add_kpi("partners", "without_order", "Partner ohne Bestellung im Zeitraum", str(len(without_order)), "count", "Aktive Partner ohne gezählte Bestellung im Zeitraum.")
    add_kpi("partners", "with_complaints", "Partner mit offenen Reklamationen", str(len(with_complaints)), "count", "Offene Tickets in einer Reklamationskategorie.")
    add_table(
        "partners",
        "comparison",
        "Partnervergleich",
        [
            {"key": "company", "label": "Vertriebspartner"},
            {"key": "region", "label": "Region"},
            {"key": "type", "label": "Typ"},
            {"key": "status", "label": "Status"},
            {"key": "owner", "label": "Zuständig"},
            {"key": "volume", "label": "CRM-Bestellwert CHF"},
            {"key": "deals", "label": "Offene Deals"},
            {"key": "tickets", "label": "Offene Tickets"},
        ],
        [
            {
                "company": row.company_name,
                "region": row.region or "",
                "type": row.partner_type,
                "status": row.status,
                "owner": row.account_owner or "",
                "volume": _money(volume_by_partner.get(row.id, Decimal("0"))),
                "deals": str(open_deals_by_partner.get(row.id, 0)),
                "tickets": str(open_tickets_by_partner.get(row.id, 0)),
            }
            for row in ranking[:100]
        ],
        "Der Bestellwert verwendet gespeicherte Positionen der gezählten Status im Zeitraum.",
    )
    add_table(
        "partners",
        "high_volume",
        "Hoher CRM-Bestellwert",
        [{"key": "company", "label": "Vertriebspartner"}, {"key": "volume", "label": "CRM-Bestellwert CHF"}],
        [
            {"company": row.company_name, "volume": _money(volume_by_partner.get(row.id, Decimal("0")))}
            for row in ranking[:5]
            if volume_by_partner.get(row.id, Decimal("0")) > 0
        ],
        "Die fünf höchsten CRM-Bestellwerte im Filter. Kein ERP-Umsatz.",
    )

    volume_month: dict[str, Decimal] = {key: Decimal("0") for key in month_keys}
    for row in counted:
        key = _month(row.ordered_on)
        if key in volume_month:
            volume_month[key] += sum((item.line_gross for item in items_by_order.get(row.id, [])), Decimal("0"))
    status_counts = {status: 0 for status in ORDER_STATUSES}
    for row in period_orders:
        status_counts[row.status] = status_counts.get(row.status, 0) + 1
    product_qty: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    product_value: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    category_value: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    for row in counted:
        for item in items_by_order.get(row.id, []):
            product_qty[item.product_name] += item.quantity
            product_value[item.product_name] += item.line_gross
            product = products.get(item.product_id)
            category_value[product.category if product is not None else "unbekannt"] += item.line_gross
    add_kpi("orders", "order_volume", "CRM-Bestellwert", _money(volume), "chf", DEFINITIONS["order_volume"])
    add_kpi("orders", "order_count", "Anzahl Bestellungen", str(len(counted)), "count", DEFINITIONS["order_count"])
    add_kpi(
        "orders",
        "average_order",
        "Durchschnittlicher Bestellwert",
        None if not counted else _money(volume / Decimal(len(counted))),
        "chf",
        DEFINITIONS["average_order"],
    )
    add_kpi("orders", "cancelled", "Stornierte Bestellungen", str(len(cancelled)), "count", DEFINITIONS["cancelled_orders"])
    add_kpi("orders", "cancelled_volume", "Stornierter Positionswert", _money(line_gross(cancelled)), "chf", DEFINITIONS["cancelled_orders"])
    add_chart("orders", "volume_month", "Bestellwert nach Monat", "line", "chf", amount_points(list(volume_month.items())), DEFINITIONS["order_volume"])
    partner_bars = ranking[:8]
    add_chart(
        "orders",
        "volume_partner",
        "Bestellwert nach Vertriebspartner",
        "bar",
        "chf",
        amount_points([(row.company_name, volume_by_partner.get(row.id, Decimal("0"))) for row in partner_bars]),
        DEFINITIONS["order_volume"],
    )
    add_chart(
        "orders",
        "by_status",
        "Bestellungen nach Status",
        "donut",
        "count",
        [{"label": status, "count": status_counts[status], "amount": None, "counted": status in COUNTED_ORDER_STATUSES} for status in ORDER_STATUSES],
        "Entwurf und storniert fliessen nicht in den Bestellwert ein. Die übrigen Status schon.",
    )
    frequent = sorted(product_qty.items(), key=lambda item: item[1], reverse=True)[:8]
    add_table(
        "orders",
        "products",
        "Häufig bestellte Produkte",
        [{"key": "product", "label": "Produkt"}, {"key": "quantity", "label": "Menge"}, {"key": "amount", "label": "CRM-Bestellwert CHF"}],
        [{"product": name, "quantity": str(qty.quantize(Decimal("0.001"))), "amount": _money(product_value[name])} for name, qty in frequent],
        "Menge und Wert aus den gespeicherten Positionen gezählter Bestellungen.",
    )
    add_chart(
        "orders",
        "by_category",
        "Bestellwert nach Produktkategorie",
        "bar",
        "chf",
        amount_points(sorted(category_value.items())),
        DEFINITIONS["product_category"],
    )

    def ticket_group(attribute: str) -> list[dict[str, object]]:
        bucket: dict[str, int] = defaultdict(int)
        for row in created_tickets:
            bucket[getattr(row, attribute) or ""] += 1
        return count_points(sorted(bucket.items()))

    add_chart("service", "by_category", "Tickets nach Kategorie", "bar", "count", ticket_group("category"), "Tickets, die im Zeitraum erstellt wurden.")
    add_chart("service", "by_priority", "Tickets nach Priorität", "donut", "count", ticket_group("priority"), "Tickets, die im Zeitraum erstellt wurden.")
    add_chart("service", "by_status", "Tickets nach Status", "donut", "count", ticket_group("status"), "Aktueller Status der im Zeitraum erstellten Tickets.")
    add_chart(
        "service",
        "new_month",
        "Neue Tickets pro Monat",
        "line",
        "count",
        month_counts([_local_date(row.created_at) for row in created_tickets]),
        "Erstellungszeitpunkt in Europe/Zurich.",
    )
    add_chart(
        "service",
        "resolved_month",
        "Gelöste Tickets pro Monat",
        "line",
        "count",
        month_counts([_local_date(row.resolved_at or row.closed_at) for row in resolved_tickets if (row.resolved_at or row.closed_at) is not None]),
        DEFINITIONS["ticket_duration"],
    )
    add_kpi(
        "service",
        "ticket_duration",
        "Durchschnittliche Bearbeitungsdauer",
        None if not durations else str((sum(durations, Decimal("0")) / Decimal(len(durations))).quantize(TENTH, rounding=ROUND_HALF_UP)),
        "hours",
        DEFINITIONS["ticket_duration"],
    )
    add_kpi("service", "critical", "Offene kritische Tickets", str(len(critical)), "count", "Aktueller Bestand mit Priorität kritisch und offenem Status.")
    partner_ticket_counts: dict[str, int] = defaultdict(int)
    for row in created_tickets:
        partner = partner_by_id.get(row.partner_id)
        partner_ticket_counts[partner.company_name if partner is not None else "Unbekannt"] += 1
    add_chart(
        "service",
        "by_partner",
        "Tickets pro Vertriebspartner",
        "bar",
        "count",
        count_points(sorted(partner_ticket_counts.items(), key=lambda item: item[1], reverse=True)[:8]),
        "Im Zeitraum erstellte Tickets.",
    )

    visible_campaigns = [
        row
        for row in campaigns
        if row.status != "archiviert" and (not owner or (row.account_owner or "") == owner) and _in_stamp(row.created_at, start, end)
    ]
    active_campaigns = [row for row in campaigns if row.status == "aktiv" and (not owner or (row.account_owner or "") == owner)]
    type_counts: dict[str, int] = defaultdict(int)
    for row in visible_campaigns:
        type_counts[row.campaign_type] += 1
    campaign_ids = {row.id for row in visible_campaigns}
    recipient_count = sum(1 for row in recipients if row.campaign_id in campaign_ids)
    add_kpi("marketing", "campaigns", "Kampagnen", str(len(visible_campaigns)), "count", "Nicht archivierte Kampagnen, die im Zeitraum erstellt wurden.")
    add_kpi("marketing", "active_campaigns", "Aktive Kampagnen", str(len(active_campaigns)), "count", "Aktueller Bestand mit Status aktiv.")
    add_kpi("marketing", "recipients", "Zugeordnete Kontakte", str(recipient_count), "count", "Gespeicherte Empfängerzeilen der gezählten Kampagnen. Entwürfe können 0 haben, solange die Zielgruppe nicht festgehalten ist.")
    add_kpi("marketing", "followups", "Erstellte Folgeaufgaben", None, "count", DEFINITIONS["campaign_links"])
    add_kpi("marketing", "activities", "Dokumentierte Kampagnenaktivitäten", None, "count", DEFINITIONS["campaign_links"])
    add_chart("marketing", "by_type", "Kampagnen nach Typ", "donut", "count", count_points(sorted(type_counts.items())), "Kampagnen aus der Kennzahl Kampagnen.")
    notices.append(DEFINITIONS["marketing_tracking"])
    notices.append(DEFINITIONS["campaign_links"])

    period_activities = [row for row in chosen_activities if _in_stamp(row.occurred_at, start, end)]
    type_activity: dict[str, int] = defaultdict(int)
    for row in period_activities:
        type_activity[row.activity_type] += 1
    open_tasks = [row for row in chosen_tasks if row.status in OPEN_TASK_STATUSES]
    task_owners: dict[str, int] = defaultdict(int)
    for row in open_tasks:
        task_owners[row.account_owner or "Ohne Zuordnung"] += 1
    add_chart(
        "work",
        "activities_month",
        "Aktivitäten pro Monat",
        "line",
        "count",
        month_counts([_local_date(row.occurred_at) for row in period_activities]),
        "Nicht archivierte Aktivitäten im Zeitraum.",
    )
    add_chart("work", "activities_type", "Aktivitäten nach Typ", "donut", "count", count_points(sorted(type_activity.items())), "Nicht archivierte Aktivitäten im Zeitraum.")
    add_kpi("work", "completed_tasks", "Erledigte Aufgaben", str(len(completed)), "count", "Status erledigt und Erledigung im Zeitraum.")
    add_kpi("work", "open_tasks", "Offene Aufgaben", str(len(open_tasks)), "count", "Aktueller Bestand offen oder in Bearbeitung.")
    add_kpi("work", "overdue_tasks", "Überfällige Aufgaben", str(len(overdue)), "count", DEFINITIONS["overdue_tasks"])
    add_kpi(
        "work",
        "task_duration",
        "Durchschnittliche Aufgabenerledigungsdauer",
        None if not task_hours else str((sum(task_hours, Decimal("0")) / Decimal(len(task_hours))).quantize(TENTH, rounding=ROUND_HALF_UP)),
        "hours",
        DEFINITIONS["task_duration"],
    )
    add_chart(
        "work",
        "tasks_owner",
        "Offene Aufgaben nach zuständiger Person",
        "bar",
        "count",
        count_points(sorted(task_owners.items(), key=lambda item: item[1], reverse=True)),
        "Aktueller Bestand.",
    )

    options = {
        "regions": sorted({row.region for row in partners if row.archived_at is None and row.region}),
        "partner_types": sorted({row.partner_type for row in partners if row.archived_at is None and row.partner_type}),
        "owners": sorted(
            {
                *(row.account_owner for row in partners if row.account_owner),
                *(row.account_owner for row in deals if row.account_owner),
                *(row.account_owner for row in tasks if row.account_owner),
                *(row.account_owner for row in tickets if row.account_owner),
            }
        ),
        "partners": [
            {"id": str(row.id), "label": row.company_name}
            for row in sorted((row for row in partners if row.archived_at is None), key=lambda item: item.company_name)[:200]
        ],
    }
    return {
        "generated_at": datetime.now(ZURICH),
        "period_from": start,
        "period_to": end,
        "filters": {
            "partner_id": str(partner_id) if partner_id else None,
            "region": region,
            "partner_type": partner_type,
            "owner": owner,
        },
        "sections": sections,
        "definitions": DEFINITIONS,
        "kpis": kpis,
        "charts": charts,
        "tables": tables,
        "notices": list(dict.fromkeys(notices)),
        "options": options,
        "source": "HopLogic BrauPartner, gespeicherte CRM-Daten. Der Bestellwert ist kein fakturierter ERP-Umsatz.",
    }
