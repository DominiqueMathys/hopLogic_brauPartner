import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import {
  changeAutomationStatus,
  errorMessage,
  fetchAutomation,
  fetchAutomations,
  fetchExecutions,
  runDueAutomations,
  saveAutomation,
} from '../../api/engagement.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Card } from '../../components/ui/Card.tsx'
import { DataTable, type DataColumn } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import {
  actionOptions,
  automationStatusOptions,
  labelOf,
  timeTriggers,
  triggerOptions,
  type Automation,
  type Execution,
} from '../../domain/engagement.ts'
import { formatDateTime } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const priorities = [
  { value: '', label: 'Keine Einschränkung' },
  { value: 'niedrig', label: 'Niedrig' },
  { value: 'normal', label: 'Normal' },
  { value: 'hoch', label: 'Hoch' },
  { value: 'kritisch', label: 'Kritisch' },
]

const taskPriorities = [
  { value: '', label: 'Standard' },
  { value: 'niedrig', label: 'Niedrig' },
  { value: 'normal', label: 'Normal' },
  { value: 'hoch', label: 'Hoch' },
  { value: 'dringend', label: 'Dringend' },
]

const columns: DataColumn<Automation>[] = [
  {
    id: 'name',
    header: 'Automatisierung',
    cell: (row) => (
      <Link to={`/automatisierungen/${row.id}`} className="font-semibold text-petrol">
        {row.name}
      </Link>
    ),
  },
  { id: 'trigger', header: 'Auslöser', cell: (row) => labelOf(triggerOptions, row.trigger_type) },
  { id: 'action', header: 'Aktion', cell: (row) => labelOf(actionOptions, row.action_type) },
  { id: 'status', header: 'Status', cell: (row) => labelOf(automationStatusOptions, row.status) },
  { id: 'last', header: 'Letzte Ausführung', cell: (row) => formatDateTime(row.last_run_at) },
  { id: 'count', header: 'Ausführungen', cell: (row) => String(row.run_count) },
  { id: 'error', header: 'Letzter Fehler', cell: (row) => row.last_error ?? 'Keiner' },
]

const executionColumns: DataColumn<Execution>[] = [
  { id: 'started', header: 'Start', cell: (row) => formatDateTime(row.started_at) },
  { id: 'finished', header: 'Ende', cell: (row) => formatDateTime(row.finished_at) },
  { id: 'status', header: 'Status', cell: (row) => (row.status === 'erfolg' ? 'Erfolg' : row.status === 'fehler' ? 'Fehler' : 'Übersprungen') },
  { id: 'message', header: 'Meldung', cell: (row) => row.error ?? row.message ?? 'Keine Angabe' },
  {
    id: 'task',
    header: 'Aufgabe',
    cell: (row) =>
      row.task_id ? (
        <Link to={`/aufgaben/${row.task_id}/bearbeiten`} className="font-semibold text-petrol">
          Öffnen
        </Link>
      ) : (
        'Keine'
      ),
  },
]

