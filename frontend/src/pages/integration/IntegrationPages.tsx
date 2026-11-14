import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import {
  downloadSyncCsv,
  fetchConflicts,
  fetchIntegrationStatus,
  fetchSyncJob,
  fetchSyncJobs,
  previewSync,
  reviewConflict,
  runSync,
  saveIntegrationIntervals,
  saveIntegrationMode,
  testIntegration,
  type IntegrationStatus,
  type SyncConflict,
  type SyncJob,
  type SyncPreview,
} from '../../api/integration.ts'
import { ApiError } from '../../api/auth.ts'
import { useAuth } from '../../auth.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Card } from '../../components/ui/Card.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { formatDateTime } from '../../domain/partners.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const KINDS = [
  { id: 'produkte', label: 'Produktkatalog' },
  { id: 'kunden', label: 'Kundenstammdaten' },
  { id: 'bestellstatus', label: 'Bestellstatus' },
]

function messageOf(caught: unknown) {
  return caught instanceof ApiError ? caught.message : 'Die Aktion ist fehlgeschlagen.'
}

export function IntegrationOverviewPage() {
  usePageTitle('ERP-Integration')
  const { can } = useAuth()
  const [status, setStatus] = useState<IntegrationStatus | null>(null)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [customers, setCustomers] = useState('0')
  const [products, setProducts] = useState('0')
  const [statuses, setStatuses] = useState('0')

  function load() {
    return fetchIntegrationStatus()
      .then((next) => {
        setStatus(next)
        setCustomers(String(next.customers_interval_minutes))
        setProducts(String(next.products_interval_minutes))
        setStatuses(String(next.status_interval_minutes))
      })
      .catch((caught: unknown) => setError(messageOf(caught)))
  }

  useEffect(() => {
    void load()
  }, [])

  if (!status && !error) return <LoadingState label="Integration wird geladen" />
  if (!status) return <ErrorState title="Integration nicht verfügbar" description={error} />

  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">ERP-Integration</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          Das Mock-ERP ist eine lokale Testumgebung mit fiktiven Daten. Es ist keine Verbindung zum ERP des Liechtensteiner Brauhauses.
        </p>
      </header>
      <nav className="flex flex-wrap gap-3 text-sm font-semibold">
        <Link to="/integration/vorschau" className="text-petrol">Vorschau</Link>
        <Link to="/integration/laeufe" className="text-petrol">Synchronisationen</Link>
        <Link to="/integration/konflikte" className="text-petrol">Konflikte</Link>
      </nav>
      {error ? <ErrorState title="Hinweis" description={error} /> : null}
      {info ? <p className="text-sm text-petrol">{info}</p> : null}
      <div className="grid gap-3 sm:grid-cols-3">
        <Card className="p-4"><p className="text-sm text-muted">Modus</p><p className="mt-1 font-semibold">{status.mode_label}</p></Card>
        <Card className="p-4"><p className="text-sm text-muted">Verbindung</p><p className="mt-1 font-semibold">{status.connection_ok === null ? 'Nicht geprüft' : status.connection_ok ? 'Test erfolgreich' : 'Test fehlgeschlagen'}</p></Card>
        <Card className="p-4"><p className="text-sm text-muted">Offene Konflikte</p><p className="mt-1 font-semibold">{status.open_conflicts}</p></Card>
      </div>
      <Card className="grid gap-2 p-4 text-sm">
        <p>Letzte erfolgreiche Synchronisation: {status.last_success_at ? formatDateTime(status.last_success_at) : 'Keine'}</p>
        <p>Letzte fehlgeschlagene Synchronisation: {status.last_failure_at ? formatDateTime(status.last_failure_at) : 'Keine'}</p>
        <p>Synchronisierte Referenzen: {status.synced_records}</p>
        <p>Quelle: {status.source_label}</p>
        <p>Automatische Bestellübertragung: ausgeschaltet</p>
      </Card>
      <Card className="p-4">
        <h2 className="font-semibold">Führende Daten</h2>
        <ul className="mt-2 grid gap-1 text-sm leading-6">
          {status.leadership.map((line) => <li key={line}>{line}</li>)}
        </ul>
      </Card>
      {can('integration.configure') ? (
        <Card className="grid gap-3 p-4">
          <h2 className="font-semibold">Verbindungskonfiguration</h2>
          <div className="flex flex-wrap gap-2">
            <Button variant={status.mode === 'nicht_konfiguriert' ? 'primary' : 'secondary'} onClick={() => void saveIntegrationMode('nicht_konfiguriert').then(setStatus).catch((caught: unknown) => setError(messageOf(caught)))}>Nicht konfiguriert</Button>
            <Button variant={status.mode === 'mock' ? 'primary' : 'secondary'} onClick={() => void saveIntegrationMode('mock').then(setStatus).catch((caught: unknown) => setError(messageOf(caught)))}>Mock-ERP</Button>
            <Button variant="secondary" disabled title="Erst verfügbar, wenn ein HTTPS-Connector registriert ist" onClick={() => void saveIntegrationMode('extern').catch((caught: unknown) => setError(messageOf(caught)))}>Externes ERP gesperrt</Button>
          </div>
          <p className="text-sm text-muted">Externes ERP lässt sich erst aktivieren, wenn ein Connector und eine gültige HTTPS-Konfiguration vorhanden sind. Beides fehlt.</p>
          {can('integration.sync') ? (
            <Button onClick={() => void testIntegration().then((job) => { setInfo(job.message); return load() }).catch((caught: unknown) => setError(messageOf(caught)))}>Verbindung testen</Button>
          ) : null}
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="grid gap-1 text-sm font-semibold">Kunden, Minuten<input className="border border-line px-3 py-2 font-normal" value={customers} onChange={(event) => setCustomers(event.target.value)} /></label>
            <label className="grid gap-1 text-sm font-semibold">Produkte, Minuten<input className="border border-line px-3 py-2 font-normal" value={products} onChange={(event) => setProducts(event.target.value)} /></label>
            <label className="grid gap-1 text-sm font-semibold">Status, Minuten<input className="border border-line px-3 py-2 font-normal" value={statuses} onChange={(event) => setStatuses(event.target.value)} /></label>
          </div>
          <Button variant="secondary" onClick={() => void saveIntegrationIntervals({ customers_interval_minutes: Number(customers) || 0, products_interval_minutes: Number(products) || 0, status_interval_minutes: Number(statuses) || 0 }).then(setStatus).catch((caught: unknown) => setError(messageOf(caught)))}>Intervalle speichern</Button>
          <p className="text-sm text-muted">0 schaltet den Hintergrundlauf aus. Die Läufe laufen im Serverprozess, unabhängig vom Browser.</p>
        </Card>
      ) : null}
    </div>
  )
}

