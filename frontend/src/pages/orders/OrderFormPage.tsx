import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { fetchContacts } from '../../api/crm.ts'
import { fetchPartners } from '../../api/partners.ts'
import { ApiError, createOrder, fetchDeals, fetchOrder, fetchProducts, updateOrder } from '../../api/sales.ts'
import { BoundaryNotice } from '../../components/sales/BoundaryNotice.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import type { Contact } from '../../domain/crm.ts'
import type { Partner } from '../../domain/partners.ts'
import { formatChf, previewLine, sumPreviews, type Deal, type Product } from '../../domain/sales.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

type Line = {
  key: string
  product_id: string
  quantity: string
  unit_price: string
  discount_percent: string
  vat_rate: string
}

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

function blankLine(): Line {
  return { key: crypto.randomUUID(), product_id: '', quantity: '1', unit_price: '', discount_percent: '0', vat_rate: '0' }
}

export function OrderCreatePage() {
  return <OrderForm />
}

export function OrderEditPage() {
  const { orderId = '' } = useParams()
  return <OrderForm orderId={orderId} />
}

function OrderForm({ orderId }: { orderId?: string }) {
  usePageTitle(orderId ? 'Bestellung bearbeiten' : 'Neue Bestellung')
  const navigate = useNavigate()
  const [search] = useSearchParams()
  const [partnerQueryText, setPartnerQueryText] = useState('')
  const [partners, setPartners] = useState<Partner[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])
  const [deals, setDeals] = useState<Deal[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [partnerId, setPartnerId] = useState(search.get('partner') ?? '')
  const [contactId, setContactId] = useState('')
  const [dealId, setDealId] = useState(search.get('deal') ?? '')
  const [orderedOn, setOrderedOn] = useState('')
  const [delivery, setDelivery] = useState('')
  const [notes, setNotes] = useState('')
  const [erp, setErp] = useState('')
  const [lines, setLines] = useState<Line[]>([blankLine()])
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(Boolean(orderId))
  const [locked, setLocked] = useState(false)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    void Promise.all([fetchPartners({ ...partnerQuery, q: partnerQueryText }), fetchProducts({})])
      .then(([partnerList, productList]) => {
        if (!active) return
        setPartners(partnerList.items)
        setProducts(productList.items)
      })
      .catch(() => {
        if (active) setError('Unternehmen oder Produkte konnten nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [partnerQueryText])

  useEffect(() => {
    if (!orderId) return
    let active = true
    void fetchOrder(orderId)
      .then((order) => {
        if (!active) return
        if (order.status !== 'entwurf') {
          setLocked(true)
          setError('Nur Entwürfe können bearbeitet werden.')
        }
        setPartnerId(order.partner_id)
        setPartnerQueryText(order.company_name)
        setContactId(order.contact_id ?? '')
        setDealId(order.deal_id ?? '')
        setOrderedOn(order.ordered_on)
        setDelivery(order.requested_delivery_on ?? '')
        setNotes(order.notes ?? '')
        setErp(order.erp_reference ?? '')
        setLines(
          order.items.map((item) => ({
            key: item.id,
            product_id: item.product_id,
            quantity: item.quantity,
            unit_price: item.unit_price,
            discount_percent: item.discount_percent,
            vat_rate: item.vat_rate,
          })),
        )
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(caught instanceof ApiError ? caught.message : 'Die Bestellung konnte nicht geladen werden.')
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [orderId])

  useEffect(() => {
    if (!partnerId) {
      return
    }
    let active = true
    void Promise.all([
      fetchContacts({ q: '', partnerId, status: '', accountOwner: '', sort: 'name', direction: 'asc', page: 1, includeArchived: false }),
      fetchDeals({ partnerId, includeClosed: true }),
    ])
      .then(([contactList, dealList]) => {
        if (!active) return
        setContacts(contactList.items)
        setDeals(dealList.items)
      })
      .catch(() => {
        if (active) {
          setContacts([])
          setDeals([])
        }
      })
    return () => {
      active = false
    }
  }, [partnerId])

  const previews = lines.map((line) => previewLine(line.quantity, line.unit_price || '0', line.discount_percent || '0', line.vat_rate || '0'))
  const totals = sumPreviews(previews)

  function updateLine(key: string, patch: Partial<Line>) {
    setLines((current) => current.map((line) => (line.key === key ? { ...line, ...patch } : line)))
  }

  async function save(submit: boolean) {
    setSaving(true)
    setError(null)
    try {
      const payload = {
        partner_id: partnerId,
        contact_id: contactId,
        deal_id: dealId,
        ordered_on: orderedOn,
        requested_delivery_on: delivery,
        notes,
        erp_reference: erp,
        submit,
        items: lines.filter((line) => line.product_id).map((line) => ({
          key: line.key,
          product_id: line.product_id,
          quantity: line.quantity,
          unit_price: line.unit_price,
          discount_percent: line.discount_percent,
        })),
      }
      const saved = orderId ? await updateOrder(orderId, payload) : await createOrder(payload)
      void navigate(`/bestellungen/${saved.id}`)
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught.message : 'Die Bestellung konnte nicht gespeichert werden.')
    } finally {
      setSaving(false)
    }
  }

  if (pending) return <LoadingState label="Bestellung wird geladen" />

  return (
    <div className="mx-auto grid max-w-4xl gap-4">
      <h1 className="text-3xl font-semibold tracking-tight">{orderId ? 'Bestellung bearbeiten' : 'Neue Bestellung'}</h1>
      <BoundaryNotice topic="orders" />
      {error ? <ErrorState title="Bestellung" description={error} /> : null}
      <Input label="Unternehmen suchen" value={partnerQueryText} onChange={(event) => setPartnerQueryText(event.target.value)} />
      <Select
        label="Vertriebspartner"
        value={partnerId}
        disabled={locked}
        onChange={(value) => {
          setPartnerId(value)
          setContactId('')
          setDealId('')
        }}
        options={[{ value: '', label: 'Bitte wählen' }, ...partners.map((partner) => ({ value: partner.id, label: partner.company_name }))]}
      />
      <Select
        label="Kontaktperson"
        value={contactId}
        disabled={locked}
        onChange={setContactId}
        options={[{ value: '', label: 'Keine Kontaktperson' }, ...(partnerId ? contacts : []).map((contact) => ({ value: contact.id, label: `${contact.first_name} ${contact.last_name}` }))]}
      />
      <Select
        label="Verkaufschance"
        value={dealId}
        disabled={locked}
        onChange={setDealId}
        options={[{ value: '', label: 'Keine Verknüpfung' }, ...(partnerId ? deals : []).map((deal) => ({ value: deal.id, label: deal.title }))]}
      />
      <div className="grid gap-3 sm:grid-cols-2">
        <Input label="Bestelldatum" type="date" value={orderedOn} disabled={locked} onChange={(event) => setOrderedOn(event.target.value)} />
        <Input label="Gewünschtes Lieferdatum" type="date" value={delivery} disabled={locked} onChange={(event) => setDelivery(event.target.value)} />
      </div>
      <div className="grid gap-3">
        {lines.map((line, index) => (
          <div key={line.key} className="grid gap-3 border border-line p-3 md:grid-cols-4">
            <Select
              label={`Produkt ${index + 1}`}
              value={line.product_id}
              disabled={locked}
              onChange={(value) => {
                const product = products.find((item) => item.id === value)
                updateLine(line.key, {
                  product_id: value,
                  unit_price: product?.list_price ?? '',
                  vat_rate: product?.vat_rate ?? '0',
                })
              }}
              options={[{ value: '', label: 'Bitte wählen' }, ...products.map((product) => ({ value: product.id, label: `${product.name} (${product.sku})` }))]}
            />
            <Input label="Menge" value={line.quantity} disabled={locked} onChange={(event) => updateLine(line.key, { quantity: event.target.value })} />
            <Input label="Einzelpreis CHF" value={line.unit_price} disabled={locked} onChange={(event) => updateLine(line.key, { unit_price: event.target.value })} />
            <Input label="Rabatt %" value={line.discount_percent} disabled={locked} onChange={(event) => updateLine(line.key, { discount_percent: event.target.value })} />
            <p className="text-sm text-muted md:col-span-4">
              Netto {formatChf(previews[index]?.net ?? '0')} · MWST {line.vat_rate} % · {formatChf(previews[index]?.vat ?? '0')} · Zeile {formatChf(previews[index]?.gross ?? '0')}
            </p>
          </div>
        ))}
      </div>
      {!locked ? (
        <Button variant="secondary" onClick={() => setLines((current) => [...current, blankLine()])}>
          Produkt hinzufügen
        </Button>
      ) : null}
      <Textarea label="Interne Bemerkungen" value={notes} disabled={locked} onChange={(event) => setNotes(event.target.value)} />
      <Input label="ERP-Referenz" hint="Für eine spätere Schnittstelle. Bleibt leer, solange nichts übertragen wurde." value={erp} disabled={locked} onChange={(event) => setErp(event.target.value)} />
      <div className="border border-line bg-cream p-4 text-sm leading-6">
        <p>Positionen netto {formatChf(totals.net)}</p>
        <p>Rabatt {formatChf(totals.discount)}</p>
        <p>Mehrwertsteuer {formatChf(totals.vat)}</p>
        <p className="font-semibold">Gesamtbetrag {formatChf(totals.gross)}</p>
        <p className="mt-2 text-muted">Vorschau auf Rappen gerundet. Der gespeicherte Betrag wird vom Server neu berechnet.</p>
      </div>
      {!locked ? (
        <div className="flex flex-wrap gap-2">
          <Button variant="secondary" disabled={saving} onClick={() => void save(false)}>
            Als Entwurf speichern
          </Button>
          <Button disabled={saving} onClick={() => void save(true)}>
            Bestellung einreichen
          </Button>
          <Link to="/bestellungen" className={cx(buttonStyles.base, buttonStyles.ghost)}>
            Abbrechen
          </Link>
        </div>
      ) : (
        <Link to={orderId ? `/bestellungen/${orderId}` : '/bestellungen'} className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Zur Bestellung
        </Link>
      )}
    </div>
  )
}