export function AutomationListPage() {
  usePageTitle('Automatisierungen')
  const [rows, setRows] = useState<Automation[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    void fetchAutomations()
      .then((items) => {
        if (active) setRows(items)
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Automatisierungen</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Zeitregeln laufen auf dem Server in Europe/Zurich. Der Browser muss dafür nicht geöffnet bleiben. Aktionen
            bleiben im CRM: Aufgabe, Hinweis, Erinnerung oder Aktivität. Es wird keine E-Mail versendet.
          </p>
        </div>
        <Link to="/automatisierungen/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Automatisierung erstellen
        </Link>
      </header>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      {rows ? (
        <Card>
          <DataTable
            caption="Automatisierungen"
            columns={columns}
            rows={rows}
            rowKey={(row) => row.id}
            empty={<EmptyState compact title="Keine Automatisierungen" description="Es ist noch keine Regel gespeichert." />}
          />
        </Card>
      ) : (
        <LoadingState label="Automatisierungen werden geladen" />
      )}
    </div>
  )
}

export function AutomationFormPage() {
  const { ruleId } = useParams()
  const navigate = useNavigate()
  const editing = Boolean(ruleId)
  usePageTitle(editing ? 'Automatisierung bearbeiten' : 'Automatisierung erstellen')
  const [name, setName] = useState('')
  const [description, setDescription] = useState('')
  const [owner, setOwner] = useState('')
  const [trigger, setTrigger] = useState('deal_created')
  const [days, setDays] = useState('30')
  const [triggerPriority, setTriggerPriority] = useState('')
  const [action, setAction] = useState('create_task')
  const [title, setTitle] = useState('')
  const [actionDescription, setActionDescription] = useState('')
  const [priority, setPriority] = useState('normal')
  const [dueDays, setDueDays] = useState('3')
  const [status, setStatus] = useState('entwurf')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [ready, setReady] = useState(!editing)

  useEffect(() => {
    if (!ruleId) return
    let active = true
    void fetchAutomation(ruleId)
      .then((rule) => {
        if (!active) return
        setName(rule.name)
        setDescription(rule.description ?? '')
        setOwner(rule.account_owner ?? '')
        setTrigger(rule.trigger_type)
        setDays(rule.trigger_config.days ? String(rule.trigger_config.days) : '30')
        setTriggerPriority(rule.trigger_config.priority ?? '')
        setAction(rule.action_type)
        setTitle(rule.action_config.title ?? '')
        setActionDescription(rule.action_config.description ?? '')
        setPriority(rule.action_config.priority ?? '')
        setDueDays(rule.action_config.due_days != null ? String(rule.action_config.due_days) : '')
        setStatus(rule.status)
        setReady(true)
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [ruleId])

  async function submit(event: FormEvent) {
    event.preventDefault()
    const parsedDays = Number(days)
    const parsedDue = dueDays.trim() ? Number(dueDays) : null
    if (timeTriggers.has(trigger) && !Number.isInteger(parsedDays)) {
      setError('Die Anzahl Tage muss eine ganze Zahl sein.')
      return
    }
    if (parsedDue != null && !Number.isInteger(parsedDue)) {
      setError('Die Fälligkeit in Tagen muss eine ganze Zahl sein.')
      return
    }
    setPending(true)
    setError('')
    try {
      const saved = await saveAutomation(ruleId ?? null, {
        name,
        description: description || null,
        trigger_type: trigger,
        trigger_config: {
          days: timeTriggers.has(trigger) ? parsedDays : null,
          priority: triggerPriority || null,
        },
        action_type: action,
        action_config: {
          title: title || null,
          description: actionDescription || null,
          priority: priority || null,
          due_days: parsedDue,
        },
        account_owner: owner || null,
      })
      void navigate(`/automatisierungen/${saved.id}`)
    } catch (caught) {
      setError(errorMessage(caught))
      setPending(false)
    }
  }

  if (!ready && !error) return <LoadingState label="Automatisierung wird geladen" />

  return (
    <form className="mx-auto grid max-w-3xl gap-4" onSubmit={(event) => void submit(event)}>
      <h1 className="text-3xl font-semibold tracking-tight">{editing ? 'Automatisierung bearbeiten' : 'Automatisierung erstellen'}</h1>
      {status === 'aktiv' ? (
        <p className="text-sm leading-6 text-muted">Aktive Automatisierungen werden zuerst pausiert. Die Änderung wird sonst abgelehnt.</p>
      ) : null}
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <Input label="Name" value={name} onChange={(event) => setName(event.target.value)} required />
      <Textarea label="Beschreibung" value={description} onChange={(event) => setDescription(event.target.value)} />
      <Input label="Zuständige Person" value={owner} onChange={(event) => setOwner(event.target.value)} />
      <Select label="Auslöser" value={trigger} onChange={setTrigger} options={triggerOptions} />
      {timeTriggers.has(trigger) ? (
        <Input label="Anzahl Tage" value={days} onChange={(event) => setDays(event.target.value)} inputMode="numeric" required />
      ) : null}
      <Select label="Priorität im Auslöser" value={triggerPriority} onChange={setTriggerPriority} options={priorities} hint="Optional. Zum Beispiel nur Tickets mit Priorität kritisch." />
      <Select label="Aktion" value={action} onChange={setAction} options={actionOptions} />
      <Input label="Titel der Aktion" value={title} onChange={(event) => setTitle(event.target.value)} required />
      <Textarea label="Beschreibung der Aktion" value={actionDescription} onChange={(event) => setActionDescription(event.target.value)} />
      <Select label="Aufgabenpriorität" value={priority} onChange={setPriority} options={taskPriorities} />
      <Input label="Fällig in Tagen" value={dueDays} onChange={(event) => setDueDays(event.target.value)} inputMode="numeric" />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending}>
          Speichern
        </Button>
        <Link to={ruleId ? `/automatisierungen/${ruleId}` : '/automatisierungen'} className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Abbrechen
        </Link>
      </div>
    </form>
  )
}

export function AutomationDetailPage() {
  const { ruleId = '' } = useParams()
  usePageTitle('Automatisierung')
  const [rule, setRule] = useState<Automation | null>(null)
  const [rows, setRows] = useState<Execution[] | null>(null)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [pending, setPending] = useState(false)

  function load() {
    return Promise.all([fetchAutomation(ruleId), fetchExecutions(ruleId)]).then(([nextRule, executions]) => {
      setRule(nextRule)
      setRows(executions)
    })
  }

  useEffect(() => {
    let active = true
    void Promise.all([fetchAutomation(ruleId), fetchExecutions(ruleId)])
      .then(([nextRule, executions]) => {
        if (!active) return
        setRule(nextRule)
        setRows(executions)
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [ruleId])

  async function run(action: () => Promise<unknown>) {
    setPending(true)
    setError('')
    try {
      await action()
      await load()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setPending(false)
    }
  }

  if (error && !rule) return <p className="text-sm text-critical">{error}</p>
  if (!rule || !rows) return <LoadingState label="Automatisierung wird geladen" />

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{rule.name}</h1>
          <p className="mt-2 text-sm leading-6 text-muted">{rule.description}</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge tone={rule.status === 'aktiv' ? 'success' : 'neutral'}>{labelOf(automationStatusOptions, rule.status)}</Badge>
            {rule.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
          </div>
        </div>
        <Link to={`/automatisierungen/${rule.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Bearbeiten
        </Link>
      </header>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      {info ? <p className="text-sm">{info}</p> : null}
      <Card className="grid gap-2 p-4 text-sm">
        <p>
          <span className="font-semibold">Auslöser: </span>
          {labelOf(triggerOptions, rule.trigger_type)}
          {rule.trigger_config.days ? ` · ${rule.trigger_config.days} Tage` : ''}
          {rule.trigger_config.priority ? ` · Priorität ${rule.trigger_config.priority}` : ''}
        </p>
        <p>
          <span className="font-semibold">Aktion: </span>
          {labelOf(actionOptions, rule.action_type)}
          {rule.action_config.title ? ` · ${rule.action_config.title}` : ''}
        </p>
        <p>
          <span className="font-semibold">Zuständig: </span>
          {rule.account_owner ?? 'Keine Angabe'}
        </p>
        <p>
          <span className="font-semibold">Letzte Ausführung: </span>
          {formatDateTime(rule.last_run_at)} · {rule.run_count} erfolgreiche Ausführungen
        </p>
        <p>
          <span className="font-semibold">Letzter Fehler: </span>
          {rule.last_error ?? 'Keiner'}
        </p>
      </Card>
      <div className="flex flex-wrap gap-2">
        {rule.allowed_statuses.map((status) => (
          <Button key={status} variant="secondary" disabled={pending} onClick={() => void run(() => changeAutomationStatus(rule.id, status))}>
            {labelOf(automationStatusOptions, status)}
          </Button>
        ))}
        {timeTriggers.has(rule.trigger_type) ? (
          <Button
            disabled={pending || rule.status !== 'aktiv'}
            onClick={() =>
              void run(async () => {
                const attempts = await runDueAutomations()
                setInfo(`Zeitprüfung abgeschlossen. Ausführungen in diesem Lauf: ${attempts}.`)
              })
            }
          >
            Zeitregeln jetzt prüfen
          </Button>
        ) : (
          <p className="self-center text-sm text-muted">Ereignisauslöser starten, wenn der passende CRM-Datensatz gespeichert wird.</p>
        )}
      </div>
      <Card>
        <h2 className="border-b border-line px-4 py-3 text-base font-semibold">Ausführungsprotokoll</h2>
        <DataTable
          caption="Ausführungsprotokoll"
          columns={executionColumns}
          rows={rows}
          rowKey={(row) => row.id}
          empty={<EmptyState compact title="Keine Ausführungen" description="Diese Automatisierung wurde noch nicht ausgeführt." />}
        />
      </Card>
    </div>
  )
}
