import { ApiError } from './auth.ts'

export type IntegrationStatus = {
  mode: string
  mode_label: string
  external_available: boolean
  connection_ok: boolean | null
  last_tested_at: string | null
  last_success_at: string | null
  last_failure_at: string | null
  synced_records: number
  open_conflicts: number
  customers_interval_minutes: number
  products_interval_minutes: number
  status_interval_minutes: number
  auto_order_transfer: boolean
  source_label: string
  leadership: string[]
}

export type SyncJob = {
  id: string
  kind: string
  status: string
  started_at: string
  finished_at: string | null
  processed_count: number
  success_count: number
  failed_count: number
  message: string
}

export type SyncRecord = {
  id: string
  external_key: string
  action: string
  message: string
  crm_id: string | null
}

export type PreviewGroup = { external_key: string; label: string; detail: string }

export type SyncPreview = {
  kind: string
  dry_run: boolean
  source_label: string
  new: PreviewGroup[]
  update: PreviewGroup[]
  unchanged: PreviewGroup[]
  conflicts: PreviewGroup[]
  invalid: PreviewGroup[]
}

export type SyncConflict = {
  id: string
  kind: string
  entity_type: string
  external_key: string
  crm_id: string | null
  field_name: string
  crm_value: string
  external_value: string
  message: string
  status: string
  created_at: string
}

async function send<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const response = await fetch(path, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!response.ok) {
    let detail = 'Die Anfrage wurde abgelehnt.'
    try {
      const payload = (await response.json()) as { detail?: string }
      if (payload.detail) detail = payload.detail
    } catch {
      detail = response.statusText
    }
    throw new ApiError(response.status, detail)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const fetchIntegrationStatus = () => send<IntegrationStatus>('/api/integration/status')
export const saveIntegrationMode = (mode: string) => send<IntegrationStatus>('/api/integration/mode', 'POST', { mode })
export const saveIntegrationIntervals = (body: { customers_interval_minutes: number; products_interval_minutes: number; status_interval_minutes: number }) =>
  send<IntegrationStatus>('/api/integration/intervals', 'PUT', body)
export const testIntegration = () => send<SyncJob>('/api/integration/test', 'POST')
export const previewSync = (kind: string) => send<SyncPreview>('/api/integration/preview', 'POST', { kind })
export const runSync = (kind: string) => send<SyncJob>('/api/integration/run', 'POST', { kind })
export const fetchSyncJobs = () => send<SyncJob[]>('/api/integration/jobs')
export const fetchSyncJob = (id: string) => send<SyncJob & { records: SyncRecord[] }>(`/api/integration/jobs/${id}`)
export const fetchConflicts = () => send<SyncConflict[]>('/api/integration/conflicts')
export const reviewConflict = (id: string) => send<SyncConflict>(`/api/integration/conflicts/${id}/review`, 'POST')
export const prepareOrderTransfer = (orderId: string) => send<{ status: string; external_reference: string | null; last_error: string; attempts: number }>(`/api/integration/orders/${orderId}/prepare`, 'POST')
export const transferOrder = (orderId: string) => send<{ status: string; external_reference: string | null; last_error: string; attempts: number }>(`/api/integration/orders/${orderId}/transfer`, 'POST')
export const recheckOrder = (orderId: string) => send<{ status: string; external_reference: string | null; last_error: string; attempts: number }>(`/api/integration/orders/${orderId}/recheck`, 'POST')
export const refreshOrderErpStatus = (orderId: string) => send<import('../domain/sales.ts').Order>(`/api/integration/orders/${orderId}/status`, 'POST')
export const advanceMockStatus = (orderId: string) => send<import('../domain/sales.ts').Order>(`/api/integration/orders/${orderId}/advance`, 'POST')

export async function downloadSyncCsv(id: string) {
  const response = await fetch(`/api/integration/jobs/${id}/export`)
  if (!response.ok) throw new ApiError(response.status, 'Das Protokoll konnte nicht exportiert werden.')
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'synchronisation.csv'
  link.click()
  URL.revokeObjectURL(url)
}
