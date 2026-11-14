import { useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { ApiError, confirmPasswordReset, requestPasswordReset } from '../../api/auth.ts'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { usePageTitle } from '../../usePageTitle.ts'

export function ResetPage() {
  usePageTitle('Passwort zurücksetzen')
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function request(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      setMessage(await requestPasswordReset(email))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Die Anfrage ist fehlgeschlagen.')
    }
  }

  async function confirm(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await confirmPasswordReset(token, password)
      setMessage('Das Passwort wurde geändert. Bitte neu anmelden.')
      setToken('')
      setPassword('')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Das Rücksetzen ist fehlgeschlagen.')
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-cream px-4 py-8">
      <div className="grid w-full max-w-lg gap-6">
        <form onSubmit={(event) => void request(event)} className="grid gap-4 border border-line bg-card p-6">
          <h1 className="text-2xl font-semibold">Passwort zurücksetzen</h1>
          <p className="text-sm leading-6 text-muted">
            Es ist kein E-Mail-Versand konfiguriert. Die Seite gibt kein Token aus. Ein Administrator startet lokal
            `python -m app.password_reset` und übergibt das einmalige Token persönlich.
          </p>
          <Input label="E-Mail" type="email" value={email} onChange={(event) => setEmail(event.target.value)} required />
          <Button type="submit">Anfrage senden</Button>
        </form>
        <form onSubmit={(event) => void confirm(event)} className="grid gap-4 border border-line bg-card p-6">
          <h2 className="text-lg font-semibold">Token einlösen</h2>
          <Input label="Einmaliges Token" value={token} onChange={(event) => setToken(event.target.value)} autoComplete="off" required />
          <Input label="Neues Passwort" type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" required />
          <Button type="submit">Passwort setzen</Button>
        </form>
        {message ? <p className="text-sm leading-6">{message}</p> : null}
        {error ? <p className="text-sm text-critical">{error}</p> : null}
        <Link to="/anmelden" className="text-sm font-semibold text-petrol">
          Zur Anmeldung
        </Link>
      </div>
    </main>
  )
}
