import { useEffect, useState } from 'react'
import { downloadReport, fetchReport, type ReportPayload, type ReportQuery } from '../../api/reports.ts'
import { ApiError } from '../../api/auth.ts'
import { ReportChart, formatKpi } from '../../components/reporting/ReportChart.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { useAuth } from '../../auth.tsx'
import { usePageTitle } from '../../usePageTitle.ts'

const SECTIONS = [
  { id: 'overview', label: 'Gesamtübersicht', permission: 'reports.overview' },
  { id: 'sales', label: 'Vertrieb', permission: 'reports.sales' },
  { id: 'partners', label: 'Vertriebspartner', permission: 'reports.partners' },
  { id: 'orders', label: 'Bestellungen', permission: 'reports.orders' },
  { id: 'service', label: 'Kundenservice', permission: 'reports.service' },
  { id: 'marketing', label: 'Marketing', permission: 'reports.marketing' },
  { id: 'work', label: 'Aktivitäten und Aufgaben', permission: 'reports.work' },
  { id: 'festivals', label: 'Festmanagement', permission: 'reports.festivals' },
]

function initialQuery(): ReportQuery {
  const end = new Date()
  const start = new Date(end)
  start.setDate(start.getDate() - 365)
  return {
    dateFrom: start.toISOString().slice(0, 10),
    dateTo: end.toISOString().slice(0, 10),
    partnerId: '',
    region: '',
    partnerType: '',
    owner: '',
  }
}

