import { useEffect, useState } from 'react'
import { fetchHealth, type HealthResult } from './api/health.ts'

function readServices(): Promise<[HealthResult, HealthResult]> {
  return Promise.all([fetchHealth('/api/health'), fetchHealth('/api/health/db')])
}

type Panel = {
  title: string
  path: string
  result: HealthResult | null
  detail: string
}

function statusLabel(result: HealthResult | null): string {
  if (result === null) {
    return 'Wird geprüft'
  }
  return result.ok ? 'Erreichbar' : 'Nicht erreichbar'
}

function statusTone(result: HealthResult | null): string {
  if (result === null) {
    return 'bg-copper'
  }
  return result.ok ? 'bg-moss' : 'bg-wine'
}

function StatusCard({ title, path, result, detail }: Panel) {
  return (
    <article className="border border-line bg-card px-6 py-5">
      <div className="flex items-center justify-between gap-4">
        <h2 className="font-display text-2xl">{title}</h2>
        <span className={`h-3 w-3 ${statusTone(result)}`} aria-hidden="true" />
      </div>
      <p className="mt-6 text-sm tracking-wide text-muted uppercase">{path}</p>
      <p className="mt-2 font-display text-3xl" role="status">
        {statusLabel(result)}
      </p>
      <p className="mt-4 max-w-sm text-sm leading-6 text-muted">{detail}</p>
    </article>
  )
}

export default function App() {
  const [api, setApi] = useState<HealthResult | null>(null)
  const [database, setDatabase] = useState<HealthResult | null>(null)
  const [checkedAt, setCheckedAt] = useState<Date | null>(null)
  const [pending, setPending] = useState(true)

  useEffect(() => {
    let active = true
    void readServices().then(([apiResult, databaseResult]) => {
      if (!active) {
        return
      }
      setApi(apiResult)
      setDatabase(databaseResult)
      setCheckedAt(new Date())
      setPending(false)
    })
    return () => {
      active = false
    }
  }, [])

  async function refresh() {
    setPending(true)
    const [apiResult, databaseResult] = await readServices()
    setApi(apiResult)
    setDatabase(databaseResult)
    setCheckedAt(new Date())
    setPending(false)
  }

  const application = api?.ok ? api.application : undefined
  const checkedLabel = checkedAt
    ? checkedAt.toLocaleTimeString('de-LI', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : 'ausstehend'

  return (
    <div className="min-h-screen">
      <header className="border-b border-line">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-6 px-6 py-5">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center bg-ink font-display text-sm text-paper">
              HL
            </div>
            <div>
              <p className="font-display text-xl leading-none">HopLogic</p>
              <p className="mt-1 text-xs tracking-[0.22em] text-copper uppercase">BrauPartner</p>
            </div>
          </div>
          <p className="text-sm text-muted">Liechtensteiner Brauhaus</p>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-6 py-12">
        <p className="text-sm tracking-[0.16em] text-copper uppercase">Phase 1 · Systemstatus</p>
        <h1 className="mt-3 max-w-3xl font-display text-5xl leading-tight">Technische Grundlage</h1>
        <p className="mt-5 max-w-2xl text-lg leading-8 text-muted">
          {application ?? 'HopLogic BrauPartner'} verbindet die Oberfläche mit der API und PostgreSQL.
          Die Fachmodule des CRM bauen in den nächsten Phasen auf dieser Grundlage auf.
        </p>

        <div className="mt-10 grid gap-4 md:grid-cols-2">
          <StatusCard
            title="API"
            path="/api/health"
            result={api}
            detail="FastAPI nimmt Anfragen entgegen und liefert den Anwendungsnamen zurück."
          />
          <StatusCard
            title="Datenbank"
            path="/api/health/db"
            result={database}
            detail="SQLAlchemy führt eine Prüfabfrage auf PostgreSQL aus."
          />
        </div>

        <div className="mt-8 flex flex-wrap items-center gap-4">
          <button
            type="button"
            onClick={() => void refresh()}
            disabled={pending}
            className="border border-ink bg-ink px-4 py-2 text-sm text-paper disabled:cursor-wait disabled:opacity-60"
          >
            {pending ? 'Prüfung läuft' : 'Status aktualisieren'}
          </button>
          <p className="text-sm text-muted">Zuletzt geprüft: {checkedLabel}</p>
        </div>
      </main>

      <footer className="border-t border-line">
        <div className="mx-auto flex max-w-5xl flex-wrap justify-between gap-3 px-6 py-5 text-sm text-muted">
          <p>FHGR · Digital Relationship Management</p>
          <p>API-Dokumentation: Port 8000, Pfad /docs</p>
        </div>
      </footer>
    </div>
  )
}
