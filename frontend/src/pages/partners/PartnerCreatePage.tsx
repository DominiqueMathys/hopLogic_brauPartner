import { useState } from 'react'
import { useNavigate } from 'react-router'
import { ApiError, createPartner } from '../../api/partners.ts'
import { useToast } from '../../components/ui/toast-state.ts'
import { emptyPartnerForm, type PartnerInput } from '../../domain/partners.ts'
import { usePageTitle } from '../../usePageTitle.ts'
import { PartnerForm } from './PartnerForm.tsx'

export function PartnerCreatePage() {
  usePageTitle('Neuen Partner erstellen')
  const navigate = useNavigate()
  const { notify } = useToast()
  const [pending, setPending] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)

  async function submit(values: PartnerInput) {
    setPending(true)
    setFieldErrors({})
    setFormError(null)
    try {
      const created = await createPartner(values)
      notify({ tone: 'success', message: 'Der Vertriebspartner wurde erstellt.' })
      navigate(`/vertriebspartner/${created.id}`)
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

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Neuen Partner erstellen</h1>
        <p className="mt-2 text-base leading-7 text-muted">
          Erfassen Sie die Unternehmens- und CRM-Daten. Der Unternehmensname ist ein Pflichtfeld.
        </p>
      </header>
      <PartnerForm
        initial={emptyPartnerForm}
        submitLabel="Partner erstellen"
        pending={pending}
        fieldErrors={fieldErrors}
        formError={formError}
        demo={false}
        cancelTo="/vertriebspartner"
        onSubmit={(values) => void submit(values)}
        onInvalid={(errors) => {
          setFieldErrors(errors)
          setFormError('Bitte prüfen Sie die markierten Felder.')
        }}
      />
    </div>
  )
}
