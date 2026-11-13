import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { ApiError, fetchTicketSummary, fetchTickets } from '../../api/service.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { DataTable, type DataColumn } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { choiceLabel, formatDateTime } from '../../domain/partners.ts'
import {
  ticketCategoryOptions,
  ticketPriorityOptions,
  ticketStatusOptions,
  type Ticket,
  type TicketList,
  type TicketSummary,
} from '../../domain/service.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const columns: DataColumn<Ticket>[] = [
  {
    id: 'number',
    header: 'Ticketnummer',
    cell: (row) => (
      <Link to={`/kundenservice/${row.id}`} className="font-semibold text-petrol">
        {row.ticket_number}
      </Link>
    ),
  },
  {
    id: 'subject',
    header: 'Betreff',
    cell: (row) => (
      <span>
        {row.subject}
        {row.is_overdue ? <Badge tone="critical">Überfällig</Badge> : null}
        {row.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
      </span>
    ),
  },
  { id: 'company', header: 'Vertriebspartner', cell: (row) => row.company_name },
  { id: 'contact', header: 'Kontaktperson', cell: (row) => row.contact_name ?? 'Keine' },
  { id: 'category', header: 'Kategorie', cell: (row) => choiceLabel(ticketCategoryOptions, row.category) },
  { id: 'priority', header: 'Priorität', cell: (row) => choiceLabel(ticketPriorityOptions, row.priority) },
  { id: 'status', header: 'Status', cell: (row) => choiceLabel(ticketStatusOptions, row.status) },
  { id: 'owner', header: 'Zuständige Person', cell: (row) => row.account_owner ?? 'Nicht zugewiesen' },
  { id: 'created', header: 'Erstellungsdatum', cell: (row) => formatDateTime(row.created_at) },
  { id: 'updated', header: 'Letzte Aktualisierung', cell: (row) => formatDateTime(row.updated_at) },
]

function SummaryStrip() {
  const [summary, setSummary] = useState<TicketSummary | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    void fetchTicketSummary()
      .then((result) => {
        if (active) setSummary(result)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
    return () => {
      active = false
    }
  }, [])

  if (failed) {
    return <EmptyState compact title="Kennzahlen nicht verfügbar" description="Die Service-Tickets konnten nicht gelesen werden." />
  }
  if (!summary) return <LoadingState label="Kennzahlen werden geladen" />

  return (
    <div className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-4">
          <h2 className="text-sm font-semibold">Offene Tickets</h2>
          <p className="mt-2 text-2xl font-semibold">{summary.open_count}</p>
        </Card>
        <Card className="p-4">
          <h2 className="text-sm font-semibold">Kritische Tickets</h2>
          <p className="mt-2 text-2xl font-semibold">{summary.critical_count}</p>
        </Card>
        <Card className="p-4">
          <h2 className="text-sm font-semibold">Gelöste und geschlossene Tickets</h2>
          <p className="mt-2 text-2xl font-semibold">{summary.resolved_count}</p>
        </Card>
        <Card className="p-4">
          <h2 className="text-sm font-semibold">Bearbeitungsdauer</h2>
          {summary.duration_sample === 0 ? (
            <p className="mt-2 text-sm leading-6 text-muted">Noch kein Ticket mit dokumentiertem Abschluss. Es wird kein Mittelwert angezeigt.</p>
          ) : (
            <p className="mt-2 text-2xl font-semibold">{summary.average_hours} h</p>
          )}
          <p className="mt-2 text-sm leading-6 text-muted">{summary.duration_definition}</p>
        </Card>
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <CountList title="Nach Kategorie" options={ticketCategoryOptions} counts={summary.by_category} />
        <CountList title="Nach Priorität" options={ticketPriorityOptions} counts={summary.by_priority} />
        <CountList title="Nach Status" options={ticketStatusOptions} counts={summary.by_status} />
      </div>
    </div>
  )
}

