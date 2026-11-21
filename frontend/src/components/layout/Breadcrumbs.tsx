import { Link, useLocation } from 'react-router'
import { currentNavItem } from '../../navigation.ts'

function detailTrail(pathname: string, root: string, labels: { create: string; edit: string; detail: string }): string[] {
  if (pathname === `${root}/neu`) {
    return [labels.create]
  }
  if (new RegExp(`^${root}/[^/]+/bearbeiten$`).test(pathname)) {
    return [labels.edit]
  }
  if (new RegExp(`^${root}/[^/]+$`).test(pathname)) {
    return [labels.detail]
  }
  return []
}

function pageTrail(pathname: string): string[] {
  if (pathname === '/verkaufschancen/pipeline') {
    return ['Pipeline']
  }
  if (pathname === '/kampagnen/vorlagen') {
    return ['Nachrichtenvorlagen']
  }
  if (pathname === '/kampagnen/vorlagen/neu') {
    return ['Nachrichtenvorlagen', 'Neue Vorlage']
  }
  if (/^\/kampagnen\/vorlagen\/[^/]+\/bearbeiten$/.test(pathname)) {
    return ['Nachrichtenvorlagen', 'Bearbeiten']
  }
  if (/^\/kampagnen\/vorlagen\/[^/]+$/.test(pathname)) {
    return ['Nachrichtenvorlagen', 'Vorlage']
  }
  if (pathname === '/benachrichtigungen/einstellungen') {
    return ['Einstellungen']
  }
  if (/^\/automatisierungen\/[^/]+\/protokoll$/.test(pathname)) {
    return ['Protokoll']
  }
  if (pathname === '/benutzer/neu') return ['Neu']
  if (pathname === '/festmanagement/neu') return ['Neue Anfrage']
  if (pathname === '/festmanagement/kalender') return ['Kalender']
  if (pathname === '/festmanagement/anfragen') return ['Anfragen']
  if (pathname === '/festmanagement/offerten') return ['Offerten']
  if (pathname === '/festmanagement/material') return ['Material']
  if (pathname === '/festmanagement/reservationen') return ['Reservationen']
  if (pathname === '/festmanagement/transporte') return ['Transporte']
  if (pathname === '/festmanagement/einsaetze') return ['Einsätze']
  if (pathname === '/festmanagement/auswertungen') return ['Auswertungen']
  if (/^\/festmanagement\/[^/]+\/bearbeiten$/.test(pathname)) return ['Bearbeiten']
  if (/^\/festmanagement\/[^/]+$/.test(pathname)) return ['Fest']
  if (pathname === '/integration/vorschau') return ['Vorschau']
  if (pathname === '/integration/laeufe') return ['Synchronisationen']
  if (pathname === '/integration/konflikte') return ['Konflikte']
  if (/^\/integration\/laeufe\/[^/]+$/.test(pathname)) return ['Synchronisationen', 'Detail']
  if (pathname === '/benutzer/rollen') return ['Rollen']
  if (pathname === '/benutzer/protokoll') return ['Audit-Protokoll']
  if (/^\/benutzer\/[^/]+$/.test(pathname)) return ['Konto']
  return [
    ...detailTrail(pathname, '/vertriebspartner', { create: 'Neuer Partner', edit: 'Bearbeiten', detail: 'Partner' }),
    ...detailTrail(pathname, '/verkaufschancen', { create: 'Neue Verkaufschance', edit: 'Bearbeiten', detail: 'Verkaufschance' }),
    ...detailTrail(pathname, '/produkte', { create: 'Neues Produkt', edit: 'Bearbeiten', detail: 'Produkt' }),
    ...detailTrail(pathname, '/bestellungen', { create: 'Neue Bestellung', edit: 'Bearbeiten', detail: 'Bestellung' }),
    ...detailTrail(pathname, '/kundenservice', { create: 'Neues Ticket', edit: 'Bearbeiten', detail: 'Ticket' }),
    ...detailTrail(pathname, '/segmente', { create: 'Neues Segment', edit: 'Bearbeiten', detail: 'Segment' }),
    ...detailTrail(pathname, '/kontakte', { create: 'Neuer Kontakt', edit: 'Bearbeiten', detail: 'Kontakt' }),
    ...detailTrail(pathname, '/aktivitaeten', { create: 'Neue Aktivität', edit: 'Bearbeiten', detail: 'Aktivität' }),
    ...detailTrail(pathname, '/aufgaben', { create: 'Neue Aufgabe', edit: 'Bearbeiten', detail: 'Aufgabe' }),
    ...detailTrail(pathname, '/kampagnen', { create: 'Neue Kampagne', edit: 'Bearbeiten', detail: 'Kampagne' }),
    ...detailTrail(pathname, '/automatisierungen', { create: 'Neue Automatisierung', edit: 'Bearbeiten', detail: 'Automatisierung' }),
  ]
}

export function Breadcrumbs() {
  const { pathname } = useLocation()
  const current = currentNavItem(pathname)
  const onDashboard = pathname === '/'
  const trail = pageTrail(pathname)

  return (
    <nav aria-label="Brotkrumen">
      <ol className="flex flex-wrap items-center gap-1 text-xs text-muted">
        <li>
          {onDashboard ? (
            <span aria-current="page">Dashboard</span>
          ) : (
            <Link to="/" className="hover:text-ink">
              Dashboard
            </Link>
          )}
        </li>
        {onDashboard ? null : (
          <li className="flex items-center gap-1" aria-current={trail.length === 0 ? 'page' : undefined}>
            <span aria-hidden="true">/</span>
            {current && trail.length > 0 ? (
              <Link to={current.path} className="hover:text-ink">
                {current.label}
              </Link>
            ) : (
              <span>{current?.label ?? (pathname === '/profil' ? 'Profil' : 'Seite')}</span>
            )}
          </li>
        )}
        {trail.map((label) => (
          <li key={label} className="flex items-center gap-1" aria-current="page">
            <span aria-hidden="true">/</span>
            <span>{label}</span>
          </li>
        ))}
      </ol>
    </nav>
  )
}
