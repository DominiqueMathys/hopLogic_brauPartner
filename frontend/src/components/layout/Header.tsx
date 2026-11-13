import { useState } from 'react'
import { Link, useNavigate } from 'react-router'
import { BellIcon, MenuIcon, UserIcon } from '../icons.tsx'
import { SearchField } from '../ui/SearchField.tsx'
import { Modal } from '../ui/Modal.tsx'
import { Breadcrumbs } from './Breadcrumbs.tsx'
import { navigation } from '../../navigation.ts'

type HeaderProps = {
  menuExpanded: boolean
  menuLabel: string
  onToggleMenu: () => void
}

export function Header({ menuExpanded, menuLabel, onToggleMenu }: HeaderProps) {
  const navigate = useNavigate()
  const [query, setQuery] = useState('')
  const [notificationsOpen, setNotificationsOpen] = useState(false)
  const [profileOpen, setProfileOpen] = useState(false)
  const normalized = query.trim().toLocaleLowerCase('de-LI')
  const results = navigation.filter((item) => item.label.toLocaleLowerCase('de-LI').includes(normalized))

  function choose(path: string) {
    setQuery('')
    void navigate(path)
  }

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
            className="inline-flex h-11 w-11 items-center justify-center border border-line bg-card"
            aria-haspopup="dialog"
            onClick={() => setNotificationsOpen(true)}
          >
            <BellIcon />
            <span className="sr-only">Benachrichtigungen</span>
          </button>
          <button
            type="button"
            className="inline-flex h-11 w-11 items-center justify-center border border-line bg-card"
            aria-haspopup="dialog"
            onClick={() => setProfileOpen(true)}
          >
            <UserIcon />
            <span className="sr-only">Benutzerprofil</span>
          </button>
        </div>
      </div>
      <Modal open={notificationsOpen} title="Benachrichtigungen" onClose={() => setNotificationsOpen(false)}>
        <p>
          Es ist kein Benachrichtigungsdienst verbunden. Hier erscheinen später echte Meldungen aus Vertrieb,
          Service und Aufgaben. Es werden keine Beispielmeldungen angezeigt.
        </p>
      </Modal>
      <Modal open={profileOpen} title="Benutzerprofil" onClose={() => setProfileOpen(false)}>
        <p>
          Es ist kein Benutzerkonto angemeldet. Name, Rolle und Abmeldung folgen mit der Anmeldung in einer
          späteren Phase.
        </p>
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
      hint="Durchsucht nur die Menüpunkte. CRM-Datensätze sind noch nicht angebunden."
      placeholder="Menüpunkt suchen"
      value={query}
      onChange={onChange}
      results={results.map((item) => ({ id: item.id, label: item.label, path: item.path }))}
      onSelect={onSelect}
    />
  )
}
