import { useState, type FormEvent } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router'
import { ApiError } from '../../api/auth.ts'
import { useAuth } from '../../auth.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { usePageTitle } from '../../usePageTitle.ts'

export function LoginPage() {
  usePageTitle('Anmelden')
  const { user, login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  const from = typeof location.state === 'object' && location.state && 'from' in location.state ? String(location.state.from) : '/'

  if (user) {
    return <Navigate to={from || '/'} replace />
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    setPending(true)
    setError('')
    try {
      await login(email, password)
      void navigate(from || '/')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Die Anmeldung ist fehlgeschlagen.')
    } finally {
      setPending(false)
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-cream px-4">
      <form onSubmit={(event) => void submit(event)} className="grid w-full max-w-md gap-4 border border-line bg-card p-6">
        <div>
          <p className="text-xs tracking-[0.16em] text-gold uppercase">HopLogic BrauPartner</p>
          <h1 className="mt-2 text-2xl font-semibold">Anmelden</h1>
          <p className="mt-2 text-sm leading-6 text-muted">Geschäftliche E-Mail und Passwort. Zugangsdaten sind nicht in der Anwendung hinterlegt.</p>
        </div>
        <Input label="E-Mail" type="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required />
        <Input label="Passwort" type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
        {error ? <p className="text-sm text-critical">{error}</p> : null}
        <Button type="submit" disabled={pending}>
          Anmelden
        </Button>
        <Link to="/passwort-zuruecksetzen" className="text-sm font-semibold text-petrol">
          Passwort zurücksetzen
        </Link>
      </form>
    </main>
  )
}
