import { ApiError } from './partners.ts'
import type {
  AudiencePreview,
  Automation,
  Campaign,
  CareRow,
  CareRule,
  EngagementSummary,
  Execution,
  Notice,
  NoticeList,
  NoticeSettings,
  Preference,
  Template,
} from '../domain/engagement.ts'

export { ApiError }

const unexpected = 'Die API hat eine unerwartete Antwort geliefert.'

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function requiredString(value: unknown): string {
  if (typeof value !== 'string' || !value) {
    throw new ApiError(500, unexpected)
  }
  return value
}

function optionalString(value: unknown): string | null {
  if (value == null) {
    return null
  }
  if (typeof value !== 'string') {
    throw new ApiError(500, unexpected)
  }
  return value
}

function requiredNumber(value: unknown): number {
  if (typeof value !== 'number') {
    throw new ApiError(500, unexpected)
  }
  return value
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    throw new ApiError(500, unexpected)
  }
  return value.filter((item): item is string => typeof item === 'string')
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
    return new ApiError(status, 'Der Datensatz wurde nicht gefunden.')
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
  if (response.status === 204) {
    return null
  }
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    throw parseError(response.status, body)
  }
  return body
}

function readCampaign(value: unknown): Campaign {
  if (!isRecord(value)) {
    throw new ApiError(500, unexpected)
  }
  return {
    id: requiredString(value.id),
    name: requiredString(value.name),
    description: optionalString(value.description),
    campaign_type: requiredString(value.campaign_type),
    account_owner: optionalString(value.account_owner),
    starts_on: optionalString(value.starts_on),
    ends_on: optionalString(value.ends_on),
    objective: optionalString(value.objective),
    audience_kind: requiredString(value.audience_kind),
    segment_id: optionalString(value.segment_id),
    segment_name: optionalString(value.segment_name),
    channel: requiredString(value.channel),
    budget: optionalString(value.budget),
    internal_note: optionalString(value.internal_note),
    status: requiredString(value.status),
    allowed_statuses: stringList(value.allowed_statuses),
    activated_at: optionalString(value.activated_at),
    audience_frozen: value.audience_frozen === true,
    recipient_count: requiredNumber(value.recipient_count),
    is_demo: value.is_demo === true,
    created_at: requiredString(value.created_at),
    updated_at: requiredString(value.updated_at),
  }
}

function readRecipient(value: unknown) {
  if (!isRecord(value)) {
    throw new ApiError(500, unexpected)
  }
  return {
    contact_id: requiredString(value.contact_id),
    partner_id: optionalString(value.partner_id),
    name: requiredString(value.name),
    company_name: typeof value.company_name === 'string' ? value.company_name : '',
    job_title: typeof value.job_title === 'string' ? value.job_title : '',
    included: value.included === true,
    exclusion_reason: optionalString(value.exclusion_reason),
  }
}

function readPreview(value: unknown): AudiencePreview {
  if (!isRecord(value) || !Array.isArray(value.included) || !Array.isArray(value.excluded) || !Array.isArray(value.members)) {
    throw new ApiError(500, unexpected)
  }
  return {
    frozen: value.frozen === true,
    notice: typeof value.notice === 'string' ? value.notice : '',
    delivery_notice: typeof value.delivery_notice === 'string' ? value.delivery_notice : '',
    consent_notice: typeof value.consent_notice === 'string' ? value.consent_notice : '',
    included_count: requiredNumber(value.included_count),
    excluded_count: requiredNumber(value.excluded_count),
    included: value.included.map((item) => readRecipient(item)),
    excluded: value.excluded.map((item) => readRecipient(item)),
    members: value.members.map((item) => {
      if (!isRecord(item)) {
        throw new ApiError(500, unexpected)
      }
      return {
        id: requiredString(item.id),
        partner_id: optionalString(item.partner_id),
        contact_id: optionalString(item.contact_id),
        label: requiredString(item.label),
      }
    }),
  }
}

