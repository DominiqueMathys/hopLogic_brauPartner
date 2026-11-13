import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import SessionLocal
from app.seed_crm import seed_demo_crm
from app.seed_partners import seed_demo_partners
from app.services.crm import CrmServiceError
from app.services.partners import PartnerServiceError


def main() -> int:
    session = SessionLocal()
    try:
        partners = seed_demo_partners(session)
        records = seed_demo_crm(session)
        session.commit()
    except (PartnerServiceError, CrmServiceError) as error:
        session.rollback()
        print(error.message, file=sys.stderr)
        return 1
    except SQLAlchemyError:
        session.rollback()
        print(
            "Die Testdaten konnten nicht gespeichert werden. Prüfen Sie, ob PostgreSQL läuft und die Migration ausgeführt wurde.",
            file=sys.stderr,
        )
        return 1
    finally:
        session.close()
    print(f"{partners} gekennzeichnete Partner-Testdatensätze sind gespeichert.")
    print(f"{records} gekennzeichnete CRM-Testdatensätze sind gespeichert.")
    print("Giulia Bernasconi und Ristorante Lago sind fiktiv. Es sind keine echten Kontaktdaten oder Einwilligungen hinterlegt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
