import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { fetchContacts } from '../../api/crm.ts'
import { fetchPartners } from '../../api/partners.ts'
import { ApiError, createDeal, fetchDeal, updateDeal } from '../../api/sales.ts'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import type { Contact } from '../../domain/crm.ts'
import type { Partner } from '../../domain/partners.ts'
import { dealPriorityOptions, dealStageOptions, dealToForm, emptyDealInput, openDealStageOptions, type DealInput } from '../../domain/sales.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const partnerQuery = {
  q: '',
  status: '',
  industry: '',
  region: '',
  accountOwner: '',
  sort: 'name' as const,
  direction: 'asc' as const,
  page: 1,
  includeArchived: false,
}

export function DealCreatePage() {
  const params = new URLSearchParams(window.location.search)
  return <DealForm initialPartnerId={params.get('partner') ?? ''} />
}

export function DealEditPage() {
  const { dealId = '' } = useParams()
  return <DealForm dealId={dealId} />
}

function DealForm({ dealId, initialPartnerId = '' }: { dealId?: string; initialPartnerId?: string }) {
  usePageTitle(dealId ? 'Verkaufschance bearbeiten' : 'Neue Verkaufschance')
  const navigate = useNavigate()
  const [form, setForm] = useState<DealInput>(emptyDealInput(initialPartnerId))
  const [partners, setPartners] = useState<Partner[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])
  const [partnerQueryText, setPartnerQueryText] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [pending, setPending] = useState(Boolean(dealId))
  const [saving, setSaving] = useState(false)
  const closed = form.stage === 'gewonnen' || form.stage === 'verloren'

  useEffect(() => {
    let active = true
    void fetchPartners({ ...partnerQuery, q: partnerQueryText })
      .then((list) => {
        if (active) setPartners(list.items)
      })
      .catch(() => {
        if (active) setError('Die Unternehmen konnten nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [partnerQueryText])

  useEffect(() => {
    if (!dealId) return
    let active = true
    void fetchDeal(dealId)
      .then((deal) => {
        if (!active) return
        setForm(dealToForm(deal))
        setPartnerQueryText(deal.company_name)
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(caught instanceof ApiError ? caught.message : 'Die Verkaufschance konnte nicht geladen werden.')
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [dealId])

  useEffect(() => {
    if (!form.partner_id) {
      return
    }
    let active = true
    void fetchContacts({
      q: '',
      partnerId: form.partner_id,
      status: '',
      accountOwner: '',
      sort: 'name',
      direction: 'asc',
      page: 1,
      includeArchived: false,
    })
      .then((list) => {
        if (active) setContacts(list.items)
      })
      .catch(() => {
        if (active) setContacts([])
      })
    return () => {
      active = false
    }
  }, [form.partner_id])

  function setField(field: keyof DealInput, value: string) {
    setForm((current) => ({ ...current, [field]: value }))
  }

  async function save() {
    setSaving(true)
    setError(null)
    setFieldErrors({})
    try {
      const saved = dealId ? await updateDeal(dealId, form) : await createDeal(form)
      void navigate(`/verkaufschancen/${saved.id}`)
    } catch (caught: unknown) {
      if (caught instanceof ApiError) {
        setError(caught.message)
        setFieldErrors(caught.fieldErrors)
      } else {
        setError('Die Verkaufschance konnte nicht gespeichert werden.')
      }
    } finally {
      setSaving(false)
    }
  }

  if (pending) return <LoadingState label="Verkaufschance wird geladen" />

  const stageOptions = closed ? dealStageOptions : openDealStageOptions

  return (
    <div className="mx-auto grid max-w-3xl gap-4">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">{dealId ? 'Verkaufschance bearbeiten' : 'Neue Verkaufschance'}</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Eine leere Wahrscheinlichkeit übernimmt den Wert der Verkaufsphase. Gewinnen und Verlieren erfolgen auf der Detailseite.
        </p>
      </header>
      {error ? <ErrorState title="Speichern nicht möglich" description={error} /> : null}
      <Input label="Unternehmen suchen" value={partnerQueryText} onChange={(event) => setPartnerQueryText(event.target.value)} />
      <Select
        label="Unternehmen"
        value={form.partner_id}
        error={fieldErrors.partner_id}
        onChange={(value) => setForm((current) => ({ ...current, partner_id: value, contact_id: '' }))}
        options={[{ value: '', label: 'Bitte wählen' }, ...partners.map((partner) => ({ value: partner.id, label: partner.company_name }))]}
      />
      <Select
        label="Kontaktperson"
        value={form.contact_id}
        error={fieldErrors.contact_id}
        onChange={(value) => setField('contact_id', value)}
        options={[
          { value: '', label: 'Keine Kontaktperson' },
          ...(form.partner_id ? contacts : []).map((contact) => ({ value: contact.id, label: `${contact.first_name} ${contact.last_name}` })),
        ]}
      />
      <Input label="Deal-Titel" value={form.title} error={fieldErrors.title} onChange={(event) => setField('title', event.target.value)} />
      <Input label="Zuständige Person" value={form.account_owner} onChange={(event) => setField('account_owner', event.target.value)} />
      <div className="grid gap-3 sm:grid-cols-2">
        <Input label="Geschätzter Wert in CHF" value={form.estimated_value} error={fieldErrors.estimated_value} onChange={(event) => setField('estimated_value', event.target.value)} />
        <Input label="Erwartetes Abschlussdatum" type="date" value={form.expected_close_on} onChange={(event) => setField('expected_close_on', event.target.value)} />
        <Select label="Verkaufsphase" value={form.stage} onChange={(value) => setField('stage', value)} options={stageOptions} disabled={closed} />
        <Input
          label="Wahrscheinlichkeit in Prozent"
          value={form.probability}
          hint="Leer lassen, um den Phasenwert zu verwenden."
          onChange={(event) => setField('probability', event.target.value)}
        />
        <Select label="Priorität" value={form.priority} onChange={(value) => setField('priority', value)} options={dealPriorityOptions} />
      </div>
      <Textarea label="Beschreibung" value={form.description} onChange={(event) => setField('description', event.target.value)} />
      <div className="flex flex-wrap gap-2">
        <Button disabled={saving} onClick={() => void save()}>
          Speichern
        </Button>
        <Link to={dealId ? `/verkaufschancen/${dealId}` : '/verkaufschancen'} className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Abbrechen
        </Link>
      </div>
    </div>
  )
}
