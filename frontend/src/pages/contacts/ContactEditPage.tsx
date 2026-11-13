import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { ApiError, updateContact } from '../../api/crm.ts'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { useToast } from '../../components/ui/toast-state.ts'
import { contactToForm, type ContactInput } from '../../domain/crm.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'
import { ContactForm } from './ContactForm.tsx'
import { useContact } from './useContact.ts'

export function ContactEditPage() {
  const { contactId } = useParams()
  const { contact, error, pending: loading } = useContact(contactId)
  const navigate = useNavigate()
  const { notify } = useToast()
  const [pending, setPending] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)
  usePageTitle(contact ? `${contact.first_name} ${contact.last_name} bearbeiten` : 'Kontakt bearbeiten')

  async function save(values: ContactInput) {
    if (!contact) {
      return
    }
    setPending(true)
    setFormError(null)
    try {
      const updated = await updateContact(contact.id, values)
      notify({ tone: 'success', message: 'Der Kontakt wurde gespeichert.' })
      navigate(`/kontakte/${updated.id}`)
    } catch (caught) {
      if (caught instanceof ApiError) {
        setFieldErrors(caught.fieldErrors)
        setFormError(caught.message)
      } else {
        setFormError('Die Verbindung zur API ist fehlgeschlagen.')
      }
      setPending(false)
    }
  }

  if (loading) {
    return <LoadingState label="Kontakt wird geladen" />
  }
  if (!contact) {
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
  if (contact.archived_at) {
    return (
      <ErrorState
        title="Archivierter Kontakt"
        description="Archivierte Kontakte können erst nach der Wiederherstellung bearbeitet werden."
        action={
          <Link to={`/kontakte/${contact.id}`} className={cx(buttonStyles.base, buttonStyles.secondary)}>
            Zurück zum Kontakt
          </Link>
        }
      />
    )
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Kontakt bearbeiten</h1>
      </header>
      <ContactForm
        key={contact.updated_at}
        initial={contactToForm(contact)}
        submitLabel="Änderungen speichern"
        pending={pending}
        fieldErrors={fieldErrors}
        formError={formError}
        demo={contact.is_demo}
        showCompany={false}
        companyOptions={[]}
        cancelTo={`/kontakte/${contact.id}`}
        onSubmit={(values) => void save(values)}
        onInvalid={setFieldErrors}
      />
    </div>
  )
}
