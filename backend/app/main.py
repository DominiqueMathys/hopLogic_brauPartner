from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.activities import router as activities_router
from app.api.contacts import router as contacts_router
from app.api.health import router as health_router
from app.api.partners import router as partners_router
from app.api.tasks import router as tasks_router
from app.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api")
app.include_router(partners_router, prefix="/api")
app.include_router(contacts_router, prefix="/api")
app.include_router(activities_router, prefix="/api")
app.include_router(tasks_router, prefix="/api")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "application": settings.app_name,
        "health": "/api/health",
        "database": "/api/health/db",
        "docs": "/docs",
    }