export function ReportingPage() {
  usePageTitle('Reporting')
  const { can } = useAuth()
  const tabs = SECTIONS.filter((item) => can(item.permission))
  const [section, setSection] = useState(tabs[0]?.id ?? 'overview')
  const [draft, setDraft] = useState<ReportQuery>(initialQuery)
  const [query, setQuery] = useState<ReportQuery>(initialQuery)
  const [report, setReport] = useState<ReportPayload | null>(null)
  const [error, setError] = useState('')
  const [exportError, setExportError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    let active = true
    void fetchReport(query)
      .then((payload) => {
        if (!active) return
        setReport(payload)
        setError('')
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Der Bericht konnte nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [query])

  if (tabs.length === 0) {
    return <ErrorState title="Reporting nicht verfügbar" description="Für diese Rolle ist kein Bericht freigegeben." />
  }

  const active = tabs.some((item) => item.id === section) ? section : tabs[0].id
  const kpis = report?.kpis.filter((item) => item.section === active) ?? []
  const charts = report?.charts.filter((item) => item.section === active) ?? []
  const tables = report?.tables.filter((item) => item.section === active) ?? []

  async function exportAs(format: 'csv' | 'xlsx' | 'pdf') {
    setPending(true)
    setExportError('')
    try {
      await downloadReport({ ...query, section: active }, format)
    } catch (caught) {
      setExportError(caught instanceof ApiError ? caught.message : 'Der Export wurde abgelehnt.')
    } finally {
      setPending(false)
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Reporting</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          Kennzahlen aus den gespeicherten CRM-Daten. Der Bestellwert ist der CRM-Bestellwert und nicht fakturierter ERP-Umsatz.
        </p>
      </header>
      <form
        className="grid gap-3 border border-line bg-card p-4 md:grid-cols-3"
        onSubmit={(event) => {
          event.preventDefault()
          setQuery(draft)
        }}
      >
        <label className="grid gap-1 text-sm font-semibold">
          Von
          <input className="border border-line bg-card px-3 py-2 font-normal" type="date" value={draft.dateFrom} onChange={(event) => setDraft({ ...draft, dateFrom: event.target.value })} />
        </label>
        <label className="grid gap-1 text-sm font-semibold">
          Bis
          <input className="border border-line bg-card px-3 py-2 font-normal" type="date" value={draft.dateTo} onChange={(event) => setDraft({ ...draft, dateTo: event.target.value })} />
        </label>
        <Select
          label="Vertriebspartner"
          value={draft.partnerId}
          onChange={(value) => setDraft({ ...draft, partnerId: value })}
          options={[{ value: '', label: 'Alle' }, ...(report?.options.partners ?? []).map((item) => ({ value: item.id, label: item.label }))]}
        />
        <Select
          label="Region"
          value={draft.region}
          onChange={(value) => setDraft({ ...draft, region: value })}
          options={[{ value: '', label: 'Alle' }, ...(report?.options.regions ?? []).map((item) => ({ value: item, label: item }))]}
        />
        <Select
          label="Partnertyp"
          value={draft.partnerType}
          onChange={(value) => setDraft({ ...draft, partnerType: value })}
          options={[{ value: '', label: 'Alle' }, ...(report?.options.partner_types ?? []).map((item) => ({ value: item, label: item }))]}
        />
        <Select
          label="Zuständige Mitarbeiter:in"
          value={draft.owner}
          onChange={(value) => setDraft({ ...draft, owner: value })}
          options={[{ value: '', label: 'Alle' }, ...(report?.options.owners ?? []).map((item) => ({ value: item, label: item }))]}
        />
        <div className="md:col-span-3">
          <Button type="submit">Filter anwenden</Button>
        </div>
      </form>
      <div role="tablist" aria-label="Berichtsbereiche" className="flex flex-wrap gap-1 border-b border-line">
        {tabs.map((item) => (
          <button
            key={item.id}
            type="button"
            role="tab"
            aria-selected={item.id === active}
            className={item.id === active ? 'border-b-2 border-petrol px-3 py-2 text-sm font-semibold' : 'px-3 py-2 text-sm text-muted'}
            onClick={() => setSection(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>
      {error ? <ErrorState title="Bericht nicht geladen" description={error} /> : null}
      {!report && !error ? <LoadingState label="Bericht wird berechnet" /> : null}
      {report ? (
        <>
          <p className="text-sm leading-6 text-muted">
            Zeitraum {report.period_from} bis {report.period_to}. Quelle: {report.source}
          </p>
          <ul className="grid gap-2">
            {report.notices.map((notice) => (
              <li key={notice} className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6">
                {notice}
              </li>
            ))}
          </ul>
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {kpis.map((kpi) => (
              <article key={kpi.key} className="border border-line bg-card p-4">
                <h2 className="text-sm font-semibold">{kpi.label}</h2>
                <p className="mt-2 text-2xl font-semibold">{formatKpi(kpi.value, kpi.unit)}</p>
                <p className="mt-2 text-sm leading-6 text-muted">{kpi.note}</p>
              </article>
            ))}
          </div>
          <div className="grid gap-4 xl:grid-cols-2">
            {charts.map((chart) => (
              <ReportChart key={chart.key} chart={chart} />
            ))}
          </div>
          {tables.map((table) => (
            <section key={table.key} className="border border-line bg-card p-4">
              <h3 className="text-base font-semibold">{table.title}</h3>
              <p className="mt-1 text-sm leading-6 text-muted">{table.note}</p>
              <div className="mt-3 overflow-x-auto">
                <table className="w-full min-w-[40rem] text-sm">
                  <caption className="sr-only">{table.title}</caption>
                  <thead>
                    <tr className="border-b border-line text-left">
                      {table.columns.map((column) => (
                        <th key={column.key} className="py-2 pr-3 font-semibold">
                          {column.label}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.length === 0 ? (
                      <tr>
                        <td className="py-3" colSpan={table.columns.length}>
                          Keine Zeilen im Filter.
                        </td>
                      </tr>
                    ) : (
                      table.rows.map((row, index) => (
                        <tr key={`${table.key}-${index}`} className="border-b border-line">
                          {table.columns.map((column) => (
                            <td key={column.key} className="py-2 pr-3">
                              {row[column.key]}
                            </td>
                          ))}
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </section>
          ))}
          {can('reports.export') ? (
            <div className="flex flex-wrap gap-2">
              <Button disabled={pending} onClick={() => void exportAs('xlsx')}>
                Excel exportieren
              </Button>
              <Button variant="secondary" disabled={pending} onClick={() => void exportAs('csv')}>
                CSV exportieren
              </Button>
              <Button variant="secondary" disabled={pending} onClick={() => void exportAs('pdf')}>
                PDF exportieren
              </Button>
            </div>
          ) : null}
          {exportError ? <p className="text-sm text-critical">{exportError}</p> : null}
          <p className="text-sm leading-6 text-muted">
            Exporte enthalten den gefilterten Bereich, den Zeitraum, die Filter, das Erstellungsdatum und die Datenquelle.
            Im PDF stehen die Diagramme als Wertetabelle, nicht als Bild.
          </p>
        </>
      ) : null}
    </div>
  )
}