export function IntegrationPreviewPage() {
  usePageTitle('Synchronisationsvorschau')
  const { can } = useAuth()
  const [kind, setKind] = useState('produkte')
  const [preview, setPreview] = useState<SyncPreview | null>(null)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')

  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <header>
        <h1 className="text-3xl font-semibold">Synchronisationsvorschau</h1>
        <p className="mt-2 text-sm text-muted">Der Dry-Run verändert keine CRM-Daten.</p>
      </header>
      <div className="flex flex-wrap gap-2">
        {KINDS.map((item) => (
          <Button key={item.id} variant={kind === item.id ? 'primary' : 'secondary'} onClick={() => setKind(item.id)}>{item.label}</Button>
        ))}
      </div>
      {can('integration.sync') ? (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => void previewSync(kind).then(setPreview).catch((caught: unknown) => setError(messageOf(caught)))}>Vorschau anzeigen</Button>
          <Button variant="secondary" onClick={() => void runSync(kind).then((job) => setInfo(`${job.status}: ${job.message}`)).catch((caught: unknown) => setError(messageOf(caught)))}>Synchronisation starten</Button>
        </div>
      ) : <p className="text-sm">Diese Rolle darf die Synchronisation nicht starten.</p>}
      {error ? <ErrorState title="Vorschau nicht verfügbar" description={error} /> : null}
      {info ? <p className="text-sm">{info}</p> : null}
      {preview ? (
        <Card className="grid gap-3 p-4 text-sm">
          <p>{preview.source_label}</p>
          <PreviewList title="Neu" rows={preview.new} />
          <PreviewList title="Zu aktualisieren" rows={preview.update} />
          <PreviewList title="Unverändert" rows={preview.unchanged} />
          <PreviewList title="Konflikte" rows={preview.conflicts} />
          <PreviewList title="Ungültig" rows={preview.invalid} />
        </Card>
      ) : null}
    </div>
  )
}

function PreviewList({ title, rows }: { title: string; rows: { external_key: string; label: string; detail: string }[] }) {
  return (
    <section>
      <h2 className="font-semibold">{title} ({rows.length})</h2>
      <ul className="mt-1 grid gap-1">
        {rows.map((row) => <li key={`${title}-${row.external_key}`}>{row.label} · {row.external_key}: {row.detail}</li>)}
      </ul>
    </section>
  )
}

