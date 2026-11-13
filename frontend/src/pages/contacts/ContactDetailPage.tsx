import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { ApiError, archiveContact, linkContactCompany, makePrimaryContact, restoreContact, unlinkContactCompany } from '../../api/crm.ts'
import { fetchPartners } from '../../api/partners.ts'
import { LinkedActivities, LinkedTasks } from '../../components/crm/LinkedRecords.tsx'
import { ContactSales } from '../../components/sales/RelatedRecords.tsx'
import { PreferencePanel } from '../../components/engagement/PreferencePanel.tsx'
import { ContactService } from '../../components/service/RelatedService.tsx'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog.tsx'
import { EmptyState } from '../../components/ui/EmptyState.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Tabs } from '../../components/ui/Tabs.tsx'
import { useToast } from '../../components/ui/toast-state.ts'
import {
  channelOptions,
  contactName,
  contactStatusOptions,
  labelOf,
  languageOptions,
  leadStatusOptions,
  lifecycleOptions,
  processingBasisOptions,
  type Contact,
} from '../../domain/crm.ts'
import { formatDateTime, type PartnerQuery } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'
import { useContact } from './useContact.ts'

const partnerQuery: PartnerQuery = {
  q: '',
  status: '',
  industry: '',
  region: '',
  accountOwner: '',
  sort: 'name',
  direction: 'asc',
  page: 1,
  includeArchived: false,
}

