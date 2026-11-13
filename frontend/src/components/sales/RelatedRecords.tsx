import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, fetchDeals, fetchOrderSummary, fetchOrders } from '../../api/sales.ts'
import { buttonStyles } from '../ui/button-styles.ts'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { LoadingState } from '../ui/LoadingState.tsx'
import { dealStageOptions, formatChf, orderStatusOptions, type Deal, type OrderListItem, type OrderSummary } from '../../domain/sales.ts'
import { choiceLabel, formatDate } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { BoundaryNotice } from './BoundaryNotice.tsx'

export function PartnerDeals({ partnerId }: { partnerId: string }) {
  const [openDeals, setOpenDeals] = useState<Deal[] | null>(null)
  const [wonDeals, setWonDeals] = useState<Deal[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void Promise.all([
      fetchDeals({ partnerId, page: 1 }),
      fetchDeals({ partnerId, stage: 'gewonnen', includeClosed: true }),
    ])
      .then(([openList, wonList]) => {
        if (!active) return
        setOpenDeals(openList.items)
        setWonDeals(wonList.items)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Die Verkaufschancen konnten nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [partnerId])

  if (error) return <ErrorState title="Verkaufschancen" description={error} />
  if (!openDeals) return <LoadingState label="Verkaufschancen werden geladen" />

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap gap-2">
        <Link to={`/verkaufschancen/neu?partner=${partnerId}`} className={cx(buttonStyles.base, buttonStyles.primary)}>
          Neue Verkaufschance
        </Link>
      </div>
      <DealGroup title="Offene Verkaufschancen" deals={openDeals} empty="Keine offenen Verkaufschancen." />
      <DealGroup title="Gewonnene Verkaufschancen" deals={wonDeals} empty="Keine gewonnenen Verkaufschancen." />
    </div>
  )
}

function DealGroup({ title, deals, empty }: { title: string; deals: Deal[]; empty: string }) {
  return (
    <section>
      <h3 className="font-semibold">{title}</h3>
      {deals.length === 0 ? <p className="mt-1 text-sm text-muted">{empty}</p> : null}
      <ul className="mt-2 grid gap-2">
        {deals.map((deal) => (
          <li key={deal.id}>
            <Link to={`/verkaufschancen/${deal.id}`} className="font-semibold text-petrol">
              {deal.title}
            </Link>
            <span className="text-sm text-muted">
              {' '}
              · {choiceLabel(dealStageOptions, deal.stage)} · {formatChf(deal.estimated_value)}
              {deal.is_demo ? ' · Testdaten' : ''}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}

export function PartnerOrders({ partnerId }: { partnerId: string }) {
  const [orders, setOrders] = useState<OrderListItem[] | null>(null)
  const [summary, setSummary] = useState<OrderSummary | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void Promise.all([fetchOrders({ partnerId }), fetchOrderSummary(partnerId)])
      .then(([list, totals]) => {
        if (!active) return
        setOrders(list.items)
        setSummary(totals)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Die Bestellungen konnten nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [partnerId])

  if (error) return <ErrorState title="Bestellungen" description={error} />
  if (!orders || !summary) return <LoadingState label="Bestellungen werden geladen" />

  return (
    <div className="grid gap-3">
      <BoundaryNotice topic="orders" />
      <p className="text-sm leading-6">
        Bestellvolumen {formatChf(summary.volume)} aus {summary.order_count} eingereichten oder weitergeführten Bestellungen.
        {summary.volume !== '0.00' && summary.volume === summary.volume_demo ? ' Ausschliesslich gekennzeichnete Testdaten.' : ''} Letzte
        Bestellung: {formatDate(summary.last_ordered_on)}.
      </p>
      <Link to={`/bestellungen/neu?partner=${partnerId}`} className={cx(buttonStyles.base, buttonStyles.primary, 'justify-self-start')}>
        Neue Bestellung
      </Link>
      {orders.length === 0 ? <EmptyState compact title="Keine Bestellungen" description="Für dieses Unternehmen ist keine Bestellung gespeichert." /> : null}
      <ul className="grid gap-2 text-sm">
        {orders.map((order) => (
          <li key={order.id}>
            <Link to={`/bestellungen/${order.id}`} className="font-semibold text-petrol">
              {order.order_number}
            </Link>
            {' · '}
            {formatDate(order.ordered_on)} · {choiceLabel(orderStatusOptions, order.status)} · {formatChf(order.gross_total)}
            {order.is_demo ? ' · Testdaten' : ''}
          </li>
        ))}
      </ul>
    </div>
  )
}

export function ContactSales({ contactId }: { contactId: string }) {
  const [deals, setDeals] = useState<Deal[] | null>(null)
  const [orders, setOrders] = useState<OrderListItem[]>([])
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void Promise.all([fetchDeals({ contactId, includeClosed: true }), fetchOrders({ contactId })])
      .then(([dealList, orderList]) => {
        if (!active) return
        setDeals(dealList.items)
        setOrders(orderList.items)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Die Verknüpfungen konnten nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [contactId])

  if (error) return <ErrorState title="Verkauf und Bestellungen" description={error} />
  if (!deals) return <LoadingState label="Verknüpfungen werden geladen" />

  return (
    <div className="grid gap-4">
      <section>
        <h3 className="font-semibold">Zugeordnete Deals</h3>
        {deals.length === 0 ? <p className="mt-1 text-sm text-muted">Keine Verkaufschancen für diese Kontaktperson.</p> : null}
        <ul className="mt-2 grid gap-2 text-sm">
          {deals.map((deal) => (
            <li key={deal.id}>
              <Link to={`/verkaufschancen/${deal.id}`} className="font-semibold text-petrol">
                {deal.title}
              </Link>
              {' · '}
              {deal.company_name} · {choiceLabel(dealStageOptions, deal.stage)}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3 className="font-semibold">Zugeordnete Bestellungen</h3>
        <BoundaryNotice topic="orders" />
        {orders.length === 0 ? <p className="mt-2 text-sm text-muted">Keine Bestellungen für diese Kontaktperson.</p> : null}
        <ul className="mt-2 grid gap-2 text-sm">
          {orders.map((order) => (
            <li key={order.id}>
              <Link to={`/bestellungen/${order.id}`} className="font-semibold text-petrol">
                {order.order_number}
              </Link>
              {' · '}
              {formatChf(order.gross_total)} · {choiceLabel(orderStatusOptions, order.status)}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

