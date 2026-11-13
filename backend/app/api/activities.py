from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.crm_support import check_page, clean_query, run_write
from app.crm_catalog import ACTIVITY_TYPES
from app.database import get_db
from app.schemas.activity import ActivityList, ActivityRead, ActivityWrite, NoteWithTaskRead, NoteWithTaskWrite
from app.services.crm import (
    CrmServiceError,
    archive_activity,
    create_note_with_task,
    query_activities,
    read_activities,
    read_tasks,
    require_activity,
    restore_activity,
    update_activity,
)
from app.services.crm import insert_activity as create_activity_row

router = APIRouter(prefix="/activities", tags=["aktivitaeten"])


def _one(db: Session, activity) -> ActivityRead:
    return read_activities(db, [activity])[0]


@router.get("", response_model=ActivityList)
def list_activities(
    q: str | None = None,
    activity_type: str | None = None,
    partner_id: UUID | None = None,
    contact_id: UUID | None = None,
    page: int = 1,
    page_size: int = 20,
    include_archived: bool = False,
    db: Session = Depends(get_db),
) -> ActivityList:
    check_page(page, page_size)
    activity_type = clean_query(activity_type, 30)
    if activity_type is not None and activity_type not in ACTIVITY_TYPES:
        raise HTTPException(status_code=422, detail="Der Aktivitätstyp ist ungültig.")
    rows, total = query_activities(
        db,
        q=clean_query(q),
        activity_type=activity_type,
        partner_id=partner_id,
        contact_id=contact_id,
        include_archived=include_archived,
        page=page,
        page_size=page_size,
    )
    return ActivityList(items=read_activities(db, rows), total=total, page=page, page_size=page_size)


@router.post("", response_model=ActivityRead, status_code=201)
def create_activity(payload: ActivityWrite, db: Session = Depends(get_db)) -> ActivityRead:
    activity = run_write(db, lambda: create_activity_row(db, payload))
    return _one(db, activity)


@router.post("/note-with-task", response_model=NoteWithTaskRead, status_code=201)
def create_note(payload: NoteWithTaskWrite, db: Session = Depends(get_db)) -> NoteWithTaskRead:
    activity, task = run_write(db, lambda: create_note_with_task(db, payload))
    return NoteWithTaskRead(
        activity=_one(db, activity),
        task=read_tasks(db, [task])[0] if task is not None else None,
    )


@router.get("/{activity_id}", response_model=ActivityRead)
def read_activity(activity_id: UUID, db: Session = Depends(get_db)) -> ActivityRead:
    try:
        activity = require_activity(db, activity_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return _one(db, activity)


@router.put("/{activity_id}", response_model=ActivityRead)
def edit_activity(activity_id: UUID, payload: ActivityWrite, db: Session = Depends(get_db)) -> ActivityRead:
    activity = run_write(db, lambda: update_activity(db, activity_id, payload))
    return _one(db, activity)


@router.post("/{activity_id}/archive", response_model=ActivityRead)
def archive(activity_id: UUID, db: Session = Depends(get_db)) -> ActivityRead:
    activity = run_write(db, lambda: archive_activity(db, activity_id))
    return _one(db, activity)


@router.post("/{activity_id}/restore", response_model=ActivityRead)
def restore(activity_id: UUID, db: Session = Depends(get_db)) -> ActivityRead:
    activity = run_write(db, lambda: restore_activity(db, activity_id))
    return _one(db, activity)
