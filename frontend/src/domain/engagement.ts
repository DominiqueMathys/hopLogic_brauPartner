import { choiceLabel, type Choice } from './partners.ts'

export const campaignTypeOptions: Choice[] = [
  { value: 'produkteinfuehrung', label: 'Produkteinführung' },
  { value: 'saisonal', label: 'Saisonale Aktion' },
  { value: 'partnerinformation', label: 'Partnerinformation' },
  { value: 'rueckgewinnung', label: 'Kundenrückgewinnung' },
  { value: 'event', label: 'Event / Veranstaltung' },
  { value: 'individuell', label: 'Individuelle Kampagne' },
]

export const campaignStatusOptions: Choice[] = [
  { value: 'entwurf', label: 'Entwurf' },
  { value: 'geplant', label: 'Geplant' },
  { value: 'aktiv', label: 'Aktiv' },
  { value: 'pausiert', label: 'Pausiert' },
  { value: 'abgeschlossen', label: 'Abgeschlossen' },
  { value: 'archiviert', label: 'Archiviert' },
]

export const channelOptions: Choice[] = [
  { value: 'email', label: 'E-Mail' },
  { value: 'telefon', label: 'Telefon' },
  { value: 'besuch', label: 'Persönlicher Besuch' },
  { value: 'brief', label: 'Brief' },
  { value: 'sonstige', label: 'Sonstige' },
]

export const audienceOptions: Choice[] = [
  { value: 'segment', label: 'Bestehendes Kundensegment' },
  { value: 'partners', label: 'Manuell ausgewählte Vertriebspartner' },
  { value: 'contacts', label: 'Manuell ausgewählte Kontaktpersonen' },
]

export const careKindOptions: Choice[] = [
  { value: 'no_contact', label: 'Kein dokumentierter Kontakt' },
  { value: 'no_order', label: 'Keine qualifizierende Bestellung' },
  { value: 'stale_deal', label: 'Offene Verkaufschance ohne Aktivität' },
  { value: 'stale_ticket', label: 'Service-Ticket unbearbeitet' },
]

export const automationStatusOptions: Choice[] = [
  { value: 'entwurf', label: 'Entwurf' },
  { value: 'aktiv', label: 'Aktiv' },
  { value: 'pausiert', label: 'Pausiert' },
  { value: 'deaktiviert', label: 'Deaktiviert' },
]

export const triggerOptions: Choice[] = [
  { value: 'deal_created', label: 'Neue Verkaufschance erstellt' },
  { value: 'deal_stage_changed', label: 'Verkaufsphase geändert' },
  { value: 'partner_created', label: 'Neuer Vertriebspartner erstellt' },
  { value: 'ticket_created', label: 'Neues Service-Ticket erstellt' },
  { value: 'ticket_priority_changed', label: 'Ticketpriorität geändert' },
  { value: 'order_created', label: 'Bestellung im CRM erstellt' },
  { value: 'task_due_soon', label: 'Aufgabe wird bald fällig' },
  { value: 'task_overdue', label: 'Aufgabe ist überfällig' },
  { value: 'no_contact', label: 'Kein Kundenkontakt seit einer Anzahl Tage' },
  { value: 'no_order', label: 'Keine Bestellung seit einer Anzahl Tage' },
  { value: 'ticket_stale', label: 'Service-Ticket seit einer Zeit unbearbeitet' },
  { value: 'festival_request_created', label: 'Neue Festanfrage erfasst' },
  { value: 'festival_quote_accepted', label: 'Festofferte angenommen' },
  { value: 'festival_material_short', label: 'Festmaterial nicht vollständig verfügbar' },
  { value: 'festival_material_damaged', label: 'Festmaterial beschädigt zurückgegeben' },
  { value: 'festival_quote_waiting', label: 'Festofferte seit einer Anzahl Tage unbeantwortet' },
  { value: 'festival_starts_soon', label: 'Fest beginnt in einer Anzahl Tage' },
  { value: 'festival_delivery_due', label: 'Festlieferung in einer Anzahl Tage' },
  { value: 'festival_ended', label: 'Fest beendet, Rücknahme offen' },
  { value: 'festival_return_overdue', label: 'Materialrücknahme überfällig' },
]

export const actionOptions: Choice[] = [
  { value: 'create_task', label: 'Aufgabe erstellen' },
  { value: 'notify_owner', label: 'Zuständige Person benachrichtigen' },
  { value: 'create_reminder', label: 'Interne Erinnerung erzeugen' },
  { value: 'log_activity', label: 'Aktivität im CRM protokollieren' },
]

export const notificationTypeOptions: Choice[] = [
  { value: 'task_assigned', label: 'Neue Aufgabe zugewiesen' },
  { value: 'task_due_soon', label: 'Aufgabe bald fällig' },
  { value: 'task_overdue', label: 'Aufgabe überfällig' },
  { value: 'critical_ticket', label: 'Kritisches Service-Ticket' },
  { value: 'deal_assigned', label: 'Neue zugewiesene Verkaufschance' },
  { value: 'automation_failed', label: 'Automatisierung fehlgeschlagen' },
  { value: 'general', label: 'Allgemeine CRM-Mitteilung' },
]

