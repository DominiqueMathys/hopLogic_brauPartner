import type { Choice } from './partners.ts'

export const dealStageOptions: Choice[] = [
  { value: 'neuer_lead', label: 'Neuer Lead' },
  { value: 'erstkontakt', label: 'Erstkontakt' },
  { value: 'bedarf', label: 'Bedarf ermittelt' },
  { value: 'angebot', label: 'Angebot erstellt' },
  { value: 'verhandlung', label: 'Verhandlung' },
  { value: 'gewonnen', label: 'Gewonnen' },
  { value: 'verloren', label: 'Verloren' },
]

export const openDealStageOptions = dealStageOptions.filter((option) => option.value !== 'gewonnen' && option.value !== 'verloren')

export const dealPriorityOptions: Choice[] = [
  { value: 'niedrig', label: 'Niedrig' },
  { value: 'normal', label: 'Normal' },
  { value: 'hoch', label: 'Hoch' },
  { value: 'dringend', label: 'Dringend' },
]

export const productCategoryOptions: Choice[] = [
  { value: 'bier', label: 'Bier' },
  { value: 'alkoholfrei', label: 'Alkoholfreie Getränke' },
  { value: 'mischgetraenke', label: 'Mischgetränke' },
  { value: 'merchandising', label: 'Merchandising' },
  { value: 'festmaterial', label: 'Festmaterial' },
  { value: 'sonstiges', label: 'Sonstiges' },
]

export const containerOptions: Choice[] = [
  { value: 'flasche', label: 'Flasche' },
  { value: 'dose', label: 'Dose' },
  { value: 'fass', label: 'Fass' },
  { value: 'gebinde', label: 'Gebinde' },
  { value: 'sonstiges', label: 'Sonstiges' },
]

export const orderStatusOptions: Choice[] = [
  { value: 'entwurf', label: 'Entwurf' },
  { value: 'eingereicht', label: 'Eingereicht' },
  { value: 'bestaetigt', label: 'Bestätigt' },
  { value: 'in_bearbeitung', label: 'In Bearbeitung' },
  { value: 'versandt', label: 'Versandt' },
  { value: 'geliefert', label: 'Geliefert' },
  { value: 'storniert', label: 'Storniert' },
]

export type Deal = {
  id: string
  title: string
  partner_id: string
  contact_id: string | null
  company_name: string
  contact_name: string | null
  account_owner: string | null
  estimated_value: string
  expected_close_on: string | null
  stage: string
  probability: string
  priority: string
  description: string | null
  closed_on: string | null
  loss_reason: string | null
  is_overdue: boolean
  is_demo: boolean
  archived_at: string | null
  created_at: string
  updated_at: string
}

export type StageHistory = {
  id: string
  from_stage: string | null
  to_stage: string
  changed_by: string | null
  changed_at: string
}

export type DealDetail = Deal & { history: StageHistory[] }

export type DealList = { items: Deal[]; total: number; page: number; page_size: number }

export type PipelineCard = {
  id: string
  title: string
  partner_id: string
  company_name: string
  estimated_value: string
  account_owner: string | null
  expected_close_on: string | null
  is_overdue: boolean
  is_demo: boolean
}

export type PipelineColumn = {
  stage: string
  count: number
  total_value: string
  deals: PipelineCard[]
}

export type PipelineBoard = { columns: PipelineColumn[] }

export type DealSummary = {
  open_count: number
  open_demo: number
  pipeline_value: string
  won_count: number
  won_value: string
  overdue_count: number
}

export type DealInput = {
  title: string
  partner_id: string
  contact_id: string
  account_owner: string
  estimated_value: string
  expected_close_on: string
  stage: string
  probability: string
  priority: string
  description: string
}

export type Product = {
  id: string
  sku: string
  name: string
  category: string
  description: string | null
  container_type: string
  container_size: string | null
  sales_unit: string | null
  list_price: string
  vat_rate: string
  is_active: boolean
  is_demo: boolean
  created_at: string
  updated_at: string
}

export type ProductList = { items: Product[]; total: number; page: number; page_size: number }

export type ProductInput = {
  sku: string
  name: string
  category: string
  description: string
  container_type: string
  container_size: string
  sales_unit: string
  list_price: string
  vat_rate: string
  is_active: boolean
}

export type OrderItem = {
  id: string
  product_id: string
  position: number
  product_name: string
  sku: string
  quantity: string
  unit_price: string
  discount_percent: string
  discount_amount: string
  vat_rate: string
  line_net: string
  line_vat: string
  line_gross: string
}

export type Order = {
  id: string
  order_number: string
  partner_id: string
  contact_id: string | null
  deal_id: string | null
  company_name: string
  contact_name: string | null
  ordered_on: string
  requested_delivery_on: string | null
  status: string
  notes: string | null
  erp_reference: string | null
  subtotal: string
  discount_total: string
  net_total: string
  vat_total: string
  gross_total: string
  is_demo: boolean
  archived_at: string | null
  created_at: string
  updated_at: string
  items: OrderItem[]
  allowed_transitions: string[]
}

