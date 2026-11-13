import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, createTicketTask, deleteAttachment, fetchTicket, postTicket, uploadAttachment } from '../../api/service.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { choiceLabel, formatDate, formatDateTime } from '../../domain/partners.ts'
import {
  eventLabels,
  resolutionOptions,
  ticketCategoryOptions,
  ticketPriorityOptions,
  ticketStatusOptions,
  type TicketDetail,
} from '../../domain/service.ts'
import { labelOf, taskPriorityOptions, taskStatusOptions } from '../../domain/crm.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const ACTOR_KEY = 'hoplogic-actor-name'

function storedActor(): string {
  return sessionStorage.getItem(ACTOR_KEY) ?? ''
}

export function TicketDetailPage() {
  const { ticketId = '' } = useParams()
  const [ticket, setTicket] = useState<TicketDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(true)
  const [actor, setActor] = useState(storedActor)
  const [note, setNote] = useState('')
  const [owner, setOwner] = useState('')
  const [resolution, setResolution] = useState('logistik')
  const [resolutionNote, setResolutionNote] = useState('')
  const [taskTitle, setTaskTitle] = useState('')
  const [taskDue, setTaskDue] = useState('')
  const [removeId, setRemoveId] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  usePageTitle(ticket ? ticket.ticket_number : 'Service-Ticket')

  useEffect(() => {
    let active = true
    void fetchTicket(ticketId)
      .then((loaded) => {
        if (!active) return
        setTicket(loaded)
        setOwner(loaded.account_owner ?? '')
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(caught instanceof ApiError ? caught.message : 'Das Ticket konnte nicht geladen werden.')
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [ticketId])

  function rememberActor(value: string) {
    setActor(value)
    sessionStorage.setItem(ACTOR_KEY, value)
  }

  async function run(action: () => Promise<TicketDetail | void>) {
    setBusy(true)
    setError(null)
    try {
      const next = await action()
      if (next) {
        setTicket(next)
        setOwner(next.account_owner ?? '')
      } else {
        setTicket(await fetchTicket(ticketId))
      }
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Die Aktion konnte nicht gespeichert werden.')
    } finally {
      setBusy(false)
    }
  }

  if (pending) return <LoadingState label="Ticket wird geladen" />
  if (!ticket) return <ErrorState title="Ticket nicht verfügbar" description={error ?? 'Das Ticket wurde nicht gefunden.'} />

  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm text-muted">{ticket.ticket_number}</p>
          <h1 className="text-3xl font-semibold tracking-tight">{ticket.subject}</h1>
          <div className="mt-2 flex flex-wrap gap-2">
            <Badge tone="petrol">{choiceLabel(ticketStatusOptions, ticket.status)}</Badge>
            <Badge tone={ticket.priority === 'kritisch' || ticket.priority === 'hoch' ? 'warning' : 'neutral'}>{choiceLabel(ticketPriorityOptions, ticket.priority)}</Badge>
            {ticket.is_overdue ? <Badge tone="critical">Überfällig</Badge> : null}
            {ticket.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
          </div>
        </div>
        <Link to={`/kundenservice/${ticket.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Ticket bearbeiten
        </Link>
      </header>
      <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6">
        Eine dokumentierte Lösung ist keine ausgeführte ERP-Massnahme. Das CRM löst keine Ersatzlieferung und keine Gutschrift aus.
        Dateien liegen unter data/ticket-attachments und sind nicht öffentlich. Ohne Anmeldung ist der Upload nicht für einen öffentlichen Produktivbetrieb geeignet.
      </p>
      {error ? <ErrorState title="Aktion nicht gespeichert" description={error} /> : null}
      <Card className="grid gap-4 p-4 sm:grid-cols-2">
        <Fact label="Kategorie" value={choiceLabel(ticketCategoryOptions, ticket.category)} />
        <Fact label="Vertriebspartner" value={<Link className="text-petrol" to={`/vertriebspartner/${ticket.partner_id}`}>{ticket.company_name}</Link>} />
        <Fact label="Kontaktperson" value={ticket.contact_id ? <Link className="text-petrol" to={`/kontakte/${ticket.contact_id}`}>{ticket.contact_name}</Link> : 'Keine'} />
        <Fact label="Zuständige Person" value={ticket.account_owner ?? 'Nicht zugewiesen'} />
        <Fact label="Bestellung" value={ticket.order_id ? <Link className="text-petrol" to={`/bestellungen/${ticket.order_id}`}>{ticket.order_number}</Link> : 'Keine'} />
        <Fact label="Erstellungsdatum" value={formatDateTime(ticket.created_at)} />
        <Fact label="Letzte Aktualisierung" value={formatDateTime(ticket.updated_at)} />
        <Fact label="Gewünschtes Erledigungsdatum" value={ticket.due_on ? formatDate(ticket.due_on) : 'Keines'} />
        <div className="sm:col-span-2">
          <h2 className="text-sm font-semibold">Beschreibung</h2>
          <p className="mt-1 whitespace-pre-wrap text-sm leading-6">{ticket.description}</p>
        </div>
        <div className="sm:col-span-2">
          <h2 className="text-sm font-semibold">Interne Bemerkung</h2>
          <p className="mt-1 text-sm leading-6 text-muted">Keine Kundennachricht.</p>
          <p className="mt-1 whitespace-pre-wrap text-sm leading-6">{ticket.internal_remark ?? 'Keine interne Bemerkung.'}</p>
        </div>
        <div className="sm:col-span-2">
          <h2 className="text-sm font-semibold">Betroffene Produkte</h2>
          {ticket.products.length === 0 ? <p className="mt-1 text-sm text-muted">Keine Produkte zugeordnet.</p> : (
            <ul className="mt-1 text-sm">
              {ticket.products.map((product) => <li key={product.id}>{product.name} · {product.sku}</li>)}
            </ul>
          )}
        </div>
      </Card>

      <Card className="grid gap-3 p-4">
        <h2 className="font-semibold">Bearbeitung</h2>
        <Input label="Name für den Verlauf" hint="Freiwillige Anzeige. Es gibt keine Benutzeranmeldung." value={actor} onChange={(event) => rememberActor(event.target.value)} />
        <div className="flex flex-wrap items-end gap-2">
          <div className="min-w-56 flex-1">
            <Input label="Zuweisen an" value={owner} onChange={(event) => setOwner(event.target.value)} />
          </div>
          <Button disabled={busy} onClick={() => void run(() => postTicket(ticket.id, 'assign', { account_owner: owner || null, changed_by: actor || null }))}>
            Ticket zuweisen
          </Button>
        </div>
        <div className="flex flex-wrap gap-2">
          {ticketPriorityOptions.map((option) => (
            <Button key={option.value} variant="secondary" disabled={busy || option.value === ticket.priority} onClick={() => void run(() => postTicket(ticket.id, 'priority', { priority: option.value, changed_by: actor || null }))}>
              Priorität {option.label}
            </Button>
          ))}
        </div>
        <div className="flex flex-wrap gap-2">
          {ticket.allowed_statuses.map((status) => (
            <Button key={status} variant="secondary" disabled={busy} onClick={() => void run(() => postTicket(ticket.id, 'status', { status, changed_by: actor || null }))}>
              Status {choiceLabel(ticketStatusOptions, status)}
            </Button>
          ))}
          {ticket.can_reopen ? (
            <Button disabled={busy} onClick={() => void run(() => postTicket(ticket.id, 'reopen', { changed_by: actor || null }))}>
              Wieder öffnen
            </Button>
          ) : null}
          {ticket.can_close ? (
            <Button variant="danger" disabled={busy} onClick={() => void run(() => postTicket(ticket.id, 'close', { changed_by: actor || null }))}>
              Ticket schliessen
            </Button>
          ) : null}
        </div>
        {ticket.can_resolve ? (
          <form
            className="grid gap-2 border border-line p-3"
            onSubmit={(event: FormEvent) => {
              event.preventDefault()
              void run(() => postTicket(ticket.id, 'resolve', { code: resolution, note: resolutionNote || null, changed_by: actor || null }))
            }}
          >
            <h3 className="text-sm font-semibold">Lösung dokumentieren</h3>
            <p className="text-sm text-muted">Der Eintrag bleibt im Verlauf. Er erzeugt keinen ERP-Vorgang.</p>
            <Select label="Lösung" value={resolution} onChange={setResolution} options={resolutionOptions} />
            <Textarea label="Lösungsnotiz" value={resolutionNote} onChange={(event) => setResolutionNote(event.target.value)} />
            <Button type="submit" disabled={busy}>Ticket lösen</Button>
          </form>
        ) : null}
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold">Dokumentierte Lösungen</h2>
        {ticket.resolutions.length === 0 ? <p className="mt-2 text-sm text-muted">Noch keine Lösung erfasst.</p> : (
          <ul className="mt-2 grid gap-2 text-sm">
            {ticket.resolutions.map((item) => (
              <li key={item.id}>
                <span className="font-semibold">{choiceLabel(resolutionOptions, item.code)}</span>
                {' · '}
                {formatDateTime(item.recorded_at)}
                {item.recorded_by ? ` · ${item.recorded_by}` : ''}
                {item.note ? <span className="block">{item.note}</span> : null}
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold">Interne Notiz</h2>
        <p className="mt-1 text-sm text-muted">Notizen sind intern. Eine Nachricht an die Kundschaft ist hier nicht vorgesehen.</p>
        <form
          className="mt-3 grid gap-2"
          onSubmit={(event) => {
            event.preventDefault()
            void run(async () => {
              const next = await postTicket(ticket.id, 'notes', { note, changed_by: actor || null })
              setNote('')
              return next
            })
          }}
        >
          <Textarea label="Notiz" value={note} onChange={(event) => setNote(event.target.value)} />
          <Button type="submit" disabled={busy || !note.trim()}>Interne Notiz hinzufügen</Button>
        </form>
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold">Folgeaufgabe</h2>
        <form
          className="mt-3 grid gap-2 md:grid-cols-2"
          onSubmit={(event) => {
            event.preventDefault()
            void run(async () => {
              await createTicketTask(ticket.id, {
                title: taskTitle,
                due_at: new Date(taskDue).toISOString(),
                priority: 'hoch',
                account_owner: actor || ticket.account_owner,
                changed_by: actor || null,
              })
              setTaskTitle('')
              setTaskDue('')
            })
          }}
        >
          <Input label="Titel" value={taskTitle} onChange={(event) => setTaskTitle(event.target.value)} required />
          <Input label="Fällig" type="datetime-local" value={taskDue} onChange={(event) => setTaskDue(event.target.value)} required />
          <Button type="submit" disabled={busy}>Folgeaufgabe erstellen</Button>
        </form>
        <ul className="mt-3 grid gap-2 text-sm">
          {ticket.tasks.map((task) => (
            <li key={task.id}>
              <Link to={`/aufgaben/${task.id}/bearbeiten`} className="font-semibold text-petrol">{task.title}</Link>
              {' · '}
              {labelOf(taskStatusOptions, task.status)}
              {' · '}
              {labelOf(taskPriorityOptions, task.priority)}
              {' · '}
              {formatDateTime(task.due_at)}
            </li>
          ))}
        </ul>
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold">Anhänge</h2>
        <Input
          label="Datei hinzufügen"
          type="file"
          accept=".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png"
          hint="PDF, JPG oder PNG, höchstens 5 MB. Zugriff nur über diese Ticketansicht."
          onChange={(event) => {
            const file = event.target.files?.[0]
            event.target.value = ''
            if (!file) return
            void run(async () => {
              await uploadAttachment(ticket.id, file)
            })
          }}
        />
        <ul className="mt-3 grid gap-2 text-sm">
          {ticket.attachments.map((file) => (
            <li key={file.id} className="flex flex-wrap items-center justify-between gap-2">
              <a className="font-semibold text-petrol" href={`/api/tickets/${ticket.id}/attachments/${file.id}`}>
                {file.original_name}
              </a>
              <span className="text-muted">{Math.ceil(file.size_bytes / 1024)} KB</span>
              <Button variant="danger" disabled={busy} onClick={() => setRemoveId(file.id)}>Entfernen</Button>
            </li>
          ))}
        </ul>
      </Card>

      <Card className="p-4">
        <h2 className="font-semibold">Bearbeitungsverlauf</h2>
        <ol className="mt-3 grid gap-3">
          {ticket.events.map((event) => (
            <li key={event.id} className="border-l-2 border-petrol pl-3">
              <p className="text-sm font-semibold">{eventLabels[event.event_type] ?? event.event_type}</p>
              <p className="text-sm text-muted">
                {formatDateTime(event.changed_at)}
                {event.changed_by ? ` · ${event.changed_by}` : ' · ohne Personenangabe'}
              </p>
              {event.from_value || event.to_value ? (
                <p className="text-sm">
                  {event.from_value ? displayValue(event.event_type, event.from_value, 'from') : '—'}
                  {' → '}
                  {event.to_value ? displayValue(event.event_type, event.to_value, 'to') : '—'}
                </p>
              ) : null}
              {event.note ? <p className="text-sm leading-6">{event.note}</p> : null}
            </li>
          ))}
        </ol>
      </Card>

      <ConfirmDialog
        open={removeId !== null}
        title="Anhang entfernen"
        description="Die Datei wird vom Ticket gelöst und aus dem Speicherort gelöscht."
        confirmLabel="Entfernen"
        tone="danger"
        onCancel={() => setRemoveId(null)}
        onConfirm={() => {
          const id = removeId
          setRemoveId(null)
          if (!id) return
          void run(async () => {
            await deleteAttachment(ticket.id, id)
          })
        }}
      />
    </div>
  )
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</p>
      <div className="mt-1 text-sm leading-6">{value}</div>
    </div>
  )
}

function displayValue(eventType: string, value: string, side: 'from' | 'to'): string {
  if (eventType === 'resolved' && side === 'to') return choiceLabel(resolutionOptions, value)
  if (eventType === 'status_changed' || eventType === 'closed' || eventType === 'reopened' || eventType === 'created' || eventType === 'resolved') {
    return choiceLabel(ticketStatusOptions, value)
  }
  if (eventType === 'priority_changed') return choiceLabel(ticketPriorityOptions, value)
  return value
}
