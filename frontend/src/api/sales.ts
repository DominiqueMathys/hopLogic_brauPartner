import { ApiError } from './partners.ts'
import type {
  Deal,
  DealDetail,
  DealInput,
  DealList,
  DealSummary,
  Order,
  OrderInput,
  OrderList,
  OrderSummary,
  PipelineBoard,
  Product,
  ProductInput,
  ProductList,
  StageHistory,
} from '../domain/sales.ts'

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

function moneyString(value: unknown): string {
  if (typeof value === 'string') {
    return value
  }
  throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
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
    const detail = isRecord(body) ? body.detail : undefined
    const fieldErrors = fieldErrorsFrom(detail)
    if (typeof detail === 'string') {
      throw new ApiError(response.status, detail, fieldErrors)
    }
    if (Object.keys(fieldErrors).length > 0) {
      throw new ApiError(response.status, 'Bitte prüfen Sie die markierten Felder.', fieldErrors)
    }
    throw new ApiError(response.status, 'Die Anfrage konnte nicht verarbeitet werden.')
  }
  return body
}

function readDeal(value: unknown): Deal {
  if (!isRecord(value)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    id: requiredString(value.id),
    title: requiredString(value.title),
    partner_id: requiredString(value.partner_id),
    contact_id: optionalString(value.contact_id),
    company_name: requiredString(value.company_name),
    contact_name: optionalString(value.contact_name),
    account_owner: optionalString(value.account_owner),
    estimated_value: moneyString(value.estimated_value),
    expected_close_on: optionalString(value.expected_close_on),
    stage: requiredString(value.stage),
    probability: moneyString(value.probability),
    priority: requiredString(value.priority),
    description: optionalString(value.description),
    closed_on: optionalString(value.closed_on),
    loss_reason: optionalString(value.loss_reason),
    is_overdue: value.is_overdue === true,
    is_demo: value.is_demo === true,
    archived_at: optionalString(value.archived_at),
    created_at: requiredString(value.created_at),
    updated_at: requiredString(value.updated_at),
  }
}

function readHistory(value: unknown): StageHistory {
  if (!isRecord(value)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    id: requiredString(value.id),
    from_stage: optionalString(value.from_stage),
    to_stage: requiredString(value.to_stage),
    changed_by: optionalString(value.changed_by),
    changed_at: requiredString(value.changed_at),
  }
}

