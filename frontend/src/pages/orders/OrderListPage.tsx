import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { ApiError, fetchOrders } from '../../api/sales.ts'
import { BoundaryNotice } from '../../components/sales/BoundaryNotice.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { DataTable, type DataColumn } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { formatChf, orderStatusOptions, type OrderList, type OrderListItem } from '../../domain/sales.ts'
import { choiceLabel, formatDate } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const columns: DataColumn<OrderListItem>[] = [
  {
    id: 'number',
    header: 'Bestellung',
    cell: (row) => (
      <Link to={`/bestellungen/${row.id}`} className="font-semibold text-petrol">
        {row.order_number}
      </Link>
    ),
  },
  { id: 'company', header: 'Unternehmen', cell: (row) => row.company_name },
  { id: 'date', header: 'Bestelldatum', cell: (row) => formatDate(row.ordered_on) },
  { id: 'status', header: 'Status', cell: (row) => choiceLabel(orderStatusOptions, row.status) },
  { id: 'total', header: 'Gesamtbetrag', cell: (row) => formatChf(row.gross_total) },
  { id: 'demo', header: 'Hinweis', cell: (row) => (row.is_demo ? <Badge tone="accent">Testdaten</Badge> : null) },
]

export function OrderListPage() {
  usePageTitle('Bestellungen')
  const [params, setParams] = useSearchParams()
  const queryKey = params.toString()
  const [data, setData] = useState<OrderList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)

  useEffect(() => {
    let active = true
    const current = new URLSearchParams(queryKey)
    const page = Number(current.get('seite') ?? '1')
    void fetchOrders({
      q: current.get('q') ?? '',
      status: current.get('status') ?? '',
      page: Number.isInteger(page) && page > 0 ? page : 1,
    })
      .then((list) => {
        if (active) {
          setData(list)
          setError(null)
          setPending(false)
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof ApiError ? caught.message : 'Die Bestellungen konnten nicht geladen werden.')
          setPending(false)
        }
      })
    return () => {
      active = false
    }
  }, [queryKey])

  function assign(changes: Record<string, string | null>, resetPage = true) {
    setPending(true)
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) next.set(key, value)
      else next.delete(key)
    }
    if (resetPage) next.delete('seite')
    setParams(next)
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Bestellungen</h1>
          <p className="mt-2 text-sm leading-6 text-muted">Dokumentierte CRM-Bestellungen mit verbindlicher Betragsberechnung auf dem Server.</p>
        </div>
        <Link to="/bestellungen/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Neue Bestellung
        </Link>
      </header>
      <BoundaryNotice topic="orders" />
      <div className="grid gap-3 md:grid-cols-2">
        <Input label="Suche" value={params.get('q') ?? ''} onChange={(event) => assign({ q: event.target.value || null })} />
        <Select
          label="Status"
          value={params.get('status') ?? ''}
          onChange={(value) => assign({ status: value || null })}
          options={[{ value: '', label: 'Alle Status' }, ...orderStatusOptions]}
        />
      </div>
      {error ? <ErrorState title="Bestellungen nicht geladen" description={error} /> : null}
      {pending && !data ? <LoadingState label="Bestellungen werden geladen" /> : null}
      {data ? (
        <DataTable
          caption="Bestellungen"
          columns={columns}
          rows={data.items}
          rowKey={(row) => row.id}
          empty={<EmptyState title="Keine Bestellungen" description="Für diesen Filter sind keine Bestellungen gespeichert." />}
        />
      ) : null}
      {data && data.total > data.page_size ? (
        <div className="flex justify-end gap-2">
          <button type="button" className={cx(buttonStyles.base, buttonStyles.secondary)} disabled={data.page <= 1} onClick={() => assign({ seite: data.page > 2 ? String(data.page - 1) : null }, false)}>
            Zurück
          </button>
          <button type="button" className={cx(buttonStyles.base, buttonStyles.secondary)} disabled={data.page * data.page_size >= data.total} onClick={() => assign({ seite: String(data.page + 1) }, false)}>
            Weiter
          </button>
        </div>
      ) : null}
    </div>
  )
}
