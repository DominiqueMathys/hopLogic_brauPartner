"""Local mock ERP stored in its own SQLite file.

The file is not the CRM database. Every row is fictional demo data and is not
a connection to the ERP of Liechtensteiner Brauhaus.
"""

from __future__ import annotations

import sqlite3
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from threading import Lock

from app.config import settings
from app.integrations.connector import SOURCE_MOCK, register_connector
from app.integrations.types import (
    ErpAmbiguousError,
    ErpCustomer,
    ErpOrderRequest,
    ErpProduct,
    ErpStatusSnapshot,
    ErpSubmitResult,
    ErpTechnicalError,
)

_LOCK = Lock()
_STATUS_FLOW = ("empfangen", "bestaetigt", "in_bearbeitung", "versandt", "geliefert")

_CUSTOMERS = (
    ("10457", "Ristorante Lago", "Via Test 1", "6600", "Locarno", "Schweiz", "+41 00 000 00 01", "ristorante-lago@example.com", "aktiv"),
    ("MOCK-3001", "Gasthaus Mockstein", "Testweg 30", "9490", "Vaduz", "Liechtenstein", "+423 000 00 30", "mockstein@example.com", "aktiv"),
    ("MOCK-ALPEN", "Hotel Alpenblick", "Andere Teststrasse 9", "9490", "Vaduz", "Liechtenstein", "+423 000 00 99", "alpenblick-mock@example.com", "aktiv"),
    ("MOCK-LEER", "", "Testweg 0", "9490", "Vaduz", "Liechtenstein", "", "ungueltig", "aktiv"),
)

_PRODUCTS = (
    ("DEMO-BIER-33", "Lagerbier 33 cl", "Fiktiver Mock-Artikel.", "bier", "Flasche", "flasche", "33 cl", "2.40", "8.10", 1),
    ("DEMO-SPEZ-50", "Spezialbier 50 cl", "Fiktiver Mock-Artikel. Der Richtpreis im Mock weicht vom CRM ab.", "bier", "Flasche", "flasche", "50 cl", "3.90", "8.10", 1),
    ("DEMO-AF-33", "Alkoholfreies Bier 33 cl", "Fiktiver Mock-Artikel.", "alkoholfrei", "Flasche", "flasche", "33 cl", "2.20", "2.60", 1),
    ("MOCK-WEIZEN-50", "Weizenbier 50 cl", "Fiktiver Mock-Artikel, der im CRM noch fehlt.", "bier", "Flasche", "flasche", "50 cl", "3.60", "8.10", 1),
    ("MOCK-PREIS-NEG", "Unbrauchbarer Testartikel", "Fiktiver Datensatz mit ungültigem Preis.", "bier", "Flasche", "flasche", "33 cl", "-1.00", "8.10", 1),
)


