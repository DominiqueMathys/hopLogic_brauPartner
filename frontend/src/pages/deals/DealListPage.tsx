import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { ApiError, fetchDeals } from '../../api/sales.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { DataTable, type DataColumn } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { dealPriorityOptions, dealStageOptions, formatChf, type Deal, type DealList } from '../../domain/sales.ts'
import { choiceLabel, formatDate } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const columns: DataColumn<Deal>[] = [
  {
    id: 'title',
    header: 'Verkaufschance',
    cell: (row) => (
      <Link to={`/verkaufschancen/${row.id}`} className="font-semibold text-petrol">
        {row.title}
      </Link>
    ),
  },
  { id: 'company', header: 'Unternehmen', cell: (row) => row.company_name },
  { id: 'stage', header: 'Phase', cell: (row) => choiceLabel(dealStageOptions, row.stage) },
  { id: 'value', header: 'Wert', cell: (row) => formatChf(row.estimated_value) },
  { id: 'close', header: 'Abschluss', cell: (row) => formatDate(row.expected_close_on) },
  { id: 'owner', header: 'Betreuung', cell: (row) => row.account_owner ?? 'Keine Angabe' },
  {
    id: 'demo',
    header: 'Hinweis',
    cell: (row) => (row.is_demo ? <Badge tone="accent">Testdaten</Badge> : row.is_overdue ? <Badge tone="warning">Überfällig</Badge> : null),
  },
]

export function DealListPage() {
  usePageTitle('Verkaufschancen')
  const [params, setParams] = useSearchParams()
  const queryKey = params.toString()
  const [data, setData] = useState<DealList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)

  useEffect(() => {
    let active = true
    const current = new URLSearchParams(queryKey)
    const page = Number(current.get('seite') ?? '1')
    void fetchDeals({
      q: current.get('q') ?? '',
      stage: current.get('phase') ?? '',
      accountOwner: current.get('betreuung') ?? '',
      closeFrom: current.get('von') ?? '',
      closeTo: current.get('bis') ?? '',
      includeClosed: current.get('abgeschlossen') === '1',
      overdueOnly: current.get('ueberfaellig') === '1',
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
          setError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
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
          <h1 className="text-3xl font-semibold tracking-tight">Verkaufschancen</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Offene Chancen stehen getrennt von gewonnenen und verlorenen Deals. Die Abschlusswahrscheinlichkeit folgt der Verkaufsphase.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/verkaufschancen/pipeline" className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Pipeline
          </Link>
          <Link to="/verkaufschancen/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
            Neue Verkaufschance
          </Link>
        </div>
      </header>
      <div className="grid gap-3 md:grid-cols-4">
        <Input label="Suche" value={params.get('q') ?? ''} onChange={(event) => assign({ q: event.target.value || null })} />
        <Select
          label="Phase"
          value={params.get('phase') ?? ''}
          onChange={(value) => assign({ phase: value || null })}
          options={[{ value: '', label: 'Offene Phasen' }, ...dealStageOptions]}
        />
        <Input label="Betreuung" value={params.get('betreuung') ?? ''} onChange={(event) => assign({ betreuung: event.target.value || null })} />
        <Select
          label="Ansicht"
          value={params.get('abgeschlossen') === '1' ? 'alle' : params.get('ueberfaellig') === '1' ? 'ueberfaellig' : 'offen'}
          onChange={(value) =>
            assign({
              abgeschlossen: value === 'alle' ? '1' : null,
              ueberfaellig: value === 'ueberfaellig' ? '1' : null,
            })
          }
          options={[
            { value: 'offen', label: 'Nur offene' },
            { value: 'alle', label: 'Inklusive Abschluss' },
            { value: 'ueberfaellig', label: 'Nur überfällige' },
          ]}
        />
      </div>
      {error ? <ErrorState title="Verkaufschancen nicht geladen" description={error} /> : null}
      {pending && !data ? <LoadingState label="Verkaufschancen werden geladen" /> : null}
      {data ? (
        <DataTable
          caption="Verkaufschancen"
          columns={columns}
          rows={data.items}
          rowKey={(row) => row.id}
          empty={<EmptyState title="Keine Verkaufschancen" description="Für diesen Filter sind keine Deals gespeichert." />}
        />
      ) : null}
      {data && data.total > data.page_size ? (
        <div className="flex justify-end gap-2">
          <button
            type="button"
            className={cx(buttonStyles.base, buttonStyles.secondary)}
            disabled={data.page <= 1}
            onClick={() => assign({ seite: data.page > 2 ? String(data.page - 1) : null }, false)}
          >
            Zurück
          </button>
          <button
            type="button"
            className={cx(buttonStyles.base, buttonStyles.secondary)}
            disabled={data.page * data.page_size >= data.total}
            onClick={() => assign({ seite: String(data.page + 1) }, false)}
          >
            Weiter
          </button>
        </div>
      ) : null}
      <p className="text-xs text-muted">Priorität: {dealPriorityOptions.map((option) => option.label).join(', ')}. Beträge in CHF.</p>
    </div>
  )
}
