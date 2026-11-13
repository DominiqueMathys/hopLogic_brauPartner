import { ApiError } from './partners.ts'
import type {
  PartnerAnalysis,
  Segment,
  SegmentInput,
  SegmentPartner,
  Ticket,
  TicketAttachment,
  TicketDetail,
  TicketInput,
  TicketList,
  TicketSummary,
} from '../domain/service.ts'
import { segmentPayload, ticketPayload } from '../domain/service.ts'

export { ApiError }

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function requiredString(value: unknown): string {
  if (typeof value !== 'string' || !value) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return value
}

function optionalString(value: unknown): string | null {
  if (value == null) return null
  if (typeof value !== 'string') throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  return value
}

function requiredNumber(value: unknown): number {
  if (typeof value !== 'number') throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  return value
}

function countMap(value: unknown): Record<string, number> {
  if (!isRecord(value)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  const result: Record<string, number> = {}
  for (const [key, count] of Object.entries(value)) {
    if (typeof count !== 'number') throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
    result[key] = count
  }
  return result
}

function fieldErrorsFrom(detail: unknown): Record<string, string> {
  if (!Array.isArray(detail)) return {}
  const errors: Record<string, string> = {}
  for (const item of detail) {
    if (!isRecord(item) || !Array.isArray(item.loc)) continue
    const field = item.loc.find((part) => typeof part === 'string' && part !== 'body')
    const message = typeof item.msg === 'string' ? item.msg.replace(/^Value error,\s*/, '') : 'Eingabe prüfen.'
    if (typeof field === 'string') errors[field] = message
  }
  return errors
}

async function request(path: string, init?: RequestInit): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError(0, 'Die Verbindung zur API ist fehlgeschlagen.')
  }
  if (response.status === 204) return null
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = isRecord(body) ? body.detail : undefined
    const message = typeof detail === 'string' ? detail : 'Die Anfrage konnte nicht ausgeführt werden.'
    throw new ApiError(response.status, message, fieldErrorsFrom(detail))
  }
  return body
}

