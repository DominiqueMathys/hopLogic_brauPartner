from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ModeWrite(BaseModel):
    mode: str


class IntervalWrite(BaseModel):
    customers_interval_minutes: int = 0
    products_interval_minutes: int = 0
    status_interval_minutes: int = 0


class SyncWrite(BaseModel):
    kind: str


class PreviewItem(BaseModel):
    external_key: str
    label: str
    detail: str


class PreviewRead(BaseModel):
    kind: str
    dry_run: bool
    source_label: str
    new: list[PreviewItem]
    update: list[PreviewItem]
    unchanged: list[PreviewItem]
    conflicts: list[PreviewItem]
    invalid: list[PreviewItem]


class StatusRead(BaseModel):
    mode: str
    mode_label: str
    external_available: bool
    connection_ok: bool | None
    last_tested_at: datetime | None
    last_success_at: datetime | None
    last_failure_at: datetime | None
    synced_records: int
    open_conflicts: int
    customers_interval_minutes: int
    products_interval_minutes: int
    status_interval_minutes: int
    auto_order_transfer: bool
    source_label: str
    leadership: list[str]
    last_success_job_id: UUID | None
    last_failure_job_id: UUID | None


class JobRead(BaseModel):
    id: UUID
    kind: str
    status: str
    dry_run: bool
    started_at: datetime
    finished_at: datetime | None
    processed_count: int
    success_count: int
    failed_count: int
    message: str
    actor_id: UUID | None


class RecordRead(BaseModel):
    id: UUID
    external_key: str
    action: str
    message: str
    crm_id: UUID | None


class JobDetail(JobRead):
    records: list[RecordRead]


class ConflictRead(BaseModel):
    id: UUID
    kind: str
    entity_type: str
    external_key: str
    crm_id: UUID | None
    field_name: str
    crm_value: str
    external_value: str
    message: str
    status: str
    created_at: datetime
    reviewed_at: datetime | None


class TransferRead(BaseModel):
    order_id: UUID
    idempotency_key: str
    status: str
    attempts: int
    external_reference: str | None
    external_status: str | None
    source: str | None
    last_error: str
    delivery_status: str = ""
    delivery_note: str = ""
    invoice_number: str = ""
    invoice_status: str = Field(default="", description="Externe Angabe, keine Buchhaltung.")
