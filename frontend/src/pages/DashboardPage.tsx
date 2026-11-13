import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { fetchActivities, fetchTaskSummary, fetchTasks } from '../api/crm.ts'
import { fetchPartnerSummary } from '../api/partners.ts'
import { Badge } from '../components/ui/Badge.tsx'
import { Card } from '../components/ui/Card.tsx'
import { DataTable, type DataColumn } from '../components/ui/DataTable.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { LoadingState } from '../components/ui/LoadingState.tsx'
import { labelOf, taskPriorityOptions, type Activity, type Task, type TaskSummary } from '../domain/crm.ts'
import { formatDateTime, type PartnerSummary } from '../domain/partners.ts'
import { navigation, type NavItem } from '../navigation.ts'
import { usePageTitle } from '../usePageTitle.ts'

const activityColumns: DataColumn<Activity>[] = [
  { id: 'when', header: 'Zeitpunkt', cell: (row) => formatDateTime(row.occurred_at) },
  { id: 'area', header: 'Bereich', cell: (row) => row.company_name ?? row.contact_name ?? 'Ohne Zuordnung' },
  {
    id: 'text',
    header: 'Beschreibung',
    cell: (row) => (
      <Link to="/aktivitaeten" className="font-semibold text-petrol">
        {row.title}
      </Link>
    ),
  },
]

const taskColumns: DataColumn<Task>[] = [
  {
    id: 'task',
    header: 'Aufgabe',
    cell: (row) => (
      <Link to={`/aufgaben/${row.id}/bearbeiten`} className={row.is_overdue ? 'font-semibold text-critical' : 'font-semibold text-petrol'}>
        {row.title}
      </Link>
    ),
  },
  {
    id: 'due',
    header: 'Fällig',
    cell: (row) => (
      <span className={row.is_overdue ? 'font-semibold text-critical' : undefined}>
        {formatDateTime(row.due_at)}
        {row.is_overdue ? ' · Überfällig' : ''}
      </span>
    ),
  },
  { id: 'priority', header: 'Priorität', cell: (row) => labelOf(taskPriorityOptions, row.priority) },
]

const kpis = ['Offene Verkaufschancen', 'Bestellungen', 'Offene Service-Tickets']

function summaryText(summary: PartnerSummary): string {
  if (summary.active === 0) {
    return 'In der Datenbank sind keine aktiven Vertriebspartner erfasst.'
  }
  if (summary.active === summary.active_demo) {
    return 'Ausschliesslich gekennzeichnete Testdaten, keine echten Kundenbeziehungen.'
  }
  if (summary.active_demo > 0) {
    return `Darin enthaltene Testdaten: ${summary.active_demo}.`
  }
  return 'Aktive Partner aus der Datenbank, ohne archivierte Datensätze.'
}

function accessBadge(item: NavItem): { tone: 'petrol' | 'success' | 'warning'; label: string } {
  if (item.id === 'settings') {
    return { tone: 'petrol', label: 'Systemstatus' }
  }
  if (item.phase === 'available') {
    return { tone: 'success', label: 'Verfügbar' }
  }
  return { tone: 'warning', label: 'In Entwicklung' }
}

function ActivePartnersCard() {
  const [summary, setSummary] = useState<PartnerSummary | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    void fetchPartnerSummary()
      .then((result) => {
        if (active) {
          setSummary(result)
        }
      })
      .catch(() => {
        if (active) {
          setFailed(true)
        }
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <Card className="p-4">
      <h3 className="text-sm font-semibold">Aktive Vertriebspartner</h3>
      {summary ? (
        <>
          <p className="mt-3 text-3xl font-semibold tracking-tight">{summary.active}</p>
          <p className="mt-2 text-sm leading-6 text-muted">{summaryText(summary)}</p>
          <Link to="/vertriebspartner?status=aktiv" className="mt-3 inline-flex text-sm font-semibold text-petrol">
            Zur Partnerliste
          </Link>
        </>
      ) : failed ? (
        <EmptyState
          compact
          title="Kennzahl nicht verfügbar"
          description="Die Partnerdatenbank konnte nicht gelesen werden."
        />
      ) : (
        <LoadingState label="Kennzahl wird geladen" />
      )}
    </Card>
  )
}

function TaskSignals() {
  const [summary, setSummary] = useState<TaskSummary | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    void fetchTaskSummary()
      .then((result) => {
        if (active) {
          setSummary(result)
        }
      })
      .catch(() => {
        if (active) {
          setFailed(true)
        }
      })
    return () => {
      active = false
    }
  }, [])

  if (failed) {
    return <EmptyState compact title="Aufgaben nicht verfügbar" description="Die Aufgaben konnten nicht gelesen werden." />
  }
  if (!summary) {
    return <LoadingState label="Aufgabenhinweise werden geladen" />
  }

  const note =
    summary.open > 0 && summary.open === summary.open_demo
      ? 'Die offenen Aufgaben sind ausschliesslich gekennzeichnete Testdaten.'
      : 'Gezählt werden gespeicherte Aufgaben. Eine automatische Benachrichtigung folgt später.'

  return (
    <div className="grid gap-3">
      <div className="grid gap-3 sm:grid-cols-3">
        <Signal label="Überfällig" value={summary.overdue} to="/aufgaben?faellig=overdue" />
        <Signal label="Bald fällig" value={summary.due_soon} to="/aufgaben?faellig=soon" />
        <Signal label="Dringend" value={summary.urgent} to="/aufgaben?faellig=urgent" />
      </div>
      <p className="text-sm leading-6 text-muted">{note}</p>
    </div>
  )
}