function readTicket(value: unknown): Ticket {
  if (!isRecord(value)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  return {
    id: requiredString(value.id),
    ticket_number: requiredString(value.ticket_number),
    subject: requiredString(value.subject),
    category: requiredString(value.category),
    priority: requiredString(value.priority),
    status: requiredString(value.status),
    partner_id: requiredString(value.partner_id),
    company_name: requiredString(value.company_name),
    contact_id: optionalString(value.contact_id),
    contact_name: optionalString(value.contact_name),
    account_owner: optionalString(value.account_owner),
    due_on: optionalString(value.due_on),
    is_overdue: value.is_overdue === true,
    is_demo: value.is_demo === true,
    created_at: requiredString(value.created_at),
    updated_at: requiredString(value.updated_at),
  }
}

function readDetail(value: unknown): TicketDetail {
  if (!isRecord(value) || !Array.isArray(value.events) || !Array.isArray(value.products)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  const base = readTicket(value)
  return {
    ...base,
    description: requiredString(value.description),
    order_id: optionalString(value.order_id),
    order_number: optionalString(value.order_number),
    internal_remark: optionalString(value.internal_remark),
    resolved_at: optionalString(value.resolved_at),
    closed_at: optionalString(value.closed_at),
    products: value.products.map((item) => {
      if (!isRecord(item)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
      return { id: requiredString(item.id), name: requiredString(item.name), sku: requiredString(item.sku) }
    }),
    events: value.events.map((item) => {
      if (!isRecord(item)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
      return {
        id: requiredString(item.id),
        event_type: requiredString(item.event_type),
        from_value: optionalString(item.from_value),
        to_value: optionalString(item.to_value),
        note: optionalString(item.note),
        changed_by: optionalString(item.changed_by),
        task_id: optionalString(item.task_id),
        changed_at: requiredString(item.changed_at),
      }
    }),
    attachments: Array.isArray(value.attachments)
      ? value.attachments.map((item) => {
          if (!isRecord(item)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
          return {
            id: requiredString(item.id),
            original_name: requiredString(item.original_name),
            content_type: requiredString(item.content_type),
            size_bytes: requiredNumber(item.size_bytes),
            created_at: requiredString(item.created_at),
          }
        })
      : [],
    resolutions: Array.isArray(value.resolutions)
      ? value.resolutions.map((item) => {
          if (!isRecord(item)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
          return {
            id: requiredString(item.id),
            code: requiredString(item.code),
            note: optionalString(item.note),
            recorded_by: optionalString(item.recorded_by),
            recorded_at: requiredString(item.recorded_at),
          }
        })
      : [],
    tasks: Array.isArray(value.tasks)
      ? value.tasks.map((item) => {
          if (!isRecord(item)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
          return {
            id: requiredString(item.id),
            title: requiredString(item.title),
            status: requiredString(item.status),
            priority: requiredString(item.priority),
            due_at: requiredString(item.due_at),
            account_owner: optionalString(item.account_owner),
          }
        })
      : [],
    allowed_statuses: Array.isArray(value.allowed_statuses) ? value.allowed_statuses.filter((item): item is string => typeof item === 'string') : [],
    can_resolve: value.can_resolve === true,
    can_close: value.can_close === true,
    can_reopen: value.can_reopen === true,
  }
}

export type TicketQuery = {
  q?: string
  status?: string
  priority?: string
  category?: string
  accountOwner?: string
  partnerId?: string
  contactId?: string
  orderId?: string
  scope?: string
  sort?: string
  direction?: string
  page?: number
  pageSize?: number
}

export async function fetchTickets(query: TicketQuery = {}): Promise<TicketList> {
  const params = new URLSearchParams()
  if (query.q) params.set('q', query.q)
  if (query.status) params.set('status', query.status)
  if (query.priority) params.set('priority', query.priority)
  if (query.category) params.set('category', query.category)
  if (query.accountOwner) params.set('account_owner', query.accountOwner)
  if (query.partnerId) params.set('partner_id', query.partnerId)
  if (query.contactId) params.set('contact_id', query.contactId)
  if (query.orderId) params.set('order_id', query.orderId)
  if (query.scope) params.set('scope', query.scope)
  if (query.sort) params.set('sort', query.sort)
  if (query.direction) params.set('direction', query.direction)
  if (query.page && query.page > 1) params.set('page', String(query.page))
  if (query.pageSize) params.set('page_size', String(query.pageSize))
  const body = await request(`/api/tickets?${params.toString()}`)
  if (!isRecord(body) || !Array.isArray(body.items)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  return {
    items: body.items.map(readTicket),
    total: requiredNumber(body.total),
    page: requiredNumber(body.page),
    page_size: requiredNumber(body.page_size),
  }
}

export async function fetchTicket(id: string): Promise<TicketDetail> {
  return readDetail(await request(`/api/tickets/${id}`))
}

export async function createTicket(input: TicketInput): Promise<TicketDetail> {
  return readDetail(await request('/api/tickets', { method: 'POST', body: JSON.stringify(ticketPayload(input)) }))
}

export async function updateTicket(id: string, input: TicketInput): Promise<TicketDetail> {
  return readDetail(await request(`/api/tickets/${id}`, { method: 'PUT', body: JSON.stringify(ticketPayload(input)) }))
}

export async function postTicket(id: string, action: string, payload: Record<string, unknown>): Promise<TicketDetail> {
  return readDetail(await request(`/api/tickets/${id}/${action}`, { method: 'POST', body: JSON.stringify(payload) }))
}

export async function createTicketTask(id: string, payload: Record<string, unknown>): Promise<void> {
  await request(`/api/tickets/${id}/tasks`, { method: 'POST', body: JSON.stringify(payload) })
}

export async function uploadAttachment(id: string, file: File): Promise<TicketAttachment> {
  const data = new FormData()
  data.append('file', file)
  let response: Response
  try {
    response = await fetch(`/api/tickets/${id}/attachments`, { method: 'POST', body: data })
  } catch {
    throw new ApiError(0, 'Die Verbindung zur API ist fehlgeschlagen.')
  }
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = isRecord(body) ? body.detail : undefined
    throw new ApiError(response.status, typeof detail === 'string' ? detail : 'Die Datei konnte nicht gespeichert werden.')
  }
  if (!isRecord(body)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  return {
    id: requiredString(body.id),
    original_name: requiredString(body.original_name),
    content_type: requiredString(body.content_type),
    size_bytes: requiredNumber(body.size_bytes),
    created_at: requiredString(body.created_at),
  }
}

export async function deleteAttachment(ticketId: string, attachmentId: string): Promise<void> {
  await request(`/api/tickets/${ticketId}/attachments/${attachmentId}`, { method: 'DELETE' })
}

export async function fetchTicketSummary(): Promise<TicketSummary> {
  const body = await request('/api/tickets/summary')
  if (!isRecord(body)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  return {
    open_count: requiredNumber(body.open_count),
    critical_count: requiredNumber(body.critical_count),
    resolved_count: requiredNumber(body.resolved_count),
    overdue_count: requiredNumber(body.overdue_count),
    open_complaints: requiredNumber(body.open_complaints),
    partners_with_complaints: requiredNumber(body.partners_with_complaints),
    overdue_service_tasks: requiredNumber(body.overdue_service_tasks),
    average_hours: optionalString(body.average_hours),
    duration_sample: requiredNumber(body.duration_sample),
    duration_definition: requiredString(body.duration_definition),
    by_category: countMap(body.by_category),
    by_priority: countMap(body.by_priority),
    by_status: countMap(body.by_status),
  }
}

export async function fetchAnalysis(partnerId: string): Promise<PartnerAnalysis> {
  const body = await request(`/api/partners/${partnerId}/analysis`)
  if (!isRecord(body)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  return {
    partner_id: requiredString(body.partner_id),
    order_count: requiredNumber(body.order_count),
    order_volume: requiredString(body.order_volume),
    average_order_value: optionalString(body.average_order_value),
    last_order_on: optionalString(body.last_order_on),
    open_deals: requiredNumber(body.open_deals),
    pipeline_value: requiredString(body.pipeline_value),
    open_tickets: requiredNumber(body.open_tickets),
    closed_tickets: requiredNumber(body.closed_tickets),
    last_complaint_on: optionalString(body.last_complaint_on),
    last_activity_on: optionalString(body.last_activity_on),
    volume_basis: requiredString(body.volume_basis),
  }
}

function readSegment(value: unknown): Segment {
  if (!isRecord(value) || !Array.isArray(value.conditions)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    id: requiredString(value.id),
    name: requiredString(value.name),
    description: optionalString(value.description),
    match_mode: requiredString(value.match_mode),
    partner_count: requiredNumber(value.partner_count),
    is_demo: value.is_demo === true,
    conditions: value.conditions.map((item) => {
      if (!isRecord(item)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
      return {
        id: requiredString(item.id),
        field_name: requiredString(item.field_name),
        operator: requiredString(item.operator),
        value: typeof item.value === 'string' ? item.value : '',
        position: requiredNumber(item.position),
      }
    }),
    created_at: requiredString(value.created_at),
    updated_at: requiredString(value.updated_at),
  }
}

export async function fetchSegments(): Promise<Segment[]> {
  const body = await request('/api/segments')
  if (!Array.isArray(body)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  return body.map(readSegment)
}

export async function fetchSegment(id: string): Promise<Segment> {
  return readSegment(await request(`/api/segments/${id}`))
}

export async function saveSegment(input: SegmentInput, id?: string): Promise<Segment> {
  const path = id ? `/api/segments/${id}` : '/api/segments'
  return readSegment(await request(path, { method: id ? 'PUT' : 'POST', body: JSON.stringify(segmentPayload(input)) }))
}

export async function deleteSegment(id: string): Promise<void> {
  await request(`/api/segments/${id}`, { method: 'DELETE' })
}

export async function fetchSegmentPartners(id: string): Promise<SegmentPartner[]> {
  const body = await request(`/api/segments/${id}/partners`)
  if (!Array.isArray(body)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  return body.map((item) => {
    if (!isRecord(item)) throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
    return {
      id: requiredString(item.id),
      company_name: requiredString(item.company_name),
      city: typeof item.city === 'string' ? item.city : '',
      partner_type: requiredString(item.partner_type),
      status: requiredString(item.status),
      order_count: requiredNumber(item.order_count),
      order_volume: requiredString(item.order_volume),
      open_tickets: requiredNumber(item.open_tickets),
    }
  })
}
