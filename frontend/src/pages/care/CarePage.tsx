import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import {
  createCareTask,
  deleteCareRule,
  errorMessage,
  fetchCareOverview,
  fetchCareRules,
  saveCareRule,
} from '../../api/engagement.ts'
import { Button } from '../../components/ui/Button.tsx'
import { Card } from '../../components/ui/Card.tsx'
import { DataTable, type DataColumn } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { careKindOptions, labelOf, type CareRow, type CareRule } from '../../domain/engagement.ts'
import { formatDate, formatDateTime } from '../../domain/partners.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const columns: DataColumn<CareRow>[] = [
  {
    id: 'partner',
    header: 'Vertriebspartner',
    cell: (row) => (
      <Link to={`/vertriebspartner/${row.partner_id}`} className="font-semibold text-petrol">
        {row.company_name}
      </Link>
    ),
  },
  { id: 'owner', header: 'Zuständig', cell: (row) => row.account_owner ?? 'Keine Angabe' },
  { id: 'contact', header: 'Letzter Kontakt', cell: (row) => formatDateTime(row.last_contact_at) },
  { id: 'order', header: 'Letzte Bestellung', cell: (row) => formatDate(row.last_order_on) },
  { id: 'tasks', header: 'Offene Aufgaben', cell: (row) => String(row.open_tasks) },
  { id: 'tickets', header: 'Offene Tickets', cell: (row) => String(row.open_tickets) },
  { id: 'next', header: 'Nächste Aktivität', cell: (row) => formatDateTime(row.next_activity_at) },
]

const signals = [
  { value: '', label: 'Alle aktiven Partner' },
  { value: 'contact', label: 'Kontaktpause' },
  { value: 'order', label: 'Ohne aktuelle Bestellung' },
  { value: 'deals', label: 'Offene Verkaufschancen' },
  { value: 'complaints', label: 'Offene Reklamationen' },
]

