from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.crm_support import check_page, clean_query, run_write
from app.crm_catalog import DUE_FILTERS, TASK_PRIORITIES, TASK_STATUSES
from app.database import get_db
from app.schemas.task import TaskFilterOptions, TaskList, TaskRead, TaskSummary, TaskWrite
from app.services.crm import complete_task, query_tasks, read_tasks, require_task, task_summary, update_task
from app.services.crm import CrmServiceError
from app.services.crm import insert_task as create_task_row
from app.services.partners import distinct_text
from app.models.task import Task

router = APIRouter(prefix="/tasks", tags=["aufgaben"])


def _one(db: Session, task) -> TaskRead:
    return read_tasks(db, [task])[0]


@router.get("/summary", response_model=TaskSummary)
def read_summary(db: Session = Depends(get_db)) -> TaskSummary:
    open_count, overdue, soon, urgent, demo = task_summary(db)
    return TaskSummary(open=open_count, overdue=overdue, due_soon=soon, urgent=urgent, open_demo=demo)


@router.get("/filters", response_model=TaskFilterOptions)
def read_filters(db: Session = Depends(get_db)) -> TaskFilterOptions:
    return TaskFilterOptions(account_owners=distinct_text(db, Task.account_owner))


@router.get("", response_model=TaskList)
def list_tasks(
    q: str | None = None,
    status: str | None = None,
    priority: str | None = None,
    account_owner: str | None = None,
    partner_id: UUID | None = None,
    contact_id: UUID | None = None,
    due: str | None = None,
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
) -> TaskList:
    check_page(page, page_size)
    status = clean_query(status, 20)
    priority = clean_query(priority, 20)
    due = clean_query(due, 20) or ""
    if status is not None and status not in TASK_STATUSES:
        raise HTTPException(status_code=422, detail="Der Aufgabenstatus ist ungültig.")
    if priority is not None and priority not in TASK_PRIORITIES:
        raise HTTPException(status_code=422, detail="Die Priorität ist ungültig.")
    if due not in DUE_FILTERS:
        raise HTTPException(status_code=422, detail="Der Fälligkeitsfilter ist ungültig.")
    rows, total = query_tasks(
        db,
        q=clean_query(q),
        status=status,
        priority=priority,
        account_owner=clean_query(account_owner, 120),
        partner_id=partner_id,
        contact_id=contact_id,
        due=due or None,
        page=page,
        page_size=page_size,
    )
    return TaskList(items=read_tasks(db, rows), total=total, page=page, page_size=page_size)


@router.post("", response_model=TaskRead, status_code=201)
def create_task(payload: TaskWrite, db: Session = Depends(get_db)) -> TaskRead:
    task = run_write(db, lambda: create_task_row(db, payload))
    return _one(db, task)


@router.get("/{task_id}", response_model=TaskRead)
def read_task(task_id: UUID, db: Session = Depends(get_db)) -> TaskRead:
    try:
        task = require_task(db, task_id)
    except CrmServiceError as error:
        raise HTTPException(status_code=error.status_code, detail=error.message) from None
    return _one(db, task)


@router.put("/{task_id}", response_model=TaskRead)
def edit_task(task_id: UUID, payload: TaskWrite, db: Session = Depends(get_db)) -> TaskRead:
    task = run_write(db, lambda: update_task(db, task_id, payload))
    return _one(db, task)


@router.post("/{task_id}/complete", response_model=TaskRead)
def complete(task_id: UUID, db: Session = Depends(get_db)) -> TaskRead:
    task = run_write(db, lambda: complete_task(db, task_id))
    return _one(db, task)
