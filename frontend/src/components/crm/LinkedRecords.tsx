import { useEffect, useState } from 'react'
import { Link } from 'react-router'
import { ApiError, fetchActivities, fetchContacts, fetchTasks } from '../../api/crm.ts'
import {
  activityTypeOptions,
  contactName,
  contactStatusOptions,
  labelOf,
  lifecycleOptions,
  toDateTimeLocal,
  type Activity,
  type Contact,
  type ContactQuery,
  type Task,
} from '../../domain/crm.ts'
import { formatDateTime } from '../../domain/partners.ts'
import { Badge } from '../ui/Badge.tsx'
import { Button } from '../ui/Button.tsx'
import { buttonStyles } from '../ui/button-styles.ts'
import { EmptyState } from '../ui/EmptyState.tsx'
import { ErrorState } from '../ui/ErrorState.tsx'
import { LoadingState } from '../ui/LoadingState.tsx'
import { Select } from '../ui/Select.tsx'
import { cx } from '../../lib/cx.ts'
import { ActivityTimeline } from './ActivityTimeline.tsx'
import { NoteTaskDialog } from './NoteTaskDialog.tsx'
import { TaskTable } from './TaskTable.tsx'

type Scope = {
  partnerId?: string
  contactId?: string
  owner?: string
}

export function LinkedActivities({ partnerId, contactId, owner = '' }: Scope) {
  const [items, setItems] = useState<Activity[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [activityType, setActivityType] = useState('')
  const [includeArchived, setIncludeArchived] = useState(false)
  const [reloadKey, setReloadKey] = useState(0)
  const [noteOpen, setNoteOpen] = useState(false)
  const [occurredAt, setOccurredAt] = useState('')

  useEffect(() => {
    let active = true
    void fetchActivities({ partnerId, contactId, activityType, includeArchived, page: 1 })
      .then((result) => {
        if (active) {
          setItems(result.items)
          setError(null)
        }
      })
      .catch((caught: unknown) => {
        if (active) {
          setItems(null)
          setError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
        }
      })
    return () => {
      active = false
    }
  }, [partnerId, contactId, activityType, includeArchived, reloadKey])

  return (
    <div className="grid gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="grid gap-3 sm:grid-cols-2">
          <Select
            label="Aktivitätstyp"
            value={activityType}
            options={[{ value: '', label: 'Alle' }, ...activityTypeOptions]}
            onChange={setActivityType}
          />
          <Select
            label="Archiv"
            value={includeArchived ? 'ja' : 'nein'}
            options={[
              { value: 'nein', label: 'Ohne archivierte Aktivitäten' },
              { value: 'ja', label: 'Mit archivierten Aktivitäten' },
            ]}
            onChange={(value) => setIncludeArchived(value === 'ja')}
          />
        </div>
        <Button
          onClick={() => {
            setOccurredAt(toDateTimeLocal(new Date().toISOString()))
            setNoteOpen(true)
          }}
        >
          Gesprächsnotiz
        </Button>
      </div>
      {error ? <ErrorState title="Aktivitäten nicht verfügbar" description={error} /> : null}
      {items ? <ActivityTimeline items={items} onChanged={() => setReloadKey((value) => value + 1)} /> : <LoadingState label="Aktivitäten werden geladen" />}
      {noteOpen ? (
        <NoteTaskDialog
          key={occurredAt}
          open
          occurredAt={occurredAt}
          contactId={contactId ?? ''}
          partnerId={partnerId ?? ''}
          owner={owner}
          onClose={() => setNoteOpen(false)}
          onSaved={() => setReloadKey((value) => value + 1)}
        />
      ) : null}
    </div>
  )
}

export function LinkedTasks({ partnerId, contactId }: Scope) {
  const [items, setItems] = useState<Task[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let active = true
    void fetchTasks({
      q: '',
      status: '',
      priority: '',
      accountOwner: '',
      partnerId: partnerId ?? '',
      contactId: contactId ?? '',
      due: '',
      page: 1,
    })
      .then((result) => {
        if (active) {
          setItems(result.items)
          setError(null)
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
  }, [partnerId, contactId, reloadKey])

  const createTo = `/aufgaben/neu?${partnerId ? `unternehmen=${partnerId}` : ''}${contactId ? `${partnerId ? '&' : ''}kontakt=${contactId}` : ''}`

  return (
    <div className="grid gap-4">
      <div className="flex justify-end">
        <Link to={createTo} className={cx(buttonStyles.base, buttonStyles.primary)}>
          Aufgabe erstellen
        </Link>
      </div>
      {error ? <ErrorState title="Aufgaben nicht verfügbar" description={error} /> : null}
      {items ? <TaskTable rows={items} onChanged={() => setReloadKey((value) => value + 1)} /> : <LoadingState label="Aufgaben werden geladen" />}
    </div>
  )
}

const contactQuery = (partnerId: string): ContactQuery => ({
  q: '',
  partnerId,
  status: '',
  accountOwner: '',
  sort: 'name',
  direction: 'asc',
  page: 1,
  includeArchived: false,
})

export function PartnerContacts({ partnerId }: { partnerId: string }) {
  const [items, setItems] = useState<Contact[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void fetchContacts(contactQuery(partnerId))
      .then((result) => {
        if (active) {
          setItems(result.items)
          setError(null)
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
  }, [partnerId])

  if (error) {
    return <ErrorState title="Kontakte nicht verfügbar" description={error} />
  }
  if (!items) {
    return <LoadingState label="Kontakte werden geladen" />
  }
  if (items.length === 0) {
    return (
      <EmptyState
        title="Keine Kontakte"
        description="Diesem Unternehmen ist noch keine Kontaktperson zugeordnet."
        action={
          <Link to={`/kontakte/neu?unternehmen=${partnerId}`} className={cx(buttonStyles.base, buttonStyles.primary)}>
            Kontakt erstellen
          </Link>
        }
      />
    )
  }

  return (
    <div className="grid gap-4">
      <div className="flex justify-end">
        <Link to={`/kontakte/neu?unternehmen=${partnerId}`} className={cx(buttonStyles.base, buttonStyles.primary)}>
          Kontakt erstellen
        </Link>
      </div>
      <ul className="grid gap-3">
        {items.map((contact) => {
          const link = contact.companies.find((company) => company.partner_id === partnerId)
          return (
            <li key={contact.id} className="border border-line px-4 py-3">
              <div className="flex flex-wrap items-center gap-2">
                <Link to={`/kontakte/${contact.id}`} className="font-semibold text-petrol">
                  {contactName(contact)}
                </Link>
                {link?.is_primary ? <Badge tone="petrol">Primär</Badge> : null}
                {contact.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
                <Badge>{labelOf(contactStatusOptions, contact.status)}</Badge>
              </div>
              <p className="mt-1 text-sm text-muted">
                {contact.job_title ?? 'Keine Funktion'} · {labelOf(lifecycleOptions, contact.lifecycle_phase)}
                {contact.last_contact_at ? ` · Letzter Kontakt ${formatDateTime(contact.last_contact_at)}` : ''}
              </p>
            </li>
          )
        })}
      </ul>
    </div>
  )
}
