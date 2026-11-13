import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { ApiError, fetchContactFilters, fetchContacts } from '../../api/crm.ts'
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
  contactName,
  contactStatusOptions,
  labelOf,
  type Contact,
  type ContactFilters,
  type ContactList,
  type ContactQuery,
} from '../../domain/crm.ts'
import { formatDateTime, withCurrent } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const columns: DataColumn<Contact>[] = [
  {
    id: 'name',
    header: 'Name',
    cell: (row) => (
      <div>
        <Link to={`/kontakte/${row.id}`} className="font-semibold text-petrol">
          {contactName(row)}
        </Link>
        {row.is_demo ? (
          <div className="mt-1">
            <Badge tone="accent">Testdaten</Badge>
          </div>
        ) : null}
      </div>
    ),
  },
  { id: 'job', header: 'Funktion', cell: (row) => row.job_title ?? 'Keine Angabe' },
  {
    id: 'company',
    header: 'Unternehmen',
    cell: (row) =>
      row.companies.length === 0
        ? 'Nicht zugeordnet'
        : row.companies.map((company) => company.company_name).join(', '),
  },
  { id: 'status', header: 'Kontaktstatus', cell: (row) => labelOf(contactStatusOptions, row.status) },
  { id: 'owner', header: 'Betreuung', cell: (row) => row.account_owner ?? 'Nicht zugewiesen' },
  {
    id: 'last',
    header: 'Letzter Kontakt',
    cell: (row) => (row.last_contact_at ? formatDateTime(row.last_contact_at) : 'Kein Eintrag'),
  },
]

function readQuery(params: URLSearchParams): ContactQuery {
  const sort = params.get('sort') === 'last_contact' ? 'last_contact' : 'name'
  const page = Number(params.get('seite') ?? '1')
  return {
    q: params.get('q') ?? '',
    partnerId: params.get('unternehmen') ?? '',
    status: params.get('status') ?? '',
    accountOwner: params.get('betreuung') ?? '',
    sort,
    direction: params.get('richtung') === 'ab' ? 'desc' : 'asc',
    page: Number.isInteger(page) && page > 0 ? page : 1,
    includeArchived: params.get('archiv') === 'ja',
  }
}

export function ContactListPage() {
  usePageTitle('Kontakte')
  const [params, setParams] = useSearchParams()
  const query = readQuery(params)
  const queryKey = params.toString()
  const [data, setData] = useState<ContactList | null>(null)
  const [filters, setFilters] = useState<ContactFilters>({ companies: [], accountOwners: [] })
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)

  useEffect(() => {
    let active = true
    void Promise.all([fetchContacts(readQuery(new URLSearchParams(queryKey))), fetchContactFilters()])
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
  }, [queryKey])

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
  const companyOptions = withCurrent(
    [
      { value: '', label: 'Alle' },
      ...filters.companies.map((company) => ({ value: company.partner_id, label: company.company_name })),
    ],
    query.partnerId,
  )
  const ownerOptions = withCurrent(
    [{ value: '', label: 'Alle' }, ...filters.accountOwners.map((owner) => ({ value: owner, label: owner }))],
    query.accountOwner,
  )

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Kontakte</h1>
          <p className="mt-2 max-w-3xl text-base leading-7 text-muted">
            Ansprechpersonen bei Restaurants, Hotels und Handelspartnern.
          </p>
        </div>
        <Link to="/kontakte/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Neuen Kontakt erstellen
        </Link>
      </header>
      <Card className="grid gap-4 p-4">
        <SearchBox key={query.q} initial={query.q} onSearch={(value) => assign({ q: value.trim() })} />
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <Select label="Unternehmen" value={query.partnerId} options={companyOptions} onChange={(value) => assign({ unternehmen: value })} />
          <Select
            label="Kontaktstatus"
            value={query.status}
            options={[{ value: '', label: 'Alle' }, ...contactStatusOptions]}
            onChange={(value) => assign({ status: value })}
          />
          <Select label="Betreuungsperson" value={query.accountOwner} options={ownerOptions} onChange={(value) => assign({ betreuung: value })} />
          <Select
            label="Sortierung"
            value={`${query.sort}:${query.direction}`}
            options={[
              { value: 'name:asc', label: 'Name (A–Z)' },
              { value: 'name:desc', label: 'Name (Z–A)' },
              { value: 'last_contact:desc', label: 'Letzter Kontakt, neueste zuerst' },
              { value: 'last_contact:asc', label: 'Letzter Kontakt, älteste zuerst' },
            ]}
            onChange={(value) => {
              const [sort, direction] = value.split(':')
              assign({
                sort: sort === 'name' ? null : (sort ?? null),
                richtung: direction === 'desc' ? 'ab' : null,
              })
            }}
          />
        </div>
        <Select
          label="Archiv"
          value={query.includeArchived ? 'ja' : 'nein'}
          options={[
            { value: 'nein', label: 'Ohne archivierte Kontakte' },
            { value: 'ja', label: 'Mit archivierten Kontakten' },
          ]}
          onChange={(value) => assign({ archiv: value === 'ja' ? 'ja' : null })}
        />
      </Card>
      <Card>
        {error ? (
          <ErrorState title="Kontakte nicht verfügbar" description={error} />
        ) : pending || !data ? (
          <LoadingState label="Kontakte werden geladen" />
        ) : (
          <div>
            <p className="px-4 pt-4 text-sm text-muted">
              {data.total === 1 ? '1 Kontakt gefunden' : `${data.total} Kontakte gefunden`}
            </p>
            <DataTable
              caption="Kontaktliste"
              columns={columns}
              rows={data.items}
              rowKey={(row) => row.id}
              empty={
                <EmptyState
                  title={query.q || query.status || query.partnerId ? 'Keine Treffer' : 'Keine Kontakte'}
                  description={
                    query.q || query.status || query.partnerId
                      ? 'Für diese Suche oder diesen Filter ist kein Kontakt gespeichert.'
                      : 'Es sind noch keine Kontaktpersonen erfasst.'
                  }
                />
              }
            />
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <p className="text-sm text-muted">
                Seite {query.page} von {pages}
              </p>
              <div className="flex gap-2">
                <Button variant="secondary" disabled={query.page <= 1 || pending} onClick={() => assign({ seite: query.page - 1 <= 1 ? null : String(query.page - 1) }, false)}>
                  Zurück
                </Button>
                <Button variant="secondary" disabled={query.page >= pages || pending} onClick={() => assign({ seite: String(query.page + 1) }, false)}>
                  Weiter
                </Button>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}

function SearchBox({ initial, onSearch }: { initial: string; onSearch: (value: string) => void }) {
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
          label="Suche nach Vorname, Nachname, Unternehmen oder E-Mail"
          value={value}
          autoComplete="off"
          onChange={(event) => setValue(event.target.value)}
        />
      </div>
      <Button type="submit">Suchen</Button>
    </form>
  )
}
