import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { ApiError, createActivity, fetchActivity, updateActivity } from '../../api/crm.ts'
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
  activityToForm,
  activityTypeOptions,
  emptyActivityForm,
  fromDateTimeLocal,
  toDateTimeLocal,
  validateActivity,
  type ActivityInput,
} from '../../domain/crm.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

function ActivityFields({
  initial,
  submitLabel,
  cancelTo,
  onSubmit,
}: {
  initial: ActivityInput
  submitLabel: string
  cancelTo: string
  onSubmit: (values: ActivityInput) => Promise<void>
}) {
  const [values, setValues] = useState({ ...initial, occurred_at: toDateTimeLocal(initial.occurred_at) })
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const next = { ...values, occurred_at: fromDateTimeLocal(values.occurred_at) }
    const found = validateActivity(next)
    setErrors(found)
    if (Object.keys(found).length > 0) {
      return
    }
    setPending(true)
    setFormError(null)
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
      <Card className="grid gap-4 p-4">
        <Select label="Aktivitätstyp" value={values.activity_type} options={activityTypeOptions} error={errors.activity_type} onChange={(value) => setValues((current) => ({ ...current, activity_type: value }))} />
        <Input label="Titel" value={values.title} error={errors.title} onChange={(event) => setValues((current) => ({ ...current, title: event.target.value }))} />
        <Textarea label="Beschreibung" value={values.description} onChange={(event) => setValues((current) => ({ ...current, description: event.target.value }))} />
        <Input label="Datum und Uhrzeit" type="datetime-local" value={values.occurred_at} error={errors.occurred_at} onChange={(event) => setValues((current) => ({ ...current, occurred_at: event.target.value }))} />
        <Input label="Zuständige Person" value={values.account_owner} onChange={(event) => setValues((current) => ({ ...current, account_owner: event.target.value }))} />
        <Input label="Kontakt-ID" value={values.contact_id} hint="Leer lassen, wenn nur das Unternehmen verknüpft ist." onChange={(event) => setValues((current) => ({ ...current, contact_id: event.target.value }))} />
        <Input label="Unternehmens-ID" value={values.partner_id} error={errors.partner_id} hint="Leer lassen, wenn nur der Kontakt verknüpft ist." onChange={(event) => setValues((current) => ({ ...current, partner_id: event.target.value }))} />
      </Card>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending}>{submitLabel}</Button>
        <Link to={cancelTo} className={cx(buttonStyles.base, buttonStyles.secondary)}>Abbrechen</Link>
      </div>
    </form>
  )
}

export function ActivityCreatePage() {
  usePageTitle('Neue Aktivität')
  const navigate = useNavigate()
  const { notify } = useToast()
  const [params] = useSearchParams()
  const initial: ActivityInput = {
    ...emptyActivityForm,
    contact_id: params.get('kontakt') ?? '',
    partner_id: params.get('unternehmen') ?? '',
    occurred_at: '',
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Aktivität erfassen</h1>
      <ActivityFields
        initial={initial}
        submitLabel="Aktivität speichern"
        cancelTo="/aktivitaeten"
        onSubmit={async (values) => {
          const created = await createActivity(values)
          notify({ tone: 'success', message: 'Die Aktivität wurde gespeichert.' })
          navigate(created.partner_id ? `/vertriebspartner/${created.partner_id}` : '/aktivitaeten')
        }}
      />
    </div>
  )
}

export function ActivityEditPage() {
  const { activityId } = useParams()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [initial, setInitial] = useState<ActivityInput | null>(null)
  const [error, setError] = useState<string | null>(null)
  usePageTitle('Aktivität bearbeiten')

  useEffect(() => {
    if (!activityId) {
      return
    }
    let active = true
    void fetchActivity(activityId)
      .then((activity) => {
        if (!active) {
          return
        }
        if (activity.archived_at) {
          setError('Archivierte Aktivitäten können erst nach der Wiederherstellung bearbeitet werden.')
          return
        }
        setInitial(activityToForm(activity))
      })
      .catch((caught: unknown) => {
        if (active) {
          setError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
        }
      })
    return () => {
      active = false
    }
  }, [activityId])

  if (error) {
    return <ErrorState title="Aktivität nicht bearbeitbar" description={error} />
  }
  if (!initial || !activityId) {
    return <LoadingState label="Aktivität wird geladen" />
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <h1 className="text-3xl font-semibold tracking-tight">Aktivität bearbeiten</h1>
      <ActivityFields
        initial={initial}
        submitLabel="Änderungen speichern"
        cancelTo="/aktivitaeten"
        onSubmit={async (values) => {
          await updateActivity(activityId, values)
          notify({ tone: 'success', message: 'Die Aktivität wurde gespeichert.' })
          navigate('/aktivitaeten')
        }}
      />
    </div>
  )
}
