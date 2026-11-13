import sys
from pathlib import Path

from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.database import SessionLocal
from app.seed_crm import seed_demo_crm
from app.seed_engagement import seed_demo_engagement
from app.seed_partners import seed_demo_partners
from app.seed_sales import seed_demo_sales
from app.seed_service import seed_demo_service
from app.services.automation import paused_automations
from app.services.crm import CrmServiceError
from app.services.partners import PartnerServiceError


def main() -> int:
    session = SessionLocal()
    try:
        with paused_automations():
            partners = seed_demo_partners(session)
            crm_records = seed_demo_crm(session)
            sales_records = seed_demo_sales(session)
            service_records = seed_demo_service(session)
            engagement_records = seed_demo_engagement(session)
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
    print(f"{partners} Partner, {crm_records} CRM-Datensätze und {sales_records} Verkaufsdatensätze sind als Testdaten gespeichert.")
    print(f"{service_records} Service- und Segmentdatensätze sind als fiktive Reklamation gespeichert.")
    print(f"{engagement_records} Kampagnen-, Betreuungs- und Automatisierungsdatensätze sind als Testdaten gespeichert.")
    print("Preise, Artikel, die Reklamation und die Kampagne sind fiktiv. Es entsteht kein ERP-Vorgang und keine E-Mail.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
