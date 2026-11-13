import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import SessionLocal
from app.seed_partners import seed_demo_partners
from app.services.partners import PartnerServiceError


def main() -> int:
    session = SessionLocal()
    try:
        count = seed_demo_partners(session)
        session.commit()
    except PartnerServiceError as error:
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
    print(f"{count} gekennzeichnete Testdatensätze sind gespeichert.")
    print("Es handelt sich um fiktive Unternehmen, nicht um Kunden des Liechtensteiner Brauhauses.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