export function ContactDetailPage() {
  const { contactId } = useParams()
  const { contact, setContact, error, pending } = useContact(contactId)
  const { notify } = useToast()
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [restoreOpen, setRestoreOpen] = useState(false)
  const [actionPending, setActionPending] = useState(false)
  usePageTitle(contact ? contactName(contact) : 'Kontakt')

  async function runAction(action: 'archive' | 'restore') {
    if (!contact) {
      return
    }
    setArchiveOpen(false)
    setRestoreOpen(false)
    setActionPending(true)
    try {
      const updated = action === 'archive' ? await archiveContact(contact.id) : await restoreContact(contact.id)
      setContact(updated)
      notify({
        tone: 'success',
        message: action === 'archive' ? 'Der Kontakt wurde archiviert.' : 'Der Kontakt wurde wiederhergestellt.',
      })
    } catch (caught) {
      notify({
        tone: 'critical',
        message: caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.',
      })
    } finally {
      setActionPending(false)
    }
  }

  if (!contactId || (!contact && !pending)) {
    return (
      <ErrorState
        title="Kontakt nicht gefunden"
        description={error ?? 'Der Kontakt wurde nicht gefunden.'}
        action={
          <Link to="/kontakte" className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Zur Übersicht
          </Link>
        }
      />
    )
  }
  if (!contact) {
    return <LoadingState label="Kontakt wird geladen" />
  }

  const primaryCompany = contact.companies.find((company) => company.is_primary) ?? contact.companies[0]

  return (
    <div className="mx-auto grid max-w-5xl gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-3xl font-semibold tracking-tight">{contactName(contact)}</h1>
            <Badge tone={contact.status === 'aktiv' ? 'success' : 'neutral'}>{labelOf(contactStatusOptions, contact.status)}</Badge>
            {contact.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
            {contact.archived_at ? <Badge tone="critical">Archiviert</Badge> : null}
          </div>
          <p className="mt-2 text-sm leading-6 text-muted">
            {contact.job_title ?? 'Keine Funktion'}
            {primaryCompany ? ` · ${primaryCompany.company_name}` : ''}
          </p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/kontakte" className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Zur Übersicht
          </Link>
          {contact.archived_at ? (
            <Button disabled={actionPending} onClick={() => setRestoreOpen(true)}>
              Wiederherstellen
            </Button>
          ) : (
            <>
              <Link to={`/kontakte/${contact.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.primary)}>
                Bearbeiten
              </Link>
              <Button variant="danger" disabled={actionPending} onClick={() => setArchiveOpen(true)}>
                Archivieren
              </Button>
            </>
          )}
        </div>
      </header>
      {contact.is_demo ? (
        <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6">
          Fiktiver Testdatensatz. Keine echte Person und keine Einwilligung.
        </p>
      ) : null}
      <Card className="p-4">
        <Tabs
          label="Kontaktbereiche"
          tabs={[
            { id: 'overview', label: 'Übersicht', content: <Overview contact={contact} /> },
            {
              id: 'activities',
              label: 'Aktivitäten',
              content: (
                <LinkedActivities
                  contactId={contact.id}
                  partnerId={primaryCompany?.partner_id}
                  owner={contact.account_owner ?? ''}
                />
              ),
            },
            { id: 'tasks', label: 'Aufgaben', content: <LinkedTasks contactId={contact.id} partnerId={primaryCompany?.partner_id} /> },
            {
              id: 'companies',
              label: 'Zugeordnete Unternehmen',
              content: <Companies contact={contact} onChange={setContact} />,
            },
            {
              id: 'opportunities',
              label: 'Verkauf und Bestellungen',
              content: <ContactSales contactId={contact.id} />,
            },
            {
              id: 'service',
              label: 'Servicefälle',
              content: <ContactService contactId={contact.id} />,
            },
            {
              id: 'preferences',
              label: 'Kommunikation',
              content: <PreferencePanel contactId={contact.id} />,
            },
          ]}
        />
      </Card>
      <ConfirmDialog
        open={archiveOpen}
        title="Kontakt archivieren"
        description="Der Kontakt und die Historie bleiben gespeichert. Zuordnungen werden nicht gelöscht."
        confirmLabel="Archivieren"
        tone="danger"
        onConfirm={() => void runAction('archive')}
        onCancel={() => setArchiveOpen(false)}
      />
      <ConfirmDialog
        open={restoreOpen}
        title="Kontakt wiederherstellen"
        description="Der Kontakt erscheint wieder in der Standardliste."
        confirmLabel="Wiederherstellen"
        onConfirm={() => void runAction('restore')}
        onCancel={() => setRestoreOpen(false)}
      />
    </div>
  )
}

function Overview({ contact }: { contact: Contact }) {
  return (
    <dl className="grid gap-4 sm:grid-cols-2">
      <Field label="Name">{contactName(contact)}</Field>
      <Field label="Funktion">{contact.job_title ?? 'Keine Angabe'}</Field>
      <Field label="E-Mail">{contact.email ?? 'Keine Angabe'}</Field>
      <Field label="Telefon">{contact.phone ?? 'Keine Angabe'}</Field>
      <Field label="Mobil">{contact.mobile ?? 'Keine Angabe'}</Field>
      <Field label="Sprache">{labelOf(languageOptions, contact.preferred_language)}</Field>
      <Field label="Kanal">{labelOf(channelOptions, contact.preferred_channel)}</Field>
      <Field label="Lifecycle-Phase">{labelOf(lifecycleOptions, contact.lifecycle_phase)}</Field>
      <Field label="Leadstatus">{labelOf(leadStatusOptions, contact.lead_status)}</Field>
      <Field label="Kontaktstatus">{labelOf(contactStatusOptions, contact.status)}</Field>
      <Field label="Betreuung">{contact.account_owner ?? 'Nicht zugewiesen'}</Field>
      <Field label="Letzter Kontakt">{contact.last_contact_at ? formatDateTime(contact.last_contact_at) : 'Kein Eintrag'}</Field>
      <Field label="Rechtsgrundlage">{labelOf(processingBasisOptions, contact.processing_basis)}</Field>
      <Field label="Erfasst am">{formatDateTime(contact.created_at)}</Field>
      <Field label="Zuletzt geändert">{formatDateTime(contact.updated_at)}</Field>
      <div className="sm:col-span-2">
        <dt className="text-xs font-semibold tracking-wide text-muted uppercase">Dokumentation der Rechtsgrundlage</dt>
        <dd className="mt-1 whitespace-pre-wrap text-sm leading-6">{contact.processing_basis_note ?? 'Keine Dokumentation'}</dd>
      </div>
      <div className="sm:col-span-2">
        <dt className="text-xs font-semibold tracking-wide text-muted uppercase">Interne Bemerkungen</dt>
        <dd className="mt-1 whitespace-pre-wrap text-sm leading-6">{contact.notes ?? 'Keine Bemerkungen'}</dd>
      </div>
    </dl>
  )
}

function Companies({ contact, onChange }: { contact: Contact; onChange: (contact: Contact) => void }) {
  const { notify } = useToast()
  const [partnerId, setPartnerId] = useState('')
  const [isPrimary, setIsPrimary] = useState(false)
  const [options, setOptions] = useState<{ value: string; label: string }[]>([{ value: '', label: 'Unternehmen wählen' }])
  const [removeId, setRemoveId] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void fetchPartners(partnerQuery).then((result) => {
      if (!active) {
        return
      }
      setOptions([
        { value: '', label: 'Unternehmen wählen' },
        ...result.items.map((partner) => ({
          value: partner.id,
          label: partner.city ? `${partner.company_name}, ${partner.city}` : partner.company_name,
        })),
      ])
    })
    return () => {
      active = false
    }
  }, [])

  async function addCompany() {
    if (!partnerId) {
      return
    }
    try {
      onChange(await linkContactCompany(contact.id, partnerId, isPrimary))
      setPartnerId('')
      notify({ tone: 'success', message: 'Das Unternehmen wurde zugeordnet.' })
    } catch (caught) {
      notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Zuordnung ist fehlgeschlagen.' })
    }
  }

  async function remove() {
    if (!removeId) {
      return
    }
    const target = removeId
    setRemoveId(null)
    try {
      onChange(await unlinkContactCompany(contact.id, target))
      notify({ tone: 'success', message: 'Die Zuordnung wurde entfernt. Der Kontakt bleibt erhalten.' })
    } catch (caught) {
      notify({ tone: 'critical', message: caught instanceof ApiError ? caught.message : 'Die Zuordnung konnte nicht entfernt werden.' })
    }
  }

  return (
    <div className="grid gap-4">
      {contact.companies.length === 0 ? (
        <EmptyState title="Keine Unternehmen" description="Dieser Kontakt ist noch keinem Unternehmen zugeordnet." />
      ) : (
        <ul className="grid gap-3">
          {contact.companies.map((company) => (
            <li key={company.partner_id} className="flex flex-wrap items-center justify-between gap-3 border border-line px-4 py-3">
              <div>
                <Link to={`/vertriebspartner/${company.partner_id}`} className="font-semibold text-petrol">
                  {company.company_name}
                </Link>
                <p className="text-sm text-muted">{company.city ?? 'Kein Ort'}</p>
                {company.is_primary ? <Badge tone="petrol">Primär</Badge> : null}
              </div>
              <div className="flex flex-wrap gap-2">
                {company.is_primary ? null : (
                  <Button
                    variant="secondary"
                    onClick={() => {
                      void makePrimaryContact(contact.id, company.partner_id)
                        .then((updated) => {
                          onChange(updated)
                          notify({ tone: 'success', message: 'Die primäre Kontaktperson wurde festgelegt.' })
                        })
                        .catch((caught: unknown) => {
                          notify({
                            tone: 'critical',
                            message: caught instanceof ApiError ? caught.message : 'Die Änderung ist fehlgeschlagen.',
                          })
                        })
                    }}
                  >
                    Als primär festlegen
                  </Button>
                )}
                <Button variant="danger" onClick={() => setRemoveId(company.partner_id)}>
                  Zuordnung entfernen
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {contact.archived_at ? null : (
        <div className="grid gap-3 border border-line p-4 md:grid-cols-[minmax(0,1fr)_auto] md:items-end">
          <Select label="Weiteres Unternehmen" value={partnerId} options={options} onChange={setPartnerId} />
          <Button onClick={() => void addCompany()} disabled={!partnerId}>
            Zuordnen
          </Button>
          <label className="flex min-h-11 items-center gap-2 text-sm font-semibold md:col-span-2">
            <input type="checkbox" checked={isPrimary} onChange={(event) => setIsPrimary(event.target.checked)} />
            Als primäre Kontaktperson festlegen
          </label>
        </div>
      )}
      <ConfirmDialog
        open={removeId !== null}
        title="Zuordnung entfernen"
        description="Nur die Verknüpfung wird entfernt. Kontakt und Historie bleiben gespeichert."
        confirmLabel="Entfernen"
        tone="danger"
        onConfirm={() => void remove()}
        onCancel={() => setRemoveId(null)}
      />
    </div>
  )
}

function Field({ label, children }: { label: string; children: string }) {
  return (
    <div>
      <dt className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</dt>
      <dd className="mt-1 text-sm leading-6 break-words">{children}</dd>
    </div>
  )
}