function readTemplate(value: unknown): Template {
  if (!isRecord(value)) {
    throw new ApiError(500, unexpected)
  }
  return {
    id: requiredString(value.id),
    name: requiredString(value.name),
    subject: requiredString(value.subject),
    body: requiredString(value.body),
    channel: requiredString(value.channel),
    is_demo: value.is_demo === true,
    archived_at: optionalString(value.archived_at),
  }
}

function readPreference(value: unknown): Preference {
  if (!isRecord(value)) {
    throw new ApiError(500, unexpected)
  }
  return {
    contact_id: requiredString(value.contact_id),
    preferred_channel: requiredString(value.preferred_channel),
    email_marketing_allowed: value.email_marketing_allowed === true,
    marketing_rejected: value.marketing_rejected === true,
    consent_on: optionalString(value.consent_on),
    consent_source: optionalString(value.consent_source),
    consent_evidence: optionalString(value.consent_evidence),
    revoked_on: optionalString(value.revoked_on),
    notice: typeof value.notice === 'string' ? value.notice : '',
    stored: value.stored === true,
  }
}

function readAutomation(value: unknown): Automation {
  if (!isRecord(value) || !isRecord(value.trigger_config) || !isRecord(value.action_config)) {
    throw new ApiError(500, unexpected)
  }
  return {
    id: requiredString(value.id),
    name: requiredString(value.name),
    description: optionalString(value.description),
    trigger_type: requiredString(value.trigger_type),
    trigger_config: {
      days: typeof value.trigger_config.days === 'number' ? value.trigger_config.days : undefined,
      priority: typeof value.trigger_config.priority === 'string' ? value.trigger_config.priority : undefined,
    },
    action_type: requiredString(value.action_type),
    action_config: {
      title: typeof value.action_config.title === 'string' ? value.action_config.title : undefined,
      description: typeof value.action_config.description === 'string' ? value.action_config.description : undefined,
      priority: typeof value.action_config.priority === 'string' ? value.action_config.priority : undefined,
      due_days: typeof value.action_config.due_days === 'number' ? value.action_config.due_days : undefined,
      notification_type:
        typeof value.action_config.notification_type === 'string' ? value.action_config.notification_type : undefined,
    },
    status: requiredString(value.status),
    allowed_statuses: stringList(value.allowed_statuses),
    account_owner: optionalString(value.account_owner),
    last_run_at: optionalString(value.last_run_at),
    run_count: requiredNumber(value.run_count),
    last_error: optionalString(value.last_error),
    is_demo: value.is_demo === true,
  }
}

function readNotice(value: unknown): Notice {
  if (!isRecord(value)) {
    throw new ApiError(500, unexpected)
  }
  return {
    id: requiredString(value.id),
    notification_type: requiredString(value.notification_type),
    title: requiredString(value.title),
    body: optionalString(value.body),
    recipient_label: requiredString(value.recipient_label),
    href: optionalString(value.href),
    read_at: optionalString(value.read_at),
    created_at: requiredString(value.created_at),
  }
}

export function errorMessage(caught: unknown): string {
  return caught instanceof ApiError ? caught.message : 'Die Anfrage ist fehlgeschlagen.'
}

export async function fetchCampaigns(query: { q?: string; status?: string; campaignType?: string }): Promise<Campaign[]> {
  const params = new URLSearchParams()
  if (query.q) params.set('q', query.q)
  if (query.status) params.set('status', query.status)
  if (query.campaignType) params.set('campaign_type', query.campaignType)
  params.set('page_size', '100')
  const body = await request(`/api/campaigns?${params.toString()}`)
  if (!isRecord(body) || !Array.isArray(body.items)) {
    throw new ApiError(500, unexpected)
  }
  return body.items.map((item) => readCampaign(item))
}

export async function fetchCampaign(id: string): Promise<Campaign> {
  return readCampaign(await request(`/api/campaigns/${id}`))
}

