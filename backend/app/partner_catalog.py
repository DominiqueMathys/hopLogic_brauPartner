"""Allowed values for Vertriebspartner.

Codes are stored in PostgreSQL. The user interface translates them.
"""

PARTNER_TYPES = (
    "restaurant",
    "hotel",
    "bar",
    "getraenkehaendler",
    "detailhandel",
    "veranstalter",
    "sonstige",
)

PARTNER_STATUSES = (
    "lead",
    "potenziell",
    "aktiv",
    "inaktiv",
)

PRIORITIES = (
    "niedrig",
    "normal",
    "hoch",
)

SORTS = (
    "name",
    "created_at",
    "last_activity",
)

DIRECTIONS = (
    "asc",
    "desc",
)
