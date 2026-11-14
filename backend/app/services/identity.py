"""Accounts, sessions, password reset and the audit log.

The service flushes changes and leaves the commit to the request. Passwords,
reset tokens and session tokens are never written to the audit detail.
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.access import PERMISSIONS, ROLE_DEFAULTS, ROLES
from app.config import settings
from app.models.activity import Activity
from app.models.contact import Contact
from app.models.engagement import AutomationRule, MarketingCampaign, Notification
from app.models.identity import AuditLog, PasswordReset, Permission, Role, RolePermission, User, UserSession
from app.models.partner import Partner
from app.models.sales import Deal
from app.models.service import ServiceTicket
from app.models.task import Task
from app.security import hash_password, hash_token, new_token, verify_password

LOGIN_MESSAGE = "Anmeldung abgelehnt."
DISABLED_MESSAGE = "Dieses Konto ist deaktiviert."
RESET_MESSAGE = (
    "Wenn ein aktives Konto zu dieser E-Mail besteht, kann ein Administrator lokal ein einmaliges "
    "Rücksetzverfahren starten. Es wird kein Token angezeigt, weil kein E-Mail-Versand konfiguriert ist."
)


class IdentityError(Exception):
    def __init__(self, message: str, status: int = 422) -> None:
        self.message = message
        self.status = status
        super().__init__(message)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def clean_email(value: str) -> str:
    email = value.strip().lower()
    if (
        not email
        or len(email) > 200
        or " " in email
        or email.count("@") != 1
        or email.startswith("@")
        or email.endswith("@")
        or "." not in email.split("@", 1)[1]
    ):
        raise IdentityError("Die geschäftliche E-Mail ist ungültig.")
    return email


def check_password(password: str, email: str) -> None:
    if not isinstance(password, str) or len(password) < 12 or len(password) > 200:
        raise IdentityError("Das Passwort muss mindestens 12 und höchstens 200 Zeichen haben.")
    if password.lower() == email.lower():
        raise IdentityError("Das Passwort darf nicht der E-Mail entsprechen.")


def clean_name(value: str, label: str) -> str:
    name = " ".join(value.split())
    if not name or len(name) > 80:
        raise IdentityError(f"{label} ist erforderlich und darf höchstens 80 Zeichen haben.")
    return name


def audit(
    db: Session,
    *,
    event_type: str,
    result: str,
    actor_id: UUID | None = None,
    actor_label: str | None = None,
    resource_type: str | None = None,
    resource_id: str | None = None,
    detail: str | None = None,
) -> AuditLog:
    if detail:
        lowered = detail.lower()
        if "passwort" in lowered and "geändert" not in lowered:
            detail = "Vorgang ohne Geheimnis protokolliert."
        detail = detail[:300]
    row = AuditLog(
        event_type=event_type,
        occurred_at=_now(),
        actor_id=actor_id,
        actor_label=(actor_label or None) and str(actor_label)[:200],
        resource_type=resource_type,
        resource_id=None if resource_id is None else str(resource_id)[:80],
        result=result,
        detail=detail,
    )
    db.add(row)
    db.flush()
    return row


def ensure_catalog(db: Session) -> None:
    permissions = {row.code: row for row in db.scalars(select(Permission)).all()}
    created_codes: set[str] = set()
    for code, resource, action, description in PERMISSIONS:
        if code in permissions:
            permissions[code].description = description
            continue
        row = Permission(code=code, resource=resource, action=action, description=description)
        db.add(row)
        db.flush()
        permissions[code] = row
        created_codes.add(code)
    roles = {row.code: row for row in db.scalars(select(Role)).all()}
    for code, name, description in ROLES:
        if code in roles:
            roles[code].name = name
            roles[code].description = description
            continue
        row = Role(code=code, name=name, description=description)
        db.add(row)
        db.flush()
        roles[code] = row
    for code, role in roles.items():
        defaults = ROLE_DEFAULTS.get(code, frozenset())
        existing = set(
            db.scalars(
                select(Permission.code)
                .join(RolePermission, RolePermission.permission_id == Permission.id)
                .where(RolePermission.role_id == role.id)
            ).all()
        )
        if not existing:
            grant = defaults
        elif code == "administrator":
            grant = set(PERMISSION_CODES_MISSING(defaults, existing))
        else:
            grant = created_codes.intersection(defaults)
        for permission_code in grant:
            db.add(RolePermission(role_id=role.id, permission_id=permissions[permission_code].id))
    db.flush()


def PERMISSION_CODES_MISSING(defaults: frozenset[str], existing: set[str]) -> set[str]:
    return set(defaults) - existing


def role_by_code(db: Session, code: str) -> Role:
    role = db.scalar(select(Role).where(Role.code == code))
    if role is None:
        raise IdentityError("Die Rolle ist nicht vorhanden.", 422)
    return role


def permissions_for_role(db: Session, role_id: UUID) -> frozenset[str]:
    rows = db.scalars(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
    ).all()
    return frozenset(rows)


def user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def require_user(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise IdentityError("Das Benutzerkonto wurde nicht gefunden.", 404)
    return user


def create_user(
    db: Session,
    *,
    first_name: str,
    last_name: str,
    email: str,
    password: str,
    role_code: str,
    is_demo: bool = False,
    actor_id: UUID | None = None,
) -> User:
    ensure_catalog(db)
    first_name = clean_name(first_name, "Der Vorname")
    last_name = clean_name(last_name, "Der Nachname")
    email = clean_email(email)
    check_password(password, email)
    if user_by_email(db, email) is not None:
        raise IdentityError("Diese E-Mail wird bereits verwendet.", 409)
    role = role_by_code(db, role_code)
    user = User(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password_hash=hash_password(password),
        role_id=role.id,
        status="aktiv",
        is_demo=is_demo,
        password_changed_at=_now(),
    )
    db.add(user)
    db.flush()
    audit(
        db,
        event_type="user_created",
        result="erfolg",
        actor_id=actor_id,
        resource_type="user",
        resource_id=user.id,
        detail=f"Konto {user.email}, Rolle {role.code}",
    )
    return user


def update_profile(db: Session, user: User, *, first_name: str, last_name: str) -> User:
    user.first_name = clean_name(first_name, "Der Vorname")
    user.last_name = clean_name(last_name, "Der Nachname")
    user.updated_at = _now()
    db.flush()
    return user


def update_user(
    db: Session,
    user_id: UUID,
    *,
    first_name: str,
    last_name: str,
    email: str,
    role_code: str,
    actor: User,
) -> User:
    user = require_user(db, user_id)
    user.first_name = clean_name(first_name, "Der Vorname")
    user.last_name = clean_name(last_name, "Der Nachname")
    email = clean_email(email)
    other = user_by_email(db, email)
    if other is not None and other.id != user.id:
        raise IdentityError("Diese E-Mail wird bereits verwendet.", 409)
    user.email = email
    _assign_role(db, user, role_code, actor)
    user.updated_at = _now()
    db.flush()
    return user


def _active_admin_count(db: Session, *, excluding: UUID | None = None) -> int:
    admin = role_by_code(db, "administrator")
    statement = select(func.count()).select_from(User).where(User.role_id == admin.id, User.status == "aktiv")
    if excluding is not None:
        statement = statement.where(User.id != excluding)
    return int(db.scalar(statement) or 0)


def _assign_role(db: Session, user: User, role_code: str, actor: User) -> None:
    role = role_by_code(db, role_code)
    if user.role_id == role.id:
        return
    current = db.get(Role, user.role_id)
    if current is not None and current.code == "administrator" and role.code != "administrator":
        if _active_admin_count(db, excluding=user.id) < 1:
            raise IdentityError("Das letzte aktive Administratorkonto behält die Rolle.", 409)
    previous = current.code if current is not None else ""
    user.role_id = role.id
    audit(
        db,
        event_type="role_changed",
        result="erfolg",
        actor_id=actor.id,
        resource_type="user",
        resource_id=user.id,
        detail=f"Rolle von {previous} auf {role.code}",
    )


def set_status(db: Session, user_id: UUID, status: str, actor: User) -> User:
    if status not in {"aktiv", "deaktiviert"}:
        raise IdentityError("Der Kontostatus ist ungültig.")
    user = require_user(db, user_id)
    if user.id == actor.id and status == "deaktiviert":
        raise IdentityError("Das eigene Konto kann nicht deaktiviert werden.", 409)
    role = db.get(Role, user.role_id)
    if status == "deaktiviert" and role is not None and role.code == "administrator":
        if _active_admin_count(db, excluding=user.id) < 1:
            raise IdentityError("Das letzte aktive Administratorkonto bleibt aktiv.", 409)
    if user.status == status:
        return user
    user.status = status
    user.updated_at = _now()
    if status == "deaktiviert":
        _revoke_all(db, user.id)
        audit(
            db,
            event_type="user_deactivated",
            result="erfolg",
            actor_id=actor.id,
            resource_type="user",
            resource_id=user.id,
            detail="Konto deaktiviert",
        )
    else:
        audit(
            db,
            event_type="user_reactivated",
            result="erfolg",
            actor_id=actor.id,
            resource_type="user",
            resource_id=user.id,
            detail="Konto reaktiviert",
        )
    db.flush()
    return user


def _revoke_all(db: Session, user_id: UUID) -> None:
    now = _now()
    rows = db.scalars(select(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))).all()
    for row in rows:
        row.revoked_at = now


def list_users(db: Session, *, q: str | None, page: int, page_size: int) -> tuple[list[User], int]:
    statement = select(User)
    if q:
        pattern = f"%{q.strip()}%"
        statement = statement.where(
            or_(User.first_name.ilike(pattern), User.last_name.ilike(pattern), User.email.ilike(pattern))
        )
    total = int(db.scalar(select(func.count()).select_from(statement.subquery())) or 0)
    rows = db.scalars(statement.order_by(User.last_name, User.first_name).offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total


def directory(db: Session) -> list[User]:
    return list(db.scalars(select(User).where(User.status == "aktiv").order_by(User.last_name, User.first_name)).all())


def open_session(db: Session, user: User) -> tuple[str, str]:
    raw, token_hash = new_token()
    csrf = secrets.token_urlsafe(32)
    db.add(
        UserSession(
            user_id=user.id,
            token_hash=token_hash,
            csrf_token=csrf,
            created_at=_now(),
            expires_at=_now() + timedelta(hours=max(settings.session_hours, 1)),
        )
    )
    user.last_login_at = _now()
    user.failed_attempts = 0
    user.locked_until = None
    db.flush()
    return raw, csrf


def authenticate(db: Session, email: str, password: str) -> tuple[User, str, str]:
    try:
        normalized = clean_email(email)
    except IdentityError:
        audit(db, event_type="login_failed", result="abgelehnt", actor_label="unbekannt", detail="Ungültige E-Mail")
        raise IdentityError(LOGIN_MESSAGE, 401) from None
    user = user_by_email(db, normalized)
    if user is None:
        audit(db, event_type="login_failed", result="abgelehnt", actor_label=normalized, detail="Unbekanntes Konto")
        raise IdentityError(LOGIN_MESSAGE, 401)
    if user.locked_until is not None and user.locked_until > _now():
        audit(
            db,
            event_type="login_failed",
            result="abgelehnt",
            actor_id=user.id,
            actor_label=user.email,
            resource_type="user",
            resource_id=user.id,
            detail="Anmeldung vorübergehend gesperrt",
        )
        raise IdentityError(LOGIN_MESSAGE, 401)
    if not verify_password(password, user.password_hash):
        user.failed_attempts += 1
        if user.failed_attempts >= settings.login_max_failures:
            user.locked_until = _now() + timedelta(minutes=max(settings.login_lock_minutes, 1))
        audit(
            db,
            event_type="login_failed",
            result="abgelehnt",
            actor_id=user.id,
            actor_label=user.email,
            resource_type="user",
            resource_id=user.id,
            detail="Passwort abgelehnt",
        )
        raise IdentityError(LOGIN_MESSAGE, 401)
    if user.status != "aktiv":
        audit(
            db,
            event_type="login_failed",
            result="abgelehnt",
            actor_id=user.id,
            actor_label=user.email,
            resource_type="user",
            resource_id=user.id,
            detail="Konto deaktiviert",
        )
        raise IdentityError(DISABLED_MESSAGE, 403)
    raw, csrf = open_session(db, user)
    audit(
        db,
        event_type="login",
        result="erfolg",
        actor_id=user.id,
        actor_label=user.email,
        resource_type="user",
        resource_id=user.id,
        detail="Anmeldung",
    )
    return user, raw, csrf


def session_from_token(db: Session, raw_token: str | None) -> tuple[UserSession, User, Role] | None:
    if not raw_token:
        return None
    row = db.scalar(
        select(UserSession).where(
            UserSession.token_hash == hash_token(raw_token),
            UserSession.revoked_at.is_(None),
            UserSession.expires_at > _now(),
        )
    )
    if row is None:
        return None
    user = db.get(User, row.user_id)
    if user is None or user.status != "aktiv":
        return None
    role = db.get(Role, user.role_id)
    if role is None:
        return None
    return row, user, role


def revoke_token(db: Session, raw_token: str | None, *, actor_id: UUID | None) -> None:
    if raw_token:
        row = db.scalar(select(UserSession).where(UserSession.token_hash == hash_token(raw_token)))
        if row is not None and row.revoked_at is None:
            row.revoked_at = _now()
            actor_id = actor_id or row.user_id
    audit(db, event_type="logout", result="erfolg", actor_id=actor_id, resource_type="session", detail="Abmeldung")
    db.flush()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise IdentityError("Das bisherige Passwort ist nicht korrekt.", 422)
    check_password(new_password, user.email)
    if verify_password(new_password, user.password_hash):
        raise IdentityError("Das neue Passwort muss sich vom bisherigen unterscheiden.", 422)
    user.password_hash = hash_password(new_password)
    user.password_changed_at = _now()
    user.failed_attempts = 0
    user.locked_until = None
    _revoke_all(db, user.id)
    audit(
        db,
        event_type="password_changed",
        result="erfolg",
        actor_id=user.id,
        resource_type="user",
        resource_id=user.id,
        detail="Passwort geändert",
    )
    db.flush()


def start_reset(db: Session, email: str) -> str | None:
    """Create a single-use reset token and return the raw value to the caller.

    HTTP endpoints must discard the return value. Only the local operator command
    may show it, and only in that process.
    """
    try:
        normalized = clean_email(email)
    except IdentityError:
        return None
    user = user_by_email(db, normalized)
    if user is None or user.status != "aktiv":
        return None
    raw, token_hash = new_token()
    db.add(
        PasswordReset(
            user_id=user.id,
            token_hash=token_hash,
            created_at=_now(),
            expires_at=_now() + timedelta(minutes=max(settings.reset_minutes, 5)),
        )
    )
    audit(
        db,
        event_type="password_reset_started",
        result="erfolg",
        actor_id=user.id,
        resource_type="user",
        resource_id=user.id,
        detail="Rücksetzverfahren gestartet",
    )
    db.flush()
    return raw


def confirm_reset(db: Session, token: str, new_password: str) -> None:
    if not token or len(token) > 200:
        raise IdentityError("Das Rücksetzverfahren ist ungültig oder abgelaufen.", 400)
    row = db.scalar(select(PasswordReset).where(PasswordReset.token_hash == hash_token(token)))
    if row is None or row.used_at is not None or row.expires_at <= _now():
        raise IdentityError("Das Rücksetzverfahren ist ungültig oder abgelaufen.", 400)
    user = db.get(User, row.user_id)
    if user is None or user.status != "aktiv":
        raise IdentityError("Das Rücksetzverfahren ist ungültig oder abgelaufen.", 400)
    check_password(new_password, user.email)
    row.used_at = _now()
    user.password_hash = hash_password(new_password)
    user.password_changed_at = _now()
    user.failed_attempts = 0
    user.locked_until = None
    _revoke_all(db, user.id)
    audit(
        db,
        event_type="password_changed",
        result="erfolg",
        actor_id=user.id,
        resource_type="user",
        resource_id=user.id,
        detail="Passwort über Rücksetzverfahren geändert",
    )
    db.flush()


def replace_role_permissions(db: Session, role_code: str, codes: list[str], actor: User) -> Role:
    if role_code == "administrator" and "users.manage" not in codes:
        raise IdentityError("Die Administration behält die Benutzerverwaltung.", 409)
    role = role_by_code(db, role_code)
    known = {row.code: row for row in db.scalars(select(Permission)).all()}
    unknown = [code for code in codes if code not in known]
    if unknown:
        raise IdentityError("Eine Berechtigung ist nicht vorhanden.")
    current = set(
        db.scalars(
            select(Permission.code)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        ).all()
    )
    desired = set(codes)
    for code in desired - current:
        db.add(RolePermission(role_id=role.id, permission_id=known[code].id))
    if current - desired:
        remove_ids = [known[code].id for code in current - desired]
        rows = db.scalars(
            select(RolePermission).where(RolePermission.role_id == role.id, RolePermission.permission_id.in_(remove_ids))
        ).all()
        for row in rows:
            db.delete(row)
    added = sorted(desired - current)
    removed = sorted(current - desired)
    audit(
        db,
        event_type="permissions_changed",
        result="erfolg",
        actor_id=actor.id,
        resource_type="role",
        resource_id=role.code,
        detail=f"Hinzu {', '.join(added) or '-'}; entfernt {', '.join(removed) or '-'}"[:300],
    )
    db.flush()
    return role


def link_known_owners(db: Session) -> int:
    """Point existing responsibility fields at a user when the display name matches."""
    users = list(db.scalars(select(User)).all())
    by_name = {user.display_name: user.id for user in users}
    updated = 0
    targets = (Partner, Contact, Activity, Task, Deal, ServiceTicket, MarketingCampaign, AutomationRule)
    for model in targets:
        if not hasattr(model, "owner_user_id") or not hasattr(model, "account_owner"):
            continue
        rows = db.scalars(select(model).where(model.owner_user_id.is_(None), model.account_owner.is_not(None))).all()
        for row in rows:
            match = by_name.get(row.account_owner or "")
            if match is None:
                continue
            row.owner_user_id = match
            updated += 1
    notices = db.scalars(select(Notification).where(Notification.user_id.is_(None))).all()
    for notice in notices:
        match = by_name.get(notice.recipient_label)
        if match is None:
            continue
        notice.user_id = match
        updated += 1
    db.flush()
    return updated


def list_audit(db: Session, *, page: int, page_size: int) -> tuple[list[AuditLog], int]:
    total = int(db.scalar(select(func.count()).select_from(AuditLog)) or 0)
    rows = db.scalars(select(AuditLog).order_by(AuditLog.occurred_at.desc()).offset((page - 1) * page_size).limit(page_size)).all()
    return list(rows), total
