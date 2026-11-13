import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ApiError, updatePartner } from '../../api/partners.ts'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { useToast } from '../../components/ui/toast-state.ts'
import { toForm, type PartnerInput } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'
import { PartnerForm } from './PartnerForm.tsx'
import { usePartner } from './usePartner.ts'

export function PartnerEditPage() {
  const { partnerId } = useParams()
  const { partner, error, pending } = usePartner(partnerId)
  const navigate = useNavigate()
  const { notify } = useToast()
  const [saving, setSaving] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  usePageTitle(partner ? `${partner.company_name} bearbeiten` : 'Partner bearbeiten')

  async function submit(values: PartnerInput) {
    if (!partner) {
      return
    }
    setSaving(true)
    setFieldErrors({})
    setFormError(null)
    try {
      await updatePartner(partner.id, values)
      notify({ tone: 'success', message: 'Die Änderungen wurden gespeichert.' })
      navigate(`/vertriebspartner/${partner.id}`)
    } catch (caught) {
      if (caught instanceof ApiError) {
        setFieldErrors(caught.fieldErrors)
        setFormError(caught.message)
      } else {
        setFormError('Die Verbindung zur API ist fehlgeschlagen.')
      }
      setSaving(false)
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

  if (partner.archived_at) {
    return (
      <ErrorState
        title="Partner ist archiviert"
        description="Stellen Sie den Partner wieder her, bevor Sie ihn bearbeiten."
        action={
          <Link to={`/vertriebspartner/${partner.id}`} className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Zur Detailseite
          </Link>
        }
      />
    )
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">{partner.company_name} bearbeiten</h1>
        <p className="mt-2 text-base leading-7 text-muted">
          Änderungen an Unternehmensdaten, Status und Betreuung werden in der Datenbank gespeichert.
        </p>
      </header>
      <PartnerForm
        key={partner.updated_at}
        initial={toForm(partner)}
        submitLabel="Änderungen speichern"
        pending={saving}
        fieldErrors={fieldErrors}
        formError={formError}
        demo={partner.is_demo}
        cancelTo={`/vertriebspartner/${partner.id}`}
        onSubmit={(values) => void submit(values)}
        onInvalid={(errors) => {
          setFieldErrors(errors)
          setFormError('Bitte prüfen Sie die markierten Felder.')
        }}
      />
    </div>
  )
}
