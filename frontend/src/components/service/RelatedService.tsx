import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, fetchAnalysis, fetchTickets } from '../../api/service.ts'
import { buttonStyles } from '../ui/button-styles.ts'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { LoadingState } from '../ui/LoadingState.tsx'
import { choiceLabel, formatDate, formatDateTime } from '../../domain/partners.ts'
import { formatChf } from '../../domain/sales.ts'
import { complaintCategories, ticketStatusOptions, type PartnerAnalysis, type Ticket } from '../../domain/service.ts'
import { cx } from '../../lib/cx.ts'

function useTickets(partnerId?: string, contactId?: string, orderId?: string) {
  const [items, setItems] = useState<Ticket[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void fetchTickets({ partnerId, contactId, orderId, pageSize: 50 })
      .then((result) => {
        if (active) setItems(result.items)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Die Tickets konnten nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [partnerId, contactId, orderId])

  return { items, error }
}

function TicketLinks({ items }: { items: Ticket[] }) {
  if (items.length === 0) return <EmptyState compact title="Keine Tickets" description="Für diesen Bezug ist kein Service-Ticket gespeichert." />
  return (
    <ul className="grid gap-2 text-sm">
      {items.map((ticket) => (
        <li key={ticket.id}>
          <Link to={`/kundenservice/${ticket.id}`} className="font-semibold text-petrol">
            {ticket.ticket_number} · {ticket.subject}
          </Link>
          <span className="text-muted"> · {choiceLabel(ticketStatusOptions, ticket.status)} · {formatDateTime(ticket.updated_at)}</span>
        </li>
      ))}
    </ul>
  )
}

export function PartnerService({ partnerId }: { partnerId: string }) {
  const { items, error } = useTickets(partnerId)
  if (error) return <ErrorState title="Tickets nicht geladen" description={error} />
  if (!items) return <LoadingState label="Tickets werden geladen" />
  const open = items.filter((ticket) => !['geloest', 'geschlossen'].includes(ticket.status))
  const closed = items.filter((ticket) => ['geloest', 'geschlossen'].includes(ticket.status))
  const complaints = items.filter((ticket) => complaintCategories.has(ticket.category))
  const last = complaints[0]
  return (
    <div className="grid gap-4">
      <Link to={`/kundenservice/neu?partner=${partnerId}`} className={cx(buttonStyles.base, buttonStyles.primary, 'w-fit')}>
        Neues Service-Ticket
      </Link>
      <section>
        <h3 className="text-sm font-semibold">Letzte Reklamation</h3>
        {last ? (
          <p className="mt-1 text-sm">
            <Link to={`/kundenservice/${last.id}`} className="font-semibold text-petrol">{last.subject}</Link>
            {' · '}
            {formatDateTime(last.updated_at)}
          </p>
        ) : (
          <p className="mt-1 text-sm text-muted">Keine Reklamation gespeichert.</p>
        )}
      </section>
      <section>
        <h3 className="text-sm font-semibold">Offene Service-Tickets</h3>
        <div className="mt-2"><TicketLinks items={open} /></div>
      </section>
      <section>
        <h3 className="text-sm font-semibold">Geschlossene Service-Tickets</h3>
        <div className="mt-2"><TicketLinks items={closed} /></div>
      </section>
    </div>
  )
}

export function ContactService({ contactId }: { contactId: string }) {
  const { items, error } = useTickets(undefined, contactId)
  if (error) return <ErrorState title="Tickets nicht geladen" description={error} />
  if (!items) return <LoadingState label="Tickets werden geladen" />
  const latest = items[0]
  return (
    <div className="grid gap-3">
      <section>
        <h3 className="text-sm font-semibold">Letzte Serviceinteraktion</h3>
        {latest ? <p className="mt-1 text-sm">{latest.subject} · {formatDateTime(latest.updated_at)}</p> : <p className="mt-1 text-sm text-muted">Keine Serviceinteraktion gespeichert.</p>}
      </section>
      <section>
        <h3 className="text-sm font-semibold">Zugeordnete Service-Tickets</h3>
        <div className="mt-2"><TicketLinks items={items} /></div>
      </section>
    </div>
  )
}

export function OrderComplaints({ orderId }: { orderId: string }) {
  const { items, error } = useTickets(undefined, undefined, orderId)
  if (error) return <ErrorState title="Reklamationen nicht geladen" description={error} />
  if (!items) return <LoadingState label="Reklamationen werden geladen" />
  return (
    <section className="grid gap-2">
      <h2 className="font-semibold">Zugehörige Reklamationen</h2>
      <TicketLinks items={items} />
    </section>
  )
}

export function PartnerAnalysisPanel({ partnerId }: { partnerId: string }) {
  const [analysis, setAnalysis] = useState<PartnerAnalysis | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void fetchAnalysis(partnerId)
      .then((result) => {
        if (active) setAnalysis(result)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Die Kundenanalyse konnte nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [partnerId])

  if (error) return <ErrorState title="Analyse nicht verfügbar" description={error} />
  if (!analysis) return <LoadingState label="Kundenanalyse wird geladen" />

  const rows: [string, string][] = [
    ['Anzahl Bestellungen', String(analysis.order_count)],
    ['CRM-Bestellvolumen', formatChf(analysis.order_volume)],
    ['Durchschnittlicher Bestellwert', analysis.average_order_value ? formatChf(analysis.average_order_value) : 'Keine Bestellung'],
    ['Letzte Bestellung', analysis.last_order_on ? formatDate(analysis.last_order_on) : 'Keine'],
    ['Offene Verkaufschancen', String(analysis.open_deals)],
    ['Geschätzter Pipeline-Wert', formatChf(analysis.pipeline_value)],
    ['Offene Service-Tickets', String(analysis.open_tickets)],
    ['Abgeschlossene Service-Tickets', String(analysis.closed_tickets)],
    ['Letzte Kontaktaktivität', analysis.last_activity_on ? formatDate(analysis.last_activity_on) : 'Keine'],
  ]

  return (
    <div className="grid gap-3">
      <p className="text-sm leading-6 text-muted">{analysis.volume_basis}</p>
      <dl className="grid gap-3 sm:grid-cols-2">
        {rows.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</dt>
            <dd className="mt-1 text-sm font-semibold">{value}</dd>
          </div>
        ))}
      </dl>
    </div>
  )
}
