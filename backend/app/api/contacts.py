from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.crm_support import check_page, clean_query, run_write
from app.crm_catalog import CONTACT_SORTS, CONTACT_STATUSES
from app.database import get_db
from app.partner_catalog import DIRECTIONS
from app.schemas.contact import (
    CompanyLinkWrite,
    ContactFilterOptions,
    ContactList,
    ContactRead,
    ContactUpdate,
    ContactWrite,
)
from app.services.crm import (
    CrmServiceError,
    archive_contact,
    contact_filter_options,
    link_company,
    query_contacts,
    read_contacts,
    require_contact,
    restore_contact,
    set_primary_company,
    unlink_company,
    update_contact,
)
from app.services.crm import insert_contact as create_contact_row

router = APIRouter(prefix="/contacts", tags=["kontakte"])


def _one(db: Session, contact) -> ContactRead:
    return read_contacts(db, [contact])[0]


@router.get("/filters", response_model=ContactFilterOptions)
def read_filters(db: Session = Depends(get_db)) -> ContactFilterOptions:
    companies, owners = contact_filter_options(db)
    return ContactFilterOptions(companies=companies, account_owners=owners)


@router.get("", response_model=ContactList)
def list_contacts(
    q: str | None = None,
    partner_id: UUID | None = None,
    status: str | None = None,
    account_owner: str | None = None,
    sort: str = "name",
    direction: str = "asc",
    page: int = 1,
    page_size: int = 20,
    include_archived: bool = False,
    db: Session = Depends(get_db),
) -> ContactList:
    if sort not in CONTACT_SORTS:
        raise HTTPException(status_code=422, detail="Die Sortierung ist ungültig.")
    if direction not in DIRECTIONS:
        raise HTTPException(status_code=422, detail="Die Sortierrichtung ist ungültig.")
    check_page(page, page_size)
    status = clean_query(status, 20)
    if status is not None and status not in CONTACT_STATUSES:
        raise HTTPException(status_code=422, detail="Der Kontaktstatus ist ungültig.")
    rows, total = query_contacts(
        db,
        q=clean_query(q),
        partner_id=partner_id,
        status=status,
        account_owner=clean_query(account_owner, 120),
        include_archived=include_archived,
        sort=sort,
        direction=direction,
        page=page,
        page_size=page_size,
    )
    return ContactList(items=read_contacts(db, rows), total=total, page=page, page_size=page_size)


@router.post("", response_model=ContactRead, status_code=201)
def create_contact(payload: ContactWrite, db: Session = Depends(get_db)) -> ContactRead:
    contact = run_write(db, lambda: create_contact_row(db, payload))
    return _one(db, contact)


@router.get("/{contact_id}", response_model=ContactRead)
def read_contact(contact_id: UUID, db: Session = Depends(get_db)) -> ContactRead:
    try:
        contact = require_contact(db, contact_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return _one(db, contact)


@router.put("/{contact_id}", response_model=ContactRead)
def edit_contact(contact_id: UUID, payload: ContactUpdate, db: Session = Depends(get_db)) -> ContactRead:
    contact = run_write(db, lambda: update_contact(db, contact_id, payload))
    return _one(db, contact)


@router.post("/{contact_id}/archive", response_model=ContactRead)
def archive(contact_id: UUID, db: Session = Depends(get_db)) -> ContactRead:
    contact = run_write(db, lambda: archive_contact(db, contact_id))
    return _one(db, contact)


@router.post("/{contact_id}/restore", response_model=ContactRead)
def restore(contact_id: UUID, db: Session = Depends(get_db)) -> ContactRead:
    contact = run_write(db, lambda: restore_contact(db, contact_id))
    return _one(db, contact)


@router.post("/{contact_id}/companies", response_model=ContactRead)
def add_company(contact_id: UUID, payload: CompanyLinkWrite, db: Session = Depends(get_db)) -> ContactRead:
    contact = run_write(db, lambda: link_company(db, contact_id, payload.partner_id, payload.is_primary))
    return _one(db, contact)


@router.delete("/{contact_id}/companies/{partner_id}", response_model=ContactRead)
def remove_company(contact_id: UUID, partner_id: UUID, db: Session = Depends(get_db)) -> ContactRead:
    contact = run_write(db, lambda: unlink_company(db, contact_id, partner_id))
    return _one(db, contact)


@router.post("/{contact_id}/companies/{partner_id}/primary", response_model=ContactRead)
def make_primary(contact_id: UUID, partner_id: UUID, db: Session = Depends(get_db)) -> ContactRead:
    contact = run_write(db, lambda: set_primary_company(db, contact_id, partner_id))
    return _one(db, contact)
