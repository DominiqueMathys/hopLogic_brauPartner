"""Start a local password reset without exposing the token through the API.

    $env:PYTHONPATH = "backend"
    .\\.venv\\Scripts\\python.exe -m app.password_reset person@example.invalid

The token is printed once in this process. It is stored only as a hash, expires,
and works a single time. There is no public endpoint that returns it.
"""

from __future__ import annotations

import sys

from app.database import SessionLocal
from app.services.identity import start_reset


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Verwendung: python -m app.password_reset email")
    with SessionLocal() as db:
        token = start_reset(db, sys.argv[1])
        db.commit()
    if token is None:
        print("Kein aktives Konto für diese E-Mail. Es wurde nichts ausgegeben, was ein Konto bestätigt.")
        return
    print("Einmaliges Rücksetz-Token, nur in diesem Fenster, nicht weitergeben:")
    print(token)


if __name__ == "__main__":
    main()
