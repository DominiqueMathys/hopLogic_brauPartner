from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.access_context import Actor
from app.api.crm_support import check_page
from app.database import get_db
from app.models.identity import AuditLog, Permission, Role, User
from app.schemas.identity import (
    AuditList,
    AuditRead,
    DirectoryEntry,
    LoginRequest,
    PasswordChange,
    PasswordResetConfirm,
    PasswordResetRequest,
    ProfileUpdate,
    RolePermissionUpdate,
    RoleRead,
    SessionRead,
    StatusUpdate,
    UserList,
    UserRead,
    UserWrite,
)
from app.security import SESSION_COOKIE, apply_session_cookies, clear_session_cookies
from app.services.identity import (
    RESET_MESSAGE,
    IdentityError,
    audit,
    change_password,
    confirm_reset,
    create_user,
    directory,
    list_audit,
    list_users,
    permissions_for_role,
    replace_role_permissions,
    require_user,
    revoke_token,
    set_status,
    update_profile,
    update_user,
    authenticate,
)
from sqlalchemy import select

auth_router = APIRouter(prefix="/auth", tags=["anmeldung"])
users_router = APIRouter(prefix="/users", tags=["benutzer"])
roles_router = APIRouter(prefix="/roles", tags=["rollen"])
audit_router = APIRouter(prefix="/audit", tags=["audit"])


def _raise(error: IdentityError) -> None:
    raise HTTPException(status_code=error.status, detail=error.message) from None


def _actor(request: Request) -> Actor:
    actor = getattr(request.state, "actor", None)
    if actor is None:
        raise HTTPException(status_code=401, detail="Anmeldung erforderlich.")
    return actor


def _user_read(db: Session, user: User) -> UserRead:
    role = db.get(Role, user.role_id)
    return UserRead(
        id=user.id,
        first_name=user.first_name,
        last_name=user.last_name,
        display_name=user.display_name,
        email=user.email,
        role_code=role.code if role is not None else "",
        role_name=role.name if role is not None else "",
        status=user.status,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        permissions=sorted(permissions_for_role(db, user.role_id)),
        is_demo=user.is_demo,
    )


@auth_router.post("/login", response_model=SessionRead)
def post_login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> SessionRead:
    try:
        user, token, csrf = authenticate(db, payload.email, payload.password)
        db.commit()
    except IdentityError as error:
        db.commit()
        _raise(error)
    db.refresh(user)
    apply_session_cookies(response, token, csrf)
    return SessionRead(user=_user_read(db, user), csrf_token=csrf)


@auth_router.post("/logout", status_code=204)
def post_logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    actor = getattr(request.state, "actor", None)
    revoke_token(db, request.cookies.get(SESSION_COOKIE), actor_id=None if actor is None else actor.id)
    db.commit()
    clear_session_cookies(response)
    response.status_code = 204
    return response


@auth_router.get("/me", response_model=SessionRead)
def get_me(request: Request, db: Session = Depends(get_db)) -> SessionRead:
    actor = _actor(request)
    user = require_user(db, actor.id)
    return SessionRead(user=_user_read(db, user), csrf_token=actor.csrf)


@auth_router.patch("/profile", response_model=UserRead)
def patch_profile(payload: ProfileUpdate, request: Request, db: Session = Depends(get_db)) -> UserRead:
    actor = _actor(request)
    user = require_user(db, actor.id)
    try:
        update_profile(db, user, first_name=payload.first_name, last_name=payload.last_name)
        db.commit()
    except IdentityError as error:
        db.rollback()
        _raise(error)
    db.refresh(user)
    return _user_read(db, user)


