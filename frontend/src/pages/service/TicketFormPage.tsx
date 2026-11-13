import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { fetchContacts } from '../../api/crm.ts'
import { fetchPartners } from '../../api/partners.ts'
import { fetchOrders, fetchProducts } from '../../api/sales.ts'
import { ApiError, createTicket, fetchTicket, updateTicket, uploadAttachment } from '../../api/service.ts'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import type { Contact } from '../../domain/crm.ts'
import type { Partner } from '../../domain/partners.ts'
import type { OrderListItem, Product } from '../../domain/sales.ts'
import { emptyTicket, ticketCategoryOptions, ticketPriorityOptions, type TicketInput } from '../../domain/service.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

export function TicketCreatePage() {
  const [params] = useSearchParams()
  return <TicketForm initialPartner={params.get('partner') ?? ''} initialOrder={params.get('order') ?? ''} />
}

export function TicketEditPage() {
  const { ticketId = '' } = useParams()
  return <TicketForm ticketId={ticketId} />
}

function TicketForm({ ticketId, initialPartner = '', initialOrder = '' }: { ticketId?: string; initialPartner?: string; initialOrder?: string }) {
  const navigate = useNavigate()
  const editing = Boolean(ticketId)
  usePageTitle(editing ? 'Ticket bearbeiten' : 'Neues Ticket')
  const [input, setInput] = useState<TicketInput>(() => emptyTicket(initialPartner))
  const [partners, setPartners] = useState<Partner[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])
  const [orders, setOrders] = useState<OrderListItem[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState<string | null>(null)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [pending, setPending] = useState(editing)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    let active = true
    void Promise.all([
      fetchPartners({ q: '', status: '', industry: '', region: '', accountOwner: '', sort: 'name', direction: 'asc', page: 1, includeArchived: false }),
      fetchProducts({}),
      ticketId ? fetchTicket(ticketId) : Promise.resolve(null),
    ])
      .then(([partnerList, productList, ticket]) => {
        if (!active) return
        setPartners(partnerList.items)
        setProducts(productList.items)
        if (ticket) {
          setInput({
            subject: ticket.subject,
            category: ticket.category,
            description: ticket.description,
            partner_id: ticket.partner_id,
            priority: ticket.priority,
            contact_id: ticket.contact_id ?? '',
            order_id: ticket.order_id ?? '',
            product_ids: ticket.products.map((product) => product.id),
            account_owner: ticket.account_owner ?? '',
            due_on: ticket.due_on ?? '',
            internal_remark: ticket.internal_remark ?? '',
          })
        } else if (initialOrder) {
          setInput((current) => ({ ...current, order_id: initialOrder }))
        }
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(caught instanceof ApiError ? caught.message : 'Das Formular konnte nicht geladen werden.')
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [ticketId, initialOrder])

  useEffect(() => {
    if (!input.partner_id) return
    let active = true
    void Promise.all([
      fetchContacts({ q: '', partnerId: input.partner_id, status: '', accountOwner: '', sort: 'name', direction: 'asc', page: 1, includeArchived: false }),
      fetchOrders({ partnerId: input.partner_id }),
    ])
      .then(([contactList, orderList]) => {
        if (!active) return
        setContacts(contactList.items)
        setOrders(orderList.items)
      })
      .catch(() => {
        if (!active) return
        setContacts([])
        setOrders([])
      })
    return () => {
      active = false
    }
  }, [input.partner_id])

  function update(changes: Partial<TicketInput>) {
    setInput((current) => ({ ...current, ...changes }))
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    setFieldErrors({})
    try {
      const saved = editing && ticketId ? await updateTicket(ticketId, input) : await createTicket(input)
      for (const file of files) {
        await uploadAttachment(saved.id, file)
      }
      navigate(`/kundenservice/${saved.id}`)
    } catch (caught) {
      if (caught instanceof ApiError) {
        setError(caught.message)
        setFieldErrors(caught.fieldErrors)
      } else {
        setError('Die Verbindung zur API ist fehlgeschlagen.')
      }
      setSaving(false)
    }
  }

  if (pending) return <LoadingState label="Ticketformular wird geladen" />

  const contactOptions = input.partner_id ? contacts : []
  const orderOptions = input.partner_id ? orders : []

  return (
    <form className="mx-auto grid max-w-3xl gap-4" onSubmit={(event) => void onSubmit(event)}>
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">{editing ? 'Ticket bearbeiten' : 'Neues Ticket erstellen'}</h1>
        <p className="mt-2 text-sm leading-6 text-muted">Pflicht sind Betreff, Kategorie, Beschreibung, Vertriebspartner und Priorität.</p>
      </header>
      {error ? <ErrorState title="Ticket nicht gespeichert" description={error} /> : null}
      <Input label="Betreff" value={input.subject} error={fieldErrors.subject} onChange={(event) => update({ subject: event.target.value })} required />
      <Select label="Kategorie" value={input.category} error={fieldErrors.category} onChange={(value) => update({ category: value })} options={ticketCategoryOptions} />
      <Textarea label="Beschreibung" value={input.description} error={fieldErrors.description} onChange={(event) => update({ description: event.target.value })} required />
      <Select
        label="Vertriebspartner"
        value={input.partner_id}
        error={fieldErrors.partner_id}
        onChange={(value) => update({ partner_id: value, contact_id: '', order_id: '' })}
        options={[{ value: '', label: 'Unternehmen wählen' }, ...partners.map((partner) => ({ value: partner.id, label: partner.company_name }))]}
      />
      <Select label="Priorität" value={input.priority} onChange={(value) => update({ priority: value })} options={ticketPriorityOptions} />
      <Select
        label="Kontaktperson"
        value={input.contact_id}
        onChange={(value) => update({ contact_id: value })}
        options={[{ value: '', label: 'Keine Kontaktperson' }, ...contactOptions.map((contact) => ({ value: contact.id, label: `${contact.first_name} ${contact.last_name}` }))]}
      />
      <Select
        label="Zugeordnete Bestellung"
        value={input.order_id}
        onChange={(value) => update({ order_id: value })}
        options={[{ value: '', label: 'Keine Bestellung' }, ...orderOptions.map((order) => ({ value: order.id, label: `${order.order_number} · ${order.company_name}` }))]}
      />
      <fieldset className="grid gap-2">
        <legend className="text-sm font-semibold">Betroffene Produkte</legend>
        {products.map((product) => (
          <label key={product.id} className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={input.product_ids.includes(product.id)}
              onChange={(event) =>
                update({
                  product_ids: event.target.checked
                    ? [...input.product_ids, product.id]
                    : input.product_ids.filter((id) => id !== product.id),
                })
              }
            />
            {product.name}
          </label>
        ))}
      </fieldset>
      <Input label="Zuständige Mitarbeiter:in" value={input.account_owner} onChange={(event) => update({ account_owner: event.target.value })} />
      <Input label="Gewünschtes Erledigungsdatum" type="date" value={input.due_on} onChange={(event) => update({ due_on: event.target.value })} />
      <Textarea label="Interne Bemerkungen" hint="Diese Bemerkung bleibt am Ticket. Zusätzliche Notizen im Verlauf sind ebenfalls intern und keine Kundennachrichten." value={input.internal_remark} onChange={(event) => update({ internal_remark: event.target.value })} />
      {editing ? (
        <p className="text-sm leading-6 text-muted">Anhänge werden auf der Ticketdetailseite hinzugefügt oder entfernt.</p>
      ) : (
        <Input
          label="Anhänge"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
          multiple
          hint="PDF, JPG oder PNG. Höchstens 5 MB pro Datei. Ohne Anmeldung ist der Upload nicht für einen öffentlichen Produktivbetrieb geeignet. Dateien liegen unter data/ticket-attachments und sind nicht öffentlich."
          onChange={(event) => setFiles(Array.from(event.target.files ?? []))}
        />
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={saving}>
          {saving ? 'Wird gespeichert' : 'Ticket speichern'}
        </Button>
        <Link to={ticketId ? `/kundenservice/${ticketId}` : '/kundenservice'} className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Abbrechen
        </Link>
      </div>
    </form>
  )
}
