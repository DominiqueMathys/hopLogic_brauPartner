import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router'
import {
  addAudienceMember,
  changeCampaignStatus,
  duplicateCampaign,
  errorMessage,
  fetchAudience,
  fetchCampaign,
  fetchCampaigns,
  fetchSuppressed,
  removeAudienceMember,
  requestCampaignSend,
  saveCampaign,
} from '../../api/engagement.ts'
import { fetchContacts } from '../../api/crm.ts'
import { fetchPartners } from '../../api/partners.ts'
import { fetchSegments } from '../../api/service.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Card } from '../../components/ui/Card.tsx'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog.tsx'
import { DataTable, type DataColumn } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import type { Contact } from '../../domain/crm.ts'
import {
  audienceOptions,
  campaignPayload,
  campaignStatusOptions,
  campaignTypeOptions,
  channelOptions,
  emptyCampaign,
  labelOf,
  type AudiencePreview,
  type Campaign,
  type CampaignInput,
  type Preference,
} from '../../domain/engagement.ts'
import { formatDate, formatDateTime, type Partner } from '../../domain/partners.ts'
import { formatChf } from '../../domain/sales.ts'
import type { Segment } from '../../domain/service.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const partnerQuery = {
  q: '',
  status: '',
  industry: '',
  region: '',
  accountOwner: '',
  sort: 'name' as const,
  direction: 'asc' as const,
  page: 1,
  includeArchived: false,
}

const contactQuery = {
  q: '',
  partnerId: '',
  status: '',
  accountOwner: '',
  sort: 'name' as const,
  direction: 'asc' as const,
  page: 1,
  includeArchived: false,
}

function toInput(campaign: Campaign): CampaignInput {
  return {
    name: campaign.name,
    description: campaign.description ?? '',
    campaign_type: campaign.campaign_type,
    account_owner: campaign.account_owner ?? '',
    starts_on: campaign.starts_on ?? '',
    ends_on: campaign.ends_on ?? '',
    objective: campaign.objective ?? '',
    audience_kind: campaign.audience_kind,
    segment_id: campaign.segment_id ?? '',
    channel: campaign.channel,
    budget: campaign.budget ?? '',
    internal_note: campaign.internal_note ?? '',
  }
}

const columns: DataColumn<Campaign>[] = [
  {
    id: 'name',
    header: 'Kampagne',
    cell: (row) => (
      <Link to={`/kampagnen/${row.id}`} className="font-semibold text-petrol">
        {row.name}
      </Link>
    ),
  },
  { id: 'type', header: 'Typ', cell: (row) => labelOf(campaignTypeOptions, row.campaign_type) },
  {
    id: 'audience',
    header: 'Zielgruppe',
    cell: (row) => row.segment_name ?? labelOf(audienceOptions, row.audience_kind),
  },
  { id: 'owner', header: 'Verantwortlich', cell: (row) => row.account_owner ?? 'Keine Angabe' },
  { id: 'start', header: 'Start', cell: (row) => formatDate(row.starts_on) },
  { id: 'end', header: 'Ende', cell: (row) => formatDate(row.ends_on) },
  { id: 'status', header: 'Status', cell: (row) => labelOf(campaignStatusOptions, row.status) },
  { id: 'count', header: 'Kontakte', cell: (row) => String(row.recipient_count) },
  { id: 'goal', header: 'Ziel', cell: (row) => row.objective ?? 'Keine Angabe' },
]

