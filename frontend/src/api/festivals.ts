import { ApiError } from './partners.ts'
import type { Festival } from '../domain/festivals.ts'

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
  if (response.status === 204) {
    return null
  }
  const body = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = body && typeof body === 'object' && 'detail' in body ? (body as { detail: unknown }).detail : null
    const message = typeof detail === 'string' ? detail : 'Die Anfrage konnte nicht verarbeitet werden.'
    throw new ApiError(response.status, message)
  }
  return body
}

export function listFestivals(params: URLSearchParams): Promise<{ items: Festival[]; total: number }> {
  return request(`/api/festivals?${params.toString()}`) as Promise<{ items: Festival[]; total: number }>
}

export function getFestival(id: string): Promise<Record<string, unknown>> {
  return request(`/api/festivals/${id}`) as Promise<Record<string, unknown>>
}

export function createFestival(payload: Record<string, unknown>): Promise<Festival> {
  return request('/api/festivals', { method: 'POST', body: JSON.stringify(payload) }) as Promise<Festival>
}

export function updateFestival(id: string, payload: Record<string, unknown>): Promise<Festival> {
  return request(`/api/festivals/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }) as Promise<Festival>
}

export function postFestivalAction(id: string, action: string): Promise<Festival> {
  return request(`/api/festivals/${id}/${action}`, { method: 'POST' }) as Promise<Festival>
}

export function getDashboard(): Promise<Record<string, unknown>> {
  return request('/api/festivals/dashboard') as Promise<Record<string, unknown>>
}

export function getCalendar(params: URLSearchParams): Promise<{ items: Festival[] }> {
  return request(`/api/festivals/calendar?${params.toString()}`) as Promise<{ items: Festival[] }>
}

export function listMaterials(): Promise<{ items: Array<Record<string, unknown>>; erp_notice: string }> {
  return request('/api/festivals/materials') as Promise<{ items: Array<Record<string, unknown>>; erp_notice: string }>
}

export function createMaterial(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request('/api/festivals/materials', { method: 'POST', body: JSON.stringify(payload) }) as Promise<Record<string, unknown>>
}

export function postStock(id: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/api/festivals/materials/${id}/stock`, { method: 'POST', body: JSON.stringify(payload) }) as Promise<Record<string, unknown>>
}

export function checkAvailability(params: URLSearchParams): Promise<Record<string, unknown>> {
  return request(`/api/festivals/materials/availability?${params.toString()}`) as Promise<Record<string, unknown>>
}

export function listReservations(festivalId?: string): Promise<{ items: Array<Record<string, unknown>> }> {
  const query = festivalId ? `?festival_id=${festivalId}` : ''
  return request(`/api/festivals/reservations${query}`) as Promise<{ items: Array<Record<string, unknown>> }>
}

export function createReservation(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request('/api/festivals/reservations', { method: 'POST', body: JSON.stringify(payload) }) as Promise<Record<string, unknown>>
}

export function reservationAction(id: string, action: string, payload?: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/api/festivals/reservations/${id}/${action}`, {
    method: 'POST',
    body: payload ? JSON.stringify(payload) : JSON.stringify({}),
  }) as Promise<Record<string, unknown>>
}

export function listQuotes(festivalId?: string): Promise<{ items: Array<Record<string, unknown>> }> {
  const query = festivalId ? `?festival_id=${festivalId}` : ''
  return request(`/api/festivals/quotes${query}`) as Promise<{ items: Array<Record<string, unknown>> }>
}

export function createQuote(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request('/api/festivals/quotes', { method: 'POST', body: JSON.stringify(payload) }) as Promise<Record<string, unknown>>
}

export function quoteAction(id: string, action: string, payload?: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/api/festivals/quotes/${id}/${action}`, {
    method: 'POST',
    body: payload ? JSON.stringify(payload) : undefined,
  }) as Promise<Record<string, unknown>>
}

export function listDeliveries(): Promise<{ items: Array<Record<string, unknown>> }> {
  return request('/api/festivals/deliveries') as Promise<{ items: Array<Record<string, unknown>> }>
}

export function createDelivery(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request('/api/festivals/deliveries', { method: 'POST', body: JSON.stringify(payload) }) as Promise<Record<string, unknown>>
}

export function updateDelivery(id: string, payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request(`/api/festivals/deliveries/${id}`, { method: 'PATCH', body: JSON.stringify(payload) }) as Promise<Record<string, unknown>>
}

export function listAssignments(): Promise<{ items: Array<Record<string, unknown>> }> {
  return request('/api/festivals/assignments') as Promise<{ items: Array<Record<string, unknown>> }>
}

export function createAssignment(payload: Record<string, unknown>): Promise<Record<string, unknown>> {
  return request('/api/festivals/assignments', { method: 'POST', body: JSON.stringify(payload) }) as Promise<Record<string, unknown>>
}

export function listMovements(materialId?: string): Promise<{ items: Array<Record<string, unknown>> }> {
  const query = materialId ? `?material_id=${materialId}` : ''
  return request(`/api/festivals/movements${query}`) as Promise<{ items: Array<Record<string, unknown>> }>
}

export function addFestivalNote(id: string, title: string, description: string): Promise<unknown> {
  return request(`/api/festivals/${id}/notes`, {
    method: 'POST',
    body: JSON.stringify({ title, description, activity_type: 'telefonat' }),
  })
}

export async function downloadPdf(path: string, filename: string): Promise<void> {
  const response = await fetch(path)
  if (!response.ok) {
    throw new ApiError(response.status, 'Das Dokument konnte nicht erzeugt werden.')
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
