from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app


@pytest.fixture()
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


def test_root_lists_health_endpoints(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["application"] == "HopLogic BrauPartner"
    assert body["health"] == "/api/health"
    assert body["database"] == "/api/health/db"


def test_api_health(client: TestClient) -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "api",
        "application": "HopLogic BrauPartner",
    }


def test_openapi_contains_health_routes(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/health" in paths
    assert "/api/health/db" in paths


def test_database_health_ok(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.api.health.check_database", lambda: None)

    response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "database"}


def test_database_health_hides_internal_details(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail() -> None:
        raise SQLAlchemyError("password=supersecret host=db.internal")

    monkeypatch.setattr("app.api.health.check_database", fail)

    response = client.get("/api/health/db")

    assert response.status_code == 503
    assert response.json()["detail"] == "Datenbank nicht erreichbar"
    assert "supersecret" not in response.text
    assert "db.internal" not in response.text
