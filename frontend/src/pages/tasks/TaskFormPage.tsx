import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { ApiError, createTask, fetchTask, updateTask } from '../../api/crm.ts'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { useToast } from '../../components/ui/toast-state.ts'
import {
  emptyTaskForm,
  fromDateTimeLocal,
  taskPriorityOptions,
  taskStatusOptions,
  taskToForm,
  taskTypeOptions,
  toDateTimeLocal,
  validateTask,
  type TaskInput,
} from '../../domain/crm.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

function TaskFields({
  initial,
  submitLabel,
  onSubmit,
}: {
  initial: TaskInput
  submitLabel: string
  onSubmit: (values: TaskInput) => Promise<void>
}) {
  const [values, setValues] = useState({ ...initial, due_at: toDateTimeLocal(initial.due_at) })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const next = { ...values, due_at: fromDateTimeLocal(values.due_at) }
    const found = validateTask(next)
    setErrors(found)
    if (Object.keys(found).length > 0) {
      return
    }
    setPending(true)
    try {
      await onSubmit(next)
    } catch (caught) {
      setFormError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
      if (caught instanceof ApiError) {
        setErrors(caught.fieldErrors)
      }
      setPending(false)
    }
  }

  return (
    <form className="grid gap-4" onSubmit={(event) => void submit(event)} noValidate>
      {formError ? <ErrorState title="Speichern fehlgeschlagen" description={formError} /> : null}
      <Card className="grid gap-4 p-4 sm:grid-cols-2">
        <div className="sm:col-span-2">
          <Input label="Titel" value={values.title} error={errors.title} onChange={(event) => setValues((current) => ({ ...current, title: event.target.value }))} />
        </div>
        <div className="sm:col-span-2">
          <Textarea label="Beschreibung" value={values.description} onChange={(event) => setValues((current) => ({ ...current, description: event.target.value }))} />
        </div>
        <Input label="Zuständige Person" value={values.account_owner} onChange={(event) => setValues((current) => ({ ...current, account_owner: event.target.value }))} />
        <Input label="Fälligkeit" type="datetime-local" value={values.due_at} error={errors.due_at} onChange={(event) => setValues((current) => ({ ...current, due_at: event.target.value }))} />
        <Select label="Priorität" value={values.priority} options={taskPriorityOptions} onChange={(value) => setValues((current) => ({ ...current, priority: value }))} />
        <Select label="Aufgabenstatus" value={values.status} options={taskStatusOptions} onChange={(value) => setValues((current) => ({ ...current, status: value }))} />
        <Select label="Aufgabentyp" value={values.task_type} options={taskTypeOptions} onChange={(value) => setValues((current) => ({ ...current, task_type: value }))} />
        <Input label="Unternehmens-ID" value={values.partner_id} onChange={(event) => setValues((current) => ({ ...current, partner_id: event.target.value }))} />
        <Input label="Kontakt-ID" value={values.contact_id} onChange={(event) => setValues((current) => ({ ...current, contact_id: event.target.value }))} />
      </Card>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending}>{submitLabel}</Button>
        <Link to="/aufgaben" className={cx(buttonStyles.base, buttonStyles.secondary)}>Abbrechen</Link>
      </div>
    </form>
  )
}

export function TaskCreatePage() {
  usePageTitle('Neue Aufgabe')
  const navigate = useNavigate()
  const { notify } = useToast()
  const [params] = useSearchParams()
  const initial: TaskInput = {
    ...emptyTaskForm,
    partner_id: params.get('unternehmen') ?? '',
    contact_id: params.get('kontakt') ?? '',
  }
  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Aufgabe erstellen</h1>
      <TaskFields
        initial={initial}
        submitLabel="Aufgabe speichern"
        onSubmit={async (values) => {
          await createTask(values)
          notify({ tone: 'success', message: 'Die Aufgabe wurde gespeichert.' })
          navigate('/aufgaben')
        }}
      />
    </div>
  )
}

export function TaskEditPage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [initial, setInitial] = useState<TaskInput | null>(null)
  const [error, setError] = useState<string | null>(null)
  usePageTitle('Aufgabe bearbeiten')

  useEffect(() => {
    if (!taskId) {
      return
    }
    let active = true
    void fetchTask(taskId)
      .then((task) => {
        if (active) {
          setInitial(taskToForm(task))
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
        }
      })
    return () => {
      active = false
    }
  }, [taskId])

  if (error) {
    return <ErrorState title="Aufgabe nicht gefunden" description={error} />
  }
  if (!initial || !taskId) {
    return <LoadingState label="Aufgabe wird geladen" />
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Aufgabe bearbeiten</h1>
      <TaskFields
        initial={initial}
        submitLabel="Änderungen speichern"
        onSubmit={async (values) => {
          await updateTask(taskId, values)
          notify({ tone: 'success', message: 'Die Aufgabe wurde gespeichert.' })
          navigate('/aufgaben')
        }}
      />
    </div>
  )
}