function CountList({ title, options, counts }: { title: string; options: { value: string; label: string }[]; counts: Record<string, number> }) {
  const rows = options.filter((option) => (counts[option.value] ?? 0) > 0)
  return (
    <Card className="p-4">
      <h2 className="text-sm font-semibold">{title}</h2>
      {rows.length === 0 ? (
        <p className="mt-2 text-sm text-muted">Keine Tickets in dieser Auswertung.</p>
      ) : (
        <ul className="mt-2 grid gap-1 text-sm">
          {rows.map((option) => (
            <li key={option.value} className="flex justify-between gap-3">
              <span>{option.label}</span>
              <span className="font-semibold">{counts[option.value]}</span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

export function TicketListPage() {
  usePageTitle('Kundenservice')
  const [params, setParams] = useSearchParams()
  const queryKey = params.toString()
  const [data, setData] = useState<TicketList | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)

  useEffect(() => {
    let active = true
    const current = new URLSearchParams(queryKey)
    const page = Number(current.get('seite') ?? '1')
    void fetchTickets({
      q: current.get('q') ?? '',
      status: current.get('status') ?? '',
      priority: current.get('prioritaet') ?? '',
      category: current.get('kategorie') ?? '',
      accountOwner: current.get('betreuung') ?? '',
      scope: current.get('ansicht') ?? '',
      sort: current.get('sort') ?? 'updated_at',
      direction: current.get('richtung') ?? 'desc',
      page: Number.isInteger(page) && page > 0 ? page : 1,
    })
      .then((list) => {
        if (!active) return
        setData(list)
        setError(null)
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(caught instanceof ApiError ? caught.message : 'Die Tickets konnten nicht geladen werden.')
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
          <h1 className="text-3xl font-semibold tracking-tight">Kundenservice</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Serviceanfragen und Reklamationen. Dokumentierte Lösungen erzeugen keine Ersatzlieferung und keine Gutschrift im ERP.
          </p>
        </div>
        <Link to="/kundenservice/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Neues Ticket erstellen
        </Link>
      </header>
      <SummaryStrip />
      <div className="grid gap-3 md:grid-cols-3">
        <Input label="Suche" hint="Ticketnummer, Betreff oder Unternehmen" value={params.get('q') ?? ''} onChange={(event) => assign({ q: event.target.value || null })} />
        <Select label="Ansicht" value={params.get('ansicht') ?? ''} onChange={(value) => assign({ ansicht: value || null })} options={[{ value: '', label: 'Alle Tickets' }, { value: 'open', label: 'Offene Tickets' }, { value: 'closed', label: 'Abgeschlossene Tickets' }, { value: 'overdue', label: 'Überfällige Tickets' }]} />
        <Select label="Status" value={params.get('status') ?? ''} onChange={(value) => assign({ status: value || null })} options={[{ value: '', label: 'Alle Status' }, ...ticketStatusOptions]} />
        <Select label="Priorität" value={params.get('prioritaet') ?? ''} onChange={(value) => assign({ prioritaet: value || null })} options={[{ value: '', label: 'Alle Prioritäten' }, ...ticketPriorityOptions]} />
        <Select label="Kategorie" value={params.get('kategorie') ?? ''} onChange={(value) => assign({ kategorie: value || null })} options={[{ value: '', label: 'Alle Kategorien' }, ...ticketCategoryOptions]} />
        <Input label="Zuständige Person" value={params.get('betreuung') ?? ''} onChange={(event) => assign({ betreuung: event.target.value || null })} />
        <Select label="Sortierung" value={params.get('sort') ?? 'updated_at'} onChange={(value) => assign({ sort: value === 'updated_at' ? null : value })} options={[{ value: 'updated_at', label: 'Letzte Aktualisierung' }, { value: 'created_at', label: 'Erstellungsdatum' }, { value: 'priority', label: 'Priorität' }]} />
        <Select label="Richtung" value={params.get('richtung') ?? 'desc'} onChange={(value) => assign({ richtung: value === 'desc' ? null : value })} options={[{ value: 'desc', label: 'Absteigend' }, { value: 'asc', label: 'Aufsteigend' }]} />
      </div>
      {error ? <ErrorState title="Tickets nicht geladen" description={error} /> : null}
      {pending && !data ? <LoadingState label="Tickets werden geladen" /> : null}
      {data ? (
        <DataTable caption="Service-Tickets" columns={columns} rows={data.items} rowKey={(row) => row.id} empty={<EmptyState title="Keine Tickets" description="Für diesen Filter sind keine Service-Tickets gespeichert." />} />
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
