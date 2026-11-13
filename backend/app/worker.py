"""Time-based automation process.

Run once for a check, or without arguments as a loop independent of the browser.
The Docker Compose service uses PROCESS_ROLE=worker. A one-shot run is the tested mode.
"""

import sys
import time

from app.config import settings
from app.database import SessionLocal
from app.services.automation import run_due_automations


def run_once() -> int:
    session = SessionLocal()
    try:
        attempts = run_due_automations(session)
        session.commit()
        return attempts
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> None:
    if "--once" in sys.argv:
        attempts = run_once()
        print(f"Zeitbasierte Automatisierungen geprüft. Ausführungen: {attempts}.")
        return
    while True:
        try:
            attempts = run_once()
            print(f"Zeitbasierte Automatisierungen geprüft. Ausführungen: {attempts}.")
        except Exception:
            print("Der Automatisierungslauf ist fehlgeschlagen und wird erneut versucht.", file=sys.stderr)
        time.sleep(settings.automation_interval_seconds)


if __name__ == "__main__":
    main()
