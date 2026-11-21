"""Codes for festival management and festival materials.

Stored values stay stable. The user interface translates them.
Material categories and prices in the demo are fictional examples, not a brewery inventory.
"""

REQUEST_STATUSES = (
    "neue_anfrage",
    "in_pruefung",
    "offerte_vorbereitung",
    "offerte_versendet",
    "bestaetigt",
    "abgelehnt",
    "storniert",
)

EVENT_STATUSES = (
    "anfrage",
    "geplant",
    "bestaetigt",
    "laufend",
    "abgeschlossen",
    "archiviert",
    "storniert",
)

MATERIAL_STATUSES = (
    "kein_bedarf",
    "ungeprueft",
    "verfuegbar",
    "teilweise",
    "konflikt",
    "reserviert",
    "ausgegeben",
    "ruecknahme_offen",
    "abgeschlossen",
)

QUOTE_STATUSES = (
    "keine",
    "entwurf",
    "in_pruefung",
    "versendet",
    "angenommen",
    "abgelehnt",
    "abgelaufen",
)

DELIVERY_STATUSES = (
    "keine",
    "geplant",
    "bereit",
    "unterwegs",
    "geliefert",
    "abholung_geplant",
    "abgeholt",
    "abgeschlossen",
)

EVENT_TYPES = (
    "fest",
    "firmenanlass",
    "vereinsanlass",
    "markt",
    "sonstige",
)

MATERIAL_TRACKING = ("menge", "einzel")

MATERIAL_CONDITIONS = ("einsatzbereit", "gesperrt", "defekt", "in_reparatur")

RESERVATION_STATUSES = (
    "entwurf",
    "angefragt",
    "in_pruefung",
    "bestaetigt",
    "teilweise_verfuegbar",
    "ausgegeben",
    "teilweise_zurueckgegeben",
    "zurueckgegeben",
    "storniert",
)

HOLDING_STATUSES = ("bestaetigt", "ausgegeben", "teilweise_zurueckgegeben")

OPEN_RESERVATION_STATUSES = (
    "entwurf",
    "angefragt",
    "in_pruefung",
    "bestaetigt",
    "teilweise_verfuegbar",
    "ausgegeben",
    "teilweise_zurueckgegeben",
)

QUOTE_ITEM_KINDS = ("material", "dienstleistung", "getraenk")

MOVEMENT_TYPES = (
    "wareneingang",
    "reservation",
    "reservationsfreigabe",
    "ausgabe",
    "ruecknahme",
    "beschaedigung",
    "verlust",
    "reparatur",
    "bestandskorrektur",
    "standortwechsel",
)

ASSIGNMENT_KINDS = (
    "materialvorbereitung",
    "lieferung",
    "aufbau",
    "betreuung",
    "abbau",
    "ruecktransport",
    "materialkontrolle",
)

ASSIGNMENT_STATUSES = ("geplant", "bestaetigt", "erledigt", "abgebrochen")

CATEGORY_EXAMPLES = (
    ("zapfanlagen", "Zapfanlagen"),
    ("kuehlschraenke", "Kühlschränke"),
    ("kuehlwagen", "Kühlwagen"),
    ("festzelte", "Festzelte"),
    ("tische", "Tische"),
    ("baenke", "Bänke"),
    ("glaeser", "Gläser"),
    ("becher", "Becher"),
    ("sonnenschirme", "Sonnenschirme"),
    ("werbematerial", "Werbematerial"),
    ("weiteres", "Weiteres Festmaterial"),
)
