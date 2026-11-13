"""Allowed values and stage probabilities for deals, products and orders.

Probabilities are configuration, not live forecasts. Codes are stored in PostgreSQL.
"""

from decimal import Decimal

DEAL_STAGES = (
    "neuer_lead",
    "erstkontakt",
    "bedarf",
    "angebot",
    "verhandlung",
    "gewonnen",
    "verloren",
)

OPEN_DEAL_STAGES = (
    "neuer_lead",
    "erstkontakt",
    "bedarf",
    "angebot",
    "verhandlung",
)

CLOSED_DEAL_STAGES = ("gewonnen", "verloren")

STAGE_PROBABILITY: dict[str, Decimal] = {
    "neuer_lead": Decimal("10.00"),
    "erstkontakt": Decimal("20.00"),
    "bedarf": Decimal("40.00"),
    "angebot": Decimal("60.00"),
    "verhandlung": Decimal("80.00"),
    "gewonnen": Decimal("100.00"),
    "verloren": Decimal("0.00"),
}

DEAL_PRIORITIES = ("niedrig", "normal", "hoch", "dringend")

PRODUCT_CATEGORIES = (
    "bier",
    "alkoholfrei",
    "mischgetraenke",
    "merchandising",
    "festmaterial",
    "sonstiges",
)

CONTAINER_TYPES = ("flasche", "dose", "fass", "gebinde", "sonstiges")

ORDER_STATUSES = (
    "entwurf",
    "eingereicht",
    "bestaetigt",
    "in_bearbeitung",
    "versandt",
    "geliefert",
    "storniert",
)

ORDER_TRANSITIONS: dict[str, frozenset[str]] = {
    "entwurf": frozenset({"eingereicht", "storniert"}),
    "eingereicht": frozenset({"bestaetigt", "storniert"}),
    "bestaetigt": frozenset({"in_bearbeitung", "storniert"}),
    "in_bearbeitung": frozenset({"versandt", "storniert"}),
    "versandt": frozenset({"geliefert"}),
    "geliefert": frozenset(),
    "storniert": frozenset(),
}

COUNTED_ORDER_STATUSES = (
    "eingereicht",
    "bestaetigt",
    "in_bearbeitung",
    "versandt",
    "geliefert",
)
