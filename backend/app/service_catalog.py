"""Allowed values for service tickets and partner segments.

Codes are stored in PostgreSQL. There is no user account yet, so the owner is a
display name. Complaint resolutions are CRM documentation, not ERP actions.
"""

TICKET_CATEGORIES = (
    "beschaedigte_lieferung",
    "fehlende_lieferung",
    "falsche_lieferung",
    "produktqualitaet",
    "rechnung",
    "anfrage",
    "technisch",
    "sonstiges",
)

COMPLAINT_CATEGORIES = (
    "beschaedigte_lieferung",
    "fehlende_lieferung",
    "falsche_lieferung",
    "produktqualitaet",
)

TICKET_PRIORITIES = ("niedrig", "normal", "hoch", "kritisch")

TICKET_STATUSES = (
    "neu",
    "offen",
    "in_bearbeitung",
    "warten_kunde",
    "warten_intern",
    "geloest",
    "geschlossen",
)

OPEN_TICKET_STATUSES = (
    "neu",
    "offen",
    "in_bearbeitung",
    "warten_kunde",
    "warten_intern",
)

TICKET_STATUS_TRANSITIONS: dict[str, frozenset[str]] = {
    "neu": frozenset({"offen", "in_bearbeitung"}),
    "offen": frozenset({"in_bearbeitung", "warten_kunde", "warten_intern"}),
    "in_bearbeitung": frozenset({"offen", "warten_kunde", "warten_intern"}),
    "warten_kunde": frozenset({"offen", "in_bearbeitung"}),
    "warten_intern": frozenset({"offen", "in_bearbeitung"}),
    "geloest": frozenset(),
    "geschlossen": frozenset(),
}

RESOLVE_FROM = frozenset(OPEN_TICKET_STATUSES)
CLOSE_FROM = frozenset({*OPEN_TICKET_STATUSES, "geloest"})
REOPEN_FROM = frozenset({"geloest", "geschlossen"})

RESOLUTION_CODES = (
    "ersatzlieferung",
    "gutschrift",
    "vertrieb",
    "logistik",
    "keine_massnahme",
    "sonstige",
)

TICKET_EVENT_TYPES = (
    "created",
    "status_changed",
    "priority_changed",
    "owner_changed",
    "note_added",
    "task_created",
    "resolved",
    "closed",
    "reopened",
)

TICKET_SORTS = ("created_at", "priority", "updated_at")

PRIORITY_RANK = {"kritisch": 0, "hoch": 1, "normal": 2, "niedrig": 3}

SEGMENT_MATCH_MODES = ("all", "any")

SEGMENT_FIELDS = (
    "partner_type",
    "industry",
    "region",
    "status",
    "order_count",
    "order_volume",
    "last_order_on",
    "open_deals",
    "open_tickets",
    "last_activity_on",
)

SEGMENT_OPERATORS = ("eq", "gte", "lte", "before", "after", "empty")

FIELD_OPERATORS: dict[str, tuple[str, ...]] = {
    "partner_type": ("eq",),
    "industry": ("eq",),
    "region": ("eq",),
    "status": ("eq",),
    "order_count": ("eq", "gte", "lte"),
    "order_volume": ("gte", "lte"),
    "last_order_on": ("before", "after", "empty"),
    "open_deals": ("eq", "gte", "lte"),
    "open_tickets": ("eq", "gte", "lte"),
    "last_activity_on": ("before", "after", "empty"),
}
