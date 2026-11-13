import { useState } from 'react'
import { Link } from 'react-router'
import { ApiError, archiveActivity, restoreActivity } from '../../api/crm.ts'
import { activityTypeOptions, labelOf, type Activity } from '../../domain/crm.ts'
import { formatDateTime } from '../../domain/partners.ts'
import { Badge } from '../ui/Badge.tsx'
import { Button } from '../ui/Button.tsx'
import { ConfirmDialog } from '../ui/ConfirmDialog.tsx'
import { EmptyState } from '../ui/EmptyState.tsx'
import { useToast } from '../ui/toast-state.ts'

type ActivityTimelineProps = {
  items: Activity[]
  onChanged: () => void
}

export function ActivityTimeline({ items, onChanged }: ActivityTimelineProps) {
  const { notify } = useToast()
  const [pendingId, setPendingId] = useState<string | null>(null)
  const selected = items.find((item) => item.id === pendingId) ?? null

  async function confirm() {
    if (!selected) {
      return
    }
    const archived = Boolean(selected.archived_at)
    setPendingId(null)
    try {
      if (archived) {
        await restoreActivity(selected.id)
      } else {
        await archiveActivity(selected.id)
      }
      notify({
        tone: 'success',
        message: archived ? 'Die Aktivität wurde wiederhergestellt.' : 'Die Aktivität wurde archiviert.',
      })
      onChanged()
    } catch (caught) {
      notify({
        tone: 'critical',
        message: caught instanceof ApiError ? caught.message : 'Die Verbindung zur API ist fehlgeschlagen.',
      })
    }
  }

  if (items.length === 0) {
    return (
      <EmptyState
        title="Keine Aktivitäten"
        description="Telefonate, Besuche, Meetings und Notizen erscheinen hier, sobald sie erfasst sind."
      />
    )
  }

  return (
    <div className="grid gap-3">
    <ol className="grid gap-3">
      {items.map((item) => (
        <li key={item.id} className="border border-line bg-card px-4 py-3">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <p className="text-xs font-semibold tracking-wide text-muted uppercase">
                {formatDateTime(item.occurred_at)}
              </p>
              <h3 className="mt-1 text-base font-semibold">{item.title}</h3>
              <p className="mt-1 text-sm text-muted">
                {labelOf(activityTypeOptions, item.activity_type)}
                {item.account_owner ? ` · ${item.account_owner}` : ''}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              {item.is_demo ? <Badge tone="accent">Testdaten</Badge> : null}
              {item.archived_at ? <Badge tone="critical">Archiviert</Badge> : null}
            </div>
          </div>
          {item.description ? <p className="mt-2 whitespace-pre-wrap text-sm leading-6">{item.description}</p> : null}
          <p className="mt-2 text-sm text-muted">
            {item.contact_name ? (
              item.contact_id ? (
                <Link to={`/kontakte/${item.contact_id}`} className="font-semibold text-petrol">
                  {item.contact_name}
                </Link>
              ) : (
                item.contact_name
              )
            ) : null}
            {item.contact_name && item.company_name ? ' · ' : null}
            {item.company_name ? (
              item.partner_id ? (
                <Link to={`/vertriebspartner/${item.partner_id}`} className="font-semibold text-petrol">
                  {item.company_name}
                </Link>
              ) : (
                item.company_name
              )
            ) : null}
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link to={`/aktivitaeten/${item.id}/bearbeiten`} className="text-sm font-semibold text-petrol">
              Bearbeiten
            </Link>
            <Button variant="ghost" onClick={() => setPendingId(item.id)}>
              {item.archived_at ? 'Wiederherstellen' : 'Archivieren'}
            </Button>
          </div>
        </li>
      ))}
    </ol>
      <ConfirmDialog
        open={selected !== null}
        title={selected?.archived_at ? 'Aktivität wiederherstellen' : 'Aktivität archivieren'}
        description={
          selected?.archived_at
            ? 'Die Aktivität erscheint wieder in der Chronik.'
            : 'Die Aktivität bleibt gespeichert und verschwindet aus der Standardchronik.'
        }
        confirmLabel={selected?.archived_at ? 'Wiederherstellen' : 'Archivieren'}
        tone={selected?.archived_at ? 'primary' : 'danger'}
        onConfirm={() => void confirm()}
        onCancel={() => setPendingId(null)}
      />
    </div>
  )
}
