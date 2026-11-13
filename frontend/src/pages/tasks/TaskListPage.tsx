import { useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router'
import { ApiError, fetchTaskFilters, fetchTasks } from '../../api/crm.ts'
import { TaskTable } from '../../components/crm/TaskTable.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { taskPriorityOptions, taskStatusOptions, type TaskList, type TaskQuery } from '../../domain/crm.ts'
import { withCurrent } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

function readQuery(params: URLSearchParams): TaskQuery {
  const page = Number(params.get('seite') ?? '1')
  return {
    q: params.get('q') ?? '',
    status: params.get('status') ?? '',
    priority: params.get('prioritaet') ?? '',
    accountOwner: params.get('betreuung') ?? '',
    partnerId: '',
    contactId: '',
    due: params.get('faellig') ?? '',
    serviceOnly: params.get('service') === '1',
    page: Number.isInteger(page) && page > 0 ? page : 1,
  }
}

export function TaskListPage() {
  usePageTitle('Aufgaben')
  const [params, setParams] = useSearchParams()
  const queryKey = params.toString()
  const query = readQuery(params)
  const [data, setData] = useState<TaskList | null>(null)
  const [owners, setOwners] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    const current = readQuery(new URLSearchParams(queryKey))
    void Promise.all([fetchTasks(current), fetchTaskFilters()])
      .then(([list, people]) => {
        if (!active) {
          return
        }
        setData(list)
        setOwners(people)
        setError(null)
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) {
          return
        }
        setError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [queryKey, reloadKey])

  function assign(changes: Record<string, string | null>, resetPage = true) {
    setPending(true)
    const next = new URLSearchParams(params)
    for (const [key, value] of Object.entries(changes)) {
      if (value) {
        next.set(key, value)
      } else {
        next.delete(key)
      }
    }
    if (resetPage) {
      next.delete('seite')
    }
    setParams(next)
  }

  const pages = Math.max(1, Math.ceil((data?.total ?? 0) / (data?.page_size ?? 20)))

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Aufgaben</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Überfällige Aufgaben sind rot markiert. Bald fällig bedeutet innerhalb von sieben Tagen. Automatische Benachrichtigungen folgen später.
          </p>
        </div>
        <Link to="/aufgaben/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Aufgabe erstellen
        </Link>
      </header>
      <Card className="grid gap-4 p-4 md:grid-cols-2 xl:grid-cols-4">
        <Select label="Status" value={query.status} options={[{ value: '', label: 'Alle' }, ...taskStatusOptions]} onChange={(value) => assign({ status: value })} />
        <Select label="Priorität" value={query.priority} options={[{ value: '', label: 'Alle' }, ...taskPriorityOptions]} onChange={(value) => assign({ prioritaet: value })} />
        <Select
          label="Zuständigkeit"
          value={query.accountOwner}
          options={withCurrent([{ value: '', label: 'Alle' }, ...owners.map((owner) => ({ value: owner, label: owner }))], query.accountOwner)}
          onChange={(value) => assign({ betreuung: value })}
        />
        <Select
          label="Fälligkeit"
          value={query.due}
          options={[
            { value: '', label: 'Alle' },
            { value: 'open', label: 'Offen' },
            { value: 'overdue', label: 'Überfällig' },
            { value: 'soon', label: 'Bald fällig' },
            { value: 'urgent', label: 'Dringend' },
          ]}
          onChange={(value) => assign({ faellig: value })}
        />
      </Card>
      <Card>
        {error ? (
          <ErrorState title="Aufgaben nicht verfügbar" description={error} />
        ) : pending || !data ? (
          <LoadingState label="Aufgaben werden geladen" />
        ) : (
          <div>
            <p className="px-4 pt-4 text-sm text-muted">{data.total === 1 ? '1 Aufgabe gefunden' : `${data.total} Aufgaben gefunden`}</p>
            <TaskTable rows={data.items} onChanged={() => setReloadKey((value) => value + 1)} />
            <div className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <p className="text-sm text-muted">Seite {query.page} von {pages}</p>
              <div className="flex gap-2">
                <Button variant="secondary" disabled={query.page <= 1} onClick={() => assign({ seite: query.page - 1 <= 1 ? null : String(query.page - 1) }, false)}>Zurück</Button>
                <Button variant="secondary" disabled={query.page >= pages} onClick={() => assign({ seite: String(query.page + 1) }, false)}>Weiter</Button>
              </div>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