export function IntegrationJobsPage() {
  usePageTitle('Synchronisationen')
  const [jobs, setJobs] = useState<SyncJob[] | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    void fetchSyncJobs().then(setJobs).catch((caught: unknown) => setError(messageOf(caught)))
  }, [])
  if (!jobs && !error) return <LoadingState label="Läufe werden geladen" />
  if (!jobs) return <ErrorState title="Läufe nicht verfügbar" description={error} />
  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <h1 className="text-3xl font-semibold">Synchronisationen</h1>
      <Card className="overflow-x-auto p-4">
        <table className="w-full text-left text-sm">
          <thead>
            <tr className="text-xs tracking-wide text-muted uppercase">
              <th className="py-2">Start</th><th>Art</th><th>Status</th><th>Verarbeitet</th><th>Erfolgreich</th><th>Fehler</th>
            </tr>
          </thead>
          <tbody>
            {jobs.map((job) => (
              <tr key={job.id} className="border-t border-line">
                <td className="py-2"><Link className="text-petrol" to={`/integration/laeufe/${job.id}`}>{formatDateTime(job.started_at)}</Link></td>
                <td>{job.kind}</td>
                <td>{job.status}</td>
                <td>{job.processed_count}</td>
                <td>{job.success_count}</td>
                <td>{job.failed_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {jobs.length === 0 ? <p className="text-sm text-muted">Noch keine Läufe.</p> : null}
      </Card>
    </div>
  )
}

export function IntegrationJobPage() {
  const { jobId = '' } = useParams()
  const [job, setJob] = useState<(SyncJob & { records: { id: string; external_key: string; action: string; message: string; crm_id: string | null }[] }) | null>(null)
  const [error, setError] = useState('')
  usePageTitle('Synchronisationsdetail')
  useEffect(() => {
    void fetchSyncJob(jobId).then(setJob).catch((caught: unknown) => setError(messageOf(caught)))
  }, [jobId])
  if (!job && !error) return <LoadingState label="Lauf wird geladen" />
  if (!job) return <ErrorState title="Lauf nicht verfügbar" description={error} />
  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-3xl font-semibold">Lauf {job.kind}</h1>
        <Button variant="secondary" onClick={() => void downloadSyncCsv(job.id)}>Protokoll exportieren</Button>
      </header>
      <Card className="grid gap-1 p-4 text-sm">
        <p>Status: {job.status}</p>
        <p>Start: {formatDateTime(job.started_at)}</p>
        <p>Ende: {job.finished_at ? formatDateTime(job.finished_at) : 'Offen'}</p>
        <p>Verarbeitet {job.processed_count}, erfolgreich {job.success_count}, fehlerhaft {job.failed_count}</p>
        <p>{job.message}</p>
      </Card>
      <Card className="p-4">
        <ul className="grid gap-2 text-sm">
          {job.records.map((record) => (
            <li key={record.id}>
              <span className="font-semibold">{record.action}</span> {record.external_key}: {record.message}
              {record.crm_id && record.external_key ? null : null}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}

export function IntegrationConflictsPage() {
  usePageTitle('Synchronisationskonflikte')
  const { can } = useAuth()
  const [rows, setRows] = useState<SyncConflict[] | null>(null)
  const [error, setError] = useState('')
  function load() {
    return fetchConflicts().then(setRows).catch((caught: unknown) => setError(messageOf(caught)))
  }
  useEffect(() => {
    void load()
  }, [])
  if (!rows && !error) return <LoadingState label="Konflikte werden geladen" />
  if (!rows) return <ErrorState title="Konflikte nicht verfügbar" description={error} />
  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <h1 className="text-3xl font-semibold">Konflikte</h1>
      <p className="text-sm text-muted">Abweichende Stammdaten werden nicht automatisch überschrieben.</p>
      {rows.map((row) => (
        <Card key={row.id} className="grid gap-2 p-4 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <Badge tone={row.status === 'offen' ? 'warning' : 'neutral'}>{row.status}</Badge>
            <span className="font-semibold">{row.external_key}</span>
          </div>
          <p>{row.message}</p>
          <p>CRM: {row.crm_value || 'leer'} · Extern: {row.external_value || 'leer'}</p>
          {row.crm_id && row.entity_type === 'partner' ? <Link className="text-petrol" to={`/vertriebspartner/${row.crm_id}`}>Partner öffnen</Link> : null}
          {row.crm_id && row.entity_type === 'produkt' ? <Link className="text-petrol" to={`/produkte/${row.crm_id}/bearbeiten`}>Produkt öffnen</Link> : null}
          {can('integration.conflicts') && row.status === 'offen' ? (
            <Button variant="secondary" onClick={() => void reviewConflict(row.id).then(() => load())}>Als geprüft markieren</Button>
          ) : null}
        </Card>
      ))}
      {rows.length === 0 ? <p className="text-sm text-muted">Keine Konflikte.</p> : null}
    </div>
  )
}
