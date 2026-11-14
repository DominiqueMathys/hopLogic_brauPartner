import { useState, type ReactNode } from 'react'
import { Link, useParams } from 'react-router'
import { LinkedActivities, LinkedTasks, PartnerContacts } from '../../components/crm/LinkedRecords.tsx'
import { PartnerDeals, PartnerOrders } from '../../components/sales/RelatedRecords.tsx'
import { PartnerAnalysisPanel, PartnerService } from '../../components/service/RelatedService.tsx'
import { ApiError, archivePartner, restorePartner } from '../../api/partners.ts'
import { Badge } from '../../components/ui/Badge.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ConfirmDialog } from '../../components/ui/ConfirmDialog.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Tabs } from '../../components/ui/Tabs.tsx'
import { useToast } from '../../components/ui/toast-state.ts'
import {
  choiceLabel,
  formatDate,
  formatDateTime,
  formatLocation,
  partnerStatusOptions,
  partnerTypeOptions,
  priorityOptions,
  statusTone,
  type Partner,
} from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'
import { usePartner } from './usePartner.ts'

export function PartnerDetailPage() {
  const { partnerId } = useParams()
  const { partner, setPartner, error, pending } = usePartner(partnerId)
  const { notify } = useToast()
  const [archiveOpen, setArchiveOpen] = useState(false)
  const [restoreOpen, setRestoreOpen] = useState(false)
  const [actionPending, setActionPending] = useState(false)
  usePageTitle(partner?.company_name ?? 'Vertriebspartner')

  async function runAction(action: 'archive' | 'restore') {
    if (!partner) {
      return
    }
    setArchiveOpen(false)
    setRestoreOpen(false)
    setActionPending(true)
    try {
      const updated = action === 'archive' ? await archivePartner(partner.id) : await restorePartner(partner.id)
      setPartner(updated)
      notify({
        tone: 'success',
        message:
          action === 'archive'
            ? 'Der Vertriebspartner wurde archiviert.'
            : 'Der Vertriebspartner wurde wiederhergestellt.',
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

  if (!partnerId || (!partner && !pending)) {
    return (
      <ErrorState
        title="Partner nicht gefunden"
        description={error ?? 'Der Vertriebspartner wurde nicht gefunden.'}
        action={
          <Link to="/vertriebspartner" className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Zur Übersicht
          </Link>
        }
      />
    )
  }

  if (!partner) {
    return <LoadingState label="Partner wird geladen" />
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-3xl font-semibold tracking-tight">{partner.company_name}</h1>
            <Badge tone={statusTone(partner.status)}>{choiceLabel(partnerStatusOptions, partner.status)}</Badge>
            {partner.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
            {partner.archived_at ? <Badge tone="critical">Archiviert</Badge> : null}
          </div>
          <p className="mt-2 text-sm leading-6 text-muted">{formatLocation(partner)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Link to="/vertriebspartner" className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Zur Übersicht
          </Link>
          {partner.archived_at ? (
            <Button disabled={actionPending} onClick={() => setRestoreOpen(true)}>
              Wiederherstellen
            </Button>
          ) : (
            <>
              <Link to={`/vertriebspartner/${partner.id}/bearbeiten`} className={cx(buttonStyles.base, buttonStyles.primary)}>
                Bearbeiten
              </Link>
              <Button variant="danger" disabled={actionPending} onClick={() => setArchiveOpen(true)}>
                Archivieren
              </Button>
            </>
          )}
        </div>
      </header>

      {partner.is_demo ? (
        <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6 text-ink">
          Fiktiver Testdatensatz. Keine echte Kundenbeziehung des Liechtensteiner Brauhauses.
        </p>
      ) : null}
      {partner.archived_at ? (
        <p className="border border-line bg-cream-deep px-4 py-3 text-sm leading-6 text-ink">
          Dieser Vertriebspartner ist seit {formatDateTime(partner.archived_at)} archiviert. Die Daten bleiben für die
          Kundenhistorie erhalten.
        </p>
      ) : null}

      <Card className="p-4">
        <Tabs
          label="Partnerbereiche"
          tabs={[
            { id: 'overview', label: 'Übersicht', content: <Overview partner={partner} /> },
            {
              id: 'contacts',
              label: 'Kontakte',
              content: <PartnerContacts partnerId={partner.id} />,
            },
            {
              id: 'activities',
              label: 'Aktivitäten',
              content: <LinkedActivities partnerId={partner.id} owner={partner.account_owner ?? ''} />,
            },
            {
              id: 'tasks',
              label: 'Aufgaben',
              content: <LinkedTasks partnerId={partner.id} />,
            },
            {
              id: 'opportunities',
              label: 'Verkaufschancen',
              content: <PartnerDeals partnerId={partner.id} />,
            },
            {
              id: 'orders',
              label: 'Bestellungen',
              content: <PartnerOrders partnerId={partner.id} />,
            },
            {
              id: 'service',
              label: 'Kundenservice',
              content: <PartnerService partnerId={partner.id} />,
            },
            {
              id: 'analysis',
              label: 'Kundenanalyse',
              content: <PartnerAnalysisPanel partnerId={partner.id} />,
            },
          ]}
        />
      </Card>

      <ConfirmDialog
        open={archiveOpen}
        title="Partner archivieren"
        description="Der Partner bleibt mit der Kundenhistorie gespeichert und verschwindet aus der Standardliste. Sie können ihn später wiederherstellen."
        confirmLabel="Archivieren"
        tone="danger"
        onConfirm={() => void runAction('archive')}
        onCancel={() => setArchiveOpen(false)}
      />
      <ConfirmDialog
        open={restoreOpen}
        title="Partner wiederherstellen"
        description="Der Partner erscheint wieder in der Standardliste."
        confirmLabel="Wiederherstellen"
        onConfirm={() => void runAction('restore')}
        onCancel={() => setRestoreOpen(false)}
      />
    </div>
  )
}

function Overview({ partner }: { partner: Partner }) {
  return (
    <div className="grid gap-6">
      <section>
        <h2 className="text-base font-semibold">Unternehmen</h2>
        <dl className="mt-3 grid gap-4 sm:grid-cols-2">
          <Field label="Unternehmensname">{partner.company_name}</Field>
          <Field label="ERP-Kundennummer">{partner.erp_customer_number ?? 'Keine Angabe'}</Field>
          <Field label="ERP-Kundenstatus">{partner.erp_customer_status ?? 'Keine Angabe'}</Field>
          <Field label="Synchronisationsquelle">{partner.erp_source === 'mock' ? 'Mock-ERP, Testdaten' : partner.erp_source ?? 'Keine externe Quelle'}</Field>
          <Field label="Letzte ERP-Aktualisierung">{partner.erp_synced_at ? formatDateTime(partner.erp_synced_at) : 'Keine'}</Field>
          <Field label="Partnertyp">{choiceLabel(partnerTypeOptions, partner.partner_type)}</Field>
          <Field label="Branche">{partner.industry ?? 'Keine Angabe'}</Field>
          <Field label="Strasse und Hausnummer">{partner.street ?? 'Keine Angabe'}</Field>
          <Field label="Standort">{formatLocation(partner)}</Field>
          <Field label="Telefon">
            {partner.phone ? <a href={`tel:${partner.phone}`}>{partner.phone}</a> : 'Keine Angabe'}
          </Field>
          <Field label="E-Mail">
            {partner.email ? <a href={`mailto:${partner.email}`}>{partner.email}</a> : 'Keine Angabe'}
          </Field>
          <Field label="Website">
            {partner.website ? (
              <a href={partner.website} rel="noreferrer" target="_blank">
                {partner.website}
              </a>
            ) : (
              'Keine Angabe'
            )}
          </Field>
        </dl>
      </section>
      <section>
        <h2 className="text-base font-semibold">Betreuung</h2>
        <dl className="mt-3 grid gap-4 sm:grid-cols-2">
          <Field label="Partnerstatus">{choiceLabel(partnerStatusOptions, partner.status)}</Field>
          <Field label="Zuständige Betreuungsperson">{partner.account_owner ?? 'Nicht zugewiesen'}</Field>
          <Field label="Akquisitionsquelle">{partner.acquisition_source ?? 'Keine Angabe'}</Field>
          <Field label="Priorität">{choiceLabel(priorityOptions, partner.priority)}</Field>
          <Field label="Erste Kontaktaufnahme">{formatDate(partner.first_contact_on)}</Field>
          <Field label="Letzter Kontakt">
            {partner.last_contact_at ? formatDateTime(partner.last_contact_at) : 'Kein Eintrag'}
          </Field>
          <Field label="Nächste Aktivität">
            {partner.next_activity_on ? formatDate(partner.next_activity_on) : 'Kein Eintrag'}
          </Field>
          <Field label="Erfasst am">{formatDateTime(partner.created_at)}</Field>
          <Field label="Zuletzt geändert">{formatDateTime(partner.updated_at)}</Field>
        </dl>
        <p className="mt-3 text-sm leading-6 text-muted">
          Letzter Kontakt stammt aus den Aktivitäten. Die nächste Aktivität ist die früheste offene Aufgabe.
        </p>
        <div className="mt-4">
          <h3 className="text-sm font-semibold">Interne Bemerkungen</h3>
          <p className="mt-2 whitespace-pre-wrap text-sm leading-6">
            {partner.notes ?? 'Keine Bemerkungen'}
          </p>
        </div>
      </section>
    </div>
  )
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <dt className="text-xs font-semibold tracking-wide text-muted uppercase">{label}</dt>
      <dd className="mt-1 text-sm leading-6 break-words">{children}</dd>
    </div>
  )
}

