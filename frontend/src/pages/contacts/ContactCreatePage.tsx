import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router'
import { ApiError, createContact } from '../../api/crm.ts'
import { fetchPartners } from '../../api/partners.ts'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { useToast } from '../../components/ui/toast-state.ts'
import { emptyContactForm, type ContactInput } from '../../domain/crm.ts'
import type { PartnerQuery } from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'
import { usePageTitle } from '../../usePageTitle.ts'
import { ContactForm } from './ContactForm.tsx'

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

export function ContactCreatePage() {
  usePageTitle('Neuer Kontakt')
  const navigate = useNavigate()
  const { notify } = useToast()
  const [params] = useSearchParams()
  const companyId = params.get('unternehmen') ?? ''
  const [options, setOptions] = useState<{ value: string; label: string }[]>([{ value: '', label: 'Kein Unternehmen' }])
  const [pending, setPending] = useState(false)
  const [loading, setLoading] = useState(true)
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
  const [formError, setFormError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    void fetchPartners(partnerQuery)
      .then((result) => {
        if (!active) {
          return
        }
        const choices = result.items.map((partner) => ({
          value: partner.id,
          label: partner.city ? `${partner.company_name}, ${partner.city}` : partner.company_name,
        }))
        setOptions([{ value: '', label: 'Kein Unternehmen' }, ...choices])
        setLoading(false)
      })
      .catch(() => {
        if (active) {
          setLoading(false)
        }
      })
    return () => {
      active = false
    }
  }, [])

  async function save(values: ContactInput) {
    setPending(true)
    setFormError(null)
    try {
      const created = await createContact(values)
      notify({ tone: 'success', message: 'Der Kontakt wurde erstellt.' })
      navigate(`/kontakte/${created.id}`)
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
    return <LoadingState label="Unternehmen werden geladen" />
  }

  return (
    <div className="mx-auto grid max-w-3xl gap-6">
      <header>
        <h1 className="text-3xl font-semibold tracking-tight">Neuen Kontakt erstellen</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          Personendaten werden nur mit einer bewusst gewählten Rechtsgrundlage dokumentiert.
        </p>
      </header>
      {companyId && !options.some((option) => option.value === companyId) ? (
        <ErrorState
          title="Unternehmen nicht in der Auswahlliste"
          description="Der gewählte Partner steht nicht auf der ersten Seite. Wählen Sie das Unternehmen in der Liste oder lassen Sie die Zuordnung leer."
          action={
            <Link to="/vertriebspartner" className={cx(buttonStyles.base, buttonStyles.secondary)}>
              Zur Partnerliste
            </Link>
          }
        />
      ) : (
        <ContactForm
          initial={{ ...emptyContactForm, partner_id: companyId }}
          submitLabel="Kontakt erstellen"
          pending={pending}
          fieldErrors={fieldErrors}
          formError={formError}
          demo={false}
          showCompany
          companyOptions={options}
          cancelTo={companyId ? `/vertriebspartner/${companyId}` : '/kontakte'}
          onSubmit={(values) => void save(values)}
          onInvalid={setFieldErrors}
        />
      )}
    </div>
  )
}
