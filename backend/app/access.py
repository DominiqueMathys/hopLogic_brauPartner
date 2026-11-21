"""Action-based permissions.

Role names do not grant access by themselves. Each route asks for a concrete
action such as read, write, archive, export or manage. `write` covers creating
and editing, because the CRM uses the same responsibility for both.
"""

from __future__ import annotations

PERMISSIONS: tuple[tuple[str, str, str, str], ...] = (
    ("partners.read", "vertriebspartner", "lesen", "Vertriebspartner lesen"),
    ("partners.write", "vertriebspartner", "schreiben", "Vertriebspartner erstellen und bearbeiten"),
    ("partners.archive", "vertriebspartner", "archivieren", "Vertriebspartner archivieren und wiederherstellen"),
    ("contacts.read", "kontakte", "lesen", "Kontakte lesen"),
    ("contacts.write", "kontakte", "schreiben", "Kontakte erstellen und bearbeiten"),
    ("contacts.archive", "kontakte", "archivieren", "Kontakte archivieren und wiederherstellen"),
    ("activities.read", "aktivitaeten", "lesen", "Aktivitäten lesen"),
    ("activities.write", "aktivitaeten", "schreiben", "Aktivitäten erstellen und bearbeiten"),
    ("activities.archive", "aktivitaeten", "archivieren", "Aktivitäten archivieren und wiederherstellen"),
    ("tasks.read", "aufgaben", "lesen", "Aufgaben lesen"),
    ("tasks.write", "aufgaben", "schreiben", "Aufgaben erstellen und bearbeiten"),
    ("deals.read", "verkaufschancen", "lesen", "Verkaufschancen lesen"),
    ("deals.write", "verkaufschancen", "schreiben", "Verkaufschancen erstellen und bearbeiten"),
    ("deals.archive", "verkaufschancen", "archivieren", "Verkaufschancen archivieren und wiederherstellen"),
    ("orders.read", "bestellungen", "lesen", "Bestellungen lesen"),
    ("orders.write", "bestellungen", "schreiben", "Bestellungen erstellen und bearbeiten"),
    ("products.read", "produkte", "lesen", "Produkte lesen"),
    ("products.write", "produkte", "schreiben", "Produkte erstellen und bearbeiten"),
    ("products.archive", "produkte", "archivieren", "Produkte deaktivieren"),
    ("tickets.read", "kundenservice", "lesen", "Alle Service-Tickets lesen"),
    ("tickets.read_assigned", "kundenservice", "lesen", "Nur zugewiesene Service-Tickets lesen"),
    ("tickets.write", "kundenservice", "schreiben", "Service-Tickets bearbeiten"),
    ("segments.read", "segmente", "lesen", "Segmente lesen"),
    ("segments.write", "segmente", "schreiben", "Segmente erstellen und bearbeiten"),
    ("segments.archive", "segmente", "archivieren", "Segmente löschen"),
    ("campaigns.read", "kampagnen", "lesen", "Kampagnen und Vorlagen lesen"),
    ("campaigns.write", "kampagnen", "schreiben", "Kampagnen und Vorlagen erstellen und bearbeiten"),
    ("campaigns.archive", "kampagnen", "archivieren", "Kampagnen und Vorlagen archivieren"),
    ("preferences.read", "kommunikation", "lesen", "Kommunikationspräferenzen lesen"),
    ("preferences.write", "kommunikation", "schreiben", "Kommunikationspräferenzen bearbeiten"),
    ("care.read", "betreuung", "lesen", "Partnerbetreuung lesen"),
    ("care.write", "betreuung", "schreiben", "Partnerbetreuung bearbeiten"),
    ("care.archive", "betreuung", "archivieren", "Betreuungsregeln löschen"),
    ("automations.read", "automatisierungen", "lesen", "Automatisierungen lesen"),
    ("automations.write", "automatisierungen", "schreiben", "Automatisierungen bearbeiten und ausführen"),
    ("notifications.read", "benachrichtigungen", "lesen", "Eigene Benachrichtigungen lesen und quittieren"),
    ("dashboard.read", "dashboard", "lesen", "Arbeitsübersicht lesen"),
    ("reports.overview", "reporting", "lesen", "Gesamtübersicht lesen"),
    ("reports.sales", "reporting", "lesen", "Vertriebsreporting lesen"),
    ("reports.partners", "reporting", "lesen", "Partnerreporting lesen"),
    ("reports.orders", "reporting", "lesen", "Bestellreporting lesen"),
    ("reports.service", "reporting", "lesen", "Service-Reporting lesen"),
    ("reports.marketing", "reporting", "lesen", "Marketing-Reporting lesen"),
    ("reports.work", "reporting", "lesen", "Aktivitäten- und Aufgabenreporting lesen"),
    ("reports.export", "reporting", "exportieren", "Erlaubte Berichte exportieren"),
    ("users.manage", "benutzer", "verwalten", "Benutzerkonten verwalten"),
    ("roles.read", "rollen", "lesen", "Rollen und Berechtigungen lesen"),
    ("roles.manage", "rollen", "verwalten", "Rollenberechtigungen ändern"),
    ("audit.read", "protokoll", "lesen", "Audit-Protokoll lesen"),
    ("settings.read", "einstellungen", "lesen", "Systemeinstellungen sehen"),
    ("integration.read", "integration", "lesen", "Integrationsstatus und Protokolle lesen"),
    ("integration.sync", "integration", "synchronisieren", "Synchronisation und Bestellübertragung starten"),
    ("integration.configure", "integration", "konfigurieren", "ERP-Modus und Intervalle konfigurieren"),
    ("integration.conflicts", "integration", "konflikte", "Synchronisationskonflikte prüfen"),
    ("festivals.read", "feste", "lesen", "Feste, Anfragen, Kalender und Offerten lesen"),
    ("festivals.write", "feste", "schreiben", "Festanfragen, Offerten und Einsätze bearbeiten"),
    ("festivals.confirm", "feste", "freigeben", "Offerten annehmen und Festaufträge bestätigen"),
    ("festivals.archive", "feste", "archivieren", "Feste archivieren und wiederherstellen"),
    ("materials.read", "festmaterial", "lesen", "Festmaterial und Verfügbarkeit lesen"),
    ("materials.write", "festmaterial", "schreiben", "Materialstamm und Wareneingang bearbeiten"),
    ("materials.reserve", "festmaterial", "reservieren", "Materialreservationen verbindlich bestätigen"),
    ("materials.issue", "festmaterial", "ausgeben", "Material ausgeben, zurücknehmen und Transporte führen"),
    ("materials.correct", "festmaterial", "korrigieren", "Bestandskorrekturen buchen"),
    ("reports.festivals", "reporting", "lesen", "Fest- und Materialreporting lesen"),
)