export function CampaignListPage() {
  usePageTitle('Marketingkampagnen')
  const [params] = useSearchParams()
  const [rows, setRows] = useState<Campaign[] | null>(null)
  const [suppressed, setSuppressed] = useState<Preference[]>([])
  const [q, setQ] = useState('')
  const [status, setStatus] = useState(params.get('status') ?? '')
  const [campaignType, setCampaignType] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    void Promise.all([fetchCampaigns({ q, status, campaignType }), fetchSuppressed()])
      .then(([campaigns, blocked]) => {
        if (!active) return
        setRows(campaigns)
        setSuppressed(blocked)
        setError('')
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [q, status, campaignType])

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Marketingkampagnen</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Kampagnen bleiben Entwürfe, bis sie geplant und aktiviert werden. Archivierte Kampagnen erscheinen nur im
            Statusfilter.
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/kampagnen/vorlagen" className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Nachrichtenvorlagen
          </Link>
          <Link to="/kampagnen/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
            Kampagne erstellen
          </Link>
        </div>
      </header>
      <Card className="grid gap-3 p-4 md:grid-cols-3">
        <Input label="Suche" value={q} onChange={(event) => setQ(event.target.value)} placeholder="Name oder Ziel" />
        <Select
          label="Status"
          value={status}
          onChange={setStatus}
          options={[{ value: '', label: 'Ohne Archiv' }, ...campaignStatusOptions]}
        />
        <Select
          label="Kampagnentyp"
          value={campaignType}
          onChange={setCampaignType}
          options={[{ value: '', label: 'Alle Typen' }, ...campaignTypeOptions]}
        />
      </Card>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      {rows ? (
        <Card>
          <DataTable
            caption="Kampagnen"
            columns={columns}
            rows={rows}
            rowKey={(row) => row.id}
            empty={<EmptyState compact title="Keine Kampagnen" description="Es ist noch keine Kampagne gespeichert." />}
          />
        </Card>
      ) : (
        <LoadingState label="Kampagnen werden geladen" />
      )}
      <Card className="p-4">
        <h2 className="text-base font-semibold">Sperrliste</h2>
        <p className="mt-2 text-sm leading-6 text-muted">
          Kontakte mit abgelehnter Marketingkommunikation. Eine geschäftliche E-Mail-Adresse allein steht nicht auf
          dieser Liste.
        </p>
        {suppressed.length === 0 ? (
          <p className="mt-3 text-sm">Keine gespeicherten Ablehnungen.</p>
        ) : (
          <ul className="mt-3 grid gap-2">
            {suppressed.map((item) => (
              <li key={item.contact_id}>
                <Link to={`/kontakte/${item.contact_id}`} className="font-semibold text-petrol">
                  Kontakt öffnen
                </Link>
                <span className="text-sm text-muted">
                  {' '}
                  · Widerruf {formatDate(item.revoked_on)}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  )
}

export function CampaignFormPage() {
  const { campaignId } = useParams()
  const navigate = useNavigate()
  const editing = Boolean(campaignId)
  usePageTitle(editing ? 'Kampagne bearbeiten' : 'Kampagne erstellen')
  const [input, setInput] = useState<CampaignInput>(emptyCampaign)
  const [segments, setSegments] = useState<Segment[]>([])
  const [frozen, setFrozen] = useState(false)
  const [archived, setArchived] = useState(false)
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [ready, setReady] = useState(!editing)

  useEffect(() => {
    let active = true
    void fetchSegments()
      .then((items) => {
        if (active) setSegments(items)
      })
      .catch(() => {
        if (active) setError('Die Segmente konnten nicht geladen werden.')
      })
    if (!campaignId) return () => {
      active = false
    }
    void fetchCampaign(campaignId)
      .then((campaign) => {
        if (!active) return
        setInput(toInput(campaign))
        setFrozen(campaign.audience_frozen)
        setArchived(campaign.status === 'archiviert')
        setReady(true)
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [campaignId])

  function update(patch: Partial<CampaignInput>) {
    setInput((current) => ({ ...current, ...patch }))
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError('')
    try {
      const saved = await saveCampaign(campaignId ?? null, campaignPayload(input))
      void navigate(`/kampagnen/${saved.id}`)
    } catch (caught) {
      setError(errorMessage(caught))
      setPending(false)
    }
  }

  if (!ready && !error) return <LoadingState label="Kampagne wird geladen" />

  return (
    <form className="mx-auto grid max-w-3xl gap-4" onSubmit={(event) => void submit(event)}>
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">{editing ? 'Kampagne bearbeiten' : 'Kampagne erstellen'}</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Der Status bleibt Entwurf, bis er auf der Detailseite geändert wird. Die Empfängerliste wird erst bei der
          Aktivierung festgehalten.
        </p>
      </header>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <Input label="Kampagnenname" value={input.name} onChange={(event) => update({ name: event.target.value })} required />
      <Textarea label="Beschreibung" value={input.description} onChange={(event) => update({ description: event.target.value })} />
      <div className="grid gap-4 md:grid-cols-2">
        <Select label="Kampagnentyp" value={input.campaign_type} onChange={(value) => update({ campaign_type: value })} options={campaignTypeOptions} />
        <Input label="Verantwortliche Person" value={input.account_owner} onChange={(event) => update({ account_owner: event.target.value })} />
        <Input label="Startdatum" type="date" value={input.starts_on} onChange={(event) => update({ starts_on: event.target.value })} />
        <Input label="Enddatum" type="date" value={input.ends_on} onChange={(event) => update({ ends_on: event.target.value })} />
      </div>
      <Textarea label="Zielsetzung" value={input.objective} onChange={(event) => update({ objective: event.target.value })} />
      <Select
        label="Zielgruppe"
        value={input.audience_kind}
        onChange={(value) => update({ audience_kind: value })}
        options={audienceOptions}
        disabled={frozen}
        hint={frozen ? 'Nach der Aktivierung bleibt die Zielgruppe unverändert.' : undefined}
      />
      {input.audience_kind === 'segment' ? (
        <Select
          label="Kundensegment"
          value={input.segment_id}
          onChange={(value) => update({ segment_id: value })}
          options={[{ value: '', label: 'Segment wählen' }, ...segments.map((item) => ({ value: item.id, label: item.name }))]}
          disabled={frozen}
        />
      ) : (
        <p className="text-sm leading-6 text-muted">
          Die einzelnen Vertriebspartner oder Kontaktpersonen werden auf der Detailseite zugeordnet.
        </p>
      )}
      <Select
        label="Kommunikationskanal"
        value={input.channel}
        onChange={(value) => update({ channel: value })}
        options={channelOptions}
        disabled={frozen}
      />
      <Input
        label="Internes Budget in CHF"
        value={input.budget}
        onChange={(event) => update({ budget: event.target.value })}
        hint="Optional. Betrag als Text, zum Beispiel 1500.00."
        inputMode="decimal"
      />
      <Textarea label="Interne Bemerkung" value={input.internal_note} onChange={(event) => update({ internal_note: event.target.value })} />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending || archived}>
          {editing ? 'Speichern' : 'Als Entwurf speichern'}
        </Button>
        <Link to={campaignId ? `/kampagnen/${campaignId}` : '/kampagnen'} className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Abbrechen
        </Link>
      </div>
    </form>
  )
}

export function CampaignDetailPage() {
  const { campaignId = '' } = useParams()
  const navigate = useNavigate()
  usePageTitle('Kampagne')
  const [campaign, setCampaign] = useState<Campaign | null>(null)
  const [preview, setPreview] = useState<AudiencePreview | null>(null)
  const [partners, setPartners] = useState<Partner[]>([])
  const [contacts, setContacts] = useState<Contact[]>([])
  const [target, setTarget] = useState('')
  const [error, setError] = useState('')
  const [sendNotice, setSendNotice] = useState('')
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [pending, setPending] = useState(false)

  function reload() {
    return Promise.all([fetchCampaign(campaignId), fetchAudience(campaignId)]).then(([nextCampaign, nextPreview]) => {
      setCampaign(nextCampaign)
      setPreview(nextPreview)
    })
  }

  useEffect(() => {
    let active = true
    void Promise.all([fetchCampaign(campaignId), fetchAudience(campaignId)])
      .then(([nextCampaign, nextPreview]) => {
        if (!active) return
        setCampaign(nextCampaign)
        setPreview(nextPreview)
        setError('')
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    void Promise.all([fetchPartners(partnerQuery), fetchContacts(contactQuery)])
      .then(([partnerList, contactList]) => {
        if (!active) return
        setPartners(partnerList.items)
        setContacts(contactList.items)
      })
      .catch(() => undefined)
    return () => {
      active = false
    }
  }, [campaignId])

  async function run(action: () => Promise<unknown>) {
    setPending(true)
    setError('')
    try {
      await action()
      await reload()
    } catch (caught) {
      setError(errorMessage(caught))
    } finally {
      setPending(false)
    }
  }

  if (error && !campaign) return <p className="text-sm text-critical">{error}</p>
  if (!campaign || !preview) return <LoadingState label="Kampagne wird geladen" />

  const manual = campaign.audience_kind !== 'segment'

  return (
    <div className="mx-auto grid max-w-6xl gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-petrol">{labelOf(campaignTypeOptions, campaign.campaign_type)}</p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{campaign.name}</h1>
          <div className="mt-3 flex flex-wrap gap-2">
            <Badge tone={campaign.status === 'aktiv' ? 'success' : 'neutral'}>{labelOf(campaignStatusOptions, campaign.status)}</Badge>
            {campaign.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
            {campaign.audience_frozen ? <Badge tone="petrol">Empfänger festgehalten</Badge> : null}
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to={`/kampagnen/${campaign.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Bearbeiten
          </Link>
          <Button variant="secondary" disabled={pending} onClick={() => void run(async () => navigate(`/kampagnen/${(await duplicateCampaign(campaign.id)).id}`))}>
            Duplizieren
          </Button>
          {campaign.allowed_statuses.includes('archiviert') ? (
            <Button variant="danger" disabled={pending} onClick={() => setArchiveOpen(true)}>
              Archivieren
            </Button>
          ) : null}
        </div>
      </header>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <Card className="grid gap-3 p-4 md:grid-cols-2">
        <Fact label="Verantwortlich" value={campaign.account_owner ?? 'Keine Angabe'} />
        <Fact label="Zeitraum" value={`${formatDate(campaign.starts_on)} – ${formatDate(campaign.ends_on)}`} />
        <Fact label="Zielgruppe" value={campaign.segment_name ?? labelOf(audienceOptions, campaign.audience_kind)} />
        <Fact label="Kanal" value={labelOf(channelOptions, campaign.channel)} />
        <Fact label="Budget" value={campaign.budget ? formatChf(campaign.budget) : 'Kein Budget'} />
        <Fact label="Aktiviert" value={formatDateTime(campaign.activated_at)} />
        <p className="md:col-span-2 text-sm leading-6">{campaign.objective ?? 'Keine Zielsetzung'}</p>
        {campaign.description ? <p className="md:col-span-2 text-sm leading-6 text-muted">{campaign.description}</p> : null}
      </Card>
      <div className="flex flex-wrap gap-2">
        {campaign.allowed_statuses
          .filter((status) => status !== 'archiviert')
          .map((status) => (
            <Button key={status} variant="secondary" disabled={pending} onClick={() => void run(() => changeCampaignStatus(campaign.id, status))}>
              Status: {labelOf(campaignStatusOptions, status)}
            </Button>
          ))}
        <Button
          variant="secondary"
          disabled={pending}
          onClick={() => {
            setPending(true)
            setSendNotice('')
            void requestCampaignSend(campaign.id)
              .then(() => setSendNotice('Der Versand wurde nicht ausgeführt.'))
              .catch((caught: unknown) => setSendNotice(errorMessage(caught)))
              .finally(() => setPending(false))
          }}
        >
          Versand prüfen
        </Button>
      </div>
      {sendNotice ? <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6">{sendNotice}</p> : null}
      <Card className="p-4">
        <h2 className="text-base font-semibold">Empfängerinnen und Empfänger</h2>
        <p className="mt-2 text-sm leading-6 text-muted">{preview.notice}</p>
        <p className="mt-2 text-sm leading-6 text-muted">{preview.consent_notice}</p>
        <p className="mt-2 text-sm leading-6">{preview.delivery_notice}</p>
        <p className="mt-3 text-sm font-semibold">
          {preview.included_count} vorgesehen · {preview.excluded_count} ausgeschlossen
        </p>
        {manual && !preview.frozen ? (
          <div className="mt-4 flex flex-wrap items-end gap-2">
            <div className="min-w-64 flex-1">
              <Select
                label={campaign.audience_kind === 'partners' ? 'Vertriebspartner' : 'Kontaktperson'}
                value={target}
                onChange={setTarget}
                options={[
                  { value: '', label: 'Auswählen' },
                  ...(campaign.audience_kind === 'partners'
                    ? partners.map((item) => ({ value: item.id, label: item.company_name }))
                    : contacts.map((item) => ({ value: item.id, label: `${item.first_name} ${item.last_name}` }))),
                ]}
              />
            </div>
            <Button
              disabled={pending || !target}
              onClick={() =>
                void run(async () => {
                  await addAudienceMember(
                    campaign.id,
                    campaign.audience_kind === 'partners' ? { partner_id: target } : { contact_id: target },
                  )
                  setTarget('')
                })
              }
            >
              Hinzufügen
            </Button>
          </div>
        ) : null}
        {preview.members.length > 0 ? (
          <ul className="mt-4 grid gap-2">
            {preview.members.map((member) => (
              <li key={member.id} className="flex flex-wrap items-center justify-between gap-2 border border-line px-3 py-2">
                <span>{member.label}</span>
                {!preview.frozen ? (
                  <Button variant="ghost" disabled={pending} onClick={() => void run(() => removeAudienceMember(campaign.id, member.id))}>
                    Entfernen
                  </Button>
                ) : null}
              </li>
            ))}
          </ul>
        ) : null}
        <RecipientList title="Vorgesehen" rows={preview.included} />
        <RecipientList title="Ausgeschlossen" rows={preview.excluded} />
      </Card>
      <ConfirmDialog
        open={archiveOpen}
        title="Kampagne archivieren"
        description="Eine archivierte Kampagne kann nicht mehr bearbeitet werden. Die festgehaltene Empfängerliste bleibt gespeichert."
        confirmLabel="Archivieren"
        tone="danger"
        onConfirm={() => {
          setArchiveOpen(false)
          void run(() => changeCampaignStatus(campaign.id, 'archiviert'))
        }}
        onCancel={() => setArchiveOpen(false)}
      />
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <p className="text-sm">
      <span className="font-semibold">{label}: </span>
      {value}
    </p>
  )
}

function RecipientList({ title, rows }: { title: string; rows: AudiencePreview['included'] }) {
  if (rows.length === 0) return null
  return (
    <div className="mt-4">
      <h3 className="text-sm font-semibold">{title}</h3>
      <ul className="mt-2 grid gap-1 text-sm">
        {rows.map((row) => (
          <li key={`${title}-${row.contact_id}`}>
            {row.name}
            {row.company_name ? ` · ${row.company_name}` : ''}
            {row.exclusion_reason ? ` · ${row.exclusion_reason}` : ''}
          </li>
        ))}
      </ul>
    </div>
  )
}
