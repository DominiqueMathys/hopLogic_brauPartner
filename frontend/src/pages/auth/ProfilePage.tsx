import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router'
import { ApiError, changePassword, updateProfile } from '../../api/auth.ts'
import { useAuth } from '../../auth.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { usePageTitle } from '../../usePageTitle.ts'

export function ProfilePage() {
  usePageTitle('Profil')
  const { user, refresh, logout } = useAuth()
  const navigate = useNavigate()
  const [firstName, setFirstName] = useState(user?.first_name ?? '')
  const [lastName, setLastName] = useState(user?.last_name ?? '')
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  async function saveProfile(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await updateProfile(firstName, lastName)
      await refresh()
      setMessage('Das Profil wurde gespeichert.')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Das Profil konnte nicht gespeichert werden.')
    }
  }

  async function savePassword(event: FormEvent) {
    event.preventDefault()
    setError('')
    try {
      await changePassword(currentPassword, newPassword)
      await logout()
      void navigate('/anmelden')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Das Passwort konnte nicht geändert werden.')
    }
  }

  if (!user) return null

  return (
    <div className="mx-auto grid max-w-xl gap-6">
      <header>
        <h1 className="text-3xl font-semibold">Profil</h1>
        <p className="mt-2 text-sm leading-6 text-muted">
          {user.email} · {user.role_name}
        </p>
      </header>
      <form onSubmit={(event) => void saveProfile(event)} className="grid gap-4 border border-line bg-card p-4">
        <Input label="Vorname" value={firstName} onChange={(event) => setFirstName(event.target.value)} required />
        <Input label="Nachname" value={lastName} onChange={(event) => setLastName(event.target.value)} required />
        <Button type="submit">Profil speichern</Button>
      </form>
      <form onSubmit={(event) => void savePassword(event)} className="grid gap-4 border border-line bg-card p-4">
        <h2 className="text-lg font-semibold">Passwort ändern</h2>
        <Input label="Bisheriges Passwort" type="password" value={currentPassword} onChange={(event) => setCurrentPassword(event.target.value)} autoComplete="current-password" required />
        <Input label="Neues Passwort" type="password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} autoComplete="new-password" required />
        <Button type="submit">Passwort ändern und abmelden</Button>
      </form>
      {message ? <p className="text-sm">{message}</p> : null}
      {error ? <p className="text-sm text-critical">{error}</p> : null}
    </div>
  )
}
