import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, changeOrderStatus, fetchOrder } from '../../api/sales.ts'
import { BoundaryNotice } from '../../components/sales/BoundaryNotice.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { formatChf, orderStatusOptions, type Order } from '../../domain/sales.ts'
import { choiceLabel, formatDate, formatDateTime } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

export function OrderDetailPage() {
  const { orderId = '' } = useParams()
  const [order, setOrder] = useState<Order | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)
  const [nextStatus, setNextStatus] = useState<string | null>(null)

  usePageTitle(order ? `Bestellung ${order.order_number}` : 'Bestellung')

  useEffect(() => {
    let active = true
    void fetchOrder(orderId)
      .then((loaded) => {
        if (!active) return
        setOrder(loaded)
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

  if (pending) return <LoadingState label="Bestellung wird geladen" />
  if (!order) return <ErrorState title="Bestellung nicht verfügbar" description={error ?? 'Die Bestellung wurde nicht gefunden.'} />

  return (
    <div className="mx-auto grid max-w-4xl gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted">{order.company_name}</p>
          <h1 className="text-3xl font-semibold tracking-tight">{order.order_number}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge tone="petrol">{choiceLabel(orderStatusOptions, order.status)}</Badge>
            {order.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
          </div>
        </div>
        {order.status === 'entwurf' ? (
          <Link to={`/bestellungen/${order.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Bearbeiten
          </Link>
        ) : null}
      </header>
      <BoundaryNotice topic="orders" />
      {error ? <ErrorState title="Status nicht geändert" description={error} /> : null}
      <Card className="p-4">
        <dl className="grid gap-2 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-muted">Vertriebspartner</dt>
            <dd>
              <Link to={`/vertriebspartner/${order.partner_id}`} className="text-petrol">
                {order.company_name}
              </Link>
            </dd>
          </div>
          <div>
            <dt className="text-muted">Kontakt</dt>
            <dd>{order.contact_name ?? 'Keine Kontaktperson'}</dd>
          </div>
          <div>
            <dt className="text-muted">Bestelldatum</dt>
            <dd>{formatDate(order.ordered_on)}</dd>
          </div>
          <div>
            <dt className="text-muted">Gewünschtes Lieferdatum</dt>
            <dd>{formatDate(order.requested_delivery_on)}</dd>
          </div>
          <div>
            <dt className="text-muted">Verkaufschance</dt>
            <dd>{order.deal_id ? <Link to={`/verkaufschancen/${order.deal_id}`} className="text-petrol">Deal öffnen</Link> : 'Keine'}</dd>
          </div>
          <div>
            <dt className="text-muted">ERP-Referenz</dt>
            <dd>{order.erp_reference ?? 'Noch keine ERP-Referenz'}</dd>
          </div>
          <div>
            <dt className="text-muted">Erstellt</dt>
            <dd>{formatDateTime(order.created_at)}</dd>
          </div>
          <div>
            <dt className="text-muted">Geändert</dt>
            <dd>{formatDateTime(order.updated_at)}</dd>
          </div>
        </dl>
        <p className="mt-3 text-sm leading-6">{order.notes ?? 'Keine internen Bemerkungen.'}</p>
      </Card>
      <Card className="overflow-x-auto p-4">
        <h2 className="font-semibold">Positionen</h2>
        <table className="mt-3 w-full text-left text-sm">
          <thead>
            <tr className="text-xs tracking-wide text-muted uppercase">
              <th className="py-2">Produkt</th>
              <th>Menge</th>
              <th>Preis</th>
              <th>Rabatt</th>
              <th>MWST</th>
              <th>Betrag</th>
            </tr>
          </thead>
          <tbody>
            {order.items.map((item) => (
              <tr key={item.id} className="border-t border-line">
                <td className="py-2">
                  {item.product_name}
                  <span className="block text-xs text-muted">{item.sku}</span>
                </td>
                <td>{item.quantity}</td>
                <td>{formatChf(item.unit_price)}</td>
                <td>{item.discount_percent} %</td>
                <td>
                  {item.vat_rate} % · {formatChf(item.line_vat)}
                </td>
                <td>{formatChf(item.line_gross)}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <dl className="mt-4 grid justify-end gap-1 text-sm">
          <div className="flex justify-between gap-8"><dt>Zwischensumme</dt><dd>{formatChf(order.subtotal)}</dd></div>
          <div className="flex justify-between gap-8"><dt>Rabatt</dt><dd>{formatChf(order.discount_total)}</dd></div>
          <div className="flex justify-between gap-8"><dt>Netto</dt><dd>{formatChf(order.net_total)}</dd></div>
          <div className="flex justify-between gap-8"><dt>Mehrwertsteuer</dt><dd>{formatChf(order.vat_total)}</dd></div>
          <div className="flex justify-between gap-8 font-semibold"><dt>Gesamtbetrag</dt><dd>{formatChf(order.gross_total)}</dd></div>
        </dl>
      </Card>
      {order.allowed_transitions.length > 0 ? (
        <div className="flex flex-wrap gap-2">
          {order.allowed_transitions.map((status) => (
            <Button key={status} variant={status === 'storniert' ? 'danger' : 'secondary'} onClick={() => setNextStatus(status)}>
              {choiceLabel(orderStatusOptions, status)}
            </Button>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted">Für diesen Status ist kein weiterer Wechsel vorgesehen.</p>
      )}
      <ConfirmDialog
        open={nextStatus !== null}
        title="Status ändern"
        description={
          nextStatus === 'versandt' || nextStatus === 'geliefert'
            ? `«${choiceLabel(orderStatusOptions, nextStatus)}» ist eine interne CRM-Angabe und bedeutet keine ERP-Auslieferung.`
            : `Die Bestellung wechselt nach «${choiceLabel(orderStatusOptions, nextStatus)}».`
        }
        confirmLabel="Status speichern"
        tone={nextStatus === 'storniert' ? 'danger' : 'primary'}
        onCancel={() => setNextStatus(null)}
        onConfirm={() => {
          if (!nextStatus) return
          void changeOrderStatus(order.id, nextStatus)
            .then((saved) => {
              setOrder(saved)
              setNextStatus(null)
            })
            .catch((caught: unknown) => {
              setNextStatus(null)
              setError(caught instanceof ApiError ? caught.message : 'Der Status konnte nicht gespeichert werden.')
            })
        }}
      />
    </div>
  )
}