function readDealDetail(value: unknown): DealDetail {
  const deal = readDeal(value)
  if (!isRecord(value) || !Array.isArray(value.history)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return { ...deal, history: value.history.map((item) => readHistory(item)) }
}

function readPage<T>(value: unknown, readItem: (item: unknown) => T): { items: T[]; total: number; page: number; page_size: number } {
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

export type DealQuery = {
  q?: string
  stage?: string
  accountOwner?: string
  partnerId?: string
  contactId?: string
  closeFrom?: string
  closeTo?: string
  includeClosed?: boolean
  includeArchived?: boolean
  overdueOnly?: boolean
  page?: number
}

function dealParams(query: DealQuery): URLSearchParams {
  const params = new URLSearchParams()
  if (query.q) params.set('q', query.q)
  if (query.stage) params.set('stage', query.stage)
  if (query.accountOwner) params.set('account_owner', query.accountOwner)
  if (query.partnerId) params.set('partner_id', query.partnerId)
  if (query.contactId) params.set('contact_id', query.contactId)
  if (query.closeFrom) params.set('close_from', query.closeFrom)
  if (query.closeTo) params.set('close_to', query.closeTo)
  if (query.includeClosed) params.set('include_closed', 'true')
  if (query.includeArchived) params.set('include_archived', 'true')
  if (query.overdueOnly) params.set('overdue_only', 'true')
  if (query.page && query.page > 1) params.set('page', String(query.page))
  return params
}

export async function fetchDeals(query: DealQuery): Promise<DealList> {
  return readPage(await request(`/api/deals?${dealParams(query).toString()}`), readDeal)
}

export async function fetchDeal(id: string): Promise<DealDetail> {
  return readDealDetail(await request(`/api/deals/${id}`))
}

export async function fetchDealSummary(partnerId?: string): Promise<DealSummary> {
  const params = new URLSearchParams()
  if (partnerId) params.set('partner_id', partnerId)
  const body = await request(`/api/deals/summary?${params.toString()}`)
  if (!isRecord(body) || typeof body.open_count !== 'number') {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    open_count: body.open_count,
    open_demo: typeof body.open_demo === 'number' ? body.open_demo : 0,
    pipeline_value: moneyString(body.pipeline_value),
    won_count: typeof body.won_count === 'number' ? body.won_count : 0,
    won_value: moneyString(body.won_value),
    overdue_count: typeof body.overdue_count === 'number' ? body.overdue_count : 0,
  }
}

export async function fetchPipeline(query: DealQuery): Promise<PipelineBoard> {
  const body = await request(`/api/deals/pipeline?${dealParams(query).toString()}`)
  if (!isRecord(body) || !Array.isArray(body.columns)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    columns: body.columns.map((column) => {
      if (!isRecord(column) || !Array.isArray(column.deals)) {
        throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
      }
      return {
        stage: requiredString(column.stage),
        count: typeof column.count === 'number' ? column.count : 0,
        total_value: moneyString(column.total_value),
        deals: column.deals.map((card) => {
          if (!isRecord(card)) {
            throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
          }
          return {
            id: requiredString(card.id),
            title: requiredString(card.title),
            partner_id: requiredString(card.partner_id),
            company_name: requiredString(card.company_name),
            estimated_value: moneyString(card.estimated_value),
            account_owner: optionalString(card.account_owner),
            expected_close_on: optionalString(card.expected_close_on),
            is_overdue: card.is_overdue === true,
            is_demo: card.is_demo === true,
          }
        }),
      }
    }),
  }
}

function dealPayload(input: DealInput): Record<string, unknown> {
  return {
    title: input.title,
    partner_id: input.partner_id,
    contact_id: input.contact_id || null,
    account_owner: input.account_owner || null,
    estimated_value: input.estimated_value,
    expected_close_on: input.expected_close_on || null,
    stage: input.stage,
    probability: input.probability || null,
    priority: input.priority,
    description: input.description || null,
  }
}

export async function createDeal(input: DealInput): Promise<Deal> {
  return readDeal(await request('/api/deals', { method: 'POST', body: JSON.stringify(dealPayload(input)) }))
}

export async function updateDeal(id: string, input: DealInput): Promise<DealDetail> {
  return readDealDetail(await request(`/api/deals/${id}`, { method: 'PUT', body: JSON.stringify(dealPayload(input)) }))
}

export async function moveDeal(id: string, stage: string): Promise<DealDetail> {
  return readDealDetail(await request(`/api/deals/${id}/stage`, { method: 'POST', body: JSON.stringify({ stage }) }))
}

export async function winDeal(id: string, closedOn: string): Promise<DealDetail> {
  return readDealDetail(
    await request(`/api/deals/${id}/win`, { method: 'POST', body: JSON.stringify({ closed_on: closedOn || null }) }),
  )
}

export async function loseDeal(id: string, lossReason: string, closedOn: string): Promise<DealDetail> {
  return readDealDetail(
    await request(`/api/deals/${id}/lose`, {
      method: 'POST',
      body: JSON.stringify({ loss_reason: lossReason, closed_on: closedOn || null }),
    }),
  )
}

export async function archiveDeal(id: string): Promise<DealDetail> {
  return readDealDetail(await request(`/api/deals/${id}/archive`, { method: 'POST' }))
}

export async function restoreDeal(id: string): Promise<DealDetail> {
  return readDealDetail(await request(`/api/deals/${id}/restore`, { method: 'POST' }))
}

function readProduct(value: unknown): Product {
  if (!isRecord(value)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    id: requiredString(value.id),
    sku: requiredString(value.sku),
    name: requiredString(value.name),
    category: requiredString(value.category),
    description: optionalString(value.description),
    container_type: requiredString(value.container_type),
    container_size: optionalString(value.container_size),
    sales_unit: optionalString(value.sales_unit),
    list_price: moneyString(value.list_price),
    vat_rate: moneyString(value.vat_rate),
    is_active: value.is_active === true,
    is_demo: value.is_demo === true,
    created_at: requiredString(value.created_at),
    updated_at: requiredString(value.updated_at),
  }
}

export async function fetchProducts(query: { q?: string; category?: string; includeInactive?: boolean; page?: number }): Promise<ProductList> {
  const params = new URLSearchParams()
  if (query.q) params.set('q', query.q)
  if (query.category) params.set('category', query.category)
  if (query.includeInactive) params.set('include_inactive', 'true')
  if (query.page && query.page > 1) params.set('page', String(query.page))
  params.set('page_size', '50')
  return readPage(await request(`/api/products?${params.toString()}`), readProduct)
}

export async function fetchProduct(id: string): Promise<Product> {
  return readProduct(await request(`/api/products/${id}`))
}

function productPayload(input: ProductInput): Record<string, unknown> {
  return {
    sku: input.sku,
    name: input.name,
    category: input.category,
    description: input.description || null,
    container_type: input.container_type,
    container_size: input.container_size || null,
    sales_unit: input.sales_unit || null,
    list_price: input.list_price,
    vat_rate: input.vat_rate,
    is_active: input.is_active,
  }
}

export async function createProduct(input: ProductInput): Promise<Product> {
  return readProduct(await request('/api/products', { method: 'POST', body: JSON.stringify(productPayload(input)) }))
}

export async function updateProduct(id: string, input: ProductInput): Promise<Product> {
  return readProduct(await request(`/api/products/${id}`, { method: 'PUT', body: JSON.stringify(productPayload(input)) }))
}

export async function deactivateProduct(id: string): Promise<Product> {
  return readProduct(await request(`/api/products/${id}/deactivate`, { method: 'POST' }))
}

function readOrder(value: unknown): Order {
  if (!isRecord(value) || !Array.isArray(value.items)) {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    id: requiredString(value.id),
    order_number: requiredString(value.order_number),
    partner_id: requiredString(value.partner_id),
    contact_id: optionalString(value.contact_id),
    deal_id: optionalString(value.deal_id),
    company_name: requiredString(value.company_name),
    contact_name: optionalString(value.contact_name),
    ordered_on: requiredString(value.ordered_on),
    requested_delivery_on: optionalString(value.requested_delivery_on),
    status: requiredString(value.status),
    notes: optionalString(value.notes),
    erp_reference: optionalString(value.erp_reference),
    subtotal: moneyString(value.subtotal),
    discount_total: moneyString(value.discount_total),
    net_total: moneyString(value.net_total),
    vat_total: moneyString(value.vat_total),
    gross_total: moneyString(value.gross_total),
    is_demo: value.is_demo === true,
    archived_at: optionalString(value.archived_at),
    created_at: requiredString(value.created_at),
    updated_at: requiredString(value.updated_at),
    allowed_transitions: Array.isArray(value.allowed_transitions)
      ? value.allowed_transitions.filter((item): item is string => typeof item === 'string')
      : [],
    items: value.items.map((item) => {
      if (!isRecord(item)) {
        throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
      }
      return {
        id: requiredString(item.id),
        product_id: requiredString(item.product_id),
        position: typeof item.position === 'number' ? item.position : 0,
        product_name: requiredString(item.product_name),
        sku: requiredString(item.sku),
        quantity: moneyString(item.quantity),
        unit_price: moneyString(item.unit_price),
        discount_percent: moneyString(item.discount_percent),
        discount_amount: moneyString(item.discount_amount),
        vat_rate: moneyString(item.vat_rate),
        line_net: moneyString(item.line_net),
        line_vat: moneyString(item.line_vat),
        line_gross: moneyString(item.line_gross),
      }
    }),
  }
}

export async function fetchOrders(query: {
  q?: string
  status?: string
  partnerId?: string
  contactId?: string
  dealId?: string
  page?: number
}): Promise<OrderList> {
  const params = new URLSearchParams()
  if (query.q) params.set('q', query.q)
  if (query.status) params.set('status', query.status)
  if (query.partnerId) params.set('partner_id', query.partnerId)
  if (query.contactId) params.set('contact_id', query.contactId)
  if (query.dealId) params.set('deal_id', query.dealId)
  if (query.page && query.page > 1) params.set('page', String(query.page))
  const body = await request(`/api/orders?${params.toString()}`)
  return readPage(body, (item) => {
    if (!isRecord(item)) {
      throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
    }
    return {
      id: requiredString(item.id),
      order_number: requiredString(item.order_number),
      partner_id: requiredString(item.partner_id),
      company_name: requiredString(item.company_name),
      ordered_on: requiredString(item.ordered_on),
      status: requiredString(item.status),
      gross_total: moneyString(item.gross_total),
      is_demo: item.is_demo === true,
    }
  })
}

export async function fetchOrder(id: string): Promise<Order> {
  return readOrder(await request(`/api/orders/${id}`))
}

export async function fetchOrderSummary(partnerId?: string): Promise<OrderSummary> {
  const params = new URLSearchParams()
  if (partnerId) params.set('partner_id', partnerId)
  const body = await request(`/api/orders/summary?${params.toString()}`)
  if (!isRecord(body) || typeof body.order_count !== 'number') {
    throw new ApiError(500, 'Die API hat eine unerwartete Antwort geliefert.')
  }
  return {
    volume: moneyString(body.volume),
    volume_demo: moneyString(body.volume_demo),
    new_count: typeof body.new_count === 'number' ? body.new_count : 0,
    order_count: body.order_count,
    last_ordered_on: optionalString(body.last_ordered_on),
  }
}

function orderPayload(input: OrderInput): Record<string, unknown> {
  return {
    partner_id: input.partner_id,
    contact_id: input.contact_id || null,
    deal_id: input.deal_id || null,
    ordered_on: input.ordered_on,
    requested_delivery_on: input.requested_delivery_on || null,
    notes: input.notes || null,
    erp_reference: input.erp_reference || null,
    submit: input.submit,
    items: input.items.map((item) => ({
      product_id: item.product_id,
      quantity: item.quantity,
      unit_price: item.unit_price || null,
      discount_percent: item.discount_percent || '0',
    })),
  }
}

export async function createOrder(input: OrderInput): Promise<Order> {
  return readOrder(await request('/api/orders', { method: 'POST', body: JSON.stringify(orderPayload(input)) }))
}

export async function updateOrder(id: string, input: OrderInput): Promise<Order> {
  return readOrder(await request(`/api/orders/${id}`, { method: 'PUT', body: JSON.stringify(orderPayload(input)) }))
}

export async function changeOrderStatus(id: string, status: string): Promise<Order> {
  return readOrder(await request(`/api/orders/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) }))
}

export { ApiError }