PERMISSION_CODES = tuple(item[0] for item in PERMISSIONS)

REPORT_SECTIONS = (
    "overview",
    "sales",
    "partners",
    "orders",
    "service",
    "marketing",
    "work",
    "festivals",
)

ROLES: tuple[tuple[str, str, str], ...] = (
    ("administrator", "Administrator:in", "Systemverwaltung, Benutzer, Rollen und alle CRM-Module."),
    ("geschaeftsleitung", "Geschäftsleitung", "Reporting und lesender Zugriff auf die CRM-Daten."),
    ("vertrieb", "Vertrieb", "Partner, Kontakte, Verkauf, Bestellungen und zugewiesene Tickets."),
    ("marketing", "Marketing", "Kampagnen, Segmente, Kommunikationspräferenzen und Marketing-Reporting."),
    ("kundenservice", "Kundenservice", "Tickets, zugehörige Stammdaten, Serviceaufgaben und Service-Reporting."),
    ("logistik", "Logistik", "Festmaterial, Reservationen, Ausgaben, Rücknahmen und Transporte."),
)


_COMMON = frozenset({"notifications.read", "dashboard.read", "settings.read"})
_READ_CRM = frozenset(
    code
    for code in PERMISSION_CODES
    if code.endswith(".read")
    and not code.startswith("reports.")
    and code not in {"tickets.read_assigned", "users.manage", "roles.read", "audit.read"}
)