export type OrderListItem = {
  id: string
  order_number: string
  partner_id: string
  company_name: string
  ordered_on: string
  status: string
  gross_total: string
  is_demo: boolean
}

export type OrderList = { items: OrderListItem[]; total: number; page: number; page_size: number }

export type OrderSummary = {
  volume: string
  volume_demo: string
  new_count: number
  order_count: number
  last_ordered_on: string | null
}

export type OrderDraftLine = {
  key: string
  product_id: string
  quantity: string
  unit_price: string
  discount_percent: string
}

export type OrderInput = {
  partner_id: string
  contact_id: string
  deal_id: string
  ordered_on: string
  requested_delivery_on: string
  notes: string
  erp_reference: string
  items: OrderDraftLine[]
  submit: boolean
}

export function emptyDealInput(partnerId = ''): DealInput {
  return {
    title: '',
    partner_id: partnerId,
    contact_id: '',
    account_owner: '',
    estimated_value: '',
    expected_close_on: '',
    stage: 'neuer_lead',
    probability: '',
    priority: 'normal',
    description: '',
  }
}

export function dealToForm(deal: Deal): DealInput {
  return {
    title: deal.title,
    partner_id: deal.partner_id,
    contact_id: deal.contact_id ?? '',
    account_owner: deal.account_owner ?? '',
    estimated_value: deal.estimated_value,
    expected_close_on: deal.expected_close_on ?? '',
    stage: deal.stage,
    probability: deal.probability,
    priority: deal.priority,
    description: deal.description ?? '',
  }
}

export function emptyProductInput(): ProductInput {
  return {
    sku: '',
    name: '',
    category: 'bier',
    description: '',
    container_type: 'flasche',
    container_size: '',
    sales_unit: 'Flasche',
    list_price: '',
    vat_rate: '8.10',
    is_active: true,
  }
}

export function productToForm(product: Product): ProductInput {
  return {
    sku: product.sku,
    name: product.name,
    category: product.category,
    description: product.description ?? '',
    container_type: product.container_type,
    container_size: product.container_size ?? '',
    sales_unit: product.sales_unit ?? '',
    list_price: product.list_price,
    vat_rate: product.vat_rate,
    is_active: product.is_active,
  }
}

export function formatChf(value: string | null): string {
  if (!value) {
    return 'CHF 0.00'
  }
  const negative = value.trim().startsWith('-')
  const [wholeRaw, frac = ''] = value.trim().replace('-', '').split('.')
  const whole = wholeRaw.replace(/\B(?=(\d{3})+(?!\d))/g, "'")
  const rappen = `${frac}00`.slice(0, 2)
  return `${negative ? '-' : ''}CHF ${whole}.${rappen}`
}

function scaled(value: string, places: number): bigint {
  const cleaned = value.trim().replace(/'/g, '').replace(',', '.')
  if (!/^\d+(\.\d+)?$/.test(cleaned)) {
    return 0n
  }
  const [whole, frac = ''] = cleaned.split('.')
  const digits = `${frac}${'0'.repeat(places)}`.slice(0, places)
  return BigInt(whole) * 10n ** BigInt(places) + BigInt(digits || '0')
}

function divRound(numerator: bigint, denominator: bigint): bigint {
  return (numerator + denominator / 2n) / denominator
}

function centsToString(cents: bigint): string {
  const whole = cents / 100n
  const frac = (cents % 100n).toString().padStart(2, '0')
  return `${whole}.${frac}`
}

export type LinePreview = {
  discount: string
  net: string
  vat: string
  gross: string
}

export function previewLine(quantity: string, unitPrice: string, discountPercent: string, vatRate: string): LinePreview {
  const qtyMilli = scaled(quantity, 3)
  const priceCents = scaled(unitPrice, 2)
  const discountHundredths = scaled(discountPercent || '0', 2)
  const vatHundredths = scaled(vatRate || '0', 2)
  const base = divRound(qtyMilli * priceCents, 1000n)
  const discount = divRound(base * discountHundredths, 10000n)
  const net = base - discount
  const vat = divRound(net * vatHundredths, 10000n)
  return {
    discount: centsToString(discount),
    net: centsToString(net),
    vat: centsToString(vat),
    gross: centsToString(net + vat),
  }
}

export function addMoney(values: string[]): string {
  const total = values.reduce((sum, value) => sum + scaled(value, 2), 0n)
  return centsToString(total)
}

export function sumPreviews(lines: LinePreview[]): LinePreview {
  const totals = lines.reduce(
    (sum, line) => ({
      discount: sum.discount + scaled(line.discount, 2),
      net: sum.net + scaled(line.net, 2),
      vat: sum.vat + scaled(line.vat, 2),
      gross: sum.gross + scaled(line.gross, 2),
    }),
    { discount: 0n, net: 0n, vat: 0n, gross: 0n },
  )
  return {
    discount: centsToString(totals.discount),
    net: centsToString(totals.net),
    vat: centsToString(totals.vat),
    gross: centsToString(totals.gross),
  }
}
