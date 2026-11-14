import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { errorMessage, fetchNoticeSummary, fetchNotices, markNoticeRead } from '../../api/engagement.ts'
import { useAuth } from '../../auth.tsx'
import { BellIcon, MenuIcon, UserIcon } from '../icons.tsx'
import { Button } from '../ui/Button.tsx'
import { SearchField } from '../ui/SearchField.tsx'
import { Modal } from '../ui/Modal.tsx'
import { Breadcrumbs } from './Breadcrumbs.tsx'
import { navAllowed, navigation } from '../../navigation.ts'
import type { Notice } from '../../domain/engagement.ts'

type HeaderProps = {
  menuExpanded: boolean
  menuLabel: string
  onToggleMenu: () => void
}

export function Header({ menuExpanded, menuLabel, onToggleMenu }: HeaderProps) {
  const navigate = useNavigate()
  const { user, logout, can } = useAuth()
  const [query, setQuery] = useState('')
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const [unread, setUnread] = useState<number | null>(null)
  const [notices, setNotices] = useState<Notice[]>([])
  const [noticeError, setNoticeError] = useState('')
  const name = user?.display_name ?? ''
  const visibleNav = navigation.filter((item) => navAllowed(item, can))
  const normalized = query.trim().toLocaleLowerCase('de-LI')
  const results = visibleNav.filter((item) => item.label.toLocaleLowerCase('de-LI').includes(normalized))

  function choose(path: string) {
    setQuery('')
    void navigate(path)
  }

  useEffect(() => {
    if (!name) return
    let active = true
    function load() {
      void fetchNoticeSummary(name)
        .then((summary) => {
          if (active) setUnread(summary.unread)
        })
        .catch(() => {
          if (active) setUnread(null)
        })
    }
    load()
    const timer = window.setInterval(load, 30000)
    return () => {
      active = false
      window.clearInterval(timer)
    }
  }, [name])

  useEffect(() => {
    if (!notificationsOpen || !name) return
    let active = true
    void fetchNotices({ recipient: name, unread: false })
      .then((result) => {
        if (!active) return
        setNotices(result.items.slice(0, 8))
        setUnread(result.unread)
        setNoticeError('')
      })
      .catch((caught: unknown) => {
        if (active) setNoticeError(errorMessage(caught))
      })
    return () => {
      active = false
    }
  }, [notificationsOpen, name])

  return (
    <header className="sticky top-0 z-30 border-b border-line bg-cream">
      <div className="flex flex-wrap items-center gap-3 px-4 py-3 md:px-6">
        <button
          type="button"
          className="inline-flex h-11 w-11 items-center justify-center border border-line bg-card"
          aria-controls="app-sidebar"
          aria-expanded={menuExpanded}
          onClick={onToggleMenu}
        >
          <MenuIcon />
          <span className="sr-only">{menuLabel}</span>
        </button>
        <div className="min-w-0">
          <Link to="/" className="block truncate text-sm font-semibold text-ink">
            HopLogic BrauPartner
          </Link>
          <Breadcrumbs />
        </div>
        <div className="order-last w-full md:order-none md:w-80">
          <SearchBox query={query} results={results} onChange={setQuery} onSelect={choose} />
        </div>
        <div className="ml-auto flex items-center gap-2">
          <button
            type="button"
            className="relative inline-flex h-11 w-11 items-center justify-center border border-line bg-card"
            aria-haspopup="dialog"
            onClick={() => setNotificationsOpen(true)}
          >
            <BellIcon />
            <span className="sr-only">Benachrichtigungen{unread ? `, ${unread} ungelesen` : ''}</span>
            {unread ? (
              <span className="absolute top-1 right-1 min-w-5 bg-petrol px-1 text-center text-[10px] leading-4 font-semibold text-cream">
                {unread > 99 ? '99+' : unread}
              </span>
            ) : null}
          </button>
          <button
            type="button"
            className="inline-flex h-11 items-center gap-2 border border-line bg-card px-3"
            aria-haspopup="dialog"
            onClick={() => setProfileOpen(true)}
          >
            <UserIcon />
            <span className="max-w-40 truncate text-sm">{user?.display_name}</span>
            <span className="sr-only">Benutzerprofil</span>
          </button>
        </div>
      </div>
      <Modal open={notificationsOpen} title="Benachrichtigungen" onClose={() => setNotificationsOpen(false)}>
        <p className="text-sm leading-6">Hinweise für {name}. Meldungen anderer Konten werden nicht angezeigt.</p>
        {noticeError ? <p className="mt-3 text-sm leading-6">{noticeError}</p> : null}
        {notices.length === 0 ? (
          <p className="mt-3 text-sm">Keine gespeicherten Hinweise für dieses Konto.</p>
        ) : (
          <ul className="mt-3 grid gap-2">
            {notices.map((item) => (
              <li key={item.id} className={item.read_at ? 'border border-line px-3 py-2' : 'border border-petrol bg-petrol-soft px-3 py-2'}>
                <p className="text-sm font-semibold">{item.title}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {item.href ? (
                    <Link to={item.href} className="text-sm font-semibold text-petrol" onClick={() => setNotificationsOpen(false)}>
                      Datensatz öffnen
                    </Link>
                  ) : null}
                  {!item.read_at ? (
                    <Button
                      variant="secondary"
                      onClick={() => {
                        void markNoticeRead(item.id, name)
                          .then(() => fetchNotices({ recipient: name }))
                          .then((result) => {
                            setNotices(result.items.slice(0, 8))
                            setUnread(result.unread)
                          })
                          .catch((caught: unknown) => setNoticeError(errorMessage(caught)))
                      }}
                    >
                      Gelesen
                    </Button>
                  ) : null}
                </div>
              </li>
            ))}
          </ul>
        )}
        <Link to="/benachrichtigungen" className="mt-4 inline-flex text-sm font-semibold text-petrol" onClick={() => setNotificationsOpen(false)}>
          Benachrichtigungscenter
        </Link>
      </Modal>
      <Modal open={profileOpen} title="Angemeldet" onClose={() => setProfileOpen(false)}>
        <p className="text-sm leading-6">
          {user?.display_name}
          <span className="mt-1 block text-muted">{user?.role_name}</span>
          <span className="mt-1 block">{user?.email}</span>
        </p>
        <div className="mt-4 flex flex-wrap gap-3">
          <Link to="/profil" className="text-sm font-semibold text-petrol" onClick={() => setProfileOpen(false)}>
            Profil und Passwort
          </Link>
          {can('users.manage') ? (
            <Link to="/benutzer" className="text-sm font-semibold text-petrol" onClick={() => setProfileOpen(false)}>
              Benutzerverwaltung
            </Link>
          ) : null}
          <Button
            variant="secondary"
            onClick={() => {
              void logout().then(() => {
                setProfileOpen(false)
                void navigate('/anmelden')
              })
            }}
          >
            Abmelden
          </Button>
        </div>
      </Modal>
    </header>
  )
}

function SearchBox({
  query,
  results,
  onChange,
  onSelect,
}: {
  query: string
  results: typeof navigation
  onChange: (value: string) => void
  onSelect: (path: string) => void
}) {
  return (
    <SearchField
      label="Suche in der Navigation"
      hint="Durchsucht die freigegebenen Menüpunkte."
      placeholder="Menüpunkt suchen"
      value={query}
      onChange={onChange}
      results={results.map((item) => ({ id: item.id, label: item.label, path: item.path }))}
      onSelect={onSelect}
    />
  )
}