ROLE_DEFAULTS: dict[str, frozenset[str]] = {
    "administrator": frozenset(PERMISSION_CODES),
    "geschaeftsleitung": frozenset(
        {
            *_READ_CRM,
            *_COMMON,
            "reports.overview",
            "reports.sales",
            "reports.partners",
            "reports.orders",
            "reports.service",
            "reports.marketing",
            "reports.work",
            "reports.festivals",
            "reports.export",
            "festivals.confirm",
        }
    ),
    "vertrieb": frozenset(
        {
            *_COMMON,
            "partners.read",
            "partners.write",
            "partners.archive",
            "contacts.read",
            "contacts.write",
            "contacts.archive",
            "activities.read",
            "activities.write",
            "activities.archive",
            "tasks.read",
            "tasks.write",
            "deals.read",
            "deals.write",
            "deals.archive",
            "orders.read",
            "orders.write",
            "products.read",
            "tickets.read_assigned",
            "segments.read",
            "campaigns.read",
            "preferences.read",
            "care.read",
            "care.write",
            "festivals.read",
            "festivals.write",
            "festivals.confirm",
            "materials.read",
        }
    ),
    "marketing": frozenset(
        {
            *_COMMON,
            "partners.read",
            "contacts.read",
            "campaigns.read",
            "campaigns.write",
            "campaigns.archive",
            "segments.read",
            "segments.write",
            "segments.archive",
            "preferences.read",
            "preferences.write",
            "reports.marketing",
            "reports.export",
            "festivals.read",
        }
    ),
    "kundenservice": frozenset(
        {
            *_COMMON,
            "partners.read",
            "contacts.read",
            "activities.read",
            "tasks.read",
            "tasks.write",
            "orders.read",
            "products.read",
            "tickets.read",
            "tickets.write",
            "reports.service",
            "reports.export",
            "festivals.read",
        }
    ),
    "logistik": frozenset(
        {
            *_COMMON,
            "festivals.read",
            "materials.read",
            "materials.write",
            "materials.reserve",
            "materials.issue",
            "materials.correct",
            "tasks.read",
            "tasks.write",
            "partners.read",
        }
    ),
}

ARCHIVE_ACTIONS = frozenset({"archive", "restore", "deactivate"})
MODULES = {
    "partners": "partners",
    "contacts": "contacts",
    "activities": "activities",
    "tasks": "tasks",
    "deals": "deals",
    "products": "products",
    "orders": "orders",
    "tickets": "tickets",
    "segments": "segments",
    "campaigns": "campaigns",
    "templates": "campaigns",
    "care": "care",
    "automations": "automations",
    "notifications": "notifications",
    "engagement": "dashboard",
    "preferences": "preferences",
}


