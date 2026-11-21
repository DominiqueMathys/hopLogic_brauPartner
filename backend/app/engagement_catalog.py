"""Codes for campaigns, care rules, automations and notifications.

The user interface translates these codes. A stored consent flag documents what
was entered in the CRM. It is not treated as proof that the consent is legally sufficient.
"""

CAMPAIGN_TYPES = (
    "produkteinfuehrung",
    "saisonal",
    "partnerinformation",
    "rueckgewinnung",
    "event",
    "individuell",
)

CAMPAIGN_STATUSES = (
    "entwurf",
    "geplant",
    "aktiv",
    "pausiert",
    "abgeschlossen",
    "archiviert",
)

CAMPAIGN_TRANSITIONS = {
    "entwurf": {"geplant", "archiviert"},
    "geplant": {"aktiv", "entwurf", "pausiert", "archiviert"},
    "aktiv": {"pausiert", "abgeschlossen"},
    "pausiert": {"aktiv", "abgeschlossen", "archiviert"},
    "abgeschlossen": {"archiviert"},
    "archiviert": set(),
}

AUDIENCE_KINDS = ("segment", "partners", "contacts")

MESSAGE_CHANNELS = ("email", "telefon", "besuch", "brief", "sonstige")

AUTOMATION_STATUSES = ("entwurf", "aktiv", "pausiert", "deaktiviert")

AUTOMATION_TRANSITIONS = {
    "entwurf": {"aktiv", "deaktiviert"},
    "aktiv": {"pausiert", "deaktiviert"},
    "pausiert": {"aktiv", "deaktiviert"},
    "deaktiviert": {"aktiv"},
}

EVENT_TRIGGERS = (
    "deal_created",
    "deal_stage_changed",
    "partner_created",
    "ticket_created",
    "ticket_priority_changed",
    "order_created",
    "festival_request_created",
    "festival_quote_accepted",
    "festival_material_short",
    "festival_material_damaged",
)

TIME_TRIGGERS = (
    "task_due_soon",
    "task_overdue",
    "no_contact",
    "no_order",
    "ticket_stale",
    "festival_quote_waiting",
    "festival_starts_soon",
    "festival_delivery_due",
    "festival_ended",
    "festival_return_overdue",
)

AUTOMATION_TRIGGERS = EVENT_TRIGGERS + TIME_TRIGGERS

AUTOMATION_ACTIONS = (
    "create_task",
    "notify_owner",
    "create_reminder",
    "log_activity",
)

CARE_RULE_KINDS = ("no_contact", "no_order", "stale_deal", "stale_ticket")

NOTIFICATION_TYPES = (
    "task_assigned",
    "task_due_soon",
    "task_overdue",
    "critical_ticket",
    "deal_assigned",
    "automation_failed",
    "general",
)

EXECUTION_STATUSES = ("erfolg", "fehler", "uebersprungen")

PLACEHOLDERS = ("{{vorname}}", "{{nachname}}", "{{unternehmen}}", "{{funktion}}")

CONSENT_NOTICE = (
    "Eine gespeicherte Einwilligung dokumentiert nur die Eingabe im CRM. "
    "Sie ist kein automatischer Nachweis, dass die Einwilligung rechtlich ausreicht. "
    "Eine geschäftliche E-Mail-Adresse erlaubt keine Marketing-E-Mails."
)

DELIVERY_NOTICE = (
    "Versand nicht konfiguriert. Es werden keine Marketing-E-Mails zugestellt. "
    "Ein Versand bleibt gesperrt, solange Anmeldung, Berechtigungen, Empfängerprüfung, "
    "Abmeldemöglichkeit und ein E-Mail-Dienst fehlen."
)

FROZEN_AUDIENCE_NOTICE = (
    "Die Empfängerliste wurde bei der Aktivierung festgehalten. "
    "Spätere Änderungen am Kundensegment verändern diese Liste nicht."
)