export async function saveCampaign(id: string | null, payload: Record<string, unknown>): Promise<Campaign> {
  const body = await request(id ? `/api/campaigns/${id}` : '/api/campaigns', {
    method: id ? 'PUT' : 'POST',
    body: JSON.stringify(payload),
  })
  return readCampaign(body)
}

export async function changeCampaignStatus(id: string, status: string): Promise<Campaign> {
  return readCampaign(await request(`/api/campaigns/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) }))
}

export async function duplicateCampaign(id: string): Promise<Campaign> {
  return readCampaign(await request(`/api/campaigns/${id}/duplicate`, { method: 'POST' }))
}

export async function fetchAudience(id: string): Promise<AudiencePreview> {
  return readPreview(await request(`/api/campaigns/${id}/audience`))
}

export async function addAudienceMember(id: string, target: { partner_id?: string; contact_id?: string }): Promise<void> {
  await request(`/api/campaigns/${id}/audience`, { method: 'POST', body: JSON.stringify(target) })
}

export async function removeAudienceMember(id: string, memberId: string): Promise<void> {
  await request(`/api/campaigns/${id}/audience/${memberId}`, { method: 'DELETE' })
}

export async function requestCampaignSend(id: string): Promise<void> {
  await request(`/api/campaigns/${id}/send`, { method: 'POST' })
}

export async function fetchTemplates(includeArchived = false): Promise<Template[]> {
  const body = await request(`/api/templates?include_archived=${includeArchived ? 'true' : 'false'}`)
  if (!Array.isArray(body)) {
    throw new ApiError(500, unexpected)
  }
  return body.map((item) => readTemplate(item))
}

export async function fetchTemplate(id: string): Promise<Template> {
  return readTemplate(await request(`/api/templates/${id}`))
}

export async function saveTemplate(id: string | null, payload: Record<string, unknown>): Promise<Template> {
  const body = await request(id ? `/api/templates/${id}` : '/api/templates', {
    method: id ? 'PUT' : 'POST',
    body: JSON.stringify(payload),
  })
  return readTemplate(body)
}

export async function archiveTemplate(id: string): Promise<Template> {
  return readTemplate(await request(`/api/templates/${id}/archive`, { method: 'POST' }))
}

export async function duplicateTemplate(id: string): Promise<Template> {
  return readTemplate(await request(`/api/templates/${id}/duplicate`, { method: 'POST' }))
}

export async function previewTemplate(id: string, payload: Record<string, unknown>): Promise<{ subject: string; body: string; delivery_notice: string }> {
  const body = await request(`/api/templates/${id}/preview`, { method: 'POST', body: JSON.stringify(payload) })
  if (!isRecord(body) || typeof body.subject !== 'string' || typeof body.body !== 'string') {
    throw new ApiError(500, unexpected)
  }
  return {
    subject: body.subject,
    body: body.body,
    delivery_notice: typeof body.delivery_notice === 'string' ? body.delivery_notice : '',
  }
}

export async function fetchPreference(contactId: string): Promise<Preference> {
  return readPreference(await request(`/api/contacts/${contactId}/preferences`))
}

export async function savePreference(contactId: string, payload: Record<string, unknown>): Promise<Preference> {
  return readPreference(await request(`/api/contacts/${contactId}/preferences`, { method: 'PUT', body: JSON.stringify(payload) }))
}

export async function fetchSuppressed(): Promise<Preference[]> {
  const body = await request('/api/preferences/suppressed')
  if (!Array.isArray(body)) {
    throw new ApiError(500, unexpected)
  }
  return body.map((item) => readPreference(item))
}

export async function fetchCareRules(): Promise<CareRule[]> {
  const body = await request('/api/care/rules')
  if (!Array.isArray(body)) {
    throw new ApiError(500, unexpected)
  }
  return body.map((item) => {
    if (!isRecord(item)) {
      throw new ApiError(500, unexpected)
    }
    return {
      id: requiredString(item.id),
      name: requiredString(item.name),
      description: optionalString(item.description),
      rule_kind: requiredString(item.rule_kind),
      threshold_days: requiredNumber(item.threshold_days),
      is_active: item.is_active === true,
      create_tasks: item.create_tasks === true,
      task_title: requiredString(item.task_title),
      account_owner: optionalString(item.account_owner),
      match_count: requiredNumber(item.match_count),
    }
  })
}

export async function saveCareRule(id: string | null, payload: Record<string, unknown>): Promise<void> {
  await request(id ? `/api/care/rules/${id}` : '/api/care/rules', {
    method: id ? 'PUT' : 'POST',
    body: JSON.stringify(payload),
  })
}

export async function deleteCareRule(id: string): Promise<void> {
  await request(`/api/care/rules/${id}`, { method: 'DELETE' })
}

export async function fetchCareOverview(signal: string): Promise<{ items: CareRow[]; contactDays: number; orderDays: number }> {
  const params = new URLSearchParams({ page_size: '100' })
  if (signal) params.set('signal', signal)
  const body = await request(`/api/care/overview?${params.toString()}`)
  if (!isRecord(body) || !Array.isArray(body.items)) {
    throw new ApiError(500, unexpected)
  }
  return {
    contactDays: requiredNumber(body.contact_days),
    orderDays: requiredNumber(body.order_days),
    items: body.items.map((item) => {
      if (!isRecord(item)) {
        throw new ApiError(500, unexpected)
      }
      return {
        partner_id: requiredString(item.partner_id),
        company_name: requiredString(item.company_name),
        account_owner: optionalString(item.account_owner),
        last_contact_at: optionalString(item.last_contact_at),
        last_order_on: optionalString(item.last_order_on),
        open_tasks: requiredNumber(item.open_tasks),
        open_tickets: requiredNumber(item.open_tickets),
        open_deals: requiredNumber(item.open_deals),
        next_activity_at: optionalString(item.next_activity_at),
        contact_gap: item.contact_gap === true,
        order_gap: item.order_gap === true,
        has_open_deals: item.has_open_deals === true,
        has_open_complaints: item.has_open_complaints === true,
      }
    }),
  }
}

export async function createCareTask(payload: Record<string, unknown>): Promise<void> {
  await request('/api/care/tasks', { method: 'POST', body: JSON.stringify(payload) })
}

export async function fetchAutomations(): Promise<Automation[]> {
  const body = await request('/api/automations')
  if (!Array.isArray(body)) {
    throw new ApiError(500, unexpected)
  }
  return body.map((item) => readAutomation(item))
}

export async function fetchAutomation(id: string): Promise<Automation> {
  return readAutomation(await request(`/api/automations/${id}`))
}

export async function saveAutomation(id: string | null, payload: Record<string, unknown>): Promise<Automation> {
  const body = await request(id ? `/api/automations/${id}` : '/api/automations', {
    method: id ? 'PUT' : 'POST',
    body: JSON.stringify(payload),
  })
  return readAutomation(body)
}

export async function changeAutomationStatus(id: string, status: string): Promise<Automation> {
  return readAutomation(await request(`/api/automations/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) }))
}

