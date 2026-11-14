"""Server-side authentication and permission check for every API route."""

import secrets
from collections.abc import Iterator

from fastapi import HTTPException, Request

from app.access import permission_needed
from app.access_context import Actor, current_actor, reset_actor, set_actor
from app.database import get_db
from app.security import CSRF_COOKIE, SESSION_COOKIE
from app.services.identity import permissions_for_role, session_from_token

SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})


def _same(left: str, right: str) -> bool:
    if len(left) != len(right):
        return False
    return secrets.compare_digest(left, right)


def authorize(request: Request) -> Iterator[None]:
    decision = permission_needed(request.method, request.url.path)
    if decision == "public":
        current_actor.set(None)
        yield
        return
    opener = request.app.dependency_overrides.get(get_db, get_db)
    db_gen = opener()
    db = next(db_gen)
    try:
        found = session_from_token(db, request.cookies.get(SESSION_COOKIE))
        if found is None:
            raise HTTPException(status_code=401, detail="Anmeldung erforderlich.")
        if decision == "deny":
            raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Aktion.")
        session_row, user, role = found
        actor = Actor(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            role_code=role.code,
            role_name=role.name,
            permissions=permissions_for_role(db, user.role_id),
            csrf=session_row.csrf_token,
        )
        if decision != "user" and not any(code in actor.permissions for code in decision):
            raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Aktion.")
        if request.method.upper() not in SAFE_METHODS:
            header = request.headers.get("x-csrf-token", "")
            cookie = request.cookies.get(CSRF_COOKIE, "")
            if not _same(header, cookie) or not _same(header, session_row.csrf_token):
                raise HTTPException(status_code=403, detail="Die Anfrage konnte nicht bestätigt werden.")
        request.state.actor = actor
        token = set_actor(actor)
        try:
            yield
        finally:
            reset_actor(token)
    finally:
        db_gen.close()
