import { formatChf } from './sales.ts'

export type Festival = {
  id: string
  event_number: string
  name: string
  description: string | null
  event_type: string
  organizer_name: string
  organizer_partner_id: string | null
  distributor_partner_id: string | null
  contact_id: string | null
  contact_name: string | null
  phone: string | null
  email: string | null
  venue_name: string | null
  street: string | null
  postal_code: string | null
  city: string | null
  region: string | null
  country: string
  starts_at: string
  ends_at: string
  expected_visitors: number | null
  notes: string | null
  requirements: string | null
  drinks: string | null
  material_wish: string | null
  delivery_wish_at: string | null
  pickup_wish_at: string | null
  account_owner: string | null
  request_status: string
  event_status: string
  material_status: string
  quote_status: string
  delivery_status: string
  is_binding: boolean
  order_id: string | null
  is_demo: boolean
  archived_at: string | null
  created_at: string
  updated_at: string
}

export type Choice = { value: string; label: string }

export const requestStatusOptions: Choice[] = [
  { value: 'neue_anfrage', label: 'Neue Anfrage' },
  { value: 'in_pruefung', label: 'In Prüfung' },
  { value: 'offerte_vorbereitung', label: 'Offerte in Vorbereitung' },
  { value: 'offerte_versendet', label: 'Offerte versendet' },
  { value: 'bestaetigt', label: 'Bestätigt' },
  { value: 'abgelehnt', label: 'Abgelehnt' },
  { value: 'storniert', label: 'Storniert' },
]

export const eventStatusOptions: Choice[] = [
  { value: 'anfrage', label: 'Anfrage' },
  { value: 'geplant', label: 'Geplant' },
  { value: 'bestaetigt', label: 'Bestätigt' },
  { value: 'laufend', label: 'Laufend' },
  { value: 'abgeschlossen', label: 'Abgeschlossen' },
  { value: 'archiviert', label: 'Archiviert' },
  { value: 'storniert', label: 'Storniert' },
]

export const materialStatusOptions: Choice[] = [
  { value: 'kein_bedarf', label: 'Kein Bedarf' },
  { value: 'ungeprueft', label: 'Ungeprüft' },
  { value: 'verfuegbar', label: 'Verfügbar' },
  { value: 'teilweise', label: 'Teilweise' },
  { value: 'konflikt', label: 'Konflikt' },
  { value: 'reserviert', label: 'Reserviert' },
  { value: 'ausgegeben', label: 'Ausgegeben' },
  { value: 'ruecknahme_offen', label: 'Rücknahme offen' },
  { value: 'abgeschlossen', label: 'Abgeschlossen' },
]

export const quoteStatusOptions: Choice[] = [
  { value: 'keine', label: 'Keine Offerte' },
  { value: 'entwurf', label: 'Entwurf' },
  { value: 'in_pruefung', label: 'In Prüfung' },
  { value: 'versendet', label: 'Versendet' },
  { value: 'angenommen', label: 'Angenommen' },
  { value: 'abgelehnt', label: 'Abgelehnt' },
  { value: 'abgelaufen', label: 'Abgelaufen' },
]

export const deliveryStatusOptions: Choice[] = [
  { value: 'keine', label: 'Kein Transport' },
  { value: 'geplant', label: 'Geplant' },
  { value: 'bereit', label: 'Bereit' },
  { value: 'unterwegs', label: 'Unterwegs' },
  { value: 'geliefert', label: 'Geliefert' },
  { value: 'abholung_geplant', label: 'Abholung geplant' },
  { value: 'abgeholt', label: 'Abgeholt' },
  { value: 'abgeschlossen', label: 'Abgeschlossen' },
]

export const reservationStatusOptions: Choice[] = [
  { value: 'entwurf', label: 'Entwurf' },
  { value: 'angefragt', label: 'Angefragt' },
  { value: 'in_pruefung', label: 'In Prüfung' },
  { value: 'bestaetigt', label: 'Bestätigt' },
  { value: 'teilweise_verfuegbar', label: 'Teilweise verfügbar' },
  { value: 'ausgegeben', label: 'Ausgegeben' },
  { value: 'teilweise_zurueckgegeben', label: 'Teilweise zurückgegeben' },
  { value: 'zurueckgegeben', label: 'Zurückgegeben' },
  { value: 'storniert', label: 'Storniert' },
]

