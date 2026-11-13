"""Exchangeable outbound mail boundary.

No provider is configured. The gateway refuses delivery instead of pretending to send.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class OutboundMessage:
    recipient: str
    subject: str
    body: str


@dataclass(frozen=True)
class SendResult:
    configured: bool
    status: str
    detail: str


class MailGateway:
    def send(self, message: OutboundMessage) -> SendResult:
        raise NotImplementedError


class UnconfiguredMailGateway(MailGateway):
    def send(self, message: OutboundMessage) -> SendResult:
        return SendResult(
            configured=False,
            status="not_configured",
            detail="Versand nicht konfiguriert",
        )


def current_gateway() -> MailGateway:
    return UnconfiguredMailGateway()
