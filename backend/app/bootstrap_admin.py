"""Create the first administrator without a password in the repository.

Run from the project root:

    $env:PYTHONPATH = "backend"
    .\\.venv\\Scripts\\python.exe -m app.bootstrap_admin

If BOOTSTRAP_ADMIN_PASSWORD is unset, a password is generated and written only
to data/local-dev-access.txt, which is gitignored. The command refuses to run
once any user exists. Demo accounts are created only when ENVIRONMENT is
development and CREATE_DEMO_USERS is not 0. They are not for production.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from app.config import ROOT_DIR, settings
from app.database import SessionLocal
from app.models.identity import Role, User
from app.services.identity import create_user, ensure_catalog, link_known_owners
from sqlalchemy import func, select


def user_by_email_exists(db, email: str) -> bool:
    return db.scalar(select(User.id).where(User.email == email)) is not None


def main() -> None:
    email = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@hoplogic.invalid").strip().lower()
    supplied = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD")
    generated = supplied is None or supplied == ""
    password = supplied if supplied else secrets.token_urlsafe(18)
    demo = settings.environment == "development" and os.environ.get("CREATE_DEMO_USERS", "1") != "0"
    with SessionLocal() as db:
        ensure_catalog(db)
        admin_role = db.scalar(select(Role).where(Role.code == "administrator"))
        real_admin = None
        if admin_role is not None:
            real_admin = db.scalar(select(func.count()).select_from(User).where(User.role_id == admin_role.id, User.is_demo.is_(False)))
        if real_admin:
            raise SystemExit("Es besteht bereits ein Administratorkonto. Die Ersteinrichtung wird nicht wiederholt.")
        if user_by_email_exists(db, email):
            raise SystemExit("Diese Administrator-E-Mail ist bereits vorhanden.")
        create_user(
            db,
            first_name=os.environ.get("BOOTSTRAP_ADMIN_FIRST_NAME", "Lokal"),
            last_name=os.environ.get("BOOTSTRAP_ADMIN_LAST_NAME", "Administrator"),
            email=email,
            password=password,
            role_code="administrator",
        )
        demo_rows = [
            ("Sandra", "Lutz", "sandra.lutz@hoplogic.invalid", "vertrieb"),
            ("Marco", "Keller", "marco.keller@hoplogic.invalid", "kundenservice"),
            ("Lina", "Frei", "lina.frei@hoplogic.invalid", "marketing"),
            ("Peter", "Held", "peter.held@hoplogic.invalid", "geschaeftsleitung"),
        ]
        if demo:
            for first_name, last_name, demo_email, role in demo_rows:
                create_user(
                    db,
                    first_name=first_name,
                    last_name=last_name,
                    email=demo_email,
                    password=password,
                    role_code=role,
                    is_demo=True,
                )
        linked = link_known_owners(db)
        db.commit()
    target = Path(ROOT_DIR) / "data" / "local-dev-access.txt"
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "HopLogic BrauPartner – lokale Ersteinrichtung",
        "Diese Datei ist nur für die lokale Entwicklung. Nicht versionieren und nicht produktiv verwenden.",
        "Dies ist keine Produktionsfreigabe.",
        f"Administrator: {email}",
    ]
    if demo:
        lines.append("Demo-Konten (fiktiv, gleiche lokale Passwortquelle, nicht produktiv):")
        lines.extend(f"- {item[2]} ({item[3]})" for item in demo_rows)
    if generated:
        lines.append(f"Lokales Passwort: {password}")
    else:
        lines.append("Das Passwort wurde aus BOOTSTRAP_ADMIN_PASSWORD gelesen und steht nicht in dieser Datei.")
    lines.append(f"Bestehende Zuständigkeiten mit passendem Namen verknüpft: {linked}")
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Ersteinrichtung abgeschlossen. Hinweise stehen in {target}.")
    print("Das Passwort wurde nicht ins Repository geschrieben.")


if __name__ == "__main__":
    main()
