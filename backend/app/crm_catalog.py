"""Allowed values for contacts, activities and tasks.

Codes are stored in PostgreSQL. The user interface translates them.
There is no user account model yet. Owner fields store a display name so a
later role check can replace the free text without rewriting history.
"""

CONTACT_STATUSES = ("aktiv", "inaktiv")

LEAD_STATUSES = ("keiner", "offen", "abgeschlossen")

LIFECYCLE_PHASES = ("lead", "interessent", "qualifiziert", "kunde", "ehemalig")

LANGUAGES = ("de", "fr", "it")

CHANNELS = ("telefon", "email", "mobil", "persoenlich")

PROCESSING_BASES = (
    "nicht_dokumentiert",
    "vertrag",
    "berechtigte_interessen",
    "einwilligung",
    "gesetzliche_pflicht",
)

ACTIVITY_TYPES = ("telefonat", "email", "besuch", "meeting", "gespraechsnotiz", "sonstige")

TASK_STATUSES = ("offen", "in_bearbeitung", "erledigt", "abgebrochen")

TASK_PRIORITIES = ("niedrig", "normal", "hoch", "dringend")

TASK_TYPES = ("anruf", "email", "besuch", "intern", "sonstige")

OPEN_TASK_STATUSES = ("offen", "in_bearbeitung")

CONTACT_SORTS = ("name", "last_contact")

DUE_FILTERS = ("", "open", "overdue", "soon", "urgent")
