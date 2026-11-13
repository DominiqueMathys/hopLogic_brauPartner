import { useEffect, useState, type FormEvent } from 'react'
import { errorMessage, fetchPreference, savePreference } from '../../api/engagement.ts'
import { Button } from '../ui/Button.tsx'
import { Input } from '../ui/Input.tsx'
import { LoadingState } from '../ui/LoadingState.tsx'
import { Select } from '../ui/Select.tsx'
import { Textarea } from '../ui/Textarea.tsx'
import { channelOptions, type Preference } from '../../domain/engagement.ts'

type PreferencePanelProps = {
  contactId: string
}

export function PreferencePanel({ contactId }: PreferencePanelProps) {
  const [row, setRow] = useState<Preference | null>(null)
  const [channel, setChannel] = useState('telefon')
  const [allowed, setAllowed] = useState(false)
  const [rejected, setRejected] = useState(false)
  const [consentOn, setConsentOn] = useState('')
  const [source, setSource] = useState('')
  const [evidence, setEvidence] = useState('')
  const [revokedOn, setRevokedOn] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)

  useEffect(() => {
    let active = true
    void fetchPreference(contactId)
      .then((preference) => {
        if (!active) return
        setRow(preference)
        setChannel(preference.preferred_channel)
        setAllowed(preference.email_marketing_allowed)
        setRejected(preference.marketing_rejected)
        setConsentOn(preference.consent_on ?? '')
        setSource(preference.consent_source ?? '')
        setEvidence(preference.consent_evidence ?? '')
        setRevokedOn(preference.revoked_on ?? '')
      })
      .catch((caught: unknown) => {
        if (active) setError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [contactId])

  function submit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError('')
    void savePreference(contactId, {
      preferred_channel: channel,
      email_marketing_allowed: allowed,
      marketing_rejected: rejected,
      consent_on: consentOn || null,
      consent_source: source || null,
      consent_evidence: evidence || null,
      revoked_on: revokedOn || null,
    })
      .then(setRow)
      .catch((caught: unknown) => setError(errorMessage(caught)))
      .finally(() => setPending(false))
  }

  if (!row && !error) return <LoadingState label="Kommunikationspräferenzen werden geladen" />

  return (
    <form className="grid gap-3" onSubmit={submit}>
      {row ? <p className="text-sm leading-6">{row.notice}</p> : null}
      {row && !row.stored ? (
        <p className="text-sm leading-6">Es ist noch keine Präferenz gespeichert. Es wird keine Einwilligung angenommen.</p>
      ) : null}
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <Select label="Bevorzugter Kommunikationskanal" value={channel} onChange={setChannel} options={channelOptions} />
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={allowed} onChange={(event) => setAllowed(event.target.checked)} />
        E-Mail-Marketing erlaubt
      </label>
      <label className="flex items-center gap-2 text-sm">
        <input type="checkbox" checked={rejected} onChange={(event) => setRejected(event.target.checked)} />
        Marketingkommunikation abgelehnt
      </label>
      <Input label="Datum der Einwilligung" type="date" value={consentOn} onChange={(event) => setConsentOn(event.target.value)} />
      <Input label="Quelle der Einwilligung" value={source} onChange={(event) => setSource(event.target.value)} hint="Zum Beispiel schriftliche Rückmeldung oder Formular." />
      <Textarea label="Nachweis" value={evidence} onChange={(event) => setEvidence(event.target.value)} />
      <Input label="Datum des Widerrufs" type="date" value={revokedOn} onChange={(event) => setRevokedOn(event.target.value)} />
      <Button type="submit" disabled={pending}>
        Präferenz speichern
      </Button>
    </form>
  )
}