def _festival_permission(method: str, path: str) -> tuple[str, ...]:
    parts = [part for part in path.split("/") if part]
    tail = parts[2:]
    if not tail:
        if method in {"GET", "HEAD"}:
            return ("festivals.read",)
        return ("festivals.write",)
    head = tail[0]
    last = tail[-1]
    if head == "dashboard":
        return ("festivals.read", "reports.festivals")
    if head == "calendar":
        return ("festivals.read",)
    if head == "materials":
        if method in {"GET", "HEAD"}:
            return ("materials.read", "festivals.read")
        if last == "stock":
            return ("materials.write", "materials.correct")
        return ("materials.write",)
    if head == "reservations":
        if method in {"GET", "HEAD"} or last == "check":
            return ("materials.read", "festivals.read", "materials.reserve")
        if last in {"confirm", "cancel", "replace"}:
            return ("materials.reserve",)
        if last in {"issue", "return"}:
            return ("materials.issue",)
        return ("festivals.write", "materials.reserve")
    if head == "quotes":
        if method in {"GET", "HEAD"} or last == "pdf":
            return ("festivals.read",)
        if last == "accept":
            return ("festivals.confirm",)
        return ("festivals.write",)
    if head == "deliveries":
        if method in {"GET", "HEAD"} or last == "pdf":
            return ("festivals.read", "materials.read")
        return ("materials.issue", "festivals.write")
    if head == "assignments":
        if method in {"GET", "HEAD"}:
            return ("festivals.read",)
        return ("festivals.write", "materials.issue")
    if head == "movements":
        return ("materials.read",)
    if method in {"GET", "HEAD"}:
        return ("festivals.read",)
    if last in {"archive", "restore"}:
        return ("festivals.archive",)
    if last in {"convert", "close"}:
        return ("festivals.confirm",)
    return ("festivals.write",)


def permission_needed(method: str, path: str) -> str | tuple[str, ...]:
    """Return 'public', 'user', a tuple of acceptable permissions, or 'deny'."""
    method = method.upper()
    path = path.split("?", 1)[0].rstrip("/") or "/"
    if method == "OPTIONS" or not path.startswith("/api"):
        return "public"
    if path in {"/api/health", "/api/health/db"}:
        return "public"
    if path == "/api/auth/login" and method == "POST":
        return "public"
    if path in {"/api/auth/password-reset/request", "/api/auth/password-reset/confirm"} and method == "POST":
        return "public"
    if path in {"/api/auth/me", "/api/auth/csrf"} and method == "GET":
        return "user"
    if path == "/api/auth/logout" and method == "POST":
        return "user"
    if path == "/api/auth/password" and method == "POST":
        return "user"
    if path == "/api/auth/profile" and method == "PATCH":
        return "user"
    if path == "/api/users/directory" and method == "GET":
        return "user"
    if path.startswith("/api/users"):
        return ("users.manage",)
    if path.startswith("/api/roles"):
        if method == "GET":
            return ("roles.read",)
        return ("roles.manage",)
    if path.startswith("/api/audit"):
        return ("audit.read",)
    if path.startswith("/api/reports/export"):
        return "user"
    if path.startswith("/api/reports"):
        return tuple(code for code in PERMISSION_CODES if code.startswith("reports.") and code != "reports.export")
    if path.startswith("/api/festivals"):
        return _festival_permission(method, path)
    if path.startswith("/api/integration"):
        if method == "GET":
            return ("integration.read",)
        if path.endswith("/mode") or path.endswith("/intervals"):
            return ("integration.configure",)
        if path.endswith("/review"):
            return ("integration.conflicts",)
        return ("integration.sync",)
    parts = [part for part in path.split("/") if part]
    if len(parts) < 2 or parts[0] != "api":
        return "deny"
    if "preferences" in parts and parts[1] == "contacts":
        module = "preferences"
    else:
        module = MODULES.get(parts[1])
    if module is None:
        return "deny"
    if module == "notifications":
        return ("notifications.read",)
    if module == "dashboard":
        return ("dashboard.read",)
    action = _action(method, parts)
    if module == "tickets" and action == "read":
        return ("tickets.read", "tickets.read_assigned")
    return (f"{module}.{action}",)


def _action(method: str, parts: list[str]) -> str:
    last = parts[-1]
    if method in {"GET", "HEAD"}:
        return "read"
    if last in ARCHIVE_ACTIONS:
        return "archive"
    if method == "DELETE" and len(parts) <= 3:
        return "archive"
    return "write"


def section_permission(section: str) -> str:
    if section not in REPORT_SECTIONS:
        raise ValueError(section)
    return f"reports.{section}"
