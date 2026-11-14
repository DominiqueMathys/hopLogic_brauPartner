import {
  toPayload,
  type Partner,
  type PartnerFilters,
  type PartnerInput,
  type PartnerList,
  type PartnerQuery,
  type PartnerSummary,
} from '../domain/partners.ts'

export class ApiError extends Error {
  readonly status: number
  readonly fieldErrors: Record<string, string>

  constructor(status: number, message: string, fieldErrors: Record<string, string> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.fieldErrors = fieldErrors
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function requiredString(value: unknown, fallback: string): string {
  if (typeof value !== 'string' || !value) {
    throw new ApiError(500, fallback)
  }
  return value
}

function optionalString(value: unknown): string | null {
  if (value == null) {
    return null
  }
  if (typeof value !== 'string') {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return value
}

export function readPartner(value: unknown): Partner {
  if (!isRecord(value)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    id: requiredString(value.id, 'Die API hat eine unerwartete Antwort geliefert.'),
    company_name: requiredString(value.company_name, 'Die API hat eine unerwartete Antwort geliefert.'),
    erp_customer_number: optionalString(value.erp_customer_number),
    erp_customer_status: optionalString(value.erp_customer_status),
    erp_source: optionalString(value.erp_source),
    erp_synced_at: optionalString(value.erp_synced_at),
    partner_type: requiredString(value.partner_type, 'Die API hat eine unerwartete Antwort geliefert.'),
    industry: optionalString(value.industry),
    street: optionalString(value.street),
    postal_code: optionalString(value.postal_code),
    city: optionalString(value.city),
    region: optionalString(value.region),
    country: requiredString(value.country, 'Die API hat eine unerwartete Antwort geliefert.'),
    phone: optionalString(value.phone),
    email: optionalString(value.email),
    website: optionalString(value.website),
    status: requiredString(value.status, 'Die API hat eine unerwartete Antwort geliefert.'),
    account_owner: optionalString(value.account_owner),
    acquisition_source: optionalString(value.acquisition_source),
    priority: requiredString(value.priority, 'Die API hat eine unerwartete Antwort geliefert.'),
    first_contact_on: optionalString(value.first_contact_on),
    notes: optionalString(value.notes),
    is_demo: value.is_demo === true,
    archived_at: optionalString(value.archived_at),
    created_at: requiredString(value.created_at, 'Die API hat eine unerwartete Antwort geliefert.'),
    updated_at: requiredString(value.updated_at, 'Die API hat eine unerwartete Antwort geliefert.'),
    last_contact_at: optionalString(value.last_contact_at),
    next_activity_on: optionalString(value.next_activity_on),
  }
}

function fieldErrorsFrom(detail: unknown): Record<string, string> {
  if (!Array.isArray(detail)) {
    return {}
  }
  const errors: Record<string, string> = {}
  for (const item of detail) {
    if (!isRecord(item) || !Array.isArray(item.loc)) {
      continue
    }
    const field = item.loc.find((part) => typeof part === 'string' && part !== 'body')
    const message = typeof item.msg === 'string' ? item.msg.replace(/^Value error,\s*/, '') : 'Eingabe prüfen.'
    if (typeof field === 'string') {
      errors[field] = message
    }
  }
  return errors
}

function parseError(status: number, body: unknown): ApiError {
  const detail = isRecord(body) ? body.detail : undefined
  const fieldErrors = fieldErrorsFrom(detail)
  if (typeof detail === 'string') {
    return new ApiError(status, detail, fieldErrors)
  }
  if (Object.keys(fieldErrors).length > 0) {
    return new ApiError(status, 'Bitte prüfen Sie die markierten Felder.', fieldErrors)
  }
  if (status === 404) {
    return new ApiError(status, 'Der Vertriebspartner wurde nicht gefunden.')
  }
  return new ApiError(status, 'Die Anfrage konnte nicht verarbeitet werden.')
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      },
    })
  } catch {
    throw new ApiError(0, 'Die Verbindung zur API ist fehlgeschlagen.')
  }
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    throw parseError(response.status, body)
  }
  return body
}

function readList(value: unknown): PartnerList {
  if (!isRecord(value) || !Array.isArray(value.items) || typeof value.total !== 'number') {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    items: value.items.map((item) => readPartner(item)),
    total: value.total,
    page: typeof value.page === 'number' ? value.page : 1,
    page_size: typeof value.page_size === 'number' ? value.page_size : 20,
  }
}

function readStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return value.filter((item): item is string => typeof item === 'string')
}

export async function fetchPartners(query: PartnerQuery): Promise<PartnerList> {
  const params = new URLSearchParams()
  if (query.q) {
    params.set('q', query.q)
  }
  if (query.status) {
    params.set('status', query.status)
  }
  if (query.industry) {
    params.set('industry', query.industry)
  }
  if (query.region) {
    params.set('region', query.region)
  }
  if (query.accountOwner) {
    params.set('account_owner', query.accountOwner)
  }
  if (query.sort !== 'name') {
    params.set('sort', query.sort)
  }
  if (query.direction !== 'asc') {
    params.set('direction', query.direction)
  }
  if (query.page > 1) {
    params.set('page', String(query.page))
  }
  params.set('page_size', '20')
  if (query.includeArchived) {
    params.set('include_archived', 'true')
  }
  return readList(await request(`/api/partners?${params.toString()}`))
}

export async function fetchPartnerFilters(): Promise<PartnerFilters> {
  const body = await request('/api/partners/filters')
  if (!isRecord(body)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    industries: readStringList(body.industries),
    regions: readStringList(body.regions),
    accountOwners: readStringList(body.account_owners),
  }
}

export async function fetchPartnerSummary(): Promise<PartnerSummary> {
  const body = await request('/api/partners/summary')
  if (!isRecord(body) || typeof body.active !== 'number' || typeof body.active_demo !== 'number') {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return { active: body.active, active_demo: body.active_demo }
}

export async function fetchPartner(id: string): Promise<Partner> {
  return readPartner(await request(`/api/partners/${id}`))
}

export async function createPartner(input: PartnerInput): Promise<Partner> {
  return readPartner(await request('/api/partners', { method: 'POST', body: JSON.stringify(toPayload(input)) }))
}

export async function updatePartner(id: string, input: PartnerInput): Promise<Partner> {
  return readPartner(
    await request(`/api/partners/${id}`, { method: 'PUT', body: JSON.stringify(toPayload(input)) }),
  )
}

export async function archivePartner(id: string): Promise<Partner> {
  return readPartner(await request(`/api/partners/${id}/archive`, { method: 'POST' }))
}

export async function restorePartner(id: string): Promise<Partner> {
  return readPartner(await request(`/api/partners/${id}/restore`, { method: 'POST' }))
}
