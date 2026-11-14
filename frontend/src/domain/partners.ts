export type Partner = {
  id: string
  company_name: string
  erp_customer_number: string | null
  erp_customer_status?: string | null
  erp_source?: string | null
  erp_synced_at?: string | null
  partner_type: string
  industry: string | null
  street: string | null
  postal_code: string | null
  city: string | null
  region: string | null
  country: string
  phone: string | null
  email: string | null
  website: string | null
  status: string
  account_owner: string | null
  acquisition_source: string | null
  priority: string
  first_contact_on: string | null
  notes: string | null
  is_demo: boolean
  archived_at: string | null
  created_at: string
  updated_at: string
  last_contact_at: string | null
  next_activity_on: string | null
}

export type PartnerInput = {
  company_name: string
  erp_customer_number: string
  partner_type: string
  industry: string
  street: string
  postal_code: string
  city: string
  region: string
  country: string
  phone: string
  email: string
  website: string
  status: string
  account_owner: string
  acquisition_source: string
  priority: string
  first_contact_on: string
  notes: string
}

export type PartnerList = {
  items: Partner[]
  total: number
  page: number
  page_size: number
}

export type PartnerFilters = {
  industries: string[]
  regions: string[]
  accountOwners: string[]
}

export type PartnerSummary = {
  active: number
  active_demo: number
}

export type PartnerQuery = {
  q: string
  status: string
  industry: string
  region: string
  accountOwner: string
  sort: 'name' | 'created_at' | 'last_activity'
  direction: 'asc' | 'desc'
  page: number
  includeArchived: boolean
}

export type Choice = {
  value: string
  label: string
}

export const partnerTypeOptions: Choice[] = [
  { value: 'restaurant', label: 'Restaurant' },
  { value: 'hotel', label: 'Hotel' },
  { value: 'bar', label: 'Bar' },
  { value: 'getraenkehaendler', label: 'Getränkehändler' },
  { value: 'detailhandel', label: 'Detailhandel' },
  { value: 'veranstalter', label: 'Veranstalter' },
  { value: 'sonstige', label: 'Sonstige' },
]

export const partnerStatusOptions: Choice[] = [
  { value: 'lead', label: 'Lead' },
  { value: 'potenziell', label: 'Potenzieller Partner' },
  { value: 'aktiv', label: 'Aktiver Partner' },
  { value: 'inaktiv', label: 'Inaktiver Partner' },
]

export const priorityOptions: Choice[] = [
  { value: 'niedrig', label: 'Niedrig' },
  { value: 'normal', label: 'Normal' },
  { value: 'hoch', label: 'Hoch' },
]

export const countryOptions: Choice[] = [
  { value: 'Schweiz', label: 'Schweiz' },
  { value: 'Liechtenstein', label: 'Liechtenstein' },
  { value: 'Österreich', label: 'Österreich' },
  { value: 'Deutschland', label: 'Deutschland' },
]

export const acquisitionOptions: Choice[] = [
  { value: '', label: 'Keine Angabe' },
  { value: 'Empfehlung', label: 'Empfehlung' },
  { value: 'Messe', label: 'Messe' },
  { value: 'Website', label: 'Website' },
  { value: 'Direktansprache', label: 'Direktansprache' },
  { value: 'Bestandskunde', label: 'Bestandskunde' },
  { value: 'Sonstige', label: 'Sonstige' },
]

export const emptyPartnerForm: PartnerInput = {
  company_name: '',
  erp_customer_number: '',
  partner_type: '',
  industry: '',
  street: '',
  postal_code: '',
  city: '',
  region: '',
  country: 'Schweiz',
  phone: '',
  email: '',
  website: '',
  status: 'lead',
  account_owner: '',
  acquisition_source: '',
  priority: 'normal',
  first_contact_on: '',
  notes: '',
}

export function choiceLabel(options: readonly Choice[], value: string | null): string {
  if (!value) {
    return 'Keine Angabe'
  }
  return options.find((option) => option.value === value)?.label ?? value
}

export function withCurrent(options: readonly Choice[], current: string): Choice[] {
  if (!current || options.some((option) => option.value === current)) {
    return [...options]
  }
  return [...options, { value: current, label: current }]
}

export function statusTone(status: string): 'accent' | 'warning' | 'success' | 'neutral' {
  if (status === 'lead') {
    return 'accent'
  }
  if (status === 'potenziell') {
    return 'warning'
  }
  if (status === 'aktiv') {
    return 'success'
  }
  return 'neutral'
}

