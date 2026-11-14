"""Request-scoped actor for record-level checks."""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class Actor:
    id: UUID
    email: str
    first_name: str
    last_name: str
    role_code: str
    role_name: str
    permissions: frozenset[str]
    csrf: str

    @property
    def display_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


current_actor: ContextVar[Actor | None] = ContextVar("current_actor", default=None)


def set_actor(actor: Actor | None) -> Token[Actor | None]:
    return current_actor.set(actor)


def reset_actor(token: Token[Actor | None]) -> None:
    try:
        current_actor.reset(token)
    except ValueError:
        current_actor.set(None)


def ticket_owner_limit() -> tuple[str, UUID] | None:
    """Return the signed-in person when they may only see assigned tickets."""
    actor = current_actor.get()
    if actor is None:
        return None
    if "tickets.read" in actor.permissions or "tickets.write" in actor.permissions:
        return None
    if "tickets.read_assigned" in actor.permissions:
        return (actor.display_name, actor.id)
    return None