function Signal({ label, value, to }: { label: string; value: number; to: string }) {
  return (
    <Link to={to} className="border border-line px-4 py-3 hover:border-petrol">
      <p className="text-sm font-semibold">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </Link>
  )
}

function RecentActivities() {
  const [rows, setRows] = useState<Activity[] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    void fetchActivities({ page: 1 })
      .then((result) => {
        if (active) {
          setRows(result.items.slice(0, 5))
        }
      })
      .catch(() => {
        if (active) {
          setFailed(true)
        }
      })
    return () => {
      active = false
    }
  }, [])

  if (failed) {
    return <EmptyState compact title="Aktivitäten nicht verfügbar" description="Die Chronik konnte nicht gelesen werden." />
  }
  if (!rows) {
    return <LoadingState label="Aktivitäten werden geladen" />
  }
  return (
    <DataTable
      caption="Letzte Aktivitäten"
      columns={activityColumns}
      rows={rows}
      rowKey={(row) => row.id}
      empty={<EmptyState compact title="Keine Aktivitäten" description="Es sind noch keine Gespräche oder Notizen gespeichert." />}
    />
  )
}

function OpenTasks() {
  const [rows, setRows] = useState<Task[] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    void fetchTasks({ q: '', status: '', priority: '', accountOwner: '', partnerId: '', contactId: '', due: 'open', page: 1 })
      .then((result) => {
        if (active) {
          setRows(result.items.slice(0, 5))
        }
      })
      .catch(() => {
        if (active) {
          setFailed(true)
        }
      })
    return () => {
      active = false
    }
  }, [])

  if (failed) {
    return <EmptyState compact title="Aufgaben nicht verfügbar" description="Die Aufgaben konnten nicht gelesen werden." />
  }
  if (!rows) {
    return <LoadingState label="Aufgaben werden geladen" />
  }
  return (
    <DataTable
      caption="Anstehende Aufgaben"
      columns={taskColumns}
      rows={rows}
      rowKey={(row) => row.id}
      empty={<EmptyState compact title="Keine Aufgaben" description="Es sind keine offenen Aufgaben gespeichert." />}
    />
  )
}

export function DashboardPage() {
  usePageTitle('Dashboard')
  const modules = navigation.filter((item) => item.id !== 'dashboard')

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header>
        <p className="text-sm font-semibold text-petrol">Willkommen</p>
        <h1 className="mt-1 text-3xl font-semibold tracking-tight">Dashboard</h1>
        <p className="mt-2 max-w-3xl text-base leading-7 text-muted">
          Zentrale Arbeitsfläche für Vertrieb, Partnerbetreuung und Kundenservice
        </p>
      </header>

      <section aria-labelledby="kpi-title" className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <h2 id="kpi-title" className="sr-only">
          Kennzahlen
        </h2>
        <ActivePartnersCard />
        {kpis.map((title) => (
          <Card key={title} className="p-4">
            <h3 className="text-sm font-semibold">{title}</h3>
            <EmptyState
              compact
              title="Keine Werte"
              description="Für diese Kennzahl liegen noch keine Datenbankwerte vor."
            />
          </Card>
        ))}
      </section>

      <Card className="p-4">
        <h2 className="text-base font-semibold">Aufgabenhinweise</h2>
        <div className="mt-3">
          <TaskSignals />
        </div>
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <h2 className="border-b border-line px-4 py-3 text-base font-semibold">Letzte Aktivitäten</h2>
          <RecentActivities />
        </Card>
        <Card>
          <h2 className="border-b border-line px-4 py-3 text-base font-semibold">Anstehende Aufgaben</h2>
          <OpenTasks />
        </Card>
      </div>

      <section aria-labelledby="quick-title">
        <h2 id="quick-title" className="text-base font-semibold">
          Schnellzugriff
        </h2>
        <ul className="mt-3 grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {modules.map((item) => {
            const badge = accessBadge(item)
            return (
            <li key={item.id}>
              <Link to={item.path} className="block h-full focus-visible:outline-petrol">
                <Card className="h-full p-4 hover:border-petrol">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="font-semibold">{item.label}</h3>
                    <Badge tone={badge.tone}>{badge.label}</Badge>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-muted">{item.summary}</p>
                </Card>
              </Link>
            </li>
            )
          })}
        </ul>
      </section>

      <Card className="p-4">
        <h2 className="text-base font-semibold">Diagramme</h2>
        <div className="mt-3 border border-dashed border-line bg-cream px-4 py-10">
          <EmptyState
            title="Diagramme folgen"
            description="Auswertungen werden ergänzt, sobald Verkaufs- und Servicedaten vorliegen."
          />
        </div>
      </Card>

      <Card className="border-t-2 border-t-gold p-4">
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-base font-semibold">Historische Ausgangslage</h2>
          <Badge tone="accent">Keine Live-Daten</Badge>
        </div>
        <p className="mt-3 max-w-3xl text-sm leading-6 text-muted">
          Werte aus dem FHGR-Projekt-Case gehören ausschliesslich in diesen Bereich und sind von den Kennzahlen
          oben getrennt. Die freigegebenen Ausgangswerte sind in dieser Phase noch nicht hinterlegt.
        </p>
      </Card>
    </div>
  )
}