export const eventTypeOptions: Choice[] = [
  { value: 'fest', label: 'Fest' },
  { value: 'firmenanlass', label: 'Firmenanlass' },
  { value: 'vereinsanlass', label: 'Vereinsanlass' },
  { value: 'markt', label: 'Markt' },
  { value: 'sonstige', label: 'Sonstige' },
]

export const assignmentKindOptions: Choice[] = [
  { value: 'materialvorbereitung', label: 'Materialvorbereitung' },
  { value: 'lieferung', label: 'Lieferung' },
  { value: 'aufbau', label: 'Aufbau' },
  { value: 'betreuung', label: 'Betreuung vor Ort' },
  { value: 'abbau', label: 'Abbau' },
  { value: 'ruecktransport', label: 'Rücktransport' },
  { value: 'materialkontrolle', label: 'Materialkontrolle' },
]

export function labelOf(options: Choice[], value: string | null | undefined): string {
  return options.find((option) => option.value === value)?.label ?? value ?? '–'
}

export function statusTone(value: string): 'neutral' | 'success' | 'warning' | 'critical' | 'petrol' {
  if (['bestaetigt', 'angenommen', 'reserviert', 'ausgegeben', 'abgeschlossen', 'geliefert', 'zurueckgegeben', 'verfuegbar'].includes(value)) {
    return 'success'
  }
  if (['konflikt', 'abgelehnt', 'storniert', 'teilweise_verfuegbar', 'ruecknahme_offen'].includes(value)) {
    return 'critical'
  }
  if (['versendet', 'in_pruefung', 'unterwegs', 'angefragt', 'ungeprueft'].includes(value)) {
    return 'warning'
  }
  if (['geplant', 'neue_anfrage', 'anfrage'].includes(value)) {
    return 'petrol'
  }
  return 'neutral'
}

export function formatStamp(value: string | null | undefined): string {
  if (!value) {
    return '–'
  }
  return new Intl.DateTimeFormat('de-CH', {
    timeZone: 'Europe/Zurich',
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function formatDay(value: string | null | undefined): string {
  if (!value) {
    return '–'
  }
  return new Intl.DateTimeFormat('de-CH', { timeZone: 'Europe/Zurich', dateStyle: 'medium' }).format(new Date(value))
}

export function zurichKey(value: string | Date): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Zurich',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  }).formatToParts(value instanceof Date ? value : new Date(value))
  const map: Record<string, string> = {}
  for (const part of parts) {
    map[part.type] = part.value
  }
  return `${map.year}-${map.month}-${map.day}`
}

export function fromZurichInput(value: string): string {
  const local = value.length === 16 ? `${value}:00` : value
  const utcGuess = new Date(`${local}Z`)
  const parts = new Intl.DateTimeFormat('en-US', {
    timeZone: 'Europe/Zurich',
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).formatToParts(utcGuess)
  const map: Record<string, string> = {}
  for (const part of parts) {
    map[part.type] = part.value
  }
  const asZone = Date.UTC(Number(map.year), Number(map.month) - 1, Number(map.day), Number(map.hour), Number(map.minute), Number(map.second))
  return new Date(utcGuess.getTime() - (asZone - utcGuess.getTime())).toISOString()
}

export function toZurichInput(value: string): string {
  const parts = new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Europe/Zurich',
    hourCycle: 'h23',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).formatToParts(new Date(value))
  const map: Record<string, string> = {}
  for (const part of parts) {
    map[part.type] = part.value
  }
  return `${map.year}-${map.month}-${map.day}T${map.hour}:${map.minute}`
}

export function formatAmount(value: string | number | null | undefined): string {
  if (value == null || value === '') {
    return 'CHF 0.00'
  }
  const text = typeof value === 'number' ? value.toFixed(2) : value
  return formatChf(text)
}

export const festivalAreas = [
  { path: '/festmanagement', label: 'Festübersicht' },
  { path: '/festmanagement/kalender', label: 'Festkalender' },
  { path: '/festmanagement/anfragen', label: 'Festanfragen' },
  { path: '/festmanagement/offerten', label: 'Offerten' },
  { path: '/festmanagement/material', label: 'Materialverwaltung' },
  { path: '/festmanagement/reservationen', label: 'Reservationen' },
  { path: '/festmanagement/transporte', label: 'Lieferungen und Rücknahmen' },
  { path: '/festmanagement/einsaetze', label: 'Einsatzplanung' },
  { path: '/festmanagement/auswertungen', label: 'Auswertungen' },
] as const
