"""ERP integration API.

Every route is checked by the application permission dependency. The mock
connector is the only available implementation.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.integration import ErpConflict, ErpOrderTransfer, ErpSyncJob, ErpSyncRecord
from app.models.sales import Order
from app.schemas.integration import (
    ConflictRead,
    IntervalWrite,
    JobDetail,
    JobRead,
    ModeWrite,
    PreviewRead,
    RecordRead,
    StatusRead,
    SyncWrite,
    TransferRead,
)
from app.schemas.sales import OrderRead
from app.services.integration import IntegrationError
from app.services.integration import advance_mock_status, job_csv, preview, pull_order_status, recheck_transfer, review_conflict, run_sync, set_intervals, set_mode, status_payload, test_connection, transfer_order
from app.services.integration import prepare_transfer
from app.services.sales import read_order

router = APIRouter(prefix="/integration", tags=["integration"])


def _actor_id(request: Request) -> UUID | None:
    actor = getattr(request.state, "actor", None)
    return None if actor is None else actor.id


def _run(action):
    try:
        return action()
    except IntegrationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from None


def _job(row: ErpSyncJob) -> JobRead:
    return JobRead.model_validate(row, from_attributes=True)


def _transfer(row: ErpOrderTransfer) -> TransferRead:
    return TransferRead.model_validate(row, from_attributes=True)


@router.get("/status", response_model=StatusRead)
def read_status(db: Session = Depends(get_db)) -> StatusRead:
    return StatusRead.model_validate(status_payload(db))


@router.post("/mode", response_model=StatusRead)
def change_mode(body: ModeWrite, db: Session = Depends(get_db)) -> StatusRead:
    _run(lambda: set_mode(db, body.mode))
    db.commit()
    return StatusRead.model_validate(status_payload(db))


@router.put("/intervals", response_model=StatusRead)
def change_intervals(body: IntervalWrite, db: Session = Depends(get_db)) -> StatusRead:
    _run(lambda: set_intervals(db, body.customers_interval_minutes, body.products_interval_minutes, body.status_interval_minutes))
    db.commit()
    return StatusRead.model_validate(status_payload(db))


@router.post("/test", response_model=JobRead)
def run_test(request: Request, db: Session = Depends(get_db)) -> JobRead:
    job = _run(lambda: test_connection(db, _actor_id(request)))
    db.commit()
    return _job(job)


@router.post("/preview", response_model=PreviewRead)
def run_preview(body: SyncWrite, db: Session = Depends(get_db)) -> PreviewRead:
    payload = _run(lambda: preview(db, body.kind))
    return PreviewRead.model_validate(payload)


@router.post("/run", response_model=JobRead)
def run_now(body: SyncWrite, request: Request, db: Session = Depends(get_db)) -> JobRead:
    job = _run(lambda: run_sync(db, body.kind, _actor_id(request)))
    db.commit()
    return _job(job)


@router.get("/jobs", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[JobRead]:
    rows = db.scalars(select(ErpSyncJob).order_by(ErpSyncJob.started_at.desc()).limit(100)).all()
    return [_job(row) for row in rows]


@router.get("/jobs/{job_id}", response_model=JobDetail)
def read_job(job_id: UUID, db: Session = Depends(get_db)) -> JobDetail:
    job = db.get(ErpSyncJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Der Synchronisationslauf wurde nicht gefunden.")
    records = db.scalars(select(ErpSyncRecord).where(ErpSyncRecord.job_id == job.id).order_by(ErpSyncRecord.external_key)).all()
    payload = _job(job).model_dump()
    payload["records"] = [RecordRead.model_validate(row, from_attributes=True) for row in records]
    return JobDetail.model_validate(payload)


@router.get("/jobs/{job_id}/export")
def export_job(job_id: UUID, db: Session = Depends(get_db)) -> Response:
    content = _run(lambda: job_csv(db, job_id))
    return Response(
        content=("\ufeff" + content).encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="synchronisation.csv"'},
    )


@router.get("/conflicts", response_model=list[ConflictRead])
def list_conflicts(db: Session = Depends(get_db)) -> list[ConflictRead]:
    rows = db.scalars(select(ErpConflict).order_by(ErpConflict.created_at.desc()).limit(200)).all()
    return [ConflictRead.model_validate(row, from_attributes=True) for row in rows]


@router.post("/conflicts/{conflict_id}/review", response_model=ConflictRead)
def mark_reviewed(conflict_id: UUID, request: Request, db: Session = Depends(get_db)) -> ConflictRead:
    row = _run(lambda: review_conflict(db, conflict_id, _actor_id(request)))
    db.commit()
    return ConflictRead.model_validate(row, from_attributes=True)


@router.post("/orders/{order_id}/prepare", response_model=TransferRead)
def prepare_order(order_id: UUID, db: Session = Depends(get_db)) -> TransferRead:
    row = _run(lambda: prepare_transfer(db, order_id))
    db.commit()
    return _transfer(row)


@router.post("/orders/{order_id}/transfer", response_model=TransferRead)
def send_order(order_id: UUID, request: Request, db: Session = Depends(get_db)) -> TransferRead:
    row = _run(lambda: transfer_order(db, order_id, _actor_id(request)))
    db.commit()
    return _transfer(row)


@router.post("/orders/{order_id}/recheck", response_model=TransferRead)
def check_order(order_id: UUID, request: Request, db: Session = Depends(get_db)) -> TransferRead:
    row = _run(lambda: recheck_transfer(db, order_id, _actor_id(request)))
    db.commit()
    return _transfer(row)


@router.post("/orders/{order_id}/status", response_model=OrderRead)
def refresh_status(order_id: UUID, request: Request, db: Session = Depends(get_db)) -> OrderRead:
    _run(lambda: pull_order_status(db, order_id, _actor_id(request)))
    db.commit()
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Die Bestellung wurde nicht gefunden.")
    return read_order(db, order)


@router.post("/orders/{order_id}/advance", response_model=OrderRead)
def advance_status(order_id: UUID, db: Session = Depends(get_db)) -> OrderRead:
    _run(lambda: advance_mock_status(db, order_id))
    db.commit()
    order = db.get(Order, order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Die Bestellung wurde nicht gefunden.")
    return read_order(db, order)
