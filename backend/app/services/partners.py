from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.partner import Partner
from app.schemas.partner import PartnerWrite

WRITABLE_FIELDS = (
    "company_name",
    "erp_customer_number",
    "partner_type",
    "industry",
    "street",
    "postal_code",
    "city",
    "region",
    "country",
    "phone",
    "email",
    "website",
    "status",
    "account_owner",
    "acquisition_source",
    "priority",
    "first_contact_on",
    "notes",
)


class PartnerServiceError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def contains_pattern(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def require_partner(db: Session, partner_id: UUID) -> Partner:
    partner = db.get(Partner, partner_id)
    if partner is None:
        raise PartnerServiceError("Der Vertriebspartner wurde nicht gefunden.", 404)
    return partner


def ensure_unique(db: Session, data: PartnerWrite, exclude_id: UUID | None = None) -> None:
    if data.erp_customer_number:
        statement = select(Partner).where(func.lower(Partner.erp_customer_number) == data.erp_customer_number.casefold())
        if exclude_id is not None:
            statement = statement.where(Partner.id != exclude_id)
        if db.scalars(statement).first() is not None:
            raise PartnerServiceError(
                "Die ERP-Kundennummer ist bereits einem Vertriebspartner zugeordnet.",
                409,
            )

    statement = select(Partner).where(
        Partner.archived_at.is_(None),
        func.lower(Partner.company_name) == data.company_name.casefold(),
    )
    if data.city is None:
        statement = statement.where(Partner.city.is_(None))
        message = "Ein Vertriebspartner mit diesem Unternehmensnamen ist bereits vorhanden."
    else:
        statement = statement.where(func.lower(Partner.city) == data.city.casefold())
        message = "Ein Vertriebspartner mit diesem Unternehmensnamen und Ort ist bereits vorhanden."
    if exclude_id is not None:
        statement = statement.where(Partner.id != exclude_id)
    if db.scalars(statement).first() is not None:
        raise PartnerServiceError(message, 409)


def apply_write(partner: Partner, data: PartnerWrite) -> None:
    for field in WRITABLE_FIELDS:
        setattr(partner, field, getattr(data, field))
    partner.updated_at = datetime.now(timezone.utc)


def insert_partner(db: Session, data: PartnerWrite) -> Partner:
    ensure_unique(db, data)
    partner = Partner(is_demo=False)
    apply_write(partner, data)
    db.add(partner)
    db.flush()
    return partner


def update_partner(db: Session, partner_id: UUID, data: PartnerWrite) -> Partner:
    partner = require_partner(db, partner_id)
    if partner.archived_at is not None:
        raise PartnerServiceError(
            "Archivierte Partner können erst nach der Wiederherstellung bearbeitet werden.",
            409,
        )
    ensure_unique(db, data, exclude_id=partner.id)
    apply_write(partner, data)
    db.flush()
    return partner


def archive_partner(db: Session, partner_id: UUID) -> Partner:
    partner = require_partner(db, partner_id)
    if partner.archived_at is not None:
        raise PartnerServiceError("Der Vertriebspartner ist bereits archiviert.", 409)
    partner.archived_at = datetime.now(timezone.utc)
    partner.updated_at = partner.archived_at
    db.flush()
    return partner


def write_from_partner(partner: Partner) -> PartnerWrite:
    payload = {field: getattr(partner, field) for field in WRITABLE_FIELDS}
    return PartnerWrite.model_validate(payload)


def restore_partner(db: Session, partner_id: UUID) -> Partner:
    partner = require_partner(db, partner_id)
    if partner.archived_at is None:
        raise PartnerServiceError("Der Vertriebspartner ist nicht archiviert.", 409)
    ensure_unique(db, write_from_partner(partner), exclude_id=partner.id)
    partner.archived_at = None
    partner.updated_at = datetime.now(timezone.utc)
    db.flush()
    return partner


def build_filters(
    *,
    q: str | None,
    status: str | None,
    industry: str | None,
    region: str | None,
    account_owner: str | None,
    include_archived: bool,
) -> list:
    filters = []
    if not include_archived:
        filters.append(Partner.archived_at.is_(None))
    if q and q.strip():
        pattern = contains_pattern(q.strip())
        filters.append(
            or_(
                Partner.company_name.ilike(pattern, escape="\\"),
                Partner.city.ilike(pattern, escape="\\"),
                Partner.erp_customer_number.ilike(pattern, escape="\\"),
            )
        )
    if status:
        filters.append(Partner.status == status)
    if industry:
        filters.append(func.lower(Partner.industry) == industry.casefold())
    if region:
        filters.append(func.lower(Partner.region) == region.casefold())
    if account_owner:
        filters.append(func.lower(Partner.account_owner) == account_owner.casefold())
    return filters


def query_partners(
    db: Session,
    *,
    q: str | None,
    status: str | None,
    industry: str | None,
    region: str | None,
    account_owner: str | None,
    include_archived: bool,
    sort: str,
    direction: str,
    page: int,
    page_size: int,
) -> tuple[list[Partner], int]:
    filters = build_filters(
        q=q,
        status=status,
        industry=industry,
        region=region,
        account_owner=account_owner,
        include_archived=include_archived,
    )
    count_statement = select(func.count()).select_from(Partner)
    statement = select(Partner)
    if filters:
        count_statement = count_statement.where(*filters)
        statement = statement.where(*filters)
    total = int(db.scalar(count_statement) or 0)
    column = Partner.created_at if sort == "created_at" else Partner.company_name
    ordered = column.desc() if direction == "desc" else column.asc()
    rows = db.scalars(
        statement.order_by(ordered, Partner.id.asc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    return list(rows), total


def partner_summary(db: Session) -> tuple[int, int]:
    active = (Partner.status == "aktiv", Partner.archived_at.is_(None))
    active_count = int(db.scalar(select(func.count()).select_from(Partner).where(*active)) or 0)
    demo_count = int(
        db.scalar(select(func.count()).select_from(Partner).where(*active, Partner.is_demo.is_(True))) or 0
    )
    return active_count, demo_count


def distinct_text(db: Session, column) -> list[str]:
    rows = db.scalars(select(column).where(column.is_not(None)).distinct()).all()
    values = {row.strip() for row in rows if isinstance(row, str) and row.strip()}
    return sorted(values, key=str.casefold)


def upsert_demo_partner(db: Session, demo_key: str, data: PartnerWrite) -> None:
    existing = db.scalar(select(Partner).where(Partner.demo_key == demo_key))
    if existing is None:
        ensure_unique(db, data)
        partner = Partner(is_demo=True, demo_key=demo_key)
        apply_write(partner, data)
        db.add(partner)
        return
    ensure_unique(db, data, exclude_id=existing.id)
    apply_write(existing, data)
    existing.is_demo = True
    existing.demo_key = demo_key