export async function fetchExecutions(id: string): Promise<Execution[]> {
  const body = await request(`/api/automations/${id}/executions`)
  if (!Array.isArray(body)) {
    throw new ApiError(500, unexpected)
  }
  return body.map((item) => {
    if (!isRecord(item)) {
      throw new ApiError(500, unexpected)
    }
    return {
      id: requiredString(item.id),
      status: requiredString(item.status),
      message: optionalString(item.message),
      error: optionalString(item.error),
      started_at: requiredString(item.started_at),
      finished_at: requiredString(item.finished_at),
      task_id: optionalString(item.task_id),
    }
  })
}

export async function runDueAutomations(): Promise<number> {
  const body = await request('/api/automations/run-due', { method: 'POST' })
  if (!isRecord(body) || typeof body.attempts !== 'number') {
    throw new ApiError(500, unexpected)
  }
  return body.attempts
}

export async function fetchNotices(query: { recipient: string; type?: string; unread?: boolean }): Promise<NoticeList> {
  const params = new URLSearchParams({ page_size: '50' })
  if (query.recipient) params.set('empfaenger', query.recipient)
  if (query.type) params.set('notification_type', query.type)
  if (query.unread) params.set('unread', 'true')
  const body = await request(`/api/notifications?${params.toString()}`)
  if (!isRecord(body) || !Array.isArray(body.items)) {
    throw new ApiError(500, unexpected)
  }
  return {
    items: body.items.map((item) => readNotice(item)),
    total: requiredNumber(body.total),
    unread: requiredNumber(body.unread),
    identity_limited: body.identity_limited === true,
    notice: typeof body.notice === 'string' ? body.notice : '',
  }
}

