import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ApiError, deleteSegment, fetchSegment, fetchSegmentPartners, fetchSegments, saveSegment } from '../../api/service.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog.tsx'
import { DataTable, type DataColumn } from '../../components/ui/DataTable.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { formatChf } from '../../domain/sales.ts'
import { choiceLabel, partnerStatusOptions, partnerTypeOptions } from '../../domain/partners.ts'
import {
  emptyCondition,
  operatorOptions,
  segmentFieldOptions,
  type Segment,
  type SegmentInput,
  type SegmentPartner,
} from '../../domain/service.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const columns: DataColumn<SegmentPartner>[] = [
  {
    id: 'name',
    header: 'Vertriebspartner',
    cell: (row) => (
      <Link to={`/vertriebspartner/${row.id}`} className="font-semibold text-petrol">
        {row.company_name}
      </Link>
    ),
  },
  { id: 'city', header: 'Ort', cell: (row) => row.city || 'Keine Angabe' },
  { id: 'type', header: 'Typ', cell: (row) => choiceLabel(partnerTypeOptions, row.partner_type) },
  { id: 'status', header: 'Status', cell: (row) => choiceLabel(partnerStatusOptions, row.status) },
  { id: 'orders', header: 'Bestellungen', cell: (row) => String(row.order_count) },
  { id: 'volume', header: 'CRM-Bestellvolumen', cell: (row) => formatChf(row.order_volume) },
  { id: 'tickets', header: 'Offene Tickets', cell: (row) => String(row.open_tickets) },
]

