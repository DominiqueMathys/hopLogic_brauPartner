"""Authenticated test client.

The password exists only for pytest. It is not a production credential.
"""

from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.main import app
from app.models.identity import User
from app.services.identity import create_user, ensure_catalog

PASSWORD = "Testpasswort-12"
ADMIN_EMAIL = "pytest-admin@example.invalid"


class AuthClient(TestClient):
    def request(self, method: str, url: str, **kwargs: object) -> object:
        headers = dict(kwargs.get("headers") or {})
        csrf = self.cookies.get("bp_csrf")
        if csrf and method.upper() not in {"GET", "HEAD", "OPTIONS"}:
            headers.setdefault("X-CSRF-Token", csrf)
        kwargs["headers"] = headers
        return super().request(method, url, **kwargs)


def login_session(
    client: TestClient,
    db: Session,
    *,
    role: str = "administrator",
    email: str = ADMIN_EMAIL,
    first: str = "Pytest",
    last: str = "Admin",
    password: str = PASSWORD,
) -> User:
    ensure_catalog(db)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        user = create_user(
            db,
            first_name=first,
            last_name=last,
            email=email,
            password=password,
            role_code=role,
            is_demo=True,
        )
        db.flush()
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    if response.status_code != 200:
        raise AssertionError(response.text)
    return user


def login_persistent(client: TestClient) -> None:
    with SessionLocal() as db:
        ensure_catalog(db)
        user = db.scalar(select(User).where(User.email == ADMIN_EMAIL))
        if user is None:
            create_user(
                db,
                first_name="Pytest",
                last_name="Admin",
                email=ADMIN_EMAIL,
                password=PASSWORD,
                role_code="administrator",
                is_demo=True,
            )
        db.commit()
    response = client.post("/api/auth/login", json={"email": ADMIN_EMAIL, "password": PASSWORD})
    if response.status_code != 200:
        raise AssertionError(response.text)


@contextmanager
def authenticated_client() -> Iterator[AuthClient]:
    with AuthClient(app) as client:
        login_persistent(client)
        yield client