export const timeTriggers = new Set(['task_due_soon', 'task_overdue', 'no_contact', 'no_order', 'ticket_stale'])

export function labelOf(options: Choice[], value: string): string {
  return choiceLabel(options, value)
}

export type Campaign = {
  id: string
  name: string
  description: string | null
  campaign_type: string
  account_owner: string | null
  starts_on: string | null
  ends_on: string | null
  objective: string | null
  audience_kind: string
  segment_id: string | null
  segment_name: string | null
  channel: string
  budget: string | null
  internal_note: string | null
  status: string
  allowed_statuses: string[]
  activated_at: string | null
  audience_frozen: boolean
  recipient_count: number
  is_demo: boolean
  created_at: string
  updated_at: string
}

export type CampaignInput = {
  name: string
  description: string
  campaign_type: string
  account_owner: string
  starts_on: string
  ends_on: string
  objective: string
  audience_kind: string
  segment_id: string
  channel: string
  budget: string
  internal_note: string
}

export type Recipient = {
  contact_id: string
  partner_id: string | null
  name: string
  company_name: string
  job_title: string
  included: boolean
  exclusion_reason: string | null
}

export type AudienceMember = {
  id: string
  partner_id: string | null
  contact_id: string | null
  label: string
}

export type AudiencePreview = {
  frozen: boolean
  notice: string
  delivery_notice: string
  consent_notice: string
  included_count: number
  excluded_count: number
  included: Recipient[]
  excluded: Recipient[]
  members: AudienceMember[]
}

export type Template = {
  id: string
  name: string
  subject: string
  body: string
  channel: string
  is_demo: boolean
  archived_at: string | null
}

export type Preference = {
  contact_id: string
  preferred_channel: string
  email_marketing_allowed: boolean
  marketing_rejected: boolean
  consent_on: string | null
  consent_source: string | null
  consent_evidence: string | null
  revoked_on: string | null
  notice: string
  stored: boolean
}

export type CareRule = {
  id: string
  name: string
  description: string | null
  rule_kind: string
  threshold_days: number
  is_active: boolean
  create_tasks: boolean
  task_title: string
  account_owner: string | null
  match_count: number
}

export type CareRow = {
  partner_id: string
  company_name: string
  account_owner: string | null
  last_contact_at: string | null
  last_order_on: string | null
  open_tasks: number
  open_tickets: number
  open_deals: number
  next_activity_at: string | null
  contact_gap: boolean
  order_gap: boolean
  has_open_deals: boolean
  has_open_complaints: boolean
}

export type Automation = {
  id: string
  name: string
  description: string | null
  trigger_type: string
  trigger_config: { days?: number; priority?: string }
  action_type: string
  action_config: { title?: string; description?: string; priority?: string; due_days?: number; notification_type?: string }
  status: string
  allowed_statuses: string[]
  account_owner: string | null
  last_run_at: string | null
  run_count: number
  last_error: string | null
  is_demo: boolean
}

export type Execution = {
  id: string
  status: string
  message: string | null
  error: string | null
  started_at: string
  finished_at: string
  task_id: string | null
}

export type Notice = {
  id: string
  notification_type: string
  title: string
  body: string | null
  recipient_label: string
  href: string | null
  read_at: string | null
  created_at: string
}

export type NoticeList = {
  items: Notice[]
  total: number
  unread: number
  identity_limited: boolean
  notice: string
}

export type NoticeSettings = {
  recipient_label: string
  task_reminders: boolean
  service_alerts: boolean
  deal_alerts: boolean
  automation_errors: boolean
  notice: string
}

export type EngagementSummary = {
  active_campaigns: number
  care_tasks: number
  partners_without_contact: number
  contact_days: number
  overdue_tasks: number
  active_automations: number
}

export function emptyCampaign(): CampaignInput {
  return {
    name: '',
    description: '',
    campaign_type: 'saisonal',
    account_owner: '',
    starts_on: '',
    ends_on: '',
    objective: '',
    audience_kind: 'segment',
    segment_id: '',
    channel: 'email',
    budget: '',
    internal_note: '',
  }
}

export function campaignPayload(input: CampaignInput): Record<string, unknown> {
  return {
    name: input.name,
    description: input.description || null,
    campaign_type: input.campaign_type,
    account_owner: input.account_owner || null,
    starts_on: input.starts_on || null,
    ends_on: input.ends_on || null,
    objective: input.objective || null,
    audience_kind: input.audience_kind,
    segment_id: input.audience_kind === 'segment' ? input.segment_id || null : null,
    channel: input.channel,
    budget: input.budget.trim() ? input.budget.trim() : null,
    internal_note: input.internal_note || null,
  }
}
