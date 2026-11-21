import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import { ApiError, fetchPartners } from '../../api/partners.ts'
import type { Partner } from '../../domain/partners.ts'
import {
  addFestivalNote,
  checkAvailability,
  createAssignment,
  createDelivery,
  createFestival,
  createMaterial,
  createQuote,
  createReservation,
  downloadPdf,
  getCalendar,
  getDashboard,
  getFestival,
  listAssignments,
  listDeliveries,
  listFestivals,
  listMaterials,
  listMovements,
  listQuotes,
  listReservations,
  postFestivalAction,
  postStock,
  quoteAction,
  reservationAction,
  updateDelivery,
  updateFestival,
} from '../../api/festivals.ts'
import { useAuth } from '../../auth.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { DataTable } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Tabs } from '../../components/ui/Tabs.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { useToast } from '../../components/ui/toast-state.ts'
import {
  assignmentKindOptions,
  deliveryStatusOptions,
  eventStatusOptions,
  eventTypeOptions,
  festivalAreas,
  formatAmount,
  formatDay,
  formatStamp,
  fromZurichInput,
  labelOf,
  materialStatusOptions,
  quoteStatusOptions,
  requestStatusOptions,
  reservationStatusOptions,
  statusTone,
  toZurichInput,
  zurichKey,
  type Festival,
} from '../../domain/festivals.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

function FestivalNav() {
  return (
    <nav aria-label="Festmanagement" className="flex gap-2 overflow-x-auto pb-1">
      {festivalAreas.map((area) => (
        <Link key={area.path} to={area.path} className={cx(buttonStyles.base, buttonStyles.secondary, 'shrink-0')}>
          {area.label}
        </Link>
      ))}
    </nav>
  )
}

function PageFrame({ title, children }: { title: string; children: ReactNode }) {
  usePageTitle(title)
  return (
    <div className="grid gap-4">
      <FestivalNav />
      {children}
    </div>
  )
}

