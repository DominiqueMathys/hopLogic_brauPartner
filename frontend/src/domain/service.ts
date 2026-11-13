export type Choice = { value: string; label: string }

export const ticketCategoryOptions: Choice[] = [
  { value: 'beschaedigte_lieferung', label: 'Beschädigte Lieferung' },
  { value: 'fehlende_lieferung', label: 'Fehlende Lieferung' },
  { value: 'falsche_lieferung', label: 'Falsche Lieferung' },
  { value: 'produktqualitaet', label: 'Produktqualität' },
  { value: 'rechnung', label: 'Rechnung / Zahlung' },
  { value: 'anfrage', label: 'Allgemeine Anfrage' },
  { value: 'technisch', label: 'Technisches Problem' },
  { value: 'sonstiges', label: 'Sonstiges' },
]

export const complaintCategories = new Set([
  'beschaedigte_lieferung',
  'fehlende_lieferung',
  'falsche_lieferung',
  'produktqualitaet',
])

export const ticketPriorityOptions: Choice[] = [
  { value: 'niedrig', label: 'Niedrig' },
  { value: 'normal', label: 'Normal' },
  { value: 'hoch', label: 'Hoch' },
  { value: 'kritisch', label: 'Kritisch' },
]

export const ticketStatusOptions: Choice[] = [
  { value: 'neu', label: 'Neu' },
  { value: 'offen', label: 'Offen' },
  { value: 'in_bearbeitung', label: 'In Bearbeitung' },
  { value: 'warten_kunde', label: 'Warten auf Kund:in' },
  { value: 'warten_intern', label: 'Warten auf interne Rückmeldung' },
  { value: 'geloest', label: 'Gelöst' },
  { value: 'geschlossen', label: 'Geschlossen' },
]

export const resolutionOptions: Choice[] = [
  { value: 'ersatzlieferung', label: 'Ersatzlieferung veranlassen' },
  { value: 'gutschrift', label: 'Gutschrift prüfen' },
  { value: 'vertrieb', label: 'Rücksprache mit Vertrieb' },
  { value: 'logistik', label: 'Rücksprache mit Logistik' },
  { value: 'keine_massnahme', label: 'Keine weitere Massnahme erforderlich' },
  { value: 'sonstige', label: 'Sonstige Lösung' },
]

export const eventLabels: Record<string, string> = {
  created: 'Ticket erstellt',
  status_changed: 'Status geändert',
  priority_changed: 'Priorität geändert',
  owner_changed: 'Zuständigkeit geändert',
  note_added: 'Interne Notiz',
  task_created: 'Aufgabe erstellt',
  resolved: 'Ticket gelöst',
  closed: 'Ticket geschlossen',
  reopened: 'Ticket wieder geöffnet',
}

export const segmentFieldOptions: Choice[] = [
  { value: 'partner_type', label: 'Partnertyp' },
  { value: 'industry', label: 'Branche' },
  { value: 'region', label: 'Region' },
  { value: 'status', label: 'Partnerstatus' },
  { value: 'order_count', label: 'Bestellhäufigkeit' },
  { value: 'order_volume', label: 'Bestellvolumen CHF' },
  { value: 'last_order_on', label: 'Letzte Bestellung' },
  { value: 'open_deals', label: 'Offene Verkaufschancen' },
  { value: 'open_tickets', label: 'Anzahl Service-Tickets' },
  { value: 'last_activity_on', label: 'Letzte Kontaktaktivität' },
]

export const operatorOptions: Record<string, Choice[]> = {
  partner_type: [{ value: 'eq', label: 'ist' }],
  industry: [{ value: 'eq', label: 'ist' }],
  region: [{ value: 'eq', label: 'ist' }],
  status: [{ value: 'eq', label: 'ist' }],
  order_count: [
    { value: 'eq', label: 'gleich' },
    { value: 'gte', label: 'mindestens' },
    { value: 'lte', label: 'höchstens' },
  ],
  order_volume: [
    { value: 'gte', label: 'mindestens' },
    { value: 'lte', label: 'höchstens' },
  ],
  last_order_on: [
    { value: 'before', label: 'vor' },
    { value: 'after', label: 'nach' },
    { value: 'empty', label: 'keine Bestellung' },
  ],
  open_deals: [
    { value: 'eq', label: 'gleich' },
    { value: 'gte', label: 'mindestens' },
    { value: 'lte', label: 'höchstens' },
  ],
  open_tickets: [
    { value: 'eq', label: 'gleich' },
    { value: 'gte', label: 'mindestens' },
    { value: 'lte', label: 'höchstens' },
  ],
  last_activity_on: [
    { value: 'before', label: 'vor' },
    { value: 'after', label: 'nach' },
    { value: 'empty', label: 'keine Aktivität' },
  ],
}

