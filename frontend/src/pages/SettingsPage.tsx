import { useEffect, useState } from 'react'
import { fetchHealth, type HealthResult } from '../api/health.ts'
import { Button } from '../components/ui/Button.tsx'
import { Card } from '../components/ui/Card.tsx'
import { ErrorState } from '../components/ui/ErrorState.tsx'
import { LoadingState } from '../components/ui/LoadingState.tsx'
import { Select } from '../components/ui/Select.tsx'
import { StatusIndicator } from '../components/ui/StatusIndicator.tsx'
import { Tabs } from '../components/ui/Tabs.tsx'
import { useToast } from '../components/ui/toast-state.ts'
import { usePageTitle } from '../usePageTitle.ts'

type Check = {
  title: string
  path: string
  result: HealthResult | null
  failure: string
  success: string
}

function readServices(): Promise<[HealthResult, HealthResult]> {
  return Promise.all([fetchHealth('/api/health'), fetchHealth('/api/health/db')])
}

export function SettingsPage() {
  usePageTitle('Einstellungen')
  const { notify } = useToast()
  const [api, setApi] = useState<HealthResult | null>(null)
  const [database, setDatabase] = useState<HealthResult | null>(null)
  const [checkedAt, setCheckedAt] = useState<Date | null>(null)
  const [pending, setPending] = useState(true)
  const [focus, setFocus] = useState('all')

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
    if (!apiResult.ok || !databaseResult.ok) {
      notify({
        tone: 'critical',
        message: 'Die Systemprüfung ist fehlgeschlagen. Die Hinweise stehen beim jeweiligen Dienst.',
      })
    }
  }

  const checks: Check[] = [
    {
      title: 'API',
      path: '/api/health',
      result: api,
      failure: 'Die API antwortet nicht. Starten Sie den Backend-Dienst und aktualisieren Sie den Status.',
      success: api?.ok && api.application ? `Die API meldet «${api.application}».` : 'Die API antwortet.',
    },
    {
      title: 'Datenbank',
      path: '/api/health/db',
      result: database,
      failure: 'Die Datenbank antwortet nicht. Die Prüfabfrage auf PostgreSQL ist fehlgeschlagen.',
      success: 'Die Prüfabfrage auf PostgreSQL war erfolgreich.',
    },
  ]
  const visible = checks.filter((check) => focus === 'all' || (focus === 'api' && check.title === 'API') || (focus === 'database' && check.title === 'Datenbank'))
  const checkedLabel = checkedAt
    ? checkedAt.toLocaleTimeString('de-LI', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    : 'ausstehend'

  return (
    <div className="mx-auto max-w-4xl">
      <h1 className="text-3xl font-semibold tracking-tight">Einstellungen</h1>
      <p className="mt-3 max-w-3xl text-base leading-7 text-muted">
        Der Systemstatus aus der technischen Grundlage ist verfügbar. Weitere Einstellungen folgen.
      </p>
      <div className="mt-6">
        <Tabs
          label="Einstellungen"
          tabs={[
            {
              id: 'status',
              label: 'Systemstatus',
              content: (
                <div className="grid gap-4">
                  <div className="flex flex-wrap items-end justify-between gap-4">
                    <div className="w-full max-w-xs">
                      <Select
                        label="Angezeigte Prüfung"
                        value={focus}
                        onChange={setFocus}
                        options={[
                          { value: 'all', label: 'API und Datenbank' },
                          { value: 'api', label: 'Nur API' },
                          { value: 'database', label: 'Nur Datenbank' },
                        ]}
                      />
                    </div>
                    <Button onClick={() => void refresh()} disabled={pending}>
                      {pending ? 'Prüfung läuft' : 'Status aktualisieren'}
                    </Button>
                  </div>
                  <p className="text-sm text-muted">Zuletzt geprüft: {checkedLabel}</p>
                  {pending && api === null ? <LoadingState label="Systemstatus wird geprüft." /> : null}
                  <div className="grid gap-4 md:grid-cols-2">
                    {visible.map((check) => (
                      <Card key={check.title} className="p-4">
                        <h2 className="text-lg font-semibold">{check.title}</h2>
                        <p className="mt-1 text-xs tracking-wide text-muted uppercase">{check.path}</p>
                        <div className="mt-4">
                          {check.result === null ? (
                            <StatusIndicator tone="pending" label="Wird geprüft" />
                          ) : check.result.ok ? (
                            <StatusIndicator tone="success" label="Erreichbar" />
                          ) : (
                            <ErrorState title="Nicht erreichbar" description={check.failure} />
                          )}
                        </div>
                        {check.result?.ok ? <p className="mt-3 text-sm leading-6 text-muted">{check.success}</p> : null}
                      </Card>
                    ))}
                  </div>
                </div>
              ),
            },
            {
              id: 'general',
              label: 'Weitere Einstellungen',
              content: (
                <Card>
                  <div className="grid gap-3 text-sm leading-6">
                    <p>
                      Die Anmeldung verwendet ein HTTP-only-Sitzungscookie. Lokal über HTTP bleibt das Secure-Flag aus,
                      sonst sendet der Browser das Cookie nicht. Hinter HTTPS muss SESSION_COOKIE_SECURE=true gesetzt werden.
                    </p>
                    <p>
                      Das erste Administratorkonto entsteht mit python -m app.bootstrap_admin. Das Passwort steht nicht im
                      Repository. Demo-Konten sind fiktiv und nicht für eine produktive Bereitstellung.
                    </p>
                    <p>
                      Diese Phase richtet Zugriff und Berichte ein. Sie ist keine abschliessende Produktionssicherheitsprüfung.
                      Offene Konfiguration und der Betrieb werden später geprüft.
                    </p>
                  </div>
                </Card>
              ),
            },
          ]}
        />
      </div>
    </div>
  )
}
