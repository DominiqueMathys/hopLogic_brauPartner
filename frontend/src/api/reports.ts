import { ApiError } from './auth.ts'

export type ReportPoint = {
  label: string
  count: number | null
  amount: string | null
  counted?: boolean | null
}

export type ReportChart = {
  section: string
  key: string
  title: string
  kind: 'bar' | 'line' | 'donut'
  unit: string
  points: ReportPoint[]
  note: string
}

export type ReportKpi = {
  section: string
  key: string
  label: string
  value: string | null
  unit: string
  note: string
}

export type ReportTable = {
  section: string
  key: string
  title: string
  columns: { key: string; label: string }[]
  rows: Record<string, string>[]
  note: string
}

export type ReportPayload = {
  generated_at: string
  period_from: string
  period_to: string
  filters: {
    partner_id: string | null
    region: string | null
    partner_type: string | null
    owner: string | null
  }
  sections: string[]
  definitions: Record<string, string>
  kpis: ReportKpi[]
  charts: ReportChart[]
  tables: ReportTable[]
  notices: string[]
  options: {
    regions: string[]
    partner_types: string[]
    owners: string[]
    partners: { id: string; label: string }[]
  }
  source: string
}

export type ReportQuery = {
  dateFrom: string
  dateTo: string
  partnerId: string
  region: string
  partnerType: string
  owner: string
  section?: string
}

export function reportParams(query: ReportQuery): URLSearchParams {
  const params = new URLSearchParams()
  if (query.dateFrom) params.set('date_from', query.dateFrom)
  if (query.dateTo) params.set('date_to', query.dateTo)
  if (query.partnerId) params.set('partner_id', query.partnerId)
  if (query.region) params.set('region', query.region)
  if (query.partnerType) params.set('partner_type', query.partnerType)
  if (query.owner) params.set('owner', query.owner)
  if (query.section) params.set('section', query.section)
  return params
}

export async function fetchReport(query: ReportQuery): Promise<ReportPayload> {
  const response = await fetch(`/api/reports?${reportParams(query)}`)
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    throw new ApiError(response.status, typeof detail === 'string' ? detail : 'Der Bericht konnte nicht geladen werden.')
  }
  return body as ReportPayload
}

export async function downloadReport(query: ReportQuery, format: 'csv' | 'xlsx' | 'pdf'): Promise<void> {
  const params = reportParams(query)
  params.set('export_format', format)
  const response = await fetch(`/api/reports/export?${params}`, { method: 'POST' })
  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null)
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    throw new ApiError(response.status, typeof detail === 'string' ? detail : 'Der Export wurde abgelehnt.')
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = format === 'xlsx' ? 'hoplogic-bericht.xlsx' : format === 'pdf' ? 'hoplogic-bericht.pdf' : 'hoplogic-bericht.csv'
  link.click()
  URL.revokeObjectURL(url)
}