export type Ticket = {
  id: string
  ticket_number: string
  subject: string
  category: string
  priority: string
  status: string
  partner_id: string
  company_name: string
  contact_id: string | null
  contact_name: string | null
  account_owner: string | null
  due_on: string | null
  is_overdue: boolean
  is_demo: boolean
  created_at: string
  updated_at: string
}

export type TicketEvent = {
  id: string
  event_type: string
  from_value: string | null
  to_value: string | null
  note: string | null
  changed_by: string | null
  task_id: string | null
  changed_at: string
}

export type TicketAttachment = {
  id: string
  original_name: string
  content_type: string
  size_bytes: number
  created_at: string
}

export type TicketResolution = {
  id: string
  code: string
  note: string | null
  recorded_by: string | null
  recorded_at: string
}

export type TicketProduct = { id: string; name: string; sku: string }

export type TicketTask = {
  id: string
  title: string
  status: string
  priority: string
  due_at: string
  account_owner: string | null
}

export type TicketDetail = Ticket & {
  description: string
  order_id: string | null
  order_number: string | null
  internal_remark: string | null
  resolved_at: string | null
  closed_at: string | null
  products: TicketProduct[]
  events: TicketEvent[]
  attachments: TicketAttachment[]
  resolutions: TicketResolution[]
  tasks: TicketTask[]
  allowed_statuses: string[]
  can_resolve: boolean
  can_close: boolean
  can_reopen: boolean
}

export type TicketList = { items: Ticket[]; total: number; page: number; page_size: number }

export type TicketInput = {
  subject: string
  category: string
  description: string
  partner_id: string
  priority: string
  contact_id: string
  order_id: string
  product_ids: string[]
  account_owner: string
  due_on: string
  internal_remark: string
}

export type TicketSummary = {
  open_count: number
  critical_count: number
  resolved_count: number
  overdue_count: number
  open_complaints: number
  partners_with_complaints: number
  overdue_service_tasks: number
  average_hours: string | null
  duration_sample: number
  duration_definition: string
  by_category: Record<string, number>
  by_priority: Record<string, number>
  by_status: Record<string, number>
}

export type PartnerAnalysis = {
  partner_id: string
  order_count: number
  order_volume: string
  average_order_value: string | null
  last_order_on: string | null
  open_deals: number
  pipeline_value: string
  open_tickets: number
  closed_tickets: number
  last_complaint_on: string | null
  last_activity_on: string | null
  volume_basis: string
}

export type SegmentCondition = {
  id: string
  field_name: string
  operator: string
  value: string
  position: number
}

export type Segment = {
  id: string
  name: string
  description: string | null
  match_mode: string
  partner_count: number
  is_demo: boolean
  conditions: SegmentCondition[]
  created_at: string
  updated_at: string
}

export type SegmentPartner = {
  id: string
  company_name: string
  city: string
  partner_type: string
  status: string
  order_count: number
  order_volume: string
  open_tickets: number
}

export type ConditionInput = { field_name: string; operator: string; value: string }

export type SegmentInput = {
  name: string
  description: string
  match_mode: string
  conditions: ConditionInput[]
}

export const emptyTicket = (partnerId = ''): TicketInput => ({
  subject: '',
  category: 'beschaedigte_lieferung',
  description: '',
  partner_id: partnerId,
  priority: 'normal',
  contact_id: '',
  order_id: '',
  product_ids: [],
  account_owner: '',
  due_on: '',
  internal_remark: '',
})

export const emptyCondition = (): ConditionInput => ({ field_name: 'partner_type', operator: 'eq', value: '' })

export function ticketPayload(input: TicketInput): Record<string, unknown> {
  return {
    subject: input.subject,
    category: input.category,
    description: input.description,
    partner_id: input.partner_id,
    priority: input.priority,
    contact_id: input.contact_id || null,
    order_id: input.order_id || null,
    product_ids: input.product_ids,
    account_owner: input.account_owner || null,
    due_on: input.due_on || null,
    internal_remark: input.internal_remark || null,
  }
}

export function segmentPayload(input: SegmentInput): Record<string, unknown> {
  return {
    name: input.name,
    description: input.description || null,
    match_mode: input.match_mode,
    conditions: input.conditions.map((condition) => ({
      field_name: condition.field_name,
      operator: condition.operator,
      value: condition.operator === 'empty' ? '' : condition.value,
    })),
  }
}