export async function fetchNoticeSummary(recipient: string): Promise<{ unread: number; identity_limited: boolean; notice: string }> {
  const params = new URLSearchParams()
  if (recipient) params.set('empfaenger', recipient)
  const body = await request(`/api/notifications/summary?${params.toString()}`)
  if (!isRecord(body) || typeof body.unread !== 'number') {
    throw new ApiError(500, unexpected)
  }
  return {
    unread: body.unread,
    identity_limited: body.identity_limited === true,
    notice: typeof body.notice === 'string' ? body.notice : '',
  }
}

export async function markNoticeRead(id: string, recipient: string): Promise<Notice> {
  const params = new URLSearchParams({ empfaenger: recipient })
  return readNotice(await request(`/api/notifications/${id}/read?${params.toString()}`, { method: 'POST' }))
}

export async function markAllNoticesRead(recipient: string): Promise<void> {
  const params = new URLSearchParams({ empfaenger: recipient })
  await request(`/api/notifications/read-all?${params.toString()}`, { method: 'POST' })
}

export async function fetchNoticeSettings(recipient: string): Promise<NoticeSettings> {
  const params = new URLSearchParams({ empfaenger: recipient })
  const body = await request(`/api/notifications/settings?${params.toString()}`)
  if (!isRecord(body)) {
    throw new ApiError(500, unexpected)
  }
  return {
    recipient_label: requiredString(body.recipient_label),
    task_reminders: body.task_reminders === true,
    service_alerts: body.service_alerts === true,
    deal_alerts: body.deal_alerts === true,
    automation_errors: body.automation_errors === true,
    notice: typeof body.notice === 'string' ? body.notice : '',
  }
}

export async function saveNoticeSettings(payload: NoticeSettings): Promise<NoticeSettings> {
  const body = await request('/api/notifications/settings', {
    method: 'PUT',
    body: JSON.stringify({
      recipient_label: payload.recipient_label,
      task_reminders: payload.task_reminders,
      service_alerts: payload.service_alerts,
      deal_alerts: payload.deal_alerts,
      automation_errors: payload.automation_errors,
    }),
  })
  if (!isRecord(body)) {
    throw new ApiError(500, unexpected)
  }
  return {
    recipient_label: requiredString(body.recipient_label),
    task_reminders: body.task_reminders === true,
    service_alerts: body.service_alerts === true,
    deal_alerts: body.deal_alerts === true,
    automation_errors: body.automation_errors === true,
    notice: typeof body.notice === 'string' ? body.notice : '',
  }
}

export async function fetchEngagementSummary(): Promise<EngagementSummary> {
  const body = await request('/api/engagement/summary')
  if (!isRecord(body)) {
    throw new ApiError(500, unexpected)
  }
  return {
    active_campaigns: requiredNumber(body.active_campaigns),
    care_tasks: requiredNumber(body.care_tasks),
    partners_without_contact: requiredNumber(body.partners_without_contact),
    contact_days: requiredNumber(body.contact_days),
    overdue_tasks: requiredNumber(body.overdue_tasks),
    active_automations: requiredNumber(body.active_automations),
  }
}
