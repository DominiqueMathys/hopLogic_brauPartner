export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

export type SessionUser = {
  id: string
  first_name: string
  last_name: string
  display_name: string
  email: string
  role_code: string
  role_name: string
  status: string
  created_at: string
  last_login_at: string | null
  permissions: string[]
  is_demo: boolean
}

export type SessionResponse = {
  user: SessionUser
  csrf_token: string
}

async function send(path: string, init?: RequestInit): Promise<unknown> {
  let response: Response
  try {
    response = await fetch(path, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
        ...init?.headers,
      },
    })
  } catch {
    throw new ApiError(0, 'Die Verbindung zur API ist fehlgeschlagen.')
  }
  if (response.status === 204) {
    return null
  }
  const body: unknown = await response.json().catch(() => null)
  if (!response.ok) {
    const detail = body && typeof body === 'object' && 'detail' in body ? body.detail : null
    throw new ApiError(response.status, typeof detail === 'string' ? detail : 'Die Anfrage konnte nicht verarbeitet werden.')
  }
  return body
}

export function sessionRequest(): Promise<SessionResponse> {
  return send('/api/auth/me') as Promise<SessionResponse>
}

export function loginRequest(email: string, password: string): Promise<SessionResponse> {
  return send('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) }) as Promise<SessionResponse>
}

export function logoutRequest(): Promise<void> {
  return send('/api/auth/logout', { method: 'POST' }) as Promise<void>
}

export function updateProfile(firstName: string, lastName: string): Promise<SessionUser> {
  return send('/api/auth/profile', {
    method: 'PATCH',
    body: JSON.stringify({ first_name: firstName, last_name: lastName }),
  }) as Promise<SessionUser>
}

export function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  return send('/api/auth/password', {
    method: 'POST',
    body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
  }) as Promise<void>
}

export function requestPasswordReset(email: string): Promise<string> {
  return send('/api/auth/password-reset/request', { method: 'POST', body: JSON.stringify({ email }) }).then((body) => {
    if (body && typeof body === 'object' && 'detail' in body && typeof body.detail === 'string') {
      return body.detail
    }
    return 'Die Anfrage wurde entgegengenommen.'
  })
}

export function confirmPasswordReset(token: string, newPassword: string): Promise<void> {
  return send('/api/auth/password-reset/confirm', {
    method: 'POST',
    body: JSON.stringify({ token, new_password: newPassword }),
  }) as Promise<void>
}

export type DirectoryEntry = {
  id: string
  display_name: string
  role_code: string
  role_name: string
}

export function fetchDirectory(): Promise<DirectoryEntry[]> {
  return send('/api/users/directory') as Promise<DirectoryEntry[]>
}

export type UserList = {
  items: SessionUser[]
  total: number
}

export function fetchUsers(q: string): Promise<UserList> {
  const params = new URLSearchParams({ page: '1', page_size: '100' })
  if (q.trim()) params.set('q', q.trim())
  return send(`/api/users?${params}`) as Promise<UserList>
}

export function fetchUser(id: string): Promise<SessionUser> {
  return send(`/api/users/${id}`) as Promise<SessionUser>
}

export function createUser(body: Record<string, string>): Promise<SessionUser> {
  return send('/api/users', { method: 'POST', body: JSON.stringify(body) }) as Promise<SessionUser>
}

export function updateUser(id: string, body: Record<string, string>): Promise<SessionUser> {
  return send(`/api/users/${id}`, { method: 'PUT', body: JSON.stringify(body) }) as Promise<SessionUser>
}

export function setUserStatus(id: string, status: string): Promise<SessionUser> {
  return send(`/api/users/${id}/status`, { method: 'POST', body: JSON.stringify({ status }) }) as Promise<SessionUser>
}

export type RoleRecord = {
  code: string
  name: string
  description: string
  permissions: string[]
}

export type PermissionRecord = {
  code: string
  resource: string
  action: string
  description: string
}

export function fetchRoles(): Promise<RoleRecord[]> {
  return send('/api/roles') as Promise<RoleRecord[]>
}

export function fetchPermissions(): Promise<PermissionRecord[]> {
  return send('/api/roles/permissions') as Promise<PermissionRecord[]>
}

export function saveRolePermissions(code: string, permissions: string[]): Promise<RoleRecord> {
  return send(`/api/roles/${code}/permissions`, {
    method: 'PUT',
    body: JSON.stringify({ permissions }),
  }) as Promise<RoleRecord>
}

export type AuditItem = {
  id: string
  event_type: string
  occurred_at: string
  actor_id: string | null
  actor_label: string | null
  resource_type: string | null
  resource_id: string | null
  result: string
  detail: string | null
}

export function fetchAudit(): Promise<{ items: AuditItem[] }> {
  return send('/api/audit?page=1&page_size=100') as Promise<{ items: AuditItem[] }>
}
