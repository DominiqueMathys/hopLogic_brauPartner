"""Fictional deal, products and order for the Ristorante Lago case.

Prices and product names are demo values. They are not the official assortment
or the official prices of Liechtensteiner Brauhaus. The order is not sent to an ERP.
"""

from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.contact import Contact
from app.models.partner import Partner
from app.models.sales import Deal, Order, Product
from app.sales_catalog import STAGE_PROBABILITY
from app.schemas.sales import DealWrite, OrderItemWrite, OrderWrite, ProductWrite
from app.seed_crm import CONTACT_KEY, PARTNER_KEY
from app.services.crm import CrmServiceError
from app.services.sales import (
    _build_items,
    _order_items,
    ensure_sku,
    insert_deal,
    insert_order,
    insert_product,
    update_product,
)

DEAL_KEY = "demo-lago-sortiment"
ORDER_KEY = "demo-lago-bestellung"
ORDER_NUMBER = "DEMO-BP-1001"
DEMO_NOTE = (
    "Fiktiver Demoartikel. Kein offizielles Sortiment und kein offizieller Preis "
    "des Liechtensteiner Brauhauses."
)

DEMO_PRODUCTS: tuple[dict[str, str], ...] = (
    {
        "demo_key": "demo-lager-33",
        "sku": "DEMO-BIER-33",
        "name": "Lagerbier 33 cl",
        "category": "bier",
        "container_size": "33 cl",
        "list_price": "2.40",
        "vat_rate": "8.10",
    },
    {
        "demo_key": "demo-spezial-50",
        "sku": "DEMO-SPEZ-50",
        "name": "Spezialbier 50 cl",
        "category": "bier",
        "container_size": "50 cl",
        "list_price": "3.80",
        "vat_rate": "8.10",
    },
    {
        "demo_key": "demo-alkoholfrei-33",
        "sku": "DEMO-AF-33",
        "name": "Alkoholfreies Bier 33 cl",
        "category": "alkoholfrei",
        "container_size": "33 cl",
        "list_price": "2.20",
        "vat_rate": "2.60",
    },
)


def _product_payload(item: dict[str, str]) -> ProductWrite:
    return ProductWrite(
        sku=item["sku"],
        name=item["name"],
        category=item["category"],
        description=DEMO_NOTE,
        container_type="flasche",
        container_size=item["container_size"],
        sales_unit="Flasche",
        list_price=item["list_price"],
        vat_rate=item["vat_rate"],
        is_active=True,
    )


def _upsert_products(db: Session) -> dict[str, Product]:
    stored: dict[str, Product] = {}
    for item in DEMO_PRODUCTS:
        data = _product_payload(item)
        existing = db.scalar(select(Product).where(Product.demo_key == item["demo_key"]))
        if existing is None:
            product = insert_product(db, data, is_demo=True, demo_key=item["demo_key"])
        else:
            ensure_sku(db, data.sku, exclude_id=existing.id)
            product = update_product(db, existing.id, data)
            product.is_demo = True
            product.demo_key = item["demo_key"]
        stored[item["demo_key"]] = product
    return stored


def _upsert_deal(db: Session, partner_id, contact_id) -> Deal:
    data = DealWrite(
        title="Erweiterung des Biersortiments",
        partner_id=partner_id,
        contact_id=contact_id,
        account_owner="Sandra Lutz",
        estimated_value="4800.00",
        expected_close_on="2026-12-15",
        stage="angebot",
        priority="hoch",
        description=(
            "Fiktive Verkaufschance zum Demo-Telefonat. Keine echte Offerte des Liechtensteiner Brauhauses."
        ),
    )
    existing = db.scalar(select(Deal).where(Deal.demo_key == DEAL_KEY))
    if existing is None:
        return insert_deal(db, data, is_demo=True, demo_key=DEAL_KEY)
    archived_at = existing.archived_at
    existing.title = data.title
    existing.partner_id = data.partner_id
    existing.contact_id = data.contact_id
    existing.account_owner = data.account_owner
    existing.estimated_value = data.estimated_value
    existing.expected_close_on = data.expected_close_on
    existing.stage = "angebot"
    existing.probability = STAGE_PROBABILITY["angebot"]
    existing.priority = data.priority
    existing.description = data.description
    existing.closed_on = None
    existing.loss_reason = None
    existing.is_demo = True
    existing.demo_key = DEAL_KEY
    existing.archived_at = archived_at
    db.flush()
    return existing


def _order_payload(partner_id, contact_id, deal_id, products: dict[str, Product]) -> OrderWrite:
    return OrderWrite(
        partner_id=partner_id,
        contact_id=contact_id,
        deal_id=deal_id,
        ordered_on=date(2026, 11, 12),
        requested_delivery_on=date(2026, 11, 20),
        notes=(
            "Fiktive Demo-Bestellung. Eine Übertragung geht nur an das Mock-ERP, erzeugt keine Rechnung "
            "und prüft keinen Lagerbestand."
        ),
        items=[
            OrderItemWrite(product_id=products["demo-lager-33"].id, quantity="24", discount_percent="0"),
            OrderItemWrite(product_id=products["demo-spezial-50"].id, quantity="12", discount_percent="5"),
            OrderItemWrite(product_id=products["demo-alkoholfrei-33"].id, quantity="12", discount_percent="0"),
        ],
        submit=True,
    )


def _upsert_order(db: Session, partner_id, contact_id, deal_id, products: dict[str, Product]) -> Order:
    data = _order_payload(partner_id, contact_id, deal_id, products)
    existing = db.scalar(select(Order).where(Order.demo_key == ORDER_KEY))
    if existing is None:
        return insert_order(db, data, is_demo=True, demo_key=ORDER_KEY, order_number=ORDER_NUMBER)
    for item in _order_items(db, existing.id):
        db.delete(item)
    db.flush()
    existing.partner_id = partner_id
    existing.contact_id = contact_id
    existing.deal_id = deal_id
    existing.ordered_on = data.ordered_on
    existing.requested_delivery_on = data.requested_delivery_on
    existing.status = "eingereicht"
    existing.notes = data.notes
    existing.erp_reference = None
    existing.is_demo = True
    existing.order_number = ORDER_NUMBER
    _build_items(db, existing, data)
    db.flush()
    return existing


def seed_demo_sales(db: Session) -> int:
    partner = db.scalar(select(Partner).where(Partner.demo_key == PARTNER_KEY))
    contact = db.scalar(select(Contact).where(Contact.demo_key == CONTACT_KEY))
    if partner is None or contact is None:
        raise CrmServiceError("Ristorante Lago oder Giulia Bernasconi fehlt. Zuerst die CRM-Testdaten laden.", 409)
    products = _upsert_products(db)
    deal = _upsert_deal(db, partner.id, contact.id)
    _upsert_order(db, partner.id, contact.id, deal.id, products)
    return len(DEMO_PRODUCTS) + 2
