import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import {
  archiveTemplate,
  duplicateTemplate,
  errorMessage,
  fetchTemplate,
  fetchTemplates,
  previewTemplate,
  saveTemplate,
} from '../../api/engagement.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Card } from '../../components/ui/Card.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { channelOptions, labelOf, type Template } from '../../domain/engagement.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'

const placeholders = ['{{vorname}}', '{{nachname}}', '{{unternehmen}}', '{{funktion}}']

export function TemplateListPage() {
  usePageTitle('Nachrichtenvorlagen')
  const [rows, setRows] = useState<Template[] | null>(null)
  const [includeArchived, setIncludeArchived] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    void fetchTemplates(includeArchived)
      .then((items) => {
        if (!active) return
        setRows(items)
        setError('')
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [includeArchived])

  return (
    <div className="mx-auto grid max-w-4xl gap-6">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">Nachrichtenvorlagen</h1>
          <p className="mt-2 text-sm leading-6 text-muted">
            Vorlagen werden nicht versendet. Fehlende Platzhalter bleiben leer, unbekannte Platzhalter bleiben stehen.
          </p>
        </div>
        <Link to="/kampagnen/vorlagen/neu" className={cx(buttonStyles.base, buttonStyles.primary)}>
          Vorlage erstellen
        </Link>
      </header>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} />
        Archivierte Vorlagen anzeigen
      </label>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      {rows ? (
        rows.length === 0 ? (
          <EmptyState title="Keine Vorlagen" description="Es ist noch keine Nachrichtenvorlage gespeichert." />
        ) : (
          <ul className="grid gap-3">
            {rows.map((row) => (
              <li key={row.id}>
                <Link to={`/kampagnen/vorlagen/${row.id}`} className="block border border-line bg-card px-4 py-3 hover:border-petrol">
                  <span className="font-semibold">{row.name}</span>
                  <span className="mt-1 block text-sm text-muted">{row.subject}</span>
                  {row.archived_at ? <Badge tone="neutral">Archiviert</Badge> : null}
                  {row.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
                </Link>
              </li>
            ))}
          </ul>
        )
      ) : (
        <LoadingState label="Vorlagen werden geladen" />
      )}
    </div>
  )
}

export function TemplateFormPage() {
  const { templateId } = useParams()
  const navigate = useNavigate()
  const editing = Boolean(templateId)
  usePageTitle(editing ? 'Vorlage bearbeiten' : 'Vorlage erstellen')
  const [name, setName] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [channel, setChannel] = useState('email')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const [ready, setReady] = useState(!editing)

  useEffect(() => {
    if (!templateId) return
    let active = true
    void fetchTemplate(templateId)
      .then((template) => {
        if (!active) return
        setName(template.name)
        setSubject(template.subject)
        setBody(template.body)
        setChannel(template.channel)
        setReady(true)
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [templateId])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError('')
    try {
      const saved = await saveTemplate(templateId ?? null, { name, subject, body, channel })
      void navigate(`/kampagnen/vorlagen/${saved.id}`)
    } catch (caught) {
      setError(errorMessage(caught))
      setPending(false)
    }
  }

  if (!ready && !error) return <LoadingState label="Vorlage wird geladen" />

  return (
    <form className="mx-auto grid max-w-3xl gap-4" onSubmit={(event) => void submit(event)}>
      <h1 className="text-3xl font-semibold tracking-tight">{editing ? 'Vorlage bearbeiten' : 'Vorlage erstellen'}</h1>
      <p className="text-sm leading-6 text-muted">Platzhalter: {placeholders.join(', ')}</p>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <Input label="Vorlagenname" value={name} onChange={(event) => setName(event.target.value)} required />
      <Input label="Betreff" value={subject} onChange={(event) => setSubject(event.target.value)} required />
      <Textarea label="Nachrichtentext" value={body} onChange={(event) => setBody(event.target.value)} required />
      <Select label="Kommunikationskanal" value={channel} onChange={setChannel} options={channelOptions} />
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending}>
          Speichern
        </Button>
        <Link to="/kampagnen/vorlagen" className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Abbrechen
        </Link>
      </div>
    </form>
  )
}

export function TemplateDetailPage() {
  const { templateId = '' } = useParams()
  const navigate = useNavigate()
  usePageTitle('Nachrichtenvorlage')
  const [template, setTemplate] = useState<Template | null>(null)
  const [preview, setPreview] = useState<{ subject: string; body: string; delivery_notice: string } | null>(null)
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [company, setCompany] = useState('')
  const [job, setJob] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    let active = true
    void fetchTemplate(templateId)
      .then((item) => {
        if (active) setTemplate(item)
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [templateId])

  if (error && !template) return <p className="text-sm text-critical">{error}</p>
  if (!template) return <LoadingState label="Vorlage wird geladen" />

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{template.name}</h1>
          <p className="mt-2 text-sm text-muted">{labelOf(channelOptions, template.channel)}</p>
          {template.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
          {template.archived_at ? <Badge>Archiviert</Badge> : null}
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to={`/kampagnen/vorlagen/${template.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Bearbeiten
          </Link>
          <Button
            variant="secondary"
            disabled={pending}
            onClick={() => {
              setPending(true)
              void duplicateTemplate(template.id)
                .then((copy) => navigate(`/kampagnen/vorlagen/${copy.id}`))
                .catch((caught: unknown) => setError(errorMessage(caught)))
                .finally(() => setPending(false))
            }}
          >
            Duplizieren
          </Button>
          {!template.archived_at ? (
            <Button
              variant="danger"
              disabled={pending}
              onClick={() => {
                setPending(true)
                void archiveTemplate(template.id)
                  .then(setTemplate)
                  .catch((caught: unknown) => setError(errorMessage(caught)))
                  .finally(() => setPending(false))
              }}
            >
              Archivieren
            </Button>
          ) : null}
        </div>
      </header>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <Card className="grid gap-2 p-4">
        <p className="text-sm font-semibold">Betreff</p>
        <p>{template.subject}</p>
        <p className="mt-2 text-sm font-semibold">Text</p>
        <p className="whitespace-pre-wrap text-sm leading-6">{template.body}</p>
      </Card>
      <Card className="grid gap-3 p-4">
        <h2 className="text-base font-semibold">Vorschau</h2>
        <p className="text-sm leading-6 text-muted">Leere Felder werden im Text ausgelassen. Es wird nichts versendet.</p>
        <div className="grid gap-3 md:grid-cols-2">
          <Input label="Vorname" value={firstName} onChange={(event) => setFirstName(event.target.value)} />
          <Input label="Nachname" value={lastName} onChange={(event) => setLastName(event.target.value)} />
          <Input label="Unternehmensname" value={company} onChange={(event) => setCompany(event.target.value)} />
          <Input label="Kontaktfunktion" value={job} onChange={(event) => setJob(event.target.value)} />
        </div>
        <Button
          disabled={pending}
          onClick={() => {
            setPending(true)
            void previewTemplate(template.id, {
              first_name: firstName || null,
              last_name: lastName || null,
              company_name: company || null,
              job_title: job || null,
            })
              .then(setPreview)
              .catch((caught: unknown) => setError(errorMessage(caught)))
              .finally(() => setPending(false))
          }}
        >
          Vorschau anzeigen
        </Button>
        {preview ? (
          <div className="border border-line bg-cream px-4 py-3">
            <p className="text-sm font-semibold">{preview.subject}</p>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{preview.body}</p>
            <p className="mt-3 text-sm leading-6 text-muted">{preview.delivery_notice}</p>
          </div>
        ) : null}
      </Card>
    </div>
  )
}