export function FestivalListPage({ mode = 'all' }: { mode?: 'all' | 'requests' }) {
  const title = mode === 'requests' ? 'Festanfragen' : 'Festübersicht'
  const [params, setParams] = useSearchParams()
  const [rows, setRows] = useState<Festival[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const query = params.toString()

  useEffect(() => {
    let cancelled = false
    const search = new URLSearchParams(query)
    if (mode === 'requests' && !search.get('request_status')) {
      search.set('request_status', 'neue_anfrage')
    }
    listFestivals(search)
      .then((result) => {
        if (!cancelled) {
          setRows(result.items)
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.')
        }
      })
    return () => {
      cancelled = true
    }
  }, [mode, query])

  function setFilter(key: string, value: string) {
    const next = new URLSearchParams(params)
    if (value) {
      next.set(key, value)
    } else {
      next.delete(key)
    }
    setParams(next)
  }

  return (
    <PageFrame title={title}>
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-ink">{title}</h1>
          <p className="mt-1 max-w-3xl text-sm leading-6 text-muted">
            Veranstalter, Gastronomiebetriebe und Getränkehändler bleiben getrennte Rollen. Eine Anfrage reserviert noch kein Material.
          </p>
        </div>
        <Link to="/festmanagement/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Neues Fest
        </Link>
      </div>
      <Card className="grid gap-3 p-4 md:grid-cols-4">
        <Input label="Suche" value={params.get('q') ?? ''} onChange={(event) => setFilter('q', event.target.value)} />
        <Select
          label="Feststatus"
          value={params.get('status') ?? ''}
          onChange={(value) => setFilter('status', value)}
          options={[{ value: '', label: 'Alle' }, ...eventStatusOptions]}
        />
        <Select
          label={mode === 'requests' ? 'Anfragestatus' : 'Anfrage'}
          value={params.get('request_status') ?? (mode === 'requests' ? 'neue_anfrage' : '')}
          onChange={(value) => setFilter('request_status', value)}
          options={[{ value: '', label: 'Alle' }, ...requestStatusOptions]}
        />
        <Input label="Region" value={params.get('region') ?? ''} onChange={(event) => setFilter('region', event.target.value)} />
        <Input label="Veranstalter" value={params.get('organizer') ?? ''} onChange={(event) => setFilter('organizer', event.target.value)} />
        <Input label="Von" type="date" value={params.get('date_from') ?? ''} onChange={(event) => setFilter('date_from', event.target.value)} />
        <Input label="Bis" type="date" value={params.get('date_to') ?? ''} onChange={(event) => setFilter('date_to', event.target.value)} />
      </Card>
      {error ? <ErrorState title="Festliste nicht geladen" description={error} /> : null}
      {rows === null && !error ? <LoadingState label="Feste werden geladen" /> : null}
      {rows ? (
        <Card>
          <DataTable
            caption="Feste"
            rows={rows}
            rowKey={(row) => row.id}
            empty={<EmptyState title="Keine Feste" description="Für diese Filter gibt es noch keine Veranstaltung." compact />}
            columns={[
              { id: 'number', header: 'Festnummer', cell: (row) => row.event_number },
              {
                id: 'name',
                header: 'Fest',
                cell: (row) => (
                  <Link to={`/festmanagement/${row.id}`} className="font-semibold text-petrol">
                    {row.name}
                  </Link>
                ),
              },
              { id: 'organizer', header: 'Veranstalter', cell: (row) => row.organizer_name },
              { id: 'place', header: 'Ort', cell: (row) => [row.city, row.region].filter(Boolean).join(', ') || '–' },
              { id: 'start', header: 'Beginn', cell: (row) => formatStamp(row.starts_at) },
              { id: 'end', header: 'Ende', cell: (row) => formatStamp(row.ends_at) },
              { id: 'owner', header: 'Zuständig', cell: (row) => row.account_owner || '–' },
              { id: 'event', header: 'Feststatus', cell: (row) => <Badge tone={statusTone(row.event_status)}>{labelOf(eventStatusOptions, row.event_status)}</Badge> },
              { id: 'material', header: 'Material', cell: (row) => <Badge tone={statusTone(row.material_status)}>{labelOf(materialStatusOptions, row.material_status)}</Badge> },
              { id: 'quote', header: 'Offerte', cell: (row) => labelOf(quoteStatusOptions, row.quote_status) },
              { id: 'delivery', header: 'Lieferung', cell: (row) => labelOf(deliveryStatusOptions, row.delivery_status) },
            ]}
          />
        </Card>
      ) : null}
    </PageFrame>
  )
}

const emptyForm = {
  name: '',
  organizer_name: '',
  organizer_partner_id: '',
  distributor_partner_id: '',
  event_type: 'fest',
  contact_name: '',
  phone: '',
  email: '',
  venue_name: '',
  street: '',
  postal_code: '',
  city: '',
  region: '',
  country: 'Schweiz',
  starts_at: '',
  ends_at: '',
  expected_visitors: '',
  account_owner: '',
  description: '',
  drinks: '',
  material_wish: '',
  requirements: '',
  notes: '',
  change_reason: '',
}

export function FestivalFormPage() {
  const { festivalId } = useParams()
  const navigate = useNavigate()
  const { notify } = useToast()
  const [form, setForm] = useState(emptyForm)
  const [partners, setPartners] = useState<Partner[]>([])
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(false)
  usePageTitle(festivalId ? 'Fest bearbeiten' : 'Neues Fest')

  useEffect(() => {
    let cancelled = false
    fetchPartners({ q: '', status: '', industry: '', region: '', accountOwner: '', sort: 'name', direction: 'asc', page: 1, pageSize: 100, includeArchived: false })
      .then((list) => {
        if (!cancelled) setPartners(list.items)
      })
      .catch(() => {
        if (!cancelled) setPartners([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!festivalId) {
      return
    }
    let cancelled = false
    getFestival(festivalId)
      .then((row) => {
        if (cancelled) {
          return
        }
        const event = row as unknown as Festival
        setForm({
          ...emptyForm,
          name: event.name,
          organizer_name: event.organizer_name,
          organizer_partner_id: event.organizer_partner_id ?? '',
          distributor_partner_id: event.distributor_partner_id ?? '',
          event_type: event.event_type,
          contact_name: event.contact_name ?? '',
          phone: event.phone ?? '',
          email: event.email ?? '',
          venue_name: event.venue_name ?? '',
          street: event.street ?? '',
          postal_code: event.postal_code ?? '',
          city: event.city ?? '',
          region: event.region ?? '',
          country: event.country,
          starts_at: toZurichInput(event.starts_at),
          ends_at: toZurichInput(event.ends_at),
          expected_visitors: event.expected_visitors?.toString() ?? '',
          account_owner: event.account_owner ?? '',
          description: event.description ?? '',
          drinks: event.drinks ?? '',
          material_wish: event.material_wish ?? '',
          requirements: event.requirements ?? '',
          notes: event.notes ?? '',
        })
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : 'Das Fest wurde nicht gefunden.')
        }
      })
    return () => {
      cancelled = true
    }
  }, [festivalId])

  function setField(key: keyof typeof emptyForm, value: string) {
    setForm((current) => ({ ...current, [key]: value }))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    const payload: Record<string, unknown> = {
      name: form.name,
      organizer_name: form.organizer_name,
      organizer_partner_id: form.organizer_partner_id || null,
      distributor_partner_id: form.distributor_partner_id || null,
      event_type: form.event_type,
      contact_name: form.contact_name || null,
      phone: form.phone || null,
      email: form.email || null,
      venue_name: form.venue_name || null,
      street: form.street || null,
      postal_code: form.postal_code || null,
      city: form.city || null,
      region: form.region || null,
      country: form.country || 'Schweiz',
      starts_at: fromZurichInput(form.starts_at),
      ends_at: fromZurichInput(form.ends_at),
      expected_visitors: form.expected_visitors ? Number(form.expected_visitors) : null,
      account_owner: form.account_owner || null,
      description: form.description || null,
      drinks: form.drinks || null,
      material_wish: form.material_wish || null,
      requirements: form.requirements || null,
      notes: form.notes || null,
    }
    try {
      const saved = festivalId
        ? await updateFestival(festivalId, { ...payload, change_reason: form.change_reason })
        : await createFestival(payload)
      notify({ tone: 'success', message: festivalId ? 'Das Fest wurde gespeichert.' : 'Die Festanfrage wurde erfasst.' })
      navigate(`/festmanagement/${saved.id}`)
    } catch (caught) {
      notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.' })
    } finally {
      setPending(false)
    }
  }

  return (
    <PageFrame title={festivalId ? 'Fest bearbeiten' : 'Neues Fest'}>
      <h1 className="text-2xl font-semibold text-ink">{festivalId ? 'Fest bearbeiten' : 'Festanfrage erfassen'}</h1>
      {error ? <ErrorState title="Fest nicht geladen" description={error} /> : null}
      <form className="grid gap-4" onSubmit={submit}>
        <Card className="grid gap-3 p-4 md:grid-cols-2">
          <Input label="Festname" value={form.name} onChange={(event) => setField('name', event.target.value)} required />
          <Select label="Veranstaltungsart" value={form.event_type} onChange={(value) => setField('event_type', value)} options={eventTypeOptions} />
          <Input label="Veranstalter" value={form.organizer_name} onChange={(event) => setField('organizer_name', event.target.value)} required />
          <Select
            label="Zugeordneter Veranstalter"
            value={form.organizer_partner_id}
            onChange={(value) => {
              setField('organizer_partner_id', value)
              const partner = partners.find((row) => row.id === value)
              if (partner) setField('organizer_name', partner.company_name)
            }}
            options={[{ value: '', label: 'Keiner' }, ...partners.filter((row) => row.partner_type === 'veranstalter').map((row) => ({ value: row.id, label: row.company_name }))]}
          />
          <Select
            label="Getränkehändler"
            value={form.distributor_partner_id}
            onChange={(value) => setField('distributor_partner_id', value)}
            options={[{ value: '', label: 'Keiner' }, ...partners.filter((row) => row.partner_type === 'getraenkehaendler').map((row) => ({ value: row.id, label: row.company_name }))]}
          />
          <Input label="Kontaktperson" value={form.contact_name} onChange={(event) => setField('contact_name', event.target.value)} />
          <Input label="Telefon" value={form.phone} onChange={(event) => setField('phone', event.target.value)} />
          <Input label="E-Mail" type="email" value={form.email} onChange={(event) => setField('email', event.target.value)} />
          <Input label="Veranstaltungsort" value={form.venue_name} onChange={(event) => setField('venue_name', event.target.value)} />
          <Input label="Strasse" value={form.street} onChange={(event) => setField('street', event.target.value)} />
          <Input label="Postleitzahl" value={form.postal_code} onChange={(event) => setField('postal_code', event.target.value)} />
          <Input label="Ort" value={form.city} onChange={(event) => setField('city', event.target.value)} />
          <Input label="Region" value={form.region} onChange={(event) => setField('region', event.target.value)} />
          <Input label="Land" value={form.country} onChange={(event) => setField('country', event.target.value)} />
          <Input label="Beginn" type="datetime-local" value={form.starts_at} onChange={(event) => setField('starts_at', event.target.value)} required />
          <Input label="Ende" type="datetime-local" value={form.ends_at} onChange={(event) => setField('ends_at', event.target.value)} required />
          <Input label="Erwartete Besucherzahl" value={form.expected_visitors} onChange={(event) => setField('expected_visitors', event.target.value)} />
          <Input label="Zuständige Mitarbeiterin oder Mitarbeiter" value={form.account_owner} onChange={(event) => setField('account_owner', event.target.value)} />
        </Card>
        <Card className="grid gap-3 p-4">
          <Textarea label="Beschreibung" value={form.description} onChange={(event) => setField('description', event.target.value)} />
          <Textarea label="Gewünschte Getränke" value={form.drinks} onChange={(event) => setField('drinks', event.target.value)} />
          <Textarea label="Benötigtes Festmaterial" value={form.material_wish} onChange={(event) => setField('material_wish', event.target.value)} />
          <Textarea label="Besondere Anforderungen" value={form.requirements} onChange={(event) => setField('requirements', event.target.value)} />
          <Textarea label="Bemerkungen" value={form.notes} onChange={(event) => setField('notes', event.target.value)} />
          {festivalId ? (
            <Input label="Änderungsgrund" value={form.change_reason} onChange={(event) => setField('change_reason', event.target.value)} required />
          ) : null}
          <p className="text-xs leading-5 text-muted">Zeiten gelten in Europe/Zurich. Ein Veranstalter ist nicht automatisch ein Bierkunde. Das Speichern wartet auf die Bestätigung des Servers.</p>
          <Button type="submit" disabled={pending}>
            {pending ? 'Wird gespeichert' : 'Speichern'}
          </Button>
        </Card>
      </form>
    </PageFrame>
  )
}

export function FestivalDetailPage() {
  const { festivalId = '' } = useParams()
  const { can } = useAuth()
  const { notify } = useToast()
  const [detail, setDetail] = useState<Record<string, unknown> | null>(null)
  const [materials, setMaterials] = useState<Array<Record<string, unknown>>>([])
  const [error, setError] = useState<string | null>(null)
  const [tick, setTick] = useState(0)
  const event = detail as unknown as Festival | null

  useEffect(() => {
    let cancelled = false
    Promise.all([getFestival(festivalId), listMaterials()])
      .then(([festival, stock]) => {
        if (!cancelled) {
          setDetail(festival)
          setMaterials(stock.items)
        }
      })
      .catch((caught: unknown) => {
        if (!cancelled) {
          setError(caught instanceof ApiError ? caught.message : 'Das Fest wurde nicht gefunden.')
        }
      })
    return () => {
      cancelled = true
    }
  }, [festivalId, tick])

  async function run(action: () => Promise<unknown>, success: string) {
    try {
      await action()
      notify({ tone: 'success', message: success })
      setTick((value) => value + 1)
    } catch (caught) {
      notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.' })
    }
  }

  if (error) {
    return (
      <PageFrame title="Fest">
        <ErrorState title="Fest nicht gefunden" description={error} />
      </PageFrame>
    )
  }
  if (!event) {
    return (
      <PageFrame title="Fest">
        <LoadingState label="Fest wird geladen" />
      </PageFrame>
    )
  }

  const quotes = (detail?.quotes as Array<Record<string, unknown>>) ?? []
  const reservations = (detail?.reservations as Array<Record<string, unknown>>) ?? []
  const deliveries = (detail?.deliveries as Array<Record<string, unknown>>) ?? []
  const assignments = (detail?.assignments as Array<Record<string, unknown>>) ?? []
  const changes = (detail?.changes as Array<Record<string, unknown>>) ?? []
  const activities = (detail?.activities as Array<Record<string, unknown>>) ?? []
  const tasks = (detail?.tasks as Array<Record<string, unknown>>) ?? []
  const tickets = (detail?.tickets as Array<Record<string, unknown>>) ?? []

  return (
    <PageFrame title={event.name}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold tracking-wide text-muted uppercase">{event.event_number}</p>
          <h1 className="text-2xl font-semibold text-ink">{event.name}</h1>
          <p className="mt-1 text-sm text-muted">
            {event.organizer_name} · {formatStamp(event.starts_at)} bis {formatStamp(event.ends_at)}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to={`/festmanagement/${event.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Bearbeiten
          </Link>
          {can('festivals.write') ? (
            <Button variant="secondary" onClick={() => run(() => postFestivalAction(event.id, 'duplicate'), 'Das Fest wurde dupliziert.')}>
              Duplizieren
            </Button>
          ) : null}
          {can('festivals.confirm') && !event.is_binding ? (
            <Button onClick={() => run(() => postFestivalAction(event.id, 'convert'), 'Der Festauftrag wurde bestätigt.')}>Auftrag bestätigen</Button>
          ) : null}
          {can('festivals.confirm') ? (
            <Button variant="secondary" onClick={() => run(() => postFestivalAction(event.id, 'close'), 'Das Fest wurde abgeschlossen.')}>
              Abschliessen
            </Button>
          ) : null}
          {can('festivals.archive') ? (
            <Button variant="secondary" onClick={() => run(() => postFestivalAction(event.id, event.archived_at ? 'restore' : 'archive'), event.archived_at ? 'Das Fest wurde wiederhergestellt.' : 'Das Fest wurde archiviert.')}>
              {event.archived_at ? 'Wiederherstellen' : 'Archivieren'}
            </Button>
          ) : null}
        </div>
      </div>
      {event.is_demo ? (
        <p className="border border-line bg-cream-deep px-4 py-3 text-sm leading-6">Fiktiver Testdatensatz. Keine echte Veranstaltung des Liechtensteiner Brauhauses.</p>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Badge tone={statusTone(event.event_status)}>{labelOf(eventStatusOptions, event.event_status)}</Badge>
        <Badge tone={statusTone(event.material_status)}>{labelOf(materialStatusOptions, event.material_status)}</Badge>
        <Badge tone={statusTone(event.quote_status)}>{labelOf(quoteStatusOptions, event.quote_status)}</Badge>
        <Badge>{labelOf(deliveryStatusOptions, event.delivery_status)}</Badge>
        <Badge tone={event.is_binding ? 'success' : 'neutral'}>{event.is_binding ? 'Verbindlicher Festauftrag' : 'Unverbindliche Anfrage'}</Badge>
      </div>
      <Tabs
        label="Festbereiche"
        tabs={[
          {
            id: 'overview',
            label: 'Übersicht',
            content: (
              <Card className="grid gap-2 p-4 text-sm leading-6">
                <p>Ort: {[event.venue_name, event.street, event.postal_code, event.city, event.region, event.country].filter(Boolean).join(', ') || '–'}</p>
                <p>Kontakt: {[event.contact_name, event.phone, event.email].filter(Boolean).join(' · ') || '–'}</p>
                <p>Zuständig: {event.account_owner || '–'}</p>
                <p>
                  Veranstalter im CRM: {event.organizer_partner_id ? <Link to={`/vertriebspartner/${event.organizer_partner_id}`}>{event.organizer_name}</Link> : 'Nur als Name erfasst, nicht als Vertriebspartner'}
                </p>
                <p>
                  Getränkehändler: {event.distributor_partner_id ? <Link to={`/vertriebspartner/${event.distributor_partner_id}`}>Zugeordneter Händler</Link> : 'Keiner zugeordnet'}
                </p>
                <p>Besucherzahl: {event.expected_visitors ?? '–'}</p>
                <p>Getränke: {event.drinks || '–'}</p>
                <p>Materialwunsch: {event.material_wish || '–'}</p>
                <p>Anforderungen: {event.requirements || '–'}</p>
                <p>Bemerkungen: {event.notes || '–'}</p>
                <p>Getränkebestellung: {event.order_id ? <Link to={`/bestellungen/${event.order_id}`}>Verknüpfte CRM-Bestellung</Link> : 'Keine direkte Bestellung. Der Veranstalter ist nicht automatisch Bierkunde.'}</p>
              </Card>
            ),
          },
          {
            id: 'quotes',
            label: 'Offerten',
            content: <QuotePanel festivalId={event.id} quotes={quotes} canWrite={can('festivals.write')} canConfirm={can('festivals.confirm')} onDone={() => setTick((value) => value + 1)} />,
          },
          {
            id: 'material',
            label: 'Material',
            content: <ReservationPanel festivalId={event.id} starts={event.starts_at} ends={event.ends_at} binding={event.is_binding} reservations={reservations} materials={materials} canReserve={can('materials.reserve')} canIssue={can('materials.issue')} canDraft={can('festivals.write') || can('materials.reserve')} onDone={() => setTick((value) => value + 1)} />,
          },
          {
            id: 'transport',
            label: 'Transporte',
            content: <DeliveryPanel festivalId={event.id} deliveries={deliveries} canWrite={can('materials.issue') || can('festivals.write')} onDone={() => setTick((value) => value + 1)} />,
          },
          {
            id: 'assignments',
            label: 'Einsätze',
            content: <AssignmentPanel festivalId={event.id} assignments={assignments} canWrite={can('festivals.write') || can('materials.issue')} onDone={() => setTick((value) => value + 1)} />,
          },
          {
            id: 'activities',
            label: 'Aktivitäten',
            content: (
              <Card className="grid gap-3 p-4">
                {activities.length === 0 ? <EmptyState title="Keine Aktivitäten" description="Telefonate und Notizen erscheinen hier, sobald sie gespeichert sind." compact /> : null}
                {activities.map((row) => (
                  <p key={String(row.id)} className="text-sm">{formatStamp(String(row.occurred_at))} · {String(row.title)}</p>
                ))}
                {tasks.map((row) => (
                  <p key={String(row.id)} className="text-sm">Aufgabe: {String(row.title)} · {String(row.status)} · {formatStamp(String(row.due_at))}</p>
                ))}
                <NoteForm festivalId={event.id} onDone={() => setTick((value) => value + 1)} />
              </Card>
            ),
          },
          {
            id: 'documents',
            label: 'Dokumente',
            content: (
              <Card className="grid gap-2 p-4 text-sm">
                {quotes.map((quote) => (
                  <button key={String(quote.id)} className="text-left text-petrol" type="button" onClick={() => downloadPdf(`/api/festivals/quotes/${quote.id}/pdf`, `${quote.quote_number}.pdf`).catch(() => notify({ tone: 'critical', message: 'Die Offerte konnte nicht erzeugt werden.' }))}>
                    PDF-Offerte {String(quote.quote_number)} Version {String(quote.version)}
                  </button>
                ))}
                {deliveries.map((row) => (
                  <button key={String(row.id)} className="text-left text-petrol" type="button" onClick={() => downloadPdf(`/api/festivals/deliveries/${row.id}/pdf`, `lieferschein.pdf`).catch(() => notify({ tone: 'critical', message: 'Der Lieferschein konnte nicht erzeugt werden.' }))}>
                    PDF-Lieferschein
                  </button>
                ))}
                {tickets.map((row) => (
                  <Link key={String(row.id)} to={`/kundenservice/${row.id}`}>{String(row.ticket_number)} · {String(row.subject)}</Link>
                ))}
                {quotes.length + deliveries.length + tickets.length === 0 ? <EmptyState title="Keine Dokumente" description="Offerten und Lieferscheine werden als PDF erzeugt." compact /> : null}
              </Card>
            ),
          },
          {
            id: 'history',
            label: 'Historie',
            content: (
              <Card>
                <DataTable
                  caption="Änderungen"
                  rows={changes}
                  rowKey={(row) => String(row.id)}
                  empty={<EmptyState title="Keine Änderungen" description="Änderungen mit Grund werden hier protokolliert." compact />}
                  columns={[
                    { id: 'time', header: 'Zeit', cell: (row) => formatStamp(String(row.changed_at)) },
                    { id: 'actor', header: 'Person', cell: (row) => String(row.actor_label ?? '–') },
                    { id: 'field', header: 'Feld', cell: (row) => String(row.field_name) },
                    { id: 'old', header: 'Vorher', cell: (row) => String(row.old_value ?? '–') },
                    { id: 'new', header: 'Nachher', cell: (row) => String(row.new_value ?? '–') },
                    { id: 'reason', header: 'Grund', cell: (row) => String(row.reason ?? '–') },
                  ]}
                />
              </Card>
            ),
          },
        ]}
      />
    </PageFrame>
  )
}

function NoteForm({ festivalId, onDone }: { festivalId: string; onDone: () => void }) {
  const { notify } = useToast()
  const [title, setTitle] = useState('Telefonische Änderung')
  const [description, setDescription] = useState('')
  return (
    <form
      className="grid gap-2"
      onSubmit={(event) => {
        event.preventDefault()
        addFestivalNote(festivalId, title, description)
          .then(() => {
            notify({ tone: 'success', message: 'Die Notiz wurde gespeichert.' })
            setDescription('')
            onDone()
          })
          .catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Notiz wurde nicht gespeichert.' }))
      }}
    >
      <Input label="Aktivität" value={title} onChange={(event) => setTitle(event.target.value)} />
      <Textarea label="Inhalt" value={description} onChange={(event) => setDescription(event.target.value)} />
      <Button type="submit">Notiz speichern</Button>
    </form>
  )
}

function QuotePanel({ festivalId, quotes, canWrite, canConfirm, onDone }: { festivalId: string; quotes: Array<Record<string, unknown>>; canWrite: boolean; canConfirm: boolean; onDone: () => void }) {
  const { notify } = useToast()
  const [description, setDescription] = useState('Fiktive Materialmiete')
  const [quantity, setQuantity] = useState('1')
  const [price, setPrice] = useState('0.00')
  const [vat, setVat] = useState('8.10')
  return (
    <div className="grid gap-3">
      <p className="text-sm leading-6 text-muted">Preise sind konfigurierbare CRM-Richtwerte. Sie sind keine Preisliste des Brauhauses.</p>
      {quotes.map((quote) => (
        <Card key={String(quote.id)} className="grid gap-2 p-4 text-sm">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <strong>{String(quote.quote_number)} · Version {String(quote.version)}</strong>
            <Badge tone={statusTone(String(quote.status))}>{labelOf(quoteStatusOptions, String(quote.status))}</Badge>
          </div>
          <p>Total {formatAmount(quote.gross_total as string | number)} inkl. MWST {formatAmount(quote.vat_total as string | number)}</p>
          <div className="flex flex-wrap gap-2">
            {canWrite && quote.status === 'entwurf' ? (
              <Button variant="secondary" onClick={() => quoteAction(String(quote.id), 'status', { status: 'versendet' }).then(onDone).catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Status nicht gespeichert.' }))}>Als versendet markieren</Button>
            ) : null}
            {canConfirm && ['entwurf', 'in_pruefung', 'versendet'].includes(String(quote.status)) ? (
              <Button onClick={() => quoteAction(String(quote.id), 'accept').then(() => { notify({ tone: 'success', message: 'Die Offerte wurde angenommen.' }); onDone() }).catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Annahme wurde abgelehnt.' }))}>Annehmen</Button>
            ) : null}
            {canWrite ? (
              <Button variant="secondary" onClick={() => quoteAction(String(quote.id), 'version').then(() => { notify({ tone: 'success', message: 'Eine neue Offertenversion wurde erstellt.' }); onDone() }).catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Version wurde nicht erstellt.' }))}>Neue Version</Button>
            ) : null}
          </div>
        </Card>
      ))}
      {canWrite ? (
        <form
          className="grid gap-2 md:grid-cols-4"
          onSubmit={(event) => {
            event.preventDefault()
            createQuote({
              festival_id: festivalId,
              vat_rate: vat,
              notes: 'Fiktive Richtpreise, keine Brauhaus-Preisliste.',
              items: [{ description, quantity, unit_price: price, vat_rate: vat, kind: 'material' }],
            })
              .then(() => {
                notify({ tone: 'success', message: 'Die Offerte wurde gespeichert.' })
                onDone()
              })
              .catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Offerte wurde nicht gespeichert.' }))
          }}
        >
          <Input label="Position" value={description} onChange={(event) => setDescription(event.target.value)} />
          <Input label="Menge" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
          <Input label="Preis CHF" value={price} onChange={(event) => setPrice(event.target.value)} />
          <Input label="MWST %" value={vat} onChange={(event) => setVat(event.target.value)} />
          <Button type="submit">Offerte erstellen</Button>
        </form>
      ) : null}
    </div>
  )
}

function ReservationPanel({
  festivalId,
  starts,
  ends,
  binding,
  reservations,
  materials,
  canReserve,
  canIssue,
  canDraft,
  onDone,
}: {
  festivalId: string
  starts: string
  ends: string
  binding: boolean
  reservations: Array<Record<string, unknown>>
  materials: Array<Record<string, unknown>>
  canReserve: boolean
  canIssue: boolean
  canDraft: boolean
  onDone: () => void
}) {
  const { notify } = useToast()
  const [materialId, setMaterialId] = useState('')
  const [assetId, setAssetId] = useState('')
  const [quantity, setQuantity] = useState('1')
  const [availability, setAvailability] = useState<string | null>(null)
  const [returnLine, setReturnLine] = useState('')
  const [returnedQty, setReturnedQty] = useState('0')
  const [damagedQty, setDamagedQty] = useState('0')
  const [missingQty, setMissingQty] = useState('0')
  const options = materials.map((row) => ({ value: String(row.id), label: `${row.material_number} ${row.name}` }))
  const selectedMaterial = materials.find((row) => String(row.id) === materialId)
  const assetOptions = ((selectedMaterial?.assets as Array<Record<string, unknown>> | undefined) ?? []).map((asset) => ({
    value: String(asset.id),
    label: String(asset.inventory_number),
  }))
  const openLines = reservations.flatMap((row) => {
    if (row.status !== 'ausgegeben' && row.status !== 'teilweise_zurueckgegeben') return []
    return ((row.lines as Array<Record<string, unknown>>) ?? []).map((line) => ({
      reservationId: String(row.id),
      lineId: String(line.id),
      label: `${String(row.reservation_number)} · ${String(line.material_name)} · offen ${Number(line.issued_qty) - Number(line.returned_qty) - Number(line.damaged_qty) - Number(line.missing_qty)}`,
    }))
  })

  return (
    <div className="grid gap-3">
      <p className="text-sm leading-6 text-muted">
        Die verfügbare Menge wird für den Zeitraum berechnet. Eine Anfrage erzeugt noch keine verbindliche Reservation.
        {binding ? ' Der Festauftrag ist bestätigt.' : ' Zuerst die Offerte annehmen und den Auftrag bestätigen.'}
      </p>
      {reservations.map((row) => {
        const lines = (row.lines as Array<Record<string, unknown>>) ?? []
        return (
          <Card key={String(row.id)} className="grid gap-2 p-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <strong>{String(row.reservation_number)}</strong>
              <Badge tone={statusTone(String(row.status))}>{labelOf(reservationStatusOptions, String(row.status))}</Badge>
            </div>
            {lines.map((line) => (
              <p key={String(line.id)}>
                {String(line.material_name)} · reserviert {String(line.quantity)} · ausgegeben {String(line.issued_qty)} · zurück {String(line.returned_qty)} · beschädigt {String(line.damaged_qty)} · fehlend {String(line.missing_qty)}
              </p>
            ))}
            <div className="flex flex-wrap gap-2">
              <Button variant="secondary" onClick={() => reservationAction(String(row.id), 'check').then((result) => notify({ tone: result.enough ? 'success' : 'warning', message: result.enough ? 'Das Material ist im Zeitraum verfügbar.' : 'Es besteht ein Materialkonflikt.' })).then(onDone).catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Prüfung ist fehlgeschlagen.' }))}>Verfügbarkeit prüfen</Button>
              {canReserve ? (
                <Button onClick={() => reservationAction(String(row.id), 'confirm').then(() => { notify({ tone: 'success', message: 'Die Reservation wurde verbindlich bestätigt.' }); onDone() }).catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Reservation wurde nicht bestätigt.' }))}>Verbindlich reservieren</Button>
              ) : null}
              {canIssue && row.status === 'bestaetigt' ? (
                <Button onClick={() => reservationAction(String(row.id), 'issue', { lines: lines.map((line) => ({ line_id: line.id, quantity: line.quantity })), condition_note: 'Ausgabe im CRM erfasst' }).then(() => { notify({ tone: 'success', message: 'Die Ausgabe wurde bestätigt.' }); onDone() }).catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Ausgabe wurde abgelehnt.' }))}>Ausgeben</Button>
              ) : null}
              {canIssue && (row.status === 'ausgegeben' || row.status === 'teilweise_zurueckgegeben') ? (
                <Button onClick={() => reservationAction(String(row.id), 'return', { lines: lines.map((line) => ({ line_id: line.id, returned_qty: Number(line.issued_qty) - Number(line.returned_qty) - Number(line.damaged_qty) - Number(line.missing_qty), damaged_qty: 0, missing_qty: 0 })), notes: 'Vollständige Rückgabe der noch offenen Menge' }).then(() => { notify({ tone: 'success', message: 'Die Rücknahme wurde verbucht.' }); onDone() }).catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Rücknahme wurde abgelehnt.' }))}>Offene Menge zurückbuchen</Button>
              ) : null}
            </div>
          </Card>
        )
      })}
      {canDraft ? (
        <form
          className="grid gap-2 md:grid-cols-3"
          onSubmit={(event) => {
            event.preventDefault()
            if (selectedMaterial?.tracking === 'einzel' && !assetId) {
              notify({ tone: 'critical', message: 'Ein Einzelstück braucht eine Inventarnummer.' })
              return
            }
            createReservation({
              festival_id: festivalId,
              starts_at: starts,
              ends_at: ends,
              lines: [{ material_id: materialId, quantity: selectedMaterial?.tracking === 'einzel' ? 1 : Number(quantity), asset_id: assetId || null }],
            })
              .then(() => {
                notify({ tone: 'success', message: 'Die Materialanfrage wurde gespeichert. Sie ist noch nicht verbindlich.' })
                onDone()
              })
              .catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Reservation wurde nicht gespeichert.' }))
          }}
        >
          <Select label="Material" value={materialId} onChange={(value) => { setMaterialId(value); setAssetId('') }} options={[{ value: '', label: 'Auswählen' }, ...options]} />
          {selectedMaterial?.tracking === 'einzel' ? (
            <Select label="Inventarnummer" value={assetId} onChange={setAssetId} options={[{ value: '', label: 'Auswählen' }, ...assetOptions]} />
          ) : (
            <Input label="Menge" value={quantity} onChange={(event) => setQuantity(event.target.value)} />
          )}
          <Button type="button" variant="secondary" onClick={() => {
            const params = new URLSearchParams({ material_id: materialId, start: starts, end: ends, quantity })
            checkAvailability(params).then((result) => setAvailability(`Verfügbar ${String(result.available)} von nutzbar ${String(result.usable)}. ${result.enough ? 'Die Menge reicht.' : 'Die Menge reicht nicht.'}`)).catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Prüfung ist fehlgeschlagen.' }))
          }}>Prüfen</Button>
          <Button type="submit">Zur Reservation hinzufügen</Button>
          {availability ? <p className="text-sm md:col-span-3">{availability}</p> : null}
        </form>
      ) : null}
      {canIssue && openLines.length > 0 ? (
        <form
          className="grid gap-2 md:grid-cols-4"
          onSubmit={(event) => {
            event.preventDefault()
            const selected = openLines.find((line) => line.lineId === returnLine)
            if (!selected) {
              notify({ tone: 'critical', message: 'Bitte eine Materialposition wählen.' })
              return
            }
            reservationAction(selected.reservationId, 'return', {
              lines: [{ line_id: selected.lineId, returned_qty: Number(returnedQty), damaged_qty: Number(damagedQty), missing_qty: Number(missingQty) }],
              notes: 'Kontrollierte Rücknahme. Beschädigt und fehlend bleiben gesperrt.',
            })
              .then(() => {
                notify({ tone: 'success', message: 'Die Rücknahme wurde verbucht. Nur die unbeschädigte Menge ist wieder verfügbar.' })
                onDone()
              })
              .catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Rücknahme wurde abgelehnt.' }))
          }}
        >
          <Select label="Rücknahmeposition" value={returnLine} onChange={setReturnLine} options={[{ value: '', label: 'Auswählen' }, ...openLines.map((line) => ({ value: line.lineId, label: line.label }))]} />
          <Input label="Zurückgegeben" value={returnedQty} onChange={(event) => setReturnedQty(event.target.value)} />
          <Input label="Beschädigt" value={damagedQty} onChange={(event) => setDamagedQty(event.target.value)} />
          <Input label="Fehlend" value={missingQty} onChange={(event) => setMissingQty(event.target.value)} />
          <Button type="submit">Rücknahme mit Kontrolle speichern</Button>
        </form>
      ) : null}
    </div>
  )
}

function DeliveryPanel({ festivalId, deliveries, canWrite, onDone }: { festivalId: string; deliveries: Array<Record<string, unknown>>; canWrite: boolean; onDone: () => void }) {
  const { notify } = useToast()
  const [address, setAddress] = useState('')
  const [deliverAt, setDeliverAt] = useState('')
  const [status, setStatus] = useState('geplant')
  return (
    <div className="grid gap-3">
      <p className="text-sm text-muted">Ein erreichtes Datum setzt den Transport nicht automatisch auf geliefert.</p>
      {deliveries.map((row) => (
        <Card key={String(row.id)} className="grid gap-2 p-4 text-sm">
          <p>{String(row.address)}</p>
          <p>Lieferung {formatStamp(row.deliver_at as string | null)} · {labelOf(deliveryStatusOptions, String(row.status))}</p>
          {canWrite ? (
            <Select label="Transportstatus" value={String(row.status)} onChange={(value) => updateDelivery(String(row.id), { festival_id: festivalId, address: String(row.address), status: value }).then(() => { notify({ tone: 'success', message: 'Der Transportstatus wurde gespeichert.' }); onDone() }).catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Der Status wurde nicht gespeichert.' }))} options={deliveryStatusOptions.filter((option) => option.value !== 'keine')} />
          ) : null}
        </Card>
      ))}
      {canWrite ? (
        <form className="grid gap-2 md:grid-cols-3" onSubmit={(event) => {
          event.preventDefault()
          createDelivery({ festival_id: festivalId, address, deliver_at: deliverAt ? fromZurichInput(deliverAt) : null, status })
            .then(() => { notify({ tone: 'success', message: 'Der Transport wurde geplant.' }); onDone() })
            .catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Der Transport wurde nicht gespeichert.' }))
        }}>
          <Input label="Lieferadresse" value={address} onChange={(event) => setAddress(event.target.value)} />
          <Input label="Liefertermin" type="datetime-local" value={deliverAt} onChange={(event) => setDeliverAt(event.target.value)} />
          <Select label="Status" value={status} onChange={setStatus} options={deliveryStatusOptions.filter((option) => option.value !== 'keine')} />
          <Button type="submit">Transport speichern</Button>
        </form>
      ) : null}
    </div>
  )
}

function AssignmentPanel({ festivalId, assignments, canWrite, onDone }: { festivalId: string; assignments: Array<Record<string, unknown>>; canWrite: boolean; onDone: () => void }) {
  const { notify } = useToast()
  const [person, setPerson] = useState('')
  const [kind, setKind] = useState('lieferung')
  const [task, setTask] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  return (
    <div className="grid gap-3">
      <p className="text-sm text-muted">Die Einsatzplanung prüft Überschneidungen derselben Person. Sie ersetzt keine Lohnbuchhaltung.</p>
      {assignments.map((row) => (
        <Card key={String(row.id)} className="p-4 text-sm">
          {String(row.person_name)} · {labelOf(assignmentKindOptions, String(row.kind))} · {String(row.task)} · {formatStamp(String(row.starts_at))} bis {formatStamp(String(row.ends_at))}
        </Card>
      ))}
      {canWrite ? (
        <form className="grid gap-2 md:grid-cols-2" onSubmit={(event) => {
          event.preventDefault()
          createAssignment({ festival_id: festivalId, person_name: person, kind, task, starts_at: fromZurichInput(start), ends_at: fromZurichInput(end) })
            .then(() => { notify({ tone: 'success', message: 'Der Einsatz wurde gespeichert.' }); onDone() })
            .catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Der Einsatz wurde nicht gespeichert.' }))
        }}>
          <Input label="Person" value={person} onChange={(event) => setPerson(event.target.value)} />
          <Select label="Einsatzart" value={kind} onChange={setKind} options={assignmentKindOptions} />
          <Input label="Aufgabe" value={task} onChange={(event) => setTask(event.target.value)} />
          <Input label="Beginn" type="datetime-local" value={start} onChange={(event) => setStart(event.target.value)} />
          <Input label="Ende" type="datetime-local" value={end} onChange={(event) => setEnd(event.target.value)} />
          <Button type="submit">Einsatz speichern</Button>
        </form>
      ) : null}
    </div>
  )
}

export function FestivalCalendarPage() {
  const [cursor, setCursor] = useState(() => new Date())
  const [view, setView] = useState<'month' | 'week' | 'day' | 'list'>('month')
  const [region, setRegion] = useState('')
  const [owner, setOwner] = useState('')
  const [shortage, setShortage] = useState(false)
  const [items, setItems] = useState<Festival[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const year = cursor.getFullYear()
  const month = cursor.getMonth()
  const dayOfMonth = cursor.getDate()

  useEffect(() => {
    let cancelled = false
    let rangeStart = new Date(Date.UTC(year, month, 1))
    let rangeEnd = new Date(Date.UTC(year, month + 1, 1))
    if (view === 'day') {
      rangeStart = new Date(Date.UTC(year, month, dayOfMonth))
      rangeEnd = new Date(rangeStart)
      rangeEnd.setUTCDate(rangeStart.getUTCDate() + 1)
    } else if (view === 'week') {
      const anchor = new Date(Date.UTC(year, month, dayOfMonth))
      const weekOffset = (anchor.getUTCDay() + 6) % 7
      rangeStart = new Date(anchor)
      rangeStart.setUTCDate(anchor.getUTCDate() - weekOffset)
      rangeEnd = new Date(rangeStart)
      rangeEnd.setUTCDate(rangeStart.getUTCDate() + 7)
    } else if (view === 'list') {
      rangeStart = new Date(Date.UTC(year, 0, 1))
      rangeEnd = new Date(Date.UTC(year + 1, 0, 1))
    }
    const params = new URLSearchParams({ start: rangeStart.toISOString(), end: rangeEnd.toISOString() })
    if (region) params.set('region', region)
    if (owner) params.set('owner', owner)
    if (shortage) params.set('shortage', 'true')
    getCalendar(params)
      .then((result) => {
        if (!cancelled) setItems(result.items)
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Der Kalender konnte nicht geladen werden.')
      })
    return () => {
      cancelled = true
    }
  }, [year, month, dayOfMonth, view, region, owner, shortage])

  const days: Date[] = []
  const first = new Date(Date.UTC(year, month, 1))
  const offset = (first.getUTCDay() + 6) % 7
  for (let index = 0; index < 42; index += 1) {
    const day = new Date(first)
    day.setUTCDate(first.getUTCDate() - offset + index)
    days.push(day)
  }

  return (
    <PageFrame title="Festkalender">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <h1 className="text-2xl font-semibold text-ink">Festkalender</h1>
        <div className="flex gap-2">
          {(['month', 'week', 'day', 'list'] as const).map((entry) => (
            <Button key={entry} variant={view === entry ? 'primary' : 'secondary'} onClick={() => setView(entry)}>
              {entry === 'month' ? 'Monat' : entry === 'week' ? 'Woche' : entry === 'day' ? 'Tag' : 'Liste'}
            </Button>
          ))}
        </div>
      </div>
      <Card className="grid gap-3 p-4 md:grid-cols-4">
        <Input label="Region" value={region} onChange={(event) => setRegion(event.target.value)} />
        <Input label="Zuständige Person" value={owner} onChange={(event) => setOwner(event.target.value)} />
        <label className="flex items-center gap-2 text-sm font-semibold">
          <input type="checkbox" checked={shortage} onChange={(event) => setShortage(event.target.checked)} />
          Nur Materialengpässe
        </label>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => {
            const next = new Date(cursor)
            if (view === 'day') next.setDate(next.getDate() - 1)
            else if (view === 'week') next.setDate(next.getDate() - 7)
            else next.setMonth(next.getMonth() - 1)
            setCursor(next)
          }}>Zurück</Button>
          <Button variant="secondary" onClick={() => {
            const next = new Date(cursor)
            if (view === 'day') next.setDate(next.getDate() + 1)
            else if (view === 'week') next.setDate(next.getDate() + 7)
            else next.setMonth(next.getMonth() + 1)
            setCursor(next)
          }}>Weiter</Button>
        </div>
      </Card>
      {error ? <ErrorState title="Kalender nicht geladen" description={error} /> : null}
      {items === null && !error ? <LoadingState label="Kalender wird geladen" /> : null}
      {items && view === 'month' ? (
        <div className="grid grid-cols-7 gap-1">
          {['Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'].map((day) => (
            <p key={day} className="px-2 text-xs font-semibold text-muted">{day}</p>
          ))}
          {days.map((day) => {
            const key = day.toISOString().slice(0, 10)
            const matches = items.filter((item) => zurichKey(item.starts_at) <= key && zurichKey(item.ends_at) >= key)
            return (
              <Card key={key} className="min-h-24 p-2">
                <p className="text-xs text-muted">{day.getUTCDate()}</p>
                {matches.map((item) => (
                  <Link key={item.id} to={`/festmanagement/${item.id}`} className="mt-1 block text-xs font-semibold text-petrol">
                    {item.name}
                  </Link>
                ))}
              </Card>
            )
          })}
        </div>
      ) : null}
      {items && view !== 'month' ? (
        <Card>
          <DataTable
            caption="Kalenderliste"
            rows={view === 'day' ? items.filter((item) => zurichKey(item.starts_at) === zurichKey(cursor)) : items}
            rowKey={(row) => row.id}
            empty={<EmptyState title="Keine Veranstaltungen" description="Im gewählten Zeitraum liegt kein Fest." compact />}
            columns={[
              { id: 'name', header: 'Fest', cell: (row) => <Link to={`/festmanagement/${row.id}`}>{row.name}</Link> },
              { id: 'place', header: 'Ort', cell: (row) => row.city || '–' },
              { id: 'when', header: 'Zeitraum', cell: (row) => `${formatStamp(row.starts_at)} – ${formatStamp(row.ends_at)}` },
              { id: 'status', header: 'Status', cell: (row) => labelOf(eventStatusOptions, row.event_status) },
              { id: 'material', header: 'Material', cell: (row) => labelOf(materialStatusOptions, row.material_status) },
              { id: 'owner', header: 'Zuständig', cell: (row) => row.account_owner || '–' },
            ]}
          />
        </Card>
      ) : null}
      <Link to="/festmanagement/neu" className={cx(buttonStyles.base, buttonStyles.primary, 'w-fit')}>Neue Veranstaltung</Link>
      <p className="text-xs text-muted">Verbindliche Terminänderungen verlangen die Freigabeberechtigung und werden serverseitig geprüft.</p>
    </PageFrame>
  )
}

export function MaterialPage() {
  const { can } = useAuth()
  const { notify } = useToast()
  const [data, setData] = useState<{ items: Array<Record<string, unknown>>; erp_notice: string } | null>(null)
  const [movements, setMovements] = useState<Array<Record<string, unknown>>>([])
  const [name, setName] = useState('')
  const [tracking, setTracking] = useState('menge')
  const [error, setError] = useState<string | null>(null)

  function load() {
    listMaterials()
      .then((result) => {
        setData(result)
        return listMovements()
      })
      .then(setMovementsFrom)
      .catch((caught: unknown) => setError(caught instanceof ApiError ? caught.message : 'Das Material konnte nicht geladen werden.'))
  }

  function setMovementsFrom(result: { items: Array<Record<string, unknown>> }) {
    setMovements(result.items)
  }

  useEffect(() => {
    let cancelled = false
    listMaterials()
      .then((result) => {
        if (!cancelled) setData(result)
        return listMovements()
      })
      .then((result) => {
        if (!cancelled) setMovements(result.items)
      })
      .catch((caught: unknown) => {
        if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Das Material konnte nicht geladen werden.')
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <PageFrame title="Materialverwaltung">
      <h1 className="text-2xl font-semibold text-ink">Materialverwaltung</h1>
      <p className="max-w-3xl text-sm leading-6 text-muted">
        Kategorien wie Zapfanlagen, Gläser oder Tische sind konfigurierbare Beispiele und kein bestätigter Inventarbestand des Brauhauses.
        {data ? ` ${data.erp_notice}` : ''}
      </p>
      {error ? <ErrorState title="Material nicht geladen" description={error} /> : null}
      {data === null && !error ? <LoadingState label="Material wird geladen" /> : null}
      {data ? (
        <Card>
          <DataTable
            caption="Festmaterial"
            rows={data.items}
            rowKey={(row) => String(row.id)}
            empty={<EmptyState title="Kein Material" description="Legen Sie lokales CRM-Material an. Es wird nicht aus einem ERP gelesen." compact />}
            columns={[
              { id: 'number', header: 'Nummer', cell: (row) => String(row.material_number) },
              { id: 'name', header: 'Name', cell: (row) => String(row.name) },
              { id: 'type', header: 'Typ', cell: (row) => (row.tracking === 'einzel' ? 'Einzelstück' : 'Menge') },
              { id: 'total', header: 'Gesamt', cell: (row) => String(row.quantity_total) },
              { id: 'usable', header: 'Nutzbar', cell: (row) => String(row.usable) },
              { id: 'available', header: 'Jetzt frei', cell: (row) => String(row.available_now) },
              { id: 'defective', header: 'Defekt', cell: (row) => String(row.quantity_defective) },
              { id: 'missing', header: 'Fehlend', cell: (row) => String(row.quantity_missing) },
              { id: 'location', header: 'Lager', cell: (row) => String(row.location ?? '–') },
              { id: 'price', header: 'Mietpreis', cell: (row) => (row.rental_price == null ? '–' : formatAmount(row.rental_price as string | number)) },
            ]}
          />
        </Card>
      ) : null}
      {can('materials.write') ? (
        <form className="grid gap-2 md:grid-cols-3" onSubmit={(event) => {
          event.preventDefault()
          createMaterial({ name, tracking, unit: 'Stück', notes: 'Lokaler CRM-Bestand, kein ERP-Livebestand.' })
            .then(() => { notify({ tone: 'success', message: 'Das Material wurde angelegt.' }); setName(''); load() })
            .catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Das Material wurde nicht gespeichert.' }))
        }}>
          <Input label="Materialname" value={name} onChange={(event) => setName(event.target.value)} />
          <Select label="Typ" value={tracking} onChange={setTracking} options={[{ value: 'menge', label: 'Mengenbasiert' }, { value: 'einzel', label: 'Einzelstück mit Inventarnummer' }]} />
          <Button type="submit">Material anlegen</Button>
        </form>
      ) : null}
      {can('materials.write') && data ? (
        <Card className="grid gap-2 p-4">
          <h2 className="font-semibold">Wareneingang</h2>
          {data.items.filter((row) => row.tracking === 'menge').map((row) => (
            <Button key={String(row.id)} variant="secondary" onClick={() => {
              const quantity = window.prompt(`Wareneingang für ${String(row.name)}`, '1')
              if (!quantity) return
              postStock(String(row.id), { movement_type: 'wareneingang', quantity: Number(quantity), note: 'Wareneingang im CRM' })
                .then(() => { notify({ tone: 'success', message: 'Der Bestand wurde erhöht.' }); load() })
                .catch((caught: unknown) => notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Der Wareneingang wurde abgelehnt.' }))
            }}>{String(row.name)} einbuchen</Button>
          ))}
        </Card>
      ) : null}
      <Card>
        <DataTable
          caption="Materialbewegungen"
          rows={movements}
          rowKey={(row) => String(row.id)}
          empty={<EmptyState title="Keine Bewegungen" description="Wareneingang, Reservation, Ausgabe und Rücknahme erscheinen im Journal." compact />}
          columns={[
            { id: 'time', header: 'Zeit', cell: (row) => formatStamp(String(row.occurred_at)) },
            { id: 'type', header: 'Art', cell: (row) => String(row.movement_type) },
            { id: 'qty', header: 'Menge', cell: (row) => String(row.quantity) },
            { id: 'actor', header: 'Person', cell: (row) => String(row.actor_label ?? '–') },
            { id: 'note', header: 'Bemerkung', cell: (row) => String(row.note ?? '–') },
          ]}
        />
      </Card>
    </PageFrame>
  )
}

export function ReservationListPage() {
  const [rows, setRows] = useState<Array<Record<string, unknown>> | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    listReservations().then((result) => { if (!cancelled) setRows(result.items) }).catch((caught: unknown) => { if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Reservationen nicht geladen.') })
    return () => { cancelled = true }
  }, [])
  return (
    <PageFrame title="Reservationen">
      <h1 className="text-2xl font-semibold text-ink">Reservationen</h1>
      {error ? <ErrorState title="Reservationen nicht geladen" description={error} /> : null}
      {rows === null && !error ? <LoadingState label="Reservationen werden geladen" /> : null}
      {rows ? (
        <Card>
          <DataTable caption="Reservationen" rows={rows} rowKey={(row) => String(row.id)} empty={<EmptyState title="Keine Reservationen" description="Reservationen entstehen auf der Festdetailseite." compact />} columns={[
            { id: 'number', header: 'Nummer', cell: (row) => <Link to={`/festmanagement/${row.festival_id}`}>{String(row.reservation_number)}</Link> },
            { id: 'status', header: 'Status', cell: (row) => labelOf(reservationStatusOptions, String(row.status)) },
            { id: 'start', header: 'Beginn', cell: (row) => formatStamp(String(row.starts_at)) },
            { id: 'end', header: 'Ende', cell: (row) => formatStamp(String(row.ends_at)) },
          ]} />
        </Card>
      ) : null}
    </PageFrame>
  )
}

export function QuoteListPage() {
  const [rows, setRows] = useState<Array<Record<string, unknown>> | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    listQuotes().then((result) => { if (!cancelled) setRows(result.items) }).catch((caught: unknown) => { if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Offerten nicht geladen.') })
    return () => { cancelled = true }
  }, [])
  return (
    <PageFrame title="Offerten">
      <h1 className="text-2xl font-semibold text-ink">Offerten</h1>
      {error ? <ErrorState title="Offerten nicht geladen" description={error} /> : null}
      {rows === null && !error ? <LoadingState label="Offerten werden geladen" /> : null}
      {rows ? (
        <Card>
          <DataTable caption="Offerten" rows={rows} rowKey={(row) => String(row.id)} empty={<EmptyState title="Keine Offerten" description="Offerten werden beim Fest erfasst." compact />} columns={[
            { id: 'number', header: 'Nummer', cell: (row) => <Link to={`/festmanagement/${row.festival_id}`}>{String(row.quote_number)} / {String(row.version)}</Link> },
            { id: 'status', header: 'Status', cell: (row) => labelOf(quoteStatusOptions, String(row.status)) },
            { id: 'total', header: 'Total', cell: (row) => formatAmount(row.gross_total as string | number) },
            { id: 'date', header: 'Datum', cell: (row) => formatDay(String(row.quote_on)) },
          ]} />
        </Card>
      ) : null}
    </PageFrame>
  )
}

export function DeliveryListPage() {
  const [rows, setRows] = useState<Array<Record<string, unknown>> | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    listDeliveries().then((result) => { if (!cancelled) setRows(result.items) }).catch((caught: unknown) => { if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Transporte nicht geladen.') })
    return () => { cancelled = true }
  }, [])
  return (
    <PageFrame title="Lieferungen und Rücknahmen">
      <h1 className="text-2xl font-semibold text-ink">Lieferungen und Rücknahmen</h1>
      {error ? <ErrorState title="Transporte nicht geladen" description={error} /> : null}
      {rows === null && !error ? <LoadingState label="Transporte werden geladen" /> : null}
      {rows ? (
        <Card>
          <DataTable caption="Transporte" rows={rows} rowKey={(row) => String(row.id)} empty={<EmptyState title="Keine Transporte" description="Lieferungen werden beim Fest geplant." compact />} columns={[
            { id: 'fest', header: 'Fest', cell: (row) => <Link to={`/festmanagement/${row.festival_id}`}>Öffnen</Link> },
            { id: 'address', header: 'Adresse', cell: (row) => String(row.address) },
            { id: 'when', header: 'Lieferung', cell: (row) => formatStamp(row.deliver_at as string | null) },
            { id: 'status', header: 'Status', cell: (row) => labelOf(deliveryStatusOptions, String(row.status)) },
          ]} />
        </Card>
      ) : null}
    </PageFrame>
  )
}

export function AssignmentListPage() {
  const [rows, setRows] = useState<Array<Record<string, unknown>> | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    listAssignments().then((result) => { if (!cancelled) setRows(result.items) }).catch((caught: unknown) => { if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Einsätze nicht geladen.') })
    return () => { cancelled = true }
  }, [])
  return (
    <PageFrame title="Einsatzplanung">
      <h1 className="text-2xl font-semibold text-ink">Einsatzplanung</h1>
      <p className="text-sm text-muted">Einfache Einsätze für Vorbereitung, Lieferung und Rücknahme. Keine Lohn- oder HR-Buchhaltung.</p>
      {error ? <ErrorState title="Einsätze nicht geladen" description={error} /> : null}
      {rows === null && !error ? <LoadingState label="Einsätze werden geladen" /> : null}
      {rows ? (
        <Card>
          <DataTable caption="Einsätze" rows={rows} rowKey={(row) => String(row.id)} empty={<EmptyState title="Keine Einsätze" description="Einsätze werden beim Fest erfasst." compact />} columns={[
            { id: 'person', header: 'Person', cell: (row) => String(row.person_name) },
            { id: 'kind', header: 'Art', cell: (row) => labelOf(assignmentKindOptions, String(row.kind)) },
            { id: 'task', header: 'Aufgabe', cell: (row) => String(row.task) },
            { id: 'when', header: 'Zeit', cell: (row) => `${formatStamp(String(row.starts_at))} – ${formatStamp(String(row.ends_at))}` },
            { id: 'fest', header: 'Fest', cell: (row) => <Link to={`/festmanagement/${row.festival_id}`}>Öffnen</Link> },
          ]} />
        </Card>
      ) : null}
    </PageFrame>
  )
}

export function FestivalDashboardPage() {
  const [data, setData] = useState<Record<string, unknown> | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    getDashboard().then((result) => { if (!cancelled) setData(result) }).catch((caught: unknown) => { if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Die Auswertung konnte nicht geladen werden.') })
    return () => { cancelled = true }
  }, [])
  const cards: Array<[string, string]> = [
    ['planned', 'Geplante Feste'],
    ['confirmed', 'Bestätigte Feste'],
    ['open_requests', 'Offene Anfragen'],
    ['open_quotes', 'Offene Offerten'],
    ['reservations', 'Reservationen'],
    ['shortages', 'Materialengpässe'],
    ['overdue_returns', 'Überfällige Rücknahmen'],
    ['damaged', 'Beschädigtes Material'],
    ['missing', 'Fehlendes Material'],
    ['open_transports', 'Offene Transporte'],
    ['open_assignments', 'Offene Einsätze'],
  ]
  const months = (data?.by_month as Array<{ label: string; count: number }>) ?? []
  const utilization = (data?.utilization as Array<Record<string, unknown>>) ?? []
  return (
    <PageFrame title="Festauswertung">
      <h1 className="text-2xl font-semibold text-ink">Auswertungen</h1>
      {error ? <ErrorState title="Auswertung nicht geladen" description={error} /> : null}
      {data === null && !error ? <LoadingState label="Kennzahlen werden geladen" /> : null}
      {data ? (
        <>
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {cards.map(([key, label]) => (
              <Card key={key} className="p-4">
                <p className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</p>
                <p className="mt-2 text-2xl font-semibold text-ink">{String(data[key] ?? 0)}</p>
              </Card>
            ))}
          </div>
          <Card className="p-4">
            <h2 className="font-semibold">Feste pro Monat</h2>
            {months.length === 0 ? <p className="mt-2 text-sm text-muted">Noch keine Feste im Bestand.</p> : null}
            <ul className="mt-3 grid gap-2">
              {months.map((month) => (
                <li key={month.label} className="flex items-center justify-between text-sm">
                  <span>{month.label}</span>
                  <span className="font-semibold">{month.count}</span>
                </li>
              ))}
            </ul>
          </Card>
          <Card>
            <DataTable caption="Materialauslastung" rows={utilization} rowKey={(row) => String(row.material)} empty={<EmptyState title="Keine Auslastung" description="Sobald Material existiert, wird die Belegung der nächsten 30 Tage berechnet." compact />} columns={[
              { id: 'material', header: 'Material', cell: (row) => String(row.material) },
              { id: 'usable', header: 'Nutzbar', cell: (row) => String(row.usable) },
              { id: 'held', header: 'Belegt', cell: (row) => String(row.held) },
              { id: 'percent', header: 'Auslastung', cell: (row) => `${String(row.percent)} %` },
            ]} />
          </Card>
          <p className="text-sm text-muted">{String(data.erp_notice)}</p>
        </>
      ) : null}
    </PageFrame>
  )
}

export function PartnerFestivals({ partnerId }: { partnerId: string }) {
  const [rows, setRows] = useState<Festival[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    let cancelled = false
    const params = new URLSearchParams({ partner_id: partnerId, page_size: '50' })
    listFestivals(params)
      .then((result) => { if (!cancelled) setRows(result.items) })
      .catch((caught: unknown) => { if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Feste nicht geladen.') })
    return () => { cancelled = true }
  }, [partnerId])
  if (error) return <p className="text-sm text-muted">{error}</p>
  if (!rows) return <LoadingState label="Feste werden geladen" />
  if (rows.length === 0) return <EmptyState title="Keine Feste" description="Diesem Vertriebspartner ist noch kein Fest als Veranstalter oder Getränkehändler zugeordnet." compact />
  return (
    <ul className="grid gap-2">
      {rows.map((row) => (
        <li key={row.id}>
          <Link to={`/festmanagement/${row.id}`} className="font-semibold text-petrol">{row.event_number} · {row.name}</Link>
          <p className="text-sm text-muted">{formatDay(row.starts_at)} · {labelOf(eventStatusOptions, row.event_status)}</p>
        </li>
      ))}
    </ul>
  )
}
