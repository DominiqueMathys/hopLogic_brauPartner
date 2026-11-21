"""Fictional festival demo. Safe to run more than once.

The rows are marked as demo data. They are not a brewery inventory and not live ERP stock.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.festival_catalog import CATEGORY_EXAMPLES
from app.models.activity import Activity
from app.models.contact import CompanyContact, Contact
from app.models.engagement import AutomationRule
from app.models.festival import FestivalMaterial, MaterialAsset
from app.models.partner import Partner
from app.models.task import Task
from app.services.festival import accept_quote, convert_festival, create_assignment, create_delivery, create_festival, create_quote
from app.services.festival_stock import add_asset, confirm_reservation, create_category, create_material, create_reservation, record_movement

ZURICH = ZoneInfo("Europe/Zurich")
NOTE = "Fiktiver Testdatensatz. Keine echte Veranstaltung und kein Inventar des Liechtensteiner Brauhauses."


def _partner(db: Session, demo_key: str, name: str, partner_type: str, city: str, region: str) -> Partner:
    existing = db.scalar(select(Partner).where(Partner.demo_key == demo_key))
    if existing is not None:
        return existing
    row = Partner(
        company_name=name,
        partner_type=partner_type,
        status="aktiv",
        priority="normal",
        city=city,
        region=region,
        country="Schweiz",
        account_owner="Sandra Lutz",
        notes=NOTE,
        is_demo=True,
        demo_key=demo_key,
    )
    db.add(row)
    db.flush()
    return row


def _stock_once(db: Session, material: FestivalMaterial, quantity: int) -> None:
    if material.quantity_total:
        return
    material.quantity_total = quantity
    record_movement(db, material, "wareneingang", quantity, note="Fiktiver Anfangsbestand im CRM, kein ERP-Bestand.")


def seed_festivals(db: Session) -> None:
    from app.models.festival import MaterialCategory

    for index, (code, name) in enumerate(CATEGORY_EXAMPLES):
        create_category(db, code, name, example=True, sort_order=index)
    by_code = {row.code: row for row in db.scalars(select(MaterialCategory)).all()}
    taps = create_material(
        db,
        {
            "name": "Zapfanlage mobil, fiktiv",
            "category_id": by_code["zapfanlagen"].id,
            "tracking": "einzel",
            "unit": "Stück",
            "location": "Lager Schaan",
            "rental_price": Decimal("80.00"),
            "deposit_amount": Decimal("200.00"),
            "prep_hours": 4,
            "return_hours": 4,
            "cleaning_hours": 8,
            "notes": NOTE,
        },
        is_demo=True,
        demo_key="demo-mat-zapf",
    )
    for number in range(1, 6):
        add_asset(db, taps.id, f"ZA-DEMO-{number:02d}", location="Lager Schaan", demo_key=f"demo-asset-zapf-{number:02d}")
    glasses = create_material(
        db,
        {"name": "Festglas 3 dl, fiktiv", "category_id": by_code["glaeser"].id, "tracking": "menge", "unit": "Stück", "location": "Lager Schaan", "rental_price": Decimal("0.50"), "notes": NOTE},
        is_demo=True,
        demo_key="demo-mat-glas",
    )
    _stock_once(db, glasses, 500)
    tables = create_material(
        db,
        {"name": "Festtisch, fiktiv", "category_id": by_code["tische"].id, "tracking": "menge", "unit": "Stück", "location": "Lager Schaan", "rental_price": Decimal("12.00"), "notes": NOTE},
        is_demo=True,
        demo_key="demo-mat-tisch",
    )
    _stock_once(db, tables, 40)
    benches = create_material(
        db,
        {"name": "Festbank, fiktiv", "category_id": by_code["baenke"].id, "tracking": "menge", "unit": "Stück", "location": "Lager Schaan", "rental_price": Decimal("8.00"), "notes": NOTE},
        is_demo=True,
        demo_key="demo-mat-bank",
    )
    _stock_once(db, benches, 80)

    organizer = _partner(db, "demo-event-seeblick", "Eventorganisation Seeblick", "veranstalter", "Locarno", "Tessin")
    distributor = _partner(db, "demo-haendler-alpenblick", "Getränkehandel Alpenblick", "getraenkehaendler", "Schaan", "Liechtenstein")
    contact = db.scalar(select(Contact).where(Contact.demo_key == "demo-lea-seeblick"))
    if contact is None:
        contact = Contact(
            first_name="Lea",
            last_name="Seeblick",
            job_title="Veranstaltungsleitung",
            email="lea.seeblick@example.invalid",
            phone="+423 000 00 00",
            account_owner="Sandra Lutz",
            preferred_language="de",
            preferred_channel="telefon",
            lifecycle_phase="interessent",
            lead_status="offen",
            status="aktiv",
            notes=NOTE + " Veranstalterkontakt, nicht automatisch Bierbestellerin.",
            processing_basis="nicht_dokumentiert",
            is_demo=True,
            demo_key="demo-lea-seeblick",
        )
        db.add(contact)
        db.flush()
        db.add(CompanyContact(partner_id=organizer.id, contact_id=contact.id, is_primary=True))

    start = datetime(2027, 7, 17, 10, 0, tzinfo=ZURICH)
    end = datetime(2027, 7, 18, 2, 0, tzinfo=ZURICH)
    festival = create_festival(
        db,
        {
            "name": "Sommerfest am See 2027",
            "organizer_name": organizer.company_name,
            "organizer_partner_id": organizer.id,
            "distributor_partner_id": distributor.id,
            "contact_id": contact.id,
            "contact_name": "Lea Seeblick",
            "phone": "+423 000 00 00",
            "email": "lea.seeblick@example.invalid",
            "venue_name": "Seepromenade",
            "street": "Seepromenade",
            "postal_code": "6600",
            "city": "Locarno",
            "region": "Tessin",
            "country": "Schweiz",
            "starts_at": start,
            "ends_at": end,
            "expected_visitors": 800,
            "account_owner": "Sandra Lutz",
            "event_type": "fest",
            "description": "Fiktives Sommerfest. Der Veranstalter bestellt das Bier nicht direkt beim Brauhaus.",
            "drinks": "Fiktives Sortiment über den Getränkehandel Alpenblick.",
            "material_wish": "3 Zapfanlagen, 200 Gläser, 10 Festtische, 20 Festbänke",
            "requirements": "Aufbau am Vortag, Rücknahme am Folgetag.",
            "notes": NOTE,
            "delivery_wish_at": start - timedelta(hours=4),
            "pickup_wish_at": end + timedelta(hours=6),
        },
        is_demo=True,
        demo_key="sommerfest-see-2027",
        publish=False,
    )
    quote = create_quote(
        db,
        {
            "festival_id": festival.id,
            "contact_name": "Lea Seeblick",
            "vat_rate": Decimal("8.10"),
            "notes": "Fiktive Richtpreise. Keine Preisliste des Liechtensteiner Brauhauses.",
            "items": [
                {"kind": "material", "description": "Zapfanlage mobil, fiktiv", "quantity": Decimal("3"), "unit_price": Decimal("80.00"), "vat_rate": Decimal("8.10"), "material_id": taps.id},
                {"kind": "material", "description": "Festglas 3 dl, fiktiv", "quantity": Decimal("200"), "unit_price": Decimal("0.50"), "vat_rate": Decimal("8.10"), "material_id": glasses.id},
                {"kind": "material", "description": "Festtisch, fiktiv", "quantity": Decimal("10"), "unit_price": Decimal("12.00"), "vat_rate": Decimal("8.10"), "material_id": tables.id},
                {"kind": "material", "description": "Festbank, fiktiv", "quantity": Decimal("20"), "unit_price": Decimal("8.00"), "vat_rate": Decimal("8.10"), "material_id": benches.id},
            ],
        },
        is_demo=True,
        demo_key="sommerfest-see-offerte",
    )
    if quote.status != "angenommen":
        accept_quote(db, quote.id)
    if not festival.is_binding:
        convert_festival(db, festival.id)
    assets = list(db.scalars(select(MaterialAsset).where(MaterialAsset.material_id == taps.id).order_by(MaterialAsset.inventory_number)).all())
    reservation = create_reservation(
        db,
        {
            "festival_id": festival.id,
            "starts_at": start,
            "ends_at": end,
            "prep_hours": 4,
            "return_hours": 4,
            "cleaning_hours": 8,
            "location": "Lager Schaan",
            "notes": NOTE,
            "lines": [
                *[{"material_id": taps.id, "asset_id": asset.id, "quantity": 1} for asset in assets[:3]],
                {"material_id": glasses.id, "quantity": 200},
                {"material_id": tables.id, "quantity": 10},
                {"material_id": benches.id, "quantity": 20},
            ],
        },
        is_demo=True,
        demo_key="sommerfest-see-reservation",
    )
    if reservation.status not in {"bestaetigt", "ausgegeben", "teilweise_zurueckgegeben", "zurueckgegeben"}:
        confirm_reservation(db, reservation.id)
    create_delivery(
        db,
        {
            "festival_id": festival.id,
            "address": "Seepromenade, 6600 Locarno",
            "deliver_at": start - timedelta(hours=4),
            "deliver_window": "06:00–08:00",
            "pickup_at": end + timedelta(hours=6),
            "pickup_window": "08:00–10:00",
            "status": "geplant",
            "account_owner": "Nora Fest",
            "notes": NOTE + " Der Termin allein gilt nicht als Zustellung.",
        },
        is_demo=True,
        demo_key="sommerfest-see-transport",
    )
    create_assignment(
        db,
        {
            "festival_id": festival.id,
            "person_name": "Nora Fest",
            "kind": "materialvorbereitung",
            "task": "Fiktives Material kommissionieren",
            "starts_at": start - timedelta(hours=6),
            "ends_at": start - timedelta(hours=2),
            "notes": NOTE,
        },
        is_demo=True,
        demo_key="sommerfest-see-einsatz",
    )
    if db.scalar(select(Task).where(Task.demo_key == "sommerfest-see-aufgabe")) is None:
        db.add(
            Task(
                title="Reklamationsweg mit dem Getränkehändler klären",
                description=NOTE,
                account_owner="Sandra Lutz",
                due_at=start - timedelta(days=7),
                priority="normal",
                status="offen",
                task_type="intern",
                partner_id=distributor.id,
                contact_id=contact.id,
                event_id=festival.id,
                origin="demo",
                is_demo=True,
                demo_key="sommerfest-see-aufgabe",
            )
        )
    if db.scalar(select(Activity).where(Activity.demo_key == "sommerfest-see-telefon")) is None:
        db.add(
            Activity(
                activity_type="telefonat",
                title="Telefonisches Kundengespräch zum Sommerfest",
                description=NOTE + " Menge der Zapfanlagen von zwei auf drei erhöht.",
                occurred_at=start - timedelta(days=20),
                account_owner="Sandra Lutz",
                partner_id=distributor.id,
                contact_id=contact.id,
                event_id=festival.id,
                is_demo=True,
                demo_key="sommerfest-see-telefon",
            )
        )
    rules = [
        ("festival-rule-request", "Neue Festanfrage prüfen", "festival_request_created", {}, "create_task"),
        ("festival-rule-quote", "Offerte seit fünf Tagen unbeantwortet", "festival_quote_waiting", {"days": 5}, "create_reminder"),
        ("festival-rule-start", "Fest beginnt in drei Tagen", "festival_starts_soon", {"days": 3}, "create_task"),
        ("festival-rule-delivery", "Lieferung morgen erinnern", "festival_delivery_due", {"days": 1}, "create_reminder"),
        ("festival-rule-ended", "Rücknahme nach Festende", "festival_ended", {"days": 1}, "create_task"),
        ("festival-rule-return", "Überfällige Rücknahme", "festival_return_overdue", {"days": 2}, "create_reminder"),
        ("festival-rule-short", "Materialengpass", "festival_material_short", {}, "notify_owner"),
        ("festival-rule-damage", "Beschädigtes Material prüfen", "festival_material_damaged", {}, "create_task"),
    ]
    for demo_key, name, trigger, config, action in rules:
        if db.scalar(select(AutomationRule).where(AutomationRule.demo_key == demo_key)) is None:
            db.add(
                AutomationRule(
                    name=name,
                    description=NOTE + " Zeitraum über die Regel konfigurierbar. Doppelte Aufgaben werden über den Schlüssel verhindert.",
                    trigger_type=trigger,
                    trigger_config=config,
                    action_type=action,
                    action_config={"title": name, "due_days": 2, "description": NOTE},
                    status="aktiv",
                    account_owner="Sandra Lutz",
                    is_demo=True,
                    demo_key=demo_key,
                )
            )
    db.flush()


def main() -> None:
    with SessionLocal() as db:
        seed_festivals(db)
        db.commit()
    print("Fiktive Festdaten sind vorhanden. Ein erneuter Lauf erzeugt keine Duplikate.")


if __name__ == "__main__":
    main()
