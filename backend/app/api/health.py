from fastapi import APIRouter, HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import check_database
from app.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def api_health() -> HealthResponse:
    return HealthResponse(status="ok", service="api", application=settings.app_name)


@router.get("/health/db", response_model=HealthResponse, response_model_exclude_none=True)
def database_health() -> HealthResponse:
    try:
        check_database()
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Datenbank nicht erreichbar") from None
    return HealthResponse(status="ok", service="database")