@auth_router.post("/password", status_code=204)
def post_password(payload: PasswordChange, request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
    actor = _actor(request)
    user = require_user(db, actor.id)
    try:
        change_password(db, user, payload.current_password, payload.new_password)
        db.commit()
    except IdentityError as error:
        db.rollback()
        _raise(error)
    clear_session_cookies(response)
    response.status_code = 204
    return response


@auth_router.post("/password-reset/request", status_code=202)
def post_reset_request(payload: PasswordResetRequest) -> dict[str, str]:
    del payload
    return {"detail": RESET_MESSAGE}


@auth_router.post("/password-reset/confirm", status_code=204)
def post_reset_confirm(payload: PasswordResetConfirm, db: Session = Depends(get_db)) -> Response:
    try:
        confirm_reset(db, payload.token, payload.new_password)
        db.commit()
    except IdentityError as error:
        db.rollback()
        _raise(error)
    return Response(status_code=204)


@users_router.get("/directory", response_model=list[DirectoryEntry])
def get_directory(db: Session = Depends(get_db)) -> list[DirectoryEntry]:
    rows = []
    for user in directory(db):
        role = db.get(Role, user.role_id)
        rows.append(
            DirectoryEntry(
                id=user.id,
                display_name=user.display_name,
                role_code=role.code if role is not None else "",
                role_name=role.name if role is not None else "",
            )
        )
    return rows


@users_router.get("", response_model=UserList)
def get_users(
    q: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> UserList:
    check_page(page, page_size)
    rows, total = list_users(db, q=q, page=page, page_size=page_size)
    return UserList(items=[_user_read(db, row) for row in rows], total=total, page=page, page_size=page_size)


@users_router.post("", response_model=UserRead, status_code=201)
def post_user(payload: UserWrite, request: Request, db: Session = Depends(get_db)) -> UserRead:
    actor = _actor(request)
    if not payload.password:
        raise HTTPException(status_code=422, detail="Ein Passwort ist erforderlich.")
    try:
        user = create_user(
            db,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            password=payload.password,
            role_code=payload.role_code,
            actor_id=actor.id,
        )
        db.commit()
    except IdentityError as error:
        db.rollback()
        _raise(error)
    db.refresh(user)
    return _user_read(db, user)


@users_router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: UUID, db: Session = Depends(get_db)) -> UserRead:
    try:
        user = require_user(db, user_id)
    except IdentityError as error:
        _raise(error)
    return _user_read(db, user)


@users_router.put("/{user_id}", response_model=UserRead)
def put_user(user_id: UUID, payload: UserWrite, request: Request, db: Session = Depends(get_db)) -> UserRead:
    actor_view = _actor(request)
    actor = require_user(db, actor_view.id)
    try:
        user = update_user(
            db,
            user_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=payload.email,
            role_code=payload.role_code,
            actor=actor,
        )
        if payload.password:
            from app.services.identity import check_password
            from app.security import hash_password

            check_password(payload.password, user.email)
            user.password_hash = hash_password(payload.password)
            audit(
                db,
                event_type="password_changed",
                result="erfolg",
                actor_id=actor.id,
                resource_type="user",
                resource_id=user.id,
                detail="Passwort durch Administration gesetzt",
            )
        db.commit()
    except IdentityError as error:
        db.rollback()
        _raise(error)
    db.refresh(user)
    return _user_read(db, user)


@users_router.post("/{user_id}/status", response_model=UserRead)
def post_status(user_id: UUID, payload: StatusUpdate, request: Request, db: Session = Depends(get_db)) -> UserRead:
    actor = require_user(db, _actor(request).id)
    try:
        user = set_status(db, user_id, payload.status, actor)
        db.commit()
    except IdentityError as error:
        db.rollback()
        _raise(error)
    db.refresh(user)
    return _user_read(db, user)


@roles_router.get("", response_model=list[RoleRead])
def get_roles(db: Session = Depends(get_db)) -> list[RoleRead]:
    roles = db.scalars(select(Role).order_by(Role.name)).all()
    return [
        RoleRead(
            code=role.code,
            name=role.name,
            description=role.description,
            permissions=sorted(permissions_for_role(db, role.id)),
        )
        for role in roles
    ]


@roles_router.get("/permissions")
def get_permissions(db: Session = Depends(get_db)) -> list[dict[str, str]]:
    rows = db.scalars(select(Permission).order_by(Permission.code)).all()
    return [
        {"code": row.code, "resource": row.resource, "action": row.action, "description": row.description}
        for row in rows
    ]


@roles_router.put("/{role_code}/permissions", response_model=RoleRead)
def put_role_permissions(
    role_code: str,
    payload: RolePermissionUpdate,
    request: Request,
    db: Session = Depends(get_db),
) -> RoleRead:
    actor = require_user(db, _actor(request).id)
    try:
        role = replace_role_permissions(db, role_code, payload.permissions, actor)
        db.commit()
    except IdentityError as error:
        db.rollback()
        _raise(error)
    db.refresh(role)
    return RoleRead(
        code=role.code,
        name=role.name,
        description=role.description,
        permissions=sorted(permissions_for_role(db, role.id)),
    )


@audit_router.get("", response_model=AuditList)
def get_audit(
    page: int = 1,
    page_size: int = 50,
    db: Session = Depends(get_db),
) -> AuditList:
    check_page(page, page_size)
    rows, total = list_audit(db, page=page, page_size=page_size)
    return AuditList(
        items=[
            AuditRead(
                id=row.id,
                event_type=row.event_type,
                occurred_at=row.occurred_at,
                actor_id=row.actor_id,
                actor_label=row.actor_label,
                resource_type=row.resource_type,
                resource_id=row.resource_id,
                result=row.result,
                detail=row.detail,
            )
            for row in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@audit_router.get("/events", response_model=list[str])
def get_audit_events(event_type: str | None = Query(default=None), db: Session = Depends(get_db)) -> list[str]:
    statement = select(AuditLog.event_type).distinct().order_by(AuditLog.event_type)
    if event_type:
        statement = statement.where(AuditLog.event_type == event_type)
    return list(db.scalars(statement).all())
