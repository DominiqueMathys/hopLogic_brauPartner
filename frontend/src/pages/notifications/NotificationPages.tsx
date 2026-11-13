import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import {
  errorMessage,
  fetchNoticeSettings,
  fetchNotices,
  markAllNoticesRead,
  markNoticeRead,
  saveNoticeSettings,
} from '../../api/engagement.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Card } from '../../components/ui/Card.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { labelOf, notificationTypeOptions, type NoticeList, type NoticeSettings } from '../../domain/engagement.ts'
import { formatDateTime } from '../../domain/partners.ts'
import { actorName, rememberActor } from '../../lib/actor.ts'
import { usePageTitle } from '../../usePageTitle.ts'

export function NotificationCenterPage() {
  usePageTitle('Benachrichtigungen')
  const [name, setName] = useState(() => actorName())
  const [draft, setDraft] = useState(() => actorName())
  const [type, setType] = useState('')
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [data, setData] = useState<NoticeList | null>(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    let active = true
    void fetchNotices({ recipient: name, type, unread: unreadOnly })
      .then((result) => {
        if (!active) return
        setData(result)
        setError('')
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [name, type, unreadOnly])

  function reload() {
    return fetchNotices({ recipient: name, type, unread: unreadOnly }).then(setData)
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Benachrichtigungen</h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Bis Phase 08 gibt es kein Benutzerkonto. Hinweise erscheinen nur für den gewählten Anzeigenamen und nicht als
            persönliche Daten anderer Personen.
          </p>
        </div>
        <Link to="/benachrichtigungen/einstellungen" className="text-sm font-semibold text-petrol">
          Einstellungen
        </Link>
      </header>
      <Card className="grid gap-3 p-4 md:grid-cols-[1fr_auto]">
        <Input label="Anzeigename" value={draft} onChange={(event) => setDraft(event.target.value)} hint="Zum Beispiel Sandra Lutz" />
        <div className="self-end">
          <Button
            onClick={() => {
              rememberActor(draft)
              setName(draft.trim())
            }}
          >
            Anzeigen
          </Button>
        </div>
      </Card>
      <div className="grid gap-3 md:grid-cols-[1fr_auto] md:items-end">
        <Select
          label="Typ"
          value={type}
          onChange={setType}
          options={[{ value: '', label: 'Alle Typen' }, ...notificationTypeOptions]}
        />
        <label className="flex min-h-11 items-center gap-2 text-sm">
          <input type="checkbox" checked={unreadOnly} onChange={(event) => setUnreadOnly(event.target.checked)} />
          Nur ungelesene
        </label>
      </div>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      {data?.notice ? <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6">{data.notice}</p> : null}
      {data && name.trim() ? (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <p className="text-sm font-semibold">{data.unread} ungelesen</p>
          <Button
            variant="secondary"
            disabled={pending || !name}
            onClick={() => {
              setPending(true)
              void markAllNoticesRead(name)
                .then(reload)
                .catch((caught: unknown) => setError(errorMessage(caught)))
                .finally(() => setPending(false))
            }}
          >
            Alle als gelesen markieren
          </Button>
        </div>
      ) : null}
      {!data ? (
        <LoadingState label="Benachrichtigungen werden geladen" />
      ) : data.items.length === 0 ? (
        <EmptyState
          title={name.trim() ? 'Keine Benachrichtigungen' : 'Kein Anzeigename'}
          description={
            name.trim()
              ? 'Für diesen Anzeigenamen sind keine gespeicherten Hinweise vorhanden.'
              : 'Ohne Anzeigename werden keine Hinweise geladen.'
          }
        />
      ) : (
        <ul className="grid gap-3">
          {data.items.map((item) => (
            <li key={item.id} className={item.read_at ? 'border border-line bg-card px-4 py-3' : 'border border-petrol bg-petrol-soft px-4 py-3'}>
              <div className="flex flex-wrap items-start justify-between gap-2">
                <div>
                  <p className="text-xs font-semibold tracking-wide text-muted uppercase">{labelOf(notificationTypeOptions, item.notification_type)}</p>
                  <p className="mt-1 font-semibold">{item.title}</p>
                  {item.body ? <p className="mt-1 text-sm leading-6">{item.body}</p> : null}
                  <p className="mt-1 text-xs text-muted">{formatDateTime(item.created_at)}</p>
                </div>
                {!item.read_at ? <Badge tone="petrol">Ungelesen</Badge> : <Badge>Gelesen</Badge>}
              </div>
              <div className="mt-3 flex flex-wrap gap-2">
                {item.href ? (
                  <Link to={item.href} className="text-sm font-semibold text-petrol">
                    Datensatz öffnen
                  </Link>
                ) : null}
                {!item.read_at ? (
                  <Button
                    variant="secondary"
                    disabled={pending}
                    onClick={() => {
                      setPending(true)
                      void markNoticeRead(item.id, name)
                        .then(reload)
                        .catch((caught: unknown) => setError(errorMessage(caught)))
                        .finally(() => setPending(false))
                    }}
                  >
                    Als gelesen markieren
                  </Button>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export function NotificationSettingsPage() {
  usePageTitle('Benachrichtigungseinstellungen')
  const [name, setName] = useState(() => actorName())
  const [settings, setSettings] = useState<NoticeSettings | null>(null)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    if (!name) return
    let active = true
    void fetchNoticeSettings(name)
      .then((result) => {
        if (active) setSettings(result)
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [name])

  function toggle(key: keyof Omit<NoticeSettings, 'recipient_label' | 'notice'>) {
    setSettings((current) => (current ? { ...current, [key]: !current[key] } : current))
  }

  return (
    <div className="mx-auto grid max-w-xl gap-4">
      <h1 className="text-3xl font-semibold tracking-tight">Benachrichtigungseinstellungen</h1>
      <p className="text-sm leading-6 text-muted">
        Die Schalter gelten für den Anzeigenamen dieser Sitzung. Sie ersetzen keine Benutzerverwaltung und gelten bis
        Phase 08 als eingeschränkt.
      </p>
      <Input
        label="Anzeigename"
        value={name}
        onChange={(event) => {
          setName(event.target.value)
          rememberActor(event.target.value)
          setSettings(null)
        }}
      />
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      {!name ? <EmptyState title="Anzeigename fehlt" description="Ohne Namen können keine persönlichen Einstellungen geladen werden." /> : null}
      {name && !settings && !error ? <LoadingState label="Einstellungen werden geladen" /> : null}
      {settings ? (
        <Card className="grid gap-3 p-4">
          <p className="text-sm leading-6">{settings.notice}</p>
          <Check label="Aufgabenerinnerungen" checked={settings.task_reminders} onChange={() => toggle('task_reminders')} />
          <Check label="Service-Ticket-Benachrichtigungen" checked={settings.service_alerts} onChange={() => toggle('service_alerts')} />
          <Check label="Verkaufschancen-Benachrichtigungen" checked={settings.deal_alerts} onChange={() => toggle('deal_alerts')} />
          <Check label="Automatisierungsfehler" checked={settings.automation_errors} onChange={() => toggle('automation_errors')} />
          <Button
            disabled={pending}
            onClick={() => {
              setPending(true)
              void saveNoticeSettings(settings)
                .then(setSettings)
                .catch((caught: unknown) => setError(errorMessage(caught)))
                .finally(() => setPending(false))
            }}
          >
            Speichern
          </Button>
        </Card>
      ) : null}
    </div>
  )
}

function Check({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="flex items-center gap-2 text-sm">
      <input type="checkbox" checked={checked} onChange={onChange} />
      {label}
    </label>
  )
}