def _connect(path: str) -> sqlite3.Connection:
    file = Path(path)
    file.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(file, timeout=5)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS customers (
            number TEXT PRIMARY KEY,
            company_name TEXT NOT NULL,
            street TEXT NOT NULL,
            postal_code TEXT NOT NULL,
            city TEXT NOT NULL,
            country TEXT NOT NULL,
            phone TEXT NOT NULL,
            email TEXT NOT NULL,
            status TEXT NOT NULL,
            is_demo INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            category TEXT NOT NULL,
            sales_unit TEXT NOT NULL,
            container_type TEXT NOT NULL,
            container_size TEXT NOT NULL,
            price TEXT NOT NULL,
            currency TEXT NOT NULL,
            vat_rate TEXT NOT NULL,
            is_active INTEGER NOT NULL,
            is_demo INTEGER NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            idempotency_key TEXT PRIMARY KEY,
            reference TEXT NOT NULL UNIQUE,
            order_number TEXT NOT NULL,
            customer_number TEXT NOT NULL,
            status TEXT NOT NULL,
            delivery_status TEXT NOT NULL,
            delivery_on TEXT,
            delivery_note TEXT NOT NULL,
            invoice_number TEXT NOT NULL,
            invoice_on TEXT,
            invoice_status TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS flags (
            name TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    if connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0] == 0:
        connection.executemany(
            """
            INSERT INTO customers
            (number, company_name, street, postal_code, city, country, phone, email, status, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """,
            _CUSTOMERS,
        )
    if connection.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        connection.executemany(
            """
            INSERT INTO products
            (sku, name, description, category, sales_unit, container_type, container_size, price, currency, vat_rate, is_active, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'CHF', ?, ?, 1)
            """,
            _PRODUCTS,
        )
    connection.commit()


class MockErpConnector:
    """In-process connector over the separate SQLite mock database."""

    source = SOURCE_MOCK

    def __init__(self, path: str | None = None) -> None:
        self.path = path or settings.mock_erp_path

    def _db(self) -> sqlite3.Connection:
        connection = _connect(self.path)
        _ensure(connection)
        return connection

    def test_connection(self) -> str:
        with _LOCK, self._db() as connection:
            count = connection.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
        return f"Mock-ERP erreichbar. Fiktive Kunden im Testdatenbestand: {count}. Keine echte ERP-Verbindung."

    def customers(self) -> list[ErpCustomer]:
        with _LOCK, self._db() as connection:
            rows = connection.execute("SELECT * FROM customers ORDER BY number").fetchall()
        return [
            ErpCustomer(
                number=row["number"],
                company_name=row["company_name"],
                street=row["street"],
                postal_code=row["postal_code"],
                city=row["city"],
                country=row["country"],
                phone=row["phone"],
                email=row["email"],
                status=row["status"],
                is_demo=bool(row["is_demo"]),
            )
            for row in rows
        ]

    def products(self) -> list[ErpProduct]:
        with _LOCK, self._db() as connection:
            rows = connection.execute("SELECT * FROM products ORDER BY sku").fetchall()
        return [
            ErpProduct(
                sku=row["sku"],
                name=row["name"],
                description=row["description"],
                category=row["category"],
                sales_unit=row["sales_unit"],
                container_type=row["container_type"],
                container_size=row["container_size"],
                price=Decimal(row["price"]),
                currency=row["currency"],
                vat_rate=Decimal(row["vat_rate"]),
                is_active=bool(row["is_active"]),
                is_demo=bool(row["is_demo"]),
            )
            for row in rows
        ]

    def arm(self, result: str, times: int = 1) -> None:
        """Test hook. The next submits return 'error' or 'ambiguous' for a limited count."""
        with _LOCK, self._db() as connection:
            connection.execute(
                "INSERT INTO flags (name, value) VALUES ('next_submit', ?) ON CONFLICT(name) DO UPDATE SET value = excluded.value",
                (f"{result}:{times}",),
            )

    def submit_order(self, request: ErpOrderRequest) -> ErpSubmitResult:
        with _LOCK, self._db() as connection:
            flag = connection.execute("SELECT value FROM flags WHERE name = 'next_submit'").fetchone()
            if flag is not None and ":" in flag["value"]:
                kind, raw_count = flag["value"].split(":", 1)
                remaining = int(raw_count) - 1
                if remaining <= 0:
                    connection.execute("DELETE FROM flags WHERE name = 'next_submit'")
                else:
                    connection.execute("UPDATE flags SET value = ? WHERE name = 'next_submit'", (f"{kind}:{remaining}",))
                connection.commit()
                if kind == "error":
                    raise ErpTechnicalError("Das Mock-ERP hat die Übertragung technisch abgelehnt.")
                if kind == "ambiguous":
                    raise ErpAmbiguousError("Das Mock-ERP hat keine eindeutige Antwort geliefert.")
            existing = connection.execute(
                "SELECT reference, status FROM orders WHERE idempotency_key = ?",
                (request.idempotency_key,),
            ).fetchone()
            if existing is not None:
                return ErpSubmitResult(request.idempotency_key, existing["reference"], existing["status"], SOURCE_MOCK)
            token_row = connection.execute("SELECT value FROM flags WHERE name = 'dataset'").fetchone()
            if token_row is None:
                token = uuid.uuid4().hex[:8]
                connection.execute("INSERT INTO flags (name, value) VALUES ('dataset', ?)", (token,))
            else:
                token = token_row["value"]
            count = connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0] + 1
            reference = f"MOCK-AUF-{token}-{count:05d}"
            connection.execute(
                """
                INSERT INTO orders
                (idempotency_key, reference, order_number, customer_number, status, delivery_status, delivery_on, delivery_note, invoice_number, invoice_on, invoice_status, created_at)
                VALUES (?, ?, ?, ?, 'empfangen', 'offen', NULL, '', '', NULL, '', ?)
                """,
                (request.idempotency_key, reference, request.order_number, request.customer_number, _now()),
            )
        return ErpSubmitResult(request.idempotency_key, reference, "empfangen", SOURCE_MOCK)

    def find_order(self, idempotency_key: str) -> ErpSubmitResult | None:
        with _LOCK, self._db() as connection:
            row = connection.execute(
                "SELECT reference, status FROM orders WHERE idempotency_key = ?",
                (idempotency_key,),
            ).fetchone()
        if row is None:
            return None
        return ErpSubmitResult(idempotency_key, row["reference"], row["status"], SOURCE_MOCK)

    def order_status(self, reference: str) -> ErpStatusSnapshot | None:
        with _LOCK, self._db() as connection:
            row = connection.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
        if row is None:
            return None
        return _snapshot(row)

    def advance_status(self, reference: str) -> ErpStatusSnapshot:
        with _LOCK, self._db() as connection:
            row = connection.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
            if row is None:
                raise ErpTechnicalError("Die Mock-Referenz ist nicht vorhanden.")
            current = row["status"]
            if current in _STATUS_FLOW:
                index = _STATUS_FLOW.index(current)
                nxt = _STATUS_FLOW[min(index + 1, len(_STATUS_FLOW) - 1)]
            else:
                nxt = current
            delivery_status = "offen"
            delivery_on = None
            delivery_note = ""
            invoice_number = ""
            invoice_on = None
            invoice_status = ""
            if nxt in {"versandt", "geliefert"}:
                delivery_status = "versandt" if nxt == "versandt" else "geliefert"
                delivery_on = date.today().isoformat()
                delivery_note = f"MOCK-LS-{reference[-5:]}"
            if nxt == "geliefert":
                invoice_number = f"MOCK-RE-{reference[-5:]}"
                invoice_on = date.today().isoformat()
                invoice_status = "externe Mock-Angabe, keine Buchhaltung"
            connection.execute(
                """
                UPDATE orders
                SET status = ?, delivery_status = ?, delivery_on = ?, delivery_note = ?, invoice_number = ?, invoice_on = ?, invoice_status = ?
                WHERE reference = ?
                """,
                (nxt, delivery_status, delivery_on, delivery_note, invoice_number, invoice_on, invoice_status, reference),
            )
            stored = connection.execute("SELECT * FROM orders WHERE reference = ?", (reference,)).fetchone()
        return _snapshot(stored)

    def order_count(self) -> int:
        with _LOCK, self._db() as connection:
            return int(connection.execute("SELECT COUNT(*) FROM orders").fetchone()[0])


def _snapshot(row: sqlite3.Row) -> ErpStatusSnapshot:
    return ErpStatusSnapshot(
        reference=row["reference"],
        status=row["status"],
        source=SOURCE_MOCK,
        delivery_status=row["delivery_status"],
        delivery_on=date.fromisoformat(row["delivery_on"]) if row["delivery_on"] else None,
        delivery_note=row["delivery_note"],
        invoice_number=row["invoice_number"],
        invoice_on=date.fromisoformat(row["invoice_on"]) if row["invoice_on"] else None,
        invoice_status=row["invoice_status"],
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


register_connector(SOURCE_MOCK, MockErpConnector)
