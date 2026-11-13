import { choiceLabel, type Choice } from './partners.ts'

export type CompanyLink = {
  partner_id: string
  company_name: string
  city: string | null
  is_primary: boolean
  partner_archived: boolean
}

export type Contact = {
  id: string
  first_name: string
  last_name: string
  job_title: string | null
  email: string | null
  phone: string | null
  mobile: string | null
  account_owner: string | null
  preferred_language: string
  preferred_channel: string
  lifecycle_phase: string
  lead_status: string
  status: string
  notes: string | null
  processing_basis: string
  processing_basis_note: string | null
  is_demo: boolean
  archived_at: string | null
  created_at: string
  updated_at: string
  last_contact_at: string | null
  companies: CompanyLink[]
}

export type ContactInput = {
  first_name: string
  last_name: string
  job_title: string
  email: string
  phone: string
  mobile: string
  account_owner: string
  preferred_language: string
  preferred_channel: string
  lifecycle_phase: string
  lead_status: string
  status: string
  notes: string
  processing_basis: string
  processing_basis_note: string
  partner_id: string
  is_primary: boolean
}

export type ContactList = {
  items: Contact[]
  total: number
  page: number
  page_size: number
}

export type ContactFilters = {
  companies: { partner_id: string; company_name: string; city: string | null }[]
  accountOwners: string[]
}

export type ContactQuery = {
  q: string
  partnerId: string
  status: string
  accountOwner: string
  sort: 'name' | 'last_contact'
  direction: 'asc' | 'desc'
  page: number
  includeArchived: boolean
}

export type Activity = {
  id: string
  activity_type: string
  title: string
  description: string | null
  occurred_at: string
  account_owner: string | null
  contact_id: string | null
  partner_id: string | null
  contact_name: string | null
  company_name: string | null
  is_demo: boolean
  archived_at: string | null
  created_at: string
  updated_at: string
}

export type ActivityInput = {
  activity_type: string
  title: string
  description: string
  occurred_at: string
  account_owner: string
  contact_id: string
  partner_id: string
}

export type ActivityList = {
  items: Activity[]
  total: number
  page: number
  page_size: number
}

export type Task = {
  id: string
  title: string
  description: string | null
  account_owner: string | null
  due_at: string
  priority: string
  status: string
  task_type: string
  partner_id: string | null
  contact_id: string | null
  activity_id: string | null
  company_name: string | null
  contact_name: string | null
  completed_at: string | null
  is_demo: boolean
  is_overdue: boolean
  is_due_soon: boolean
  is_urgent: boolean
  created_at: string
  updated_at: string
}

export type TaskInput = {
  title: string
  description: string
  account_owner: string
  due_at: string
  priority: string
  status: string
  task_type: string
  partner_id: string
  contact_id: string
  activity_id: string
}

export type TaskList = {
  items: Task[]
  total: number
  page: number
  page_size: number
}

export type TaskSummary = {
  open: number
  overdue: number
  due_soon: number
  urgent: number
  open_demo: number
}

export type TaskQuery = {
  q: string
  status: string
  priority: string
  accountOwner: string
  partnerId: string
  contactId: string
  due: string
  serviceOnly: boolean
  page: number
}

export const contactStatusOptions: Choice[] = [
  { value: 'aktiv', label: 'Aktiv' },
  { value: 'inaktiv', label: 'Inaktiv' },
]

export const leadStatusOptions: Choice[] = [
  { value: 'keiner', label: 'Kein aktiver Lead' },
  { value: 'offen', label: 'Offener Lead' },
  { value: 'abgeschlossen', label: 'Abgeschlossener Lead' },
]

export const lifecycleOptions: Choice[] = [
  { value: 'lead', label: 'Lead' },
  { value: 'interessent', label: 'Interessent:in' },
  { value: 'qualifiziert', label: 'Qualifizierte:r Interessent:in' },
  { value: 'kunde', label: 'Kund:in' },
  { value: 'ehemalig', label: 'Ehemalige:r Kund:in' },
]

export const languageOptions: Choice[] = [
  { value: 'de', label: 'Deutsch' },
  { value: 'fr', label: 'Französisch' },
  { value: 'it', label: 'Italienisch' },
]

