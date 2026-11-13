import { useEffect, useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, archiveDeal, fetchDeal, fetchOrder, fetchOrders, loseDeal, restoreDeal, winDeal } from '../../api/sales.ts'
import { LinkedActivities, LinkedTasks } from '../../components/crm/LinkedRecords.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Modal } from '../../components/ui/Modal.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { dealPriorityOptions, dealStageOptions, formatChf, type DealDetail, type Order } from '../../domain/sales.ts'
import { choiceLabel, formatDate, formatDateTime } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

export function DealDetailPage() {
  const { dealId = '' } = useParams()
  const [deal, setDeal] = useState<DealDetail | null>(null)
  const [orders, setOrders] = useState<Order[]>([])
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)
  const [winOpen, setWinOpen] = useState(false)
  const [loseOpen, setLoseOpen] = useState(false)
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [lossReason, setLossReason] = useState('')
  const [closedOn, setClosedOn] = useState('')

  usePageTitle(deal?.title ?? 'Verkaufschance')

  useEffect(() => {
    let active = true
    void Promise.all([fetchDeal(dealId), fetchOrders({ dealId })])
      .then(async ([loaded, list]) => {
        const details = await Promise.all(list.items.map((item) => fetchOrder(item.id)))
        if (!active) return
        setDeal(loaded)
        setOrders(details)
        setError(null)
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

  async function run(action: () => Promise<DealDetail>) {
    setError(null)
    try {
      const next = await action()
      setDeal(next)
      setWinOpen(false)
      setLoseOpen(false)
      setArchiveOpen(false)
    } catch (caught: unknown) {
      setError(caught instanceof ApiError ? caught.message : 'Die Aktion konnte nicht gespeichert werden.')
    }
  }

  if (pending) return <LoadingState label="Verkaufschance wird geladen" />
  if (!deal) return <ErrorState title="Verkaufschance nicht verfügbar" description={error ?? 'Der Deal wurde nicht gefunden.'} />

  const open = deal.stage !== 'gewonnen' && deal.stage !== 'verloren'
  const weighted = formatChf(previewWeighted(deal.estimated_value, deal.probability))

  return (
    <div className="mx-auto grid max-w-6xl gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted">{deal.company_name}</p>
          <h1 className="text-3xl font-semibold tracking-tight">{deal.title}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge tone="petrol">{choiceLabel(dealStageOptions, deal.stage)}</Badge>
            <Badge tone="neutral">{choiceLabel(dealPriorityOptions, deal.priority)}</Badge>
            {deal.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
            {deal.is_overdue ? <Badge tone="warning">Überfällig</Badge> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to={`/verkaufschancen/${deal.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Bearbeiten
          </Link>
          {open && !deal.archived_at ? (
            <>
              <Button onClick={() => setWinOpen(true)}>Gewinnen</Button>
              <Button variant="danger" onClick={() => setLoseOpen(true)}>
                Verlieren
              </Button>
            </>
          ) : null}
          {deal.archived_at ? (
            <Button onClick={() => void run(() => restoreDeal(deal.id))}>Wiederherstellen</Button>
          ) : (
            <Button variant="secondary" onClick={() => setArchiveOpen(true)}>
              Archivieren
            </Button>
          )}
        </div>
      </header>
      {error ? <ErrorState title="Aktion fehlgeschlagen" description={error} /> : null}
      {deal.is_demo ? (
        <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6">Fiktive Verkaufschance. Keine echte Offerte.</p>
      ) : null}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="p-4 lg:col-span-2">
          <h2 className="font-semibold">Deal-Informationen</h2>
          <dl className="mt-3 grid gap-2 text-sm sm:grid-cols-2">
            <Info label="Unternehmen" value={<Link to={`/vertriebspartner/${deal.partner_id}`} className="text-petrol">{deal.company_name}</Link>} />
            <Info label="Kontakt" value={deal.contact_name ?? 'Keine Kontaktperson'} />
            <Info label="Betreuung" value={deal.account_owner ?? 'Keine Angabe'} />
            <Info label="Geschätzter Wert" value={formatChf(deal.estimated_value)} />
            <Info label="Erwarteter Umsatz" value={`${weighted} bei ${deal.probability} %`} />
            <Info label="Erwarteter Abschluss" value={formatDate(deal.expected_close_on)} />
            <Info label="Tatsächlicher Abschluss" value={formatDate(deal.closed_on)} />
            <Info label="Verlustgrund" value={deal.loss_reason ?? 'Keiner'} />
            <Info label="Erstellt" value={formatDateTime(deal.created_at)} />
            <Info label="Geändert" value={formatDateTime(deal.updated_at)} />
          </dl>
          <p className="mt-4 text-sm leading-6">{deal.description ?? 'Keine Beschreibung.'}</p>
        </Card>
        <Card className="p-4">
          <h2 className="font-semibold">Phasenverlauf</h2>
          <ol className="mt-3 grid gap-2 text-sm">
            {deal.history.map((entry) => (
              <li key={entry.id}>
                {choiceLabel(dealStageOptions, entry.to_stage)} · {formatDateTime(entry.changed_at)}
                {entry.changed_by ? ` · ${entry.changed_by}` : ''}
              </li>
            ))}
          </ol>
        </Card>
      </div>
      <Card className="p-4">
        <h2 className="font-semibold">Produkte aus verknüpften Bestellungen</h2>
        {orders.length === 0 ? (
          <p className="mt-2 text-sm text-muted">Noch keine Bestellung mit diesem Deal verknüpft.</p>
        ) : (
          <ul className="mt-3 grid gap-3">
            {orders.map((order) => (
              <li key={order.id}>
                <Link to={`/bestellungen/${order.id}`} className="font-semibold text-petrol">
                  {order.order_number}
                </Link>
                <span className="text-sm text-muted"> · {formatChf(order.gross_total)}</span>
                <ul className="mt-1 text-sm">
                  {order.items.map((item) => (
                    <li key={item.id}>
                      {item.product_name} · {item.quantity} × {formatChf(item.unit_price)} · MWST {item.vat_rate} %
                    </li>
                  ))}
                </ul>
              </li>
            ))}
          </ul>
        )}
      </Card>
      <Card className="p-4">
        <h2 className="font-semibold">Aktivitäten</h2>
        <LinkedActivities partnerId={deal.partner_id} contactId={deal.contact_id ?? undefined} owner={deal.account_owner ?? ''} />
      </Card>
      <Card className="p-4">
        <h2 className="font-semibold">Aufgaben</h2>
        <LinkedTasks partnerId={deal.partner_id} contactId={deal.contact_id ?? undefined} />
      </Card>
      <ConfirmDialog
        open={winOpen}
        title="Deal gewinnen"
        description="Der Deal verlässt die offene Pipeline und bleibt in der Historie als gewonnen gespeichert."
        confirmLabel="Gewinnen"
        onConfirm={() => void run(() => winDeal(deal.id, closedOn))}
        onCancel={() => setWinOpen(false)}
      />
      <Modal open={loseOpen} title="Deal verlieren" onClose={() => setLoseOpen(false)}>
        <div className="grid gap-3">
          <Textarea label="Verlustgrund" value={lossReason} onChange={(event) => setLossReason(event.target.value)} />
          <Input label="Abschlussdatum" type="date" value={closedOn} onChange={(event) => setClosedOn(event.target.value)} />
          <div className="flex justify-end gap-2">
            <Button variant="secondary" onClick={() => setLoseOpen(false)}>
              Abbrechen
            </Button>
            <Button variant="danger" onClick={() => void run(() => loseDeal(deal.id, lossReason, closedOn))}>
              Verlieren
            </Button>
          </div>
        </div>
      </Modal>
      <ConfirmDialog
        open={archiveOpen}
        title="Verkaufschance archivieren"
        description="Der Deal bleibt gespeichert und kann wiederhergestellt werden."
        confirmLabel="Archivieren"
        tone="danger"
        onConfirm={() => void run(() => archiveDeal(deal.id))}
        onCancel={() => setArchiveOpen(false)}
      />
    </div>
  )
}

function Info({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <dt className="text-muted">{label}</dt>
      <dd>{value}</dd>
    </div>
  )
}

function previewWeighted(value: string, probability: string): string {
  const [whole, frac = ''] = value.split('.')
  const cents = BigInt(whole || '0') * 100n + BigInt(`${frac}00`.slice(0, 2))
  const [pWhole, pFrac = ''] = probability.split('.')
  const points = BigInt(pWhole || '0') * 100n + BigInt(`${pFrac}00`.slice(0, 2))
  const weighted = (cents * points + 5000n) / 10000n
  return `${weighted / 100n}.${(weighted % 100n).toString().padStart(2, '0')}`
}
