import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { Navigate, Outlet, useLocation } from 'react-router'
import { ApiError, loginRequest, logoutRequest, sessionRequest, type SessionUser } from './api/auth.ts'
import { LoadingState } from './components/ui/LoadingState.tsx'

type AuthValue = {
  user: SessionUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => Promise<void>
  refresh: () => Promise<void>
  can: (permission: string) => boolean
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<SessionUser | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    try {
      const session = await sessionRequest()
      setUser(session.user)
    } catch {
      setUser(null)
    }
  }, [])

  useEffect(() => {
    let active = true
    void sessionRequest()
      .then((session) => {
        if (active) setUser(session.user)
      })
      .catch(() => {
        if (active) setUser(null)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const session = await loginRequest(email, password)
    setUser(session.user)
  }, [])

  const logout = useCallback(async () => {
    try {
      await logoutRequest()
    } catch (caught) {
      if (!(caught instanceof ApiError) || caught.status !== 401) {
        setUser(null)
        throw caught
      }
    }
    setUser(null)
  }, [])

  const value = useMemo<AuthValue>(
    () => ({
      user,
      loading,
      login,
      logout,
      refresh,
      can: (permission) => Boolean(user?.permissions.includes(permission)),
    }),
    [user, loading, login, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) {
    throw new Error('Die Anmeldung ist nicht verfügbar.')
  }
  return value
}

export function RequireAuth() {
  const { user, loading } = useAuth()
  const location = useLocation()
  if (loading) {
    return (
      <div className="grid min-h-screen place-items-center bg-cream">
        <LoadingState label="Anmeldung wird geprüft" />
      </div>
    )
  }
  if (!user) {
    return <Navigate to="/anmelden" replace state={{ from: location.pathname }} />
  }
  return <Outlet />
}