export const channelOptions: Choice[] = [
  { value: 'telefon', label: 'Telefon' },
  { value: 'email', label: 'E-Mail' },
  { value: 'mobil', label: 'Mobil' },
  { value: 'persoenlich', label: 'Persönlich' },
]

export const processingBasisOptions: Choice[] = [
  { value: 'nicht_dokumentiert', label: 'Nicht dokumentiert' },
  { value: 'vertrag', label: 'Vertrag' },
  { value: 'berechtigte_interessen', label: 'Berechtigte Interessen' },
  { value: 'einwilligung', label: 'Einwilligung' },
  { value: 'gesetzliche_pflicht', label: 'Gesetzliche Pflicht' },
]

export const activityTypeOptions: Choice[] = [
  { value: 'telefonat', label: 'Telefonat' },
  { value: 'email', label: 'E-Mail' },
  { value: 'besuch', label: 'Persönlicher Besuch' },
  { value: 'meeting', label: 'Meeting' },
  { value: 'gespraechsnotiz', label: 'Gesprächsnotiz' },
  { value: 'sonstige', label: 'Sonstige Interaktion' },
]

export const taskStatusOptions: Choice[] = [
  { value: 'offen', label: 'Offen' },
  { value: 'in_bearbeitung', label: 'In Bearbeitung' },
  { value: 'erledigt', label: 'Erledigt' },
  { value: 'abgebrochen', label: 'Abgebrochen' },
]

export const taskPriorityOptions: Choice[] = [
  { value: 'niedrig', label: 'Niedrig' },
  { value: 'normal', label: 'Normal' },
  { value: 'hoch', label: 'Hoch' },
  { value: 'dringend', label: 'Dringend' },
]

export const taskTypeOptions: Choice[] = [
  { value: 'anruf', label: 'Anruf' },
  { value: 'email', label: 'E-Mail' },
  { value: 'besuch', label: 'Besuch' },
  { value: 'intern', label: 'Intern' },
  { value: 'sonstige', label: 'Sonstige' },
]

export const emptyContactForm: ContactInput = {
  first_name: '',
  last_name: '',
  job_title: '',
  email: '',
  phone: '',
  mobile: '',
  account_owner: '',
  preferred_language: 'de',
  preferred_channel: 'telefon',
  lifecycle_phase: '',
  lead_status: 'keiner',
  status: 'aktiv',
  notes: '',
  processing_basis: 'nicht_dokumentiert',
  processing_basis_note: '',
  partner_id: '',
  is_primary: true,
}

export const emptyActivityForm: ActivityInput = {
  activity_type: 'gespraechsnotiz',
  title: '',
  description: '',
  occurred_at: '',
  account_owner: '',
  contact_id: '',
  partner_id: '',
}

export const emptyTaskForm: TaskInput = {
  title: '',
  description: '',
  account_owner: '',
  due_at: '',
  priority: 'normal',
  status: 'offen',
  task_type: 'intern',
  partner_id: '',
  contact_id: '',
  activity_id: '',
}

export function contactName(contact: { first_name: string; last_name: string }): string {
  return `${contact.first_name} ${contact.last_name}`
}

export function labelOf(options: readonly Choice[], value: string | null): string {
  return choiceLabel(options, value)
}

function blank(value: string): string | null {
  const cleaned = value.trim()
  return cleaned ? cleaned : null
}

export function contactToForm(contact: Contact): ContactInput {
  return {
    first_name: contact.first_name,
    last_name: contact.last_name,
    job_title: contact.job_title ?? '',
    email: contact.email ?? '',
    phone: contact.phone ?? '',
    mobile: contact.mobile ?? '',
    account_owner: contact.account_owner ?? '',
    preferred_language: contact.preferred_language,
    preferred_channel: contact.preferred_channel,
    lifecycle_phase: contact.lifecycle_phase,
    lead_status: contact.lead_status,
    status: contact.status,
    notes: contact.notes ?? '',
    processing_basis: contact.processing_basis,
    processing_basis_note: contact.processing_basis_note ?? '',
    partner_id: '',
    is_primary: false,
  }
}

