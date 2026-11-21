import os
import threading
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.authorize import authorize

from app.api.activities import router as activities_router
from app.api.festival import router as festival_router
from app.api.contacts import router as contacts_router
from app.api.engagement import (
    automations_router,
    campaigns_router,
    care_router,
    notifications_router,
    preferences_router,
    summary_router,
    templates_router,
)
from app.api.health import router as health_router
from app.api.identity import audit_router, auth_router, roles_router, users_router
from app.api.integration import router as integration_router
from app.api.reports import router as reports_router
from app.api.partners import router as partners_router
from app.api.sales import deals_router, orders_router, products_router
from app.api.service import analysis_router, segments_router, tickets_router
from app.api.tasks import router as tasks_router
from app.config import settings


def _prepare_access() -> None:
    from sqlalchemy import inspect

    from app.database import SessionLocal, engine
    from app.services.identity import ensure_catalog

    if not inspect(engine).has_table("rollen"):
        return
    with SessionLocal() as db:
        ensure_catalog(db)
        db.commit()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _prepare_access()
    stop = threading.Event()
    if settings.automation_embedded_worker and "PYTEST_CURRENT_TEST" not in os.environ:
        def loop() -> None:
            from app.worker import run_once

            while not stop.is_set():
                try:
                    run_once()
                except Exception:
                    pass
                stop.wait(settings.automation_interval_seconds)

        threading.Thread(target=loop, name="automation-worker", daemon=True).start()
    yield
    stop.set()


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan, dependencies=[Depends(authorize)])

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(users_router, prefix="/api")
app.include_router(roles_router, prefix="/api")
app.include_router(audit_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(integration_router, prefix="/api")
app.include_router(partners_router, prefix="/api")
app.include_router(festival_router, prefix="/api")
app.include_router(contacts_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")
app.include_router(deals_router, prefix="/api")
app.include_router(products_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(tickets_router, prefix="/api")
app.include_router(segments_router, prefix="/api")
app.include_router(analysis_router, prefix="/api")
app.include_router(campaigns_router, prefix="/api")
app.include_router(templates_router, prefix="/api")
app.include_router(care_router, prefix="/api")
app.include_router(automations_router, prefix="/api")
app.include_router(notifications_router, prefix="/api")
app.include_router(preferences_router, prefix="/api")
app.include_router(summary_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "health": "/api/health",
        "database": "/api/health/db",
        "docs": "/docs",
    }