export function CarePage() {
  usePageTitle('Partnerbetreuung')
  const [rows, setRows] = useState<CareRow[] | null>(null)
  const [rules, setRules] = useState<CareRule[]>([])
  const [days, setDays] = useState({ contact: 30, order: 60 })
  const [signal, setSignal] = useState('')
  const [error, setError] = useState('')
  const [taskPartner, setTaskPartner] = useState('')
  const [taskTitle, setTaskTitle] = useState('Partnerkontakt planen')
  const [taskDue, setTaskDue] = useState('')
  const [taskOwner, setTaskOwner] = useState('')
  const [ruleName, setRuleName] = useState('')
  const [ruleKind, setRuleKind] = useState('no_contact')
  const [ruleDays, setRuleDays] = useState('30')
  const [ruleTitle, setRuleTitle] = useState('Partnerkontakt planen')
  const [ruleOwner, setRuleOwner] = useState('')
  const [ruleDescription, setRuleDescription] = useState('')
  const [createTasks, setCreateTasks] = useState(false)
  const [editing, setEditing] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  function load() {
    return Promise.all([fetchCareOverview(signal), fetchCareRules()]).then(([overview, nextRules]) => {
      setRows(overview.items)
      setDays({ contact: overview.contactDays, order: overview.orderDays })
      setRules(nextRules)
    })
  }

  useEffect(() => {
    let active = true
    void Promise.all([fetchCareOverview(signal), fetchCareRules()])
      .then(([overview, nextRules]) => {
        if (!active) return
        setRows(overview.items)
        setDays({ contact: overview.contactDays, order: overview.orderDays })
        setRules(nextRules)
        setError('')
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [signal])

  async function run(action: () => Promise<unknown>) {
    setPending(true)
    setError('')
    try {
      await action()
      await load()
      return true
    } catch (caught) {
      setError(errorMessage(caught))
      return false
    } finally {
      setPending(false)
    }
  }

  function saveRule(event: FormEvent) {
    event.preventDefault()
    const threshold = Number(ruleDays)
    if (!Number.isInteger(threshold)) {
      setError('Die Anzahl Tage muss eine ganze Zahl sein.')
      return
    }
    void run(() =>
      saveCareRule(editing, {
        name: ruleName,
        description: ruleDescription || null,
        rule_kind: ruleKind,
        threshold_days: threshold,
        is_active: true,
        create_tasks: createTasks,
        task_title: ruleTitle,
        account_owner: ruleOwner || null,
      }),
    ).then((saved) => {
      if (!saved) return
      setEditing(null)
      setRuleName('')
    })
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Partnerbetreuung</h1>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
          Die Übersicht liest vorhandene Kontakte, Bestellungen, Aufgaben, Tickets und Verkaufschancen. Kontaktpause ab{' '}
          {days.contact} Tagen, Bestellpause ab {days.order} Tagen. Entwürfe und stornierte Bestellungen zählen nicht.
        </p>
      </header>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <Select label="Ansicht" value={signal} onChange={setSignal} options={signals} />
      {rows ? (
        <Card>
          <DataTable
            caption="Partnerbetreuung"
            columns={columns}
            rows={rows}
            rowKey={(row) => row.partner_id}
            empty={<EmptyState compact title="Keine Partner" description="Für diese Ansicht sind keine Partner gespeichert." />}
          />
        </Card>
      ) : (
        <LoadingState label="Betreuung wird geladen" />
      )}
      <Card className="grid gap-3 p-4">
        <h2 className="text-base font-semibold">Betreuungsaufgabe</h2>
        <Select
          label="Vertriebspartner"
          value={taskPartner}
          onChange={setTaskPartner}
          options={[{ value: '', label: 'Partner wählen' }, ...(rows ?? []).map((row) => ({ value: row.partner_id, label: row.company_name }))]}
        />
        <Input label="Aufgabentitel" value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} />
        <Input label="Fällig" type="datetime-local" value={taskDue} onChange={(event) => setTaskDue(event.target.value)} />
        <Input label="Zuständige Person" value={taskOwner} onChange={(event) => setTaskOwner(event.target.value)} />
        <Button
          disabled={pending || !taskPartner || !taskDue}
          onClick={() =>
            void run(() =>
              createCareTask({
                partner_id: taskPartner,
                title: taskTitle,
                due_at: new Date(taskDue).toISOString(),
                account_owner: taskOwner || null,
              }),
            )
          }
        >
          Aufgabe erstellen
        </Button>
      </Card>
      <Card className="grid gap-4 p-4">
        <h2 className="text-base font-semibold">Betreuungsregeln</h2>
        <p className="text-sm leading-6 text-muted">
          Dieselbe Bedingung erzeugt nicht erneut eine Aufgabe, solange der letzte Auslöser unverändert ist. Aufgaben
          aus Regeln entstehen nur, wenn «Aufgaben erzeugen» aktiv ist. Die zeitgesteuerte Automatisierung bleibt
          davon getrennt.
        </p>
        <ul className="grid gap-2">
          {rules.map((rule) => (
            <li key={rule.id} className="flex flex-wrap items-center justify-between gap-2 border border-line px-3 py-2">
              <span>
                <span className="font-semibold">{rule.name}</span>
                <span className="block text-sm text-muted">
                  {labelOf(careKindOptions, rule.rule_kind)} · {rule.threshold_days} Tage · {rule.match_count} Treffer
                  {rule.create_tasks ? ' · erzeugt Aufgaben' : ' · nur Hinweis'}
                </span>
              </span>
              <span className="flex gap-2">
                <Button
                  variant="secondary"
                  onClick={() => {
                    setEditing(rule.id)
                    setRuleName(rule.name)
                    setRuleKind(rule.rule_kind)
                    setRuleDays(String(rule.threshold_days))
                    setRuleTitle(rule.task_title)
                    setRuleOwner(rule.account_owner ?? '')
                    setRuleDescription(rule.description ?? '')
                    setCreateTasks(rule.create_tasks)
                  }}
                >
                  Bearbeiten
                </Button>
                <Button variant="ghost" disabled={pending} onClick={() => void run(() => deleteCareRule(rule.id))}>
                  Entfernen
                </Button>
              </span>
            </li>
          ))}
        </ul>
        <form className="grid gap-3" onSubmit={saveRule}>
          <h3 className="text-sm font-semibold">{editing ? 'Regel bearbeiten' : 'Regel erstellen'}</h3>
          <Input label="Name" value={ruleName} onChange={(event) => setRuleName(event.target.value)} required />
          <Textarea label="Beschreibung" value={ruleDescription} onChange={(event) => setRuleDescription(event.target.value)} />
          <Select label="Bedingung" value={ruleKind} onChange={setRuleKind} options={careKindOptions} />
          <Input label="Anzahl Tage" value={ruleDays} onChange={(event) => setRuleDays(event.target.value)} inputMode="numeric" required />
          <Input label="Aufgabentitel" value={ruleTitle} onChange={(event) => setRuleTitle(event.target.value)} required />
          <Input label="Zuständige Person" value={ruleOwner} onChange={(event) => setRuleOwner(event.target.value)} />
          <label className="flex items-center gap-2 text-sm">
            <input type="checkbox" checked={createTasks} onChange={(event) => setCreateTasks(event.target.checked)} />
            Aufgaben erzeugen, ohne dieselbe Bedingung doppelt auszulösen
          </label>
          <Button type="submit" disabled={pending}>
            Regel speichern
          </Button>
        </form>
      </Card>
    </div>
  )
}