export function contactPayload(input: ContactInput, includeCompany: boolean): Record<string, unknown> {
  return {
    first_name: input.first_name,
    last_name: input.last_name,
    job_title: blank(input.job_title),
    email: blank(input.email),
    phone: blank(input.phone),
    mobile: blank(input.mobile),
    account_owner: blank(input.account_owner),
    preferred_language: input.preferred_language,
    preferred_channel: input.preferred_channel,
    lifecycle_phase: input.lifecycle_phase,
    lead_status: input.lead_status,
    status: input.status,
    notes: blank(input.notes),
    processing_basis: input.processing_basis,
    processing_basis_note: blank(input.processing_basis_note),
    companies:
      includeCompany && input.partner_id
        ? [{ partner_id: input.partner_id, is_primary: input.is_primary }]
        : [],
  }
}

export function activityPayload(input: ActivityInput): Record<string, unknown> {
  return {
    activity_type: input.activity_type,
    title: input.title,
    description: blank(input.description),
    occurred_at: input.occurred_at,
    account_owner: blank(input.account_owner),
    contact_id: blank(input.contact_id),
    partner_id: blank(input.partner_id),
  }
}

export function taskPayload(input: TaskInput): Record<string, unknown> {
  return {
    title: input.title,
    description: blank(input.description),
    account_owner: blank(input.account_owner),
    due_at: input.due_at,
    priority: input.priority,
    status: input.status,
    task_type: input.task_type,
    partner_id: blank(input.partner_id),
    contact_id: blank(input.contact_id),
    activity_id: blank(input.activity_id),
  }
}

export function activityToForm(activity: Activity): ActivityInput {
  return {
    activity_type: activity.activity_type,
    title: activity.title,
    description: activity.description ?? '',
    occurred_at: activity.occurred_at,
    account_owner: activity.account_owner ?? '',
    contact_id: activity.contact_id ?? '',
    partner_id: activity.partner_id ?? '',
  }
}

export function taskToForm(task: Task): TaskInput {
  return {
    title: task.title,
    description: task.description ?? '',
    account_owner: task.account_owner ?? '',
    due_at: task.due_at,
    priority: task.priority,
    status: task.status,
    task_type: task.task_type,
    partner_id: task.partner_id ?? '',
    contact_id: task.contact_id ?? '',
    activity_id: task.activity_id ?? '',
  }
}

const emailPattern = /^[^@\s]+@[^@\s]+\.[^@\s]+$/
const phonePattern = /^[0-9+()\s./-]{6,40}$/

export function validateContact(input: ContactInput): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!input.first_name.trim()) {
    errors.first_name = 'Vorname ist erforderlich.'
  }
  if (!input.last_name.trim()) {
    errors.last_name = 'Nachname ist erforderlich.'
  }
  if (!input.lifecycle_phase) {
    errors.lifecycle_phase = 'Lifecycle-Phase ist erforderlich.'
  }
  if (input.email.trim() && !emailPattern.test(input.email.trim())) {
    errors.email = 'E-Mail ist ungültig.'
  }
  if (input.phone.trim() && !phonePattern.test(input.phone.trim())) {
    errors.phone = 'Telefonnummer ist ungültig.'
  }
  if (input.mobile.trim() && !phonePattern.test(input.mobile.trim())) {
    errors.mobile = 'Mobilnummer ist ungültig.'
  }
  return errors
}

export function validateActivity(input: ActivityInput): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!input.activity_type) {
    errors.activity_type = 'Aktivitätstyp ist erforderlich.'
  }
  if (!input.title.trim()) {
    errors.title = 'Titel ist erforderlich.'
  }
  if (!input.occurred_at) {
    errors.occurred_at = 'Datum und Uhrzeit sind erforderlich.'
  }
  if (!input.contact_id && !input.partner_id) {
    errors.partner_id = 'Die Aktivität braucht einen Kontakt oder ein Unternehmen.'
  }
  return errors
}

export function validateTask(input: TaskInput): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!input.title.trim()) {
    errors.title = 'Titel ist erforderlich.'
  }
  if (!input.due_at) {
    errors.due_at = 'Fälligkeit ist erforderlich.'
  }
  if (!input.status) {
    errors.status = 'Aufgabenstatus ist erforderlich.'
  }
  return errors
}

export function toDateTimeLocal(value: string): string {
  if (!value) {
    return ''
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return ''
  }
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${parsed.getFullYear()}-${pad(parsed.getMonth() + 1)}-${pad(parsed.getDate())}T${pad(parsed.getHours())}:${pad(parsed.getMinutes())}`
}

export function fromDateTimeLocal(value: string): string {
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return ''
  }
  return parsed.toISOString()
}
