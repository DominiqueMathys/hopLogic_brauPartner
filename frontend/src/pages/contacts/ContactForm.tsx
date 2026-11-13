import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select, type SelectOption } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import {
  channelOptions,
  contactStatusOptions,
  languageOptions,
  leadStatusOptions,
  lifecycleOptions,
  processingBasisOptions,
  validateContact,
  type ContactInput,
} from '../../domain/crm.ts'
import { cx } from '../../lib/cx.ts'

type ContactFormProps = {
  initial: ContactInput
  submitLabel: string
  pending: boolean
  fieldErrors: Record<string, string>
  formError: string | null
  demo: boolean
  showCompany: boolean
  companyOptions: SelectOption[]
  cancelTo: string
  onSubmit: (values: ContactInput) => void
  onInvalid: (errors: Record<string, string>) => void
}

export function ContactForm({
  initial,
  submitLabel,
  pending,
  fieldErrors,
  formError,
  demo,
  showCompany,
  companyOptions,
  cancelTo,
  onSubmit,
  onInvalid,
}: ContactFormProps) {
  const [values, setValues] = useState(initial)

  function setField(field: keyof ContactInput, value: string | boolean) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    const errors = validateContact(values)
    if (Object.keys(errors).length > 0) {
      onInvalid(errors)
      return
    }
    onSubmit(values)
  }

  return (
    <form className="grid gap-6" onSubmit={submit} noValidate>
      {formError ? <ErrorState title="Speichern fehlgeschlagen" description={formError} /> : null}
      {demo ? (
        <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6">
          Dieser Kontakt ist ein gekennzeichneter Testdatensatz.
        </p>
      ) : null}
      <Card className="grid gap-4 p-4">
        <h2 className="text-base font-semibold">Person</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Input label="Vorname" value={values.first_name} error={fieldErrors.first_name} onChange={(event) => setField('first_name', event.target.value)} />
          <Input label="Nachname" value={values.last_name} error={fieldErrors.last_name} onChange={(event) => setField('last_name', event.target.value)} />
          <Input label="Funktion" value={values.job_title} onChange={(event) => setField('job_title', event.target.value)} />
          <Input label="Geschäftliche E-Mail" type="email" value={values.email} error={fieldErrors.email} onChange={(event) => setField('email', event.target.value)} />
          <Input label="Geschäftliche Telefonnummer" value={values.phone} error={fieldErrors.phone} onChange={(event) => setField('phone', event.target.value)} />
          <Input label="Mobilnummer" value={values.mobile} error={fieldErrors.mobile} onChange={(event) => setField('mobile', event.target.value)} />
          <Select label="Bevorzugte Sprache" value={values.preferred_language} options={languageOptions} onChange={(value) => setField('preferred_language', value)} />
          <Select label="Bevorzugter Kommunikationskanal" value={values.preferred_channel} options={channelOptions} onChange={(value) => setField('preferred_channel', value)} />
        </div>
      </Card>
      <Card className="grid gap-4 p-4">
        <h2 className="text-base font-semibold">CRM</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          <Select label="Lifecycle-Phase" value={values.lifecycle_phase} options={[{ value: '', label: 'Bitte wählen' }, ...lifecycleOptions]} error={fieldErrors.lifecycle_phase} onChange={(value) => setField('lifecycle_phase', value)} />
          <Select
            label="Leadstatus"
            value={values.lead_status}
            options={leadStatusOptions}
            hint="Unabhängig von der Lifecycle-Phase. Eine Kundin muss keinen offenen Lead haben."
            onChange={(value) => setField('lead_status', value)}
          />
          <Select label="Kontaktstatus" value={values.status} options={contactStatusOptions} onChange={(value) => setField('status', value)} />
          <Input label="Zuständige Betreuungsperson" value={values.account_owner} onChange={(event) => setField('account_owner', event.target.value)} />
          <Select
            label="Rechtsgrundlage"
            value={values.processing_basis}
            options={processingBasisOptions}
            hint="Nichts wird automatisch als Einwilligung angenommen."
            onChange={(value) => setField('processing_basis', value)}
          />
        </div>
        <Textarea label="Dokumentation der Rechtsgrundlage" value={values.processing_basis_note} onChange={(event) => setField('processing_basis_note', event.target.value)} />
        <Textarea label="Interne Bemerkungen" value={values.notes} onChange={(event) => setField('notes', event.target.value)} />
      </Card>
      {showCompany ? (
        <Card className="grid gap-4 p-4">
          <h2 className="text-base font-semibold">Unternehmen</h2>
          <Select label="Zugeordnetes Unternehmen" value={values.partner_id} options={companyOptions} onChange={(value) => setField('partner_id', value)} />
          <label className="flex min-h-11 items-center gap-2 text-sm font-semibold">
            <input type="checkbox" checked={values.is_primary} onChange={(event) => setField('is_primary', event.target.checked)} />
            Primäre Kontaktperson für dieses Unternehmen
          </label>
          <p className="text-sm leading-6 text-muted">Weitere Unternehmen können auf der Kontaktseite zugeordnet werden.</p>
        </Card>
      ) : null}
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending}>
          {submitLabel}
        </Button>
        <Link to={cancelTo} className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Abbrechen
        </Link>
      </div>
    </form>
  )
}
