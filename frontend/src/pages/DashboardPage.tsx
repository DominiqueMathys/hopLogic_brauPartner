import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { fetchActivities, fetchTaskSummary, fetchTasks } from '../api/crm.ts'
import { fetchEngagementSummary, fetchNoticeSummary } from '../api/engagement.ts'
import { fetchPartnerSummary } from '../api/partners.ts'
import { fetchDealSummary, fetchOrderSummary } from '../api/sales.ts'
import { fetchSegments, fetchTicketSummary } from '../api/service.ts'
import { Badge } from '../components/ui/Badge.tsx'
import { Card } from '../components/ui/Card.tsx'
import { DataTable, type DataColumn } from '../components/ui/DataTable.tsx'
import { EmptyState } from '../components/ui/EmptyState.tsx'
import { LoadingState } from '../components/ui/LoadingState.tsx'
import { labelOf, taskPriorityOptions, type Activity, type Task, type TaskSummary } from '../domain/crm.ts'
import { formatDateTime, type PartnerSummary } from '../domain/partners.ts'
import { formatChf, type DealSummary, type OrderSummary } from '../domain/sales.ts'
import type { EngagementSummary } from '../domain/engagement.ts'
import type { Segment, TicketSummary } from '../domain/service.ts'
import { actorName } from '../lib/actor.ts'
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

function SalesKpis() {
  const [deals, setDeals] = useState<DealSummary | null>(null)
  const [orders, setOrders] = useState<OrderSummary | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    void Promise.all([fetchDealSummary(), fetchOrderSummary()])
      .then(([dealSummary, orderSummary]) => {
        if (!active) return
        setDeals(dealSummary)
        setOrders(orderSummary)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
    return () => {
      active = false
    }
  }, [])

  if (failed) {
    return <EmptyState compact title="Kennzahlen nicht verfügbar" description="Verkaufschancen und Bestellungen konnten nicht gelesen werden." />
  }
  if (!deals || !orders) {
    return <LoadingState label="Verkaufskennzahlen werden geladen" />
  }

  const dealNote =
    deals.open_count > 0 && deals.open_count === deals.open_demo
      ? 'Die offenen Verkaufschancen sind ausschliesslich gekennzeichnete Testdaten.'
      : 'Gezählt werden gespeicherte, nicht archivierte Deals.'
  const orderNote =
    orders.volume !== '0.00' && orders.volume === orders.volume_demo
      ? 'Das Bestellvolumen besteht ausschliesslich aus gekennzeichneten Testdaten.'
      : 'Entwürfe und stornierte Bestellungen zählen nicht zum Volumen.'

  return (
    <>
      <Metric title="Offene Verkaufschancen" value={String(deals.open_count)} note={dealNote} to="/verkaufschancen" />
      <Metric title="Erwarteter Pipeline-Wert" value={formatChf(deals.pipeline_value)} note="Summe aus Wert mal Phasenwahrscheinlichkeit." to="/verkaufschancen/pipeline" />
      <Metric title="Gewonnene Deals" value={`${deals.won_count} · ${formatChf(deals.won_value)}`} note="Abgeschlossene gewonnene Verkaufschancen." to="/verkaufschancen?abgeschlossen=1&phase=gewonnen" />
      <Metric title="Überfällige Verkaufschancen" value={String(deals.overdue_count)} note="Offene Deals mit Abschlussdatum vor heute." to="/verkaufschancen?ueberfaellig=1" />
      <Metric title="Bestellvolumen" value={formatChf(orders.volume)} note={orderNote} to="/bestellungen" />
      <Metric title="Neue Bestellungen" value={String(orders.new_count)} note="Eingereicht oder weitergeführt in den letzten 30 Tagen." to="/bestellungen" />
    </>
  )
}

