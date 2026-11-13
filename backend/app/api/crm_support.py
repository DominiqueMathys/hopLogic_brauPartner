from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.crm import CrmServiceError

T = TypeVar("T")


def clean_query(value: str | None, limit: int = 200) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > limit:
        raise HTTPException(status_code=422, detail="Ein Filterwert ist zu lang.")
    return cleaned


def check_page(page: int, page_size: int) -> None:
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="Seite oder Seitengrösse ist ungültig.")


def run_write(db: Session, action: Callable[[], T]) -> T:
    try:
        result = action()
        db.commit()
    except CrmServiceError as error:
        db.rollback()
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Der Datensatz verletzt eine Eindeutigkeitsregel.",
        ) from None
    return result
