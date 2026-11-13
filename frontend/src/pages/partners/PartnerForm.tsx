import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { Button } from '../../components/ui/Button.tsx'
import { buttonStyles } from '../../components/ui/button-styles.ts'
import { Card } from '../../components/ui/Card.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { Textarea } from '../../components/ui/Textarea.tsx'
import {
  acquisitionOptions,
  countryOptions,
  partnerStatusOptions,
  partnerTypeOptions,
  priorityOptions,
  validatePartner,
  withCurrent,
  type PartnerInput,
} from '../../domain/partners.ts'
import { cx } from '../../lib/cx.ts'

type PartnerFormProps = {
  initial: PartnerInput
  submitLabel: string
  pending: boolean
  fieldErrors: Record<string, string>
  formError: string | null
  demo: boolean
  cancelTo: string
  onSubmit: (values: PartnerInput) => void
  onInvalid: (errors: Record<string, string>) => void
}

export function PartnerForm({
  initial,
  submitLabel,
  pending,
  fieldErrors,
  formError,
  demo,
  cancelTo,
  onSubmit,
  onInvalid,
}: PartnerFormProps) {
  const [values, setValues] = useState(initial)

  function setField(field: keyof PartnerInput, value: string) {
    setValues((current) => ({ ...current, [field]: value }))
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const errors = validatePartner(values)
    if (Object.keys(errors).length > 0) {
      onInvalid(errors)
      return
    }
    onSubmit(values)
  }

  return (
    <form className="grid gap-4" noValidate onSubmit={handleSubmit}>
      {formError ? <ErrorState title="Speichern nicht möglich" description={formError} /> : null}
      {demo ? (
        <p className="border border-gold bg-gold-soft px-4 py-3 text-sm leading-6 text-ink">
          Dieser Datensatz ist als Testdaten gekennzeichnet. Ein erneuter Seed setzt die Musterwerte zurück.
        </p>
      ) : null}
      <Card className="p-4">
        <fieldset className="grid gap-4" disabled={pending}>
          <legend className="text-base font-semibold">Unternehmensdaten</legend>
          <Input
            label="Unternehmensname"
            value={values.company_name}
            error={fieldErrors.company_name}
            autoComplete="organization"
            maxLength={200}
            required
            onChange={(event) => setField('company_name', event.target.value)}
          />
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="ERP-Kundennummer"
              value={values.erp_customer_number}
              error={fieldErrors.erp_customer_number}
              hint="Optional. Eine Kundennummer darf nur einmal vorkommen."
              maxLength={40}
              spellCheck={false}
              onChange={(event) => setField('erp_customer_number', event.target.value)}
            />
            <Select
              label="Partnertyp"
              value={values.partner_type}
              error={fieldErrors.partner_type}
              options={[{ value: '', label: 'Bitte wählen' }, ...partnerTypeOptions]}
              onChange={(value) => setField('partner_type', value)}
            />
            <Input
              label="Branche"
              value={values.industry}
              error={fieldErrors.industry}
              maxLength={120}
              onChange={(event) => setField('industry', event.target.value)}
            />
            <Input
              label="Strasse und Hausnummer"
              value={values.street}
              error={fieldErrors.street}
              autoComplete="street-address"
              maxLength={200}
              onChange={(event) => setField('street', event.target.value)}
            />
            <Input
              label="Postleitzahl"
              value={values.postal_code}
              error={fieldErrors.postal_code}
              autoComplete="postal-code"
              maxLength={12}
              onChange={(event) => setField('postal_code', event.target.value)}
            />
            <Input
              label="Ort"
              value={values.city}
              error={fieldErrors.city}
              autoComplete="address-level2"
              maxLength={120}
              onChange={(event) => setField('city', event.target.value)}
            />
            <Input
              label="Kanton/Region"
              value={values.region}
              error={fieldErrors.region}
              autoComplete="address-level1"
              maxLength={120}
              onChange={(event) => setField('region', event.target.value)}
            />
            <Select
              label="Land"
              value={values.country}
              error={fieldErrors.country}
              options={withCurrent(countryOptions, values.country)}
              onChange={(value) => setField('country', value)}
            />
            <Input
              label="Geschäftliche Telefonnummer"
              type="tel"
              value={values.phone}
              error={fieldErrors.phone}
              autoComplete="tel"
              maxLength={40}
              onChange={(event) => setField('phone', event.target.value)}
            />
            <Input
              label="Geschäftliche E-Mail"
              type="email"
              value={values.email}
              error={fieldErrors.email}
              autoComplete="email"
              maxLength={254}
              spellCheck={false}
              onChange={(event) => setField('email', event.target.value)}
            />
          </div>
          <Input
            label="Website"
            type="url"
            value={values.website}
            error={fieldErrors.website}
            hint="Mit https:// beginnen."
            autoComplete="url"
            maxLength={300}
            spellCheck={false}
            onChange={(event) => setField('website', event.target.value)}
          />
        </fieldset>
      </Card>
      <Card className="p-4">
        <fieldset className="grid gap-4 sm:grid-cols-2" disabled={pending}>
          <legend className="text-base font-semibold sm:col-span-2">CRM-Informationen</legend>
          <Select
            label="Partnerstatus"
            value={values.status}
            error={fieldErrors.status}
            options={partnerStatusOptions}
            onChange={(value) => setField('status', value)}
          />
          <Input
            label="Zuständige Betreuungsperson"
            value={values.account_owner}
            error={fieldErrors.account_owner}
            hint="Freitext, bis Benutzerkonten vorhanden sind."
            maxLength={120}
            onChange={(event) => setField('account_owner', event.target.value)}
          />
          <Select
            label="Akquisitionsquelle"
            value={values.acquisition_source}
            error={fieldErrors.acquisition_source}
            options={withCurrent(acquisitionOptions, values.acquisition_source)}
            onChange={(value) => setField('acquisition_source', value)}
          />
          <Select
            label="Priorität"
            value={values.priority}
            error={fieldErrors.priority}
            options={priorityOptions}
            onChange={(value) => setField('priority', value)}
          />
          <Input
            label="Datum der ersten Kontaktaufnahme"
            type="date"
            value={values.first_contact_on}
            error={fieldErrors.first_contact_on}
            onChange={(event) => setField('first_contact_on', event.target.value)}
          />
          <div className="sm:col-span-2">
            <Textarea
              label="Interne Bemerkungen"
              value={values.notes}
              error={fieldErrors.notes}
              hint="Nur intern sichtbar."
              maxLength={4000}
              rows={5}
              onChange={(event) => setField('notes', event.target.value)}
            />
          </div>
        </fieldset>
      </Card>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={pending}>
          {pending ? 'Wird gespeichert…' : submitLabel}
        </Button>
        <Link to={cancelTo} className={cx(buttonStyles.base, buttonStyles.secondary)}>
          Abbrechen
        </Link>
      </div>
    </form>
  )
}