function Metric({ title, value, note, to }: { title: string; value: string; note: string; to: string }) {
  return (
    <Card className="p-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <p className="mt-3 text-2xl font-semibold tracking-tight">{value}</p>
      <p className="mt-2 text-sm leading-6 text-muted">{note}</p>
      <Link to={to} className="mt-3 inline-flex text-sm font-semibold text-petrol">
        Anzeigen
      </Link>
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
      : 'Gezählt werden gespeicherte Aufgaben. Hinweise stehen im Benachrichtigungscenter für den gewählten Anzeigenamen.'

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

function ServiceSignals() {
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
    return <EmptyState compact title="Servicekennzahlen nicht verfügbar" description="Die Tickets konnten nicht gelesen werden." />
  }
  if (!summary) return <LoadingState label="Servicekennzahlen werden geladen" />

  return (
    <>
      <Metric title="Offene Reklamationen" value={String(summary.open_complaints)} note="Offene Tickets zu Lieferung oder Produktqualität." to="/kundenservice?ansicht=open" />
      <Metric title="Kritische Service-Tickets" value={String(summary.critical_count)} note="Offene Tickets mit Priorität kritisch." to="/kundenservice?prioritaet=kritisch&ansicht=open" />
      <Metric title="Überfällige Serviceaufgaben" value={String(summary.overdue_service_tasks)} note="Offene Aufgaben mit Ticketbezug, deren Fälligkeit vor jetzt liegt." to="/aufgaben?faellig=overdue&service=1" />
      <Metric title="Partner mit offenen Reklamationen" value={String(summary.partners_with_complaints)} note="Unterschiedliche Partner mit mindestens einer offenen Reklamation." to="/segmente" />
    </>
  )
}

function SegmentOverview() {
  const [items, setItems] = useState<Segment[] | null>(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    void fetchSegments()
      .then((result) => {
        if (active) setItems(result)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
    return () => {
      active = false
    }
  }, [])

  if (failed) return <EmptyState compact title="Segmente nicht verfügbar" description="Die Segmentdefinitionen konnten nicht gelesen werden." />
  if (!items) return <LoadingState label="Segmente werden geladen" />
  if (items.length === 0) return <EmptyState compact title="Keine Segmente" description="Es ist noch keine Segmentdefinition gespeichert." />

  return (
    <ul className="grid gap-2 sm:grid-cols-2">
      {items.map((segment) => (
        <li key={segment.id}>
          <Link to={`/segmente/${segment.id}`} className="flex items-center justify-between gap-3 border border-line px-4 py-3 hover:border-petrol">
            <span className="font-semibold">{segment.name}</span>
            <span className="text-sm">{segment.partner_count}</span>
          </Link>
        </li>
      ))}
    </ul>
  )
}

function EngagementSignals() {
  const [summary, setSummary] = useState<EngagementSummary | null>(null)
  const [unread, setUnread] = useState<number | null>(null)
  const [limited, setLimited] = useState(true)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let active = true
    const name = actorName()
    void Promise.all([fetchEngagementSummary(), fetchNoticeSummary(name)])
      .then(([engagement, notices]) => {
        if (!active) return
        setSummary(engagement)
        setUnread(notices.unread)
        setLimited(!name)
      })
      .catch(() => {
        if (active) setFailed(true)
      })
    return () => {
      active = false
    }
  }, [])

  if (failed) {
    return <EmptyState compact title="Betreuung nicht verfügbar" description="Kampagnen und Automatisierungen konnten nicht gelesen werden." />
  }
  if (!summary || unread === null) return <LoadingState label="Betreuungskennzahlen werden geladen" />

  return (
    <>
      <Metric title="Aktive Kampagnen" value={String(summary.active_campaigns)} note="Kampagnen mit Status aktiv." to="/kampagnen?status=aktiv" />
      <Metric title="Anstehende Betreuungsaufgaben" value={String(summary.care_tasks)} note="Offene Aufgaben aus Betreuung oder Automatisierung, deren Fälligkeit noch nicht vorbei ist." to="/aufgaben" />
      <Metric title="Partner ohne aktuellen Kontakt" value={String(summary.partners_without_contact)} note={`Kein dokumentierter Kontakt seit ${summary.contact_days} Tagen, nach der aktiven Betreuungsregel.`} to="/partnerbetreuung" />
      <Metric title="Überfällige Aufgaben" value={String(summary.overdue_tasks)} note="Offene Aufgaben mit Fälligkeit vor jetzt." to="/aufgaben?faellig=overdue" />
      <Metric
        title="Ungelesene Benachrichtigungen"
        value={limited ? '—' : String(unread)}
        note={limited ? 'Bis Phase 08 braucht es einen Anzeigenamen. Fremde Hinweise werden nicht gezählt.' : 'Gespeicherte ungelesene Hinweise für den Anzeigenamen dieser Sitzung.'}
        to="/benachrichtigungen"
      />
      <Metric title="Aktive Automatisierungen" value={String(summary.active_automations)} note="Regeln mit Status aktiv. Zeitregeln laufen auf dem Server." to="/automatisierungen" />
    </>
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
    void fetchTasks({ q: '', status: '', priority: '', accountOwner: '', partnerId: '', contactId: '', due: 'open', serviceOnly: false, page: 1 })
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
        <SalesKpis />
        <ServiceSignals />
        <EngagementSignals />
      </section>

      <Card className="p-4">
        <h2 className="text-base font-semibold">Partnersegmente</h2>
        <div className="mt-3">
          <SegmentOverview />
        </div>
      </Card>

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
            description="Grafische Auswertungen folgen später. Die Kennzahlen oben stammen aus den gespeicherten CRM-Daten."
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
