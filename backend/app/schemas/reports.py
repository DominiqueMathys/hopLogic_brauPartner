from datetime import date, datetime

from pydantic import BaseModel


class ReportFilters(BaseModel):
    partner_id: str | None
    region: str | None
    partner_type: str | None
    owner: str | None


class KpiRead(BaseModel):
    section: str
    key: str
    label: str
    value: str | None
    unit: str
    note: str


class ChartPoint(BaseModel):
    label: str
    count: int | None = None
    amount: str | None = None
    counted: bool | None = None


class ChartRead(BaseModel):
    section: str
    key: str
    title: str
    kind: str
    unit: str
    points: list[ChartPoint]
    note: str


class TableColumn(BaseModel):
    key: str
    label: str


class TableRead(BaseModel):
    section: str
    key: str
    title: str
    columns: list[TableColumn]
    rows: list[dict[str, str]]
    note: str


class PartnerOption(BaseModel):
    id: str
    label: str


class ReportOptions(BaseModel):
    regions: list[str]
    partner_types: list[str]
    owners: list[str]
    partners: list[PartnerOption]


class ReportRead(BaseModel):
    generated_at: datetime
    period_from: date
    period_to: date
    filters: ReportFilters
    sections: list[str]
    definitions: dict[str, str]
    kpis: list[KpiRead]
    charts: list[ChartRead]
    tables: list[TableRead]
    notices: list[str]
    options: ReportOptions
    source: str


class ExportMeta(BaseModel):
    filename: str
    media_type: str
