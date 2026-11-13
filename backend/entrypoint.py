"""Wait for PostgreSQL, apply migrations, then start the API."""

import os
import subprocess
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        sys.exit("DATABASE_URL ist nicht gesetzt.")
    return url


def wait_for_database(url: str) -> None:
    engine = create_engine(url, pool_pre_ping=True)
    last_error = "unbekannt"
    try:
        for _ in range(30):
            try:
                with engine.connect() as connection:
                    connection.execute(text("SELECT 1"))
                return
            except SQLAlchemyError as exc:
                last_error = exc.__class__.__name__
                time.sleep(1)
    finally:
        engine.dispose()
    sys.exit(f"Datenbank nicht erreichbar ({last_error}).")


def main() -> None:
    wait_for_database(database_url())
    subprocess.check_call([sys.executable, "-m", "alembic", "upgrade", "head"])
    if os.environ.get("PROCESS_ROLE") == "worker":
        raise SystemExit(subprocess.call([sys.executable, "-m", "app.worker"]))
    command = [
        sys.executable,
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
        "--port",
        "8000",
    ]
    if os.environ.get("UVICORN_RELOAD") == "1":
        command.append("--reload")
    raise SystemExit(subprocess.call(command))


if __name__ == "__main__":
    main()
