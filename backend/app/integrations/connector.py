"""ERP connector boundary.

A future vendor connector implements ErpConnector, reads its address and
credentials from the environment, and speaks TLS. It is registered with
register_connector. Until that happens, only the local mock connector exists,
and the mode «extern» stays unavailable.
"""

from __future__ import annotations

from typing import Protocol

from app.integrations.types import ErpCustomer, ErpOrderRequest, ErpProduct, ErpStatusSnapshot, ErpSubmitResult

SOURCE_MOCK = "mock"
SOURCE_EXTERN = "extern"
SOURCE_LABELS = {
    SOURCE_MOCK: "Mock-ERP (fiktive Testdaten, keine echte ERP-Verbindung)",
    SOURCE_EXTERN: "Externes ERP",
}


class ErpConnector(Protocol):
    source: str

    def test_connection(self) -> str: ...

    def customers(self) -> list[ErpCustomer]: ...

    def products(self) -> list[ErpProduct]: ...

    def submit_order(self, request: ErpOrderRequest) -> ErpSubmitResult: ...

    def find_order(self, idempotency_key: str) -> ErpSubmitResult | None: ...

    def order_status(self, reference: str) -> ErpStatusSnapshot | None: ...

    def advance_status(self, reference: str) -> ErpStatusSnapshot: ...


_REGISTRY: dict[str, type] = {}


def register_connector(source: str, factory: type) -> None:
    """Register a connector class. Tests and a future package call this."""
    _REGISTRY[source] = factory


def connector_registered(source: str) -> bool:
    return source in _REGISTRY


def build_connector(source: str) -> ErpConnector:
    factory = _REGISTRY.get(source)
    if factory is None:
        raise LookupError(source)
    return factory()
