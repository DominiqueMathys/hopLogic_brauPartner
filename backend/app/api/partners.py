from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.partner import Partner
from app.partner_catalog import DIRECTIONS, PARTNER_STATUSES, SORTS
from app.schemas.partner import PartnerFilterOptions, PartnerList, PartnerRead, PartnerSummary, PartnerWrite
from app.services.partners import (
    PartnerServiceError,
    archive_partner,
    distinct_text,
    insert_partner,
    partner_summary,
    query_partners,
    require_partner,
    restore_partner,
    update_partner,
)
from app.services.timeline import attach_partner_timeline

router = APIRouter(prefix="/partners", tags=["vertriebspartner"])


def _save(db: Session, partner: Partner) -> Partner:
    try:
        db.commit()
        db.refresh(partner)
        attach_partner_timeline(db, [partner])
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Die ERP-Kundennummer ist bereits einem Vertriebspartner zugeordnet.",
        ) from None
    return partner


def _call(db: Session, action) -> Partner:
    try:
        partner = action()
    except PartnerServiceError as error:
        db.rollback()
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Die ERP-Kundennummer ist bereits einem Vertriebspartner zugeordnet.",
        ) from None
    return _save(db, partner)


def _clean_query(value: str | None, limit: int = 200) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if len(cleaned) > limit:
        raise HTTPException(status_code=422, detail="Ein Filterwert ist zu lang.")
    return cleaned


@router.get("/summary", response_model=PartnerSummary)
def read_summary(db: Session = Depends(get_db)) -> PartnerSummary:
    active, active_demo = partner_summary(db)
    return PartnerSummary(active=active, active_demo=active_demo)


@router.get("/filters", response_model=PartnerFilterOptions)
def read_filters(db: Session = Depends(get_db)) -> PartnerFilterOptions:
    return PartnerFilterOptions(
        industries=distinct_text(db, Partner.industry),
        regions=distinct_text(db, Partner.region),
        account_owners=distinct_text(db, Partner.account_owner),
    )


@router.get("", response_model=PartnerList)
def list_partners(
    q: str | None = None,
    status: str | None = None,
    industry: str | None = None,
    region: str | None = None,
    account_owner: str | None = None,
    sort: str = "name",
    direction: str = "asc",
    page: int = 1,
    page_size: int = 20,
    include_archived: bool = False,
    db: Session = Depends(get_db),
) -> PartnerList:
    if sort not in SORTS:
        raise HTTPException(status_code=422, detail="Die Sortierung ist ungültig.")
    if direction not in DIRECTIONS:
        raise HTTPException(status_code=422, detail="Die Sortierrichtung ist ungültig.")
    if page < 1 or page_size < 1 or page_size > 100:
        raise HTTPException(status_code=422, detail="Seite oder Seitengrösse ist ungültig.")
    status = _clean_query(status, 40)
    if status is not None and status not in PARTNER_STATUSES:
        raise HTTPException(status_code=422, detail="Der Partnerstatus ist ungültig.")
    rows, total = query_partners(
        db,
        q=_clean_query(q),
        status=status,
        industry=_clean_query(industry, 120),
        region=_clean_query(region, 120),
        account_owner=_clean_query(account_owner, 120),
        include_archived=include_archived,
        sort=sort,
        direction=direction,
        page=page,
        page_size=page_size,
    )
    return PartnerList(
        items=[PartnerRead.model_validate(row) for row in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=PartnerRead, status_code=201)
def create_partner(payload: PartnerWrite, db: Session = Depends(get_db)) -> Partner:
    return _call(db, lambda: insert_partner(db, payload))


@router.get("/{partner_id}", response_model=PartnerRead)
def read_partner(partner_id: UUID, db: Session = Depends(get_db)) -> Partner:
    try:
        partner = require_partner(db, partner_id)
        attach_partner_timeline(db, [partner])
        return partner
    except PartnerServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None


@router.put("/{partner_id}", response_model=PartnerRead)
def edit_partner(partner_id: UUID, payload: PartnerWrite, db: Session = Depends(get_db)) -> Partner:
    return _call(db, lambda: update_partner(db, partner_id, payload))


@router.post("/{partner_id}/archive", response_model=PartnerRead)
def archive(partner_id: UUID, db: Session = Depends(get_db)) -> Partner:
    return _call(db, lambda: archive_partner(db, partner_id))


@router.post("/{partner_id}/restore", response_model=PartnerRead)
def restore(partner_id: UUID, db: Session = Depends(get_db)) -> Partner:
    return _call(db, lambda: restore_partner(db, partner_id))