export function SegmentListPage() {
  usePageTitle('Segmente')
  const [items, setItems] = useState<Segment[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void fetchSegments()
      .then((result) => {
        if (active) setItems(result)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Die Segmente konnten nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [])

  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Partnersegmente</h1>
          <p className="mt-2 max-w-3xl text-sm leading-6 text-muted">
            Die Zugehörigkeit wird bei jeder Abfrage aus den aktuellen CRM-Daten berechnet. Es wird keine separate Partnerliste gespeichert.
          </p>
        </div>
        <Link to="/segmente/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Segment erstellen
        </Link>
      </header>
      {error ? <ErrorState title="Segmente nicht geladen" description={error} /> : null}
      {!items && !error ? <LoadingState label="Segmente werden geladen" /> : null}
      {items && items.length === 0 ? <EmptyState title="Keine Segmente" description="Legen Sie ein Segment mit mindestens einer Bedingung an." /> : null}
      <ul className="grid gap-3">
        {items?.map((segment) => (
          <li key={segment.id}>
            <Link to={`/segmente/${segment.id}`} className="block">
              <Card className="p-4 hover:border-petrol">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-semibold">{segment.name}</h2>
                  <span className="text-sm font-semibold">{segment.partner_count} Partner</span>
                </div>
                <p className="mt-2 text-sm leading-6 text-muted">{segment.description ?? 'Keine Beschreibung.'}</p>
                {segment.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
              </Card>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  )
}

export function SegmentCreatePage() {
  return <SegmentEditor />
}

export function SegmentEditPage() {
  const { segmentId = '' } = useParams()
  return <SegmentEditor segmentId={segmentId} />
}

function SegmentEditor({ segmentId }: { segmentId?: string }) {
  const navigate = useNavigate()
  const editing = Boolean(segmentId)
  usePageTitle(editing ? 'Segment bearbeiten' : 'Segment erstellen')
  const [input, setInput] = useState<SegmentInput>({
    name: '',
    description: '',
    match_mode: 'all',
    conditions: [emptyCondition()],
  })
  const [error, setError] = useState<string | null>(null)
  const [pending, setPending] = useState(editing)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    if (!segmentId) return
    let active = true
    void fetchSegment(segmentId)
      .then((segment) => {
        if (!active) return
        setInput({
          name: segment.name,
          description: segment.description ?? '',
          match_mode: segment.match_mode,
          conditions: segment.conditions.map((condition) => ({
            field_name: condition.field_name,
            operator: condition.operator,
            value: condition.value,
          })),
        })
        setPending(false)
      })
      .catch((caught: unknown) => {
        if (!active) return
        setError(caught instanceof ApiError ? caught.message : 'Das Segment konnte nicht geladen werden.')
        setPending(false)
      })
    return () => {
      active = false
    }
  }, [segmentId])

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const saved = await saveSegment(input, segmentId)
      navigate(`/segmente/${saved.id}`)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Das Segment konnte nicht gespeichert werden.')
      setSaving(false)
    }
  }

  if (pending) return <LoadingState label="Segment wird geladen" />

  return (
    <form className="mx-auto grid max-w-3xl gap-4" onSubmit={(event) => void onSubmit(event)}>
      <h1 className="text-3xl font-semibold tracking-tight">{editing ? 'Segment bearbeiten' : 'Segment erstellen'}</h1>
      {error ? <ErrorState title="Segment nicht gespeichert" description={error} /> : null}
      <Input label="Name" value={input.name} onChange={(event) => setInput({ ...input, name: event.target.value })} required />
      <Textarea label="Beschreibung" value={input.description} onChange={(event) => setInput({ ...input, description: event.target.value })} />
      <Select
        label="Verknüpfung"
        value={input.match_mode}
        onChange={(value) => setInput({ ...input, match_mode: value })}
        options={[
          { value: 'all', label: 'Alle Bedingungen (UND)' },
          { value: 'any', label: 'Eine Bedingung genügt (ODER)' },
        ]}
      />
      {input.conditions.map((condition, index) => {
        const operators = operatorOptions[condition.field_name] ?? []
        return (
          <div key={`${condition.field_name}-${index}`} className="grid gap-2 border border-line p-3 md:grid-cols-3">
            <Select
              label="Feld"
              value={condition.field_name}
              onChange={(value) => {
                const next = input.conditions.slice()
                next[index] = { field_name: value, operator: operatorOptions[value]?.[0]?.value ?? 'eq', value: '' }
                setInput({ ...input, conditions: next })
              }}
              options={segmentFieldOptions}
            />
            <Select
              label="Operator"
              value={condition.operator}
              onChange={(value) => {
                const next = input.conditions.slice()
                next[index] = { ...condition, operator: value }
                setInput({ ...input, conditions: next })
              }}
              options={operators}
            />
            {condition.operator === 'empty' ? (
              <p className="self-end text-sm text-muted">Kein Vergleichswert nötig.</p>
            ) : condition.field_name === 'partner_type' ? (
              <Select label="Wert" value={condition.value} onChange={(value) => replaceValue(index, value)} options={[{ value: '', label: 'Typ wählen' }, ...partnerTypeOptions]} />
            ) : condition.field_name === 'status' ? (
              <Select label="Wert" value={condition.value} onChange={(value) => replaceValue(index, value)} options={[{ value: '', label: 'Status wählen' }, ...partnerStatusOptions]} />
            ) : (
              <Input
                label="Wert"
                type={condition.field_name.endsWith('_on') ? 'date' : 'text'}
                value={condition.value}
                onChange={(event) => replaceValue(index, event.target.value)}
              />
            )}
            {input.conditions.length > 1 ? (
              <Button
                type="button"
                variant="secondary"
                onClick={() => setInput({ ...input, conditions: input.conditions.filter((_, item) => item !== index) })}
              >
                Bedingung entfernen
              </Button>
            ) : null}
          </div>
        )
      })}
      <Button type="button" variant="secondary" onClick={() => setInput({ ...input, conditions: [...input.conditions, emptyCondition()] })}>
        Bedingung hinzufügen
      </Button>
      <div className="flex gap-2">
        <Button type="submit" disabled={saving}>{saving ? 'Wird gespeichert' : 'Segment speichern'}</Button>
        <Link to="/segmente" className={cx(buttonStyles.base, buttonStyles.secondary)}>Abbrechen</Link>
      </div>
    </form>
  )

  function replaceValue(index: number, value: string) {
    const next = input.conditions.slice()
    const current = next[index]
    if (!current) return
    next[index] = { ...current, value }
    setInput({ ...input, conditions: next })
  }
}

export function SegmentDetailPage() {
  const { segmentId = '' } = useParams()
  const navigate = useNavigate()
  const [segment, setSegment] = useState<Segment | null>(null)
  const [partners, setPartners] = useState<SegmentPartner[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [confirm, setConfirm] = useState(false)
  usePageTitle(segment?.name ?? 'Segment')

  useEffect(() => {
    let active = true
    void Promise.all([fetchSegment(segmentId), fetchSegmentPartners(segmentId)])
      .then(([loaded, rows]) => {
        if (!active) return
        setSegment(loaded)
        setPartners(rows)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Das Segment konnte nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [segmentId])

  if (error && !segment) return <ErrorState title="Segment nicht verfügbar" description={error} />
  if (!segment || !partners) return <LoadingState label="Segment wird geladen" />

  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{segment.name}</h1>
          <p className="mt-2 text-sm leading-6 text-muted">{segment.description ?? 'Keine Beschreibung.'}</p>
          <p className="mt-2 text-sm font-semibold">{segment.partner_count} Partner · {segment.match_mode === 'any' ? 'ODER' : 'UND'}</p>
        </div>
        <div className="flex gap-2">
          <Link to={`/segmente/${segment.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.secondary)}>Bearbeiten</Link>
          <Button variant="danger" onClick={() => setConfirm(true)}>Löschen</Button>
        </div>
      </header>
      {segment.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
      <Card className="p-4">
        <h2 className="font-semibold">Bedingungen</h2>
        <ul className="mt-2 grid gap-1 text-sm">
          {segment.conditions.map((condition) => (
            <li key={condition.id}>
              {choiceLabel(segmentFieldOptions, condition.field_name)} {choiceLabel(operatorOptions[condition.field_name] ?? [], condition.operator)} {condition.value}
            </li>
          ))}
        </ul>
      </Card>
      <DataTable caption="Zugehörige Partner" columns={columns} rows={partners} rowKey={(row) => row.id} empty={<EmptyState title="Keine Partner" description="Mit den aktuellen CRM-Daten erfüllt kein Partner die Bedingungen." />} />
      <ConfirmDialog
        open={confirm}
        title="Segment löschen"
        description="Die Definition wird gelöscht. Die Vertriebspartner bleiben unverändert, weil keine Zuordnung gespeichert ist."
        confirmLabel="Löschen"
        tone="danger"
        onCancel={() => setConfirm(false)}
        onConfirm={() => {
          void deleteSegment(segment.id).then(() => navigate('/segmente')).catch((caught: unknown) => {
            setConfirm(false)
            setError(caught instanceof ApiError ? caught.message : 'Das Segment konnte nicht gelöscht werden.')
          })
        }}
      />
    </div>
  )
}