export function formatLocation(partner: Pick<Partner, 'postal_code' | 'city' | 'region' | 'country'>): string {
  const place = [partner.postal_code, partner.city].filter(Boolean).join(' ')
  const parts = [place, partner.region, partner.country].filter(Boolean)
  return parts.join(', ') || 'Kein Standort'
}

export function formatDate(value: string | null): string {
  if (!value) {
    return 'Keine Angabe'
  }
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(value)
  if (!match) {
    return value
  }
  return `${match[3]}.${match[2]}.${match[1]}`
}

export function formatDateTime(value: string | null): string {
  if (!value) {
    return 'Keine Angabe'
  }
  const parsed = new Date(value)
  if (Number.isNaN(parsed.getTime())) {
    return 'Keine Angabe'
  }
  return new Intl.DateTimeFormat('de-CH', { dateStyle: 'medium', timeStyle: 'short' }).format(parsed)
}

export function toForm(partner: Partner): PartnerInput {
  return {
    company_name: partner.company_name,
    erp_customer_number: partner.erp_customer_number ?? '',
    partner_type: partner.partner_type,
    industry: partner.industry ?? '',
    street: partner.street ?? '',
    postal_code: partner.postal_code ?? '',
    city: partner.city ?? '',
    region: partner.region ?? '',
    country: partner.country,
    phone: partner.phone ?? '',
    email: partner.email ?? '',
    website: partner.website ?? '',
    status: partner.status,
    account_owner: partner.account_owner ?? '',
    acquisition_source: partner.acquisition_source ?? '',
    priority: partner.priority,
    first_contact_on: partner.first_contact_on ?? '',
    notes: partner.notes ?? '',
  }
}

function emptyToNull(value: string): string | null {
  const cleaned = value.trim()
  return cleaned ? cleaned : null
}

export function toPayload(input: PartnerInput): Record<string, string | null> {
  return {
    company_name: input.company_name,
    erp_customer_number: emptyToNull(input.erp_customer_number),
    partner_type: input.partner_type,
    industry: emptyToNull(input.industry),
    street: emptyToNull(input.street),
    postal_code: emptyToNull(input.postal_code),
    city: emptyToNull(input.city),
    region: emptyToNull(input.region),
    country: input.country,
    phone: emptyToNull(input.phone),
    email: emptyToNull(input.email),
    website: emptyToNull(input.website),
    status: input.status,
    account_owner: emptyToNull(input.account_owner),
    acquisition_source: emptyToNull(input.acquisition_source),
    priority: input.priority,
    first_contact_on: emptyToNull(input.first_contact_on),
    notes: emptyToNull(input.notes),
  }
}

function todayIso(): string {
  const now = new Date()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${now.getFullYear()}-${month}-${day}`
}

export function validatePartner(input: PartnerInput): Record<string, string> {
  const errors: Record<string, string> = {}
  if (!input.company_name.trim()) {
    errors.company_name = 'Unternehmensname ist erforderlich.'
  } else if (input.company_name.trim().length > 200) {
    errors.company_name = 'Unternehmensname darf höchstens 200 Zeichen haben.'
  }
  if (!input.partner_type) {
    errors.partner_type = 'Partnertyp ist erforderlich.'
  }
  if (!input.status) {
    errors.status = 'Partnerstatus ist erforderlich.'
  }
  if (!input.country.trim()) {
    errors.country = 'Land ist erforderlich.'
  }
  if (input.email.trim() && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(input.email.trim())) {
    errors.email = 'E-Mail ist ungültig.'
  }
  if (input.website.trim() && !/^https?:\/\/[^\s]+$/i.test(input.website.trim())) {
    errors.website = 'Website muss mit http:// oder https:// beginnen.'
  }
  if (input.phone.trim() && !/^[0-9+()\s./-]{6,40}$/.test(input.phone.trim())) {
    errors.phone = 'Telefonnummer ist ungültig.'
  }
  if (input.postal_code.trim() && !/^[A-Za-z0-9][A-Za-z0-9 -]{2,11}$/.test(input.postal_code.trim())) {
    errors.postal_code = 'Postleitzahl ist ungültig.'
  }
  if (input.erp_customer_number.trim() && !/^[A-Za-z0-9][A-Za-z0-9/-]{0,39}$/.test(input.erp_customer_number.trim())) {
    errors.erp_customer_number =
      'Die ERP-Kundennummer darf nur Buchstaben, Ziffern, Bindestriche und Schrägstriche enthalten.'
  }
  if (input.first_contact_on && input.first_contact_on > todayIso()) {
    errors.first_contact_on = 'Das Datum der ersten Kontaktaufnahme darf nicht in der Zukunft liegen.'
  }
  return errors
}
