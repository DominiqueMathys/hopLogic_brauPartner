import { useState, type FormEvent } from 'react'
import { ApiError, createNoteWithTask } from '../../api/crm.ts'
import {
  activityTypeOptions,
  emptyActivityForm,
  fromDateTimeLocal,
  taskPriorityOptions,
  validateActivity,
  type ActivityInput,
} from '../../domain/crm.ts'
import { Button } from '../ui/Button.tsx'
import { Input } from '../ui/Input.tsx'
import { Modal } from '../ui/Modal.tsx'
import { Select } from '../ui/Select.tsx'
import { Textarea } from '../ui/Textarea.tsx'

type NoteTaskDialogProps = {
  open: boolean
  occurredAt: string
  contactId: string
  partnerId: string
  owner: string
  onClose: () => void
  onSaved: () => void
}

export function NoteTaskDialog({
  open,
  occurredAt,
  contactId,
  partnerId,
  owner,
  onClose,
  onSaved,
}: NoteTaskDialogProps) {
  const [activity, setActivity] = useState<ActivityInput>({
    ...emptyActivityForm,
    activity_type: 'telefonat',
    occurred_at: occurredAt,
    account_owner: owner,
    contact_id: contactId,
    partner_id: partnerId,
  })
  const [createTask, setCreateTask] = useState(false)
  const [taskTitle, setTaskTitle] = useState('')
  const [taskOwner, setTaskOwner] = useState(owner)
  const [taskDue, setTaskDue] = useState('')
  const [taskPriority, setTaskPriority] = useState('normal')
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    const nextErrors = validateActivity({ ...activity, contact_id: contactId, partner_id: partnerId })
    if (createTask && !taskTitle.trim()) {
      nextErrors.task_title = 'Aufgabentitel ist erforderlich.'
    }
    if (createTask && !taskDue) {
      nextErrors.task_due = 'Fälligkeit ist erforderlich.'
    }
    setErrors(nextErrors)
    if (Object.keys(nextErrors).length > 0) {
      return
    }
    setPending(true)
    setFormError(null)
    try {
      await createNoteWithTask({
        activity: {
          ...activity,
          occurred_at: fromDateTimeLocal(activity.occurred_at),
          contact_id: contactId,
          partner_id: partnerId,
        },
        createTask,
        taskTitle,
        taskOwner,
        taskDue: fromDateTimeLocal(taskDue),
        taskPriority,
      })
      onSaved()
      onClose()
    } catch (caught) {
      setFormError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
    } finally {
      setPending(false)
    }
  }

  return (
    <Modal open={open} wide title="Gesprächsnotiz" onClose={onClose}>
      <form className="grid gap-4" onSubmit={(event) => void submit(event)} noValidate>
        {formError ? (
          <p className="border border-critical bg-critical-soft px-3 py-2 text-sm text-critical">{formError}</p>
        ) : null}
        <Select
          label="Aktivitätstyp"
          value={activity.activity_type}
          options={activityTypeOptions}
          error={errors.activity_type}
          onChange={(value) => setActivity((current) => ({ ...current, activity_type: value }))}
        />
        <Input
          label="Titel"
          value={activity.title}
          error={errors.title}
          onChange={(event) => setActivity((current) => ({ ...current, title: event.target.value }))}
        />
        <Textarea
          label="Beschreibung"
          value={activity.description}
          onChange={(event) => setActivity((current) => ({ ...current, description: event.target.value }))}
        />
        <Input
          label="Datum und Uhrzeit"
          type="datetime-local"
          value={activity.occurred_at}
          error={errors.occurred_at}
          onChange={(event) => setActivity((current) => ({ ...current, occurred_at: event.target.value }))}
        />
        <Input
          label="Zuständige Person"
          value={activity.account_owner}
          onChange={(event) => setActivity((current) => ({ ...current, account_owner: event.target.value }))}
        />
        <label className="flex min-h-11 items-center gap-2 text-sm font-semibold">
          <input type="checkbox" checked={createTask} onChange={(event) => setCreateTask(event.target.checked)} />
          Folgeaufgabe erstellen
        </label>
        {createTask ? (
          <div className="grid gap-4 border border-line bg-cream p-3">
            <Input
              label="Aufgabentitel"
              value={taskTitle}
              error={errors.task_title}
              onChange={(event) => setTaskTitle(event.target.value)}
            />
            <Input
              label="Zuständige Person"
              value={taskOwner}
              onChange={(event) => setTaskOwner(event.target.value)}
            />
            <Input
              label="Fälligkeitsdatum"
              type="datetime-local"
              value={taskDue}
              error={errors.task_due}
              onChange={(event) => setTaskDue(event.target.value)}
            />
            <Select label="Priorität" value={taskPriority} options={taskPriorityOptions} onChange={setTaskPriority} />
          </div>
        ) : null}
        <div className="flex flex-wrap justify-end gap-2">
          <Button variant="secondary" onClick={onClose}>
            Abbrechen
          </Button>
          <Button type="submit" disabled={pending}>
            Speichern
          </Button>
        </div>
      </form>
    </Modal>
  )
}
