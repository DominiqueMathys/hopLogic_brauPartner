export { ApiError } from './partners.ts'
import { ApiError } from './partners.ts'
import {
  activityPayload,
  contactPayload,
  taskPayload,
  type Activity,
  type ActivityInput,
  type ActivityList,
  type Contact,
  type ContactFilters,
  type ContactInput,
  type ContactList,
  type ContactQuery,
  type Task,
  type TaskInput,
  type TaskList,
  type TaskQuery,
  type TaskSummary,
} from '../domain/crm.ts'

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
  if (value == null) {
    return null
  }
  if (typeof value !== 'string') {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return value
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
    const field = [...item.loc].reverse().find((part) => typeof part === 'string' && part !== 'body')
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
  return new ApiError(status, 'Die Anfrage konnte nicht verarbeitet werden.', fieldErrors)
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

function readCompany(value: unknown) {
  if (!isRecord(value)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    partner_id: requiredString(value.partner_id),
    company_name: requiredString(value.company_name),
    city: optionalString(value.city),
    is_primary: value.is_primary === true,
    partner_archived: value.partner_archived === true,
  }
}

export function readContact(value: unknown): Contact {
  if (!isRecord(value) || !Array.isArray(value.companies)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    id: requiredString(value.id),
    first_name: requiredString(value.first_name),
    last_name: requiredString(value.last_name),
    job_title: optionalString(value.job_title),
    email: optionalString(value.email),
    phone: optionalString(value.phone),
    mobile: optionalString(value.mobile),
    account_owner: optionalString(value.account_owner),
    preferred_language: requiredString(value.preferred_language),
    preferred_channel: requiredString(value.preferred_channel),
    lifecycle_phase: requiredString(value.lifecycle_phase),
    lead_status: requiredString(value.lead_status),
    status: requiredString(value.status),
    notes: optionalString(value.notes),
    processing_basis: requiredString(value.processing_basis),
    processing_basis_note: optionalString(value.processing_basis_note),
    is_demo: value.is_demo === true,
    archived_at: optionalString(value.archived_at),
    created_at: requiredString(value.created_at),
    updated_at: requiredString(value.updated_at),
    last_contact_at: optionalString(value.last_contact_at),
    companies: value.companies.map((item) => readCompany(item)),
  }
}

function readActivity(value: unknown): Activity {
  if (!isRecord(value)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    id: requiredString(value.id),
    activity_type: requiredString(value.activity_type),
    title: requiredString(value.title),
    description: optionalString(value.description),
    occurred_at: requiredString(value.occurred_at),
    account_owner: optionalString(value.account_owner),
    contact_id: optionalString(value.contact_id),
    partner_id: optionalString(value.partner_id),
    contact_name: optionalString(value.contact_name),
    company_name: optionalString(value.company_name),
    is_demo: value.is_demo === true,
    archived_at: optionalString(value.archived_at),
    created_at: requiredString(value.created_at),
    updated_at: requiredString(value.updated_at),
  }
}

function readTask(value: unknown): Task {
  if (!isRecord(value)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    id: requiredString(value.id),
    title: requiredString(value.title),
    description: optionalString(value.description),
    account_owner: optionalString(value.account_owner),
    due_at: requiredString(value.due_at),
    priority: requiredString(value.priority),
    status: requiredString(value.status),
    task_type: requiredString(value.task_type),
    partner_id: optionalString(value.partner_id),
    contact_id: optionalString(value.contact_id),
    activity_id: optionalString(value.activity_id),
    company_name: optionalString(value.company_name),
    contact_name: optionalString(value.contact_name),
    completed_at: optionalString(value.completed_at),
    is_demo: value.is_demo === true,
    is_overdue: value.is_overdue === true,
    is_due_soon: value.is_due_soon === true,
    is_urgent: value.is_urgent === true,
    created_at: requiredString(value.created_at),
    updated_at: requiredString(value.updated_at),
  }
}

function readPaged<T>(value: unknown, readItem: (item: unknown) => T): { items: T[]; total: number; page: number; page_size: number } {
  if (!isRecord(value) || !Array.isArray(value.items) || typeof value.total !== 'number') {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    items: value.items.map((item) => readItem(item)),
    total: value.total,
    page: typeof value.page === 'number' ? value.page : 1,
    page_size: typeof value.page_size === 'number' ? value.page_size : 20,
  }
}

export async function fetchContacts(query: ContactQuery): Promise<ContactList> {
  const params = new URLSearchParams()
  if (query.q) params.set('q', query.q)
  if (query.partnerId) params.set('partner_id', query.partnerId)
  if (query.status) params.set('status', query.status)
  if (query.accountOwner) params.set('account_owner', query.accountOwner)
  if (query.sort !== 'name') params.set('sort', query.sort)
  if (query.direction !== 'asc') params.set('direction', query.direction)
  if (query.page > 1) params.set('page', String(query.page))
  params.set('page_size', '20')
  if (query.includeArchived) params.set('include_archived', 'true')
  return readPaged(await request(`/api/contacts?${params.toString()}`), readContact)
}

export async function fetchContactFilters(): Promise<ContactFilters> {
  const body = await request('/api/contacts/filters')
  if (!isRecord(body) || !Array.isArray(body.companies) || !Array.isArray(body.account_owners)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    companies: body.companies.map((item) => {
      const company = readCompany(item)
      return { partner_id: company.partner_id, company_name: company.company_name, city: company.city }
    }),
    accountOwners: body.account_owners.filter((item): item is string => typeof item === 'string'),
  }
}

export async function fetchContact(id: string): Promise<Contact> {
  return readContact(await request(`/api/contacts/${id}`))
}

export async function createContact(input: ContactInput): Promise<Contact> {
  return readContact(await request('/api/contacts', { method: 'POST', body: JSON.stringify(contactPayload(input, true)) }))
}

export async function updateContact(id: string, input: ContactInput): Promise<Contact> {
  return readContact(
    await request(`/api/contacts/${id}`, { method: 'PUT', body: JSON.stringify(contactPayload(input, false)) }),
  )
}

export async function archiveContact(id: string): Promise<Contact> {
  return readContact(await request(`/api/contacts/${id}/archive`, { method: 'POST' }))
}

export async function restoreContact(id: string): Promise<Contact> {
  return readContact(await request(`/api/contacts/${id}/restore`, { method: 'POST' }))
}

export async function linkContactCompany(contactId: string, partnerId: string, isPrimary: boolean): Promise<Contact> {
  return readContact(
    await request(`/api/contacts/${contactId}/companies`, {
      method: 'POST',
      body: JSON.stringify({ partner_id: partnerId, is_primary: isPrimary }),
    }),
  )
}

export async function unlinkContactCompany(contactId: string, partnerId: string): Promise<Contact> {
  return readContact(await request(`/api/contacts/${contactId}/companies/${partnerId}`, { method: 'DELETE' }))
}

export async function makePrimaryContact(contactId: string, partnerId: string): Promise<Contact> {
  return readContact(await request(`/api/contacts/${contactId}/companies/${partnerId}/primary`, { method: 'POST' }))
}

export async function fetchActivities(query: {
  q?: string
  activityType?: string
  partnerId?: string
  contactId?: string
  page?: number
  includeArchived?: boolean
}): Promise<ActivityList> {
  const params = new URLSearchParams()
  if (query.q) params.set('q', query.q)
  if (query.activityType) params.set('activity_type', query.activityType)
  if (query.partnerId) params.set('partner_id', query.partnerId)
  if (query.contactId) params.set('contact_id', query.contactId)
  if (query.page && query.page > 1) params.set('page', String(query.page))
  params.set('page_size', '20')
  if (query.includeArchived) params.set('include_archived', 'true')
  return readPaged(await request(`/api/activities?${params.toString()}`), readActivity)
}

export async function fetchActivity(id: string): Promise<Activity> {
  return readActivity(await request(`/api/activities/${id}`))
}

export async function createActivity(input: ActivityInput): Promise<Activity> {
  return readActivity(await request('/api/activities', { method: 'POST', body: JSON.stringify(activityPayload(input)) }))
}

export async function updateActivity(id: string, input: ActivityInput): Promise<Activity> {
  return readActivity(
    await request(`/api/activities/${id}`, { method: 'PUT', body: JSON.stringify(activityPayload(input)) }),
  )
}

export async function archiveActivity(id: string): Promise<Activity> {
  return readActivity(await request(`/api/activities/${id}/archive`, { method: 'POST' }))
}

export async function restoreActivity(id: string): Promise<Activity> {
  return readActivity(await request(`/api/activities/${id}/restore`, { method: 'POST' }))
}

export async function createNoteWithTask(input: {
  activity: ActivityInput
  createTask: boolean
  taskTitle: string
  taskOwner: string
  taskDue: string
  taskPriority: string
}): Promise<{ activity: Activity; task: Task | null }> {
  const body = await request('/api/activities/note-with-task', {
    method: 'POST',
    body: JSON.stringify({
      activity: activityPayload(input.activity),
      create_task: input.createTask,
      task: input.createTask
        ? {
            title: input.taskTitle,
            account_owner: input.taskOwner.trim() ? input.taskOwner.trim() : null,
            due_at: input.taskDue,
            priority: input.taskPriority,
            task_type: 'anruf',
          }
        : null,
    }),
  })
  if (!isRecord(body)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    activity: readActivity(body.activity),
    task: body.task == null ? null : readTask(body.task),
  }
}

export async function fetchTasks(query: TaskQuery): Promise<TaskList> {
  const params = new URLSearchParams()
  if (query.q) params.set('q', query.q)
  if (query.status) params.set('status', query.status)
  if (query.priority) params.set('priority', query.priority)
  if (query.accountOwner) params.set('account_owner', query.accountOwner)
  if (query.partnerId) params.set('partner_id', query.partnerId)
  if (query.contactId) params.set('contact_id', query.contactId)
  if (query.due) params.set('due', query.due)
  if (query.serviceOnly) params.set('service_only', 'true')
  if (query.page > 1) params.set('page', String(query.page))
  params.set('page_size', '20')
  return readPaged(await request(`/api/tasks?${params.toString()}`), readTask)
}

export async function fetchTaskSummary(): Promise<TaskSummary> {
  const body = await request('/api/tasks/summary')
  if (
    !isRecord(body) ||
    typeof body.open !== 'number' ||
    typeof body.overdue !== 'number' ||
    typeof body.due_soon !== 'number' ||
    typeof body.urgent !== 'number' ||
    typeof body.open_demo !== 'number'
  ) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    open: body.open,
    overdue: body.overdue,
    due_soon: body.due_soon,
    urgent: body.urgent,
    open_demo: body.open_demo,
  }
}

export async function fetchTaskFilters(): Promise<string[]> {
  const body = await request('/api/tasks/filters')
  if (!isRecord(body) || !Array.isArray(body.account_owners)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return body.account_owners.filter((item): item is string => typeof item === 'string')
}

export async function fetchTask(id: string): Promise<Task> {
  return readTask(await request(`/api/tasks/${id}`))
}

export async function createTask(input: TaskInput): Promise<Task> {
  return readTask(await request('/api/tasks', { method: 'POST', body: JSON.stringify(taskPayload(input)) }))
}

export async function updateTask(id: string, input: TaskInput): Promise<Task> {
  return readTask(await request(`/api/tasks/${id}`, { method: 'PUT', body: JSON.stringify(taskPayload(input)) }))
}

export async function completeTask(id: string): Promise<Task> {
  return readTask(await request(`/api/tasks/${id}/complete`, { method: 'POST' }))
}
