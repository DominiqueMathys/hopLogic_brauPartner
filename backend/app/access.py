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
)

ROLES: tuple[tuple[str, str, str], ...] = (
    ("administrator", "Administrator:in", "Systemverwaltung, Benutzer, Rollen und alle CRM-Module."),
    ("geschaeftsleitung", "Geschäftsleitung", "Reporting und lesender Zugriff auf die CRM-Daten."),
    ("vertrieb", "Vertrieb", "Partner, Kontakte, Verkauf, Bestellungen und zugewiesene Tickets."),
    ("marketing", "Marketing", "Kampagnen, Segmente, Kommunikationspräferenzen und Marketing-Reporting."),
    ("kundenservice", "Kundenservice", "Tickets, zugehörige Stammdaten, Serviceaufgaben und Service-Reporting."),
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
            "reports.export",
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
