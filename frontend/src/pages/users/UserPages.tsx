import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import {
  ApiError,
  createUser,
  fetchAudit,
  fetchPermissions,
  fetchRoles,
  fetchUser,
  fetchUsers,
  saveRolePermissions,
  setUserStatus,
  updateUser,
  type AuditItem,
  type PermissionRecord,
  type RoleRecord,
  type SessionUser,
} from '../../api/auth.ts'
import { useAuth } from '../../auth.tsx'
import { Button } from '../../components/ui/Button.tsx'
import { ErrorState } from '../../components/ui/ErrorState.tsx'
import { Input } from '../../components/ui/Input.tsx'
import { LoadingState } from '../../components/ui/LoadingState.tsx'
import { Select } from '../../components/ui/Select.tsx'
import { formatDateTime } from '../../domain/partners.ts'
import { usePageTitle } from '../../usePageTitle.ts'

function Guard({ children }: { children: ReactNode }) {
  const { can } = useAuth()
  if (!can('users.manage') && !can('roles.read') && !can('audit.read')) {
    return <ErrorState title="Nicht verfügbar" description="Die Benutzerverwaltung ist für diese Rolle nicht freigegeben." />
  }
  return children
}

export function UserListPage() {
  usePageTitle('Benutzer')
  const { can } = useAuth()
  const [query, setQuery] = useState('')
  const [rows, setRows] = useState<SessionUser[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!can('users.manage')) return
    let active = true
    void fetchUsers(query)
      .then((result) => {
        if (active) setRows(result.items)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Die Benutzerliste konnte nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [query, can])

  return (
    <Guard>
      <div className="mx-auto grid max-w-5xl gap-4">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h1 className="text-3xl font-semibold">Benutzer</h1>
            <p className="mt-2 text-sm leading-6 text-muted">Konten, Rollen und Status. Nur die Administration verwaltet Konten.</p>
          </div>
          <div className="flex flex-wrap gap-3">
            {can('users.manage') ? (
              <Link to="/benutzer/neu" className="text-sm font-semibold text-petrol">
                Benutzer:in erstellen
              </Link>
            ) : null}
            {can('roles.read') ? (
              <Link to="/benutzer/rollen" className="text-sm font-semibold text-petrol">
                Rollen
              </Link>
            ) : null}
            {can('audit.read') ? (
              <Link to="/benutzer/protokoll" className="text-sm font-semibold text-petrol">
                Audit-Protokoll
              </Link>
            ) : null}
          </div>
        </header>
        {can('users.manage') ? (
          <Input label="Suche" value={query} onChange={(event) => setQuery(event.target.value)} hint="Name oder E-Mail" />
        ) : null}
        {error ? <p className="text-sm text-critical">{error}</p> : null}
        {!can('users.manage') ? null : rows === null ? (
          <LoadingState label="Benutzer werden geladen" />
        ) : (
          <div className="overflow-x-auto border border-line bg-card">
            <table className="w-full min-w-[40rem] text-sm">
              <caption className="sr-only">Benutzerkonten</caption>
              <thead>
                <tr className="border-b border-line text-left">
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">E-Mail</th>
                  <th className="px-3 py-2">Rolle</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2">Letzte Anmeldung</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => (
                  <tr key={row.id} className="border-b border-line">
                    <td className="px-3 py-2">
                      <Link to={`/benutzer/${row.id}`} className="font-semibold text-petrol">
                        {row.display_name}
                      </Link>
                      {row.is_demo ? <span className="ml-2 text-xs text-muted">Demo</span> : null}
                    </td>
                    <td className="px-3 py-2">{row.email}</td>
                    <td className="px-3 py-2">{row.role_name}</td>
                    <td className="px-3 py-2">{row.status === 'aktiv' ? 'Aktiv' : 'Deaktiviert'}</td>
                    <td className="px-3 py-2">{row.last_login_at ? formatDateTime(row.last_login_at) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </Guard>
  )
}

export function UserCreatePage() {
  usePageTitle('Benutzer erstellen')
  const navigate = useNavigate()
  const { can } = useAuth()
  const [roles, setRoles] = useState<RoleRecord[]>([])
  const [form, setForm] = useState({ first_name: '', last_name: '', email: '', role_code: 'vertrieb', password: '' })
  const [error, setError] = useState('')

  useEffect(() => {
    void fetchRoles()
      .then(setRoles)
      .catch(() => setRoles([]))
  }, [])

  if (!can('users.manage')) {
    return <ErrorState title="Nicht verfügbar" description="Nur die Administration darf Konten erstellen." />
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    try {
      const created = await createUser(form)
      void navigate(`/benutzer/${created.id}`)
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Das Konto konnte nicht erstellt werden.')
    }
  }

  return (
    <form onSubmit={(event) => void submit(event)} className="mx-auto grid max-w-xl gap-4">
      <h1 className="text-3xl font-semibold">Benutzer:in erstellen</h1>
      <Input label="Vorname" value={form.first_name} onChange={(event) => setForm({ ...form, first_name: event.target.value })} required />
      <Input label="Nachname" value={form.last_name} onChange={(event) => setForm({ ...form, last_name: event.target.value })} required />
      <Input label="Geschäftliche E-Mail" type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} required />
      <Select label="Rolle" value={form.role_code} onChange={(value) => setForm({ ...form, role_code: value })} options={roles.map((role) => ({ value: role.code, label: role.name }))} />
      <Input label="Erstes Passwort" type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} required />
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <Button type="submit">Konto erstellen</Button>
    </form>
  )
}

export function UserDetailPage() {
  usePageTitle('Benutzerkonto')
  const { userId = '' } = useParams()
  const { can, user: actor } = useAuth()
  const [row, setRow] = useState<SessionUser | null>(null)
  const [roles, setRoles] = useState<RoleRecord[]>([])
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

  useEffect(() => {
    let active = true
    void Promise.all([fetchUser(userId), fetchRoles()])
      .then(([account, roleRows]) => {
        if (!active) return
        setRow(account)
        setRoles(roleRows)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Das Konto wurde nicht gefunden.')
      })
    return () => {
      active = false
    }
  }, [userId])

  if (!can('users.manage')) {
    return <ErrorState title="Nicht verfügbar" description="Nur die Administration darf Konten öffnen." />
  }
  if (error) return <ErrorState title="Konto nicht verfügbar" description={error} />
  if (!row) return <LoadingState label="Konto wird geladen" />

  async function save(event: FormEvent) {
    event.preventDefault()
    if (!row) return
    try {
      const updated = await updateUser(row.id, {
        first_name: row.first_name,
        last_name: row.last_name,
        email: row.email,
        role_code: row.role_code,
      })
      setRow(updated)
      setMessage('Die Angaben wurden gespeichert.')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Das Konto konnte nicht gespeichert werden.')
    }
  }

  async function toggle() {
    if (!row) return
    const next = row.status === 'aktiv' ? 'deaktiviert' : 'aktiv'
    try {
      setRow(await setUserStatus(row.id, next))
      setMessage(next === 'aktiv' ? 'Das Konto ist wieder aktiv.' : 'Das Konto wurde deaktiviert.')
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Der Status konnte nicht geändert werden.')
    }
  }

  return (
    <form onSubmit={(event) => void save(event)} className="mx-auto grid max-w-xl gap-4">
      <h1 className="text-3xl font-semibold">{row.display_name}</h1>
      <p className="text-sm text-muted">Erstellt {formatDateTime(row.created_at)}</p>
      <Input label="Vorname" value={row.first_name} onChange={(event) => setRow({ ...row, first_name: event.target.value })} required />
      <Input label="Nachname" value={row.last_name} onChange={(event) => setRow({ ...row, last_name: event.target.value })} required />
      <Input label="E-Mail" type="email" value={row.email} onChange={(event) => setRow({ ...row, email: event.target.value })} required />
      <Select label="Rolle" value={row.role_code} onChange={(value) => setRow({ ...row, role_code: value })} options={roles.map((role) => ({ value: role.code, label: role.name }))} />
      <p className="text-sm leading-6">Berechtigungen dieser Rolle: {row.permissions.join(', ') || 'keine'}</p>
      {message ? <p className="text-sm">{message}</p> : null}
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <div className="flex flex-wrap gap-2">
        <Button type="submit">Speichern</Button>
        <Button type="button" variant={row.status === 'aktiv' ? 'danger' : 'secondary'} onClick={() => void toggle()} disabled={actor?.id === row.id && row.status === 'aktiv'}>
          {row.status === 'aktiv' ? 'Deaktivieren' : 'Reaktivieren'}
        </Button>
      </div>
    </form>
  )
}

export function RolesPage() {
  usePageTitle('Rollen')
  const { can } = useAuth()
  const [roles, setRoles] = useState<RoleRecord[]>([])
  const [permissions, setPermissions] = useState<PermissionRecord[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    void Promise.all([fetchRoles(), fetchPermissions()])
      .then(([roleRows, permissionRows]) => {
        if (!active) return
        setRoles(roleRows)
        setPermissions(permissionRows)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Die Rollen konnten nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [])

  if (!can('roles.read')) {
    return <ErrorState title="Nicht verfügbar" description="Die Berechtigungsübersicht ist der Administration vorbehalten." />
  }

  async function toggle(role: RoleRecord, code: string) {
    if (!can('roles.manage') || role.code === 'administrator') return
    const next = role.permissions.includes(code) ? role.permissions.filter((item) => item !== code) : [...role.permissions, code]
    try {
      const updated = await saveRolePermissions(role.code, next)
      setRoles((current) => current.map((item) => (item.code === role.code ? updated : item)))
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Die Berechtigung konnte nicht geändert werden.')
    }
  }

  return (
    <div className="mx-auto grid max-w-6xl gap-4">
      <h1 className="text-3xl font-semibold">Rollen und Berechtigungen</h1>
      <p className="text-sm leading-6 text-muted">
        Rechte gelten für konkrete Aktionen. Die Rolle allein öffnet kein Modul. Die Administration behält die Benutzerverwaltung.
      </p>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      <div className="overflow-x-auto border border-line bg-card">
        <table className="w-full min-w-[50rem] text-sm">
          <caption className="sr-only">Berechtigungsmatrix</caption>
          <thead>
            <tr className="border-b border-line text-left">
              <th className="px-3 py-2">Berechtigung</th>
              {roles.map((role) => (
                <th key={role.code} className="px-3 py-2">
                  {role.name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {permissions.map((permission) => (
              <tr key={permission.code} className="border-b border-line">
                <th className="px-3 py-2 text-left font-normal">
                  <span className="font-semibold">{permission.description}</span>
                  <span className="mt-1 block text-xs text-muted">{permission.code}</span>
                </th>
                {roles.map((role) => {
                  const checked = role.permissions.includes(permission.code)
                  const locked = role.code === 'administrator' || !can('roles.manage')
                  return (
                    <td key={role.code} className="px-3 py-2">
                      <input
                        type="checkbox"
                        checked={checked}
                        disabled={locked}
                        aria-label={`${role.name}: ${permission.description}`}
                        onChange={() => void toggle(role, permission.code)}
                      />
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export function AuditPage() {
  usePageTitle('Audit-Protokoll')
  const { can } = useAuth()
  const [rows, setRows] = useState<AuditItem[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!can('audit.read')) return
    let active = true
    void fetchAudit()
      .then((result) => {
        if (active) setRows(result.items)
      })
      .catch((caught: unknown) => {
        if (active) setError(caught instanceof ApiError ? caught.message : 'Das Protokoll konnte nicht geladen werden.')
      })
    return () => {
      active = false
    }
  }, [can])

  if (!can('audit.read')) {
    return <ErrorState title="Nicht verfügbar" description="Das Audit-Protokoll ist der Administration vorbehalten." />
  }

  return (
    <div className="mx-auto grid max-w-5xl gap-4">
      <h1 className="text-3xl font-semibold">Audit-Protokoll</h1>
      <p className="text-sm leading-6 text-muted">Anmeldungen, Konten, Rollen, Passwortänderungen und Exporte. Keine Passwörter und keine Tokens.</p>
      {error ? <p className="text-sm text-critical">{error}</p> : null}
      {rows === null ? (
        <LoadingState label="Protokoll wird geladen" />
      ) : (
        <div className="overflow-x-auto border border-line bg-card">
          <table className="w-full min-w-[40rem] text-sm">
            <caption className="sr-only">Sicherheitsrelevante Ereignisse</caption>
            <thead>
              <tr className="border-b border-line text-left">
                <th className="px-3 py-2">Zeit</th>
                <th className="px-3 py-2">Ereignis</th>
                <th className="px-3 py-2">Ergebnis</th>
                <th className="px-3 py-2">Konto</th>
                <th className="px-3 py-2">Detail</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id} className="border-b border-line">
                  <td className="px-3 py-2">{formatDateTime(row.occurred_at)}</td>
                  <td className="px-3 py-2">{row.event_type}</td>
                  <td className="px-3 py-2">{row.result}</td>
                  <td className="px-3 py-2">{row.actor_label ?? '—'}</td>
                  <td className="px-3 py-2">{row.detail ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
