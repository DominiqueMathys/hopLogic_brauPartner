from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from app.access import REPORT_SECTIONS, section_permission
from app.database import get_db
from app.schemas.reports import ReportRead
from app.services.exports import render_csv, render_pdf, render_xlsx
from app.services.identity import audit
from app.services.reporting import build_report

router = APIRouter(prefix="/reports", tags=["reporting"])

SECTION_TITLES = {
    "overview": "Gesamtübersicht",
    "sales": "Vertrieb",
    "partners": "Vertriebspartner",
    "orders": "Bestellungen",
    "service": "Kundenservice",
    "marketing": "Marketing",
    "work": "Aktivitäten und Aufgaben",
}


def _allowed(request: Request) -> set[str]:
    actor = getattr(request.state, "actor", None)
    if actor is None:
        raise HTTPException(status_code=401, detail="Anmeldung erforderlich.")
    return {section for section in REPORT_SECTIONS if section_permission(section) in actor.permissions}


def _report(
    db: Session,
    *,
    allowed: set[str],
    date_from: date | None,
    date_to: date | None,
    partner_id: UUID | None,
    region: str | None,
    partner_type: str | None,
    owner: str | None,
) -> dict[str, object]:
    if not allowed:
        raise HTTPException(status_code=403, detail="Keine Berechtigung für diese Aktion.")
    try:
        return build_report(
            db,
            date_from=date_from,
            date_to=date_to,
            partner_id=partner_id,
            region=region or None,
            partner_type=partner_type or None,
            owner=owner or None,
            allowed=allowed,
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from None


@router.get("", response_model=ReportRead)
def get_report(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    partner_id: UUID | None = None,
    region: str | None = None,
    partner_type: str | None = None,
    owner: str | None = None,
    section: str | None = None,
    db: Session = Depends(get_db),
) -> ReportRead:
    allowed = _allowed(request)
    if section:
        if section not in REPORT_SECTIONS or section not in allowed:
            raise HTTPException(status_code=403, detail="Keine Berechtigung für diesen Bericht.")
        allowed = {section}
    payload = _report(
        db,
        allowed=allowed,
        date_from=date_from,
        date_to=date_to,
        partner_id=partner_id,
        region=region,
        partner_type=partner_type,
        owner=owner,
    )
    return ReportRead.model_validate(payload)


@router.post("/export")
def export_report(
    request: Request,
    date_from: date | None = None,
    date_to: date | None = None,
    partner_id: UUID | None = None,
    region: str | None = None,
    partner_type: str | None = None,
    owner: str | None = None,
    section: str | None = None,
    export_format: str = "xlsx",
    db: Session = Depends(get_db),
) -> Response:
    actor = request.state.actor
    allowed = _allowed(request)
    if "reports.export" not in actor.permissions:
        audit(
            db,
            event_type="data_export",
            result="abgelehnt",
            actor_id=actor.id,
            resource_type="report",
            detail=f"Export {export_format} ohne Berechtigung",
        )
        db.commit()
        raise HTTPException(status_code=403, detail="Keine Berechtigung für den Export.")
    if section:
        if section not in REPORT_SECTIONS or section not in allowed:
            audit(
                db,
                event_type="data_export",
                result="abgelehnt",
                actor_id=actor.id,
                resource_type="report",
                resource_id=section,
                detail=f"Export {export_format} abgelehnt",
            )
            db.commit()
            raise HTTPException(status_code=403, detail="Keine Berechtigung für diesen Bericht.")
        allowed = {section}
    if export_format not in {"csv", "xlsx", "pdf"}:
        raise HTTPException(status_code=422, detail="Das Exportformat ist ungültig.")
    payload = _report(
        db,
        allowed=allowed,
        date_from=date_from,
        date_to=date_to,
        partner_id=partner_id,
        region=region,
        partner_type=partner_type,
        owner=owner,
    )
    title = "HopLogic Bericht " + (", ".join(SECTION_TITLES[item] for item in payload["sections"]) or "ohne Bereich")
    if export_format == "csv":
        body = render_csv(payload, title=title)
        media = "text/csv; charset=utf-8"
        filename = "hoplogic-bericht.csv"
    elif export_format == "pdf":
        body = render_pdf(payload, title=title)
        media = "application/pdf"
        filename = "hoplogic-bericht.pdf"
    else:
        body = render_xlsx(payload, title=title)
        media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "hoplogic-bericht.xlsx"
    audit(
        db,
        event_type="data_export",
        result="erfolg",
        actor_id=actor.id,
        resource_type="report",
        resource_id=",".join(str(item) for item in payload["sections"])[:80],
        detail=f"Export {export_format}, Zeitraum {payload['period_from']} bis {payload['period_to']}",
    )
    db.commit()
    return Response(content=body, media_type=media, headers={"Content-Disposition": f'attachment; filename="{filename}"'})
