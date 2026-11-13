import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { ApiError, fetchPartnerFilters, fetchPartners } from '../../api/partners.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { DataTable, type DataColumn } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import {
  choiceLabel,
  formatLocation,
  partnerStatusOptions,
  partnerTypeOptions,
  statusTone,
  withCurrent,
  type Partner,
  type PartnerFilters,
  type PartnerList,
  type PartnerQuery,
} from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const columns: DataColumn<Partner>[] = [
  {
    id: 'name',
    header: 'Unternehmensname',
    cell: (row) => (
      <div className="grid gap-1">
        <Link to={`/vertriebspartner/${row.id}`} className="font-semibold text-petrol hover:underline">
          {row.company_name}
        </Link>
        <div className="flex flex-wrap gap-1">
          {row.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
          {row.archived_at ? <Badge tone="critical">Archiviert</Badge> : null}
        </div>
      </div>
    ),
  },
  {
    id: 'type',
    header: 'Partnertyp',
    cell: (row) => choiceLabel(partnerTypeOptions, row.partner_type),
  },
  {
    id: 'location',
    header: 'Standort',
    cell: (row) => formatLocation(row),
  },
  {
    id: 'status',
    header: 'Partnerstatus',
    cell: (row) => <Badge tone={statusTone(row.status)}>{choiceLabel(partnerStatusOptions, row.status)}</Badge>,
  },
  {
    id: 'owner',
    header: 'Zuständige Betreuungsperson',
    cell: (row) => row.account_owner ?? 'Nicht zugewiesen',
  },
  {
    id: 'contact',
    header: 'Letzter Kontakt',
    cell: () => <span title="Aktivitäten sind noch nicht implementiert.">Nicht implementiert</span>,
  },
  {
    id: 'next',
    header: 'Nächste Aktivität',
    cell: () => <span title="Aktivitäten sind noch nicht implementiert.">Nicht implementiert</span>,
  },
]

const sortOptions = [
  { value: 'name:asc', label: 'Name (A–Z)' },
  { value: 'name:desc', label: 'Name (Z–A)' },
  { value: 'created_at:desc', label: 'Erstellungsdatum, neueste zuerst' },
  { value: 'created_at:asc', label: 'Erstellungsdatum, älteste zuerst' },
  { value: 'last_activity:desc', label: 'Letzte Aktivität' },
]

function readQuery(params: URLSearchParams): PartnerQuery {
  const sortValue = params.get('sort')
  const sort = sortValue === 'created_at' || sortValue === 'last_activity' ? sortValue : 'name'
  const page = Number(params.get('seite') ?? '1')
  return {
    q: params.get('q') ?? '',
    status: params.get('status') ?? '',
    industry: params.get('branche') ?? '',
    region: params.get('region') ?? '',
    accountOwner: params.get('betreuung') ?? '',
    sort,
    direction: params.get('richtung') === 'ab' ? 'desc' : 'asc',
    page: Number.isInteger(page) && page > 0 ? page : 1,
    includeArchived: params.get('archiv') === 'ja',
  }
}

function resultLabel(total: number): string {
  return total === 1 ? '1 Vertriebspartner gefunden' : `${total} Vertriebspartner gefunden`
}

function textChoices(values: string[], current: string) {
  return withCurrent(
    [{ value: '', label: 'Alle' }, ...values.map((value) => ({ value, label: value }))],
    current,
  )
}

export function PartnerListPage() {
  usePageTitle('Vertriebspartner')
  const [params, setParams] = useSearchParams()
  const query = readQuery(params)
  const queryKey = params.toString()
  const [data, setData] = useState<PartnerList | null>(null)
  const [filters, setFilters] = useState<PartnerFilters>({ industries: [], regions: [], accountOwners: [] })
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    void Promise.all([fetchPartners(readQuery(new URLSearchParams(queryKey))), fetchPartnerFilters()])
      .then(([list, options]) => {
        if (!active) {
          return
        }
        setData(list)
        setFilters(options)
        setError(null)
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) {
          return
        }
        setData(null)
        setError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [queryKey, reloadKey])

  function assign(changes: Record<string, string | null>, resetPage = true) {
    setPending(true)
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) {
        next.set(key, value)
      } else {
        next.delete(key)
      }
    }
    if (resetPage) {
      next.delete('seite')
    }
    setParams(next)
  }

  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 20)))
  const filtered = Boolean(query.q || query.status || query.industry || query.region || query.accountOwner)
  const sortValue = `${query.sort}:${query.direction}`

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Vertriebspartner</h1>
          <p className="mt-2 max-w-3xl text-base leading-7 text-muted">
            Restaurants, Hotels, Bars, Getränkehändler und weitere Geschäftspartner zentral betreuen.
          </p>
        </div>
        <Link to="/vertriebspartner/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Neuen Partner erstellen
        </Link>
      </header>

      <Card className="grid gap-4 p-4">
        <PartnerSearch key={query.q} initial={query.q} onSearch={(value) => assign({ q: value.trim() })} />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Select
            label="Partnerstatus"
            value={query.status}
            options={[{ value: '', label: 'Alle' }, ...partnerStatusOptions]}
            onChange={(value) => assign({ status: value })}
          />
          <Select
            label="Branche"
            value={query.industry}
            options={textChoices(filters.industries, query.industry)}
            onChange={(value) => assign({ branche: value })}
          />
          <Select
            label="Region"
            value={query.region}
            options={textChoices(filters.regions, query.region)}
            onChange={(value) => assign({ region: value })}
          />
          <Select
            label="Betreuungsperson"
            value={query.accountOwner}
            options={textChoices(filters.accountOwners, query.accountOwner)}
            onChange={(value) => assign({ betreuung: value })}
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)_auto] md:items-end">
          <Select
            label="Sortierung"
            value={sortOptions.some((option) => option.value === sortValue) ? sortValue : 'name:asc'}
            options={sortOptions}
            hint={
              query.sort === 'last_activity'
                ? 'Aktivitäten werden noch nicht gespeichert. Sortiert wird nach dem Namen.'
                : undefined
            }
            onChange={(value) => {
              const [sort, direction] = value.split(':')
              assign({
                sort: sort === 'name' ? null : (sort ?? null),
                richtung: direction === 'desc' ? 'ab' : null,
              })
            }}
          />
          <Select
            label="Archiv"
            value={query.includeArchived ? 'ja' : 'nein'}
            options={[
              { value: 'nein', label: 'Ohne archivierte Partner' },
              { value: 'ja', label: 'Mit archivierten Partnern' },
            ]}
            onChange={(value) => assign({ archiv: value === 'ja' ? 'ja' : null })}
          />
          <Button
            variant="ghost"
            onClick={() => {
              setPending(true)
              setParams(new URLSearchParams())
            }}
          >
            Filter zurücksetzen
          </Button>
        </div>
      </Card>

      <Card>
        {data === null && pending ? <LoadingState label="Vertriebspartner werden geladen" /> : null}
        {data === null && error ? (
          <div className="p-4">
            <ErrorState
              title="Liste nicht verfügbar"
              description={error}
              action={
                <Button
                  variant="secondary"
                  onClick={() => {
                    setPending(true)
                    setError(null)
                    setReloadKey((value) => value + 1)
                  }}
                >
                  Erneut laden
                </Button>
              }
            />
          </div>
        ) : null}
        {data ? (
          <div aria-busy={pending}>
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-line px-4 py-3">
              <p aria-live="polite" className="text-sm font-semibold">
                {resultLabel(data.total)}
              </p>
              {pending ? <LoadingState label="Liste wird aktualisiert" /> : null}
            </div>
            {data.items.some((item) => item.is_demo) ? (
              <p className="border-b border-line px-4 py-3 text-sm leading-6 text-muted">
                Mit «Testdaten» markierte Unternehmen sind fiktiv und keine Kunden des Liechtensteiner Brauhauses.
              </p>
            ) : null}
            <DataTable
              caption="Vertriebspartner"
              columns={columns}
              rows={data.items}
              rowKey={(row) => row.id}
              tableClassName="min-w-[72rem]"
              empty={
                <EmptyState
                  title={filtered || query.includeArchived ? 'Keine Treffer' : 'Noch keine Vertriebspartner'}
                  description={
                    filtered
                      ? 'Passen Sie Suche oder Filter an. Es werden keine erfundenen Partner angezeigt.'
                      : 'Legen Sie den ersten Partner an oder spielen Sie die gekennzeichneten Testdaten ein.'
                  }
                  action={
                    filtered ? undefined : (
                      <Link to="/vertriebspartner/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
                        Neuen Partner erstellen
                      </Link>
                    )
                  }
                />
              }
            />
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <p className="text-sm text-muted">
                Seite {query.page} von {pages}
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  disabled={query.page <= 1 || pending}
                  onClick={() => assign({ seite: query.page - 1 <= 1 ? null : String(query.page - 1) }, false)}
                >
                  Zurück
                </Button>
                <Button
                  variant="secondary"
                  disabled={query.page >= pages || pending}
                  onClick={() => assign({ seite: String(query.page + 1) }, false)}
                >
                  Weiter
                </Button>
              </div>
            </div>
          </div>
        ) : null}
      </Card>
    </div>
  )
}

function PartnerSearch({ initial, onSearch }: { initial: string; onSearch: (value: string) => void }) {
  const [value, setValue] = useState(initial)

  return (
    <form
      className="flex flex-wrap items-end gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        onSearch(value)
      }}
    >
      <div className="min-w-[16rem] flex-1">
        <Input
          label="Suche nach Name, Ort oder Kundennummer"
          value={value}
          hint="Durchsucht Unternehmensname, Ort und ERP-Kundennummer."
          autoComplete="off"
          onChange={(event) => setValue(event.target.value)}
        />
      </div>
      <Button type="submit">Suchen</Button>
    </form>
  )
}
